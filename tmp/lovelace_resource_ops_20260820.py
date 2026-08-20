"""Narrow native Lovelace resource operations for the ChatGPT bridge."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.const import CONF_ID, CONF_URL
from homeassistant.core import HomeAssistant


def _validate_urls(expected_old_url: str, new_url: str) -> None:
    old = urlsplit(expected_old_url)
    new = urlsplit(new_url)
    if old.scheme or old.netloc or new.scheme or new.netloc:
        raise ValueError("only local relative Lovelace resources are allowed")
    if not old.path.startswith("/local/") or not new.path.startswith("/local/"):
        raise ValueError("only /local/ Lovelace resources are allowed")
    if old.path != new.path:
        raise ValueError("resource path must stay unchanged; only cache tag may change")
    if expected_old_url == new_url:
        raise ValueError("new_url must differ from expected_old_url")
    if not new.query:
        raise ValueError("new_url must include a cache-busting query")


async def async_lovelace_resource_update(
    hass: HomeAssistant, value: dict[str, Any]
) -> dict[str, Any]:
    """Update one existing storage-mode Lovelace resource through HA's collection API."""
    expected_old_url = str(value.get("expected_old_url", "")).strip()
    new_url = str(value.get("new_url", "")).strip()
    if not expected_old_url or not new_url:
        raise ValueError("expected_old_url and new_url are required")
    _validate_urls(expected_old_url, new_url)

    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        raise ValueError("Lovelace data is not loaded")
    if lovelace.resource_mode != MODE_STORAGE:
        raise ValueError(f"Lovelace resources are not in storage mode: {lovelace.resource_mode}")

    resource_collection = lovelace.resources
    for method in ("async_get_info", "async_items", "async_update_item"):
        if not hasattr(resource_collection, method):
            raise ValueError(f"Lovelace resource collection lacks {method}")

    await resource_collection.async_get_info()
    items = list(resource_collection.async_items() or [])
    old_matches = [item for item in items if item.get(CONF_URL) == expected_old_url]
    new_matches = [item for item in items if item.get(CONF_URL) == new_url]

    if not old_matches and len(new_matches) == 1:
        return {
            "ok": True,
            "result": "already_updated",
            "resource_id": new_matches[0].get(CONF_ID),
            "url": new_url,
        }
    if len(old_matches) != 1:
        raise ValueError(
            f"expected exactly one resource with old URL, found {len(old_matches)}"
        )
    if new_matches:
        raise ValueError(f"new URL already exists {len(new_matches)} time(s)")

    resource_id = str(old_matches[0].get(CONF_ID, "")).strip()
    if not resource_id:
        raise ValueError("matched Lovelace resource has no id")

    await resource_collection.async_update_item(resource_id, {CONF_URL: new_url})

    after = list(resource_collection.async_items() or [])
    old_after = [item for item in after if item.get(CONF_URL) == expected_old_url]
    new_after = [item for item in after if item.get(CONF_URL) == new_url]
    if old_after or len(new_after) != 1:
        raise RuntimeError(
            f"Lovelace resource readback mismatch old={len(old_after)} new={len(new_after)}"
        )

    return {
        "ok": True,
        "result": "lovelace_resource_updated",
        "resource_id": resource_id,
        "before_url": expected_old_url,
        "url": new_url,
    }
