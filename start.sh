#!/usr/bin/env bash
# macOS/Linux one-command launcher. Always invoke with: bash start.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

action="${1:-start}"
case "$action" in
  start)
    if [ ! -x .venv/bin/python ] || [ ! -x web/node_modules/.bin/vite ]; then
      echo "[DataControl] First start: installing missing Portal/Web/Agent dependencies..."
      bash scripts/setup-dev.sh
    fi
    exec bash scripts/start-dev.sh
    ;;
  setup)
    bash scripts/setup-dev.sh
    ;;
  repair)
    if [ ! -x .venv/bin/python ] || [ ! -x web/node_modules/.bin/vite ]; then
      bash scripts/setup-dev.sh
    else
      bash scripts/setup-agent.sh
    fi
    exec bash scripts/start-dev.sh
    ;;
  stop)
    exec bash scripts/stop-dev.sh
    ;;
  *)
    echo "Usage: bash start.sh [start|setup|repair|stop]" >&2
    exit 2
    ;;
esac
