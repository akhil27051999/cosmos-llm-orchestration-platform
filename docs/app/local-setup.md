# Module 1: Local Application Setup

> **Goal:** Get the Flask Student Management REST API running locally — Python venv, dependencies, PostgreSQL, migrations, seeding, and verification.

> **Why this matters:** Every DevOps/SRE workflow starts with reproducing the dev environment. If you can't run it locally, you can't containerize it, deploy it, or debug it.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Prerequisites](#prerequisites)
5. [Setup Walkthrough](#setup-walkthrough)
6. [API Endpoints](#api-endpoints)
7. [Commands Reference](#commands-reference)
8. [Troubleshooting](#troubleshooting)
9. [Interview Q&A](#interview-qa)
10. [STAR Stories](#star-stories)
11. [Production Hardening](#production-hardening)

---

## Project Overview

A REST API that manages student records (CRUD operations on a `Student` model with fields: `id`, `name`, `domain`, `email`, `gpa`). Used as the foundation for all downstream DevOps work — containerization, orchestration, observability, GitOps.

**Why Flask?** Lightweight, easy to instrument, ideal for demonstrating end-to-end DevOps workflows without the noise of large frameworks.

---

## Architecture

```
   ┌─────────────┐      ┌────────────────┐      ┌──────────────┐
   │   Client    │─────►│  Flask App     │─────►│  PostgreSQL  │
   │ (curl/HTTP) │ HTTP │ (Gunicorn:5000)│ SQLA │   :5432      │
   └─────────────┘      └────────────────┘      └──────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │ Alembic      │
                        │ migrations   │
                        └──────────────┘
```

- **Flask** serves HTTP routes
- **Flask-SQLAlchemy** is the ORM
- **Flask-Migrate (Alembic)** manages DB schema migrations
- **Gunicorn** is the WSGI server (production-grade, replaces `flask run` for prod)
- **PostgreSQL** is the persistence layer

---

## Tech Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Language | Python 3.10+ | Application runtime |
| Framework | Flask 3.1 | HTTP framework |
| ORM | Flask-SQLAlchemy 3.1 | Database abstraction |
| Migrations | Flask-Migrate (Alembic) 4.1 | Schema versioning |
| WSGI Server | Gunicorn 23 | Production HTTP server |
| Database | PostgreSQL 15 | Persistence |
| Driver | psycopg2-binary | Postgres Python driver |
| Testing | pytest 8.4 + pytest-flask | Unit + integration tests |
| Config | python-dotenv | Loads `.env` files |

---

## Prerequisites

| Tool | Why | Install (macOS) |
|------|-----|-----------------|
| Python 3.10+ | App runtime | `brew install python` |
| PostgreSQL 15 | DB | `brew install postgresql@15 && brew services start postgresql@15` |
| Git | Source control | `brew install git` |

---

## Setup Walkthrough

### 1. Clone & enter the repo

```bash
git clone https://github.com/akhil27051999/cosmos-llm-orchestration-platform.git
cd cosmos-llm-orchestration-platform
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

> **Why a venv?** Python dependencies are global by default. A venv isolates them per project so version conflicts (e.g., Flask 2 vs Flask 3) don't affect other apps.

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r app/requirements.txt
```

### 4. Create the database

```bash
psql postgres -c "CREATE DATABASE studentdb;"
psql postgres -c "CREATE USER postgres WITH PASSWORD 'postgres123';" 2>/dev/null || true
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE studentdb TO postgres;"
```

### 5. Configure environment variables

Create a `.env` file at the project root:

```bash
# Flask
FLASK_ENV=development
FLASK_APP=app/wsgi.py
FLASK_DEBUG=1
PYTHONUNBUFFERED=1

# Postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=studentdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/studentdb
```

> **Why a `.env` file?** Externalizes config from code (12-factor app). Same code runs in dev/staging/prod — only env vars change.

### 6. Run migrations (create tables)

```bash
flask db upgrade
```

> **What's a migration?** A versioned SQL change script. `db upgrade` runs all pending migrations to bring the DB schema up to date. Reproducible across environments.

### 7. Seed sample data

```bash
python app/seed.py
```

Inserts 100 student records with random domains and GPAs.

### 8. Run the app

```bash
flask run
```

Server starts at `http://127.0.0.1:5000`.

### 9. Verify

```bash
curl http://127.0.0.1:5000/students/3
# → {"id":3,"name":"Student 3","domain":"...","email":"...","gpa":...}
```

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Welcome message |
| GET | `/health` | Liveness check (used by K8s probes) |
| GET | `/students` | List all students |
| GET | `/students/<id>` | Get one student |
| POST | `/students` | Create a student |
| PUT | `/students/<id>` | Update a student |
| DELETE | `/students/<id>` | Delete a student |
| GET | `/metrics` | Prometheus metrics (added later) |

---

## Commands Reference

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Activate venv | `source venv/bin/activate` | Isolates Python dependencies |
| 2 | Install dependencies | `pip install -r app/requirements.txt` | Locks exact versions across environments |
| 3 | Create migration | `flask db migrate -m "msg"` | Generates a new migration script from model changes |
| 4 | Apply migrations | `flask db upgrade` | Brings DB schema to latest version |
| 5 | Roll back migration | `flask db downgrade` | Reverts the last migration (use with care) |
| 6 | Seed DB | `python app/seed.py` | Loads sample data for dev |
| 7 | Run dev server | `flask run` | Built-in dev server (auto-reload) |
| 8 | Run prod server | `gunicorn --bind 0.0.0.0:5000 --workers=2 app.wsgi:app` | Production WSGI server |
| 9 | Run tests | `pytest -v tests/unit` | Unit tests only |
| 10 | Deactivate venv | `deactivate` | Exits the virtual environment |

---

## Troubleshooting

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | `zsh: command not found: flask` after `source venv/bin/activate` | Project moved to a new path; venv binary shebangs point to the old absolute path | Recreate the venv: `rm -rf venv && python3 -m venv venv && pip install -r app/requirements.txt` |
| 2 | `psycopg2.OperationalError: connection refused` | Postgres not running, or wrong host/port | `brew services start postgresql@15`; verify `POSTGRES_HOST=localhost` in `.env` |
| 3 | `relation "student" does not exist` | Migrations not applied | `flask db upgrade` |
| 4 | `Address already in use: 5000` on macOS | macOS AirPlay Receiver uses port 5000 | Disable AirPlay Receiver in System Settings, or run on a different port: `flask run -p 5001` |
| 5 | `ModuleNotFoundError: No module named 'app'` | Running script from wrong directory or PYTHONPATH not set | Run from project root with `PYTHONPATH=.` or use module form: `python -m app.seed` |
| 6 | `Error: Path doesn't exist: migrations` | Working directory mismatch | Run from project root, or specify explicitly: `flask db upgrade --directory app/migrations` |
| 7 | App responds but DB queries fail | Stale `.env` not reloaded | Restart `flask run` after editing `.env` |
| 8 | `pip install` fails on `psycopg2-binary` | Missing PostgreSQL dev headers | `brew install postgresql@15` first |

---

## Interview Q&A

| Q | A |
|---|---|
| **Why use a virtual environment?** | Isolates project-specific Python dependencies. Without it, installing Flask 3 globally could break another project requiring Flask 2. Industry standard since `venv` shipped with Python 3.3. |
| **What's the difference between `flask run` and `gunicorn`?** | `flask run` is a single-threaded **dev server** with auto-reload. `gunicorn` is a **production WSGI server** — multi-process, multi-worker, handles concurrent requests properly. Never use `flask run` in production. |
| **What is WSGI?** | Web Server Gateway Interface — the spec for how Python web apps talk to web servers. Flask is a WSGI app; Gunicorn is a WSGI server. ASGI is the async equivalent (used by FastAPI). |
| **How do migrations work?** | Alembic compares your SQLAlchemy models to the DB schema and generates Python scripts to bring them in sync. Each script has `upgrade()` and `downgrade()` functions. The `alembic_version` table tracks which migrations have been applied. |
| **Why externalize config to `.env`?** | 12-factor app principle. Same code runs in dev/staging/prod — only env vars change. Secrets (passwords, API keys) never get committed. |
| **How would you handle DB connection pooling?** | SQLAlchemy has built-in pooling (`QueuePool` by default). Configure via `SQLALCHEMY_ENGINE_OPTIONS = {'pool_size': 10, 'max_overflow': 20}`. For high-scale, use PgBouncer in front. |
| **What's `python-dotenv` doing?** | Loads `.env` file values into `os.environ` at app startup. Without it, you'd `export` each var manually before running. |
| **How do you secure secrets in `.env`?** | Never commit `.env` (add to `.gitignore`). For prod, use Vault / AWS Secrets Manager / SSM Parameter Store and inject via env vars at runtime. |
| **What does `app/wsgi.py` do?** | Entry point for Gunicorn — exports a callable `app` object. Gunicorn imports it and serves it. Decoupling lets you swap servers (gunicorn, uwsgi, mod_wsgi) without changing app code. |
| **Why pin exact dependency versions in requirements.txt?** | Reproducibility. `Flask>=3.0` could pull 3.0.1 today and 3.5.0 next month with breaking changes. `Flask==3.1.1` guarantees the same behavior everywhere. Use `pip-tools` or `poetry` for lock files in larger projects. |
| **How do you debug a Python app in production?** | Structured logging (JSON), correlation IDs, distributed tracing (OpenTelemetry), error tracking (Sentry). Never `print()` — use `logger.info()`. |
| **What's the difference between SQLAlchemy Core and ORM?** | Core = SQL expression language (close to raw SQL). ORM = object-relational mapper (Python classes ↔ tables). We use ORM for most work, Core for performance-critical or complex queries. |

---

## STAR Stories

### Story 1: "Tell me about a time you had to debug a hard environment issue."

**Situation:** After moving the Flask project from `~/Desktop` to `~/Documents`, the venv stopped working — `source venv/bin/activate` ran successfully but `flask` command was not found.

**Task:** Get the dev environment back online without disrupting other team members' setups.

**Action:**
1. Confirmed `flask` binary existed in `venv/bin/` (so packages were installed).
2. Inspected `venv/bin/flask` shebang — it pointed to the old absolute path: `#!/Users/x/Desktop/Flask-REST-API/venv/bin/python3`.
3. Realized Python's venv writes hardcoded absolute paths into the shebangs of installed CLI tools.
4. Solution: deleted and recreated the venv, then re-installed dependencies.
5. Documented this in the README so the next team member doesn't hit it.

**Result:** Dev environment back up in 5 minutes. Added a note in setup docs: "Don't move the project folder; if you do, recreate the venv."

**Takeaway:** Python venvs are not portable across paths. For portability, use Docker (which we did in Module 2) or `pyenv-virtualenv` with relative paths.

---

### Story 2: "Tell me about a time you couldn't connect to a port."

**Situation:** Couldn't bind Flask to port 5000 on a fresh macOS install.

**Task:** Identify the port conflict and resolve it.

**Action:**
1. Ran `lsof -i :5000` — found `ControlCenter` (macOS AirPlay Receiver) holding the port.
2. Two options: disable AirPlay Receiver in System Settings, or use a different port.
3. Chose port `5001` for the dev workflow (less disruption); for the Docker/K8s setup later, used port-mapping `-p 8080:5000` to bypass the host conflict.

**Result:** Documented "macOS AirPlay = port 5000 conflict" in our team wiki.

**Takeaway:** OS-level processes can occupy "open" ports. Always check with `lsof -i :<port>` when binding fails.

---

## Production Hardening

| Area | Local | Production |
|------|-------|-----------|
| **WSGI server** | `flask run` (single-threaded) | Gunicorn with `--workers=(2*CPU+1)`, `--worker-class=gevent` for I/O-bound workloads |
| **Database** | Local Postgres | Managed RDS / Cloud SQL with Multi-AZ, automated backups, read replicas |
| **DB pooling** | Default SQLAlchemy pool | PgBouncer in front of Postgres for connection multiplexing |
| **Secrets** | `.env` file | Vault / AWS Secrets Manager / Kubernetes Secrets, injected at runtime |
| **Migrations** | Manual `flask db upgrade` | Init container or pre-deploy hook in CD pipeline |
| **Logging** | stdout, plaintext | JSON-structured, shipped to Loki/CloudWatch/Splunk |
| **Error tracking** | Stack traces in console | Sentry / Rollbar with alerts |
| **Health checks** | `/health` returns 200 | `/health/live` (liveness) + `/health/ready` (DB connectivity check) |
| **Metrics** | None | `/metrics` Prometheus endpoint (added in Module 7) |
| **Config validation** | Crashes on bad config at first request | Validate config on startup, fail fast |
| **TLS** | HTTP | Terminate TLS at ingress / ALB; HSTS headers |

---

## Cloud Mapping

| Local Component | AWS Equivalent | Why |
|-----------------|---------------|-----|
| Local Python | Lambda (event-driven), ECS/EKS (container), Elastic Beanstalk (managed) | Runtime managed for you |
| Local Postgres | RDS PostgreSQL | Managed backups, Multi-AZ failover, automatic patching |
| `.env` file | SSM Parameter Store (config) + Secrets Manager (passwords) | Secure, versioned, IAM-controlled |
| Gunicorn behind nginx | ALB → ECS/EKS pods running Gunicorn | ALB handles TLS, routing, health checks |
| File logs | CloudWatch Logs | Centralized, searchable, alerting |

---

## Reference Links (Internal)

- App entry point: [app/__init__.py](../../app/__init__.py)
- Models: [app/models.py](../../app/models.py)
- Routes: [app/routes.py](../../app/routes.py)
- Config: [app/config.py](../../app/config.py)
- Seed script: [app/seed.py](../../app/seed.py)
- Migrations: [app/migrations/](../../app/migrations/)
- Tests: [tests/unit/](../../tests/unit/)
