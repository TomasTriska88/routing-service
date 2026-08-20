import sqlite3, datetime
DB="/config/home-assistant_v2.db"
con=sqlite3.connect(DB)
cur=con.cursor()
tz=datetime.timezone(datetime.timedelta(hours=2))
for entity in ("switch.zahrada_cerpadlo_destovka","sensor.zahrada_cerpadlo_destovka_vykon"):
    row=cur.execute("SELECT metadata_id FROM states_meta WHERE entity_id=?",(entity,)).fetchone()
    if not row:
        print(entity,"NO_METADATA")
        continue
    mid=row[0]
    first=cur.execute("SELECT state,last_updated_ts FROM states WHERE metadata_id=? ORDER BY last_updated_ts LIMIT 1",(mid,)).fetchone()
    last=cur.execute("SELECT state,last_updated_ts FROM states WHERE metadata_id=? ORDER BY last_updated_ts DESC LIMIT 1",(mid,)).fetchone()
    count=cur.execute("SELECT count(*) FROM states WHERE metadata_id=?",(mid,)).fetchone()[0]
    def fmt(r):
        return f"{r[0]}@{datetime.datetime.fromtimestamp(float(r[1]),tz).isoformat()}" if r else "NONE"
    print(f"{entity} count={count} first={fmt(first)} last={fmt(last)}")
con.close()
