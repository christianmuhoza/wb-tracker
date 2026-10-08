import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    admin_issue_reset_token,
    forgot_password,
    reset_password,
)


def test_forgot_password_returns_generic_message_for_unknown_user():
    with patch("auth.find_user_by_username_or_email", return_value=None):
        res = forgot_password(ForgotPasswordRequest(identifier="nobody"))

    assert "If an account" in res["message"]


@patch("auth.issue_password_reset_token", return_value=("tok_abc", datetime.now(UTC)))
@patch("auth.send_reset_email", return_value=True)
@patch("auth.email_configured", return_value=True)
def test_forgot_password_emails_link_when_account_has_email(mock_configured, mock_send, mock_issue):
    user = {"username": "alice", "email": "alice@example.com", "is_active": True}
    with patch("auth.find_user_by_username_or_email", return_value=user):
        forgot_password(ForgotPasswordRequest(identifier="alice@example.com"))

    mock_issue.assert_called_once()
    mock_send.assert_called_once_with("alice@example.com", "alice", "tok_abc")


@patch("auth.send_reset_email")
def test_forgot_password_does_not_send_when_no_email_on_file(mock_send):
    user = {"username": "bob", "email": None, "is_active": True}
    with (
        patch("auth.find_user_by_username_or_email", return_value=user),
        patch("auth.email_configured", return_value=True),
    ):
        res = forgot_password(ForgotPasswordRequest(identifier="bob"))

    mock_send.assert_not_called()
    assert "If an account" in res["message"]


def _patch_reset_token_row(used_at=None, expires_at=None):
    expires_at = expires_at or (datetime.now(UTC) + timedelta(minutes=30))
    calls = []

    def fake_q(sql, params=None):
        calls.append(sql)
        if "SELECT" in sql.upper():
            return [{"username": "alice", "expires_at": expires_at, "used_at": used_at}]
        return []

    return patch("auth.q", side_effect=fake_q), calls


def test_reset_password_updates_credentials_and_consumes_token():
    ctx, calls = _patch_reset_token_row()
    with ctx:
        res = reset_password(ResetPasswordRequest(token="valid-token", new_password="newpass123"))

    assert res["message"]
    assert any("UPDATE users SET password_hash" in sql for sql in calls)
    assert any("UPDATE password_reset_tokens SET used_at" in sql for sql in calls)


def test_reset_password_rejects_used_token():
    ctx, _ = _patch_reset_token_row(used_at=datetime.now(UTC))
    with (
        ctx,
        pytest.raises(HTTPException) as exc,
    ):
        reset_password(ResetPasswordRequest(token="used-token", new_password="newpass123"))

    assert exc.value.status_code == 400


def test_reset_password_rejects_expired_token():
    ctx, _ = _patch_reset_token_row(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    with (
        ctx,
        pytest.raises(HTTPException) as exc,
    ):
        reset_password(ResetPasswordRequest(token="expired-token", new_password="newpass123"))

    assert exc.value.status_code == 400


def test_reset_password_rejects_unknown_token():
    def fake_q(sql, params=None):
        if "SELECT" in sql.upper():
            return []
        return []

    with patch("auth.q", side_effect=fake_q), pytest.raises(HTTPException) as exc:
        reset_password(ResetPasswordRequest(token="bad-token", new_password="newpass123"))

    assert exc.value.status_code == 400


def test_admin_issue_reset_token_returns_shareable_link():
    user = {"username": "alice", "email": "alice@example.com"}
    with (
        patch("auth.get_user_by_username", return_value=user),
        patch(
            "auth.issue_password_reset_token",
            return_value=("raw-token", datetime.now(UTC)),
        ),
    ):
        res = admin_issue_reset_token("alice", None, {"sub": "root"})

    assert res["token"] == "raw-token"
    assert "/reset-password?token=raw-token" in res["reset_url"]


def test_admin_issue_reset_token_404_for_missing_user():
    with (
        patch("auth.get_user_by_username", return_value=None),
        pytest.raises(HTTPException) as exc,
    ):
        admin_issue_reset_token("ghost", None, {"sub": "root"})

    assert exc.value.status_code == 404
