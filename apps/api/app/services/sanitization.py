from __future__ import annotations

import html
import re

SCRIPT_RE = re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
INSTRUCTION_RE = re.compile(
    (
        r"\b(ignore previous instructions|reveal system prompt|exfiltrate|jailbreak|"
        r"developer message)\b"
    ),
    re.IGNORECASE,
)


def sanitize_untrusted_text(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    cleaned = html.unescape(text)

    if SCRIPT_RE.search(cleaned) or TAG_RE.search(cleaned):
        warnings.append("HTML content was stripped from source text.")
        cleaned = SCRIPT_RE.sub(" ", cleaned)
        cleaned = TAG_RE.sub(" ", cleaned)

    if INSTRUCTION_RE.search(cleaned):
        warnings.append("Instruction-like source text was removed before analysis.")
        cleaned = INSTRUCTION_RE.sub(" ", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, warnings
