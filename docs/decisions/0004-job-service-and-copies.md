# 0004: Job service, dependency injection and copy semantics

**Status:** Accepted · **Date:** 2026-10-31 · **Milestone:** M3

## Context
The use cases (submit, get, cancel) need one home that knows neither HTTP nor the database. A test of "cancel is
saved" passed even though the code never called `update`, because the in-memory dict held the very object the
service was changing. A real database never behaves like that.

## Decision
- **`JobService`** holds the use cases and receives a `JobRepository` in its constructor (**dependency
  injection**). Only the composition root (`main.py`) picks the concrete adapter.
- **`JobNotFound`** lives in the service: the repository returns `None`, and the service decides that a missing
  job is an error for `get` and `cancel`.
- **`update`** is added to the port; changes are persisted only through `add` and `update`.
- **The in-memory adapter stores and returns copies** (`dataclasses.replace`), so it behaves like a database.
- **Cancel = load → `transition_to` → `update` → return.** An illegal move raises before anything is saved.

## Alternatives considered
- **Service creates its own repository:** simpler, but welds it to one storage and makes tests unable to prepare
  state.
- **Keep the shared-object fake:** fewer lines, but it hides missing `update` calls, which is the bug we hit.
- **Return `None` from `service.get`:** pushes the "is missing an error?" decision into every caller.

## Consequences
- Tests can hand the service a prepared repository (for example, one holding a cancelled job).
- The fake is now trustworthy enough that M6 can run **one shared contract test suite** against both adapters.
- `add` vs `update` semantics need a precise definition in Postgres (insert vs update; what if the id exists?).
