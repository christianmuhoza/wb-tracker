"""Database connection and query helpers with connection pooling."""

import logging
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
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


def run_migrations() -> None:
    """Apply versioned database migrations before application services start."""
    alembic_config = Config(str(Path(__file__).with_name("alembic.ini")))
    alembic_config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    command.upgrade(alembic_config, "head")


def ensure_support_tables():
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
