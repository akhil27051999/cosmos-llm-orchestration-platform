# Cosmos

[![CI](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/actions/workflows/ci.yml)

An asynchronous job-orchestration platform for LLM workloads, built from scratch, one stage at a time, as a hands-on learning project.

> **Current state:** a working HTTP API with idempotency keys (submit, get and cancel jobs; domain errors mapped to 404/409; a repeated `Idempotency-Key` replays the first job), on a tested domain and service layer. **Now: M6**, starting with the async refactor (M6a). Where every stage stands is in [Status](#status).

## Why I'm building this

I have five years in tech and I'm early in my SRE career. Cosmos is where I build a production-style system end to end and then **operate it the way an SRE would**: ship it with GitOps, set SLOs, alert on burn rate, write runbooks, load-test it and break it on purpose. The application side covers the patterns real platforms depend on (async job processing, queues and workers, idempotency, concurrency control, resilient calls to a flaky LLM API). I build it module by module with an AI pair-programmer: Claude drafts the code and tests; I review every change, explain it back, and own every design decision, each one test-first and recorded in `docs/decisions/`. The goal is to understand the trade-offs behind each decision, not just the end result. What I learned each day is in [`docs/learning-log.md`](docs/learning-log.md).

## Status

**Where I am:** 7 of 18 stages done (+1 optional) (M0–M5, 52 tests). **Now: M6a.** **103 build hours left** (≈ 6 weeks at
20 h/week), target finish **mid-January 2027**. Roadmap decisions: [0007](docs/decisions/0007-sre-focused-roadmap.md),
amended by [0008](docs/decisions/0008-roadmap-skill-gaps.md).

**Done: the application core**
- [x] **M0** — FastAPI app, `/health` endpoint, pytest setup
- [x] **M0.5** — CI on every PR, pinned dependencies, protected `main`
- [x] **M1** — Job entity and state machine (pure Python)
- [x] **M2** — Job ids, repository port, in-memory adapter
- [x] **M3** — Job service (submit, get, cancel)
- [x] **M4** — Jobs API: `POST /jobs`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/cancel`
- [x] **M5** — Idempotency keys on `POST /jobs`

**Part A: the system to operate**
- [ ] **M6** — PostgreSQL, async SQLAlchemy, Alembic migrations, Docker Compose, optimistic concurrency &nbsp;⬅ **we are here**
  - [ ] **M6a** — async refactor of repository, service and routes (no database yet) ⬅ *in progress*
  - [ ] **M6b** — Postgres adapter, async SQLAlchemy, Alembic, Docker Compose, shared contract tests
  - [ ] **M6c** — optimistic concurrency (`version`) and a unique index on `idempotency_key` (race → replay `200`)
- [ ] **Stage 1** — Redis queue and worker: `202 Accepted`, at-least-once, retries, dead-letter queue

**Part B: ship it**
- [ ] **S1 Containers** — multi-stage, non-root, multi-arch (arm64 + amd64) images; Trivy scan, SBOM and cosign signing in CI; *graceful SIGTERM shutdown in the worker (PID 1, signals)*
- [ ] **S2 Kubernetes** — Helm chart, probes, resources, PDB, `securityContext`, Pod Security Admission, NetworkPolicy; HPA for the API, KEDA on queue depth
- [ ] **S3 GitOps** — ArgoCD with dev/prod *as Kustomize overlays over the Helm chart*, Argo Rollouts canary, secrets kept out of Git

**Part C: operate it**
- [ ] **S4 Observability** — RED metrics, JSON logs with request ids, OpenTelemetry traces, dashboards; *trace one request end to end with `tcpdump` (DNS → Service → pod)*
- [ ] **S5 SLOs** — two SLOs, multi-window burn-rate alerts, one runbook per alert
- [ ] **S6 Reliability** — k6 load test and capacity notes; chaos (kill a worker, the DB, Redis); a postmortem; *Linux drills (OOMKill, disk full, file-descriptor exhaustion); `cosmosctl`, a Python ops CLI (find stuck jobs via the Kubernetes API, drain the dead-letter queue, parse logs, cost report)*

**Part D: the LLM dependency and the cloud**
- [ ] **S7 LLM calls** — timeouts, retries with jitter, circuit breaker, rate limits, token and cost budget
- [ ] **S8 Terraform on AWS** — *EKS*, VPC, IAM roles for service accounts, ALB controller, ECR, S3 backups, Route 53; remote state, plan on every PR; apply, demo, destroy

**Part E: prove it at scale**
- [ ] **S9 Design doc** — *"Cosmos at 100×": sharding, multi-region, queue choice, cost*
- [ ] **S10 Ansible** *(optional)* — *install k3s on two Multipass VMs with Ansible (systemd, Linux setup)*

*Italics* = added on 2026-11-25 to close skill gaps ([0008](docs/decisions/0008-roadmap-skill-gaps.md)).

### Timeline

**Budget: 103 hours, fixed.** When a stage runs over, scope is cut (list below), not the deadline. The 103 h
are build time only; reviewing finished modules and interview practice (3–5 h/week) come on top.

| Week of | Stages | Est. hours |
|---|---|---|
| 2026-11-30 | M6 (M6a → M6b → M6c) | 14 |
| 2026-12-07 | Stage 1, S1 | 16 |
| 2026-12-14 | S2, S3 | 19 |
| 2026-12-21 | S4, S5 | 16 |
| 2026-12-28 | S6 (holiday week: `cosmosctl` kept to two commands) | 15 |
| 2027-01-04 | S7, S8 (cloud, one or two days, destroyed the same day) | 19 |
| 2027-01-11 | S9 | 4 |
| | **Total** | **103** |

**Cut list**, applied in this order if a week overruns: (1) S10 is already outside the budget; (2) S9 becomes a
one-page design note; (3) `cosmosctl` shrinks to one command; (4) the `tcpdump` trace is dropped; (5) multi-arch
images become amd64 only. Every cut is recorded here, so the gap is honest, not hidden.

## Tech stack

Python 3.12 · FastAPI · Uvicorn · pytest · GitHub Actions

## Run it locally

Requires Python 3.12.

```bash
git clone https://github.com/akhil27051999/cosmos-llm-orchestration-platform.git
cd cosmos-llm-orchestration-platform
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests:

```bash
pytest -v
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Then open:

- [http://localhost:8000/health](http://localhost:8000/health) — health check
- [http://localhost:8000/docs](http://localhost:8000/docs) — interactive API docs

## Try the API

With the server running:

```bash
# submit a job → 201, returns {"id": "...", "status": "pending"}
curl -s -X POST http://localhost:8000/jobs

# look it up (paste the id from above) → 200, or 404 if unknown
curl -s http://localhost:8000/jobs/<job-id>

# cancel it → 200; cancelling again → 409 Conflict
curl -s -X POST http://localhost:8000/jobs/<job-id>/cancel
```

Or use the interactive docs at http://localhost:8000/docs.

## How changes land

Every change goes through a pull request. GitHub Actions runs the test suite on
each PR and again on `main` after merge, and a branch ruleset blocks direct
pushes and force-pushes to `main` and requires the `test` check to pass before
anything merges.

## Project layout

```
app/
  main.py                        FastAPI routes, response model, error → HTTP status mapping
  domain/
    job.py                       Job entity, JobStatus, state machine rules
  ports/
    job_repository.py            JobRepository interface (what storage must do)
  adapters/
    memory_job_repository.py     in-memory JobRepository; stores copies, like a real database
  services/
    job_service.py               JobService: submit, get, cancel; JobNotFound
tests/
  test_health.py                 health endpoint
  test_job.py                    state machine rules: allowed, illegal, terminal
  test_memory_job_repository.py  repository add/get/update and copy behaviour
  test_job_service.py            service use cases: submit, get, cancel
  test_jobs_api.py               HTTP API: status codes, bodies, 404/409/422
docs/
  decisions/                     architecture decision records
  learning-log.md                what I learned in each module
.github/
  workflows/ci.yml               CI: runs pytest on PRs and pushes to main
pytest.ini                       pytest config (adds project root to the import path)
requirements.txt                 pinned Python dependencies
```

## Design decisions

Recorded in [`docs/decisions/`](docs/decisions/):

- [0001 — FastAPI app and project layout](docs/decisions/0001-fastapi-and-layout.md)
- [0002 — Job state machine and repository port](docs/decisions/0002-state-machine-and-repository-port.md)
- [0003 — CI on every change and a protected `main`](docs/decisions/0003-ci-and-branch-protection.md)
- [0004 — Job service, dependency injection and copy semantics](docs/decisions/0004-job-service-and-copies.md)
- [0005 — HTTP API shape and error mapping](docs/decisions/0005-http-api.md)
- [0006 — Idempotency keys on `POST /jobs`](docs/decisions/0006-idempotency-keys.md)
- [0007 — An SRE-focused roadmap](docs/decisions/0007-sre-focused-roadmap.md)
- [0008 — Close the roadmap's skill gaps](docs/decisions/0008-roadmap-skill-gaps.md)

