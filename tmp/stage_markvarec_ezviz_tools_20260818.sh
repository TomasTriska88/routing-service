#!/bin/sh
set -eu
COMMIT=0a7cc00b7ce7e61b62535afa64eb05d0671c1504
BASE="https://raw.githubusercontent.com/TomasTriska88/routing-service/$COMMIT/tmp/markvarec_ezviz_tools_20260818"
STAGE=/tmp/markvarec_ezviz_tools_stage
rm -rf "$STAGE"
mkdir -p "$STAGE"
curl -fsSL "$BASE/__init__.py" -o "$STAGE/__init__.py"
curl -fsSL "$BASE/manifest.json" -o "$STAGE/manifest.json"
curl -fsSL "$BASE/services.yaml" -o "$STAGE/services.yaml"
[ "$(wc -c < "$STAGE/__init__.py" | tr -d ' ')" -eq 3707 ]
[ "$(wc -c < "$STAGE/manifest.json" | tr -d ' ')" -eq 181 ]
[ "$(wc -c < "$STAGE/services.yaml" | tr -d ' ')" -eq 170 ]
[ "$(sha256sum "$STAGE/__init__.py" | awk '{print $1}')" = "229edc5cf6e7a3e8f46ea74bba8cb617c6421a608c9ff36266ed05bbdd747934" ]
[ "$(sha256sum "$STAGE/manifest.json" | awk '{print $1}')" = "f9d69c18bd3546ad34db8283087176b604d6b0b7f140550e36afae3eaededeee" ]
[ "$(sha256sum "$STAGE/services.yaml" | awk '{print $1}')" = "a282c14b44433d744555fdb60ce9a542f9b47cd5c4a7ad264f7c7aea59fa9f3a" ]
python3 -m py_compile "$STAGE/__init__.py"
docker exec homeassistant rm -rf /tmp/markvarec_ezviz_tools_stage
docker cp "$STAGE" homeassistant:/tmp/markvarec_ezviz_tools_stage >/dev/null
docker exec -i homeassistant python3 - <<'PY'
from pathlib import Path
import json, py_compile, yaml
base=Path("/tmp/markvarec_ezviz_tools_stage")
py_compile.compile(str(base/"__init__.py"), doraise=True)
json.loads((base/"manifest.json").read_text(encoding="utf-8"))
yaml.safe_load((base/"services.yaml").read_text(encoding="utf-8"))
src=(base/"__init__.py").read_text(encoding="utf-8")
assert 'DVUR_SERIAL = "BF0029567"' in src
assert 'ptz_control' not in src
print("CAMERA_EZVIZ_TOOLS_STAGE_OK")
PY
