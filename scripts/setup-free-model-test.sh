#!/usr/bin/env bash
# Optional, isolated, pinned public-model plugin installation for synthetic dev tests.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PLUGIN="$ROOT/.local/dsh-our-free-model-v2.7.2"
PROFILE="dataagent-headless-free"
HOME_DIR="$ROOT/.local/dsh-home-v0.2.1-rc.3"
DSH="$ROOT/agent/dsh/node_modules/.bin/dsh"
COMMIT="e1b347aec9cc956eda70a766219f028a811078e2"
[ -x "$DSH" ] || { echo 'Install DataControl Agent first: bash start.sh setup' >&2; exit 1; }
# dsh's plugin manager starts pnpm by name. Prefer pnpm already installed in
# DataControl's pinned dsh dependencies; no global Homebrew install required.
export PATH="$ROOT/agent/dsh/node_modules/.bin:$PATH"
if ! command -v pnpm >/dev/null 2>&1; then
  echo "Local dsh pnpm executable is missing. Run 'bash start.sh setup' or install pnpm; expected $ROOT/agent/dsh/node_modules/.bin/pnpm" >&2
  exit 1
fi

command -v git >/dev/null || { echo 'git is required' >&2; exit 1; }
mkdir -p "$ROOT/.local"
if [ ! -d "$PLUGIN/.git" ]; then
  git clone --depth 1 --branch v2.7.2 https://github.com/Ebony-Vinyl/dsh-our-free-model.git "$PLUGIN"
fi
[ "$(git -C "$PLUGIN" rev-parse HEAD)" = "$COMMIT" ] || {
  echo 'Pinned plugin release does not match its expected commit; refusing to install' >&2
  exit 1
}
export DSH_HOME="$HOME_DIR" DSH_TELEMETRY_MODE=DISABLED
PROFILE_DIR="$HOME_DIR/profiles/$PROFILE"
if [ ! -f "$PROFILE_DIR/package.json" ]; then
  "$DSH" --profile "$PROFILE" --from-default-profile headless --dump-config >/dev/null
fi
python_cmd="$ROOT/.venv/bin/python"
[ -x "$python_cmd" ] || { echo 'Missing .venv; run bash start.sh setup' >&2; exit 1; }
"$python_cmd" - "$ROOT/agent/dsh/profile/headless.patch.yml" "$PROFILE_DIR/cordis.patch.yml" <<'PY'
from pathlib import Path
import sys
text=Path(sys.argv[1]).read_text(encoding="utf-8")
old="provider: deepseek-official\n    model: deepseek-flash"
assert old in text, "Official model declaration changed: inspect before reinstall"
Path(sys.argv[2]).write_text(text.replace(old,"provider: our-free-model\n    model: kilo-auto/free"),encoding="utf-8")
PY
if [ ! -f "$PROFILE_DIR/node_modules/dsh-our-free-model/package.json" ]; then
  "$DSH" plugin --profile "$PROFILE" add "$PLUGIN"
fi
"$DSH" --profile "$PROFILE" --dump-config | grep -q 'our-free-model' || {
  echo 'Plugin not active in isolated profile; check compatibility with pinned dsh' >&2
  exit 1
}
printf 'v2.7.2; commit=%s\n' "$COMMIT" >"$ROOT/.local/free-model-test-v2.7.2.ready"
echo "Optional free-model test profile is ready. No extra environment switch is required."
