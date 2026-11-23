import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_submit_job_returns_201():
    response = client.post("/jobs")
    assert response.status_code == 201

def test_submit_job_returns_the_new_job():
    response = client.post("jobs")
    body = response.json()
    assert body["status"] == "pending"
    assert "id" in body 

def test_get_job_returns_the_submitted_job():
    created = client.post("/jobs").json()
    response = client.get(f"/jobs/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_job_returns_404_with_reason():
    job_id = uuid.uuid4()
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 404
    assert str(job_id) in response.json()["detail"]


def test_get_job_with_malformed_id_returns_422():
    response = client.get("/jobs/not-a-uuid")
    assert response.status_code == 422


def test_cancel_job_returns_the_cancelled_job():
    created = client.post("/jobs").json()
    response = client.post(f"/jobs/{created['id']}/cancel")
    assert response.status_code == 200
    assert response.json() == {"id": created["id"], "status": "cancelled"}


def test_cancel_job_stays_cancelled():
    created = client.post("/jobs").json()
    client.post(f"/jobs/{created['id']}/cancel")
    response = client.get(f"/jobs/{created['id']}")
    assert response.json()["status"] == "cancelled"


def test_cancel_unknown_job_returns_404_with_reason():
    job_id = uuid.uuid4()
    response = client.post(f"/jobs/{job_id}/cancel")
    assert response.status_code == 404
    assert str(job_id) in response.json()["detail"]


def test_cancel_already_cancelled_job_returns_409():
    created = client.post("/jobs").json()
    client.post(f"/jobs/{created['id']}/cancel")
    response = client.post(f"/jobs/{created['id']}/cancel")
    assert response.status_code == 409

def test_repeated_idempotency_key_returns_the_same_job_with_200():
    headers = {"Idempotency-Key": "retry-abc-123"}
    first = client.post("/jobs", headers=headers)
    second = client.post("/jobs", headers=headers)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()


def test_different_idempotency_keys_create_different_jobs():
    first = client.post("/jobs", headers={"Idempotency-Key": "key-a"})
    second = client.post("/jobs", headers={"Idempotency-Key": "key-b"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_without_idempotency_key_every_post_creates_a_new_job():
    first = client.post("/jobs")
    second = client.post("/jobs")
    assert first.json()["id"] != second.json()["id"]
