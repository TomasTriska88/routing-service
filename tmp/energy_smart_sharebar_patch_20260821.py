#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_SHA256 = "969344785c0c44be675aff6d6960f11ea4a29d1dc99cf9ce650cadca1a462e68"
VERSION_OLD = "20260821-compact-allin-r1"
VERSION_NEW = "20260821-smart-sharebar-r1"

if len(sys.argv) != 3:
    raise SystemExit("usage: energy_smart_sharebar_patch_20260821.py INPUT OUTPUT")

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

old_history = '''    let historyHtml = "";

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

new_history = '''    let historyHtml = "";
    const smartTomasKwh = Number(a.history.tomas);
    const smartParentsKwh = Number(a.history.parents);
    const smartTomasPct = Number(a.history.tomasPct);
    const smartParentsPct = Number(a.history.parentsPct);
    const smartShareReady =
      Number.isFinite(smartTomasKwh) &&
      Number.isFinite(smartParentsKwh) &&
      Number.isFinite(smartTomasPct) &&
      Number.isFinite(smartParentsPct) &&
      smartTomasKwh + smartParentsKwh > 0;
    const clampPct = (v) => Math.max(0, Math.min(100, Number(v) || 0));

    if (smartShareReady) {
      historyHtml = `
        <div
          class="history history-smart"
          title="Skutečný kumulativní poměr spotřeby Tomáš / Rodiče pouze ze společné smart historie obou kořenových měřáků od zapojení rodičovského elektroměru 20. 8. 2026"
        >
          <div class="history-smart-head">
            <strong>Tomáš vs. rodiče</strong>
            <span>T ${this._fmt(smartTomasKwh, 1)} kWh · R ${this._fmt(smartParentsKwh, 1)} kWh · od 20. 8.</span>
          </div>
          <div
            class="smart-sharebar"
            role="img"
            aria-label="Podíl spotřeby od 20. 8. 2026: Tomáš ${this._fmt(smartTomasPct, 0)} procent, rodiče ${this._fmt(smartParentsPct, 0)} procent"
          >
            <span class="smart-sharebar-tomas" style="width:${clampPct(smartTomasPct)}%">
              <b>T ${this._fmt(smartTomasPct, 0)} %</b>
            </span>
            <span class="smart-sharebar-parents" style="width:${clampPct(smartParentsPct)}%">
              <b>R ${this._fmt(smartParentsPct, 0)} %</b>
            </span>
          </div>
        </div>`;
    } else {
      const smartStateText = a.history.loading
        ? "Načítám společnou smart historii od 20. 8."
        : "Společná smart historie od 20. 8. zatím nestačí pro poměr";
      historyHtml = `
        <div
          class="history history-smart history-smart-empty"
          title="Poměr se nikdy nedoplňuje historickým odhadem; čeká výhradně na společná smart data obou kořenových měřáků"
        >
          <strong>Tomáš vs. rodiče</strong>
          <span>${this._esc(smartStateText)}</span>
        </div>`;
    }

'''
replace_once(old_history, new_history, "HISTORY_RENDER")

old_css = '''        .history-compact {
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
'''

new_css = '''        .history-smart {
          display:flex;
          flex-direction:column;
          gap:4px;
          padding:5px 8px;
          min-width:0;
        }

        .history-smart-head {
          display:flex;
          align-items:baseline;
          justify-content:space-between;
          gap:8px;
          min-width:0;
        }

        .history-smart-head strong,
        .history-smart-empty strong {
          font-size:12px;
          white-space:nowrap;
        }

        .history-smart-head span,
        .history-smart-empty span {
          min-width:0;
          font-size:10px;
          opacity:.72;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:ellipsis;
        }

        .history-smart-empty {
          flex-direction:row;
          align-items:baseline;
          justify-content:space-between;
          gap:8px;
        }

        .smart-sharebar {
          display:flex;
          width:100%;
          height:14px;
          overflow:hidden;
          border-radius:999px;
          background:rgba(127,127,127,.12);
        }

        .smart-sharebar > span {
          display:flex;
          align-items:center;
          justify-content:center;
          min-width:0;
          overflow:hidden;
        }

        .smart-sharebar-tomas {
          background:var(--primary-color);
          color:var(--text-primary-color, #fff);
        }

        .smart-sharebar-parents {
          background:var(--secondary-text-color);
          color:var(--card-background-color, #fff);
        }

        .smart-sharebar b {
          padding:0 3px;
          font-size:9px;
          line-height:1;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:clip;
        }
'''
replace_once(old_css, new_css, "HISTORY_CSS")

old_tv = '''        :host([data-tv-kiosk="1"]) .history-compact strong { font-size:14px; }
        :host([data-tv-kiosk="1"]) .history-compact span { font-size:12px; opacity:.82; }
'''
new_tv = '''        :host([data-tv-kiosk="1"]) .history-smart-head strong,
        :host([data-tv-kiosk="1"]) .history-smart-empty strong { font-size:14px; }
        :host([data-tv-kiosk="1"]) .history-smart-head span,
        :host([data-tv-kiosk="1"]) .history-smart-empty span { font-size:12px; opacity:.82; }
        :host([data-tv-kiosk="1"]) .smart-sharebar { height:18px; }
        :host([data-tv-kiosk="1"]) .smart-sharebar b { font-size:12px; }
'''
replace_once(old_tv, new_tv, "TV_HISTORY_CSS")

required = (
    VERSION_NEW,
    'history_start: "2026-08-20T15:00:00+02:00"',
    'type: "recorder/statistics_during_period"',
    'const smartTomasKwh = Number(a.history.tomas);',
    'const smartParentsKwh = Number(a.history.parents);',
    'const smartTomasPct = Number(a.history.tomasPct);',
    'const smartParentsPct = Number(a.history.parentsPct);',
    'class="smart-sharebar"',
    'class="smart-sharebar-tomas"',
    'class="smart-sharebar-parents"',
    'T ${this._fmt(smartTomasKwh, 1)} kWh',
    'R ${this._fmt(smartParentsKwh, 1)} kWh',
    'od 20. 8.',
    'const topLoads = a.loads.slice(0, 3);',
    'class="monthline"',
    '${this._esc(monthCostText)}',
    '${this._esc(monthCostLabel)} · vč. fixu',
)
for marker in required:
    if marker not in text:
        raise SystemExit(f"REQUIRED_MISSING={marker}")

history_start = text.find('    let historyHtml = "";')
history_end = text.find('    this.shadowRoot.innerHTML = `', history_start)
if history_start < 0 or history_end < 0:
    raise SystemExit("HISTORY_RENDER_RANGE_NOT_FOUND")
history_render = text[history_start:history_end]
for forbidden in (
    "a.history.longTomas",
    "a.history.longParents",
    "26. 6. 2025",
    "Dlouhodobý odhad",
    "historical_anchor_tomas_kwh",
    "historical_anchor_parents_kwh",
):
    if forbidden in history_render:
        raise SystemExit(f"STALE_HISTORY_VISIBLE={forbidden}")

if history_render.count('class="smart-sharebar"') != 1:
    raise SystemExit("SMART_SHAREBAR_RENDER_COUNT_BAD")

dst.write_text(text, encoding="utf-8")
new_raw = text.encode("utf-8")
print(f"PATCH_OK old_sha={actual} new_sha={hashlib.sha256(new_raw).hexdigest()} bytes={len(new_raw)}")
