// Markvarec Hnízdo energy card: 20260820-site-split-r1
// Two parallel root branches (Tomáš + Rodiče), shared 25 A feed, reset-safe Recorder history.

class LinaEnergyCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._lastRenderKey = "";
    this._history = {
      loading: false,
      error: null,
      tomas: NaN,
      parents: NaN,
      from: null,
      to: null,
      updated: 0,
    };
    this._historyRefreshAt = 0;
    this._historyPromise = null;
  }

  setConfig(config) {
    this.dataset.tvKiosk = new URLSearchParams(window.location.search).has("kiosk") ? "1" : "0";
    this._config = {
      name: "Energie",

      root_power: "sensor.vnitrni_rozvadec_vykon",
      root_current: "sensor.vnitrni_rozvadec_proud",
      root_voltage: "sensor.vnitrni_rozvadec_napeti",
      root_energy: "sensor.vnitrni_rozvadec_celkova_energie",

      parent_power: "sensor.rodicovsky_rozvadec_vykon",
      parent_current: "sensor.rodicovsky_rozvadec_proud",
      parent_voltage: "sensor.rodicovsky_rozvadec_napeti",
      parent_energy: "sensor.rodicovsky_rozvadec_celkova_energie",

      site_limit_a: 25,
      branch_limit_a: 16,
      history_start: "2026-08-20T15:00:00+02:00",
      history_refresh_ms: 900000,

      price_entity: "sensor.elektrina_aktualni_promena_cena",
      month_energy: "sensor.elektrina_spotreba_tento_mesic",
      month_cost: "sensor.elektrina_naklad_tento_mesic",
      fixed_monthly: "sensor.elektrina_fixni_poplatky_mesic",

      branches: [
        { entity: "sensor.loznicovy_rozvadec_vykon", name: "Ložnice", icon: "🛏️" },
        { entity: "sensor.jezirko_rozvadec_vykon", name: "Jezírko", icon: "💧" },
      ],

      child_loads: [
        { entity: "sensor.primotop_v_loznici_vykon", name: "Přímotop", icon: "♨️" },
        { entity: "sensor.sonoff_s60zbtpf_vykon", name: "Starlink", icon: "🛰️" },
        { entity: "sensor.zahrada_cerpadlo_destovka_vykon", name: "Dešťovka", icon: "🚰" },
        { entity: "sensor.loznice_vetrak_vykon", name: "Větrák", icon: "🌀" },
        { entity: "sensor.vanocni_osvetleni_vykon", name: "Krevetárium", icon: "💡" },
        { entity: "sensor.loznice_ostatni_vykon", name: "Ostatní ložnice", icon: "🔌" },
        { entity: "sensor.voliera_reflektor_vykon", name: "Voliéra", icon: "🐔" },
      ],

      ...config,
    };
    this._historyRefreshAt = 0;
    this._render(true);
  }

  set hass(hass) {
    this._hass = hass;
    this._refreshHistory();
    this._render();
  }

  getCardSize() { return 6; }
  getGridOptions() { return { columns: 12, rows: 6, min_rows: 5 }; }

  _st(id) {
    return this._hass?.states?.[id];
  }

  _valid(id) {
    const st = this._st(id)?.state;
    return st !== undefined &&
      st !== null &&
      !["unknown", "unavailable", ""].includes(String(st));
  }

  _num(id, fallback = NaN) {
    const n = Number.parseFloat(this._st(id)?.state);
    return Number.isFinite(n) ? n : fallback;
  }

  _esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
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
    if (Math.abs(watts) >= 1000) {
      return `${this._fmt(watts / 1000, Math.abs(watts) >= 10000 ? 1 : 2)} kW`;
    }
    return `${this._fmt(watts, Math.abs(watts) < 10 ? 1 : 0)} W`;
  }

  _powerParts(watts) {
    if (!Number.isFinite(watts)) return { value: "—", unit: "W" };
    if (Math.abs(watts) >= 1000) {
      return {
        value: this._fmt(watts / 1000, Math.abs(watts) >= 10000 ? 1 : 2),
        unit: "kW",
      };
    }
    return {
      value: this._fmt(watts, Math.abs(watts) < 10 ? 1 : 0),
      unit: "W",
    };
  }

  _currentText(amps) {
    if (!Number.isFinite(amps)) return "—";
    return `${this._fmt(amps, Math.abs(amps) < 10 ? 2 : 1)} A`;
  }

  _historyDateText(ms) {
    if (!Number.isFinite(ms)) return "—";
    return new Intl.DateTimeFormat("cs-CZ", {
      day: "numeric",
      month: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(ms));
  }

  _moreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId },
    }));
  }

  _refreshHistory(force = false) {
    if (!this._hass?.callWS || !this._config?.root_energy || !this._config?.parent_energy) {
      return this._historyPromise;
    }
    if (this._historyPromise) return this._historyPromise;

    const now = Date.now();
    if (!force && now < this._historyRefreshAt) return null;

    const refreshMs = Math.max(60000, Number(this._config.history_refresh_ms) || 900000);
    this._historyRefreshAt = now + refreshMs;
    this._history = { ...this._history, loading: true, error: null };

    const task = (async () => {
      try {
        const ids = [this._config.root_energy, this._config.parent_energy];
        const result = await this._hass.callWS({
          type: "recorder/statistics_during_period",
          start_time: this._config.history_start || "2026-08-20T15:00:00+02:00",
          end_time: new Date().toISOString(),
          statistic_ids: ids,
          period: "hour",
          types: ["sum"],
        });

        const normalize = rows => (Array.isArray(rows) ? rows : [])
          .map(row => ({ start: Number(row?.start), sum: Number(row?.sum) }))
          .filter(row => Number.isFinite(row.start) && Number.isFinite(row.sum));

        const tomasRows = normalize(result?.[ids[0]]);
        const parentRows = normalize(result?.[ids[1]]);
        const tomasByStart = new Map(tomasRows.map(row => [row.start, row.sum]));
        const parentByStart = new Map(parentRows.map(row => [row.start, row.sum]));

        const sharedStarts = [...tomasByStart.keys()]
          .filter(ts => parentByStart.has(ts))
          .sort((a, b) => a - b);

        if (sharedStarts.length < 2) {
          throw new Error("not enough overlapping long-term statistics");
        }

        const first = sharedStarts[0];
        const last = sharedStarts[sharedStarts.length - 1];

        const tomas = Math.max(0, tomasByStart.get(last) - tomasByStart.get(first));
        const parents = Math.max(0, parentByStart.get(last) - parentByStart.get(first));

        this._history = {
          loading: false,
          error: null,
          tomas,
          parents,
          from: first,
          to: last,
          updated: Date.now(),
        };
      } catch (err) {
        this._history = {
          ...this._history,
          loading: false,
          error: String(err?.message || err || "historie není dostupná"),
          updated: Date.now(),
        };
        this._historyRefreshAt = Date.now() + Math.min(refreshMs, 300000);
      } finally {
        this._historyPromise = null;
        this._render(true);
      }
    })();

    this._historyPromise = task;
    return task;
  }

  _assess() {
    const c = this._config;

    const rootPower = this._num(c.root_power, NaN);
    const rootCurrent = this._num(c.root_current, NaN);
    const rootVoltage = this._num(c.root_voltage, NaN);
    const rootEnergy = this._num(c.root_energy, NaN);

    const parentPower = this._num(c.parent_power, NaN);
    const parentCurrent = this._num(c.parent_current, NaN);
    const parentVoltage = this._num(c.parent_voltage, NaN);
    const parentEnergy = this._num(c.parent_energy, NaN);

    const sitePower = Number.isFinite(rootPower) && Number.isFinite(parentPower)
      ? Math.max(0, rootPower) + Math.max(0, parentPower)
      : NaN;

    const siteCurrent = Number.isFinite(rootCurrent) && Number.isFinite(parentCurrent)
      ? Math.max(0, rootCurrent) + Math.max(0, parentCurrent)
      : NaN;

    const siteLimitA = Math.max(1, Number(c.site_limit_a) || 25);
    const branchLimitA = Math.max(1, Number(c.branch_limit_a) || 16);

    const price = this._num(c.price_entity, NaN);
    const costPerHour = Number.isFinite(sitePower) && Number.isFinite(price)
      ? Math.max(0, sitePower) / 1000 * price
      : NaN;

    const monthEnergy = this._num(c.month_energy, NaN);
    const monthCost = this._num(c.month_cost, NaN);
    const fixedMonthly = this._num(c.fixed_monthly, NaN);

    const issues = [];

    if (!this._valid(c.root_power) || !Number.isFinite(rootPower)) {
      issues.push({
        level: 3,
        icon: "⚡",
        title: "Tomášova větev nemá data",
        text: "Vnitřní rozvaděč teď nelze spolehlivě vyhodnotit.",
        entity: c.root_power,
      });
    }

    if (!this._valid(c.parent_power) || !Number.isFinite(parentPower)) {
      issues.push({
        level: 3,
        icon: "⚡",
        title: "Rodičovská větev nemá data",
        text: "Rodičovský rozvaděč teď nelze spolehlivě vyhodnotit.",
        entity: c.parent_power,
      });
    }

    if (Number.isFinite(siteCurrent)) {
      if (siteCurrent >= siteLimitA) {
        issues.push({
          level: 2,
          icon: "⚡",
          title: `Společný přívod je na hranici ${this._fmt(siteLimitA, 0)} A`,
          text: `${this._currentText(siteCurrent)} součtem obou kořenových větví.`,
          entity: c.root_current,
        });
      } else if (siteCurrent >= siteLimitA * 0.9) {
        issues.push({
          level: 1,
          icon: "⚡",
          title: "Společný přívod se blíží limitu",
          text: `${this._currentText(siteCurrent)} z orientačního limitu ${this._fmt(siteLimitA, 0)} A.`,
          entity: c.root_current,
        });
      }
    }

    [
      { name: "Tomáš", current: rootCurrent, entity: c.root_current },
      { name: "Rodiče", current: parentCurrent, entity: c.parent_current },
    ].forEach(branch => {
      if (!Number.isFinite(branch.current)) return;

      if (branch.current >= branchLimitA) {
        issues.push({
          level: 2,
          icon: "⚡",
          title: `${branch.name}: větev je na hranici ${this._fmt(branchLimitA, 0)} A`,
          text: `${this._currentText(branch.current)} na kořenovém měření.`,
          entity: branch.entity,
        });
      } else if (branch.current >= branchLimitA * 0.9) {
        issues.push({
          level: 1,
          icon: "⚡",
          title: `${branch.name}: vyšší proud`,
          text: `${this._currentText(branch.current)} z orientačního limitu ${this._fmt(branchLimitA, 0)} A.`,
          entity: branch.entity,
        });
      }
    });

    if (!this._valid(c.price_entity) || !Number.isFinite(price)) {
      issues.push({
        level: 1,
        icon: "💸",
        title: "Cena elektřiny nemá data",
        text: "Příkon je dostupný, ale finanční odhad teď není spolehlivý.",
        entity: c.price_entity,
      });
    }

    issues.sort((a, b) => b.level - a.level);

    const branches = (Array.isArray(c.branches) ? c.branches : [])
      .map(x => ({ ...x, value: this._num(x.entity, NaN) }));

    const loads = (Array.isArray(c.child_loads) ? c.child_loads : [])
      .map(x => ({ ...x, value: this._num(x.entity, NaN) }))
      .filter(x => Number.isFinite(x.value) && x.value >= 3)
      .sort((a, b) => b.value - a.value);

    let status = { cls: "ok", label: "Běžný provoz", icon: "⚡" };

    if (!Number.isFinite(sitePower) || !Number.isFinite(siteCurrent)) {
      status = { cls: "critical", label: "Neúplná data", icon: "⚠️" };
    } else if (
      siteCurrent >= siteLimitA ||
      rootCurrent >= branchLimitA ||
      parentCurrent >= branchLimitA
    ) {
      status = { cls: "action", label: "Na hranici", icon: "⚡" };
    } else if (
      siteCurrent >= siteLimitA * 0.9 ||
      rootCurrent >= branchLimitA * 0.9 ||
      parentCurrent >= branchLimitA * 0.9
    ) {
      status = { cls: "watch", label: "Vyšší zatížení", icon: "⚡" };
    } else if (sitePower >= 1000) {
      status = { cls: "active", label: "Aktivní provoz", icon: "⚡" };
    } else if (sitePower < 150) {
      status = { cls: "calm", label: "Klidný odběr", icon: "⚡" };
    }

    const percentage = Number.isFinite(siteCurrent)
      ? Math.max(0, Math.min(100, siteCurrent / siteLimitA * 100))
      : 0;

    const rootPercentage = Number.isFinite(rootCurrent)
      ? Math.max(0, Math.min(100, rootCurrent / branchLimitA * 100))
      : 0;

    const parentPercentage = Number.isFinite(parentCurrent)
      ? Math.max(0, Math.min(100, parentCurrent / branchLimitA * 100))
      : 0;

    const historyTomas = Number(this._history?.tomas);
    const historyParents = Number(this._history?.parents);

    const historyTotal = Number.isFinite(historyTomas) && Number.isFinite(historyParents)
      ? Math.max(0, historyTomas) + Math.max(0, historyParents)
      : NaN;

    const historyTomasPct = Number.isFinite(historyTotal) && historyTotal > 0
      ? Math.max(0, historyTomas) / historyTotal * 100
      : NaN;

    const historyParentsPct = Number.isFinite(historyTotal) && historyTotal > 0
      ? Math.max(0, historyParents) / historyTotal * 100
      : NaN;

    return {
      rootPower, rootCurrent, rootVoltage, rootEnergy,
      parentPower, parentCurrent, parentVoltage, parentEnergy,
      sitePower, siteCurrent, siteLimitA, branchLimitA,
      price, costPerHour, monthEnergy, monthCost, fixedMonthly,
      issues, branches, loads, status,
      percentage, rootPercentage, parentPercentage,
      history: {
        ...(this._history || {}),
        tomas: historyTomas,
        parents: historyParents,
        total: historyTotal,
        tomasPct: historyTomasPct,
        parentsPct: historyParentsPct,
      },
    };
  }

  _render(force = false) {
    if (!this._hass) return;

    const c = this._config;
    const a = this._assess();

    const key = JSON.stringify([
      a.rootPower, a.rootCurrent, a.rootVoltage,
      a.parentPower, a.parentCurrent, a.parentVoltage,
      a.sitePower, a.siteCurrent, a.price, a.costPerHour,
      a.monthEnergy, a.monthCost, a.fixedMonthly,
      a.status.cls, a.percentage, a.rootPercentage, a.parentPercentage,
      a.issues.map(x => [x.level, x.title, x.text]),
      a.branches.map(x => [x.entity, x.value]),
      a.loads.map(x => [x.entity, x.value]),
      [
        a.history.loading,
        a.history.error,
        a.history.tomas,
        a.history.parents,
        a.history.from,
        a.history.to,
      ],
    ]);

    if (!force && key === this._lastRenderKey) return;
    this._lastRenderKey = key;

    const sitePower = this._powerParts(a.sitePower);

    const rootItems = [
      {
        name: "Tomáš",
        power: a.rootPower,
        current: a.rootCurrent,
        percentage: a.rootPercentage,
        entity: c.root_power,
      },
      {
        name: "Rodiče",
        power: a.parentPower,
        current: a.parentCurrent,
        percentage: a.parentPercentage,
        entity: c.parent_power,
      },
    ];

    const rootHtml = rootItems.map((x, i) => `
      <button class="root-card" data-root="${i}" title="Otevřít detail kořenové větve">
        <div class="root-head">
          <strong>${this._esc(x.name)}</strong>
          <span>${this._esc(this._powerText(x.power))}</span>
        </div>
        <div class="root-current">
          <strong>${this._esc(this._currentText(x.current))}</strong>
          <small>/ ${this._fmt(a.branchLimitA, 0)} A</small>
        </div>
        <div class="mini-meter">
          <span style="width:${x.percentage.toFixed(2)}%"></span>
        </div>
      </button>`).join("");

    const branchHtml = a.branches.length
      ? a.branches.map((x, i) => `
          <button class="load branch" data-branch="${i}" title="Otevřít detail Tomášovy podružné větve">
            <span class="load-icon">${this._esc(x.icon || "•")}</span>
            <span class="load-copy">
              <small>${this._esc(x.name || x.entity)}</small>
              <strong>${this._esc(this._powerText(x.value))}</strong>
            </span>
          </button>`).join("")
      : `<div class="loads-empty">Tomášovy měřené podružné větve nejsou dostupné.</div>`;

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
      : `<div class="loads-empty">Žádný známý Tomášův podružný odběr není právě výrazný.</div>`;

    const issue = a.issues[0] || null;

    const issueHtml = issue
      ? `<button class="issue sev${issue.level}" data-issue title="Otevřít detail">
           <span>${issue.icon}</span>
           <span>
             <strong>${this._esc(issue.title)}</strong>
             <small>${this._esc(issue.text)}</small>
           </span>
         </button>`
      : "";

    const priceText = Number.isFinite(a.price)
      ? `${this._fmt(a.price, 2)} Kč/kWh`
      : "—";

    const costText = Number.isFinite(a.costPerHour)
      ? `≈ ${this._fmt(a.costPerHour, a.costPerHour < 10 ? 2 : 1)} Kč/h`
      : "—";

    const rootVoltageText = Number.isFinite(a.rootVoltage)
      ? `${this._fmt(a.rootVoltage, 0)} V`
      : "—";

    const monthEnergyUnit = this._st(c.month_energy)?.attributes?.unit_of_measurement || "kWh";

    const monthEnergyText = Number.isFinite(a.monthEnergy)
      ? `${this._fmt(a.monthEnergy, a.monthEnergy >= 100 ? 0 : 2)} ${monthEnergyUnit}`
      : "—";

    const monthCostText = Number.isFinite(a.monthCost)
      ? `${this._fmt(a.monthCost, 2)} Kč`
      : "—";

    const rateDetail = Number.isFinite(a.price)
      ? `obě kořenové větve · ${priceText} proměnná`
      : "Cena není dostupná";

    let historyHtml;

    if (
      Number.isFinite(a.history.tomasPct) &&
      Number.isFinite(a.history.parentsPct) &&
      Number.isFinite(a.history.tomas) &&
      Number.isFinite(a.history.parents)
    ) {
      historyHtml = `
        <div class="history">
          <div class="history-head">
            <strong>Spotřeba Tomáš × Rodiče</strong>
            <span>${this._esc(this._historyDateText(a.history.from))} → ${this._esc(this._historyDateText(a.history.to))}</span>
          </div>
          <div class="sharebar" title="Reset-safe dlouhodobé statistiky Recorderu">
            <span class="share-tomas" style="width:${Math.max(0, Math.min(100, a.history.tomasPct)).toFixed(2)}%"></span>
            <span class="share-parents" style="width:${Math.max(0, Math.min(100, a.history.parentsPct)).toFixed(2)}%"></span>
          </div>
          <div class="sharelegend">
            <span>
              <strong>Tomáš ${this._fmt(a.history.tomasPct, 0)} %</strong>
              <small>${this._fmt(a.history.tomas, 2)} kWh</small>
            </span>
            <span>
              <strong>Rodiče ${this._fmt(a.history.parentsPct, 0)} %</strong>
              <small>${this._fmt(a.history.parents, 2)} kWh</small>
            </span>
          </div>
        </div>`;
    } else {
      const historyState = a.history.loading
        ? "Načítám společnou reset-safe historii…"
        : (a.history.error
            ? "Společná historie zatím není dostupná."
            : "Čekám na dostatek společných dlouhodobých statistik.");

      historyHtml = `
        <div class="history history-pending">
          <div class="history-head">
            <strong>Spotřeba Tomáš × Rodiče</strong>
            <span>od 20. 8. 15:00</span>
          </div>
          <div class="loads-empty">${this._esc(historyState)}</div>
        </div>`;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display:block;
          container-type:inline-size;
          height:100%;
        }

        ha-card {
          height:100%;
          overflow:hidden;
          position:relative;
          border-radius:var(--ha-card-border-radius,16px);
        }

        .wrap {
          box-sizing:border-box;
          height:100%;
          min-height:280px;
          padding:11px 13px 10px;
          display:flex;
          flex-direction:column;
          gap:7px;
          position:relative;
          isolation:isolate;
          background:
            radial-gradient(
              circle at 8% 0%,
              color-mix(in srgb, var(--primary-color) 15%, transparent),
              transparent 34%
            ),
            linear-gradient(
              145deg,
              color-mix(in srgb, var(--card-background-color) 96%, var(--primary-color) 4%),
              var(--ha-card-background,var(--card-background-color))
            );
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

        .header {
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:10px;
          min-width:0;
        }

        .title { min-width:0; }

        .title strong {
          display:block;
          font-size:16px;
          line-height:1.1;
        }

        .title small {
          display:block;
          margin-top:3px;
          font-size:11px;
          opacity:.68;
          overflow-wrap:anywhere;
        }

        .status {
          flex:0 0 auto;
          border-radius:999px;
          padding:5px 8px;
          font-size:12px;
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

        .reading {
          min-width:0;
          display:flex;
          align-items:baseline;
          gap:5px;
        }

        .reading strong {
          font-size:38px;
          line-height:.95;
          letter-spacing:-.045em;
          font-weight:780;
        }

        .reading span {
          font-size:15px;
          opacity:.68;
          font-weight:650;
        }

        .rate {
          min-width:0;
          text-align:right;
        }

        .rate strong {
          display:block;
          font-size:15px;
        }

        .rate small {
          display:block;
          font-size:11px;
          opacity:.68;
          margin-top:2px;
        }

        .limitline {
          display:flex;
          justify-content:space-between;
          align-items:baseline;
          gap:8px;
          font-size:11px;
        }

        .limitline strong { font-size:12px; }
        .limitline span { opacity:.76; }

        .meter,
        .mini-meter,
        .sharebar {
          height:7px;
          border-radius:999px;
          overflow:hidden;
          background:rgba(127,127,127,.12);
        }

        .meter > span,
        .mini-meter > span {
          display:block;
          height:100%;
          min-width:0;
          border-radius:inherit;
          background:linear-gradient(
            90deg,
            color-mix(in srgb, var(--primary-color) 78%, white 22%),
            var(--primary-color)
          );
          box-shadow:0 0 16px color-mix(in srgb, var(--primary-color) 38%, transparent);
          transition:width .45s ease;
        }

        .root-split {
          display:grid;
          grid-template-columns:repeat(2,minmax(0,1fr));
          gap:6px;
        }

        .root-card {
          appearance:none;
          color:inherit;
          border:1px solid color-mix(in srgb, var(--primary-color) 18%, transparent);
          border-radius:11px;
          padding:7px 8px;
          background:rgba(127,127,127,.055);
          text-align:left;
          cursor:pointer;
          min-width:0;
        }

        .root-head {
          display:flex;
          justify-content:space-between;
          align-items:baseline;
          gap:8px;
        }

        .root-head strong { font-size:13px; }

        .root-head span {
          font-size:14px;
          font-weight:750;
          white-space:nowrap;
        }

        .root-current {
          display:flex;
          align-items:baseline;
          gap:3px;
          margin-top:3px;
        }

        .root-current strong { font-size:17px; }
        .root-current small { font-size:10px; opacity:.68; }

        .mini-meter {
          margin-top:5px;
          height:5px;
        }

        .history {
          border-radius:11px;
          padding:7px 8px;
          background:rgba(127,127,127,.045);
        }

        .history-head {
          display:flex;
          justify-content:space-between;
          align-items:baseline;
          gap:8px;
          min-width:0;
        }

        .history-head strong { font-size:12px; }

        .history-head span {
          font-size:10px;
          opacity:.68;
          white-space:nowrap;
        }

        .sharebar {
          display:flex;
          margin-top:6px;
        }

        .sharebar span {
          display:block;
          height:100%;
        }

        .share-tomas { background:var(--primary-color); }

        .share-parents {
          background:color-mix(
            in srgb,
            var(--primary-color) 28%,
            rgba(127,127,127,.55)
          );
        }

        .sharelegend {
          display:grid;
          grid-template-columns:repeat(2,minmax(0,1fr));
          gap:8px;
          margin-top:5px;
        }

        .sharelegend span {
          display:flex;
          justify-content:space-between;
          gap:7px;
          min-width:0;
        }

        .sharelegend strong { font-size:11px; }

        .sharelegend small {
          font-size:10px;
          opacity:.68;
          white-space:nowrap;
        }

        .meta {
          display:grid;
          grid-template-columns:repeat(4,minmax(0,1fr));
          gap:6px;
        }

        .meta button {
          appearance:none;
          color:inherit;
          text-align:left;
          border:0;
          padding:6px 8px;
          border-radius:11px;
          background:rgba(127,127,127,.055);
          cursor:pointer;
          min-width:0;
        }

        .meta small {
          display:block;
          font-size:10px;
          opacity:.68;
          text-transform:uppercase;
          letter-spacing:.045em;
        }

        .meta strong {
          display:block;
          font-size:14px;
          margin-top:2px;
          overflow-wrap:anywhere;
        }

        .loads-head {
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:8px;
          min-width:0;
        }

        .loads-head strong {
          font-size:12px;
          opacity:.68;
        }

        .loads-head span {
          font-size:11px;
          opacity:.68;
        }

        .branches,
        .loads {
          display:grid;
          grid-template-columns:repeat(3,minmax(0,1fr));
          gap:6px;
        }

        .branch {
          border:1px solid color-mix(in srgb, var(--primary-color) 18%, transparent);
        }

        .load {
          appearance:none;
          color:inherit;
          border:0;
          border-radius:11px;
          padding:6px 8px;
          background:rgba(127,127,127,.055);
          display:flex;
          align-items:center;
          gap:7px;
          min-width:0;
          text-align:left;
          cursor:pointer;
        }

        .load-icon {
          flex:0 0 auto;
          font-size:15px;
        }

        .load-copy { min-width:0; }

        .load-copy small {
          display:block;
          font-size:12px;
          opacity:.68;
          overflow-wrap:anywhere;
        }

        .load-copy strong {
          display:block;
          font-size:15px;
          margin-top:1px;
          white-space:nowrap;
        }

        .loads-empty {
          padding:6px 8px;
          border-radius:9px;
          background:rgba(127,127,127,.04);
          font-size:11px;
          opacity:.68;
        }

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

        .issue strong {
          display:block;
          font-size:12px;
        }

        .issue small {
          display:block;
          font-size:11px;
          opacity:.68;
          margin-top:1px;
          overflow-wrap:anywhere;
        }

        .issue.sev1 { background:rgba(255,193,7,.10); }
        .issue.sev2 { background:rgba(255,152,0,.13); }
        .issue.sev3 { background:rgba(244,67,54,.14); }

        @container (max-width:460px) {
          .wrap {
            padding:11px;
            min-height:320px;
          }

          .hero {
            grid-template-columns:1fr;
            gap:4px;
          }

          .rate { text-align:left; }

          .meta {
            grid-template-columns:repeat(2,minmax(0,1fr));
          }

          .reading strong { font-size:34px; }

          .root-split,
          .sharelegend,
          .branches,
          .loads {
            grid-template-columns:1fr;
          }

          .load { padding:6px 8px; }

          .history-head {
            align-items:flex-start;
            flex-direction:column;
            gap:2px;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          .wrap::before,
          .meter > span,
          .mini-meter > span {
            transition:none !important;
            animation:none !important;
          }
        }

        /* Markvarec TV space-aware readability: 20260820-energy-site-split-r1 */
        :host([data-tv-kiosk="1"]) .title small { font-size:13px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .reading span { font-size:16px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .rate strong { font-size:17px; }
        :host([data-tv-kiosk="1"]) .rate small { font-size:14px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .limitline { font-size:13px; }
        :host([data-tv-kiosk="1"]) .limitline strong { font-size:14px; }
        :host([data-tv-kiosk="1"]) .root-head strong { font-size:15px; }
        :host([data-tv-kiosk="1"]) .root-head span { font-size:17px; }
        :host([data-tv-kiosk="1"]) .root-current strong { font-size:19px; }
        :host([data-tv-kiosk="1"]) .root-current small { font-size:13px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .history-head strong { font-size:14px; }
        :host([data-tv-kiosk="1"]) .history-head span { font-size:12px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .sharelegend strong { font-size:14px; }
        :host([data-tv-kiosk="1"]) .sharelegend small { font-size:13px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .meta small { font-size:13px; opacity:.82; letter-spacing:.035em; }
        :host([data-tv-kiosk="1"]) .meta strong { font-size:16px; }
        :host([data-tv-kiosk="1"]) .loads-head strong { font-size:14px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .loads-head span { font-size:13px; opacity:.80; }
        :host([data-tv-kiosk="1"]) .load-copy small { font-size:15px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .load-copy strong { font-size:17px; }
        :host([data-tv-kiosk="1"]) .loads-empty { font-size:13px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .issue strong { font-size:14px; }
        :host([data-tv-kiosk="1"]) .issue small { font-size:13px; opacity:.82; }
      </style>

      <ha-card>
        <div class="wrap ${a.status.cls}" style="--energy-load:${a.percentage.toFixed(2)}">
          <div class="header">
            <div class="title">
              <strong>${this._esc(c.name)}</strong>
              <small>
                Markvarec celkem · Tomáš + Rodiče · společný přívod ${this._fmt(a.siteLimitA,0)} A
              </small>
            </div>
            <div class="status ${a.status.cls}">
              ${a.status.icon} ${this._esc(a.status.label)}
            </div>
          </div>

          <div class="hero">
            <div class="reading">
              <strong>${this._esc(sitePower.value)}</strong>
              <span>${this._esc(sitePower.unit)}</span>
            </div>
            <div class="rate">
              <strong>${this._esc(costText)}</strong>
              <small>${this._esc(rateDetail)}</small>
            </div>
          </div>

          <div class="limitline">
            <strong>Společný přívod</strong>
            <span>
              ${this._esc(this._currentText(a.siteCurrent))}
              / ${this._fmt(a.siteLimitA,0)} A
            </span>
          </div>

          <div
            class="meter"
            title="Součet proudů obou kořenových větví proti společnému limitu"
          >
            <span style="width:${a.percentage.toFixed(2)}%"></span>
          </div>

          <div class="root-split">${rootHtml}</div>

          ${historyHtml}

          <div class="meta">
            <button data-entity="${this._esc(c.price_entity)}">
              <small>Cena</small>
              <strong>${this._esc(priceText)}</strong>
            </button>

            <button data-entity="${this._esc(c.root_voltage)}">
              <small>Napětí Tomáš</small>
              <strong>${this._esc(rootVoltageText)}</strong>
            </button>

            <button data-entity="${this._esc(c.month_energy)}">
              <small>Tomáš tento měsíc</small>
              <strong>${this._esc(monthEnergyText)}</strong>
            </button>

            <button data-entity="${this._esc(c.month_cost)}">
              <small>Tomáš + fix</small>
              <strong>${this._esc(monthCostText)}</strong>
            </button>
          </div>

          ${issueHtml}

          <div class="loads-head">
            <strong>Tomáš · podružné větve</strong>
            <span>součást jeho kořenové větve</span>
          </div>

          <div class="branches">${branchHtml}</div>

          <div class="loads-head">
            <strong>Tomáš · největší spotřebiče právě teď</strong>
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
      this.shadowRoot.querySelector("[data-issue]")?.addEventListener(
        "click",
        () => this._moreInfo(issue.entity),
      );
    }

    this.shadowRoot.querySelectorAll("[data-root]").forEach(el => {
      el.addEventListener("click", () => {
        const item = rootItems[Number(el.getAttribute("data-root"))];
        if (item?.entity) this._moreInfo(item.entity);
      });
    });

    this.shadowRoot.querySelectorAll("[data-branch]").forEach(el => {
      el.addEventListener("click", () => {
        const item = a.branches[Number(el.getAttribute("data-branch"))];
        if (item?.entity) this._moreInfo(item.entity);
      });
    });

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
    description: "Přehled Markvarce: společný přívod, Tomáš, rodiče a reset-safe poměr spotřeby.",
    preview: true,
  });
}
