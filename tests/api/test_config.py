from __future__ import annotations

from app.core import config
from app.core.config import Settings
from app.schemas import MatchRequest


def test_backend_settings_load_root_shared_and_api_env_files() -> None:
    assert config.ENV_FILES == (
        config.REPO_ROOT / ".env",
        config.APPS_ROOT / ".env",
        config.API_ROOT / ".env",
    )


def test_match_request_defaults_to_singapore_and_thirty_roles() -> None:
    request = MatchRequest(resume_text="Python TypeScript React FastAPI engineering experience")

    assert request.location == "Singapore"
    assert request.limit == 30


def test_model_timeout_defaults_allow_current_provider_latency() -> None:
    settings = Settings(_env_file=None)

    assert settings.model_call_timeout_seconds == 24.0
    assert settings.model_task_budget_seconds == 60.0


def test_openai_api_key_rejects_malformed_prompt_text() -> None:
    settings = Settings(_env_file=None, OPENAI_API_KEY="paste this; sk-example")

    assert settings.openai_api_key == ""
