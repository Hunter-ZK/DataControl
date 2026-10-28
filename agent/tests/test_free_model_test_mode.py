"""The optional third-party lane must never silently replace the official default."""
import asyncio
import json
from pathlib import Path

import dataagent_gateway.runner as runner_module
from dataagent_gateway.runner import HeadlessHarnessRunner


def test_default_mode_is_deepseek(monkeypatch):
    monkeypatch.delenv("DATACONTROL_AGENT_MODEL_MODE", raising=False)
    monkeypatch.delenv("DATACONTROL_FREE_TEST_ACCEPT_PUBLIC_GATEWAY", raising=False)
    runner = HeadlessHarnessRunner()
    assert runner.profile == "dataagent-headless"
    assert not runner.free_test


def test_free_test_is_separate_profile_and_does_not_require_deepseek_key(monkeypatch, tmp_path):
    monkeypatch.setenv("DATACONTROL_AGENT_MODEL_MODE", "free-test")
    monkeypatch.delenv("DATACONTROL_FREE_TEST_ACCEPT_PUBLIC_GATEWAY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    runner = HeadlessHarnessRunner()
    assert runner.profile == "dataagent-headless-free"
    source = tmp_path / "agent" / "dsh" / "profile"
    source.mkdir(parents=True)
    (source / "headless.patch.yml").write_bytes(
        b"- id: agent-default-model\n  config:\n    provider: deepseek-official\n    model: deepseek-flash\n"
    )
    runner.repo_root = tmp_path
    runner.agent_root = tmp_path / "agent"
    runner.dsh_home = tmp_path / "local-dsh"
    runner.dsh_js_entry = tmp_path / "dsh.js"
    runner.dsh_js_entry.touch()
    prof = runner.profile_dir
    (prof / "node_modules" / "dsh-our-free-model").mkdir(parents=True)
    (prof / "cordis.patch.yml").write_bytes(
        b"- id: agent-default-model\n  config:\n    provider: our-free-model\n    model: kilo-auto/free\n"
    )
    (prof / "package.json").write_text(
        json.dumps({"dsh": {"profile": {"bundles": ["dsh-our-free-model"]}}}),
        encoding="utf-8"
    )
    (prof / "node_modules" / "dsh-our-free-model" / "package.json").write_text(
        json.dumps({"version": "2.7.2"}), encoding="utf-8"
    )
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "free-model-test-v2.7.2.ready").touch()
    async def reachable():
        return True
    monkeypatch.setattr(runner, "_mcp_reachable", reachable)
    runner.dsh_bin = tmp_path / "dsh"
    runner.dsh_bin.touch()
    available = asyncio.run(runner.health())
    assert available["profileReady"] and available["ready"]
    assert available["modelMode"] == "free-test"
    assert available["apiKeyRequired"] is False
    assert available["provider"] == "our-free-model"
    assert available["model"] == "kilo-auto/free"
