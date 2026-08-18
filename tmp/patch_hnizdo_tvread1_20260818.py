from pathlib import Path
import re, shutil, hashlib, subprocess

stamp = "20260818-1830-tvread1"
marker = "// Markvarec TV typography profile: 20260818-tvread1"
files = [
    Path("/config/www/lina-home-card.js"),
    Path("/config/www/lina-weather-card.js"),
    Path("/config/www/lina-security-card.js"),
    Path("/config/www/lina-climate-safety-card.js"),
    Path("/config/www/lina-energy-card.js"),
    Path("/config/www/lina-rainwater-card.js"),
]
font_map = {"8":"10", "9":"11", "10":"12", "11":"13", "12":"14", "13":"15"}
backups = {}

def rollback():
    for p, backup in backups.items():
        if backup.exists():
            shutil.copy2(backup, p)

try:
    for p in files:
        s = p.read_text(encoding="utf-8")
        if marker in s:
            print("ALREADY", p.name)
            continue
        backup = p.with_name(p.name + ".bak-" + stamp)
        shutil.copy2(p, backup)
        backups[p] = backup

        s = re.sub(
            r"font-size:(8|9|10|11|12|13)px",
            lambda m: f"font-size:{font_map[m.group(1)]}px",
            s,
        )

        out = []
        for line in s.splitlines(keepends=True):
            if "font-size:" in line and "opacity:." in line:
                def op(m):
                    value = float("0." + m.group(1))
                    return "opacity:.68" if value < 0.68 else m.group(0)
                line = re.sub(r"opacity:\.(\d+)", op, line)
            out.append(line)
        s = "".join(out)

        compact = {
            "lina-home-card.js": [
                ("padding:14px 16px 13px;", "padding:11px 13px 10px;"),
                ("flex-direction:column; gap:10px;", "flex-direction:column; gap:8px;"),
            ],
            "lina-security-card.js": [
                ("padding:14px 16px 12px;", "padding:11px 13px 10px;"),
                ("flex-direction:column; gap:10px;", "flex-direction:column; gap:8px;"),
            ],
            "lina-climate-safety-card.js": [
                (".wrap { padding:12px 13px;", ".wrap { padding:10px 12px;"),
            ],
            "lina-energy-card.js": [
                ("padding:14px 16px 13px;", "padding:11px 13px 10px;"),
                ("gap:10px;", "gap:8px;"),
            ],
            "lina-rainwater-card.js": [
                ("padding:14px 16px 12px;", "padding:11px 13px 10px;"),
            ],
        }.get(p.name, [])
        for old, new in compact:
            if old in s:
                s = s.replace(old, new, 1)

        if p.name == "lina-energy-card.js":
            s = s.replace(
                ".load-copy small { display:block; font-size:10px;",
                ".load-copy small { display:block; font-size:13px;",
                1,
            )
            s = s.replace(
                ".load-copy strong { display:block; font-size:14px;",
                ".load-copy strong { display:block; font-size:16px;",
                1,
            )
        if p.name == "lina-security-card.js":
            s = s.replace(
                ".chip small { display:block; font-size:11px;",
                ".chip small { display:block; font-size:13px;",
                1,
            )
        if p.name == "lina-home-card.js":
            s = s.replace(
                ".activity strong { font-size:11px;",
                ".activity strong { font-size:12px;",
                1,
            )

        p.write_text(marker + "\n" + s, encoding="utf-8")

    for p in files:
        data = p.read_bytes()
        print(p.name, len(data), hashlib.sha256(data).hexdigest())
except Exception:
    rollback()
    raise
