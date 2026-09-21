from __future__ import annotations

import re
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
WEB_PATCH = AGENT_ROOT / "dsh" / "profile" / "cordis.patch.yml"
HEADLESS_PATCH = AGENT_ROOT / "dsh" / "profile" / "headless.patch.yml"


def _row_disabled(text: str, row_id: str) -> bool:
    pattern = rf"(?ms)^- id: {re.escape(row_id)}\s*\n(?:  .+\n)*?  disabled: true\s*$"
    return re.search(pattern, text) is not None


def test_headless_profile_is_direct_and_does_not_depend_on_agent_presets():
    text = HEADLESS_PATCH.read_text(encoding="utf-8")
    assert "DataControl DataAgent" in text
    assert "mcp-agent3" in text
    assert "dataagent-query" not in text
    assert "agent-presets" not in text
    assert "mode: native" in text


def test_headless_profile_disables_general_purpose_model_tools():
    text = HEADLESS_PATCH.read_text(encoding="utf-8")
    blocked = {
        "tool-plugin-manager",
        "tool-bash",
        "tool-pwsh",
        "tool-jobs",
        "tool-fs",
        "tool-fs-search",
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
        "tool-ralph",
        "tool-todo",
        "tool-web",
    }
    missing = sorted(row_id for row_id in blocked if not _row_disabled(text, row_id))
    assert missing == [], f"headless safety tombstones missing: {missing}"


def test_headless_keeps_only_read_only_skill_surface_beside_agent3_mcp():
    text = HEADLESS_PATCH.read_text(encoding="utf-8")
    # The base profile already owns these rows. The overlay deliberately does
    # not disable them so project .dsh/skills remain available read-only.
    assert "- id: skill-filesystem\n  disabled: true" not in text
    assert "- id: tool-skill\n  disabled: true" not in text
    assert "sandbox: read-only" in text
    assert "approval: ask" in text


def test_web_profile_still_uses_dataagent_query_preset():
    text = WEB_PATCH.read_text(encoding="utf-8")
    assert "agent-presets" in text
    assert "default: dataagent-query" in text
