"""Durable job execution — persisted jobs table + worker loop.

Replaces the fragile in-process threading model. Jobs are recorded in
`fetch_jobs` and executed by a background worker. This gives us:
  - visibility into job status via the API / queue
  - crash resilience (jobs can be retried after restart)
  - a proper place to run award-alert sync, bidder imports, etc.
"""

import hashlib
import json
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


def job_idempotency_key(job_type: str, payload: dict | None = None) -> str:
    canonical_payload = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{job_type}:{canonical_payload}".encode()).hexdigest()


def enqueue_job(job_type: str, payload: dict | None = None) -> int:
    """Insert a job into the queue and return its id."""
    ensure_jobs_table()
    with db() as conn:
        with conn.cursor() as cur:
            idempotency_key = job_idempotency_key(job_type, payload)
            cur.execute(
                """
                INSERT INTO fetch_jobs (job_type, payload, max_attempts, idempotency_key)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (job_type, json.dumps(payload or {}), DEFAULT_MAX_ATTEMPTS, idempotency_key),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    """
                    SELECT id
                    FROM fetch_jobs
                    WHERE idempotency_key = %s
                      AND status IN ('queued', 'running')
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (idempotency_key,),
                )
                row = cur.fetchone()
            if row is None:
                raise RuntimeError("Unable to create or locate the requested ingestion job")
            job_id = row["id"]
        conn.commit()
    log.info(
        "Enqueued or reused job", extra={"job_type": job_type, "job_id": job_id, "idempotency_key": idempotency_key}
    )
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


def job_summary() -> dict:
    rows = q(
        """
        SELECT status, COUNT(*) AS count
        FROM fetch_jobs
        GROUP BY status
        """
    )
    counts = {status: 0 for status in JOB_STATES}
    for row in rows:
        counts[row["status"]] = int(row["count"])
    retry_row = q(
        """
        SELECT COUNT(*) AS count
        FROM fetch_jobs
        WHERE status = 'queued' AND next_attempt_at IS NOT NULL
        """
    )[0]
    stale_row = q(
        """
        SELECT COUNT(*) AS count
        FROM fetch_jobs
        WHERE status = 'running'
          AND COALESCE(locked_at, updated_at) < NOW() - INTERVAL '6 hours'
        """
    )[0]
    return {
        "counts": counts,
        "retry_waiting": int(retry_row["count"]),
        "stale_running": int(stale_row["count"]),
    }


def retry_job(job_id: int) -> dict | None:
    rows = q(
        """
        UPDATE fetch_jobs
        SET status = 'queued',
            next_attempt_at = NOW(),
            finished_at = NULL,
            locked_at = NULL,
            error = NULL,
            progress = 'Manually queued for retry',
            progress_data = jsonb_build_object('stage', 'queued', 'message', 'Manually queued for retry'),
            heartbeat_at = NULL,
            updated_at = NOW()
        WHERE id = %s AND status IN ('failed', 'cancelled')
        RETURNING *
        """,
        [job_id],
    )
    return dict(rows[0]) if rows else None


def cancel_job(job_id: int) -> dict | None:
    rows = q(
        """
        UPDATE fetch_jobs
        SET status = 'cancelled',
            finished_at = NOW(),
            locked_at = NULL,
            updated_at = NOW()
        WHERE id = %s AND status IN ('queued', 'running')
        RETURNING *
        """,
        [job_id],
    )
    return dict(rows[0]) if rows else None


def update_job_progress(job_id: int, **progress):
    """Persist structured progress and renew the worker lease."""
    message = progress.get("message") or progress.get("stage") or "Working"
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE fetch_jobs
                SET progress = %s,
                    progress_data = %s::jsonb,
                    heartbeat_at = NOW(),
                    locked_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s AND status = 'running'
                """,
                [message, json.dumps(progress), job_id],
            )
        conn.commit()


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
        elif key == "progress_data":
            sets.append("progress_data = %s::jsonb")
            params.append(json.dumps(val))
        elif key == "locked_at":
            sets.append("locked_at = %s")
            params.append(val)
        elif key == "heartbeat_at":
            sets.append("heartbeat_at = %s")
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
                    heartbeat_at = NULL,
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
                progress_data = jsonb_build_object('stage', 'starting', 'message', 'Job claimed'),
                heartbeat_at = NOW(),
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

            result = run_full_fetch(payload, job_id=job_id)
            _set_status(
                job_id,
                "completed",
                finished_at=True,
                locked_at=None,
                heartbeat_at=None,
                progress=result.get("stdout", "Done"),
                progress_data={"stage": "completed", "message": result.get("stdout", "Done")},
            )
        elif job_type == "country_backfill":
            from routers.fetch_utils import run_country_backfill

            result = run_country_backfill(payload, job_id=job_id)
            _set_status(
                job_id,
                "completed",
                finished_at=True,
                locked_at=None,
                heartbeat_at=None,
                progress=result.get("stdout", "Done"),
                progress_data={"stage": "completed", "message": result.get("stdout", "Done")},
            )
        elif job_type == "sync_award_alerts":
            from routers.awards import sync_award_alerts

            result = sync_award_alerts()
            _set_status(
                job_id,
                "completed",
                finished_at=True,
                locked_at=None,
                heartbeat_at=None,
                progress=f"Created {result.get('created', 0)}, updated {result.get('updated', 0)}",
                progress_data={"stage": "completed", "message": "Award alerts synchronized"},
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
                heartbeat_at=None,
                progress=f"Processed {result.get('processed', 0)} notices",
                progress_data={"stage": "completed", "message": "Bidder import completed"},
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
                        heartbeat_at = NULL,
                        error = %s,
                        progress_data = jsonb_build_object('stage', 'failed', 'message', 'Job failed'),
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
