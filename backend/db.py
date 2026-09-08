"""Database connection and query helpers with connection pooling."""

import logging
import os
from contextlib import contextmanager

from config import DATABASE_URL, DB_HOST, DB_NAME, DB_PASSWORD, DB_POOL_MAX, DB_POOL_MIN, DB_PORT, DB_USER
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)

_pool: pool.ThreadedConnectionPool | None = None


def _get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        connection_options = (
            {"dsn": DATABASE_URL}
            if DATABASE_URL
            else {
                "host": DB_HOST,
                "port": DB_PORT,
                "dbname": DB_NAME,
                "user": DB_USER,
                "password": DB_PASSWORD,
            }
        )
        _pool = pool.ThreadedConnectionPool(
            DB_POOL_MIN,
            DB_POOL_MAX,
            cursor_factory=RealDictCursor,
            **connection_options,
        )
        log.info("Database connection pool created (min=%d, max=%d)", DB_POOL_MIN, DB_POOL_MAX)
    return _pool


@contextmanager
def db():
    """Yield a pooled psycopg2 connection with RealDictCursor."""
    conn = _get_pool().getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        _get_pool().putconn(conn)


def q(sql, params=None):
    """Convenient query helper — returns list of RealDict rows."""
    with db() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
        conn.commit()
        return rows


def health_check() -> bool:
    """Return True if the database is reachable."""
    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:
        log.exception("Database health check failed")
        return False


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
                    ('baseline_date', (CURRENT_DATE - INTERVAL '2 years')::text),
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            SERIAL PRIMARY KEY,
                    username      TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active     BOOLEAN DEFAULT TRUE,
                    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at    TIMESTAMPTZ DEFAULT NOW(),
                    updated_at    TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("""
                UPDATE users SET is_admin = TRUE
                WHERE id = (SELECT id FROM users ORDER BY id LIMIT 1)
                  AND NOT EXISTS (SELECT 1 FROM users WHERE is_admin)
            """)
            bootstrap_username = os.getenv("ADMIN_USERNAME", "").strip()
            bootstrap_hash = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
            if bootstrap_username and bootstrap_hash:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, is_admin)
                    SELECT %s, %s, TRUE
                    WHERE NOT EXISTS (SELECT 1 FROM users)
                    """,
                    (bootstrap_username, bootstrap_hash),
                )
            cur.execute("""
                CREATE TABLE IF NOT EXISTS target_countries (
                    id              SERIAL PRIMARY KEY,
                    name            TEXT UNIQUE NOT NULL,
                    is_active       BOOLEAN DEFAULT TRUE,
                    query_aliases   TEXT[] DEFAULT '{}',
                    storage_aliases TEXT[] DEFAULT '{}',
                    sync_order      INT DEFAULT 0,
                    added_at        TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE target_countries ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
            cur.execute("ALTER TABLE target_countries ADD COLUMN IF NOT EXISTS query_aliases TEXT[] DEFAULT '{}'")
            cur.execute("ALTER TABLE target_countries ADD COLUMN IF NOT EXISTS storage_aliases TEXT[] DEFAULT '{}'")
            cur.execute("ALTER TABLE target_countries ADD COLUMN IF NOT EXISTS sync_order INT DEFAULT 0")
        conn.commit()
        seed_countries_from_defaults()


def get_app_settings_map():
    ensure_support_tables()
    rows = q("SELECT key, value, updated_at FROM app_settings ORDER BY key")
    settings = {row["key"]: row["value"] for row in rows}
    settings["updated_at"] = max((row["updated_at"] for row in rows), default=None)
    return settings


def seed_countries_from_defaults():
    """Populate the initial country list without replacing user-managed rows."""
    from config import DEFAULT_COUNTRIES

    with db() as conn, conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO target_countries (name, sync_order)
            VALUES (%s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            [(country, index) for index, country in enumerate(DEFAULT_COUNTRIES, 1)],
        )
        conn.commit()
