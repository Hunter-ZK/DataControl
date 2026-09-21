#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY314="${PYTHON314_BIN:-python3.14}"
command -v "$PY314" >/dev/null 2>&1 || { echo "Python 3.14 is required for the embedded DataAgent." >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Node.js/npm is required for the embedded DataAgent." >&2; exit 1; }
[ -d .venv-agent ] || "$PY314" -m venv .venv-agent
.venv-agent/bin/python -m pip install -U pip
.venv-agent/bin/python -m pip install -e './agent[all,dev]'
(cd agent/dsh && npm install --no-audit --no-fund)
(cd agent/guard-plugin && npm install --no-audit --no-fund && npm run build && npm test)
DSH_HOME="$ROOT/.local/dsh-home" bash agent/scripts/setup_dataagent.sh
echo "Embedded DataAgent setup complete (.venv-agent + local dsh profile)."
