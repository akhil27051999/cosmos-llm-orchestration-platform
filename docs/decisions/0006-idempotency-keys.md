# 0006: Idempotency keys on `POST /jobs`

**Status:** Accepted · **Date:** 2026-11-24 · **Milestone:** M5

## Context
Clients retry `POST /jobs` after timeouts and network errors. `POST` isn't idempotent, so each retry would create
another job, and for LLM workloads that means paying for the same work twice.

## Decision
- **Optional `Idempotency-Key` request header.** No key → a new job every time (backward compatible).
- **First request with a key → 201** and a new job; **repeat → 200** and the **same** job, same body.
- **The key is stored on `Job`** (`idempotency_key: str | None = None`); the repository finds a job by key through
  an index `key → id` (one source of truth, O(1)).
- **`submit()` returns `(job, created)`:** the service reports a fact; the HTTP layer turns it into 201/200.
  Introduced as a refactor first (`(job, True)` everywhere), then the behaviour.
- **A second cancel stays 409:** cancel is a state change, not a create; replaying it is a conflict.

## Alternatives considered
- **Required key:** strongest guarantee, but breaks every existing client with 422.
- **Server-side dedup by request body:** the server can't tell a retry from a genuinely new identical request.
- **Return just `job` and compare timestamps in the route:** fragile and leaks service logic into HTTP.
- **409 on replay:** tells a well-behaved retrying client it did something wrong.

## Consequences
- Retries with a key are safe in the single-request case.
- **Known limitation (check-then-insert race):** two same-key requests at the same instant can both see "no job
  yet" and both create one. M6 fixes it with a **unique index** on `idempotency_key` and by catching the
  unique-violation error to return the winner as a replay (200).
- Keys never expire yet; real systems keep them for a window (for example 24 h). Revisit with Postgres.
- The same body is replayed, but a replay with a *different* request body isn't detected (no request fingerprint).
