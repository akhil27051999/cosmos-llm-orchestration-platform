# 0002: Job state machine and repository port

**Status:** Accepted · **Date:** 2026-10-29 · **Milestones:** M1, M2

## Context
Jobs move through a lifecycle, and the platform must never allow impossible
states (a cancelled job that later "succeeds"). Jobs also need to be stored
and found again, first in memory, later in PostgreSQL, without rewriting the
business code when storage changes.

## Decision
- **State machine as data:** `ALLOWED_TRANSITIONS` maps each status to the set
  of statuses it may move to. Terminal statuses map to an empty set.
  `transition_to()` checks the table *before* changing anything and raises
  `InvalidTransition` otherwise.
- **Retries stay inside `running`:** only the final outcome becomes `failed`.
- **Each `Job` creates its own UUID** at construction.
- **Ports and adapters:** the service will depend on the `JobRepository`
  protocol, never on a concrete store. `InMemoryJobRepository` implements it
  now; a PostgreSQL adapter will implement it in M6.
- **`get()` returns `None` for an unknown id.** The repository reports facts;
  the service decides whether "missing" is an error (→ 404 in the API).

## Alternatives considered
- **if/else chains for the rules:** harder to read and change than one table.
- **Retries as states** (`failed → pending`): more visibility per attempt but
  needs two failure states; can be revisited if needed.
- **Database-generated integer ids:** only known after saving, and they leak
  how many jobs exist.
- **Raising from `get()`:** forces callers that expect "not found" (e.g.
  idempotency checks in M5) to use exceptions for normal control flow.

## Consequences
- Business rules are testable with no database — 24 tests run in under a second.
- Swapping storage means writing one new adapter; the service and API don't change.
- Known limitation: the transition check uses the in-memory copy of a job.
  A stale copy could overwrite a concurrent cancel — fixed in M6 with
  optimistic concurrency (a `version` column).