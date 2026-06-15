"""Database connection and query helpers for the WB Tracker backend."""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


@contextmanager
def db():
    """Yield a psycopg2 connection with RealDictCursor."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "wb_tracker"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        cursor_factory=RealDictCursor,
    )
    try:
        yield conn
    finally:
        conn.close()


def q(sql, params=None):
    """Convenient query helper – returns list of RealDict rows."""
    with db() as conn:
        with conn.cursor() as cur:
            if params is not None:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            return cur.fetchall()


def ensure_support_tables():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                INSERT INTO app_settings (key, value)
                VALUES
                    ('baseline_date', '2025-01-01'),
                    ('country_batch', '5'),
                    ('request_delay', '1.2'),
                    ('auto_sync_hour', '06:00')
                ON CONFLICT (key) DO NOTHING
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS country_fetch_status (
                    country              TEXT PRIMARY KEY,
                    status               TEXT NOT NULL DEFAULT 'not_started',
                    last_started_at      TIMESTAMPTZ,
                    last_finished_at     TIMESTAMPTZ,
                    last_success_at      TIMESTAMPTZ,
                    last_attempted_since DATE,
                    last_page_size       INT,
                    fetched_records      INT DEFAULT 0,
                    new_records          INT DEFAULT 0,
                    total_available      INT DEFAULT 0,
                    row_count            INT DEFAULT 0,
                    first_notice_date    DATE,
                    last_notice_date     DATE,
                    error_msg            TEXT,
                    api_url              TEXT,
                    retry_count          INT DEFAULT 0,
                    updated_at           TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        conn.commit()


def get_app_settings_map():
    ensure_support_tables()
    rows = q("SELECT key, value, updated_at FROM app_settings ORDER BY key")
    settings = {row["key"]: row["value"] for row in rows}
    settings["updated_at"] = max((row["updated_at"] for row in rows), default=None)
    return settings
