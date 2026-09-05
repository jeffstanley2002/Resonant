from __future__ import annotations

import hmac
from dataclasses import dataclass

import httpx
from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None = None
    session_token: str | None = None


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session_cookie: str | None = Cookie(default=None, alias="resonant_session"),
    csrf_cookie: str | None = Cookie(default=None, alias="resonant_csrf"),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AuthUser:
    if settings.demo_auth and settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Production authentication is misconfigured",
        )
    if settings.demo_auth:
        return AuthUser(id="demo-user", email="demo@example.com", session_token="demo-token")

    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif session_cookie:
        require_cookie_csrf(csrf_cookie=csrf_cookie, csrf_header=csrf_header)
        token = session_cookie
    else:
        token = ""

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured",
        )

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.supabase_anon_key,
            },
        )

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")

    payload = response.json()
    return AuthUser(id=payload["id"], email=payload.get("email"), session_token=token)


def require_cookie_csrf(csrf_cookie: str | None, csrf_header: str | None) -> None:
    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token required for cookie authentication",
        )
