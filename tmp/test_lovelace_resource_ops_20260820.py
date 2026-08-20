import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE

MODULE = Path("/config/custom_components/chatgpt_bridge/lovelace_ops.py")
INIT = Path("/config/custom_components/chatgpt_bridge/__init__.py")
spec = importlib.util.spec_from_file_location("lovelace_ops_under_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

class FakeResources:
    def __init__(self):
        self.data = [
            {"id": "abc", "url": "/local/lina-home-card.js?v=old", "type": "module"},
            {"id": "other", "url": "/local/other-card.js?v=1", "type": "module"},
        ]

    async def async_get_info(self):
        return {"resources": len(self.data)}

    def async_items(self):
        return list(self.data)

    async def async_update_item(self, item_id, updates):
        for item in self.data:
            if item["id"] == item_id:
                item.update(updates)
                return item
        raise KeyError(item_id)

async def main():
    resources = FakeResources()
    hass = SimpleNamespace(data={
        LOVELACE_DATA: SimpleNamespace(resource_mode=MODE_STORAGE, resources=resources)
    })
    result = await mod.async_lovelace_resource_update(hass, {
        "expected_old_url": "/local/lina-home-card.js?v=old",
        "new_url": "/local/lina-home-card.js?v=new",
    })
    assert result["result"] == "lovelace_resource_updated", result
    assert resources.data[0]["url"] == "/local/lina-home-card.js?v=new"

    result2 = await mod.async_lovelace_resource_update(hass, {
        "expected_old_url": "/local/lina-home-card.js?v=old",
        "new_url": "/local/lina-home-card.js?v=new",
    })
    assert result2["result"] == "already_updated", result2

    try:
        await mod.async_lovelace_resource_update(hass, {
            "expected_old_url": "/local/lina-home-card.js?v=new",
            "new_url": "/local/different-card.js?v=2",
        })
    except ValueError as exc:
        assert "path must stay unchanged" in str(exc)
    else:
        raise AssertionError("different resource path was not rejected")

asyncio.run(main())

source = MODULE.read_text(encoding="utf-8")
init = INIT.read_text(encoding="utf-8")
assert "/config/.storage" not in source
assert "async_update_item(resource_id" in source
assert "LOVELACE_DATA" in source and "MODE_STORAGE" in source
assert init.count('if command == "lovelace_resource_update":') == 1
assert "async_lovelace_resource_update" in init
print("LOVELACE_RESOURCE_OPS_REGRESSION_OK")
