#!/bin/sh
set -eu
FILES_COMMIT=a89ec4b1d1b1cd54e620665857d1abec22a31710
BASE="https://raw.githubusercontent.com/TomasTriska88/routing-service/$FILES_COMMIT/tmp/markvarec_camera_events_20260818"
STAGE=/tmp/markvarec_camera_events_stage
rm -rf "$STAGE"
mkdir -p "$STAGE"
curl -fsSL "$BASE/__init__.py" -o "$STAGE/__init__.py"
curl -fsSL "$BASE/manifest.json" -o "$STAGE/manifest.json"
curl -fsSL "$BASE/services.yaml" -o "$STAGE/services.yaml"
[ "$(wc -c < "$STAGE/__init__.py" | tr -d ' ')" -eq 16480 ]
[ "$(wc -c < "$STAGE/manifest.json" | tr -d ' ')" -eq 211 ]
[ "$(wc -c < "$STAGE/services.yaml" | tr -d ' ')" -eq 749 ]
[ "$(git hash-object "$STAGE/__init__.py")" = "080341504a21f19c39db1da6d577dbcd5e095f5c" ]
[ "$(git hash-object "$STAGE/manifest.json")" = "f4ece8ea37c61874b1bc4c9b535bf285ae4bfa89" ]
[ "$(git hash-object "$STAGE/services.yaml")" = "e52cbb790a46b2569155ec38ed51bae438dced4b" ]
echo '=== HOST_STAGE ==='
wc -c "$STAGE"/__init__.py "$STAGE"/manifest.json "$STAGE"/services.yaml
sha256sum "$STAGE"/__init__.py "$STAGE"/manifest.json "$STAGE"/services.yaml
python3 -m py_compile "$STAGE/__init__.py"
python3 -c 'import json; json.load(open("/tmp/markvarec_camera_events_stage/manifest.json")); print("HOST_JSON_OK")'
docker exec homeassistant rm -rf /tmp/markvarec_camera_events_stage
docker cp "$STAGE" homeassistant:/tmp/markvarec_camera_events_stage >/dev/null
H1=$(sha256sum "$STAGE/__init__.py" | awk '{print $1}')
H2=$(sha256sum "$STAGE/manifest.json" | awk '{print $1}')
H3=$(sha256sum "$STAGE/services.yaml" | awk '{print $1}')
C1=$(docker exec homeassistant sha256sum /tmp/markvarec_camera_events_stage/__init__.py | awk '{print $1}')
C2=$(docker exec homeassistant sha256sum /tmp/markvarec_camera_events_stage/manifest.json | awk '{print $1}')
C3=$(docker exec homeassistant sha256sum /tmp/markvarec_camera_events_stage/services.yaml | awk '{print $1}')
[ "$H1" = "$C1" ]
[ "$H2" = "$C2" ]
[ "$H3" = "$C3" ]
echo '=== CONTAINER_STAGE ==='
docker exec homeassistant sh -lc 'wc -c /tmp/markvarec_camera_events_stage/__init__.py /tmp/markvarec_camera_events_stage/manifest.json /tmp/markvarec_camera_events_stage/services.yaml; sha256sum /tmp/markvarec_camera_events_stage/__init__.py /tmp/markvarec_camera_events_stage/manifest.json /tmp/markvarec_camera_events_stage/services.yaml; python3 -m py_compile /tmp/markvarec_camera_events_stage/__init__.py; python3 -c '"'"'import json,yaml; json.load(open("/tmp/markvarec_camera_events_stage/manifest.json")); yaml.safe_load(open("/tmp/markvarec_camera_events_stage/services.yaml")); print("CONTAINER_JSON_YAML_OK")'"'"''
echo CAMERA_INBOX_STAGE_VERIFIED
