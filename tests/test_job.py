import pytest

from app.domain.job import Job, JobStatus, InvalidTransition

@pytest.mark.parametrize("start, target", [
    (JobStatus.PENDING, JobStatus.RUNNING),
    (JobStatus.PENDING, JobStatus.CANCELLED),
    (JobStatus.RUNNING, JobStatus.SUCCEEDED),
    (JobStatus.RUNNING, JobStatus.FAILED),
    (JobStatus.RUNNING, JobStatus.CANCELLED),
])
def test_allowed_moves(start, target):
    job = Job(status=start)           
    job.transition_to(target)
    assert job.status == target

def test_new_job_starts_pending():
    job = Job()
    assert job.status == JobStatus.PENDING

def test_succeeded_job_cannot_be_cancelled():
    job = Job(status=JobStatus.SUCCEEDED)
    with pytest.raises(InvalidTransition):
        job.transition_to(JobStatus.CANCELLED)
    assert job.status == JobStatus.SUCCEEDED

def test_cancelled_job_cannot_be_succeeded():
    job = Job(status=JobStatus.CANCELLED)
    with pytest.raises(InvalidTransition):
        job.transition_to(JobStatus.SUCCEEDED)
    assert job.status == JobStatus.CANCELLED

@pytest.mark.parametrize("start, target", [
    (JobStatus.PENDING, JobStatus.SUCCEEDED),
    (JobStatus.PENDING, JobStatus.FAILED),
    (JobStatus.RUNNING, JobStatus.PENDING),
    (JobStatus.SUCCEEDED, JobStatus.RUNNING),
    (JobStatus.SUCCEEDED, JobStatus.CANCELLED),
    (JobStatus.FAILED, JobStatus.RUNNING),
    (JobStatus.CANCELLED, JobStatus.SUCCEEDED),
])
def test_illegal_moves_are_rejected(start, target):
    job = Job(status=start)
    with pytest.raises(InvalidTransition):
        job.transition_to(target)
    assert job.status == start
