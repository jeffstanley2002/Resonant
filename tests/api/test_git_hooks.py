from __future__ import annotations

import os
import stat

from scripts import install_git_hooks


def test_install_hook_writes_expected_pre_commit(tmp_path) -> None:
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)

    status = install_git_hooks.install_hook(tmp_path)

    hook = hooks_dir / "pre-commit"
    assert status == "pre-commit hook installed"
    assert "scripts/scan_secrets.py" in hook.read_text()
    assert "scripts/repo_hygiene.py" in hook.read_text()
    assert hook.stat().st_mode & stat.S_IXUSR


def test_install_hook_refuses_to_overwrite_existing_hook(tmp_path) -> None:
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\necho custom\n")

    try:
        install_git_hooks.install_hook(tmp_path)
    except install_git_hooks.HookInstallError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected existing custom hook to be preserved")

    assert hook.read_text() == "#!/bin/sh\necho custom\n"


def test_install_hook_force_replaces_existing_hook(tmp_path) -> None:
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\necho custom\n")
    os.chmod(hook, 0o600)

    status = install_git_hooks.install_hook(tmp_path, force=True)

    assert status == "pre-commit hook installed"
    assert hook.read_text() == install_git_hooks.HOOK_BODY
    assert hook.stat().st_mode & stat.S_IXUSR
