from pathlib import Path
import os, re, hashlib

ROOT = Path(os.environ.get("ROOT", "/config"))
CFG = ROOT / "configuration.yaml"
AUTO = ROOT / "automations.yaml"
CARD = ROOT / "www" / "lina-rainwater-card.js"

cfg = CFG.read_text(encoding="utf-8")
auto = AUTO.read_text(encoding="utf-8")
card = CARD.read_text(encoding="utf-8")

def require(cond, msg):
    if not cond:
        raise SystemExit(msg)

require("destovka_odber_prutok_l_min:" not in cfg, "flow helper already exists")
old_daily = '''  destovka_denni_spotreba_l:
    name: "Dešťovka - odhad denní spotřeby"
    min: 0
    max: 300
    step: 5
    unit_of_measurement: "L"
    icon: mdi:water-minus
    mode: box

'''
require(cfg.count(old_daily) == 1, f"daily helper block count={cfg.count(old_daily)}")
new_daily = '''  destovka_denni_spotreba_l:
    name: "Dešťovka - naučený / fallback denní odhad spotřeby"
    min: 0
    max: 300
    step: 0.1
    unit_of_measurement: "L"
    icon: mdi:water-minus
    mode: box

  destovka_odber_prutok_l_min:
    name: "Dešťovka - kalibrovaný průtok aktuálního odběru"
    min: 0.1
    max: 12
    step: 0.1
    unit_of_measurement: "L/min"
    icon: mdi:waves-arrow-right
    mode: box

  destovka_spotreba_dnes_l:
    name: "Dešťovka - interní změřená spotřeba dnes"
    min: 0
    max: 2000
    step: 0.1
    unit_of_measurement: "L"
    icon: mdi:water-minus
    mode: box

  destovka_odber_validni_min_dnes:
    name: "Dešťovka - interní minuty platného odběrového proxy dnes"
    min: 0
    max: 2000
    step: 0.1
    unit_of_measurement: "min"
    icon: mdi:timer-check-outline
    mode: box

'''
cfg = cfg.replace(old_daily, new_daily, 1)

require("destovka_savo_odhad_od:" not in cfg, "Savo estimate helper already exists")
anchor = '''  destovka_savo_poznamka:
'''
require(cfg.count(anchor) == 1, f"Savo note anchor count={cfg.count(anchor)}")
estimate_text_helpers = '''  destovka_savo_odhad_od:
    name: "Dešťovka - Savo odhad nejstaršího možného data dávky"
    max: 10
    icon: mdi:calendar-range

  destovka_savo_odhad_do:
    name: "Dešťovka - Savo odhad nejnovějšího možného data dávky"
    max: 10
    icon: mdi:calendar-range

'''
cfg = cfg.replace(anchor, estimate_text_helpers + anchor, 1)

elec_anchor = '''  - sensor:
      - name: "Elektřina - aktuální proměnná cena"
'''
require(cfg.count(elec_anchor) == 1, f"electricity template anchor count={cfg.count(elec_anchor)}")
proxy_block = '''  - binary_sensor:
      - name: "Dešťovka - odběr vody běží"
        default_entity_id: binary_sensor.destovka_odber_bezi
        unique_id: destovka_odber_bezi
        device_class: running
        availability: >-
          {% set raw = states('sensor.zahrada_cerpadlo_destovka_vykon') %}
          {{ raw not in ['unknown', 'unavailable', 'none', '']
             and (raw | float(-999)) >= 0 }}
        state: >-
          {{ (states('sensor.zahrada_cerpadlo_destovka_vykon') | float(0)) > 2 }}
        attributes:
          source_entity: sensor.zahrada_cerpadlo_destovka_vykon
          source_role: "provizorní PondoVario 750; později domácí vodárna, nakonec průtokoměr"
          threshold_w: 2
          model: "W slouží jen k detekci běhu; litry = doba běhu × kalibrovaný L/min"

'''
cfg = cfg.replace(elec_anchor, proxy_block + elec_anchor, 1)

age_anchor = '''          pritok_od_davky_l: "{{ states('input_number.destovka_savo_pritok_od_davky_l') | float(0) | round(1) }}"
'''
require(cfg.count(age_anchor) == 1, f"Savo attribute anchor count={cfg.count(age_anchor)}")
approx_attrs = '''          vek_davky_min_dni: >-
            {% set exact_ts = as_timestamp(states('input_text.destovka_savo_posledni_cas'), 0) | float(0) %}
            {% set estimate_ts = as_timestamp(states('input_text.destovka_savo_odhad_do'), 0) | float(0) %}
            {% if exact_ts > 0 %}
              {{ ((as_timestamp(now()) - exact_ts) / 86400) | round(2) }}
            {% elif estimate_ts > 0 %}
              {{ ((as_timestamp(now()) - estimate_ts) / 86400) | round(0, 'floor') }}
            {% else %}
              {{ none }}
            {% endif %}
          vek_davky_max_dni: >-
            {% set exact_ts = as_timestamp(states('input_text.destovka_savo_posledni_cas'), 0) | float(0) %}
            {% set estimate_ts = as_timestamp(states('input_text.destovka_savo_odhad_od'), 0) | float(0) %}
            {% if exact_ts > 0 %}
              {{ ((as_timestamp(now()) - exact_ts) / 86400) | round(2) }}
            {% elif estimate_ts > 0 %}
              {{ ((as_timestamp(now()) - estimate_ts) / 86400) | round(0, 'floor') }}
            {% else %}
              {{ none }}
            {% endif %}
          redeni_min_pct: >-
            {% set inflow = states('input_number.destovka_savo_pritok_od_davky_l') | float(0) %}
            {% set exact = is_state('input_boolean.destovka_savo_davka_znama', 'on') %}
            {% set dose_volume = states('input_number.destovka_objem_pri_savu_l') | float(0) %}
            {% set estimate = states('input_text.destovka_savo_odhad_od') not in ['unknown','unavailable','none','']
                              and states('input_text.destovka_savo_odhad_do') not in ['unknown','unavailable','none',''] %}
            {% if exact and dose_volume > 0 %}
              {{ ((inflow / dose_volume) * 100) | round(1) }}
            {% elif estimate %}
              {{ ((inflow / 1000) * 100) | round(1) }}
            {% else %}
              {{ none }}
            {% endif %}
          redeni_je_spodni_mez: >-
            {{ (not is_state('input_boolean.destovka_savo_davka_znama', 'on'))
               and states('input_text.destovka_savo_odhad_od') not in ['unknown','unavailable','none','']
               and states('input_text.destovka_savo_odhad_do') not in ['unknown','unavailable','none',''] }}
'''
cfg = cfg.replace(age_anchor, approx_attrs + age_anchor, 1)

balance_re = re.compile(r"(?ms)^- id: ['\"]?markvarec_destovka_prubezna_bilance['\"]?\n.*?(?=^- id:|\Z)")
matches = list(balance_re.finditer(auto))
require(len(matches) == 1, f"balance automation count={len(matches)}")

balance_and_learning = r'''- id: markvarec_destovka_prubezna_bilance
  alias: "Markvarec - Dešťovka - průběžná bilance"
  description: >-
    Model hladiny od kalibračního bodu. Přičítá jen nový déšť a spotřebu odečítá
    primárně podle skutečné doby běhu obecného odběrového proxy. Aktuálně proxy
    vychází z výkonu PondoVaria; při jeho nedostupnosti se dočasně použije
    naučený/fallback denní odhad. Nikdy zpětně nereplayuje historický déšť ani
    historickou spotřebu do aktuální kalibrované hladiny.
  triggers:
    - trigger: time_pattern
      minutes: "/1"
    - trigger: state
      entity_id: sensor.sencor_srazky_dnes
    - trigger: state
      entity_id: binary_sensor.destovka_odber_bezi
  conditions: []
  actions:
    - variables:
        now_ts: "{{ as_timestamp(now()) | float(0) }}"
        prev_ts: "{{ states('input_number.destovka_bilance_posledni_update_ts') | float(0) }}"
        prev_rain: "{{ states('input_number.destovka_bilance_posledni_srazky_dnes_mm') | float(-1) }}"
        current_rain: "{{ states('sensor.sencor_srazky_dnes') | float(0) }}"
        current_level: "{{ states('input_number.destovka_stav_l') | float(0) }}"
        gain_l_mm: "{{ states('input_number.destovka_zisk_l_na_mm') | float(0) }}"
        flow_l_min: "{{ states('input_number.destovka_odber_prutok_l_min') | float(0) }}"
        fallback_l_day: "{{ states('input_number.destovka_denni_spotreba_l') | float(0) }}"
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ prev_ts <= 0 or prev_rain < 0 }}"
          sequence:
            - action: input_number.set_value
              target:
                entity_id: input_number.destovka_bilance_posledni_srazky_dnes_mm
              data:
                value: "{{ current_rain }}"
            - action: input_number.set_value
              target:
                entity_id: input_number.destovka_bilance_posledni_update_ts
              data:
                value: "{{ now_ts }}"
      default:
        - variables:
            elapsed_s: "{{ [0, now_ts - prev_ts] | max }}"
            rain_delta_mm: >-
              {% if current_rain >= prev_rain %}
                {{ current_rain - prev_rain }}
              {% else %}
                {{ current_rain }}
              {% endif %}
            inflow_l: "{{ ([0, rain_delta_mm] | max * gain_l_mm) | round(3) }}"
            source_state: >-
              {% if trigger is defined
                    and trigger.platform == 'state'
                    and trigger.entity_id == 'binary_sensor.destovka_odber_bezi'
                    and trigger.from_state is not none %}
                {{ trigger.from_state.state }}
              {% else %}
                {{ states('binary_sensor.destovka_odber_bezi') }}
              {% endif %}
            source_valid: "{{ source_state in ['on', 'off'] }}"
            source_running: "{{ source_state == 'on' }}"
            consumption_l: >-
              {% if source_valid %}
                {{ ((elapsed_s / 60) * flow_l_min if source_running else 0) | round(3) }}
              {% else %}
                {{ ((elapsed_s / 86400) * fallback_l_day) | round(3) }}
              {% endif %}
            next_level: "{{ [[current_level + inflow_l - consumption_l, 0] | max, 1000] | min | round(1) }}"
            savo_estimate_active: >-
              {% set bad = ['unknown','unavailable','none',''] %}
              {{ states('input_text.destovka_savo_odhad_od') not in bad
                 and states('input_text.destovka_savo_odhad_do') not in bad }}
            savo_tracking: "{{ is_state('input_boolean.destovka_savo_davka_znama', 'on') or savo_estimate_active }}"
            savo_inflow: "{{ states('input_number.destovka_savo_pritok_od_davky_l') | float(0) }}"
            today_use: "{{ states('input_number.destovka_spotreba_dnes_l') | float(0) }}"
            valid_minutes: "{{ states('input_number.destovka_odber_validni_min_dnes') | float(0) }}"
        - action: input_number.set_value
          target:
            entity_id: input_number.destovka_stav_l
          data:
            value: "{{ next_level }}"
        - action: input_number.set_value
          target:
            entity_id: input_number.destovka_bilance_posledni_srazky_dnes_mm
          data:
            value: "{{ current_rain }}"
        - action: input_number.set_value
          target:
            entity_id: input_number.destovka_bilance_posledni_update_ts
          data:
            value: "{{ now_ts }}"
        - if:
            - condition: template
              value_template: "{{ savo_tracking and inflow_l > 0 }}"
          then:
            - action: input_number.set_value
              target:
                entity_id: input_number.destovka_savo_pritok_od_davky_l
              data:
                value: "{{ [2000, savo_inflow + inflow_l] | min | round(1) }}"
        - if:
            - condition: template
              value_template: "{{ source_valid and elapsed_s > 0 }}"
          then:
            - action: input_number.set_value
              target:
                entity_id: input_number.destovka_spotreba_dnes_l
              data:
                value: "{{ [2000, today_use + consumption_l] | min | round(1) }}"
            - action: input_number.set_value
              target:
                entity_id: input_number.destovka_odber_validni_min_dnes
              data:
                value: "{{ [2000, valid_minutes + (elapsed_s / 60)] | min | round(1) }}"
  mode: queued
  max: 10

- id: markvarec_destovka_denni_uceni_spotreby
  alias: "Markvarec - Dešťovka - denní učení spotřeby"
  description: >-
    Jednou denně zpřesňuje predikční L/den z reálně odhadnutého odběru. Aktualizuje
    odhad jen pokud byl odběrový proxy platný alespoň 20 hodin; jinak starý odhad
    ponechá jako fallback. Používá pomalou EMA, aby jeden neobvyklý den nerozhodil
    semafor. Dnešní čítače pak resetuje.
  triggers:
    - trigger: time
      at: "23:59:30"
  conditions: []
  actions:
    - variables:
        measured_today: "{{ states('input_number.destovka_spotreba_dnes_l') | float(0) }}"
        coverage_min: "{{ states('input_number.destovka_odber_validni_min_dnes') | float(0) }}"
        previous_daily: "{{ states('input_number.destovka_denni_spotreba_l') | float(0) }}"
        learned_daily: "{{ ((previous_daily * 0.65) + (measured_today * 0.35)) | round(1) }}"
    - if:
        - condition: template
          value_template: "{{ coverage_min >= 1200 }}"
      then:
        - action: input_number.set_value
          target:
            entity_id: input_number.destovka_denni_spotreba_l
          data:
            value: "{{ learned_daily }}"
    - action: input_number.set_value
      target:
        entity_id: input_number.destovka_spotreba_dnes_l
      data:
        value: 0
    - action: input_number.set_value
      target:
        entity_id: input_number.destovka_odber_validni_min_dnes
      data:
        value: 0
  mode: single

'''
auto = balance_re.sub(balance_and_learning, auto, count=1)

require('label:"NEPŘIDÁVAT"' in card, "old Savo visual label missing")
card = card.replace('label:"NEPŘIDÁVAT"', 'label:"NEDÁVAT"', 1)

old_title_css = '.savo-title strong { display:block; font-size:15px; line-height:1.1; overflow-wrap:anywhere; }'
require(card.count(old_title_css) == 1, f"Savo title CSS count={card.count(old_title_css)}")
card = card.replace(
    old_title_css,
    '.savo-title strong { display:block; font-size:14px; line-height:1.1; white-space:nowrap; overflow-wrap:normal; }',
    1,
)

var_re = re.compile(
    r'''(?ms)^    const savoAgeRaw = Number\.parseFloat\(this\._attr\("sensor\.destovka_savo_doporuceni", "vek_davky_dni", null\)\);\n'''
    r'''    const savoAgeDays = Number\.isFinite\(savoAgeRaw\) \? savoAgeRaw : null;\n'''
    r'''    const savoInflow = this\._num\("input_number\.destovka_savo_pritok_od_davky_l", null\);\n'''
    r'''    const savoCheckDays = this\._num\("input_number\.destovka_savo_kontrola_dni", 7\);\n'''
    r'''    const savoDilutionLimit = this\._num\("input_number\.destovka_savo_kontrola_redeni_pct", 25\);\n'''
)
require(len(var_re.findall(card)) == 1, "Savo JS input variables shape changed")
new_vars = '''    const savoAgeRaw = Number.parseFloat(this._attr("sensor.destovka_savo_doporuceni", "vek_davky_dni", null));
    const savoAgeDays = Number.isFinite(savoAgeRaw) ? savoAgeRaw : null;
    const savoAgeMinRaw = Number.parseFloat(this._attr("sensor.destovka_savo_doporuceni", "vek_davky_min_dni", null));
    const savoAgeMaxRaw = Number.parseFloat(this._attr("sensor.destovka_savo_doporuceni", "vek_davky_max_dni", null));
    const savoAgeMinDays = Number.isFinite(savoAgeMinRaw) ? savoAgeMinRaw : null;
    const savoAgeMaxDays = Number.isFinite(savoAgeMaxRaw) ? savoAgeMaxRaw : null;
    const savoDilutionFloorRaw = Number.parseFloat(this._attr("sensor.destovka_savo_doporuceni", "redeni_min_pct", null));
    const savoDilutionFloor = Number.isFinite(savoDilutionFloorRaw) ? savoDilutionFloorRaw : null;
    const savoDilutionIsFloor = String(this._attr("sensor.destovka_savo_doporuceni", "redeni_je_spodni_mez", false)).toLowerCase() === "true";
    const savoInflow = this._num("input_number.destovka_savo_pritok_od_davky_l", null);
    const savoCheckDays = this._num("input_number.destovka_savo_kontrola_dni", 7);
    const savoDilutionLimit = this._num("input_number.destovka_savo_kontrola_redeni_pct", 25);
'''
card = var_re.sub(new_vars, card, count=1)

render_old = "savoAgeDays, savoInflow, savoCheckDays, savoDilutionLimit,"
require(card.count(render_old) == 1, "render-key Savo fields changed")
card = card.replace(
    render_old,
    "savoAgeDays, savoAgeMinDays, savoAgeMaxDays, savoDilutionFloor, savoDilutionIsFloor, savoInflow, savoCheckDays, savoDilutionLimit,",
    1,
)

derived_re = re.compile(r'''(?ms)^    const savoAgeKnown = .*?^    const dilutionLabel = .*?;\n(?=\n    const stat =)''')
matches = derived_re.findall(card)
require(len(matches) == 1, f"Savo derived block count={len(matches)}")
new_derived = '''    const exactAgeKnown = Number.isFinite(savoAgeDays) && Number.isFinite(savoCheckDays) && savoCheckDays > 0;
    const approximateAgeKnown = !exactAgeKnown && Number.isFinite(savoAgeMinDays) && Number.isFinite(savoAgeMaxDays)
      && Number.isFinite(savoCheckDays) && savoCheckDays > 0;
    const savoAgeKnown = exactAgeKnown || approximateAgeKnown;
    const ageForMeter = exactAgeKnown ? savoAgeDays : (approximateAgeKnown ? savoAgeMaxDays : 0);
    const savoAgePct = savoAgeKnown ? this._clamp((ageForMeter / savoCheckDays) * 100, 0, 100) : 0;
    const dilutionPct = known && Number.isFinite(savoInflow) && Number.isFinite(doseVolume) && doseVolume > 0
      ? (savoInflow / doseVolume) * 100 : null;
    const displayedDilution = Number.isFinite(dilutionPct) ? dilutionPct : savoDilutionFloor;
    const dilutionKnown = Number.isFinite(displayedDilution) && Number.isFinite(savoDilutionLimit) && savoDilutionLimit > 0;
    const dilutionMeterPct = dilutionKnown ? this._clamp((displayedDilution / savoDilutionLimit) * 100, 0, 100) : 0;
    const ageLabel = exactAgeKnown
      ? `${savoAgeDays.toFixed(1)} / ${savoCheckDays.toFixed(0)} d`
      : (approximateAgeKnown ? `~${savoAgeMinDays.toFixed(0)}–${savoAgeMaxDays.toFixed(0)} d` : `? / ${savoCheckDays.toFixed(0)} d`);
    const dilutionLabel = dilutionKnown
      ? `${(!Number.isFinite(dilutionPct) || savoDilutionIsFloor) ? "≥" : ""}${displayedDilution.toFixed(0)} / ${savoDilutionLimit.toFixed(0)} %`
      : `? / ${savoDilutionLimit.toFixed(0)} %`;
'''
card = derived_re.sub(new_derived, card, count=1)

CFG.write_text(cfg, encoding="utf-8")
AUTO.write_text(auto, encoding="utf-8")
CARD.write_text(card, encoding="utf-8")

for p in (CFG, AUTO, CARD):
    print(p, hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size)
