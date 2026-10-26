# 0001: FastAPI app and project layout

**Status:** Accepted · **Date:** 2026-10-26 · **Milestone:** M0

## Context

Cosmos needs an HTTP API that clients use to submit and track LLM jobs.
Those jobs call LLMs that can take 10+ seconds, so the API must handle many
slow requests at once. The code also has to be testable without starting a
server or any infrastructure.

## Decision

- **FastAPI** as the web framework, served by **uvicorn** (an ASGI server).
- Project layout: application code in `app/`, tests in `tests/`.
- **pytest** for tests, with `pythonpath = .` in `pytest.ini`.
- Dependencies isolated in a per-project **virtual environment** (`.venv`).



## Why



### 1. ASGI and uvicorn

A web app has two jobs. The **server** (uvicorn) opens the port, accepts
connections, parses raw HTTP into Python objects, and writes the response
back. The **application** (FastAPI + my code) only decides what each request
returns. FastAPI never touches the network itself — running
`python app/main.py` exits silently because nothing listens on a port.

**ASGI** is the standard contract between server and application, so the
server can be swapped without changing app code. It is *asynchronous*: one
process can wait on many slow requests at once, which matters for LLM calls.
The older standard, WSGI (Flask + gunicorn), handles one request per worker
at a time.

### 2. `--reload` — development only

`--reload` makes uvicorn watch the source files and restart the server on
every save. In production it's wrong because:

- code never changes in a running container — a new version is a new image
and a new rollout;
- a restart drops in-flight requests;
- file watching costs CPU and runs a single process;
- process restarts belong to Kubernetes/systemd, driven by health checks.



### 3. The virtual environment

Without a venv, `pip install` writes into one Python shared by every project,
so two projects needing different versions of the same package break each
other. A venv is a folder with its own private packages
(`.venv/lib/python3.12/site-packages`); `activate` only puts `.venv/bin`
first on `PATH`. Same idea as container isolation, but for Python packages
only.

### 4. `ModuleNotFoundError: No module named 'app'`

`import app` searches the folders listed in `sys.path`, in order. pytest
added the test file's folder (`tests/`), not the project root, so `app/` was
not found. `pythonpath = .` in `pytest.ini` adds the root. uvicorn never had
the problem because it adds the current working directory, and I run it
from the project root.

## Alternatives considered

- **Flask** — familiar from my earlier project, but WSGI/synchronous, and it
has no built-in request validation or auto-generated API docs.
- **Django** — full framework with ORM, admin and templates; far more than
an API service needs.



## Consequences

- `/docs` and `/openapi.json` are generated automatically from the code.
- Tests call the app in-process through `TestClient` — no server needed.
- Async code becomes a skill I must learn properly before adding database
and LLM calls.

