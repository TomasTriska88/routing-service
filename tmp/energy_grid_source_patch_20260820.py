from pathlib import Path
from shutil import copy2

BASE = Path("/config/custom_components/chatgpt_bridge")
ENERGY = BASE / "energy_ops.py"
INIT = BASE / "__init__.py"
TEST = Path("/config/tests/test_energy_grid_source_regression.py")
SUFFIX = ".bak-energy-grid-20260820"

for path in (ENERGY, INIT):
    backup = Path(str(path) + SUFFIX)
    if not backup.exists():
        copy2(path, backup)

energy = ENERGY.read_text(encoding="utf-8")
if "async def async_energy_ensure_grid_source(" not in energy:
    marker = "\nasync def async_energy_replace_device_entities("
    if marker not in energy:
        raise RuntimeError("energy insertion marker not found")
    function = 'async def async_energy_ensure_grid_source(\n    hass: HomeAssistant, value: dict[str, Any]\n) -> dict[str, Any]:\n    """Ensure one Energy grid source exists, using native EnergyManager storage."""\n    stat_energy_from = str(value.get("stat_energy_from", "")).strip()\n    stat_rate = str(value.get("stat_rate", "")).strip()\n    price_entity = str(value.get("entity_energy_price", "")).strip()\n    name = str(value.get("name", "")).strip()\n\n    if not stat_energy_from or not stat_rate or not price_entity:\n        raise ValueError(\n            "stat_energy_from, stat_rate and entity_energy_price are required"\n        )\n\n    energy_state = hass.states.get(stat_energy_from)\n    if energy_state is None:\n        raise ValueError(f"energy entity not found: {stat_energy_from}")\n    if energy_state.attributes.get("device_class") != "energy":\n        raise ValueError(f"entity is not an energy sensor: {stat_energy_from}")\n    if energy_state.attributes.get("state_class") not in ("total", "total_increasing"):\n        raise ValueError(\n            f"energy entity must be total/total_increasing: {stat_energy_from}"\n        )\n\n    rate_state = hass.states.get(stat_rate)\n    if rate_state is None:\n        raise ValueError(f"power entity not found: {stat_rate}")\n    if rate_state.attributes.get("device_class") != "power":\n        raise ValueError(f"entity is not a power sensor: {stat_rate}")\n\n    price_state = hass.states.get(price_entity)\n    if price_state is None:\n        raise ValueError(f"price entity not found: {price_entity}")\n    try:\n        price_value = float(price_state.state)\n    except (TypeError, ValueError) as err:\n        raise ValueError(\n            f"price entity is not numeric: {price_entity}={price_state.state!r}"\n        ) from err\n    if price_value < 0:\n        raise ValueError("price must be non-negative")\n\n    if not name:\n        name = str(energy_state.attributes.get("friendly_name") or stat_energy_from)\n\n    manager = await async_get_manager(hass)\n    prefs = manager.data or manager.default_preferences()\n    sources = deepcopy(list(prefs.get("energy_sources", [])))\n\n    matches = [\n        source\n        for source in sources\n        if source.get("type") == "grid"\n        and source.get("stat_energy_from") == stat_energy_from\n    ]\n    if len(matches) > 1:\n        raise ValueError(\n            f"expected at most one matching grid source, found {len(matches)}"\n        )\n\n    created = not matches\n    changed = created\n    if created:\n        source = {\n            "type": "grid",\n            "stat_energy_from": stat_energy_from,\n            "stat_energy_to": None,\n            "stat_cost": None,\n            "stat_compensation": None,\n            "entity_energy_price": price_entity,\n            "number_energy_price": None,\n            "entity_energy_price_export": None,\n            "number_energy_price_export": None,\n            "cost_adjustment_day": 0.0,\n            "name": name,\n            "power_config": {"stat_rate": stat_rate},\n            "stat_rate": stat_rate,\n        }\n        sources.append(source)\n    else:\n        source = matches[0]\n        desired = {\n            "entity_energy_price": price_entity,\n            "number_energy_price": None,\n            "name": name,\n            "stat_rate": stat_rate,\n            "power_config": {"stat_rate": stat_rate},\n        }\n        for key, desired_value in desired.items():\n            if source.get(key) != desired_value:\n                source[key] = desired_value\n                changed = True\n\n    if changed:\n        await manager.async_update({"energy_sources": sources})\n\n    return {\n        "ok": True,\n        "result": "energy_grid_source_ensured",\n        "created": created,\n        "changed": changed,\n        "stat_energy_from": stat_energy_from,\n        "stat_rate": stat_rate,\n        "entity_energy_price": price_entity,\n        "price_value": price_value,\n        "name": name,\n        "grid_source_count": len(sources),\n    }'
    energy = energy.replace(marker, "\n" + function + marker, 1)
    ENERGY.write_text(energy, encoding="utf-8")

init = INIT.read_text(encoding="utf-8")
if 'if command == "energy_ensure_grid_source":' not in init:
    marker = '            if command == "energy_replace_device_entities":\n'
    if marker not in init:
        raise RuntimeError("dispatch insertion marker not found")
    dispatch = '            if command == "energy_ensure_grid_source":\n                from .energy_ops import async_energy_ensure_grid_source\n                return await asyncio.wait_for(\n                    async_energy_ensure_grid_source(hass, value),\n                    timeout=command_timeout,\n                )\n'
    init = init.replace(marker, dispatch + marker, 1)
    INIT.write_text(init, encoding="utf-8")

test = 'from pathlib import Path\n\nenergy = Path("/config/custom_components/chatgpt_bridge/energy_ops.py").read_text(encoding="utf-8")\ninit = Path("/config/custom_components/chatgpt_bridge/__init__.py").read_text(encoding="utf-8")\n\nassert energy.count("async def async_energy_ensure_grid_source(") == 1\nfor needle in (\n    \'value.get("stat_energy_from"\',\n    \'value.get("stat_rate"\',\n    \'value.get("entity_energy_price"\',\n    \'energy_state.attributes.get("device_class") != "energy"\',\n    \'energy_state.attributes.get("state_class") not in ("total", "total_increasing")\',\n    \'rate_state.attributes.get("device_class") != "power"\',\n    \'source.get("stat_energy_from") == stat_energy_from\',\n    \'"power_config": {"stat_rate": stat_rate}\',\n    \'await manager.async_update({"energy_sources": sources})\',\n    \'"energy_grid_source_ensured"\',\n):\n    assert needle in energy, needle\n\nassert "/config/.storage/energy" not in energy\nassert init.count(\'if command == "energy_ensure_grid_source":\') == 1\nassert "async_energy_ensure_grid_source" in init\n\nprint("ENERGY_GRID_SOURCE_REGRESSION_OK")\n'
TEST.write_text(test, encoding="utf-8")
print("ENERGY_GRID_SOURCE_PATCH_OK")
