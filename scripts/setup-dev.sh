#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then PYTHON_BIN=python; else echo "Python 3 is required." >&2; exit 1; fi
fi
if ! command -v npm >/dev/null 2>&1; then echo "Node.js 24+ / npm is required." >&2; exit 1; fi

if [ ! -d .venv ]; then "$PYTHON_BIN" -m venv .venv; fi
VENV_PY=".venv/bin/python"
"$VENV_PY" -m pip install -U pip
"$VENV_PY" -m pip install -e '.[dev]'
"$VENV_PY" -m alembic upgrade head
"$VENV_PY" samples/generate_demo_data.py
"$VENV_PY" samples/enrich_p1_data.py

(cd web && npm install)
echo "Setup complete. Run ./scripts/start-dev.sh"
