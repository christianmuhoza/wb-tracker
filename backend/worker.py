"""Dedicated background worker process.

Runs the durable job worker (processes queued `fetch_jobs`) and the auto-sync
scheduler (reads `app_settings.auto_sync_hour` from DB). Deployed as a separate
Render background worker / Docker service so jobs survive web-instance idle
spin-downs on the free tier.

Usage:
    python worker.py [--once]      # --once processes a single queued job then exits
"""

import logging
import sys
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def _run_once():
    """Process a single queued job, then exit (used for cron-style scheduling)."""
    from jobs import _run_job, claim_next_job, json_loads

    job = claim_next_job()
    if job:
        log.info("Processing one job: #%s (%s)", job["id"], job["job_type"])
        _run_job(job["id"], job["job_type"], json_loads(job["payload"]))
    else:
        log.info("No queued jobs to process")


def main():
    from jobs import (
        ensure_jobs_table,
        scheduler_loop,
        worker_loop,
    )

    ensure_jobs_table()
    stop_event = threading.Event()

    if "--once" in sys.argv:
        _run_once()
        return

    worker = threading.Thread(target=worker_loop, args=(stop_event,), daemon=True)
    scheduler = threading.Thread(target=scheduler_loop, args=(stop_event,), daemon=True)
    worker.start()
    scheduler.start()
    log.info("Background worker started (worker + scheduler)")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Shutting down worker")
        stop_event.set()


if __name__ == "__main__":
    main()
