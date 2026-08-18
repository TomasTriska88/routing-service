import asyncio
import json
from pathlib import Path

from pyimouapi.device import ImouDeviceManager
from pyimouapi.openapi import ImouOpenApiClient

ENTRY_ID = "01M083FX5D21G8DAY2K3PXKY4K"
TARGET_DEVICE_ID = "35746BJPSF81815"

cfg = json.loads(Path("/config/.storage/core.config_entries").read_text(encoding="utf-8"))
entry = next(
    item for item in cfg["data"]["entries"]
    if item["entry_id"] == ENTRY_ID
)
data = entry["data"]


def pick(obj, *names):
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


async def main():
    client = ImouOpenApiClient(
        data["app_id"],
        data["app_secret"],
        data["api_url"],
    )
    manager = ImouDeviceManager(client)
    try:
        devices = await manager.async_get_devices(page_size=50)
        device = next(
            item for item in devices
            if item.device_id == TARGET_DEVICE_ID
        )

        print("TARGET_FOUND=1")
        print("MODEL=" + str(pick(device, "device_model", "_device_model")))
        print("ACCESS_TYPE=" + str(pick(device, "access_type", "_access_type")))
        print("DEVICE_ABILITY=" + str(pick(device, "device_ability", "_device_ability")))

        channels = pick(device, "channels", "_channels") or []
        print("CHANNEL_COUNT=" + str(len(channels)))
        for channel in channels:
            payload = {
                "id": pick(channel, "channel_id", "_channel_id"),
                "status": pick(channel, "channel_status", "_channel_status"),
                "ability": pick(channel, "channel_ability", "_channel_ability"),
            }
            print(
                "CHANNEL="
                + json.dumps(
                    payload,
                    ensure_ascii=False,
                    default=str,
                    sort_keys=True,
                )
            )
    finally:
        await manager.async_close()


asyncio.run(main())
