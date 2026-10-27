import uuid

import pytest

from app.domain.job import Job, JobStatus, InvalidTransition

def test_new_job_starts_pending():
    job = Job()
    assert job.status == JobStatus.PENDING

def test_new_job_has_an_id():
    job = Job()
    assert isinstance(job.id, uuid.UUID)

def test_each_job_gets_a_unique_id():
    first = Job()
    second = Job()
    assert first.id != second.id

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

def test_rejected_move_leaves_status_unchanged():
    job = Job(status=JobStatus.SUCCEEDED)
    with pytest.raises(InvalidTransition):
        job.transition_to(JobStatus.CANCELLED)
    assert job.status == JobStatus.SUCCEEDED

@pytest.mark.parametrize("status, expected", [
    (JobStatus.PENDING, False),
    (JobStatus.RUNNING, False),
    (JobStatus.SUCCEEDED, True),
    (JobStatus.FAILED, True),
    (JobStatus.CANCELLED, True),
])
def test_is_terminal(status, expected):
    job = Job(status=status)
    assert job.is_terminal == expected

