# Local Setup & API Testing Guide — Student REST API

## Overview

This guide covers everything you need to build, set up, and test the Student REST API locally — from environment setup and database configuration to running the server and testing all API endpoints.

---

## Prerequisites

- Python 3.8+
- PostgreSQL running locally on port `5432`
- Git

---

## 1. Clone & Setup Virtual Environment

```sh
git clone <repository-url>
cd Flask-REST-API

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

---

## 2. Configure Environment Variables

Create a `.env` file at the project root (never commit this):

```env
FLASK_ENV=development
FLASK_APP=app:create_app
FLASK_DEBUG=1
DEBUG=True

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=studentdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/studentdb
```

> **Note:** Use `localhost` as the host when running outside Docker. Use `postgres` (service name) only inside Docker Compose.

---

## 3. PostgreSQL Database Setup

```sh
# Access PostgreSQL shell
psql -U postgres -h localhost -W
```

Run inside psql:

```sql
CREATE USER postgres WITH PASSWORD 'postgres123';
CREATE DATABASE studentdb;
GRANT ALL PRIVILEGES ON DATABASE studentdb TO postgres;
ALTER DATABASE studentdb OWNER TO postgres;
\q
```

---

## 4. Database Migrations

```sh
export FLASK_APP=app:create_app

flask db init                                                      # Run once — creates migrations/ folder
flask db migrate -m "initial migration - create student table"     # Generate migration script
flask db upgrade                                                   # Apply migration — creates tables
```

**Verify tables were created:**

```sh
psql -U postgres -h localhost -d studentdb -W

\dt                      # Should show alembic_version and students
SELECT * FROM students;  # Should return empty rows
\q
```

**Other useful migration commands:**

```sh
flask db downgrade    # Rollback last migration
flask db current      # Show current revision
flask db history      # Show full migration history
```

---

## 5. Seed the Database

```sh
python seed.py    # Inserts 100 student records
```

---

## 6. Run the Flask Server

```sh
source venv/bin/activate
flask run
```

Server starts at: `http://127.0.0.1:5000`

> **macOS Note:** Always use `127.0.0.1` instead of `localhost` in your requests — macOS resolves `localhost` to IPv6 (`::1`) but Flask listens on IPv4 only.

---

## 7. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/students` | Get all students |
| GET | `/students/<id>` | Get student by ID |
| POST | `/students` | Add a new student |
| PUT | `/students/<id>` | Update a student |
| DELETE | `/students/<id>` | Delete a student |

---

## 8. Testing with curl

**Health check:**

```sh
curl http://127.0.0.1:5000/health
```

**GET all students:**

```sh
curl http://127.0.0.1:5000/students
```

**GET student by ID:**

```sh
curl http://127.0.0.1:5000/students/1
```

**POST — Add a student:**

```sh
curl -X POST http://127.0.0.1:5000/students \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Johnson", "domain": "Computer Science", "gpa": 3.8, "email": "alice@university.edu"}'
```

**PUT — Update a student:**

```sh
curl -X PUT http://127.0.0.1:5000/students/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Smith", "gpa": 3.9}'
```

**DELETE — Remove a student:**

```sh
curl -X DELETE http://127.0.0.1:5000/students/1
```

---

## 9. Testing with Postman

1. Download and open [Postman](https://www.postman.com/downloads/)
2. Create a new **Collection** → name it `Student API`
3. For each request:
   - Set the HTTP method and URL (use `http://127.0.0.1:5000`)
   - For POST/PUT: go to **Body** → **raw** → select **JSON**
4. Save each request inside the collection for reuse

**Common issues:**

| Issue | Cause | Fix |
|-------|-------|-----|
| `Connection refused` | Flask server not running | Run `flask run` |
| `404 Not Found` | Wrong URL prefix | Use `/students`, not `/api/students` |
| Empty response | `localhost` resolves to IPv6 on macOS | Use `127.0.0.1` instead |
| `flask: command not found` | Virtual env not activated | Run `source venv/bin/activate` |

---

## 10. Viewing Logs

Logs are auto-created at `student_api.log` in the project root on first app start.

```sh
# Live log stream (recommended during development)
tail -f student_api.log

# Last 50 lines
tail -n 50 student_api.log

# Filter errors only
grep "ERROR" student_api.log

# Filter by keyword
grep "students" student_api.log
```

---

## 11. Quick Reference — Full Command Sequence

```sh
# One-time setup
source venv/bin/activate
export FLASK_APP=app:create_app
flask db init
flask db migrate -m "initial migration"
flask db upgrade
python seed.py

# Every time
source venv/bin/activate
flask run

# In a separate terminal — live logs
tail -f student_api.log
```
