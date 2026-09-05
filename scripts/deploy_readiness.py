"""Validate deployment configuration before touching Vercel, Render, or Supabase."""

from __future__ import annotations

import argparse
import base64
import binascii
import os
import pathlib
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLACEHOLDER_RE = re.compile(r"(replace|optional|your-project|example\.com)", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    level: str
    message: str


BACKEND_REQUIRED = [
    "APP_ENV",
    "ALLOWED_ORIGINS",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "APP_ENCRYPTION_KEY",
]

FRONTEND_REQUIRED = [
    "NEXT_PUBLIC_API_BASE_URL",
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
]

OPTIONAL_BUT_RECOMMENDED = [
    "ADZUNA_APP_ID",
    "ADZUNA_APP_KEY",
    "APIFY_MCF_RUN_URL",
    "APIFY_API_TOKEN",
    "HELICONE_API_KEY",
    "NEXT_PUBLIC_AMPLITUDE_API_KEY",
]

FRONTEND_FORBIDDEN_PATTERNS = [
    "SUPABASE_SERVICE_ROLE_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "HELICONE_API_KEY",
    "TURNSTILE_SECRET_KEY",
    "APP_ENCRYPTION_KEY",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env-file",
        action="append",
        default=None,
        help="Env file to validate. Repeat to merge files; later files override earlier files.",
    )
    parser.add_argument("--production", action="store_true", help="Require production values")
    args = parser.parse_args()

    env_files = args.env_file or [".env"]
    env = read_env_files([ROOT / env_file for env_file in env_files])
    findings = [
        *validate_required(env, FRONTEND_REQUIRED, "frontend", args.production),
        *validate_required(env, BACKEND_REQUIRED, "backend", args.production),
        *validate_optional(env),
        *validate_origins(env),
        *validate_service_urls(env, args.production),
        *validate_frontend_secret_leakage(),
        *validate_demo_auth(env, args.production),
        *validate_encryption_key(env, args.production),
        *validate_paired_configuration(env, args.production),
        *validate_model_provider(env, args.production),
    ]

    for finding in findings:
        print(f"{finding.level}: {finding.message}")

    has_error = any(finding.level == "ERROR" for finding in findings)
    return 1 if has_error else 0


def read_env(path: pathlib.Path) -> dict[str, str]:
    return read_env_files([path])


def read_env_files(paths: list[pathlib.Path]) -> dict[str, str]:
    env = dict(os.environ)
    for path in paths:
        env.update(read_env_file(path))
    return env


def read_env_file(path: pathlib.Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def validate_required(
    env: dict[str, str],
    keys: list[str],
    surface: str,
    production: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    for key in keys:
        value = env.get(key, "")
        if not value:
            findings.append(Finding("ERROR", f"{surface} missing required {key}"))
        elif production and PLACEHOLDER_RE.search(value):
            findings.append(Finding("ERROR", f"{surface} {key} still looks like a placeholder"))
    return findings


def validate_optional(env: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    for key in OPTIONAL_BUT_RECOMMENDED:
        value = env.get(key, "")
        if not value or PLACEHOLDER_RE.search(value):
            findings.append(
                Finding("WARN", f"{key} is not configured; that integration is unavailable")
            )
    return findings


def configured(env: dict[str, str], key: str) -> bool:
    value = env.get(key, "")
    return bool(value and not PLACEHOLDER_RE.search(value))


def validate_model_provider(env: dict[str, str], production: bool) -> list[Finding]:
    findings = validate_openai_api_key(env, production)
    if not production:
        return findings
    configured_provider = bool(openai_api_key_is_valid(env) or configured(env, "GROQ_API_KEY"))
    if configured_provider:
        return findings
    return [
        *findings,
        Finding("ERROR", "Production requires at least one configured AI model provider"),
    ]


def validate_openai_api_key(env: dict[str, str], production: bool) -> list[Finding]:
    if not configured(env, "OPENAI_API_KEY"):
        return []
    if openai_api_key_is_valid(env):
        return []
    level = "ERROR" if production else "WARN"
    return [Finding(level, "OPENAI_API_KEY must contain only the API key value")]


def openai_api_key_is_valid(env: dict[str, str]) -> bool:
    value = env.get("OPENAI_API_KEY", "").strip()
    return configured(env, "OPENAI_API_KEY") and value.startswith("sk-") and not re.search(
        r"\s", value
    )


def validate_origins(env: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    origins = env.get("ALLOWED_ORIGINS", "")
    api_base = env.get("NEXT_PUBLIC_API_BASE_URL", "")
    if origins and "*" in origins:
        findings.append(Finding("ERROR", "ALLOWED_ORIGINS must not use wildcard origins"))
    if api_base and api_base.startswith("http://") and "localhost" not in api_base:
        findings.append(Finding("ERROR", "Production API base URL must use HTTPS"))
    return findings


def validate_service_urls(env: dict[str, str], production: bool) -> list[Finding]:
    findings: list[Finding] = []
    level = "ERROR" if production else "WARN"

    for key in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_URL"):
        if not configured(env, key):
            continue
        parsed = urlparse(env[key])
        if not parsed.scheme or not parsed.netloc:
            findings.append(Finding(level, f"{key} must be a full Supabase project URL"))
            continue
        if parsed.path not in {"", "/"}:
            findings.append(
                Finding(level, f"{key} must be the project base URL without /rest/v1 or /auth/v1")
            )
        if production and parsed.scheme != "https":
            findings.append(Finding("ERROR", f"{key} must use HTTPS in production"))

    if configured(env, "APIFY_MCF_RUN_URL"):
        parsed = urlparse(env["APIFY_MCF_RUN_URL"])
        valid_apify_url = (
            parsed.scheme == "https"
            and parsed.hostname == "api.apify.com"
            and "/v2/actors/" in parsed.path
            and parsed.path.rstrip("/").endswith(("/runs", "/run-sync-get-dataset-items"))
        )
        if not valid_apify_url:
            findings.append(
                Finding(
                    level,
                    "APIFY_MCF_RUN_URL must be an Apify actor /runs or /run-sync-get-dataset-items URL",
                )
            )

    return findings


def validate_frontend_secret_leakage() -> list[Finding]:
    findings: list[Finding] = []
    frontend_files = [
        path
        for path in (ROOT / "apps/web").rglob("*")
        if path.is_file() and "node_modules" not in path.parts and ".next" not in path.parts
    ]
    for path in frontend_files:
        text = path.read_text(errors="ignore")
        for pattern in FRONTEND_FORBIDDEN_PATTERNS:
            if pattern in text:
                findings.append(
                    Finding(
                        "ERROR",
                        f"backend-only secret name {pattern} appears in frontend file {path}",
                    )
                )
    return findings


def validate_demo_auth(env: dict[str, str], production: bool) -> list[Finding]:
    if production and env.get("DEMO_AUTH", "").lower() == "true":
        return [Finding("ERROR", "DEMO_AUTH must be false in production")]
    return []


def validate_encryption_key(env: dict[str, str], production: bool) -> list[Finding]:
    if not production:
        return []
    value = env.get("APP_ENCRYPTION_KEY", "")
    if not value or PLACEHOLDER_RE.search(value):
        return []
    try:
        decoded = base64.urlsafe_b64decode(value.encode("utf-8"))
    except (binascii.Error, ValueError):
        return [Finding("ERROR", "APP_ENCRYPTION_KEY must be a Fernet-compatible key")]
    if len(decoded) != 32:
        return [Finding("ERROR", "APP_ENCRYPTION_KEY must decode to 32 bytes")]
    return []


def validate_paired_configuration(env: dict[str, str], production: bool) -> list[Finding]:
    findings: list[Finding] = []
    frontend_supabase_url = env.get("NEXT_PUBLIC_SUPABASE_URL", "")
    backend_supabase_url = env.get("SUPABASE_URL", "")
    frontend_anon_key = env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
    backend_anon_key = env.get("SUPABASE_ANON_KEY", "")

    if (
        production
        and configured(env, "NEXT_PUBLIC_SUPABASE_URL")
        and configured(env, "SUPABASE_URL")
        and frontend_supabase_url.rstrip("/") != backend_supabase_url.rstrip("/")
    ):
        findings.append(
            Finding("ERROR", "Frontend and backend Supabase URLs must point to the same project")
        )

    if (
        production
        and configured(env, "NEXT_PUBLIC_SUPABASE_ANON_KEY")
        and configured(env, "SUPABASE_ANON_KEY")
        and frontend_anon_key != backend_anon_key
    ):
        findings.append(Finding("ERROR", "Frontend and backend Supabase anon keys must match"))

    turnstile_site = configured(env, "NEXT_PUBLIC_TURNSTILE_SITE_KEY")
    turnstile_secret = configured(env, "TURNSTILE_SECRET_KEY")
    if turnstile_site != turnstile_secret:
        level = "ERROR" if production else "WARN"
        findings.append(
            Finding(
                level,
                "Turnstile must configure both NEXT_PUBLIC_TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY",
            )
        )

    apify_url = configured(env, "APIFY_MCF_RUN_URL")
    apify_token = configured(env, "APIFY_API_TOKEN")
    if apify_url != apify_token:
        level = "ERROR" if production else "WARN"
        findings.append(
            Finding(
                level, "Apify MyCareersFuture requires both APIFY_MCF_RUN_URL and APIFY_API_TOKEN"
            )
        )

    return findings


if __name__ == "__main__":
    sys.exit(main())
