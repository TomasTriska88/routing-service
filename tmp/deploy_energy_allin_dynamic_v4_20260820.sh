#!/usr/bin/env bash
set -euo pipefail

D=/tmp/energy-allin-dynamic-stage
ST=/tmp/energy-allin-dynamic-v4
CARD=/config/www/lina-energy-card.js
CFG=/config/configuration.yaml
STAMP=20260820-2324-v4
BKC="/config/www/lina-energy-card.js.bak-allin-dynamic-${STAMP}"
BKG="/config/configuration.yaml.bak-energy-allin-dynamic-${STAMP}"

test "$(sha256sum "$D/card_patch.py" | awk '{print $1}')" = "13fd51af574055ce11273275274eebfed8ce60bb51c60742f158eec5c63a3f48"
test "$(sha256sum "$D/card_test.js" | awk '{print $1}')" = "ab208bbb7defd14ca1eacd2d8bc7c88cf3c3090710e9a648bdbae8299e50a590"
test "$(sha256sum "$D/config_patch.py" | awk '{print $1}')" = "2feb5ba70c9ebb55aa230aeebca3f0c4d066cc1e22118b32fab9403494a6be2c"
test "$(sha256sum "$D/config_test.py" | awk '{print $1}')" = "63fbaa893f4b34607e1013ff17b0d3d956826686983887bbf8e4b1281e52ce9b"

rm -rf "$ST"
mkdir -p "$ST"
docker cp "homeassistant:$CFG" "$ST/configuration.yaml"
docker cp "homeassistant:$CARD" "$ST/card.js"

CURRENT_CARD_SHA="$(sha256sum "$ST/card.js" | awk '{print $1}')"
test "$CURRENT_CARD_SHA" = "628fdab2ff5dbc6bb50ea7727ede5fdbdcd8e94aa6ac613fbb613a4c092f109f"

python3 "$D/config_patch.py" "$ST/configuration.yaml"

python3 -c 'from pathlib import Path; import sys; p=Path(sys.argv[1]); s=p.read_text(encoding="utf-8"); old="20260820-allin-price-r1"; new="20260820-allin-dynamic-r2"; assert s.count(old)==2,s.count(old); p.write_text(s.replace(old,new,1),encoding="utf-8")' "$ST/card.js"
python3 "$D/card_patch.py" "$ST/card.js"
node --check "$ST/card.js"
node "$D/card_test.js" "$ST/card.js"

python3 -c 'from pathlib import Path; import sys; s=Path(sys.argv[1]).read_text(encoding="utf-8"); s=s.replace("from pathlib import Path\n\n","from pathlib import Path\nimport sys\n\n",1).replace("Path(\"/config/configuration.yaml\")","Path(sys.argv[1])",1); Path(sys.argv[2]).write_text(s,encoding="utf-8")' "$D/config_test.py" "$ST/config_test_stage.py"
python3 -m py_compile "$ST/config_test_stage.py"
python3 "$ST/config_test_stage.py" "$ST/configuration.yaml"

STAGED_CFG_SHA="$(sha256sum "$ST/configuration.yaml" | awk '{print $1}')"
STAGED_CARD_SHA="$(sha256sum "$ST/card.js" | awk '{print $1}')"

docker exec homeassistant cp -p "$CFG" "$BKG"
docker exec homeassistant cp -p "$CARD" "$BKC"

rollback() {
  docker exec homeassistant cp -p "$BKG" "$CFG" || true
  docker exec homeassistant cp -p "$BKC" "$CARD" || true
  echo ENERGY_ALLIN_DYNAMIC_V4_ROLLED_BACK
}
trap rollback ERR

docker cp "$ST/configuration.yaml" "homeassistant:$CFG.new-energy-allin-v4"
docker cp "$ST/card.js" "homeassistant:$CARD.new-energy-allin-v4"
docker cp "$D/config_test.py" "homeassistant:/config/tests/test_energy_allin_config_regression.py"
docker cp "$D/card_test.js" "homeassistant:/config/tests/test_lina_energy_allin_dynamic_regression_20260820.js"

docker exec homeassistant mv "$CFG.new-energy-allin-v4" "$CFG"
docker exec homeassistant mv "$CARD.new-energy-allin-v4" "$CARD"

docker exec homeassistant python3 /config/tests/test_energy_allin_config_regression.py
docker cp "homeassistant:$CARD" "$ST/card.live.js"
node --check "$ST/card.live.js"
node "$D/card_test.js" "$ST/card.live.js"

trap - ERR
echo "CURRENT_CARD_SHA=$CURRENT_CARD_SHA"
echo "STAGED_CFG_SHA=$STAGED_CFG_SHA"
echo "LIVE_CFG_SHA=$(docker exec homeassistant sha256sum "$CFG" | awk '{print $1}')"
echo "STAGED_CARD_SHA=$STAGED_CARD_SHA"
echo "LIVE_CARD_SHA=$(docker exec homeassistant sha256sum "$CARD" | awk '{print $1}')"
echo "BACKUP_CFG=$BKG"
echo "BACKUP_CARD=$BKC"
echo ENERGY_ALLIN_DYNAMIC_V4_DEPLOY_OK
