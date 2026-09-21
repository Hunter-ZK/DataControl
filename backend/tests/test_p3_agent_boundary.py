from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_agent_runtime_is_monorepo_owned_and_not_external_acp_bridge():
    config = (ROOT / "backend/app/core/config.py").read_text(encoding="utf-8")
    runtime = (ROOT / "backend/app/agent/runtime.py").read_text(encoding="utf-8")
    agent_readme = (ROOT / "agent/README.md").read_text(encoding="utf-8")
    assert "DATACONTROL_AGENT_HOME" in config
    assert "DATACONTROL_AGENT_GATEWAY_URL" in config
    assert "DATACONTROL_AGENT3_MCP_URL" not in config
    assert "DATACONTROL_DSH_COMMAND" not in config
    assert "ACP" not in runtime
    assert "DataAgent-dsh" in agent_readme
    assert "migration baseline" in agent_readme
    assert "must not need a second Git repository at runtime" in agent_readme


def test_agent_source_migration_is_complete_but_runtime_gate_remains_closed():
    manifest = json.loads((ROOT / "agent/runtime-manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "embedded-monorepo"
    assert manifest["sourceRepository"] == "Hunter-ZK/DataAgent-dsh"
    assert manifest["sourceCommit"] == "f04e266c6fe93e6e89d7e4b5c6e31128082a8c96"
    assert manifest["sourceMigrated"] is True
    assert manifest["coreEmbedded"] is True
    assert manifest["mcpEmbedded"] is True
    assert manifest["dshAssetsEmbedded"] is True
    assert manifest["integrated"] is False
