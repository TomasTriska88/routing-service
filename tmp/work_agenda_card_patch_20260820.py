from pathlib import Path
import hashlib
import shutil

CARD = Path("/config/www/lina-home-card.js")
BACKUP = Path("/config/www/lina-home-card.js.bak-work-agenda-20260820")
BASELINE = "a5f901c7722fa96e66ebf7cd937a1047b5122f9b11218157c6908a4c79043193"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

text = CARD.read_text(encoding="utf-8")
current = sha(CARD)
if current != BASELINE:
    raise SystemExit(f"unexpected lina-home-card baseline: {current}")
if not BACKUP.exists():
    shutil.copy2(CARD, BACKUP)

def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, got {count}")
    text = text.replace(old, new, 1)

replace_once(
'''      todo_entity: "todo.markvarec",
      calendar_entities: ["calendar.hlavni", "calendar.rodina", "calendar.narozeniny"],
''',
'''      todo_entity: "todo.markvarec",
      work_agenda_entity: "sensor.lineum_work_agenda",
      calendar_entities: ["calendar.hlavni", "calendar.rodina", "calendar.narozeniny"],
''',
"config",
)

old_combined = '''  _combinedAgenda(nowMs = Date.now()) {
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
'''
new_combined = '''  _workPriority(raw) {
    const workKey = String(raw || "none").toLowerCase();
    if (workKey === "urgent") return { rank:1, key:"high", workKey:"urgent" };
    if (workKey === "high") return { rank:1, key:"high", workKey:"high" };
    if (workKey === "normal") return { rank:2, key:"medium", workKey:"normal" };
    if (workKey === "low") return { rank:3, key:"low", workKey:"low" };
    return { rank:2, key:"normal", workKey:"none" };
  }

  _workAgendaItems() {
    const work = this._st(this._config.work_agenda_entity);
    const attrs = work?.attributes || {};
    if (String(attrs.source_status || "unknown") === "error") return [];
    const items = Array.isArray(attrs.items) ? attrs.items : [];
    return items.filter(item => item && item.source === "clickup");
  }

  _workAgendaCandidate(item) {
    const priority = this._workPriority(item?.priority);
    const due = this._dueMeta(item?.due);
    const dueNow = Number.isFinite(due.diff) && due.diff <= 0;
    const dueTomorrow = due.diff === 1;
    let bucket = 10;

    if (priority.workKey === "urgent") bucket = dueNow ? 1 : dueTomorrow ? 2 : 4;
    else if (priority.workKey === "high") bucket = dueNow ? 2 : dueTomorrow ? 3 : 5;
    else if (priority.workKey === "normal") bucket = dueNow ? 5 : dueTomorrow ? 6 : 8;
    else if (priority.workKey === "low") bucket = dueNow ? 9 : dueTomorrow ? 10 : 11;
    else bucket = dueNow ? 7 : dueTomorrow ? 8 : 10;

    return {
      kind:"work",
      bucket,
      stamp:Number.isFinite(due.stamp) ? due.stamp : Number.MAX_SAFE_INTEGER,
      title:String(item?.title || "Pracovní úkol"),
      priority,
      workPriority:priority.workKey,
      item,
    };
  }

  _combinedAgenda(nowMs = Date.now()) {
    const candidates = [];
    this._agendaItems.forEach(item => candidates.push(this._todoAgendaCandidate(item)));
    this._calendarEvents.forEach(event => {
      const candidate = this._calendarAgendaCandidate(event, nowMs);
      if (candidate) candidates.push(candidate);
    });
    this._workAgendaItems().forEach(item => candidates.push(this._workAgendaCandidate(item)));
    const kindRank = { calendar:0, work:1, todo:2 };
    return candidates.sort((a,b) =>
      a.bucket - b.bucket ||
      a.stamp - b.stamp ||
      (kindRank[a.kind] ?? 9) - (kindRank[b.kind] ?? 9) ||
      String(a.title || "").localeCompare(String(b.title || ""), "cs")
    );
  }
'''
replace_once(old_combined, new_combined, "combined agenda")

replace_once(
'''      agendaSelection.map(x => x.kind === "calendar"
        ? ["calendar",x.event?._calendarEntity,x.event?.summary,x.event?.start,x.event?.end,x.bucket]
        : ["todo",x.item?.summary,x.item?.due,x.item?.status,x.bucket]),
''',
'''      agendaSelection.map(x => x.kind === "calendar"
        ? ["calendar",x.event?._calendarEntity,x.event?.summary,x.event?.start,x.event?.end,x.bucket]
        : x.kind === "work"
          ? ["work",x.item?.id,x.item?.title,x.item?.due,x.item?.status,x.item?.priority,x.bucket]
          : ["todo",x.item?.summary,x.item?.due,x.item?.status,x.bucket]),
''',
"render key",
)

replace_once(
'''        return `<button class="agenda-row ${cls}" data-agenda="calendar" data-calendar="${this._esc(event?._calendarEntity || "")}"><span>${icon}</span><time>${this._esc(meta.label)}</time><strong>${this._esc(summary)}</strong></button>`;
      }
      const item = candidate.item;
''',
'''        return `<button class="agenda-row ${cls}" data-agenda="calendar" data-calendar="${this._esc(event?._calendarEntity || "")}"><span>${icon}</span><time>${this._esc(meta.label)}</time><strong>${this._esc(summary)}</strong></button>`;
      }
      if (candidate.kind === "work") {
        const item = candidate.item;
        const due = this._dueMeta(item?.due);
        const icon = candidate.workPriority === "urgent" ? "🔥" : due.overdue ? "⚠️" : "💼";
        const cls = `work ${due.overdue ? "overdue" : ""} ${candidate.priority.key}`.trim();
        const project = String(item?.project || item?.workspace || "").trim();
        const title = project ? `${project} · ${item?.title || "Pracovní úkol"}` : String(item?.title || "Pracovní úkol");
        return `<button class="agenda-row ${cls}" data-agenda="work"><span>${icon}</span><time>${this._esc(due.label || "práce")}</time><strong>${this._esc(title)}</strong></button>`;
      }
      const item = candidate.item;
''',
"work row",
)

replace_once(
'''    const agendaCount = this._calendarEvents.length
      ? `${this._agendaItems.length} úkolů · ${this._calendarEvents.length} událostí`
      : `${this._agendaItems.length} otevřených`;
''',
'''    const workCount = this._workAgendaItems().length;
    const agendaParts = [`${this._agendaItems.length} domů`];
    if (this._calendarEvents.length) agendaParts.push(`${this._calendarEvents.length} kal.`);
    if (workCount) agendaParts.push(`${workCount} práce`);
    const agendaCount = agendaParts.join(" · ");
''',
"agenda count",
)

replace_once(
'''    this.shadowRoot.querySelectorAll("[data-agenda=calendar]").forEach(el => {
      const entityId = el.getAttribute("data-calendar");
      el.addEventListener("click", () => this._moreInfo(entityId));
    });
''',
'''    this.shadowRoot.querySelectorAll("[data-agenda=calendar]").forEach(el => {
      const entityId = el.getAttribute("data-calendar");
      el.addEventListener("click", () => this._moreInfo(entityId));
    });
    this.shadowRoot.querySelectorAll("[data-agenda=work]").forEach(el => {
      el.addEventListener("click", () => this._moreInfo(c.work_agenda_entity));
    });
''',
"work click",
)

CARD.write_text(text, encoding="utf-8")
print("CARD_SHA256=" + sha(CARD))
print("WORK_AGENDA_CARD_PATCH_OK")
