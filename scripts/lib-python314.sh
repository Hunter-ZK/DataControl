#!/usr/bin/env bash
# Shared Python 3.14 discovery for the embedded DataAgent.
# Keep this file sourceable from Bash 3.2+ (macOS system Bash).

resolve_python314() {
  local candidate resolved brew_prefix pyenv_candidate

  for candidate in \
    "${PYTHON314_BIN:-}" \
    python3.14 \
    python3 \
    python \
    /opt/homebrew/bin/python3.14 \
    /usr/local/bin/python3.14
  do
    [ -n "$candidate" ] || continue
    if [[ "$candidate" == */* ]]; then
      [ -x "$candidate" ] || continue
      resolved="$candidate"
    else
      resolved="$(command -v "$candidate" 2>/dev/null || true)"
      [ -n "$resolved" ] || continue
    fi
    if "$resolved" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done

  if command -v brew >/dev/null 2>&1; then
    brew_prefix="$(brew --prefix python@3.14 2>/dev/null || true)"
    if [ -n "$brew_prefix" ]; then
      candidate="$brew_prefix/bin/python3.14"
      if [ -x "$candidate" ] && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)' >/dev/null 2>&1; then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  fi

  if command -v pyenv >/dev/null 2>&1; then
    pyenv_candidate="$(pyenv which python3.14 2>/dev/null || true)"
    if [ -n "$pyenv_candidate" ] && [ -x "$pyenv_candidate" ] && "$pyenv_candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "$pyenv_candidate"
      return 0
    fi
  fi

  return 1
}

print_python314_help() {
  echo "Python 3.14 is required for the embedded DataAgent, but no usable 3.14 interpreter was found." >&2
  echo "Checked PYTHON314_BIN, python3.14, python3, python, Homebrew default prefixes, and pyenv." >&2
  if command -v brew >/dev/null 2>&1; then
    echo "On this Mac you can install it with: brew install python@3.14" >&2
    echo "Then rerun: bash ./scripts/setup-agent.sh" >&2
  else
    echo "Install Python 3.14, or set PYTHON314_BIN to the interpreter path, then rerun ./scripts/setup-agent.sh." >&2
  fi
}
