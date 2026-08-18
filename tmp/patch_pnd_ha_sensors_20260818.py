from pathlib import Path
import shutil
import subprocess
import sys
import time

CFG = Path('/config/configuration.yaml')
text = CFG.read_text(encoding='utf-8')
marker = 'unique_id: cez_namerena_data_stav'
if marker in text:
    print('PND_HA_SENSORS_ALREADY_PRESENT')
    raise SystemExit(0)

anchor = '\nmarkvarec_camera_push_sync:\n'
if text.count(anchor) != 1:
    raise SystemExit(f'Unexpected command_line end anchor count: {text.count(anchor)}')

block = r'''
  - sensor:
      name: "ČEZ - stav naměřených dat"
      unique_id: cez_namerena_data_stav
      command: "cat /config/pnd_state.json"
      command_timeout: 3
      scan_interval: 300
      value_template: "{{ value_json.status | default('chyba') }}"
      json_attributes:
        - fetched_at
        - source
        - upstream_commit
        - collector_version
        - elm
        - message
        - error

  - sensor:
      name: "ČEZ - spotřeba včera"
      unique_id: cez_spotreba_vcera
      command: "cat /config/pnd_state.json"
      command_timeout: 3
      scan_interval: 300
      unit_of_measurement: "kWh"
      device_class: energy
      state_class: measurement
      value_template: "{{ value_json.yesterday_kwh | default('unknown') }}"
      availability: "{{ value_json.status == 'ok' and value_json.yesterday_kwh is defined and value_json.yesterday_kwh is not none }}"
      json_attributes:
        - yesterday_date
        - fetched_at
        - source
        - elm

  - sensor:
      name: "ČEZ - spotřeba tento měsíc"
      unique_id: cez_spotreba_tento_mesic
      command: "cat /config/pnd_state.json"
      command_timeout: 3
      scan_interval: 300
      unit_of_measurement: "kWh"
      device_class: energy
      state_class: total
      value_template: "{{ value_json.month_kwh | default('unknown') }}"
      availability: "{{ value_json.status == 'ok' and value_json.month_kwh is defined and value_json.month_kwh is not none }}"
      json_attributes:
        - month_start
        - interval_end
        - fetched_at
        - source
        - elm
'''

stamp = time.strftime('%Y%m%d-%H%M%S')
backup = CFG.with_name(CFG.name + f'.bak-pnd-{stamp}')
shutil.copy2(CFG, backup)
CFG.write_text(text.replace(anchor, '\n' + block + anchor, 1), encoding='utf-8')

proc = subprocess.run(
    [sys.executable, '-m', 'homeassistant', '--script', 'check_config', '-c', '/config'],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
print(proc.stdout)
bad_text = 'could not be validated and has been disabled' in proc.stdout.lower()
if proc.returncode != 0 or bad_text:
    shutil.copy2(backup, CFG)
    raise SystemExit(f'HA check_config failed; restored {backup.name}')

print(f'PND_HA_SENSORS_PATCH_OK backup={backup.name}')
