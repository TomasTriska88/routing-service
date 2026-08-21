#!/usr/bin/env node
"use strict";

const fs = require("fs");
const assert = require("assert");

if (process.argv.length !== 3) {
  console.error("usage: test_lina_energy_allin_dynamic_regression_20260821_r2b.js CARD.js");
  process.exit(2);
}

const src = fs.readFileSync(process.argv[2], "utf8");

function has(s, msg = s) {
  assert(src.includes(s), `missing: ${msg}`);
}
function lacks(s, msg = s) {
  assert(!src.includes(s), `forbidden: ${msg}`);
}

has("ENERGY_ALLIN_DYNAMIC_20260821_R2", "all-in dynamic card marker");
has("const fixedAccrued =", "accrued monthly charges");
has("const fixedPerHour =", "hourly share of monthly charges");
has("const elapsedMonthFraction =", "elapsed month fraction");
has("const hoursInMonth =", "actual local calendar month hours");
has("new Date(nowDate.getFullYear(), nowDate.getMonth(), 1)", "local month start");
has("new Date(nowDate.getFullYear(), nowDate.getMonth() + 1, 1)", "local next-month boundary");
has("Math.max(0, fixedMonthly) * elapsedMonthFraction", "time-proportional monthly accrual");
has("Math.max(0, fixedMonthly) / hoursInMonth", "time-proportional hourly share");
has("Math.max(0, siteMonthEnergy) * price + fixedAccrued", "month-to-date all-in cost");
has("Math.max(0, sitePower) / 1000 * price + fixedPerHour", "live all-in Kč/h");
has("const effectivePrice = monthComplete &&", "effective Kč/kWh only with full dual-branch coverage");
has("const monthEstimated = false;", "no monetary historical backfill");

lacks("parentBeforeSmartEstimate", "historical ratio must not fabricate billed parent kWh");
lacks("financeParentRatio", "historical ratio must not enter money calculation");
lacks("rootBeforeSmart", "historical ratio must not enter money calculation");
lacks("Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)", "whole monthly charge must not be booked on day one");
lacks("Math.max(0, sitePower) / 1000 * effectivePrice", "live rate must not multiply by MTD effective price");
lacks("Chybějící část rodičovské spotřeby je dopočtená", "money coverage must not claim backfill");
lacks("rodičovská část dopočtená", "money coverage must not claim backfill");

has("Spotřeba měsíce dosud");
has("Známá spotřeba dosud");
has("Náklad měsíce dosud");
has("Známý náklad dosud");
has("Konečná Kč/kWh");
has("peníze chybějící období neodhadují");
has("známé minimum bez historického dopočtu");
has("všech časově naběhlých účtovaných složek");

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
  "Tomáš · podružné větve",
]) {
  has(marker, `preserved topology/history marker ${marker}`);
}

lacks("sensor.elektrina_rodice_spotreba_tento_mesic", "do not add duplicate parent monthly meter");
lacks("elektrina_rodice_spotreba_mesic", "do not add duplicate parent utility meter");

function finance({nowMs, y, m, powerW, knownMonthKwh, variablePrice, monthlyCharges, coverageComplete}) {
  const start = new Date(y, m, 1).getTime();
  const next = new Date(y, m + 1, 1).getTime();
  const duration = next - start;
  const elapsed = Math.max(0, Math.min(duration, nowMs - start));
  const fraction = elapsed / duration;
  const hours = duration / 3600000;
  const fixedAccrued = monthlyCharges * fraction;
  const fixedPerHour = monthlyCharges / hours;
  const monthCost = knownMonthKwh * variablePrice + fixedAccrued;
  const effectivePrice = coverageComplete && knownMonthKwh > 0 ? monthCost / knownMonthKwh : NaN;
  const liveCost = powerW / 1000 * variablePrice + fixedPerHour;
  return { fixedAccrued, fixedPerHour, monthCost, effectivePrice, liveCost };
}

const augStart = new Date(2026, 7, 1).getTime();
const sepStart = new Date(2026, 8, 1).getTime();
const augMid = augStart + (sepStart - augStart) / 2;
const f = finance({
  nowMs: augMid,
  y: 2026,
  m: 7,
  powerW: 1000,
  knownMonthKwh: 100,
  variablePrice: 6,
  monthlyCharges: 744,
  coverageComplete: true,
});
assert(Math.abs(f.fixedPerHour - 1) < 1e-9, `fixedPerHour=${f.fixedPerHour}`);
assert(Math.abs(f.fixedAccrued - 372) < 1e-9, `fixedAccrued=${f.fixedAccrued}`);
assert(Math.abs(f.liveCost - 7) < 1e-9, `liveCost=${f.liveCost}`);
assert(Math.abs(f.monthCost - 972) < 1e-9, `monthCost=${f.monthCost}`);
assert(Math.abs(f.effectivePrice - 9.72) < 1e-9, `effectivePrice=${f.effectivePrice}`);

const partial = finance({
  nowMs: augMid,
  y: 2026,
  m: 7,
  powerW: 500,
  knownMonthKwh: 50,
  variablePrice: 6,
  monthlyCharges: 744,
  coverageComplete: false,
});
assert(Number.isNaN(partial.effectivePrice), "partial first smart month must not show fabricated all-in Kč/kWh");
assert(Math.abs(partial.monthCost - 672) < 1e-9, `known minimum monthCost=${partial.monthCost}`);
assert(Math.abs(partial.liveCost - 4) < 1e-9, `partial liveCost=${partial.liveCost}`);

console.log("ENERGY_ALLIN_DYNAMIC_R2B_REGRESSION_OK");
