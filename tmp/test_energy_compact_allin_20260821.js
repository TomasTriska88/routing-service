"use strict";

const fs = require("fs");
const assert = require("assert");

if (process.argv.length !== 3) {
  console.error("usage: test_energy_compact_allin_20260821.js CARD.js");
  process.exit(2);
}
const src = fs.readFileSync(process.argv[2], "utf8");

function has(s, msg = s) {
  assert(src.includes(s), `missing: ${msg}`);
}
function lacks(s, msg = s) {
  assert(!src.includes(s), `forbidden: ${msg}`);
}

has("20260821-smart-sharebar-r2", "current compact smart-share version marker");
assert.strictEqual((src.match(/20260821-smart-sharebar-r2/g) || []).length, 2);
has('Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)', "month total includes full fixed monthly charge");
has('const monthCostLabel = a.month.complete ? "Markvarec · měsíc celkem" : "Markvarec · odhad celkem";');
has('class="history history-smart"');
has('class="smart-sharebar"');
has('class="monthline"');
has('${this._esc(monthCostText)}');
has('${this._esc(monthCostLabel)} · vč. fixu');
has('const topLoads = a.loads.slice(0, 3);');
has('<strong>Největší spotřebiče právě teď</strong>');
has('<div class="loads">${loadHtml}</div>');
has('<strong>Podružné větve</strong>');

const renderStart = src.indexOf('    this.shadowRoot.innerHTML = `');
const renderEnd = src.indexOf('    this.shadowRoot.querySelectorAll("[data-entity]")', renderStart);
assert(renderStart >= 0 && renderEnd > renderStart);
const render = src.slice(renderStart, renderEnd);

for (const forbidden of [
  '${this._esc(costText)}',
  '${this._esc(rateDetail)}',
  '<div class="meta">',
  '<small>Konečná cena</small>',
  'bez měsíčního fixu',
]) {
  assert(!render.includes(forbidden), `visible money/layout residue: ${forbidden}`);
}
assert(render.indexOf('class="monthline"') < render.indexOf('Největší spotřebiče právě teď'));
assert(render.indexOf('Největší spotřebiče právě teď') < render.indexOf('<div class="loads">${loadHtml}</div>'));

const hStart = src.indexOf("    let historyHtml");
const hEnd = src.indexOf("    this.shadowRoot.innerHTML = `", hStart);
assert(hStart >= 0 && hEnd > hStart);
const history = src.slice(hStart, hEnd);
assert.strictEqual((history.match(/class="smart-sharebar"/g) || []).length, 1, "exactly one compact smart sharebar");
for (const forbidden of ['class="sharelegend"', 'class="smart-share"', 'Smart od 20. 8.', 'Dlouhodobý odhad']) {
  assert(!history.includes(forbidden), `old expanded history residue: ${forbidden}`);
}

for (const marker of [
  "Markvarec celkem",
  "Tomáš",
  "Rodiče",
  "site_limit_a",
  "branch_limit_a",
  "recorder/statistics_during_period",
  'period: "hour"',
  'types: ["sum"]',
  "historical_anchor_tomas_kwh",
  "historical_anchor_parents_kwh",
]) {
  has(marker, `preserved topology/history marker ${marker}`);
}

console.log("ENERGY_COMPACT_ALLIN_20260821_OK");
