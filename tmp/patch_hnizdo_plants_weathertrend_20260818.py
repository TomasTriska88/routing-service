#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import hashlib, json, os, shutil

CONFIG = Path("/config/configuration.yaml")
CLIMATE = Path("/config/www/lina-climate-safety-card.js")
WEATHER = Path("/config/www/lina-weather-card.js")
RES = Path("/config/.storage/lovelace_resources")

EXPECTED_CLIMATE = "a46b3c912439b96d6a1144d7ea63319b18cb204f50d57738fa01c34593e83b5c"
EXPECTED_WEATHER = "6fc296c991a00af0351f6c17425c3d236ee5396f8efbf719d48214be57380cf2"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

assert sha(CLIMATE) == EXPECTED_CLIMATE, (CLIMATE, sha(CLIMATE))
assert sha(WEATHER) == EXPECTED_WEATHER, (WEATHER, sha(WEATHER))

cfg = CONFIG.read_text(encoding="utf-8")
climate = CLIMATE.read_text(encoding="utf-8")
weather = WEATHER.read_text(encoding="utf-8")
res = json.loads(RES.read_text(encoding="utf-8"))

assert "zahrada_letnene_rostliny_venku:" not in cfg
cfg_anchor = '''  zahrada_docasne_venku:
    name: "Zahrada - dočasně jsme venku"
    icon: mdi:walk

'''
cfg_insert = cfg_anchor + '''  zahrada_letnene_rostliny_venku:
    name: "Letněné rostliny venku"
    icon: mdi:sprout

'''
assert cfg.count(cfg_anchor) == 1
cfg_new = cfg.replace(cfg_anchor, cfg_insert, 1)

climate_anchor1 = '''      safe_min_temp: "input_number.loznice_primotop_minimalni_teplota",
      sencor_online: "binary_sensor.sencor_meteostanice_online",
'''
climate_repl1 = '''      safe_min_temp: "input_number.loznice_primotop_minimalni_teplota",
      summer_plants_out: "input_boolean.zahrada_letnene_rostliny_venku",
      sencor_online: "binary_sensor.sencor_meteostanice_online",
'''
assert climate.count(climate_anchor1) == 1
climate_new = climate.replace(climate_anchor1, climate_repl1, 1)

climate_anchor2 = '''    const forecast = this._forecastSummary();
    const heater = this._heaterState();
    const outdoorAnimalTemps = [outT, forecast.min48].filter(Number.isFinite);
'''
climate_repl2 = '''    const forecast = this._forecastSummary();
    const heater = this._heaterState();
    const summerPlantsOut = this._st(c.summer_plants_out)?.state === "on";
    const seasonalTemps = [outT, forecast.min48].filter(Number.isFinite);
    const seasonalRef = seasonalTemps.length ? Math.min(...seasonalTemps) : NaN;
    const seasonalRefLabel = Number.isFinite(forecast.min48) && (!Number.isFinite(outT) || forecast.min48 < outT) ? "výhled do 48 h" : "venku nyní";
    const outdoorAnimalTemps = [outT, forecast.min48].filter(Number.isFinite);
'''
assert climate_new.count(climate_anchor2) == 1
climate_new = climate_new.replace(climate_anchor2, climate_repl2, 1)

climate_anchor3 = '''    if (this._st(c.sencor_online)?.state !== "on") {
      add(2, "📡", "Chybí venkovní měření", "Sencor není potvrzen online; mrazové a větrné hodnocení je méně jisté.", c.sencor_online);
    }
'''
climate_repl3 = climate_anchor3 + '''    if (summerPlantsOut && Number.isFinite(seasonalRef) && seasonalRef < 13) {
      add(2, "🌿", "Letněné rostliny: přestěhovat dovnitř", `${seasonalRef.toFixed(1)} °C · ${seasonalRefLabel}; při výhledu pod 13 °C už je nenechávat venku.`, c.summer_plants_out);
    }
'''
assert climate_new.count(climate_anchor3) == 1
climate_new = climate_new.replace(climate_anchor3, climate_repl3, 1)

weather_anchor1 = '''  _irrigation(radar, temp, solar) {
'''
trend_method = '''  _temperatureTrend(currentTemp) {
    const now = Date.now();
    const future = (this._forecast.hourly || []).filter(f => {
      const t = Date.parse(f?.datetime || "");
      return Number.isFinite(t) && t >= now - 30 * 60 * 1000 && t <= now + 8 * 60 * 60 * 1000 &&
        Number.isFinite(Number(f?.temperature));
    });
    if (!future.length || !Number.isFinite(currentTemp)) return null;
    const target = future[Math.min(future.length - 1, 6)];
    const targetTemp = Number(target.temperature);
    const delta = targetTemp - currentTemp;
    const time = this._timeLabel(target.datetime);
    if (delta >= 1.5) return { icon:"↗", label:"oteplování", target:targetTemp, time };
    if (delta <= -1.5) return { icon:"↘", label:"ochlazování", target:targetTemp, time };
    return { icon:"→", label:"teplota stabilní", target:targetTemp, time };
  }

'''
assert weather.count(weather_anchor1) == 1
weather_new = weather.replace(weather_anchor1, trend_method + weather_anchor1, 1)

weather_anchor2 = '''    const nextRain = this._nextRain(radar);
    const irr = this._irrigation(radar,temp,solar);
'''
weather_repl2 = '''    const nextRain = this._nextRain(radar);
    const tempTrend = this._temperatureTrend(temp);
    const irr = this._irrigation(radar,temp,solar);
'''
assert weather_new.count(weather_anchor2) == 1
weather_new = weather_new.replace(weather_anchor2, weather_repl2, 1)

weather_anchor3 = '''      radar,nextRain,irr,hourly,daily,pressureTrend
'''
weather_repl3 = '''      radar,nextRain,tempTrend,irr,hourly,daily,pressureTrend
'''
assert weather_new.count(weather_anchor3) == 1
weather_new = weather_new.replace(weather_anchor3, weather_repl3, 1)

weather_anchor4 = '''        .condition-text { font-size:12px; margin-top:3px; }
        .place {
'''
weather_repl4 = '''        .condition-text { font-size:12px; margin-top:3px; }
        .temp-trend { font-size:10px; margin-top:3px; opacity:.76; line-height:1.2; overflow-wrap:anywhere; }
        .temp-trend strong { font-weight:700; opacity:1; }
        .place {
'''
assert weather_new.count(weather_anchor4) == 1
weather_new = weather_new.replace(weather_anchor4, weather_repl4, 1)

weather_anchor5 = '''                <div class="condition-text">${this._esc(this._conditionLabel(cond))}</div>
                <div class="place">${this._esc(this._config.name)}</div>
'''
weather_repl5 = '''                <div class="condition-text">${this._esc(this._conditionLabel(cond))}</div>
                ${tempTrend ? `<div class="temp-trend"><strong>${this._esc(tempTrend.icon+" "+tempTrend.label)}</strong> · do ${this._esc(tempTrend.time)} ${this._esc(Math.round(tempTrend.target)+"°")}</div>` : ""}
                <div class="place">${this._esc(this._config.name)}</div>
'''
assert weather_new.count(weather_anchor5) == 1
weather_new = weather_new.replace(weather_anchor5, weather_repl5, 1)

items = res.get("data", {}).get("items", [])
weather_hits = [x for x in items if "lina-weather-card.js" in str(x.get("url",""))]
climate_hits = [x for x in items if "lina-climate-safety-card.js" in str(x.get("url",""))]
assert len(weather_hits) == 1, weather_hits
assert len(climate_hits) == 1, climate_hits
assert weather_hits[0]["url"] == "/local/lina-weather-card.js?v=20260817-compact1", weather_hits[0]
assert climate_hits[0]["url"] == "/local/lina-climate-safety-card.js?v=20260818-v2", climate_hits[0]
weather_hits[0]["url"] = "/local/lina-weather-card.js?v=20260818-trend1"
climate_hits[0]["url"] = "/local/lina-climate-safety-card.js?v=20260818-v3"

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
for p in (CONFIG, CLIMATE, WEATHER, RES):
    shutil.copy2(p, Path(str(p) + f".bak-plants-trend-{stamp}"))

def atomic_text(p, text):
    q = Path(str(p)+".new")
    q.write_text(text, encoding="utf-8")
    os.replace(q, p)

atomic_text(CONFIG, cfg_new)
atomic_text(CLIMATE, climate_new)
atomic_text(WEATHER, weather_new)
q = Path(str(RES)+".new")
q.write_text(json.dumps(res, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
os.replace(q, RES)

print("PATCHED")
print("CONFIG_SHA="+sha(CONFIG))
print("CLIMATE_SHA="+sha(CLIMATE))
print("WEATHER_SHA="+sha(WEATHER))
print("RES_SHA="+sha(RES))
print("BACKUP_STAMP="+stamp)
