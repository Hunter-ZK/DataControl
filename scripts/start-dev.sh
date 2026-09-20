#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x .venv/bin/python ]; then
  echo "Virtual environment not found. Run ./scripts/setup-dev.sh first." >&2
  exit 1
fi

exec .venv/bin/python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
