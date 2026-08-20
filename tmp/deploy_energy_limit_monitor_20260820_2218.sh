#!/bin/sh
set -eu

AUTO=/config/automations.yaml
BACKUP=/config/automations.yaml.bak-energy-limit-monitor-20260820-2218
TEST=/config/tests/test_energy_limit_monitor_regression.py
TEST_BACKUP=/config/tests/test_energy_limit_monitor_regression.py.bak-energy-limit-monitor-20260820-2218
EXPECTED_OLD=09bdeb7a0125d4fb4156c9948526444244414cb62e05b4714061a22d39d981f3

CURRENT=$(docker exec homeassistant sha256sum "$AUTO" | awk '{print $1}')
echo "ENERGY_LIMIT_CURRENT_SHA=$CURRENT"
test "$CURRENT" = "$EXPECTED_OLD"

docker exec homeassistant cp -p "$AUTO" "$BACKUP"
HAD_TEST=0
if docker exec homeassistant test -e "$TEST"; then
  HAD_TEST=1
  docker exec homeassistant cp -p "$TEST" "$TEST_BACKUP"
fi

rollback() {
  docker exec homeassistant cp -p "$BACKUP" "$AUTO" || true
  if [ "$HAD_TEST" -eq 1 ]; then
    docker exec homeassistant cp -p "$TEST_BACKUP" "$TEST" || true
  else
    docker exec homeassistant rm -f "$TEST" || true
  fi
  echo ENERGY_LIMIT_DEPLOY_ROLLED_BACK
}
trap rollback ERR

docker exec -i homeassistant python3 - <<'PY'
from pathlib import Path

auto = Path("/config/automations.yaml")
test = Path("/config/tests/test_energy_limit_monitor_regression.py")
text = auto.read_text(encoding="utf-8")
aid = "markvarec_elektrina_limitni_dohled"
assert aid not in text, "energy limit automation already exists"

block = r'''
- id: 'markvarec_elektrina_limitni_dohled'
  alias: "Markvarec - Elektřina - limitní dohled"
  description: "Pouze monitoruje 16A limity obou sourozeneckých větví a společný jednofázový 25A limit. Nad 90 % po 2 min upozorní, skutečné překročení limitu po 30 s eskaluje a po návratu pod 80 % po 2 min oznámí obnovu rezervy. Nic automaticky neodpojuje; přímotop ani kořenové rozvaděče nejsou load-shedding cíle."
  triggers:
    - trigger: numeric_state
      entity_id: sensor.vnitrni_rozvadec_proud
      above: 14.4
      below: 16
      for: "00:02:00"
      id: tomas_high
    - trigger: numeric_state
      entity_id: sensor.rodicovsky_rozvadec_proud
      above: 14.4
      below: 16
      for: "00:02:00"
      id: rodice_high
    - trigger: template
      value_template: >-
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set t = states('sensor.vnitrni_rozvadec_proud') %}
        {% set r = states('sensor.rodicovsky_rozvadec_proud') %}
        {{ t not in bad and r not in bad
           and (t | float(0) + r | float(0)) > 22.5
           and (t | float(0) + r | float(0)) < 25 }}
      for: "00:02:00"
      id: celkem_high
    - trigger: numeric_state
      entity_id: sensor.vnitrni_rozvadec_proud
      above: 16
      for: "00:00:30"
      id: tomas_critical
    - trigger: numeric_state
      entity_id: sensor.rodicovsky_rozvadec_proud
      above: 16
      for: "00:00:30"
      id: rodice_critical
    - trigger: template
      value_template: >-
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set t = states('sensor.vnitrni_rozvadec_proud') %}
        {% set r = states('sensor.rodicovsky_rozvadec_proud') %}
        {{ t not in bad and r not in bad
           and (t | float(0) + r | float(0)) > 25 }}
      for: "00:00:30"
      id: celkem_critical
  conditions: []
  actions:
    - variables:
        source: >-
          {% if trigger.id.startswith('tomas_') %}tomas
          {% elif trigger.id.startswith('rodice_') %}rodice
          {% else %}celkem{% endif %}
        level: "{{ 'critical' if trigger.id.endswith('_critical') else 'high' }}"
        tomas_a: "{{ states('sensor.vnitrni_rozvadec_proud') | float(0) | round(2) }}"
        rodice_a: "{{ states('sensor.rodicovsky_rozvadec_proud') | float(0) | round(2) }}"
        celkem_a: "{{ ((states('sensor.vnitrni_rozvadec_proud') | float(0)) + (states('sensor.rodicovsky_rozvadec_proud') | float(0))) | round(2) }}"
    - variables:
        label: >-
          {% if source == 'tomas' %}Tomášova větev
          {% elif source == 'rodice' %}Rodičovská větev
          {% else %}Markvarec celkem{% endif %}
        current_a: >-
          {% if source == 'tomas' %}{{ tomas_a }}
          {% elif source == 'rodice' %}{{ rodice_a }}
          {% else %}{{ celkem_a }}{% endif %}
        limit_a: "{{ 25 if source == 'celkem' else 16 }}"
        safe_a: "{{ 20 if source == 'celkem' else 12.8 }}"
        alert_tag: "markvarec-elektrina-{{ source }}"
        alert_title: >-
          {% if level == 'critical' %}Markvarec – překročený proudový limit
          {% else %}Markvarec – vysoké zatížení{% endif %}
        alert_message: >-
          {% if level == 'critical' %}
            {{ label }} je podle HA telemetrie nejméně 30 sekund nad jmenovitým limitem {{ limit_a }} A; aktuálně {{ current_a }} A.
            Bezpečně sniž zátěž. Fyzické jištění zůstává hlavní ochranou a HA nic automaticky neodpojuje.
          {% else %}
            {{ label }} je nejméně 2 minuty nad 90 % jmenovitého limitu {{ limit_a }} A; aktuálně {{ current_a }} A.
            Zkontroluj právě běžící zátěž. HA nic automaticky neodpojuje; přímotop ani kořenové rozvaděče nejsou cílem tohoto dohledu.
          {% endif %}
        voice_message: >-
          {% if level == 'critical' %}
            Pozor. {{ label }} je podle měření už třicet sekund nad limitem {{ limit_a }} ampér, aktuálně {{ current_a }} ampér.
            Bezpečně sniž zátěž. Nic sama neodpojuji; hlavní ochranou zůstává fyzické jištění.
          {% else %}
            {{ label }} je už dvě minuty nad devadesáti procenty limitu {{ limit_a }} ampér, aktuálně {{ current_a }} ampér.
            Zkontroluj, co právě běží. Nic sama neodpojuji.
          {% endif %}
        voice_priority: "{{ 'critical' if level == 'critical' else 'important' }}"
    - action: notify.tomas
      continue_on_error: true
      data:
        title: "{{ alert_title }}"
        message: "{{ alert_message }}"
        data:
          tag: "{{ alert_tag }}"
    - action: script.lina_mluv
      continue_on_error: true
      data:
        text: "{{ voice_message }}"
        priorita: "{{ voice_priority }}"
    - wait_for_trigger:
        - trigger: template
          id: recovered
          value_template: >-
            {% set bad = ['unknown', 'unavailable', 'none', ''] %}
            {% set t = states('sensor.vnitrni_rozvadec_proud') %}
            {% set r = states('sensor.rodicovsky_rozvadec_proud') %}
            {% if source == 'tomas' %}
              {{ t not in bad and (t | float(0)) < 12.8 }}
            {% elif source == 'rodice' %}
              {{ r not in bad and (r | float(0)) < 12.8 }}
            {% else %}
              {{ t not in bad and r not in bad
                 and (t | float(0) + r | float(0)) < 20 }}
            {% endif %}
          for: "00:02:00"
        - trigger: template
          id: escalated
          value_template: >-
            {% set bad = ['unknown', 'unavailable', 'none', ''] %}
            {% set t = states('sensor.vnitrni_rozvadec_proud') %}
            {% set r = states('sensor.rodicovsky_rozvadec_proud') %}
            {% if level != 'high' %}
              {{ false }}
            {% elif source == 'tomas' %}
              {{ t not in bad and (t | float(0)) > 16 }}
            {% elif source == 'rodice' %}
              {{ r not in bad and (r | float(0)) > 16 }}
            {% else %}
              {{ t not in bad and r not in bad
                 and (t | float(0) + r | float(0)) > 25 }}
            {% endif %}
          for: "00:00:30"
      timeout: "12:00:00"
      continue_on_timeout: false
    - condition: template
      value_template: "{{ wait.trigger is not none and wait.trigger.id == 'recovered' }}"
    - variables:
        recovery_a: >-
          {% if source == 'tomas' %}
            {{ states('sensor.vnitrni_rozvadec_proud') | float(0) | round(2) }}
          {% elif source == 'rodice' %}
            {{ states('sensor.rodicovsky_rozvadec_proud') | float(0) | round(2) }}
          {% else %}
            {{ ((states('sensor.vnitrni_rozvadec_proud') | float(0)) + (states('sensor.rodicovsky_rozvadec_proud') | float(0))) | round(2) }}
          {% endif %}
    - action: notify.tomas
      continue_on_error: true
      data:
        title: "Markvarec – proud zpět v rezervě"
        message: "{{ label }} je nejméně 2 minuty zpět pod 80 % limitu {{ limit_a }} A; aktuálně {{ recovery_a }} A."
        data:
          tag: "{{ alert_tag }}"
    - action: script.lina_mluv
      continue_on_error: true
      data:
        text: "{{ label }} je zase stabilně v bezpečné provozní rezervě, aktuálně {{ recovery_a }} ampér."
        priorita: normal
  mode: parallel
  max: 6
'''

if not text.endswith("\n"):
    text += "\n"
auto.write_text(text + block.lstrip("\n"), encoding="utf-8")

test.write_text(r'''from pathlib import Path
import unittest
import yaml

AUTOMATIONS = yaml.safe_load(Path("/config/automations.yaml").read_text(encoding="utf-8"))

def by_id(aid):
    return next(a for a in AUTOMATIONS if str(a.get("id")) == aid)

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)

class EnergyLimitMonitorRegression(unittest.TestCase):
    def setUp(self):
        self.a = by_id("markvarec_elektrina_limitni_dohled")
        self.triggers = {t.get("id"): t for t in self.a.get("triggers", [])}

    def test_exact_monitoring_thresholds(self):
        self.assertEqual(self.triggers["tomas_high"].get("above"), 14.4)
        self.assertEqual(self.triggers["tomas_high"].get("below"), 16)
        self.assertEqual(self.triggers["rodice_high"].get("above"), 14.4)
        self.assertEqual(self.triggers["rodice_high"].get("below"), 16)
        self.assertEqual(self.triggers["tomas_critical"].get("above"), 16)
        self.assertEqual(self.triggers["rodice_critical"].get("above"), 16)
        self.assertEqual(self.triggers["tomas_high"].get("for"), "00:02:00")
        self.assertEqual(self.triggers["rodice_high"].get("for"), "00:02:00")
        self.assertEqual(self.triggers["tomas_critical"].get("for"), "00:00:30")
        self.assertEqual(self.triggers["rodice_critical"].get("for"), "00:00:30")

    def test_total_25a_templates_use_both_root_currents(self):
        high = self.triggers["celkem_high"]
        critical = self.triggers["celkem_critical"]
        high_raw = high.get("value_template", "")
        crit_raw = critical.get("value_template", "")
        for raw in (high_raw, crit_raw):
            self.assertIn("sensor.vnitrni_rozvadec_proud", raw)
            self.assertIn("sensor.rodicovsky_rozvadec_proud", raw)
            self.assertIn("unknown", raw)
            self.assertIn("unavailable", raw)
        self.assertIn("> 22.5", high_raw)
        self.assertIn("< 25", high_raw)
        self.assertEqual(high.get("for"), "00:02:00")
        self.assertIn("> 25", crit_raw)
        self.assertEqual(critical.get("for"), "00:00:30")

    def test_recovery_is_tied_to_an_actual_alert_run(self):
        raw = yaml.safe_dump(self.a, allow_unicode=True, sort_keys=False)
        self.assertIn("wait_for_trigger", raw)
        self.assertIn("id: recovered", raw)
        self.assertIn("id: escalated", raw)
        self.assertIn("< 12.8", raw)
        self.assertIn("< 20", raw)
        self.assertIn("00:02:00", raw)

    def test_dual_output_and_priorities(self):
        raw = yaml.safe_dump(self.a, allow_unicode=True, sort_keys=False)
        self.assertIn("notify.tomas", raw)
        self.assertIn("script.lina_mluv", raw)
        self.assertIn("priorita: '{{ voice_priority }}'", raw)
        self.assertIn("priorita: normal", raw)
        self.assertIn("critical", raw)
        self.assertIn("important", raw)

    def test_monitor_never_switches_power(self):
        services = {
            node.get("action")
            for node in walk(self.a)
            if isinstance(node.get("action"), str)
        }
        forbidden = {
            "switch.turn_off", "switch.turn_on",
            "homeassistant.turn_off", "homeassistant.turn_on",
            "climate.turn_off", "climate.turn_on",
        }
        self.assertTrue(services.isdisjoint(forbidden), services & forbidden)
        raw = yaml.safe_dump(self.a, allow_unicode=True, sort_keys=False)
        self.assertNotIn("switch.technicka_mistnost_vnitrni_rozvadec", raw)
        self.assertNotIn("switch.rodicovsky_rozvadec_zasuvka_1", raw)
        self.assertNotIn("switch.primotop_v_loznici_zasuvka_1", raw)

    def test_parallel_waiters_are_bounded(self):
        self.assertEqual(self.a.get("mode"), "parallel")
        self.assertEqual(self.a.get("max"), 6)

if __name__ == "__main__":
    unittest.main(verbosity=2)
''', encoding="utf-8")

print("ENERGY_LIMIT_MONITOR_FILES_WRITTEN")
PY

docker exec homeassistant python3 -m py_compile "$TEST"
docker exec homeassistant python3 "$TEST"

NEW=$(docker exec homeassistant sha256sum "$AUTO" | awk '{print $1}')
TEST_SHA=$(docker exec homeassistant sha256sum "$TEST" | awk '{print $1}')
echo "ENERGY_LIMIT_NEW_SHA=$NEW"
echo "ENERGY_LIMIT_TEST_SHA=$TEST_SHA"
echo ENERGY_LIMIT_PRECHECKS_OK
trap - ERR
