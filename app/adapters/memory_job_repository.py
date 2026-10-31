import uuid
from dataclasses import replace

from app.domain.job import Job


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, Job] = {}

    def add(self, job: Job) -> None:
        self._jobs[job.id] = replace(job)

    def get(self, job_id: uuid.UUID) -> Job | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return replace(job)
    
    def update(self, job: Job) -> None:
        self._jobs[job.id] = replace(job)
