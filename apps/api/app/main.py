from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import account, agent, feedback, health, resumes, saved_jobs, session
from app.core.bot_protection import verify_bot_protection
from app.core.config import settings
from app.core.encryption import validate_encryption_key
from app.core.rate_limit import rate_limiter
from app.services.model_router import warm_model_client


def production_configuration_errors() -> list[str]:
    if not settings.is_production:
        return []

    errors: list[str] = []
    if settings.demo_auth:
        errors.append("DEMO_AUTH must be false")
    if not settings.supabase_url or not settings.supabase_anon_key:
        errors.append("Supabase auth configuration is required")
    if not settings.supabase_service_role_key:
        errors.append("SUPABASE_SERVICE_ROLE_KEY is required")
    if not validate_encryption_key(settings.app_encryption_key):
        errors.append("a valid APP_ENCRYPTION_KEY is required")
    if not settings.allowed_origins or "*" in settings.allowed_origins:
        errors.append("explicit ALLOWED_ORIGINS are required")
    return errors


@asynccontextmanager
async def lifespan(_app: FastAPI):
    errors = production_configuration_errors()
    if errors:
        raise RuntimeError(f"Unsafe production configuration: {'; '.join(errors)}")
    # Warm in the background so the port still binds immediately for the health check.
    warmup = asyncio.create_task(warm_model_client())
    try:
        yield
    finally:
        warmup.cancel()


app = FastAPI(
    title="Resonant API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["DELETE", "GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Turnstile-Token"],
)


@app.middleware("http")
async def security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; object-src 'none'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'"
    )
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
    response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - start) * 1000:.1f}"
    return response


@app.middleware("http")
async def basic_rate_limit(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    key = (
        request.headers.get("authorization") or request.client.host if request.client else "unknown"
    )
    if request.url.path in {"/resumes/analyze", "/agent/matches"}:
        await verify_bot_protection(request)
        rate_limiter.check(key=key, limit=settings.daily_match_limit, window_seconds=24 * 60 * 60)
    return await call_next(request)


app.include_router(health.router)
app.include_router(account.router)
app.include_router(resumes.router)
app.include_router(agent.router)
app.include_router(feedback.router)
app.include_router(saved_jobs.router)
app.include_router(session.router)
