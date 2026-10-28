import uuid
from typing import Protocol

from app.domain.job import Job

class JobRepository(Protocol):
    def add(self, job: Job) -> None: ...

    def get(self, job_id: uuid.UUID) -> Job | None: ...
