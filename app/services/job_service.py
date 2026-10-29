import uuid

from app.domain.job import Job
from app.ports.job_repository import JobRepository

class JobNotFound(LookupError):
    def __init__(self, job_id: uuid.UUID):
        self.job_id = job_id
        super().__init__(f"job {job_id} not found")

class JobService:
    def __init__(self, repo: JobRepository) -> None:
        self._repo = repo

    def submit(self) -> Job:
        job = Job()
        self._repo.add(job)
        return job

    def get(self, job_id: uuid.UUID) -> Job:
        job = self._repo.get(job_id)
        if job is None:
            raise JobNotFound(job_id)
        return job