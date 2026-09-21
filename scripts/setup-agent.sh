#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v npm >/dev/null 2>&1 || { echo "Node.js/npm is required for the embedded DataAgent." >&2; exit 1; }

find_python() {
  local candidate resolved
  for candidate in "${PYTHON_BIN:-}" python3 python; do
    [ -n "$candidate" ] || continue
    resolved="$(command -v "$candidate" 2>/dev/null || true)"
    [ -n "$resolved" ] || continue
    if "$resolved" -c 'import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done
  return 1
}

if [ ! -x .venv/bin/python ]; then
  PYTHON="$(find_python || true)"
  if [ -z "$PYTHON" ]; then
    echo "DataControl requires Python 3.13 or 3.14, but no compatible interpreter was found." >&2
    echo "Set PYTHON_BIN to a Python 3.13/3.14 interpreter, or install Python 3.13+." >&2
    exit 1
  fi
  echo "Creating shared DataControl environment with $PYTHON ($("$PYTHON" --version 2>&1))"
  "$PYTHON" -m venv .venv
  .venv/bin/python -m pip install -U pip
  .venv/bin/python -m pip install -e '.[dev]'
fi

PYTHON="$ROOT/.venv/bin/python"
"$PYTHON" -c 'import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)' >/dev/null 2>&1 || {
  echo "Existing .venv uses $($PYTHON --version 2>&1). Recreate .venv with Python 3.13 or 3.14." >&2
  exit 1
}

echo "Embedded DataAgent Python: $PYTHON ($($PYTHON --version 2>&1))"
"$PYTHON" -m pip install -e './agent[all]'

(cd agent/dsh && npm install --no-audit --no-fund)
(cd agent/guard-plugin && npm install --no-audit --no-fund && npm run build && npm test)
DSH_HOME="$ROOT/.local/dsh-home" bash agent/scripts/setup_dataagent.sh

"$PYTHON" -c 'import agent3, dataagent_gateway' >/dev/null
[ -x agent/dsh/node_modules/.bin/dsh ] || { echo "dsh installation did not produce agent/dsh/node_modules/.bin/dsh" >&2; exit 1; }
[ -f .local/dsh-home/profiles/dataagent-headless/package.json ] || { echo "DataAgent headless profile bootstrap did not complete." >&2; exit 1; }

echo "Embedded DataAgent setup complete (shared .venv + local dsh profile)."
