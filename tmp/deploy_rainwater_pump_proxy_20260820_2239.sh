#!/usr/bin/env bash
set -euo pipefail

ORIG_URL='https://raw.githubusercontent.com/TomasTriska88/routing-service/44f086d3039085e21e5cc137aa24f67617f5aa8d/tmp/rainwater_pump_proxy_patch_20260820_2228.py'
ORIG='/tmp/rainwater_pump_proxy_patch_20260820_2228.py'
REB='/tmp/rainwater_pump_proxy_patch_20260820_2239_rebased.py'
OLD_AUTO='09bdeb7a0125d4fb4156c9948526444244414cb62e05b4714061a22d39d981f3'
NEW_AUTO='ce315cd3c339b24b714ac6a1b73af0baf10dc47852b45fc073e3e07d1c1fb4c6'
CARD='8f7f34e08befe4aa809ce9601a4195aacb674d3abe2f49b2e814cb7a8fbada22'
ORIG_SHA='6144faed811632539348d1391bc0342a6ceca688dac1d9ef673946052fd34cae'
ORIG_BYTES='21721'

CURRENT_AUTO="$(docker exec homeassistant sha256sum /config/automations.yaml | awk '{print $1}')"
CURRENT_CARD="$(docker exec homeassistant sha256sum /config/www/lina-rainwater-card.js | awk '{print $1}')"
echo "CURRENT_AUTO_SHA256=$CURRENT_AUTO"
echo "CURRENT_CARD_SHA256=$CURRENT_CARD"
test "$CURRENT_AUTO" = "$NEW_AUTO"
test "$CURRENT_CARD" = "$CARD"

curl -fSsL --max-time 20 "$ORIG_URL" -o "$ORIG"
test "$(sha256sum "$ORIG" | awk '{print $1}')" = "$ORIG_SHA"
test "$(wc -c < "$ORIG" | tr -d ' ')" = "$ORIG_BYTES"

python3 - "$ORIG" "$REB" "$OLD_AUTO" "$NEW_AUTO" <<'PY'
from pathlib import Path
import sys
src, dst, old, new = sys.argv[1:]
text = Path(src).read_text(encoding="utf-8")
assert text.count(old) == 1, text.count(old)
text = text.replace(old, new, 1)
assert old not in text
assert text.count(new) == 1
Path(dst).write_text(text, encoding="utf-8")
print("RAINWATER_PATCH_REBASED")
PY

python3 -m py_compile "$REB"
REB_SHA="$(sha256sum "$REB" | awk '{print $1}')"
REB_BYTES="$(wc -c < "$REB" | tr -d ' ')"
echo "REBASED_SHA256=$REB_SHA"
echo "REBASED_BYTES=$REB_BYTES"

docker cp "$REB" homeassistant:/tmp/rainwater_pump_proxy_patch_20260820_2239_rebased.py
docker exec homeassistant python3 /tmp/rainwater_pump_proxy_patch_20260820_2239_rebased.py

echo "RAINWATER_PUMP_PROXY_DEPLOY_WRAPPER_OK"
