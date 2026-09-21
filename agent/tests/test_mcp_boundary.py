from agent3.adapters.mcp.authz import static_authz_provider
from agent3.adapters.mcp.tools import MCPToolAdapter
from agent3.contracts.authz import AuthzContext
from agent3.services.factory import build_demo_core

def test_mcp_adapter_is_thin_and_never_executes_ddl():
    adapter=MCPToolAdapter(build_demo_core(),static_authz_provider(AuthzContext(principal="u1")));assert adapter.get_schema("dwd_loan_snapshot")["found"] is True
    result=adapter.submit_ddl("CREATE TABLE x(a BIGINT)");assert result["execution_enabled"] is False and result["approval_required"] is True
