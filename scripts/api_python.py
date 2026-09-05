"""Run backend Python commands from the local venv when it exists.

CI installs backend dependencies into the active Python environment, while local setup uses
`apps/api/.venv`. This launcher keeps npm scripts portable across both paths.
"""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    command = build_command(ROOT, sys.argv[1:])
    if not command:
        print("Usage: python3 scripts/api_python.py <python-args...>")
        return 2
    os.execv(command[0], command)
    return 1


def build_command(root: pathlib.Path, args: list[str]) -> list[str]:
    if not args:
        return []
    return [str(select_python(root)), *args]


def select_python(root: pathlib.Path) -> pathlib.Path:
    venv_python = root / "apps" / "api" / ".venv" / "bin" / "python"
    if venv_python.exists():
        return venv_python
    return pathlib.Path(sys.executable)


if __name__ == "__main__":
    sys.exit(main())
