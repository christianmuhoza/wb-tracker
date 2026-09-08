"""FastAPI entry point for the WB Tracker API."""

import logging
import os
import threading
from contextlib import asynccontextmanager

from auth import router as auth_router
from config import CORS_ORIGINS, validate_runtime_configuration
from db import ensure_support_tables, health_check
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.awards import router as awards_router
from routers.bidders import router as bidders_router
from routers.borrowers import router as borrowers_router
from routers.export import router as export_router
from routers.fetch import router as fetch_router
from routers.notices import router as notices_router
from routers.settings import router as settings_router
from routers.software import router as software_router

log = logging.getLogger(__name__)

# ── Background workers ────────────────────────────────────────────────────────
# The job worker runs fetch/bidder/award jobs from the DB queue. The scheduler
# reads app_settings.auto_sync_hour so the UI setting actually takes effect.
#
# Dedicated deployment: Render/Docker runs `worker.py` as a separate background
# service which owns the worker + scheduler. The web API can be told to run them
# in-process too for single-process local development via ENABLE_IN_PROCESS_WORKER=1.
# Default: RUN the worker in-process for local convenience.

ENABLE_IN_PROCESS_WORKER = os.getenv("ENABLE_IN_PROCESS_WORKER", "1") == "1"

_stop_event = threading.Event()
_worker_thread = None
_scheduler_thread = None


def _start_background_workers():
    global _worker_thread, _scheduler_thread
    if not ENABLE_IN_PROCESS_WORKER:
        return
    try:
        from jobs import ensure_jobs_table, scheduler_loop, worker_loop

        ensure_jobs_table()
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(target=worker_loop, args=(_stop_event,), daemon=True)
            _worker_thread.start()
            log.info("Job worker thread started")
        if _scheduler_thread is None or not _scheduler_thread.is_alive():
            _scheduler_thread = threading.Thread(target=scheduler_loop, args=(_stop_event,), daemon=True)
            _scheduler_thread.start()
            log.info("Scheduler thread started")
    except Exception:
        log.exception("Failed to start background workers")


def _stop_background_workers():
    _stop_event.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime_configuration()
    log.info("WB Tracker API starting — CORS origins: %s", CORS_ORIGINS)
    try:
        ensure_support_tables()
        from auth import seed_admin_from_env
        seed_admin_from_env()
    except Exception:
        log.warning("Could not ensure support tables on startup (DB may be unavailable)")
    _start_background_workers()
    yield
    _stop_background_workers()
    log.info("WB Tracker API shutting down")


app = FastAPI(
    title="WB Procurement Tracker API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(notices_router)
app.include_router(bidders_router)
app.include_router(borrowers_router)
app.include_router(awards_router)
app.include_router(settings_router)
app.include_router(software_router)
app.include_router(fetch_router)
app.include_router(export_router)


@app.get("/health")
def health():
    db_ok = health_check()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "version": app.version,
    }
