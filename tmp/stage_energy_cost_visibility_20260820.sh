#!/bin/sh
set -eu
D=/tmp/energy-cost-visibility-20260820
rm -rf "$D"
mkdir -p "$D"
BASE='https://raw.githubusercontent.com/TomasTriska88/routing-service/1248d4e0ab09e44107cd9f00d4c880b0c07370b7'
curl -fSsL --max-time 20 "$BASE/tmp/patch_lina_energy_cost_visibility_20260820.py" -o "$D/patch.py"
curl -fSsL --max-time 20 "$BASE/tmp/test_lina_energy_cost_visibility_regression_20260820.js" -o "$D/test.js"
sha256sum "$D/patch.py" "$D/test.js"
wc -c "$D/patch.py" "$D/test.js"
docker cp homeassistant:/config/www/lina-energy-card.js "$D/live.js"
LIVE_SHA=$(sha256sum "$D/live.js" | awk '{print $1}')
echo LIVE_SHA="$LIVE_SHA"
test "$LIVE_SHA" = 'fc318bfaccd5191177c92244edf5560fadb2c56c204270b7d2661c064d654a8e'
python3 "$D/patch.py" "$D/live.js" "$D/staged.js"
node --check "$D/staged.js"
node "$D/test.js" "$D/staged.js"
STAGED_SHA=$(sha256sum "$D/staged.js" | awk '{print $1}')
STAGED_BYTES=$(wc -c < "$D/staged.js" | tr -d ' ')
echo STAGED_SHA="$STAGED_SHA"
echo STAGED_BYTES="$STAGED_BYTES"
echo ENERGY_COST_VISIBILITY_STAGE_OK
