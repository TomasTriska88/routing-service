#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, shutil, sys, os

ROOT = Path("/config")
HOME = ROOT / "www/lina-home-card.js"
RES = ROOT / ".storage/lovelace_resources"
CAL_TEST = ROOT / "tests/test_lina_home_calendar_agenda_regression.js"

EXPECTED_SHA = "53e2e63f5c24c022050634aa1090a9fc25761a3ba1891397f0dd7fa87340aa40"
OLD_URL = "/local/lina-home-card.js?v=20260819-agenda-calendar-r1"
NEW_URL = "/local/lina-home-card.js?v=20260820-agenda-unified-r1"
OLD_MARKER = "Markvarec Lina agenda: 20260819-agenda-calendar-r1"
NEW_MARKER = "Markvarec Lina agenda: 20260820-agenda-unified-r1"

stamp = sys.argv[1] if len(sys.argv) > 1 else "manual"
home_bytes = HOME.read_bytes()
sha = hashlib.sha256(home_bytes).hexdigest()
if sha != EXPECTED_SHA:
    raise SystemExit(f"PRECONDITION_HOME_SHA={sha}")

source = home_bytes.decode("utf-8")
test_source = CAL_TEST.read_text(encoding="utf-8")
resources = json.loads(RES.read_text(encoding="utf-8"))

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}_COUNT={count}")
    return text.replace(old, new, 1)

helpers_anchor = '''  async _refreshCalendar(force = false) {'''
helpers = r'''  _localDayDiff(stamp, nowMs = Date.now()) {
    if (!Number.isFinite(stamp)) return 9999;
    const d = new Date(stamp);
    const n = new Date(nowMs);
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
    const today = new Date(n.getFullYear(), n.getMonth(), n.getDate()).getTime();
    return Math.round((day - today) / 86400000);
  }

  _todoAgendaCandidate(item) {
    const priority = this._agendaPriority(item?.summary);
    const due = this._dueMeta(item?.due);
    const dueNow = Number.isFinite(due.diff) && due.diff <= 0;
    let bucket = 8;
    if (priority.key === "critical") bucket = 0;
    else if (priority.key === "high") bucket = dueNow ? 2 : 4;
    else if (priority.key === "low") bucket = dueNow ? 10 : 12;
    else bucket = dueNow ? 6 : 8;
    return {
      kind:"todo",
      bucket,
      stamp:Number.isFinite(due.stamp) ? due.stamp : Number.MAX_SAFE_INTEGER,
      title:this._agendaSummary(item?.summary),
      priority,
      item,
    };
  }

  _calendarAgendaCandidate(event, nowMs = Date.now()) {
    const priority = this._agendaPriority(event?.summary);
    const start = this._eventMeta(event?.start);
    const end = this._eventMeta(event?.end);
    const dayDiff = this._localDayDiff(start.stamp, nowMs);
    const minutes = (start.stamp - nowMs) / 60000;
    const ended = Number.isFinite(end.stamp) && end.stamp <= nowMs;
    if (!start.allDay && ended) return null;

    let bucket;
    if (start.allDay) bucket = dayDiff <= 0 ? 6 : dayDiff === 1 ? 9 : 11;
    else if (minutes <= 120) bucket = 1;
    else if (dayDiff <= 0 && minutes <= 240) bucket = 3;
    else if (dayDiff <= 0 && minutes <= 480) bucket = 5;
    else if (dayDiff <= 0) bucket = 7;
    else if (dayDiff === 1) bucket = 9;
    else bucket = 11;

    // Explicit prefixes are manual overrides. Critical is absolute, High can
    // promote a distant event, and Low can intentionally demote even an imminent one.
    if (priority.key === "critical") bucket = 0;
    else if (priority.key === "high") bucket = Math.min(bucket, 2);
    else if (priority.key === "medium") bucket = Math.min(bucket, 8);
    else if (priority.key === "low") bucket = Math.max(bucket, 10);

    return {
      kind:"calendar",
      bucket,
      stamp:start.stamp,
      title:this._agendaSummary(event?.summary || "Událost"),
      priority,
      imminent:!start.allDay && bucket === 1,
      event,
    };
  }

  _combinedAgenda(nowMs = Date.now()) {
    const candidates = [];
    this._agendaItems.forEach(item => candidates.push(this._todoAgendaCandidate(item)));
    this._calendarEvents.forEach(event => {
      const candidate = this._calendarAgendaCandidate(event, nowMs);
      if (candidate) candidates.push(candidate);
    });
    return candidates.sort((a,b) =>
      a.bucket - b.bucket ||
      a.stamp - b.stamp ||
      (a.kind === b.kind ? 0 : a.kind === "calendar" ? -1 : 1) ||
      String(a.title || "").localeCompare(String(b.title || ""), "cs")
    );
  }

  async _refreshCalendar(force = false) {'''
source = replace_once(source, helpers_anchor, helpers, "HELPERS_ANCHOR")

old_render_head = '''    const calendarEvent = this._calendarEvents[0] || null;
    const agenda = this._agendaItems.slice(0, calendarEvent ? 1 : 2);
'''
new_render_head = '''    const agendaSelection = this._combinedAgenda().slice(0, 2);
'''
source = replace_once(source, old_render_head, new_render_head, "RENDER_HEAD")

old_key = '''      calendarEvent ? [calendarEvent._calendarEntity, calendarEvent.summary, calendarEvent.start, calendarEvent.end] : null,
      agenda.map(x => [x.summary,x.due,x.status]),
'''
new_key = '''      agendaSelection.map(x => x.kind === "calendar"
        ? ["calendar",x.event?._calendarEntity,x.event?.summary,x.event?.start,x.event?.end,x.bucket]
        : ["todo",x.item?.summary,x.item?.due,x.item?.status,x.bucket]),
'''
source = replace_once(source, old_key, new_key, "RENDER_KEY")

old_rows = r'''    const calendarRow = calendarEvent ? (() => {
      const meta = this._eventMeta(calendarEvent?.start);
      const summary = String(calendarEvent?.summary || "Událost");
      const birthday = calendarEvent?._calendarEntity === "calendar.narozeniny" || /narozenin/i.test(summary);
      return `<button class="agenda-row calendar" data-agenda="calendar" data-calendar="${this._esc(calendarEvent?._calendarEntity || "")}"><span>${birthday ? "🎂" : "📅"}</span><time>${this._esc(meta.label)}</time><strong>${this._esc(summary)}</strong></button>`;
    })() : "";
    const todoRows = agenda.map(item => {
      const due = this._dueMeta(item?.due);
      const priority = this._agendaPriority(item?.summary);
      const icon = priority.key === "critical" ? "🚨" :
        due.overdue ? "⚠️" : priority.key === "high" ? "🔴" :
        priority.key === "medium" ? "🟡" : priority.key === "low" ? "⚪" : "☑️";
      const cls = `${due.overdue ? "overdue" : ""} ${priority.key}`.trim();
      return `<button class="agenda-row ${cls}" data-agenda="todo"><span>${icon}</span><time>${this._esc(due.label || "úkol")}</time><strong>${this._esc(this._agendaSummary(item?.summary))}</strong></button>`;
    }).join("");
    const agendaRows = `${calendarRow}${todoRows}`;
    const agendaCount = calendarEvent ? `${this._agendaItems.length} úkolů` : `${this._agendaItems.length} otevřených`;
    const agendaBlock = agendaRows ? `<div class="agenda-title"><span>co nás čeká</span><span>${this._esc(agendaCount)}</span></div><div class="agenda">${agendaRows}</div>` : "";
'''
new_rows = r'''    const agendaRows = agendaSelection.map(candidate => {
      if (candidate.kind === "calendar") {
        const event = candidate.event;
        const meta = this._eventMeta(event?.start);
        const summary = this._agendaSummary(event?.summary || "Událost");
        const birthday = event?._calendarEntity === "calendar.narozeniny" || /narozenin/i.test(summary);
        const icon = candidate.priority.key === "critical" ? "🚨" :
          candidate.imminent ? "⏰" : birthday ? "🎂" : "📅";
        const cls = `calendar ${candidate.imminent ? "imminent" : ""} ${candidate.priority.key}`.trim();
        return `<button class="agenda-row ${cls}" data-agenda="calendar" data-calendar="${this._esc(event?._calendarEntity || "")}"><span>${icon}</span><time>${this._esc(meta.label)}</time><strong>${this._esc(summary)}</strong></button>`;
      }
      const item = candidate.item;
      const due = this._dueMeta(item?.due);
      const priority = candidate.priority;
      const icon = priority.key === "critical" ? "🚨" :
        due.overdue ? "⚠️" : priority.key === "high" ? "🔴" :
        priority.key === "medium" ? "🟡" : priority.key === "low" ? "⚪" : "☑️";
      const cls = `${due.overdue ? "overdue" : ""} ${priority.key}`.trim();
      return `<button class="agenda-row ${cls}" data-agenda="todo"><span>${icon}</span><time>${this._esc(due.label || "úkol")}</time><strong>${this._esc(this._agendaSummary(item?.summary))}</strong></button>`;
    }).join("");
    const agendaCount = this._calendarEvents.length
      ? `${this._agendaItems.length} úkolů · ${this._calendarEvents.length} událostí`
      : `${this._agendaItems.length} otevřených`;
    const agendaBlock = agendaRows ? `<div class="agenda-title"><span>co nás čeká</span><span>${this._esc(agendaCount)}</span></div><div class="agenda">${agendaRows}</div>` : "";
'''
source = replace_once(source, old_rows, new_rows, "RENDER_ROWS")

source = replace_once(source, OLD_MARKER, NEW_MARKER, "MARKER")
css_anchor = '''        .agenda-row.high:not(.overdue) { background:rgba(255,193,7,.075); border-color:rgba(255,193,7,.12); }
'''
css_new = css_anchor + '''        .agenda-row.calendar.imminent { background:rgba(33,150,243,.10); border-color:rgba(33,150,243,.20); }
'''
source = replace_once(source, css_anchor, css_new, "CSS_IMMINENT")

old_test_block = r'''  card._agendaItems = [
    { summary:"[KRITICKÁ] Kritický test", due:tomorrow, status:"needs_action" },
    { summary:"[VYSOKÁ] Druhý úkol nesmí vytlačit kalendář", due:tomorrow, status:"needs_action" },
  ];
  card._calendarEvents = [{
    start:tomorrow,
    end:localDatePlus(2),
    summary:"Nejbližší kalendářní událost",
    _calendarEntity:"calendar.hlavni",
  }];
  card._lastRenderKey = "";
  card._render(true);
  const html = card.shadowRoot.innerHTML;
  assert(html.includes("Nejbližší kalendářní událost"), "calendar row must render");
  assert(html.includes("Kritický test"), "highest-priority todo must remain visible beside calendar");
  assert(!html.includes("Druhý úkol nesmí vytlačit kalendář"), "mixed agenda must stay capped at two rows");
  assert(html.includes('data-agenda="calendar"'), "calendar row marker missing");

  card._calendarEvents = [];
  card._lastRenderKey = "";
  card._render(true);
  const noCalendar = card.shadowRoot.innerHTML;
  assert(noCalendar.includes("Kritický test"), "first todo missing without calendar");
  assert(noCalendar.includes("Druhý úkol nesmí vytlačit kalendář"), "two todos should render when calendar is empty");

  console.log("LINA_HOME_CALENDAR_AGENDA_REGRESSION_OK");
'''
new_test_block = r'''  const now = new Date();
  now.setHours(10, 0, 0, 0);
  const nowMs = now.getTime();
  const isoInMinutes = mins => new Date(nowMs + mins * 60000).toISOString();

  const criticalA = { summary:"[KRITICKÁ] Kritický A", due:tomorrow, status:"needs_action" };
  const criticalB = { summary:"[KRITICKÁ] Kritický B", due:tomorrow, status:"needs_action" };
  const highToday = { summary:"[VYSOKÁ] Vysoký dnes", due:localDatePlus(0), status:"needs_action" };
  const mediumToday = { summary:"Střední dnes", due:localDatePlus(0), status:"needs_action" };
  const event90 = { start:isoInMinutes(90), end:isoInMinutes(150), summary:"Schůzka za 90 minut", _calendarEntity:"calendar.hlavni" };
  const eventTomorrow = { start:tomorrow, end:localDatePlus(2), summary:"Událost zítra", _calendarEntity:"calendar.rodina" };

  card._agendaItems = [criticalA, criticalB, highToday];
  card._calendarEvents = [event90];
  let ranked = card._combinedAgenda(nowMs).slice(0,2);
  assert.deepStrictEqual(ranked.map(x => x.title), ["Kritický A","Kritický B"], "two critical todos must be allowed to occupy both visible rows");

  card._agendaItems = [highToday];
  card._calendarEvents = [event90];
  ranked = card._combinedAgenda(nowMs).slice(0,2);
  assert.deepStrictEqual(ranked.map(x => x.title), ["Schůzka za 90 minut","Vysoký dnes"], "event within two hours must outrank a high todo due today");

  card._agendaItems = [highToday];
  card._calendarEvents = [eventTomorrow];
  ranked = card._combinedAgenda(nowMs).slice(0,2);
  assert.deepStrictEqual(ranked.map(x => x.title), ["Vysoký dnes","Událost zítra"], "tomorrow calendar event must not displace an important todo due today");

  card._agendaItems = [mediumToday];
  card._calendarEvents = [
    { start:isoInMinutes(30), end:isoInMinutes(60), summary:"První blízká", _calendarEntity:"calendar.hlavni" },
    { start:isoInMinutes(75), end:isoInMinutes(105), summary:"Druhá blízká", _calendarEntity:"calendar.rodina" },
  ];
  ranked = card._combinedAgenda(nowMs).slice(0,2);
  assert.deepStrictEqual(ranked.map(x => x.title), ["První blízká","Druhá blízká"], "two imminent fixed commitments may occupy both rows");

  card._agendaItems = [highToday, mediumToday];
  card._calendarEvents = [{ start:localDatePlus(0), end:tomorrow, summary:"Celodenní dnes", _calendarEntity:"calendar.hlavni" }];
  ranked = card._combinedAgenda(nowMs).slice(0,3);
  assert.deepStrictEqual(ranked.map(x => x.title), ["Vysoký dnes","Celodenní dnes","Střední dnes"], "all-day today should behave like a due-today item, below high todo");

  card._agendaItems = [mediumToday];
  card._calendarEvents = [{ start:isoInMinutes(20), end:isoInMinutes(50), summary:"[NÍZKÁ] Nízká schůzka", _calendarEntity:"calendar.hlavni" }];
  ranked = card._combinedAgenda(nowMs).slice(0,2);
  assert.deepStrictEqual(ranked.map(x => x.title), ["Střední dnes","Nízká schůzka"], "explicit low calendar prefix must be able to demote an event");
  assert.strictEqual(ranked[1].title, "Nízká schůzka", "calendar priority prefix must be stripped visually");

  card._agendaItems = [criticalA, highToday];
  card._calendarEvents = [event90];
  card._lastRenderKey = "";
  card._render(true);
  const html = card.shadowRoot.innerHTML;
  assert(html.includes("Kritický A"), "critical todo must render");
  assert(html.includes("Schůzka za 90 minut"), "imminent calendar row must render");
  assert(!html.includes("Vysoký dnes"), "mixed agenda must stay capped at two highest-ranked rows");
  assert(html.includes('data-agenda="calendar"'), "calendar row marker missing");

  card._calendarEvents = [];
  card._lastRenderKey = "";
  card._render(true);
  const noCalendar = card.shadowRoot.innerHTML;
  assert(noCalendar.includes("Kritický A"), "first todo missing without calendar");
  assert(noCalendar.includes("Vysoký dnes"), "two todos should render when calendar is empty");

  assert(source.includes("20260820-agenda-unified-r1"), "unified agenda marker missing");
  assert(source.includes("_combinedAgenda(nowMs = Date.now())"), "shared Calendar × Todo queue missing");
  console.log("LINA_HOME_CALENDAR_AGENDA_REGRESSION_OK");
'''
test_source = replace_once(test_source, old_test_block, new_test_block, "CAL_TEST_BLOCK")

def rewrite_resource(x):
    changed = 0
    if isinstance(x, dict):
        for k,v in list(x.items()):
            if k == "url" and v == OLD_URL:
                x[k] = NEW_URL
                changed += 1
            else:
                changed += rewrite_resource(v)
    elif isinstance(x, list):
        for v in x:
            changed += rewrite_resource(v)
    return changed

resource_count = rewrite_resource(resources)
if resource_count != 1:
    raise RuntimeError(f"RESOURCE_URL_COUNT={resource_count}")

home_backup = HOME.with_name(HOME.name + f".bak-unified-priority-{stamp}")
res_backup = RES.with_name(RES.name + f".bak-unified-priority-{stamp}")
test_backup = CAL_TEST.with_name(CAL_TEST.name + f".bak-unified-priority-{stamp}")
shutil.copy2(HOME, home_backup)
shutil.copy2(RES, res_backup)
shutil.copy2(CAL_TEST, test_backup)

try:
    home_tmp = HOME.with_name(HOME.name + ".tmp-unified-priority")
    res_tmp = RES.with_name(RES.name + ".tmp-unified-priority")
    test_tmp = CAL_TEST.with_name(CAL_TEST.name + ".tmp-unified-priority")
    home_tmp.write_text(source, encoding="utf-8")
    res_tmp.write_text(json.dumps(resources, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    test_tmp.write_text(test_source, encoding="utf-8")
    os.replace(home_tmp, HOME)
    os.replace(res_tmp, RES)
    os.replace(test_tmp, CAL_TEST)
except Exception:
    shutil.copy2(home_backup, HOME)
    shutil.copy2(res_backup, RES)
    shutil.copy2(test_backup, CAL_TEST)
    raise

new_bytes = HOME.read_bytes()
print(f"HOME_BACKUP={home_backup}")
print(f"RESOURCE_BACKUP={res_backup}")
print(f"TEST_BACKUP={test_backup}")
print(f"HOME_SHA256={hashlib.sha256(new_bytes).hexdigest()}")
print(f"HOME_BYTES={len(new_bytes)}")
print(f"NEW_RESOURCE_URL={NEW_URL}")
print("LINA_UNIFIED_PRIORITY_PATCH_WRITTEN")
