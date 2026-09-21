#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "Missing shared .venv; run scripts/setup-dev.sh (or scripts/setup-agent.sh) first" >&2; exit 1; }
"$PY" -c 'import agent3' >/dev/null 2>&1 || { echo "Agent package is not installed in .venv; run scripts/setup-agent.sh" >&2; exit 1; }
export AGENT3_MCP_POC_MODE=1
export DATACONTROL_PORTAL_URL="${DATACONTROL_PORTAL_URL:-http://127.0.0.1:8000/api/v1}"
cd "$ROOT/agent"
exec "$PY" -m agent3.adapters.mcp.server
