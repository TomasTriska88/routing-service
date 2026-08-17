#!/bin/sh
set -eu

PY_URL="https://raw.githubusercontent.com/TomasTriska88/routing-service/d7ae15dd263e81e4edbefaa6c6ee6834b0d59092/tmp/markvarec_camera_push_sync_20260818.py"
PY_SHA="edd8de5a284037d2904496a5276d2924dff342941182926bc7a65397cd64a36a"
HOST_TMP="/tmp/markvarec_camera_push_sync_install.py"

curl -fL --retry 2 "$PY_URL" -o "$HOST_TMP"
printf '%s  %s\n' "$PY_SHA" "$HOST_TMP" | sha256sum -c -
[ "$(wc -c < "$HOST_TMP" | tr -d ' ')" -eq 13286 ]
docker cp "$HOST_TMP" homeassistant:/tmp/markvarec_camera_push_sync_install.py

docker exec -i homeassistant sh -s <<'SH'
set -eu
SRC=/tmp/markvarec_camera_push_sync_install.py
DST=/config/custom_components/markvarec_camera_push_sync
CFG=/config/configuration.yaml
STAMP=$(date +%Y%m%d-%H%M%S)
SHA=edd8de5a284037d2904496a5276d2924dff342941182926bc7a65397cd64a36a

[ "$(sha256sum "$SRC" | awk '{print $1}')" = "$SHA" ]
[ "$(wc -c < "$SRC" | tr -d ' ')" -eq 13286 ]
python3 -m py_compile "$SRC"

mkdir -p "$DST"
cp "$CFG" "$CFG.bak-camera-push-$STAMP"
if [ -f "$DST/__init__.py" ]; then cp "$DST/__init__.py" "$DST/__init__.py.bak-$STAMP"; fi
if [ -f "$DST/manifest.json" ]; then cp "$DST/manifest.json" "$DST/manifest.json.bak-$STAMP"; fi

cp "$SRC" "$DST/__init__.py.new"
python3 -m py_compile "$DST/__init__.py.new"
mv "$DST/__init__.py.new" "$DST/__init__.py"

printf '%s\n' '{"domain":"markvarec_camera_push_sync","name":"Markvarec Camera Vendor Push Sync","version":"1.0.0","after_dependencies":["ezviz","imou_life"]}' > "$DST/manifest.json.new"
python3 -m json.tool "$DST/manifest.json.new" >/dev/null
mv "$DST/manifest.json.new" "$DST/manifest.json"

python3 - <<'PY'
from pathlib import Path
p=Path("/config/configuration.yaml")
s=p.read_text(encoding="utf-8")
needle="markvarec_camera_push_sync:"
if not any(line.strip()==needle for line in s.splitlines()):
    if s and not s.endswith("\n"):
        s += "\n"
    s += "\nmarkvarec_camera_push_sync:\n"
    p.write_text(s, encoding="utf-8")
    print("CONFIG_ENTRY_ADDED")
else:
    print("CONFIG_ENTRY_ALREADY_PRESENT")
PY

echo "CAMERA_PUSH_SYNC_INSTALLED"
echo "SOURCE_SHA=$(sha256sum "$DST/__init__.py" | awk '{print $1}')"
echo "BACKUP_CFG=$CFG.bak-camera-push-$STAMP"
SH
