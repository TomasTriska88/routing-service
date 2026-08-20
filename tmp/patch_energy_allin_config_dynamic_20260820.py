from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global text
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)

old_block = '''      - name: "Elektřina - aktuální proměnná cena"
        default_entity_id: sensor.elektrina_aktualni_promena_cena
        unique_id: markvarec_elektrina_aktualni_promena_cena
        unit_of_measurement: "CZK/kWh"
        icon: mdi:cash-multiple
        state: >-
          {{ states('input_number.elektrina_promena_cena_kwh') | float(0) | round(6) }}
        attributes:
          zdroj: "ČEZ faktura 08/2026"
          produkt: "Elektřina na dobu neurčitou"
          distribucni_sazba: "D02D"
          poznamka: "Proměnná cena včetně DPH; fixní měsíční poplatky jsou vedeny zvlášť."

      - name: "Elektřina - fixní poplatky měsíčně"
        default_entity_id: sensor.elektrina_fixni_poplatky_mesic
        unique_id: markvarec_elektrina_fixni_poplatky_mesic
        unit_of_measurement: "CZK"
        device_class: monetary
        icon: mdi:calendar-cash
        state: >-
          {{ states('input_number.elektrina_fixni_poplatky_mesic') | float(0) | round(2) }}

      - name: "Elektřina - okamžitý náklad"
        default_entity_id: sensor.elektrina_okamzity_naklad
        unique_id: markvarec_elektrina_okamzity_naklad
        unit_of_measurement: "CZK/h"
        icon: mdi:cash-clock
        state: >-
          {% set p = states('sensor.vnitrni_rozvadec_vykon') | float(0) %}
          {% set price = states('sensor.elektrina_aktualni_promena_cena') | float(0) %}
          {{ ((p / 1000) * price) | round(2) }}

      - name: "Elektřina - náklad tento měsíc"
        default_entity_id: sensor.elektrina_naklad_tento_mesic
        unique_id: markvarec_elektrina_naklad_tento_mesic
        unit_of_measurement: "CZK"
        device_class: monetary
        icon: mdi:receipt-text
        state: >-
          {% set kwh = states('sensor.elektrina_spotreba_tento_mesic') | float(0) %}
          {% set price = states('sensor.elektrina_aktualni_promena_cena') | float(0) %}
          {% set fixed = states('sensor.elektrina_fixni_poplatky_mesic') | float(0) %}
          {{ (kwh * price + fixed) | round(2) }}

      - name: "Elektřina - efektivní cena tento měsíc"
        default_entity_id: sensor.elektrina_efektivni_cena_mesic
        unique_id: markvarec_elektrina_efektivni_cena_mesic
        unit_of_measurement: "CZK/kWh"
        icon: mdi:calculator-variant
        state: >-
          {% set kwh = states('sensor.elektrina_spotreba_tento_mesic') | float(0) %}
          {% set cost = states('sensor.elektrina_naklad_tento_mesic') | float(0) %}
          {{ (cost / kwh) | round(3) if kwh > 0 else 0 }}
'''

new_block = '''      - name: "Elektřina - variabilní složka ceny"
        default_entity_id: sensor.elektrina_aktualni_promena_cena
        unique_id: markvarec_elektrina_aktualni_promena_cena
        unit_of_measurement: "CZK/kWh"
        icon: mdi:cash-multiple
        state: >-
          {{ states('input_number.elektrina_promena_cena_kwh') | float(0) | round(6) }}
        attributes:
          zdroj: "ČEZ faktura 08/2026"
          produkt: "Elektřina na dobu neurčitou"
          distribucni_sazba: "D02D"
          poznamka: "Interní variabilní složka. Uživatelsky zobrazované ceny a náklady používají all-in model včetně průběžně nabíhajících měsíčních poplatků."

      - name: "Elektřina - fixní poplatky měsíčně"
        default_entity_id: sensor.elektrina_fixni_poplatky_mesic
        unique_id: markvarec_elektrina_fixni_poplatky_mesic
        unit_of_measurement: "CZK"
        device_class: monetary
        icon: mdi:calendar-cash
        state: >-
          {{ states('input_number.elektrina_fixni_poplatky_mesic') | float(0) | round(2) }}
        attributes:
          hodinovy_podil: >-
            {% set start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) %}
            {% if start.month == 12 %}
              {% set finish = start.replace(year=start.year + 1, month=1) %}
            {% else %}
              {% set finish = start.replace(month=start.month + 1) %}
            {% endif %}
            {% set seconds = as_timestamp(finish) - as_timestamp(start) %}
            {{ ((states('input_number.elektrina_fixni_poplatky_mesic') | float(0)) / (seconds / 3600)) | round(6) }}
          nabehlo_tento_mesic: >-
            {% set start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) %}
            {% if start.month == 12 %}
              {% set finish = start.replace(year=start.year + 1, month=1) %}
            {% else %}
              {% set finish = start.replace(month=start.month + 1) %}
            {% endif %}
            {% set seconds = as_timestamp(finish) - as_timestamp(start) %}
            {% set elapsed = as_timestamp(now()) - as_timestamp(start) %}
            {% set elapsed = [seconds, [0, elapsed] | max] | min %}
            {{ ((states('input_number.elektrina_fixni_poplatky_mesic') | float(0)) * elapsed / seconds) | round(4) }}
          podil_mesice: >-
            {% set start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) %}
            {% if start.month == 12 %}
              {% set finish = start.replace(year=start.year + 1, month=1) %}
            {% else %}
              {% set finish = start.replace(month=start.month + 1) %}
            {% endif %}
            {% set seconds = as_timestamp(finish) - as_timestamp(start) %}
            {% set elapsed = as_timestamp(now()) - as_timestamp(start) %}
            {{ ([1, [0, elapsed / seconds] | max] | min) | round(6) }}
          poznamka: "Interní rozpad fixních měsíčních poplatků pro all-in cenový model; samostatně se na Hnízdě nezobrazuje."

      - name: "Elektřina - okamžitý náklad"
        default_entity_id: sensor.elektrina_okamzity_naklad
        unique_id: markvarec_elektrina_okamzity_naklad
        unit_of_measurement: "CZK/h"
        icon: mdi:cash-clock
        availability: >-
          {{ is_number(states('sensor.vnitrni_rozvadec_vykon'))
             and is_number(states('sensor.rodicovsky_rozvadec_vykon'))
             and is_number(states('sensor.elektrina_aktualni_promena_cena'))
             and is_number(state_attr('sensor.elektrina_fixni_poplatky_mesic', 'hodinovy_podil')) }}
        state: >-
          {% set p = states('sensor.vnitrni_rozvadec_vykon') | float(0) %}
          {% set pp = states('sensor.rodicovsky_rozvadec_vykon') | float(0) %}
          {% set price = states('sensor.elektrina_aktualni_promena_cena') | float(0) %}
          {% set fixed_h = state_attr('sensor.elektrina_fixni_poplatky_mesic', 'hodinovy_podil') | float(0) %}
          {{ ((((p + pp) / 1000) * price) + fixed_h) | round(2) }}
        attributes:
          rozsah: "Markvarec celkem"
          model: "all-in: spotřeba + průběžný hodinový podíl měsíčních poplatků"

      - name: "Elektřina - náklad tento měsíc"
        default_entity_id: sensor.elektrina_naklad_tento_mesic
        unique_id: markvarec_elektrina_naklad_tento_mesic
        unit_of_measurement: "CZK"
        device_class: monetary
        icon: mdi:receipt-text
        availability: >-
          {{ is_number(states('sensor.elektrina_spotreba_tento_mesic'))
             and is_number(states('sensor.elektrina_rodice_spotreba_tento_mesic'))
             and is_number(states('sensor.elektrina_aktualni_promena_cena'))
             and is_number(state_attr('sensor.elektrina_fixni_poplatky_mesic', 'nabehlo_tento_mesic')) }}
        state: >-
          {% set tomas = states('sensor.elektrina_spotreba_tento_mesic') | float(0) %}
          {% set rodice = states('sensor.elektrina_rodice_spotreba_tento_mesic') | float(0) %}
          {% set price = states('sensor.elektrina_aktualni_promena_cena') | float(0) %}
          {% set fixed = state_attr('sensor.elektrina_fixni_poplatky_mesic', 'nabehlo_tento_mesic') | float(0) %}
          {{ (((tomas + rodice) * price) + fixed) | round(2) }}
        attributes:
          rozsah: "Markvarec celkem"
          model: "all-in month-to-date; fix nabíhá plynule podle času v kalendářním měsíci"

      - name: "Elektřina - konečná cena tento měsíc"
        default_entity_id: sensor.elektrina_efektivni_cena_mesic
        unique_id: markvarec_elektrina_efektivni_cena_mesic
        unit_of_measurement: "CZK/kWh"
        icon: mdi:calculator-variant
        availability: >-
          {{ is_number(states('sensor.elektrina_spotreba_tento_mesic'))
             and is_number(states('sensor.elektrina_rodice_spotreba_tento_mesic'))
             and is_number(states('sensor.elektrina_naklad_tento_mesic'))
             and ((states('sensor.elektrina_spotreba_tento_mesic') | float(0))
                  + (states('sensor.elektrina_rodice_spotreba_tento_mesic') | float(0))) > 0 }}
        state: >-
          {% set tomas = states('sensor.elektrina_spotreba_tento_mesic') | float(0) %}
          {% set rodice = states('sensor.elektrina_rodice_spotreba_tento_mesic') | float(0) %}
          {% set kwh = tomas + rodice %}
          {% set cost = states('sensor.elektrina_naklad_tento_mesic') | float(0) %}
          {{ (cost / kwh) | round(3) }}
        attributes:
          rozsah: "Markvarec celkem"
          model: "all-in efektivní cena month-to-date; obsahuje všechny průběžně naběhlé pravidelné i spotřební složky"
'''

replace_once(old_block, new_block, "energy finance template block")

old_um = '''utility_meter:
  elektrina_spotreba_mesic:
    source: sensor.vnitrni_rozvadec_celkova_energie
    name: "Elektřina - spotřeba tento měsíc"
    cycle: monthly
'''

new_um = '''utility_meter:
  elektrina_spotreba_mesic:
    source: sensor.vnitrni_rozvadec_celkova_energie
    name: "Elektřina - spotřeba tento měsíc"
    cycle: monthly

  elektrina_rodice_spotreba_mesic:
    source: sensor.rodicovsky_rozvadec_celkova_energie
    name: "Elektřina - rodiče spotřeba tento měsíc"
    cycle: monthly
'''

replace_once(old_um, new_um, "parent monthly utility meter")

path.write_text(text, encoding="utf-8")
print(f"ENERGY_ALLIN_CONFIG_PATCH_OK bytes={len(text.encode('utf-8'))}")
