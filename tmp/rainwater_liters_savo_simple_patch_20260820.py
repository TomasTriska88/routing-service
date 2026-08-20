from pathlib import Path
import hashlib
import shutil

CARD = Path("/config/www/lina-rainwater-card.js")
VISUAL = Path("/config/tests/test_rainwater_visual_semantics_regression.py")
PUMP = Path("/config/tests/test_rainwater_pump_proxy_regression.py")
LITERS = Path("/config/tests/test_rainwater_liters_only_regression.py")

EXPECTED_CARD_SHA = "b99fb2775540183227599fae5c4b9d3ab888ff27114b3615ddddb287f8c13efc"
STAMP = "20260820-2338-liters-savo-simple"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

actual = sha(CARD)
if actual != EXPECTED_CARD_SHA:
    raise SystemExit(f"STALE_CARD expected={EXPECTED_CARD_SHA} actual={actual}")

for p in (CARD, VISUAL, PUMP):
    if p.exists():
        shutil.copy2(p, p.with_name(p.name + f".bak-{STAMP}"))
if LITERS.exists():
    shutil.copy2(LITERS, LITERS.with_name(LITERS.name + f".bak-{STAMP}"))

card = CARD.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global card
    count = card.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, got {count}")
    card = card.replace(old, new, 1)

for line, label in [
    ('    const rain7 = this._num("sensor.destovka_srazky_7_dni", null);\n', "rain7 read"),
    ('    const rain3 = this._num("sensor.destovka_predpoved_srazek_3_dny", null);\n', "rain3 read"),
    ('    const rain5 = this._num("sensor.destovka_predpoved_srazek_5_dni", null);\n', "rain5 read"),
    ('    const yieldPerMm = this._num("input_number.destovka_zisk_l_na_mm", null);\n', "yield read"),
    ('    const savoInflow = this._num("input_number.destovka_savo_pritok_od_davky_l", null);\n', "savo inflow read"),
    ('    const savoCheckDays = this._num("input_number.destovka_savo_kontrola_dni", 7);\n', "savo days read"),
    ('    const savoDilutionLimit = this._num("input_number.destovka_savo_kontrola_redeni_pct", 25);\n', "savo dilution read"),
]:
    replace_once(line, "", label)

old = '''      level, recommendation, message, savoRecommendation, savoMessage, savoAgeDays, savoInflow, savoCheckDays, savoDilutionLimit,
      days, free, rain7, inflow7, rain3, inflow3, rain5, inflow5, projected5, release, known, dose, doseVolume, doseTime,
      doseNote, comfort, pump, pumpPower, flowEstimate, use, yieldPerMm, pondFouling, pondCleaning, pondPower
'''
new = '''      level, recommendation, message, savoRecommendation, savoMessage, savoAgeDays,
      days, free, inflow7, inflow3, inflow5, projected5, release, known, dose, doseVolume, doseTime,
      doseNote, comfort, pump, pumpPower, flowEstimate, use, pondFouling, pondCleaning, pondPower
'''
replace_once(old, new, "render key")

start = card.index("    // Exact dose time is unknown.")
end = card.index("    const flowLabel =", start)
simple_savo = r'''    // Exact dose time is unknown. Preserve the user's approximate age as an
    // interval, but keep the TV card decision-first: state, reason, age. No
    // chlorine/dilution math is shown when the dose is not known precisely.
    const savoApproxEarliestTs = Date.parse("2026-08-13T22:00:00+02:00");
    const savoApproxLatestTs = Date.parse("2026-08-16T22:00:00+02:00");
    const nowMs = Date.now();
    const savoApproxAgeMin = !known && Number.isFinite(savoApproxLatestTs) ? Math.max(0, (nowMs - savoApproxLatestTs) / 86400000) : null;
    const savoApproxAgeMax = !known && Number.isFinite(savoApproxEarliestTs) ? Math.max(0, (nowMs - savoApproxEarliestTs) / 86400000) : null;
    const exactAgeAvailable = known && Number.isFinite(savoAgeDays);
    const approxAgeAvailable = !known && Number.isFinite(savoApproxAgeMin) && Number.isFinite(savoApproxAgeMax);
    const savoAgeSummary = exactAgeAvailable
      ? `${savoAgeDays.toFixed(1)} d od dávky`
      : approxAgeAvailable
        ? `cca ${savoApproxAgeMin.toFixed(0)}–${savoApproxAgeMax.toFixed(0)} dní od dávky`
        : "čas dávky neznámý";
    const savoReason = !known
      ? "dávka není přesně známá"
      : /ZKONTROLOVAT/i.test(savoRecommendation)
        ? "zkontroluj vodu před další dávkou"
        : /NEPŘIDÁVAT/i.test(savoRecommendation)
          ? "další dávku teď nepřidávej"
          : "dávka je evidovaná";

'''
card = card[:start] + simple_savo + card[end:]

replace_once(
    '    const yieldLabel = Number.isFinite(yieldPerMm) ? `≈${yieldPerMm.toFixed(0)} l/mm` : "—";\n',
    "",
    "yield label",
)

replace_once(
    '      stat("🌧️", `${this._fmt(rain7, 1, " mm")} → ${this._fmt(inflow7, 0, " l")}`, "posledních 7 dní", "sensor.destovka_srazky_7_dni"),\n',
    '      stat("💧", this._fmt(inflow7, 0, " l"), "přiteklo za 7 dní", "sensor.destovka_pritok_7_dni"),\n',
    "7d stat",
)

old_rain = '''          <div class="section-title">déšť → nádrž</div>
          <div class="rain-grid">
            <div class="rain-box" data-entity="sensor.destovka_predpoved_srazek_3_dny">
              <div class="rain-top"><strong>🌧️ 3 dny</strong><b>${this._fmt(rain3,1," mm")}</b></div>
              <small>očekávaný přítok ≈ ${this._fmt(inflow3,0," l")}</small>
            </div>
            <div class="rain-box" data-entity="sensor.destovka_predpoved_srazek_5_dni">
              <div class="rain-top"><strong>🌧️ 5 dní</strong><b>${this._fmt(rain5,1," mm")}</b></div>
              <small>očekávaný přítok ≈ ${this._fmt(inflow5,0," l")}</small>
            </div>
          </div>
'''
new_rain = '''          <div class="section-title">očekávaný přítok do nádrže</div>
          <div class="rain-grid">
            <div class="rain-box" data-entity="sensor.destovka_ocekavany_pritok_3_dny">
              <div class="rain-top"><strong>💧 3 dny</strong><b>≈ ${this._fmt(inflow3,0," l")}</b></div>
              <small>kolik vody má přibýt</small>
            </div>
            <div class="rain-box" data-entity="sensor.destovka_ocekavany_pritok_5_dni">
              <div class="rain-top"><strong>💧 5 dní</strong><b>≈ ${this._fmt(inflow5,0," l")}</b></div>
              <small>kolik vody má přibýt</small>
            </div>
          </div>
'''
replace_once(old_rain, new_rain, "rain boxes")

old_css = '''        .savo-dose { padding:3px 6px; border-radius:999px; font-size:10px; font-weight:800; white-space:nowrap; background:rgba(127,127,127,.10); }
        .savo-card.caution { background:rgba(255,193,7,.08); border-color:rgba(255,193,7,.16); }
        .savo-card.check { background:rgba(255,152,0,.10); border-color:rgba(255,152,0,.20); }
        .savo-card.ok { background:rgba(76,175,80,.08); border-color:rgba(76,175,80,.16); }
        .savo-card.caution .savo-icon,.savo-card.check .savo-icon { background:rgba(255,193,7,.18); }
        .savo-card.ok .savo-icon { background:rgba(76,175,80,.16); }
        .savo-meters { display:grid; gap:6px; }
        .savo-meter { display:grid; grid-template-columns:18px minmax(0,1fr) auto; gap:6px; align-items:center; min-width:0; }
        .savo-meter > span { font-size:15px; }
        .meter-copy { min-width:0; }
        .meter-head { display:flex; justify-content:space-between; gap:5px; align-items:baseline; font-size:10px; line-height:1; margin-bottom:3px; }
        .meter-head span { opacity:.68; text-transform:uppercase; letter-spacing:.05em; }
        .meter-track { height:6px; border-radius:999px; overflow:hidden; background:rgba(127,127,127,.16); }
        .meter-fill { height:100%; width:var(--p); border-radius:inherit; background:linear-gradient(90deg,rgba(76,175,80,.72),rgba(255,193,7,.86)); }
        .savo-meter b { font-size:10px; white-space:nowrap; font-variant-numeric:tabular-nums; }
        .savo-meter.unknown .meter-track { background:repeating-linear-gradient(135deg,rgba(127,127,127,.20) 0 5px,rgba(127,127,127,.08) 5px 10px); }
        .savo-meter.unknown .meter-fill { display:none; }
'''
new_css = '''        .savo-card.caution { background:rgba(255,193,7,.08); border-color:rgba(255,193,7,.16); }
        .savo-card.check { background:rgba(255,152,0,.10); border-color:rgba(255,152,0,.20); }
        .savo-card.ok { background:rgba(76,175,80,.08); border-color:rgba(76,175,80,.16); }
        .savo-card.caution .savo-icon,.savo-card.check .savo-icon { background:rgba(255,193,7,.18); }
        .savo-card.ok .savo-icon { background:rgba(76,175,80,.16); }
        .savo-reason { font-size:13px; line-height:1.2; font-weight:750; }
        .savo-age { display:flex; align-items:center; gap:5px; font-size:11px; line-height:1.2; opacity:.72; }
'''
replace_once(old_css, new_css, "savo css")

old_html = '''            <div class="quality savo-card ${this._esc(savoView.cls)}" data-entity="sensor.destovka_savo_doporuceni" title="${this._esc(savoMessage)}">
              <div class="savo-head">
                <div class="savo-icon">🧴${this._esc(savoView.icon)}</div>
                <div class="savo-title"><small>Savo</small><strong>${this._esc(savoView.label)}</strong></div>
                <div class="savo-dose">${known && Number.isFinite(dose) ? `${dose.toFixed(0)} ml` : "dávka ?"}</div>
              </div>
              <div class="savo-meters">
                <div class="savo-meter ${savoAgeKnown ? "" : "unknown"}">
                  <span>⏱</span>
                  <div class="meter-copy"><div class="meter-head"><span>čas od dávky</span></div><div class="meter-track"><div class="meter-fill" style="--p:${savoAgePct.toFixed(1)}%"></div></div></div>
                  <b>${this._esc(ageLabel)}</b>
                </div>
                <div class="savo-meter ${dilutionKnown ? "" : "unknown"}">
                  <span>🌧</span>
                  <div class="meter-copy"><div class="meter-head"><span>naředění</span></div><div class="meter-track"><div class="meter-fill" style="--p:${dilutionMeterPct.toFixed(1)}%"></div></div></div>
                  <b>${this._esc(dilutionLabel)}</b>
                </div>
              </div>
            </div>
'''
new_html = '''            <div class="quality savo-card ${this._esc(savoView.cls)}" data-entity="sensor.destovka_savo_doporuceni" title="${this._esc(savoMessage)}">
              <div class="savo-head">
                <div class="savo-icon">🧴${this._esc(savoView.icon)}</div>
                <div class="savo-title"><small>Savo</small><strong>${this._esc(savoView.label)}</strong></div>
              </div>
              <div class="savo-reason">${this._esc(savoReason)}</div>
              <div class="savo-age"><span>🕒</span><span>${this._esc(savoAgeSummary)}</span></div>
            </div>
'''
replace_once(old_html, new_html, "savo html")

replace_once(
    ':host([data-tv-kiosk="1"]) .savo-dose { font-size:11px; }\n',
    ':host([data-tv-kiosk="1"]) .savo-reason { font-size:14px; }\n',
    "tv savo dose",
)
replace_once(
    ':host([data-tv-kiosk="1"]) .meter-head,:host([data-tv-kiosk="1"]) .savo-meter b { font-size:11px; }\n',
    ':host([data-tv-kiosk="1"]) .savo-age { font-size:12px; opacity:.82; }\n',
    "tv meter",
)
replace_once(
    '            <span>${this._esc(pumpLabel)} · ${this._fmt(pumpPower,1," W")} · průtok ${this._esc(flowLabel)} · predikce ${this._esc(useLabel)} · zisk ${this._esc(yieldLabel)}</span>\n',
    '            <span>${this._esc(pumpLabel)} · ${this._fmt(pumpPower,1," W")} · průtok ${this._esc(flowLabel)} · predikce ${this._esc(useLabel)}</span>\n',
    "footer",
)

marker = '        /* Markvarec TV space-aware readability: 20260819-spaceaware-r1 */\n'
replace_once(marker, '        /* Markvarec Water UX: 20260820-liters-savo-simple-r1 */\n' + marker, "ux marker")

CARD.write_text(card, encoding="utf-8")

visual = r'''from pathlib import Path
import re

card = Path("/config/www/lina-rainwater-card.js").read_text(encoding="utf-8")

assert '_useSignal(rec)' in card
for cls in ('lamp red', 'lamp amber', 'lamp green'):
    assert cls in card, cls
assert 's.includes("VELMI ŠETŘIT") || s === "ŠETŘIT"' in card
assert 's === "BĚŽNĚ") return "amber"' in card
assert 's.includes("BEZ OMEZENÍ") || s.includes("KLIDNĚ VÍC") || s.includes("VYUŽÍVAT VÍC")' in card
assert '<div class="eyebrow">semafor používání</div>' in card
assert 'sensor.destovka_doporuceni' in card
assert 'sensor.destovka_savo_doporuceni' in card
assert 'data-entity="sensor.destovka_savo_doporuceni"' in card
assert 'savo-reason' in card and 'savo-age' in card
assert 'dávka není přesně známá' in card
assert 'savoAgeSummary' in card
assert 'savo-meter' not in card
assert 'dilutionLabel' not in card
assert 'dávka ?' not in card
assert 'comfort-visual' in card
assert 'senzorická zpětná vazba · ne měření chloru' not in card
assert '${this._esc(savoMessage)} · poslední dávka:' not in card
assert 'kvalita vody a jezírko' in card
assert 'title="${this._esc(savoMessage)}"' in card
assert 'title="${this._esc(message)}"' in card

signal_body = re.search(r'_useSignal\(rec\) \{(.*?)\n  \}', card, re.S)
assert signal_body
body = signal_body.group(1)
assert body.count('return "red"') == 1
assert body.count('return "amber"') == 1
assert body.count('return "green"') == 1
assert body.count('return "none"') == 1

print("RAINWATER_VISUAL_SEMANTICS_REGRESSION_OK")
'''
VISUAL.write_text(visual, encoding="utf-8")

pump = r'''from pathlib import Path
CFG=Path('/config/configuration.yaml').read_text(encoding='utf-8')
AUTO=Path('/config/automations.yaml').read_text(encoding='utf-8')
CARD=Path('/config/www/lina-rainwater-card.js').read_text(encoding='utf-8')
assert 'unique_id: markvarec_destovka_odber_vody_bezi' in CFG
assert "states('sensor.zahrada_cerpadlo_destovka_vykon')" in CFG
assert '| float(0) > 2.0' in CFG
assert 'destovka_odhad_prutoku_l_min:' in CFG
assert 'name: "Dešťovka - predikční / fallback denní spotřeba (odhad)"' in CFG
assert 'destovka_odber_start_ts:' in CFG
assert 'destovka_spotreba_dnes_l:' in CFG
assert 'interní přítok při neznámé dávce Sava (od zapnutí modelu)' in CFG
a0=AUTO.index("- id: 'markvarec_destovka_prubezna_bilance'")
a1=AUTO.index("\n- id: 'markvarec_destovka_rucni_kalibrace'",a0)
b=AUTO[a0:a1]
assert 'binary_sensor.destovka_odber_vody_bezi' in b
assert 'runtime_consumption_l' in b and 'flow_l_min' in b
assert 'fallback_consumption_l' in b and 'forecast_use_per_day' in b
assert 'use_per_day * (elapsed_s' not in b
assert 'daily_rollover' in b
assert 'label:"NEDÁVAT"' in CARD
assert 'label:"NEPŘIDÁVAT"' not in CARD
assert 'white-space:nowrap; overflow:hidden; text-overflow:ellipsis' in CARD
assert 'binary_sensor.destovka_odber_vody_bezi' in CARD
assert 'sensor.zahrada_cerpadlo_destovka_vykon' in CARD
assert '≈${flowEstimate.toFixed(1)} l/min' in CARD
assert 'savoApproxAgeMin' in CARD and 'savoApproxAgeMax' in CARD
assert 'approxDilutionMinPct' not in CARD
assert 'savoApproxInflow' not in CARD
assert 'dilutionLabel' not in CARD
assert 'savo-meter' not in CARD
assert 'dávka není přesně známá' in CARD
runtime_seconds=4.29*60
flow_l_min=10.0
liters=runtime_seconds*flow_l_min/60
assert abs(liters-42.9)<1e-9
print('RAINWATER_PUMP_PROXY_REGRESSION_OK')
'''
PUMP.write_text(pump, encoding="utf-8")

liters = r'''from pathlib import Path
CARD=Path('/config/www/lina-rainwater-card.js').read_text(encoding='utf-8')

assert ' mm' not in CARD
assert 'l/mm' not in CARD
assert 'sensor.destovka_srazky_7_dni' not in CARD
assert 'sensor.destovka_predpoved_srazek_3_dny' not in CARD
assert 'sensor.destovka_predpoved_srazek_5_dni' not in CARD
assert 'input_number.destovka_zisk_l_na_mm' not in CARD

assert 'sensor.destovka_pritok_7_dni' in CARD
assert 'sensor.destovka_ocekavany_pritok_3_dny' in CARD
assert 'sensor.destovka_ocekavany_pritok_5_dni' in CARD
assert 'přiteklo za 7 dní' in CARD
assert 'očekávaný přítok do nádrže' in CARD
assert 'kolik vody má přibýt' in CARD
assert '20260820-liters-savo-simple-r1' in CARD

assert 'savo-reason' in CARD
assert 'savo-age' in CARD
assert 'savo-meter' not in CARD
assert 'čas od dávky' not in CARD
assert 'naředění' not in CARD

print('RAINWATER_LITERS_ONLY_REGRESSION_OK')
'''
LITERS.write_text(liters, encoding="utf-8")

print("RAINWATER_LITERS_SAVO_PATCH_OK")
print("CARD_SHA256=" + sha(CARD))
print("VISUAL_SHA256=" + sha(VISUAL))
print("PUMP_SHA256=" + sha(PUMP))
print("LITERS_SHA256=" + sha(LITERS))
