"""Operational monitoring and controls for the durable ingestion queue."""

from auth import require_operator
from fastapi import APIRouter, Depends, HTTPException, Query
from jobs import cancel_job, get_job, job_summary, list_jobs, retry_job

router = APIRouter(prefix="/api/operations", tags=["operations"], dependencies=[Depends(require_operator)])


@router.get("/jobs")
def get_operation_jobs(limit: int = Query(50, ge=1, le=200), status: str | None = Query(None)):
    return list_jobs(limit=limit, status=status)


@router.get("/jobs/summary")
def get_operation_job_summary():
    return job_summary()


@router.get("/jobs/{job_id}")
def get_operation_job(job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/retry")
def retry_operation_job(job_id: int):
    job = retry_job(job_id)
    if not job:
        raise HTTPException(status_code=409, detail="Only failed or cancelled jobs can be retried")
    return job


@router.post("/jobs/{job_id}/cancel")
def cancel_operation_job(job_id: int):
    job = cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=409, detail="Only queued or running jobs can be cancelled")
    return job
