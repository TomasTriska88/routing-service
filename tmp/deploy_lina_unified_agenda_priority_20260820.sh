#!/usr/bin/env bash
set -euo pipefail

REF="${1:?pinned commit required}"
HOST=/home/lina/osobni-pamet/homeassistant/config
BASE_URL="https://raw.githubusercontent.com/TomasTriska88/routing-service/${REF}/tmp/patch_lina_unified_agenda_priority_20260820.py"
FIX_URL="https://raw.githubusercontent.com/TomasTriska88/routing-service/${REF}/tmp/fix_lina_unified_priority_test_fixture_20260820.py"
P=/tmp/patch_lina_unified_agenda_priority_20260820.py
F=/tmp/fix_lina_unified_priority_test_fixture_20260820.py
STAMP="$(date +%Y%m%d-%H%M%S)"
HOME_BAK="$HOST/www/lina-home-card.js.bak-unified-priority-$STAMP"
RES_BAK="$HOST/.storage/lovelace_resources.bak-unified-priority-$STAMP"
TEST_BAK="$HOST/tests/test_lina_home_calendar_agenda_regression.js.bak-unified-priority-$STAMP"
MUTATED=0

cleanup() {
  rm -f "$P" "$F" /tmp/__pycache__/patch_lina_unified_agenda_priority_20260820.* /tmp/__pycache__/fix_lina_unified_priority_test_fixture_20260820.* 2>/dev/null || true
  docker exec homeassistant rm -f /tmp/patch_lina_unified_agenda_priority_20260820.py /tmp/fix_lina_unified_priority_test_fixture_20260820.py >/dev/null 2>&1 || true
}
rollback() {
  [ "$MUTATED" = 1 ] || return 0
  echo LINA_UNIFIED_PRIORITY_ROLLBACK_BEGIN >&2
  docker exec homeassistant cp "/config/www/lina-home-card.js.bak-unified-priority-$STAMP" /config/www/lina-home-card.js
  docker exec homeassistant cp "/config/.storage/lovelace_resources.bak-unified-priority-$STAMP" /config/.storage/lovelace_resources
  docker exec homeassistant cp "/config/tests/test_lina_home_calendar_agenda_regression.js.bak-unified-priority-$STAMP" /config/tests/test_lina_home_calendar_agenda_regression.js
  node --check "$HOST/www/lina-home-card.js"
  node "$HOST/tests/test_lina_home_agenda_regression.js" "$HOST/www/lina-home-card.js"
  node "$HOST/tests/test_lina_home_calendar_agenda_regression.js" "$HOST/www/lina-home-card.js"
  echo LINA_UNIFIED_PRIORITY_ROLLED_BACK >&2
}
finish() {
  rc=$?
  if [ "$rc" -ne 0 ]; then rollback || true; fi
  cleanup
  exit "$rc"
}
trap finish EXIT

curl -fsSL "$BASE_URL" -o "$P"
curl -fsSL "$FIX_URL" -o "$F"
test "$(wc -c < "$P" | tr -d ' ')" = 16560
test "$(sha256sum "$P" | awk '{print $1}')" = f1364d3c9189d2e3db97765eb8eca1224d60ea5bc0377e7dad70a9e971b7e5ec
test "$(wc -c < "$F" | tr -d ' ')" = 1343
test "$(sha256sum "$F" | awk '{print $1}')" = b74e4ace7647319c64a772c999cb565f190c7408d0822450a1a95b7404bd38c7
python3 -m py_compile "$P" "$F"

docker cp "$P" homeassistant:/tmp/patch_lina_unified_agenda_priority_20260820.py >/dev/null
docker cp "$F" homeassistant:/tmp/fix_lina_unified_priority_test_fixture_20260820.py >/dev/null
docker exec homeassistant python3 /tmp/patch_lina_unified_agenda_priority_20260820.py "$STAMP"
MUTATED=1
docker exec homeassistant python3 /tmp/fix_lina_unified_priority_test_fixture_20260820.py /config/tests/test_lina_home_calendar_agenda_regression.js

node --check "$HOST/www/lina-home-card.js"
node "$HOST/tests/test_lina_home_agenda_regression.js" "$HOST/www/lina-home-card.js"
node "$HOST/tests/test_lina_home_calendar_agenda_regression.js" "$HOST/www/lina-home-card.js"
python3 - "$HOST" <<'PY'
import hashlib, json, sys
from pathlib import Path
root=Path(sys.argv[1])
home=root/'www/lina-home-card.js'
s=home.read_text(encoding='utf-8')
r=json.loads((root/'.storage/lovelace_resources').read_text(encoding='utf-8'))
def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x,list):
        for v in x: yield from walk(v)
urls=[x.get('url') for x in walk(r) if isinstance(x.get('url'),str) and 'lina-home-card.js' in x.get('url')]
assert urls == ['/local/lina-home-card.js?v=20260820-agenda-unified-r1'], urls
assert s.count('Markvarec Lina agenda: 20260820-agenda-unified-r1') == 1
assert '_combinedAgenda(nowMs = Date.now())' in s
b=home.read_bytes()
print('LIVE_HOME_SHA256='+hashlib.sha256(b).hexdigest())
print('LIVE_HOME_BYTES='+str(len(b)))
print('LIVE_RESOURCE_URL='+urls[0])
PY

echo LINA_UNIFIED_PRIORITY_DEPLOY_VALIDATED
