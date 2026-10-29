import uuid
import pytest

from app.adapters.memory_job_repository import InMemoryJobRepository
from app.domain.job import JobStatus
from app.services.job_service import JobService, JobNotFound

def test_submit_returns_a_pending_job():
    service = JobService(InMemoryJobRepository())
    job = service.submit()
    assert job.status == JobStatus.PENDING

def test_submitted_job_is_stored():
    repo = InMemoryJobRepository()
    service = JobService(repo)
    job = service.submit()
    assert repo.get(job.id) == job

def test_get_returns_the_submitted_job():
    service = JobService(InMemoryJobRepository())
    job = service.submit()
    assert service.get(job.id) == job

def test_get_unknown_id_raises_job_not_found():
    service = JobService(InMemoryJobRepository())
    with pytest.raises(JobNotFound):
        service.get(uuid.uuid4())
