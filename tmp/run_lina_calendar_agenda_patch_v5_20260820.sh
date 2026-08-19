#!/usr/bin/env bash
set -euo pipefail

REF=9481da4aa451afdebab05db5a7eb9aaaf525e0fb
URL="https://raw.githubusercontent.com/TomasTriska88/routing-service/$REF/tmp/run_lina_calendar_agenda_patch_v2_20260819.sh"
W=/tmp/run_lina_calendar_agenda_patch_v2_fixed_v5_20260820.sh
trap 'rm -f "$W"' EXIT

curl -fsSL "$URL" -o "$W"
test "$(wc -c < "$W" | tr -d ' ')" = "2854"
test "$(sha256sum "$W" | awk '{print $1}')" = "6aedebe268af35119f57a05c88da7bfd80c203f75af92696e563f49c2f522a96"

python3 - "$W" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

replacements = [
    (
        '  node "$HOST/tests/test_lina_home_agenda_regression.js" 2>&1 &&',
        '  node "$HOST/tests/test_lina_home_agenda_regression.js" "$HOST/www/lina-home-card.js" 2>&1 &&',
        "todo test invocation",
    ),
    (
        '  node "$HOST/tests/test_lina_home_calendar_agenda_regression.js" 2>&1',
        '  node "$HOST/tests/test_lina_home_calendar_agenda_regression.js" "$HOST/www/lina-home-card.js" 2>&1',
        "calendar test invocation",
    ),
]
for old, new, label in replacements:
    if s.count(old) != 1:
        raise SystemExit(f"{label}: anchor count={s.count(old)}")
    s = s.replace(old, new, 1)

old_anchor = '''p.write_text(s, encoding="utf-8")
print("PATCH_SOURCE_ANCHOR_FIXED")'''
new_anchor = '''test_path_old = 'const sourcePath = "/config/www/lina-home-card.js";'
test_path_new = 'const sourcePath = process.argv[2];'
if s.count(test_path_old) != 1:
    raise SystemExit(f"calendar test source path anchor count={s.count(test_path_old)}")
s = s.replace(test_path_old, test_path_new, 1)
p.write_text(s, encoding="utf-8")
print("PATCH_SOURCE_ANCHOR_FIXED")
print("CALENDAR_TEST_SOURCE_PATH_FIXED")'''
if s.count(old_anchor) != 1:
    raise SystemExit(f"primary patch edit anchor count={s.count(old_anchor)}")
s = s.replace(old_anchor, new_anchor, 1)

p.write_text(s, encoding="utf-8")
print("TODO_TEST_INVOCATION_FIXED")
print("CALENDAR_TEST_INVOCATION_FIXED")
PY

bash -n "$W"
echo "V5_FIXED_V2_SHA256=$(sha256sum "$W" | awk '{print $1}')"
echo "V5_FIXED_V2_BYTES=$(wc -c < "$W" | tr -d ' ')"

bash "$W"
echo LINA_CALENDAR_V5_WRAPPER_OK
