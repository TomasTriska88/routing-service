#!/usr/bin/env bash
set -euo pipefail
EXPECTED_WATER_BLOCK_SHA="${1:?expected water block sha required}"
V2=/tmp/deploy_rainwater_pump_proxy_v2_20260820.sh
V3=/tmp/deploy_rainwater_pump_proxy_v3_20260820.sh
test "$(sha256sum "$V2" | awk '{print $1}')" = "8c10c89aeda4884bde4fd8ddb3929f4873137c214bdcc826b5ff74e0fe51237d"
test "$(wc -c < "$V2" | tr -d ' ')" = "10549"
python3 - "$V2" "$V3" <<'PY'
from pathlib import Path
import sys
src,dst=sys.argv[1:]
s=Path(src).read_text(encoding='utf-8')
old="ORIG_BYTES='21721'"
new="ORIG_BYTES='21867'"
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)
Path(dst).write_text(s,encoding='utf-8')
PY
bash -n "$V3"
echo "V3_SHA256=$(sha256sum "$V3" | awk '{print $1}')"
echo "V3_BYTES=$(wc -c < "$V3" | tr -d ' ')"
bash "$V3" "$EXPECTED_WATER_BLOCK_SHA"
