#!/usr/bin/env node
"use strict";

const fs = require("fs");

const path = process.argv[2];
if (!path) {
  console.error("usage: test_energy_smart_sharebar_20260821.js CARD_JS");
  process.exit(2);
}
const text = fs.readFileSync(path, "utf8");

function must(cond, msg) {
  if (!cond) {
    console.error(`FAIL: ${msg}`);
    process.exit(1);
  }
}

must((text.match(/20260821-smart-sharebar-r2/g) || []).length === 2, "new version marker must appear twice");
must(text.includes('history_start: "2026-08-20T15:00:00+02:00"'), "shared smart baseline must remain 20 Aug 2026 15:00 +02");
must(text.includes('type: "recorder/statistics_during_period"'), "ratio must remain based on Recorder statistics");
must(text.includes("const smartTomasKwh = Number(a.history.tomas);"), "bar must use smart Tomáš kWh");
must(text.includes("const smartParentsKwh = Number(a.history.parents);"), "bar must use smart parent kWh");
must(text.includes("const smartTomasPct = Number(a.history.tomasPct);"), "bar must use smart Tomáš percent");
must(text.includes("const smartParentsPct = Number(a.history.parentsPct);"), "bar must use smart parent percent");
must(text.includes('class="smart-sharebar"'), "smart share bar must render");
must(text.includes('class="smart-sharebar-tomas"'), "Tomáš bar segment must render");
must(text.includes('class="smart-sharebar-parents"'), "parent bar segment must render");
must(text.includes("background:#ef6c00;"), "parent bar must keep original orange identity");
must(text.includes("T ${this._fmt(smartTomasKwh, 1)} kWh"), "Tomáš kWh must be visible");
must(text.includes("R ${this._fmt(smartParentsKwh, 1)} kWh"), "parent kWh must be visible");
must(text.includes("od 20. 8."), "bar must visibly identify smart overlap start");
must(text.includes('role="img"'), "bar must have semantic image role");
must(text.includes("const topLoads = a.loads.slice(0, 3);"), "three top loads must remain");
must(text.includes('class="monthline"'), "compact monthly line must remain");
must(text.includes("${this._esc(monthCostText)}"), "all-in monthly cost hero must remain");
must(text.includes("${this._esc(monthCostLabel)} · vč. fixu"), "all-in fixed-charge label must remain");
must(text.includes('const monthCostLabel = a.month.complete ? "Markvarec · měsíc celkem" : "Markvarec · odhad celkem";'), "monthly all-in label must explicitly identify whole Markvarec");
must(text.includes("const refreshMs = Math.max(60000, Number(this._config.history_refresh_ms) || 900000);"), "smart history refresh remains 15 minutes by default");

const start = text.indexOf('    let historyHtml = "";');
const end = text.indexOf('    this.shadowRoot.innerHTML = `', start);
must(start >= 0 && end > start, "history render range must exist");
const history = text.slice(start, end);

for (const forbidden of [
  "a.history.longTomas",
  "a.history.longParents",
  "26. 6. 2025",
  "Dlouhodobý odhad",
  "historical_anchor_tomas_kwh",
  "historical_anchor_parents_kwh",
]) {
  must(!history.includes(forbidden), `displayed ratio must never depend on stale historical estimate: ${forbidden}`);
}
must((history.match(/class="smart-sharebar"/g) || []).length === 1, "exactly one smart share bar must render");
must(history.includes("smartTomasKwh + smartParentsKwh > 0"), "bar must require a positive shared measured total");
must(history.includes("Poměr se nikdy nedoplňuje historickým odhadem"), "unavailable state must explicitly avoid historical fallback");

console.log("ENERGY_SMART_SHAREBAR_20260821_OK");
