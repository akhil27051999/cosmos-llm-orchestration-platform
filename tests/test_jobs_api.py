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
    response = client.get(f"/jobs/{id}")
    assert response.status_code == 404
    assert str(id) in response.json()["detail"]


def test_get_job_with_malformed_id_returns_422():
    response = client.get("/jobs/not-a-uuid")
    assert response.status_code == 422
