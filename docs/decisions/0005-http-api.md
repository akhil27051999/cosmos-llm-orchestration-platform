# 0005: HTTP API shape and error mapping

**Status:** Accepted · **Date:** 2026-11-06 · **Milestone:** M4

## Context
Clients need to submit, read and cancel jobs over HTTP. Status codes must tell a client what to do next (retry,
fix the request, stop), and HTTP details must not leak into the service or the domain.

## Decision
| Endpoint | Success | Errors |
|---|---|---|
| `POST /jobs` | 201 + job | (200 on idempotent replay, M5) |
| `GET /jobs/{job_id}` | 200 + job | 404 unknown, 422 malformed id |
| `POST /jobs/{job_id}/cancel` | 200 + job | 404 unknown, 409 illegal move, 422 malformed id |

- **`JobResponse`** (Pydantic) is the public shape: `id` and `status` only, separate from the `Job` dataclass.
- **Cancel is `POST …/cancel`, not `DELETE`:** cancelling changes state; the job still exists and can be read.
- **Errors mapped once** with exception handlers: `JobNotFound → 404`, `InvalidTransition → 409`, body
  `{"detail": "..."}` (the same shape FastAPI uses for 422).
- **Thin routes:** call the service, build the response; no business logic, no try/except.
- **One shared `JobService`**, created once in the composition root.

## Alternatives considered
- **Return the dataclass directly:** less code, but every internal field becomes public API.
- **try/except in each route:** works, but repeats the mapping and is easy to forget in a new route.
- **`DELETE /jobs/{id}`:** suggests the resource is gone, which contradicts "cancelled jobs remain visible".
- **400 for an illegal cancel:** 409 is more precise: the request is valid, it conflicts with current state.

## Consequences
- The API contract is explicit and testable through HTTP only (tests cover 201/200/404/409/422).
- When a worker processes jobs (Stage 1), `POST /jobs` becomes **202 Accepted**: a deliberate contract change.
- A second cancel stays 409 (revisited and kept in M5).
