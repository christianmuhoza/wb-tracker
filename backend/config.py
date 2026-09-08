"""Centralized configuration — reads all settings from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────────
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_NAME: str = os.getenv("DB_NAME", "wb_tracker")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
# Keep this optional. When the individual DB_* values are used, psycopg2 must
# receive them separately so special characters in DB_PASSWORD need no URL
# encoding. DATABASE_URL is used only when an explicit DSN is supplied.
DATABASE_URL: str | None = os.getenv("DATABASE_URL") or None

# ── Connection pool ───────────────────────────────────────────────────────────
DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", "1"))
DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", "10"))


# ── CORS ──────────────────────────────────────────────────────────────────────
def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:80",
            "http://localhost:8000",
        ]
    return [o.strip() for o in raw.split(",") if o.strip()]


CORS_ORIGINS: list[str] = _parse_cors_origins()

# ── Auth ──────────────────────────────────────────────────────────────────────
APP_ENV: str = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION: bool = APP_ENV in {"production", "prod"}
JWT_SECRET: str = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD_HASH: str = os.getenv("ADMIN_PASSWORD_HASH", "")


def validate_runtime_configuration() -> None:
    """Fail fast rather than running with an insecure JWT secret in production.

    Login credentials are stored (bcrypt-hashed) in the `users` table and are
    managed through the API. ADMIN_USERNAME / ADMIN_PASSWORD_HASH env vars are
    only a one-time bootstrap to seed the first user and are NOT required here.
    JWT_SECRET is the token signing key and must always be set.
    """
    if not IS_PRODUCTION:
        return
    if not JWT_SECRET:
        raise RuntimeError("Missing required production configuration: JWT_SECRET")
    if len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters in production")


# ── Fetcher ───────────────────────────────────────────────────────────────────
DEFAULT_COUNTRIES: list[str] = [
    "Zambia",
    "Sierra Leone",
    "Ethiopia",
    "Malawi",
    "Kenya",
    "Ghana",
    "Angola",
    "Central African Republic",
    "Guinea",
    "Gambia",
    "Botswana",
    "Benin",
    "Somalia, Federal Republic of",
    "Tanzania",
    "Mozambique",
    "Rwanda",
]

# ── API keys (external services) ──────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
