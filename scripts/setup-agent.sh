#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=/dev/null
source "$ROOT/scripts/lib-python314.sh"

PY314="$(resolve_python314 || true)"
if [ -z "$PY314" ]; then
  print_python314_help
  exit 1
fi
command -v npm >/dev/null 2>&1 || { echo "Node.js/npm is required for the embedded DataAgent." >&2; exit 1; }

echo "Embedded DataAgent Python: $PY314 ($("$PY314" --version 2>&1))"

if [ -d .venv-agent ]; then
  if ! .venv-agent/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)' >/dev/null 2>&1; then
    echo "Existing .venv-agent is not Python 3.14; rebuilding it." >&2
    rm -rf .venv-agent
  fi
fi

[ -d .venv-agent ] || "$PY314" -m venv .venv-agent
.venv-agent/bin/python -m pip install -U pip
.venv-agent/bin/python -m pip install -e './agent[all,dev]'
(cd agent/dsh && npm install --no-audit --no-fund)
(cd agent/guard-plugin && npm install --no-audit --no-fund && npm run build && npm test)
DSH_HOME="$ROOT/.local/dsh-home" bash agent/scripts/setup_dataagent.sh

.venv-agent/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 14)'
[ -x agent/dsh/node_modules/.bin/dsh ] || { echo "dsh installation did not produce agent/dsh/node_modules/.bin/dsh" >&2; exit 1; }
[ -f .local/dsh-home/profiles/dataagent-headless/package.json ] || { echo "DataAgent headless profile bootstrap did not complete." >&2; exit 1; }

echo "Embedded DataAgent setup complete (.venv-agent + local dsh profile)."
