from __future__ import annotations

import base64

from app.core.encryption import ENCRYPTION_VERSION, decrypt_json, encrypt_json
from app.schemas import ResumeAnalysis, Skill
from app.services.storage import _resume_analysis_row

TEST_FERNET_KEY = base64.urlsafe_b64encode(b"0" * 32).decode("utf-8")


def test_app_layer_encryption_round_trips_json(monkeypatch) -> None:
    monkeypatch.setattr("app.core.encryption.settings.app_encryption_key", TEST_FERNET_KEY)

    token = encrypt_json({"summary": "Ada built secure AI systems", "skills": ["Python"]})

    assert "Ada built secure AI systems" not in token
    assert decrypt_json(token)["skills"] == ["Python"]


def test_resume_analysis_row_uses_plaintext_without_key(monkeypatch) -> None:
    monkeypatch.setattr("app.services.storage.settings.app_encryption_key", "")
    analysis = ResumeAnalysis(
        resume_id="resume_1",
        summary="Python and security engineer",
        skills=[Skill(name="Python")],
    )

    row = _resume_analysis_row(user_id="user_1", resume_hash="hash_1", analysis=analysis)

    assert row["summary"] == "Python and security engineer"
    assert row["skills"][0]["name"] == "Python"
    assert row["encrypted_payload"] is None
    assert row["encryption_version"] is None


def test_resume_analysis_row_encrypts_sensitive_payload(monkeypatch) -> None:
    monkeypatch.setattr("app.services.storage.settings.app_encryption_key", TEST_FERNET_KEY)
    monkeypatch.setattr("app.core.encryption.settings.app_encryption_key", TEST_FERNET_KEY)
    analysis = ResumeAnalysis(
        resume_id="resume_1",
        summary="Private resume summary",
        skills=[Skill(name="LangGraph")],
        role_signals=["AI Engineer"],
        seniority="mid-level",
        evidence=["Built LangGraph workflows"],
        uncertainties=["Years of experience not stated"],
        ai_status="succeeded",
        warnings=["Low text extraction confidence"],
    )

    row = _resume_analysis_row(user_id="user_1", resume_hash="hash_1", analysis=analysis)
    decrypted = decrypt_json(row["encrypted_payload"])

    assert row["summary"] == "[encrypted]"
    assert row["skills"] == []
    assert row["warnings"] == []
    assert row["encryption_version"] == ENCRYPTION_VERSION
    assert decrypted["summary"] == "Private resume summary"
    assert decrypted["skills"][0]["name"] == "LangGraph"
    assert decrypted["role_signals"] == ["AI Engineer"]
    assert decrypted["seniority"] == "mid-level"
    assert decrypted["evidence"] == ["Built LangGraph workflows"]
    assert decrypted["uncertainties"] == ["Years of experience not stated"]
    assert decrypted["ai_status"] == "succeeded"
