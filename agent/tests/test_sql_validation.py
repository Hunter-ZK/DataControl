from agent3.contracts.authz import AuthzContext
from agent3.services.factory import build_demo_core

def codes(result): return {issue["code"] for issue in result["issues"]}
def test_valid_metric_sql_passes():
    sql="SELECT org_id, SUM(balance_amt) AS loan_balance FROM dw.dwd_loan_snapshot WHERE status <> 'cancelled' AND dt = '2026-08-31' GROUP BY org_id";assert build_demo_core().validate_sql(AuthzContext.system(),sql,metric_id="loan_balance")["valid"] is True
def test_unknown_table_and_column_fail_closed():
    core=build_demo_core();assert "UNKNOWN_COLUMN" in codes(core.validate_sql(AuthzContext.system(),"select imaginary from dw.dwd_loan_snapshot where dt='2026-08-31'"));assert "UNKNOWN_TABLE" in codes(core.validate_sql(AuthzContext.system(),"select x from dw.no_such_table"))
def test_drop_and_multiple_statements_block():
    core=build_demo_core();assert "DROP_OR_TRUNCATE" in codes(core.validate_sql(AuthzContext.system(),"drop table dw.dwd_loan_snapshot"));assert codes(core.validate_sql(AuthzContext.system(),"SELECT 1; DROP TABLE dw.dwd_loan_snapshot"))=={"MULTI_STATEMENT_NOT_ALLOWED"}
