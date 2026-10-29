"""Startup must check the *checked-out* dependency manifest, not old setup markers."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check-portal-deps.py"


def run_checker(file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(file)],
        capture_output=True, text=True, check=False,
    )


def test_installed_requirements_are_accepted(tmp_path: Path) -> None:
    file = tmp_path / "pyproject.toml"
    file.write_text('[project]\ndependencies = ["pip>=1"]\n', encoding="utf-8")
    result = run_checker(file)
    assert result.returncode == 0, result.stderr


def test_new_missing_dependency_is_detected(tmp_path: Path) -> None:
    file = tmp_path / "pyproject.toml"
    file.write_text(
        '[project]\ndependencies = ["pip>=1", "datacontrol-nonexistent-test-package>=1"]\n',
        encoding="utf-8",
    )
    result = run_checker(file)
    assert result.returncode == 1
    assert "datacontrol-nonexistent-test-package" in result.stderr


def test_incompatible_dependency_version_is_detected(tmp_path: Path) -> None:
    file = tmp_path / "pyproject.toml"
    file.write_text('[project]\ndependencies = ["pip>=9999"]\n', encoding="utf-8")
    result = run_checker(file)
    assert result.returncode == 1
    assert "does not meet" in result.stderr


def test_current_project_dependencies_are_installed() -> None:
    result = run_checker(ROOT / "pyproject.toml")
    assert result.returncode == 0, result.stderr
