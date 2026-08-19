from pathlib import Path
import hashlib
import shutil

marker = "Markvarec TV sofa-readable profile: 20260819-tvread-v3"
stamp = "20260819-1050-tvread-v3"
expected = {
    "lina-home-card.js": "70af8438a88a50a5f5389f0cd280b65ca2f0dd3b4e4a9d7d0638e9d2a2153140",
    "lina-weather-card.js": "ec07e043d7d34950d118f1e68c6589a73956a14899a9ace89d50ec6518b31cc7",
    "lina-security-card.js": "1d4827aa8eedd742943652404cd7d9517441386534b4d3452478a35973b6538b",
    "lina-climate-safety-card.js": "93e3a832ea1597dabe39cef371b149c3b32180ef079ce67263df695301cedea3",
    "lina-energy-card.js": "f7c38b269012a061a53a382e07c42648eef249f368db5d2901222b4004c5e679",
    "lina-rainwater-card.js": "d8a9a53af3c2d05d1159ac32ee781c395ba20e67a56f93ef801af6abbe8a8269",
}

overrides = {
"lina-home-card.js": r'''@container (min-width:431px) {
.wrap{gap:6px!important;padding:9px 11px 8px!important}.hero{gap:9px!important}.avatar{font-size:48px!important}
.eyebrow{font-size:20px!important;font-weight:750!important;letter-spacing:.02em!important;opacity:.86!important}
h2{font-size:32px!important;line-height:1.02!important}.sub{display:none!important}.mode{font-size:19px!important;padding:5px 9px!important}
.thought{font-size:21px!important;line-height:1.12!important;padding:7px 9px!important;-webkit-line-clamp:2!important}
.wrap.normal .thought,.wrap.normal .activity-title,.wrap.normal .activities{display:none!important}
.health{gap:5px!important}.chip{padding:7px 8px!important;gap:7px!important}.chip>span{font-size:24px!important}
.chip small{font-size:19px!important;font-weight:650!important;opacity:.86!important}.chip strong{font-size:24px!important;line-height:1.02!important;margin-top:2px!important}
.activity-title,.activity time{font-size:18px!important;opacity:.82!important}.activity strong{font-size:20px!important}.activity{padding:4px 6px!important}
}''',
"lina-weather-card.js": r'''@container (min-width:431px) {
.wrap{padding:9px 11px 8px!important}.top{gap:6px!important}.condition{font-size:48px!important}.temp{font-size:42px!important}
.feels{font-size:19px!important;opacity:.84!important}.condition-text{font-size:23px!important;font-weight:700!important;line-height:1.05!important}
.temp-trend{font-size:20px!important;line-height:1.08!important;opacity:.9!important}.temp-trend small{font-size:18px!important;line-height:1.08!important;opacity:.84!important}
.place{display:none!important}.rain-next{padding:7px 9px!important;gap:7px!important}.rain-next .drop{font-size:31px!important}.rain-next strong{font-size:27px!important;line-height:1.02!important}
.rain-next small{font-size:19px!important;line-height:1.08!important;opacity:.86!important}.signals{gap:4px!important;margin-top:5px!important}.signal{padding:5px 6px!important;gap:5px!important}
.signal>span{font-size:23px!important}.signal strong{font-size:21px!important;line-height:1.03!important}.signal small{font-size:18px!important;opacity:.84!important}
.radar-wrap{margin-top:5px!important;padding:5px 6px 3px!important}.radar-title{font-size:18px!important;font-weight:650!important;opacity:.84!important}.radar-point small{font-size:18px!important;opacity:.86!important}
.irrigation{padding:6px 8px!important}.irrigation strong{font-size:24px!important;line-height:1.02!important}.irrigation small{font-size:19px!important;line-height:1.08!important;opacity:.86!important}
.group-title{font-size:20px!important;font-weight:750!important;letter-spacing:.02em!important;opacity:.88!important;margin-bottom:2px!important}.forecast{gap:3px!important}.forecast-cell{padding:4px 2px!important}
.forecast-cell small{font-size:18px!important;font-weight:700!important;opacity:.9!important}.forecast-cell b{font-size:27px!important;line-height:1!important;margin:0!important}
.forecast-cell strong{font-size:23px!important;line-height:1.02!important}.forecast-cell em{font-size:18px!important;opacity:.86!important;min-height:0!important}.loading{font-size:19px!important}.footer{display:none!important}
}''',
"lina-security-card.js": r'''@container (min-width:431px) {
.wrap{padding:9px 11px 8px!important;gap:6px!important}.hero{gap:9px!important}.hero-icon{font-size:48px!important}
.eyebrow{font-size:20px!important;font-weight:750!important;letter-spacing:.02em!important;opacity:.86!important}.hero h2{font-size:31px!important;line-height:1.02!important}
.hero p{font-size:20px!important;line-height:1.1!important;opacity:.86!important}.normal .hero p{display:none!important}.status{font-size:19px!important;padding:5px 9px!important}
.grid{gap:5px!important}.chip{padding:7px 8px!important;gap:7px!important}.chip-icon{font-size:27px!important}.chip small{font-size:20px!important;font-weight:650!important;opacity:.88!important;white-space:normal!important}
.chip strong{font-size:25px!important;line-height:1.02!important;margin-top:1px!important}.extra{font-size:19px!important;opacity:.84!important}
}''',
"lina-climate-safety-card.js": r'''@container (min-width:431px) {
.wrap{padding:8px 10px!important}.title strong{font-size:29px!important;line-height:1.02!important}.title small{display:none!important}.status{font-size:19px!important;padding:5px 9px!important}
.outside{gap:5px!important;margin-top:6px!important}.outside-box{padding:6px 7px!important}.outside-box small{font-size:19px!important;font-weight:700!important;opacity:.88!important}
.outside-box strong{font-size:31px!important;line-height:1!important}.outside-box em{display:none!important}.zones{gap:4px!important;margin-top:5px!important}.zone{padding:6px!important}
.zone-head{gap:4px!important}.zone-head strong{font-size:23px!important;font-weight:750!important;line-height:1.02!important}.zone-values{gap:5px!important;margin-top:2px!important}
.zone-values .temp{font-size:34px!important;line-height:1!important}.zone-values .hum{font-size:20px!important;font-weight:650!important;opacity:.86!important}
.heater{margin-top:5px!important;padding:6px 7px!important;gap:5px!important}.heater-main small{display:none!important}.heater-main button{font-size:22px!important;line-height:1.03!important}
.pill{font-size:19px!important;padding:4px 7px!important}.issues{gap:4px!important;margin-top:5px!important}.issue{padding:5px 7px!important;gap:6px!important}
.issue-icon{font-size:24px!important}.issue strong{font-size:22px!important;line-height:1.05!important}.issue small{font-size:19px!important;line-height:1.1!important;opacity:.88!important}
.more-issues{font-size:19px!important;opacity:.86!important}.all-good,.footer{display:none!important}
}''',
"lina-energy-card.js": r'''@container (min-width:431px) {
.wrap{padding:8px 10px!important;gap:5px!important}.title strong{font-size:28px!important;line-height:1.02!important}.title small{display:none!important}.status{font-size:19px!important;padding:5px 9px!important}
.hero{gap:7px!important}.reading strong{font-size:46px!important;line-height:.95!important}.reading span{font-size:22px!important}.rate strong{font-size:25px!important;line-height:1.02!important}.rate small{display:none!important}
.meter{margin-top:3px!important;margin-bottom:3px!important}.meta{gap:4px!important}.meta button{padding:5px 5px!important}.meta small{font-size:19px!important;font-weight:700!important;opacity:.88!important;letter-spacing:0!important}
.meta strong{font-size:23px!important;line-height:1.02!important}.loads-head{display:none!important}.loads{gap:4px!important;margin-top:4px!important}.load{padding:5px 7px!important}
.load-copy small{font-size:23px!important;font-weight:750!important;opacity:.94!important;line-height:1.03!important;white-space:normal!important}.load-copy strong{font-size:29px!important;line-height:1!important}
.loads-empty{font-size:20px!important}.issue{padding:5px 7px!important}.issue strong{font-size:22px!important;line-height:1.05!important}.issue small{font-size:19px!important;line-height:1.08!important;opacity:.88!important}
}''',
"lina-rainwater-card.js": r'''@container (min-width:431px) {
.wrap{padding:8px 10px!important}.top{gap:6px!important}.hero{grid-template-columns:82px minmax(0,1fr)!important;gap:9px!important;padding:6px!important}
.tank{width:66px!important;height:94px!important}.tank-pct{font-size:23px!important}.hero-copy .label{font-size:23px!important;font-weight:750!important;opacity:.9!important;letter-spacing:.02em!important}
.liters{font-size:46px!important;line-height:.95!important;margin:2px 0!important}.estimate{display:none!important}.advice{padding:7px 9px!important}.advice .eyebrow{display:none!important}
.advice strong{font-size:31px!important;line-height:1.01!important;margin:0!important}.advice small{display:none!important}.stats{gap:4px!important;margin-top:5px!important}
.stat{padding:6px!important;gap:5px!important}.stat-icon{font-size:25px!important}.stat strong{font-size:23px!important;line-height:1.02!important}.stat small{display:none!important}
.rain-grid{gap:5px!important;margin-top:5px!important}.rain-box{padding:6px 8px!important}.rain-box strong{font-size:22px!important}.rain-box b{font-size:27px!important}
.rain-box small{font-size:20px!important;font-weight:700!important;opacity:.9!important;line-height:1.05!important}.overflow-note{padding:6px 8px!important;margin-top:4px!important}
.overflow-note>span{font-size:29px!important}.overflow-note strong{font-size:23px!important}.overflow-note small{font-size:19px!important;opacity:.88!important}
.water-quality{gap:4px!important;margin-top:5px!important}.quality{padding:6px 7px!important}.quality .qicon{font-size:29px!important}
.quality .qcopy small{font-size:19px!important;font-weight:700!important;opacity:.88!important;letter-spacing:0!important}.quality .qcopy strong{font-size:23px!important;line-height:1.02!important}
.quality p,.footer,.section-title{display:none!important}
}''',
}

root = Path("/config/www")
changed = []
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
    backup = Path(str(path) + f".bak-{stamp}")
    shutil.copy2(path, backup)
    injection = "\n/* " + marker + " */\n" + overrides[name].strip() + "\n"
    text = text.replace("</style>", injection + "</style>", 1)
    tmp = Path(str(path) + ".tvread-v3.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    changed.append((name, hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size))
print("HNIZDO_TVREAD_V3_PATCHED")
for name, sha, size in changed:
    print(name, sha, size)
