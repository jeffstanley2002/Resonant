from __future__ import annotations

import pytest
from app.core.config import settings


@pytest.fixture(autouse=True)
def deterministic_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "demo_auth", True)
    monkeypatch.setattr(settings, "adzuna_app_id", "")
    monkeypatch.setattr(settings, "adzuna_app_key", "")
    monkeypatch.setattr(settings, "apify_mcf_run_url", "")
    monkeypatch.setattr(settings, "apify_api_token", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "cheap_model", "")
    monkeypatch.setattr(settings, "strong_model", "")
    monkeypatch.setattr(settings, "allow_demo_data", False)
