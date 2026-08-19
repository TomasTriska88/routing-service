#!/usr/bin/env bash
set -euo pipefail
STAMP=20260819-1401-preinstrument
FILES=(lina-home-card.js lina-weather-card.js lina-security-card.js lina-climate-safety-card.js lina-energy-card.js lina-rainwater-card.js)
declare -A CUR=(
[lina-home-card.js]=0174871fc111295071338a55978cfd5a9404d66b1f7df6f434b6d4644c3d27c1
[lina-weather-card.js]=1e2053db295d581a37d8cea1fc548cb5e627083cf807a0fbf89a816cfe6a9173
[lina-security-card.js]=08c89562300184c7eb0e1d1e25744fa63d1b22bdedbec091644d11e32c14107a
[lina-climate-safety-card.js]=75e8b60d1efa83bb35712d49a3c9d740f631517d38bf5e914d38deed64b01ae3
[lina-energy-card.js]=77d1aadcd6681f63f860b903696b44706009e0aff57dfa483f002760cac1669c
[lina-rainwater-card.js]=121ea621cda18b99bbe7d2ecaea8697501d3640c9290e2c57b3e23afa7912f2e
)
declare -A OLD=(
[lina-home-card.js]=3e3766e4bea4cc380731aa640bafdf4ff685ae1b1f86816b7c3cca0a89f3659d
[lina-weather-card.js]=c67f5f5c63b1fd66228c5c95fb3065664f4012848a100e97a5682bebe1dc7265
[lina-security-card.js]=cd5cd0c4d10456bd6c0147bd80bf282f18793f64f5821880072339d990fd4a19
[lina-climate-safety-card.js]=e408c12085ba68800d04e696eb6d9b723233f8c5ac85ccd9a8d800944d304708
[lina-energy-card.js]=b63f1d050fcef1ae4af2ecb5990d02dd9360e7f07491f901b1f0e51116ed97bf
[lina-rainwater-card.js]=6f3b93fc2ca5db8546a0f998fecaa8e4135dc45e024684aa23004114f94d6644
)
declare -A SIZE=(
[lina-home-card.js]=9048 [lina-weather-card.js]=27228 [lina-security-card.js]=10005
[lina-climate-safety-card.js]=29718 [lina-energy-card.js]=18269 [lina-rainwater-card.js]=17228
)
rollback(){
  for f in "${FILES[@]}"; do
    docker exec homeassistant sh -lc "test -f /config/www/$f.bak-$STAMP && cp /config/www/$f.bak-$STAMP /config/www/$f || true"
  done
}
trap 'rc=$?; if [ $rc -ne 0 ]; then rollback; fi; exit $rc' EXIT
for f in "${FILES[@]}"; do
  live=$(docker exec homeassistant sha256sum "/config/www/$f" | awk '{print $1}')
  [ "$live" = "${CUR[$f]}" ] || { echo "LIVE_SHA_MISMATCH $f $live"; exit 80; }
  src="/config/www/$f.bak-20260818-2244-instrument-v1"
  old=$(docker exec homeassistant sha256sum "$src" | awk '{print $1}')
  [ "$old" = "${OLD[$f]}" ] || { echo "BACKUP_SHA_MISMATCH $f $old"; exit 81; }
  bytes=$(docker exec homeassistant wc -c < <(docker exec homeassistant cat "$src") 2>/dev/null || true)
  # authoritative size check is performed after docker cp below
  docker exec homeassistant cp "/config/www/$f" "/config/www/$f.bak-$STAMP"
  docker exec homeassistant cp "$src" "/tmp/$f.preinstrument.js"
  docker cp "homeassistant:/tmp/$f.preinstrument.js" "/tmp/$f.preinstrument.js" >/dev/null
  [ "$(wc -c < "/tmp/$f.preinstrument.js" | tr -d ' ')" = "${SIZE[$f]}" ] || { echo "SIZE_MISMATCH $f"; exit 82; }
  [ "$(sha256sum "/tmp/$f.preinstrument.js" | awk '{print $1}')" = "${OLD[$f]}" ] || { echo "STAGE_SHA_MISMATCH $f"; exit 83; }
  node --check "/tmp/$f.preinstrument.js" >/dev/null
  grep -q 'Markvarec TV typography profile: 20260818-tvread1' "/tmp/$f.preinstrument.js" || { echo "MARKER_MISSING $f"; exit 84; }
done
for f in "${FILES[@]}"; do
  docker exec homeassistant cp "/tmp/$f.preinstrument.js" "/config/www/$f"
done
for f in "${FILES[@]}"; do
  live=$(docker exec homeassistant sha256sum "/config/www/$f" | awk '{print $1}')
  [ "$live" = "${OLD[$f]}" ] || { echo "POST_SHA_MISMATCH $f $live"; exit 85; }
  echo "$f $live ${SIZE[$f]}"
  rm -f "/tmp/$f.preinstrument.js"
done
export DISPLAY=:0
export XAUTHORITY=/home/lina/.Xauthority
WIN=$(wmctrl -lx | awk '$3=="Navigator.firefox" {print $1; exit}')
[ -n "$WIN" ] || { echo FIREFOX_WINDOW_NOT_FOUND; exit 86; }
wmctrl -ia "$WIN"
sleep 0.3
xdotool key --window "$WIN" --clearmodifiers ctrl+shift+r
sleep 1
wmctrl -lGx | awk '$3=="Navigator.firefox" {print; exit}'
echo HNIZDO_PREINSTRUMENT_VISUAL_RESTORED
trap - EXIT
