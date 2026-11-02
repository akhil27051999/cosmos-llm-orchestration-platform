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

