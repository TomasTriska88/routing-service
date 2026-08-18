from pathlib import Path
import hashlib, os, shutil, subprocess, time, yaml

SCRIPTS = Path("/config/scripts.yaml")
AUTOMATIONS = Path("/config/automations.yaml")
TEST = "/config/tests/test_fan_regression.py"
EXPECTED_SCRIPTS = "52afc0c1f454118097a9e2a3b2e72f53cb3e5b718e15a9be4899eff11c42c5ed"
EXPECTED_AUTOMATIONS = "f5e548c4bfb60749b10f17e5243dc02679b9d3a32acc2027267c3687bd53e5c6"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

if sha(SCRIPTS) != EXPECTED_SCRIPTS or sha(AUTOMATIONS) != EXPECTED_AUTOMATIONS:
    raise SystemExit("PRECONDITION_SHA_MISMATCH")

s = SCRIPTS.read_text()
a = AUTOMATIONS.read_text()

old_desc = '  description: "Best-effort opakované vypnutí cloudové Tuya zásuvky větráku. Běží dál i když HA po prvním pokusu už chybně hlásí off; není náhradou nezávislého fyzického readbacku."'
new_desc = '  description: "Best-effort opakované vypnutí cloudové Tuya zásuvky větráku. Další retry proběhne jen pokud fan stále hlásí off a oba 9min ochranné timery jsou idle; nové OFF→ON tím nemůže přebít rozběhnutý starý OFF."'
if s.count(old_desc) != 1:
    raise SystemExit("OFF_DESCRIPTION_ANCHOR_MISMATCH")
s = s.replace(old_desc, new_desc, 1)

guards = '''    - condition: state
      entity_id: fan.loznice_vetrak_loznice_zasuvka_1
      state: "off"
    - condition: state
      entity_id: timer.loznice_vetrak_minimalni_beh
      state: "idle"
    - condition: state
      entity_id: timer.loznice_vetrak_rucni
      state: "idle"
'''
for delay in ("00:00:03", "00:00:04"):
    old = f'    - delay: "{delay}"\n    - action: fan.turn_off'
    new = f'    - delay: "{delay}"\n' + guards + '    - action: fan.turn_off'
    if s.count(old) != 1:
        raise SystemExit(f"OFF_RETRY_ANCHOR_MISMATCH_{delay}")
    s = s.replace(old, new, 1)

start = a.find("- id: markvarec_loznice_vetrak_manualni_13min\n")
if start < 0:
    raise SystemExit("MANUAL_AUTOMATION_NOT_FOUND")
end = a.find("\n- id:", start + 1)
if end < 0:
    end = len(a)
section = a[start:end]
old = "  actions:\n    - action: timer.start\n"
new = '''  actions:
    - action: script.turn_off
      target:
        entity_id: script.loznice_vetrak_vypnout_spolehlive
    - action: timer.start
'''
if section.count(old) != 1:
    raise SystemExit("MANUAL_ACTION_ANCHOR_MISMATCH")
section = section.replace(old, new, 1)
a = a[:start] + section + a[end:]

yaml.safe_load(s)
yaml.safe_load(a)

stamp = time.strftime("%Y%m%d-%H%M%S")
sb = SCRIPTS.with_name(f"scripts.yaml.bak-fan-race-{stamp}")
ab = AUTOMATIONS.with_name(f"automations.yaml.bak-fan-race-{stamp}")
shutil.copy2(SCRIPTS, sb)
shutil.copy2(AUTOMATIONS, ab)

try:
    st = SCRIPTS.with_name("scripts.yaml.new-fan-race")
    at = AUTOMATIONS.with_name("automations.yaml.new-fan-race")
    st.write_text(s)
    at.write_text(a)
    os.replace(st, SCRIPTS)
    os.replace(at, AUTOMATIONS)
    subprocess.run(["python3", TEST], check=True)
except Exception:
    shutil.copy2(sb, SCRIPTS)
    shutil.copy2(ab, AUTOMATIONS)
    raise

print("FAN_RACE_PATCHED")
print("SCRIPTS_SHA=" + sha(SCRIPTS))
print("AUTOMATIONS_SHA=" + sha(AUTOMATIONS))
print("SCRIPTS_BACKUP=" + str(sb))
print("AUTOMATIONS_BACKUP=" + str(ab))
