from agent3.contracts.authz import AuthzContext
from agent3.services.factory import build_demo_core


def codes(result):
    return {issue["code"] for issue in result["issues"]}


def test_valid_metric_sql_passes():
    sql = """
    SELECT org_id, SUM(balance_amt) AS loan_balance
    FROM dw.dwd_loan_snapshot
    WHERE status <> 'cancelled' AND dt = '2026-08-31'
    GROUP BY org_id
    """
    result = build_demo_core().validate_sql(
        AuthzContext.system(),
        sql,
        metric_id="loan_balance",
    )
    assert result["valid"] is True
    assert result["operation"] == "query"
    assert result["risk_level"] == "low"
    assert result["execution_allowed"] is False


def test_unknown_table_and_column_fail_closed():
    core = build_demo_core()
    assert "UNKNOWN_COLUMN" in codes(
        core.validate_sql(
            AuthzContext.system(),
            "select imaginary from dw.dwd_loan_snapshot where dt='2026-08-31'",
        )
    )
    assert "UNKNOWN_TABLE" in codes(
        core.validate_sql(AuthzContext.system(), "select x from dw.no_such_table")
    )


def test_multi_statement_program_is_still_rejected_per_validate_call():
    result = build_demo_core().validate_sql(
        AuthzContext.system(),
        "SELECT 1; DROP TABLE dw.dwd_loan_snapshot",
    )
    assert codes(result) == {"MULTI_STATEMENT_NOT_ALLOWED"}
    assert result["valid"] is False


def test_insert_is_validated_as_dml_but_never_marked_executable():
    sql = """
    INSERT INTO TABLE dw.dwd_loan_snapshot
    SELECT dt, org_id, region_code, product_id, balance_amt, status
    FROM dw.dwd_loan_snapshot
    WHERE dt = '2026-08-31'
    """
    result = build_demo_core().validate_sql(AuthzContext.system(), sql)
    assert result["valid"] is True
    assert result["operation"] == "dml"
    assert result["risk_level"] == "high"
    assert result["execution_allowed"] is False
    assert "MUTATING_STATEMENT_GENERATION_ONLY" in codes(result)


def test_create_table_as_select_allows_new_target_and_validates_source_metadata():
    sql = """
    CREATE TABLE dw.tmp_loan_snapshot AS
    SELECT org_id, balance_amt
    FROM dw.dwd_loan_snapshot
    WHERE dt = '2026-08-31'
    """
    result = build_demo_core().validate_sql(AuthzContext.system(), sql)
    assert result["valid"] is True
    assert result["operation"] == "ddl"
    assert result["risk_level"] == "medium"
    assert result["execution_allowed"] is False
    assert "UNKNOWN_TABLE" not in codes(result)
    assert "MUTATING_STATEMENT_GENERATION_ONLY" in codes(result)


def test_drop_is_high_risk_generation_only_not_confused_with_execution_permission():
    result = build_demo_core().validate_sql(
        AuthzContext.system(),
        "DROP TABLE dw.dwd_loan_snapshot",
    )
    assert result["valid"] is True
    assert result["operation"] == "ddl"
    assert result["risk_level"] == "critical"
    assert result["execution_allowed"] is False
    assert "DESTRUCTIVE_STATEMENT_GENERATION_ONLY" in codes(result)


def test_non_additive_metric_rejects_two_snapshot_or_branches():
    sql = """
    SELECT org_id, SUM(balance_amt) AS loan_balance
    FROM dw.dwd_loan_snapshot
    WHERE status <> 'cancelled'
      AND (dt = '2026-08-31' OR dt = '2026-07-31')
    GROUP BY org_id
    """
    result = build_demo_core().validate_sql(
        AuthzContext.system(),
        sql,
        metric_id="loan_balance",
    )
    assert result["valid"] is False
    assert "NON_ADDITIVE_OVER_TIME" in codes(result)


def test_non_additive_metric_accepts_single_value_in_snapshot():
    sql = """
    SELECT org_id, SUM(balance_amt) AS loan_balance
    FROM dw.dwd_loan_snapshot
    WHERE status <> 'cancelled' AND dt IN ('2026-08-31')
    GROUP BY org_id
    """
    result = build_demo_core().validate_sql(
        AuthzContext.system(),
        sql,
        metric_id="loan_balance",
    )
    assert result["valid"] is True
    assert "NON_ADDITIVE_OVER_TIME" not in codes(result)


def test_cte_name_is_not_mistaken_for_a_physical_table():
    sql = """
    WITH base AS (
      SELECT org_id, balance_amt
      FROM dw.dwd_loan_snapshot
      WHERE dt = '2026-08-31'
    )
    SELECT base.org_id, SUM(base.balance_amt)
    FROM base
    GROUP BY base.org_id
    """
    result = build_demo_core().validate_sql(AuthzContext.system(), sql)
    assert result["valid"] is True
    assert "UNKNOWN_TABLE" not in codes(result)
    assert "UNKNOWN_COLUMN" not in codes(result)


def test_unknown_cte_output_column_is_rejected():
    sql = """
    WITH base AS (
      SELECT org_id, balance_amt
      FROM dw.dwd_loan_snapshot
      WHERE dt = '2026-08-31'
    )
    SELECT base.not_a_column
    FROM base
    """
    result = build_demo_core().validate_sql(AuthzContext.system(), sql)
    assert result["valid"] is False
    assert "UNKNOWN_CTE_COLUMN" in codes(result)
