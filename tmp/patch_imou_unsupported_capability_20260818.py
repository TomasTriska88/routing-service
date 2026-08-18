from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

SYNC = Path("/config/custom_components/markvarec_camera_push_sync/__init__.py")
TEST = Path("/config/tests/test_camera_push_regression.py")
EXPECTED_SYNC_SHA256 = "484f1af4c6a403e1bb02d75ad36c909cae14662d1bd0a465fa9956273b478d02"
STAMP = "20260818-2018-imou-unsupported-capability"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

current_sha = sha256(SYNC)
if current_sha != EXPECTED_SYNC_SHA256:
    raise RuntimeError(f"source hash changed: {current_sha}")

backups = []
for path in (SYNC, TEST):
    backup = path.with_name(path.name + ".bak-" + STAMP)
    shutil.copy2(path, backup)
    backups.append((path, backup))

try:
    s = SYNC.read_text(encoding="utf-8")
    start_marker = '''        # Consumer Imou Life notification policy uses the device-level
        # one-click disarm capability. It is independent of motion detection,
        # recording, our HTTPS callback and alarm-linked deterrence.
'''
    end_marker = '''        # Callback ownership belongs exclusively to imou_life. This synchronizer
'''
    start = s.index(start_marker)
    end = s.index(end_marker, start)
    replacement = '''        # Consumer Imou Life control is attempted only when the camera itself
        # explicitly declares InstantDisAlarm. Never probe unsupported or unknown
        # capabilities on a battery camera just because the generic endpoint exists.
        desired_disarm = not desired
        consumer_app_control = "capability_unknown"
        if device_declares_instant_disarm is True:
            consumer_app_control = "instantDisAlarm"
            try:
                instant_disarm_readback = await _imou_get_capability_switch(
                    client,
                    device_id,
                    None,
                    "instantDisAlarm",
                )
                if instant_disarm_readback != desired_disarm:
                    instant_disarm_set_result = await _imou_set_capability_switch(
                        client,
                        device_id,
                        None,
                        "instantDisAlarm",
                        desired_disarm,
                    )
                    instant_disarm_wrote = True
                    await asyncio.sleep(0.5)
                    instant_disarm_readback = await _imou_get_capability_switch(
                        client,
                        device_id,
                        None,
                        "instantDisAlarm",
                    )
                if instant_disarm_readback != desired_disarm:
                    instant_disarm_error = (
                        "readback_mismatch:"
                        f"desired={desired_disarm}:actual={instant_disarm_readback}"
                    )
                else:
                    instant_disarm_error = None
            except Exception as err:
                instant_disarm_error = f"{type(err).__name__}:{err}"
        elif device_declares_instant_disarm is False:
            consumer_app_control = "unsupported_on_device"
            instant_disarm_error = "unsupported_capability"
        else:
            instant_disarm_error = (
                "capability_unknown"
                if device_metadata_error is None
                else f"capability_unknown:{device_metadata_error}"
            )

'''
    s = s[:start] + replacement + s[end:]

    old = '            consumer_app_control="instantDisAlarm",\n'
    if s.count(old) != 1:
        raise RuntimeError(f"consumer_app_control anchor count={s.count(old)}")
    s = s.replace(old, '            consumer_app_control=consumer_app_control,\n', 1)

    old_confirmation = '''            confirmation=(
                "consumer app policy confirmed by instantDisAlarm readback"
                if consumer_verified
                else "consumer app policy not confirmed; instantDisAlarm unavailable"
            ),
'''
    new_confirmation = '''            confirmation=(
                "consumer app policy confirmed by instantDisAlarm readback"
                if consumer_verified
                else "consumer app control unsupported by device capability"
                if device_declares_instant_disarm is False
                else "consumer app policy not confirmed; capability unavailable"
            ),
'''
    if s.count(old_confirmation) != 1:
        raise RuntimeError(f"confirmation anchor count={s.count(old_confirmation)}")
    s = s.replace(old_confirmation, new_confirmation, 1)
    SYNC.write_text(s, encoding="utf-8")

    t = TEST.read_text(encoding="utf-8")
    old_test = '''assert SYNC.count('"instantDisAlarm"') >= 3
assert "instant_disarm_set_result = await _imou_set_capability_switch(" in SYNC
'''
    new_test = '''assert "if device_declares_instant_disarm is True:" in SYNC
assert 'consumer_app_control = "unsupported_on_device"' in SYNC
assert 'instant_disarm_error = "unsupported_capability"' in SYNC
assert "instant_disarm_set_result = await _imou_set_capability_switch(" in SYNC
'''
    if t.count(old_test) != 1:
        raise RuntimeError(f"test anchor count={t.count(old_test)}")
    t = t.replace(old_test, new_test, 1)
    TEST.write_text(t, encoding="utf-8")

    subprocess.run([sys.executable, "-m", "py_compile", str(SYNC), str(TEST)], check=True)
    subprocess.run([sys.executable, str(TEST)], check=True)
    subprocess.run(
        [sys.executable, "-m", "homeassistant", "--script", "check_config", "-c", "/config"],
        check=True,
    )

    print("IMOU_UNSUPPORTED_CAPABILITY_PATCH_OK")
    print("SYNC_SHA256=" + sha256(SYNC))
except Exception:
    for path, backup in backups:
        shutil.copy2(backup, path)
    print("IMOU_UNSUPPORTED_CAPABILITY_PATCH_ROLLED_BACK")
    raise
