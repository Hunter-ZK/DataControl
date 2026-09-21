import pytest
from agent3.contracts.authz import AuthzContext
from agent3.semantic.compiler import SemanticCompileError
from agent3.semantic.models import QueryIR
from agent3.services.factory import build_demo_core


def test_resolve_and_compile_standard_metric():
    core = build_demo_core()
    authz = AuthzContext.system()
    assert core.resolve_metric(authz, "余额")["resolved"] is True
    compiled = core.compile_query(authz, QueryIR(metric_id="loan_balance", dimensions=("org_id",), time_values=("2026-08-31",)))
    assert "SUM(balance_amt)" in compiled["sql"]
    assert compiled["validation"]["valid"] is True


def test_natural_language_metric_resolution_ignores_time_and_query_noise():
    core = build_demo_core()
    authz = AuthzContext.system()
    for phrase in ["本期贷款余额", "帮我查一下当前贷款余额", "最新一期贷款余额是多少", "期末贷款余额"]:
        result = core.resolve_metric(authz, phrase)
        assert result["resolved"] is True, phrase
        assert result["metric"]["id"] == "loan_balance"


def test_latest_period_compiles_to_max_governed_time_field():
    core = build_demo_core()
    compiled = core.compile_query(
        AuthzContext.system(),
        QueryIR(metric_id="loan_balance", dimensions=("region_code",), time_values=("LATEST",)),
    )
    sql = compiled["sql"]
    assert "dt = (SELECT MAX(dt) FROM dw.dwd_loan_snapshot)" in sql
    assert "GROUP BY region_code" in sql
    assert compiled["validation"]["valid"] is True


def test_previous_period_is_deterministic():
    core = build_demo_core()
    sql = core.compile_query(AuthzContext.system(), QueryIR(metric_id="loan_balance", time_values=("PREVIOUS",)))["sql"]
    assert "MAX(dt)" in sql and "dt < (SELECT MAX(dt)" in sql


def test_non_additive_metric_rejects_multiple_snapshots():
    with pytest.raises(SemanticCompileError):
        build_demo_core().compile_query(AuthzContext.system(), QueryIR(metric_id="loan_balance", time_values=("2026-07-31", "2026-08-31")))


def test_schema_and_search_are_structured():
    core = build_demo_core()
    authz = AuthzContext.system()
    assert core.search_tables(authz, "贷款快照")["tables"][0]["full_name"] == "dw.dwd_loan_snapshot"
    assert core.get_schema(authz, "dwd_loan_snapshot")["found"] is True
