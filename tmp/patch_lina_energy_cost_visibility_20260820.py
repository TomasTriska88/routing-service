from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_lina_energy_cost_visibility_20260820.py INPUT OUTPUT")

src = Path(sys.argv[1])
out = Path(sys.argv[2])
t = src.read_text(encoding="utf-8")


def rep(old: str, new: str) -> None:
    global t
    count = t.count(old)
    if count != 1:
        raise AssertionError(f"expected exactly one match, got {count}: {old[:120]!r}")
    t = t.replace(old, new, 1)


rep(
    '// Markvarec Hnízdo energy card: 20260820-site-split-r1\n// Two parallel root branches (Tomáš + Rodiče), shared 25 A feed, reset-safe Recorder history.',
    '// Markvarec Hnízdo energy card: 20260820-cost-visibility-r1\n// Two parallel root branches, utilization-colored amp bars, archive+smart share and combined monthly cost.',
)

rep(
    '''      parents: NaN,\n      from: null,\n      to: null,\n      updated: 0,''',
    '''      parents: NaN,\n      parentMonth: NaN,\n      monthFrom: null,\n      monthComplete: false,\n      from: null,\n      to: null,\n      updated: 0,''',
)

rep(
    '''      history_start: "2026-08-20T15:00:00+02:00",\n      history_refresh_ms: 900000,''',
    '''      history_start: "2026-08-20T15:00:00+02:00",\n      history_refresh_ms: 900000,\n      historical_anchor_start: "2025-06-26T00:00:00+02:00",\n      historical_anchor_tomas_kwh: 4607,\n      historical_anchor_parents_kwh: 2281,''',
)

rep(
    '''  _currentText(amps) {\n    if (!Number.isFinite(amps)) return "—";\n    return `${this._fmt(amps, Math.abs(amps) < 10 ? 2 : 1)} A`;\n  }\n\n  _historyDateText(ms) {''',
    '''  _currentText(amps) {\n    if (!Number.isFinite(amps)) return "—";\n    return `${this._fmt(amps, Math.abs(amps) < 10 ? 2 : 1)} A`;\n  }\n\n  _utilClass(percent) {\n    if (!Number.isFinite(percent)) return "util-unknown";\n    if (percent >= 90) return "util-critical";\n    if (percent >= 80) return "util-high";\n    if (percent >= 60) return "util-watch";\n    return "util-ok";\n  }\n\n  _historyDateText(ms) {''',
)

rep(
    '''        const tomas = Math.max(0, tomasByStart.get(last) - tomasByStart.get(first));\n        const parents = Math.max(0, parentByStart.get(last) - parentByStart.get(first));\n\n        this._history = {\n          loading: false,\n          error: null,\n          tomas,\n          parents,\n          from: first,\n          to: last,\n          updated: Date.now(),\n        };''',
    '''        const tomas = Math.max(0, tomasByStart.get(last) - tomasByStart.get(first));\n        const parents = Math.max(0, parentByStart.get(last) - parentByStart.get(first));\n\n        const monthStartDate = new Date();\n        monthStartDate.setDate(1);\n        monthStartDate.setHours(0, 0, 0, 0);\n        const monthStart = monthStartDate.getTime();\n        const configuredHistoryStart = Date.parse(this._config.history_start || "2026-08-20T15:00:00+02:00");\n        const parentMonthCutoff = Math.max(monthStart, configuredHistoryStart);\n        const parentMonthRows = parentRows\n          .filter(row => row.start >= parentMonthCutoff)\n          .sort((a, b) => a.start - b.start);\n        const parentMonth = parentMonthRows.length >= 2\n          ? Math.max(0, parentMonthRows[parentMonthRows.length - 1].sum - parentMonthRows[0].sum)\n          : 0;\n        const monthFrom = parentMonthRows.length ? parentMonthRows[0].start : null;\n        const monthComplete = Number.isFinite(configuredHistoryStart) && configuredHistoryStart <= monthStart;\n\n        this._history = {\n          loading: false,\n          error: null,\n          tomas,\n          parents,\n          parentMonth,\n          monthFrom,\n          monthComplete,\n          from: first,\n          to: last,\n          updated: Date.now(),\n        };''',
)

rep(
    '''    const monthEnergy = this._num(c.month_energy, NaN);\n    const monthCost = this._num(c.month_cost, NaN);\n    const fixedMonthly = this._num(c.fixed_monthly, NaN);''',
    '''    const monthEnergy = this._num(c.month_energy, NaN);\n    const fixedMonthly = this._num(c.fixed_monthly, NaN);\n    const parentMonthEnergy = Number(this._history?.parentMonth);\n    const siteMonthEnergy = Number.isFinite(monthEnergy) && Number.isFinite(parentMonthEnergy)\n      ? Math.max(0, monthEnergy) + Math.max(0, parentMonthEnergy)\n      : NaN;\n    const siteMonthCost = Number.isFinite(siteMonthEnergy) && Number.isFinite(price) && Number.isFinite(fixedMonthly)\n      ? Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)\n      : NaN;\n    const monthComplete = Boolean(this._history?.monthComplete);''',
)

rep(
    '''    const historyParentsPct = Number.isFinite(historyTotal) && historyTotal > 0\n      ? Math.max(0, historyParents) / historyTotal * 100\n      : NaN;\n\n    return {''',
    '''    const historyParentsPct = Number.isFinite(historyTotal) && historyTotal > 0\n      ? Math.max(0, historyParents) / historyTotal * 100\n      : NaN;\n\n    const smartAvailable = Number.isFinite(historyTomas) && Number.isFinite(historyParents);\n    const anchorTomas = Number(c.historical_anchor_tomas_kwh);\n    const anchorParents = Number(c.historical_anchor_parents_kwh);\n    const longTomas = Number.isFinite(anchorTomas)\n      ? Math.max(0, anchorTomas) + (smartAvailable ? Math.max(0, historyTomas) : 0)\n      : NaN;\n    const longParents = Number.isFinite(anchorParents)\n      ? Math.max(0, anchorParents) + (smartAvailable ? Math.max(0, historyParents) : 0)\n      : NaN;\n    const longTotal = Number.isFinite(longTomas) && Number.isFinite(longParents)\n      ? longTomas + longParents\n      : NaN;\n    const longTomasPct = Number.isFinite(longTotal) && longTotal > 0 ? longTomas / longTotal * 100 : NaN;\n    const longParentsPct = Number.isFinite(longTotal) && longTotal > 0 ? longParents / longTotal * 100 : NaN;\n\n    return {''',
)

rep(
    '''      price, costPerHour, monthEnergy, monthCost, fixedMonthly,\n      issues, branches, loads, status,\n      percentage, rootPercentage, parentPercentage,\n      history: {\n        ...(this._history || {}),\n        tomas: historyTomas,\n        parents: historyParents,\n        total: historyTotal,\n        tomasPct: historyTomasPct,\n        parentsPct: historyParentsPct,\n      },''',
    '''      price, costPerHour, monthEnergy, fixedMonthly,\n      month: {\n        parents: parentMonthEnergy,\n        total: siteMonthEnergy,\n        cost: siteMonthCost,\n        complete: monthComplete,\n        from: this._history?.monthFrom ?? null,\n      },\n      issues, branches, loads, status,\n      percentage, rootPercentage, parentPercentage,\n      history: {\n        ...(this._history || {}),\n        tomas: historyTomas,\n        parents: historyParents,\n        total: historyTotal,\n        tomasPct: historyTomasPct,\n        parentsPct: historyParentsPct,\n        smartAvailable,\n        longTomas,\n        longParents,\n        longTotal,\n        longTomasPct,\n        longParentsPct,\n      },''',
)

rep(
    '''      a.sitePower, a.siteCurrent, a.price, a.costPerHour,\n      a.monthEnergy, a.monthCost, a.fixedMonthly,\n      a.status.cls, a.percentage, a.rootPercentage, a.parentPercentage,''',
    '''      a.sitePower, a.siteCurrent, a.price, a.costPerHour,\n      a.monthEnergy, a.fixedMonthly, a.month.parents, a.month.total, a.month.cost, a.month.complete,\n      a.status.cls, a.percentage, a.rootPercentage, a.parentPercentage,''',
)

rep(
    '''        a.history.tomas,\n        a.history.parents,\n        a.history.from,\n        a.history.to,''',
    '''        a.history.tomas,\n        a.history.parents,\n        a.history.longTomas,\n        a.history.longParents,\n        a.history.longTomasPct,\n        a.history.longParentsPct,\n        a.history.from,\n        a.history.to,''',
)

rep(
    '''        current: a.rootCurrent,\n        percentage: a.rootPercentage,\n        entity: c.root_power,''',
    '''        current: a.rootCurrent,\n        voltage: a.rootVoltage,\n        percentage: a.rootPercentage,\n        entity: c.root_power,''',
)

rep(
    '''        current: a.parentCurrent,\n        percentage: a.parentPercentage,\n        entity: c.parent_power,''',
    '''        current: a.parentCurrent,\n        voltage: a.parentVoltage,\n        percentage: a.parentPercentage,\n        entity: c.parent_power,''',
)

rep(
    '''        <div class="root-current">\n          <strong>${this._esc(this._currentText(x.current))}</strong>\n          <small>/ ${this._fmt(a.branchLimitA, 0)} A</small>\n        </div>\n        <div class="mini-meter">\n          <span style="width:${x.percentage.toFixed(2)}%"></span>\n        </div>''',
    '''        <div class="root-current">\n          <strong>${this._esc(this._currentText(x.current))}</strong>\n          <small>/ ${this._fmt(a.branchLimitA, 0)} A</small>\n          <span class="root-voltage">${Number.isFinite(x.voltage) ? `${this._fmt(x.voltage, 0)} V` : "—"}</span>\n        </div>\n        <div class="mini-meter ${this._utilClass(x.percentage)}">\n          <span style="width:${x.percentage.toFixed(2)}%"></span>\n        </div>''',
)

rep(
    '''    const rootVoltageText = Number.isFinite(a.rootVoltage)\n      ? `${this._fmt(a.rootVoltage, 0)} V`\n      : "—";\n\n    const monthEnergyUnit = this._st(c.month_energy)?.attributes?.unit_of_measurement || "kWh";\n\n    const monthEnergyText = Number.isFinite(a.monthEnergy)\n      ? `${this._fmt(a.monthEnergy, a.monthEnergy >= 100 ? 0 : 2)} ${monthEnergyUnit}`\n      : "—";\n\n    const monthCostText = Number.isFinite(a.monthCost)\n      ? `${this._fmt(a.monthCost, 2)} Kč`\n      : "—";''',
    '''    const fixedText = Number.isFinite(a.fixedMonthly)\n      ? `${this._fmt(a.fixedMonthly, 2)} Kč`\n      : "—";\n\n    const monthEnergyUnit = this._st(c.month_energy)?.attributes?.unit_of_measurement || "kWh";\n\n    const monthEnergyText = Number.isFinite(a.month.total)\n      ? `${this._fmt(a.month.total, a.month.total >= 100 ? 0 : 2)} ${monthEnergyUnit}`\n      : "—";\n\n    const monthCostText = Number.isFinite(a.month.cost)\n      ? `${this._fmt(a.month.cost, 2)} Kč`\n      : "—";\n\n    const monthEnergyLabel = a.month.complete ? "Markvarec tento měsíc" : "Známé minimum měsíce";\n    const monthCostLabel = a.month.complete ? "Cena měsíce vč. fixu" : "Min. cena vč. fixu";''',
)

rep(
    '''    const rateDetail = Number.isFinite(a.price)\n      ? `obě kořenové větve · ${priceText} proměnná`\n      : "Cena není dostupná";''',
    '''    const rateDetail = Number.isFinite(a.price)\n      ? `obě kořenové větve · ${priceText} proměnná · bez měsíčního fixu`\n      : "Cena není dostupná";''',
)

old_history = '''    let historyHtml;\n\n    if (\n      Number.isFinite(a.history.tomasPct) &&\n      Number.isFinite(a.history.parentsPct) &&\n      Number.isFinite(a.history.tomas) &&\n      Number.isFinite(a.history.parents)\n    ) {\n      historyHtml = `\n        <div class="history">\n          <div class="history-head">\n            <strong>Spotřeba Tomáš × Rodiče</strong>\n            <span>${this._esc(this._historyDateText(a.history.from))} → ${this._esc(this._historyDateText(a.history.to))}</span>\n          </div>\n          <div class="sharebar" title="Reset-safe dlouhodobé statistiky Recorderu">\n            <span class="share-tomas" style="width:${Math.max(0, Math.min(100, a.history.tomasPct)).toFixed(2)}%"></span>\n            <span class="share-parents" style="width:${Math.max(0, Math.min(100, a.history.parentsPct)).toFixed(2)}%"></span>\n          </div>\n          <div class="sharelegend">\n            <span>\n              <strong>Tomáš ${this._fmt(a.history.tomasPct, 0)} %</strong>\n              <small>${this._fmt(a.history.tomas, 2)} kWh</small>\n            </span>\n            <span>\n              <strong>Rodiče ${this._fmt(a.history.parentsPct, 0)} %</strong>\n              <small>${this._fmt(a.history.parents, 2)} kWh</small>\n            </span>\n          </div>\n        </div>`;\n    } else {\n      const historyState = a.history.loading\n        ? "Načítám společnou reset-safe historii…"\n        : (a.history.error\n            ? "Společná historie zatím není dostupná."\n            : "Čekám na dostatek společných dlouhodobých statistik.");\n\n      historyHtml = `\n        <div class="history history-pending">\n          <div class="history-head">\n            <strong>Spotřeba Tomáš × Rodiče</strong>\n            <span>od 20. 8. 15:00</span>\n          </div>\n          <div class="loads-empty">${this._esc(historyState)}</div>\n        </div>`;\n    }'''

new_history = '''    let historyHtml;\n\n    if (\n      Number.isFinite(a.history.longTomasPct) &&\n      Number.isFinite(a.history.longParentsPct) &&\n      Number.isFinite(a.history.longTomas) &&\n      Number.isFinite(a.history.longParents)\n    ) {\n      const smartLine = a.history.smartAvailable\n        ? `Smart od 20. 8.: Tomáš ${this._fmt(a.history.tomasPct, 0)} % · Rodiče ${this._fmt(a.history.parentsPct, 0)} % · ${this._fmt(a.history.tomas, 2)} / ${this._fmt(a.history.parents, 2)} kWh`\n        : (a.history.loading ? "Smart poměr se načítá…" : "Smart poměr zatím není dostupný.");\n      historyHtml = `\n        <div class="history">\n          <div class="history-head">\n            <strong>Dlouhodobý odhad poměru</strong>\n            <span>od 26. 6. 2025 · archiv + smart</span>\n          </div>\n          <div class="sharebar" title="Historický odhad z archivních odečtů, od 20. 8. 2026 doplňovaný reset-safe smart statistikami">\n            <span class="share-tomas" style="width:${Math.max(0, Math.min(100, a.history.longTomasPct)).toFixed(2)}%">\n              ${a.history.longTomasPct >= 12 ? `<b>${this._fmt(a.history.longTomasPct, 0)} %</b>` : ""}\n            </span>\n            <span class="share-parents" style="width:${Math.max(0, Math.min(100, a.history.longParentsPct)).toFixed(2)}%">\n              ${a.history.longParentsPct >= 12 ? `<b>${this._fmt(a.history.longParentsPct, 0)} %</b>` : ""}\n            </span>\n          </div>\n          <div class="sharelegend">\n            <span>\n              <strong>Tomáš ${this._fmt(a.history.longTomasPct, 0)} %</strong>\n              <small>≈ ${this._fmt(a.history.longTomas, 0)} kWh</small>\n            </span>\n            <span>\n              <strong>Rodiče ${this._fmt(a.history.longParentsPct, 0)} %</strong>\n              <small>≈ ${this._fmt(a.history.longParents, 0)} kWh</small>\n            </span>\n          </div>\n          <div class="smart-share">${this._esc(smartLine)}</div>\n        </div>`;\n    } else {\n      historyHtml = `\n        <div class="history history-pending">\n          <div class="history-head">\n            <strong>Dlouhodobý odhad poměru</strong>\n            <span>archiv + smart</span>\n          </div>\n          <div class="loads-empty">Historický poměr zatím není dostupný.</div>\n        </div>`;\n    }'''
rep(old_history, new_history)

rep(
    '''        .meter > span,\n        .mini-meter > span {\n          display:block;\n          height:100%;\n          min-width:0;\n          border-radius:inherit;\n          background:linear-gradient(\n            90deg,\n            color-mix(in srgb, var(--primary-color) 78%, white 22%),\n            var(--primary-color)\n          );\n          box-shadow:0 0 16px color-mix(in srgb, var(--primary-color) 38%, transparent);\n          transition:width .45s ease;\n        }''',
    '''        .meter > span,\n        .mini-meter > span {\n          display:block;\n          height:100%;\n          min-width:0;\n          border-radius:inherit;\n          transition:width .45s ease, background .25s ease, box-shadow .25s ease;\n        }\n\n        .meter { height:9px; }\n        .util-ok > span { background:linear-gradient(90deg,#2e7d32,#43a047); box-shadow:0 0 12px rgba(67,160,71,.30); }\n        .util-watch > span { background:linear-gradient(90deg,#f9a825,#fbc02d); box-shadow:0 0 13px rgba(251,192,45,.34); }\n        .util-high > span { background:linear-gradient(90deg,#ef6c00,#fb8c00); box-shadow:0 0 14px rgba(251,140,0,.38); }\n        .util-critical > span { background:linear-gradient(90deg,#c62828,#e53935); box-shadow:0 0 16px rgba(229,57,53,.48); }\n        .util-unknown > span { background:rgba(127,127,127,.35); box-shadow:none; }''',
)

rep(
    '''        .root-current strong { font-size:17px; }\n        .root-current small { font-size:10px; opacity:.68; }\n\n        .mini-meter {\n          margin-top:5px;\n          height:5px;\n        }''',
    '''        .root-current strong { font-size:17px; }\n        .root-current small { font-size:10px; opacity:.68; }\n        .root-voltage {\n          margin-left:auto;\n          font-size:11px;\n          font-weight:700;\n          opacity:.80;\n          white-space:nowrap;\n        }\n\n        .mini-meter {\n          margin-top:5px;\n          height:6px;\n        }''',
)

rep(
    '''        .sharebar {\n          display:flex;\n          margin-top:6px;\n        }\n\n        .sharebar span {\n          display:block;\n          height:100%;\n        }\n\n        .share-tomas { background:var(--primary-color); }\n\n        .share-parents {\n          background:color-mix(\n            in srgb,\n            var(--primary-color) 28%,\n            rgba(127,127,127,.55)\n          );\n        }''',
    '''        .sharebar {\n          display:flex;\n          margin-top:6px;\n          height:16px;\n          border:1px solid rgba(255,255,255,.22);\n          box-shadow:inset 0 0 0 1px rgba(0,0,0,.08);\n        }\n\n        .sharebar span {\n          display:flex;\n          align-items:center;\n          justify-content:center;\n          height:100%;\n          min-width:0;\n          transition:width .45s ease;\n        }\n\n        .sharebar b {\n          color:white;\n          font-size:10px;\n          line-height:1;\n          font-weight:850;\n          text-shadow:0 1px 3px rgba(0,0,0,.72);\n          white-space:nowrap;\n        }\n\n        .share-tomas { background:#1565c0; }\n\n        .share-parents {\n          background:#ef6c00;\n          border-left:2px solid rgba(255,255,255,.90);\n        }''',
)

rep(
    '''        .sharelegend small {\n          font-size:10px;\n          opacity:.68;\n          white-space:nowrap;\n        }\n\n        .meta {''',
    '''        .sharelegend small {\n          font-size:10px;\n          opacity:.68;\n          white-space:nowrap;\n        }\n\n        .smart-share {\n          margin-top:4px;\n          font-size:10px;\n          line-height:1.25;\n          opacity:.72;\n          overflow-wrap:anywhere;\n        }\n\n        .meta {''',
)

rep(
    '''        .meta button {\n          appearance:none;\n          color:inherit;\n          text-align:left;\n          border:0;\n          padding:6px 8px;\n          border-radius:11px;\n          background:rgba(127,127,127,.055);\n          cursor:pointer;\n          min-width:0;\n        }''',
    '''        .meta button {\n          appearance:none;\n          color:inherit;\n          text-align:left;\n          border:0;\n          padding:6px 8px;\n          border-radius:11px;\n          background:rgba(127,127,127,.055);\n          cursor:pointer;\n          min-width:0;\n        }\n\n        .meta button:not([data-entity]) { cursor:default; }''',
)

rep(
    '''        /* Markvarec TV space-aware readability: 20260820-energy-site-split-r1 */''',
    '''        /* Markvarec TV space-aware readability: 20260820-cost-visibility-r1 */''',
)

rep(
    '''        :host([data-tv-kiosk="1"]) .root-current strong { font-size:19px; }\n        :host([data-tv-kiosk="1"]) .root-current small { font-size:13px; opacity:.82; }''',
    '''        :host([data-tv-kiosk="1"]) .root-current strong { font-size:19px; }\n        :host([data-tv-kiosk="1"]) .root-current small { font-size:13px; opacity:.82; }\n        :host([data-tv-kiosk="1"]) .root-voltage { font-size:14px; opacity:.88; }''',
)

rep(
    '''        :host([data-tv-kiosk="1"]) .sharelegend strong { font-size:14px; }\n        :host([data-tv-kiosk="1"]) .sharelegend small { font-size:13px; opacity:.82; }''',
    '''        :host([data-tv-kiosk="1"]) .sharebar { height:18px; }\n        :host([data-tv-kiosk="1"]) .sharebar b { font-size:12px; }\n        :host([data-tv-kiosk="1"]) .sharelegend strong { font-size:14px; }\n        :host([data-tv-kiosk="1"]) .sharelegend small { font-size:13px; opacity:.82; }\n        :host([data-tv-kiosk="1"]) .smart-share { font-size:12px; opacity:.82; }''',
)

rep(
    '''            class="meter"\n            title="Součet proudů obou kořenových větví proti společnému limitu"''',
    '''            class="meter ${this._utilClass(a.percentage)}"\n            title="Součet proudů obou kořenových větví proti společnému limitu; barva roste se zatížením"''',
)

rep(
    '''          <div class="meta">\n            <button data-entity="${this._esc(c.price_entity)}">\n              <small>Cena</small>\n              <strong>${this._esc(priceText)}</strong>\n            </button>\n\n            <button data-entity="${this._esc(c.root_voltage)}">\n              <small>Napětí Tomáš</small>\n              <strong>${this._esc(rootVoltageText)}</strong>\n            </button>\n\n            <button data-entity="${this._esc(c.month_energy)}">\n              <small>Tomáš tento měsíc</small>\n              <strong>${this._esc(monthEnergyText)}</strong>\n            </button>\n\n            <button data-entity="${this._esc(c.month_cost)}">\n              <small>Tomáš + fix</small>\n              <strong>${this._esc(monthCostText)}</strong>\n            </button>\n          </div>''',
    '''          <div class="meta">\n            <button data-entity="${this._esc(c.price_entity)}">\n              <small>Cena za kWh</small>\n              <strong>${this._esc(priceText)}</strong>\n            </button>\n\n            <button data-entity="${this._esc(c.fixed_monthly)}">\n              <small>Fix / měsíc</small>\n              <strong>${this._esc(fixedText)}</strong>\n            </button>\n\n            <button title="Součet Tomášovy měsíční spotřeby a dostupné rodičovské smart spotřeby">\n              <small>${this._esc(monthEnergyLabel)}</small>\n              <strong>${this._esc(monthEnergyText)}</strong>\n            </button>\n\n            <button title="Proměnná cena známé spotřeby + právě jeden společný měsíční fix">\n              <small>${this._esc(monthCostLabel)}</small>\n              <strong>${this._esc(monthCostText)}</strong>\n            </button>\n          </div>''',
)

rep(
    '''    description: "Přehled Markvarce: společný přívod, Tomáš, rodiče a reset-safe poměr spotřeby.",''',
    '''    description: "Přehled Markvarce: dvě kořenové větve, barevné zatížení, dlouhodobý poměr a společná cena včetně fixu.",''',
)

out.write_text(t, encoding="utf-8")
print(f"ENERGY_COST_VISIBILITY_PATCH_OK bytes={len(t.encode('utf-8'))}")
