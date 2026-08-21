#!/usr/bin/env node
"use strict";

const fs = require("fs");
const assert = require("assert");

if (process.argv.length !== 3) {
  console.error("usage: test_lina_energy_allin_dynamic_regression_20260821.js CARD.js");
  process.exit(2);
}

const src = fs.readFileSync(process.argv[2], "utf8");

function has(s, msg = s) {
  assert(src.includes(s), `missing: ${msg}`);
}
function lacks(s, msg = s) {
  assert(!src.includes(s), `forbidden: ${msg}`);
}

has("20260821-allin-dynamic-r1", "new card version");
has("const fixedAccrued =", "accrued fixed charge");
has("const fixedPerHour =", "hourly fixed charge");
has("const elapsedMonthFraction =", "elapsed month fraction");
has("const hoursInMonth =", "actual calendar month hours");
has("new Date(nowDate.getFullYear(), nowDate.getMonth(), 1)", "local month start");
has("new Date(nowDate.getFullYear(), nowDate.getMonth() + 1, 1)", "local next-month boundary");
has("Math.max(0, fixedMonthly) * elapsedMonthFraction", "fixed accrual formula");
has("Math.max(0, fixedMonthly) / hoursInMonth", "fixed hourly formula");
has("Math.max(0, siteMonthEnergy) * price + fixedAccrued", "month-to-date all-in formula");
has("Math.max(0, sitePower) / 1000 * price + fixedPerHour", "live all-in rate formula");
lacks("Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)", "whole fixed fee must not be charged on day one");
lacks("Math.max(0, sitePower) / 1000 * effectivePrice", "live rate must not multiply by month-to-date effective price");

has("Náklad měsíce dosud");
has("Odhad nákladu dosud");
has("proměnná spotřeba + průběžný podíl fixu");
has("Efektivně dosud");
has("fixní měsíční poplatky se započítávají jen poměrně podle dosud uplynulého času");
lacks('const monthCostLabel = a.month.complete ? "Cena měsíce" : "Odhad ceny měsíce"');
lacks("konečná efektivní cena");
lacks("odhad konečné efektivní ceny");
lacks("bez měsíčního fixu");

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
  "sensor.technicka_rozvadec_provizorni_vykon",
  "Tomáš · podružné větve",
]) {
  has(marker, `preserved topology/history marker ${marker}`);
}

lacks("sensor.elektrina_rodice_spotreba_tento_mesic", "do not add duplicate parent monthly meter");
lacks("elektrina_rodice_spotreba_mesic", "do not add duplicate parent utility meter");

function finance({nowMs, y, m, powerW, monthKwh, variablePrice, fixedMonthly}) {
  const start = new Date(y, m, 1).getTime();
  const next = new Date(y, m + 1, 1).getTime();
  const duration = next - start;
  const elapsed = Math.max(0, Math.min(duration, nowMs - start));
  const fraction = elapsed / duration;
  const hours = duration / 3600000;
  const fixedAccrued = fixedMonthly * fraction;
  const fixedPerHour = fixedMonthly / hours;
  return {
    fixedAccrued,
    fixedPerHour,
    monthCost: monthKwh * variablePrice + fixedAccrued,
    liveCost: powerW / 1000 * variablePrice + fixedPerHour,
  };
}

const start = new Date(2026, 7, 1).getTime();
const next = new Date(2026, 8, 1).getTime();
const mid = start + (next - start) / 2;
const f = finance({
  nowMs: mid,
  y: 2026,
  m: 7,
  powerW: 1000,
  monthKwh: 100,
  variablePrice: 6,
  fixedMonthly: 744,
});
assert(Math.abs(f.fixedPerHour - 1) < 1e-9, `fixedPerHour=${f.fixedPerHour}`);
assert(Math.abs(f.fixedAccrued - 372) < 1e-9, `fixedAccrued=${f.fixedAccrued}`);
assert(Math.abs(f.liveCost - 7) < 1e-9, `liveCost=${f.liveCost}`);
assert(Math.abs(f.monthCost - 972) < 1e-9, `monthCost=${f.monthCost}`);

console.log("ENERGY_ALLIN_DYNAMIC_REGRESSION_OK");
