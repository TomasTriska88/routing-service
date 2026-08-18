from pathlib import Path
import hashlib
import shutil

marker = "Markvarec TV readable text profile: 20260818-tvtext-v2"
stamp = "20260818-2259-tvtext-v2"
expected = {
    "lina-home-card.js": "4a60e370720f4868aa4f57945f24db488b7a95c68ae8aa7574438b7c6ffaa92a",
    "lina-weather-card.js": "346c556aababeee7c6331ff677be61ad34dcd7cb08a59117639aa4d1808d1a5e",
    "lina-security-card.js": "6f8ec2b5814ff632f587dc7ddab040dc9d05d15f3155aacad130cf23da10df39",
    "lina-climate-safety-card.js": "a6185d2e72580d606696ce33ae23c6856138c381a4fdaccefa4e131e42f34b1f",
    "lina-energy-card.js": "65488b878959eccaea15cf6b987badbbbf2fa3a5dfe281aa41e22f3879ecfcad",
    "lina-rainwater-card.js": "99af2b8b0d4d6c92867df4414c889e3fcf9379db5cdcd0892647e5ad57363576"
}
overrides = {
    "lina-home-card.js": r"""
@container (min-width:431px) {
  .eyebrow { font-size:16px !important; letter-spacing:.05em !important; }
  h2 { font-size:25px !important; line-height:1.06 !important; }
  .sub { font-size:16px !important; line-height:1.15 !important; }
  .mode { font-size:15px !important; padding:5px 8px !important; }
  .thought { font-size:16px !important; line-height:1.18 !important; }
  .chip small { font-size:15px !important; opacity:.76 !important; }
  .chip strong { font-size:18px !important; line-height:1.05 !important; }
  .activity-title,.activity time { font-size:15px !important; }
  .activity strong { font-size:16px !important; }
}""",
    "lina-weather-card.js": r"""
@container (min-width:431px) {
  .feels { font-size:15px !important; }
  .condition-text { font-size:18px !important; }
  .temp-trend { font-size:16px !important; line-height:1.12 !important; }
  .temp-trend small,.place,.rain-next small,.signal small,.radar-title,
  .radar-point small,.irrigation small,.forecast-cell small,.forecast-cell em,
  .loading,.footer { font-size:15px !important; opacity:.76 !important; }
  .signal strong,.irrigation strong { font-size:18px !important; }
  .group-title { font-size:16px !important; opacity:.78 !important; }
  .forecast-cell b { font-size:20px !important; }
  .forecast-cell strong { font-size:17px !important; }
}""",
    "lina-security-card.js": r"""
@container (min-width:431px) {
  .eyebrow { font-size:16px !important; letter-spacing:.05em !important; opacity:.78 !important; }
  .hero h2 { font-size:25px !important; line-height:1.06 !important; }
  .hero p { font-size:16px !important; line-height:1.16 !important; }
  .status { font-size:15px !important; padding:5px 8px !important; }
  .chip-icon { font-size:23px !important; }
  .chip small { font-size:16px !important; opacity:.78 !important; }
  .chip strong { font-size:19px !important; line-height:1.05 !important; }
  .extra { font-size:15px !important; opacity:.76 !important; }
}""",
    "lina-climate-safety-card.js": r"""
@container (min-width:431px) {
  .title strong { font-size:22px !important; line-height:1.05 !important; }
  .title small { font-size:15px !important; }
  .status { font-size:15px !important; padding:5px 8px !important; }
  .outside-box small { font-size:15px !important; opacity:.78 !important; }
  .outside-box strong { font-size:23px !important; }
  .outside-box em { font-size:15px !important; opacity:.76 !important; }
  .zone-head strong { font-size:19px !important; line-height:1.04 !important; }
  .zone-values .temp { font-size:27px !important; }
  .zone-values .hum { font-size:16px !important; opacity:.76 !important; }
  .heater-main small { font-size:15px !important; opacity:.76 !important; }
  .heater-main button { font-size:18px !important; line-height:1.05 !important; }
  .pill { font-size:15px !important; padding:4px 7px !important; }
  .more-issues { font-size:15px !important; }
  .issue strong { font-size:17px !important; }
  .issue small { font-size:15px !important; line-height:1.15 !important; opacity:.78 !important; }
}""",
    "lina-energy-card.js": r"""
@container (min-width:431px) {
  .title strong { font-size:20px !important; line-height:1.05 !important; }
  .title small { font-size:15px !important; opacity:.76 !important; }
  .status { font-size:15px !important; }
  .reading span { font-size:18px !important; }
  .rate strong { font-size:18px !important; }
  .rate small { font-size:15px !important; opacity:.76 !important; }
  .meta small { font-size:15px !important; opacity:.76 !important; letter-spacing:0 !important; }
  .meta strong { font-size:18px !important; }
  .loads-head strong,.loads-head span { font-size:15px !important; opacity:.76 !important; }
  .load-copy small { font-size:18px !important; opacity:.8 !important; }
  .load-copy strong { font-size:21px !important; }
  .loads-empty { font-size:15px !important; }
  .issue strong { font-size:17px !important; }
  .issue small { font-size:15px !important; opacity:.78 !important; }
}""",
    "lina-rainwater-card.js": r"""
@container (min-width:431px) {
  .tank-pct { font-size:18px !important; }
  .hero-copy .label { font-size:18px !important; opacity:.8 !important; letter-spacing:.04em !important; }
  .estimate { font-size:15px !important; opacity:.76 !important; }
  .advice .eyebrow { font-size:15px !important; opacity:.78 !important; letter-spacing:.05em !important; }
  .advice strong { font-size:25px !important; line-height:1.02 !important; }
  .advice small { font-size:15px !important; line-height:1.16 !important; opacity:.78 !important; }
  .stat strong { font-size:18px !important; }
  .stat small { font-size:15px !important; opacity:.76 !important; }
  .rain-box strong { font-size:18px !important; }
  .rain-box b { font-size:21px !important; }
  .rain-box small { font-size:15px !important; opacity:.78 !important; }
  .overflow-note strong { font-size:18px !important; }
  .overflow-note small { font-size:15px !important; opacity:.78 !important; }
  .quality .qcopy small { font-size:15px !important; opacity:.78 !important; letter-spacing:.02em !important; }
  .quality .qcopy strong { font-size:18px !important; }
  .quality p,.footer { font-size:15px !important; opacity:.76 !important; }
}"""
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
    tmp = Path(str(path) + ".tvtext-v2.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    changed.append((name, hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size))

print("HNIZDO_TVTEXT_V2_PATCHED")
for name, sha, size in changed:
    print(name, sha, size)
