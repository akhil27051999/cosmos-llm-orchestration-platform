from app.domain.job import Job, JobStatus
import pytest

@pytest.mark.parametrize("start, target", [
    (JobStatus.PENDING, JobStatus.RUNNING),
    (JobStatus.PENDING, JobStatus.CANCELLED),
    (JobStatus.RUNNING, JobStatus.SUCCEEDED),
    (JobStatus.RUNNING, JobStatus.FAILED),
    (JobStatus.RUNNING, JobStatus.CANCELLED),
])
def test_allowed_moves(start, target):
    job = Job(status=start)           # arrange: build it directly in the start state
    job.transition_to(target)
    assert job.status == target

def test_new_job_starts_pending():
    job = Job()
    assert job.status == JobStatus.PENDING
