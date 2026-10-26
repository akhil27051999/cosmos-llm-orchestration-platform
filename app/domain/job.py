from enum import Enum
from dataclasses import dataclass

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Job:
    status: JobStatus = JobStatus.PENDING

    def transition_to(self, status: JobStatus):
        self.status = status

    def is_allowed_to_transition_to(self, status: JobStatus) -> bool:
        return status in self.allowed_transitions[self.status]

    def is_valid_transition(self, status: JobStatus) -> bool:
        return self.is_allowed_to_transition_to(status)