from pathlib import Path
import re

card = Path("/config/www/lina-rainwater-card.js").read_text(encoding="utf-8")

assert '_useSignal(rec)' in card
for cls in ('lamp red', 'lamp amber', 'lamp green'):
    assert cls in card, cls
assert 's.includes("VELMI ŠETŘIT") || s === "ŠETŘIT"' in card
assert 's === "BĚŽNĚ") return "amber"' in card
assert 's.includes("BEZ OMEZENÍ") || s.includes("KLIDNĚ VÍC") || s.includes("VYUŽÍVAT VÍC")' in card
assert '<div class="eyebrow">semafor používání</div>' in card
assert 'sensor.destovka_doporuceni' in card
assert 'sensor.destovka_savo_doporuceni' in card
assert 'data-entity="sensor.destovka_savo_doporuceni"' in card
assert 'savo-meter' in card and 'čas od dávky' in card and 'naředění' in card
assert 'savoAgeKnown ? "" : "unknown"' in card
assert 'dilutionKnown ? "" : "unknown"' in card
assert 'dávka ?' in card
assert 'comfort-visual' in card
assert 'senzorická zpětná vazba · ne měření chloru' not in card
assert '${this._esc(savoMessage)} · poslední dávka:' not in card
assert 'kvalita vody a jezírko' in card
assert 'title="${this._esc(savoMessage)}"' in card
assert 'title="${this._esc(message)}"' in card

signal_body = re.search(r'_useSignal\(rec\) \{(.*?)\n  \}', card, re.S)
assert signal_body
body = signal_body.group(1)
assert body.count('return "red"') == 1
assert body.count('return "amber"') == 1
assert body.count('return "green"') == 1
assert body.count('return "none"') == 1

print("RAINWATER_VISUAL_SEMANTICS_REGRESSION_OK")
