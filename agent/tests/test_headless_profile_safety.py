from __future__ import annotations

import json
import re
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
WEB_PATCH = AGENT_ROOT / "dsh" / "profile" / "cordis.patch.yml"
HEADLESS_PATCH = AGENT_ROOT / "dsh" / "profile" / "headless.patch.yml"
MULTI_PATCH = AGENT_ROOT / "dsh" / "profile" / "headless-multi.patch.yml"
QUERY_PRESET = AGENT_ROOT / "dsh" / "presets" / "dataagent-query" / "agent.cordis.yml"


def _row_disabled(text: str, row_id: str) -> bool:
    pattern = rf"(?ms)^- id: {re.escape(row_id)}\s*\n(?:  .+\n)*?  disabled: true\s*$"
    return re.search(pattern, text) is not None


def test_headless_profile_is_direct_and_does_not_depend_on_agent_presets():
    text = HEADLESS_PATCH.read_text(encoding="utf-8")
    assert "DataControl DataAgent" in text
    assert "mcp-agent3" in text
    assert "dataagent-query" not in text
    assert "- id: agent-presets" not in text
    assert "mode: native" in text


def test_headless_profile_enables_autonomy_but_blocks_unsafe_tools():
    text = HEADLESS_PATCH.read_text(encoding="utf-8")
    blocked = {
        "tool-plugin-manager",
        "tool-bash",
        "tool-pwsh",
        "tool-jobs",
        "tool-fs",
        "tool-fs-search",
        "tool-web",
    }
    enabled = {
        "command-goal",
        "tool-goal",
        "plan-mode",
        "compaction-basic",
        "command-compact",
        "tool-result-pruner",
        "tool-subagent-control",
        "tool-subagent-list-agents",
        "tool-subagent",
        "tool-subagent-fork",
        "workflow-ptc",
        "tool-workflow",
        "tool-todo",
    }
    missing = sorted(row_id for row_id in blocked if not _row_disabled(text, row_id))
    assert missing == [], f"headless safety tombstones missing: {missing}"
    still_disabled = sorted(row_id for row_id in enabled if _row_disabled(text, row_id))
    assert still_disabled == [], f"autonomous planning tools still disabled: {still_disabled}"
    assert "Standard query profile" in text
    assert "do not use Goal, Todo, Workflow, Subagent or Plan Mode" in text
    multi = MULTI_PATCH.read_text(encoding="utf-8")
    assert "Multi-step task profile" in multi
    for row_id in blocked:
        assert _row_disabled(multi, row_id)
    assert "- id: mcp-agent3" in multi


def test_dataagent_skill_discovery_is_embedded_and_deterministic():
    headless = HEADLESS_PATCH.read_text(encoding="utf-8")
    preset = QUERY_PRESET.read_text(encoding="utf-8")
    for text in (headless, MULTI_PATCH.read_text(encoding="utf-8"), preset):
        assert "includeDefaultRoots: false" in text
        assert "/agent/.dsh/skills" in text
    assert "- id: skill-filesystem\n  disabled: true" not in headless
    assert "- id: tool-skill\n  disabled: true" not in headless
    assert "sandbox: read-only" in headless
    assert "approval: ask" in headless


def test_web_profile_uses_v021_declarative_preset_registry():
    text = WEB_PATCH.read_text(encoding="utf-8")
    assert "agent-preset-registry" in text
    assert "default: standard" in text
    assert "- id: agent-presets" not in text

def test_overlays_reference_only_pinned_harness_plugin_ids():
    """Guard against patching absent rows (e.g. removed tool-ralph)."""
    registry = json.loads((AGENT_ROOT / "dsh" / "profile" / "pinned-plugin-ids.json").read_text(encoding="utf-8"))
    assert registry["version"] == "0.2.1-rc.3"
    for patch, mode in ((HEADLESS_PATCH, "headless"), (MULTI_PATCH, "headless"), (WEB_PATCH, "web")):
        text = patch.read_text(encoding="utf-8")
        root_ids = re.findall(r"(?m)^- id: ([\w-]+)\s*$", text)
        unknown = sorted(set(root_ids) - set(registry[mode]))
        assert not unknown, f"{patch.name} references absent dsh {mode} rows: {unknown}"
    assert "tool-ralph" not in HEADLESS_PATCH.read_text(encoding="utf-8")


def test_guard_plugin_is_loaded_directly_without_profile_package_install():
    for patch in (HEADLESS_PATCH, MULTI_PATCH, WEB_PATCH):
        text = patch.read_text(encoding="utf-8")
        assert "- id: agent3-guard" in text
        assert "agent/guard-plugin/dist/index.js" in text
    for script in (
        AGENT_ROOT / "scripts" / "setup_dataagent.ps1",
        AGENT_ROOT / "scripts" / "setup_dataagent.sh",
    ):
        assert 'plugin --profile' not in script.read_text(encoding="utf-8")
