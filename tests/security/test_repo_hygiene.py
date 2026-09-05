from __future__ import annotations

from types import SimpleNamespace

import scripts.repo_hygiene as hygiene


def test_repo_hygiene_accepts_expected_ignore_contract(monkeypatch) -> None:
    ignored = set(hygiene.MUST_BE_IGNORED)

    monkeypatch.setattr(hygiene, "is_ignored", lambda path: path in ignored)

    assert hygiene.validate_hygiene() == []


def test_repo_hygiene_rejects_ignored_deploy_template(monkeypatch) -> None:
    ignored = {".env.production.example", *hygiene.MUST_BE_IGNORED}

    monkeypatch.setattr(hygiene, "is_ignored", lambda path: path in ignored)

    findings = hygiene.validate_hygiene()

    assert findings[0].level == "ERROR"
    assert ".env.production.example" in findings[0].message


def test_repo_hygiene_rejects_unignored_local_env(monkeypatch) -> None:
    ignored = set(hygiene.MUST_BE_IGNORED) - {".env"}

    monkeypatch.setattr(hygiene, "is_ignored", lambda path: path in ignored)

    findings = hygiene.validate_hygiene()

    assert findings[0].level == "ERROR"
    assert ".env" in findings[0].message


def test_is_ignored_uses_git_check_ignore(monkeypatch) -> None:
    calls: list[list[str]] = []

    def run(args, **_kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="/tmp/repo\n")

    monkeypatch.setattr(hygiene.subprocess, "run", run)

    assert hygiene.is_ignored(".env") is True
    assert calls == [
        ["git", "rev-parse", "--show-toplevel"],
        ["git", "check-ignore", "--quiet", ".env"],
    ]
