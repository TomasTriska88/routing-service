#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, os, sys
from datetime import datetime

CLIMATE=Path('/config/www/lina-climate-safety-card.js')
RES=Path('/config/.storage/lovelace_resources')
EXPECTED_CLIMATE='3ccc8b71dc1a08c23d19da7ded9b79d44af99f40aee3551e340ae6f2b291d342'
EXPECTED_RES='c0baee47b0805c3e9c682412ccc944416f5d3a582b7502cda47de69defeae632'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    assert sha(CLIMATE)==EXPECTED_CLIMATE,(sha(CLIMATE),EXPECTED_CLIMATE)
    assert sha(RES)==EXPECTED_RES,(sha(RES),EXPECTED_RES)

def prepare():
    verify()
    s=CLIMATE.read_text(encoding='utf-8')
    anchor="""    const smallMammalRef = outdoorAnimalTemps.length ? Math.min(...outdoorAnimalTemps) : NaN;\n    const smallMammalRefLabel = Number.isFinite(forecast.min48) && (!Number.isFinite(outT) || forecast.min48 < outT) ? 'výhled do 48 h' : 'venku nyní';\n    const issues = [];"""
    replacement="""    const smallMammalRef = outdoorAnimalTemps.length ? Math.min(...outdoorAnimalTemps) : NaN;\n    const smallMammalRefLabel = Number.isFinite(forecast.min48) && (!Number.isFinite(outT) || forecast.min48 < outT) ? 'výhled do 48 h' : 'venku nyní';\n    // Ducks and geese sleep mainly in the outdoor aviary; some smaller birds may use the coop/goose shelter.\n    // There is no dedicated probe in their usual sleeping zone or goose shelter yet, so never present this as measured microclimate.\n    const waterfowlRef = smallMammalRef;\n    const waterfowlRefLabel = smallMammalRefLabel;\n    const weatherState = String(this._st(c.weather_entity)?.state || '');\n    const wetNow = ['rainy','pouring','snowy-rainy','hail'].includes(weatherState);\n    const exposedWindNow = Number.isFinite(gust) ? gust >= 30 : (Number.isFinite(wind) && wind >= 22);\n    const waterfowlCurrentExposure = Number.isFinite(outT) && outT <= -5 && (wetNow || exposedWindNow);\n    const issues = [];"""
    assert s.count(anchor)==1
    s=s.replace(anchor,replacement,1)

    old="""    if (Number.isFinite(coopT) && Number.isFinite(coopH)) {\n      if (coopT <= 0 && coopH >= 80) add(2, \"🐔\", \"Kurník: mráz a vysoká vlhkost\", `${coopT.toFixed(1)} °C · ${coopH.toFixed(0)} % · zvýšené riziko omrzlin; zkontrolovat suchost a ventilaci bez průvanu.`, c.coop_temp);\n      else if (coopT <= 5 && coopH >= 85) add(1, \"🐔\", \"Kurník: chladno a velmi vlhko\", `${coopT.toFixed(1)} °C · ${coopH.toFixed(0)} % · hlídat kondenzaci a suchou podestýlku.`, c.coop_temp);\n      if (coopT >= 32) add(2, \"🐔\", \"Kurník: přehřátí\", `${coopT.toFixed(1)} °C · zajistit stín a ventilaci.`, c.coop_temp);\n      else if (coopT >= 29) add(1, \"🐔\", \"Kurník: velmi teplo\", `${coopT.toFixed(1)} °C.`, c.coop_temp);\n    }\n\n"""
    new="""    if (Number.isFinite(coopT)) {\n      const coopMoist = Number.isFinite(coopH) ? ` · ${coopH.toFixed(0)} % RH` : '';\n      const coopHumidityRisk = Number.isFinite(coopH) && coopH >= 80;\n      if (coopT <= 2) add(3, \"🐔\", \"Slepice: kurník je kriticky studený\", `${coopT.toFixed(1)} °C${coopMoist} · u našeho hejna včetně malých sebritek okamžitě řešit tepelnou ochranu, suchou podestýlku a průvan${coopHumidityRisk ? '; vysoká vlhkost zvyšuje riziko omrzlin' : ''}.`, c.coop_temp);\n      else if (coopT <= 5) add(2, \"🐔\", \"Slepice: kurník je silně chladný\", `${coopT.toFixed(1)} °C${coopMoist} · zkontrolovat suchost, závětří a připravenost bezpečného přitápění${coopHumidityRisk ? '; současně je vysoká vlhkost' : ''}.`, c.coop_temp);\n      else if (coopT < 8) add(1, \"🐔\", \"Slepice: kurník chladne\", `${coopT.toFixed(1)} °C${coopMoist} · malé/lehké kusy hlídat dřív než těžká plemena.`, c.coop_temp);\n      if (coopT >= 32) add(2, \"🐔\", \"Kurník: přehřátí\", `${coopT.toFixed(1)} °C · zajistit stín a ventilaci.`, c.coop_temp);\n      else if (coopT >= 29) add(1, \"🐔\", \"Kurník: velmi teplo\", `${coopT.toFixed(1)} °C.`, c.coop_temp);\n    }\n\n    if (Number.isFinite(waterfowlRef)) {\n      const ref = `${waterfowlRef.toFixed(1)} °C · ${waterfowlRefLabel} · bez lokálního čidla v běžném nocležišti / husníku.`;\n      if (waterfowlRef <= -10 || waterfowlCurrentExposure) {\n        add(3, \"🦆\", \"Kachny + husy: kritický chlad\", `${ref} Okamžitě zkontrolovat, že mají suchý závětrný úkryt, nezamrzlou vodu a nejslabší kusy nejsou prochladlé${waterfowlCurrentExposure ? '; venku je navíc mokro nebo silný vítr' : ''}.`, c.weather_entity);\n      } else if (waterfowlRef <= -5) {\n        add(2, \"🦆\", \"Kachny + husy: silný mráz\", `${ref} Aktivně zkontrolovat nocleh, suchou podestýlku, závětří a vodu.`, c.weather_entity);\n      } else if (waterfowlRef <= 0) {\n        add(2, \"🦆\", \"Kachny + husy: mráz\", `${ref} Zkontrolovat suchý chráněný nocleh a nezamrzlou vodu; husník je závětrný, ale zatím neměřený.`, c.weather_entity);\n      } else if (waterfowlRef < 5) {\n        add(1, \"🦆\", \"Kachny + husy: chladná noc\", `${ref} Hlídat suchý úkryt a skutečné chování ptáků.`, c.weather_entity);\n      }\n    }\n\n"""
    assert s.count(old)==1
    s=s.replace(old,new,1)
    climate_new=Path(str(CLIMATE)+'.new-waterfowl'); climate_new.write_text(s,encoding='utf-8')

    r=json.loads(RES.read_text(encoding='utf-8')); items=r.get('data',{}).get('items',[]); hits=[x for x in items if 'lina-climate-safety-card.js' in str(x.get('url',''))]
    assert len(hits)==1 and hits[0]['url']=='/local/lina-climate-safety-card.js?v=20260818-v3',hits
    hits[0]['url']='/local/lina-climate-safety-card.js?v=20260818-v4'
    res_new=Path(str(RES)+'.new-waterfowl'); res_new.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('PREPARED',climate_new,climate_new.stat().st_size,sha(climate_new))
    print('PREPARED',res_new,res_new.stat().st_size,sha(res_new))

def commit():
    verify(); cn=Path(str(CLIMATE)+'.new-waterfowl'); rn=Path(str(RES)+'.new-waterfowl'); assert cn.exists() and rn.exists()
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    shutil.copy2(CLIMATE,Path(str(CLIMATE)+f'.bak-waterfowl-{stamp}')); shutil.copy2(RES,Path(str(RES)+f'.bak-waterfowl-{stamp}'))
    os.replace(cn,CLIMATE); os.replace(rn,RES)
    print('COMMITTED',stamp); print('CLIMATE',sha(CLIMATE),CLIMATE.stat().st_size); print('RES',sha(RES),RES.stat().st_size)

if __name__=='__main__': {'prepare':prepare,'commit':commit}[sys.argv[1] if len(sys.argv)>1 else 'prepare']()
