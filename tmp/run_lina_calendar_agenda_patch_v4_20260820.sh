#!/usr/bin/env bash
set -euo pipefail

REF=9481da4aa451afdebab05db5a7eb9aaaf525e0fb
URL="https://raw.githubusercontent.com/TomasTriska88/routing-service/$REF/tmp/run_lina_calendar_agenda_patch_v2_20260819.sh"
W=/tmp/run_lina_calendar_agenda_patch_v2_fixed_20260820.sh

curl -fsSL "$URL" -o "$W"
test "$(wc -c < "$W" | tr -d ' ')" = "2854"
test "$(sha256sum "$W" | awk '{print $1}')" = "6aedebe268af35119f57a05c88da7bfd80c203f75af92696e563f49c2f522a96"

python3 - "$W" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old = '  node "$HOST/tests/test_lina_home_agenda_regression.js" 2>&1 &&'
new = '  node "$HOST/tests/test_lina_home_agenda_regression.js" "$HOST/www/lina-home-card.js" 2>&1 &&'
if s.count(old) != 1:
    raise SystemExit(f"todo regression invocation anchor count={s.count(old)}")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("TODO_TEST_INVOCATION_FIXED")
PY

bash -n "$W"
echo "V4_FIXED_V2_SHA256=$(sha256sum "$W" | awk '{print $1}')"
echo "V4_FIXED_V2_BYTES=$(wc -c < "$W" | tr -d ' ')"

set +e
bash "$W"
RC=$?
set -e
rm -f "$W"
exit "$RC"
