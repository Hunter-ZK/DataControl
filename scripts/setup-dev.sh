#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT_DIR"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then if command -v python >/dev/null 2>&1; then PYTHON_BIN=python; else echo "Python 3 is required." >&2; exit 1; fi; fi
command -v npm >/dev/null 2>&1 || { echo "Node.js 24+ / npm is required." >&2; exit 1; }
[ -d .venv ] || "$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m alembic upgrade head
.venv/bin/python samples/generate_demo_data.py
.venv/bin/python samples/enrich_p1_data.py
.venv/bin/python samples/rebuild_search_index.py
(cd web && npm install)
if command -v "${PYTHON314_BIN:-python3.14}" >/dev/null 2>&1; then bash scripts/setup-agent.sh; else echo "WARNING: Python 3.14 not found; Portal/Web are ready but embedded DataAgent setup was skipped. Install Python 3.14 and run scripts/setup-agent.sh." >&2; fi
echo "Setup complete. Run ./scripts/start-dev.sh"
