from __future__ import annotations

from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

SYNC = Path('/config/custom_components/markvarec_camera_push_sync/__init__.py')
TEST = Path('/config/tests/test_camera_push_regression.py')
EXPECTED_SYNC_SHA = 'b3121a9c8d3338fe182e274975cf6369810200dc894360af41615c9a753d7db1'
STAMP = '20260818-2133-motion-policy'
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


if sha256(SYNC) != EXPECTED_SYNC_SHA:
    raise RuntimeError(f'live sync hash changed: {sha256(SYNC)}')

shutil.copy2(SYNC, SYNC_BAK)
shutil.copy2(TEST, TEST_BAK)

try:
    s = SYNC.read_text(encoding='utf-8')
    t = TEST.read_text(encoding='utf-8')

    s = replace_one(
        s,
        '''    deterrence_wrote = False\n    white_light_readback: bool | None = None\n''',
        '''    deterrence_wrote = False\n    motion_detect_readback: bool | None = None\n    motion_detect_error: str | None = None\n    motion_detect_wrote = False\n    white_light_readback: bool | None = None\n''',
        'motion vars',
    )

    callback_anchor = '''        else:\n            callback_errors.append(f"{entry.entry_id}:event_push_disabled")\n\n        try:\n            white_light_readback = await _imou_get_capability_switch(\n'''
    callback_replacement = '''        else:\n            callback_errors.append(f"{entry.entry_id}:event_push_disabled")\n\n        # Branka detection follows the same authoritative HA security state. The\n        # Imou Life detection schedule stays static (24/7); we only enable the\n        # supported channel-level motion detector while the garden is armed.\n        # Unknown/missing security is already fail-safe ON via _security_policy().\n        try:\n            motion_detect_readback = await _imou_get_capability_switch(\n                client,\n                device_id,\n                channel_id,\n                "motionDetect",\n            )\n            if motion_detect_readback != desired:\n                await _imou_set_capability_switch(\n                    client,\n                    device_id,\n                    channel_id,\n                    "motionDetect",\n                    desired,\n                )\n                motion_detect_wrote = True\n                await asyncio.sleep(0.5)\n                motion_detect_readback = await _imou_get_capability_switch(\n                    client,\n                    device_id,\n                    channel_id,\n                    "motionDetect",\n                )\n            if motion_detect_readback != desired:\n                motion_detect_error = (\n                    "readback_mismatch:"\n                    f"desired={desired}:actual={motion_detect_readback}"\n                )\n            else:\n                motion_detect_error = None\n        except Exception as err:\n            motion_detect_error = f"{type(err).__name__}:{err}"\n            _LOGGER.exception(\n                "Failed to sync Imou motion detection policy for entry %s",\n                entry.entry_id,\n            )\n\n        try:\n            white_light_readback = await _imou_get_capability_switch(\n'''
    s = replace_one(s, callback_anchor, callback_replacement, 'motion sync block')

    diag_anchor = '''            device_metadata_error=device_metadata_error,\n            consumer_app_readback_available=consumer_verified,\n            attempted_entries=attempted,\n'''
    diag_replacement = '''            device_metadata_error=device_metadata_error,\n            motion_policy="security_state",\n            desired_motion_detect=desired,\n            motion_detect_readback=motion_detect_readback,\n            motion_detect_error=motion_detect_error,\n            motion_detect_wrote=motion_detect_wrote,\n            detection_schedule_management="static_24_7_in_imou_life",\n            consumer_app_readback_available=consumer_verified,\n            attempted_entries=attempted,\n'''
    s = replace_one(s, diag_anchor, diag_replacement, 'motion diagnostic attrs')

    s = replace_one(
        s,
        '''            wrote_api=instant_disarm_wrote,\n''',
        '''            wrote_api=instant_disarm_wrote or motion_detect_wrote,\n''',
        'wrote_api',
    )

    old_test = '''assert "device_declares_instant_disarm=device_declares_instant_disarm" in SYNC\nassert '\"motionDetect\"' not in SYNC\n\nprint("CAMERA_PUSH_REGRESSION_OK")\n'''
    new_test = '''assert "device_declares_instant_disarm=device_declares_instant_disarm" in SYNC\nassert '\"motionDetect\"' in SYNC\nassert "if motion_detect_readback != desired:" in SYNC\nassert "desired_motion_detect=desired" in SYNC\nassert "motion_detect_readback=motion_detect_readback" in SYNC\nassert "motion_detect_error=motion_detect_error" in SYNC\nassert "motion_detect_wrote=motion_detect_wrote" in SYNC\nassert 'detection_schedule_management="static_24_7_in_imou_life"' in SYNC\nassert 'return True, state, f"fail_safe_{state}"' in SYNC\nassert "modifyDeviceAlarmPlan" not in SYNC\nassert "deviceAlarmPlan" not in SYNC\nassert '\"humanDetect\"' not in SYNC\n\nprint("CAMERA_PUSH_REGRESSION_OK")\n'''
    t = replace_one(t, old_test, new_test, 'regression assertions')

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

    print('IMOU_MOTION_POLICY_PATCH_OK')
    print('SYNC_SHA256=' + sha256(SYNC))
except Exception:
    rollback()
    raise
