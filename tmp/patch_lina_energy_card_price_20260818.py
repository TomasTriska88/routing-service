from pathlib import Path

p = Path('/config/www/lina-energy-card.js')
s = p.read_text(encoding='utf-8')


def one(old: str, new: str, label: str) -> None:
    global s
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: expected 1 match, got {n}')
    s = s.replace(old, new, 1)


one(
    '      price_per_kwh: 7.21,\n',
    '      price_entity: "sensor.elektrina_aktualni_promena_cena",\n'
    '      instant_cost: "sensor.elektrina_okamzity_naklad",\n'
    '      month_energy: "sensor.elektrina_spotreba_tento_mesic",\n'
    '      month_cost: "sensor.elektrina_naklad_tento_mesic",\n'
    '      fixed_monthly: "sensor.elektrina_fixni_poplatky_mesic",\n',
    'pricing config',
)

one(
    '    const price = Number(c.price_per_kwh);\n'
    '    const costPerHour = Number.isFinite(power) && Number.isFinite(price)\n'
    '      ? Math.max(0, power) / 1000 * price\n'
    '      : NaN;\n',
    '    const price = this._num(c.price_entity, NaN);\n'
    '    const instantCost = this._num(c.instant_cost, NaN);\n'
    '    const costPerHour = Number.isFinite(instantCost)\n'
    '      ? instantCost\n'
    '      : (Number.isFinite(power) && Number.isFinite(price)\n'
    '          ? Math.max(0, power) / 1000 * price\n'
    '          : NaN);\n'
    '    const monthEnergy = this._num(c.month_energy, NaN);\n'
    '    const monthCost = this._num(c.month_cost, NaN);\n'
    '    const fixedMonthly = this._num(c.fixed_monthly, NaN);\n',
    'pricing assessment',
)

one(
    '    } else if (power >= 2000) {\n'
    '      issues.push({\n'
    '        level: 1,\n'
    '        icon: "⚡",\n'
    '        title: "Vyšší odběr",\n'
    '        text: `${this._powerText(power)} na kořenovém měření.`,\n'
    '        entity: c.root_power,\n'
    '      });\n'
    '    }\n\n'
    '    const loads =',
    '    } else if (power >= 2000) {\n'
    '      issues.push({\n'
    '        level: 1,\n'
    '        icon: "⚡",\n'
    '        title: "Vyšší odběr",\n'
    '        text: `${this._powerText(power)} na kořenovém měření.`,\n'
    '        entity: c.root_power,\n'
    '      });\n'
    '    }\n\n'
    '    if (!this._valid(c.price_entity) || !Number.isFinite(price)) {\n'
    '      issues.push({\n'
    '        level: 1,\n'
    '        icon: "💸",\n'
    '        title: "Cena elektřiny nemá data",\n'
    '        text: "Příkon je dostupný, ale finanční odhad teď není spolehlivý.",\n'
    '        entity: c.price_entity,\n'
    '      });\n'
    '    }\n\n'
    '    const loads =',
    'price issue',
)

one(
    '    return { power, voltage, energy, costPerHour, maxPower, issues, loads, status, percentage };\n',
    '    return { power, voltage, energy, price, costPerHour, monthEnergy, monthCost, fixedMonthly, maxPower, issues, loads, status, percentage };\n',
    'assessment return',
)

one(
    '      a.power, a.voltage, a.energy, a.costPerHour, a.status.cls, a.percentage,\n',
    '      a.power, a.voltage, a.energy, a.price, a.costPerHour, a.monthEnergy, a.monthCost, a.fixedMonthly, a.status.cls, a.percentage,\n',
    'render key',
)

one(
    '    const voltageText = Number.isFinite(a.voltage) ? `${this._fmt(a.voltage, 0)} V` : "—";\n'
    '    const costText = Number.isFinite(a.costPerHour)\n'
    '      ? `≈ ${this._fmt(a.costPerHour, a.costPerHour < 10 ? 2 : 1)} Kč/h`\n'
    '      : "—";\n',
    '    const voltageText = Number.isFinite(a.voltage) ? `${this._fmt(a.voltage, 0)} V` : "—";\n'
    '    const costText = Number.isFinite(a.costPerHour)\n'
    '      ? `≈ ${this._fmt(a.costPerHour, a.costPerHour < 10 ? 2 : 1)} Kč/h`\n'
    '      : "—";\n'
    '    const priceText = Number.isFinite(a.price) ? `${this._fmt(a.price, 2)} Kč/kWh` : "—";\n'
    '    const fixedText = Number.isFinite(a.fixedMonthly) ? `${this._fmt(a.fixedMonthly, 2)} Kč/měs.` : "—";\n'
    '    const monthEnergyUnit = this._st(c.month_energy)?.attributes?.unit_of_measurement || "kWh";\n'
    '    const monthEnergyText = Number.isFinite(a.monthEnergy)\n'
    '      ? `${this._fmt(a.monthEnergy, a.monthEnergy >= 100 ? 0 : 2)} ${monthEnergyUnit}`\n'
    '      : "—";\n'
    '    const monthCostText = Number.isFinite(a.monthCost)\n'
    '      ? `${this._fmt(a.monthCost, 2)} Kč`\n'
    '      : "—";\n'
    '    const rateDetail = Number.isFinite(a.price)\n'
    '      ? `${priceText} proměnná${Number.isFinite(a.fixedMonthly) ? ` · fix ${fixedText}` : ""}`\n'
    '      : "Cena není dostupná";\n',
    'display texts',
)

one(
    '          grid-template-columns:repeat(2,minmax(0,1fr));\n',
    '          grid-template-columns:repeat(4,minmax(0,1fr));\n',
    'meta desktop columns',
)

one(
    '          .hero { grid-template-columns:1fr; gap:5px; }\n'
    '          .rate { text-align:left; }\n',
    '          .hero { grid-template-columns:1fr; gap:5px; }\n'
    '          .rate { text-align:left; }\n'
    '          .meta { grid-template-columns:repeat(2,minmax(0,1fr)); }\n',
    'meta narrow columns',
)

one(
    '              <small>při současném odběru · ${this._fmt(Number(c.price_per_kwh), 2)} Kč/kWh</small>\n',
    '              <small>při současném odběru · ${this._esc(rateDetail)}</small>\n',
    'hero price detail',
)

one(
    '          <div class="meta">\n'
    '            <button data-entity="${this._esc(c.root_voltage)}"><small>Napětí</small><strong>${this._esc(voltageText)}</strong></button>\n'
    '            <button data-entity="${this._esc(c.root_energy)}"><small>Celkové měřidlo</small><strong>${this._esc(energyText)}</strong></button>\n'
    '          </div>\n',
    '          <div class="meta">\n'
    '            <button data-entity="${this._esc(c.root_voltage)}"><small>Napětí</small><strong>${this._esc(voltageText)}</strong></button>\n'
    '            <button data-entity="${this._esc(c.root_energy)}"><small>Celkové měřidlo</small><strong>${this._esc(energyText)}</strong></button>\n'
    '            <button data-entity="${this._esc(c.month_energy)}"><small>Tento měsíc</small><strong>${this._esc(monthEnergyText)}</strong></button>\n'
    '            <button data-entity="${this._esc(c.month_cost)}"><small>Odhad účtu vč. fixu</small><strong>${this._esc(monthCostText)}</strong></button>\n'
    '          </div>\n',
    'monthly meta',
)

if 'price_per_kwh: 7.21' in s or 'Number(c.price_per_kwh)' in s:
    raise RuntimeError('old hard-coded price still present')
for required in (
    'sensor.elektrina_aktualni_promena_cena',
    'sensor.elektrina_okamzity_naklad',
    'sensor.elektrina_spotreba_tento_mesic',
    'sensor.elektrina_naklad_tento_mesic',
    'sensor.elektrina_fixni_poplatky_mesic',
):
    if required not in s:
        raise RuntimeError(f'missing required entity: {required}')

marker = '// Energy pricing model: 20260818-v2\n'
if marker not in s:
    s = s.replace('// Markvarec TV typography profile: 20260818-tvread1\n', '// Markvarec TV typography profile: 20260818-tvread1\n' + marker, 1)

p.write_text(s, encoding='utf-8')
print('LINA_ENERGY_CARD_PRICE_PATCH_OK')
