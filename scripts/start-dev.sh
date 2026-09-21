#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[ -x .venv/bin/python ] || { echo "Portal environment is missing. Run ./scripts/setup-dev.sh first." >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required." >&2; exit 1; }
[ -x web/node_modules/.bin/vite ] || { echo "Frontend dependencies are missing. Run ./scripts/setup-dev.sh (or npm install inside web) first." >&2; exit 1; }

.venv/bin/python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 & BACKEND_PID=$!
MCP_PID=""; GATEWAY_PID=""
cleanup(){
  [ -z "$GATEWAY_PID" ] || kill "$GATEWAY_PID" >/dev/null 2>&1 || true
  [ -z "$MCP_PID" ] || kill "$MCP_PID" >/dev/null 2>&1 || true
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
for _ in {1..40}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then break; fi
  sleep .25
done

if [ -x .venv-agent/bin/python ]; then
  [ -x agent/dsh/node_modules/.bin/dsh ] || { echo "Embedded DataAgent dsh dependencies are missing. Run ./scripts/setup-agent.sh first." >&2; exit 1; }
  [ -f .local/dsh-home/profiles/dataagent-headless/package.json ] || { echo "Headless DataAgent profile is missing. Run ./scripts/setup-agent.sh first." >&2; exit 1; }
  export AGENT3_MCP_POC_MODE=1
  export DATACONTROL_PORTAL_URL=http://127.0.0.1:8000/api/v1
  export DSH_HOME="$ROOT/.local/dsh-home"
  export DSH_TELEMETRY_MODE=DISABLED
  (cd agent && ../.venv-agent/bin/python -m agent3.adapters.mcp.server) >.local/agent-mcp.log 2>.local/agent-mcp.err.log & MCP_PID=$!
  sleep .9
  .venv-agent/bin/python -m uvicorn dataagent_gateway.app:app --host 127.0.0.1 --port 8910 >.local/agent-gateway.log 2>.local/agent-gateway.err.log & GATEWAY_PID=$!
  echo "Agent3 MCP:        http://127.0.0.1:8900/mcp"
  echo "DataAgent Gateway: http://127.0.0.1:8910"
  [ -n "${DEEPSEEK_API_KEY:-}" ] || echo "WARNING: DEEPSEEK_API_KEY is not set; Agent Gateway will stay degraded until the key is provided before startup." >&2
else
  echo "WARNING: Embedded DataAgent skipped because .venv-agent is missing. Run ./scripts/setup-agent.sh." >&2
fi

printf '\nDataControl API: http://127.0.0.1:8000\nDataControl Web: http://127.0.0.1:5173\n'
cd web
npm run dev
