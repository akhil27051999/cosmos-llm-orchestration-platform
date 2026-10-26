from enum import Enum

class JobStatus(Enum):
    PENDING = "pending"

class Job:
    def __init__(self):
        self.status = JobStatus.PENDING
