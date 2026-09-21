#!/usr/bin/env bash
set -euo pipefail
AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$AGENT_ROOT/.." && pwd)"
DSH_HOME="${DSH_HOME:-$REPO_ROOT/.local/dsh-home}"
export DSH_HOME DSH_TELEMETRY_MODE=DISABLED
DSH_DIR="$AGENT_ROOT/dsh"; GUARD_DIR="$AGENT_ROOT/guard-plugin"; PROFILE="$DSH_HOME/profiles/dataagent"
DSH_BIN="$DSH_DIR/node_modules/.bin/dsh"

if [ ! -x "$DSH_BIN" ]; then echo "DeepSeek Harness is not installed. Run scripts/setup-agent.sh first." >&2; exit 1; fi
mkdir -p "$DSH_HOME"
if [ -d "$PROFILE" ] && [ ! -f "$PROFILE/package.json" ]; then rm -rf "$PROFILE"; fi
if [ ! -f "$PROFILE/package.json" ]; then
  (cd "$REPO_ROOT" && "$DSH_BIN" --profile dataagent --from-default-profile web --dump-config >/dev/null)
fi
if ! grep -q '"@hunter-zk/agent3-guard"' "$PROFILE/package.json" 2>/dev/null; then
  (cd "$REPO_ROOT" && "$DSH_BIN" plugin --profile dataagent add "$GUARD_DIR")
fi
cp "$AGENT_ROOT/dsh/profile/cordis.patch.yml" "$PROFILE/cordis.patch.yml"
OUT="$(mktemp)"; ERR="$(mktemp)"; trap 'rm -f "$OUT" "$ERR"' EXIT
(cd "$REPO_ROOT" && "$DSH_BIN" --profile dataagent --dump-config >"$OUT" 2>"$ERR") || { cat "$ERR" >&2; exit 1; }
for required in deepseek-official mcp-agent3 agent3-guard dataagent-query; do grep -q "$required" "$OUT" || { echo "DataAgent profile missing $required" >&2; exit 1; }; done
if grep -Eq '127\.0\.0\.1:8100|deepseek-v3-local|LOCAL_LLM_KEY' "$OUT"; then echo "Retired local LLM config detected" >&2; exit 1; fi
echo "DataAgent dsh profile ready: $DSH_HOME (profile=dataagent)"
