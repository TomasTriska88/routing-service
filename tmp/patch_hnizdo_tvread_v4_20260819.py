from pathlib import Path
import hashlib
import shutil

marker = "Markvarec TV accessibility profile: 20260819-tvread-v4"
stamp = "20260819-1055-tvread-v4"
expected = {
    "lina-home-card.js": "8c9a4778efa247837e008b9c6cc452e698970f22a6cf0de3486b165c8bdfca00",
    "lina-weather-card.js": "969b9b9f533f5023098802725e091cfd5992bea29896ddad2605a5b10c7731a1",
    "lina-security-card.js": "255562287462ffa7945160e7859b286fbc9e7dd4d0c52499986c3a21b7894273",
    "lina-climate-safety-card.js": "4e953dc8f0f202510f17153b68b73539a6851e49db22ea2d00734a213f38b083",
    "lina-energy-card.js": "694bc07f972770b33d466e15629e4b6eeeddca749b0dbf0ed6c01e4b60d93762",
    "lina-rainwater-card.js": "c5f853d930c05edb50099053a5b527f760bfbf6842412d63aaa3f210687148ad",
}

overrides = {
"lina-home-card.js": r'''@container (min-width:431px) {
.eyebrow{font-size:23px!important}.mode{font-size:22px!important}h2{font-size:35px!important}
.chip small{font-size:23px!important}.chip strong{font-size:29px!important}.chip>span{font-size:28px!important}
.thought{font-size:24px!important}.activity-title,.activity time{font-size:22px!important}.activity strong{font-size:24px!important}
}''',
"lina-weather-card.js": r'''@container (min-width:431px) {
.condition-text{font-size:27px!important}.feels{font-size:22px!important}.temp-trend{font-size:23px!important}.temp-trend small{font-size:22px!important}
.rain-next strong{font-size:31px!important}.rain-next small{font-size:23px!important}.signal strong{font-size:25px!important}.signal small{font-size:22px!important}
.radar-title,.radar-point small{font-size:22px!important}.irrigation strong{font-size:28px!important}.irrigation small{font-size:23px!important}
.group-title{font-size:23px!important}.forecast-cell small{font-size:22px!important}.forecast-cell b{font-size:31px!important}
.forecast-cell strong{font-size:27px!important}.forecast-cell em{display:none!important}.loading{font-size:22px!important}
}''',
"lina-security-card.js": r'''@container (min-width:431px) {
.eyebrow{font-size:23px!important}.hero h2{font-size:35px!important}.hero p{font-size:23px!important}.status{font-size:22px!important}
.chip-icon{font-size:30px!important}.chip small{font-size:23px!important}.chip strong{font-size:29px!important}.extra{font-size:22px!important}
}''',
"lina-climate-safety-card.js": r'''@container (min-width:431px) {
.title strong{font-size:31px!important}.status{font-size:22px!important}.outside-box small{font-size:22px!important}
.outside-box strong{font-size:35px!important}.zone-head strong{font-size:27px!important}.zone-values .temp{font-size:39px!important}
.zone-values .hum{font-size:23px!important}.heater-main button{font-size:26px!important}.pill{font-size:22px!important}
.issue-icon{font-size:28px!important}.issue strong{font-size:26px!important}.issue small,.more-issues{font-size:22px!important}
}''',
"lina-energy-card.js": r'''@container (min-width:431px) {
.title strong{font-size:31px!important}.status{font-size:22px!important}.reading strong{font-size:48px!important}.reading span{font-size:26px!important}
.rate strong{font-size:29px!important}.meta small{font-size:22px!important}.meta strong{font-size:27px!important}
.load-copy small{font-size:27px!important}.load-copy strong{font-size:34px!important}.loads-empty{font-size:23px!important}
.issue strong{font-size:26px!important}.issue small{font-size:22px!important}
}''',
"lina-rainwater-card.js": r'''@container (min-width:431px) {
.tank-pct{font-size:26px!important}.hero-copy .label{font-size:27px!important}.liters{font-size:49px!important}
.advice strong{font-size:35px!important}.stat-icon{font-size:29px!important}.stat strong{font-size:27px!important}
.rain-box strong{font-size:25px!important}.rain-box b{font-size:31px!important}.rain-box small{font-size:23px!important}
.overflow-note>span{font-size:32px!important}.overflow-note strong{font-size:27px!important}.overflow-note small{font-size:22px!important}
.quality .qicon{font-size:32px!important}.quality .qcopy small{font-size:22px!important}.quality .qcopy strong{font-size:27px!important}
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
    tmp = Path(str(path) + ".tvread-v4.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    changed.append((name, hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size))

print("HNIZDO_TVREAD_V4_PATCHED")
for name, sha, size in changed:
    print(name, sha, size)
