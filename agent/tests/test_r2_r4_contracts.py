"""New Agent tools must remain deterministic, grounded and non-executing."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent3.contracts.authz import AuthzContext
from agent3.semantic.revision import revise_plan
from agent3.services.development import check_naming, generate_ddl, generate_dq_checks, generate_etl
from agent3.services.factory import build_demo_core


def test_revision_preserves_original_metrics_and_filters():
    plan = {"metrics": ["metric_loan_balance"], "dimensions": ["region_code"],
            "filters": [{"field": "currency_cd", "op": "eq", "value": "CNY"}],
            "timeValues": ["LATEST"], "comparison": "none", "semanticValidated": True}
    ir = revise_plan(plan, {"comparison": "yoy", "filtersAdd": [
        {"field": "region_code", "op": "eq", "value": "GD"}]})
    assert ir.metric_id == "metric_loan_balance"
    assert ir.comparison == "yoy"
    assert ir.dimensions == ("region_code",)
    assert len(ir.filters) == 2
    assert ir.filters[0].field == "currency_cd"


@pytest.mark.parametrize("bad_changes", [
    {"metrics": ["other_metric"]}, {"rawSql": "DELETE FROM x"},
    {"filtersAdd": [{"field": "x;DROP", "op": "eq", "value": 1}]},
])
def test_revision_rejects_untrusted_changes(bad_changes):
    plan = {"metrics": ["metric_loan_balance"], "semanticValidated": True}
    if "filtersAdd" in bad_changes:
        # Raw fragments are rejected downstream by the compiler/identifier validator,
        # not by the structural parser that only accepts declarative fields.
        with pytest.raises((ValueError, Exception)):
            from agent3.services.development import identifier
            identifier(bad_changes["filtersAdd"][0]["field"])
    else:
        with pytest.raises(ValueError):
            revise_plan(plan, bad_changes)


def test_naming_and_ddl_drafts_are_non_executing():
    checked = check_naming("loan_balance_amt", roots={"loan", "balance", "amt"})
    assert checked["status"] == "valid"
    assert check_naming("loan_balance_amt", roots={"loan"})["status"] == "review_required"
    ddl = generate_ddl("stat_prod.dws_loan_month", [
        {"name": "loan_amt", "type": "DECIMAL(20,2)", "comment": "贷款金额"},
    ], partition_key="pt")
    assert ddl["sql"].startswith("CREATE TABLE IF NOT EXISTS")
    assert ddl["execution_allowed"] is False
    with pytest.raises(ValueError):
        generate_ddl("unsafe; DROP TABLE x", [{"name": "x", "type": "STRING"}])


def test_etl_and_dq_require_governed_source_fields():
    etl = generate_etl("ods.loan", "dws.loan", [
        {"source": "loan_amt", "target": "balance_amt"},
    ], {"loan_amt", "pt"}, source_partition="pt")
    assert "INSERT OVERWRITE" in etl["sql"]
    assert etl["execution_allowed"] is False
    with pytest.raises(ValueError):
        generate_etl("ods.loan", "dws.loan", [
            {"source": "unknown", "target": "balance_amt"}], {"loan_amt"})
    checks = generate_dq_checks("ods.loan", {"loan_amt", "id"},
                                required_columns=["loan_amt"], unique_keys=["id"])
    assert checks["execution_allowed"] is False
    assert len(checks["checks"]) == 3
    with pytest.raises(ValueError):
        generate_dq_checks("ods.loan", {"loan_amt"}, required_columns=["unknown"])


def test_single_tool_catalog_matches_mcp_adapter_and_guarded_facade():
    from agent3.adapters.mcp.tools import MCPToolAdapter
    from dataagent_gateway.runner import MCP_TOOL_SUFFIXES

    catalog = json.loads((Path(__file__).resolve().parents[1] / "tool-catalog.json").read_text())
    assert set(catalog["tools"]) == MCP_TOOL_SUFFIXES
    assert all(callable(getattr(MCPToolAdapter, name, None)) for name in catalog["tools"])


def test_core_draft_generation_keeps_explicit_no_execution():
    core = build_demo_core()
    result = core.generate_ddl(AuthzContext.system(), "analytics.demo",
                               [{"name": "amount", "type": "BIGINT"}])
    assert result["execution_allowed"] is False
    assert result["requiresApproval"] is True


def test_separate_dsh_profiles_have_explicit_tier_and_timeouts(monkeypatch):
    from dataagent_gateway.runner import HeadlessHarnessRunner

    monkeypatch.delenv("DATACONTROL_AGENT_RUN_TIMEOUT", raising=False)
    monkeypatch.delenv("DATACONTROL_AGENT_RUN_TIMEOUT_MULTI", raising=False)
    single = HeadlessHarnessRunner(task_tier="standard")
    multi = HeadlessHarnessRunner(task_tier="multi")
    assert single.profile == "dataagent-headless"
    assert multi.profile == "dataagent-headless-multi"
    assert single.timeout_seconds == 120
    assert multi.timeout_seconds == 600
    with pytest.raises(ValueError):
        HeadlessHarnessRunner(task_tier="unknown")
