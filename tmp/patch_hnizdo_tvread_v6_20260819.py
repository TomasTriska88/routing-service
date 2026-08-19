from pathlib import Path
import hashlib, shutil

stamp = "20260819-1310-tvread-v6"
marker = "Markvarec TV balanced reset profile: 20260819-tvread-v6"

live_expected = {
    "lina-home-card.js": "d2ef7475d9c44ea2778fa0bb7401e8d45bb2dacab246fea84e3b410e7946efae",
    "lina-weather-card.js": "182707b2274fc76a785159ca830aefab3da97ab5cbd036817ba3df3ed6e2734c",
    "lina-security-card.js": "ab77e9199ac161fbbe5b99710f4988aa6165d8586ef1e94ba776f7276e69f199",
    "lina-climate-safety-card.js": "f2c9a3fa8417fb7271dbdeaa08d56e820f2652fedb07037f91e67f7285807c75",
    "lina-energy-card.js": "5ef555cbba435103b5d78e2c4940dc7837b79e89caedf0b81be11db714a7d8f5",
    "lina-rainwater-card.js": "96e1a6cb0a4276650fa659598110d91438dd151b83808e5a146ad16cf350eb6e",
}
v3_expected = {
    "lina-home-card.js": "8c9a4778efa247837e008b9c6cc452e698970f22a6cf0de3486b165c8bdfca00",
    "lina-weather-card.js": "969b9b9f533f5023098802725e091cfd5992bea29896ddad2605a5b10c7731a1",
    "lina-security-card.js": "255562287462ffa7945160e7859b286fbc9e7dd4d0c52499986c3a21b7894273",
    "lina-climate-safety-card.js": "4e953dc8f0f202510f17153b68b73539a6851e49db22ea2d00734a213f38b083",
    "lina-energy-card.js": "694bc07f972770b33d466e15629e4b6eeeddca749b0dbf0ed6c01e4b60d93762",
    "lina-rainwater-card.js": "c5f853d930c05edb50099053a5b527f760bfbf6842412d63aaa3f210687148ad",
}
overrides = {
"lina-home-card.js": '''@container (min-width:431px) {
.thought{font-size:22px!important;line-height:1.16!important}
}''',
"lina-weather-card.js": '''@container (min-width:431px) {
.temp-trend small,.rain-next small,.signal small,.irrigation small{font-size:21px!important;line-height:1.14!important}
.loading{font-size:20px!important}
}''',
"lina-security-card.js": '''@container (min-width:431px) {
.hero p,.extra{font-size:21px!important;line-height:1.14!important}
}''',
"lina-climate-safety-card.js": '''@container (min-width:431px) {
.issue small,.more-issues{font-size:21px!important;line-height:1.14!important}
}''',
"lina-energy-card.js": '''@container (min-width:431px) {
.issue small,.loads-empty{font-size:21px!important;line-height:1.14!important}
}''',
"lina-rainwater-card.js": '''@container (min-width:431px) {
.rain-box small,.overflow-note small{font-size:21px!important;line-height:1.14!important}
}''',
}

root = Path("/config/www")
prepared = {}
for name in live_expected:
    live = root / name
    live_sha = hashlib.sha256(live.read_bytes()).hexdigest()
    if live_sha != live_expected[name]:
        raise SystemExit(f"LIVE_SHA_MISMATCH {name} expected={live_expected[name]} got={live_sha}")
    backup_v3 = Path(str(live) + ".bak-20260819-1055-tvread-v4")
    if not backup_v3.exists():
        raise SystemExit(f"V3_BACKUP_MISSING {name}")
    raw = backup_v3.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != v3_expected[name]:
        raise SystemExit(f"V3_BACKUP_SHA_MISMATCH {name} expected={v3_expected[name]} got={got}")
    text = raw.decode("utf-8")
    if "Markvarec TV sofa-readable profile: 20260819-tvread-v3" not in text:
        raise SystemExit(f"V3_MARKER_MISSING {name}")
    if "20260819-tvread-v4" in text or "20260819-tvread-v5" in text:
        raise SystemExit(f"V3_BACKUP_CONTAMINATED {name}")
    if text.count("</style>") < 1:
        raise SystemExit(f"STYLE_END_NOT_FOUND {name}")
    injection = "\n/* " + marker + " */\n" + overrides[name].strip() + "\n"
    prepared[name] = text.replace("</style>", injection + "</style>", 1)

for name, text in prepared.items():
    live = root / name
    shutil.copy2(live, Path(str(live) + f".bak-{stamp}-rejected-v5"))
    tmp = Path(str(live) + ".tvread-v6.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(live)

print("HNIZDO_TVREAD_V6_PATCHED")
for name in prepared:
    live = root / name
    print(name, hashlib.sha256(live.read_bytes()).hexdigest(), live.stat().st_size)
