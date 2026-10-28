import uuid

from app.adapters.memory_job_repository import InMemoryJobRepository
from app.domain.job import Job

def test_added_job_can_be_found_by_id():
    repo = InMemoryJobRepository()
    job = Job()
    repo.add(job)
    assert repo.get(job.id) == job

def test_unknown_job_returns_none():
    repo = InMemoryJobRepository()
    assert repo.get(uuid.uuid4()) is None
