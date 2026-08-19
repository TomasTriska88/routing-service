from pathlib import Path
import json, hashlib, shutil, sys

p = Path("/config/.storage/lovelace_resources")
expected_sha = "44fa75ace8e3b279645f3875d6d81f910eab04205a0957638ad0cbf0c2035f17"
tag = "20260819-tvbaseline-r1"
names = [
    "lina-home-card.js",
    "lina-weather-card.js",
    "lina-security-card.js",
    "lina-climate-safety-card.js",
    "lina-energy-card.js",
    "lina-rainwater-card.js",
]
raw = p.read_bytes()
got = hashlib.sha256(raw).hexdigest()
if got != expected_sha:
    raise SystemExit(f"RESOURCE_PRE_SHA_MISMATCH {got}")
data = json.loads(raw)
items = data.get("data", {}).get("items", [])
for name in names:
    matches = [x for x in items if name in str(x.get("url", ""))]
    if len(matches) != 1:
        raise SystemExit(f"RESOURCE_MATCH_COUNT {name} {len(matches)}")
    matches[0]["url"] = f"/local/{name}?v={tag}"
backup = p.with_name(f"lovelace_resources.bak-{tag}")
shutil.copy2(p, backup)
tmp = p.with_name("lovelace_resources.tmp-tvbaseline-r1")
tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
check = json.loads(tmp.read_text(encoding="utf-8"))
for name in names:
    matches = [x for x in check["data"]["items"] if x.get("url") == f"/local/{name}?v={tag}"]
    if len(matches) != 1:
        raise SystemExit(f"RESOURCE_READBACK_COUNT {name} {len(matches)}")
tmp.replace(p)
newraw = p.read_bytes()
print("RESOURCE_POST_SHA="+hashlib.sha256(newraw).hexdigest())
for name in names:
    print(f"/local/{name}?v={tag}")
print("RESOURCE_BACKUP="+str(backup))
print("HNIZDO_RESOURCE_VERSION_BUMP_OK")
