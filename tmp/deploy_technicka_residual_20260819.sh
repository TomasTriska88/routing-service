#!/usr/bin/env bash
set -euo pipefail

STAMP="$(date +%Y%m%d-%H%M%S)"
CFG_BAK="/config/configuration.yaml.bak-technicka-residual-$STAMP"
LOV_BAK="/config/.storage/lovelace.linino_hnizdo.bak-technicka-residual-$STAMP"
TEST="/config/tests/test_technicka_energy_residual_regression.py"

docker exec -i -e STAMP="$STAMP" homeassistant python3 - <<'PY'
from pathlib import Path
import json, os, shutil

stamp = os.environ["STAMP"]
cfg = Path("/config/configuration.yaml")
lov = Path("/config/.storage/lovelace.linino_hnizdo")
test = Path("/config/tests/test_technicka_energy_residual_regression.py")
cfg_bak = Path(f"/config/configuration.yaml.bak-technicka-residual-{stamp}")
lov_bak = Path(f"/config/.storage/lovelace.linino_hnizdo.bak-technicka-residual-{stamp}")
test_bak = Path(f"/config/tests/test_technicka_energy_residual_regression.py.bak-{stamp}")

shutil.copy2(cfg, cfg_bak)
shutil.copy2(lov, lov_bak)
if test.exists():
    shutil.copy2(test, test_bak)

cfg_text = cfg.read_text(encoding="utf-8")
marker = '      - name: "Jezírko - zanesení čerpadla"\n'
entity_marker = "default_entity_id: sensor.technicka_rozvadec_provizorni_vykon"
if entity_marker not in cfg_text:
    assert cfg_text.count(marker) == 1, cfg_text.count(marker)
    block = '''      - name: "Rozvaděč technické místnosti – provizorní příkon"
        default_entity_id: sensor.technicka_rozvadec_provizorni_vykon
        unique_id: markvarec_technicka_rozvadec_provizorni_vykon
        device_class: power
        state_class: measurement
        unit_of_measurement: "W"
        availability: >-
          {% set bad = ['unknown', 'unavailable', 'none', ''] %}
          {{ states('sensor.vnitrni_rozvadec_vykon') not in bad
             and states('sensor.loznicovy_rozvadec_vykon') not in bad
             and states('sensor.jezirko_rozvadec_vykon') not in bad
             and states('sensor.sonoff_s60zbtpf_vykon') not in bad
             and states('sensor.drubezi_vybeh_vykon') not in bad }}
        state: >-
          {% set root = states('sensor.vnitrni_rozvadec_vykon') | float(0) %}
          {% set known = states('sensor.loznicovy_rozvadec_vykon') | float(0)
             + states('sensor.jezirko_rozvadec_vykon') | float(0)
             + states('sensor.sonoff_s60zbtpf_vykon') | float(0)
             + states('sensor.drubezi_vybeh_vykon') | float(0) %}
          {{ [0, root - known] | max | round(1) }}
        attributes:
          popis: "Provizorní reziduální větev: převážně Technická místnost + Kuchyň + drobné dosud neměřené odběry."
          zahrnuje: "Technická, Kuchyň, PondoVario 750 (dešťovka), drobné neměřené odběry včetně senzoru ve výběhu."
          nezahrnuje: "Ložnice, Jezírkový rozvaděč, Starlink, Voliéra – reflektor."
          poznamka: "PondoVario 750 se záměrně neodečítá; je fyzicky napájené z technické/vnitřní větve. Po doplnění skutečných měřáků Technické a výběhu tento odhad nahradit."

'''
    cfg_text = cfg_text.replace(marker, block + marker, 1)
    tmp = cfg.with_name(cfg.name + ".tmp-technicka-residual")
    tmp.write_text(cfg_text, encoding="utf-8")
    tmp.replace(cfg)

data = json.loads(lov.read_text(encoding="utf-8"))
cards = []
def walk(x):
    if isinstance(x, dict):
        if x.get("type") == "custom:lina-energy-card":
            cards.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
walk(data)
assert len(cards) == 1, len(cards)
cards[0]["branches"] = [
    {"entity": "sensor.loznicovy_rozvadec_vykon", "name": "Ložnice", "icon": "🛏️"},
    {"entity": "sensor.technicka_rozvadec_provizorni_vykon", "name": "Technická (odhad)", "icon": "🧰"},
    {"entity": "sensor.jezirko_rozvadec_vykon", "name": "Jezírko", "icon": "💧"},
]
lov_tmp = lov.with_name(lov.name + ".tmp-technicka-residual")
lov_tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
lov_tmp.replace(lov)

test.write_text(r'''from pathlib import Path
import json

cfg = Path("/config/configuration.yaml").read_text(encoding="utf-8")
needle = "default_entity_id: sensor.technicka_rozvadec_provizorni_vykon"
assert cfg.count(needle) == 1
start = cfg.index(needle)
next_sensor = cfg.find("\n      - name:", start + len(needle))
block = cfg[start:] if next_sensor < 0 else cfg[start:next_sensor]

for required in (
    "sensor.vnitrni_rozvadec_vykon",
    "sensor.loznicovy_rozvadec_vykon",
    "sensor.jezirko_rozvadec_vykon",
    "sensor.sonoff_s60zbtpf_vykon",
    "sensor.drubezi_vybeh_vykon",
):
    assert required in block, required

assert "sensor.jezirko_cerpadlo_vykon" not in block
assert "PondoVario 750" in block

data = json.loads(Path("/config/.storage/lovelace.linino_hnizdo").read_text(encoding="utf-8"))
cards = []
def walk(x):
    if isinstance(x, dict):
        if x.get("type") == "custom:lina-energy-card":
            cards.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
walk(data)
assert len(cards) == 1
branches = cards[0].get("branches")
assert isinstance(branches, list)
entities = [x.get("entity") for x in branches]
assert entities == [
    "sensor.loznicovy_rozvadec_vykon",
    "sensor.technicka_rozvadec_provizorni_vykon",
    "sensor.jezirko_rozvadec_vykon",
], entities
assert branches[1].get("name") == "Technická (odhad)"
print("TECHNICKA_ENERGY_RESIDUAL_REGRESSION_OK")
''', encoding="utf-8")

print(f"CFG_BACKUP={cfg_bak}")
print(f"LOVELACE_BACKUP={lov_bak}")
print(f"TEST_BACKUP={test_bak if test_bak.exists() else 'none'}")
print("TECHNICKA_RESIDUAL_WRITE_OK")
PY

set +e
TEST_OUT="$(docker exec homeassistant python3 "$TEST" 2>&1)"
TEST_RC=$?
CHECK_OUT="$(docker exec homeassistant python -m homeassistant --script check_config -c /config 2>&1)"
CHECK_RC=$?
set -e

printf '%s\n' "$TEST_OUT"
printf '%s\n' "$CHECK_OUT"

BAD=0
[ "$TEST_RC" -eq 0 ] || BAD=1
[ "$CHECK_RC" -eq 0 ] || BAD=1
printf '%s\n' "$CHECK_OUT" | grep -Fqi "could not be validated and has been disabled" && BAD=1

if [ "$BAD" -ne 0 ]; then
  docker exec homeassistant sh -lc "cp '$CFG_BAK' /config/configuration.yaml; cp '$LOV_BAK' /config/.storage/lovelace.linino_hnizdo"
  echo TECHNICKA_RESIDUAL_VALIDATION_FAILED_ROLLED_BACK
  exit 1
fi

echo TECHNICKA_RESIDUAL_VALIDATION_OK
nohup sh -c 'sleep 8; docker restart homeassistant >/tmp/technicka-residual-restart.log 2>&1' >/dev/null 2>&1 &
echo TECHNICKA_RESIDUAL_RESTART_SCHEDULED
