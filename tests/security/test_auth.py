from __future__ import annotations

import asyncio

import pytest
from app.core.auth import require_cookie_csrf, require_user
from app.core.config import settings
from fastapi import HTTPException


def test_cookie_auth_rejects_missing_csrf_header() -> None:
    with pytest.raises(HTTPException) as exc:
        require_cookie_csrf(csrf_cookie="token", csrf_header=None)

    assert exc.value.status_code == 403


def test_cookie_auth_rejects_mismatched_csrf_token() -> None:
    with pytest.raises(HTTPException) as exc:
        require_cookie_csrf(csrf_cookie="token", csrf_header="other")

    assert exc.value.status_code == 403


def test_cookie_auth_accepts_matching_csrf_token() -> None:
    require_cookie_csrf(csrf_cookie="token", csrf_header="token")


def test_demo_auth_fails_closed_in_production(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "demo_auth", True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            require_user(
                credentials=None,
                session_cookie=None,
                csrf_cookie=None,
                csrf_header=None,
            )
        )

    assert exc.value.status_code == 503
