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

const card = new Card();
card.setConfig({ branches: [
  { entity: 'sensor.loznicovy_rozvadec_vykon', name: 'Ložnice', icon: 'x' },
  { entity: 'sensor.technicka_rozvadec_provizorni_vykon', name: 'Technická (odhad)', icon: 'x' },
  { entity: 'sensor.jezirko_rozvadec_vykon', name: 'Jezírko', icon: 'x' },
]});
const states = {
  'sensor.vnitrni_rozvadec_vykon': { state: '1000' },
  'sensor.vnitrni_rozvadec_proud': { state: '4.3' },
  'sensor.vnitrni_rozvadec_napeti': { state: '235' },
  'sensor.vnitrni_rozvadec_celkova_energie': { state: '0.1' },
  'sensor.rodicovsky_rozvadec_vykon': { state: '500' },
  'sensor.rodicovsky_rozvadec_proud': { state: '2.2' },
  'sensor.rodicovsky_rozvadec_napeti': { state: '236' },
  'sensor.rodicovsky_rozvadec_celkova_energie': { state: '0.2' },
  'sensor.elektrina_aktualni_promena_cena': { state: '6' },
  'sensor.elektrina_spotreba_tento_mesic': { state: '123', attributes: { unit_of_measurement: 'kWh' } },
  'sensor.elektrina_naklad_tento_mesic': { state: '1000' },
  'sensor.elektrina_fixni_poplatky_mesic': { state: '302' },
  'sensor.loznicovy_rozvadec_vykon': { state: '200' },
  'sensor.technicka_rozvadec_provizorni_vykon': { state: '300' },
  'sensor.jezirko_rozvadec_vykon': { state: '100' },
  'sensor.primotop_v_loznici_vykon': { state: '800' },
  'sensor.sonoff_s60zbtpf_vykon': { state: '40' },
  'sensor.zahrada_cerpadlo_destovka_vykon': { state: '0' },
  'sensor.loznice_vetrak_vykon': { state: '5' },
  'sensor.vanocni_osvetleni_vykon': { state: '4' },
  'sensor.loznice_ostatni_vykon': { state: '10' },
  'sensor.voliera_reflektor_vykon': { state: '3' },
};
const starts = [1787230800000, 1787234400000, 1787238000000];
card._hass = {
  states,
  callWS: async payload => {
    assert.strictEqual(payload.type, 'recorder/statistics_during_period');
    assert.strictEqual(payload.period, 'hour');
    assert.deepStrictEqual(Array.from(payload.types), ['sum']);
    assert.strictEqual(payload.start_time, '2026-08-20T15:00:00+02:00');
    return {
      'sensor.vnitrni_rozvadec_celkova_energie': [
        { start: starts[0], sum: 100 }, { start: starts[1], sum: 101 }, { start: starts[2], sum: 103 },
      ],
      'sensor.rodicovsky_rozvadec_celkova_energie': [
        { start: starts[0], sum: 10 }, { start: starts[1], sum: 10.5 }, { start: starts[2], sum: 11 },
      ],
    };
  },
};
let a = card._assess();
assert.strictEqual(a.sitePower, 1500, 'site power must be root + parent');
assert(Math.abs(a.siteCurrent - 6.5) < 1e-9, 'site current must be root + parent');
assert.strictEqual(a.siteLimitA, 25, 'shared feed limit must be 25 A');
assert.strictEqual(a.branchLimitA, 16, 'branch limit must be 16 A');
assert.strictEqual(card._utilClass(20), 'util-ok');
assert.strictEqual(card._utilClass(60), 'util-watch');
assert.strictEqual(card._utilClass(80), 'util-high');
assert.strictEqual(card._utilClass(90), 'util-critical');

(async () => {
  await card._refreshHistory(true);
  card._history.parentMonth = 1;
  card._history.monthComplete = false;
  a = card._assess();
  assert.strictEqual(a.history.tomas, 3, 'Tomáš smart history must use Recorder sum delta');
  assert.strictEqual(a.history.parents, 1, 'parent smart history must use Recorder sum delta');
  assert.strictEqual(Math.round(a.history.tomasPct), 75);
  assert.strictEqual(Math.round(a.history.parentsPct), 25);
  assert.strictEqual(a.history.longTomas, 4610, 'archive anchor + smart Tomáš delta');
  assert.strictEqual(a.history.longParents, 2282, 'archive anchor + smart parent delta');
  assert.strictEqual(a.month.total, 124, 'known month total must add Tomáš month helper + parent smart month');
  assert.strictEqual(a.month.cost, 1046, 'month cost must be variable known consumption + exactly one fixed monthly fee');
  card._render(true);
  const html = card.shadowRoot.innerHTML;
  for (const marker of [
    'Markvarec celkem', 'Tomáš', 'Rodiče', 'Společný přívod', '25 A', '16 A',
    '235 V', '236 V', 'Dlouhodobý odhad poměru', 'archiv + smart', 'Smart od 20. 8.',
    'Známé minimum měsíce', 'Min. cena vč. fixu', 'Fix / měsíc', 'Cena za kWh', 'Technická (odhad)',
    'bez měsíčního fixu',
  ]) assert(html.includes(marker), `render marker missing: ${marker}`);
  for (const oldMarker of ['Napětí Tomáš', 'Tomáš tento měsíc', 'Tomáš + fix']) {
    assert(!html.includes(oldMarker), `obsolete asymmetric marker must be absent: ${oldMarker}`);
  }
  for (const marker of [
    'util-ok', 'util-watch', 'util-high', 'util-critical',
    '#1565c0', '#ef6c00',
    'historical_anchor_tomas_kwh: 4607', 'historical_anchor_parents_kwh: 2281',
    'siteMonthEnergy) * price + Math.max(0, fixedMonthly)',
  ]) assert(src.includes(marker), `source marker missing: ${marker}`);
  console.log('ENERGY_COST_VISIBILITY_REGRESSION_OK');
})().catch(err => { console.error(err); process.exit(1); });
