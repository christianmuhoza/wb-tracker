import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import UserUpdate, require_operator, update_user


def test_viewer_cannot_use_operator_dependency():
    with pytest.raises(HTTPException) as exc:
        require_operator({"sub": "viewer", "role": "viewer"})

    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["operator", "admin"])
def test_operator_dependency_accepts_operator_and_admin(role):
    assert require_operator({"sub": role, "role": role})["role"] == role


def test_last_active_admin_cannot_be_demoted():
    with (
        patch("auth.get_user_by_username", return_value={"is_admin": True, "is_active": True}),
        patch("auth.q", return_value=[{"count": 1}]),
        pytest.raises(HTTPException) as exc,
    ):
        update_user("admin", UserUpdate(role="viewer"), {})

    assert exc.value.status_code == 400
