#!/usr/bin/env node
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");

function ok(cond, msg) {
  if (!cond) throw new Error(msg);
}

ok((src.match(/20260821-smart-sharebar-r2/g) || []).length === 2, "r2 version marker missing");
const parentBlock = src.match(/\.smart-sharebar-parents\s*\{[^}]*\}/s)?.[0] || "";
ok(parentBlock.includes("background:#ef6c00;"), "parents segment must keep original orange #ef6c00");
ok(parentBlock.includes("color:#fff;"), "parents segment must use readable white text");
ok(!parentBlock.includes("secondary-text-color"), "parents segment must not regress to theme secondary/black-ish color");

ok(
  src.includes('const monthCostLabel = a.month.complete ? "Markvarec · měsíc celkem" : "Markvarec · odhad celkem";'),
  "all-in label must explicitly say Markvarec"
);
ok(
  src.includes("Math.max(0, monthEnergy) + Math.max(0, parentMonthEnergy)"),
  "site month energy must combine Tomáš + parents"
);
ok(
  src.includes("Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)"),
  "site month cost must add the shared fixed charge exactly once"
);
ok(
  src.includes("const refreshMs = Math.max(60000, Number(this._config.history_refresh_ms) || 900000);"),
  "smart history refresh contract must remain 15 minutes by default"
);
ok(src.includes('class="smart-sharebar"'), "smart share bar missing");
ok(src.includes("const smartTomasPct = Number(a.history.tomasPct);"), "visible share must use smart Tomáš history");
ok(src.includes("const smartParentsPct = Number(a.history.parentsPct);"), "visible share must use smart parent history");

console.log("ENERGY_SHAREBAR_IDENTITY_20260821_OK");
