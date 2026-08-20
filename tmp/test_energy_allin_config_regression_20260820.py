from pathlib import Path

cfg = Path("/config/configuration.yaml").read_text(encoding="utf-8")

def block_between(start_marker: str, end_marker: str) -> str:
    start = cfg.index(start_marker)
    end = cfg.index(end_marker, start)
    return cfg[start:end]

fixed = block_between('      - name: "Elektřina - fixní poplatky měsíčně"', '      - name: "Elektřina - okamžitý náklad"')
assert "hodinovy_podil:" in fixed
assert "nabehlo_tento_mesic:" in fixed
assert "podil_mesice:" in fixed
assert "now().replace(day=1" in fixed
assert "as_timestamp(finish) - as_timestamp(start)" in fixed

instant = block_between('      - name: "Elektřina - okamžitý náklad"', '      - name: "Elektřina - náklad tento měsíc"')
assert "sensor.vnitrni_rozvadec_vykon" in instant
assert "sensor.rodicovsky_rozvadec_vykon" in instant
assert "sensor.elektrina_aktualni_promena_cena" in instant
assert "state_attr('sensor.elektrina_fixni_poplatky_mesic', 'hodinovy_podil')" in instant
assert 'rozsah: "Markvarec celkem"' in instant
assert "all-in" in instant

month = block_between('      - name: "Elektřina - náklad tento měsíc"', '      - name: "Elektřina - konečná cena tento měsíc"')
assert "sensor.elektrina_spotreba_tento_mesic" in month
assert "sensor.elektrina_rodice_spotreba_tento_mesic" in month
assert "state_attr('sensor.elektrina_fixni_poplatky_mesic', 'nabehlo_tento_mesic')" in month
assert "Markvarec celkem" in month

effective = block_between('      - name: "Elektřina - konečná cena tento měsíc"', "\nsensor:")
assert "default_entity_id: sensor.elektrina_efektivni_cena_mesic" in effective
assert "sensor.elektrina_spotreba_tento_mesic" in effective
assert "sensor.elektrina_rodice_spotreba_tento_mesic" in effective
assert "sensor.elektrina_naklad_tento_mesic" in effective
assert "(cost / kwh)" in effective
assert "all-in" in effective

utility = block_between("utility_meter:", "\nshell_command:")
assert "elektrina_rodice_spotreba_mesic:" in utility
assert "source: sensor.rodicovsky_rozvadec_celkova_energie" in utility
assert 'name: "Elektřina - rodiče spotřeba tento měsíc"' in utility

variable = block_between('      - name: "Elektřina - variabilní složka ceny"', '      - name: "Elektřina - fixní poplatky měsíčně"')
assert "Interní variabilní složka" in variable
assert "all-in model" in variable

assert "{% set fixed = states('sensor.elektrina_fixni_poplatky_mesic') | float(0) %}" not in month
assert "{% set kwh = states('sensor.elektrina_spotreba_tento_mesic') | float(0) %}\n          {% set cost" not in effective

print("ENERGY_ALLIN_CONFIG_REGRESSION_OK")
