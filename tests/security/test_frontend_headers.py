from __future__ import annotations

import pathlib

NEXT_CONFIG = pathlib.Path("apps/web/next.config.mjs")


def test_frontend_csp_supports_optional_turnstile() -> None:
    config = NEXT_CONFIG.read_text()

    assert "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com" in config
    assert "frame-src https://challenges.cloudflare.com" in config
    assert "object-src 'none'" in config
    assert "base-uri 'none'" in config
    assert "form-action 'self'" in config
    assert "frame-ancestors 'none'" in config
    assert "devConnectPolicy" in config


def test_frontend_security_headers_disable_framing_and_sniffing() -> None:
    config = NEXT_CONFIG.read_text()

    assert '{ key: "X-Frame-Options", value: "DENY" }' in config
    assert '{ key: "X-Content-Type-Options", value: "nosniff" }' in config
    assert '{ key: "Strict-Transport-Security"' in config
    assert "poweredByHeader: false" in config
