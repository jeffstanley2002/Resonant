from __future__ import annotations

import json
import pathlib
import sys

API_ROOT = pathlib.Path(__file__).resolve().parents[2] / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.services.match_reasoning import MatchReasoningEnvelope
from app.services.sanitization import sanitize_untrusted_text
from app.services.structured_output import json_object_from_text


def call_api(prompt, options, context):
    variables = context.get("vars", {})
    mode = variables.get("mode", "sanitize")
    if mode == "match_reasoning_validation":
        try:
            MatchReasoningEnvelope.model_validate(
                json_object_from_text(variables.get("model_output", ""))
            )
        except (ValueError, TypeError):
            status = "rejected_invalid_model_output"
        else:
            status = "accepted_valid_model_output"
        return {"output": json.dumps({"status": status})}

    cleaned, warnings = sanitize_untrusted_text(variables.get("source_text", ""))
    requested_limit = int(variables.get("requested_limit", 30))
    return {
        "output": json.dumps(
            {
                "sanitized": cleaned,
                "warnings": warnings,
                "effective_limit": min(max(requested_limit, 1), 40),
                "system_prompt": None,
                "secrets": None,
            }
        )
    }
