#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SKIP_AGENT=0
if [ "${1:-}" = "--skip-agent" ]; then SKIP_AGENT=1; fi
EXPECTED_RUNTIME_CONTRACT="embedded-agent-gateway-v1"
PYTHON="$ROOT/.venv/bin/python"

[ -x "$PYTHON" ] || { echo "DataControl environment is missing. Run ./scripts/setup-dev.sh first." >&2; exit 1; }
"$PYTHON" -c 'import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)' >/dev/null 2>&1 || {
  echo "DataControl .venv must use Python 3.13 or 3.14; found $($PYTHON --version 2>&1)." >&2
  exit 1
}
command -v npm >/dev/null 2>&1 || { echo "npm is required." >&2; exit 1; }
[ -x web/node_modules/.bin/vite ] || { echo "Frontend dependencies are missing. Run ./scripts/setup-dev.sh (or npm install inside web) first." >&2; exit 1; }
mkdir -p .local

# DataControl's Portal/Gateway/MCP are loopback-only process boundaries. Preserve
# any external proxy for DeepSeek, but force local traffic to bypass it.
export NO_PROXY="127.0.0.1,localhost,::1${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY"

if [ "$SKIP_AGENT" -eq 0 ]; then
  if ! "$PYTHON" -c 'import agent3, dataagent_gateway' >/dev/null 2>&1 || [ ! -x agent/dsh/node_modules/.bin/dsh ] || [ ! -f .local/dsh-home/profiles/dataagent-headless/package.json ]; then
    echo "Embedded DataAgent setup is incomplete; bootstrapping it in the shared .venv now..."
    bash ./scripts/setup-agent.sh
  fi
  "$PYTHON" -c 'import agent3, dataagent_gateway' >/dev/null 2>&1 || { echo "Embedded DataAgent Python package is unavailable after setup." >&2; exit 1; }
fi

assert_port_free() {
  local port="$1" name="$2"
  if "$PYTHON" - "$port" <<'PY'
import socket, sys
port=int(sys.argv[1])
s=socket.socket()
try:
    s.bind(("127.0.0.1", port))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
PY
  then return 0; fi
  echo "$name cannot start because port $port is already in use. Stop the stale process first, then rerun ./scripts/start-dev.sh." >&2
  exit 1
}

wait_http() {
  local pid="$1" url="$2" name="$3" errlog="$4" timeout="${5:-25}"
  local end=$((SECONDS + timeout))
  while [ "$SECONDS" -lt "$end" ]; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "$name exited before becoming reachable." >&2; echo "--- $name stderr ---" >&2; tail -n 40 "$errlog" 2>/dev/null || true; return 1
    fi
    if curl --noproxy '*' -fsS "$url" >/dev/null 2>&1; then return 0; fi
    sleep .25
  done
  echo "$name did not become reachable at $url within ${timeout}s." >&2; tail -n 40 "$errlog" 2>/dev/null || true; return 1
}

wait_tcp() {
  local pid="$1" port="$2" name="$3" errlog="$4" timeout="${5:-30}"
  local end=$((SECONDS + timeout))
  while [ "$SECONDS" -lt "$end" ]; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "$name exited before binding port $port." >&2; echo "--- $name stderr ---" >&2; tail -n 40 "$errlog" 2>/dev/null || true; return 1
    fi
    if (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1; then return 0; fi
    sleep .25
  done
  echo "$name did not bind port $port within ${timeout}s." >&2; tail -n 40 "$errlog" 2>/dev/null || true; return 1
}

assert_port_free 8000 "DataControl API"
if [ "$SKIP_AGENT" -eq 0 ]; then assert_port_free 8900 "Agent3 MCP"; assert_port_free 8910 "DataAgent Gateway"; fi

rm -f .local/backend.log .local/backend.err.log .local/agent-mcp.log .local/agent-mcp.err.log .local/agent-gateway.log .local/agent-gateway.err.log
"$PYTHON" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 >.local/backend.log 2>.local/backend.err.log & BACKEND_PID=$!
MCP_PID=""; GATEWAY_PID=""
cleanup(){ [ -z "$GATEWAY_PID" ] || kill "$GATEWAY_PID" >/dev/null 2>&1 || true; [ -z "$MCP_PID" ] || kill "$MCP_PID" >/dev/null 2>&1 || true; kill "$BACKEND_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM
wait_http "$BACKEND_PID" http://127.0.0.1:8000/health "DataControl API" .local/backend.err.log 20

portal_health="$(curl --noproxy '*' -fsS http://127.0.0.1:8000/health)"
PORTAL_HEALTH="$portal_health" EXPECTED_RUNTIME_CONTRACT="$EXPECTED_RUNTIME_CONTRACT" "$PYTHON" - <<'PY'
import json, os
payload=json.loads(os.environ["PORTAL_HEALTH"])
expected=os.environ["EXPECTED_RUNTIME_CONTRACT"]
actual=payload.get("runtimeContract")
if actual != expected:
    raise SystemExit(f"DataControl API runtime contract mismatch: expected {expected!r}, got {actual!r}. A stale Portal process or stale checkout is being used.")
PY

if [ "$SKIP_AGENT" -eq 0 ]; then
  # Fail before MCP startup if the exact Portal facts required to build Agent3 Core
  # are unavailable. This turns a late MCP traceback into a precise startup gate.
  if ! "$PYTHON" - <<'PY'
import httpx
urls = [
    "http://127.0.0.1:8000/api/v1/metrics",
    "http://127.0.0.1:8000/api/v1/tables?limit=1",
]
with httpx.Client(timeout=10.0, trust_env=False) as client:
    for url in urls:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "data" not in payload:
            raise RuntimeError(f"invalid Portal fact contract: {url}")
metrics = client.get("http://127.0.0.1:8000/api/v1/metrics").json().get("data", [])
if not isinstance(metrics, list) or not metrics:
    raise RuntimeError("Portal has no metric semantics; rerun scripts/setup-dev.sh to seed the P3 corpus")
PY
  then
    echo "Portal Agent-fact preflight failed. Agent3 requires /api/v1/metrics and /api/v1/tables before MCP can start." >&2
    echo "--- DataControl API stderr ---" >&2
    tail -n 60 .local/backend.err.log 2>/dev/null || true
    exit 1
  fi
  echo "Portal Agent facts:  READY /api/v1/metrics + /api/v1/tables"

  export AGENT3_MCP_POC_MODE=1
  export DATACONTROL_PORTAL_URL=http://127.0.0.1:8000/api/v1
  export DSH_HOME="$ROOT/.local/dsh-home"
  export DSH_TELEMETRY_MODE=DISABLED
  (cd agent && "$PYTHON" -m agent3.adapters.mcp.server) >.local/agent-mcp.log 2>.local/agent-mcp.err.log & MCP_PID=$!
  wait_tcp "$MCP_PID" 8900 "Agent3 MCP" .local/agent-mcp.err.log 30
  "$PYTHON" -m uvicorn dataagent_gateway.app:app --host 127.0.0.1 --port 8910 >.local/agent-gateway.log 2>.local/agent-gateway.err.log & GATEWAY_PID=$!
  wait_http "$GATEWAY_PID" http://127.0.0.1:8910/health "DataAgent Gateway" .local/agent-gateway.err.log 25
  echo "Agent3 MCP:        READY http://127.0.0.1:8900/mcp"
  gateway_health="$(curl --noproxy '*' -fsS http://127.0.0.1:8910/health)"
  if printf '%s' "$gateway_health" | grep -q '"ready":true'; then echo "DataAgent Gateway: READY http://127.0.0.1:8910"; else echo "WARNING: DataAgent Gateway is running but degraded: $gateway_health" >&2; fi
  [ -n "${DEEPSEEK_API_KEY:-}" ] || echo "WARNING: DEEPSEEK_API_KEY is not set; Agent Gateway will be degraded until DataControl is restarted with the key present." >&2
else
  echo "WARNING: Embedded DataAgent intentionally skipped (--skip-agent). Intelligent Q&A will be unavailable." >&2
fi

printf '\nPython runtime:       %s\nDataControl API:      READY http://127.0.0.1:8000 (%s)\nDataControl Web:            http://127.0.0.1:5173\n' "$($PYTHON --version 2>&1)" "$EXPECTED_RUNTIME_CONTRACT"
cd web
npm run dev
