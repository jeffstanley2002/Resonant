"""Install optional local Git hooks for pre-deployment safety checks."""

from __future__ import annotations

import argparse
import pathlib
import stat
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK_RELATIVE_PATH = pathlib.Path(".git/hooks/pre-commit")
HOOK_BODY = """#!/bin/sh
set -eu

python3 scripts/scan_secrets.py
python3 scripts/repo_hygiene.py
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Replace an existing pre-commit hook")
    parser.add_argument("--check", action="store_true", help="Check whether the hook is installed")
    args = parser.parse_args()

    try:
        if args.check:
            status = check_hook(ROOT)
        else:
            status = install_hook(ROOT, force=args.force)
    except HookInstallError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(status)
    return 0


def check_hook(root: pathlib.Path) -> str:
    hook_path = root / HOOK_RELATIVE_PATH
    if hook_path.exists() and hook_path.read_text() == HOOK_BODY:
        return "pre-commit hook is installed"
    raise HookInstallError("pre-commit hook is not installed")


def install_hook(root: pathlib.Path, force: bool = False) -> str:
    git_dir = root / ".git"
    hooks_dir = git_dir / "hooks"
    hook_path = root / HOOK_RELATIVE_PATH
    if not git_dir.exists():
        raise HookInstallError("repository has no .git directory")
    hooks_dir.mkdir(parents=True, exist_ok=True)

    if hook_path.exists() and hook_path.read_text() != HOOK_BODY and not force:
        raise HookInstallError("pre-commit hook already exists; rerun with --force to replace it")

    if hook_path.exists() and hook_path.read_text() == HOOK_BODY:
        ensure_executable(hook_path)
        return "pre-commit hook is already installed"

    hook_path.write_text(HOOK_BODY)
    ensure_executable(hook_path)
    return "pre-commit hook installed"


def ensure_executable(path: pathlib.Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class HookInstallError(Exception):
    """Raised when hooks cannot be installed safely."""


if __name__ == "__main__":
    sys.exit(main())
