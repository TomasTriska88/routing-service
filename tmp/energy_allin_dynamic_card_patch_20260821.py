#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_SHA256 = "628fdab2ff5dbc6bb50ea7727ede5fdbdcd8e94aa6ac613fbb613a4c092f109f"
OLD_VERSION = "20260820-cost-visibility-r1"
NEW_VERSION = "20260821-allin-dynamic-r1"

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_energy_card.py INPUT OUTPUT")

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

replace_once(
    OLD_VERSION,
    NEW_VERSION,
    "VERSION_ANCHOR",
)

old_finance = '''    const siteMonthCost = Number.isFinite(siteMonthEnergy) && Number.isFinite(price) && Number.isFinite(fixedMonthly)
      ? Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)
      : NaN;
    const effectivePrice = Number.isFinite(siteMonthCost) && Number.isFinite(siteMonthEnergy) && siteMonthEnergy > 0
      ? siteMonthCost / siteMonthEnergy
      : NaN;
    const costPerHour = Number.isFinite(sitePower) && Number.isFinite(effectivePrice)
      ? Math.max(0, sitePower) / 1000 * effectivePrice
      : NaN;
'''
new_finance = '''    // Accrue the shared monthly fixed charge continuously through the actual
    // local calendar month. This avoids showing the whole monthly fixed fee
    // on day one while keeping the live Kč/h number genuinely all-in.
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
    const siteMonthCost = Number.isFinite(siteMonthEnergy) && Number.isFinite(price) && Number.isFinite(fixedAccrued)
      ? Math.max(0, siteMonthEnergy) * price + fixedAccrued
      : NaN;
    const effectivePrice = Number.isFinite(siteMonthCost) && Number.isFinite(siteMonthEnergy) && siteMonthEnergy > 0
      ? siteMonthCost / siteMonthEnergy
      : NaN;
    const costPerHour = Number.isFinite(sitePower) && Number.isFinite(price) && Number.isFinite(fixedPerHour)
      ? Math.max(0, sitePower) / 1000 * price + fixedPerHour
      : NaN;
'''
replace_once(old_finance, new_finance, "FINANCE_BLOCK")

replace_once(
    '    const monthCostLabel = a.month.complete ? "Cena měsíce" : "Odhad ceny měsíce";',
    '    const monthCostLabel = a.month.complete ? "Náklad měsíce dosud" : "Odhad nákladu dosud";',
    "MONTH_COST_LABEL",
)

old_rate = '''    const rateDetail = Number.isFinite(a.effectivePrice)
      ? `${a.month.complete ? "konečná efektivní cena" : "odhad konečné efektivní ceny"} ${finalPriceText}`
      : "Konečná cena zatím není dostupná";
'''
new_rate = '''    const rateDetail = Number.isFinite(a.effectivePrice)
      ? `proměnná spotřeba + průběžný podíl fixu · efektivně dosud ${finalPriceText}`
      : "Průběžná all-in cena zatím není dostupná";
'''
replace_once(old_rate, new_rate, "RATE_DETAIL")

replace_once(
    'title="Výsledná efektivní cena za kWh podle celkového měsíčního nákladu a spotřeby"',
    'title="Průběžná efektivní cena za kWh podle dosud naběhlého nákladu a spotřeby"',
    "EFFECTIVE_PRICE_TOOLTIP",
)
replace_once(
    '<small>Konečná cena</small>',
    '<small>Efektivně dosud</small>',
    "EFFECTIVE_PRICE_LABEL",
)
replace_once(
    'title="Výsledný celkový náklad za měsíc podle aktuálního cenového modelu; na kartě se jednotlivé tarifní složky nerozepisují"',
    'title="Náklad obou větví od začátku měsíce; fixní měsíční poplatky se započítávají jen poměrně podle dosud uplynulého času"',
    "MONTH_COST_TOOLTIP",
)

if "společná cena včetně fixu." in text:
    replace_once(
        "společná cena včetně fixu.",
        "průběžná all-in cena s časově nabíhajícím podílem fixu.",
        "DESCRIPTION_PRICE_WORDING",
    )

for forbidden in (
    "Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)",
    "Math.max(0, sitePower) / 1000 * effectivePrice",
    'const monthCostLabel = a.month.complete ? "Cena měsíce" : "Odhad ceny měsíce";',
    "konečná efektivní cena",
    "odhad konečné efektivní ceny",
):
    if forbidden in text:
        raise SystemExit(f"FORBIDDEN_REMAINS={forbidden}")

required = (
    NEW_VERSION,
    "const fixedAccrued =",
    "const fixedPerHour =",
    "new Date(nowDate.getFullYear(), nowDate.getMonth() + 1, 1)",
    "Math.max(0, siteMonthEnergy) * price + fixedAccrued",
    "Math.max(0, sitePower) / 1000 * price + fixedPerHour",
    "Náklad měsíce dosud",
    "Odhad nákladu dosud",
    "proměnná spotřeba + průběžný podíl fixu",
    "Efektivně dosud",
)
for marker in required:
    if marker not in text:
        raise SystemExit(f"REQUIRED_MISSING={marker}")

dst_path.write_text(text, encoding="utf-8")
print(f"PATCH_OK old_sha={actual} new_sha={hashlib.sha256(text.encode('utf-8')).hexdigest()} bytes={len(text.encode('utf-8'))}")
