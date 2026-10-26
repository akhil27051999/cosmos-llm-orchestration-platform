# Cosmos

An asynchronous job-orchestration platform for LLM workloads, built from scratch, one stage at a time, as a hands-on learning project.

> **Current state:** early scaffold. The API serves a health check; job handling is the next milestone.

## Why I'm building this

I've spent five years as a DevOps/SRE engineer running other people's distributed systems in production; this project is how I learn to *build* one. Cosmos covers the patterns behind real backend platforms (async job processing, queues and workers, idempotency, concurrency control, resilient LLM calls) and I'm writing every part by hand, one tested milestone at a time, so I understand the trade-offs behind each design decision, not just the end result.

## Status

- [x] **M0** — FastAPI app, `/health` endpoint, pytest setup
- [ ] **M1** — Job entity and state machine (pure Python)
- [ ] **M2–M3** — Repository interface, in-memory store, job service
- [ ] **M4–M5** — Jobs API (`POST /jobs`, `GET /jobs/{id}`, cancel), idempotency keys
- [ ] **M6** — PostgreSQL persistence with optimistic concurrency
- [ ] **Stage 1** — Redis queue and background worker
- [ ] **Stage 3** — LLM agent loop with tool use and token budget



## Tech stack

Python 3.12 · FastAPI · Uvicorn · pytest

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



## Project layout

```
app/
  main.py          FastAPI application and routes
tests/
  test_health.py   API tests (run in-process, no server needed)
pytest.ini         pytest config (adds project root to the import path)
requirements.txt   Python dependencies
```

