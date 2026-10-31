import uuid

from app.adapters.memory_job_repository import InMemoryJobRepository
from app.domain.job import Job, JobStatus

def test_added_job_can_be_found_by_id():
    repo = InMemoryJobRepository()
    job = Job()
    repo.add(job)
    assert repo.get(job.id) == job

def test_unknown_job_returns_none():
    repo = InMemoryJobRepository()
    assert repo.get(uuid.uuid4()) is None

def test_changing_a_job_after_add_does_not_change_the_stored_job():
    repo = InMemoryJobRepository()
    job = Job()
    repo.add(job)
    job.transition_to(JobStatus.RUNNING)
    assert repo.get(job.id).status == JobStatus.PENDING