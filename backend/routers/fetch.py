"""Fetch triggers — enqueue durable jobs and expose status."""

from datetime import date

from auth import require_auth
from db import ensure_support_tables, q
from fastapi import APIRouter, Depends, HTTPException, Query
from jobs import enqueue_job, get_job, list_jobs
from ratelimit import STRICT_LIMITER, rate_limited

router = APIRouter(prefix="/api/fetch", tags=["fetch"], dependencies=[Depends(require_auth)])

# Backwards-compatible in-memory status that mirrors the most recent job.
# Frontend polls this; the bat-signal lights when a job is running.
_fetch_status = {
    "running": False,
    "last_triggered": None,
    "last_finished": None,
    "last_result": None,
    "job_id": None,
}


def _bind_shared_fetch_status():
    """Point notices' placeholder _fetch_status at this shared dict so the
    dashboard reads the same live state that fetch.py mutates."""
    try:
        import routers.notices as notices

        notices._fetch_status = _fetch_status
    except Exception:
        pass


_bind_shared_fetch_status()


def _sync_status_from_job(job_id: int | None):
    """Refresh the in-memory status from the durable job record."""
    if not job_id:
        _fetch_status["running"] = False
        _fetch_status["job_id"] = None
        return
    job = get_job(job_id)
    if not job:
        _fetch_status["running"] = False
        _fetch_status["job_id"] = job_id
        return
    _fetch_status["running"] = job["status"] in ("queued", "running")
    _fetch_status["job_id"] = job_id
    _fetch_status["last_result"] = {
        "success": job["status"] == "completed",
        "exit_code": 0 if job["status"] == "completed" else -1,
        "stdout": job.get("progress") or "",
        "stderr": job.get("error") or "",
        "status": job["status"],
    }
    if job["created_at"]:
        _fetch_status["last_triggered"] = str(job["created_at"])
    if job["finished_at"]:
        _fetch_status["last_finished"] = str(job["finished_at"])


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/", dependencies=[Depends(rate_limited(STRICT_LIMITER))])
def trigger_fetch(
    _: dict = Depends(require_auth),
):
    """Trigger a full fetch via the durable job queue."""
    job_id = enqueue_job("full_fetch", {"scope": "all"})
    _sync_status_from_job(job_id)
    return {"status": "queued", "job_id": job_id, "message": "Fetch enqueued"}


@router.get("/status")
def get_fetch_status():
    _sync_status_from_job(_fetch_status["job_id"])
    return _fetch_status


@router.get("/jobs")
def get_jobs(limit: int = Query(50), status: str | None = Query(None)):
    return list_jobs(limit=limit, status=status)


@router.get("/countries")
def get_country_fetch_status():
    from routers.notices import get_country_fetch_status_rows

    return get_country_fetch_status_rows()


@router.post("/backfill/{name}", dependencies=[Depends(rate_limited(STRICT_LIMITER))])
def trigger_country_backfill(
    name: str,
    since: date | None = Query(None),
    with_bidders: bool = Query(True),
    _: dict = Depends(require_auth),
):
    ensure_support_tables()
    country_rows = q("SELECT name FROM target_countries WHERE name = %s", [name])
    if not country_rows:
        raise HTTPException(404, f"{name} is not in target_countries")
    job_id = enqueue_job(
        "country_backfill",
        {
            "name": name,
            "since": str(since) if since else None,
            "with_bidders": with_bidders,
        },
    )
    _sync_status_from_job(job_id)
    return {"status": "queued", "job_id": job_id, "message": f"{name} backfill enqueued"}


@router.post("/backfill_all", dependencies=[Depends(rate_limited(STRICT_LIMITER))])
def trigger_full_backfill(
    since: date | None = Query(None),
    with_bidders: bool = Query(True),
    _: dict = Depends(require_auth),
):
    """Backfill all countries from baseline then import bidders and sync alerts."""
    ensure_support_tables()
    job_id = enqueue_job(
        "full_fetch",
        {
            "since": str(since) if since else None,
            "with_bidders": with_bidders,
        },
    )
    _sync_status_from_job(job_id)
    return {"status": "queued", "job_id": job_id, "message": "Full backfill enqueued"}


# ── Backwards-compatible legacy jobs table (fetch_runs) ───────────────────────


@router.get("/runs")
def get_runs(limit: int = Query(50)):
    rows = q("SELECT * FROM fetch_runs ORDER BY run_at DESC LIMIT %s", [limit])
    return [dict(r) for r in rows]
