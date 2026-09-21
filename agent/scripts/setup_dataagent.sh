#!/usr/bin/env bash
set -euo pipefail
AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$AGENT_ROOT/.." && pwd)"
DSH_HOME="${DSH_HOME:-$REPO_ROOT/.local/dsh-home}"
export DSH_HOME DSH_TELEMETRY_MODE=DISABLED
DSH_DIR="$AGENT_ROOT/dsh"
GUARD_DIR="$AGENT_ROOT/guard-plugin"
DSH_BIN_DIR="$DSH_DIR/node_modules/.bin"
DSH_BIN="$DSH_BIN_DIR/dsh"
PNPM_BIN="$DSH_BIN_DIR/pnpm"
PATCH="$AGENT_ROOT/dsh/profile/cordis.patch.yml"

if [ ! -x "$DSH_BIN" ]; then
  echo "DeepSeek Harness is not installed. Run scripts/setup-agent.sh first." >&2
  exit 1
fi
if [ ! -x "$PNPM_BIN" ]; then
  echo "Pinned pnpm is missing from agent/dsh. Run scripts/setup-agent.sh again." >&2
  exit 1
fi
export PATH="$DSH_BIN_DIR:$PATH"
mkdir -p "$DSH_HOME"

setup_profile() {
  local name="$1" base="$2" profile="$DSH_HOME/profiles/$1"
  if [ -d "$profile" ] && [ ! -f "$profile/package.json" ]; then rm -rf "$profile"; fi
  if [ ! -f "$profile/package.json" ]; then
    (cd "$REPO_ROOT" && "$DSH_BIN" --profile "$name" --from-default-profile "$base" --dump-config >/dev/null)
  fi
  if ! grep -q '"@hunter-zk/agent3-guard"' "$profile/package.json" 2>/dev/null; then
    (cd "$REPO_ROOT" && "$DSH_BIN" plugin --profile "$name" add "$GUARD_DIR")
  fi
  cp "$PATCH" "$profile/cordis.patch.yml"
  local out err
  out="$(mktemp)"; err="$(mktemp)"
  if ! (cd "$REPO_ROOT" && "$DSH_BIN" --profile "$name" --dump-config >"$out" 2>"$err"); then
    cat "$err" >&2; rm -f "$out" "$err"; exit 1
  fi
  for required in deepseek-official mcp-agent3 agent3-guard dataagent-query; do
    grep -q "$required" "$out" || { echo "DataAgent profile $name missing $required" >&2; rm -f "$out" "$err"; exit 1; }
  done
  if grep -Eq '127\.0\.0\.1:8100|deepseek-v3-local|LOCAL_LLM_KEY' "$out"; then
    echo "Retired local LLM config detected in $name" >&2; rm -f "$out" "$err"; exit 1
  fi
  rm -f "$out" "$err"
}

setup_profile dataagent web
setup_profile dataagent-headless headless
echo "DataAgent dsh profiles ready: dataagent + dataagent-headless ($DSH_HOME)"
