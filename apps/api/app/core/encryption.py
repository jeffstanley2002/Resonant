from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import settings

ENCRYPTION_VERSION = "fernet-v1"


def encryption_configured() -> bool:
    return bool(settings.app_encryption_key.strip())


def validate_encryption_key(value: str) -> bool:
    if not value.strip():
        return False
    try:
        _fernet_for_key(value.strip())
    except (TypeError, ValueError):
        return False
    return True


def encrypt_json(value: dict[str, Any]) -> str:
    key = settings.app_encryption_key.strip()
    if not key:
        raise ValueError("APP_ENCRYPTION_KEY is required for app-layer encryption")
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _fernet_for_key(key).encrypt(payload).decode("utf-8")


def decrypt_json(token: str) -> dict[str, Any]:
    key = settings.app_encryption_key.strip()
    if not key:
        raise ValueError("APP_ENCRYPTION_KEY is required for app-layer decryption")
    payload = _fernet_for_key(key).decrypt(token.encode("utf-8"))
    decoded = json.loads(payload.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Encrypted payload must decode to an object")
    return decoded


@lru_cache(maxsize=4)
def _fernet_for_key(key: str) -> Fernet:
    return Fernet(key.encode("utf-8"))
