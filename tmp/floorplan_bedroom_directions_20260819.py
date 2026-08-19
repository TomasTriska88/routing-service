import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

P = Path("/config/.storage/lovelace.linino_hnizdo")

def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)

data = json.loads(P.read_text(encoding="utf-8"))
cards = [x for x in walk(data) if x.get("type") == "custom:easy-floorplan-card"]
assert len(cards) == 1, len(cards)
card = cards[0]
assert card.get("title") == "Plán Markvarce"
assert card.get("width") == 1500
assert card.get("height") == 900
assert card.get("grid") == 20
assert card.get("snap") == 0
assert card.get("offlineStyle") == "strike"
assert card.get("sunDimming") is True
assert card.get("sunlight") is True
assert card.get("north") == 0
assert "sunBearing" not in card
assert "compactHeader" not in card

floors = {f.get("id"): f for f in card.get("floors", [])}
assert "domek" in floors and "pozemek" in floors
domek = floors["domek"]
items = {i.get("id"): i for i in domek.get("items", [])}
assert len(items) == len(domek.get("items", []))

targets = {
    "item_markvarec_loznice_pritomnost": 30,
    "item_markvarec_tv": 30,
    "item_markvarec_nest": 30,
    "item_markvarec_sencor_loznice": 30,
    "item_markvarec_primotop": 210,
    "item_markvarec_krevetarium": 300,
}
for item_id in targets:
    assert item_id in items, item_id

assert items["item_9zaj9cc"].get("entity") == "fan.loznice_vetrak_loznice_zasuvka_1"
assert items["item_9zaj9cc"].get("angle") == 120
assert items["item_markvarec_krevetarium"].get("entity") == "switch.loznice_krevetarium_osvetleni"
assert items["item_markvarec_tv"].get("entity") == "media_player.loznice_televize_google_tv"
assert items["item_markvarec_loznice_svetlo"].get("entity") == "light.loznice_svetlo"
assert items["item_markvarec_loznice_svetlo"].get("glow") is True

before_xy = {k: (v.get("x"), v.get("y")) for k, v in items.items()}
before_walls = json.dumps(domek.get("walls", []), ensure_ascii=False, sort_keys=True)
before_openings = json.dumps(domek.get("openings", []), ensure_ascii=False, sort_keys=True)
before_furniture = json.dumps(domek.get("furniture", []), ensure_ascii=False, sort_keys=True)
before_count = len(domek.get("items", []))

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = P.with_name(P.name + ".bak-floorplan-bedroom-directions-" + stamp)
shutil.copy2(P, backup)

for item_id, angle in targets.items():
    items[item_id]["angle"] = angle

krev = items["item_markvarec_krevetarium"]
krev["glow"] = True
krev["glowRadius"] = 140
krev["glowColor"] = "#ffffff"

tv = items["item_markvarec_tv"]
tv["showState"] = False
tv["icon"] = "mdi:television"
rules = [r for r in (tv.get("stateColor") or []) if r.get("state") != "off"]
rules.append({"state": "off", "color": "#78909c", "icon": "mdi:television"})
tv["stateColor"] = rules

tmp = P.with_name(P.name + ".tmp-floorplan-bedroom-directions")
tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
os.replace(tmp, P)

try:
    check_data = json.loads(P.read_text(encoding="utf-8"))
    ccards = [x for x in walk(check_data) if x.get("type") == "custom:easy-floorplan-card"]
    assert len(ccards) == 1
    cfloors = {f.get("id"): f for f in ccards[0].get("floors", [])}
    cdomek = cfloors["domek"]
    citems = {i.get("id"): i for i in cdomek.get("items", [])}
    assert len(cdomek.get("items", [])) == before_count
    assert {k: (v.get("x"), v.get("y")) for k, v in citems.items()} == before_xy
    assert json.dumps(cdomek.get("walls", []), ensure_ascii=False, sort_keys=True) == before_walls
    assert json.dumps(cdomek.get("openings", []), ensure_ascii=False, sort_keys=True) == before_openings
    assert json.dumps(cdomek.get("furniture", []), ensure_ascii=False, sort_keys=True) == before_furniture

    for item_id, angle in targets.items():
        assert citems[item_id].get("angle") == angle
    assert citems["item_9zaj9cc"].get("angle") == 120

    ck = citems["item_markvarec_krevetarium"]
    assert ck.get("glow") is True
    assert ck.get("glowRadius") == 140
    assert ck.get("glowColor") == "#ffffff"

    ctv = citems["item_markvarec_tv"]
    assert ctv.get("showState") is False
    assert ctv.get("icon") == "mdi:television"
    off = [r for r in ctv.get("stateColor", []) if r.get("state") == "off"]
    assert len(off) == 1
    assert off[0].get("color") == "#78909c"
    assert off[0].get("icon") == "mdi:television"

    proc = subprocess.run(
        [sys.executable, "-m", "homeassistant", "--script", "check_config", "-c", "/config"],
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    print(output, end="")
    if proc.returncode != 0 or "could not be validated and has been disabled" in output.lower():
        raise RuntimeError(f"check_config failed rc={proc.returncode}")
except Exception:
    shutil.copy2(backup, P)
    print("FLOORPLAN_BEDROOM_DIRECTIONS_VALIDATION_FAILED_ROLLED_BACK")
    raise

print("FLOORPLAN_BEDROOM_DIRECTIONS_WRITE_OK")
print("PRESENCE_ANGLE=30")
print("TV_ANGLE=30")
print("NEST_ANGLE=30")
print("SENCOR_ANGLE=30")
print("HEATER_ANGLE=210")
print("KREVETARIUM_ANGLE=300")
print("KREVETARIUM_GLOW=true")
print("KREVETARIUM_GLOW_RADIUS=140")
print("KREVETARIUM_GLOW_COLOR=#ffffff")
print("TV_SHOW_STATE=false")
print("TV_OFF_STYLE=neutral")
print("USER_COORDINATES_PRESERVED=true")
print("BACKUP=" + str(backup))
print("FLOORPLAN_BEDROOM_DIRECTIONS_CHECK_CONFIG_OK")
