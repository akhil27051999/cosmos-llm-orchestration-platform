import uuid

from app.domain.job import Job

class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, Job] = {}

    def add(self, job: Job) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: uuid.UUID) -> Job | None:
        return self._jobs.get(job_id)
