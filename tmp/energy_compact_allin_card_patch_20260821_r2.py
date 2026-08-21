#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_SHA256 = "628fdab2ff5dbc6bb50ea7727ede5fdbdcd8e94aa6ac613fbb613a4c092f109f"
VERSION_OLD = "20260820-allin-price-r1"
VERSION_NEW = "20260821-compact-allin-r1"

if len(sys.argv) != 3:
    raise SystemExit("usage: energy_compact_allin_card_patch_20260821.py INPUT OUTPUT")

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
raw = src.read_bytes()
actual = hashlib.sha256(raw).hexdigest()
if actual != EXPECTED_SHA256:
    raise SystemExit(f"LIVE_SHA_MISMATCH expected={EXPECTED_SHA256} actual={actual}")

text = raw.decode("utf-8")

def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}_COUNT={count}")
    text = text.replace(old, new, 1)

if text.count(VERSION_OLD) != 2:
    raise SystemExit(f"VERSION_COUNT={text.count(VERSION_OLD)}")
text = text.replace(VERSION_OLD, VERSION_NEW)

replace_once(
    '    const monthCostLabel = a.month.complete ? "Cena měsíce" : "Odhad ceny měsíce";',
    '    const monthCostLabel = a.month.complete ? "Měsíc celkem" : "Odhad celkem";',
    "MONTH_COST_LABEL",
)

history_start = text.find("    let historyHtml;\n")
history_end = text.find("    this.shadowRoot.innerHTML = `", history_start)
if history_start < 0 or history_end < 0 or history_end <= history_start:
    raise SystemExit("HISTORY_BLOCK_NOT_FOUND")

history_new = '''    let historyHtml = "";

    if (
      Number.isFinite(a.history.longTomasPct) &&
      Number.isFinite(a.history.longParentsPct)
    ) {
      historyHtml = `
        <div
          class="history history-compact"
          title="Dlouhodobý odhad poměru spotřeby Tomáš / Rodiče z archivu a smart statistik"
        >
          <strong>Poměr T / R</strong>
          <span>${this._fmt(a.history.longTomasPct, 0)} % / ${this._fmt(a.history.longParentsPct, 0)} % · od 26. 6. 2025</span>
        </div>`;
    }

'''
text = text[:history_start] + history_new + text[history_end:]

replace_once(
'''        .history {
          border-radius:11px;
          padding:7px 8px;
          background:rgba(127,127,127,.045);
        }
''',
'''        .history {
          border-radius:11px;
          padding:7px 8px;
          background:rgba(127,127,127,.045);
        }

        .history-compact {
          display:flex;
          align-items:baseline;
          justify-content:space-between;
          gap:8px;
          padding:5px 8px;
          min-width:0;
        }

        .history-compact strong {
          font-size:12px;
          white-space:nowrap;
        }

        .history-compact span {
          min-width:0;
          font-size:10px;
          opacity:.72;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:ellipsis;
        }
''',
    "HISTORY_CSS",
)

replace_once(
'''        .loads-head {
''',
'''        .monthline {
          display:flex;
          align-items:baseline;
          justify-content:space-between;
          gap:8px;
          min-width:0;
          padding:3px 8px;
          border-radius:9px;
          background:rgba(127,127,127,.04);
        }

        .monthline strong {
          font-size:14px;
          white-space:nowrap;
        }

        .monthline span {
          min-width:0;
          font-size:10px;
          opacity:.72;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:ellipsis;
        }

        .loads-head {
''',
    "MONTHLINE_CSS",
)

replace_once(
'''        /* Markvarec TV space-aware readability: 20260821-compact-allin-r1 */
        :host([data-tv-kiosk="1"]) .title small { font-size:13px; opacity:.82; }
''',
'''        /* Markvarec TV space-aware readability: 20260821-compact-allin-r1 */
        :host([data-tv-kiosk="1"]) .history-compact strong { font-size:14px; }
        :host([data-tv-kiosk="1"]) .history-compact span { font-size:12px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .monthline strong { font-size:16px; }
        :host([data-tv-kiosk="1"]) .monthline span { font-size:12px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .title small { font-size:13px; opacity:.82; }
''',
    "TV_COMPACT_CSS",
)

replace_once(
'''            <div class="rate">
              <strong>${this._esc(costText)}</strong>
              <small>${this._esc(rateDetail)}</small>
            </div>
''',
'''            <div
              class="rate"
              title="Celkový náklad za měsíc včetně měsíčního fixu; v prvním neúplném smart měsíci jde o odhad celku"
            >
              <strong>${this._esc(monthCostText)}</strong>
              <small>${this._esc(monthCostLabel)} · vč. fixu</small>
            </div>
''',
    "HERO_FINANCE",
)

meta_start = text.find('          <div class="meta">\n')
meta_end = text.find('          ${issueHtml}\n', meta_start)
if meta_start < 0 or meta_end < 0 or meta_end <= meta_start:
    raise SystemExit("META_RENDER_BLOCK_NOT_FOUND")

monthline = '''          <div
            class="monthline"
            title="Spotřeba obou kořenových větví za měsíc; stav dat říká, zda je období kompletní nebo dopočtené"
          >
            <strong>${this._esc(monthEnergyText)}</strong>
            <span>${this._esc(monthEnergyLabel)} · data ${this._esc(coverageText.toLowerCase())}</span>
          </div>

'''
text = text[:meta_start] + monthline + text[meta_end:]

replace_once(
    '<strong>Tomáš · podružné větve</strong>\n            <span>součást jeho kořenové větve</span>',
    '<strong>Podružné větve</strong>\n            <span>Tomáš</span>',
    "BRANCH_HEAD",
)
replace_once(
    '<strong>Tomáš · největší spotřebiče právě teď</strong>',
    '<strong>Největší spotřebiče právě teď</strong>',
    "LOADS_HEAD",
)

replace_once(
'''          display:flex;
          flex-direction:column;
          gap:7px;
          position:relative;
''',
'''          display:flex;
          flex-direction:column;
          gap:6px;
          position:relative;
''',
    "WRAP_GAP",
)
replace_once(
'''          padding:7px 8px;
          background:rgba(127,127,127,.055);
          text-align:left;
''',
'''          padding:6px 8px;
          background:rgba(127,127,127,.055);
          text-align:left;
''',
    "ROOT_CARD_PADDING",
)

required = (
    VERSION_NEW,
    'class="history history-compact"',
    'class="monthline"',
    '${this._esc(monthCostText)}',
    '${this._esc(monthCostLabel)} · vč. fixu',
    'Měsíc celkem',
    'Odhad celkem',
    'Největší spotřebiče právě teď',
    'const topLoads = a.loads.slice(0, 3);',
    'Math.max(0, siteMonthEnergy) * price + Math.max(0, fixedMonthly)',
)
for marker in required:
    if marker not in text:
        raise SystemExit(f"REQUIRED_MISSING={marker}")

render_start = text.find('    this.shadowRoot.innerHTML = `')
render_end = text.find('    this.shadowRoot.querySelectorAll("[data-entity]")', render_start)
render = text[render_start:render_end]
for forbidden in (
    '${this._esc(costText)}',
    '${this._esc(rateDetail)}',
    '<div class="meta">',
    '<small>Konečná cena</small>',
    'bez měsíčního fixu',
):
    if forbidden in render:
        raise SystemExit(f"VISIBLE_FORBIDDEN={forbidden}")

history_render = text[text.find("    let historyHtml"):text.find("    this.shadowRoot.innerHTML = `")]
for forbidden in ("sharebar", "sharelegend", "smart-share", "Smart od 20. 8."):
    if forbidden in history_render:
        raise SystemExit(f"HISTORY_NOT_COMPACT={forbidden}")

dst.write_text(text, encoding="utf-8")
new_raw = text.encode("utf-8")
print(f"PATCH_OK old_sha={actual} new_sha={hashlib.sha256(new_raw).hexdigest()} bytes={len(new_raw)}")
