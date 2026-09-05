from __future__ import annotations

import sys

from scripts import api_python


def test_api_python_uses_local_venv_when_available(tmp_path) -> None:
    venv_python = tmp_path / "apps" / "api" / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("")

    command = api_python.build_command(tmp_path, ["-m", "pytest"])

    assert command == [str(venv_python), "-m", "pytest"]


def test_api_python_falls_back_to_active_python(tmp_path) -> None:
    command = api_python.build_command(tmp_path, ["-m", "pytest"])

    assert command == [sys.executable, "-m", "pytest"]


def test_api_python_rejects_missing_command(tmp_path) -> None:
    assert api_python.build_command(tmp_path, []) == []
