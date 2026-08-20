from pathlib import Path
import hashlib

PATH = Path("/config/www/lina-rainwater-card.js")
EXPECTED_OLD = "9632f85d66c818a37e4eca6b67311f2c8d14d132b70bda209a9c3b279953ce23"

raw = PATH.read_bytes()
old_hash = hashlib.sha256(raw).hexdigest()
if old_hash != EXPECTED_OLD:
    raise SystemExit(f"unexpected live rainwater card hash: {old_hash}")

text = raw.decode("utf-8")

def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, got {count}")
    text = text.replace(old, new, 1)

status_block = '''  _statusClass(rec) {
    const s = String(rec || "").toUpperCase();
    if (s.includes("VELMI ŠETŘIT")) return "danger";
    if (s === "ŠETŘIT") return "warn";
    if (s.includes("VYUŽÍVAT VÍC")) return "overflow";
    if (s.includes("KLIDNĚ VÍC")) return "wet";
    if (s.includes("BEZ OMEZENÍ")) return "good";
    return "calm";
  }
'''
status_new = status_block + '''  _useSignal(rec) {
    const s = String(rec || "").toUpperCase();
    if (s.includes("VELMI ŠETŘIT") || s === "ŠETŘIT") return "red";
    if (s.includes("BEZ OMEZENÍ") || s.includes("KLIDNĚ VÍC") || s.includes("VYUŽÍVAT VÍC")) return "green";
    if (s === "BĚŽNĚ") return "amber";
    return "none";
  }
  _useHint(rec) {
    const s = String(rec || "").toUpperCase();
    if (s.includes("VELMI ŠETŘIT")) return "jen nezbytná spotřeba";
    if (s === "ŠETŘIT") return "omez zbytečnou spotřebu";
    if (s.includes("VYUŽÍVAT VÍC")) return "uvolni místo na déšť";
    if (s.includes("KLIDNĚ VÍC")) return "můžeš spotřebu zvýšit";
    if (s.includes("BEZ OMEZENÍ")) return "používej normálně";
    if (s === "BĚŽNĚ") return "používej normálně";
    return "čekám na data";
  }
  _savoView(state) {
    const s = String(state || "").toUpperCase();
    if (s.includes("NEPŘIDÁVAT")) return { cls:"caution", label:"NEPŘIDÁVAT", icon:"?" };
    if (s.includes("ZKONTROLOVAT")) return { cls:"check", label:"ZKONTROLOVAT", icon:"!" };
    if (s.includes("VEDENO")) return { cls:"ok", label:"VEDENO", icon:"✓" };
    return { cls:"unknown", label:"NEZNÁMÉ", icon:"?" };
  }
  _comfortView(value) {
    const raw = String(value || "—");
    const s = raw.toLowerCase();
    if (s.includes("zatuch") || s.includes("zapách") || s.includes("smrd")) return { cls:"bad", label:"ZATUCHLÁ", icon:"⚠️" };
    if (s.includes("savov") || s.includes("chlor")) return { cls:"warn", label:"SAVOVÁ", icon:"🏊" };
    if (s.includes("neutr") || s.includes("bez zápachu") || s.includes("v pořádku")) return { cls:"good", label:"NEUTRÁLNÍ", icon:"💧" };
    return { cls:"neutral", label:raw, icon:"🚿" };
  }
'''
replace_once(status_block, status_new, "helper methods")

savo_vars = '''    const savoRecommendation = this._txt("sensor.destovka_savo_doporuceni", "—");
    const savoMessage = this._attr("sensor.destovka_savo_doporuceni", "message", "Dezinfekční model se právě načítá.");
'''
savo_vars_new = savo_vars + '''    const savoAgeRaw = Number.parseFloat(this._attr("sensor.destovka_savo_doporuceni", "vek_davky_dni", null));
    const savoAgeDays = Number.isFinite(savoAgeRaw) ? savoAgeRaw : null;
    const savoInflow = this._num("input_number.destovka_savo_pritok_od_davky_l", null);
    const savoCheckDays = this._num("input_number.destovka_savo_kontrola_dni", 7);
    const savoDilutionLimit = this._num("input_number.destovka_savo_kontrola_redeni_pct", 25);
'''
replace_once(savo_vars, savo_vars_new, "Savo visual inputs")

render_old = '''      level, recommendation, message, savoRecommendation, savoMessage, days, free, rain7, inflow7, rain3, inflow3,
      rain5, inflow5, projected5, release, known, dose, doseVolume, doseTime,
      doseNote, comfort, pump, use, yieldPerMm, pondFouling, pondCleaning, pondPower
'''
render_new = '''      level, recommendation, message, savoRecommendation, savoMessage, savoAgeDays, savoInflow, savoCheckDays, savoDilutionLimit,
      days, free, rain7, inflow7, rain3, inflow3, rain5, inflow5, projected5, release, known, dose, doseVolume, doseTime,
      doseNote, comfort, pump, use, yieldPerMm, pondFouling, pondCleaning, pondPower
'''
replace_once(render_old, render_new, "render key")

dose_block = '''    const doseSub = known
      ? `${doseTime ? this._esc(doseTime) : "čas nezapsán"}${Number.isFinite(doseVolume) ? ` · při ~${doseVolume.toFixed(0)} l` : ""}`
      : this._esc(doseNote || "čeká na první přesnou dávku v ml");
'''
derived = dose_block + '''
    const useSignal = this._useSignal(recommendation);
    const useHint = this._useHint(recommendation);
    const useMore = /VYUŽÍVAT VÍC|KLIDNĚ VÍC/i.test(recommendation);
    const savoView = this._savoView(savoRecommendation);
    const comfortView = this._comfortView(comfort);
    const savoAgeKnown = Number.isFinite(savoAgeDays) && Number.isFinite(savoCheckDays) && savoCheckDays > 0;
    const savoAgePct = savoAgeKnown ? this._clamp((savoAgeDays / savoCheckDays) * 100, 0, 100) : 0;
    const dilutionPct = known && Number.isFinite(savoInflow) && Number.isFinite(doseVolume) && doseVolume > 0
      ? (savoInflow / doseVolume) * 100 : null;
    const dilutionKnown = Number.isFinite(dilutionPct) && Number.isFinite(savoDilutionLimit) && savoDilutionLimit > 0;
    const dilutionMeterPct = dilutionKnown ? this._clamp((dilutionPct / savoDilutionLimit) * 100, 0, 100) : 0;
    const ageLabel = savoAgeKnown ? `${savoAgeDays.toFixed(1)} / ${savoCheckDays.toFixed(0)} d` : `? / ${savoCheckDays.toFixed(0)} d`;
    const dilutionLabel = dilutionKnown ? `${dilutionPct.toFixed(0)} / ${savoDilutionLimit.toFixed(0)} %` : `? / ${savoDilutionLimit.toFixed(0)} %`;
'''
replace_once(dose_block, derived, "derived visual model")

advice_css = '''        .advice {
          border-radius:16px; padding:11px 12px; min-width:0; display:flex; flex-direction:column; justify-content:center;
          background:rgba(127,127,127,.07); border:1px solid rgba(127,127,127,.12);
        }
        .advice .eyebrow { font-size:12px; text-transform:uppercase; letter-spacing:.09em; opacity:.68; }
        .advice strong { font-size:21px; line-height:1.05; margin:4px 0 5px; overflow-wrap:anywhere; }
        .advice small { font-size:13px; line-height:1.35; opacity:.72; overflow-wrap:anywhere; }
'''
advice_css_new = '''        .advice {
          border-radius:16px; padding:9px 11px; min-width:0; display:grid; grid-template-columns:44px minmax(0,1fr);
          gap:10px; align-items:center; background:rgba(127,127,127,.07); border:1px solid rgba(127,127,127,.12);
        }
        .signal-copy { min-width:0; }
        .advice .eyebrow { font-size:12px; text-transform:uppercase; letter-spacing:.09em; opacity:.68; }
        .advice strong { display:block; font-size:21px; line-height:1.05; margin:4px 0 4px; overflow-wrap:anywhere; }
        .advice small { display:block; font-size:13px; line-height:1.25; opacity:.72; overflow-wrap:anywhere; }
        .traffic-light {
          width:36px; box-sizing:border-box; padding:5px; border-radius:13px; display:grid; gap:5px; justify-self:center;
          background:linear-gradient(145deg,rgba(10,12,16,.96),rgba(34,37,43,.92));
          border:1px solid rgba(255,255,255,.12); box-shadow:inset 0 0 0 1px rgba(0,0,0,.55),0 3px 10px rgba(0,0,0,.22);
        }
        .lamp {
          width:24px; height:24px; border-radius:50%; display:block; background:currentColor; opacity:.16;
          box-shadow:inset 0 2px 5px rgba(255,255,255,.16),inset 0 -3px 6px rgba(0,0,0,.36);
          transition:opacity .2s ease,box-shadow .2s ease,transform .2s ease;
        }
        .lamp.red { color:#ff5252; }
        .lamp.amber { color:#ffc107; }
        .lamp.green { color:#4caf50; }
        .lamp.on { opacity:1; transform:scale(1.03); box-shadow:0 0 13px color-mix(in srgb,currentColor 82%,transparent),inset 0 2px 5px rgba(255,255,255,.34),inset 0 -3px 6px rgba(0,0,0,.25); }
        .signal-extra { display:inline-flex; align-items:center; gap:4px; margin-top:5px; padding:3px 7px; border-radius:999px; font-size:11px; font-weight:750; background:rgba(76,175,80,.13); }
'''
replace_once(advice_css, advice_css_new, "traffic light CSS")

quality_css = '''        .quality p { font-size:12px; line-height:1.3; opacity:.68; margin:5px 0 0; overflow-wrap:anywhere; }
'''
quality_css_new = quality_css + '''        .savo-card { display:grid; gap:8px; }
        .savo-head { display:grid; grid-template-columns:38px minmax(0,1fr) auto; gap:7px; align-items:center; min-width:0; }
        .savo-icon { width:36px; height:36px; border-radius:11px; display:grid; place-items:center; font-size:17px; font-weight:900; background:rgba(127,127,127,.10); letter-spacing:-2px; }
        .savo-title { min-width:0; }
        .savo-title small { display:block; font-size:11px; opacity:.68; text-transform:uppercase; letter-spacing:.06em; }
        .savo-title strong { display:block; font-size:15px; line-height:1.1; overflow-wrap:anywhere; }
        .savo-dose { padding:3px 6px; border-radius:999px; font-size:10px; font-weight:800; white-space:nowrap; background:rgba(127,127,127,.10); }
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
        .quality.comfort-visual { display:grid; align-content:center; }
        .comfort-main { display:flex; align-items:center; gap:10px; min-width:0; }
        .comfort-icon { width:40px; height:40px; border-radius:50%; display:grid; place-items:center; font-size:22px; background:rgba(127,127,127,.10); flex:0 0 auto; }
        .comfort-copy { min-width:0; }
        .comfort-copy small { display:block; font-size:11px; opacity:.68; text-transform:uppercase; letter-spacing:.06em; }
        .comfort-copy strong { display:block; font-size:16px; line-height:1.1; overflow-wrap:anywhere; }
        .comfort-visual.warn .comfort-icon { background:rgba(255,193,7,.15); }
        .comfort-visual.bad .comfort-icon { background:rgba(244,67,54,.14); }
        .comfort-visual.good .comfort-icon { background:rgba(76,175,80,.14); }
'''
replace_once(quality_css, quality_css_new, "Savo visual CSS")

tv_css = ''':host([data-tv-kiosk="1"]) .quality .qcopy strong { font-size:15px; }
:host([data-tv-kiosk="1"]) .quality p { font-size:13px; opacity:.80; }
'''
tv_css_new = tv_css + ''':host([data-tv-kiosk="1"]) .savo-title strong { font-size:16px; }
:host([data-tv-kiosk="1"]) .savo-title small { font-size:12px; opacity:.82; }
:host([data-tv-kiosk="1"]) .savo-dose { font-size:11px; }
:host([data-tv-kiosk="1"]) .meter-head,:host([data-tv-kiosk="1"]) .savo-meter b { font-size:11px; }
:host([data-tv-kiosk="1"]) .comfort-copy strong { font-size:17px; }
:host([data-tv-kiosk="1"]) .comfort-copy small { font-size:12px; opacity:.82; }
'''
replace_once(tv_css, tv_css_new, "TV visual CSS")

advice_html = '''            <div class="advice" data-entity="sensor.destovka_doporuceni">
              <div class="eyebrow">semafor používání</div>
              <strong>${this._esc(recommendation)}</strong>
              <small>${this._esc(message)}</small>
            </div>
'''
advice_html_new = '''            <div class="advice" data-entity="sensor.destovka_doporuceni" title="${this._esc(message)}">
              <div class="traffic-light" aria-label="semafor používání">
                <span class="lamp red ${useSignal === "red" ? "on" : ""}"></span>
                <span class="lamp amber ${useSignal === "amber" ? "on" : ""}"></span>
                <span class="lamp green ${useSignal === "green" ? "on" : ""}"></span>
              </div>
              <div class="signal-copy">
                <div class="eyebrow">semafor používání</div>
                <strong>${this._esc(recommendation)}</strong>
                <small>${this._esc(useHint)}</small>
                ${useMore ? `<span class="signal-extra">↗ využívej víc</span>` : ""}
              </div>
            </div>
'''
replace_once(advice_html, advice_html_new, "traffic light HTML")

savo_html = '''            <div class="quality ${known ? "" : "unknown"}" data-entity="input_boolean.destovka_savo_davka_znama">
              <div class="qtop"><div class="qicon">🧴</div><div class="qcopy"><small>Savo / dezinfekce</small><strong>${this._esc(savoRecommendation)}</strong></div></div>
              <p>${this._esc(savoMessage)} · poslední dávka: ${this._esc(doseMain)} · ${doseSub}</p>
            </div>
            <div class="quality" data-entity="input_text.destovka_komfort_vody">
              <div class="qtop"><div class="qicon">🚿</div><div class="qcopy"><small>komfort vody</small><strong>${this._esc(comfort)}</strong></div></div>
              <p>senzorická zpětná vazba · ne měření chloru</p>
            </div>
'''
savo_html_new = '''            <div class="quality savo-card ${this._esc(savoView.cls)}" data-entity="sensor.destovka_savo_doporuceni" title="${this._esc(savoMessage)}">
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
            <div class="quality comfort-visual ${this._esc(comfortView.cls)}" data-entity="input_text.destovka_komfort_vody" title="${this._esc(comfort)}">
              <div class="comfort-main">
                <div class="comfort-icon">${this._esc(comfortView.icon)}</div>
                <div class="comfort-copy"><small>komfort vody</small><strong>${this._esc(comfortView.label)}</strong></div>
              </div>
            </div>
'''
replace_once(savo_html, savo_html_new, "Savo/comfort HTML")

replace_once('<div class="section-title">voda a jezírko</div>',
             '<div class="section-title">kvalita vody a jezírko</div>',
             "section title")

PATH.write_text(text, encoding="utf-8")
new_hash = hashlib.sha256(PATH.read_bytes()).hexdigest()
print("RAINWATER_VISUAL_PATCH_OK", new_hash, PATH.stat().st_size)
