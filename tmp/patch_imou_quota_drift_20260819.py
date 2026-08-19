from __future__ import annotations

from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

SYNC = Path("/config/custom_components/markvarec_camera_push_sync/__init__.py")
TEST = Path("/config/tests/test_camera_push_regression.py")
EXPECTED_SYNC_SHA = "f4103fb5867bf3f764200ea31c548ec85c954e9124986de7fd8c7d583f5f6a54"
STAMP = "20260819-imou-quota-drift-v1"
SYNC_BAK = SYNC.with_name(SYNC.name + ".bak-" + STAMP)
TEST_BAK = TEST.with_name(TEST.name + ".bak-" + STAMP)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def rollback() -> None:
    if SYNC_BAK.exists():
        shutil.copy2(SYNC_BAK, SYNC)
    if TEST_BAK.exists():
        shutil.copy2(TEST_BAK, TEST)


if sha256(SYNC) != EXPECTED_SYNC_SHA:
    raise RuntimeError(f"live sync hash changed: {sha256(SYNC)}")

shutil.copy2(SYNC, SYNC_BAK)
shutil.copy2(TEST, TEST_BAK)

try:
    s = SYNC.read_text(encoding="utf-8")
    t = TEST.read_text(encoding="utf-8")

    sync_all_block = '''    async def _sync_all(sync_reason: str, *, force: bool = False) -> None:
        desired, security_state, policy_reason = _security_policy(hass)
        async with runtime["lock"]:
            await _sync_ezviz(
                hass,
                runtime,
                desired,
                security_state,
                policy_reason,
                sync_reason,
                force=force,
            )
            await _sync_imou(
                hass,
                runtime,
                desired,
                security_state,
                policy_reason,
                sync_reason,
                force=force,
            )

'''
    sync_helpers_block = sync_all_block + '''    async def _sync_ezviz_only(sync_reason: str, *, force: bool = False) -> None:
        desired, security_state, policy_reason = _security_policy(hass)
        async with runtime["lock"]:
            await _sync_ezviz(
                hass,
                runtime,
                desired,
                security_state,
                policy_reason,
                sync_reason,
                force=force,
            )

    async def _sync_imou_only(sync_reason: str, *, force: bool = False) -> None:
        desired, security_state, policy_reason = _security_policy(hass)
        async with runtime["lock"]:
            await _sync_imou(
                hass,
                runtime,
                desired,
                security_state,
                policy_reason,
                sync_reason,
                force=force,
            )

'''
    s = replace_one(s, sync_all_block, sync_helpers_block, "provider-only sync helpers")

    periodic_old = '''    @callback
    def _periodic(_now: Any) -> None:
        # EZVIZ push, Imou instantDisAlarm and alarm-linked deterrence
        # are re-read from the cloud. The Imou callback is owned by imou_life
        # and is deliberately never re-registered here.
        hass.async_create_task(_sync_all("periodic_drift_check"))

    runtime["unsubs"].append(
        async_track_time_interval(hass, _periodic, timedelta(minutes=5))
    )

'''
    periodic_new = '''    @callback
    def _periodic_ezviz(_now: Any) -> None:
        # Keep the existing EZVIZ five-minute drift protection. It does not
        # consume the Imou Open Platform interface-request quota.
        hass.async_create_task(_sync_ezviz_only("periodic_drift_check_ezviz"))

    runtime["unsubs"].append(
        async_track_time_interval(hass, _periodic_ezviz, timedelta(minutes=5))
    )

    @callback
    def _periodic_imou(_now: Any) -> None:
        # Imou security changes are synchronized immediately by _security_changed.
        # This is only an independent cloud drift fallback, so keep it deliberately
        # sparse: the official Imou coordinator already polls device state every
        # 15 minutes and event push handles alarm traffic without polling.
        hass.async_create_task(_sync_imou_only("periodic_drift_check_imou"))

    runtime["unsubs"].append(
        async_track_time_interval(hass, _periodic_imou, timedelta(minutes=30))
    )

    @callback
    def _imou_motion_changed(event: Any) -> None:
        # If the official 15-minute Imou poll (or a manual HA action) discovers
        # that motion detection drifted away from the authoritative security
        # policy, repair it immediately instead of waiting for the 30-minute
        # independent cloud audit. Normal attribute-only refreshes are ignored.
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        if old_state is not None and old_state.state == new_state.state:
            return
        if new_state.state not in ("on", "off"):
            return
        desired, _security_state, _policy_reason = _security_policy(hass)
        actual = new_state.state == "on"
        if actual != desired:
            hass.async_create_task(_sync_imou_only("motion_state_drift"))

    runtime["unsubs"].append(
        async_track_state_change_event(
            hass,
            [IMOU_MOTION_ENTITY],
            _imou_motion_changed,
        )
    )

'''
    s = replace_one(s, periodic_old, periodic_new, "quota-aware periodic scheduling")

    test_anchor = '''assert 'f"desired={desired}:cloud={motion_detect_readback}:"' in SYNC

print("CAMERA_PUSH_REGRESSION_OK")
'''
    test_new = '''assert 'f"desired={desired}:cloud={motion_detect_readback}:"' in SYNC
assert '_sync_ezviz_only("periodic_drift_check_ezviz")' in SYNC
assert '_sync_imou_only("periodic_drift_check_imou")' in SYNC
assert 'async_track_time_interval(hass, _periodic_ezviz, timedelta(minutes=5))' in SYNC
assert 'async_track_time_interval(hass, _periodic_imou, timedelta(minutes=30))' in SYNC
assert '_sync_all("periodic_drift_check")' not in SYNC
assert '[IMOU_MOTION_ENTITY]' in SYNC
assert '_sync_imou_only("motion_state_drift")' in SYNC
assert 'if actual != desired:' in SYNC

print("CAMERA_PUSH_REGRESSION_OK")
'''
    t = replace_one(t, test_anchor, test_new, "quota regression assertions")

    SYNC.write_text(s, encoding="utf-8")
    TEST.write_text(t, encoding="utf-8")

    subprocess.run([sys.executable, "-m", "py_compile", str(SYNC), str(TEST)], check=True)
    subprocess.run([sys.executable, str(TEST)], check=True)

    check = subprocess.run(
        [sys.executable, "-m", "homeassistant", "--script", "check_config", "-c", "/config"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(check.stdout, end="")
    if check.returncode != 0:
        raise RuntimeError(f"check_config rc={check.returncode}")
    if "could not be validated and has been disabled" in check.stdout.lower():
        raise RuntimeError("check_config contained hidden validation warning")

    print("IMOU_QUOTA_DRIFT_PATCH_OK")
    print("SYNC_SHA256=" + sha256(SYNC))
    print("TEST_SHA256=" + sha256(TEST))
except Exception:
    rollback()
    raise
