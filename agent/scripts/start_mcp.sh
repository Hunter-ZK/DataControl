#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/.venv-agent/bin/python"
[ -x "$PY" ] || { echo "Missing .venv-agent; run scripts/setup-agent.sh" >&2; exit 1; }
export AGENT3_MCP_POC_MODE=1
export DATACONTROL_PORTAL_URL="${DATACONTROL_PORTAL_URL:-http://127.0.0.1:8000/api/v1}"
cd "$ROOT/agent"
exec "$PY" -m agent3.adapters.mcp.server
