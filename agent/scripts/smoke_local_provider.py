"""Offline end-to-end dsh config smoke for a local OpenAI-compatible model.

Uses a synthetic model ID; needs installed pinned dsh and built Guard but does
not need a running llama.cpp service or external credentials.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from dataagent_gateway.local_provider import LocalModel, expected_overlay, profile_name, ROOT


def main() -> int:
    entry = ROOT / "agent" / "dsh" / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
    bins = ROOT / "agent" / "dsh" / "node_modules" / ".bin"
    if not entry.exists():
        raise RuntimeError("Pinned dsh JS entry missing")
    with tempfile.TemporaryDirectory(prefix="datacontrol-local-profile-") as tmp:
        env = os.environ.copy()
        env["DSH_HOME"] = tmp
        env["DSH_TELEMETRY_MODE"] = "DISABLED"
        env["PYTHONIOENCODING"] = "utf-8"
        env["DATACONTROL_LOCAL_MODEL_API_KEY"] = "local-no-key-required"
        env["PATH"] = str(bins) + os.pathsep + env.get("PATH", "")
        for tier in ("standard", "multi"):
            name = profile_name(tier)
            command = ["node", str(entry), "--profile", name]
            boot = subprocess.run(
                command + ["--from-default-profile", "headless", "--dump-config"],
                env=env, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=150,
            )
            if boot.returncode:
                raise RuntimeError("local profile bootstrap failed: " + boot.stderr[-3000:])
            profile = Path(tmp) / "profiles" / name
            patch = profile / "cordis.patch.yml"
            if not (profile / "package.json").exists():
                raise RuntimeError("dsh did not create profile package.json")
            patch.write_text(
                expected_overlay(tier, LocalModel("ci-exact-model-id", "http://127.0.0.1:9931/v1")),
                encoding="utf-8",
            )
            check = subprocess.run(
                command + ["--dump-config"], cwd=ROOT, env=env,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=150,
            )
            if check.returncode:
                raise RuntimeError("local dsh config invalid: " + check.stderr[-3000:])
            for marker in ("local-llama", "ci-exact-model-id", "llm-pi-ai", "mcp-agent3", "agent3-guard"):
                if marker not in check.stdout:
                    raise RuntimeError("dsh local provider configuration missing " + marker)
            print("dsh local " + tier + " profile validated without external model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
