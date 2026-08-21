from pathlib import Path

scripts = Path("/config/scripts.yaml")
tests = Path("/config/tests/test_postblackout_health_regression.py")

s = scripts.read_text(encoding="utf-8")

if "parent_root_live =" not in s:
    old = '''          {% if states('switch.technicka_mistnost_loznicovy_rozvadec') != 'on'
                or states('select.loznicovy_rozvadec_chovani_pri_zapnuti') != 'power_on' %}
            {% set ns.items = ns.items + ['Ložnicový rozvaděč'] %}
          {% endif %}
          {% if states('switch.starlink_router') != 'on' '''
    new = '''          {% if states('switch.technicka_mistnost_loznicovy_rozvadec') != 'on'
                or states('select.loznicovy_rozvadec_chovani_pri_zapnuti') != 'power_on' %}
            {% set ns.items = ns.items + ['Ložnicový rozvaděč'] %}
          {% endif %}
          {% if states('switch.rodicovsky_rozvadec_zasuvka_1') != 'on'
                or states('select.rodicovsky_rozvadec_chovani_pri_zapnuti') != 'power_on' %}
            {% set ns.items = ns.items + ['Rodičovský rozvaděč'] %}
          {% endif %}
          {% if states('switch.starlink_router') != 'on' '''
    assert s.count(old) == 1, "parent root insertion anchor mismatch"
    s = s.replace(old, new, 1)

    old = '''          {% if states('sensor.vnitrni_rozvadec_vykon') in invalid
                or states('sensor.loznicovy_rozvadec_vykon') in invalid
                or states('sensor.primotop_v_loznici_vykon') in invalid %}
            {% set ns.items = ns.items + ['měření kritických napájecích větví'] %}
          {% endif %}'''
    new = '''          {% if states('sensor.vnitrni_rozvadec_vykon') in invalid
                or states('sensor.vnitrni_rozvadec_proud') in invalid
                or states('sensor.vnitrni_rozvadec_napeti') in invalid
                or states('sensor.rodicovsky_rozvadec_vykon') in invalid
                or states('sensor.rodicovsky_rozvadec_proud') in invalid
                or states('sensor.rodicovsky_rozvadec_napeti') in invalid
                or states('sensor.loznicovy_rozvadec_vykon') in invalid
                or states('sensor.primotop_v_loznici_vykon') in invalid %}
            {% set ns.items = ns.items + ['měření kořenových a kritických napájecích větví'] %}
          {% endif %}'''
    assert s.count(old) == 1, "measurement insertion anchor mismatch"
    s = s.replace(old, new, 1)

    old = '''          {% set intro = 'Test post-blackout health checku je hotový.' if test | default(false) else 'Po úplném restartu Prcka jsem dokončila kontrolu Markvarce.' %}
          {% if ns.items | length == 0 %}
            {{ intro }} Home Assistant, síť, kritické napájecí větve, přímotop, Zigbee, meteostanice, zabezpečení, kamery, jezírko, zálohy i hlasová cesta se podle dostupné telemetrie vrátily do normálu. Pokud restart souvisel s vodou nebo elektrikou, tohle nenahrazuje fyzickou kontrolu postiženého místa.
          {% else %}
            {{ intro }} Většina systému je zpátky, ale problém nebo nedostupnost stále vidím u: {{ ns.items | join(', ') }}. Nic kvůli tomu automaticky neodpojuju ani neresetuju elektrické jištění. Pokud restart souvisel s vodou nebo elektrikou, postižené místo je potřeba fyzicky zkontrolovat.
          {% endif %}'''
    new = '''          {% set own_root_live =
               states('switch.technicka_mistnost_vnitrni_rozvadec') == 'on'
               and states('sensor.vnitrni_rozvadec_vykon') not in invalid
               and states('sensor.vnitrni_rozvadec_proud') not in invalid
               and states('sensor.vnitrni_rozvadec_napeti') not in invalid %}
          {% set parent_root_live =
               states('switch.rodicovsky_rozvadec_zasuvka_1') == 'on'
               and states('sensor.rodicovsky_rozvadec_vykon') not in invalid
               and states('sensor.rodicovsky_rozvadec_proud') not in invalid
               and states('sensor.rodicovsky_rozvadec_napeti') not in invalid %}
          {% set parent_link_live = states('binary_sensor.markvarec_parent_router_link') == 'on' %}
          {% if own_root_live and parent_root_live and parent_link_live %}
            {% set branch_context = 'Obě kořenové větve jsou teď dostupné a spoj k rodičům je zpátky.' %}
          {% elif own_root_live and parent_root_live %}
            {% set branch_context = 'Obě kořenové větve jsou teď pod napětím, ale spoj k rodičovskému routeru není zpátky; aktuální problém je tedy až za rodičovským kořenovým měřákem nebo v síťové cestě.' %}
          {% elif own_root_live %}
            {% set branch_context = 'Tvoje kořenová větev je teď dostupná, rodičovská kořenová větev ne.' %}
          {% elif parent_root_live %}
            {% set branch_context = 'Rodičovská kořenová větev je teď dostupná, tvoje kořenová větev ne.' %}
          {% else %}
            {% set branch_context = 'Ani jednu kořenovou větev teď nemám spolehlivě potvrzenou jako dostupnou.' %}
          {% endif %}
          {% set intro = 'Test post-blackout health checku je hotový.' if test | default(false) else 'Po úplném restartu Prcka jsem dokončila kontrolu Markvarce.' %}
          {% if ns.items | length == 0 %}
            {{ intro }} {{ branch_context }} Home Assistant, síť, přímotop, Zigbee, meteostanice, zabezpečení, kamery, jezírko, zálohy i hlasová cesta se podle dostupné telemetrie vrátily do normálu. Pokud restart souvisel s vodou nebo elektrikou, tohle nenahrazuje fyzickou kontrolu postiženého místa.
          {% else %}
            {{ intro }} {{ branch_context }} Většina systému je zpátky, ale problém nebo nedostupnost stále vidím u: {{ ns.items | join(', ') }}. Nic kvůli tomu automaticky neodpojuju ani neresetuju elektrické jištění. Pokud restart souvisel s vodou nebo elektrikou, postižené místo je potřeba fyzicky zkontrolovat.
          {% endif %}'''
    assert s.count(old) == 1, "branch context insertion anchor mismatch"
    s = s.replace(old, new, 1)

    old_desc = '  description: "Read-only souhrnný health check po restartu celého Prcka. Nic fyzicky nespíná, nic nerestartuje a neopravuje elektrické jištění."'
    new_desc = '  description: "Read-only souhrnný health check po restartu celého Prcka. Kontroluje obě kořenové větve a další kritické vrstvy. Okamžitý bezpečnostní text je deterministický lokální fallback; případná LLM formulace jej nesmí zdržet ani nahradit. Nic fyzicky nespíná, nic nerestartuje a neopravuje elektrické jištění."'
    assert s.count(old_desc) == 1, "description anchor mismatch"
    s = s.replace(old_desc, new_desc, 1)

    scripts.write_text(s, encoding="utf-8")

t = tests.read_text(encoding="utf-8")
marker = "# Parent-root and branch-scope regression."
if marker not in t:
    insert = '''
# Parent-root and branch-scope regression.
for entity in (
    "switch.rodicovsky_rozvadec_zasuvka_1",
    "select.rodicovsky_rozvadec_chovani_pri_zapnuti",
    "sensor.rodicovsky_rozvadec_vykon",
    "sensor.rodicovsky_rozvadec_proud",
    "sensor.rodicovsky_rozvadec_napeti",
    "sensor.vnitrni_rozvadec_proud",
    "sensor.vnitrni_rozvadec_napeti",
):
    assert entity in H, entity

for token in (
    "own_root_live",
    "parent_root_live",
    "parent_link_live",
    "branch_context",
    "Obě kořenové větve jsou teď dostupné",
    "Tvoje kořenová větev je teď dostupná, rodičovská kořenová větev ne.",
    "Rodičovská kořenová větev je teď dostupná, tvoje kořenová větev ne.",
    "aktuální problém je tedy až za rodičovským kořenovým měřákem nebo v síťové cestě",
    "deterministický lokální fallback",
):
    assert token in H, token

assert H.count("{{ branch_context }}") == 2
assert "měření kořenových a kritických napájecích větví" in H
'''
    needle = 'print("POSTBLACKOUT_HEALTH_REGRESSION_OK")'
    assert t.count(needle) == 1, "test print anchor mismatch"
    t = t.replace(needle, insert + "\n" + needle, 1)
    tests.write_text(t, encoding="utf-8")

print("POSTBLACKOUT_PARENT_SCOPE_PATCH_OK")
