#!/usr/bin/env bash
set -euo pipefail

REF=ce7c2a0d923931415d0de124ef823c1dd2ca6e56
URL="https://raw.githubusercontent.com/TomasTriska88/routing-service/$REF/tmp/patch_lina_calendar_agenda_20260819.py"
P=/tmp/patch_lina_calendar_agenda_20260819.py
HOST=/home/lina/osobni-pamet/homeassistant/config

curl -fsSL "$URL" -o "$P"
test "$(wc -c < "$P" | tr -d ' ')" = "16935"
test "$(sha256sum "$P" | awk '{print $1}')" = "f2e26b3c84f4d0d9405470a3ac29c19fb663c4d774a2778861282bb64878f5ba"

python3 - "$P" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
label = '    "constructor calendar state",\n)'
pos = s.find(label)
if pos < 0:
    raise SystemExit("constructor label not found")
start = s.rfind("src = replace_once(\n", 0, pos)
if start < 0:
    raise SystemExit("constructor replace block start not found")
block = s[start:pos + len(label)]
old_fragment = "'''    this._agendaTimer = null;\n  }'''"
new_fragment = "'''    this._agendaTimer = null;\n    this._calendarEvents = [];"
if block.count(old_fragment) != 1 or block.count(new_fragment) != 1:
    raise SystemExit(f"unexpected constructor block anchors old={block.count(old_fragment)} new={block.count(new_fragment)}")
block = block.replace(old_fragment, "'''    this._agendaRefreshPending = false;\n    this._agendaTimer = null;\n  }'''", 1)
block = block.replace(new_fragment, "'''    this._agendaRefreshPending = false;\n    this._agendaTimer = null;\n    this._calendarEvents = [];", 1)
s = s[:start] + block + s[pos + len(label):]
p.write_text(s, encoding="utf-8")
print("PATCH_SOURCE_ANCHOR_FIXED")
PY

python3 -m py_compile "$P"
echo "FIXED_PATCH_SHA256=$(sha256sum "$P" | awk '{print $1}')"
echo "FIXED_PATCH_BYTES=$(wc -c < "$P" | tr -d ' ')"

PATCH_OUT="$(docker exec -i homeassistant python3 - < "$P")"
printf '%s\n' "$PATCH_OUT"
HOME_BACKUP="$(printf '%s\n' "$PATCH_OUT" | sed -n 's/^HOME_BACKUP=//p')"
RESOURCE_BACKUP="$(printf '%s\n' "$PATCH_OUT" | sed -n 's/^RESOURCE_BACKUP=//p')"
test -n "$HOME_BACKUP"
test -n "$RESOURCE_BACKUP"

set +e
VALID_OUT="$(
  node --check "$HOST/www/lina-home-card.js" 2>&1 &&
  node "$HOST/tests/test_lina_home_agenda_regression.js" 2>&1 &&
  node "$HOST/tests/test_lina_home_calendar_agenda_regression.js" 2>&1
)"
VALID_RC=$?
set -e
printf '%s\n' "$VALID_OUT"

if [ "$VALID_RC" -ne 0 ]; then
  docker exec homeassistant sh -lc "cp '$HOME_BACKUP' /config/www/lina-home-card.js; cp '$RESOURCE_BACKUP' /config/.storage/lovelace_resources; rm -f /config/tests/test_lina_home_calendar_agenda_regression.js"
  echo LINA_CALENDAR_AGENDA_VALIDATION_FAILED_ROLLED_BACK
  exit 82
fi

rm -f "$P" "${P}c"
echo "LIVE_HOME_SHA256=$(sha256sum "$HOST/www/lina-home-card.js" | awk '{print $1}')"
echo "LIVE_HOME_BYTES=$(wc -c < "$HOST/www/lina-home-card.js" | tr -d ' ')"
echo LINA_CALENDAR_AGENDA_DEPLOY_VALIDATED
