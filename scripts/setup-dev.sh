#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SKIP_AGENT=0
if [ "${1:-}" = "--skip-agent" ]; then SKIP_AGENT=1; fi
command -v npm >/dev/null 2>&1 || { echo "Node.js 24+ / npm is required." >&2; exit 1; }

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
  [ -n "$PYTHON" ] || { echo "DataControl requires Python 3.13 or 3.14. Set PYTHON_BIN or install a compatible Python." >&2; exit 1; }
  echo "Creating .venv with $PYTHON ($("$PYTHON" --version 2>&1))"
  "$PYTHON" -m venv .venv
fi

.venv/bin/python -c 'import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)' >/dev/null 2>&1 || {
  echo "Existing .venv uses $(.venv/bin/python --version 2>&1); DataControl supports Python 3.13 and 3.14." >&2
  echo "Remove .venv and rerun setup-dev.sh with a compatible interpreter." >&2
  exit 1
}

.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m alembic upgrade head
.venv/bin/python samples/generate_demo_data.py
.venv/bin/python samples/enrich_p1_data.py
.venv/bin/python samples/enrich_p3_reference.py
.venv/bin/python samples/rebuild_search_index.py
.venv/bin/python samples/generate_p3_question_bank.py
(cd web && npm install)

if [ "$SKIP_AGENT" -eq 0 ]; then
  echo "Setting up embedded DataAgent in the shared Python environment..."
  bash scripts/setup-agent.sh
else
  echo "WARNING: Embedded DataAgent setup intentionally skipped (--skip-agent). Intelligent Q&A will be unavailable." >&2
fi

echo "Setup complete. Python: $(.venv/bin/python --version 2>&1)"
echo "P3 question bank: .local/p3-question-bank.json"
echo "Run ./scripts/start-dev.sh"
