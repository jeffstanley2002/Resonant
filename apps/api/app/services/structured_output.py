from __future__ import annotations

import json
import re
from typing import Any


def json_object_from_text(content: str) -> dict[str, Any]:
    candidate = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    elif not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model output did not contain a JSON object")
        candidate = candidate[start : end + 1]

    decoded = json.loads(candidate)
    if not isinstance(decoded, dict):
        raise ValueError("Model output must be a JSON object")
    return decoded
