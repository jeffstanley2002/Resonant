from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.core.encryption import validate_encryption_key

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "resonant-api"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, bool | str]:
    supabase_configured = bool(
        settings.supabase_url and settings.supabase_anon_key and settings.supabase_service_role_key
    )
    demo_mode_ready = settings.demo_auth and not settings.is_production
    auth_ready = demo_mode_ready or supabase_configured
    encryption_configured = validate_encryption_key(settings.app_encryption_key)
    persistence_ready = demo_mode_ready or encryption_configured
    model_provider_configured = bool(
        settings.openai_api_key
        or settings.groq_api_key
    )
    production_ready = (
        auth_ready
        and persistence_ready
        and (model_provider_configured or not settings.is_production)
        and not (settings.is_production and settings.demo_auth)
    )
    if not production_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if production_ready else "not_ready",
        "environment": settings.app_env,
        "demo_mode": demo_mode_ready,
        "auth_ready": auth_ready,
        "supabase_configured": supabase_configured,
        "app_encryption_configured": encryption_configured,
        "job_api_configured": bool(settings.adzuna_app_id and settings.adzuna_app_key),
        "model_provider_configured": model_provider_configured,
        "monitoring_configured": bool(settings.helicone_api_key),
        "bot_protection_configured": bool(settings.turnstile_secret_key),
    }
