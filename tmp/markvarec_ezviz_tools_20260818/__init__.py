"""Fixed-scope EZVIZ snapshot tools for Markvarec."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.image import ImageEntity
from homeassistant.components.image.const import DATA_COMPONENT as IMAGE_DATA_COMPONENT
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

DOMAIN = "markvarec_ezviz_tools"

DVUR_SERIAL = "BF0029567"
DVUR_CHANNEL = 1
CURRENT_IMAGE_ENTITY = "image.markvarec_dvur_aktualni_snimek"

_LOGGER = logging.getLogger(__name__)


def _find_dvur_client(hass: HomeAssistant) -> Any:
    """Return the already-authenticated EZVIZ client that owns Dvůr."""
    for entry in hass.config_entries.async_loaded_entries(domain="ezviz"):
        coordinator = getattr(entry, "runtime_data", None)
        client = getattr(coordinator, "ezviz_client", None)
        data = getattr(coordinator, "data", None)
        if client is not None and isinstance(data, dict) and DVUR_SERIAL in data:
            return client
    raise HomeAssistantError(
        "Loaded EZVIZ cloud coordinator for the Markvarec Dvůr camera was not found"
    )


class MarkvarecCurrentEzvizImage(ImageEntity):
    """Hold only the latest explicitly requested Dvůr snapshot in memory."""

    _attr_name = "Markvarec Dvůr – aktuální snímek"
    _attr_should_poll = False
    _attr_unique_id = "markvarec_dvur_current_snapshot"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)
        self.entity_id = CURRENT_IMAGE_ENTITY
        self._content: bytes | None = None
        self._content_type = "image/jpeg"
        self._updated: datetime | None = None

    @property
    def image_last_updated(self) -> datetime | None:
        return self._updated

    @property
    def content_type(self) -> str:
        return self._content_type

    async def async_image(self) -> bytes | None:
        return self._content

    @callback
    def set_snapshot(self, content: bytes, content_type: str) -> None:
        self._content = content
        self._content_type = content_type
        self._updated = dt_util.utcnow()
        self.async_write_ha_state()


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up fixed-scope Markvarec EZVIZ tools."""
    image = MarkvarecCurrentEzvizImage(hass)
    await hass.data[IMAGE_DATA_COMPONENT].async_add_entities([image])

    async def _snapshot_dvur(_call: ServiceCall) -> None:
        client = _find_dvur_client(hass)

        def _capture() -> tuple[bytes, str, bool]:
            output = BytesIO()
            result = client.save_image(DVUR_SERIAL, output, channel=DVUR_CHANNEL)
            content = output.getvalue()
            content_type = str(result.get("content_type") or "image/jpeg")
            triggered = bool(result.get("triggered_capture", False))
            return content, content_type, triggered

        content, content_type, triggered = await hass.async_add_executor_job(_capture)
        if not content:
            raise HomeAssistantError("EZVIZ returned an empty Dvůr snapshot")
        if not content.startswith(b"\xff\xd8\xff"):
            raise HomeAssistantError("EZVIZ Dvůr snapshot is not a JPEG image")
        image.set_snapshot(content, content_type)
        _LOGGER.info(
            "Captured fresh EZVIZ Dvůr snapshot (%s bytes, triggered_capture=%s)",
            len(content),
            triggered,
        )

    hass.services.async_register(DOMAIN, "snapshot_dvur", _snapshot_dvur)
    return True
