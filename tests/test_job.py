from app.domain.job import Job, JobStatus

def test_new_job_starts_pending():
    job = Job()
    assert job.status == JobStatus.PENDING
