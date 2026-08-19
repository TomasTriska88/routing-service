from pathlib import Path
import hashlib
import shutil

marker = "Markvarec TV balanced hierarchy profile: 20260819-tvread-v5"
stamp = "20260819-1210-tvread-v5"
expected = {
    "lina-home-card.js": "d1cd5a77e88d151119404c236854cd0c71a9dae23afbdb9f1a56ac5676d5c836",
    "lina-weather-card.js": "ff25ebccf5d470c51c82c4ab8e314a463c3e6af5049ec098bd4fe499ded372d0",
    "lina-security-card.js": "82abe37b59a725acb1845a5d872aa8f8fe0c75f38b21f9fdfda3b818cc928e4e",
    "lina-climate-safety-card.js": "0f0756573cea027e224fe0127e94a4985803294127779a092c1e665a9c4d2c17",
    "lina-energy-card.js": "388ab5ec7ca59c3a4d4e4dfdcde2607f067d9fb2b4204719c0e27a41fe7caf03",
    "lina-rainwater-card.js": "f59ab82b8c144bcc6f6b0fc02394fa60e567608e647cbbb0655d235850a30ab7",
}

overrides = {
"lina-home-card.js": r'''@container (min-width:431px) {
.eyebrow{font-size:20px!important;font-weight:750!important;letter-spacing:.03em!important;opacity:.84!important}
h2{font-size:32px!important;line-height:1.03!important}.mode{font-size:19px!important;padding:5px 8px!important}
.chip small{font-size:20px!important;line-height:1.06!important;font-weight:650!important;opacity:.84!important}
.chip strong{font-size:26px!important;line-height:1.02!important}.chip>span{font-size:25px!important}
.thought{font-size:22px!important;line-height:1.12!important}
.activity-title,.activity time{font-size:20px!important}.activity strong{font-size:22px!important}
}''',
"lina-weather-card.js": r'''@container (min-width:431px) {
.condition-text{font-size:24px!important;line-height:1.04!important}.feels{font-size:20px!important}
.temp-trend{font-size:21px!important;line-height:1.08!important}.temp-trend small{font-size:22px!important;line-height:1.08!important}
.rain-next strong{font-size:29px!important}.rain-next small{font-size:22px!important;line-height:1.08!important}
.signal strong{font-size:23px!important}.signal small{font-size:22px!important;line-height:1.06!important}
.radar-title,.radar-point small{font-size:20px!important}.irrigation strong{font-size:26px!important}.irrigation small{font-size:22px!important}
.group-title{font-size:20px!important}.forecast-cell small{font-size:20px!important;white-space:nowrap!important}
.forecast-cell b{font-size:29px!important}.forecast-cell strong{font-size:25px!important}.forecast-cell em{display:none!important}.loading{font-size:22px!important}
}''',
"lina-security-card.js": r'''@container (min-width:431px) {
.eyebrow{font-size:20px!important}.hero h2{font-size:32px!important}.hero p{font-size:22px!important;line-height:1.1!important}
.status{font-size:19px!important;padding:5px 8px!important}.chip-icon{font-size:27px!important}
.chip small{font-size:20px!important;line-height:1.06!important}.chip strong{font-size:26px!important;line-height:1.03!important}
.extra{font-size:22px!important;line-height:1.08!important}
}''',
"lina-climate-safety-card.js": r'''@container (min-width:431px) {
.title strong{font-size:29px!important}.status{font-size:19px!important;padding:5px 8px!important}
.outside-box small{font-size:20px!important;white-space:nowrap!important}.outside-box strong{font-size:32px!important}
.zone-head strong{font-size:24px!important;line-height:1.02!important;white-space:nowrap!important;overflow-wrap:normal!important}
.zone-values .temp{font-size:36px!important}.zone-values .hum{font-size:21px!important}
.heater-main button{font-size:24px!important}.pill{font-size:20px!important}
.issue-icon{font-size:26px!important}.issue strong{font-size:24px!important}.issue small,.more-issues{font-size:22px!important;line-height:1.1!important}
}''',
"lina-energy-card.js": r'''@container (min-width:431px) {
.title strong{font-size:29px!important}.status{font-size:19px!important}
.reading strong{font-size:47px!important}.reading span{font-size:23px!important}.rate strong{font-size:27px!important}
.meta small{font-size:20px!important;white-space:nowrap!important;line-height:1.04!important}.meta strong{font-size:25px!important}
.load-copy small{font-size:24px!important;line-height:1.04!important}.load-copy strong{font-size:31px!important}
.loads-empty{font-size:22px!important}.issue strong{font-size:24px!important}.issue small{font-size:22px!important;line-height:1.08!important}
}''',
"lina-rainwater-card.js": r'''@container (min-width:431px) {
.tank-pct{font-size:24px!important}.hero-copy .label{font-size:24px!important;line-height:1.04!important;white-space:nowrap!important}
.liters{font-size:47px!important}.advice strong{font-size:32px!important}
.stat-icon{font-size:27px!important}.stat strong{font-size:25px!important}
.rain-box strong{font-size:22px!important;white-space:nowrap!important}.rain-box b{font-size:29px!important}.rain-box small{font-size:23px!important;line-height:1.06!important}
.overflow-note>span{font-size:30px!important}.overflow-note strong{font-size:25px!important}.overflow-note small{font-size:22px!important;line-height:1.08!important}
.quality .qicon{font-size:30px!important}.quality .qcopy small{font-size:20px!important;line-height:1.04!important;white-space:nowrap!important}
.quality .qcopy strong{font-size:25px!important;line-height:1.03!important}
}''',
}

root = Path("/config/www")
sources = {}
for name, expected_sha in expected.items():
    path = root / name
    raw = path.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != expected_sha:
        raise SystemExit(f"SHA_MISMATCH {name} expected={expected_sha} got={got}")
    text = raw.decode("utf-8")
    if marker in text:
        raise SystemExit(f"MARKER_ALREADY_PRESENT {name}")
    if text.count("</style>") < 1:
        raise SystemExit(f"STYLE_END_NOT_FOUND {name}")
    sources[name] = text

changed = []
for name, text in sources.items():
    path = root / name
    backup = Path(str(path) + f".bak-{stamp}")
    shutil.copy2(path, backup)
    injection = "\n/* " + marker + " */\n" + overrides[name].strip() + "\n"
    text = text.replace("</style>", injection + "</style>", 1)
    tmp = Path(str(path) + ".tvread-v5.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    changed.append((name, hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size))

print("HNIZDO_TVREAD_V5_PATCHED")
for name, sha, size in changed:
    print(name, sha, size)
