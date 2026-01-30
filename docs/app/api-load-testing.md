# Flask REST API Load Testing

This repository contains load testing scripts for the Student Management Flask API, which manages student records using PostgreSQL.

## Overview

The API provides endpoints to manage students:

Method	Endpoint	Description
GET	/	Home page
GET	/health	Health check
GET	/students	Get all students
POST	/students	Add a new student
GET	/students/<id>	Get a single student
PUT	/students/<id>	Update a student
DELETE	/students/<id>	Delete a student

## Load Testing Goals:

- Test the performance and stability of the API under concurrent requests.
- Measure request throughput (requests per second), response times, and failure rates.
- Identify potential bottlenecks for GET and POST requests.
- Verify that the API can handle both read and write-heavy traffic.

## Setup

Activate virtual environment:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
pip install locust
```

Ensure API is running:

```bash
flask run --host=0.0.0.0 --port=5000
```

Verify /students and /health endpoints are accessible.

## Load Testing with Locust

### Locust Test Script

The load test script is located at `tests/load_test.py`.

It simulates Student API users performing:

- GET /students
- POST /students with random student data

(Optional: can add PUT, DELETE, GET /students/<id>)

Run Locust:

```bash
cd tests
locust -f load_test.py --host=http://localhost:5000 --web-host 0.0.0.0
```

Locust web UI will be available at `http://<server-ip>:8089`.

Configure number of users and spawn rate from the UI.

### Endpoints Tested in Locust

- `/` (Home) — lightweight endpoint
- `/health` (Health check) — lightweight endpoint
- `/students` (GET/POST) — core student API
- `/students/<id>` (GET/PUT/DELETE) — single student operations

## Observations from Load Testing

### GET / and /health

- All requests succeeded.
- Median response: 150–200ms.
- Low payload, very fast and reliable.

### GET /students

- Handles ~13 requests/sec for 1,300+ records.
- Median response ≈ 291ms.
- 95th percentile ≈ 780ms (due to large payloads).

### POST /students

- Some failures observed due to duplicate emails (email is unique in DB).
- Handles ~5–6 successful requests/sec with random payload.
- Median response ≈ 325ms; maximum ≈ 1.6s.
- Recommendation: generate unique test data for high-volume writes.

### Single student operations

- GET/PUT/DELETE /students/<id> are extremely fast (avg ~20ms).
- Some GET failures occur if the student ID was deleted during the test.

### Overall

- Aggregated throughput: ~32–35 requests/sec across endpoints.
- Median response for all endpoints ≈ 48ms.
- POST operations require better handling for unique constraints.
- API is stable and performant for read-heavy workloads.

## Load Testing Best Practices

- Use unique test data for POST requests to avoid conflicts.
- Seed the database with realistic test data (`seed.py`) before running tests.
- Monitor database performance under concurrent writes.
- Incrementally increase users in Locust to observe scaling limits.
- Measure 95th percentile response times for production-level performance.

## Generating Test Data

Seed the database with dummy students:

```bash
python seed.py
```

This will insert 100 dummy students with unique emails.

## Running Advanced Tests

To load test all endpoints including `/students/<id>` operations:

Modify `load_test.py` to:

- Maintain a list of existing student IDs.
- Perform GET/PUT/DELETE operations on valid IDs.
- Avoid None or deleted IDs to reduce failures.

Run Locust as usual:

```bash
locust -f tests/load_test.py --host=http://localhost:5000 --web-host 0.0.0.0
```
