import sqlite3, time, datetime, statistics, re
DB = "/config/home-assistant_v2.db"
con = sqlite3.connect(DB)
cur = con.cursor()

def metadata_id(entity):
    row = cur.execute("SELECT metadata_id FROM states_meta WHERE entity_id=?", (entity,)).fetchone()
    return row[0] if row else None

def state_rows(entity, days):
    mid = metadata_id(entity)
    if mid is None:
        return []
    start = time.time() - days * 86400
    before = cur.execute(
        "SELECT state,last_updated_ts FROM states WHERE metadata_id=? AND last_updated_ts<? ORDER BY last_updated_ts DESC LIMIT 1",
        (mid, start),
    ).fetchone()
    rows = cur.execute(
        "SELECT state,last_updated_ts FROM states WHERE metadata_id=? AND last_updated_ts>=? ORDER BY last_updated_ts",
        (mid, start),
    ).fetchall()
    return ([before] if before else []) + rows

def on_seconds(entity, days):
    rows = state_rows(entity, days)
    if not rows:
        return 0.0, 0
    start = time.time() - days * 86400
    end = time.time()
    total = 0.0
    intervals = 0
    for i, (state, ts) in enumerate(rows):
        a = max(float(ts), start)
        b = min(float(rows[i + 1][1]) if i + 1 < len(rows) else end, end)
        if state == "on" and b > a:
            total += b - a
            intervals += 1
    return total, intervals

for days in (7, 30):
    seconds, intervals = on_seconds("switch.zahrada_cerpadlo_destovka", days)
    print(f"PUMP_ON_{days}D_MIN={seconds/60:.2f} intervals={intervals}")

mid = metadata_id("sensor.zahrada_cerpadlo_destovka_vykon")
if mid is not None:
    start = time.time() - 30 * 86400
    vals = []
    for state, ts in cur.execute(
        "SELECT state,last_updated_ts FROM states WHERE metadata_id=? AND last_updated_ts>=? ORDER BY last_updated_ts",
        (mid, start),
    ):
        try:
            value = float(state)
        except (TypeError, ValueError):
            continue
        if value > 2:
            vals.append(value)
    if vals:
        print(
            "PUMP_ACTIVE_POWER_SAMPLES="
            f"{len(vals)} medianW={statistics.median(vals):.2f} minW={min(vals):.2f} maxW={max(vals):.2f}"
        )
    else:
        print("PUMP_ACTIVE_POWER_SAMPLES=0")

mid = metadata_id("sensor.sencor_srazky_dnes")
if mid is not None:
    start = time.time() - 8 * 86400
    daily = {}
    tz = datetime.timezone(datetime.timedelta(hours=2))
    for state, ts in cur.execute(
        "SELECT state,last_updated_ts FROM states WHERE metadata_id=? AND last_updated_ts>=? ORDER BY last_updated_ts",
        (mid, start),
    ):
        try:
            value = float(state)
        except (TypeError, ValueError):
            continue
        day = datetime.datetime.fromtimestamp(float(ts), tz).date().isoformat()
        daily[day] = max(daily.get(day, 0.0), value)
    print("RAIN_DAILY_MM=" + ";".join(f"{day}:{daily[day]:.2f}" for day in sorted(daily)))
    today = datetime.datetime.now(tz).date()
    for n in (4, 7):
        wanted = [(today - datetime.timedelta(days=i)).isoformat() for i in range(n)]
        print(f"RAIN_LAST_{n}D_MM={sum(daily.get(day,0.0) for day in wanted):.2f}")

con.close()

patterns = re.compile(r"zahrada_cerpadlo_destovka|destovka_.*(spotreba|prutok|kwh|energie)", re.I)
print("=== CONFIG_REUSE ===")
for path in ("/config/configuration.yaml", "/config/automations.yaml"):
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        continue
    for i, line in enumerate(lines, 1):
        if patterns.search(line):
            print(f"{path}:{i}:{line.strip()}")
