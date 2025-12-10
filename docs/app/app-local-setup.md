# Student-REST-API — End-to-End Setup & Run Guide

https://github.com/user-attachments/assets/1f86060a-b82a-4c2c-b263-c99ec93a8954

Overview
--------
This document is an end-to-end, step-by-step guide for setting up, running, testing, and maintaining the Student-REST-API Flask project. It is intentionally written as an implementation guide for newcomers (no code is included here because the repository already contains the source). The guide covers environment preparation, dependency installation, database setup (PostgreSQL), migrations, running in development and production, testing, common troubleshooting, and best-practices for maintenance and contribution.

Who this is for
----------------
- New contributors who cloned the repository and want to run the project locally.
- Developers preparing a local or staging environment.
- DevOps or SRE engineers who want a reference for deployment and troubleshooting.

Prerequisites
-------------
Before you start, make sure the following tools are installed on your machine:
- Python 3.8 or newer
- pip (Python package installer)
- git
- PostgreSQL (server and client tools) — for the production-like local setup
- Optional: Docker / Docker Compose (if you prefer containerized DB and app)

Local environment variables and secrets will be read from a `.env` file. Do not commit `.env` to version control.

Repository layout (what to expect)
----------------------------------
You should see an application package (for example `app/`) with:
- app factory (creates the Flask app)
- config module (reads environment variables)
- models (SQLAlchemy models)
- routes/blueprints (API endpoints)
- migrations/ (Flask-Migrate / Alembic artifacts — may be present)
- requirements.txt
- README.md (this file)
- a .env.example or documentation describing expected .env variables (if present)

Quick start — clone & prepare
-----------------------------
1. Clone the repository:
   $ git clone <repository-url>

2. Move into the project directory:
   $ cd <repository-directory>

3. Create a Python virtual environment (recommended):
   $ python3 -m venv .venv

4. Activate the virtual environment:
   - On macOS / Linux: $ source .venv/bin/activate
   - On Windows (PowerShell): $ .venv\Scripts\Activate

5. Install dependencies:
   $ pip install -r requirements.txt

6. Verify installed packages:
   $ pip list

Environment configuration
-------------------------
The app reads configuration from environment variables. Create a `.env` file in the repository root (do not commit it). The `.env` file should provide values similar to these (replace placeholders with real secrets):

- FLASK_APP — the app factory entry (for example `app:create_app`)
- FLASK_ENV — development or production
- DEBUG — true/false
- DATABASE_URL — full SQLAlchemy-compatible connection string or supply individual POSTGRES_* variables:
  - POSTGRES_USER
  - POSTGRES_PASSWORD
  - POSTGRES_DB
  - POSTGRES_HOST
  - POSTGRES_PORT

Important: If your deployment platform provides a single connection URL (for example Heroku, Railway), prefer setting DATABASE_URL.

PostgreSQL: local DB setup
--------------------------
You have two options: native local installation or Docker.

A) Native PostgreSQL (Ubuntu / macOS Homebrew):
- Install PostgreSQL using your package manager.
- Ensure the service is running and enabled on boot.
- Create a dedicated DB user and database for the app.
- Give the app user the necessary privileges for the application DB.

B) Docker (recommended for isolation):
- Start a Postgres container and map the port; create a database and user via environment variables or a small initialization script.

In both options, note the connection string and set it to DATABASE_URL in `.env`.

Database user and DB example values (replace with strong secrets):
- DB name: studentdb
- DB user: student_user
- DB password: <secure-password>
- Host: localhost (or the Docker container hostname)
- Port: 5432

Migrations (Flask-Migrate / Alembic)
------------------------------------
The project uses Flask-Migrate to manage database schema changes. Basic migration workflow:

1. Ensure FLASK_APP is set to your app factory (for local CLI usage).
2. Initialize migrations directory (only needed once if not already present).
3. Create migration scripts after model changes (a descriptive message helps).
4. Apply migrations to the target DB.

Notes:
- Never delete or reinitialize migrations on production without a careful migration plan (backups, tested rollbacks).
- For adding non-nullable fields to existing tables, add them as nullable first, backfill values, then alter to non-nullable in a subsequent migration or use server defaults in migration scripts.

Running the application
-----------------------
Development:
- Use Flask's development server through the app factory. Ensure you are using the virtual environment and environment variables are set.
- You can enable debug mode via environment variables (only in local development).

Production:
- Use a production WSGI server (e.g., gunicorn) and configure the process supervisor appropriate for your platform (systemd, Docker, Kubernetes).
- Ensure environment variables (secrets) are injected securely (secrets manager, environment variables in your hosting platform).
- Configure logging to a file/system and ensure log rotation is in place for long-running services.

API base path
-------------
By convention the API is mounted under a base prefix like `/api/students` (the exact prefix is present in the repository’s blueprint registration). Use that prefix for your client requests.

Testing the API
---------------
- Unit and integration tests are set up using pytest (if the project includes tests). Run tests with:
  $ pytest

- For manual testing use curl, HTTPie, Postman, or your preferred REST client against the running server. The project includes a Postman collection and/or test examples in the repository.

Common requests to verify (examples of action, not code):
- Health/readiness endpoint to confirm server is running.
- Create a student record (POST).
- List all student records (GET).
- Retrieve a student by ID (GET).
- Update student (PUT/PATCH).
- Delete student (DELETE).

Troubleshooting & common issues
-------------------------------
This section lists common errors encountered during setup and how to resolve them.

1) "Unable to connect to the database" / connection refused
- Cause: PostgreSQL not running, wrong host/port, firewall or Docker container network issues.
- Fixes:
  - Ensure Postgres service is running (or container is up).
  - Verify host and port: if using Docker, check container hostname or map host port to container.
  - Verify credentials and database name in `.env`.
  - Confirm network access (local firewall or Docker network rules).

2) "OperationalError: could not translate host name" or DNS errors
- Cause: Using a hostname not resolvable in your environment (common when Docker container name is used as host outside of Docker network).
- Fixes:
  - Use `localhost` or the container’s mapped port on the host.
  - If using Docker Compose, run the app in the same Compose network or use the service name as host.

3) "ModuleNotFoundError" or import errors on startup
- Cause: Virtual environment not activated, missing dependencies, or incorrect PYTHONPATH.
- Fixes:
  - Activate the virtual environment.
  - Install dependencies from requirements.txt.
  - Check the FLASK_APP or entrypoint configured to ensure it points to the correct app factory.

4) "flask db upgrade" failing or migrations causing errors
- Cause: Migrations out of sync, model changes conflicting with DB schema, or issues with Alembic environment.
- Fixes:
  - Inspect the generated migration script before applying.
  - If migrations diverged in development, either merge migration revisions or, in development only, reinitialize migrations after dumping data or resetting DB.
  - For production, avoid rebuilding migrations from scratch; instead create new migrations that reconcile the schema.

5) Duplicate key / Unique constraint violation on create
- Cause: Attempting to insert a record with a unique field (e.g., email) already existing.
- Fixes:
  - Handle conflict responses gracefully in your client.
  - For testing, use unique data or clean up test records before re-running tests.

6) Timeouts / slow queries in production
- Cause: Missing indexes, large volume of data, improper query patterns, or connection pooling misconfiguration.
- Fixes:
  - Add indexes for frequently queried columns.
  - Use connection pooling (SQLAlchemy supports pooling options).
  - Monitor slow queries and tune as needed or add caching for read-heavy endpoints.

7) Missing or incorrectly set environment variables
- Cause: Not loading `.env` in local environment, or CI/host not configured to provide environment variables.
- Fixes:
  - Add `.env` locally (do not commit).
  - For production, set environment variables in the hosting environment (platform-specific).
  - Confirm the config module reads from the correct variables and has sensible defaults (where appropriate).

8) Permissions errors when running scripts or writing logs
- Cause: File system permissions, log file ownership, or restricted directories.
- Fixes:
  - Ensure the process user has write permission to log and temporary directories.
  - Use configurable log file paths that are writable by the running process.

9) Running tests that depend on DB and failing due to state
- Cause: Tests assume a fresh DB state.
- Fixes:
  - Use a test database configured via environment variables and run migrations before tests.
  - Consider using transactional tests or test fixtures that roll back DB changes after each test.

Operational notes for production deployment
-------------------------------------------
- Use environment-specific configurations (production, staging, development).
- Do not commit secrets; use a secrets manager.
- Enforce TLS/SSL for all external traffic.
- Configure process monitoring/restart (systemd, supervisor, or container orchestration).
- Configure database backups and verify restore procedures periodically.
- Restrict database user privileges (principle of least privilege) and use a different user for admin tasks.
- Run migrations as part of a controlled release process and ensure rolling migrations are safe for production traffic.

Maintenance & dependency updates
-------------------------------
- Frequently update and test dependencies in a development branch before promoting to production.
- After adding new dependencies, update requirements.txt using pip freeze and commit.
- Run the test suite after dependency upgrades and before deploying.

Contribution workflow
---------------------
- Fork the repository and work in a feature branch `feat/<short-description>` or `fix/<ticket-number>`.
- Add tests for any new behavior or to reproduce bugs.
- Keep commits small and focused, and use descriptive commit messages.
- Open a pull request with a clear description of the changes and any migration steps required.

Cheat sheet — essential commands
-------------------------------
Below is a short list of the command-style steps you’ll run while following this guide. Replace placeholders with the repository URL, database credentials, and other environment-specific values.

- Clone repository: git clone <repository-url>
- Create and activate venv: python3 -m venv .venv  then activate (.venv/bin/activate or .venv\Scripts\Activate)
- Install deps: pip install -r requirements.txt
- Set environment variables: create `.env` and populate connection info
- DB migrations: (initialize if needed, create migration scripts, and apply them)
- Start app in development: run the Flask development server via the configured FLASK_APP
- Production run: use gunicorn (or the WSGI server of your choice) and ensure proper environment and logging

Where to get help
-----------------
- Check application logs (console or file) for stack traces and error messages.
- Confirm environment variables and database connectivity first — most setup problems stem from configuration.
- If the repository includes an issues tracker, search for similar problems or open a new issue with detailed reproduction steps and logs.

Appendix — key reminders
------------------------
- Never commit `.env` or secrets to Git.
- Prefer strong, unique passwords for DB users and rotate if exposed.
- Back up the database before applying potentially destructive migrations.
- Test migrations on a staging or local clone of production data (or a sample dataset) when possible.

End of guide
------------
This README is intended to be a living document. If anything in the repository changes (paths, blueprint prefixes, migration usage), update this documentation so new contributors have the clearest onboarding path possible.
