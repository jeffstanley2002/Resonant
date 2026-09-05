from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("resonant")
logging.basicConfig(level=logging.INFO, format="%(message)s")


SENSITIVE_KEYS = {"resume_text", "description", "token", "api_key", "secret", "password"}


def log_event(event: str, **metadata: Any) -> None:
    safe = {
        key: value
        for key, value in metadata.items()
        if not any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS)
    }
    logger.info(json.dumps({"event": event, **safe}, default=str))
