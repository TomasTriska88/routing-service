from pathlib import Path
import shutil, subprocess, sys

CFG = Path("/config/configuration.yaml")
AUTO = Path("/config/automations.yaml")
TEST = Path("/config/tests/test_fan_regression.py")
STAMP = "winter-fan-20260818-1740"
backups = {}

def backup(p):
    if p.exists():
        b = p.with_name(p.name + ".bak-" + STAMP)
        shutil.copy2(p, b)
        backups[p] = b
    else:
        backups[p] = None

def restore_all():
    for p,b in backups.items():
        if b is None:
            if p.exists():
                p.unlink()
        elif b.exists():
            shutil.copy2(b, p)

def replace_automation_block(text, aid, new_block):
    markers = [f"- id: '{aid}'", f'- id: "{aid}"', f"- id: {aid}"]
    starts = [(text.find(m), m) for m in markers if text.find(m) >= 0]
    if not starts:
        raise RuntimeError(f"automation not found: {aid}")
    start, marker = min(starts)
    end = text.find("\n- id:", start + len(marker))
    if end < 0:
        end = len(text)
    return text[:start] + new_block.rstrip() + "\n" + text[end:]

template_insert = r'''
  - binary_sensor:
      - name: "Ložnice - větrák AUTO start"
        default_entity_id: binary_sensor.loznice_vetrak_auto_start
        unique_id: markvarec_loznice_vetrak_auto_start
        availability: >-
          {% set bad = ['unknown', 'unavailable', 'none', ''] %}
          {% set room = states('sensor.sencor_loznice_teplota') %}
          {% if is_state('input_boolean.loznice_vetrak_zimni_smer', 'on') %}
            {{ room not in bad
               and states('sensor.sencor_technicka_teplota') not in bad
               and states('binary_sensor.markvarec_chladny_provoz') in ['on', 'off'] }}
          {% else %}
            {{ room not in bad and states('sun.sun') in ['above_horizon', 'below_horizon'] }}
          {% endif %}
        state: >-
          {% set room = states('sensor.sencor_loznice_teplota') | float(0) %}
          {% if is_state('input_boolean.loznice_vetrak_zimni_smer', 'on') %}
            {% set tech = states('sensor.sencor_technicka_teplota') | float(0) %}
            {% set comfort = states('input_number.loznice_primotop_optimalni_teplota') | float(24) %}
            {{ is_state('binary_sensor.markvarec_chladny_provoz', 'on')
               and room >= comfort + 1.0
               and (room - tech) >= 3.0 }}
          {% else %}
            {% set on_at = 25.5 if is_state('sun.sun', 'below_horizon') else 26.0 %}
            {{ room >= on_at }}
          {% endif %}

      - name: "Ložnice - větrák AUTO držet"
        default_entity_id: binary_sensor.loznice_vetrak_auto_keep
        unique_id: markvarec_loznice_vetrak_auto_keep
        availability: >-
          {% set bad = ['unknown', 'unavailable', 'none', ''] %}
          {% set room = states('sensor.sencor_loznice_teplota') %}
          {% if is_state('input_boolean.loznice_vetrak_zimni_smer', 'on') %}
            {{ room not in bad
               and states('sensor.sencor_technicka_teplota') not in bad
               and states('binary_sensor.markvarec_chladny_provoz') in ['on', 'off'] }}
          {% else %}
            {{ room not in bad and states('sun.sun') in ['above_horizon', 'below_horizon'] }}
          {% endif %}
        state: >-
          {% set room = states('sensor.sencor_loznice_teplota') | float(0) %}
          {% if is_state('input_boolean.loznice_vetrak_zimni_smer', 'on') %}
            {% set tech = states('sensor.sencor_technicka_teplota') | float(0) %}
            {% set comfort = states('input_number.loznice_primotop_optimalni_teplota') | float(24) %}
            {{ is_state('binary_sensor.markvarec_chladny_provoz', 'on')
               and room > comfort + 0.5
               and (room - tech) > 1.5 }}
          {% else %}
            {% set off_at = 25.0 if is_state('sun.sun', 'below_horizon') else 25.5 %}
            {{ room > off_at }}
          {% endif %}

'''

auto_block = '- id: \'markvarec_loznice_vetrak_auto\'\n  alias: "Markvarec - Loznice - Vetrak AUTO"\n  description: "Sezonne adaptivni rizeni loznicoveho vetraku. Fyzicky zimni smer potvrzuje helper; chladny provoz odvozuje HA z klouzaveho 24h venkovniho prumeru s hysteresi 17/19 C. V zime se teplo prenasi do technicke pri rozdilu >=3 C a loznici >= komfort+1 C, dobeh pokracuje do rozdilu 1.5 C nebo komfort+0.5 C. V letnim smeru zustava komfortni hystereze 26.0/25.5 C ve dne a 25.5/25.0 C v noci. Minimalni 9min beh a race ochrany zustavaji zachovane."\n  triggers:\n    - trigger: state\n      entity_id: binary_sensor.loznice_vetrak_auto_start\n    - trigger: state\n      entity_id: binary_sensor.loznice_vetrak_auto_keep\n    - trigger: state\n      entity_id: fan.loznice_vetrak_loznice_zasuvka_1\n    - trigger: homeassistant\n      event: start\n    - trigger: event\n      event_type: timer.finished\n      event_data:\n        entity_id: timer.loznice_vetrak_minimalni_beh\n    - trigger: time_pattern\n      minutes: "/5"\n  conditions: []\n  actions:\n    - choose:\n        - conditions:\n            - condition: state\n              entity_id: binary_sensor.loznice_vetrak_auto_start\n              state: "on"\n            - condition: state\n              entity_id: fan.loznice_vetrak_loznice_zasuvka_1\n              state: "off"\n          sequence:\n            - action: script.loznice_vetrak_zapnout_spolehlive\n        - conditions:\n            - condition: state\n              entity_id: binary_sensor.loznice_vetrak_auto_keep\n              state: "off"\n            - condition: state\n              entity_id: timer.loznice_vetrak_minimalni_beh\n              state: "idle"\n            - condition: state\n              entity_id: timer.loznice_vetrak_rucni\n              state: "idle"\n          sequence:\n            - action: script.loznice_vetrak_vypnout_spolehlive\n  mode: single\n'
manual_block = '- id: \'markvarec_loznice_vetrak_manualni_13min\'\n  alias: "Markvarec - Loznice - Vetrak rucne 9 min"\n  description: "Pri skutecnem HA prechodu OFF->ON zrusi rozbehnuty OFF retry a spusti 9min minimalni beh. Samostatny rucni 9min timer se pouzije jen tehdy, kdy jednotna AUTO logika nema duvod vetrak dal drzet; zimni i letni rezim tak pouzivaji stejny zdroj pravdy."\n  triggers:\n    - trigger: state\n      entity_id: fan.loznice_vetrak_loznice_zasuvka_1\n      from: "off"\n      to: "on"\n  conditions: []\n  actions:\n    - action: script.turn_off\n      target:\n        entity_id: script.loznice_vetrak_vypnout_spolehlive\n    - action: timer.start\n      target:\n        entity_id: timer.loznice_vetrak_minimalni_beh\n      data:\n        duration: "00:09:00"\n    - choose:\n        - conditions:\n            - condition: state\n              entity_id: binary_sensor.loznice_vetrak_auto_keep\n              state: "off"\n          sequence:\n            - action: timer.start\n              target:\n                entity_id: timer.loznice_vetrak_rucni\n              data:\n                duration: "00:09:00"\n      default:\n        - action: timer.cancel\n          target:\n            entity_id: timer.loznice_vetrak_rucni\n  mode: restart\n'
timeout_block = '- id: \'markvarec_loznice_vetrak_rucni_timeout\'\n  alias: "Markvarec - Loznice - Vetrak rucni timeout"\n  description: "Po dokonceni rucniho 9min timeru vypne vetrak jen pokud jednotna AUTO logika rika, ze uz jej neni potreba drzet. Pri unknown/unavailable je AUTO helper unavailable a timeout nic nevypina."\n  triggers:\n    - trigger: event\n      event_type: timer.finished\n      event_data:\n        entity_id: timer.loznice_vetrak_rucni\n  conditions:\n    - condition: state\n      entity_id: binary_sensor.loznice_vetrak_auto_keep\n      state: "off"\n  actions:\n    - action: script.loznice_vetrak_vypnout_spolehlive\n  mode: restart\n'
test_content = 'from pathlib import Path\nimport unittest\nimport yaml\n\nCONFIG_TEXT = Path("/config/configuration.yaml").read_text(encoding="utf-8")\nS = yaml.safe_load(Path("/config/scripts.yaml").read_text(encoding="utf-8"))\nA = yaml.safe_load(Path("/config/automations.yaml").read_text(encoding="utf-8"))\n\ndef by_id(aid):\n    return next(x for x in A if str(x.get("id")) == aid)\n\ndef actions(obj):\n    if isinstance(obj, dict):\n        if "action" in obj:\n            yield obj\n        for v in obj.values():\n            yield from actions(v)\n    elif isinstance(obj, list):\n        for v in obj:\n            yield from actions(v)\n\ndef retry_calls(checkpoints):\n    n = 1\n    for fan_state, minimum, manual in checkpoints:\n        if (fan_state, minimum, manual) != ("off", "idle", "idle"):\n            break\n        n += 1\n    return n\n\ndef policy(winter_direction, cold_mode, room, tech, comfort, sun="above_horizon"):\n    if winter_direction:\n        start = cold_mode and room >= comfort + 1.0 and (room - tech) >= 3.0\n        keep = cold_mode and room > comfort + 0.5 and (room - tech) > 1.5\n    else:\n        on_at = 25.5 if sun == "below_horizon" else 26.0\n        off_at = 25.0 if sun == "below_horizon" else 25.5\n        start = room >= on_at\n        keep = room > off_at\n    return start, keep\n\nclass FanRaceRegression(unittest.TestCase):\n    def setUp(self):\n        self.off = S["loznice_vetrak_vypnout_spolehlive"]["sequence"]\n        self.manual = by_id("markvarec_loznice_vetrak_manualni_13min")\n\n    def test_manual_on_cancels_inflight_off_first(self):\n        first = self.manual["actions"][0]\n        self.assertEqual(first.get("action"), "script.turn_off")\n        target = first.get("target", {}).get("entity_id")\n        self.assertEqual(target, "script.loznice_vetrak_vypnout_spolehlive")\n\n    def test_each_delayed_retry_has_race_guards(self):\n        off_idx = [i for i,x in enumerate(self.off) if isinstance(x,dict) and x.get("action") == "fan.turn_off"]\n        self.assertEqual(len(off_idx), 3)\n        need = {\n            ("fan.loznice_vetrak_loznice_zasuvka_1", "off"),\n            ("timer.loznice_vetrak_minimalni_beh", "idle"),\n            ("timer.loznice_vetrak_rucni", "idle"),\n        }\n        for a,b in zip(off_idx, off_idx[1:]):\n            got = {(x.get("entity_id"),x.get("state")) for x in self.off[a+1:b]\n                   if isinstance(x,dict) and x.get("condition") == "state"}\n            self.assertTrue(need <= got, f"missing retry guards: {need-got}")\n\n    def test_manual_protection_timers_remain(self):\n        calls = list(actions(self.manual))\n        started = {x.get("target",{}).get("entity_id") for x in calls if x.get("action") == "timer.start"}\n        self.assertIn("timer.loznice_vetrak_minimalni_beh", started)\n        self.assertIn("timer.loznice_vetrak_rucni", started)\n\n    def test_normal_stale_off_still_retries_three_times(self):\n        self.assertEqual(retry_calls([("off","idle","idle"),("off","idle","idle")]), 3)\n\n    def test_manual_on_aborts_remaining_retries(self):\n        self.assertEqual(retry_calls([("on","active","active"),("off","active","active")]), 1)\n\n    def test_timer_blocks_retry_even_if_fan_looks_off_again(self):\n        self.assertEqual(retry_calls([("off","active","idle"),("off","active","idle")]), 1)\n\n    def test_unknown_state_fails_safe(self):\n        self.assertEqual(retry_calls([("unknown","idle","idle")]), 1)\n\nclass FanSeasonRegression(unittest.TestCase):\n    def test_config_has_weather_regime_and_physical_direction(self):\n        for text in (\n            "unique_id: sencor_venkovni_teplota_24h",\n            "state_characteristic: average_linear",\n            "hours: 24",\n            \'name: "Markvarec chladný provoz"\',\n            "lower: 18",\n            "hysteresis: 1",\n            "loznice_vetrak_zimni_smer:",\n            "unique_id: markvarec_loznice_vetrak_auto_start",\n            "unique_id: markvarec_loznice_vetrak_auto_keep",\n        ):\n            self.assertIn(text, CONFIG_TEXT)\n\n    def test_all_fan_control_uses_central_auto_helpers(self):\n        auto = by_id("markvarec_loznice_vetrak_auto")\n        manual = by_id("markvarec_loznice_vetrak_manualni_13min")\n        timeout = by_id("markvarec_loznice_vetrak_rucni_timeout")\n        raw_auto = yaml.safe_dump(auto, allow_unicode=True, sort_keys=False)\n        raw_manual = yaml.safe_dump(manual, allow_unicode=True, sort_keys=False)\n        raw_timeout = yaml.safe_dump(timeout, allow_unicode=True, sort_keys=False)\n        self.assertIn("binary_sensor.loznice_vetrak_auto_start", raw_auto)\n        self.assertIn("binary_sensor.loznice_vetrak_auto_keep", raw_auto)\n        self.assertIn("binary_sensor.loznice_vetrak_auto_keep", raw_manual)\n        self.assertIn("binary_sensor.loznice_vetrak_auto_keep", raw_timeout)\n        self.assertNotIn("sensor.sencor_technicka_teplota", raw_auto)\n\n    def test_current_winter_shape_wants_fan(self):\n        self.assertEqual(policy(True, True, 28.1, 19.6, 24), (True, True))\n\n    def test_winter_start_and_keep_have_hysteresis(self):\n        self.assertEqual(policy(True, True, 25.0, 23.0, 24), (False, True))\n        self.assertEqual(policy(True, True, 25.0, 23.5, 24), (False, False))\n        self.assertEqual(policy(True, True, 24.5, 19.0, 24), (False, False))\n\n    def test_warm_regime_disables_winter_transfer(self):\n        self.assertEqual(policy(True, False, 30.0, 18.0, 24), (False, False))\n\n    def test_summer_day_hysteresis_is_preserved(self):\n        self.assertEqual(policy(False, False, 26.0, 20.0, 24, "above_horizon"), (True, True))\n        self.assertEqual(policy(False, False, 25.7, 20.0, 24, "above_horizon"), (False, True))\n        self.assertEqual(policy(False, False, 25.5, 20.0, 24, "above_horizon"), (False, False))\n\n    def test_summer_night_hysteresis_is_preserved(self):\n        self.assertEqual(policy(False, False, 25.5, 20.0, 24, "below_horizon"), (True, True))\n        self.assertEqual(policy(False, False, 25.2, 20.0, 24, "below_horizon"), (False, True))\n        self.assertEqual(policy(False, False, 25.0, 20.0, 24, "below_horizon"), (False, False))\n\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n'

for p in (CFG, AUTO, TEST):
    backup(p)

try:
    cfg = CFG.read_text(encoding="utf-8")
    required = [
        "unique_id: sencor_venkovni_teplota_24h",
        'name: "Markvarec chladný provoz"',
        "loznice_vetrak_zimni_smer:",
    ]
    missing = [x for x in required if x not in cfg]
    if missing:
        raise RuntimeError("missing config groundwork: " + repr(missing))
    if "unique_id: markvarec_loznice_vetrak_auto_start" not in cfg:
        marker = '  - sensor:\n      - name: "Jezírko - zanesení čerpadla"\n'
        if marker not in cfg:
            raise RuntimeError("template sensor insertion marker not found")
        cfg = cfg.replace(marker, template_insert + marker, 1)
        CFG.write_text(cfg, encoding="utf-8")

    auto = AUTO.read_text(encoding="utf-8")
    auto = replace_automation_block(auto, "markvarec_loznice_vetrak_auto", auto_block)
    auto = replace_automation_block(auto, "markvarec_loznice_vetrak_manualni_13min", manual_block)
    auto = replace_automation_block(auto, "markvarec_loznice_vetrak_rucni_timeout", timeout_block)
    AUTO.write_text(auto, encoding="utf-8")

    TEST.parent.mkdir(parents=True, exist_ok=True)
    TEST.write_text(test_content, encoding="utf-8")
    cp = subprocess.run([sys.executable, "-m", "py_compile", str(TEST)], text=True, capture_output=True)
    print(cp.stdout, end="")
    print(cp.stderr, end="", file=sys.stderr)
    if cp.returncode:
        raise RuntimeError("fan test compile failed")

    chk = subprocess.run([sys.executable, "-m", "homeassistant", "--script", "check_config", "-c", "/config"], text=True, capture_output=True)
    out = (chk.stdout or "") + (chk.stderr or "")
    print(out, end="")
    if chk.returncode != 0 or "could not be validated and has been disabled" in out.lower():
        raise RuntimeError(f"check_config failed rc={chk.returncode}")

    tst = subprocess.run([sys.executable, str(TEST)], text=True, capture_output=True)
    print(tst.stdout, end="")
    print(tst.stderr, end="", file=sys.stderr)
    if tst.returncode:
        raise RuntimeError(f"fan regression failed rc={tst.returncode}")

    print("WINTER_FAN_PATCH_OK")
except Exception as e:
    restore_all()
    print("WINTER_FAN_PATCH_FAILED:", repr(e), file=sys.stderr)
    sys.exit(90)
