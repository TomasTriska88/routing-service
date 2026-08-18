from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

FILES = {
    "/config/www/lina-home-card.js": "9b468964b75ebae7a1c2feb1542460cc93e957ac284450b02abdce83a7da1976",
    "/config/www/lina-weather-card.js": "044412dd7353849279bccdbc5674165d8a646a8cadfda5123603e7537b74939d",
    "/config/www/lina-security-card.js": "b09c54675ec334840b8cf16eb7dad04162f2f09dbd2258bbcda653a7d0467d40",
    "/config/www/lina-rainwater-card.js": "845c14f8b3bc757223ee3a0b21d202bc469538c56d3189b9ea2727f269110d4d",
    "/config/.storage/lovelace_resources": "3a9ce1e748b33547189890d2fac2c1d05b15d669c1761a9fa6081507288d22f4",
}

STAGED_SUFFIX = ".new-fit1"
STATE = Path("/tmp/hnizdo_fit1_state.json")


def sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def verify_live() -> None:
    for path, expected in FILES.items():
        actual = sha(path)
        if actual != expected:
            raise RuntimeError(f"live source changed: {path} expected={expected} actual={actual}")


def prepare() -> None:
    verify_live()
    staged = {}

    p = Path("/config/www/lina-home-card.js")
    s = p.read_text(encoding="utf-8")
    s = replace_once(
        s,
        ".activity-title { margin-top:auto; font-size:9px; text-transform:uppercase; letter-spacing:.09em; opacity:.48; }",
        ".activity-title { margin-top:2px; font-size:9px; text-transform:uppercase; letter-spacing:.09em; opacity:.48; }",
        "home activity spacer",
    )
    out = Path(str(p) + STAGED_SUFFIX)
    out.write_text(s, encoding="utf-8")
    staged[str(p)] = {"stage": str(out), "sha": sha(out), "size": out.stat().st_size}

    p = Path("/config/www/lina-security-card.js")
    s = p.read_text(encoding="utf-8")
    s = replace_once(
        s,
        ".grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:7px; margin-top:auto; }",
        ".grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:7px; margin-top:2px; }",
        "security grid spacer",
    )
    out = Path(str(p) + STAGED_SUFFIX)
    out.write_text(s, encoding="utf-8")
    staged[str(p)] = {"stage": str(out), "sha": sha(out), "size": out.stat().st_size}

    p = Path("/config/www/lina-weather-card.js")
    s = p.read_text(encoding="utf-8")
    s = replace_once(
        s,
        'if (Number.isFinite(hum) && hum >= 85) signals.push(["💧","vysoká vlhkost",`${Math.round(hum)} %`,""]);',
        'if (Number.isFinite(hum) && hum >= 85 && !rainSoon) signals.push(["💧","vysoká vlhkost",`${Math.round(hum)} %`,""]);',
        "weather redundant humidity",
    )
    s = replace_once(
        s,
        "@container (max-width:520px) {",
        "@container (max-width:430px) {",
        "weather responsive breakpoint",
    )
    out = Path(str(p) + STAGED_SUFFIX)
    out.write_text(s, encoding="utf-8")
    staged[str(p)] = {"stage": str(out), "sha": sha(out), "size": out.stat().st_size}

    p = Path("/config/www/lina-rainwater-card.js")
    s = p.read_text(encoding="utf-8")
    s = replace_once(
        s,
        "padding:14px 16px 12px;",
        "padding:11px 13px 10px;",
        "water outer padding",
    )
    s = replace_once(
        s,
        ".top { display:grid; grid-template-columns:1.02fr .98fr; gap:10px; align-items:stretch; min-width:0; }",
        ".top { display:grid; grid-template-columns:1.02fr .98fr; gap:8px; align-items:stretch; min-width:0; }",
        "water top gap",
    )
    s = replace_once(
        s,
        ".section-title { font-size:11px; text-transform:uppercase; letter-spacing:.09em; opacity:.55; margin:11px 1px 5px; }",
        ".section-title { font-size:10px; text-transform:uppercase; letter-spacing:.09em; opacity:.55; margin:7px 1px 4px; }",
        "water section spacing",
    )
    s = replace_once(
        s,
        "@container (max-width:520px) {",
        "@container (max-width:430px) {",
        "water responsive breakpoint",
    )
    out = Path(str(p) + STAGED_SUFFIX)
    out.write_text(s, encoding="utf-8")
    staged[str(p)] = {"stage": str(out), "sha": sha(out), "size": out.stat().st_size}

    p = Path("/config/.storage/lovelace_resources")
    data = json.loads(p.read_text(encoding="utf-8"))
    replacements = {
        "/local/lina-weather-card.js?v=20260818-tv2": "/local/lina-weather-card.js?v=20260818-fit1",
        "/local/lina-rainwater-card.js?v=20260818-water2": "/local/lina-rainwater-card.js?v=20260818-fit1",
        "/local/lina-security-card.js?v=20260818-v2": "/local/lina-security-card.js?v=20260818-fit1",
        "/local/lina-home-card.js?v=20260818-v1": "/local/lina-home-card.js?v=20260818-fit1",
    }
    items = data.get("data", {}).get("items", [])
    seen = {old: 0 for old in replacements}
    for item in items:
        url = item.get("url")
        if url in replacements:
            seen[url] += 1
            item["url"] = replacements[url]
    bad = {k: v for k, v in seen.items() if v != 1}
    if bad:
        raise RuntimeError(f"resource replacement count mismatch: {bad}")
    out = Path(str(p) + STAGED_SUFFIX)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    json.loads(out.read_text(encoding="utf-8"))
    staged[str(p)] = {"stage": str(out), "sha": sha(out), "size": out.stat().st_size}

    STATE.write_text(json.dumps({"staged": staged}, ensure_ascii=False), encoding="utf-8")
    print("HNIZDO_FIT1_PREPARED")
    for path, meta in staged.items():
        print(path, meta["sha"], meta["size"])


def commit() -> None:
    verify_live()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    staged = state["staged"]

    for path, meta in staged.items():
        if sha(meta["stage"]) != meta["sha"]:
            raise RuntimeError(f"staged hash changed: {path}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = []
    for path, meta in staged.items():
        live = Path(path)
        backup = Path(f"{path}.bak-fit1-{stamp}")
        backup.write_bytes(live.read_bytes())
        backups.append(str(backup))

    for path, meta in staged.items():
        os.replace(meta["stage"], path)

    print("HNIZDO_FIT1_COMMITTED", stamp)
    for path in staged:
        print(path, sha(path), Path(path).stat().st_size)
    print("BACKUPS", ",".join(backups))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "commit"}:
        raise SystemExit("usage: patch_hnizdo_fit1.py prepare|commit")
    globals()[sys.argv[1]]()
