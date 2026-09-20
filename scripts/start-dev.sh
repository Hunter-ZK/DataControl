#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
if [ ! -x .venv/bin/python ]; then echo "Virtual environment not found. Run ./scripts/setup-dev.sh first." >&2; exit 1; fi
if ! command -v npm >/dev/null 2>&1; then echo "npm is required. Run ./scripts/setup-dev.sh first." >&2; exit 1; fi

.venv/bin/python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cleanup(){ kill "$BACKEND_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM
printf '\nDataControl API: http://127.0.0.1:8000\nDataControl Web: http://127.0.0.1:5173\n\n'
cd web
npm run dev
