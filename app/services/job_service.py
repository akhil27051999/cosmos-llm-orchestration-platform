from app.domain.job import Job
from app.ports.job_repository import JobRepository


class JobService:
    def __init__(self, repo: JobRepository) -> None:
        self._repo = repo

    def submit(self) -> Job:
        job = Job()
        self._repo.add(job)
        return job