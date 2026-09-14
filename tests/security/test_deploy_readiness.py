from __future__ import annotations

import base64
import pathlib

import scripts.deploy_readiness as readiness

TEST_FERNET_KEY = base64.urlsafe_b64encode(b"0" * 32).decode("utf-8")


def test_production_readiness_rejects_placeholder_values() -> None:
    env = {
        "NEXT_PUBLIC_API_BASE_URL": "https://resonant.example.com",
        "NEXT_PUBLIC_SUPABASE_URL": "https://your-project.supabase.co",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY": "replace-me",
        "APP_ENV": "production",
        "ALLOWED_ORIGINS": "https://resonant.vercel.app",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_ANON_KEY": "replace-me",
        "SUPABASE_SERVICE_ROLE_KEY": "replace-me",
        "APP_ENCRYPTION_KEY": "replace-me",
        "DEMO_AUTH": "false",
        "OPENAI_API_KEY": "sk-live-openai-key",
    }

    findings = [
        *readiness.validate_required(env, readiness.FRONTEND_REQUIRED, "frontend", True),
        *readiness.validate_required(env, readiness.BACKEND_REQUIRED, "backend", True),
    ]

    assert any(finding.level == "ERROR" for finding in findings)
    assert any("placeholder" in finding.message for finding in findings)


def test_deployment_readiness_merges_env_files_in_order(tmp_path: pathlib.Path) -> None:
    root_env = tmp_path / ".env"
    apps_env = tmp_path / "apps" / ".env"
    apps_env.parent.mkdir()
    root_env.write_text("SUPABASE_URL=https://root.supabase.co\nCHEAP_MODEL=root/model\n")
    apps_env.write_text("SUPABASE_URL=https://apps.supabase.co\nOPENAI_API_KEY=key\n")

    env = readiness.read_env_files([root_env, apps_env])

    assert env["SUPABASE_URL"] == "https://apps.supabase.co"
    assert env["CHEAP_MODEL"] == "root/model"
    assert env["OPENAI_API_KEY"] == "key"


def test_production_readiness_rejects_wildcard_origins_and_http_api() -> None:
    env = {
        "ALLOWED_ORIGINS": "*",
        "NEXT_PUBLIC_API_BASE_URL": "http://resonant-api.onrender.com",
    }

    findings = readiness.validate_origins(env)

    assert {finding.message for finding in findings} == {
        "ALLOWED_ORIGINS must not use wildcard origins",
        "Production API base URL must use HTTPS",
    }


def test_production_readiness_rejects_supabase_rest_api_url() -> None:
    findings = readiness.validate_service_urls(
        {
            "NEXT_PUBLIC_SUPABASE_URL": "https://abc.supabase.co/rest/v1/",
            "SUPABASE_URL": "https://abc.supabase.co/auth/v1",
        },
        production=True,
    )

    messages = [finding.message for finding in findings]
    assert findings
    assert all(finding.level == "ERROR" for finding in findings)
    assert any(
        "NEXT_PUBLIC_SUPABASE_URL must be the project base URL" in message for message in messages
    )
    assert any("SUPABASE_URL must be the project base URL" in message for message in messages)


def test_production_readiness_rejects_malformed_apify_url() -> None:
    findings = readiness.validate_service_urls(
        {"APIFY_MCF_RUN_URL": "$API_TOKEN"},
        production=True,
    )

    assert findings == [
        readiness.Finding(
            "ERROR",
            "APIFY_MCF_RUN_URL must be an Apify actor /runs or /run-sync-get-dataset-items URL",
        )
    ]


def test_production_readiness_rejects_demo_auth() -> None:
    findings = readiness.validate_demo_auth({"DEMO_AUTH": "true"}, production=True)

    assert findings[0].level == "ERROR"


def test_frontend_secret_leakage_scans_web_files(
    tmp_path: pathlib.Path,
    monkeypatch,
) -> None:
    root = tmp_path
    web = root / "apps" / "web"
    web.mkdir(parents=True)
    (web / "page.tsx").write_text("const bad = 'SUPABASE_SERVICE_ROLE_KEY';")
    monkeypatch.setattr(readiness, "ROOT", root)

    findings = readiness.validate_frontend_secret_leakage()

    assert findings
    assert "SUPABASE_SERVICE_ROLE_KEY" in findings[0].message


def test_frontend_secret_leakage_allows_public_supabase_key(
    tmp_path: pathlib.Path,
    monkeypatch,
) -> None:
    root = tmp_path
    web = root / "apps" / "web"
    web.mkdir(parents=True)
    (web / "page.tsx").write_text("process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY")
    monkeypatch.setattr(readiness, "ROOT", root)

    assert readiness.validate_frontend_secret_leakage() == []


def test_production_ready_env_has_no_errors() -> None:
    env = {
        "NEXT_PUBLIC_API_BASE_URL": "https://resonant-api.onrender.com",
        "NEXT_PUBLIC_SUPABASE_URL": "https://abc.supabase.co",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY": "public-anon-key",
        "APP_ENV": "production",
        "ALLOWED_ORIGINS": "https://resonant.vercel.app",
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_ANON_KEY": "public-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
        "APP_ENCRYPTION_KEY": TEST_FERNET_KEY,
        "DEMO_AUTH": "false",
        "OPENAI_API_KEY": "sk-live-openai-key",
    }

    findings = [
        *readiness.validate_required(env, readiness.FRONTEND_REQUIRED, "frontend", True),
        *readiness.validate_required(env, readiness.BACKEND_REQUIRED, "backend", True),
        *readiness.validate_origins(env),
        *readiness.validate_demo_auth(env, production=True),
        *readiness.validate_encryption_key(env, production=True),
        *readiness.validate_paired_configuration(env, production=True),
        *readiness.validate_model_provider(env, production=True),
    ]

    assert [finding for finding in findings if finding.level == "ERROR"] == []


def test_production_readiness_requires_model_provider() -> None:
    findings = readiness.validate_model_provider({}, production=True)

    assert findings == [
        readiness.Finding("ERROR", "Production requires at least one configured AI model provider")
    ]


def test_development_readiness_warns_on_malformed_openai_key() -> None:
    findings = readiness.validate_model_provider(
        {"OPENAI_API_KEY": "paste this first sk-live-key"},
        production=False,
    )

    assert findings == [
        readiness.Finding("WARN", "OPENAI_API_KEY must contain only the API key value")
    ]


def test_production_readiness_rejects_supabase_project_mismatch() -> None:
    findings = readiness.validate_paired_configuration(
        {
            "NEXT_PUBLIC_SUPABASE_URL": "https://frontend.supabase.co",
            "SUPABASE_URL": "https://backend.supabase.co",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY": "same-anon-key",
            "SUPABASE_ANON_KEY": "same-anon-key",
        },
        production=True,
    )

    assert findings[0].level == "ERROR"
    assert "Supabase URLs" in findings[0].message


def test_production_readiness_rejects_supabase_anon_key_mismatch() -> None:
    findings = readiness.validate_paired_configuration(
        {
            "NEXT_PUBLIC_SUPABASE_URL": "https://abc.supabase.co",
            "SUPABASE_URL": "https://abc.supabase.co",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY": "frontend-anon",
            "SUPABASE_ANON_KEY": "backend-anon",
        },
        production=True,
    )

    assert findings[0].level == "ERROR"
    assert "anon keys" in findings[0].message


def test_production_readiness_rejects_turnstile_half_configuration() -> None:
    findings = readiness.validate_paired_configuration(
        {"NEXT_PUBLIC_TURNSTILE_SITE_KEY": "site-key"},
        production=True,
    )

    assert findings[0].level == "ERROR"
    assert "Turnstile" in findings[0].message


def test_production_readiness_rejects_invalid_encryption_key() -> None:
    findings = readiness.validate_encryption_key(
        {"APP_ENCRYPTION_KEY": "not-a-fernet-key"},
        production=True,
    )

    assert findings[0].level == "ERROR"
    assert "APP_ENCRYPTION_KEY" in findings[0].message


def test_render_manifest_contains_model_and_cost_controls() -> None:
    render_yaml = pathlib.Path("render.yaml").read_text()

    for key in [
        "APP_ENCRYPTION_KEY",
        "OPENAI_API_KEY",
        "CHEAP_MODEL",
        "STRONG_MODEL",
        "HELICONE_API_KEY",
        "DEFAULT_JOB_LIMIT",
        "MAX_JOB_LIMIT",
        "DAILY_MATCH_LIMIT",
        "MODEL_CALL_TIMEOUT_SECONDS",
        "MODEL_TASK_BUDGET_SECONDS",
    ]:
        assert f"key: {key}" in render_yaml


def test_schema_check_covers_every_table_the_api_writes() -> None:
    """Schema drift is silent at runtime, so the check must not miss a table."""
    import sys

    sys.path.insert(0, str(pathlib.Path("scripts").resolve()))
    from check_supabase_schema import EXPECTED_COLUMNS

    sys.path.insert(0, str(pathlib.Path("apps/api").resolve()))
    from app.services.storage import USER_DATA_TABLES

    assert set(USER_DATA_TABLES) == set(EXPECTED_COLUMNS)
    # The columns migration 002 adds are exactly the ones that were missing in production.
    assert {"analysis_mode", "telemetry"}.issubset(EXPECTED_COLUMNS["resume_analyses"])
