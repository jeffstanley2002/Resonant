from __future__ import annotations

from functools import lru_cache
from pathlib import Path

try:
    from pydantic import Field, field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:  # pragma: no cover - fallback for minimal test environments
    from pydantic import BaseModel as BaseSettings
    from pydantic import Field

    class SettingsConfigDict(dict):
        pass

    def field_validator(*args, **kwargs):  # type: ignore[no-untyped-def]
        def decorator(func):  # type: ignore[no-untyped-def]
            return func

        return decorator


API_ROOT = Path(__file__).resolve().parents[2]
APPS_ROOT = API_ROOT.parent
REPO_ROOT = APPS_ROOT.parent
ENV_FILES = (
    REPO_ROOT / ".env",
    APPS_ROOT / ".env",
    API_ROOT / ".env",
)


class Settings(BaseSettings):
    app_env: str = "development"
    allowed_origins_raw: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias="ALLOWED_ORIGINS",
    )
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    app_encryption_key: str = ""
    demo_auth: bool = False
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "sg"
    apify_mcf_run_url: str = ""
    apify_api_token: str = ""
    apify_mcf_country: str = "Singapore"
    openai_api_key: str = ""
    groq_api_key: str = ""
    helicone_api_key: str = ""
    turnstile_secret_key: str = ""
    default_job_limit: int = 30
    max_job_limit: int = 40
    max_upload_bytes: int = 5 * 1024 * 1024
    daily_match_limit: int = 20
    model_call_timeout_seconds: float = 24.0
    model_task_budget_seconds: float = 60.0
    cheap_model: str = ""
    strong_model: str = ""
    allow_demo_data: bool = False

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @field_validator("openai_api_key")
    @classmethod
    def normalize_openai_api_key(cls, value: str) -> str:
        value = value.strip()
        return value if value.startswith("sk-") else ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
