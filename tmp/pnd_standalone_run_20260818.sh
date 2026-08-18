#!/bin/sh
set -u
BASE="$HOME/.local/share/markvarec-pnd"
mkdir -p "$BASE/bin"
GECKO=$(find "$HOME/.cache/selenium" -type f -name geckodriver -perm -u+x 2>/dev/null | sort | tail -n 1)
if [ -n "$GECKO" ]; then
    ln -sf "$GECKO" "$BASE/bin/geckodriver"
fi
export MARKVAREC_GECKODRIVER="$BASE/bin/geckodriver"
export PATH="$BASE/bin:$PATH"
export PYTHONPATH="$BASE/shim:$BASE/vendor:$BASE/upstream"
python3 "$BASE/run_standalone.py"
RC=$?
if [ -f "$BASE/state.json" ]; then
    docker cp "$BASE/state.json" homeassistant:/config/pnd_state.json >/dev/null 2>&1 || true
fi
exit "$RC"
