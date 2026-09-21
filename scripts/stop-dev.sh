#!/usr/bin/env bash
set -euo pipefail

# Stop only listeners whose command lines match DataControl-owned process markers.
# This mirrors scripts/stop-dev.ps1 and refuses to kill unrelated processes.
TARGETS=(
  "8000|backend.app.main:app|DataControl API"
  "8900|agent3.adapters.mcp.server|Agent3 MCP"
  "8910|dataagent_gateway.app:app|DataAgent Gateway"
)

listener_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
    return
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "$port" 2>/dev/null | tr ' ' '\n' | sed '/^$/d' || true
    return
  fi
  echo "Neither lsof nor fuser is available; cannot safely identify the listener on port $port." >&2
  return 2
}

for target in "${TARGETS[@]}"; do
  IFS='|' read -r port marker name <<<"$target"
  mapfile_supported=true
  if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
    mapfile_supported=false
  fi

  if [[ "$mapfile_supported" == true ]]; then
    mapfile -t pids < <(listener_pids "$port")
  else
    # macOS still ships Bash 3.2 by default, where mapfile is unavailable.
    pids=()
    while IFS= read -r pid; do
      [[ -n "$pid" ]] && pids+=("$pid")
    done < <(listener_pids "$port")
  fi

  if [[ "${#pids[@]}" -eq 0 ]]; then
    echo "$name: no listener on $port"
    continue
  fi

  for pid in "${pids[@]}"; do
    command_line="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$command_line" != *"$marker"* ]]; then
      echo "$name port $port is owned by PID $pid, but its command line does not match DataControl marker '$marker'. Refusing to kill an unrelated process." >&2
      exit 1
    fi
    kill "$pid"
    echo "$name: stopped stale DataControl process PID $pid on port $port"
  done
done
