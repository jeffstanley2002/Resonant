from __future__ import annotations

from scripts.scan_secrets import PATTERNS


def test_secret_scan_allows_documented_placeholders() -> None:
    placeholders = [
        "SUPABASE_SERVICE_ROLE_KEY=...",
        "SUPABASE_SERVICE_ROLE_KEY=replace-only-in-render-never-frontend",
        "SUPABASE_SERVICE_ROLE_KEY=your-service-role-key",
        "APP_ENCRYPTION_KEY=optional-local-fernet-key",
        "APP_ENCRYPTION_KEY=replace-with-generated-fernet-key",
    ]

    for placeholder in placeholders:
        assert not any(pattern.search(placeholder) for pattern in PATTERNS)


def test_secret_scan_rejects_real_looking_service_role_value() -> None:
    leaked = "SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.real"

    assert any(pattern.search(leaked) for pattern in PATTERNS)


def test_secret_scan_rejects_real_looking_app_encryption_key() -> None:
    leaked = "APP_ENCRYPTION_KEY=MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="

    assert any(pattern.search(leaked) for pattern in PATTERNS)
