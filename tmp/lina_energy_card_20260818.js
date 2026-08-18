class LinaEnergyCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._lastRenderKey = "";
  }

  setConfig(config) {
    this._config = {
      name: "Energie",
      root_power: "sensor.vnitrni_rozvadec_vykon",
      root_energy: "sensor.vnitrni_rozvadec_celkova_energie",
      root_voltage: "sensor.vnitrni_rozvadec_napeti",
      max_power: 3600,
      price_per_kwh: 7.21,
      child_loads: [
        { entity: "sensor.primotop_v_loznici_vykon", name: "Přímotop", icon: "♨️" },
        { entity: "sensor.sonoff_s60zbtpf_vykon", name: "Starlink", icon: "🛰️" },
        { entity: "sensor.jezirko_rozvadec_vykon", name: "Jezírko", icon: "💧" },
        { entity: "sensor.jezirko_cerpadlo_vykon", name: "Dešťovka", icon: "🚰" },
        { entity: "sensor.loznice_vetrak_vykon", name: "Větrák", icon: "🌀" },
        { entity: "sensor.vanocni_osvetleni_vykon", name: "Krevetárium", icon: "💡" },
        { entity: "sensor.drubezi_vybeh_vykon", name: "Voliéra", icon: "🐔" }
      ],
      ...config,
    };
    this._render(true);
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return 5; }
  getGridOptions() { return { columns: 12, rows: 5, min_rows: 4 }; }

  _st(id) { return this._hass?.states?.[id]; }
  _valid(id) {
    const st = this._st(id)?.state;
    return st !== undefined && st !== null && !["unknown", "unavailable", ""].includes(String(st));
  }
  _num(id, fallback = NaN) {
    const raw = this._st(id)?.state;
    const n = Number.parseFloat(raw);
    return Number.isFinite(n) ? n : fallback;
  }
  _esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    }[c]));
  }
  _fmt(value, digits = 0) {
    if (!Number.isFinite(value)) return "—";
    return new Intl.NumberFormat("cs-CZ", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(value);
  }
  _powerText(watts) {
    if (!Number.isFinite(watts)) return "—";
    if (Math.abs(watts) >= 1000) return `${this._fmt(watts / 1000, watts >= 10000 ? 1 : 2)} kW`;
    return `${this._fmt(watts, watts < 10 ? 1 : 0)} W`;
  }
  _moreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId },
    }));
  }

  _assess() {
    const c = this._config;
    const rootValid = this._valid(c.root_power);
    const power = this._num(c.root_power, NaN);
    const voltage = this._num(c.root_voltage, NaN);
    const energy = this._num(c.root_energy, NaN);
    const maxPower = Math.max(1, Number(c.max_power) || 3600);
    const price = Number(c.price_per_kwh);
    const costPerHour = Number.isFinite(power) && Number.isFinite(price)
      ? Math.max(0, power) / 1000 * price
      : NaN;

    const issues = [];
    if (!rootValid || !Number.isFinite(power)) {
      issues.push({
        level: 3,
        icon: "⚡",
        title: "Kořenové měření nemá data",
        text: "Aktuální spotřebu nelze spolehlivě vyhodnotit.",
        entity: c.root_power,
      });
    } else if (power >= 3000) {
      issues.push({
        level: 2,
        icon: "⚡",
        title: "Velmi vysoký odběr",
        text: `${this._powerText(power)} na kořenovém měření · prověřit, co právě běží.`,
        entity: c.root_power,
      });
    } else if (power >= 2000) {
      issues.push({
        level: 1,
        icon: "⚡",
        title: "Vyšší odběr",
        text: `${this._powerText(power)} na kořenovém měření.`,
        entity: c.root_power,
      });
    }

    const loads = (Array.isArray(c.child_loads) ? c.child_loads : [])
      .map(x => {
        const value = this._num(x.entity, NaN);
        return { ...x, value };
      })
      .filter(x => Number.isFinite(x.value) && x.value >= 3)
      .sort((a, b) => b.value - a.value);

    let status = { cls: "ok", label: "Běžný provoz", icon: "⚡" };
    if (!rootValid || !Number.isFinite(power)) status = { cls: "critical", label: "Bez dat", icon: "⚠️" };
    else if (power >= 3000) status = { cls: "action", label: "Vysoký odběr", icon: "⚡" };
    else if (power >= 2000) status = { cls: "watch", label: "Vyšší odběr", icon: "⚡" };
    else if (power >= 800) status = { cls: "active", label: "Aktivní provoz", icon: "⚡" };
    else if (power < 100) status = { cls: "calm", label: "Klidný odběr", icon: "⚡" };

    const percentage = Number.isFinite(power)
      ? Math.max(0, Math.min(100, power / maxPower * 100))
      : 0;

    return { power, voltage, energy, costPerHour, maxPower, issues, loads, status, percentage };
  }

  _render(force = false) {
    if (!this._hass) return;
    const c = this._config;
    const a = this._assess();

    const key = JSON.stringify([
      a.power, a.voltage, a.energy, a.costPerHour, a.status.cls, a.percentage,
      a.issues.map(x => [x.level, x.title, x.text]),
      a.loads.map(x => [x.entity, x.value]),
    ]);
    if (!force && key === this._lastRenderKey) return;
    this._lastRenderKey = key;

    const topLoads = a.loads.slice(0, 3);
    const hiddenLoads = Math.max(0, a.loads.length - topLoads.length);
    const loadHtml = topLoads.length
      ? topLoads.map((x, i) => `
          <button class="load" data-load="${i}" title="Otevřít detail">
            <span class="load-icon">${this._esc(x.icon || "•")}</span>
            <span class="load-copy">
              <small>${this._esc(x.name || x.entity)}</small>
              <strong>${this._esc(this._powerText(x.value))}</strong>
            </span>
          </button>`).join("")
      : `<div class="loads-empty">Žádný známý podružný odběr není právě výrazný.</div>`;

    const issue = a.issues[0] || null;
    const issueHtml = issue
      ? `<button class="issue sev${issue.level}" data-issue title="Otevřít detail">
           <span>${issue.icon}</span>
           <span><strong>${this._esc(issue.title)}</strong><small>${this._esc(issue.text)}</small></span>
         </button>`
      : "";

    const energyUnit = this._st(c.root_energy)?.attributes?.unit_of_measurement || "kWh";
    const energyText = Number.isFinite(a.energy)
      ? `${this._fmt(a.energy, a.energy >= 100 ? 0 : 2)} ${energyUnit}`
      : "—";
    const voltageText = Number.isFinite(a.voltage) ? `${this._fmt(a.voltage, 0)} V` : "—";
    const costText = Number.isFinite(a.costPerHour)
      ? `≈ ${this._fmt(a.costPerHour, a.costPerHour < 10 ? 2 : 1)} Kč/h`
      : "—";

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; container-type:inline-size; height:100%; }
        ha-card {
          height:100%;
          overflow:hidden;
          position:relative;
          border-radius:var(--ha-card-border-radius,16px);
        }
        .wrap {
          box-sizing:border-box;
          height:100%;
          min-height:220px;
          padding:14px 16px 13px;
          display:flex;
          flex-direction:column;
          gap:10px;
          position:relative;
          isolation:isolate;
          background:
            radial-gradient(circle at 8% 0%,
              color-mix(in srgb, var(--primary-color) 15%, transparent),
              transparent 34%),
            linear-gradient(145deg,
              color-mix(in srgb, var(--card-background-color) 96%, var(--primary-color) 4%),
              var(--ha-card-background,var(--card-background-color)));
        }
        .wrap::before {
          content:"";
          position:absolute;
          inset:-35% -25% auto 38%;
          height:190px;
          z-index:-1;
          opacity:.18;
          filter:blur(3px);
          background:radial-gradient(circle, var(--primary-color), transparent 67%);
          transform:translate3d(calc(var(--energy-load,0) * .12px),0,0);
          transition:opacity .35s ease, transform .5s ease;
          pointer-events:none;
        }
        .wrap.watch::before { opacity:.24; }
        .wrap.action::before { opacity:.32; }
        .wrap.critical::before { opacity:.38; }

        .header { display:flex; align-items:center; justify-content:space-between; gap:10px; min-width:0; }
        .title { min-width:0; }
        .title strong { display:block; font-size:16px; line-height:1.1; }
        .title small { display:block; margin-top:3px; font-size:9px; opacity:.55; overflow-wrap:anywhere; }
        .status {
          flex:0 0 auto;
          border-radius:999px;
          padding:5px 8px;
          font-size:10px;
          font-weight:750;
          border:1px solid rgba(127,127,127,.18);
          background:rgba(127,127,127,.08);
        }
        .status.calm,.status.ok { background:rgba(76,175,80,.11); }
        .status.active { background:color-mix(in srgb, var(--primary-color) 13%, transparent); }
        .status.watch { background:rgba(255,193,7,.15); }
        .status.action { background:rgba(255,152,0,.18); }
        .status.critical { background:rgba(244,67,54,.19); }

        .hero {
          display:grid;
          grid-template-columns:minmax(0,1fr) auto;
          align-items:end;
          gap:12px;
          min-width:0;
        }
        .reading { min-width:0; display:flex; align-items:baseline; gap:5px; }
        .reading strong { font-size:42px; line-height:.95; letter-spacing:-.045em; font-weight:780; }
        .reading span { font-size:15px; opacity:.58; font-weight:650; }
        .rate { min-width:0; text-align:right; }
        .rate strong { display:block; font-size:15px; }
        .rate small { display:block; font-size:9px; opacity:.55; margin-top:2px; }

        .meter { height:7px; border-radius:999px; overflow:hidden; background:rgba(127,127,127,.12); }
        .meter > span {
          display:block;
          height:100%;
          width:calc(var(--energy-load,0) * 1%);
          min-width:0;
          border-radius:inherit;
          background:linear-gradient(90deg, color-mix(in srgb, var(--primary-color) 78%, white 22%), var(--primary-color));
          box-shadow:0 0 16px color-mix(in srgb, var(--primary-color) 38%, transparent);
          transition:width .45s ease;
        }
        .meta {
          display:grid;
          grid-template-columns:repeat(2,minmax(0,1fr));
          gap:6px;
        }
        .meta button {
          appearance:none;
          color:inherit;
          text-align:left;
          border:0;
          padding:7px 8px;
          border-radius:11px;
          background:rgba(127,127,127,.055);
          cursor:pointer;
          min-width:0;
        }
        .meta small { display:block; font-size:8px; opacity:.52; text-transform:uppercase; letter-spacing:.055em; }
        .meta strong { display:block; font-size:13px; margin-top:2px; overflow-wrap:anywhere; }

        .loads-head {
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:8px;
          min-width:0;
        }
        .loads-head strong { font-size:10px; opacity:.68; }
        .loads-head span { font-size:9px; opacity:.48; }
        .loads { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:6px; }
        .load {
          appearance:none;
          color:inherit;
          border:0;
          border-radius:11px;
          padding:7px 8px;
          background:rgba(127,127,127,.055);
          display:flex;
          align-items:center;
          gap:7px;
          min-width:0;
          text-align:left;
          cursor:pointer;
        }
        .load-icon { flex:0 0 auto; font-size:16px; }
        .load-copy { min-width:0; }
        .load-copy small { display:block; font-size:8px; opacity:.55; overflow-wrap:anywhere; }
        .load-copy strong { display:block; font-size:12px; margin-top:1px; white-space:nowrap; }
        .loads-empty { padding:8px 9px; border-radius:11px; background:rgba(127,127,127,.045); font-size:9px; opacity:.58; }
        .issue {
          appearance:none;
          width:100%;
          color:inherit;
          border:1px solid rgba(127,127,127,.14);
          border-radius:11px;
          padding:7px 8px;
          display:grid;
          grid-template-columns:auto minmax(0,1fr);
          gap:8px;
          align-items:start;
          text-align:left;
          cursor:pointer;
          background:rgba(127,127,127,.055);
        }
        .issue strong { display:block; font-size:10px; }
        .issue small { display:block; font-size:9px; opacity:.64; margin-top:1px; overflow-wrap:anywhere; }
        .issue.sev1 { background:rgba(255,193,7,.10); }
        .issue.sev2 { background:rgba(255,152,0,.13); }
        .issue.sev3 { background:rgba(244,67,54,.14); }

        @container (max-width:460px) {
          .wrap { padding:12px; min-height:235px; }
          .hero { grid-template-columns:1fr; gap:5px; }
          .rate { text-align:left; }
          .reading strong { font-size:36px; }
          .loads { grid-template-columns:1fr; }
          .load { padding:6px 8px; }
        }
        @media (prefers-reduced-motion: reduce) {
          .wrap::before,.meter > span { transition:none !important; animation:none !important; }
        }
      </style>
      <ha-card>
        <div class="wrap ${a.status.cls}" style="--energy-load:${a.percentage.toFixed(2)}">
          <div class="header">
            <div class="title">
              <strong>${this._esc(c.name)}</strong>
              <small>Kořenové měření celého Markvarce · podružné větve jsou jen kontext</small>
            </div>
            <div class="status ${a.status.cls}">${a.status.icon} ${this._esc(a.status.label)}</div>
          </div>

          <div class="hero">
            <div class="reading">
              <strong>${this._esc(Number.isFinite(a.power) ? this._fmt(a.power, a.power < 10 ? 1 : 0) : "—")}</strong>
              <span>W</span>
            </div>
            <div class="rate">
              <strong>${this._esc(costText)}</strong>
              <small>při současném odběru · ${this._fmt(Number(c.price_per_kwh), 2)} Kč/kWh</small>
            </div>
          </div>

          <div class="meter" title="Orientační zatížení vůči ${this._fmt(a.maxPower,0)} W">
            <span></span>
          </div>

          <div class="meta">
            <button data-entity="${this._esc(c.root_voltage)}"><small>Napětí</small><strong>${this._esc(voltageText)}</strong></button>
            <button data-entity="${this._esc(c.root_energy)}"><small>Celkové měřidlo</small><strong>${this._esc(energyText)}</strong></button>
          </div>

          ${issueHtml}

          <div class="loads-head">
            <strong>Největší známé odběry právě teď</strong>
            <span>${hiddenLoads ? `+ ${hiddenLoads} další` : ""}</span>
          </div>
          <div class="loads">${loadHtml}</div>
        </div>
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll("[data-entity]").forEach(el => {
      el.addEventListener("click", () => this._moreInfo(el.getAttribute("data-entity")));
    });
    if (issue?.entity) {
      this.shadowRoot.querySelector("[data-issue]")?.addEventListener("click", () => this._moreInfo(issue.entity));
    }
    this.shadowRoot.querySelectorAll("[data-load]").forEach(el => {
      el.addEventListener("click", () => {
        const item = topLoads[Number(el.getAttribute("data-load"))];
        if (item?.entity) this._moreInfo(item.entity);
      });
    });
  }

  static getStubConfig() {
    return { name: "Energie" };
  }
}

if (!customElements.get("lina-energy-card")) {
  customElements.define("lina-energy-card", LinaEnergyCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some(x => x.type === "lina-energy-card")) {
  window.customCards.push({
    type: "lina-energy-card",
    name: "Lina Energy Card",
    description: "Významový přehled kořenové spotřeby a aktivních podružných větví.",
    preview: true,
  });
}
