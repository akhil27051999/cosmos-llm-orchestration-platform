# Cosmos learning log

What I built, block by block, the concepts behind each block, and the questions an interviewer could ask.
Newest modules at the bottom. Each module links to the PR that holds the code.

**How to use this log**
1. Read a block's code, then **What it is, line by line**, then the **Built** line.
2. Cover the **Model answers** and answer the **Questions** out loud.
3. Compare. If you couldn't answer, re-read **Concepts** and open the file in the repo.

Code is shown as it is today (after M5), so a block may include a line added in a later module; that's noted.

---

## 2026-10-26: M0, project skeleton (PRs #1–#4)
**Goal:** a running FastAPI app with one tested endpoint, so every later module has a place to live.

### Block 1: `requirements.txt`, pinned dependencies
```text
fastapi==0.162.0
uvicorn[standard]==0.54.0
pytest==9.1.1
httpx==0.28.1
```
**What it is, line by line**
- `fastapi==0.162.0`: the web framework. `==` means "exactly this version", nothing newer.
- `uvicorn[standard]==0.54.0`: the server that runs the app. `[standard]` is an "extra": it also installs the
  faster optional parts (uvloop for the event loop, httptools for parsing HTTP).
- `pytest==9.1.1`: the test runner. Only needed for development and CI, but kept in one file for simplicity.
- `httpx==0.28.1`: an HTTP client. We never import it ourselves; FastAPI's `TestClient` uses it under the hood.
- `pip install -r requirements.txt` reads this file line by line and installs each package.

**Built:** the four packages the project needs, each pinned to an exact version.

**Concepts**
- **FastAPI** is the web framework (routing, validation). **uvicorn** is the server that runs it.
  `[standard]` adds faster extras (uvloop, httptools). **pytest** runs tests. **httpx** is what `TestClient` uses.
- **Pinning (`==`):** the same versions on my laptop, in CI and in production. A red build then means *I* changed
  something, not that a library released a new version overnight.
- **Gap:** only *direct* dependencies are pinned. Their own dependencies (starlette, pydantic, anyio…) can still
  move. A lock file (`pip-tools`, `uv lock`) pins the whole tree.
- **venv:** `.venv/` keeps these packages isolated per project, and it's in `.gitignore` because it's rebuilt from
  this file, never committed.

**Questions**
- Why pin exact versions instead of `fastapi>=0.100`?
- What's still not reproducible with this file?

**Model answers**
- *Why pin?* Reproducible builds. With `>=`, a new release can break CI with zero changes on my side, and two
  machines can run different code. Upgrades become a deliberate PR I can test and roll back.
- *Not reproducible?* Transitive dependencies aren't pinned, and nothing checks file hashes. A lock file with
  hashes (`pip install --require-hashes`) fixes both; it also guards against a tampered package.

### Block 2: `app/main.py`, the app and `/health`
```python
from fastapi import FastAPI

app = FastAPI(title="Cosmos", description="Asynchronous job-orchestration API for LLM workloads.", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok"}
```
**What it is, line by line**
- `from fastapi import FastAPI`: imports the class that builds a web application.
- `app = FastAPI(title=..., description=..., version=...)`: creates **the** application object. uvicorn looks for
  this exact name when you run `uvicorn app.main:app`. The three arguments only fill the docs page at `/docs`.
- `@app.get("/health")`: a decorator. It tells `app`: "when a `GET` request arrives for `/health`, call the
  function right below me".
- `def health_check():`: the handler function. Its name doesn't matter to HTTP; only the path in the decorator does.
- `return {"status": "ok"}`: a plain Python dict. FastAPI turns it into the JSON body `{"status": "ok"}` and
  sends it with status 200 (the default for GET).

**Built:** the application object and one endpoint that returns `{"status": "ok"}`.

**Concepts**
- **ASGI:** the contract between a Python web server and a Python web app. uvicorn (server) speaks HTTP on a port;
  `app` (application) receives each request through ASGI. Run it with `uvicorn app.main:app`, which means
  "module `app.main`, object `app`".
- **Decorator `@app.get("/health")`:** registers the function below as the handler for `GET /health`.
- **Return a dict → JSON:** FastAPI serializes it and sets `Content-Type: application/json`.
- **`title`, `version`:** appear in the auto-generated docs at `/docs` (OpenAPI).
- **Health endpoint:** what a load balancer or Kubernetes probe calls. Today it only proves the process answers;
  in S2 it splits into **liveness** (process alive) and **readiness** (can reach Postgres and Redis).
- **`--reload`:** a dev-only flag. A parent process watches files and restarts a child server. Never in production:
  restarts drop in-flight requests.

**Questions**
- What's the difference between uvicorn and FastAPI?
- Why is "returns 200" a weak health check, and what will replace it?

**Model answers**
- *uvicorn vs FastAPI?* uvicorn is the server: it owns the port, parses HTTP and manages connections. FastAPI is
  the application: it maps paths to functions and validates input and output. ASGI is the interface between them,
  so either side can be swapped.
- *Weak health check?* It says the process is up, not that it can do its job. If Postgres is down, `/health` still
  says ok, and the load balancer keeps sending traffic to a pod that will fail every request. A readiness check
  that touches its dependencies takes the pod out of rotation instead. Liveness stays simple, so a database
  outage doesn't make Kubernetes restart every pod.

### Block 3: `pytest.ini`
```ini
[pytest]
pythonpath = .
testpaths = tests
```
**What it is, line by line**
- `[pytest]`: the section header. pytest only reads settings under this name in `pytest.ini`.
- `pythonpath = .`: adds the project root (`.`) to Python's import search path while tests run, so test files
  can write `from app.main import app`.
- `testpaths = tests`: when you just type `pytest`, it searches only the `tests/` folder for tests.

**Built:** pytest settings for the project.

**Concepts**
- **`sys.path`:** the list of folders Python searches for imports. `from app.main import app` works only if the
  project root is on it.
- **`pythonpath = .`** adds the project root. uvicorn didn't need it because it's started *from* the root, and the
  current folder is on the path. pytest's entry point is not, so `import app` failed until this line.
- **`testpaths = tests`:** pytest only looks in `tests/`, so a stray `test_*.py` elsewhere isn't collected.

**Questions**
- Why did uvicorn find `app` but pytest didn't?

**Model answers**
- When you run `uvicorn app.main:app` from the root, the current folder is on `sys.path`. pytest, run as a console
  script, puts its own location and the test file's folder on the path instead, so the root was missing.
  `pythonpath = .` adds it explicitly, so the behaviour no longer depends on how pytest was started.

### Block 4: `tests/test_health.py`
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```
**What it is, line by line**
- `from fastapi.testclient import TestClient`: a fake browser that talks to the app directly, in the same process.
- `from app.main import app`: imports the application object from Block 2.
- `client = TestClient(app)`: wraps the app. `client.get(...)` now calls the app as if a real request came in.
  It's created once at the top, and every test in the file uses it.
- `def test_health_check():`: the name starts with `test_`, so pytest finds and runs it automatically.
- `response = client.get("/health")`: sends `GET /health` and keeps the full response.
- `assert response.status_code == 200`: if the status isn't 200, the test fails and pytest shows both values.
- `assert response.json() == {"status": "ok"}`: parses the JSON body and compares it with the expected dict.

**Built:** the first test, which calls the endpoint and checks the status and body.

**Concepts**
- **`TestClient`:** sends real HTTP-shaped requests to the app **in-process**, with no server, no port and no
  network. That's fast and deterministic.
- **pytest discovery:** files `test_*.py`, functions `test_*`. A plain `assert` is enough; pytest rewrites it to
  show both sides when it fails.
- **Check status and body:** a 200 with the wrong body is still a bug.

**Questions**
- Is this a unit test or an integration test?

**Model answers**
- It's an in-process **integration** test of the HTTP layer: routing, serialization and status code are all real,
  but nothing leaves the process. It's not end-to-end, because no real server or network is involved.

---

## 2026-10-26: M0.5, CI and branch protection (#5, #6)
**Goal:** every change is tested automatically, and `main` can only change through a reviewed, green PR.

### Block 1: `.github/workflows/ci.yml`, triggers and safety settings
```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```
**What it is, line by line**
- `on:`: the list of events that start this workflow.
- `pull_request: branches: [main]`: run when a PR **targeting** `main` is opened or gets new commits.
- `push: branches: [main]`: run when commits land on `main` (here, when a PR is merged).
- `permissions: contents: read`: the automatic token every step gets may only read the repository, never write.
- `concurrency: group: ${{ github.workflow }}-${{ github.ref }}`: runs with the same group name share one "lane".
  `github.workflow` is `CI`; `github.ref` is the branch, so the group is something like `CI-refs/pull/12/merge`.
- `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`: an expression that is `true` for PR runs and
  `false` for pushes. True means "a new run in this lane cancels the older one still running".

**Built:** when CI runs, what its token may do, and what happens to older runs of the same branch.

**Concepts**
- **Two triggers:** `pull_request` tests a proposed change; `push` to `main` tests what actually landed.
- **`permissions: contents: read`:** least privilege for the `GITHUB_TOKEN` every step receives.
- **`concurrency`:** one group per workflow and branch. A new push to a PR cancels the older, now pointless run.
  Runs on `main` are **never** cancelled, so every commit on `main` gets a result.

**Questions**
- Why trigger CI on both `pull_request` and `push` to `main`?
- What does `permissions: contents: read` protect against?
- Why cancel old PR runs but not old `main` runs?

**Model answers**
- *Both triggers?* The PR run tests the branch merged with `main` *at that moment*. After the squash merge, `main`
  is a new commit, and other PRs may have merged in between, so the push run tests what really landed. It also
  keeps `main`'s caches current, and caches saved on the default branch are shared with PR branches.
- *`contents: read`?* If a dependency or third-party action is compromised, the token it steals can only read. It
  can't push code, change workflows or create releases. This is least privilege, like an IAM role scoped to one
  bucket.
- *Cancel rules?* An old PR run tests a commit nobody will merge, so it only wastes minutes. Every `main` commit is
  a potential release, so I want a pass/fail for each one; cancelling would leave holes in the history.

### Block 2: `.github/workflows/ci.yml`, the job
```yaml
jobs:
  test:
    name: test
    runs-on: ubuntu-26.04
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - run: pytest -v
```
**What it is, line by line**
- `jobs: test:`: the workflow has one job, with the id `test`.
- `name: test`: the name shown on the PR. Branch protection requires a check with exactly this name.
- `runs-on: ubuntu-26.04`: GitHub starts a fresh Ubuntu 26.04 virtual machine for this job.
- `timeout-minutes: 10`: kill the job if it runs longer than 10 minutes.
- `uses: actions/checkout@v7`: a ready-made action that clones the repository into the machine.
- `uses: actions/setup-python@v7` with `python-version: "3.12"`: installs Python 3.12.
  `cache: pip` saves pip's downloads between runs, keyed by `requirements.txt`.
- `run: pip install -r requirements.txt`: a shell command; installs the pinned packages.
- `run: pytest -v`: runs the tests, `-v` lists each test by name. If any test fails, pytest exits with a non-zero
  code, the step fails, and the check turns red.

**Built:** one job named `test`: check out, install Python 3.12 with a pip cache, install pinned deps, run pytest.

**Concepts**
- **`runs-on: ubuntu-26.04`, not `ubuntu-latest`:** pin the runner too. `latest` moves to a new OS without
  warning.
- **`timeout-minutes: 10`:** a hung test is killed after 10 minutes instead of burning the default 6 hours.
- **`cache: pip`:** downloaded packages are cached, keyed by a hash of `requirements.txt`. Change a pin and you
  get a fresh cache.
- **Job `name: test`:** branch protection requires a check by this exact name. Rename it and merging blocks.
- **A check you've seen fail:** I broke a test on purpose and watched CI go red, then reverted.

**Questions**
- Why is a CI check you've never seen fail untrustworthy?
- What happens if someone renames the job?

**Model answers**
- *Never seen fail?* A check that always passes might not run your tests at all: a wrong path, zero tests
  collected, or `|| true`. You only know it guards something after you've seen it go red for the right reason.
- *Renamed job?* The ruleset waits for a check called `test` that never reports, so every PR is stuck as "pending".
  The required check name and the job name are a contract.

### Block 3: the `protect-main` ruleset (GitHub settings, not code)
| Rule | Effect |
|---|---|
| Pull request required | nobody pushes to `main` directly |
| Required check `test` | a red or missing CI result blocks the merge |
| No bypass | applies to me too, the admin |
| Block force-push and deletion | `main`'s history can't be rewritten or erased |

**Concepts**
- **Policy as configuration:** the process is enforced by the platform, not by discipline.
- **Squash merge:** each PR becomes one commit on `main`, so `main` reads as a list of features and one
  `git revert` undoes a whole feature.

**Questions**
- Why no bypass, even for the repo owner?

**Model answers**
- The owner's token is the most valuable one to steal, and "just this once" is how untested code reaches
  production. If an emergency fix is needed, it goes through a PR like everything else; the CI run takes under a
  minute.

---

## 2026-10-27: M1, Job state machine (#7)
**Goal:** a `Job` that can only move between statuses along legal paths, enforced in one place.

### Block 1: `JobStatus`
```python
class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
```
**What it is, line by line**
- `class JobStatus(Enum):`: a new type whose possible values are fixed. It inherits from `Enum`
  (`from enum import Enum` at the top of the file).
- `PENDING = "pending"`: one member. `PENDING` is the **name** you use in code (`JobStatus.PENDING`);
  `"pending"` is the **value**, used when the status is sent as JSON or stored.
- The five lines together are the complete list. `JobStatus("pending")` turns a string back into a member, and
  `JobStatus("bogus")` raises an error.

**Built:** the five statuses a job can have.

**Concepts**
- **Enum:** a fixed set of named values. `JobStatus.RUNING` (a typo) fails immediately with `AttributeError`;
  the string `"runing"` would silently never match.
- **Member vs value:** code compares members (`JobStatus.PENDING`); the API sends the value (`"pending"`).
- **Pending, running, succeeded, failed, cancelled** is the same lifecycle as a Kubernetes Pod phase or a CI run.

**Questions**
- Why an Enum instead of plain strings?

**Model answers**
- Typos fail loudly at the line where they happen, the full list of states lives in one place, and editors and type
  checkers know the valid options. The string values exist only at the edges (JSON, database).

### Block 2: `InvalidTransition`
```python
class InvalidTransition(ValueError):
    def __init__(self, start: JobStatus, target: JobStatus):
        self.start = start
        self.target = target
        super().__init__(f"cannot move from {start.value} to {target.value}")
```
**What it is, line by line**
- `class InvalidTransition(ValueError):`: a new exception type that **is a** `ValueError`, so code catching
  `ValueError` would catch it too.
- `def __init__(self, start, target):`: runs when you write `InvalidTransition(JobStatus.PENDING, JobStatus.FAILED)`.
- `self.start = start` / `self.target = target`: saves both statuses on the error object, so code can read
  `error.start` later.
- `super().__init__(f"cannot move from {start.value} to {target.value}")`: calls the parent `ValueError` with the
  message, for example `cannot move from pending to failed`. `str(error)` now returns that text.

**Built:** the error raised for an illegal move, carrying both statuses and a readable message.

**Concepts**
- **Custom exception:** callers can catch *this* failure specifically (`except InvalidTransition`), and the HTTP
  layer maps it to 409.
- **Subclass of `ValueError`:** "the argument has the right type but a bad value", which is what an illegal target
  is.
- **Attributes (`start`, `target`):** code can read them; the message is for humans and logs.
- **`super().__init__(message)`:** passes the message to the base exception, so `str(error)` returns it.

**Questions**
- Why store `start` and `target` as attributes when they're already in the message?

**Model answers**
- Parsing a message string is fragile. Attributes let code (a handler, a metric label, a test) use the values
  directly, and the message can be reworded without breaking anything.

### Block 3: `ALLOWED_TRANSITIONS`
```python
ALLOWED_TRANSITIONS = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.SUCCEEDED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}
```
**What it is, line by line**
- `ALLOWED_TRANSITIONS = { ... }`: a dict, defined once at module level (not inside a class).
- Each **key** is a status; each **value** is a set of the statuses it may move to next.
- `JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED}`: a pending job can start or be cancelled.
- `JobStatus.RUNNING: {SUCCEEDED, FAILED, CANCELLED}`: a running job can finish either way, or be cancelled.
- `JobStatus.SUCCEEDED: set()` (and FAILED, CANCELLED): an empty set, so no move is allowed. These are the
  terminal states. Note `set()`, not `{}`: `{}` would be an empty **dict**.

**Built:** the whole state machine as one table: for each status, where it may go next.

**Concepts**
- **State machine as data:** one table instead of if/else chains spread around the code. Adding a status means
  adding one row.
- **Sets:** `target in allowed` is an O(1) lookup, and duplicates are impossible.
- **Terminal states map to `set()`:** "no moves allowed" needs no special-case code.
- **Retries stay inside `running`** (decision record 0002): a retry doesn't leave `running`, so the table stays
  small.

**Questions**
- A worker reports success just after a user cancels. What stops `cancelled → succeeded`?

**Model answers**
- `cancelled` maps to an empty set, so `transition_to(SUCCEEDED)` raises `InvalidTransition` and the job keeps
  `cancelled`. That only works if the worker **reloads** the job and sees `cancelled`; a stale copy is the M6
  problem (see the module questions below).

### Block 4: the `Job` dataclass
```python
@dataclass
class Job:
    id: uuid.UUID = field(default_factory=uuid.uuid4)      # M2
    status: JobStatus = JobStatus.PENDING
    idempotency_key: str | None = None                     # M5

    @property
    def is_terminal(self) -> bool:
        return not ALLOWED_TRANSITIONS[self.status]

    def transition_to(self, target: JobStatus) -> None:
        allowed = ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise InvalidTransition(self.status, target)
        self.status = target
```
**What it is, line by line**
- `@dataclass`: generates the boring methods for you: `__init__` (so `Job(status=...)` works), `__repr__`
  (readable printing) and `__eq__` (two jobs with the same fields are `==`).
- `id: uuid.UUID = field(default_factory=uuid.uuid4)`: a fresh random id for every new job (explained in M2).
- `status: JobStatus = JobStatus.PENDING`: new jobs start pending unless you pass another status.
- `idempotency_key: str | None = None`: either a string or nothing; nothing by default (M5).
- `@property` + `def is_terminal(self) -> bool:`: read it as `job.is_terminal`, without `()`.
- `return not ALLOWED_TRANSITIONS[self.status]`: looks up this job's allowed moves. An empty set counts as
  "false", so `not` turns it into `True` (terminal); a non-empty set gives `False`.
- `def transition_to(self, target):`: the only way the status should change.
- `allowed = ALLOWED_TRANSITIONS[self.status]`: the set of legal next statuses from where the job is now.
- `if target not in allowed: raise InvalidTransition(self.status, target)`: illegal → stop here with an error.
  The next line never runs, so the status stays as it was.
- `self.status = target`: only reached if the move is legal.

**Built:** the job itself. It starts `pending`, knows if it's finished, and changes status only through
`transition_to`.

**Concepts**
- **`@dataclass`:** generates `__init__`, `__repr__` and `__eq__` from the fields, so `Job(status=...)` and
  `job_a == job_b` just work.
- **`is_terminal` is derived, not stored:** it's computed from the table, so it can never disagree with it.
  `not set()` is `True`, so an empty set means terminal.
- **`@property`:** read like an attribute (`job.is_terminal`), no `()`.
- **Check before change:** validate first, assign last. A rejected move leaves the job exactly as it was.

**Questions**
- Why is `is_terminal` a property and not a stored field?
- Why must the check come before `self.status = target`?

**Model answers**
- *Property?* A stored flag can drift: someone updates `status` and forgets the flag. A property is computed from
  the single source of truth, the table, every time.
- *Check first?* If the assignment happened first and then raised, the job would be left in an illegal state.
  Validate, then mutate: either the whole change happens or none of it does.

### Block 5: `tests/test_job.py`, parametrized tests
```python
@pytest.mark.parametrize("start, target", [
    (JobStatus.PENDING, JobStatus.SUCCEEDED),
    (JobStatus.RUNNING, JobStatus.PENDING),
    (JobStatus.CANCELLED, JobStatus.SUCCEEDED),
    # ...
])
def test_illegal_moves_are_rejected(start, target):
    job = Job(status=start)
    with pytest.raises(InvalidTransition):
        job.transition_to(target)
    assert job.status == start
```
**What it is, line by line**
- `@pytest.mark.parametrize("start, target", [ ... ])`: run the test below once per pair in the list. The two
  names in the string become the function's two parameters.
- `(JobStatus.PENDING, JobStatus.SUCCEEDED)`: one case: start at pending, try to jump straight to succeeded.
- `def test_illegal_moves_are_rejected(start, target):`: pytest fills `start` and `target` from the current pair.
- `job = Job(status=start)`: a job that begins in the start status.
- `with pytest.raises(InvalidTransition):`: "the code inside this block must raise `InvalidTransition`". If it
  doesn't raise, the test fails.
- `job.transition_to(target)`: the illegal move we expect to be refused.
- `assert job.status == start`: after the refused move, the status is still the original one.

**Built:** one test function that checks many illegal moves, and that each one leaves the status unchanged.

**Concepts**
- **`parametrize`:** one function, many cases. Each case is reported separately
  (`test_illegal_moves_are_rejected[JobStatus.RUNNING-JobStatus.PENDING]`), so you see exactly which one failed.
- **`pytest.raises`:** the test passes only if that exception is raised inside the `with` block.
- **The assert after the `with`:** proves "check before change".
- **TDD:** red (the test fails for the right reason), green (minimum code), refactor (only under green tests).

**Questions**
- Why read the error *type* of a red test, not just the count of failures?

**Model answers**
- A test can fail for the wrong reason, like an `ImportError` or a typo, and then go green for the wrong reason
  too. Red should fail because the *feature is missing* (for example `AttributeError: no transition_to`). Then
  green proves the new code is what fixed it.

**Module interview questions**
- *Why is the state machine "necessary but not enough"?*
  The worker loaded the job while it was `running`. In its **stale copy**, `running → succeeded` is legal, so the
  check passes, and saving that copy would overwrite the cancel (a lost update). The fix in M6 is **optimistic
  concurrency**: a `version` column and `UPDATE … WHERE id = ? AND version = ?`. If 0 rows change, someone else
  wrote first: reload and decide again. The state machine checks if a move is *legal*; the version check proves
  it's based on *current* data.

---

## 2026-10-28: M2, IDs and the repository port (#8)
**Goal:** every job has a unique id, and the code depends on an interface for storage, not on a database.

### Block 1: the `id` field
```python
id: uuid.UUID = field(default_factory=uuid.uuid4)
```
**What it is, line by line**
- `id`: the field name. (This is the one legitimate `id` in the code: the attribute `job.id`.)
- `: uuid.UUID`: a type hint: this field holds a UUID object.
- `field(...)`: from `dataclasses`; lets you configure a field beyond a simple default.
- `default_factory=uuid.uuid4`: "to get a default, **call** `uuid.uuid4`". Note there's no `()` after `uuid4`:
  we pass the function itself, and the dataclass calls it once per new `Job`.

**Built:** each new `Job` gets its own random UUID.

**Concepts**
- **UUIDv4:** 128 bits, 122 of them random, written as 32 hex digits. Unique without asking anyone (no
  coordination), so any process can create ids.
- **`default_factory` vs `default`:** `default=uuid.uuid4()` would be called **once**, when the class is defined,
  and every job would share the same id. `default_factory=uuid.uuid4` passes the function, which is called for each
  new job. It's the classic shared-default bug (same as `def f(items=[])`).

**Questions**
- What goes wrong with `id: uuid.UUID = uuid.uuid4()`?
- UUIDv4 vs auto-increment IDs: trade-offs?

**Model answers**
- *`= uuid.uuid4()`?* It runs once at import time, so every job gets the same id, and the repository dict keeps
  overwriting one entry. `test_each_job_gets_a_unique_id` exists to catch exactly this.
- *Trade-offs:*

| | UUIDv4 | Auto-increment |
|---|---|---|
| Generated | in the app, no DB round trip, unique across nodes | by the DB, one sequence |
| Guessable | no (no `/jobs/1`, `/jobs/2` enumeration) | yes; also leaks volume |
| Size | 16 bytes | 4–8 bytes |
| Index | random → scattered B-tree inserts | ordered, compact |

  **UUIDv7** keeps the benefits and adds time ordering, which fixes the index problem. It's an open M6 decision.

### Block 2: `app/ports/job_repository.py`, the port
```python
class JobRepository(Protocol):
    def add(self, job: Job) -> None: ...
    def get(self, job_id: uuid.UUID) -> Job | None: ...
    def update(self, job: Job) -> None: ...                                  # M3
    def get_by_idempotency_key(self, idempotency_key: str) -> Job | None: ... # M5
```
**What it is, line by line**
- `class JobRepository(Protocol):`: declares an interface. `Protocol` comes from `typing`.
- `def add(self, job: Job) -> None: ...`: any repository must have an `add` that takes a job and returns nothing.
  The `...` means "no body here"; this is a signature only.
- `def get(self, job_id: uuid.UUID) -> Job | None: ...`: takes an id; returns the job, or `None` if it doesn't exist.
- `def update(self, job: Job) -> None: ...`: saves changes to a job that already exists (added in M3).
- `def get_by_idempotency_key(self, idempotency_key: str) -> Job | None: ...`: find a job by its key (added in M5).
- Nobody inherits from this class. `InMemoryJobRepository` just has methods with the same names and shapes, and
  that's enough to fit.

**Built:** a description of what the service needs from storage, with no implementation.

**Concepts**
- **Hexagonal architecture (ports and adapters):** the core (service and domain) defines a **port**; outside code
  provides **adapters** that plug into it. It's the same idea as kubelet → CRI → containerd: kubelet doesn't care
  which runtime is behind the interface.
- **`Protocol` (structural typing):** an adapter doesn't inherit from it. Any class with matching methods fits. This
  is checked by a type checker like mypy, **not at runtime** (we don't run mypy in CI yet; that's a gap).
- **`...`:** "no body here". It's a signature only.
- **`get` returns `Job | None`:** the repository reports facts. Whether "missing" is an error is decided above it.

**Questions**
- Why should the service never import a concrete database adapter?

**Model answers**
- The service depends on the **port**, and `main.py` picks the adapter: dependency inversion. Unit tests run in
  milliseconds against the in-memory adapter with no database. Swapping in Postgres (M6) means writing one new
  adapter, while the service and its tests stay the same.

### Block 3: `InMemoryJobRepository`, the first adapter
```python
class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, Job] = {}

    def add(self, job: Job) -> None:
        self._jobs[job.id] = replace(job)

    def get(self, job_id: uuid.UUID) -> Job | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return replace(job)
```
**What it is, line by line**
- `class InMemoryJobRepository:`: note there's no `(JobRepository)`: it fits the port by shape, not by inheritance.
- `def __init__(self) -> None:`: runs once when you create it with `InMemoryJobRepository()`.
- `self._jobs: dict[uuid.UUID, Job] = {}`: an empty dict that maps an id to a job. This dict **is** the storage.
- `def add(self, job)`: `self._jobs[job.id] = replace(job)` stores a copy of the job under its id.
- `def get(self, job_id)`: `job = self._jobs.get(job_id)` looks the id up; `.get` returns `None` when the key is
  missing instead of raising an error.
- `if job is None: return None`: not found → say so with `None`.
- `return replace(job)`: found → return a **copy**, so the caller can't change the stored job by accident.

**Built:** storage in a dict keyed by job id. (The `replace(...)` copies arrived in M3; see there.)

**Concepts**
- **Adapter:** a real implementation of the port. Later, `PostgresJobRepository` has the same methods.
- **`_jobs` (leading underscore):** "private by convention"; only this class touches it.
- **`dict.get(key)`** returns `None` instead of raising `KeyError`, matching the port's contract.
- **Limit:** it lives in one process's memory. Restart → all jobs gone. Two replicas → two separate stores. That's
  why Kubernetes waits until Postgres exists.

**Questions**
- What breaks if you run this app with 2 replicas behind a load balancer?

**Model answers**
- Each replica has its own dict. `POST /jobs` lands on replica A, then `GET /jobs/{id}` lands on B and returns 404.
  Idempotency breaks too: the same key on two replicas creates two jobs. State must live outside the process
  (Postgres) before you scale out.

---

## 2026-10-29 → 31: M3, Job service (#9)
**Goal:** one place for the use cases (submit, get, cancel), independent of HTTP and of the database.

### Block 1: `JobNotFound`
```python
class JobNotFound(LookupError):
    def __init__(self, job_id: uuid.UUID):
        self.job_id = job_id
        super().__init__(f"job {job_id} not found")
```
**What it is, line by line**
- `class JobNotFound(LookupError):`: a new exception that **is a** `LookupError`, Python's family for "not found".
- `def __init__(self, job_id: uuid.UUID):`: runs on `JobNotFound(job_id)`.
- `self.job_id = job_id`: keeps the missing id on the error, for code that needs it.
- `super().__init__(f"job {job_id} not found")`: the message the API sends back, for example
  `job 3f2a… not found`.

**Built:** the error for an id that doesn't exist.

**Concepts**
- **`LookupError`** is the built-in base for "key or index not found" (`KeyError` and `IndexError` subclass it).
- **It lives in the service, not the domain:** "not found" is about a use case looking something up, not about
  what a job is.

**Questions**
- Where should "not found → error" be decided, and why there?

**Model answers**
- **In the service.** The repository reports facts (`None`). Whether "missing" is an error depends on the use case.
  For `cancel`, it is (`JobNotFound`). For the M5 idempotency lookup, missing is normal and means "create a new job".
  HTTP then maps `JobNotFound` to 404 in one exception handler.

### Block 2: `JobService.__init__`, dependency injection
```python
class JobService:
    def __init__(self, repo: JobRepository) -> None:
        self._repo = repo
```
**What it is, line by line**
- `class JobService:`: the class holding the use cases.
- `def __init__(self, repo: JobRepository) -> None:`: whoever creates the service must hand it a repository.
  The type hint names the **port**, not a concrete class.
- `self._repo = repo`: keeps it, so `submit`, `get` and `cancel` can use `self._repo` later.

**Built:** the service receives its repository instead of creating one.

**Concepts**
- **Dependency injection:** whoever creates the service decides which repository it gets. Tests pass
  `InMemoryJobRepository()`; production passes Postgres.
- **The type hint is the port** (`JobRepository`), not a concrete class.

**Questions**
- What would be wrong with `self._repo = InMemoryJobRepository()` inside `__init__`?

**Model answers**
- The service would be welded to one storage. You couldn't use Postgres without editing the service, and tests
  couldn't pass in a repository they prepared (for example one already holding a cancelled job).

### Block 3: `get` and `cancel`
```python
def get(self, job_id: uuid.UUID) -> Job:
    job = self._repo.get(job_id)
    if job is None:
        raise JobNotFound(job_id)
    return job

def cancel(self, job_id: uuid.UUID) -> Job:
    job = self.get(job_id)
    job.transition_to(JobStatus.CANCELLED)
    self._repo.update(job)
    return job
```
**What it is, line by line**
- `def get(self, job_id) -> Job:`: always returns a real `Job`, never `None`.
- `job = self._repo.get(job_id)`: asks storage; may get `None`.
- `if job is None: raise JobNotFound(job_id)`: turns "nothing found" into an error the caller can't ignore.
- `return job`: found.
- `def cancel(self, job_id) -> Job:`
- `job = self.get(job_id)`: reuses `get`, so a missing id raises `JobNotFound` here too.
- `job.transition_to(JobStatus.CANCELLED)`: the domain checks the move; an illegal one raises and stops here.
- `self._repo.update(job)`: saves the changed job. Without this line, the change exists only in our copy.
- `return job`: hands the cancelled job back to the caller (the route).

**Built:** `get` turns `None` into `JobNotFound`; `cancel` loads, changes, **saves** and returns the job.

**Concepts**
- **Reuse `get` inside `cancel`:** the not-found rule is written once.
- **Load → change → save:** the domain decides if the change is legal (`transition_to`); the repository persists it.
- **The order matters:** if `transition_to` raises, `update` never runs, so nothing invalid is saved.

**Questions**
- What happens, step by step, when you cancel a job that's already cancelled?

**Model answers**
- `get` finds it → `transition_to(CANCELLED)` checks the table: `cancelled` allows nothing → raises
  `InvalidTransition` → `update` is never called → the error bubbles up to HTTP and becomes 409.

### Block 4: the adapter stores **copies** (`update` and `replace`)
```python
def add(self, job: Job) -> None:
    self._jobs[job.id] = replace(job)

def update(self, job: Job) -> None:
    self._jobs[job.id] = replace(job)
```
**What it is, line by line**
- `replace(job)`: comes from `from dataclasses import replace`. It builds a **new** `Job` with the same fields,
  a copy.
- `self._jobs[job.id] = replace(job)` in `add`: what's stored is a copy, so changing the caller's `job` later
  doesn't touch storage.
- `update` does the same: overwrite the stored entry with a copy of the changed job.
- Together with `get` returning a copy, this makes the fake behave like a database: you only change what's stored
  by calling `add` or `update`.

**Built:** `update` in the port and adapter, and the adapter now saves and returns copies.

**Concepts**
- **The bug a test passed for the wrong reason:** before copies, the dict held *the same object* the service was
  changing. `transition_to` changed the stored job directly, so "cancel is saved" passed even without `update`. A
  real database returns copies, so production would have lost every cancel.
- **`dataclasses.replace(job)`** creates a new `Job` with the same fields: a copy.
- **Fakes must behave like the real thing**, or they hide bugs.
- **Fix forward:** the mistake was already pushed, so it was fixed with a new commit, not by rewriting history.

**Questions**
- How can a fake/in-memory dependency hide a real bug? How do you prevent it?

**Model answers**
- My fake stored the same object the service changed, so a cancel "saved" itself without `update()`. Prevention:
  make the fake follow the real contract (store and return copies). Run **one shared contract test suite** against
  both the fake and the real adapter (M6). Keep a few integration tests against a real Postgres.

---

## 2026-11-02 → 06: M4, HTTP API (#10)
**Goal:** expose the service over HTTP with correct status codes, keeping HTTP details out of the service.

### Block 1: the composition root
```python
app = FastAPI(...)

job_service = JobService(InMemoryJobRepository())
```
**What it is, line by line**
- `app = FastAPI(...)`: the application (from M0).
- `job_service = JobService(InMemoryJobRepository())`: two steps on one line, read inside-out:
  `InMemoryJobRepository()` creates an empty repository; `JobService(...)` creates the service and hands it that
  repository.
- This line runs **once**, when Python first imports `app.main`. Every request later uses this same
  `job_service`.

**Built:** one service with one repository, created once when the app starts.

**Concepts**
- **Composition root:** the single place that picks concrete classes and wires them together. Only `main.py` knows
  "in-memory"; in M6 this one line changes to Postgres.
- **Created once, at import time:** every request shares the same service and store. A repository created per
  request would start empty every time.
- **`InMemoryJobRepository()` with `()`:** an instance, not the class.

**Questions**
- Why is creating the repository inside a route function a bug?

**Model answers**
- Each request would get a brand-new empty dict: `POST` stores a job, and the next `GET` gets a different, empty
  repository and returns 404. State must outlive the request.

### Block 2: `JobResponse`
```python
class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
```
**What it is, line by line**
- `class JobResponse(BaseModel):`: a Pydantic model, so FastAPI knows how to validate it and turn it into JSON.
- `id: uuid.UUID`: the job's id. In JSON it becomes a string like `"3f2a…"`.
- `status: str`: the status as text, like `"pending"`.
- Two fields only: this is everything a client sees about a job.

**Built:** the public JSON shape of a job.

**Concepts**
- **Response model separate from the domain:** the API contract stays stable when `Job` changes. For example, M5
  added `idempotency_key` to `Job` without exposing it to clients.
- **Pydantic `BaseModel`:** validates the data and turns it into JSON (a UUID becomes a string).
- **`status=job.status.value`:** the enum member becomes the string `"pending"`.

**Questions**
- Why not just return the `Job` dataclass?

**Model answers**
- Every internal field would become public API, and renaming one would break clients. A response model is an
  explicit contract: you choose what leaves the service.

### Block 3: the routes
```python
@app.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID) -> JobResponse:
    job = job_service.get(job_id)
    return JobResponse(id=job.id, status=job.status.value)

@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: uuid.UUID) -> JobResponse:
    job = job_service.cancel(job_id)
    return JobResponse(id=job.id, status=job.status.value)
```
**What it is, line by line**
- `@app.get("/jobs/{job_id}")`: handles `GET /jobs/<something>`. The `{job_id}` part is captured from the path.
- `def get_job(job_id: uuid.UUID) -> JobResponse:`: the parameter name must match `{job_id}`. The hint
  `uuid.UUID` makes FastAPI convert the text to a UUID, or return 422 if it isn't one. `-> JobResponse` tells
  FastAPI the shape of the reply.
- `job = job_service.get(job_id)`: may raise `JobNotFound` (handled in Block 4).
- `return JobResponse(id=job.id, status=job.status.value)`: builds the reply. `.value` turns
  `JobStatus.PENDING` into `"pending"`.
- `@app.post("/jobs/{job_id}/cancel")`: handles `POST /jobs/<id>/cancel`.
- `job = job_service.cancel(job_id)`: may raise `JobNotFound` (404) or `InvalidTransition` (409).
- The return line is the same as in `get_job`: same response shape.

**Built:** read one job and cancel one job. (`POST /jobs` is shown in M5, where it changed.)

**Concepts**
- **Path parameter:** `{job_id}` in the path must match the function parameter `job_id` exactly; a mismatch gives
  422.
- **Type hint `uuid.UUID`:** FastAPI validates it. `/jobs/not-a-uuid` → **422** before my code runs.
- **Thin routes:** call the service, return a response. No business logic, no try/except.
- **`POST …/cancel` instead of `DELETE`:** cancelling changes the job's state; the job still exists and can be read.

**Questions**
- 404 vs 409 vs 422: when is each one returned?

**Model answers**
- **422:** the request is malformed (not a UUID); FastAPI rejects it. **404:** well-formed, but no such job.
  **409:** the job exists, but the action conflicts with its current state (cancelling a finished job).

### Block 4: exception handlers
```python
@app.exception_handler(JobNotFound)
async def job_not_found(request: Request, error: JobNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})

@app.exception_handler(InvalidTransition)
async def invalid_transition(request: Request, error: InvalidTransition) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(error)})
```
**What it is, line by line**
- `@app.exception_handler(JobNotFound)`: "if any route lets a `JobNotFound` escape, call the function below
  instead of returning a 500".
- `async def job_not_found(request: Request, error: JobNotFound) -> JSONResponse:`: FastAPI passes the request and
  the exception object. It's `async` because Starlette's handlers are; it does no waiting.
- `return JSONResponse(status_code=404, content={"detail": str(error)})`: the reply: status 404, body
  `{"detail": "job … not found"}`.
- The second handler is the same pattern: `InvalidTransition` → 409 with the "cannot move from … to …" message.

**Built:** domain errors become HTTP responses in one place.

**Concepts**
- **One mapping:** whenever `JobNotFound` escapes any route, FastAPI calls this handler.
- **`{"detail": ...}`:** the same shape FastAPI uses for its own errors, so clients parse one format.
- **`str(error)`:** the message built in the exception's `__init__`.

**Questions**
- Why map errors in one exception handler instead of try/except in every route?

**Model answers**
- **One place:** every route returns the same error shape, and a new route can't forget the mapping.
  **Thin routes:** each route only calls the service. **Clean layers:** the domain raises domain errors, and only
  the HTTP layer knows about 404 and 409.

### Block 5: `tests/test_jobs_api.py`
```python
def test_cancel_already_cancelled_job_returns_409():
    created = client.post("/jobs").json()
    client.post(f"/jobs/{created['id']}/cancel")
    response = client.post(f"/jobs/{created['id']}/cancel")
    assert response.status_code == 409
```
**What it is, line by line**
- `created = client.post("/jobs").json()`: create a fresh job for this test and keep its JSON
  (`{"id": ..., "status": "pending"}`).
- `client.post(f"/jobs/{created['id']}/cancel")`: first cancel; should succeed. The f-string puts the id into
  the URL.
- `response = client.post(f"/jobs/{created['id']}/cancel")`: second cancel of the same job.
- `assert response.status_code == 409`: the second cancel must be refused as a conflict.

**Built:** API tests for every status code: 201, 200, 404, 409, 422.

**Concepts**
- **Test through the public interface:** these tests only use HTTP, so the internals can be refactored freely.
- **The refactor caught by tests:** a copy-paste put `submit()` inside GET; the tests went red immediately.
- **Shared state:** all API tests share one app and one in-memory store. They pass because each test creates its
  own job. A test relying on "the store is empty" would be order-dependent.

**Questions**
- Why 201 now and 202 later (once a worker runs jobs)?

**Model answers**
- **201 Created:** the resource exists and the request is complete. **202 Accepted:** "I've taken your request; the
  work happens later." Once a worker processes jobs from a queue, POST only enqueues, so 202 tells the client to
  poll `GET /jobs/{job_id}`. It's usually sent with a `Location` header.

---

## 2026-11-23 → 24: M5, idempotency keys (PR #11)
**Goal:** a client can safely retry `POST /jobs`: the same `Idempotency-Key` never creates a second job.

### Block 1: the key on `Job`
```python
idempotency_key: str | None = None
```
**What it is, line by line**
- `idempotency_key`: a new field on `Job`.
- `: str | None`: it holds either a string (the key the client sent) or `None` (no key).
- `= None`: the default, so `Job()` still works without a key, exactly like before M5.

**Built:** a job remembers which key created it, if any.

**Concepts**
- **Idempotency:** doing it twice has the same effect as doing it once. `GET`, `PUT` and `DELETE` are idempotent by
  definition; `POST` is not, so a retry after a timeout can create a duplicate.
- **The client creates the key** (usually a UUID): only the client knows "this is the same request again".
- **`str | None = None`:** optional, so existing code (`Job()`) still works.

**Questions**
- Why can't the server generate the idempotency key?

**Model answers**
- The server can't tell a retry from a genuinely new request: both look like `POST /jobs`. Only the client knows its
  own intent, so it sends the same key on every retry of one operation.

### Block 2: the repository index
```python
self._idempotency_keys: dict[str, uuid.UUID] = {}

def add(self, job: Job) -> None:
    self._jobs[job.id] = replace(job)
    if job.idempotency_key is not None:
        self._idempotency_keys[job.idempotency_key] = job.id

def get_by_idempotency_key(self, idempotency_key: str) -> Job | None:
    job_id = self._idempotency_keys.get(idempotency_key)
    if job_id is None:
        return None
    return self.get(job_id)
```
**What it is, line by line**
- `self._idempotency_keys: dict[str, uuid.UUID] = {}`: a second dict, created in `__init__`, mapping a key to a
  job **id** (not to the job itself).
- In `add`: after storing the job, `if job.idempotency_key is not None:` only jobs that have a key are indexed.
- `self._idempotency_keys[job.idempotency_key] = job.id`: remember "this key → this job's id".
- `def get_by_idempotency_key(self, idempotency_key)`:
- `job_id = self._idempotency_keys.get(idempotency_key)`: look the key up; `None` if never seen.
- `if job_id is None: return None`: unknown key.
- `return self.get(job_id)`: known key → fetch the job by id, through the normal `get`, which returns a copy.

**Built:** a second dict `key → job id`, and a lookup by key.

**Concepts**
- **Index as a pointer:** store `key → id`, not a second copy of the job. One source of truth, so the two can't
  disagree.
- **O(1) lookup** instead of looping over every job. This is what a database index does.
- **Reuse `get`:** the lookup returns a copy, like every other read.

**Questions**
- Why a second dict instead of looping over all jobs?

**Model answers**
- Looping is O(n): it gets slower with every job. A dict is O(1). It also mirrors M6, where a unique index on
  `idempotency_key` makes the same lookup fast in Postgres.

### Block 3: `submit` returns `(job, created)`
```python
def submit(self, idempotency_key: str | None = None) -> tuple[Job, bool]:
    if idempotency_key is not None:
        existing = self._repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, False
    job = Job(idempotency_key=idempotency_key)
    self._repo.add(job)
    return job, True
```
**What it is, line by line**
- `def submit(self, idempotency_key: str | None = None) -> tuple[Job, bool]:`: the key is optional; the method
  returns two things: the job, and whether it was newly created.
- `if idempotency_key is not None:`: only look up when a key was sent.
- `existing = self._repo.get_by_idempotency_key(idempotency_key)`: has this key been used before?
- `if existing is not None: return existing, False`: yes → hand back the old job, `False` = "not created now".
- `job = Job(idempotency_key=idempotency_key)`: no key, or a new key → make a new job (the key may be `None`).
- `self._repo.add(job)`: store it (this also indexes the key, Block 2).
- `return job, True`: `True` = "created now".

**Built:** a known key returns the existing job with `False`; otherwise a new job is created and returned with
`True`.

**Concepts**
- **Changing a contract safely:** first a refactor (return `(job, True)` everywhere, all callers updated, tests
  green), then the new behaviour. Two small steps instead of one risky one.
- **Tuple unpacking:** `job, created = service.submit(...)`; `job, _ = ...` when you don't need the flag.
- **Check-then-insert race:** the lookup and the `add` are two separate steps; see Q3 below.

### Block 4: the `Idempotency-Key` header and 201/200
```python
@app.post("/jobs", status_code=201)
def submit_job(
    response: Response,
    idempotency_key: str | None = Header(default=None),
) -> JobResponse:
    job, created = job_service.submit(idempotency_key=idempotency_key)
    if not created:
        response.status_code = 200
    return JobResponse(id=job.id, status=job.status.value)
```
**What it is, line by line**
- `@app.post("/jobs", status_code=201)`: handles `POST /jobs`; the default status for success is 201.
- `response: Response,`: FastAPI hands the route the outgoing response object, so the code can change its status.
- `idempotency_key: str | None = Header(default=None),`: "read this value from the request **headers**, not the
  URL or body". FastAPI looks for the header `idempotency-key` (it swaps `_` for `-`; case doesn't matter).
  Missing header → `None`.
- `job, created = job_service.submit(idempotency_key=idempotency_key)`: unpack the two returned values.
- `if not created: response.status_code = 200`: a replay → change 201 to 200.
- `return JobResponse(...)`: the same body either way.

**Built:** the route reads the header, defaults to 201, and switches to 200 on a replay.

**Concepts**
- **`Header(default=None)`:** FastAPI reads the parameter from an HTTP header. It converts the name: `idempotency_key`
  → header `idempotency-key` (headers are case-insensitive, so `Idempotency-Key` matches).
- **`response: Response`:** FastAPI injects the outgoing response, so the route can change its status code
  depending on the result.
- **Same body on replay:** the client gets exactly what the first call returned; only the status differs.

### Block 5: the tests
```python
def test_repeated_idempotency_key_returns_the_same_job_with_200():
    headers = {"Idempotency-Key": "retry-abc-123"}
    first = client.post("/jobs", headers=headers)
    second = client.post("/jobs", headers=headers)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
```
**What it is, line by line**
- `headers = {"Idempotency-Key": "retry-abc-123"}`: the header a retrying client would send.
- `first = client.post("/jobs", headers=headers)`: the original request.
- `second = client.post("/jobs", headers=headers)`: the retry, with the same key.
- `assert first.status_code == 201`: the first one created a job.
- `assert second.status_code == 200`: the retry did not create one.
- `assert second.json() == first.json()`: and it got back exactly the same job (same id, same status).

**Built:** tests at all three layers (repository, service, API) for same key, different keys and no key.

**Concepts**
- **Each layer tests its own contract:** the repository finds by key; the service returns `created`; the API
  returns 201/200.

**Module questions and model answers** (Q1 also answers "walk through a duplicate POST"; Q3 answers "safe under
concurrency")

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

<!-- Add the next module here, block by block: code, Built, Concepts, Questions, Model answers. -->
