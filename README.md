# Cosmos

[![CI](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/actions/workflows/ci.yml)

An asynchronous job-orchestration platform for LLM workloads, built from scratch, one stage at a time, as a hands-on learning project.

> **Current state:** a working HTTP API — submit, get and cancel jobs over HTTP, with domain errors mapped to 404/409 — on top of a tested domain and service layer. Next: idempotency keys (M5).

## Why I'm building this

I have five years in tech and I'm early in my SRE career. Cosmos is where I build a production-style system end to end and then **operate it the way an SRE would**: ship it with GitOps, set SLOs, alert on burn rate, write runbooks, load-test it and break it on purpose. The application side covers the patterns real platforms depend on (async job processing, queues and workers, idempotency, concurrency control, resilient calls to a flaky LLM API). I build it module by module with an AI pair-programmer: Claude drafts the code and tests; I review every change, explain it back, and own every design decision, each one test-first and recorded in `docs/decisions/`. The goal is to understand the trade-offs behind each decision, not just the end result. What I learned each day is in [`docs/learning-log.md`](docs/learning-log.md).

## Status

- [x] **M0** — FastAPI app, `/health` endpoint, pytest setup
- [x] **M0.5** — CI on every PR, pinned dependencies, protected `main`
- [x] **M1** — Job entity and state machine (pure Python)
- [x] **M2** — Job ids, repository port, in-memory adapter
- [x] **M3** — Job service (submit, get, cancel)
- [x] **M4** — Jobs API: `POST /jobs`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/cancel`
- [x] **M5** — Idempotency keys on `POST /jobs`

**Part A: the system to operate**
- [ ] **M6** — PostgreSQL, async SQLAlchemy, Alembic migrations, Docker Compose, optimistic concurrency
- [ ] **Stage 1** — Redis queue and worker: `202 Accepted`, at-least-once, retries, dead-letter queue

**Part B: ship it**
- [ ] **S1 Containers** — multi-stage, non-root images; Trivy scan, SBOM and cosign signing in CI
- [ ] **S2 Kubernetes** — Helm chart, probes, resources, PDB; HPA for the API, KEDA on queue depth
- [ ] **S3 GitOps** — ArgoCD with dev/prod, Argo Rollouts canary, secrets kept out of Git

**Part C: operate it**
- [ ] **S4 Observability** — RED metrics, JSON logs with request ids, OpenTelemetry traces, dashboards
- [ ] **S5 SLOs** — two SLOs, multi-window burn-rate alerts, one runbook per alert
- [ ] **S6 Reliability** — k6 load test and capacity notes; chaos (kill a worker, the DB, Redis); a postmortem

**Part D: the LLM dependency and the cloud**
- [ ] **S7 LLM calls** — timeouts, retries with jitter, circuit breaker, rate limits, token and cost budget
- [ ] **S8 Terraform** — managed cluster with remote state: apply, demo, destroy

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
.github/
  workflows/ci.yml               CI: runs pytest on PRs and pushes to main
pytest.ini                       pytest config (adds project root to the import path)
requirements.txt                 pinned Python dependencies
```

## Design decisions

Recorded in [`docs/decisions/`](docs/decisions/):

- [0001 — FastAPI app and project layout](docs/decisions/0001-fastapi-and-layout.md)
- [0002 — Job state machine and repository port](docs/decisions/0002-state-machine-and-repository-port.md)

