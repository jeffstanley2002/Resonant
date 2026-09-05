from __future__ import annotations

import logging

from app.core.logging import log_event


def test_structured_logging_redacts_sensitive_keys(caplog) -> None:
    caplog.set_level(logging.INFO, logger="resonant")

    log_event("test", resume_text="private", api_key="secret", run_id="run_123")

    assert "run_123" in caplog.text
    assert "private" not in caplog.text
    assert "secret" not in caplog.text
