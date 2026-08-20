#!/usr/bin/env bash
set -euo pipefail

EXPECTED_WATER_BLOCK_SHA="${1:?expected current rainwater balance block sha256 required}"
ORIG_URL='https://raw.githubusercontent.com/TomasTriska88/routing-service/44f086d3039085e21e5cc137aa24f67617f5aa8d/tmp/rainwater_pump_proxy_patch_20260820_2228.py'
ORIG='/tmp/rainwater_pump_proxy_patch_20260820_2228.py'
REB='/tmp/rainwater_pump_proxy_patch_20260820_v2_rebased.py'
OLD_AUTO='09bdeb7a0125d4fb4156c9948526444244414cb62e05b4714061a22d39d981f3'
CARD_OLD='8f7f34e08befe4aa809ce9601a4195aacb674d3abe2f49b2e814cb7a8fbada22'
ORIG_SHA='6144faed811632539348d1391bc0342a6ceca688dac1d9ef673946052fd34cae'
ORIG_BYTES='21721'
STAMP='20260820-2248-v2'
CFG='/config/configuration.yaml'
AUTO='/config/automations.yaml'
CARD='/config/www/lina-rainwater-card.js'
TEST='/config/tests/test_rainwater_pump_proxy_regression.py'
BCFG="${CFG}.bak-pump-proxy-${STAMP}"
BAUTO="${AUTO}.bak-pump-proxy-${STAMP}"
BCARD="${CARD}.bak-pump-proxy-${STAMP}"
BTEST="${TEST}.bak-pump-proxy-${STAMP}"

water_block_sha() {
  docker exec -i homeassistant python3 - <<'PY'
from pathlib import Path
import hashlib
s=Path('/config/automations.yaml').read_text(encoding='utf-8')
a=s.index("- id: 'markvarec_destovka_prubezna_bilance'")
b=s.index("\n- id: 'markvarec_destovka_rucni_kalibrace'", a)
print(hashlib.sha256(s[a:b].encode('utf-8')).hexdigest())
PY
}

CURRENT_WATER_BLOCK_SHA="$(water_block_sha)"
CURRENT_AUTO="$(docker exec homeassistant sha256sum "$AUTO" | awk '{print $1}')"
CURRENT_CARD="$(docker exec homeassistant sha256sum "$CARD" | awk '{print $1}')"
echo "CURRENT_WATER_BLOCK_SHA256=$CURRENT_WATER_BLOCK_SHA"
echo "CURRENT_AUTO_SHA256=$CURRENT_AUTO"
echo "CURRENT_CARD_SHA256=$CURRENT_CARD"
test "$CURRENT_WATER_BLOCK_SHA" = "$EXPECTED_WATER_BLOCK_SHA"
test "$CURRENT_CARD" = "$CARD_OLD"

curl -fSsL --max-time 20 "$ORIG_URL" -o "$ORIG"
test "$(sha256sum "$ORIG" | awk '{print $1}')" = "$ORIG_SHA"
test "$(wc -c < "$ORIG" | tr -d ' ')" = "$ORIG_BYTES"

python3 - "$ORIG" "$REB" "$OLD_AUTO" "$CURRENT_AUTO" <<'PY'
from pathlib import Path
import sys
src,dst,old,new=sys.argv[1:]
s=Path(src).read_text(encoding='utf-8')
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)
Path(dst).write_text(s,encoding='utf-8')
print('RAINWATER_PATCH_V2_REBASED')
PY
python3 -m py_compile "$REB"
echo "REBASED_PATCH_SHA256=$(sha256sum "$REB" | awk '{print $1}')"
echo "REBASED_PATCH_BYTES=$(wc -c < "$REB" | tr -d ' ')"

# Fresh rollback point from the exact files being mutated now.
docker exec homeassistant cp -p "$CFG" "$BCFG"
docker exec homeassistant cp -p "$AUTO" "$BAUTO"
docker exec homeassistant cp -p "$CARD" "$BCARD"
if docker exec homeassistant test -e "$TEST"; then
  TEST_EXISTED=1
  docker exec homeassistant cp -p "$TEST" "$BTEST"
else
  TEST_EXISTED=0
fi
rollback() {
  docker exec homeassistant cp -p "$BCFG" "$CFG" || true
  docker exec homeassistant cp -p "$BAUTO" "$AUTO" || true
  docker exec homeassistant cp -p "$BCARD" "$CARD" || true
  if [ "$TEST_EXISTED" = 1 ]; then
    docker exec homeassistant cp -p "$BTEST" "$TEST" || true
  else
    docker exec homeassistant rm -f "$TEST" || true
  fi
  echo RAINWATER_PUMP_PROXY_V2_ROLLED_BACK
}
trap rollback ERR

docker cp "$REB" homeassistant:/tmp/rainwater_pump_proxy_patch_20260820_v2_rebased.py
docker exec homeassistant python3 /tmp/rainwater_pump_proxy_patch_20260820_v2_rebased.py

# Precision cleanup: unknown Savo dose keeps an age interval but NEVER invents dilution.
# The internal approximate-rain counter may collect diagnostics, but it is not displayed
# and does not participate in the Savo recommendation while exact dose is unknown.
docker exec -i homeassistant python3 - <<'PY'
from pathlib import Path
CFG=Path('/config/configuration.yaml')
CARD=Path('/config/www/lina-rainwater-card.js')
TEST=Path('/config/tests/test_rainwater_pump_proxy_regression.py')

cfg=CFG.read_text(encoding='utf-8')
card=CARD.read_text(encoding='utf-8')

old_name='    name: "Dešťovka - odhad přítoku od přibližné poslední dávky Sava"'
new_name='    name: "Dešťovka - interní přítok při neznámé dávce Sava (od zapnutí modelu)"'
assert cfg.count(old_name)==1, cfg.count(old_name)
cfg=cfg.replace(old_name,new_name,1)

line='    const savoApproxInflow = this._num("input_number.destovka_savo_pritok_od_davky_odhad_l", null);\n'
assert card.count(line)==1, card.count(line)
card=card.replace(line,'',1)
old='savoAgeDays, savoInflow, savoApproxInflow, savoCheckDays'
new='savoAgeDays, savoInflow, savoCheckDays'
assert card.count(old)==1, card.count(old)
card=card.replace(old,new,1)

start=card.index('    // Current unknown exact dose is anchored')
end=card.index('    const flowLabel =', start)
honest=r'''    // Exact dose time is unknown. Preserve the user's 4–7 day estimate as an interval,
    // but never turn incomplete history into a fake chlorine/dilution percentage.
    const savoApproxEarliestTs = Date.parse("2026-08-13T22:00:00+02:00");
    const savoApproxLatestTs = Date.parse("2026-08-16T22:00:00+02:00");
    const nowMs = Date.now();
    const savoApproxAgeMin = !known && Number.isFinite(savoApproxLatestTs) ? Math.max(0, (nowMs - savoApproxLatestTs) / 86400000) : null;
    const savoApproxAgeMax = !known && Number.isFinite(savoApproxEarliestTs) ? Math.max(0, (nowMs - savoApproxEarliestTs) / 86400000) : null;
    const exactAgeAvailable = known && Number.isFinite(savoAgeDays);
    const approxAgeAvailable = !known && Number.isFinite(savoApproxAgeMin) && Number.isFinite(savoApproxAgeMax);
    const savoAgeKnown = (exactAgeAvailable || approxAgeAvailable) && Number.isFinite(savoCheckDays) && savoCheckDays > 0;
    const ageForMeter = exactAgeAvailable ? savoAgeDays : (approxAgeAvailable ? savoApproxAgeMax : null);
    const savoAgePct = savoAgeKnown ? this._clamp((ageForMeter / savoCheckDays) * 100, 0, 100) : 0;

    const exactDilutionPct = known && Number.isFinite(savoInflow) && Number.isFinite(doseVolume) && doseVolume > 0
      ? (savoInflow / doseVolume) * 100 : null;
    const dilutionKnown = Number.isFinite(exactDilutionPct) && Number.isFinite(savoDilutionLimit) && savoDilutionLimit > 0;
    const dilutionMeterPct = dilutionKnown ? this._clamp((exactDilutionPct / savoDilutionLimit) * 100, 0, 100) : 0;
    const ageLabel = exactAgeAvailable
      ? `${savoAgeDays.toFixed(1)} / ${savoCheckDays.toFixed(0)} d`
      : approxAgeAvailable
        ? `~${savoApproxAgeMin.toFixed(1)}–${savoApproxAgeMax.toFixed(1)} / ${savoCheckDays.toFixed(0)} d`
        : `? / ${savoCheckDays.toFixed(0)} d`;
    const dilutionLabel = dilutionKnown
      ? `${exactDilutionPct.toFixed(0)} / ${savoDilutionLimit.toFixed(0)} %`
      : `? / ${savoDilutionLimit.toFixed(0)} %`;

'''
card=card[:start]+honest+card[end:]

old='    const pump = this._st("switch.zahrada_cerpadlo_destovka")?.state || "unknown";'
new='    const pump = this._st("binary_sensor.destovka_odber_vody_bezi")?.state || "unknown";'
assert card.count(old)==1, card.count(old)
card=card.replace(old,new,1)
old='    const pumpLabel = pump === "on" ? "čerpadlo zapnuto" : pump === "off" ? "čerpadlo vypnuto" : "čerpadlo neznámé";'
new='    const pumpLabel = pump === "on" ? "odběr vody běží" : pump === "off" ? "odběr vody stojí" : "odběr vody neznámý";'
assert card.count(old)==1, card.count(old)
card=card.replace(old,new,1)

CFG.write_text(cfg,encoding='utf-8')
CARD.write_text(card,encoding='utf-8')

# Permanent regression test for the semantic/predictive contract.
test=r'''from pathlib import Path
CFG=Path('/config/configuration.yaml').read_text(encoding='utf-8')
AUTO=Path('/config/automations.yaml').read_text(encoding='utf-8')
CARD=Path('/config/www/lina-rainwater-card.js').read_text(encoding='utf-8')
assert 'unique_id: markvarec_destovka_odber_vody_bezi' in CFG
assert "states('sensor.zahrada_cerpadlo_destovka_vykon')" in CFG
assert '| float(0) > 2.0' in CFG
assert 'destovka_odhad_prutoku_l_min:' in CFG
assert 'name: "Dešťovka - predikční / fallback denní spotřeba (odhad)"' in CFG
assert 'destovka_odber_start_ts:' in CFG
assert 'destovka_spotreba_dnes_l:' in CFG
assert 'interní přítok při neznámé dávce Sava (od zapnutí modelu)' in CFG
a0=AUTO.index("- id: 'markvarec_destovka_prubezna_bilance'")
a1=AUTO.index("\n- id: 'markvarec_destovka_rucni_kalibrace'",a0)
b=AUTO[a0:a1]
assert 'binary_sensor.destovka_odber_vody_bezi' in b
assert 'runtime_consumption_l' in b and 'flow_l_min' in b
assert 'fallback_consumption_l' in b and 'forecast_use_per_day' in b
assert 'use_per_day * (elapsed_s' not in b
assert 'daily_rollover' in b
assert 'label:"NEDÁVAT"' in CARD
assert 'label:"NEPŘIDÁVAT"' not in CARD
assert 'white-space:nowrap; overflow:hidden; text-overflow:ellipsis' in CARD
assert 'binary_sensor.destovka_odber_vody_bezi' in CARD
assert 'sensor.zahrada_cerpadlo_destovka_vykon' in CARD
assert '≈${flowEstimate.toFixed(1)} l/min' in CARD
assert 'savoApproxAgeMin' in CARD and 'savoApproxAgeMax' in CARD
assert 'approxDilutionMinPct' not in CARD
assert 'savoApproxInflow' not in CARD
assert ': `? / ${savoDilutionLimit.toFixed(0)} %`' in CARD
runtime_seconds=4.29*60
flow_l_min=10.0
liters=runtime_seconds*flow_l_min/60
assert abs(liters-42.9)<1e-9
print('RAINWATER_PUMP_PROXY_REGRESSION_OK')
'''
TEST.write_text(test,encoding='utf-8')
print('RAINWATER_PUMP_PROXY_PRECISION_CLEANUP_OK')
PY

docker exec homeassistant python3 -m py_compile "$TEST"
docker exec homeassistant python3 "$TEST"
docker exec homeassistant python3 /config/tests/test_rainwater_use_semaphore_regression.py
docker exec homeassistant python3 /config/tests/test_rainwater_visual_semantics_regression.py
if docker exec homeassistant test -e /config/tests/test_fan_regression.py; then
  docker exec homeassistant python3 /config/tests/test_fan_regression.py
fi
if docker exec homeassistant test -e /config/tests/test_energy_limit_monitor_regression.py; then
  docker exec homeassistant python3 /config/tests/test_energy_limit_monitor_regression.py
fi

docker cp homeassistant:"$CARD" /tmp/lina-rainwater-card-v2.js
node --check /tmp/lina-rainwater-card-v2.js

trap - ERR
echo "CFG_SHA256=$(docker exec homeassistant sha256sum "$CFG" | awk '{print $1}')"
echo "AUTO_SHA256=$(docker exec homeassistant sha256sum "$AUTO" | awk '{print $1}')"
echo "CARD_SHA256=$(docker exec homeassistant sha256sum "$CARD" | awk '{print $1}')"
echo "TEST_SHA256=$(docker exec homeassistant sha256sum "$TEST" | awk '{print $1}')"
echo "ROLLBACK_CFG=$BCFG"
echo "ROLLBACK_AUTO=$BAUTO"
echo "ROLLBACK_CARD=$BCARD"
echo RAINWATER_PUMP_PROXY_V2_PRECHECKS_OK
