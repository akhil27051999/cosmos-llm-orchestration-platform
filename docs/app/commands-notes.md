# Student-REST-API — Commands Cheat Sheet with Notes

This document lists the exact commands you will run to set up, run, test, and maintain the Student-REST-API project. Each command block is followed by a short note explaining why it is used and what to check after running it. Use these commands in the sequence indicated for a smooth end-to-end workflow.

> Precondition: You already cloned the repository and the project code (Flask app, migrations, requirements.txt, etc.) is present in the repo root.

Table of contents
- Quick clone & environment setup
- Install dependencies
- Freeze dependencies
- Git / version control commands
- Create .gitignore (quick commands)
- Create & populate .env
- PostgreSQL local install (native) — Ubuntu
- PostgreSQL quick setup script (native)
- PostgreSQL via Docker (optional)
- Database verification & common psql commands
- Flask-Migrate commands (migrations)
- Running the app (development & production)
- Running tests
- Common maintenance & dependency commands
- Troubleshooting commands (network, logs, DB)
- Helpful cleanup and migration reset (development only)
- Contribution workflow commands

---

Quick clone & environment setup
```bash
# 1) Clone repository (replace <repo-url> with your repo)
git clone <repository-url>

# 2) Enter repo directory
cd <repository-directory>

# 3) Create Python virtual environment
python3 -m venv .venv

# 4) Activate virtual environment (macOS / Linux)
source .venv/bin/activate

# 4b) Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate
```
Note: Always activate the virtual environment before installing packages or running Python commands so packages are installed into the venv.

Install dependencies
```bash
# Install pinned dependencies from requirements.txt
pip install -r requirements.txt
```
Note: If you don't have requirements.txt or want to install the basic set, use pip install with the package names (Flask, Flask-SQLAlchemy, Flask-Migrate, psycopg2-binary, python-dotenv, pytest, pytest-flask, gunicorn).

Freeze dependencies
```bash
# Update requirements.txt to current venv state
pip freeze > requirements.txt
```
Note: Run this after adding or upgrading packages. Commit the updated `requirements.txt`.

Git / version control commands
```bash
# Initialize a git repo (if not already initialized)
git init

# Add all files to staging area
git add .

# Initial commit
git commit -m "Initial commit: Flask REST API project setup"

# Add remote (replace your-username and repo name)
git remote add origin https://github.com/your-username/student-crud-api.git

# Rename default branch to main
git branch -M main

# Push to remote
git push -u origin main
```
Note: If the remote already exists or you've been provided a remote, skip adding it. Ensure you don't push secrets (e.g., .env) — add .env to .gitignore.

Create .gitignore (quick)
```bash
# Create a basic .gitignore (UNIX-like shells)
cat > .gitignore <<'EOF'
# Virtual environments
.venv/
venv/

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# Environment variables
.env
.env.local

# Database
*.db
*.sqlite3

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Logs
*.log

# Temporary files
tmp/
temp/
EOF
```
Note: Confirm `.env` and any other secrets are listed. Commit `.gitignore` early.

Create & populate .env (example)
```bash
# Create a .env file (edit values to match your environment)
cat > .env <<'EOF'
# Flask env
FLASK_APP=app:create_app
FLASK_ENV=development
DEBUG=True

# PostgreSQL (example)
POSTGRES_USER=student_user
POSTGRES_PASSWORD=student123
POSTGRES_DB=studentdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Full SQLAlchemy URL (optional override)
DATABASE_URL=postgresql://student_user:student123@localhost:5432/studentdb
EOF
```
Note: Do not commit `.env`. Replace credentials with secure values. Some platforms expect DATABASE_URL; keep it in sync with POSTGRES_* vars.

PostgreSQL local install (Ubuntu)
```bash
# Update package lists
sudo apt update

# Install PostgreSQL server and contrib
sudo apt install -y postgresql postgresql-contrib

# Verify status
sudo systemctl status postgresql

# Start and enable on boot
sudo systemctl start postgresql
sudo systemctl enable postgresql
```
Note: For macOS, use Homebrew: `brew install postgresql` and `brew services start postgresql`.

PostgreSQL quick setup script (native)
```bash
# Create a quick script to create user and DB (UNIX)
cat > setup_db.sh <<'EOF'
#!/bin/bash
sudo -u postgres psql -c "CREATE USER student_user WITH PASSWORD 'student123';"
sudo -u postgres psql -c "CREATE DATABASE studentdb;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE studentdb TO student_user;"
EOF

# Make the script executable and run it
chmod +x setup_db.sh
./setup_db.sh
```
Note: Change passwords before using beyond development. Use `sudo -u postgres psql` to run ad-hoc SQL if you prefer.

PostgreSQL via Docker (optional)
```bash
# Run PostgreSQL using Docker
docker run --name student-postgres -e POSTGRES_USER=student_user -e POSTGRES_PASSWORD=student123 -e POSTGRES_DB=studentdb -p 5432:5432 -d postgres:15

# Check container logs
docker logs -f student-postgres
```
Note: If you use Docker Compose, define a service and run `docker-compose up -d`. When using Docker, set POSTGRES_HOST to `localhost` (if you mapped the port) or the service name if running inside Compose network.

Database verification & common psql commands
```bash
# List PostgreSQL users
sudo -u postgres psql -c "\du"

# List PostgreSQL databases
sudo -u postgres psql -c "\l"

# Connect to DB as created user (prompts for password)
psql -U student_user -d studentdb -h localhost -W

# From inside psql: list tables
\dt

# Describe a table structure
\d students

# Query table contents
SELECT * FROM students;

# Exit psql
\q
```
Note: If connecting remotely, ensure firewall and pg_hba.conf allow your client.

Flask-Migrate commands (migrations)
```bash
# Ensure FLASK_APP is set, for example:
export FLASK_APP=app:create_app        # macOS / Linux
# On Windows PowerShell: $env:FLASK_APP='app:create_app'

# Initialize migrations directory (only if migrations/ not present)
flask db init

# Create a new migration after model changes
flask db migrate -m "describe your change"

# Apply migrations to the configured DB
flask db upgrade

# To rollback the last migration
flask db downgrade
```
Note: Inspect the generated migration file in `migrations/versions/` before running `upgrade`. Do not reinitialize migrations on production without planning.

Running the app (development & production)
```bash
# Development: run Flask development server
export FLASK_ENV=development
flask run   # defaults to http://127.0.0.1:5000

# Production: run with gunicorn (example, 4 workers)
gunicorn -w 4 -b 0.0.0.0:8000 'app:create_app()'

# If using systemd, create a unit file and ensure environment is provided to the service
# If using Docker, build an image and run it with appropriate env vars
```
Note: For production, configure logging, monitoring, and run migrations as part of deployment.

Running tests
```bash
# Run pytest (will discover tests)
pytest

# Run a specific test file
pytest tests/test_students.py

# Run with increased verbosity
pytest -v
```
Note: Tests that require DB should point to a test database (set via environment variables) and the DB should be migrated prior to running tests. Consider using fixtures to isolate DB state.

Common maintenance & dependency commands
```bash
# Install a new package
pip install <package-name>

# Update requirements.txt after changes
pip freeze > requirements.txt
git add requirements.txt && git commit -m "Update requirements"

# Upgrade a package
pip install --upgrade <package-name> && pip freeze > requirements.txt

# List outdated packages
pip list --outdated
```
Note: Test thoroughly after dependency upgrades; use a branch for dependency updates.

Troubleshooting commands (network, logs, DB)
```bash
# Check Python version
python3 --version

# See installed packages
pip list

# Check if Postgres listens on port 5432 (Linux)
sudo ss -tulpn | grep 5432

# Tail PostgreSQL logs (Ubuntu path — adjust for your distro)
sudo tail -f /var/log/postgresql/postgresql-*.log

# Inspect app logs (if your app writes to app.log)
tail -f app.log

# Test DB connection from CLI using sqlalchemy (quick one-liner)
python3 -c "import os; from sqlalchemy import create_engine; print(create_engine(os.getenv('DATABASE_URL')).engine)"

# Check open ports and processes (macOS / Linux)
netstat -an | grep 5432 || ss -ltnp | grep 5432

# If you see permission issues on log files
ls -l app.log
chmod 664 app.log    # adjust per your policies
```
Note: Replace paths with your environment specifics. Check container logs if using Docker.

Helpful cleanup and migration reset (development only)
```bash
# Warning: destructive. Only for development where you can drop DB and reset migrations.

# Drop and recreate DB (UNIX)
sudo -u postgres psql -c "DROP DATABASE IF EXISTS studentdb;"
sudo -u postgres psql -c "CREATE DATABASE studentdb;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE studentdb TO student_user;"

# Remove migrations directory and reinitialize (development only)
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```
Note: Never do this on production. For production schema issues, create forward migrations to reconcile differences.

Contribution workflow commands
```bash
# Create a feature branch
git checkout -b feat/your-feature

# Add changes
git add <files>

# Commit with a descriptive message
git commit -m "feat: add ..."

# Push your branch
git push origin feat/your-feature

# Create a Pull Request using GitHub UI or hub/gh CLI tool
# If using gh CLI:
gh pr create --fill
```
Note: Include tests and update migrations as part of the PR if you change models.

Essential curl examples (smoke tests)
```bash
# Health check (adjust base path as per your app)
curl http://localhost:5000/health

# Create student (example)
curl -X POST http://localhost:5000/api/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice Johnson","domain":"Computer Science","gpa":3.8,"email":"alice@univ.edu"}'

# Get all students
curl http://localhost:5000/api/students

# Get single student
curl http://localhost:5000/api/students/1

# Update student
curl -X PUT http://localhost:5000/api/students/1 \
  -H "Content-Type: application/json" \
  -d '{"gpa": 3.9}'

# Delete student
curl -X DELETE http://localhost:5000/api/students/1
```
Note: These are manual verification commands. Use Postman or automated tests for repeated runs.

Reset PostgreSQL password (if needed)
```bash
# In psql as superuser (example)
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'new_secure_password';"
```
Note: Update `.env` or your secrets store after changing DB passwords.

PG_HBA / remote connection checks
```bash
# If remote connections failing, check Postgres is listening on 0.0.0.0 in postgresql.conf
# And verify pg_hba.conf has proper host entries, then restart PostgreSQL:
sudo systemctl restart postgresql
```
Note: Editing `postgresql.conf` and `pg_hba.conf` requires admin rights and should be done carefully.

When migrating non-nullable columns safely
```bash
# Pattern:
# 1) Add column as nullable via model change + migration
flask db migrate -m "Add phone nullable"
flask db upgrade

# 2) Backfill values with a script or SQL
# 3) Alter column to non-nullable via a new migration
flask db migrate -m "Make phone non-nullable"
flask db upgrade
```
Note: This avoids locking or failing migrations on existing rows.

Final checklist to start working
```bash
# 1) Activate venv
source .venv/bin/activate

# 2) Ensure .env is populated and correct

# 3) Ensure PostgreSQL is running and DB exists

# 4) Run migrations
flask db upgrade

# 5) Start app (development)
flask run
```
Note: After these steps, use curl or Postman to hit the health and students endpoints.

---

If you want, I can:
- Commit this file into your repository if you provide the repository owner/name and branch (I will need that info to push via the GitHub write tool).
- Or create a Docker Compose file to bring up the app and Postgres for local development.
Which would you prefer next?
