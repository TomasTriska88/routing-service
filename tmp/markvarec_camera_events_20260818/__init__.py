"""Local camera event spool for Markvarec."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.components.camera import async_get_image as async_get_camera_image
from homeassistant.components.image import ImageEntity, async_get_image as async_get_image_entity
from homeassistant.components.image.const import DATA_COMPONENT as IMAGE_DATA_COMPONENT
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

DOMAIN = "markvarec_camera_events"

EZVIZ_EVENT_IMAGE = "image.dvur_posledni_snimek_s_pohybem"
IMOU_CAMERA = "camera.branka_live"
SECURITY_ENTITY = "binary_sensor.zabezpeceni_zahrady_aktivni"

PENDING_BINARY_SENSOR = "binary_sensor.markvarec_kamerove_udalosti_ceka"
PENDING_COUNT_SENSOR = "sensor.markvarec_kamerove_udalosti_pocet"
PENDING_EVENT_SENSOR = "sensor.markvarec_kamerova_udalost"
PENDING_IMAGE_ENTITY = "image.markvarec_kamera_nezpracovana"

EVENT_DIR_NAME = "camera_events"
INDEX_NAME = "index.json"
RETENTION = timedelta(hours=48)
MAX_EVENTS = 50
EZVIZ_DEDUP_SECONDS = 20
IMOU_DEDUP_SECONDS = 60

_LOGGER = logging.getLogger(__name__)

CAPTURE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("camera", default="manual"): cv.string,
        vol.Optional("source", default="manual"): cv.string,
        vol.Optional("synthetic", default=False): cv.boolean,
    }
)
MARK_PROCESSED_SCHEMA = vol.Schema({vol.Required("event_id"): cv.string})

_ALLOWED_EVENT_KEYS = (
    "type",
    "code",
    "deviceId",
    "device_id",
    "channel",
    "alarmType",
    "alarm_type",
    "name",
    "timestamp",
    "event_id",
    "synthetic",
)


def _utcnow() -> datetime:
    return dt_util.utcnow()


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = dt_util.parse_datetime(str(value))
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    return dt_util.as_utc(parsed)


def _safe_event_data(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    safe: dict[str, Any] = {}
    for key in _ALLOWED_EVENT_KEYS:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = str(value)[:200] if isinstance(value, str) else value
    return safe


class CameraEventStore:
    """Persist bounded camera evidence and publish lightweight HA status."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.base_dir = Path(hass.config.path(EVENT_DIR_NAME))
        self.index_path = self.base_dir / INDEX_NAME
        self.events: list[dict[str, Any]] = []
        self._capture_lock = asyncio.Lock()
        self.pending_image: PendingCameraEventImage | None = None

    async def async_load(self) -> None:
        await self.hass.async_add_executor_job(self._load_sync)
        async with self._capture_lock:
            await self.hass.async_add_executor_job(self._prune_and_save_sync)
        self.publish_state()

    def _load_sync(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.events = []
            return
        try:
            raw = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            _LOGGER.error(
                "Camera event index is unreadable; starting with an empty index: %s",
                err,
            )
            self.events = []
            return
        if isinstance(raw, dict):
            raw = raw.get("events", [])
        self.events = (
            [item for item in raw if isinstance(item, dict)]
            if isinstance(raw, list)
            else []
        )

    def _write_index_sync(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "events": self.events}
        tmp_path = self.index_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp_path, self.index_path)

    def _write_image_sync(self, path: Path, content: bytes) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_bytes(content)
        os.replace(tmp_path, path)

    @staticmethod
    def _read_image_sync(path: Path) -> bytes | None:
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    @staticmethod
    def _delete_image_sync(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return

    def _prune_and_save_sync(self) -> None:
        now = _utcnow()
        keep: list[dict[str, Any]] = []
        drop_paths: list[Path] = []

        for item in self.events:
            created = _parse_datetime(item.get("created_at"))
            rel_path = item.get("image")
            path = self.base_dir / str(rel_path) if rel_path else None
            if (
                created is None
                or now - created > RETENTION
                or path is None
                or not path.exists()
            ):
                if path is not None:
                    drop_paths.append(path)
                continue
            keep.append(item)

        keep.sort(key=lambda item: str(item.get("created_at", "")))
        if len(keep) > MAX_EVENTS:
            overflow = keep[:-MAX_EVENTS]
            keep = keep[-MAX_EVENTS:]
            for item in overflow:
                rel_path = item.get("image")
                if rel_path:
                    drop_paths.append(self.base_dir / str(rel_path))

        self.events = keep
        for path in drop_paths:
            self._delete_image_sync(path)
        self._write_index_sync()

    def _recent_duplicate(self, camera: str, seconds: int) -> bool:
        cutoff = _utcnow() - timedelta(seconds=seconds)
        for item in reversed(self.events):
            if item.get("camera") != camera:
                continue
            created = _parse_datetime(item.get("created_at"))
            return created is not None and created >= cutoff
        return False

    @property
    def pending_events(self) -> list[dict[str, Any]]:
        return [item for item in self.events if not item.get("processed", False)]

    @property
    def oldest_pending(self) -> dict[str, Any] | None:
        pending = self.pending_events
        if not pending:
            return None
        return min(pending, key=lambda item: str(item.get("created_at", "")))

    async def async_read_oldest_pending_image(self) -> bytes | None:
        item = self.oldest_pending
        if not item or not item.get("image"):
            return None
        return await self.hass.async_add_executor_job(
            self._read_image_sync, self.base_dir / str(item["image"])
        )

    async def _async_fetch_entity_image(self, entity_id: str) -> tuple[str, bytes]:
        if entity_id.startswith("image."):
            image = await async_get_image_entity(self.hass, entity_id, timeout=15)
        elif entity_id.startswith("camera."):
            image = await async_get_camera_image(self.hass, entity_id, timeout=20)
        else:
            raise ServiceValidationError(
                "Only image.* and camera.* entities are supported"
            )
        if not image.content:
            raise HomeAssistantError(f"No image returned by {entity_id}")
        return image.content_type or "image/jpeg", image.content

    async def async_capture(
        self,
        entity_id: str,
        *,
        camera: str,
        source: str,
        synthetic: bool = False,
        event_data: dict[str, Any] | None = None,
        event_time: datetime | None = None,
        dedup_seconds: int = 0,
    ) -> str | None:
        async with self._capture_lock:
            if (
                not synthetic
                and dedup_seconds
                and self._recent_duplicate(camera, dedup_seconds)
            ):
                _LOGGER.debug("Skipping duplicate camera event for %s", camera)
                return None

            content_type, content = await self._async_fetch_entity_image(entity_id)
            captured_at = _utcnow()
            created_at = dt_util.as_utc(event_time) if event_time else captured_at
            suffix = ".png" if "png" in content_type.lower() else ".jpg"
            event_id = (
                f"{camera}-{created_at.strftime('%Y%m%dT%H%M%S%fZ')}-"
                f"{uuid4().hex[:6]}"
            )
            filename = f"{event_id}{suffix}"
            await self.hass.async_add_executor_job(
                self._write_image_sync, self.base_dir / filename, content
            )

            security_state = self.hass.states.get(SECURITY_ENTITY)
            item = {
                "event_id": event_id,
                "camera": camera,
                "source": source,
                "entity_id": entity_id,
                "created_at": created_at.isoformat(),
                "captured_at": captured_at.isoformat(),
                "security_state": (
                    security_state.state if security_state else "unknown"
                ),
                "content_type": content_type,
                "image": filename,
                "processed": False,
                "processed_at": None,
                "synthetic": bool(synthetic),
                "event_data": _safe_event_data(event_data),
            }
            self.events.append(item)
            await self.hass.async_add_executor_job(self._prune_and_save_sync)

        self.publish_state()
        _LOGGER.info(
            "Stored camera event %s (%s, %s bytes)", event_id, camera, len(content)
        )
        return event_id

    async def async_mark_processed(self, event_id: str) -> None:
        async with self._capture_lock:
            found = False
            for item in self.events:
                if item.get("event_id") == event_id:
                    item["processed"] = True
                    item["processed_at"] = _utcnow().isoformat()
                    found = True
                    break
            if not found:
                raise ServiceValidationError(
                    f"Camera event {event_id} was not found"
                )
            await self.hass.async_add_executor_job(self._prune_and_save_sync)
        self.publish_state()

    def publish_state(self) -> None:
        pending = self.pending_events
        oldest = self.oldest_pending

        self.hass.states.async_set(
            PENDING_BINARY_SENSOR,
            "on" if pending else "off",
            {
                "friendly_name": "Kamerové události čekají",
                "icon": "mdi:camera-alert",
                "pending_count": len(pending),
            },
        )
        self.hass.states.async_set(
            PENDING_COUNT_SENSOR,
            str(len(pending)),
            {
                "friendly_name": "Kamerové události – počet",
                "icon": "mdi:counter",
                "unit_of_measurement": "událostí",
            },
        )

        attrs: dict[str, Any] = {
            "friendly_name": "Kamerová událost – nejstarší nezpracovaná",
            "icon": "mdi:camera-clock",
            "pending_count": len(pending),
            "image_entity_id": PENDING_IMAGE_ENTITY,
        }
        state = "none"
        if oldest:
            state = str(oldest["event_id"])
            attrs.update(
                {
                    "event_id": oldest.get("event_id"),
                    "camera": oldest.get("camera"),
                    "source": oldest.get("source"),
                    "created_at": oldest.get("created_at"),
                    "captured_at": oldest.get("captured_at"),
                    "security_state": oldest.get("security_state"),
                    "synthetic": oldest.get("synthetic", False),
                }
            )
        self.hass.states.async_set(PENDING_EVENT_SENSOR, state, attrs)

        if self.pending_image is not None and self.pending_image.hass is not None:
            self.pending_image.async_write_ha_state()


class PendingCameraEventImage(ImageEntity):
    """Expose the oldest pending local frame to the existing media bridge."""

    _attr_name = "Markvarec kamera – nezpracovaná událost"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, store: CameraEventStore) -> None:
        super().__init__(hass)
        self.store = store
        self.entity_id = PENDING_IMAGE_ENTITY

    @property
    def image_last_updated(self) -> datetime | None:
        item = self.store.oldest_pending
        return _parse_datetime(item.get("created_at")) if item else None

    @property
    def content_type(self) -> str:
        item = self.store.oldest_pending
        return (
            str(item.get("content_type") or "image/jpeg")
            if item
            else "image/jpeg"
        )

    async def async_image(self) -> bytes | None:
        return await self.store.async_read_oldest_pending_image()


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Markvarec camera event spool."""
    store = CameraEventStore(hass)
    hass.data[DOMAIN] = store
    await store.async_load()

    pending_image = PendingCameraEventImage(hass, store)
    store.pending_image = pending_image
    hass.data[IMAGE_DATA_COMPONENT].async_add_entities([pending_image])

    @callback
    def _ezviz_state_changed(event: Event) -> None:
        if event.data.get("entity_id") != EZVIZ_EVENT_IMAGE:
            return
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if (
            old_state is None
            or new_state is None
            or old_state.state == new_state.state
        ):
            return
        event_time = _parse_datetime(new_state.state)
        hass.async_create_task(
            store.async_capture(
                EZVIZ_EVENT_IMAGE,
                camera="dvur",
                source="ezviz_event_image",
                event_time=event_time,
                dedup_seconds=EZVIZ_DEDUP_SECONDS,
            ),
            "Store EZVIZ camera event",
        )

    @callback
    def _imou_alarm(event: Event) -> None:
        event_data = dict(event.data)
        synthetic = bool(event_data.get("synthetic", False))
        hass.async_create_task(
            store.async_capture(
                IMOU_CAMERA,
                camera="branka",
                source="imou_life_alarm",
                synthetic=synthetic,
                event_data=event_data,
                dedup_seconds=IMOU_DEDUP_SECONDS,
            ),
            "Store Imou camera event",
        )

    unsub_ezviz = hass.bus.async_listen(EVENT_STATE_CHANGED, _ezviz_state_changed)
    unsub_imou = hass.bus.async_listen("imou_life_alarm", _imou_alarm)

    async def _capture_service(call: ServiceCall) -> None:
        await store.async_capture(
            call.data["entity_id"],
            camera=call.data["camera"],
            source=call.data["source"],
            synthetic=call.data["synthetic"],
        )

    async def _mark_processed_service(call: ServiceCall) -> None:
        await store.async_mark_processed(call.data["event_id"])

    hass.services.async_register(
        DOMAIN, "capture", _capture_service, schema=CAPTURE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        "mark_processed",
        _mark_processed_service,
        schema=MARK_PROCESSED_SCHEMA,
    )

    @callback
    def _stop(_event: Event) -> None:
        unsub_ezviz()
        unsub_imou()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop)
    store.publish_state()
    return True
