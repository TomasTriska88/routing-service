import json, hashlib
from pathlib import Path

P = Path("/config/.storage/lovelace.linino_hnizdo")
JS = Path("/config/www/easy-floorplan-card.js")

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
assert len(cards) == 1
c = cards[0]
assert c.get("title") == "Plán Markvarce"
assert c.get("width") == 1500 and c.get("height") == 900
assert c.get("grid") == 20 and c.get("snap") == 0
assert c.get("offlineStyle") == "strike"
assert c.get("sunDimming") is True and c.get("sunlight") is True and c.get("north") == 0
assert "sunBearing" not in c and "compactHeader" not in c

floors = {f.get("id"): f for f in c.get("floors", [])}
domek = floors["domek"]
items = {i.get("id"): i for i in domek.get("items", [])}
assert len(domek.get("items", [])) == 15
expected = {
    "item_markvarec_loznice_pritomnost": 30,
    "item_markvarec_tv": 30,
    "item_markvarec_nest": 30,
    "item_markvarec_sencor_loznice": 30,
    "item_markvarec_primotop": 210,
    "item_markvarec_krevetarium": 300,
    "item_9zaj9cc": 120,
}
for k, a in expected.items():
    assert items[k].get("angle") == a, (k, items[k].get("angle"))

k = items["item_markvarec_krevetarium"]
assert k.get("glow") is True and k.get("glowRadius") == 140 and k.get("glowColor") == "#ffffff"

tv = items["item_markvarec_tv"]
assert tv.get("showState") is False and tv.get("icon") == "mdi:television"
off = [r for r in tv.get("stateColor", []) if r.get("state") == "off"]
assert len(off) == 1 and off[0].get("color") == "#78909c"

light = items["item_markvarec_loznice_svetlo"]
assert light.get("glow") is True

sha = hashlib.sha256(JS.read_bytes()).hexdigest()
assert sha == "9a7593a3f8f40e13056c1e16cd04b4db7477bfbded6b7b99cc4beca9dda7eaac", sha
print("ANGLES=presence:30,tv:30,nest:30,sencor:30,heater:210,krevetarium:300,fan:120")
print("KREVETARIUM_GLOW=true,radius=140,color=#ffffff")
print("TV_SHOW_STATE=false,off_style=neutral")
print("MAIN_LIGHT_GLOW=true")
print("DOMEK_ITEMS=15")
print("JS_SHA256=" + sha)
print("FLOORPLAN_BEDROOM_DIRECTIONS_POSTRESTART_READBACK_OK")
