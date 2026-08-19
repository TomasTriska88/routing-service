set -euo pipefail

STAMP=$(date +%Y%m%d-%H%M%S)
CFG_BAK="/config/configuration.yaml.bak-bedroom-residual-$STAMP"
CARD_BAK="/config/www/lina-energy-card.js.bak-bedroom-residual-$STAMP"
RES_BAK="/config/.storage/lovelace_resources.bak-bedroom-residual-$STAMP"
TEST="/config/tests/test_bedroom_energy_residual_regression.py"
EXPECTED_CARD_SHA="bd3bc79067bed02812f74ae45a9993f074d67108b4cb444de3a126f6ef682346"
NEW_RESOURCE="/local/lina-energy-card.js?v=20260819-bedroom-residual-r1"

docker exec -i \
  -e CFG_BAK="$CFG_BAK" \
  -e CARD_BAK="$CARD_BAK" \
  -e RES_BAK="$RES_BAK" \
  -e TEST="$TEST" \
  -e EXPECTED_CARD_SHA="$EXPECTED_CARD_SHA" \
  -e NEW_RESOURCE="$NEW_RESOURCE" \
  homeassistant python3 - <<'PY'
from pathlib import Path
import hashlib, json, os, shutil

cfg = Path("/config/configuration.yaml")
card = Path("/config/www/lina-energy-card.js")
res = Path("/config/.storage/lovelace_resources")
test = Path(os.environ["TEST"])
cfg_bak = Path(os.environ["CFG_BAK"])
card_bak = Path(os.environ["CARD_BAK"])
res_bak = Path(os.environ["RES_BAK"])
expected_sha = os.environ["EXPECTED_CARD_SHA"]
new_resource = os.environ["NEW_RESOURCE"]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

assert sha(card) == expected_sha, f"energy card SHA changed: {sha(card)}"
cfg_text = cfg.read_text(encoding="utf-8")
card_text = card.read_text(encoding="utf-8")
res_data = json.loads(res.read_text(encoding="utf-8"))

assert "default_entity_id: sensor.loznice_ostatni_vykon" not in cfg_text
assert 'sensor.loznice_ostatni_vykon' not in card_text

cfg_marker = '''  - sensor:
      - name: "Jezírko - zanesení čerpadla"
'''
assert cfg_text.count(cfg_marker) == 1, cfg_text.count(cfg_marker)

sensor_block = '''  - sensor:
      - name: "Ložnice - ostatní příkon"
        default_entity_id: sensor.loznice_ostatni_vykon
        unique_id: markvarec_loznice_ostatni_vykon
        device_class: power
        state_class: measurement
        unit_of_measurement: "W"
        availability: >-
          {% set bad = ['unknown', 'unavailable', 'none', ''] %}
          {{ states('sensor.loznicovy_rozvadec_vykon') not in bad
             and states('sensor.primotop_v_loznici_vykon') not in bad
             and states('sensor.loznice_vetrak_vykon') not in bad
             and states('sensor.vanocni_osvetleni_vykon') not in bad }}
        state: >-
          {% set root = states('sensor.loznicovy_rozvadec_vykon') | float(0) %}
          {% set known = states('sensor.primotop_v_loznici_vykon') | float(0)
             + states('sensor.loznice_vetrak_vykon') | float(0)
             + states('sensor.vanocni_osvetleni_vykon') | float(0) %}
          {{ [0, root - known] | max | round(1) }}
        attributes:
          popis: "Zbytkový příkon ložnicové větve mimo samostatně měřený přímotop, větrák a Krevetárium; zejména TV, Prcek, notebooky a další neměřené spotřebiče."
          poznamka: "Může krátkodobě kolísat kvůli asynchronní Tuya telemetrii; záporný rozdíl se ořezává na 0 W."

      - name: "Jezírko - zanesení čerpadla"
'''
new_cfg = cfg_text.replace(cfg_marker, sensor_block, 1)

card_anchor = '''        { entity: "sensor.vanocni_osvetleni_vykon", name: "Krevetárium", icon: "💡" },
        { entity: "sensor.drubezi_vybeh_vykon", name: "Voliéra", icon: "🐔" }
'''
assert card_text.count(card_anchor) == 1, card_text.count(card_anchor)
new_card = card_text.replace(
    card_anchor,
    '''        { entity: "sensor.vanocni_osvetleni_vykon", name: "Krevetárium", icon: "💡" },
        { entity: "sensor.loznice_ostatni_vykon", name: "Ostatní ložnice", icon: "🔌" },
        { entity: "sensor.drubezi_vybeh_vykon", name: "Voliéra", icon: "🐔" }
''',
    1,
)

matches = []
def walk(x):
    if isinstance(x, dict):
        if isinstance(x.get("url"), str) and "lina-energy-card.js" in x["url"]:
            matches.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
walk(res_data)
assert len(matches) == 1, len(matches)
old_url = matches[0]["url"]
assert old_url == "/local/lina-energy-card.js?v=20260819-hierarchy-r1", old_url

shutil.copy2(cfg, cfg_bak)
shutil.copy2(card, card_bak)
shutil.copy2(res, res_bak)

cfg_tmp = cfg.with_name(cfg.name + ".tmp-bedroom-residual")
card_tmp = card.with_name(card.name + ".tmp-bedroom-residual")
res_tmp = res.with_name(res.name + ".tmp-bedroom-residual")

cfg_tmp.write_text(new_cfg, encoding="utf-8")
card_tmp.write_text(new_card, encoding="utf-8")
matches[0]["url"] = new_resource
res_tmp.write_text(json.dumps(res_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

cfg_tmp.replace(cfg)
card_tmp.replace(card)
res_tmp.replace(res)

test.write_text(r'''from pathlib import Path
import json

CFG = Path("/config/configuration.yaml").read_text(encoding="utf-8")
CARD = Path("/config/www/lina-energy-card.js").read_text(encoding="utf-8")
RES = json.loads(Path("/config/.storage/lovelace_resources").read_text(encoding="utf-8"))

assert CFG.count("default_entity_id: sensor.loznice_ostatni_vykon") == 1
for entity in (
    "sensor.loznicovy_rozvadec_vykon",
    "sensor.primotop_v_loznici_vykon",
    "sensor.loznice_vetrak_vykon",
    "sensor.vanocni_osvetleni_vykon",
):
    assert entity in CFG
assert "{{ [0, root - known] | max | round(1) }}" in CFG
assert CARD.count('sensor.loznice_ostatni_vykon') == 1
assert 'name: "Ostatní ložnice"' in CARD

for forbidden in (
    "countdown_1",
    "cycle_time",
    "random_time",
    "switch_inching",
):
    assert forbidden not in CFG

for path in ("/config/automations.yaml", "/config/scripts.yaml", "/config/scenes.yaml"):
    text = Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""
    assert "switch.technicka_mistnost_loznicovy_rozvadec" not in text

urls = []
def walk(x):
    if isinstance(x, dict):
        if isinstance(x.get("url"), str) and "lina-energy-card.js" in x["url"]:
            urls.append(x["url"])
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
walk(RES)
assert urls == ["/local/lina-energy-card.js?v=20260819-bedroom-residual-r1"], urls
print("BEDROOM_ENERGY_RESIDUAL_REGRESSION_OK")
''', encoding="utf-8")

print("BEDROOM_RESIDUAL_WRITE_OK")
print("OLD_RESOURCE=" + old_url)
print("NEW_RESOURCE=" + new_resource)
print("NEW_CARD_SHA=" + sha(card))
print("CFG_BACKUP=" + str(cfg_bak))
print("CARD_BACKUP=" + str(card_bak))
print("RES_BACKUP=" + str(res_bak))
PY

set +e
TEST_OUT="$(docker exec homeassistant python3 "$TEST" 2>&1)"
TEST_RC=$?
CFG_OUT="$(docker exec homeassistant python -m homeassistant --script check_config -c /config 2>&1)"
CFG_RC=$?
if command -v node >/dev/null 2>&1; then
  NODE_OUT="$(node --check /home/lina/osobni-pamet/homeassistant/config/www/lina-energy-card.js 2>&1)"
  NODE_RC=$?
else
  NODE_OUT="node unavailable; JS syntax check skipped"
  NODE_RC=0
fi
set -e

printf '%s\n' "$TEST_OUT"
printf '%s\n' "$NODE_OUT"
printf '%s\n' "$CFG_OUT"

BAD=0
[ "$TEST_RC" -eq 0 ] || BAD=1
[ "$NODE_RC" -eq 0 ] || BAD=1
[ "$CFG_RC" -eq 0 ] || BAD=1
printf '%s\n' "$CFG_OUT" | grep -Fqi "could not be validated and has been disabled" && BAD=1

if [ "$BAD" -ne 0 ]; then
  docker exec homeassistant sh -lc "cp '$CFG_BAK' /config/configuration.yaml; cp '$CARD_BAK' /config/www/lina-energy-card.js; cp '$RES_BAK' /config/.storage/lovelace_resources; rm -f '$TEST'"
  echo BEDROOM_RESIDUAL_VALIDATION_FAILED_ROLLED_BACK
  exit 1
fi

echo BEDROOM_RESIDUAL_VALIDATION_OK
nohup sh -c 'sleep 8; docker restart homeassistant >/tmp/bedroom-residual-restart.log 2>&1' >/dev/null 2>&1 &
echo BEDROOM_RESIDUAL_RESTART_SCHEDULED
