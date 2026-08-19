import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

p = Path("/config/.storage/lovelace.linino_hnizdo")
data = json.loads(p.read_text(encoding="utf-8"))

def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)

cards = [
    x for x in walk(data)
    if x.get("type") == "custom:easy-floorplan-card"
    and x.get("title") == "Plán Markvarce"
]
assert len(cards) == 1, len(cards)
card = cards[0]

# Preflight: change only the known bad grid/snap pair, and refuse any drift.
assert card.get("width") == 1500
assert card.get("height") == 900
assert card.get("grid") == 2000
assert card.get("snap") == 2000
assert card.get("offlineStyle") == "strike"
assert card.get("sunDimming") is True
assert card.get("sunlight") is True
assert card.get("north") == 0
assert "sunBearing" not in card
assert "compactHeader" not in card

floors = {f.get("id"): f for f in card.get("floors", [])}
assert len(floors["domek"].get("items", [])) == 15
assert len(floors["pozemek"].get("items", [])) == 10

doors = [x for x in walk(card) if x.get("id") == "door_pcltbs3"]
assert len(doors) == 1
assert doors[0].get("staticClosed") is True
assert doors[0].get("glazed") is True
assert "sunlight" not in doors[0]

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = p.with_name(p.name + ".bak-floorplan-grid-snap-" + stamp)
shutil.copy2(p, backup)

card["grid"] = 20
card["snap"] = 0

tmp = p.with_name(p.name + ".tmp-grid-snap")
tmp.write_text(
    json.dumps(data, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8",
)
os.replace(tmp, p)

try:
    check = json.loads(p.read_text(encoding="utf-8"))
    cc = [
        x for x in walk(check)
        if x.get("type") == "custom:easy-floorplan-card"
        and x.get("title") == "Plán Markvarce"
    ]
    assert len(cc) == 1
    assert cc[0].get("grid") == 20
    assert cc[0].get("snap") == 0
    assert cc[0].get("offlineStyle") == "strike"

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
    shutil.copy2(backup, p)
    print("FLOORPLAN_GRID_SNAP_VALIDATION_FAILED_ROLLED_BACK")
    raise

print("FLOORPLAN_GRID_SNAP_WRITE_OK")
print("GRID=20")
print("SNAP=0")
print("BACKUP=" + str(backup))
print("FLOORPLAN_GRID_SNAP_CHECK_CONFIG_OK")
