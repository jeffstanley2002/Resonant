"""Small local secret scanner for committed files.

This is intentionally conservative and dependency-free. It catches common
mistakes before a stronger scanner such as gitleaks is added to CI.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
IGNORED_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".next",
}
IGNORED_FILES = {"tests/security/test_secret_scan.py"}
ALLOWED_ENV_EXAMPLES = {".env.example", ".env.production.example", "apps/web/.env.example"}

PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(
        r"SUPABASE_SERVICE_ROLE_KEY\s*=\s*(?!replace|optional|your-|\.{3}|$).+",
        re.IGNORECASE,
    ),
    re.compile(
        r"APP_ENCRYPTION_KEY\s*=\s*(?!replace|optional|your-|\.{3}|$)[A-Za-z0-9_\-]{43}=",
        re.IGNORECASE,
    ),
    re.compile(r"(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}", re.IGNORECASE),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def should_scan(path: pathlib.Path) -> bool:
    if path.name.startswith(".env") and str(path) not in ALLOWED_ENV_EXAMPLES:
        return False
    return str(path) not in IGNORED_FILES and not any(part in IGNORED_PARTS for part in path.parts)


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path.relative_to(ROOT)):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                findings.append(str(path.relative_to(ROOT)))
                break

    if findings:
        print("Potential secrets found:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("No obvious secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
