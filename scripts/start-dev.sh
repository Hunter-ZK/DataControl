#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)";cd "$ROOT"
[ -x .venv/bin/python ] || { echo "Run ./scripts/setup-dev.sh first." >&2; exit 1; };command -v npm >/dev/null 2>&1 || { echo "npm is required." >&2; exit 1; }
.venv/bin/python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 & BACKEND_PID=$!
MCP_PID=""
cleanup(){ kill "$BACKEND_PID" >/dev/null 2>&1||true;[ -z "$MCP_PID" ]||kill "$MCP_PID" >/dev/null 2>&1||true;};trap cleanup EXIT INT TERM
for _ in {1..40};do if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1;then break;fi;sleep .25;done
if [ -x .venv-agent/bin/python ]; then AGENT3_MCP_POC_MODE=1 DATACONTROL_PORTAL_URL=http://127.0.0.1:8000/api/v1 .venv-agent/bin/python -m agent3.adapters.mcp.server >.local/agent-mcp.log 2>&1 & MCP_PID=$!; echo "Agent3 MCP: http://127.0.0.1:8900/mcp"; else echo "Agent3 MCP: skipped (.venv-agent missing)"; fi
printf '\nDataControl API: http://127.0.0.1:8000\nDataControl Web: http://127.0.0.1:5173\n'
cd web;npm run dev
