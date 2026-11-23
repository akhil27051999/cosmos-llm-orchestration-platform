# Cosmos learning log

What I built each day, the concepts behind it, and the questions an interviewer could ask.
Newest entries at the bottom. Each entry links to the PR that holds the code.

---

## 2026-10-26: M0 and M0.5, project skeleton and CI
**Built:** FastAPI app with `/health`, pytest setup, README, decision record 0001 (PRs #1–#4);
GitHub Actions CI on every PR, pinned dependencies, protected `main` branch (#5, #6).

**Concepts**
- **ASGI:** uvicorn is the server (port, HTTP parsing), FastAPI is the application (routing). ASGI is the contract between them.
- **`--reload`** runs a parent process (the file watcher) and a child process (the server). Never use it in production: restarts drop in-flight requests.
- **venv:** each project gets its own isolated Python packages.
- **`sys.path`:** why pytest needed `pythonpath = .` and uvicorn didn't.
- **CI you have seen fail:** I broke a test on purpose to prove CI goes red, then reverted it.
- **Pinning** dependencies and the runner (`ubuntu-26.04`): a red build should mean I changed something.
- **Branch protection:** PR required, `test` check required, no bypass.

**Interview questions**
- Why trigger CI on both `pull_request` and `push` to `main`?
- What does `permissions: contents: read` protect against?
- Why is a CI check you've never seen fail untrustworthy?

---

## 2026-10-27: M1, Job state machine (#7)
**Built:** `Job` + `JobStatus` (pending, running, succeeded, failed, cancelled), `ALLOWED_TRANSITIONS`
table, `transition_to()` that refuses illegal moves, `InvalidTransition`, `is_terminal`.

**Concepts**
- **State machine as data:** one table, so there are no if/else chains to keep in sync.
- **Terminal states** map to an empty set, so no special-case code is needed.
- **Check before change:** a rejected move must leave the job untouched.
- **TDD:** red, then green, then refactor. Every feature commit follows a failing test commit.
- **Retries stay inside `running`** (approach B), so the state machine stays small.

**Interview questions**
- A worker reports success just after a user cancels. What stops `cancelled → succeeded`?
- Why is the state machine "necessary but not enough"? (The worker may hold a stale copy; that's the M6 version check.)

---

## 2026-10-28: M2, IDs and the repository port (#8)
**Built:** `Job.id` (UUIDv4), `JobRepository` protocol (port), `InMemoryJobRepository` (adapter),
decision record 0002.

**Concepts**
- **Hexagonal architecture:** the service depends on a **port**, and adapters plug in. Same idea as kubelet → CRI → containerd.
- **UUIDv4:** 128 bits, 122 of them random. Shown as 32 hex digits. Unique without coordination.
- **`field(default_factory=uuid.uuid4)`:** a fresh value per object. The classic shared-default bug.
- **`get` returns `None`:** the repository reports facts; the layer above decides whether "missing" is an error.

**Interview questions**
- Why should the service never import a concrete database adapter?
- UUIDv4 vs auto-increment IDs: trade-offs?

---

## 2026-10-29 → 31: M3, Job service (#9)
**Built:** `JobService.submit / get / cancel`, `JobNotFound`, `JobRepository.update`; the in-memory
adapter now stores and returns **copies**.

**Concepts**
- **Dependency injection:** `JobService(repo)` receives its repository, so tests pass an in-memory one and production passes Postgres.
- **A test that passed for the wrong reason:** the in-memory dict held *the same object*, so a cancel "saved" itself without `update`. Making the fake behave like a real database (copies) exposed the bug.
- **Fix forward:** correct a pushed mistake with a new commit instead of rewriting history.

**Interview questions**
- How can a fake/in-memory dependency hide a real bug? How do you prevent it?
- Where should "not found → error" be decided, and why there?

---

## 2026-11-02 → 06: M4, HTTP API (#10)
**Built:** `POST /jobs` (201), `GET /jobs/{job_id}` (200/404/422), `POST /jobs/{job_id}/cancel`
(200/404/409), `JobResponse` model, exception handlers mapping domain errors to HTTP.

**Concepts**
- **Composition root:** `main.py` is the only place that picks concrete adapters.
- **Response model:** the public JSON shape stays separate from the domain object.
- **404 vs 409 vs 422:** not found / conflicts with current state / malformed input.
- **`POST …/cancel` instead of `DELETE`:** cancelling doesn't remove the job.
- **Refactor only under green tests:** the tests caught a copy-paste `submit()` inside GET.
- **One shared service:** a repository created per request would start empty every time.

**Interview questions**
- Why 201 now and 202 later (once a worker runs jobs)?
- Why map errors in one exception handler instead of try/except in every route?

---

## 2026-11-23 → 24: M5, idempotency keys (PR #11)
**Built:** `Job.idempotency_key`; repository lookup by key (a second dict key → id, like a DB index);
`submit()` returns `(job, created)`; `Idempotency-Key` header → 201 for new, 200 for replay.

**Concepts**
- **Idempotency:** repeating a request has the same effect as doing it once. Needed for POST retries.
- **The client creates the key:** only the client knows "this is the same request again".
- **Index as a pointer:** store `key → id`, not a second copy of the job (one source of truth).
- **Changing a contract safely:** refactor first (`submit` returns a pair, all callers updated, tests green), then add behaviour.
- **Check-then-insert race:** two same-key requests at the same instant can both create a job. It's documented here and fixed in M6 by a **unique index**.

**Interview questions**
- Walk through a duplicate POST, layer by layer.
- How do you make idempotency safe under concurrency?

**Model answers**

*Q1. The same key arrives twice. What happens, layer by layer?*
1. **HTTP:** the client sends `POST /jobs` with the header `Idempotency-Key: abc`. FastAPI reads it into the
   `idempotency_key` parameter through `Header(default=None)`.
2. **Route → service:** the route calls `job_service.submit(idempotency_key="abc")`.
3. **Service:** the key is not `None`, so it asks the repository: `get_by_idempotency_key("abc")`.
4. **Repository:** the second dict maps `"abc"` to the job's id, then `get(job_id)` returns a **copy** of that job.
5. **Back up:** the service returns `(existing, False)`. The route sees `created=False`, sets
   `response.status_code = 200` and returns the same `JobResponse`. The first request got 201.

*Q2. Why does `submit` return `(job, created)` instead of just `job`?*
The route must choose **201 (new)** or **200 (replay)**, and the job looks the same in both cases, so the job alone
can't tell it which. Only the service knows whether it created one. The service stays free of HTTP: it returns a
fact (`created`), and the HTTP layer turns that fact into a status code.

*Q3. Two same-key requests arrive at the same instant. What goes wrong, and how does M6 fix it?*
Both requests check the key, both see "no job yet", and both create one: two jobs for one key (a check-then-insert
race). In M6, a **unique index** on `idempotency_key` makes the database reject the second insert. The service
must also **catch** that unique-violation error, fetch the job that won and return `(existing, False)`. Without
that last step the client gets a 500 instead of a clean replay.

*Q4. Why is `idempotency_key` optional (`None` by default)?*
- **Backward compatibility:** `POST /jobs` worked without the header before M5. Making it required would break
  existing clients with a 422.
- **The client decides:** a client that never retries doesn't need a key. A client that retries without a key
  accepts that it may get duplicates.
- **In the code:** the `None` default means old calls like `service.submit()` still work unchanged.
- Stripe's API uses the same design: the key is optional, and recommended for POST retries.

---

<!-- Add the next entry here after each module: date, PR, built, concepts, interview questions. -->
