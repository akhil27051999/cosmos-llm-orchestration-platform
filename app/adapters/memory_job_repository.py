import uuid
from dataclasses import replace

from app.domain.job import Job


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, Job] = {}
        self._idempotency_keys: dict[str, uuid.UUID] = {}

    def add(self, job: Job) -> None:
        self._jobs[job.id] = replace(job)
        if job.idempotency_key is not None:
            self._idempotency_keys[job.idempotency_key] = job.id

    def get(self, job_id: uuid.UUID) -> Job | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return replace(job)

    def get_by_idempotency_key(self, idempotency_key: str) -> Job | None:
        job_id = self._idempotency_keys.get(idempotency_key)
        if job_id is None:
            return None
        return self.get(job_id)

    def update(self, job: Job) -> None:
        self._jobs[job.id] = replace(job)
        if job.idempotency_key is not None:
            self._idempotency_keys[job.idempotency_key] = job.id
