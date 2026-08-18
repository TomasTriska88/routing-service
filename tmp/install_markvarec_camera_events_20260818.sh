#!/bin/sh
set -eu
docker exec -i homeassistant sh -s <<'SH'
set -eu
SRC=/tmp/markvarec_camera_events_stage
DST=/config/custom_components/markvarec_camera_events
TMPDST=/config/custom_components/.markvarec_camera_events.new
CFG=/config/configuration.yaml
[ -d "$SRC" ]
[ ! -e "$DST" ]
[ "$(sha256sum "$SRC/__init__.py" | awk '{print $1}')" = "70d07d7b2e15cc86e3ee549029daba2a3ee6af469917a3eebdd8f3d7c1b49a8f" ]
[ "$(sha256sum "$SRC/manifest.json" | awk '{print $1}')" = "0c31c99fd10a8d8507939e7a2a7ce6691aaabecd88d16cb4a997234e80026013" ]
[ "$(sha256sum "$SRC/services.yaml" | awk '{print $1}')" = "f6cba63dade72c4a14e8b1e44ee7e8b615b47e6c773f45d3fd654e6c9baf778d" ]
TS=$(date +%Y%m%d-%H%M%S)
BACKUP="$CFG.bak-camera-inbox-$TS"
cp "$CFG" "$BACKUP"
rm -rf "$TMPDST"
trap 'cp "$BACKUP" "$CFG" 2>/dev/null || true; rm -rf "$TMPDST" "$DST"' EXIT
mkdir -p "$TMPDST"
cp "$SRC/__init__.py" "$SRC/manifest.json" "$SRC/services.yaml" "$TMPDST/"
[ "$(sha256sum "$TMPDST/__init__.py" | awk '{print $1}')" = "70d07d7b2e15cc86e3ee549029daba2a3ee6af469917a3eebdd8f3d7c1b49a8f" ]
[ "$(sha256sum "$TMPDST/manifest.json" | awk '{print $1}')" = "0c31c99fd10a8d8507939e7a2a7ce6691aaabecd88d16cb4a997234e80026013" ]
[ "$(sha256sum "$TMPDST/services.yaml" | awk '{print $1}')" = "f6cba63dade72c4a14e8b1e44ee7e8b615b47e6c773f45d3fd654e6c9baf778d" ]
python3 -m py_compile "$TMPDST/__init__.py"
python3 -c 'import json,yaml; json.load(open("/config/custom_components/.markvarec_camera_events.new/manifest.json")); yaml.safe_load(open("/config/custom_components/.markvarec_camera_events.new/services.yaml"))'
mv "$TMPDST" "$DST"
if ! grep -Eq '^[[:space:]]*markvarec_camera_events:[[:space:]]*$' "$CFG"; then
  printf '\nmarkvarec_camera_events:\n' >> "$CFG"
fi
trap - EXIT
echo "CAMERA_INBOX_INSTALLED"
echo "CONFIG_BACKUP=$BACKUP"
sha256sum "$DST/__init__.py" "$DST/manifest.json" "$DST/services.yaml" "$CFG"
SH
