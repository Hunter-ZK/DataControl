"""Launch the pinned dsh CLI with Unicode-safe, file-backed diagnostics.

The Windows runner invokes dsh.cmd through cmd.exe, but Python receives UTF-16
arguments from PowerShell and writes native UTF-8 output as bytes without the
Windows PowerShell 5.1 legacy console decoding/pipeline behavior.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    arguments = options.arguments
    if arguments and arguments[0] == "--":
        arguments = arguments[1:]
    if not arguments:
        parser.error("dsh CLI arguments are required")
    argv = [str(Path(options.executable).resolve()), *arguments]
    if os.name == "nt":
        # Avoid cmd.exe and npm's dsh.cmd shim altogether. Windows cmd /s /c
        # quoting is fragile for paths containing spaces/CJK characters.
        # Invoke the pinned official JS bin using argument-vector subprocess.
        package_json = Path(options.executable).parent.parent / "@deepseek-ai" / "dsh" / "package.json"
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
            if pkg.get("version") != "0.2.1-rc.3":
                raise ValueError(f"unexpected installed dsh version: {pkg.get('version')}")
            relative_bin = pkg["bin"]["dsh"]
            entrypoint = (package_json.parent / relative_bin).resolve()
            if not entrypoint.is_file():
                raise FileNotFoundError(entrypoint)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            Path(options.stderr).write_text(f"Cannot resolve installed dsh JS entrypoint: {exc}\\n", encoding="utf-8")
            return 125
        command = ["node", str(entrypoint), *arguments]
    else:
        command = argv
    out_path, err_path = Path(options.stdout), Path(options.stderr)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    err_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            command,
            cwd=options.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=options.timeout,
            check=False,
        )
        out_path.write_bytes(result.stdout)
        err_path.write_bytes(result.stderr)
        return result.returncode if 0 <= result.returncode <= 255 else 1
    except subprocess.TimeoutExpired as exc:
        out_path.write_bytes(exc.stdout or b"")
        err_path.write_bytes((exc.stderr or b"") + b"\ndsh profile command timed out\n")
        return 124
    except OSError as exc:
        out_path.write_bytes(b"")
        err_path.write_text(f"dsh process launch error: {exc}\n", encoding="utf-8")
        return 125


if __name__ == "__main__":
    sys.exit(main())
