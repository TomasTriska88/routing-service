#!/bin/sh
set -eu
D=/tmp/rainwater-visual-20260820
LIVE=/config/www/lina-rainwater-card.js
CARD_BAK=/config/www/lina-rainwater-card.js.bak-visual-semaphore-savo-20260820-1913
USE_TEST=/config/tests/test_rainwater_use_semaphore_regression.py
USE_BAK=/config/tests/test_rainwater_use_semaphore_regression.py.bak-visual-20260820-1913
VIS_TEST=/config/tests/test_rainwater_visual_semantics_regression.py
OLD=9632f85d66c818a37e4eca6b67311f2c8d14d132b70bda209a9c3b279953ce23
NEW=8f7f34e08befe4aa809ce9601a4195aacb674d3abe2f49b2e814cb7a8fbada22
PATCH_SHA=008ae6c4b80beed5623c38c3acffa6501e02a235da7dd27e67296b22f8d469e6
VIS_SHA=0db2396c561d1e2d5139d9d4242bf967522e3c0a184394d78f495ce711d8c016
USE_SHA=fb1122aefdc202c002a9a316c247794a117a81e12032d7ef0b55cff155e57b38

hash() { sha256sum "$1" | cut -d' ' -f1; }
test "$(hash "$D/patch.py")" = "$PATCH_SHA"
test "$(hash "$D/test.py")" = "$VIS_SHA"
test "$(hash "$D/use_test.py")" = "$USE_SHA"
test "$(docker exec homeassistant sha256sum "$LIVE" | cut -d' ' -f1)" = "$OLD"

docker exec homeassistant cp -p "$LIVE" "$CARD_BAK"
docker exec homeassistant cp -p "$USE_TEST" "$USE_BAK"

cleanup_on_fail() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    docker exec homeassistant cp -p "$CARD_BAK" "$LIVE" || true
    docker exec homeassistant cp -p "$USE_BAK" "$USE_TEST" || true
    docker exec homeassistant rm -f "$VIS_TEST" || true
    echo RAINWATER_VISUAL_ROLLED_BACK
  fi
  exit "$rc"
}
trap cleanup_on_fail EXIT

cat "$D/patch.py" | docker exec -i homeassistant sh -c 'cat > /tmp/rainwater_visual_patch_20260820.py'
cat "$D/test.py" | docker exec -i homeassistant sh -c 'cat > /config/tests/test_rainwater_visual_semantics_regression.py'
cat "$D/use_test.py" | docker exec -i homeassistant sh -c 'cat > /config/tests/test_rainwater_use_semaphore_regression.py'

docker exec homeassistant python3 /tmp/rainwater_visual_patch_20260820.py
test "$(docker exec homeassistant sha256sum "$LIVE" | cut -d' ' -f1)" = "$NEW"
node --check /home/lina/osobni-pamet/homeassistant/config/www/lina-rainwater-card.js
docker exec homeassistant python3 "$VIS_TEST"
docker exec homeassistant python3 "$USE_TEST"

echo RAINWATER_VISUAL_NEW_SHA256="$(docker exec homeassistant sha256sum "$LIVE" | cut -d' ' -f1)"
echo RAINWATER_VISUAL_NEW_BYTES="$(docker exec homeassistant wc -c "$LIVE" | awk '{print $1}')"
echo RAINWATER_VISUAL_DEPLOY_TESTS_OK
trap - EXIT
exit 0
