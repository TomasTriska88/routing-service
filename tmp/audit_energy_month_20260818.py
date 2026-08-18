from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ENTITY = "sensor.vnitrni_rozvadec_celkova_energie"
PRICE_ENTITY = "sensor.elektrina_aktualni_promena_cena"

prefs_raw = json.loads(Path("/config/.storage/energy").read_text(encoding="utf-8"))
prefs = prefs_raw.get("data", {})
grids = [
    s for s in prefs.get("energy_sources", [])
    if s.get("type") == "grid" and s.get("stat_energy_from") == ENTITY
]
print("ENERGY_PREFS=" + json.dumps(grids, ensure_ascii=False, sort_keys=True))

con = sqlite3.connect("/config/home-assistant_v2.db")
con.row_factory = sqlite3.Row
meta = con.execute(
    "SELECT * FROM statistics_meta WHERE statistic_id = ?", (ENTITY,)
).fetchone()
if meta is None:
    print("STAT_META=NOT_FOUND")
else:
    print("STAT_META=" + json.dumps(dict(meta), ensure_ascii=False, default=str, sort_keys=True))
    metadata_id = meta["id"]
    now = datetime.now(ZoneInfo("Europe/Prague"))
    start_local = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_ts = start_local.timestamp()
    print(f"MONTH_START_LOCAL={start_local.isoformat()} START_TS={start_ts}")

    cols = [r[1] for r in con.execute("PRAGMA table_info(statistics)").fetchall()]
    print("STAT_COLUMNS=" + ",".join(cols))

    around = con.execute(
        "SELECT start_ts, state, sum FROM statistics "
        "WHERE metadata_id = ? AND start_ts BETWEEN ? AND ? "
        "ORDER BY start_ts",
        (metadata_id, start_ts - 10800, start_ts + 10800),
    ).fetchall()
    print("AROUND_START=" + json.dumps([dict(r) for r in around], default=str))

    baseline = con.execute(
        "SELECT start_ts, state, sum FROM statistics "
        "WHERE metadata_id = ? AND start_ts >= ? ORDER BY start_ts LIMIT 1",
        (metadata_id, start_ts),
    ).fetchone()
    latest = con.execute(
        "SELECT start_ts, state, sum FROM statistics "
        "WHERE metadata_id = ? ORDER BY start_ts DESC LIMIT 1",
        (metadata_id,),
    ).fetchone()
    print("BASELINE=" + json.dumps(dict(baseline) if baseline else None, default=str))
    print("LATEST=" + json.dumps(dict(latest) if latest else None, default=str))
    if baseline and latest and baseline["sum"] is not None and latest["sum"] is not None:
        consumption = float(latest["sum"]) - float(baseline["sum"])
        print(f"MONTH_CONSUMPTION_KWH={consumption:.9f}")

svc = Path("/usr/src/homeassistant/homeassistant/components/utility_meter/services.yaml")
if svc.exists():
    text = svc.read_text(encoding="utf-8")
    idx = text.find("calibrate:")
    if idx >= 0:
        print("UTILITY_CALIBRATE_SCHEMA=" + text[idx:idx+900].replace("\n", "\\n"))
    else:
        print("UTILITY_CALIBRATE_SCHEMA=NOT_FOUND")
else:
    print("UTILITY_CALIBRATE_SCHEMA_FILE=NOT_FOUND")

con.close()
