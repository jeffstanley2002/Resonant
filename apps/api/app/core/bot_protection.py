from __future__ import annotations

import httpx
from fastapi import HTTPException, Request, status

from app.core.config import settings


async def verify_bot_protection(request: Request) -> None:
    if not settings.turnstile_secret_key:
        return

    token = request.headers.get("x-turnstile-token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot protection token required",
        )

    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": settings.turnstile_secret_key, "response": token},
        )

    if response.status_code != 200 or not response.json().get("success"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bot protection failed")
