"""Check repository hygiene before the first GitHub push."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class HygieneFinding:
    level: str
    message: str


MUST_BE_TRACKABLE = [
    ".env.example",
    ".env.production.example",
    "render.yaml",
    "apps/web/vercel.json",
    "supabase/migrations/001_initial_schema.sql",
]

MUST_BE_IGNORED = [
    ".env",
    ".env.local",
    ".env.production.local",
    "node_modules",
    "apps/api/.venv",
    "apps/web/.next",
    "apps/web/test-results",
    ".pytest_cache",
    ".ruff_cache",
]


def main() -> int:
    findings = validate_hygiene()
    for finding in findings:
        print(f"{finding.level}: {finding.message}")
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


def validate_hygiene() -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    for path in MUST_BE_TRACKABLE:
        if is_ignored(path):
            findings.append(HygieneFinding("ERROR", f"{path} must be trackable before deploy"))

    for path in MUST_BE_IGNORED:
        if not is_ignored(path):
            findings.append(HygieneFinding("ERROR", f"{path} must stay ignored"))

    return findings


def is_ignored(path: str) -> bool:
    candidates = [path]
    if not path.endswith("/"):
        candidates.append(f"{path}/")
    root = repository_root()
    return any(_check_ignored(candidate, root) for candidate in candidates)


def _check_ignored(path: str, root: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", path],
        check=False,
        cwd=root,
    )
    return result.returncode == 0


def repository_root() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


if __name__ == "__main__":
    sys.exit(main())
