from pathlib import Path

p = Path('/config/www/lina-energy-card.js')
s = p.read_text(encoding='utf-8')

replacements = [
    ('title: "Kořenové měření nemá data",', 'title: "Měřená větev nemá data",'),
    ('text: "Aktuální spotřebu nelze spolehlivě vyhodnotit.",', 'text: "Aktuální spotřebu této větve nelze spolehlivě vyhodnotit.",'),
    ('<small>Kořenové měření celého Markvarce · podružné větve jsou jen kontext</small>', '<small>Měřená část odběru · celý elektroměr ČEZ je vyšší</small>'),
    ('<small>Tento měsíc</small><strong>${this._esc(monthEnergyText)}</strong>', '<small>HA naměřeno</small><strong>${this._esc(monthEnergyText)}</strong>'),
    ('<small>Odhad účtu vč. fixu</small><strong>${this._esc(monthCostText)}</strong>', '<small>Min. náklad dosud</small><strong>${this._esc(monthCostText)}</strong>'),
]

for old, new in replacements:
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f'expected exactly one match for {old!r}, got {count}')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('ENERGY_CARD_PARTIAL_LABELS_PATCH_OK')
