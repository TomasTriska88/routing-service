from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

WEATHER = Path("/config/www/lina-weather-card.js")
RAIN = Path("/config/www/lina-rainwater-card.js")
ENERGY_FINAL = Path("/config/www/lina-energy-card.js")
ENERGY_STAGE = Path("/config/www/lina-energy-card.js.new")
HOME = Path("/config/www/lina-home-card.js")
RESOURCES = Path("/config/.storage/lovelace_resources")
DASHBOARD = Path("/config/.storage/lovelace.linino_hnizdo")
STATE = Path("/tmp/hnizdo_6cards_state.json")

EXPECTED = {
    str(WEATHER): "b1b2b6d40db817b9d0dab49963ad84ddcbc9592f29ee2622cdbcc7f06278c2b7",
    str(RAIN): "3dfcfff1bfa507cbd49349e39c96ae1d7e68cfa985f690e4751da6ac2c85b616",
    str(ENERGY_STAGE): "e0b09b134a8c4fd1e92c53626d9d3d88f3c393c02b575a5e984e36ed1e7f228d",
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assert_sha(path: Path, expected: str) -> None:
    actual = sha(path)
    assert actual == expected, f"{path}: expected {expected}, got {actual}"

def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    assert n == 1, f"{label}: expected exactly one match, got {n}"
    return text.replace(old, new, 1)

HOME_JS = r'''class LinaHomeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._lastRenderKey = "";
  }

  setConfig(config) {
    this._config = {
      name: "Lina",
      status_entity: "sensor.lina_status",
      internet_entity: "binary_sensor.markvarec_local_internet",
      bridge_entity: "automation.chatgpt_home_assistant_bridge",
      voice_entity: "media_player.loznice_google_nest_mini",
      ...config,
    };
    this._render(true);
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return 5; }
  getGridOptions() { return { columns: 12, rows: 5, min_rows: 4 }; }

  _st(id) { return this._hass?.states?.[id]; }
  _esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
      "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;"
    }[c]));
  }
  _bad(id) {
    const s = this._st(id)?.state;
    return !s || ["off","unknown","unavailable"].includes(String(s));
  }
  _voiceBad(id) {
    const s = this._st(id)?.state;
    return !s || ["unknown","unavailable"].includes(String(s));
  }
  _moreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles:true, composed:true, detail:{ entityId }
    }));
  }
  _time(raw) {
    if (!raw) return "";
    const bits = String(raw).split(" ");
    return bits.length > 1 ? bits[1].slice(0,5) : String(raw).slice(0,5);
  }

  _render(force = false) {
    if (!this._hass) return;
    const c = this._config;
    const status = this._st(c.status_entity);
    const a = status?.attributes || {};
    const name = a.profile_name || c.name || "Lina";
    const icon = a.profile_icon || "💖";
    const thought = String(a.thoughts || "Sleduji Markvarec a dávám pozor na to důležité.");
    const history = Array.isArray(a.activity_history) ? a.activity_history.slice(-3).reverse() : [];

    const internetBad = this._bad(c.internet_entity);
    const bridgeBad = this._bad(c.bridge_entity);
    const voiceBad = this._voiceBad(c.voice_entity);
    const hardBad = internetBad || bridgeBad;
    const level = hardBad ? "critical" : voiceBad ? "watch" : "normal";
    const headline = hardBad ? "Hnízdo potřebuje pozornost" : voiceBad ? "Hnízdo funguje, hlas je mimo" : "Hnízdo je v pořádku";
    const subline = hardBad
      ? (internetBad ? "Lokální internet není potvrzený." : "HA bridge není aktivní.")
      : voiceBad ? "Dashboard a automatizace běží dál." : "Spojení, bridge i hlas jsou dostupné.";

    const health = [
      { icon:"🌐", label:"Internet", value:internetBad ? "problém" : "online", bad:internetBad, entity:c.internet_entity },
      { icon:"🔗", label:"HA bridge", value:bridgeBad ? "problém" : "aktivní", bad:bridgeBad, entity:c.bridge_entity },
      { icon:"🔊", label:"Hlas", value:voiceBad ? "mimo" : "připraven", bad:voiceBad, entity:c.voice_entity },
    ];
    const key = JSON.stringify([name,icon,thought,history,level,headline,subline,health.map(x=>[x.value,x.bad])]);
    if (!force && key === this._lastRenderKey) return;
    this._lastRenderKey = key;

    const chips = health.map((x,i)=>`<button class="chip ${x.bad ? "bad" : ""}" data-health="${i}"><span>${x.icon}</span><small>${this._esc(x.label)}</small><strong>${this._esc(x.value)}</strong></button>`).join("");
    const activity = history.length ? history.map(x=>`<div class="activity"><span>${this._esc(this._time(x.time))}</span><p>${this._esc(x.text || "")}</p></div>`).join("") : `<div class="empty">Zatím bez nové zaznamenané aktivity.</div>`;

    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;container-type:inline-size;height:100%}
        ha-card{height:100%;overflow:hidden}
        .wrap{box-sizing:border-box;height:100%;min-height:220px;padding:14px 16px 12px;display:flex;flex-direction:column;gap:10px;background:radial-gradient(circle at 10% 0%,color-mix(in srgb,var(--primary-color) 13%,transparent),transparent 34%),var(--ha-card-background,var(--card-background-color))}
        .hero{display:grid;grid-template-columns:auto minmax(0,1fr);gap:11px;align-items:center;padding:7px 8px;border-radius:14px}.critical .hero{background:rgba(244,67,54,.11)}.watch .hero{background:rgba(255,193,7,.10)}
        .avatar{font-size:42px;line-height:1}.eyebrow{font-size:9px;text-transform:uppercase;letter-spacing:.09em;opacity:.52}.hero h2{font-size:20px;line-height:1.1;margin:2px 0 0}.hero p{font-size:10px;line-height:1.3;opacity:.65;margin:4px 0 0}
        .thought{padding:8px 10px;border-radius:12px;background:rgba(127,127,127,.06);font-size:11px;line-height:1.35;overflow-wrap:anywhere}.thought:before{content:"💭";margin-right:6px}
        .health{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.chip{appearance:none;color:inherit;border:0;padding:7px;border-radius:11px;background:rgba(127,127,127,.055);text-align:center;cursor:pointer}.chip>span{font-size:17px}.chip small,.chip strong{display:block}.chip small{font-size:8px;opacity:.55}.chip strong{font-size:11px;margin-top:1px}.chip.bad{background:rgba(244,67,54,.12)}
        .section{font-size:9px;text-transform:uppercase;letter-spacing:.08em;opacity:.48;margin-top:auto}.activities{display:grid;gap:4px}.activity{display:grid;grid-template-columns:38px minmax(0,1fr);gap:7px;padding:5px 7px;border-radius:9px;background:rgba(127,127,127,.045)}.activity span{font-size:9px;opacity:.52}.activity p{font-size:9px;line-height:1.25;margin:0;overflow-wrap:anywhere}.empty{font-size:9px;opacity:.52;padding:7px}
        @container (max-width:460px){.wrap{padding:12px}.health{grid-template-columns:1fr}.avatar{font-size:35px}.hero h2{font-size:17px}}
      </style>
      <ha-card class="${level}"><div class="wrap ${level}">
        <div class="hero"><div class="avatar">${this._esc(icon)}</div><div><div class="eyebrow">${this._esc(name)} · Markvarec</div><h2>${this._esc(headline)}</h2><p>${this._esc(subline)}</p></div></div>
        <div class="thought">${this._esc(thought)}</div>
        <div class="health">${chips}</div>
        <div class="section">poslední aktivita</div><div class="activities">${activity}</div>
      </div></ha-card>`;
    this.shadowRoot.querySelectorAll("[data-health]").forEach(el=>el.addEventListener("click",()=>{const x=health[Number(el.dataset.health)];this._moreInfo(x?.entity)}));
  }
}
if(!customElements.get("lina-home-card")) customElements.define("lina-home-card",LinaHomeCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(x=>x.type==="lina-home-card")) window.customCards.push({type:"lina-home-card",name:"Lina Home Card",description:"TV souhrn Liny a zdraví Hnízda."});
'''

def prepare() -> None:
    for p, h in EXPECTED.items():
        assert_sha(Path(p), h)

    weather = WEATHER.read_text(encoding="utf-8")
    rain = RAIN.read_text(encoding="utf-8")
    energy = ENERGY_STAGE.read_text(encoding="utf-8")

    weather = replace_once(weather, 'const daily = (this._forecast.daily || []).slice(0,4);', 'const daily = (this._forecast.daily || []).slice(0,6);', "weather daily count")
    weather = replace_once(weather, ':host { display:block; }', ':host { display:block; height:100%; }', "weather host height")
    weather = replace_once(weather, 'ha-card { overflow:hidden; cursor:pointer; container-type:inline-size; }', 'ha-card { overflow:hidden; cursor:pointer; container-type:inline-size; height:100%; }', "weather card height")
    weather = replace_once(weather, '.forecasts { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:7px; margin-top:7px; }', '.forecasts { display:block; margin-top:7px; }', "weather forecasts columns")
    weather = replace_once(weather, '.forecast { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:4px; }', '.forecast { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:4px; }', "weather daily grid count")
    weather = replace_once(weather, '<div class="forecasts">\n            <div class="forecast-group">\n              <div class="group-title">nejbližší hodiny</div>\n              <div class="forecast">${hourlyHtml}</div>\n            </div>\n            <div class="forecast-group">\n              <div class="group-title">další dny</div>\n              <div class="forecast">${dailyHtml}</div>\n            </div>\n          </div>', '<div class="forecasts">\n            <div class="forecast-group">\n              <div class="group-title">další dny</div>\n              <div class="forecast">${dailyHtml}</div>\n            </div>\n          </div>', "weather hide hourly")
    weather = replace_once(weather, '${tempTrend ? `<div class="temp-trend"><strong>${this._esc(tempTrend.label)}</strong>${tempTrend.detail ? ` · ${this._esc(tempTrend.detail)}` : ""}${tempTrend.far ? `<small>${this._esc(tempTrend.far)}${tempTrend.farDetail ? ` · ${this._esc(tempTrend.farDetail)}` : ""}</small>` : ""}</div>` : ""}', '${tempTrend ? `<div class="temp-trend"><strong>${this._esc(tempTrend.longRange ? "0–15 dní · " : "")}${this._esc(tempTrend.label)}</strong>${tempTrend.detail ? ` · ${this._esc(tempTrend.detail)}` : ""}${tempTrend.far ? `<small>${this._esc(tempTrend.far)}${tempTrend.farDetail ? ` · ${this._esc(tempTrend.farDetail)}` : ""}</small>` : ""}</div>` : ""}', "weather long-range label")

    rain = replace_once(rain, ':host { display:block; min-width:0; container-type:inline-size; }', ':host { display:block; min-width:0; container-type:inline-size; height:100%; }', "rain host height")
    rain = replace_once(rain, 'ha-card { overflow:hidden; cursor:pointer; }', 'ha-card { overflow:hidden; cursor:pointer; height:100%; }', "rain card height")
    rain = replace_once(rain, 'padding:14px 16px 12px;\n          min-width:0;', 'padding:12px 14px 10px;\n          min-width:0; height:100%; box-sizing:border-box;', "rain compact wrap")
    rain = replace_once(rain, 'const yieldPerMm = this._num("input_number.destovka_zisk_l_na_mm", null);', 'const yieldPerMm = this._num("input_number.destovka_zisk_l_na_mm", null);\n    const pondFouling = this._txt("sensor.jezirko_zaneseni_cerpadla", "—");\n    const pondCleaning = this._txt("sensor.jezirko_stav_cisteni", "—");\n    const pondPower = this._num("sensor.jezirko_rozvadec_vykon", null);', "rain pond vars")
    rain = replace_once(rain, 'doseNote, comfort, pump, use, yieldPerMm\n    ]);', 'doseNote, comfort, pump, use, yieldPerMm, pondFouling, pondCleaning, pondPower\n    ]);', "rain render key")
    rain = replace_once(rain, '.water-quality { display:grid; grid-template-columns:1fr 1fr; gap:6px; min-width:0; }', '.water-quality { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:6px; min-width:0; }', "rain quality 3 cols")
    rain = replace_once(rain, '<div class="section-title">voda a Savo</div>', '<div class="section-title">voda a jezírko</div>', "rain section title")
    old_comfort = '''            <div class="quality" data-entity="input_text.destovka_komfort_vody">
              <div class="qtop"><div class="qicon">🚿</div><div class="qcopy"><small>komfort vody</small><strong>${this._esc(comfort)}</strong></div></div>
              <p>senzorická zpětná vazba · ne měření chloru</p>
            </div>'''
    new_comfort = old_comfort + '''
            <div class="quality" data-entity="sensor.jezirko_stav_cisteni">
              <div class="qtop"><div class="qicon">🐟</div><div class="qcopy"><small>jezírko</small><strong>${this._esc(pondCleaning)}</strong></div></div>
              <p>čerpadlo ${pondPower === null ? "—" : this._esc(Math.round(pondPower)+" W")} · zanesení ${this._esc(pondFouling)}</p>
            </div>'''
    rain = replace_once(rain, old_comfort, new_comfort, "rain pond block")

    staged_map = {
        WEATHER: weather,
        RAIN: rain,
        ENERGY_FINAL: energy,
        HOME: HOME_JS,
    }
    for target, text in staged_map.items():
        target.with_name(target.name + ".new-hnizdo").write_text(text, encoding="utf-8")

    rdata = json.loads(RESOURCES.read_text(encoding="utf-8"))
    items = rdata.get("data", {}).get("items", [])
    def upsert(url_key: str, url: str):
        hits = [x for x in items if url_key in str(x.get("url", ""))]
        for x in hits[1:]:
            items.remove(x)
        if hits:
            hits[0]["url"] = url
            hits[0]["type"] = "module"
        else:
            items.append({"id": uuid.uuid4().hex, "url": url, "type": "module"})
    upsert("lina-weather-card.js", "/local/lina-weather-card.js?v=20260818-tv2")
    upsert("lina-rainwater-card.js", "/local/lina-rainwater-card.js?v=20260818-water2")
    upsert("lina-energy-card.js", "/local/lina-energy-card.js?v=20260818-v1")
    upsert("lina-home-card.js", "/local/lina-home-card.js?v=20260818-v1")
    RESOURCES.with_name(RESOURCES.name + ".new-hnizdo").write_text(json.dumps(rdata, ensure_ascii=False, separators=(",",":")), encoding="utf-8")

    ddata = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    data = ddata.get("data", {})
    cfg = data.get("config", data)
    view = next(x for x in cfg.get("views", []) if x.get("path") == "prehled")
    view["type"] = "panel"
    view.pop("sections", None)
    view["cards"] = [{
        "type": "grid",
        "columns": 3,
        "square": False,
        "cards": [
            {"type":"custom:lina-home-card", "name":"Lina"},
            {"type":"custom:lina-weather-card", "entity":"weather.zahrada_pocasi_home", "name":"Počasí Markvarec", "radar_entity":"sensor.chmi_radar_markvarec"},
            {"type":"custom:lina-security-card", "name":"Bezpečnost"},
            {"type":"custom:lina-climate-safety-card", "name":"Klima a teplotní bezpečnost", "weather_entity":"weather.zahrada_pocasi_home"},
            {"type":"custom:lina-energy-card", "name":"Energie"},
            {"type":"custom:lina-rainwater-card", "entity":"input_number.destovka_stav_l", "name":"Voda"},
        ],
    }]
    DASHBOARD.with_name(DASHBOARD.name + ".new-hnizdo").write_text(
        json.dumps(ddata, ensure_ascii=False, separators=(",",":")), encoding="utf-8"
    )

    staged = {}
    for target in [WEATHER, RAIN, ENERGY_FINAL, HOME, RESOURCES, DASHBOARD]:
        p = target.with_name(target.name + ".new-hnizdo")
        staged[str(target)] = {"sha": sha(p), "size": p.stat().st_size}
    original = {}
    for target in [WEATHER, RAIN, ENERGY_FINAL, HOME, RESOURCES, DASHBOARD]:
        if target.exists():
            original[str(target)] = {"sha": sha(target), "size": target.stat().st_size}
        else:
            original[str(target)] = None
    STATE.write_text(json.dumps({"staged": staged, "original": original}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PREPARED")
    for path, meta in staged.items():
        print(path, meta["sha"], meta["size"])

def commit() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    for p, h in EXPECTED.items():
        assert_sha(Path(p), h)
    for path, meta in state["original"].items():
        p = Path(path)
        if meta is None:
            assert not p.exists(), f"{p} appeared after prepare"
        else:
            assert p.exists(), f"{p} disappeared after prepare"
            assert sha(p) == meta["sha"], f"{p} changed after prepare"
    for path, meta in state["staged"].items():
        p = Path(path).with_name(Path(path).name + ".new-hnizdo")
        assert p.exists(), f"missing staged {p}"
        assert sha(p) == meta["sha"], f"staged drift {p}"

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = []
    for path in state["staged"]:
        target = Path(path)
        staged = target.with_name(target.name + ".new-hnizdo")
        if target.exists():
            backup = target.with_name(target.name + f".bak-hnizdo6-{stamp}")
            shutil.copy2(target, backup)
            backups.append(str(backup))
        os.replace(staged, target)
    print("COMMITTED", stamp)
    for path, meta in state["staged"].items():
        p = Path(path)
        print(path, sha(p), p.stat().st_size)
    print("BACKUPS", ",".join(backups))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    if mode == "prepare":
        prepare()
    elif mode == "commit":
        commit()
    else:
        raise SystemExit(f"unknown mode {mode}")
