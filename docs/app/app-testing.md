# App Testing Guide — Unit Testing & Load Testing

This guide covers unit testing and load testing of the Student Management Flask REST API.

---

## Overview

The API provides the following endpoints tested across both unit and load tests:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home page |
| GET | `/health` | Health check |
| GET | `/students` | Get all students |
| POST | `/students` | Add a new student |
| GET | `/students/<id>` | Get a single student |
| PUT | `/students/<id>` | Update a student |
| DELETE | `/students/<id>` | Delete a student |

---

## Part 1 — Unit Testing

### Overview

Unit tests use **pytest** with an **in-memory SQLite database** — no real PostgreSQL connection needed. Each test starts with a clean DB and tears it down after.

**Test config** (`tests/config.py`): uses `sqlite:///:memory:` so tests are fast and isolated.

**Fixtures** (`tests/unit/conftest.py`): creates all tables before each test and drops them after.

### Setup

```sh
source venv/bin/activate
pip install pytest pytest-flask
```

### Run Unit Tests

```sh
# Run all unit tests with verbose output
pytest tests/unit/ -v

# Run a specific test
pytest tests/unit/test_students.py::test_add_student -v

# Run with short summary
pytest tests/unit/ -v --tb=short
```

### What's Being Tested

| Test | Endpoint | What it checks |
|------|----------|----------------|
| `test_healthcheck` | `GET /health` | Returns `200` and `{"status": "ok"}` |
| `test_add_student` | `POST /students` | Returns `201` and success message |
| `test_get_students` | `GET /students` | Returns `200` and a list |
| `test_get_student_by_id` | `GET /students/1` | Returns correct student data by ID |
| `test_update_student` | `PUT /students/1` | Returns `200` and update success message |
| `test_delete_student` | `DELETE /students/1` | Returns `200` and delete success message |

### Expected Output

```sh
tests/unit/test_students.py::test_healthcheck           PASSED
tests/unit/test_students.py::test_add_student           PASSED
tests/unit/test_students.py::test_get_students          PASSED
tests/unit/test_students.py::test_get_student_by_id     PASSED
tests/unit/test_students.py::test_update_student        PASSED
tests/unit/test_students.py::test_delete_student        PASSED

6 passed in Xs
```

### Unit Testing Best Practices

- Each test is independent — do not rely on state from other tests.
- Use unique emails per test to avoid unique constraint conflicts.
- Always add a record before testing GET/PUT/DELETE by ID.
- Use the in-memory SQLite DB for speed — never run unit tests against the production DB.

---

## Part 2 — Load Testing

### Overview

Load testing uses **Locust** to simulate concurrent users hitting all API endpoints. It measures throughput (requests/sec), response times, and failure rates.

### Load Testing Goals

- Test performance and stability under concurrent requests.
- Measure request throughput, response times, and failure rates.
- Identify bottlenecks for read-heavy and write-heavy traffic.
- Verify the API handles mixed traffic patterns reliably.

### Setup

```sh
source venv/bin/activate
pip install locust
```

Seed the database with test data before running:

```sh
python seed.py    # Inserts 100 student records
```

Start the Flask server:

```sh
flask run
```

### Run Load Tests

**Web UI mode (recommended):**

```sh
locust -f tests/load_test.py --host=http://127.0.0.1:5000
```

Open `http://localhost:8089` in your browser → set users and spawn rate → click **Start swarming**.

**Headless mode (no UI):**

```sh
locust -f tests/load_test.py --host=http://127.0.0.1:5000 \
  --headless -u 50 -r 10 --run-time 60s
```

| Flag | Description |
|------|-------------|
| `-u 50` | 50 concurrent users |
| `-r 10` | Spawn 10 users per second |
| `--run-time 60s` | Run for 60 seconds |

### Endpoints Tested & Task Weights

The load test script is at `tests/load_test.py`. It simulates realistic user behaviour with weighted tasks:

| Task | Weight | Endpoint |
|------|--------|----------|
| Home | 1x | `GET /` |
| Health check | 1x | `GET /health` |
| Get all students | 2x | `GET /students` |
| Create student | 1x | `POST /students` |
| Get by ID | 1x | `GET /students/<id>` |
| Update student | 1x | `PUT /students/<id>` |
| Delete student | 1x | `DELETE /students/<id>` |

`GET /students` has 2x weight to simulate read-heavy workloads.

### Observations from Load Testing

**GET / and /health:**
- All requests succeeded.
- Median response: 150–200ms.
- Lightweight endpoints, very fast and reliable.

**GET /students:**
- Handles ~13 requests/sec for 1,300+ records.
- Median response ≈ 291ms.
- 95th percentile ≈ 780ms due to large response payloads.
- Recommendation: add pagination for production use.

**POST /students:**
- Some failures due to duplicate email constraints.
- Handles ~5–6 successful requests/sec with random payload.
- Median response ≈ 325ms; maximum ≈ 1.6s.
- Recommendation: generate truly unique emails in test data.

**GET / PUT / DELETE /students/<id>:**
- Extremely fast — average ~20ms.
- Some GET/DELETE failures occur if the ID was already deleted during the test run.

**Overall results:**
- Aggregated throughput: ~32–35 requests/sec across all endpoints.
- Median response across all endpoints ≈ 48ms.
- API is stable and performant for read-heavy workloads.
- Write operations require better unique constraint handling under load.

### Load Testing Best Practices

- Seed the DB with `python seed.py` before each load test run.
- Use unique test data for POST requests to avoid email constraint failures.
- Incrementally increase users to observe scaling limits.
- Monitor 95th percentile response times — not just the median.
- Monitor DB performance (`pg_stat_activity`) during concurrent write tests.
- Run load tests in a separate terminal from the Flask server to avoid interference.

---

## Quick Reference

```sh
# Unit tests
source venv/bin/activate
pytest tests/unit/ -v

# Load tests (web UI)
source venv/bin/activate
flask run                                                         # Terminal 1
locust -f tests/load_test.py --host=http://127.0.0.1:5000        # Terminal 2
# Open http://localhost:8089

# Load tests (headless)
locust -f tests/load_test.py --host=http://127.0.0.1:5000 \
  --headless -u 50 -r 10 --run-time 60s
```
