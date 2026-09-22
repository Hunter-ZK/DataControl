from __future__ import annotations

import os

from agent3.adapters.mcp.authz import static_authz_provider
from agent3.adapters.mcp.tools import MCPToolAdapter
from agent3.contracts.authz import AuthzContext
from agent3.services.factory import build_datacontrol_core, build_demo_core


def build_poc_server():
    """Build the local P3 MCP server. Static identity is development-only."""
    if os.getenv("AGENT3_MCP_POC_MODE") != "1":
        raise RuntimeError(
            "Static MCP identity is PoC-only. Set AGENT3_MCP_POC_MODE=1 for local P3 verification."
        )
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install datacontrol-agent[mcp] to run the MCP transport") from exc

    core = build_demo_core() if os.getenv("AGENT3_DEMO_MODE") == "1" else build_datacontrol_core()
    adapter = MCPToolAdapter(
        core,
        static_authz_provider(
            AuthzContext(
                principal="datacontrol-local",
                roles=("poc",),
                purpose="p3-local",
            )
        ),
    )
    mcp = FastMCP("agent3", host="127.0.0.1", port=8900)
    for tool in (
        adapter.search_tables,
        adapter.get_schema,
        adapter.get_semantic_model,
        adapter.resolve_metric,
        adapter.plan_metric,
        adapter.search_verified_sql,
        adapter.validate_sql,
        adapter.explain_sql,
        adapter.compile_query,
        adapter.submit_ddl,
    ):
        mcp.tool()(tool)
    return mcp


def main() -> None:
    build_poc_server().run(transport="streamable-http")


if __name__ == "__main__":
    main()
