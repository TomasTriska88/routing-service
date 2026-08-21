#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_SHA = "e1ade30ff11ba13ae6cc2b61f5c952fe3eaf5ce621b8666087bf5cff24f1ded7"

if len(sys.argv) != 3:
    raise SystemExit("usage: patch.py INPUT OUTPUT")

src_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
data = src_path.read_bytes()
sha = hashlib.sha256(data).hexdigest()
assert sha == EXPECTED_SHA, f"unexpected live sha: {sha}"

s = data.decode("utf-8")

old_marker = "20260821-smart-sharebar-r1"
new_marker = "20260821-smart-sharebar-r2"
assert s.count(old_marker) == 2, f"version marker count={s.count(old_marker)}"
s = s.replace(old_marker, new_marker)

old_css = '''        .smart-sharebar-parents {
          background:var(--secondary-text-color);
          color:var(--card-background-color, #fff);
        }'''
new_css = '''        .smart-sharebar-parents {
          background:#ef6c00;
          color:#fff;
        }'''
assert s.count(old_css) == 1, "parent sharebar CSS anchor mismatch"
s = s.replace(old_css, new_css, 1)

old_label = '    const monthCostLabel = a.month.complete ? "Měsíc celkem" : "Odhad celkem";'
new_label = '    const monthCostLabel = a.month.complete ? "Markvarec · měsíc celkem" : "Markvarec · odhad celkem";'
assert s.count(old_label) == 1, "month cost label anchor mismatch"
s = s.replace(old_label, new_label, 1)

out_path.write_text(s, encoding="utf-8")
print(f"PATCH_OK old_sha={sha} new_sha={hashlib.sha256(s.encode('utf-8')).hexdigest()} bytes={len(s.encode('utf-8'))}")
