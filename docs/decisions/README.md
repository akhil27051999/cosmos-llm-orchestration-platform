# Architecture decision records

One file per significant decision: the context, what we chose, what we rejected and the consequences.
A record is never rewritten when a decision changes; a new record **supersedes** it, and the old one's status
says so. Every module PR adds or updates a record here.

| # | Decision | Milestone | Status |
|---|---|---|---|
| [0001](0001-fastapi-and-layout.md) | FastAPI app and project layout | M0 | Accepted |
| [0002](0002-state-machine-and-repository-port.md) | Job state machine and repository port | M1, M2 | Accepted |
| [0003](0003-ci-and-branch-protection.md) | CI on every change and a protected `main` | M0.5 | Accepted |
| [0004](0004-job-service-and-copies.md) | Job service, dependency injection and copy semantics | M3 | Accepted |
| [0005](0005-http-api.md) | HTTP API shape and error mapping | M4 | Accepted |
| [0006](0006-idempotency-keys.md) | Idempotency keys on `POST /jobs` | M5 | Accepted |
| [0007](0007-sre-focused-roadmap.md) | An SRE-focused roadmap | all | Accepted, amended by 0008 |
| [0008](0008-roadmap-skill-gaps.md) | Close the roadmap's skill gaps | all | Accepted |

**Template:** `# NNNN: Title` · `**Status:** Proposed/Accepted/Superseded by NNNN · **Date:** · **Milestone:**`,
then `## Context`, `## Decision`, `## Alternatives considered`, `## Consequences`.
