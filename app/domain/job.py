import uuid
from dataclasses import dataclass, field
from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InvalidTransition(ValueError):
    def __init__(self, start: JobStatus, target: JobStatus):
        self.start = start
        self.target = target
        super().__init__(f"cannot move from {start.value} to {target.value}")


ALLOWED_TRANSITIONS = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.SUCCEEDED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}


@dataclass
class Job:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: JobStatus = JobStatus.PENDING

    @property
    def is_terminal(self) -> bool:
        return not ALLOWED_TRANSITIONS[self.status]

    def transition_to(self, target: JobStatus) -> None:
        allowed = ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise InvalidTransition(self.status, target)
        self.status = target

