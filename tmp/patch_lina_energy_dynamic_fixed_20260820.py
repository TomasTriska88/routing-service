from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding='utf-8')

def replace_once(old: str, new: str, label: str):
    global text
    count = text.count(old)
    if count != 1:
        raise AssertionError(f'{label}: expected exactly one match, got {count}')
    text = text.replace(old, new, 1)

replace_once('20260820-allin-price-r1', '20260820-allin-dynamic-r2', 'version marker')

old_finance = '''    const siteMonthCost = Number.isFinite(siteMonthEnergy) && Number.isFinite(price) && Number.isFinite(fixedMonthly)\n      ? Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)\n      : NaN;\n    const effectivePrice = Number.isFinite(siteMonthCost) && Number.isFinite(siteMonthEnergy) && siteMonthEnergy > 0\n      ? siteMonthCost / siteMonthEnergy\n      : NaN;\n    const costPerHour = Number.isFinite(sitePower) && Number.isFinite(effectivePrice)\n      ? Math.max(0, sitePower) / 1000 * effectivePrice\n      : NaN;\n    const monthEstimated = !monthComplete && Number.isFinite(financeParentRatio)\n      && Number.isFinite(parentMonthEnergy);\n'''
new_finance = '''    // Monthly standing charges are accrued continuously through the current\n    // calendar month. Every user-facing financial value is therefore all-in:\n    // the live Kč/h adds the standing-charge burn rate, while month-to-date\n    // cost and effective Kč/kWh include only the share accrued up to now.\n    const nowDate = new Date();\n    const monthStartMs = new Date(nowDate.getFullYear(), nowDate.getMonth(), 1).getTime();\n    const nextMonthStartMs = new Date(nowDate.getFullYear(), nowDate.getMonth() + 1, 1).getTime();\n    const monthDurationMs = Math.max(1, nextMonthStartMs - monthStartMs);\n    const elapsedMonthMs = Math.max(0, Math.min(monthDurationMs, nowDate.getTime() - monthStartMs));\n    const elapsedMonthFraction = elapsedMonthMs / monthDurationMs;\n    const fixedAccrued = Number.isFinite(fixedMonthly)\n      ? Math.max(0, fixedMonthly) * elapsedMonthFraction\n      : NaN;\n    const fixedPerHour = Number.isFinite(fixedMonthly)\n      ? Math.max(0, fixedMonthly) / (monthDurationMs / 3600000)\n      : NaN;\n    const siteMonthCost = Number.isFinite(siteMonthEnergy) && Number.isFinite(price) && Number.isFinite(fixedAccrued)\n      ? Math.max(0, siteMonthEnergy) * price + fixedAccrued\n      : NaN;\n    const effectivePrice = Number.isFinite(siteMonthCost) && Number.isFinite(siteMonthEnergy) && siteMonthEnergy > 0\n      ? siteMonthCost / siteMonthEnergy\n      : NaN;\n    const costPerHour = Number.isFinite(sitePower) && Number.isFinite(price) && Number.isFinite(fixedPerHour)\n      ? Math.max(0, sitePower) / 1000 * price + fixedPerHour\n      : NaN;\n    const monthEstimated = !monthComplete && Number.isFinite(financeParentRatio)\n      && Number.isFinite(parentMonthEnergy);\n'''
replace_once(old_finance, new_finance, 'dynamic standing charge block')

old_return = '''      price, effectivePrice, costPerHour, monthEnergy, fixedMonthly,\n      month: {\n        parents: parentMonthEnergy,\n        total: siteMonthEnergy,\n        cost: siteMonthCost,\n        effectivePrice,\n        complete: monthComplete,\n        estimated: monthEstimated,\n        from: this._history?.monthFrom ?? null,\n      },\n'''
new_return = '''      price, effectivePrice, costPerHour, monthEnergy, fixedMonthly, fixedPerHour,\n      month: {\n        parents: parentMonthEnergy,\n        total: siteMonthEnergy,\n        cost: siteMonthCost,\n        effectivePrice,\n        fixedAccrued,\n        elapsedFraction: elapsedMonthFraction,\n        complete: monthComplete,\n        estimated: monthEstimated,\n        from: this._history?.monthFrom ?? null,\n      },\n'''
replace_once(old_return, new_return, 'return dynamic standing charge fields')

old_key = '''      a.sitePower, a.siteCurrent, a.price, a.effectivePrice, a.costPerHour,\n      a.monthEnergy, a.fixedMonthly, a.month.parents, a.month.total, a.month.cost, a.month.complete, a.month.estimated,\n'''
new_key = '''      a.sitePower, a.siteCurrent, a.price, a.effectivePrice, a.costPerHour, a.fixedPerHour,\n      a.monthEnergy, a.fixedMonthly, a.month.parents, a.month.total, a.month.cost, a.month.fixedAccrued, a.month.elapsedFraction, a.month.complete, a.month.estimated,\n'''
replace_once(old_key, new_key, 'render key dynamic standing charge fields')

old_labels = '''    const monthEnergyLabel = a.month.complete ? "Spotřeba měsíce" : "Odhad spotřeby";\n    const monthCostLabel = a.month.complete ? "Cena měsíce" : "Odhad ceny měsíce";\n    const coverageText = a.month.complete ? "KOMPLETNÍ" : (a.month.estimated ? "ODHAD" : "NEÚPLNÉ");\n\n    const rateDetail = Number.isFinite(a.effectivePrice)\n      ? `${a.month.complete ? "konečná efektivní cena" : "odhad konečné efektivní ceny"} ${finalPriceText}`\n      : "Konečná cena zatím není dostupná";\n'''
new_labels = '''    const monthEnergyLabel = a.month.complete ? "Spotřeba měsíce" : "Odhad spotřeby";\n    const monthCostLabel = "Náklad měsíce dosud";\n    const coverageText = a.month.complete ? "KOMPLETNÍ" : (a.month.estimated ? "ODHAD" : "NEÚPLNÉ");\n\n    const rateDetail = Number.isFinite(a.effectivePrice)\n      ? `všechny poplatky průběžně započítané · ${finalPriceText}`\n      : "Výsledná cena zatím není dostupná";\n'''
replace_once(old_labels, new_labels, 'all-in visible labels')

old_cost_button = '''            <button title="Výsledný celkový náklad za měsíc podle aktuálního cenového modelu; na kartě se jednotlivé tarifní složky nerozepisují">\n              <small>${this._esc(monthCostLabel)}</small>\n              <strong>${this._esc(monthCostText)}</strong>\n            </button>\n'''
new_cost_button = '''            <button title="Celkový náklad od začátku měsíce do této chvíle; všechny pravidelné i spotřební složky se započítávají průběžně">\n              <small>${this._esc(monthCostLabel)}</small>\n              <strong>${this._esc(monthCostText)}</strong>\n            </button>\n'''
replace_once(old_cost_button, new_cost_button, 'month-to-date cost title')

# User-visible finance copy must never fall back to a component breakdown.
for forbidden in ('Fix / měsíc', 'bez měsíčního fixu', 'vč. fixu', 'proměnná ·', 'Odhad ceny měsíce', '<small>Cena za kWh</small>'):
    if forbidden in text:
        raise AssertionError(f'visible legacy finance copy remains: {forbidden}')

path.write_text(text, encoding='utf-8')
print(f'ENERGY_DYNAMIC_FIXED_PATCH_OK bytes={len(text.encode("utf-8"))}')
