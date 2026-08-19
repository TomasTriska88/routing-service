#!/bin/bash
set -euo pipefail

PATCH_URL='https://raw.githubusercontent.com/TomasTriska88/routing-service/0f93e0d0a316c6f1fe245177aed033297bb82a42/tmp/patch_hnizdo_tvread_v5_20260819.py'
PATCH=/tmp/patch_hnizdo_tvread_v5_20260819.py
PATCH_BYTES=6269
PATCH_SHA='35fff6b21236b038fab417ac89091ca0b894f794c640137277f91180a2dfd816'
STAMP='20260819-1210-tvread-v5'
MARKER='Markvarec TV balanced hierarchy profile: 20260819-tvread-v5'
FILES='lina-home-card.js lina-weather-card.js lina-security-card.js lina-climate-safety-card.js lina-energy-card.js lina-rainwater-card.js'

rollback() {
  for f in $FILES; do
    docker exec homeassistant sh -lc "test -f /config/www/$f.bak-$STAMP && cp /config/www/$f.bak-$STAMP /config/www/$f || true" || true
  done
}
trap 'rc=$?; if [ "$rc" -ne 0 ]; then rollback; fi; exit "$rc"' EXIT

curl -fsSL "$PATCH_URL" -o "$PATCH"
test "$(wc -c < "$PATCH" | tr -d ' ')" = "$PATCH_BYTES"
test "$(sha256sum "$PATCH" | awk '{print $1}')" = "$PATCH_SHA"

docker cp "$PATCH" homeassistant:/tmp/patch_hnizdo_tvread_v5_20260819.py >/dev/null
docker exec homeassistant python3 /tmp/patch_hnizdo_tvread_v5_20260819.py

for f in $FILES; do
  T="/tmp/hnizdo-v5-$f"
  docker cp "homeassistant:/config/www/$f" "$T" >/dev/null
  node --check "$T" >/dev/null
  test "$(grep -cF "$MARKER" "$T")" -eq 1
done

export DISPLAY=:0
export XAUTHORITY=/home/lina/.Xauthority
W="$(wmctrl -lGx | awk 'tolower($0) ~ /firefox/ {print $1; exit}')"
test -n "$W"
wmctrl -ia "$W"
sleep 0.4
xdotool key --clearmodifiers ctrl+shift+r
sleep 1.5
wmctrl -lGx | awk 'tolower($0) ~ /firefox/ {print; exit}'

trap - EXIT
rm -f "$PATCH" /tmp/hnizdo-v5-*.js
echo HNIZDO_TVREAD_V5_DEPLOY_OK
