#!/usr/bin/env python3
import hashlib, os, re, shutil, sys
from pathlib import Path
from datetime import datetime

WEATHER = Path("/config/www/lina-weather-card.js")
OUTLOOK = Path("/config/markvarec_temperature_outlook.py")
RESOURCES = Path("/config/.storage/lovelace_resources")

EXPECTED = {
    WEATHER: "b1b2b6d40db817b9d0dab49963ad84ddcbc9592f29ee2622cdbcc7f06278c2b7",
    OUTLOOK: "feb538ff214baaafe77a06a63299ba5c91f71c8e0cf8e197b809ae9acf5bed0d",
    RESOURCES: "796e5e3e18f9340da2db16142651abb6ee30474616268754d54c3f19fc713dfa",
}
RESOURCE_OLD = "/local/lina-weather-card.js?v=20260818-trend46"
RESOURCE_NEW = "/local/lina-weather-card.js?v=20260818-minima-irrigation-v1"

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def require_hashes():
    for p, expected in EXPECTED.items():
        actual = sha(p)
        if actual != expected:
            raise SystemExit(f"STALE_LIVE_FILE {p} expected={expected} actual={actual}")

OUTLOOK_NEW = r'''#!/usr/bin/env python3
import json, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Markvarec-HA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def avg(values):
    vals = [float(v) for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None

def short_label(delta):
    if delta is None:
        return "0–15 dní: bez dat"
    if delta <= -3.0:
        return "↘ minima výrazně klesají"
    if delta <= -1.5:
        return "↘ minima klesají"
    if delta >= 3.0:
        return "↗ minima výrazně rostou"
    if delta >= 1.5:
        return "↗ minima rostou"
    return "→ minima bez výrazné změny"

def far_label(delta):
    if delta is None:
        return "3–6 týdnů: bez dat"
    if delta <= -2.5:
        return "3–6 týdnů: minima výrazně klesají"
    if delta <= -1.0:
        return "3–6 týdnů: minima spíše klesají"
    if delta >= 2.5:
        return "3–6 týdnů: minima výrazně rostou"
    if delta >= 1.0:
        return "3–6 týdnů: minima spíše rostou"
    return "3–6 týdnů: minima bez výrazné změny"

try:
    raw = json.loads(Path("/config/.storage/core.config").read_text(encoding="utf-8"))
    cfg = raw.get("data", raw)
    lat = cfg["latitude"]
    lon = cfg["longitude"]

    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_min,temperature_2m_max",
        "forecast_days": 16,
        "timezone": "Europe/Prague",
    })
    daily = fetch("https://api.open-meteo.com/v1/forecast?" + params).get("daily", {})
    mins = daily.get("temperature_2m_min", [])
    maxs = daily.get("temperature_2m_max", [])
    start_min = avg(mins[:3])
    end_min = avg(mins[-3:])
    end_max = avg(maxs[-3:])
    delta = None if start_min is None or end_min is None else end_min - start_min
    medium_label = short_label(delta)
    if end_min is not None:
        if end_max is not None:
            medium_detail = f"ke konci minima kolem {end_min:.0f} °C · maxima {end_max:.0f} °C"
        else:
            medium_detail = f"ke konci minima kolem {end_min:.0f} °C"
    else:
        medium_detail = "konkrétní minima nejsou dostupná"

    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_min",
        "models": "ecmwf_ec46_ensemble_mean",
        "forecast_days": 46,
        "timezone": "Europe/Prague",
    })
    ec = fetch("https://seasonal-api.open-meteo.com/v1/seasonal?" + params).get("daily", {})
    ecmins = ec.get("temperature_2m_min", [])
    far = [float(v) for v in ecmins[16:46] if v is not None]
    week_means = []
    for i in range(0, len(far), 7):
        chunk = far[i:i+7]
        if len(chunk) >= 4:
            week_means.append(sum(chunk) / len(chunk))
    far_start = avg(week_means[:2])
    far_end = avg(week_means[-2:])
    far_delta = None if far_start is None or far_end is None else far_end - far_start
    subseasonal_label = far_label(far_delta)
    if far_start is not None and far_end is not None:
        subseasonal_detail = f"EC46 průměr denních minim {far_start:.0f} → {far_end:.0f} °C"
    else:
        subseasonal_detail = "EC46 nemá dost denních minim pro spolehlivý trend"

    state = "stabilni"
    if delta is not None and delta <= -1.5:
        state = "ochlazovani"
    elif delta is not None and delta >= 1.5:
        state = "oteplovani"

    print(json.dumps({
        "ok": True,
        "state": state,
        "medium_label": medium_label,
        "medium_detail": medium_detail,
        "medium_days": min(15, max(0, len(mins) - 1)),
        "subseasonal_label": subseasonal_label,
        "subseasonal_detail": subseasonal_detail,
        "subseasonal_weeks": len(week_means),
        "basis": "daily_minima",
        "source": "Open-Meteo 0–15 d minima + ECMWF EC46 daily minima 16–46 d",
        "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, separators=(",", ":")))
except Exception as exc:
    print(json.dumps({
        "ok": False,
        "state": "chyba",
        "error": type(exc).__name__,
        "basis": "daily_minima",
    }, ensure_ascii=False, separators=(",", ":")))
'''

TREND_METHOD = r'''  _temperatureTrend(currentTemp) {
    const outlook = this._st(this._config.outlook_entity);
    if (outlook && !["unknown","unavailable"].includes(String(outlook.state))) {
      const a = outlook.attributes || {};
      const main = String(a.medium_label || "").trim();
      const detail = String(a.medium_detail || "").trim();
      const far = String(a.subseasonal_label || "").trim();
      const farDetail = String(a.subseasonal_detail || "").trim();
      if (main || far) {
        const icon = String(outlook.state) === "ochlazovani" ? "↘" :
          String(outlook.state) === "oteplovani" ? "↗" : "→";
        return { icon, label:main || "0–15 dní: minima", detail, far, farDetail, longRange:true };
      }
    }
    const daily = (this._forecast.daily || [])
      .filter(f => Number.isFinite(Number(f?.templow)))
      .slice(0,6);
    if (!daily.length) return null;
    const first = Number(daily[0].templow);
    const last = Number(daily[daily.length - 1].templow);
    const delta = last - first;
    const icon = delta <= -1.5 ? "↘" : delta >= 1.5 ? "↗" : "→";
    const label = delta <= -1.5 ? "minima klesají" : delta >= 1.5 ? "minima rostou" : "minima stabilní";
    return {
      icon, label,
      detail:`${Math.round(first)} → ${Math.round(last)} °C`,
      far:"", farDetail:"", longRange:false
    };
  }

'''

IRR_METHOD = r'''  _irrigation(radar, temp, solar) {
    const rain7 = this._num("sensor.destovka_srazky_7_dni", null);
    const hourly = (this._forecast.hourly || []).slice(0,48);
    let rain24 = 0, rain48 = 0;
    hourly.forEach((f,i) => {
      const p = Number(f.precipitation || 0);
      if (i < 24) rain24 += p;
      rain48 += p;
    });
    if (!hourly.length) {
      const f3 = this._num("sensor.destovka_predpoved_srazek_3_dni", 0) ||
        this._num("sensor.destovka_predpoved_srazek_3_dny", 0) || 0;
      rain48 = f3;
      rain24 = f3 * 0.45;
    }

    let level = 0;
    const rainIncoming = radar.rainNow || Number.isFinite(radar.eta) || rain24 >= 4 || rain48 >= 7;
    if (!rainIncoming && rain7 !== null && rain7 < 2 && rain48 < 4) level = 1;
    if (level >= 1 && rain7 !== null && rain7 < 0.5 &&
        ((Number.isFinite(temp) && temp >= 28) || (Number.isFinite(solar) && solar >= 600))) level = 2;
    if (level >= 2 && rain7 !== null && rain7 < 0.2 && rain48 < 1 &&
        Number.isFinite(temp) && temp >= 31 && Number.isFinite(solar) && solar >= 750) level = 3;

    const labels = ["NEZALÉVAT","JEN NOVÉ","NOVÉ + OSLABENÉ","NOUZOVĚ I OSTATNÍ"];
    const details = [
      "bez zásahu",
      "Grace Star + čerstvé výsadby",
      "Grace Star · meruňka · slivoň/broskev",
      "nové + obrůstající ovoce · ostatní jen při vadnutí"
    ];
    return { level, label:labels[level], detail:details[level], rain7, rain24, rain48 };
  }

'''

def patch_js(text: str) -> str:
    out = text

    pat = re.compile(r'  _temperatureTrend\(currentTemp\) \{.*?\n  \}\n\n(?=  _irrigation)', re.S)
    out, n = pat.subn(TREND_METHOD, out, count=1)
    if n != 1:
        raise SystemExit(f"TREND_REPLACE_COUNT={n}")

    pat = re.compile(r'  _irrigation\(radar, temp, solar\) \{.*?\n  \}\n\n(?=  _windUnit)', re.S)
    out, n = pat.subn(IRR_METHOD, out, count=1)
    if n != 1:
        raise SystemExit(f"IRR_REPLACE_COUNT={n}")

    old_decl = '''    const hourly = (this._forecast.hourly || []).slice(0,4);
    const daily = (this._forecast.daily || []).slice(0,4);
'''
    new_decl = '''    const hourlyCandidates = (this._forecast.hourly || []).slice(0,6);
    const abruptTempDrop = hourlyCandidates.slice(0,4).some(f =>
      Number.isFinite(Number(f?.temperature)) && Number.isFinite(temp) &&
      (Number(f.temperature) <= temp - 5 || Number(f.temperature) <= 2));
    const significantHourly = hourlyCandidates.some(f => {
      const p = Number(f?.precipitation || 0);
      const pr = Number(f?.precipitation_probability || 0);
      const c = String(f?.condition || "").toLowerCase();
      return p >= 1 || pr >= 70 || c.includes("lightning") || c.includes("hail");
    }) || abruptTempDrop || windRelevant;
    const hourly = significantHourly ? hourlyCandidates.slice(0,4) : [];
    const daily = (this._forecast.daily || []).slice(0,6);
    const nearestNight = daily.find(f => Number.isFinite(Number(f?.templow)));
'''
    if out.count(old_decl) != 1:
        raise SystemExit(f"DECL_COUNT={out.count(old_decl)}")
    out = out.replace(old_decl, new_decl, 1)

    pat = re.compile(r'    const hourlyHtml = .*?\n    const age = ', re.S)
    new_html = r'''    const hourlyHtml = hourly.length ? hourly.map(f => {
      const p = Number(f.precipitation || 0);
      const pr = Number(f.precipitation_probability || 0);
      return `<div class="forecast-cell ${this._isRain(f) ? "wet" : ""}">
        <small>${this._timeLabel(f.datetime)}</small>
        <b>${this._conditionIcon(f.condition)}</b>
        <strong>${Number.isFinite(Number(f.temperature)) ? Math.round(Number(f.temperature))+"°" : "—"}</strong>
        <em>${p > 0 ? p.toFixed(1)+"mm" : pr >= 25 ? pr+"%" : ""}</em>
      </div>`;
    }).join("") : "";

    const dailyHtml = daily.length ? daily.map(f => {
      const hi = Number(f.temperature), lo = Number(f.templow);
      const p = Number(f.precipitation || 0), pr = Number(f.precipitation_probability || 0);
      return `<div class="day-cell ${this._isRain(f) ? "wet" : ""}">
        <small>${this._dayLabel(f.datetime)}</small>
        <b>${this._conditionIcon(f.condition)}</b>
        <strong class="night">🌙 ${Number.isFinite(lo) ? Math.round(lo)+"°" : "—"}</strong>
        <span class="dayhi">${Number.isFinite(hi) ? "↑ "+Math.round(hi)+"°" : ""}</span>
        <em>${p > 0 ? p.toFixed(1)+"mm" : pr >= 25 ? pr+"%" : ""}</em>
      </div>`;
    }).join("") : `<div class="loading">načítám výhled…</div>`;

    const nearestMinText = nearestNight && Number.isFinite(Number(nearestNight.templow))
      ? `${Math.round(Number(nearestNight.templow))}°C`
      : "—";
    const nearestMinDay = nearestNight ? this._dayLabel(nearestNight.datetime) : "bez dat";
    const rain7Text = irr.rain7 === null ? "?" : Number(irr.rain7).toFixed(1);
    const irrigationMeta = `bez půdní sondy · 7 d ${rain7Text} mm · 48 h ${Number(irr.rain48 || 0).toFixed(1)} mm`;
    const age = '''
    out, n = pat.subn(new_html, out, count=1)
    if n != 1:
        raise SystemExit(f"FORECAST_HTML_REPLACE_COUNT={n}")

    old_trend_inline = '${tempTrend ? `<div class="temp-trend"><strong>${this._esc(tempTrend.label)}</strong>${tempTrend.detail ? ` · ${this._esc(tempTrend.detail)}` : ""}${tempTrend.far ? `<small>${this._esc(tempTrend.far)}${tempTrend.farDetail ? ` · ${this._esc(tempTrend.farDetail)}` : ""}</small>` : ""}</div>` : ""}\n'
    if out.count(old_trend_inline) != 1:
        raise SystemExit(f"TREND_INLINE_COUNT={out.count(old_trend_inline)}")
    out = out.replace(old_trend_inline, "", 1)

    old_block = '''          ${signalHtml ? `<div class="signals">${signalHtml}</div>` : ""}
          ${radarActive ? `<div class="radar-wrap"><div class="radar-title">ČHMÚ radar · 60 min</div><div class="radar">${radarDots}</div></div>` : ""}

          <div class="irrigation">
            <div>
              <strong>🌱 Závlaha: ${this._esc(irr.label)}</strong>
              <small>meteorologický odhad</small>
            </div>
            <div class="drops">${drops}</div>
          </div>

          <div class="forecasts">
            <div class="forecast-group">
              <div class="group-title">nejbližší hodiny</div>
              <div class="forecast">${hourlyHtml}</div>
            </div>
            <div class="forecast-group">
              <div class="group-title">další dny</div>
              <div class="forecast">${dailyHtml}</div>
            </div>
          </div>
'''
    new_block = '''          ${signalHtml ? `<div class="signals">${signalHtml}</div>` : ""}
          ${radarActive ? `<div class="radar-wrap"><div class="radar-title">ČHMÚ radar · 60 min</div><div class="radar">${radarDots}</div></div>` : ""}

          <div class="trend-strip">
            <div class="trend-chip primary">
              <small>nejbližší noc</small>
              <strong>🌙 ${this._esc(nearestMinText)}</strong>
              <span>${this._esc(nearestMinDay)}</span>
            </div>
            <div class="trend-chip">
              <small>0–15 dní · minima</small>
              <strong>${tempTrend ? this._esc(tempTrend.label) : "bez dat"}</strong>
              <span>${tempTrend?.detail ? this._esc(tempTrend.detail) : ""}</span>
            </div>
            <div class="trend-chip">
              <small>16–46 dní · minima</small>
              <strong>${tempTrend?.far ? this._esc(tempTrend.far) : "bez spolehlivého signálu"}</strong>
              <span>${tempTrend?.farDetail ? this._esc(tempTrend.farDetail) : ""}</span>
            </div>
          </div>

          <div class="irrigation irrigation-${irr.level}">
            <div class="irrigation-icon">🌱</div>
            <div>
              <small>zahradní nouzový režim</small>
              <strong>${this._esc(irr.label)}</strong>
              <span>${this._esc(irr.detail)}</span>
              <em>${this._esc(irrigationMeta)}</em>
            </div>
          </div>

          <div class="forecast-group days">
            <div class="group-title">dalších 6 dní · důraz na noční minima</div>
            <div class="forecast-days">${dailyHtml}</div>
          </div>
          ${hourlyHtml ? `<div class="forecast-group hourly-alert"><div class="group-title">rychlá změna v nejbližších hodinách</div><div class="forecast">${hourlyHtml}</div></div>` : ""}
'''
    if out.count(old_block) != 1:
        raise SystemExit(f"MAIN_BLOCK_COUNT={out.count(old_block)}")
    out = out.replace(old_block, new_block, 1)

    css_marker = '''        @container (max-width:520px) {
'''
    css_new = r'''        .trend-strip {
          display:grid; grid-template-columns:.82fr 1.09fr 1.09fr; gap:6px; margin-top:7px;
        }
        .trend-chip {
          min-width:0; padding:7px 8px; border-radius:12px;
          background:rgba(127,127,127,.06); border:1px solid rgba(127,127,127,.10);
        }
        .trend-chip.primary { background:rgba(74,108,247,.09); border-color:rgba(99,126,255,.18); }
        .trend-chip small,.trend-chip strong,.trend-chip span { display:block; min-width:0; overflow-wrap:anywhere; }
        .trend-chip small { font-size:8px; opacity:.48; text-transform:uppercase; letter-spacing:.04em; }
        .trend-chip strong { font-size:12px; line-height:1.18; margin-top:2px; }
        .trend-chip.primary strong { font-size:20px; line-height:1.05; }
        .trend-chip span { font-size:8px; opacity:.58; margin-top:2px; line-height:1.2; }

        .irrigation {
          grid-template-columns:auto minmax(0,1fr); padding:7px 9px;
          background:rgba(76,175,80,.07); border-color:rgba(76,175,80,.16);
        }
        .irrigation-icon { font-size:22px; }
        .irrigation small,.irrigation strong,.irrigation span,.irrigation em {
          display:block; min-width:0; overflow-wrap:anywhere;
        }
        .irrigation small { font-size:8px; opacity:.48; text-transform:uppercase; letter-spacing:.04em; }
        .irrigation strong { font-size:15px; line-height:1.05; margin-top:1px; }
        .irrigation span { font-size:9px; opacity:.76; margin-top:2px; }
        .irrigation em { font-size:8px; opacity:.46; font-style:normal; margin-top:2px; }
        .irrigation-1 { background:rgba(255,193,7,.08); border-color:rgba(255,193,7,.18); }
        .irrigation-2 { background:rgba(255,152,0,.10); border-color:rgba(255,152,0,.22); }
        .irrigation-3 { background:rgba(244,67,54,.11); border-color:rgba(244,67,54,.24); }

        .forecast-group.days { margin-top:7px; }
        .forecast-days { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:4px; }
        .day-cell {
          min-width:0; text-align:center; border-radius:10px; padding:5px 2px;
          background:rgba(127,127,127,.055);
        }
        .day-cell.wet { background:rgba(41,182,246,.10); }
        .day-cell small,.day-cell strong,.day-cell span,.day-cell em { display:block; min-width:0; }
        .day-cell small { font-size:8px; opacity:.58; }
        .day-cell b { display:block; font-size:18px; line-height:1.1; margin:1px 0; }
        .day-cell .night { font-size:12px; white-space:nowrap; }
        .day-cell .dayhi { font-size:8px; opacity:.5; margin-top:1px; white-space:nowrap; }
        .day-cell em { font-size:8px; opacity:.6; font-style:normal; min-height:9px; }
        .hourly-alert { margin-top:6px; padding-top:5px; border-top:1px solid var(--divider-color); }

'''
    if out.count(css_marker) != 1:
        raise SystemExit(f"CSS_MARKER_COUNT={out.count(css_marker)}")
    out = out.replace(css_marker, css_new + css_marker, 1)

    narrow_old = '''          .forecasts { grid-template-columns:1fr; }
          .forecast-cell b { font-size:17px; }
'''
    narrow_new = '''          .forecasts { grid-template-columns:1fr; }
          .forecast-cell b { font-size:17px; }
          .trend-strip { grid-template-columns:1fr; }
          .forecast-days { grid-template-columns:repeat(3,minmax(0,1fr)); }
'''
    if out.count(narrow_old) != 1:
        raise SystemExit(f"NARROW_COUNT={out.count(narrow_old)}")
    out = out.replace(narrow_old, narrow_new, 1)

    desc_old = 'description:"Kompaktní lokální počasí, radar, výhled a meteorologický odhad závlahy."'
    desc_new = 'description:"Vizuální počasí Markvarec s nočními minimy, radarovým nowcastem a nouzovým zahradním watchdogem."'
    if out.count(desc_old) != 1:
        raise SystemExit(f"DESC_COUNT={out.count(desc_old)}")
    out = out.replace(desc_old, desc_new, 1)

    if "const drops =" in out:
        raise SystemExit("OLD_DROPS_REMAINS")
    for marker in ["NEZALÉVAT", "NOUZOVĚ I OSTATNÍ", "dalších 6 dní", "16–46 dní · minima", "bez půdní sondy"]:
        if marker not in out:
            raise SystemExit(f"MISSING_MARKER {marker}")
    return out

def prepare():
    require_hashes()
    js = patch_js(WEATHER.read_text(encoding="utf-8"))
    res = RESOURCES.read_text(encoding="utf-8")
    if res.count(RESOURCE_OLD) != 1:
        raise SystemExit(f"RESOURCE_OLD_COUNT={res.count(RESOURCE_OLD)}")
    res = res.replace(RESOURCE_OLD, RESOURCE_NEW, 1)

    weather_stage = WEATHER.with_name(WEATHER.name + ".new-minima")
    outlook_stage = OUTLOOK.with_name(OUTLOOK.name + ".new-minima")
    resources_stage = RESOURCES.with_name(RESOURCES.name + ".new-minima")
    weather_stage.write_text(js, encoding="utf-8")
    outlook_stage.write_text(OUTLOOK_NEW, encoding="utf-8")
    resources_stage.write_text(res, encoding="utf-8")
    print("WEATHER_MINIMA_PREPARED")
    for p in (weather_stage, outlook_stage, resources_stage):
        print(f"{p} bytes={len(p.read_bytes())} sha256={sha(p)}")

def commit():
    require_hashes()
    stages = {
        WEATHER: WEATHER.with_name(WEATHER.name + ".new-minima"),
        OUTLOOK: OUTLOOK.with_name(OUTLOOK.name + ".new-minima"),
        RESOURCES: RESOURCES.with_name(RESOURCES.name + ".new-minima"),
    }
    for live, stage in stages.items():
        if not stage.exists():
            raise SystemExit(f"MISSING_STAGE {stage}")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for live in stages:
        backup = live.with_name(live.name + f".bak-weather-minima-{stamp}")
        shutil.copy2(live, backup)
        print(f"BACKUP={backup}")
    for live, stage in stages.items():
        os.replace(stage, live)
    print("WEATHER_MINIMA_COMMITTED")
    for p in (WEATHER, OUTLOOK, RESOURCES):
        print(f"{p} sha256={sha(p)}")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    if mode == "prepare":
        prepare()
    elif mode == "commit":
        commit()
    else:
        raise SystemExit("usage: patch_hnizdo_weather_minima.py [prepare|commit]")
