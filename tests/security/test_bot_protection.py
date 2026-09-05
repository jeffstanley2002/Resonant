from __future__ import annotations

import asyncio

import pytest
from app.core.bot_protection import verify_bot_protection
from app.core.config import settings
from fastapi import Request
from starlette.datastructures import Headers


def test_bot_protection_noops_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "turnstile_secret_key", "")

    asyncio.run(verify_bot_protection(fake_request(headers={})))


def test_bot_protection_requires_token_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "turnstile_secret_key", "configured")

    with pytest.raises(Exception) as exc:
        asyncio.run(verify_bot_protection(fake_request(headers={})))

    assert "Bot protection token required" in str(exc.value)


def fake_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/agent/matches",
        "headers": Headers(headers).raw,
    }
    return Request(scope)
