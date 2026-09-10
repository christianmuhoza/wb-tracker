"""JWT authentication with a database-backed user store.

Login credentials live in the `users` table (source of truth). On the very
first run the `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` env vars act as a
one-time bootstrap so an initial admin can be created; afterwards users are
managed through the API and the env vars are not required.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt
from config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from db import ensure_support_tables, q
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# ── Token helpers ─────────────────────────────────────────────────────────────


def create_access_token(data: dict) -> str:
    payload = {
        **data,
        "exp": datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


# ── Database user helpers ─────────────────────────────────────────────────────


def _ensure_users_table():
    ensure_support_tables()


def seed_admin_from_env() -> None:
    """One-time bootstrap: if the users table is empty and ADMIN_USERNAME +
    ADMIN_PASSWORD_HASH env vars are present, create that admin. Safe to call
    on every startup — it only acts when there are no users."""
    import os

    _ensure_users_table()
    existing = q("SELECT 1 FROM users LIMIT 1")
    if existing:
        return
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password_hash = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
    if username and password_hash:
        q(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, TRUE)",
            (username, password_hash),
        )
        log.info("Seeded initial admin user '%s' from environment", username)


def get_user_by_username(username: str) -> dict | None:
    rows = q("SELECT * FROM users WHERE username = %s", [username])
    return rows[0] if rows else None


def authenticate(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if not user or not user.get("is_active", False):
        return None
    try:
        if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return None
    except ValueError:
        return None
    return user


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ── Schemas ───────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: Literal["viewer", "operator", "admin"] = "viewer"


class UserUpdate(BaseModel):
    password: str | None = None
    is_active: bool | None = None
    role: Literal["viewer", "operator", "admin"] | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    # Also bootstrap here so the first login works when an older local entry
    # point is used without the main application's lifespan hook.
    seed_admin_from_env()
    user = authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["username"]})
    return LoginResponse(access_token=token, username=user["username"])


@router.get("/me")
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    return {"username": payload.get("sub"), "authenticated": True}


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Dependency that enforces authentication. Returns the JWT payload."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    user = get_user_by_username(payload.get("sub", ""))
    if not user or not user.get("is_active", False):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload["role"] = "admin" if user.get("is_admin") else user.get("role", "viewer")
    return payload


def require_operator(payload: dict = Depends(require_auth)) -> dict:
    """Require an active operator or administrator account."""
    if payload.get("role") not in {"operator", "admin"}:
        raise HTTPException(status_code=403, detail="Operator access required")
    return payload


def require_admin(payload: dict = Depends(require_auth)) -> dict:
    """Require an active administrator account for account management."""
    user = get_user_by_username(payload.get("sub", ""))
    if not user or not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Administrator access required")
    return payload


@router.get("/users")
def list_users(_: dict = Depends(require_admin)):
    rows = q("SELECT id, username, is_active, is_admin, role, created_at, updated_at FROM users ORDER BY id")
    return [dict(r) for r in rows]


@router.post("/users", status_code=201)
def create_user(body: UserCreate, _: dict = Depends(require_admin)):
    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    _ensure_users_table()
    try:
        q(
            "INSERT INTO users (username, password_hash, is_admin, role) VALUES (%s, %s, %s, %s) RETURNING id",
            (username, hash_password(body.password), body.role == "admin", body.role),
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Username already exists") from exc
    return {"username": username, "created": True}


@router.put("/users/{username}")
def update_user(username: str, body: UserUpdate, _: dict = Depends(require_admin)):
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    is_demoting_last_admin = user.get("is_admin", False) and (
        body.role is not None and body.role != "admin" or body.is_active is False
    )
    if is_demoting_last_admin:
        admins = q("SELECT COUNT(*) AS count FROM users WHERE is_admin AND is_active")
        if admins and admins[0]["count"] <= 1:
            raise HTTPException(status_code=400, detail="At least one active administrator is required")
    if body.password:
        q(
            "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE username = %s",
            (hash_password(body.password), username),
        )
    if body.is_active is not None or body.role is not None:
        role = body.role or ("admin" if user.get("is_admin") else user.get("role", "viewer"))
        q(
            "UPDATE users SET is_active = %s, updated_at = NOW() WHERE username = %s",
            [body.is_active if body.is_active is not None else user.get("is_active", True), username],
        )
        if body.role is not None:
            q(
                "UPDATE users SET role = %s, is_admin = %s, updated_at = NOW() WHERE username = %s",
                [role, role == "admin", username],
            )
    return {"username": username, "updated": True}


@router.delete("/users/{username}")
def delete_user(username: str, _: dict = Depends(require_admin)):
    user = get_user_by_username(username)
    if user and user.get("is_admin"):
        admins = q("SELECT COUNT(*) AS count FROM users WHERE is_admin AND is_active")
        if admins and admins[0]["count"] <= 1:
            raise HTTPException(status_code=400, detail="At least one active administrator is required")
    rows = q("DELETE FROM users WHERE username = %s RETURNING username", [username])
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": username, "deleted": True}


@router.put("/change-password")
def change_password(body: ChangePasswordRequest, payload: dict = Depends(require_auth)):
    username = payload.get("sub")
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        ok = bcrypt.checkpw(body.current_password.encode("utf-8"), user["password_hash"].encode("utf-8"))
    except ValueError:
        ok = False
    if not ok:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    q(
        "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE username = %s",
        (hash_password(body.new_password), username),
    )
    return {"message": "Password updated"}
