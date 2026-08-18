#!/bin/sh
set -eu

SRC_URL="https://raw.githubusercontent.com/TomasTriska88/routing-service/main/tmp/patch_hnizdo_weather_minima_irrigation_20260818.py"
SRC=/tmp/patch_hnizdo_weather_minima_irrigation_20260818.py
FIXED=/tmp/patch_hnizdo_weather_minima_irrigation_20260818.fixed.py
EXPECTED_SHA="7f40f7bbfea9d06b2b29cbbc5e60a65e2fbcc4a28c6018341563071fe37aec0f"

curl -fsSL "$SRC_URL" -o "$SRC"
[ "$(sha256sum "$SRC" | awk '{print $1}')" = "$EXPECTED_SHA" ]

python3 - "$SRC" "$FIXED" <<'PY'
from pathlib import Path
import sys
src = Path(sys.argv[1]).read_text(encoding="utf-8")

replacements = [
    (
        '    }) || abruptTempDrop || windRelevant;\n',
        '    }) || abruptTempDrop;\n',
        'hourly TDZ fix',
    ),
    (
        '    const nearestNight = daily.find(f => Number.isFinite(Number(f?.templow)));\n',
        '''    const currentHour = new Date().getHours();\n    const nearestNight = daily.find((f,i) =>\n      Number.isFinite(Number(f?.templow)) && !(i === 0 && currentHour >= 12));\n''',
        'nearest upcoming night',
    ),
    (
        '''    let level = 0;\n    const rainIncoming = radar.rainNow || Number.isFinite(radar.eta) || rain24 >= 4 || rain48 >= 7;\n    if (!rainIncoming && rain7 !== null && rain7 < 2 && rain48 < 4) level = 1;\n    if (level >= 1 && rain7 !== null && rain7 < 0.5 &&\n        ((Number.isFinite(temp) && temp >= 28) || (Number.isFinite(solar) && solar >= 600))) level = 2;\n    if (level >= 2 && rain7 !== null && rain7 < 0.2 && rain48 < 1 &&\n        Number.isFinite(temp) && temp >= 31 && Number.isFinite(solar) && solar >= 750) level = 3;\n''',
        '''    const forecastHighs = (this._forecast.daily || []).slice(0,3)\n      .map(f => Number(f?.temperature)).filter(Number.isFinite);\n    const heatMax = forecastHighs.length ? Math.max(...forecastHighs) : NaN;\n    const heatStress = (Number.isFinite(temp) && temp >= 28) ||\n      (Number.isFinite(heatMax) && heatMax >= 29) ||\n      (Number.isFinite(solar) && solar >= 600);\n    const extremeHeat = (Number.isFinite(temp) && temp >= 31) ||\n      (Number.isFinite(heatMax) && heatMax >= 32);\n\n    let level = 0;\n    const rainIncoming = radar.rainNow || Number.isFinite(radar.eta) || rain24 >= 4 || rain48 >= 7;\n    if (!rainIncoming && rain7 !== null && rain7 < 2 && rain48 < 4) level = 1;\n    if (level >= 1 && rain7 !== null && rain7 < 0.5 && heatStress) level = 2;\n    if (level >= 2 && rain7 !== null && rain7 < 0.2 && rain48 < 1 && extremeHeat) level = 3;\n''',
        'night-stable irrigation heat stress',
    ),
]

for old, new, label in replacements:
    count = src.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 occurrence, got {count}")
    src = src.replace(old, new, 1)

if '|| windRelevant' in src:
    raise SystemExit('windRelevant early reference remains')
Path(sys.argv[2]).write_text(src, encoding="utf-8")
print('WEATHER_PATCH_SOURCE_CORRECTED')
PY

python3 -m py_compile "$FIXED"
docker cp "$FIXED" homeassistant:/tmp/patch_hnizdo_weather_minima_irrigation_20260818.py
docker exec homeassistant python3 -m py_compile /tmp/patch_hnizdo_weather_minima_irrigation_20260818.py
docker exec homeassistant python3 /tmp/patch_hnizdo_weather_minima_irrigation_20260818.py prepare

docker exec homeassistant python3 -m py_compile /config/markvarec_temperature_outlook.py.new-minima
docker cp homeassistant:/config/www/lina-weather-card.js.new-minima /tmp/lina-weather-card.new-minima.js
node --check /tmp/lina-weather-card.new-minima.js

docker exec homeassistant python3 - <<'PY'
import json, subprocess
out = subprocess.check_output(['python3','/config/markvarec_temperature_outlook.py.new-minima'], text=True).strip()
print('OUTLOOK_JSON='+out)
data = json.loads(out)
assert data.get('ok') is True, data
assert data.get('basis') == 'daily_minima', data
assert data.get('medium_label'), data
assert data.get('subseasonal_label'), data
print('OUTLOOK_MINIMA_RUNTIME_OK')
PY

docker exec homeassistant python3 - <<'PY'
import json
from pathlib import Path
p = Path('/config/.storage/lovelace_resources.new-minima')
data = json.loads(p.read_text(encoding='utf-8'))
text = p.read_text(encoding='utf-8')
assert '/local/lina-weather-card.js?v=20260818-minima-irrigation-v1' in text
print('RESOURCE_STAGE_JSON_OK')
PY

grep -Fq 'NOUZOVĚ I OSTATNÍ' /tmp/lina-weather-card.new-minima.js
grep -Fq '16–46 dní · minima' /tmp/lina-weather-card.new-minima.js
grep -Fq 'dalších 6 dní · důraz na noční minima' /tmp/lina-weather-card.new-minima.js
grep -Fq 'bez půdní sondy' /tmp/lina-weather-card.new-minima.js
! grep -Fq '|| windRelevant' /tmp/lina-weather-card.new-minima.js

echo WEATHER_MINIMA_STAGE_VALIDATED
sha256sum "$FIXED" /tmp/lina-weather-card.new-minima.js
