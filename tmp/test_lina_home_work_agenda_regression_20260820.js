const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("/config/www/lina-home-card.js", "utf8");

let Defined = null;
class FakeHTMLElement {
  constructor() {
    this.dataset = {};
    this.shadowRoot = null;
  }
  attachShadow() {
    this.shadowRoot = {
      innerHTML: "",
      querySelectorAll: () => [],
    };
    return this.shadowRoot;
  }
  dispatchEvent() {}
}

const sandbox = {
  HTMLElement: FakeHTMLElement,
  CustomEvent: class {},
  URLSearchParams,
  window: {
    location: { search: "" },
    setInterval: () => 1,
    clearInterval: () => {},
    setTimeout: (fn) => fn(),
  },
  customElements: {
    get: () => null,
    define: (_name, cls) => { Defined = cls; },
  },
  console,
  Date,
  Number,
  String,
  Array,
  Object,
  Math,
  JSON,
  RegExp,
};
vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: "lina-home-card.js" });
if (!Defined) throw new Error("LinaHomeCard was not registered");

const card = new Defined();
card.setConfig({});
if (card._config.work_agenda_entity !== "sensor.lineum_work_agenda") {
  throw new Error("work agenda entity is not configured");
}

const pad = n => String(n).padStart(2, "0");
const localDate = offset => {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() + offset);
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
};

card._agendaItems = [{
  summary: "[KRITICKÁ] Bezpečnostní Markvarec úkol",
  due: localDate(0),
  status: "needs_action",
}];
card._calendarEvents = [];
card._hass = {
  states: {
    "sensor.lineum_work_agenda": {
      state: "2",
      attributes: {
        source_status: "ok",
        items: [
          {
            id: "work-high",
            title: "Kritický pracovní blocker",
            project: "Development",
            workspace: "Client",
            status: "in progress",
            priority: "urgent",
            due: localDate(-1),
            url: "https://app.clickup.com/t/work-high",
            source: "clickup",
          },
          {
            id: "work-normal",
            title: "Běžný pracovní úkol",
            project: "Lineum",
            workspace: "Lineum",
            status: "to do",
            priority: "normal",
            due: localDate(1),
            url: "https://app.clickup.com/t/work-normal",
            source: "clickup",
          },
        ],
      },
    },
    "sensor.lina_status": { state: "ok", attributes: {} },
    "binary_sensor.markvarec_local_internet": { state: "on" },
    "automation.chatgpt_home_assistant_bridge": { state: "on" },
    "media_player.loznice_google_nest_mini": { state: "idle" },
  },
};

let combined = card._combinedAgenda();
if (combined[0]?.kind !== "todo" || combined[0]?.priority?.key !== "critical") {
  throw new Error("critical Markvarec todo must remain absolute first");
}
if (combined[1]?.kind !== "work" || combined[1]?.item?.id !== "work-high") {
  throw new Error("urgent overdue work item should follow critical Markvarec todo");
}

card._agendaItems = [{
  summary: "[STŘEDNÍ] Běžný domácí úkol",
  due: localDate(3),
  status: "needs_action",
}];
combined = card._combinedAgenda();
if (combined[0]?.kind !== "work" || combined[0]?.item?.id !== "work-high") {
  throw new Error("urgent overdue work item should outrank a normal future home todo");
}

card._render(true);
if (!card.shadowRoot.innerHTML.includes('data-agenda="work"')) {
  throw new Error("rendered agenda does not include a work row");
}
if (!card.shadowRoot.innerHTML.includes("Development · Kritický pracovní blocker")) {
  throw new Error("work row does not carry project context");
}

card._hass.states["sensor.lineum_work_agenda"].attributes.source_status = "error";
if (card._workAgendaItems().length !== 0) {
  throw new Error("source_status=error must hide stale/untrusted work items");
}

if (!source.includes('this._moreInfo(c.work_agenda_entity)')) {
  throw new Error("work row does not keep a safe HA more-info click target");
}

console.log("WORK_AGENDA_CARD_REGRESSION_OK");
