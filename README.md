# Cosmos

[![CI](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/actions/workflows/ci.yml)

An asynchronous job-orchestration platform for LLM workloads, built from scratch, one stage at a time, as a hands-on learning project.

> **Current state:** scaffold with CI. The API serves a health check; the Job state machine is the next milestone.

## Why I'm building this

I've spent five years as a DevOps/SRE engineer running other people's distributed systems in production; this project is how I learn to *build* one. Cosmos covers the patterns behind real backend platforms (async job processing, queues and workers, idempotency, concurrency control, resilient LLM calls) and I'm writing every part by hand, one tested milestone at a time, so I understand the trade-offs behind each design decision, not just the end result.

## Status

- [x] **M0** — FastAPI app, `/health` endpoint, pytest setup
- [x] **M0.5** — CI on every PR, pinned dependencies, protected `main`
- [ ] **M1** — Job entity and state machine (pure Python)
- [ ] **M2–M3** — Repository interface, in-memory store, job service
- [ ] **M4–M5** — Jobs API (`POST /jobs`, `GET /jobs/{id}`, cancel), idempotency keys
- [ ] **M6** — PostgreSQL persistence with optimistic concurrency
- [ ] **Stage 1** — Redis queue and background worker
- [ ] **Stage 3** — LLM agent loop with tool use and token budget

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

## How changes land

Every change goes through a pull request. GitHub Actions runs the test suite on
each PR and again on `main` after merge, and a branch ruleset blocks direct
pushes and force-pushes to `main` and requires the `test` check to pass before
anything merges.

## Project layout

```
app/
  main.py               FastAPI application and routes
tests/
  test_health.py        API tests (run in-process, no server needed)
docs/
  decisions/            architecture decision records
.github/
  workflows/ci.yml      CI: runs pytest on PRs and pushes to main
pytest.ini              pytest config (adds project root to the import path)
requirements.txt        pinned Python dependencies
```

## Design decisions

Recorded in [`docs/decisions/`](docs/decisions/):

- [0001 — FastAPI app and project layout](docs/decisions/0001-fastapi-and-layout.md)