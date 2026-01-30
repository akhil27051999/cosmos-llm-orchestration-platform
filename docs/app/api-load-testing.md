# Load Testing - Student Management API

## Overview

This directory contains load testing scripts for the Student Management API. We use Locust to simulate concurrent users and measure API performance under load.

The load test covers the following endpoints:

- `GET /students` — Retrieve all students
- `POST /students` — Create a new student

## Prerequisites

- Python 3.10+
- Locust 2.x
- The Flask API must be running locally or remotely

Install Locust if not already installed:

```bash
pip install locust
```

## Running the Load Test

1. Start your Flask API:

```bash
export FLASK_APP=app:create_app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

2. Open a new terminal and navigate to the `tests/` directory:

```bash
cd tests
```

3. Run Locust:

```bash
locust -f load_test.py --host=http://localhost:5000 --web-host 0.0.0.0
```

4. Access the web interface in your browser and specify number of users and spawn rate:

```
http://<your-server-ip>:8089
```

Start the test from the web UI.

## Load Test Script (tests/load_test.py)

```python
from locust import HttpUser, task, between
import random

class StudentApiUser(HttpUser):
    wait_time = between(1, 2)

    @task(2)
    def get_students(self):
        self.client.get("/students")

    @task(1)
    def create_student(self):
        student_id = random.randint(1000, 9999)
        payload = {
            "name": f"Test User {student_id}",
            "domain": "Engineering",
            "gpa": round(random.uniform(6.0, 10.0), 2),
            "email": f"testuser{student_id}@example.com"
        }
        self.client.post("/students", json=payload)
```

## Observations from Load Testing

The load test was run with 50 concurrent users and a spawn rate of 5 users per second.

### Summary Table

| Request       | # Requests | # Failures | Median (ms) | Average (ms) | Min (ms) | Max (ms) | Avg Size (bytes) |
|---------------|------------|------------|-------------|--------------|----------|----------|-------------------|
| GET /students | 1257       | 0          | 13          | 17.87        | 5        | 159      | 40932.49          |
| POST /students| 601        | 19         | 8           | 11.65        | 6        | 78       | 1934.76           |
| **Aggregated**| 1858       | 19         | 11          | 15.86        | 5        | 159      | 28318.05          |

### Observations

- GET Requests:
  - No failures occurred.
  - Response times were fast (median: 13 ms, average: 17.87 ms), showing the API handles read-heavy operations well.

- POST Requests:
  - A small number of failures (19) occurred out of 601 requests (~3% failure rate).
  - Response times were slightly lower than GET requests (median: 8 ms, average: 11.65 ms), but failures indicate occasional issues with creating new entries under load.

- Overall Performance:
  - The API handled approximately 32 requests/sec (aggregated) under this simulated load.
  - Response times stayed under 200 ms for both GET and POST requests, indicating good responsiveness.
  - Failures on POST requests may require investigation into database constraints, concurrency handling, or server resource limits.

## Recommendations

- Investigate POST failures to identify whether they are caused by:
  - database constraints (unique indexes, FK constraints),
  - race conditions during concurrent inserts,
  - connection/timeouts to the database,
  - or insufficient server resources under burst load.

- Consider:
  - implementing database connection pooling,
  - adding retries for transient failures (with exponential backoff),
  - validating and sanitizing payloads before inserting,
  - introducing optimistic locking or deduplication where appropriate.

- Run additional tests:
  - with higher concurrency to observe scaling limits,
  - with realistic user behavior (think time, different endpoints),
  - varying payload sizes and database load.

- Use the Locust web interface to continuously monitor:
  - requests/sec (RPS),
  - failure rates,
  - response-time percentiles (median, 95th, 99th),
  - and request/response sizes.

## Notes

- Keep test environment as close to production as possible for meaningful results (same DB size/config, same instance types).
- Capture and inspect server logs during the test to correlate errors and stack traces with failing requests.
- If failures persist, run a focused test targeting POSTs to reproduce and capture detailed error responses from the API.
