"""Durable job execution — persisted jobs table + worker loop.

Replaces the fragile in-process threading model. Jobs are recorded in
`fetch_jobs` and executed by a background worker. This gives us:
  - visibility into job status via the API / queue
  - crash resilience (jobs can be retried after restart)
  - a proper place to run award-alert sync, bidder imports, etc.
"""

import logging
import threading
import time
import traceback
from datetime import datetime, timedelta

from db import db, ensure_support_tables, q

log = logging.getLogger(__name__)

JOB_TYPES = ("full_fetch", "country_backfill", "sync_award_alerts", "import_bidders")
JOB_STATES = ("queued", "running", "completed", "failed", "cancelled")
DEFAULT_MAX_ATTEMPTS = 3
STALE_JOB_TIMEOUT = timedelta(hours=6)
MAX_RETRY_DELAY = timedelta(hours=1)


def ensure_jobs_table():
    ensure_support_tables()


def enqueue_job(job_type: str, payload: dict | None = None) -> int:
    """Insert a job into the queue and return its id."""
    ensure_jobs_table()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fetch_jobs (job_type, payload, max_attempts)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (job_type, __import__("json").dumps(payload or {}), DEFAULT_MAX_ATTEMPTS),
            )
            row = cur.fetchone()
            job_id = row["id"]
        conn.commit()
    log.info("Enqueued %s job #%s", job_type, job_id)
    return job_id


def get_job(job_id: int) -> dict | None:
    try:
        rows = q("SELECT * FROM fetch_jobs WHERE id = %s", [job_id])
    except Exception:
        return None
    return dict(rows[0]) if rows else None


def list_jobs(limit: int = 50, status: str | None = None) -> list[dict]:
    if status:
        rows = q(
            "SELECT * FROM fetch_jobs WHERE status = %s ORDER BY created_at DESC LIMIT %s",
            [status, limit],
        )
    else:
        rows = q("SELECT * FROM fetch_jobs ORDER BY created_at DESC LIMIT %s", [limit])
    return [dict(r) for r in rows]


def _set_status(job_id: int, status: str, **fields):
    sets = ["status = %s", "updated_at = NOW()"]
    params: list = [status]
    for key, val in fields.items():
        if key == "started_at" and val is True:
            sets.append("started_at = COALESCE(started_at, NOW())")
        elif key == "finished_at" and val is True:
            sets.append("finished_at = NOW()")
        elif key in ("progress", "error"):
            sets.append(f"{key} = %s")
            params.append(val)
        elif key == "locked_at":
            sets.append("locked_at = %s")
            params.append(val)
    params.append(job_id)
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE fetch_jobs SET {', '.join(sets)} WHERE id = %s", params)
        conn.commit()


def retry_delay(attempt_count: int) -> timedelta:
    """Return a bounded delay before the next attempt."""
    delay = timedelta(minutes=2 ** max(0, attempt_count - 1))
    return min(delay, MAX_RETRY_DELAY)


def recover_stale_jobs(now: datetime | None = None) -> int:
    """Requeue or fail jobs whose worker lease expired."""
    now = now or datetime.now().astimezone()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE fetch_jobs
                SET status = CASE WHEN attempt_count < max_attempts THEN 'queued' ELSE 'failed' END,
                    next_attempt_at = CASE
                        WHEN attempt_count < max_attempts
                        THEN NOW() + LEAST(3600, 60 * POWER(2, GREATEST(attempt_count - 1, 0))) * INTERVAL '1 second'
                        ELSE NULL
                    END,
                    finished_at = CASE WHEN attempt_count < max_attempts THEN NULL ELSE NOW() END,
                    locked_at = NULL,
                    error = CASE
                        WHEN attempt_count < max_attempts THEN 'Worker lease expired; job scheduled for retry.'
                        ELSE 'Worker lease expired after maximum attempts.'
                    END,
                    updated_at = NOW()
                WHERE status = 'running'
                  AND COALESCE(locked_at, updated_at) < %s
                """,
                [now - STALE_JOB_TIMEOUT],
            )
            recovered = cur.rowcount
        conn.commit()
    if recovered:
        log.warning("Recovered %s stale job(s)", recovered)
    return recovered


def claim_next_job() -> dict | None:
    """Atomically claim one queued job so concurrent workers cannot duplicate it."""
    recover_stale_jobs()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                WITH next_job AS (
                    SELECT id FROM fetch_jobs
                    WHERE status = 'queued'
                      AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE fetch_jobs AS job
                SET status = 'running',
                    started_at = COALESCE(job.started_at, NOW()),
                locked_at = NOW(),
                attempt_count = job.attempt_count + 1,
                next_attempt_at = NULL,
                    progress = 'Starting',
                    updated_at = NOW()
                FROM next_job
                WHERE job.id = next_job.id
                RETURNING job.id, job.job_type, job.payload, job.attempt_count, job.max_attempts
            """)
            row = cur.fetchone()
        conn.commit()
    return dict(row) if row else None


def _run_job(job_id: int, job_type: str, payload: dict):
    try:
        if job_type == "full_fetch":
            from routers.fetch_utils import run_full_fetch

            result = run_full_fetch(payload)
            _set_status(job_id, "completed", finished_at=True, locked_at=None, progress=result.get("stdout", "Done"))
        elif job_type == "country_backfill":
            from routers.fetch_utils import run_country_backfill

            result = run_country_backfill(payload)
            _set_status(job_id, "completed", finished_at=True, locked_at=None, progress=result.get("stdout", "Done"))
        elif job_type == "sync_award_alerts":
            from routers.awards import sync_award_alerts

            result = sync_award_alerts()
            _set_status(
                job_id,
                "completed",
                finished_at=True,
                locked_at=None,
                progress=f"Created {result.get('created', 0)}, updated {result.get('updated', 0)}",
            )
        elif job_type == "import_bidders":
            from routers.bidders import import_bidders_by_country, import_missing_awards

            country = payload.get("country")
            if country:
                result = import_bidders_by_country(country=country, fetch_detail=payload.get("fetch_detail", False))
            else:
                result = import_missing_awards(fetch_detail=payload.get("fetch_detail", False))
            _set_status(
                job_id,
                "completed",
                finished_at=True,
                locked_at=None,
                progress=f"Processed {result.get('processed', 0)} notices",
            )
        else:
            raise ValueError(f"Unknown job type: {job_type}")
    except Exception:
        log.exception("Job #%s (%s) failed", job_id, job_type)
        error = traceback.format_exc()[:2000]
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE fetch_jobs
                    SET status = CASE WHEN attempt_count < max_attempts THEN 'queued' ELSE 'failed' END,
                        next_attempt_at = CASE
                            WHEN attempt_count < max_attempts
                            THEN NOW() + LEAST(3600, 60 * POWER(2, GREATEST(attempt_count - 1, 0))) * INTERVAL '1 second'
                            ELSE NULL
                        END,
                        finished_at = CASE WHEN attempt_count < max_attempts THEN NULL ELSE NOW() END,
                        locked_at = NULL,
                        error = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING status, attempt_count, max_attempts
                    """,
                    [error, job_id],
                )
                failure = cur.fetchone()
            conn.commit()
        if failure and failure["status"] == "queued":
            log.warning(
                "Job #%s scheduled for retry (%s/%s)",
                job_id,
                failure["attempt_count"],
                failure["max_attempts"],
            )
    finally:
        log.info("Job #%s (%s) finished", job_id, job_type)


def worker_loop(stop_event: threading.Event):
    """Background worker that picks up queued jobs."""
    ensure_jobs_table()
    log.info("Job worker started")
    while not stop_event.is_set():
        try:
            job = claim_next_job()
            if job:
                _run_job(job["id"], job["job_type"], json_loads(job["payload"]))
            else:
                time.sleep(5)
        except Exception:
            log.exception("Worker loop error")
            time.sleep(10)
    log.info("Job worker stopped")


def json_loads(raw):
    import json

    if isinstance(raw, dict | list):
        return raw
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}


# ── Scheduler (auto-sync) ─────────────────────────────────────────────────────
# Reads `auto_sync_hour` from app_settings each cycle so the UI setting actually
# takes effect. Docker/Render run a dedicated worker; this scheduler is used
# when running the backend as a single process.


def scheduler_loop(stop_event: threading.Event):
    """Checks app_settings.auto_sync_hour every 60s and enqueues a full_fetch
    once per day at that hour."""
    last_run_date = None
    while not stop_event.is_set():
        try:
            settings = q("SELECT value FROM app_settings WHERE key = 'auto_sync_hour'")
            sync_hour = settings[0]["value"] if settings else "06:00"
            try:
                hh, mm = map(int, sync_hour.split(":"))
            except Exception:
                hh, mm = 6, 0
            now = datetime.now()
            today = now.date()
            if now.hour == hh and now.minute >= mm and last_run_date != today:
                log.info("Auto-sync triggered at %s", sync_hour)
                try:
                    enqueue_job("full_fetch", {"scope": "all"})
                except Exception:
                    log.exception("Failed to enqueue auto-sync")
                last_run_date = today
        except Exception:
            log.exception("Scheduler loop error")
        stop_event.wait(60)
    log.info("Scheduler stopped")
