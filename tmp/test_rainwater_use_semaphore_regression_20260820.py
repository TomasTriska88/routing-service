from pathlib import Path

cfg=Path('/config/configuration.yaml').read_text(encoding='utf-8')
card=Path('/config/www/lina-rainwater-card.js').read_text(encoding='utf-8')
a=cfg.index('- name: "Dešťovka - doporučení"')
b=cfg.index('\n  - sensor:',a)
block=cfg[a:b]
assert 'destovka_savo_doporuceni' not in block
assert 'savo_priority' not in block
assert 'sensor.destovka_doporuceni' in card
assert 'sensor.destovka_savo_doporuceni' in card
assert 'data-entity="sensor.destovka_doporuceni"' in card
assert 'data-entity="sensor.destovka_savo_doporuceni"' in card
print('RAINWATER_USE_SEMAPHORE_REGRESSION_OK')
