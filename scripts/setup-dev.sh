#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SKIP_AGENT=0
if [ "${1:-}" = "--skip-agent" ]; then SKIP_AGENT=1; fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then PYTHON_BIN=python; else echo "Python 3 is required." >&2; exit 1; fi
fi
command -v npm >/dev/null 2>&1 || { echo "Node.js 24+ / npm is required." >&2; exit 1; }

[ -d .venv ] || "$PYTHON_BIN" -m venv .venv
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
  echo "Setting up embedded DataAgent (Python 3.14 runtime)..."
  bash scripts/setup-agent.sh
else
  echo "WARNING: Embedded DataAgent setup intentionally skipped (--skip-agent). Intelligent Q&A will be unavailable." >&2
fi

echo "Setup complete. P3 question bank: .local/p3-question-bank.json"
echo "Run ./scripts/start-dev.sh"
