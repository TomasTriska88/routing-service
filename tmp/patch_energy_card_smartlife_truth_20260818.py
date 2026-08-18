from pathlib import Path

p = Path('/config/www/lina-energy-card.js')
s = p.read_text(encoding='utf-8')

replacements = [
    ('title: "Měřená větev nemá data",', 'title: "Vnitřní rozvaděč nemá data",'),
    ('<small>Měřená část odběru · celý elektroměr ČEZ je vyšší</small>', '<small>Vnitřní rozvaděč · podružné větve jsou jen kontext</small>'),
    ('<small>HA naměřeno</small><strong>${this._esc(monthEnergyText)}</strong>', '<small>Tento měsíc</small><strong>${this._esc(monthEnergyText)}</strong>'),
]

for old, new in replacements:
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f'expected exactly one match for {old!r}, got {count}')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('ENERGY_CARD_SMARTLIFE_TRUTH_PATCH_OK')
