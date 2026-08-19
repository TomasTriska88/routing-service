#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys

JS = Path('/config/www/lina-home-card.js')
RES = Path('/config/.storage/lovelace_resources')
EXPECTED_JS = 'f9ebdff64afbf2c6ab360c2e96b3cf14ba228de71e9b96b6d0b4ddd7d91e91bf'
OLD_URL = '/local/lina-home-card.js?v=20260819-spaceaware-r1'
NEW_URL = '/local/lina-home-card.js?v=20260819-agenda-r1'
MARKER = 'Markvarec Lina agenda: 20260819-agenda-r1'
SUFFIX = '.bak-20260819-1552-agenda-r1'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(path: Path) -> Path:
    b = path.with_name(path.name + SUFFIX)
    shutil.copy2(path, b)
    return b


def restore() -> None:
    for p in (JS, RES):
        b = p.with_name(p.name + SUFFIX)
        if b.exists():
            shutil.copy2(b, p)
    print('HNIZDO_LINA_AGENDA_ROLLBACK_OK')


if '--rollback' in sys.argv:
    restore()
    raise SystemExit(0)

if sha(JS) != EXPECTED_JS:
    raise SystemExit(f'LIVE_SHA_MISMATCH {sha(JS)} != {EXPECTED_JS}')

s = JS.read_text(encoding='utf-8')
if MARKER in s:
    raise SystemExit('AGENDA_MARKER_ALREADY_PRESENT')


def one(old: str, new: str, label: str) -> None:
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'ANCHOR_{label}_{n}')
    s = s.replace(old, new, 1)


one(
'''    this._lastRenderKey = "";\n  }''',
'''    this._lastRenderKey = "";\n    this._agendaItems = [];\n    this._agendaLoading = false;\n    this._agendaRefreshAt = 0;\n    this._agendaTodoVersion = "";\n  }''',
'constructor',
)

one(
'''      voice_entity: "media_player.loznice_google_nest_mini",\n      ...config,''',
'''      voice_entity: "media_player.loznice_google_nest_mini",\n      todo_entity: "todo.markvarec",\n      ...config,''',
'config',
)

one(
'''  set hass(hass) {\n    this._hass = hass;\n    this._render();\n  }''',
'''  set hass(hass) {\n    this._hass = hass;\n    const todo = this._st(this._config.todo_entity);\n    const version = todo ? `${todo.state}|${todo.last_updated || todo.last_changed || ""}` : "";\n    const changed = Boolean(version && version !== this._agendaTodoVersion);\n    if (version) this._agendaTodoVersion = version;\n    this._render();\n    this._refreshAgenda(changed);\n  }''',
'hass',
)

one(
'''  _time(raw) {\n    if (!raw) return "";\n    const bits = String(raw).split(" ");\n    return bits.length > 1 ? bits[1].slice(0,5) : String(raw).slice(0,5);\n  }\n\n  _render(force = false) {''',
'''  _time(raw) {\n    if (!raw) return "";\n    const bits = String(raw).split(" ");\n    return bits.length > 1 ? bits[1].slice(0,5) : String(raw).slice(0,5);\n  }\n\n  _agendaHigh(summary) {\n    return /^\\s*\\[VYSOKÁ\\]/i.test(String(summary || ""));\n  }\n\n  _agendaSummary(summary) {\n    return String(summary || "Úkol").replace(/^\\s*\\[VYSOKÁ\\]\\s*/i, "").trim();\n  }\n\n  _dueMeta(raw) {\n    const m = /^(\\d{4})-(\\d{2})-(\\d{2})/.exec(String(raw || ""));\n    if (!m) return { label:"", overdue:false, diff:99999, stamp:Number.MAX_SAFE_INTEGER };\n    const due = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));\n    due.setHours(0,0,0,0);\n    const today = new Date();\n    today.setHours(0,0,0,0);\n    const diff = Math.round((due.getTime() - today.getTime()) / 86400000);\n    const label = diff < 0 ? "po termínu" : diff === 0 ? "dnes" : diff === 1 ? "zítra" : `${Number(m[3])}. ${Number(m[2])}.`;\n    return { label, overdue:diff < 0, diff, stamp:due.getTime() };\n  }\n\n  _agendaSort(items) {\n    return [...items].sort((a,b) => {\n      const ah = this._agendaHigh(a?.summary);\n      const bh = this._agendaHigh(b?.summary);\n      const ad = this._dueMeta(a?.due);\n      const bd = this._dueMeta(b?.due);\n      const ab = ad.overdue ? (ah ? 0 : 1) : (ah ? 2 : 3);\n      const bb = bd.overdue ? (bh ? 0 : 1) : (bh ? 2 : 3);\n      return ab - bb || ad.stamp - bd.stamp || this._agendaSummary(a?.summary).localeCompare(this._agendaSummary(b?.summary), "cs");\n    });\n  }\n\n  async _refreshAgenda(force = false) {\n    if (!this._hass || !this._config.todo_entity || this._agendaLoading) return;\n    const now = Date.now();\n    if (!force && now < this._agendaRefreshAt) return;\n    this._agendaLoading = true;\n    this._agendaRefreshAt = now + 120000;\n    try {\n      const result = await this._hass.callWS({\n        type:"call_service",\n        domain:"todo",\n        service:"get_items",\n        target:{ entity_id:this._config.todo_entity },\n        service_data:{},\n        return_response:true,\n      });\n      const items = result?.response?.[this._config.todo_entity]?.items;\n      if (Array.isArray(items)) {\n        this._agendaItems = this._agendaSort(items.filter(x => String(x?.status || "needs_action") !== "completed"));\n      }\n    } catch (_err) {\n      // Keep the last good agenda. A transient service error must not blank the card.\n    } finally {\n      this._agendaLoading = false;\n      this._lastRenderKey = "";\n      this._render(true);\n    }\n  }\n\n  _render(force = false) {''',
'agenda_methods',
)

one(
'''    const history = Array.isArray(a.activity_history) ? a.activity_history.slice(-3).reverse() : [];''',
'''    const history = Array.isArray(a.activity_history) ? a.activity_history.slice(-3).reverse() : [];\n    const agenda = this._agendaItems.slice(0, 2);''',
'agenda_data',
)

one(
'''    const key = JSON.stringify([name, icon, thought, history, health.map(x => [x.value,x.bad])]);''',
'''    const key = JSON.stringify([name, icon, thought, history, agenda.map(x => [x.summary,x.due,x.status]), health.map(x => [x.value,x.bad])]);''',
'render_key',
)

one(
'''    const activity = history.length ? history.map(item => {\n      const trigger = String(item?.trigger || "");\n      const mark = item?.status === "error" ? "⚠️" : trigger === "requested" ? "🟣" : "🟢";\n      const desc = item?.description || item?.tool || "aktivita";\n      return `<div class="activity"><span>${mark}</span><time>${this._esc(this._time(item?.timestamp))}</time><strong>${this._esc(desc)}</strong></div>`;\n    }).join("") : `<div class="activity empty"><span>🌙</span><strong>Zatím žádná nová aktivita.</strong></div>`;''',
'''    const activity = history.length ? history.map(item => {\n      const trigger = String(item?.trigger || "");\n      const mark = item?.status === "error" ? "⚠️" : trigger === "requested" ? "🟣" : "🟢";\n      const desc = item?.description || item?.tool || "aktivita";\n      return `<div class="activity"><span>${mark}</span><time>${this._esc(this._time(item?.timestamp))}</time><strong>${this._esc(desc)}</strong></div>`;\n    }).join("") : `<div class="activity empty"><span>🌙</span><strong>Zatím žádná nová aktivita.</strong></div>`;\n\n    const agendaRows = agenda.map(item => {\n      const due = this._dueMeta(item?.due);\n      const high = this._agendaHigh(item?.summary);\n      const icon = due.overdue ? "⚠️" : high ? "🔴" : "☑️";\n      const cls = `${due.overdue ? "overdue" : ""} ${high ? "high" : ""}`.trim();\n      return `<button class="agenda-row ${cls}" data-agenda="todo"><span>${icon}</span><time>${this._esc(due.label || "úkol")}</time><strong>${this._esc(this._agendaSummary(item?.summary))}</strong></button>`;\n    }).join("");\n    const agendaBlock = agendaRows ? `<div class="agenda-title"><span>co nás čeká</span><span>${this._esc(String(this._agendaItems.length))} otevřených</span></div><div class="agenda">${agendaRows}</div>` : "";''',
'agenda_rows',
)

one(
'''        .activity-title { margin-top:2px; font-size:11px; text-transform:uppercase; letter-spacing:.08em; opacity:.68; }''',
'''        /* Markvarec Lina agenda: 20260819-agenda-r1 */\n        .agenda-title { display:flex; justify-content:space-between; gap:8px; margin-top:1px; font-size:11px; text-transform:uppercase; letter-spacing:.08em; opacity:.72; }\n        .agenda { display:grid; gap:4px; }\n        .agenda-row {\n          appearance:none; color:inherit; width:100%; min-width:0; border:1px solid transparent;\n          display:grid; grid-template-columns:auto auto minmax(0,1fr); gap:6px; align-items:center;\n          padding:5px 7px; border-radius:9px; background:rgba(127,127,127,.05); text-align:left; cursor:pointer;\n        }\n        .agenda-row.overdue { background:rgba(244,67,54,.075); border-color:rgba(244,67,54,.13); }\n        .agenda-row.high:not(.overdue) { background:rgba(255,193,7,.075); border-color:rgba(255,193,7,.12); }\n        .agenda-row span { font-size:13px; line-height:1; }\n        .agenda-row time { font-size:11px; opacity:.76; white-space:nowrap; }\n        .agenda-row strong { min-width:0; font-size:12px; line-height:1.2; font-weight:650; overflow-wrap:anywhere; }\n        :host([data-tv-kiosk="1"]) .agenda-title { font-size:12px; opacity:.82; }\n        :host([data-tv-kiosk="1"]) .agenda-row time { font-size:12px; opacity:.84; }\n        :host([data-tv-kiosk="1"]) .agenda-row strong { font-size:14px; }\n        .activity-title { margin-top:2px; font-size:11px; text-transform:uppercase; letter-spacing:.08em; opacity:.68; }''',
'agenda_css',
)

one(
'''          <div class="health">${chips}</div>\n          <div class="activity-title">poslední činnost</div>''',
'''          <div class="health">${chips}</div>\n          ${agendaBlock}\n          <div class="activity-title">poslední činnost</div>''',
'agenda_html',
)

one(
'''    this.shadowRoot.querySelectorAll("[data-health]").forEach(el => {\n      el.addEventListener("click", () => {\n        const item = health[Number(el.getAttribute("data-health"))];\n        this._moreInfo(item?.entity);\n      });\n    });\n  }''',
'''    this.shadowRoot.querySelectorAll("[data-health]").forEach(el => {\n      el.addEventListener("click", () => {\n        const item = health[Number(el.getAttribute("data-health"))];\n        this._moreInfo(item?.entity);\n      });\n    });\n    this.shadowRoot.querySelectorAll("[data-agenda=todo]").forEach(el => {\n      el.addEventListener("click", () => this._moreInfo(c.todo_entity));\n    });\n  }''',
'agenda_listener',
)

# Validate the resource registry before touching either live file.
d = json.loads(RES.read_text(encoding='utf-8'))
items = (d.get('data') or {}).get('items') or []
old = [x for x in items if x.get('url') == OLD_URL]
new = [x for x in items if x.get('url') == NEW_URL]
if len(old) != 1 or new:
    raise SystemExit(f'RESOURCE_MATCH old={len(old)} new={len(new)}')

backup(JS)
backup(RES)
try:
    JS.write_text(s, encoding='utf-8')
    old[0]['url'] = NEW_URL
    RES.write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
except Exception:
    restore()
    raise

print('JS_BYTES', len(JS.read_bytes()))
print('JS_SHA256', sha(JS))
print('RES_SHA256', sha(RES))
print('HNIZDO_LINA_AGENDA_PATCHED')
