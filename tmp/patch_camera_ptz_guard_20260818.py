from pathlib import Path
import hashlib
import os
import py_compile
import shutil
import time

FILES = {
    "tools": Path("/config/custom_components/markvarec_ezviz_tools/__init__.py"),
    "events": Path("/config/custom_components/markvarec_camera_events/__init__.py"),
    "automations": Path("/config/automations.yaml"),
}
EXPECTED_SHA = {
    "tools": "229edc5cf6e7a3e8f46ea74bba8cb617c6421a608c9ff36266ed05bbdd747934",
    "events": "222b3a53a6a7c797b481cc6f856f8f990ed2c868e64bf90d59d1f2a67b079db8",
}

stamp = time.strftime("%Y%m%d-%H%M%S")
backups = {}
original = {}
for key, path in FILES.items():
    original[key] = path.read_text(encoding="utf-8")
    backup = path.with_name(path.name + f".bak-ptz-guard-{stamp}")
    shutil.copy2(path, backup)
    backups[key] = backup

for key, wanted in EXPECTED_SHA.items():
    actual = hashlib.sha256(FILES[key].read_bytes()).hexdigest()
    if actual != wanted:
        raise SystemExit(f"unexpected {key} sha256: {actual}")

test_path = Path("/config/tests/test_camera_ptz_guard.py")
test_existed = test_path.exists()
test_backup = None
if test_existed:
    test_backup = test_path.with_name(test_path.name + f".bak-ptz-guard-{stamp}")
    shutil.copy2(test_path, test_backup)

try:
    tools = original["tools"]
    old = 'CURRENT_IMAGE_ENTITY = "image.markvarec_dvur_aktualni_snimek"\n'
    new = old + 'PTZ_OWN_MOTION_SENSOR = "binary_sensor.markvarec_dvur_ptz_vlastni_pohyb"\n'
    if tools.count(old) != 1:
        raise RuntimeError("tools current-image anchor mismatch")
    tools = tools.replace(old, new, 1)
    old = '    image = MarkvarecCurrentEzvizImage(hass)\n    await hass.data[IMAGE_DATA_COMPONENT].async_add_entities([image])\n\n'
    new = '''    hass.states.async_set(\n        PTZ_OWN_MOTION_SENSOR,\n        "off",\n        {\n            "friendly_name": "Dvůr PTZ – vlastní pohyb",\n            "icon": "mdi:camera-control",\n        },\n    )\n    image = MarkvarecCurrentEzvizImage(hass)\n    await hass.data[IMAGE_DATA_COMPONENT].async_add_entities([image])\n\n'''
    if tools.count(old) != 1:
        raise RuntimeError("tools setup anchor mismatch")
    tools = tools.replace(old, new, 1)

    events = original["events"]
    old = 'SECURITY_ENTITY = "binary_sensor.zabezpeceni_zahrady_aktivni"\n'
    new = old + 'PTZ_OWN_MOTION_SENSOR = "binary_sensor.markvarec_dvur_ptz_vlastni_pohyb"\n'
    if events.count(old) != 1:
        raise RuntimeError("events security anchor mismatch")
    events = events.replace(old, new, 1)
    old = '''    def _ezviz_state_changed(event: Event) -> None:\n        if event.data.get("entity_id") != EZVIZ_EVENT_IMAGE:\n            return\n        old_state = event.data.get("old_state")\n'''
    new = '''    def _ezviz_state_changed(event: Event) -> None:\n        if event.data.get("entity_id") != EZVIZ_EVENT_IMAGE:\n            return\n        ptz_state = hass.states.get(PTZ_OWN_MOTION_SENSOR)\n        if ptz_state is not None and ptz_state.state == "on":\n            _LOGGER.debug("Ignoring EZVIZ event image during Markvarec-owned PTZ motion")\n            return\n        old_state = event.data.get("old_state")\n'''
    if events.count(old) != 1:
        raise RuntimeError("events EZVIZ listener anchor mismatch")
    events = events.replace(old, new, 1)

    automations = original["automations"]
    marker = "- id: 'markvarec_security_motion_push'"
    start = automations.find(marker)
    if start < 0:
        raise RuntimeError("security motion automation not found")
    end = automations.find("\n- id:", start + 1)
    if end < 0:
        end = len(automations)
    block = automations[start:end]
    old = '''    - condition: state\n      entity_id: binary_sensor.zabezpeceni_zahrady_aktivni\n      state: "on"\n\n    - condition: template\n'''
    new = '''    - condition: state\n      entity_id: binary_sensor.zabezpeceni_zahrady_aktivni\n      state: "on"\n\n    # Vlastní PTZ pohyb potlačuje jen přesný stav ON; missing/unknown zůstává fail-secure.\n    - condition: template\n      value_template: >-\n        {{ states('binary_sensor.markvarec_dvur_ptz_vlastni_pohyb') != 'on' }}\n\n    - condition: template\n'''
    if block.count(old) != 1:
        raise RuntimeError("security guard insertion anchor mismatch")
    block = block.replace(old, new, 1)
    automations = automations[:start] + block + automations[end:]

    test_path.parent.mkdir(parents=True, exist_ok=True)
    test = '''from pathlib import Path\n\nTOOLS = Path("/config/custom_components/markvarec_ezviz_tools/__init__.py").read_text(encoding="utf-8")\nEVENTS = Path("/config/custom_components/markvarec_camera_events/__init__.py").read_text(encoding="utf-8")\nAUTOS = Path("/config/automations.yaml").read_text(encoding="utf-8")\n\nSENSOR = "binary_sensor.markvarec_dvur_ptz_vlastni_pohyb"\nassert SENSOR in TOOLS\nassert 'PTZ_OWN_MOTION_SENSOR,\\n        "off"' in TOOLS\nassert SENSOR in EVENTS\nassert 'ptz_state is not None and ptz_state.state == "on"' in EVENTS\nassert "states('binary_sensor.markvarec_dvur_ptz_vlastni_pohyb') != 'on'" in AUTOS\nassert "ptz_control_coordinates(" not in TOOLS, "Guard deployment must not add PTZ actuation yet"\n\ndef security_allows(value):\n    return value != "on"\n\nassert not security_allows("on")\nfor value in ("off", "unknown", "unavailable", None):\n    assert security_allows(value)\nprint("CAMERA_PTZ_GUARD_TESTS_OK")\n'''

    replacements = {"tools": tools, "events": events, "automations": automations}
    temps = {}
    for key, text in replacements.items():
        path = FILES[key]
        tmp = path.with_name(path.name + ".new-ptz-guard")
        tmp.write_text(text, encoding="utf-8")
        temps[key] = tmp
    test_tmp = test_path.with_name(test_path.name + ".new-ptz-guard")
    test_tmp.write_text(test, encoding="utf-8")
    py_compile.compile(str(temps["tools"]), doraise=True)
    py_compile.compile(str(temps["events"]), doraise=True)
    py_compile.compile(str(test_tmp), doraise=True)
    for key, tmp in temps.items():
        os.replace(tmp, FILES[key])
    os.replace(test_tmp, test_path)

    ns = {"__name__": "__main__"}
    exec(compile(test_path.read_text(encoding="utf-8"), str(test_path), "exec"), ns, ns)
except Exception:
    for key, backup in backups.items():
        shutil.copy2(backup, FILES[key])
    if test_existed and test_backup is not None:
        shutil.copy2(test_backup, test_path)
    elif test_path.exists():
        test_path.unlink()
    raise

print("CAMERA_PTZ_GUARD_PATCHED")
for key, path in FILES.items():
    print(f"{key.upper()}_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}")
print(f"TEST_SHA256={hashlib.sha256(test_path.read_bytes()).hexdigest()}")
for key, backup in backups.items():
    print(f"{key.upper()}_BACKUP={backup}")
