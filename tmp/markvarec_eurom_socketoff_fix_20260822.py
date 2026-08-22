from pathlib import Path

p = Path('/config/automations.yaml')
text = p.read_text(encoding='utf-8')
start = text.find('- id: markvarec_loznice_primotop_problem_notify')
assert start >= 0
end = text.find('\n- id: ', start + 1)
if end < 0:
    end = len(text)
block = text[start:end]
old = "{{ is_state('switch.primotop_v_loznici_zasuvka_1','on')\n         and t_raw not in ['unknown','unavailable','none','']\n         and p_raw not in ['unknown','unavailable','none','']\n         and (t_raw | float(99)) <= 22.0\n         and (p_raw | float(9999)) < 500 }}"
new = "{{ t_raw not in ['unknown','unavailable','none','']\n         and p_raw not in ['unknown','unavailable','none','']\n         and (t_raw | float(99)) <= 22.0\n         and (not is_state('switch.primotop_v_loznici_zasuvka_1','on') or (p_raw | float(9999)) < 500) }}"
assert old in block, 'expected Eurom problem template not found'
block = block.replace(old, new, 1)
block = block.replace('Pokud ložnice klesne na 22 °C nebo méně a zásuvka 10 minut nepotvrdí topný odběr alespoň 500 W, vyžádá ruční spuštění 1h časovače.', 'Pokud ložnice klesne na 22 °C nebo méně a zásuvka není ON nebo 10 minut nepotvrdí topný odběr alespoň 500 W, vyžádá ruční spuštění 1h časovače.', 1)
text = text[:start] + block + text[end:]
p.write_text(text, encoding='utf-8')

test = Path('/config/tests/test_heater_eurom_fallback_regression.py')
t = test.read_text(encoding='utf-8')
needle = "assert '< 500' in problem\n"
assert needle in t
if "assert \"not is_state('switch.primotop_v_loznici_zasuvka_1','on')\" in problem\n" not in t:
    t = t.replace(needle, needle + "assert \"not is_state('switch.primotop_v_loznici_zasuvka_1','on')\" in problem\n", 1)
test.write_text(t, encoding='utf-8')
print('EUROM_SOCKET_OFF_FIX_OK')
