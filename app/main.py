import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.adapters.memory_job_repository import InMemoryJobRepository
from app.services.job_service import JobService, JobNotFound

app = FastAPI(title="Cosmos", description="Asynchronous job-orchestration API for LLM workloads.", version="0.1.0")

job_service = JobService(InMemoryJobRepository())

class JobResponse(BaseModel):
    id: uuid.UUID
    status: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/jobs", status_code=201)
def submit_job() -> JobResponse:
    job = job_service.submit()
    return JobResponse(id=job.id, status=job.status.value)

@app.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID) -> JobResponse:
    try:
        job = job_service.get(job_id)
    except JobNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return JobResponse(id=job.id, status=job.status.value)
