from __future__ import annotations

import secrets

from fastapi import APIRouter, Cookie, Depends, Header, Response

from app.core.auth import AuthUser, require_cookie_csrf, require_user
from app.core.config import settings

router = APIRouter(prefix="/session", tags=["session"])


@router.post("")
async def establish_session(
    response: Response,
    user: AuthUser = Depends(require_user),
) -> dict[str, str]:
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="resonant_session",
        value=user.session_token or "",
        httponly=True,
        secure=settings.app_env == "production",
        samesite="none" if settings.app_env == "production" else "lax",
        max_age=60 * 60,
    )
    response.set_cookie(
        key="resonant_csrf",
        value=csrf_token,
        httponly=False,
        secure=settings.app_env == "production",
        samesite="none" if settings.app_env == "production" else "lax",
        max_age=60 * 60,
    )
    return {"status": "established", "user_id": user.id, "csrf_token": csrf_token}


@router.delete("")
async def clear_session(
    response: Response,
    session_cookie: str | None = Cookie(default=None, alias="resonant_session"),
    csrf_cookie: str | None = Cookie(default=None, alias="resonant_csrf"),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict[str, str]:
    if session_cookie:
        require_cookie_csrf(csrf_cookie=csrf_cookie, csrf_header=csrf_header)
    response.delete_cookie(
        key="resonant_session",
        httponly=True,
        secure=settings.app_env == "production",
        samesite="none" if settings.app_env == "production" else "lax",
    )
    response.delete_cookie(
        key="resonant_csrf",
        httponly=False,
        secure=settings.app_env == "production",
        samesite="none" if settings.app_env == "production" else "lax",
    )
    return {"status": "cleared"}
