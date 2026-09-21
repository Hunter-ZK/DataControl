#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SKIP_AGENT=0
if [ "${1:-}" = "--skip-agent" ]; then SKIP_AGENT=1; fi

[ -x .venv/bin/python ] || { echo "Portal environment is missing. Run ./scripts/setup-dev.sh first." >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required." >&2; exit 1; }
[ -x web/node_modules/.bin/vite ] || { echo "Frontend dependencies are missing. Run ./scripts/setup-dev.sh (or npm install inside web) first." >&2; exit 1; }
mkdir -p .local

if [ "$SKIP_AGENT" -eq 0 ]; then
  [ -x .venv-agent/bin/python ] || { echo "Embedded DataAgent environment is missing. Run ./scripts/setup-agent.sh first (Python 3.14 required). Use --skip-agent only when intentionally starting Portal/Web without intelligent Q&A." >&2; exit 1; }
  [ -x agent/dsh/node_modules/.bin/dsh ] || { echo "Embedded DataAgent dsh dependencies are missing. Run ./scripts/setup-agent.sh first." >&2; exit 1; }
  [ -f .local/dsh-home/profiles/dataagent-headless/package.json ] || { echo "Headless DataAgent profile is missing. Run ./scripts/setup-agent.sh first." >&2; exit 1; }
fi

wait_http() {
  local pid="$1" url="$2" name="$3" errlog="$4" timeout="${5:-25}"
  local end=$((SECONDS + timeout))
  while [ "$SECONDS" -lt "$end" ]; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "$name exited before becoming reachable." >&2
      echo "--- $name stderr ---" >&2
      tail -n 40 "$errlog" 2>/dev/null || true
      return 1
    fi
    if curl -fsS "$url" >/dev/null 2>&1; then return 0; fi
    sleep .25
  done
  echo "$name did not become reachable at $url within ${timeout}s." >&2
  echo "--- $name stderr ---" >&2
  tail -n 40 "$errlog" 2>/dev/null || true
  return 1
}

wait_tcp() {
  local pid="$1" port="$2" name="$3" errlog="$4" timeout="${5:-30}"
  local end=$((SECONDS + timeout))
  while [ "$SECONDS" -lt "$end" ]; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "$name exited before binding port $port." >&2
      echo "--- $name stderr ---" >&2
      tail -n 40 "$errlog" 2>/dev/null || true
      return 1
    fi
    if (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1; then return 0; fi
    sleep .25
  done
  echo "$name did not bind port $port within ${timeout}s." >&2
  echo "--- $name stderr ---" >&2
  tail -n 40 "$errlog" 2>/dev/null || true
  return 1
}

.venv/bin/python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 >.local/backend.log 2>.local/backend.err.log & BACKEND_PID=$!
MCP_PID=""; GATEWAY_PID=""
cleanup(){
  [ -z "$GATEWAY_PID" ] || kill "$GATEWAY_PID" >/dev/null 2>&1 || true
  [ -z "$MCP_PID" ] || kill "$MCP_PID" >/dev/null 2>&1 || true
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
wait_http "$BACKEND_PID" http://127.0.0.1:8000/health "DataControl API" .local/backend.err.log 20

if [ "$SKIP_AGENT" -eq 0 ]; then
  export AGENT3_MCP_POC_MODE=1
  export DATACONTROL_PORTAL_URL=http://127.0.0.1:8000/api/v1
  export DSH_HOME="$ROOT/.local/dsh-home"
  export DSH_TELEMETRY_MODE=DISABLED
  rm -f .local/agent-mcp.log .local/agent-mcp.err.log .local/agent-gateway.log .local/agent-gateway.err.log
  (cd agent && ../.venv-agent/bin/python -m agent3.adapters.mcp.server) >.local/agent-mcp.log 2>.local/agent-mcp.err.log & MCP_PID=$!
  wait_tcp "$MCP_PID" 8900 "Agent3 MCP" .local/agent-mcp.err.log 30
  .venv-agent/bin/python -m uvicorn dataagent_gateway.app:app --host 127.0.0.1 --port 8910 >.local/agent-gateway.log 2>.local/agent-gateway.err.log & GATEWAY_PID=$!
  wait_http "$GATEWAY_PID" http://127.0.0.1:8910/health "DataAgent Gateway" .local/agent-gateway.err.log 25
  echo "Agent3 MCP:        READY http://127.0.0.1:8900/mcp"
  gateway_health="$(curl -fsS http://127.0.0.1:8910/health)"
  if printf '%s' "$gateway_health" | grep -q '"ready":true'; then
    echo "DataAgent Gateway: READY http://127.0.0.1:8910"
  else
    echo "WARNING: DataAgent Gateway is running but degraded: $gateway_health" >&2
  fi
  [ -n "${DEEPSEEK_API_KEY:-}" ] || echo "WARNING: DEEPSEEK_API_KEY is not set; Agent Gateway is expected to be degraded until DataControl is restarted with the key present." >&2
else
  echo "WARNING: Embedded DataAgent intentionally skipped (--skip-agent). Intelligent Q&A will be unavailable." >&2
fi

printf '\nDataControl API: READY http://127.0.0.1:8000\nDataControl Web:       http://127.0.0.1:5173\n'
cd web
npm run dev
