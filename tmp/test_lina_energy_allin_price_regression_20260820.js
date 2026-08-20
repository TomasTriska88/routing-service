const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const sourcePath = process.argv[2];
assert(sourcePath, 'card path argument required');
const src = fs.readFileSync(sourcePath, 'utf8');
let Card;
class HTMLElementStub {
  constructor() { this.dataset = {}; this.shadowRoot = null; }
  attachShadow() {
    this.shadowRoot = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    return this.shadowRoot;
  }
  dispatchEvent() {}
}
const sandbox = {
  console, HTMLElement: HTMLElementStub, CustomEvent: class {}, URLSearchParams,
  Intl, Date, Map, Math, Number, String, Array, Object, Promise, setTimeout, clearTimeout,
  window: { location: { search: '?kiosk' }, customCards: [] },
  customElements: { get: () => undefined, define: (name, cls) => { if (name === 'lina-energy-card') Card = cls; } },
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: sourcePath });
assert(Card, 'lina-energy-card class was not registered');

function cardWith(monthComplete, parentMonth) {
  const card = new Card();
  card.setConfig({
    root_power: 'sensor.root_power', root_current: 'sensor.root_current', root_voltage: 'sensor.root_voltage', root_energy: 'sensor.root_energy',
    parent_power: 'sensor.parent_power', parent_current: 'sensor.parent_current', parent_voltage: 'sensor.parent_voltage', parent_energy: 'sensor.parent_energy',
    price_entity: 'sensor.price', fixed_monthly: 'sensor.fixed', month_energy: 'sensor.root_month',
    historical_anchor_tomas_kwh: 4607, historical_anchor_parents_kwh: 2281,
    branches: [], child_loads: [],
  });
  card._hass = { states: {
    'sensor.root_power': { state: '1000' }, 'sensor.root_current': { state: '4.3' }, 'sensor.root_voltage': { state: '235' }, 'sensor.root_energy': { state: '10' },
    'sensor.parent_power': { state: '500' }, 'sensor.parent_current': { state: '2.2' }, 'sensor.parent_voltage': { state: '236' }, 'sensor.parent_energy': { state: '3' },
    'sensor.price': { state: '6' }, 'sensor.fixed': { state: '300' },
    'sensor.root_month': { state: '120', attributes: { unit_of_measurement: 'kWh' } },
  }};
  card._history = {
    loading: false, error: null,
    tomas: 20, parents: 10,
    parentMonth,
    monthComplete,
    monthFrom: Date.parse('2026-08-20T15:00:00+02:00'),
    from: Date.parse('2026-08-20T15:00:00+02:00'),
    to: Date.parse('2026-08-20T22:00:00+02:00'),
  };
  return card;
}

// First partial smart month: estimate only missing parent kWh from archived branch ratio.
let card = cardWith(false, 10);
let a = card._assess();
const parentRatio = 2281 / 4607;
const expectedParent = 10 + (120 - 20) * parentRatio;
const expectedTotal = 120 + expectedParent;
const expectedCost = expectedTotal * 6 + 300;
const expectedEffective = expectedCost / expectedTotal;
assert(Math.abs(a.month.parents - expectedParent) < 1e-9, 'partial parent month estimate mismatch');
assert(Math.abs(a.month.total - expectedTotal) < 1e-9, 'partial site month total mismatch');
assert(Math.abs(a.month.cost - expectedCost) < 1e-9, 'partial all-in month cost mismatch');
assert(Math.abs(a.effectivePrice - expectedEffective) < 1e-9, 'all-in effective price mismatch');
assert(Math.abs(a.costPerHour - 1.5 * expectedEffective) < 1e-9, 'current equivalent hourly cost must use all-in effective price');
assert.strictEqual(a.month.estimated, true, 'partial first month must be labeled estimated');

card._render(true);
let html = card.shadowRoot.innerHTML;
for (const marker of ['Konečná cena', 'Odhad spotřeby', 'Odhad ceny měsíce', 'Měsíční data', 'ODHAD', 'odhad konečné efektivní ceny']) {
  assert(html.includes(marker), `render marker missing: ${marker}`);
}
for (const forbidden of ['Fix / měsíc', 'bez měsíčního fixu', 'vč. fixu', '<small>Cena za kWh</small>', 'proměnná ·']) {
  assert(!html.includes(forbidden), `legacy tariff breakdown leaked into render: ${forbidden}`);
}

// Future complete smart month: no archival estimate should be added.
card = cardWith(true, 60);
a = card._assess();
assert.strictEqual(a.month.parents, 60, 'complete parent month must use actual smart month only');
assert.strictEqual(a.month.total, 180, 'complete site month total mismatch');
assert.strictEqual(a.month.cost, 1380, 'complete all-in month cost mismatch');
assert(Math.abs(a.effectivePrice - 1380 / 180) < 1e-9, 'complete all-in effective price mismatch');
assert.strictEqual(a.month.estimated, false, 'complete month must not be estimated');
card._render(true);
html = card.shadowRoot.innerHTML;
for (const marker of ['Konečná cena', 'Spotřeba měsíce', 'Cena měsíce', 'KOMPLETNÍ', 'konečná efektivní cena']) {
  assert(html.includes(marker), `complete render marker missing: ${marker}`);
}
for (const forbidden of ['Fix / měsíc', 'bez měsíčního fixu', 'vč. fixu', '<small>Cena za kWh</small>']) {
  assert(!html.includes(forbidden), `complete render leaked tariff breakdown: ${forbidden}`);
}

assert(src.includes('20260820-allin-price-r1'));
console.log('ENERGY_ALLIN_PRICE_REGRESSION_OK');
