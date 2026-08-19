#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import os
import shutil
import time

HOME = Path("/config/www/lina-home-card.js")
RES = Path("/config/.storage/lovelace_resources")
TEST = Path("/config/tests/test_lina_home_calendar_agenda_regression.js")
OLD_SHA = "07e521982fa4f38087e71a7e93590b714e640fe7c7cbec22f3aae04aa7d8a179"
OLD_URL = "/local/lina-home-card.js?v=20260819-agenda-r2"
NEW_URL = "/local/lina-home-card.js?v=20260819-agenda-calendar-r1"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)

if sha(HOME) != OLD_SHA:
    raise RuntimeError(f"unexpected lina-home-card.js SHA: {sha(HOME)}")
raw_res = RES.read_text(encoding="utf-8")
json.loads(raw_res)
if raw_res.count(OLD_URL) != 1:
    raise RuntimeError(f"expected exactly one old resource URL, found {raw_res.count(OLD_URL)}")
if NEW_URL in raw_res:
    raise RuntimeError("new resource URL already present")
if TEST.exists():
    raise RuntimeError(f"calendar regression test already exists: {TEST}")

stamp = time.strftime("%Y%m%d-%H%M%S")
home_bak = HOME.with_name(HOME.name + f".bak-calendar-agenda-{stamp}")
res_bak = RES.with_name(RES.name + f".bak-calendar-agenda-{stamp}")
shutil.copy2(HOME, home_bak)
shutil.copy2(RES, res_bak)

src = HOME.read_text(encoding="utf-8")

src = replace_once(
    src,
    '''    this._agendaTimer = null;
  }''',
    '''    this._agendaTimer = null;
    this._calendarEvents = [];
    this._calendarLoading = false;
    this._calendarRefreshAt = 0;
    this._calendarVersion = "";
    this._calendarRefreshPending = false;
  }''',
    "constructor calendar state",
)

src = replace_once(
    src,
    '''      todo_entity: "todo.markvarec",
      ...config,''',
    '''      todo_entity: "todo.markvarec",
      calendar_entities: ["calendar.hlavni", "calendar.rodina", "calendar.narozeniny"],
      ...config,''',
    "calendar config",
)

src = replace_once(
    src,
    '''      this._agendaTimer = window.setInterval(() => this._refreshAgenda(true), 30000);''',
    '''      this._agendaTimer = window.setInterval(() => {
        this._refreshAgenda(true);
        this._refreshCalendar(false);
      }, 30000);''',
    "agenda timer",
)

src = replace_once(
    src,
    '''    if (version) this._agendaTodoVersion = version;
    this._render();
    this._refreshAgenda(changed);''',
    '''    if (version) this._agendaTodoVersion = version;

    const calendarVersion = this._calendarIds().map(id => {
      const s = this._st(id);
      return s ? `${id}:${s.state}|${s.last_updated || s.last_changed || ""}` : `${id}:missing`;
    }).join(";");
    const calendarChanged = Boolean(calendarVersion && calendarVersion !== this._calendarVersion);
    if (calendarVersion) this._calendarVersion = calendarVersion;

    this._render();
    this._refreshAgenda(changed);
    this._refreshCalendar(calendarChanged);''',
    "hass calendar refresh",
)

calendar_helpers = r'''
  _calendarIds() {
    return Array.isArray(this._config.calendar_entities)
      ? this._config.calendar_entities.filter(Boolean)
      : [];
  }

  _eventMeta(raw) {
    const value = String(raw || "");
    const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    let date;
    let allDay = false;
    if (dateOnly) {
      date = new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]));
      allDay = true;
    } else {
      date = new Date(value);
    }
    if (!Number.isFinite(date?.getTime?.())) {
      return { label:"událost", stamp:Number.MAX_SAFE_INTEGER, allDay:true };
    }

    const today = new Date();
    today.setHours(0,0,0,0);
    const day = new Date(date);
    day.setHours(0,0,0,0);
    const diff = Math.round((day.getTime() - today.getTime()) / 86400000);
    const base = diff < 0 ? "probíhá" : diff === 0 ? "dnes" : diff === 1 ? "zítra" : `${day.getDate()}. ${day.getMonth() + 1}.`;
    const hasTime = !allDay && /T\d{2}:\d{2}/.test(value);
    const time = hasTime ? date.toLocaleTimeString("cs-CZ", { hour:"2-digit", minute:"2-digit" }) : "";
    return { label:time ? `${base} ${time}` : base, stamp:date.getTime(), allDay };
  }

  _calendarSort(events) {
    return [...events].sort((a,b) => {
      const at = this._eventMeta(a?.start).stamp;
      const bt = this._eventMeta(b?.start).stamp;
      return at - bt || String(a?.summary || "").localeCompare(String(b?.summary || ""), "cs");
    });
  }

  async _refreshCalendar(force = false) {
    const ids = this._calendarIds();
    if (!this._hass || !ids.length) return;
    if (this._calendarLoading) {
      if (force) this._calendarRefreshPending = true;
      return;
    }
    const now = Date.now();
    if (!force && now < this._calendarRefreshAt) return;
    this._calendarLoading = true;
    this._calendarRefreshAt = now + 300000;
    try {
      const result = await this._hass.callWS({
        type:"call_service",
        domain:"calendar",
        service:"get_events",
        target:{ entity_id:ids },
        service_data:{ duration:{ days:14 } },
        return_response:true,
      });
      const response = result?.response || {};
      const events = [];
      ids.forEach(entityId => {
        const rows = response?.[entityId]?.events;
        if (!Array.isArray(rows)) return;
        rows.forEach(event => {
          if (!event?.start) return;
          events.push({ ...event, _calendarEntity:entityId });
        });
      });
      this._calendarEvents = this._calendarSort(events).slice(0, 16);
    } catch (_err) {
      // Keep the last good calendar data. A transient Google/HA error must not blank the card.
    } finally {
      this._calendarLoading = false;
      const refreshAgain = this._calendarRefreshPending;
      this._calendarRefreshPending = false;
      this._lastRenderKey = "";
      this._render(true);
      if (refreshAgain) window.setTimeout(() => this._refreshCalendar(true), 0);
    }
  }
'''
src = replace_once(
    src,
    '\n  async _refreshAgenda(force = false) {',
    calendar_helpers + '\n  async _refreshAgenda(force = false) {',
    "calendar helpers",
)

src = replace_once(
    src,
    '''    const agenda = this._agendaItems.slice(0, 2);''',
    '''    const calendarEvent = this._calendarEvents[0] || null;
    const agenda = this._agendaItems.slice(0, calendarEvent ? 1 : 2);''',
    "render agenda selection",
)

src = replace_once(
    src,
    '''    const key = JSON.stringify([name, icon, thought, history, agenda.map(x => [x.summary,x.due,x.status]), health.map(x => [x.value,x.bad])]);''',
    '''    const key = JSON.stringify([
      name, icon, thought, history,
      calendarEvent ? [calendarEvent._calendarEntity, calendarEvent.summary, calendarEvent.start, calendarEvent.end] : null,
      agenda.map(x => [x.summary,x.due,x.status]),
      health.map(x => [x.value,x.bad])
    ]);''',
    "render key",
)

old_agenda_render = r'''    const agendaRows = agenda.map(item => {
      const due = this._dueMeta(item?.due);
      const priority = this._agendaPriority(item?.summary);
      const icon = priority.key === "critical" ? "🚨" :
        due.overdue ? "⚠️" : priority.key === "high" ? "🔴" :
        priority.key === "medium" ? "🟡" : priority.key === "low" ? "⚪" : "☑️";
      const cls = `${due.overdue ? "overdue" : ""} ${priority.key}`.trim();
      return `<button class="agenda-row ${cls}" data-agenda="todo"><span>${icon}</span><time>${this._esc(due.label || "úkol")}</time><strong>${this._esc(this._agendaSummary(item?.summary))}</strong></button>`;
    }).join("");
    const agendaBlock = agendaRows ? `<div class="agenda-title"><span>co nás čeká</span><span>${this._esc(String(this._agendaItems.length))} otevřených</span></div><div class="agenda">${agendaRows}</div>` : "";'''

new_agenda_render = r'''    const calendarRow = calendarEvent ? (() => {
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
    const agendaBlock = agendaRows ? `<div class="agenda-title"><span>co nás čeká</span><span>${this._esc(agendaCount)}</span></div><div class="agenda">${agendaRows}</div>` : "";'''
src = replace_once(src, old_agenda_render, new_agenda_render, "mixed agenda renderer")

src = replace_once(
    src,
    '''        /* Markvarec Lina agenda: 20260819-agenda-r2 */''',
    '''        /* Markvarec Lina agenda: 20260819-agenda-calendar-r1 */''',
    "agenda marker",
)

src = replace_once(
    src,
    '''    this.shadowRoot.querySelectorAll("[data-agenda=todo]").forEach(el => {
      el.addEventListener("click", () => this._moreInfo(c.todo_entity));
    });''',
    '''    this.shadowRoot.querySelectorAll("[data-agenda=todo]").forEach(el => {
      el.addEventListener("click", () => this._moreInfo(c.todo_entity));
    });
    this.shadowRoot.querySelectorAll("[data-agenda=calendar]").forEach(el => {
      const entityId = el.getAttribute("data-calendar");
      el.addEventListener("click", () => this._moreInfo(entityId));
    });''',
    "calendar click",
)

if "calendar.ceske_statni_svatky" in src:
    raise RuntimeError("public-holiday calendar must not be part of compact Lina agenda")
for required in (
    'calendar_entities: ["calendar.hlavni", "calendar.rodina", "calendar.narozeniny"]',
    'service:"get_events"',
    'service_data:{ duration:{ days:14 } }',
    'this._calendarRefreshAt = now + 300000',
    'data-agenda="calendar"',
    '20260819-agenda-calendar-r1',
):
    if required not in src:
        raise RuntimeError(f"required calendar agenda marker missing: {required}")

test = r'''const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const sourcePath = "/config/www/lina-home-card.js";
const source = fs.readFileSync(sourcePath, "utf8");

class HTMLElementStub {
  constructor() {
    this.dataset = {};
    this.shadowRoot = null;
  }
  attachShadow() {
    this.shadowRoot = {
      innerHTML: "",
      querySelectorAll() { return []; },
    };
    return this.shadowRoot;
  }
  dispatchEvent() {}
}

const sandbox = {
  console,
  HTMLElement: HTMLElementStub,
  CustomEvent: class CustomEvent {},
  URLSearchParams,
  Date,
  JSON,
  Array,
  String,
  Number,
  Math,
  RegExp,
  Object,
  Promise,
  window: {
    location: { search: "" },
    customCards: [],
    setInterval() { return 1; },
    clearInterval() {},
    setTimeout(fn) { fn(); return 1; },
  },
  customElements: {
    get() { return undefined; },
    define() {},
  },
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(source + "\n;globalThis.__LinaHomeCard=LinaHomeCard;", sandbox);

const Card = sandbox.__LinaHomeCard;
assert(Card, "LinaHomeCard class not exported to test sandbox");

const card = new Card();
card.setConfig({});
assert.deepStrictEqual(
  Array.from(card._config.calendar_entities),
  ["calendar.hlavni", "calendar.rodina", "calendar.narozeniny"],
  "compact agenda must use Main + Family + Birthdays"
);
assert(!source.includes("calendar.ceske_statni_svatky"), "public holidays must not crowd compact Lina agenda");
assert(source.includes('service:"get_events"'), "calendar.get_events call missing");
assert(source.includes('service_data:{ duration:{ days:14 } }'), "14-day calendar horizon missing");
assert(source.includes("this._calendarRefreshAt = now + 300000"), "5-minute calendar cache missing");

function localDatePlus(days) {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
}

const tomorrow = localDatePlus(1);
const later = localDatePlus(4);
assert.strictEqual(card._eventMeta(tomorrow).label, "zítra", "date-only calendar label should be local-day aware");

let calendarCall = null;
card._hass = {
  states: {
    "binary_sensor.markvarec_local_internet": { state:"on" },
    "automation.chatgpt_home_assistant_bridge": { state:"on" },
    "media_player.loznice_google_nest_mini": { state:"idle" },
  },
  async callWS(payload) {
    calendarCall = payload;
    return {
      response: {
        "calendar.hlavni": { events: [{ start:later, end:localDatePlus(5), summary:"Pozdější událost" }] },
        "calendar.rodina": { events: [{ start:tomorrow, end:localDatePlus(2), summary:"Rodinná událost" }] },
        "calendar.narozeniny": { events: [{ start:localDatePlus(2), end:localDatePlus(3), summary:"Test – narozeniny" }] },
      },
    };
  },
};

(async () => {
  await card._refreshCalendar(true);
  assert(calendarCall, "calendar refresh did not call HA");
  assert.strictEqual(calendarCall.domain, "calendar");
  assert.strictEqual(calendarCall.service, "get_events");
  assert.deepStrictEqual(Array.from(calendarCall.target.entity_id), ["calendar.hlavni","calendar.rodina","calendar.narozeniny"]);
  assert.strictEqual(calendarCall.service_data.duration.days, 14);
  assert.strictEqual(card._calendarEvents.length, 3);
  assert.strictEqual(card._calendarEvents[0].summary, "Rodinná událost", "calendar events must sort by nearest start");
  assert.strictEqual(card._calendarEvents[0]._calendarEntity, "calendar.rodina");

  card._agendaItems = [
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
})().catch(err => {
  console.error(err);
  process.exit(1);
});
'''

try:
    home_tmp = HOME.with_name(HOME.name + ".tmp-calendar-agenda")
    home_tmp.write_text(src, encoding="utf-8")
    os.replace(home_tmp, HOME)

    new_res = raw_res.replace(OLD_URL, NEW_URL, 1)
    json.loads(new_res)
    res_tmp = RES.with_name(RES.name + ".tmp-calendar-agenda")
    res_tmp.write_text(new_res, encoding="utf-8")
    json.loads(res_tmp.read_text(encoding="utf-8"))
    os.replace(res_tmp, RES)

    TEST.parent.mkdir(parents=True, exist_ok=True)
    TEST.write_text(test, encoding="utf-8")
except Exception:
    shutil.copy2(home_bak, HOME)
    shutil.copy2(res_bak, RES)
    TEST.unlink(missing_ok=True)
    raise

print(f"HOME_BACKUP={home_bak}")
print(f"RESOURCE_BACKUP={res_bak}")
print(f"HOME_SHA256={sha(HOME)}")
print(f"HOME_BYTES={len(HOME.read_bytes())}")
print(f"RESOURCE_SHA256={sha(RES)}")
print(f"CALENDAR_TEST={TEST}")
print(f"NEW_RESOURCE_URL={NEW_URL}")
print("LINA_HOME_CALENDAR_AGENDA_PATCH_WRITTEN")
