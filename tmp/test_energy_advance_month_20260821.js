#!/usr/bin/env node
const fs = require("fs");

const cardPath = process.argv[2];
const configPath = process.argv[3];
if (!cardPath || !configPath) {
  throw new Error("usage: node test_energy_advance_month_20260821.js CARD_JS CONFIG_YAML");
}
const s = fs.readFileSync(cardPath, "utf8");
const cfg = fs.readFileSync(configPath, "utf8");

function must(cond, msg) {
  if (!cond) throw new Error(msg);
}
function count(text, needle) {
  return text.split(needle).length - 1;
}

must(count(s, "20260821-advance-month-r1") === 2, "new version marker must occur exactly twice");
must(s.includes('advance_entity: "input_number.elektrina_zaloha_mesic"'), "card must consume HA advance helper");
must(cfg.includes("  elektrina_zaloha_mesic:"), "HA advance helper missing");
const helperStart = cfg.indexOf("  elektrina_zaloha_mesic:");
const helperEnd = cfg.indexOf("\nutility_meter:", helperStart);
must(helperStart >= 0 && helperEnd > helperStart, "advance helper block bounds missing");
const helperBlock = cfg.slice(helperStart, helperEnd);
must(helperBlock.includes('name: "Elektřina - měsíční záloha"'), "advance helper friendly name missing");
must(helperBlock.includes('unit_of_measurement: "CZK"'), "advance helper unit missing");
must(!helperBlock.includes("initial:"), "advance helper must restore state instead of resetting on restart");

must(s.includes("projectionElapsedHours >= 48"), "forecast must have 48-hour early-month guard");
must(s.includes("projectionNow.getMonth() + 1"), "forecast must derive current calendar-month end dynamically");
must(s.includes("projectedMonthEnergy") && s.includes("/ projectionFraction"), "forecast must extrapolate month-to-date energy");
must(s.includes("Math.max(0, projectedMonthEnergy) * price + Math.max(0, fixedMonthly)"), "projected all-in cost must include fixed charge exactly once");
must(s.includes("projectedMonthCost > advanceMonthly + 1"), "forecast must only beat advance when actually higher");
must(s.includes("(overAdvance ? projectedMonthCost : advanceMonthly)"), "headline reference must use advance unless higher forecast wins");
must(s.includes('financeHeadlineLabel = a.finance.overAdvance') && s.includes('"Odhad měsíce"') && s.includes('"Záloha"'), "headline source must be explicit");
must(s.includes("rate-over"), "over-advance state must be visually distinguished");
must(s.includes("nad zálohu"), "over-advance delta must be visible");
must(s.includes("odhad měsíce po prvních 48 h"), "advance must stay baseline before forecast is credible");

must(s.includes("financeReferenceCost * tomasMonthRatio"), "Tomáš proportional money split missing");
must(s.includes("financeReferenceCost - tomasReferenceCost"), "parents split must be remainder so split sums to headline");
must(s.includes("Poměrné rozdělení stejné částky, která je nahoře"), "split semantics must explain same headline basis");
must(s.includes("Není to účetní saldo rodičů"), "card must not confuse monthly split with parent ledger settlement");
must(s.includes("aktuálním kalendářním měsíci"), "finance horizon must be current calendar month");

must(!s.includes("· vč. fixu"), "visible redundant vč. fixu must be removed");
must(s.includes("zahrnují společný měsíční fix právě jednou"), "tooltip must preserve all-in semantics");
must(count(s, "Math.max(0, projectedMonthEnergy) * price + Math.max(0, fixedMonthly)") === 1, "forecast fixed charge must be added exactly once");

const historyStart = s.indexOf('let historyHtml = ""');
const historyEnd = s.indexOf('this.shadowRoot.innerHTML = `', historyStart);
must(historyStart >= 0 && historyEnd > historyStart, "history render range missing");
const historyRender = s.slice(historyStart, historyEnd);
must(!historyRender.includes("a.history.longTomas"), "visible smart bar must not use long Tomáš estimate");
must(!historyRender.includes("a.history.longParents"), "visible smart bar must not use long parent estimate");
must(!historyRender.includes("26. 6. 2025"), "visible smart bar must not show archive date");
must(historyRender.includes("Tomáš ${this._fmt(smartTomasKwh, 1)} kWh"), "full Tomáš kWh label missing");
must(historyRender.includes("rodiče ${this._fmt(smartParentsKwh, 1)} kWh"), "full parents kWh label missing");
must(!historyRender.includes("<b>T ${this._fmt(smartTomasPct"), "T percent prefix must be removed");
must(!historyRender.includes("<b>R ${this._fmt(smartParentsPct"), "R percent prefix must be removed");
must(historyRender.includes("<b>${this._fmt(smartTomasPct, 0)} %</b>"), "Tomáš percent must remain");
must(historyRender.includes("<b>${this._fmt(smartParentsPct, 0)} %</b>"), "parents percent must remain");
must(s.includes("#ef6c00"), "parents original orange must stay");
must(s.includes("history_refresh_ms: 900000"), "15-minute smart history refresh must stay");
must(s.includes('history_start: "2026-08-20T15:00:00+02:00"'), "smart baseline must stay");

must(s.includes("configuredHistoryStart <= monthStart"), "future full months must automatically stop first-month backfill");
must(s.includes("!monthComplete") && s.includes("parentBeforeSmartEstimate"), "first smart month may retain finance-only backfill");
must(s.includes("const topLoads = a.loads.slice(0, 3);"), "top 3 loads must stay");
must(s.includes('class="monthline"'), "monthly energy line must stay");
must(s.includes('class="finance-split"'), "monthly money split line missing");

console.log("ENERGY_ADVANCE_MONTH_20260821_OK");
