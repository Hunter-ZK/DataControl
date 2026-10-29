"""Verify installed Portal dependencies against the checked-out pyproject.toml.

This is read-only: the PowerShell launcher decides whether to synchronize
requirements without reinitializing sample data, npm dependencies or Agent.
"""
from __future__ import annotations

import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    from packaging.requirements import Requirement
except ImportError:
    # pip is present in the repository's .venv. Use its vendored packaging
    # when there is no separately installed packaging distribution.
    from pip._vendor.packaging.requirements import Requirement


def missing_requirements(pyproject: Path) -> list[str]:
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    missing: list[str] = []
    for raw in project.get("project", {}).get("dependencies", []):
        requirement = Requirement(raw)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = version(requirement.name)
        except PackageNotFoundError:
            missing.append(f"{requirement.name} (not installed)")
            continue
        if requirement.specifier and not requirement.specifier.contains(installed):
            missing.append(
                f"{requirement.name} ({installed} does not meet {requirement.specifier})"
            )
    return missing


def main(argv: list[str]) -> int:
    pyproject = (
        Path(argv[0]) if argv else Path(__file__).resolve().parents[1] / "pyproject.toml"
    )
    try:
        missing = missing_requirements(pyproject)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"[DataControl] Portal dependency manifest check failed: {exc}", file=sys.stderr)
        return 2
    if missing:
        print("[DataControl] Portal dependencies require synchronization:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print("[DataControl] Portal Python dependencies: current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
