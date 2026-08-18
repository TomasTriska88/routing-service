from __future__ import annotations

from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

SYNC = Path('/config/custom_components/markvarec_camera_push_sync/__init__.py')
TEST = Path('/config/tests/test_camera_push_regression.py')
EXPECTED_SYNC_SHA = 'bec7287564434f6a68e1ed6cb95f45bcb563dae50f61e227439cf93922db30cc'
STAMP = '20260818-2146-motion-entity-sync-v2'
SYNC_BAK = SYNC.with_name(SYNC.name + '.bak-' + STAMP)
TEST_BAK = TEST.with_name(TEST.name + '.bak-' + STAMP)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected one match, got {count}')
    return text.replace(old, new, 1)


def rollback() -> None:
    if SYNC_BAK.exists():
        shutil.copy2(SYNC_BAK, SYNC)
    if TEST_BAK.exists():
        shutil.copy2(TEST_BAK, TEST)


live_sha = sha256(SYNC)
if live_sha != EXPECTED_SYNC_SHA:
    raise RuntimeError(f'live sync hash changed: {live_sha}')

shutil.copy2(SYNC, SYNC_BAK)
shutil.copy2(TEST, TEST_BAK)

try:
    s = SYNC.read_text(encoding='utf-8')
    t = TEST.read_text(encoding='utf-8')

    s = replace_one(
        s,
        'IMOU_ENTITY = "camera.branka_live"\n',
        'IMOU_ENTITY = "camera.branka_live"\nIMOU_MOTION_ENTITY = "switch.branka_motion_detect"\n',
        'motion entity constant',
    )
    s = replace_one(
        s,
        '''    motion_detect_readback: bool | None = None\n    motion_detect_error: str | None = None\n    motion_detect_wrote = False\n''',
        '''    motion_detect_readback: bool | None = None\n    motion_detect_ha_readback: bool | None = None\n    motion_detect_error: str | None = None\n    motion_detect_wrote = False\n''',
        'motion HA readback var',
    )

    old_motion = '''        # Branka detection follows the same authoritative HA security state. The\n        # Imou Life detection schedule stays static (24/7); we only enable the\n        # supported channel-level motion detector while the garden is armed.\n        # Unknown/missing security is already fail-safe ON via _security_policy().\n        try:\n            motion_detect_readback = await _imou_get_capability_switch(\n                client,\n                device_id,\n                channel_id,\n                "motionDetect",\n            )\n            if motion_detect_readback != desired:\n                await _imou_set_capability_switch(\n                    client,\n                    device_id,\n                    channel_id,\n                    "motionDetect",\n                    desired,\n                )\n                motion_detect_wrote = True\n                await asyncio.sleep(0.5)\n                motion_detect_readback = await _imou_get_capability_switch(\n                    client,\n                    device_id,\n                    channel_id,\n                    "motionDetect",\n                )\n            if motion_detect_readback != desired:\n                motion_detect_error = (\n                    "readback_mismatch:"\n                    f"desired={desired}:actual={motion_detect_readback}"\n                )\n            else:\n                motion_detect_error = None\n        except Exception as err:\n            motion_detect_error = f"{type(err).__name__}:{err}"\n            _LOGGER.exception(\n                "Failed to sync Imou motion detection policy for entry %s",\n                entry.entry_id,\n            )\n'''
    new_motion = '''        # Branka detection follows the authoritative HA security state. Keep the\n        # Imou Life schedule static at 24/7 and operate the existing HA switch so\n        # pyimouapi's cached device state and the HA entity stay truthful too.\n        # The independent cloud GET below remains the final drift/readback check.\n        # Unknown/missing security is already fail-safe ON via _security_policy().\n        try:\n            motion_detect_readback = await _imou_get_capability_switch(\n                client,\n                device_id,\n                channel_id,\n                "motionDetect",\n            )\n            motion_state_obj = hass.states.get(IMOU_MOTION_ENTITY)\n            motion_detect_ha_readback = (\n                True\n                if motion_state_obj is not None and motion_state_obj.state == "on"\n                else False\n                if motion_state_obj is not None and motion_state_obj.state == "off"\n                else None\n            )\n            if (\n                motion_detect_readback != desired\n                or motion_detect_ha_readback != desired\n            ):\n                await hass.services.async_call(\n                    "switch",\n                    "turn_on" if desired else "turn_off",\n                    {"entity_id": IMOU_MOTION_ENTITY},\n                    blocking=True,\n                )\n                motion_detect_wrote = True\n                await asyncio.sleep(0.5)\n                motion_detect_readback = await _imou_get_capability_switch(\n                    client,\n                    device_id,\n                    channel_id,\n                    "motionDetect",\n                )\n                motion_state_obj = hass.states.get(IMOU_MOTION_ENTITY)\n                motion_detect_ha_readback = (\n                    True\n                    if motion_state_obj is not None and motion_state_obj.state == "on"\n                    else False\n                    if motion_state_obj is not None and motion_state_obj.state == "off"\n                    else None\n                )\n            if (\n                motion_detect_readback != desired\n                or motion_detect_ha_readback != desired\n            ):\n                motion_detect_error = (\n                    "readback_mismatch:"\n                    f"desired={desired}:cloud={motion_detect_readback}:"\n                    f"ha={motion_detect_ha_readback}"\n                )\n            else:\n                motion_detect_error = None\n        except Exception as err:\n            motion_detect_error = f"{type(err).__name__}:{err}"\n            _LOGGER.exception(\n                "Failed to sync Imou motion detection policy for entry %s",\n                entry.entry_id,\n            )\n'''
    s = replace_one(s, old_motion, new_motion, 'motion service-path block')

    s = replace_one(
        s,
        '''            motion_detect_readback=motion_detect_readback,\n            motion_detect_error=motion_detect_error,\n''',
        '''            motion_detect_readback=motion_detect_readback,\n            motion_detect_ha_readback=motion_detect_ha_readback,\n            motion_detect_error=motion_detect_error,\n''',
        'motion HA diagnostic attr',
    )

    t = replace_one(
        t,
        'assert "if motion_detect_readback != desired:" in SYNC\n',
        'assert "motion_detect_readback != desired" in SYNC\n',
        'obsolete single-readback regression assertion',
    )
    t = replace_one(
        t,
        '''assert '"humanDetect"' not in SYNC\n\nprint("CAMERA_PUSH_REGRESSION_OK")\n''',
        '''assert '"humanDetect"' not in SYNC\nassert 'IMOU_MOTION_ENTITY = "switch.branka_motion_detect"' in SYNC\nassert 'await hass.services.async_call(' in SYNC\nassert '"turn_on" if desired else "turn_off"' in SYNC\nassert 'motion_detect_ha_readback=motion_detect_ha_readback' in SYNC\nassert 'f"desired={desired}:cloud={motion_detect_readback}:"' in SYNC\n\nprint("CAMERA_PUSH_REGRESSION_OK")\n''',
        'regression service-path assertions',
    )

    SYNC.write_text(s, encoding='utf-8')
    TEST.write_text(t, encoding='utf-8')

    subprocess.run([sys.executable, '-m', 'py_compile', str(SYNC), str(TEST)], check=True)
    subprocess.run([sys.executable, str(TEST)], check=True)
    check = subprocess.run(
        [sys.executable, '-m', 'homeassistant', '--script', 'check_config', '-c', '/config'],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(check.stdout, end='')
    if check.returncode != 0:
        raise RuntimeError(f'check_config rc={check.returncode}')
    if 'could not be validated and has been disabled' in check.stdout.lower():
        raise RuntimeError('check_config contained hidden validation warning')

    print('IMOU_MOTION_ENTITY_SYNC_PATCH_OK')
    print('SYNC_SHA256=' + sha256(SYNC))
except Exception:
    rollback()
    raise
