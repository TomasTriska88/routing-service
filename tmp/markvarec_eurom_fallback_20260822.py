from pathlib import Path
import shutil

AUTOMATIONS = Path('/config/automations.yaml')
TEST = Path('/config/tests/test_heater_eurom_fallback_regression.py')
BACKUP = Path('/config/automations.yaml.bak-eurom-fallback-20260822')

replacements = {
    'markvarec_loznice_primotop_dohled_ztracen': '- id: markvarec_loznice_primotop_dohled_ztracen\n  alias: Markvarec - Ložnice - ztráta dohledu přímotopu\n  description: Dočasný dohled ručního náhradního Euromu. Pokud je v chladném provozu nedostupná zásuvka nebo její měření déle než 5 minut, upozorní, že stav topení nelze ověřit. QH4100 climate se po dobu reklamace nepoužívá.\n  triggers:\n  - trigger: template\n    value_template: "{{ states(\'switch.primotop_v_loznici_zasuvka_1\') in [\'unknown\',\'unavailable\'] or states(\'sensor.primotop_v_loznici_vykon\') in [\'unknown\',\'unavailable\'] }}"\n    for: 00:05:00\n  conditions:\n  - condition: template\n    value_template: "{{ is_state(\'binary_sensor.markvarec_chladny_provoz\',\'on\') or (states(\'sensor.sencor_loznice_teplota\') | float(99)) <= 22.0 }}"\n  actions:\n  - action: notify.send_message\n    continue_on_error: true\n    target:\n      entity_id: notify.tomas\n    data:\n      message: "Náhradní přímotop Eurom v ložnici teď nemám spolehlivě pod dohledem. Zásuvka: {{ states(\'switch.primotop_v_loznici_zasuvka_1\') }}, příkon: {{ states(\'sensor.primotop_v_loznici_vykon\') }}. Po výpadku se Eurom sám nerozběhne; pokud je v ložnici zima, zkontroluj ho a ručně nastav 1h časovač."\n  - action: script.lina_mluv\n    continue_on_error: true\n    data:\n      text: Pozor. Náhradní Eurom v ložnici teď nemám spolehlivě pod dohledem. Po výpadku se sám nerozběhne, takže pokud je zima, zkontroluj ho a ručně nastav hodinový časovač.\n      priorita: important\n  mode: single\n',
    'markvarec_loznice_primotop_problem_notify': '- id: markvarec_loznice_primotop_problem_notify\n  alias: Markvarec - Loznice - problem primotopu\n  description: Dočasný stateful watchdog ručního náhradního Euromu. Pokud ložnice klesne na 22 °C nebo méně a zásuvka 10 minut nepotvrdí topný odběr alespoň 500 W, vyžádá ruční spuštění 1h časovače. HA Eurom nezapíná.\n  triggers:\n  - trigger: template\n    value_template: >-\n      {% set t_raw = states(\'sensor.sencor_loznice_teplota\') %}\n      {% set p_raw = states(\'sensor.primotop_v_loznici_vykon\') %}\n      {{ is_state(\'switch.primotop_v_loznici_zasuvka_1\',\'on\')\n         and t_raw not in [\'unknown\',\'unavailable\',\'none\',\'\']\n         and p_raw not in [\'unknown\',\'unavailable\',\'none\',\'\']\n         and (t_raw | float(99)) <= 22.0\n         and (p_raw | float(9999)) < 500 }}\n    for: 00:10:00\n  conditions:\n  - condition: state\n    entity_id: input_boolean.loznice_primotop_problem\n    state: \'off\'\n  actions:\n  - action: input_boolean.turn_on\n    target:\n      entity_id: input_boolean.loznice_primotop_problem\n  - action: notify.send_message\n    continue_on_error: true\n    target:\n      entity_id: notify.tomas\n    data:\n      message: "Ložnice má {{ states(\'sensor.sencor_loznice_teplota\') }} °C a náhradní Eurom už 10 minut nepotvrzuje topný odběr ({{ states(\'sensor.primotop_v_loznici_vykon\') }} W). Po výpadku se sám nerozběhne. Ručně na něm nastav 1h časovač; tím se znovu aktivuje jeho automatika na 23 °C."\n  mode: single\n',
    'markvarec_loznice_primotop_recovery_notify': '- id: markvarec_loznice_primotop_recovery_notify\n  alias: Markvarec - Loznice - primotop obnoven\n  description: Dočasná recovery ručního náhradního Euromu. Po problému vyžaduje alespoň 30 s potvrzeného topného odběru 800 W nebo více; samotné napětí zásuvky za obnovení nestačí.\n  triggers:\n  - trigger: template\n    value_template: >-\n      {% set p_raw = states(\'sensor.primotop_v_loznici_vykon\') %}\n      {{ is_state(\'switch.primotop_v_loznici_zasuvka_1\',\'on\')\n         and p_raw not in [\'unknown\',\'unavailable\',\'none\',\'\']\n         and (p_raw | float(0)) >= 800 }}\n    for: 00:00:30\n  conditions:\n  - condition: state\n    entity_id: input_boolean.loznice_primotop_problem\n    state: \'on\'\n  actions:\n  - action: notify.send_message\n    continue_on_error: true\n    target:\n      entity_id: notify.tomas\n    data:\n      message: "Náhradní Eurom v ložnici znovu prokazatelně topí ({{ states(\'sensor.primotop_v_loznici_vykon\') }} W). Ruční nahození se podařilo."\n  - action: input_boolean.turn_off\n    target:\n      entity_id: input_boolean.loznice_primotop_problem\n  mode: single\n',
    'markvarec_lina_primotop_problem_hlas': '- id: markvarec_lina_primotop_problem_hlas\n  alias: Markvarec - Lina - problém přímotopu hlasem\n  triggers:\n  - trigger: state\n    entity_id: input_boolean.loznice_primotop_problem\n    from: \'off\'\n    to: \'on\'\n  conditions: []\n  actions:\n  - action: script.lina_mluv\n    data:\n      text: Pozor. Ložnice chladne a náhradní Eurom netopí. Po výpadku se sám nerozběhne; ručně na něm nastav hodinový časovač, aby se aktivovala automatika na 23 stupňů.\n      priorita: important\n  mode: single\n',
    'markvarec_lina_primotop_obnoven_hlas': '- id: markvarec_lina_primotop_obnoven_hlas\n  alias: Markvarec - Lina - přímotop obnoven hlasem\n  triggers:\n  - trigger: state\n    entity_id: input_boolean.loznice_primotop_problem\n    from: \'on\'\n    to: \'off\'\n  conditions: []\n  actions:\n  - action: script.lina_mluv\n    data:\n      text: Náhradní Eurom v ložnici zase prokazatelně topí.\n      priorita: normal\n  mode: single\n',
}

text = AUTOMATIONS.read_text(encoding='utf-8')
if not BACKUP.exists():
    shutil.copy2(AUTOMATIONS, BACKUP)

for automation_id, replacement in replacements.items():
    marker = f'- id: {automation_id}'
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f'missing automation: {automation_id}')
    end = text.find('\n- id: ', start + 1)
    if end < 0:
        end = len(text)
    text = text[:start] + replacement.rstrip() + '\n' + text[end + 1 if end < len(text) else end:]

AUTOMATIONS.write_text(text, encoding='utf-8')
TEST.write_text(
"""from pathlib import Path

text = Path('/config/automations.yaml').read_text(encoding='utf-8')

def block(automation_id: str) -> str:
    marker = f'- id: {automation_id}'
    start = text.find(marker)
    assert start >= 0, f'missing {automation_id}'
    end = text.find('\\n- id: ', start + 1)
    if end < 0:
        end = len(text)
    return text[start:end]

lost = block('markvarec_loznice_primotop_dohled_ztracen')
problem = block('markvarec_loznice_primotop_problem_notify')
recovery = block('markvarec_loznice_primotop_recovery_notify')
voice = block('markvarec_lina_primotop_problem_hlas')

assert 'climate.primotop_loznice' not in lost
assert '00:05:00' in lost
assert '1h časovač' in lost
assert "sensor.sencor_loznice_teplota" in problem
assert '<= 22.0' in problem
assert '< 500' in problem
assert '00:10:00' in problem
assert 'HA Eurom nezapíná' in problem
assert '>= 800' in recovery
assert '00:00:30' in recovery
assert '1h časovač' in problem
assert '23 °C' in problem
assert 'hodinový časovač' in voice
assert '23 stupňů' in voice

print('EUROM_FALLBACK_REGRESSION_OK')
""", encoding='utf-8')
print('EUROM_FALLBACK_PATCH_OK')
