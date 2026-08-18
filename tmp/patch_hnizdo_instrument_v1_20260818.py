from pathlib import Path
import hashlib
import re
import shutil

stamp = "20260818-2244-instrument-v1"
marker = "Markvarec TV instrument profile: 20260818-instrument-v1"

expected = {
    "lina-home-card.js": "3e3766e4bea4cc380731aa640bafdf4ff685ae1b1f86816b7c3cca0a89f3659d",
    "lina-weather-card.js": "c67f5f5c63b1fd66228c5c95fb3065664f4012848a100e97a5682bebe1dc7265",
    "lina-security-card.js": "cd5cd0c4d10456bd6c0147bd80bf282f18793f64f5821880072339d990fd4a19",
    "lina-climate-safety-card.js": "e408c12085ba68800d04e696eb6d9b723233f8c5ac85ccd9a8d800944d304708",
    "lina-energy-card.js": "b63f1d050fcef1ae4af2ecb5990d02dd9360e7f07491f901b1f0e51116ed97bf",
    "lina-rainwater-card.js": "6f3b93fc2ca5db8546a0f998fecaa8e4135dc45e024684aa23004114f94d6644",
}

root = Path("/config/www")
files = {name: root / name for name in expected}
backups = {}

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def replace_once(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return s.replace(old, new, 1)

def inject_css(s: str, css: str, label: str) -> str:
    token = "</style>"
    if token not in s:
        raise RuntimeError(f"{label}: no </style>")
    block = f"\n        /* {marker} */\n{css.rstrip()}\n"
    return s.replace(token, block + "      </style>", 1)

def rollback():
    for p, bak in backups.items():
        if bak.exists():
            shutil.copy2(bak, p)

try:
    for name, p in files.items():
        s = p.read_text(encoding="utf-8")
        if marker in s:
            print("ALREADY", name, sha256(p))
            continue
        actual = sha256(p)
        if actual != expected[name]:
            raise RuntimeError(f"{name}: SHA mismatch expected={expected[name]} actual={actual}")

    p = files["lina-home-card.js"]
    s = p.read_text(encoding="utf-8")
    bak = p.with_name(p.name + ".bak-" + stamp)
    shutil.copy2(p, bak); backups[p] = bak
    s = replace_once(s, '<div class="eyebrow">${this._esc(name)} · Linino Hnízdo</div>', '<div class="eyebrow">${this._esc(name)}</div>', "home eyebrow")
    s = inject_css(s, """
        .eyebrow { font-size:14px; letter-spacing:.06em; opacity:.78; }
        h2 { font-size:23px; }
        .sub { display:none; }
        .normal .thought { display:none; }
        .thought { font-size:15px; line-height:1.25; -webkit-line-clamp:2; }
        .chip small { display:none; }
        .chip strong { font-size:16px; }
        .activity-title,.activities { display:none; }
        .health { margin-top:2px; }
    """, "home css")
    p.write_text(s, encoding="utf-8")

    p = files["lina-weather-card.js"]
    s = p.read_text(encoding="utf-8")
    bak = p.with_name(p.name + ".bak-" + stamp)
    shutil.copy2(p, bak); backups[p] = bak
    s = inject_css(s, """
        .condition-text { font-size:16px; }
        .place,.temp-trend small,.rain-next small,.signal small,.radar-title,.irrigation small,.footer { display:none; }
        .temp-trend { font-size:14px; }
        .signal strong,.irrigation strong { font-size:16px; }
        .group-title { font-size:13px; opacity:.72; }
        .forecast-cell small { font-size:11px; opacity:.72; }
    """, "weather css")
    p.write_text(s, encoding="utf-8")

    p = files["lina-security-card.js"]
    s = p.read_text(encoding="utf-8")
    bak = p.with_name(p.name + ".bak-" + stamp)
    shutil.copy2(p, bak); backups[p] = bak
    s = inject_css(s, """
        .hero h2 { font-size:22px; }
        .hero p,.extra { display:none; }
        .warn .hero p,.critical .hero p { display:block; font-size:14px; line-height:1.25; opacity:.76; }
        .eyebrow { font-size:13px; opacity:.76; }
        .chip small { font-size:14px; opacity:.74; }
        .chip strong { font-size:16px; }
    """, "security css")
    p.write_text(s, encoding="utf-8")

    p = files["lina-climate-safety-card.js"]
    s = p.read_text(encoding="utf-8")
    bak = p.with_name(p.name + ".bak-" + stamp)
    shutil.copy2(p, bak); backups[p] = bak
    s = replace_once(s, '<div class="title"><strong>🌡️ ${this._esc(this._config.name)}</strong><small>teplota · vlhkost · zvířata · technika</small></div>', '<div class="title"><strong>🌡️ Klima</strong></div>', "climate header")
    s = replace_once(s, '<small>venku teď</small>', '<small>🌲 venku</small>', "climate outside now")
    s = replace_once(s, '<small>nejnižší do 48 h</small>', '<small>🌙 48 h</small>', "climate 48h")
    s = replace_once(s, '<em>${Number.isFinite(v.outH) ? `${v.outH.toFixed(0)} % vlhkost` : "místní Sencor"}</em>', '<em>${Number.isFinite(v.outH) ? `💧 ${v.outH.toFixed(0)} %` : "Sencor"}</em>', "climate outside humidity")
    s = replace_once(s, '<em>${Number.isFinite(a.forecast.max48) ? `maximum ${a.forecast.max48.toFixed(0)} °C` : (this._forecastLoading ? "načítám výhled…" : "výhled počasí")}</em>', '<em>${Number.isFinite(a.forecast.max48) ? `↑ ${a.forecast.max48.toFixed(0)} °C` : (this._forecastLoading ? "…" : "")}</em>', "climate 48h max")
    s, n = re.subn(r' : `<div class="all-good">✓ Aktuálně bez teplotního nebo vlhkostního problému\.</div>`;', ' : "";', s, count=1)
    if n != 1:
        raise RuntimeError(f"climate all-good: expected 1 match, got {n}")
    s = inject_css(s, """
        .title strong { font-size:20px; }
        .outside-box small { font-size:13px; opacity:.74; text-transform:none; letter-spacing:0; }
        .outside-box strong { font-size:22px; }
        .outside-box em { font-size:14px; opacity:.72; }
        .zone { padding:9px 8px; }
        .zone-head strong { font-size:16px; }
        .zone-values { margin-top:5px; gap:7px; }
        .zone-values .temp { font-size:25px; }
        .zone-values .hum { font-size:14px; opacity:.72; }
        .heater-main small { display:none; }
        .heater-main button { font-size:16px; }
        .pill { font-size:13px; }
        .all-good,.footer { display:none; }
        .issues:empty { display:none; }
        .issue strong { font-size:15px; }
        .issue small,.more-issues { font-size:13px; opacity:.74; }
    """, "climate css")
    p.write_text(s, encoding="utf-8")

    p = files["lina-energy-card.js"]
    s = p.read_text(encoding="utf-8")
    bak = p.with_name(p.name + ".bak-" + stamp)
    shutil.copy2(p, bak); backups[p] = bak
    s = replace_once(s, '<small>Celkové měřidlo</small>', '<small>Celkem</small>', "energy total label")
    s = replace_once(s, '<small>Tento měsíc</small>', '<small>Měsíc</small>', "energy month label")
    s = replace_once(s, '<small>Min. náklad dosud</small>', '<small>Účet min.</small>', "energy cost label")
    s = inject_css(s, """
        .title strong { font-size:20px; }
        .title small,.rate small,.loads-head { display:none; }
        .rate strong { font-size:18px; }
        .meta small { font-size:12px; opacity:.74; }
        .meta strong { font-size:17px; }
        .load-copy small { font-size:14px; opacity:.76; }
        .load-copy strong { font-size:18px; }
    """, "energy css")
    p.write_text(s, encoding="utf-8")

    p = files["lina-rainwater-card.js"]
    s = p.read_text(encoding="utf-8")
    bak = p.with_name(p.name + ".bak-" + stamp)
    shutil.copy2(p, bak); backups[p] = bak
    s = replace_once(s, '<div class="eyebrow">vodní semafor</div>', '', "water advice eyebrow")
    s = replace_once(s, '<small>očekávaný přítok ≈ ${this._fmt(inflow3,0," l")}</small>', '<small>→ ${this._fmt(inflow3,0," l")}</small>', "water rain3")
    s = replace_once(s, '<small>očekávaný přítok ≈ ${this._fmt(inflow5,0," l")}</small>', '<small>→ ${this._fmt(inflow5,0," l")}</small>', "water rain5")
    s = replace_once(s, '<small>poslední Savo</small>', '<small>Savo</small>', "water savo")
    s = replace_once(s, '<small>komfort vody</small>', '<small>Voda</small>', "water comfort")
    s = replace_once(s, '<small>jezírko</small><strong>${this._esc(pondCleaning)}</strong>', '<small>Jezírko</small><strong>${this._esc(pondCleaning)} · ${this._fmt(pondPower,0," W")}</strong>', "water pond power")
    s = inject_css(s, """
        .tank { width:64px; height:90px; }
        .tank-pct { font-size:16px; }
        .hero-copy .label { font-size:15px; opacity:.76; }
        .liters { font-size:40px; }
        .estimate,.section-title,.stat small,.quality p,.footer { display:none; }
        .advice strong { font-size:24px; }
        .advice small { font-size:14px; line-height:1.25; }
        .good .advice small,.wet .advice small { display:none; }
        .stats,.rain-grid,.water-quality { margin-top:7px; }
        .stat strong { font-size:17px; }
        .rain-box strong { font-size:16px; }
        .rain-box b { font-size:20px; }
        .rain-box small { font-size:14px; opacity:.76; font-weight:650; }
        .quality .qcopy small { font-size:12px; opacity:.74; }
        .quality .qcopy strong { font-size:16px; }
        .overflow-note strong { font-size:16px; }
        .overflow-note small { font-size:14px; opacity:.74; }
    """, "water css")
    p.write_text(s, encoding="utf-8")

    print("HNIZDO_INSTRUMENT_V1_PATCHED")
    for name, p in files.items():
        print(name, sha256(p), p.stat().st_size)

except Exception:
    rollback()
    raise
