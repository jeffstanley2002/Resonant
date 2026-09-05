from __future__ import annotations

import base64

import pytest
from app.core.config import settings
from app.main import app, production_configuration_errors
from fastapi.testclient import TestClient

TEST_FERNET_KEY = base64.urlsafe_b64encode(b"0" * 32).decode("utf-8")


def test_production_runtime_configuration_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "demo_auth", True)
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_anon_key", "")
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    monkeypatch.setattr(settings, "app_encryption_key", "")

    errors = production_configuration_errors()

    assert "DEMO_AUTH must be false" in errors
    assert "Supabase auth configuration is required" in errors
    assert "a valid APP_ENCRYPTION_KEY is required" in errors


def test_production_runtime_configuration_accepts_secure_values(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "demo_auth", False)
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "public")
    monkeypatch.setattr(settings, "supabase_service_role_key", "private")
    monkeypatch.setattr(settings, "app_encryption_key", TEST_FERNET_KEY)
    monkeypatch.setattr(settings, "allowed_origins_raw", "https://resonant.example")

    assert production_configuration_errors() == []


def test_application_refuses_to_start_with_unsafe_production_config(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "demo_auth", True)

    with pytest.raises(RuntimeError, match="Unsafe production configuration"), TestClient(app):
        pass
