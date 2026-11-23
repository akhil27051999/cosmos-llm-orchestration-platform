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

def test_changing_a_fetched_job_does_not_change_the_stored_job():
    repo = InMemoryJobRepository()
    job = Job()
    repo.add(job)
    fetched = repo.get(job.id)
    fetched.transition_to(JobStatus.RUNNING)
    assert repo.get(job.id).status == JobStatus.PENDING

def test_updated_job_is_stored():
    repo = InMemoryJobRepository()
    job = Job()
    repo.add(job)
    fetched = repo.get(job.id)
    fetched.transition_to(JobStatus.CANCELLED)
    repo.update(fetched)
    assert repo.get(job.id).status == JobStatus.CANCELLED

def test_job_can_be_found_by_idempotency_key():
    repo = InMemoryJobRepository()
    job = Job(idempotency_key="abc-123")
    repo.add(job)
    assert repo.get_by_idempotency_key("abc-123") == job

def test_unknown_idempotency_key_returns_none():
    repo = InMemoryJobRepository()
    assert repo.get_by_idempotency_key("never-used") is None