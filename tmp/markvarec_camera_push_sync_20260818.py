"""Keep vendor camera app notifications aligned with Markvarec security."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.components import webhook
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)

DOMAIN = "markvarec_camera_push_sync"
SECURITY_ENTITY = "binary_sensor.zabezpeceni_zahrady_aktivni"
EZVIZ_ENTITY = "camera.dvur"
EZVIZ_DIAG = "binary_sensor.markvarec_ezviz_app_push"
IMOU_DIAG = "binary_sensor.markvarec_imou_app_push"
EZVIZ_DOMAIN = "ezviz"
IMOU_DOMAIN = "imou_life"
_LOGGER = logging.getLogger(__name__)


def _security_policy(hass: HomeAssistant) -> tuple[bool, str, str]:
    state_obj = hass.states.get(SECURITY_ENTITY)
    state = state_obj.state if state_obj is not None else "missing"
    if state == "off":
        return False, state, "security_off"
    if state == "on":
        return True, state, "security_on"
    return True, state, f"fail_safe_{state}"


def _set_diag(
    hass: HomeAssistant,
    entity_id: str,
    state: str,
    *,
    desired: bool,
    security_state: str,
    reason: str,
    provider: str,
    **attrs: Any,
) -> None:
    data = {
        "friendly_name": f"{provider} app - bezpecnostni notifikace",
        "desired_push": desired,
        "security_entity": SECURITY_ENTITY,
        "security_state": security_state,
        "policy_reason": reason,
        "fail_safe": security_state not in ("on", "off"),
    }
    data.update(attrs)
    hass.states.async_set(entity_id, state, data)


def _ezviz_serial(hass: HomeAssistant) -> str | None:
    ent = er.async_get(hass).async_get(EZVIZ_ENTITY)
    if ent is None or ent.device_id is None:
        return None
    dev = dr.async_get(hass).async_get(ent.device_id)
    if dev is None:
        return None
    for domain, identifier in dev.identifiers:
        if domain == EZVIZ_DOMAIN:
            return str(identifier)
    return None


def _ezviz_cloud_push(coordinator: Any, serial: str) -> bool | None:
    data = getattr(coordinator, "data", None)
    if not isinstance(data, dict):
        return None
    item = data.get(serial)
    if not isinstance(item, dict):
        return None
    value = item.get("push_notify_alarm")
    return value if isinstance(value, bool) else None


async def _sync_ezviz(
    hass: HomeAssistant,
    runtime: dict[str, Any],
    desired: bool,
    security_state: str,
    policy_reason: str,
    sync_reason: str,
    *,
    force: bool,
) -> None:
    serial = _ezviz_serial(hass)
    if not serial:
        _set_diag(
            hass,
            EZVIZ_DIAG,
            "unavailable",
            desired=desired,
            security_state=security_state,
            reason=policy_reason,
            provider="EZVIZ",
            sync_reason=sync_reason,
            error="camera.dvur serial not found",
        )
        return

    coordinator = None
    for entry in hass.config_entries.async_entries(EZVIZ_DOMAIN):
        candidate = getattr(entry, "runtime_data", None)
        data = getattr(candidate, "data", None)
        if isinstance(data, dict) and serial in data:
            coordinator = candidate
            break

    if coordinator is None:
        _set_diag(
            hass,
            EZVIZ_DIAG,
            "unavailable",
            desired=desired,
            security_state=security_state,
            reason=policy_reason,
            provider="EZVIZ",
            sync_reason=sync_reason,
            serial=serial,
            error="EZVIZ runtime not ready",
        )
        return

    client = getattr(coordinator, "ezviz_client", None)
    if client is None:
        _set_diag(
            hass,
            EZVIZ_DIAG,
            "unavailable",
            desired=desired,
            security_state=security_state,
            reason=policy_reason,
            provider="EZVIZ",
            sync_reason=sync_reason,
            serial=serial,
            error="EZVIZ client missing",
        )
        return

    current = _ezviz_cloud_push(coordinator, serial)
    needs_write = force or current is None or current != desired

    try:
        if needs_write:
            # pyezviz do_not_disturb=True suppresses phone notifications while
            # alarm events continue to be recorded in the vendor app.
            await hass.async_add_executor_job(
                client.do_not_disturb,
                serial,
                int(not desired),
            )
            await coordinator.async_refresh()
            current = _ezviz_cloud_push(coordinator, serial)
            if current != desired:
                await asyncio.sleep(1)
                await coordinator.async_refresh()
                current = _ezviz_cloud_push(coordinator, serial)

        runtime["ezviz_last_desired"] = desired
        state = "on" if current is True else "off" if current is False else "unavailable"
        _set_diag(
            hass,
            EZVIZ_DIAG,
            state,
            desired=desired,
            security_state=security_state,
            reason=policy_reason,
            provider="EZVIZ",
            sync_reason=sync_reason,
            serial=serial,
            do_not_disturb=not desired,
            cloud_readback=current,
            wrote_api=needs_write,
        )
        if current is not None and current != desired:
            _LOGGER.warning(
                "EZVIZ app push readback mismatch: desired=%s actual=%s",
                desired,
                current,
            )
    except Exception as err:
        _LOGGER.exception("Failed to sync EZVIZ app notification policy")
        _set_diag(
            hass,
            EZVIZ_DIAG,
            "unavailable",
            desired=desired,
            security_state=security_state,
            reason=policy_reason,
            provider="EZVIZ",
            sync_reason=sync_reason,
            serial=serial,
            error=f"{type(err).__name__}: {err}",
        )


async def _sync_imou(
    hass: HomeAssistant,
    runtime: dict[str, Any],
    desired: bool,
    security_state: str,
    policy_reason: str,
    sync_reason: str,
    *,
    force: bool,
) -> None:
    # Import from the installed official integration so callback flags and
    # option names stay identical to its own event_push implementation.
    from custom_components.imou_life.const import (
        PARAM_ENABLE_EVENT_PUSH,
        PARAM_EVENT_PUSH_TYPES,
        PARAM_WEBHOOK_ID,
        PARAM_WEBHOOK_URL,
        event_push_types_to_callback_flags,
    )

    if not force and runtime.get("imou_last_desired") is desired:
        _set_diag(
            hass,
            IMOU_DIAG,
            "on" if desired else "off",
            desired=desired,
            security_state=security_state,
            reason=policy_reason,
            provider="Imou",
            sync_reason=sync_reason,
            base_push="1" if desired else "2",
            wrote_api=False,
            confirmation="last successful API write",
        )
        return

    attempted = 0
    successes = 0
    errors: list[str] = []

    for entry in hass.config_entries.async_entries(IMOU_DOMAIN):
        if not bool(entry.options.get(PARAM_ENABLE_EVENT_PUSH)):
            continue
        runtime_data = getattr(entry, "runtime_data", None)
        client = getattr(runtime_data, "client", None)
        if client is None:
            errors.append(f"{entry.entry_id}:runtime_not_ready")
            continue

        attempted += 1
        webhook_id = entry.data.get(PARAM_WEBHOOK_ID, "")
        if not webhook_id:
            errors.append(f"{entry.entry_id}:missing_webhook_id")
            continue

        try:
            callback_url = (
                entry.options.get(PARAM_WEBHOOK_URL)
                or webhook.async_generate_url(hass, webhook_id)
            )
            raw_types = entry.options.get(PARAM_EVENT_PUSH_TYPES, [])
            callback_flags = event_push_types_to_callback_flags(list(raw_types))
            await client.async_set_message_callback(
                status="on",
                callback_url=callback_url,
                callback_flag=callback_flags if callback_flags else None,
                base_push="1" if desired else "2",
            )
            successes += 1
        except Exception as err:
            errors.append(f"{entry.entry_id}:{type(err).__name__}")
            _LOGGER.exception(
                "Failed to sync Imou app notification policy for entry %s",
                entry.entry_id,
            )

    if successes:
        runtime["imou_last_desired"] = desired
        _set_diag(
            hass,
            IMOU_DIAG,
            "on" if desired else "off",
            desired=desired,
            security_state=security_state,
            reason=policy_reason,
            provider="Imou",
            sync_reason=sync_reason,
            base_push="1" if desired else "2",
            attempted_entries=attempted,
            synced_entries=successes,
            errors=errors,
            wrote_api=True,
            confirmation="Open Platform callback API write",
        )
        _LOGGER.info(
            "Imou app push synced=%s basePush=%s reason=%s",
            desired,
            "1" if desired else "2",
            sync_reason,
        )
    else:
        _set_diag(
            hass,
            IMOU_DIAG,
            "unavailable",
            desired=desired,
            security_state=security_state,
            reason=policy_reason,
            provider="Imou",
            sync_reason=sync_reason,
            attempted_entries=attempted,
            errors=errors or ["no event-push enabled Imou entry ready"],
        )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Markvarec vendor notification synchronization."""
    if DOMAIN in hass.data:
        return True

    runtime: dict[str, Any] = {
        "lock": asyncio.Lock(),
        "imou_last_desired": None,
        "ezviz_last_desired": None,
        "unsubs": [],
    }
    hass.data[DOMAIN] = runtime

    async def _sync_all(sync_reason: str, *, force: bool = False) -> None:
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

    @callback
    def _security_changed(event: Any) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        if old_state is not None and old_state.state == new_state.state:
            return
        hass.async_create_task(_sync_all("security_state_change"))

    runtime["unsubs"].append(
        async_track_state_change_event(
            hass,
            [SECURITY_ENTITY],
            _security_changed,
        )
    )

    @callback
    def _periodic(_now: Any) -> None:
        # EZVIZ has a cloud readback and therefore repairs vendor-side drift.
        # Imou avoids periodic API writes unless its desired policy changed.
        hass.async_create_task(_sync_all("periodic_drift_check"))

    runtime["unsubs"].append(
        async_track_time_interval(hass, _periodic, timedelta(minutes=5))
    )

    async def _provider_entry_updated(_hass: HomeAssistant, _entry: Any) -> None:
        @callback
        def _later(_now: Any) -> None:
            runtime["imou_last_desired"] = None
            hass.async_create_task(_sync_all("provider_entry_update", force=True))

        async_call_later(hass, 8, _later)

    for provider in (EZVIZ_DOMAIN, IMOU_DOMAIN):
        for entry in hass.config_entries.async_entries(provider):
            runtime["unsubs"].append(
                entry.add_update_listener(_provider_entry_updated)
            )

    @callback
    def _startup(_now: Any) -> None:
        hass.async_create_task(_sync_all("startup", force=True))

    async_call_later(hass, 5, _startup)

    # Bounded retries cover provider config entries that finish loading later.
    for delay in (15, 45, 120):
        @callback
        def _retry(_now: Any, delay_s: int = delay) -> None:
            ez = hass.states.get(EZVIZ_DIAG)
            im = hass.states.get(IMOU_DIAG)
            if (
                ez is None
                or im is None
                or ez.state == "unavailable"
                or im.state == "unavailable"
            ):
                hass.async_create_task(
                    _sync_all(f"startup_retry_{delay_s}", force=True)
                )

        async_call_later(hass, delay, _retry)

    return True
