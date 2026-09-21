#!/usr/bin/env bash
set -euo pipefail
AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; REPO_ROOT="$(cd "$AGENT_ROOT/.." && pwd)"
export DSH_HOME="${DSH_HOME:-$REPO_ROOT/.local/dsh-home}" DSH_TELEMETRY_MODE=DISABLED
DSH_BIN="$AGENT_ROOT/dsh/node_modules/.bin/dsh"; [ -x "$DSH_BIN" ] || { echo "Run scripts/setup-agent.sh first" >&2; exit 1; }
[ -n "${DEEPSEEK_API_KEY:-}" ] || echo "Warning: DEEPSEEK_API_KEY is not set; model calls require a configured DeepSeek credential." >&2
cd "$REPO_ROOT"; exec "$DSH_BIN" --profile dataagent --no-open
