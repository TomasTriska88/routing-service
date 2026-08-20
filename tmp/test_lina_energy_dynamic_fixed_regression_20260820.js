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

function currentMonthHours() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1).getTime();
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1).getTime();
  return (next - start) / 3600000;
}

// Partial first smart month: missing parent kWh are estimated, and standing charges
// are accrued only for elapsed calendar time rather than charged in full on day 1.
let card = cardWith(false, 10);
let a = card._assess();
const parentRatio = 2281 / 4607;
const expectedParent = 10 + (120 - 20) * parentRatio;
const expectedTotal = 120 + expectedParent;
const expectedFixedPerHour = 300 / currentMonthHours();
assert(Math.abs(a.month.parents - expectedParent) < 1e-9, 'partial parent month estimate mismatch');
assert(Math.abs(a.month.total - expectedTotal) < 1e-9, 'partial site month total mismatch');
assert(a.month.fixedAccrued >= 0 && a.month.fixedAccrued <= 300, 'accrued standing charge must stay within monthly charge');
assert(a.month.elapsedFraction >= 0 && a.month.elapsedFraction <= 1, 'elapsed month fraction out of range');
assert(Math.abs(a.fixedPerHour - expectedFixedPerHour) < 1e-9, 'standing charge hourly burn mismatch');
assert(Math.abs(a.month.cost - (expectedTotal * 6 + a.month.fixedAccrued)) < 1e-9, 'month-to-date all-in cost mismatch');
assert(Math.abs(a.effectivePrice - a.month.cost / expectedTotal) < 1e-9, 'dynamic all-in effective price mismatch');
assert(Math.abs(a.costPerHour - (1.5 * 6 + expectedFixedPerHour)) < 1e-9, 'live Kč/h must include dynamic standing charge burn rate');
assert.strictEqual(a.month.estimated, true, 'partial first month must be labeled estimated');

card._render(true);
let html = card.shadowRoot.innerHTML;
for (const marker of ['Konečná cena', 'Odhad spotřeby', 'Náklad měsíce dosud', 'Měsíční data', 'ODHAD', 'všechny poplatky průběžně započítané']) {
  assert(html.includes(marker), `render marker missing: ${marker}`);
}
for (const forbidden of ['Fix / měsíc', 'bez měsíčního fixu', 'vč. fixu', '<small>Cena za kWh</small>', 'proměnná ·', 'Odhad ceny měsíce']) {
  assert(!html.includes(forbidden), `legacy component pricing leaked into render: ${forbidden}`);
}

// Complete smart month coverage: actual parent kWh are used, but the current
// calendar month's standing charge still accrues continuously with time.
card = cardWith(true, 60);
a = card._assess();
assert.strictEqual(a.month.parents, 60, 'complete parent month must use actual smart month only');
assert.strictEqual(a.month.total, 180, 'complete site month total mismatch');
assert(Math.abs(a.month.cost - (180 * 6 + a.month.fixedAccrued)) < 1e-9, 'complete month-to-date all-in cost mismatch');
assert(Math.abs(a.effectivePrice - a.month.cost / 180) < 1e-9, 'complete dynamic all-in effective price mismatch');
assert(Math.abs(a.costPerHour - (1.5 * 6 + expectedFixedPerHour)) < 1e-9, 'complete live Kč/h must include standing charge burn rate');
assert.strictEqual(a.month.estimated, false, 'complete month must not be estimated');
card._render(true);
html = card.shadowRoot.innerHTML;
for (const marker of ['Konečná cena', 'Spotřeba měsíce', 'Náklad měsíce dosud', 'KOMPLETNÍ', 'všechny poplatky průběžně započítané']) {
  assert(html.includes(marker), `complete render marker missing: ${marker}`);
}
for (const forbidden of ['Fix / měsíc', 'bez měsíčního fixu', 'vč. fixu', '<small>Cena za kWh</small>', 'Odhad ceny měsíce']) {
  assert(!html.includes(forbidden), `complete render leaked component pricing: ${forbidden}`);
}

assert(src.includes('20260820-allin-dynamic-r2'));
assert(src.includes('fixedPerHour'));
assert(src.includes('fixedAccrued'));
console.log('ENERGY_DYNAMIC_FIXED_REGRESSION_OK');
