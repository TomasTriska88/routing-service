#!/usr/bin/env python3
from pathlib import Path
import sys, json, hashlib, shutil, os
from datetime import datetime

CONFIG=Path('/config/configuration.yaml')
WEATHER=Path('/config/www/lina-weather-card.js')
RES=Path('/config/.storage/lovelace_resources')
OUTLOOK=Path('/config/markvarec_temperature_outlook.py')
EXPECTED={
 CONFIG:'0e442076a8435d355fb594ccefd7cf5c5d84225533c47180d4680805a8707b40',
 WEATHER:'1a1f7f3cec98b351ae212acecc4d867440c9feffde4c3502da9bea0e82625174',
 RES:'f3900ee4d563bcf1bf93395f1277d3b2aa6eb7f27c5f32470c545d762f0ac1c7',
}
OUTLOOK_SOURCE=r'''#!/usr/bin/env python3
import json, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def fetch(url, timeout=25):
    req=urllib.request.Request(url,headers={'User-Agent':'Markvarec-HA/1.0'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.load(r)

def avg(values):
    vals=[float(v) for v in values if v is not None]
    return sum(vals)/len(vals) if vals else None

def medium_label(delta):
    if delta is None: return '15 dní: bez dat'
    if delta <= -3.0: return '↘ výrazné ochlazování'
    if delta <= -1.5: return '↘ ochlazování'
    if delta >= 3.0: return '↗ výrazné oteplování'
    if delta >= 1.5: return '↗ oteplování'
    return '→ bez výrazné změny'

def subseasonal_signal(anoms):
    vals=[float(x) for x in anoms if x is not None]
    if len(vals)<2:
        return ('3–6 týdnů: bez dat','EC46 nemá dost týdnů pro spolehlivou tendenci')
    pos=sum(v>=0.7 for v in vals); neg=sum(v<=-0.7 for v in vals); a=sum(vals)/len(vals)
    if pos>=2 and neg==0 and a>=0.7:
        return (f"3–6 týdnů: {'výrazně tepleji' if a>=1.5 else 'spíše tepleji'}",f'EC46 týdenní anomálie průměrně {a:+.1f} °C')
    if neg>=2 and pos==0 and a<=-0.7:
        return (f"3–6 týdnů: {'výrazně chladněji' if a<=-1.5 else 'spíše chladněji'}",f'EC46 týdenní anomálie průměrně {a:+.1f} °C')
    return ('3–6 týdnů: bez spolehlivého signálu','EC46 týdny si nejsou dost konzistentní; vzdálený trend netvrdíme')

try:
    raw=json.loads(Path('/config/.storage/core.config').read_text(encoding='utf-8'))
    cfg=raw.get('data',raw); lat=cfg['latitude']; lon=cfg['longitude']
    p=urllib.parse.urlencode({'latitude':lat,'longitude':lon,'daily':'temperature_2m_mean,temperature_2m_min,temperature_2m_max','forecast_days':16,'timezone':'Europe/Prague'})
    d=fetch('https://api.open-meteo.com/v1/forecast?'+p).get('daily',{})
    means=d.get('temperature_2m_mean',[]); mins=d.get('temperature_2m_min',[]); maxs=d.get('temperature_2m_max',[])
    start=avg(means[:3]); end=avg(means[-3:]); end_min=avg(mins[-3:]); end_max=avg(maxs[-3:])
    delta=None if start is None or end is None else end-start
    ml=medium_label(delta)
    md=(f'ke konci výhledu zhruba {end_min:.0f}–{end_max:.0f} °C' if end_min is not None and end_max is not None else (f'ke konci výhledu průměr kolem {end:.0f} °C' if end is not None else 'konkrétní teploty nejsou dostupné'))
    p=urllib.parse.urlencode({'latitude':lat,'longitude':lon,'weekly':'temperature_2m_mean,temperature_2m_anomaly','models':'ecmwf_ec46_ensemble_mean','forecast_days':46,'timezone':'Europe/Prague'})
    w=fetch('https://seasonal-api.open-meteo.com/v1/seasonal?'+p).get('weekly',{})
    times=w.get('time',[]); anomalies=w.get('temperature_2m_anomaly',[])
    sl,sd=subseasonal_signal(anomalies[2:6])
    state='stabilni'
    if delta is not None and delta<=-1.5: state='ochlazovani'
    elif delta is not None and delta>=1.5: state='oteplovani'
    print(json.dumps({'ok':True,'state':state,'medium_label':ml,'medium_detail':md,'medium_days':min(15,max(0,len(means)-1)),'subseasonal_label':sl,'subseasonal_detail':sd,'subseasonal_weeks':min(6,len(times)),'source':'Open-Meteo 0–15 d + ECMWF EC46 weeks 3–6','updated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds')},ensure_ascii=False,separators=(',',':')))
except Exception as exc:
    print(json.dumps({'ok':False,'state':'chyba','error':type(exc).__name__},ensure_ascii=False,separators=(',',':')))
'''

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    for p,s in EXPECTED.items():
        assert p.exists(),f'missing {p}'
        got=sha(p); assert got==s,f'sha mismatch {p}: {got} != {s}'

def prepare():
    verify()
    cfg=CONFIG.read_text(encoding='utf-8')
    marker='\nmarkvarec_camera_push_sync:\n'
    assert marker in cfg and 'markvarec_temperature_outlook' not in cfg
    sensor='''\n  - sensor:\n      name: "Markvarec - teplotní výhled"\n      unique_id: markvarec_temperature_outlook\n      command: "python3 /config/markvarec_temperature_outlook.py"\n      command_timeout: 35\n      scan_interval: 21600\n      value_template: "{{ value_json.state | default('bez_dat') }}"\n      availability: "{{ value_json.ok | default(false) }}"\n      json_attributes:\n        - medium_label\n        - medium_detail\n        - medium_days\n        - subseasonal_label\n        - subseasonal_detail\n        - subseasonal_weeks\n        - source\n        - updated_utc\n'''
    cfg2=cfg.replace(marker,sensor+marker,1)
    w=WEATHER.read_text(encoding='utf-8')
    a='''      radar_entity: "sensor.chmi_radar_markvarec",\n      ...config,'''; b='''      radar_entity: "sensor.chmi_radar_markvarec",\n      outlook_entity: "sensor.markvarec_teplotni_vyhled",\n      ...config,'''
    assert w.count(a)==1; w=w.replace(a,b,1)
    s=w.index('  _temperatureTrend(currentTemp) {'); e=w.index('\n  _irrigation(',s)
    method=r'''  _temperatureTrend(currentTemp) {
    const outlook = this._st(this._config.outlook_entity);
    if (outlook && !["unknown","unavailable"].includes(String(outlook.state))) {
      const a = outlook.attributes || {};
      const main = String(a.medium_label || "").trim();
      const detail = String(a.medium_detail || "").trim();
      const far = String(a.subseasonal_label || "").trim();
      const farDetail = String(a.subseasonal_detail || "").trim();
      if (main || far) {
        const icon = String(outlook.state) === "ochlazovani" ? "↘" : String(outlook.state) === "oteplovani" ? "↗" : "→";
        return { icon, label:main || "15 dní: výhled", detail, far, farDetail, longRange:true };
      }
    }
    const now = Date.now();
    const future = (this._forecast.hourly || []).filter(f => {
      const t = Date.parse(f?.datetime || "");
      return Number.isFinite(t) && t >= now - 30 * 60 * 1000 && t <= now + 8 * 60 * 60 * 1000 && Number.isFinite(Number(f?.temperature));
    });
    if (!future.length || !Number.isFinite(currentTemp)) return null;
    const target = future[Math.min(future.length - 1, 6)];
    const targetTemp = Number(target.temperature); const delta = targetTemp-currentTemp; const time=this._timeLabel(target.datetime);
    if (delta >= 1.5) return {icon:"↗",label:"krátce oteplování",detail:`do ${time} ${Math.round(targetTemp)}°`,far:"",farDetail:"",longRange:false};
    if (delta <= -1.5) return {icon:"↘",label:"krátce ochlazování",detail:`do ${time} ${Math.round(targetTemp)}°`,far:"",farDetail:"",longRange:false};
    return {icon:"→",label:"krátce stabilní",detail:`do ${time} ${Math.round(targetTemp)}°`,far:"",farDetail:"",longRange:false};
  }
'''
    w=w[:s]+method+w[e:]
    old='${tempTrend ? `<div class="temp-trend"><strong>${this._esc(tempTrend.icon+" "+tempTrend.label)}</strong> · do ${this._esc(tempTrend.time)} ${this._esc(Math.round(tempTrend.target)+"°")}</div>` : ""}'
    new='${tempTrend ? `<div class="temp-trend"><strong>${this._esc(tempTrend.label)}</strong>${tempTrend.detail ? ` · ${this._esc(tempTrend.detail)}` : ""}${tempTrend.far ? `<small>${this._esc(tempTrend.far)}${tempTrend.farDetail ? ` · ${this._esc(tempTrend.farDetail)}` : ""}</small>` : ""}</div>` : ""}'
    assert w.count(old)==1; w=w.replace(old,new,1)
    oldcss='.temp-trend strong { font-weight:700; opacity:1; }'; newcss=oldcss+'\n        .temp-trend small { display:block; margin-top:2px; font-size:9px; opacity:.72; line-height:1.2; overflow-wrap:anywhere; }'
    assert w.count(oldcss)==1; w=w.replace(oldcss,newcss,1)
    r=json.loads(RES.read_text(encoding='utf-8')); items=r.get('data',{}).get('items',[]); hits=[x for x in items if 'lina-weather-card.js' in str(x.get('url',''))]
    assert len(hits)==1 and hits[0]['url']=='/local/lina-weather-card.js?v=20260818-trend1',hits
    hits[0]['url']='/local/lina-weather-card.js?v=20260818-trend46'
    files=[(Path(str(CONFIG)+'.new-outlook'),cfg2),(Path(str(WEATHER)+'.new-outlook'),w),(Path(str(RES)+'.new-outlook'),json.dumps(r,ensure_ascii=False,separators=(',',':'))),(Path(str(OUTLOOK)+'.new-outlook'),OUTLOOK_SOURCE)]
    for p,t in files: p.write_text(t,encoding='utf-8'); print('PREPARED',p,p.stat().st_size,sha(p))

def commit():
    verify(); pairs=[(CONFIG,Path(str(CONFIG)+'.new-outlook')),(WEATHER,Path(str(WEATHER)+'.new-outlook')),(RES,Path(str(RES)+'.new-outlook')),(OUTLOOK,Path(str(OUTLOOK)+'.new-outlook'))]
    for _,n in pairs: assert n.exists(),n
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    for old,new in pairs:
        if old.exists(): shutil.copy2(old,Path(str(old)+f'.bak-outlook-{stamp}'))
        os.replace(new,old)
    print('COMMITTED',stamp)
    for old,_ in pairs: print(old,sha(old),old.stat().st_size)

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'prepare'
    {'prepare':prepare,'commit':commit}[mode]()
