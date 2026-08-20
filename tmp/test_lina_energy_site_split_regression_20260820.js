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
assert.strictEqual(card.getGridOptions().rows, 6, 'expanded card must reserve six grid rows');

(async () => {
  await card._refreshHistory(true);
  a = card._assess();
  assert.strictEqual(a.history.tomas, 3, 'Tomáš history must use Recorder sum delta');
  assert.strictEqual(a.history.parents, 1, 'parent history must use Recorder sum delta');
  assert.strictEqual(Math.round(a.history.tomasPct), 75);
  assert.strictEqual(Math.round(a.history.parentsPct), 25);
  card._render(true);
  const html = card.shadowRoot.innerHTML;
  for (const marker of [
    'Markvarec celkem', 'Tomáš', 'Rodiče', 'Společný přívod', '25 A', '16 A',
    'Spotřeba Tomáš × Rodiče', 'Tomáš tento měsíc', 'Tomáš + fix', 'Technická (odhad)',
  ]) assert(html.includes(marker), `render marker missing: ${marker}`);
  assert(src.includes('recorder/statistics_during_period'));
  assert(src.includes('types: ["sum"]'));
  assert(src.includes('history_start: "2026-08-20T15:00:00+02:00"'));
  console.log('ENERGY_SITE_SPLIT_REGRESSION_OK');
})().catch(err => { console.error(err); process.exit(1); });
