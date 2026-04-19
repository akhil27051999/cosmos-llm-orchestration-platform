# Module 1B: Application Testing — Unit & Load Tests

> **Goal:** Validate API correctness with **unit tests** (pytest + in-memory SQLite) and measure performance under load with **load tests** (Locust).

> **Why this matters:** SREs are paid to prevent regressions and capacity surprises. Unit tests catch logic bugs in CI; load tests catch scaling cliffs before production users do.

---

## Table of Contents

1. [Test Strategy Overview](#test-strategy-overview)
2. [Part 1 — Unit Testing](#part-1--unit-testing)
3. [Part 2 — Load Testing](#part-2--load-testing)
4. [Commands Reference](#commands-reference)
5. [Troubleshooting](#troubleshooting)
6. [Interview Q&A](#interview-qa)
7. [STAR Stories](#star-stories)
8. [Production Hardening](#production-hardening)

---

## Test Strategy Overview

### The Test Pyramid

```
              /\
             /  \   E2E (slow, brittle, few)
            /────\
           / Integ.\  Integration (medium count)
          /────────\
         /  Unit    \  Unit (fast, many, isolated)
        /────────────\
```

| Type | Tool in this Project | Speed | When to Run | What It Catches |
|------|---------------------|-------|-------------|-----------------|
| **Unit** | pytest + Flask test client + in-memory SQLite | ms | Every commit (CI) | Logic bugs, regressions |
| **Load** | Locust | minutes | Pre-release / weekly | Performance bottlenecks, scaling limits |
| **Integration** | pytest with real Postgres (not done here) | seconds | Pre-merge | Wiring bugs, schema drift |
| **E2E** | Playwright/Cypress (not in scope) | minutes | Pre-release | UX-level regressions |

---

## Part 1 — Unit Testing

### Why In-Memory SQLite?

| Real Postgres | In-Memory SQLite |
|---------------|------------------|
| Slow startup (network, container) | Instant |
| State leaks between tests | Fresh per test |
| Requires running DB | No external deps |
| Catches DB-specific issues (Postgres types, JSONB) | Misses some Postgres quirks |

**Trade-off:** Speed over fidelity. We use SQLite for unit tests (catch logic bugs fast); integration tests with real Postgres are run separately if needed.

### Test Configuration

**[tests/config.py](../../tests/config.py):**
```python
class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

`:memory:` means SQLite creates the DB in RAM — no file on disk. Each test fixture creates a fresh DB and drops it after.

### Test Fixture (conftest.py)

**[tests/unit/conftest.py](../../tests/unit/conftest.py):**
```python
import pytest
from app import create_app, db
from tests.config import TestConfig

@pytest.fixture
def client():
    app = create_app(config_class=TestConfig)

    with app.app_context():
        db.create_all()

    with app.test_client() as client:
        yield client

    with app.app_context():
        db.drop_all()
```

**Key concepts:**
- `pytest.fixture` — reusable setup. Tests that include `client` as a parameter get a fresh DB.
- `app.test_client()` — Flask's built-in test client; sends requests without an HTTP server.
- `yield` — pytest fixture pattern: setup → run test → teardown.

### Sample Unit Test

**[tests/unit/test_students.py](../../tests/unit/test_students.py):**
```python
def test_add_student(client):
    student_data = {
        "name": "Ramesh Kumar",
        "domain": "ECE",
        "gpa": 8.7,
        "email": "160101130001@cutm.ac.in"
    }
    res = client.post("/students", json=student_data)
    assert res.status_code == 201
    assert res.get_json()["message"] == "Student added successfully!"
```

### What's Covered

| Test | Endpoint | Validates |
|------|----------|-----------|
| `test_healthcheck` | GET `/health` | Returns 200 + `{"status":"ok"}` |
| `test_add_student` | POST `/students` | Returns 201 + success message |
| `test_get_students` | GET `/students` | Returns 200 + list |
| `test_get_student_by_id` | GET `/students/<id>` | Returns 200 + correct student |
| `test_update_student` | PUT `/students/<id>` | Returns 200 + updated message |
| `test_delete_student` | DELETE `/students/<id>` | Returns 200 + deleted message |

### Run Unit Tests

```bash
# All unit tests
pytest -v tests/unit

# Single test
pytest -v tests/unit/test_students.py::test_add_student

# Stop at first failure
pytest -v tests/unit -x

# Show coverage
pip install pytest-cov
pytest --cov=app tests/unit
```

---

## Part 2 — Load Testing

### Why Load Test?

Unit tests prove "it works." Load tests prove "it works under N users." Without them, you discover bottlenecks in production — usually during a launch or marketing push.

### What Load Tests Measure (RED Method)

| Metric | What It Reveals |
|--------|-----------------|
| **Rate** (req/s) | Throughput capacity |
| **Errors** (% failures) | When the system breaks |
| **Duration** (p50/p95/p99) | User-visible latency at percentiles |

Plus saturation indicators: CPU%, memory%, DB connection pool exhaustion, network bandwidth.

### Tool: Locust

Python-based load testing framework. You write user behavior in code, run from CLI or web UI, scale to thousands of simulated users.

### Load Test Script

**[tests/load_test.py](../../tests/load_test.py):**
```python
from locust import HttpUser, task, between
import random

class StudentApiUser(HttpUser):
    wait_time = between(1, 2)   # simulated user think time
    last_student_ids = []

    @task(2)
    def get_students(self):     # weight = 2 (runs 2x more often than weight 1)
        self.client.get("/students")

    @task(1)
    def create_student(self):
        payload = {
            "name": f"Test User {random.randint(1000,9999)}",
            "domain": "Engineering",
            "gpa": round(random.uniform(6.0, 10.0), 2),
            "email": f"testuser{random.randint(1000,9999)}@example.com"
        }
        response = self.client.post("/students", json=payload)
        if response.status_code == 201:
            self.last_student_ids.append(response.json()["id"])
```

**Concepts:**
- `HttpUser` — base class for simulated users that make HTTP calls.
- `wait_time = between(1, 2)` — each user waits 1–2s between actions (simulates real user behavior; without it, you DDoS your own service).
- `@task(N)` — N is the relative weight. `@task(2)` runs 2x as often as `@task(1)`.

### Run Load Test

**Pre-requisites:**
```bash
pip install locust
```

**With UI (recommended):**
```bash
locust -f tests/load_test.py --host=http://localhost:5000
# Then open http://localhost:8089 in browser
# Set: number of users (e.g., 50), spawn rate (e.g., 5/s), and start
```

**Headless (for CI):**
```bash
locust -f tests/load_test.py \
  --host=http://localhost:5000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 2m \
  --headless \
  --csv=load-test-results
```

Outputs CSV with stats: req/s, p50/p95/p99 latency, failure rate.

### Interpreting Results

| Sign | What It Means | Action |
|------|---------------|--------|
| Stable p95 latency, low errors | System healthy at this load | Increase users to find the limit |
| p95 climbing, p99 spiking | Approaching saturation | Profile to find the bottleneck |
| Errors > 1% | System is failing | Stop and fix before going further |
| CPU 100%, low req/s | CPU-bound | Scale horizontally or optimize hot path |
| Low CPU, low req/s, high latency | I/O-bound (DB?) | Check DB connections, query plans |

---

## Commands Reference

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Run all unit tests | `pytest -v tests/unit` | Verbose output for clarity |
| 2 | Run single test file | `pytest -v tests/unit/test_students.py` | Focus during dev |
| 3 | Run single test | `pytest -v tests/unit/test_students.py::test_add_student` | Debug one failure |
| 4 | Stop at first failure | `pytest -x tests/unit` | Faster feedback while iterating |
| 5 | Test coverage | `pytest --cov=app tests/unit` | Identify untested code paths |
| 6 | Show print statements | `pytest -s tests/unit` | Useful when debugging with `print()` |
| 7 | Locust with UI | `locust -f tests/load_test.py --host=http://localhost:5000` | Manual exploration |
| 8 | Locust headless (CI) | `locust ... --headless --users 50 --spawn-rate 5 --run-time 2m` | Reproducible runs |
| 9 | Generate test report | `pytest --html=report.html tests/unit` | (requires `pytest-html`) For CI artifacts |
| 10 | Run load test against k8s service | `locust -f tests/load_test.py --host=http://localhost:8080` (after port-forward) | Test deployed env |

---

## Troubleshooting

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | `ModuleNotFoundError: No module named 'locust'` in CI | Locust isn't in requirements.txt | Limit pytest scope to unit folder: `pytest -v tests/unit` so `tests/load_test.py` isn't collected |
| 2 | `ValueError: Duplicated timeseries in CollectorRegistry: flask_app_info` | `metrics.info()` registers in global Prometheus registry; tests create app multiple times | Don't call `metrics.info()` — use base `PrometheusMetrics(app)` only |
| 3 | Tests fail with `RuntimeError: Working outside of application context` | Used DB or Flask globals outside `app.app_context()` | Wrap with `with app.app_context():` |
| 4 | Tests pass locally but fail in CI | Different Python version or dependency drift | Pin Python version in CI (`actions/setup-python`); use `pip freeze > requirements.txt` |
| 5 | Locust shows 100% failures from start | Wrong host URL or app not running | Verify `--host` flag matches a running server |
| 6 | Connection errors after ~30 users | Connection pool exhausted (DB or HTTP) | Increase pool size in app config; or rate-limit users |
| 7 | Tests interfere with each other | Shared state across tests | Use `pytest.fixture` with proper teardown (already done in conftest) |

---

## Interview Q&A

| Q | A |
|---|---|
| **What's the test pyramid?** | A guide to test mix: many fast unit tests at the base, fewer integration tests in the middle, very few slow E2E tests at the top. Avoids the "ice cream cone" anti-pattern (mostly slow E2E tests). |
| **Why use in-memory SQLite for tests?** | Fast (instant startup), isolated (fresh DB per test), no external dependencies. Trade-off: doesn't catch Postgres-specific issues — supplement with integration tests using real DB. |
| **What's a pytest fixture?** | Reusable setup/teardown function. Decorated with `@pytest.fixture`. Tests request fixtures by including them as parameters. Pytest manages lifecycle (function/class/module/session scope). |
| **How does `yield` work in fixtures?** | Code before `yield` = setup. Code after = teardown. Pytest runs setup, then runs the test with the yielded value, then runs teardown — even if the test fails. |
| **What's the difference between unit and integration tests?** | Unit = tests one function/class in isolation (mocks DB, network). Integration = tests multiple components together (real DB, real HTTP). Both have value. |
| **Why use Locust over JMeter?** | Locust is Python — easier for Python teams to write/extend. JMeter is GUI-driven, more enterprise. Locust scales horizontally easily. K6 (JS) is another popular choice. |
| **What's `wait_time = between(1,2)` for?** | Simulates real user think time. Without it, you create artificial load that doesn't match production patterns and can DoS your own service. |
| **Difference between p50/p95/p99 latency?** | Percentiles — p95 = 95% of requests are faster than X. p99 captures tail latency (the bad experience for some users). Average is misleading; always look at p99. |
| **What's the RED method?** | Rate, Errors, Duration — the three metrics every service should expose. Used in our Prometheus + Grafana setup (Module 7). |
| **How do you test in CI?** | Run `pytest` on every PR. Block merge if tests fail. Run integration tests on merge to main. Run load tests nightly or pre-release. |
| **How do you handle flaky tests?** | Investigate root cause (don't just retry). Common causes: timing issues, shared state, external dependencies. If genuinely flaky, quarantine and fix. |
| **How do you load-test stateful APIs?** | Track created resource IDs across tasks (like our `last_student_ids` list). Or use a setup phase to pre-populate test data, then run read-heavy tasks. |
| **What's contract testing?** | Tests that verify API contract between services (Pact, Spring Cloud Contract). Catches breaking API changes before they reach consumers. |
| **What's the difference between black-box and white-box testing?** | Black-box = test by inputs/outputs only (E2E). White-box = test internal implementation (unit tests with mocks). Both used in modern testing. |

---

## STAR Stories

### Story 1: "Tell me about a time tests broke and you had to debug it."

**Situation:** After adding `prometheus-flask-exporter` to instrument Flask metrics, all 5 unit tests started failing with `ValueError: Duplicated timeseries in CollectorRegistry: flask_app_info`.

**Task:** Get tests passing again without removing observability.

**Action:**
1. Read the stack trace — failure was on second test execution (first test passed).
2. Realized the `metrics.info('flask_app_info', ...)` call registers a Prometheus metric in the **global default registry**.
3. Each test creates a fresh Flask app via the `client` fixture — but the registry is process-global, not per-app.
4. Second test → second `metrics.info()` call → conflict with already-registered metric.
5. Two options: (a) remove `metrics.info()` since it was optional, or (b) use a per-app `CollectorRegistry`.
6. Chose (a) — `PrometheusMetrics(app)` alone exposes all default request metrics; the `info()` call only added a static label.

**Result:** All 5 tests passing again. CI green within 10 minutes.

**Takeaway:** Process-global state (Prometheus registry, logging handlers, env vars) is hostile to tests that create app instances repeatedly. Either avoid it or scope it explicitly.

---

### Story 2: "Tell me about a time you load-tested a service."

**Situation:** Wanted to know the throughput limit of our Flask API before going to production.

**Task:** Find the breaking point — at what concurrent user count do errors start, and what's the p95 latency curve?

**Action:**
1. Wrote a Locust scenario covering all CRUD endpoints with realistic weights (more reads than writes).
2. Ran in headless mode against the K8s deployment (3 Flask replicas behind nginx).
3. Started at 10 users, ramped to 200 in steps of 50.
4. Watched p95 climb from 50ms → 200ms at 100 users → 800ms at 200 users.
5. Errors started at 180 users (5xx from Postgres connection pool exhaustion).
6. Captured CPU/mem from Grafana — Flask was at 70% CPU, postgres at 95%.

**Result:** Established baseline: ~150 users/sec at p95 < 500ms. Documented this as the SLO. Recommended increasing Postgres connection pool from 10 → 30, which raised the limit to ~250 users.

**Takeaway:** Load test reveals the bottleneck (often DB, not app). Always correlate load test results with infrastructure metrics (CPU, mem, DB connections).

---

## Production Hardening

| Area | Current | Production |
|------|---------|-----------|
| **Test isolation** | In-memory SQLite per test | Add **integration tests** with real Postgres in CI (testcontainers / docker-compose) |
| **Coverage** | None enforced | Enforce > 80% coverage in CI (`pytest --cov-fail-under=80`) |
| **Mutation testing** | None | `mutmut` or `cosmic-ray` to verify tests actually catch bugs |
| **Contract tests** | None | Pact / Spring Cloud Contract for API consumer/provider verification |
| **Snapshot tests** | None | Useful for stable JSON responses |
| **Load testing in CI** | Manual | Nightly Locust runs against staging; alert on regression |
| **Performance budgets** | None | Define SLOs (e.g., p95 < 200ms); fail CI if regression |
| **Chaos engineering** | None | Litmus/Chaos Mesh — kill pods during load tests to verify resilience |
| **Test data management** | Ad-hoc | Factories (factory_boy), fixtures with realistic data |
| **Parallel execution** | Sequential | `pytest-xdist` for parallel test runs |
| **Test reporting** | Console output | JUnit XML for CI, HTML reports for humans, Allure for analytics |
| **Flaky test detection** | None | Tools like `pytest-flakefinder` to detect non-deterministic tests |

---

## Cloud Mapping

| Test Type | Where It Runs | AWS / Cloud Service |
|-----------|---------------|---------------------|
| Unit tests | CI runner | GitHub Actions, AWS CodeBuild, GitLab CI |
| Load tests (manual) | Locust on laptop | — |
| Load tests (distributed) | Multi-node Locust cluster | EKS pods, ECS tasks, Lambda (with limits) |
| Pre-prod load testing | Staging env | AWS Distributed Load Testing (CloudFormation template) |
| Synthetic monitoring | Continuous in production | CloudWatch Synthetics, Datadog Synthetics, Pingdom |
| Chaos engineering | Production-like env | AWS Fault Injection Simulator, Chaos Mesh on EKS |

---

## Reference Links (Internal)

- Test config: [tests/config.py](../../tests/config.py)
- Pytest fixture: [tests/unit/conftest.py](../../tests/unit/conftest.py)
- Unit tests: [tests/unit/test_students.py](../../tests/unit/test_students.py)
- Load test script: [tests/load_test.py](../../tests/load_test.py)
- CI integration: [.github/workflows/ci-pipeline.yaml](../../.github/workflows/ci-pipeline.yaml) (runs `pytest -v tests/unit`)
