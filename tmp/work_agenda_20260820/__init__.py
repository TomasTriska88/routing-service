from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

from .normalize import normalize_snapshot

DOMAIN = "markvarec_work_agenda"
SERVICE_SET_SNAPSHOT = "set_snapshot"
ENTITY_ID = "sensor.lineum_work_agenda"
STORAGE_VERSION = 1
STORAGE_KEY = "markvarec_work_agenda"
STALE_AFTER_MINUTES = 180
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)
SERVICE_SCHEMA = vol.Schema({vol.Required("snapshot"): dict})


def _attributes(snapshot: dict[str, Any], received_at: str) -> dict[str, Any]:
    return {
        "friendly_name": "Lineum – pracovní agenda",
        "icon": "mdi:briefcase-clock-outline",
        "source": "clickup",
        "source_status": snapshot["source_status"],
        "generated_at": snapshot["generated_at"],
        "last_received_at": received_at,
        "stale_after_minutes": STALE_AFTER_MINUTES,
        "open_count": snapshot["open_count"],
        "urgent_count": snapshot["urgent_count"],
        "overdue_count": snapshot["overdue_count"],
        "today_count": snapshot["today_count"],
        "mail_attention_count": snapshot["mail_attention_count"],
        "items": snapshot["items"],
    }


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load()
    if not isinstance(stored, dict):
        stored = normalize_snapshot({"source_status": "unknown"})

    received_at = datetime.now(timezone.utc).isoformat()
    hass.states.async_set(
        ENTITY_ID,
        str(stored.get("open_count", 0)),
        _attributes(stored, received_at),
    )

    async def set_snapshot(call: ServiceCall) -> None:
        try:
            normalized = normalize_snapshot(call.data["snapshot"])
        except (TypeError, ValueError) as exc:
            _LOGGER.warning("Rejected work agenda snapshot: %s", exc)
            raise vol.Invalid(str(exc)) from exc

        now = datetime.now(timezone.utc).isoformat()
        await store.async_save(normalized)
        hass.states.async_set(
            ENTITY_ID,
            str(normalized["open_count"]),
            _attributes(normalized, now),
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SNAPSHOT,
        set_snapshot,
        schema=SERVICE_SCHEMA,
    )
    return True
