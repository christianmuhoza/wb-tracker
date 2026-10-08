"""JWT authentication with a database-backed user store.

Login credentials live in the `users` table (source of truth). On the very
first run the `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` env vars act as a
one-time bootstrap so an initial admin can be created; afterwards users are
managed through the API and the env vars are not required.
"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt
from config import (
    APP_BASE_URL,
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET,
    PASSWORD_RESET_EXPIRE_MINUTES,
    email_configured,
)
from db import ensure_support_tables, q
from email_service import send_email
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from ratelimit import AUTH_LIMITER, rate_limited

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# ── Token helpers ─────────────────────────────────────────────────────────────


def create_access_token(data: dict) -> str:
    now = datetime.now(UTC)
    payload = {
        **data,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": now.timestamp(),
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
    email = os.getenv("ADMIN_EMAIL", "").strip().lower() or None
    if username and password_hash:
        q(
            "INSERT INTO users (username, password_hash, is_admin, email) "
            "VALUES (%s, %s, TRUE, %s)",
            (username, password_hash, email),
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


# ── Password reset helpers ────────────────────────────────────────────────────


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_password_reset_token(
    username: str,
    issued_by: str | None = None,
    invalidate_previous: bool = True,
) -> tuple[str, datetime]:
    """Create a single-use reset token for the user.

    Any previously issued but unused tokens for the same user are invalidated
    so only the most recent link works. Returns (raw_token, expires_at)."""
    if invalidate_previous:
        q(
            "UPDATE password_reset_tokens SET used_at = NOW() "
            "WHERE username = %s AND used_at IS NULL",
            [username],
        )
    q("DELETE FROM password_reset_tokens WHERE expires_at < NOW() - INTERVAL '7 days'")
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)
    q(
        "INSERT INTO password_reset_tokens (username, token_hash, expires_at, issued_by) "
        "VALUES (%s, %s, %s, %s)",
        (username, _hash_reset_token(token), expires_at, issued_by),
    )
    return token, expires_at


def build_reset_url(token: str) -> str:
    return f"{APP_BASE_URL}/reset-password?token={token}"


def send_reset_email(email: str, username: str, token: str) -> bool:
    reset_url = build_reset_url(token)
    minutes = PASSWORD_RESET_EXPIRE_MINUTES
    text = (
        f"Hello {username},\n\n"
        "A password reset was requested for your WB Procurement Tracker account.\n\n"
        f"Open this link to choose a new password (valid for {minutes} minutes):\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can safely ignore this email — "
        "your password has not changed.\n"
    )
    html = (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:480px;margin:0 auto;">'
        '<img src="cid:logo" alt="WB Tracker" width="56" height="56" '
        'style="display:block;margin-bottom:16px;border-radius:12px;">'
        f"<p>Hello {username},</p>"
        f"<p>A password reset was requested for your WB Procurement Tracker account.</p>"
        f'<p><a href="{reset_url}">Click here to choose a new password</a> '
        f"(valid for {minutes} minutes).</p>"
        "<p>If you did not request this, you can safely ignore this email — "
        "your password has not changed.</p>"
        "</div>"
    )
    return send_email(email, "Reset your WB Tracker password", text, html)


def find_user_by_username_or_email(identifier: str) -> dict | None:
    rows = q(
        "SELECT * FROM users WHERE username = %s OR (email IS NOT NULL AND lower(email) = lower(%s))",
        [identifier, identifier],
    )
    return rows[0] if rows else None


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
    email: str | None = None


class UserUpdate(BaseModel):
    password: str | None = None
    is_active: bool | None = None
    role: Literal["viewer", "operator", "admin"] | None = None
    email: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    identifier: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class AdminResetTokenRequest(BaseModel):
    send_email: bool = False


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse, dependencies=[Depends(rate_limited(AUTH_LIMITER))])
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
    user = get_user_by_username(payload.get("sub", ""))
    return {
        "username": payload.get("sub"),
        "role": ("admin" if user and user.get("is_admin") else user.get("role", "viewer")) if user else "viewer",
        "authenticated": True,
    }


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
    changed_at = user.get("password_changed_at")
    if changed_at is not None:
        issued_at = datetime.fromtimestamp(payload.get("iat", 0), UTC)
        if issued_at <= changed_at:
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
    rows = q(
        "SELECT id, username, email, is_active, is_admin, role, created_at, updated_at "
        "FROM users ORDER BY id"
    )
    return [dict(r) for r in rows]


@router.post("/users", status_code=201)
def create_user(body: UserCreate, _: dict = Depends(require_admin)):
    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    email = (body.email or "").strip().lower() or None
    if email and "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    _ensure_users_table()
    try:
        q(
            "INSERT INTO users (username, password_hash, is_admin, role, email) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (username, hash_password(body.password), body.role == "admin", body.role, email),
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
    if body.email is not None:
        email = (body.email or "").strip().lower() or None
        if email and "@" not in email:
            raise HTTPException(status_code=400, detail="Invalid email address")
        try:
            q(
                "UPDATE users SET email = %s, updated_at = NOW() WHERE username = %s",
                [email, username],
            )
        except Exception:
            raise HTTPException(status_code=409, detail="Email is already in use") from None
    if body.password:
        q(
            "UPDATE users SET password_hash = %s, password_changed_at = NOW(), updated_at = NOW() "
            "WHERE username = %s",
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
        "UPDATE users SET password_hash = %s, password_changed_at = NOW(), updated_at = NOW() "
        "WHERE username = %s",
        (hash_password(body.new_password), username),
    )
    return {"message": "Password updated"}


# ── Password reset (public) ───────────────────────────────────────────────────


@router.post("/forgot-password", dependencies=[Depends(rate_limited(AUTH_LIMITER))])
def forgot_password(body: ForgotPasswordRequest):
    identifier = body.identifier.strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="Username or email is required")
    user = find_user_by_username_or_email(identifier)
    if user and user.get("is_active", False) and user.get("email") and email_configured():
        token, _ = issue_password_reset_token(user["username"], invalidate_previous=False)
        emailed = send_reset_email(user["email"], user["username"], token)
        if emailed:
            q(
                "UPDATE password_reset_tokens SET used_at = NOW() "
                "WHERE username = %s AND used_at IS NULL AND token_hash <> %s",
                (user["username"], _hash_reset_token(token)),
            )
            log.info("Password reset link emailed to %s", user["username"])
        else:
            q(
                "UPDATE password_reset_tokens SET used_at = NOW() "
                "WHERE token_hash = %s AND used_at IS NULL",
                [_hash_reset_token(token)],
            )
            log.warning("Reset link for %s not delivered", user["username"])
    else:
        # Generic response regardless of whether the account exists, to avoid
        # user enumeration. When an account has no email, only an admin can
        # issue a reset link.
        log.info("Forgot-password request for identifier (no email sent)")
    return {
        "message": (
            "If an account matches and email delivery is enabled, a reset link will be sent. "
            "Check your inbox."
        )
    }


@router.post("/reset-password", dependencies=[Depends(rate_limited(AUTH_LIMITER))])
def reset_password(body: ResetPasswordRequest):
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    rows = q(
        "SELECT t.id, t.username, t.expires_at, t.used_at, u.is_active "
        "FROM password_reset_tokens t JOIN users u ON u.username = t.username "
        "WHERE t.token_hash = %s",
        [_hash_reset_token(body.token)],
    )
    if not rows:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    row = rows[0]
    expires_at = row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        row.get("used_at") is not None
        or expires_at <= datetime.now(UTC)
        or not row.get("is_active", True)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    q(
        "UPDATE users SET password_hash = %s, password_changed_at = NOW(), updated_at = NOW() "
        "WHERE username = %s AND is_active = TRUE",
        (hash_password(body.new_password), row["username"]),
    )
    q(
        "UPDATE password_reset_tokens SET used_at = NOW() "
        "WHERE username = %s AND used_at IS NULL",
        [row["username"]],
    )
    log.info("Password reset completed for %s", row["username"])
    return {"message": "Password has been reset. You can now sign in."}


@router.get("/reset-password/verify", dependencies=[Depends(rate_limited(AUTH_LIMITER))])
def verify_reset_token(token: str):
    rows = q(
        "SELECT t.expires_at, t.used_at, u.is_active FROM password_reset_tokens t "
        "JOIN users u ON u.username = t.username WHERE t.token_hash = %s",
        [_hash_reset_token(token)],
    )
    if not rows:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    row = rows[0]
    expires_at = row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if row.get("used_at") is not None or expires_at <= datetime.now(UTC) or not row.get("is_active", True):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    return {"valid": True}


# ── Password reset (admin fallback) ───────────────────────────────────────────


@router.post("/users/{username}/reset-token")
def admin_issue_reset_token(
    username: str,
    body: AdminResetTokenRequest | None = None,
    payload: dict = Depends(require_admin),
):
    """Generate a reset link an admin can share manually, optionally emailing it."""
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token, expires_at = issue_password_reset_token(username, issued_by=payload.get("sub"))
    emailed = False
    if body and body.send_email and user.get("email"):
        emailed = send_reset_email(user["email"], username, token)
    return {
        "token": token,
        "reset_url": build_reset_url(token),
        "expires_at": expires_at.isoformat(),
        "emailed": emailed,
        "email": user.get("email"),
    }
