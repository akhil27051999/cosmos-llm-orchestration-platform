import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.adapters.memory_job_repository import InMemoryJobRepository
from app.services.job_service import JobService, JobNotFound
from app.domain.job import InvalidTransition

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
    job = job_service.get(job_id)
    return JobResponse(id=job.id, status=job.status.value)

@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: uuid.UUID) -> JobResponse:
    job = job_service.cancel(job_id)
    return JobResponse(id=job.id, status=job.status.value)

@app.exception_handler(JobNotFound)
async def job_not_found(request: Request, error: JobNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(InvalidTransition)
async def invalid_transition(request: Request, error: InvalidTransition) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(error)})