#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "/config/tests/test_lina_home_calendar_agenda_regression.js")
s = p.read_text(encoding="utf-8")
old = "ranked.map(x => x.title)"
new = "Array.from(ranked, x => x.title)"
count = s.count(old)
if count != 6:
    raise SystemExit(f"REALM_FIX_ANCHOR_COUNT={count}")
p.write_text(s.replace(old, new), encoding="utf-8")
print("LINA_UNIFIED_PRIORITY_TEST_REALM_FIXED")
