import pytest

from agent3.contracts.authz import AuthzContext
from agent3.semantic.compiler import SemanticCompileError
from agent3.semantic.models import (
    Additivity,
    ComparisonKind,
    MandatoryFilter,
    MetricDefinition,
    MetricKind,
    QueryIR,
)
from agent3.semantic.registry import SemanticRegistry
from agent3.services.core import Agent3Core
from agent3.services.factory import build_demo_core


def test_resolve_and_compile_standard_metric():
    core = build_demo_core()
    authz = AuthzContext.system()
    assert core.resolve_metric(authz, "余额")["resolved"] is True
    compiled = core.compile_query(
        authz,
        QueryIR(
            metric_id="loan_balance",
            dimensions=("org_id",),
            time_values=("2026-08-31",),
        ),
    )
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
    sql = core.compile_query(
        AuthzContext.system(),
        QueryIR(metric_id="loan_balance", time_values=("PREVIOUS",)),
    )["sql"]
    assert "MAX(dt)" in sql and "dt < (SELECT MAX(dt)" in sql


def test_non_additive_metric_rejects_multiple_snapshots():
    with pytest.raises(SemanticCompileError):
        build_demo_core().compile_query(
            AuthzContext.system(),
            QueryIR(metric_id="loan_balance", time_values=("2026-07-31", "2026-08-31")),
        )


def test_schema_and_search_are_structured():
    core = build_demo_core()
    authz = AuthzContext.system()
    assert core.search_tables(authz, "贷款快照")["tables"][0]["full_name"] == "dw.dwd_loan_snapshot"
    schema = core.get_schema(authz, "dwd_loan_snapshot")
    assert schema["found"] is True
    currency = next(item for item in schema["columns"] if item["name"] == "currency_cd")
    assert currency["code_table_no"] == "CD_CURRENCY"


def test_p2_code_value_resolution_uses_internal_governed_code_table():
    core = build_demo_core()
    result = core.resolve_code_value(
        AuthzContext.system(),
        "dw.dwd_loan_snapshot",
        "currency_cd",
        "人民币",
    )
    assert result["status"] == "resolved"
    assert result["researchPolicy"] == "internal_only"
    assert result["codeTableNo"] == "CD_CURRENCY"
    assert result["matches"][0]["value"] == "CNY"


def _p2_core() -> Agent3Core:
    demo = build_demo_core()
    monthly = {
        "source_entity": "dw.dwd_loan_snapshot",
        "valid_dimensions": ("region_code", "org_id"),
        "time_field": "stat_month",
        "time_grain": "MONTH",
    }
    metrics = (
        MetricDefinition(
            id="loan_balance",
            name="贷款余额",
            aliases=("贷款增长",),
            aggregation="sum",
            measure="balance_amt",
            additivity_time=Additivity.NON_ADDITIVE,
            mandatory_filters=(MandatoryFilter("currency_cd", "eq", "CNY"),),
            **monthly,
        ),
        MetricDefinition(
            id="new_loan_amount",
            name="新增贷款金额",
            aliases=("贷款增长",),
            aggregation="sum",
            measure="new_loan_amt",
            **monthly,
        ),
        MetricDefinition(
            id="npl_balance",
            name="不良贷款余额",
            aggregation="sum",
            measure="npl_balance",
            additivity_time=Additivity.NON_ADDITIVE,
            **monthly,
        ),
        MetricDefinition(
            id="npl_ratio",
            name="不良贷款率",
            aggregation="ratio",
            measure="npl_balance",
            additivity_time=Additivity.NON_ADDITIVE,
            kind=MetricKind.RATIO,
            numerator_metric_id="npl_balance",
            denominator_metric_id="loan_balance",
            **monthly,
        ),
        MetricDefinition(
            id="loan_balance_yoy",
            name="贷款余额同比增长率",
            aggregation="derived",
            measure="balance_amt",
            additivity_time=Additivity.NON_ADDITIVE,
            kind=MetricKind.DERIVED,
            formula="(current(loan_balance) - yoy(loan_balance)) / yoy(loan_balance)",
            **monthly,
        ),
    )
    return Agent3Core(metadata=demo.metadata, semantics=SemanticRegistry(metrics))


def test_p2_ambiguous_metric_returns_structured_user_options_without_external_research():
    result = _p2_core().plan_metric(AuthzContext.system(), "贷款增长")
    assert result["status"] == "clarification_required"
    assert result["researchPolicy"] == "internal_only"
    clarification = result["clarification"]
    assert clarification["selection_mode"] == "single"
    assert {item["value"] for item in clarification["options"]} == {
        "loan_balance",
        "new_loan_amount",
    }


def test_p2_missing_metric_fails_closed_to_custom_clarification():
    result = _p2_core().plan_metric(AuthzContext.system(), "火星资产回报率")
    assert result["status"] == "evidence_insufficient"
    assert result["researchPolicy"] == "internal_only"
    assert result["clarification"]["options"] == []
    assert result["clarification"]["allow_custom_input"] is True


def test_p2_ratio_metric_and_topn_compile_deterministically():
    core = _p2_core()
    compiled = core.compile_query(
        AuthzContext.system(),
        QueryIR(
            metric_id="npl_ratio",
            dimensions=("region_code",),
            time_values=("LATEST",),
            order="DESC",
            limit=10,
        ),
    )
    sql = compiled["sql"]
    assert "CASE WHEN SUM(balance_amt) = 0 THEN NULL" in sql
    assert "SUM(npl_balance) / SUM(balance_amt)" in sql
    assert "GROUP BY region_code" in sql
    assert "ORDER BY npl_ratio DESC LIMIT 10" in sql
    assert compiled["validation"]["valid"] is True
    assert compiled["semanticPlan"]["semanticValidated"] is True


def test_p2_multi_metric_same_source_query_is_compiled_once():
    compiled = _p2_core().compile_query(
        AuthzContext.system(),
        QueryIR(
            metric_id="loan_balance",
            metric_ids=("new_loan_amount",),
            dimensions=("region_code",),
            time_values=("2026-08",),
            order="DESC",
            order_metric_id="new_loan_amount",
            limit=20,
        ),
    )
    sql = compiled["sql"]
    assert "SUM(balance_amt) AS loan_balance" in sql
    assert "SUM(new_loan_amt) AS new_loan_amount" in sql
    assert "currency_cd = 'CNY'" in sql
    assert "ORDER BY new_loan_amount DESC LIMIT 20" in sql
    assert compiled["semanticPlan"]["metrics"] == ["loan_balance", "new_loan_amount"]
    assert compiled["validation"]["valid"] is True


def test_p2_complex_filters_are_declarative_and_escaped():
    compiled = _p2_core().compile_query(
        AuthzContext.system(),
        QueryIR(
            metric_id="new_loan_amount",
            dimensions=("region_code",),
            time_values=("2026-08",),
            filters=(
                MandatoryFilter("region_code", "in", ["440000", "440300"]),
                MandatoryFilter("org_id", "between", ["001", "999"]),
                MandatoryFilter("status", "contains", "正常"),
            ),
        ),
    )
    sql = compiled["sql"]
    assert "region_code IN ('440000', '440300')" in sql
    assert "org_id BETWEEN '001' AND '999'" in sql
    assert "status LIKE '%正常%'" in sql
    assert compiled["validation"]["valid"] is True


def test_p2_yoy_and_mom_use_governed_month_calendar():
    core = _p2_core()
    yoy = core.compile_query(
        AuthzContext.system(),
        QueryIR(
            metric_id="loan_balance",
            dimensions=("region_code",),
            time_values=("2026-08",),
            comparison=ComparisonKind.YOY,
        ),
    )
    assert "'2025-08'" in yoy["sql"]
    assert "AS loan_balance_yoy" in yoy["sql"]
    assert yoy["validation"]["valid"] is True

    mom = core.compile_query(
        AuthzContext.system(),
        QueryIR(
            metric_id="loan_balance",
            dimensions=("region_code",),
            time_values=("2026-01",),
            comparison=ComparisonKind.MOM,
        ),
    )
    assert "'2025-12'" in mom["sql"]
    assert "AS loan_balance_mom" in mom["sql"]
    assert mom["validation"]["valid"] is True


def test_p2_latest_comparison_uses_dynamic_governed_period_offset():
    compiled = _p2_core().compile_query(
        AuthzContext.system(),
        QueryIR(
            metric_id="loan_balance",
            time_values=("LATEST",),
            comparison=ComparisonKind.MOM,
        ),
    )
    sql = compiled["sql"]
    assert "MAX(stat_month)" in sql
    assert "LPAD" in sql
    assert compiled["validation"]["valid"] is True


def test_p2_governed_derived_yoy_metric_compiles_without_free_form_formula_sql():
    compiled = _p2_core().compile_query(
        AuthzContext.system(),
        QueryIR(
            metric_id="loan_balance_yoy",
            dimensions=("region_code",),
            time_values=("2026-08",),
            order="DESC",
            limit=5,
        ),
    )
    sql = compiled["sql"]
    assert "AS loan_balance_yoy" in sql
    assert "'2025-08'" in sql
    assert "ORDER BY loan_balance_yoy DESC LIMIT 5" in sql
    assert compiled["validation"]["valid"] is True


def test_p2_multi_metric_comparison_fails_closed():
    with pytest.raises(SemanticCompileError, match="同比/环比"):
        _p2_core().compile_query(
            AuthzContext.system(),
            QueryIR(
                metric_id="loan_balance",
                metric_ids=("new_loan_amount",),
                comparison=ComparisonKind.YOY,
                time_values=("2026-08",),
            ),
        )
