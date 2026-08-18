from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime

CFG = Path("/config/configuration.yaml")
BRIDGE = Path("/config/custom_components/chatgpt_bridge/__init__.py")
OPS = Path("/config/custom_components/chatgpt_bridge/energy_ops.py")
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
CFG_BAK = CFG.with_name(CFG.name + f".bak-energy-{STAMP}")
BRIDGE_BAK = BRIDGE.with_name(BRIDGE.name + f".bak-energy-{STAMP}")
OPS_BAK = OPS.with_name(OPS.name + f".bak-energy-{STAMP}")
HAD_OPS = OPS.exists()

TEMPLATE_BLOCK = '\n  - sensor:\n      - name: "Elektřina - aktuální proměnná cena"\n        default_entity_id: sensor.elektrina_aktualni_promena_cena\n        unique_id: markvarec_elektrina_aktualni_promena_cena\n        unit_of_measurement: "CZK/kWh"\n        icon: mdi:cash-multiple\n        state: >-\n          {{ states(\'input_number.elektrina_promena_cena_kwh\') | float(0) | round(6) }}\n        attributes:\n          zdroj: "ČEZ faktura 08/2026"\n          produkt: "Elektřina na dobu neurčitou"\n          distribucni_sazba: "D02D"\n          poznamka: "Proměnná cena včetně DPH; fixní měsíční poplatky jsou vedeny zvlášť."\n\n      - name: "Elektřina - fixní poplatky měsíčně"\n        default_entity_id: sensor.elektrina_fixni_poplatky_mesic\n        unique_id: markvarec_elektrina_fixni_poplatky_mesic\n        unit_of_measurement: "CZK"\n        device_class: monetary\n        icon: mdi:calendar-cash\n        state: >-\n          {{ states(\'input_number.elektrina_fixni_poplatky_mesic\') | float(0) | round(2) }}\n\n      - name: "Elektřina - okamžitý náklad"\n        default_entity_id: sensor.elektrina_okamzity_naklad\n        unique_id: markvarec_elektrina_okamzity_naklad\n        unit_of_measurement: "CZK/h"\n        icon: mdi:cash-clock\n        state: >-\n          {% set p = states(\'sensor.vnitrni_rozvadec_vykon\') | float(0) %}\n          {% set price = states(\'sensor.elektrina_aktualni_promena_cena\') | float(0) %}\n          {{ ((p / 1000) * price) | round(2) }}\n\n      - name: "Elektřina - náklad tento měsíc"\n        default_entity_id: sensor.elektrina_naklad_tento_mesic\n        unique_id: markvarec_elektrina_naklad_tento_mesic\n        unit_of_measurement: "CZK"\n        device_class: monetary\n        icon: mdi:receipt-text\n        state: >-\n          {% set kwh = states(\'sensor.elektrina_spotreba_mesic\') | float(0) %}\n          {% set price = states(\'sensor.elektrina_aktualni_promena_cena\') | float(0) %}\n          {% set fixed = states(\'sensor.elektrina_fixni_poplatky_mesic\') | float(0) %}\n          {{ (kwh * price + fixed) | round(2) }}\n\n      - name: "Elektřina - efektivní cena tento měsíc"\n        default_entity_id: sensor.elektrina_efektivni_cena_mesic\n        unique_id: markvarec_elektrina_efektivni_cena_mesic\n        unit_of_measurement: "CZK/kWh"\n        icon: mdi:calculator-variant\n        state: >-\n          {% set kwh = states(\'sensor.elektrina_spotreba_mesic\') | float(0) %}\n          {% set cost = states(\'sensor.elektrina_naklad_tento_mesic\') | float(0) %}\n          {{ (cost / kwh) | round(3) if kwh > 0 else 0 }}\n\n'
INPUT_UTILITY_BLOCK = '\n  elektrina_promena_cena_kwh:\n    name: "Elektřina - proměnná cena"\n    min: 0\n    max: 20\n    step: 0.000001\n    unit_of_measurement: "CZK/kWh"\n    icon: mdi:cash\n    mode: box\n\n  elektrina_fixni_poplatky_mesic:\n    name: "Elektřina - fixní poplatky měsíčně"\n    min: 0\n    max: 2000\n    step: 0.01\n    unit_of_measurement: "CZK"\n    icon: mdi:calendar-cash\n    mode: box\n\nutility_meter:\n  elektrina_spotreba_mesic:\n    source: sensor.vnitrni_rozvadec_celkova_energie\n    name: "Elektřina - spotřeba tento měsíc"\n    cycle: monthly\n'
ENERGY_OPS = '"""Narrow Energy preferences operations for the ChatGPT bridge."""\n\nfrom __future__ import annotations\n\nfrom copy import deepcopy\nfrom typing import Any\n\nfrom homeassistant.components.energy.data import async_get_manager\nfrom homeassistant.core import HomeAssistant\n\n\nasync def async_energy_set_price_entity(\n    hass: HomeAssistant, value: dict[str, Any]\n) -> dict[str, Any]:\n    """Set one grid source to a live price entity via EnergyManager."""\n    stat_energy_from = str(value.get("stat_energy_from", "")).strip()\n    price_entity = str(value.get("entity_energy_price", "")).strip()\n\n    if not stat_energy_from or not price_entity:\n        raise ValueError(\n            "stat_energy_from and entity_energy_price are required"\n        )\n\n    price_state = hass.states.get(price_entity)\n    if price_state is None:\n        raise ValueError(f"price entity not found: {price_entity}")\n    try:\n        price_value = float(price_state.state)\n    except (TypeError, ValueError) as err:\n        raise ValueError(\n            f"price entity is not numeric: {price_entity}={price_state.state!r}"\n        ) from err\n    if price_value < 0:\n        raise ValueError("price must be non-negative")\n\n    manager = await async_get_manager(hass)\n    prefs = manager.data or manager.default_preferences()\n    sources = deepcopy(list(prefs.get("energy_sources", [])))\n\n    matches = [\n        source\n        for source in sources\n        if source.get("type") == "grid"\n        and source.get("stat_energy_from") == stat_energy_from\n    ]\n    if len(matches) != 1:\n        raise ValueError(\n            f"expected exactly one matching grid source, found {len(matches)}"\n        )\n\n    source = matches[0]\n    before_entity = source.get("entity_energy_price")\n    before_number = source.get("number_energy_price")\n    source["entity_energy_price"] = price_entity\n    source["number_energy_price"] = None\n\n    await manager.async_update({"energy_sources": sources})\n\n    return {\n        "ok": True,\n        "result": "energy_price_entity_updated",\n        "stat_energy_from": stat_energy_from,\n        "entity_energy_price": price_entity,\n        "price_value": price_value,\n        "before_entity_energy_price": before_entity,\n        "before_number_energy_price": before_number,\n    }\n'


def rollback() -> None:
    shutil.copy2(CFG_BAK, CFG)
    shutil.copy2(BRIDGE_BAK, BRIDGE)
    if HAD_OPS:
        shutil.copy2(OPS_BAK, OPS)
    else:
        OPS.unlink(missing_ok=True)


def run_checked(cmd: list[str], label: str) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed rc={proc.returncode}")


shutil.copy2(CFG, CFG_BAK)
shutil.copy2(BRIDGE, BRIDGE_BAK)
if HAD_OPS:
    shutil.copy2(OPS, OPS_BAK)

try:
    cfg = CFG.read_text(encoding="utf-8")

    if "markvarec_elektrina_aktualni_promena_cena" not in cfg:
        anchor = "\ninput_boolean:\n"
        if cfg.count(anchor) != 1:
            raise RuntimeError(f"input_boolean anchor count={cfg.count(anchor)}")
        cfg = cfg.replace(anchor, "\n" + TEMPLATE_BLOCK + "input_boolean:\n", 1)

    if "elektrina_promena_cena_kwh:" not in cfg:
        anchor = "\nshell_command:\n"
        if cfg.count(anchor) != 1:
            raise RuntimeError(f"shell_command anchor count={cfg.count(anchor)}")
        cfg = cfg.replace(anchor, "\n" + INPUT_UTILITY_BLOCK + "\nshell_command:\n", 1)

    CFG.write_text(cfg, encoding="utf-8")

    bridge = BRIDGE.read_text(encoding="utf-8")
    if 'command == "energy_set_price_entity"' not in bridge:
        anchor = '            if command == "zha_network":\n'
        if bridge.count(anchor) != 1:
            raise RuntimeError(f"zha_network anchor count={bridge.count(anchor)}")
        insert = (
            '            if command == "energy_set_price_entity":\n'
            '                from .energy_ops import async_energy_set_price_entity\n'
            '                return await asyncio.wait_for(\n'
            '                    async_energy_set_price_entity(hass, value),\n'
            '                    timeout=command_timeout,\n'
            '                )\n\n'
        )
        bridge = bridge.replace(anchor, insert + anchor, 1)
        BRIDGE.write_text(bridge, encoding="utf-8")

    OPS.write_text(ENERGY_OPS, encoding="utf-8")

    run_checked(
        [sys.executable, "-m", "py_compile", str(BRIDGE), str(OPS)],
        "py_compile",
    )
    run_checked(
        [sys.executable, "-m", "homeassistant", "--script", "check_config", "-c", "/config"],
        "check_config",
    )
except Exception:
    rollback()
    raise

print(f"ENERGY_MODEL_PATCH_OK backup_stamp={STAMP}")
