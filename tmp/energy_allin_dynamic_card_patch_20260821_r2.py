#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_SHA256 = "628fdab2ff5dbc6bb50ea7727ede5fdbdcd8e94aa6ac613fbb613a4c092f109f"

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_energy_card_r2.py INPUT OUTPUT")

src_path = Path(sys.argv[1])
dst_path = Path(sys.argv[2])
raw = src_path.read_bytes()
actual = hashlib.sha256(raw).hexdigest()
if actual != EXPECTED_SHA256:
    raise SystemExit(f"LIVE_SHA_MISMATCH expected={EXPECTED_SHA256} actual={actual}")

text = raw.decode("utf-8")

def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}_COUNT={count}")
    text = text.replace(old, new, 1)

old_finance = '''    // Finance UX is deliberately all-in. For the partial first smart month,
    // estimate only the missing pre-smart parent consumption from the archived
    // long-term branch ratio, then combine it with actual smart parent kWh.
    const smartMonthTomas = Number(this._history?.tomas);
    const financeAnchorTomas = Number(c.historical_anchor_tomas_kwh);
    const financeAnchorParents = Number(c.historical_anchor_parents_kwh);
    const financeParentRatio = Number.isFinite(financeAnchorTomas) && financeAnchorTomas > 0
      && Number.isFinite(financeAnchorParents)
      ? Math.max(0, financeAnchorParents) / Math.max(0.001, financeAnchorTomas)
      : NaN;
    const rootBeforeSmart = !monthComplete && Number.isFinite(monthEnergy) && Number.isFinite(smartMonthTomas)
      ? Math.max(0, monthEnergy - Math.max(0, smartMonthTomas))
      : 0;
    const parentBeforeSmartEstimate = !monthComplete && Number.isFinite(financeParentRatio)
      ? rootBeforeSmart * financeParentRatio
      : 0;
    const parentMonthEnergy = Number.isFinite(parentMonthActual)
      ? Math.max(0, parentMonthActual) + parentBeforeSmartEstimate
      : NaN;
    const siteMonthEnergy = Number.isFinite(monthEnergy) && Number.isFinite(parentMonthEnergy)
      ? Math.max(0, monthEnergy) + Math.max(0, parentMonthEnergy)
      : NaN;
    const siteMonthCost = Number.isFinite(siteMonthEnergy) && Number.isFinite(price) && Number.isFinite(fixedMonthly)
      ? Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)
      : NaN;
    const effectivePrice = Number.isFinite(siteMonthCost) && Number.isFinite(siteMonthEnergy) && siteMonthEnergy > 0
      ? siteMonthCost / siteMonthEnergy
      : NaN;
    const costPerHour = Number.isFinite(sitePower) && Number.isFinite(effectivePrice)
      ? Math.max(0, sitePower) / 1000 * effectivePrice
      : NaN;
    const monthEstimated = !monthComplete && Number.isFinite(financeParentRatio)
      && Number.isFinite(parentMonthEnergy);
'''

new_finance = '''    // ENERGY_ALLIN_DYNAMIC_20260821_R2
    // Money uses measured energy only. Historical branch ratios remain useful
    // for the separate ratio visualisation, but never fabricate missing billed kWh.
    const parentMonthEnergy = Number.isFinite(parentMonthActual)
      ? Math.max(0, parentMonthActual)
      : NaN;
    const siteMonthEnergy = Number.isFinite(monthEnergy) && Number.isFinite(parentMonthEnergy)
      ? Math.max(0, monthEnergy) + Math.max(0, parentMonthEnergy)
      : NaN;

    // Spread the shared monthly non-kWh charges continuously through the actual
    // local calendar month. At the last instant of the month exactly 100 % has accrued.
    const nowDate = new Date();
    const monthStartDate = new Date(nowDate.getFullYear(), nowDate.getMonth(), 1);
    const nextMonthStartDate = new Date(nowDate.getFullYear(), nowDate.getMonth() + 1, 1);
    const monthDurationMs = nextMonthStartDate.getTime() - monthStartDate.getTime();
    const elapsedMonthMs = monthDurationMs > 0
      ? Math.max(0, Math.min(monthDurationMs, nowDate.getTime() - monthStartDate.getTime()))
      : NaN;
    const elapsedMonthFraction = Number.isFinite(elapsedMonthMs) && monthDurationMs > 0
      ? elapsedMonthMs / monthDurationMs
      : NaN;
    const hoursInMonth = monthDurationMs > 0 ? monthDurationMs / 3600000 : NaN;
    const fixedAccrued = Number.isFinite(fixedMonthly) && Number.isFinite(elapsedMonthFraction)
      ? Math.max(0, fixedMonthly) * elapsedMonthFraction
      : NaN;
    const fixedPerHour = Number.isFinite(fixedMonthly) && Number.isFinite(hoursInMonth) && hoursInMonth > 0
      ? Math.max(0, fixedMonthly) / hoursInMonth
      : NaN;

    // All visible monetary values are all-in. During the first partial parent
    // smart month the total is explicitly only the known measured minimum.
    const siteMonthCost = Number.isFinite(siteMonthEnergy) && Number.isFinite(price) && Number.isFinite(fixedAccrued)
      ? Math.max(0, siteMonthEnergy) * price + fixedAccrued
      : NaN;
    const effectivePrice = monthComplete && Number.isFinite(siteMonthCost)
      && Number.isFinite(siteMonthEnergy) && siteMonthEnergy > 0
      ? siteMonthCost / siteMonthEnergy
      : NaN;
    const costPerHour = Number.isFinite(sitePower) && Number.isFinite(price) && Number.isFinite(fixedPerHour)
      ? Math.max(0, sitePower) / 1000 * price + fixedPerHour
      : NaN;
    const monthEstimated = false;
'''
replace_once(old_finance, new_finance, "FINANCE_MODEL")

replace_once(
    '    const monthEnergyLabel = a.month.complete ? "Spotřeba měsíce" : "Odhad spotřeby";\n    const monthCostLabel = a.month.complete ? "Cena měsíce" : "Odhad ceny měsíce";',
    '    const monthEnergyLabel = a.month.complete ? "Spotřeba měsíce dosud" : "Známá spotřeba dosud";\n    const monthCostLabel = a.month.complete ? "Náklad měsíce dosud" : "Známý náklad dosud";',
    "MONTH_LABELS",
)

old_rate = '''    const rateDetail = Number.isFinite(a.effectivePrice)
      ? `${a.month.complete ? "konečná efektivní cena" : "odhad konečné efektivní ceny"} ${finalPriceText}`
      : "Konečná cena zatím není dostupná";
'''
new_rate = '''    const rateDetail = Number.isFinite(a.effectivePrice)
      ? `all-in cena dosud ${finalPriceText} · všechny účtované složky průběžně započítané`
      : (a.month.complete
        ? "All-in Kč/kWh zatím není dostupná"
        : "All-in Kč/kWh zatím nezobrazujeme: rodičovská větev nemá měření za celý měsíc");
'''
replace_once(old_rate, new_rate, "RATE_DETAIL")

replace_once(
    'title="Výsledná efektivní cena za kWh podle celkového měsíčního nákladu a spotřeby"',
    'title="Konečná all-in cena za kWh podle dosud naběhlého celkového nákladu a měřené spotřeby; zobrazí se až při úplném měření obou větví"',
    "EFFECTIVE_PRICE_TOOLTIP",
)
replace_once(
    '<small>Konečná cena</small>',
    '<small>Konečná Kč/kWh</small>',
    "EFFECTIVE_PRICE_LABEL",
)
replace_once(
    'title="${a.month.complete ? "Rodičovská větev má smart data za celý měsíc" : "Chybějící část rodičovské spotřeby je dopočtená z dlouhodobého poměru větví"}"',
    'title="${a.month.complete ? "Obě kořenové větve mají měření od začátku měsíce" : "První rodičovské smart měření začalo až 20. 8.; peníze chybějící období neodhadují"}"',
    "COVERAGE_TOOLTIP",
)
replace_once(
    'title="Celková spotřeba obou kořenových větví za měsíc; v prvním neúplném smart měsíci je rodičovská část dopočtená"',
    'title="Dosud změřená spotřeba obou kořenových větví; v prvním neúplném smart měsíci jde o známé minimum bez historického dopočtu"',
    "MONTH_ENERGY_TOOLTIP",
)
replace_once(
    'title="Výsledný celkový náklad za měsíc podle aktuálního cenového modelu; na kartě se jednotlivé tarifní složky nerozepisují"',
    'title="All-in náklad dosud ze změřené spotřeby a všech časově naběhlých účtovaných složek; tarifní rozpad se na kartě nezobrazuje"',
    "MONTH_COST_TOOLTIP",
)

for forbidden in (
    "parentBeforeSmartEstimate",
    "financeParentRatio",
    "rootBeforeSmart",
    "Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)",
    "Math.max(0, sitePower) / 1000 * effectivePrice",
    'const monthCostLabel = a.month.complete ? "Cena měsíce" : "Odhad ceny měsíce";',
    "Chybějící část rodičovské spotřeby je dopočtená",
    "rodičovská část dopočtená",
):
    if forbidden in text:
        raise SystemExit(f"FORBIDDEN_REMAINS={forbidden}")

required = (
    "ENERGY_ALLIN_DYNAMIC_20260821_R2",
    "const fixedAccrued =",
    "const fixedPerHour =",
    "const elapsedMonthFraction =",
    "new Date(nowDate.getFullYear(), nowDate.getMonth() + 1, 1)",
    "Math.max(0, siteMonthEnergy) * price + fixedAccrued",
    "Math.max(0, sitePower) / 1000 * price + fixedPerHour",
    "const effectivePrice = monthComplete &&",
    "const monthEstimated = false;",
    "Spotřeba měsíce dosud",
    "Známá spotřeba dosud",
    "Náklad měsíce dosud",
    "Známý náklad dosud",
    "Konečná Kč/kWh",
    "peníze chybějící období neodhadují",
    "známé minimum bez historického dopočtu",
)
for marker in required:
    if marker not in text:
        raise SystemExit(f"REQUIRED_MISSING={marker}")

dst_path.write_text(text, encoding="utf-8")
print(f"PATCH_OK old_sha={actual} new_sha={hashlib.sha256(text.encode('utf-8')).hexdigest()} bytes={len(text.encode('utf-8'))}")
