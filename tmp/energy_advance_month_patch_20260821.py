#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_CARD_SHA = "3fc72aa7b5b65e962367f8b37b7cd388c70472750c03f4f42105180bf1ee1d98"
OLD_VERSION = "20260821-smart-sharebar-r2"
NEW_VERSION = "20260821-advance-month-r1"

def die(msg):
    raise SystemExit(msg)

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        die(f"{label}: expected exactly one anchor, got {count}")
    return text.replace(old, new, 1)

def main():
    if len(sys.argv) not in (3, 4):
        die("usage: energy_advance_month_patch_20260821.py CARD_JS CONFIG_YAML [--check-only]")
    card_path = Path(sys.argv[1])
    config_path = Path(sys.argv[2])
    check_only = len(sys.argv) == 4 and sys.argv[3] == "--check-only"
    if len(sys.argv) == 4 and not check_only:
        die("only supported optional flag is --check-only")

    card_bytes = card_path.read_bytes()
    card_sha = hashlib.sha256(card_bytes).hexdigest()
    if card_sha != EXPECTED_CARD_SHA:
        die(f"card precondition failed: expected {EXPECTED_CARD_SHA}, got {card_sha}")
    card = card_bytes.decode("utf-8")
    config = config_path.read_text(encoding="utf-8")

    version_count = card.count(OLD_VERSION)
    if version_count != 2:
        die(f"version precondition failed: expected 2 markers, got {version_count}")
    card = card.replace(OLD_VERSION, NEW_VERSION)

    card = replace_once(
        card,
        '''      fixed_monthly: "sensor.elektrina_fixni_poplatky_mesic",
''',
        '''      fixed_monthly: "sensor.elektrina_fixni_poplatky_mesic",
      advance_entity: "input_number.elektrina_zaloha_mesic",
''',
        "card advance config",
    )

    finance_anchor = '''    const monthEstimated = !monthComplete && Number.isFinite(financeParentRatio)
      && Number.isFinite(parentMonthEnergy);

    const issues = [];
'''
    finance_new = '''    const monthEstimated = !monthComplete && Number.isFinite(financeParentRatio)
      && Number.isFinite(parentMonthEnergy);

    // The monthly advance is the user's real cash-flow baseline. A forecast is
    // deliberately allowed to replace it only when current month-to-date usage
    // points above the advance. The first 48 h of a month are too noisy for a
    // headline forecast, so the advance remains authoritative during that guard.
    const advanceMonthly = this._num(c.advance_entity, NaN);
    const projectionNow = new Date();
    const projectionMonthStart = new Date(
      projectionNow.getFullYear(),
      projectionNow.getMonth(),
      1,
      0, 0, 0, 0
    );
    const projectionMonthEnd = new Date(
      projectionNow.getFullYear(),
      projectionNow.getMonth() + 1,
      1,
      0, 0, 0, 0
    );
    const projectionMonthMs = Math.max(1, projectionMonthEnd.getTime() - projectionMonthStart.getTime());
    const projectionElapsedMs = Math.max(
      0,
      Math.min(projectionMonthMs, projectionNow.getTime() - projectionMonthStart.getTime())
    );
    const projectionElapsedHours = projectionElapsedMs / 3600000;
    const projectionFraction = projectionElapsedMs / projectionMonthMs;
    const projectionReady = projectionElapsedHours >= 48
      && projectionFraction > 0
      && Number.isFinite(siteMonthEnergy)
      && siteMonthEnergy > 0
      && Number.isFinite(price)
      && Number.isFinite(fixedMonthly);
    const projectedMonthEnergy = projectionReady
      ? Math.max(0, siteMonthEnergy) / projectionFraction
      : NaN;
    const projectedMonthCost = projectionReady
      ? Math.max(0, projectedMonthEnergy) * price + Math.max(0, fixedMonthly)
      : NaN;
    const hasAdvance = Number.isFinite(advanceMonthly) && advanceMonthly > 0;
    const overAdvance = hasAdvance
      && Number.isFinite(projectedMonthCost)
      && projectedMonthCost > advanceMonthly + 1;
    const financeReferenceCost = hasAdvance
      ? (overAdvance ? projectedMonthCost : advanceMonthly)
      : (Number.isFinite(projectedMonthCost) ? projectedMonthCost : siteMonthCost);
    const overAdvanceAmount = overAdvance ? projectedMonthCost - advanceMonthly : 0;

    // Split the same headline reference amount so Tomáš + rodiče always sums
    // exactly to what the card shows at the top. The shared fixed charge is
    // thereby allocated proportionally by current-calendar-month kWh share.
    const tomasMonthRatio = Number.isFinite(siteMonthEnergy) && siteMonthEnergy > 0
      && Number.isFinite(monthEnergy)
      ? Math.max(0, Math.min(1, Math.max(0, monthEnergy) / siteMonthEnergy))
      : NaN;
    const parentsMonthRatio = Number.isFinite(tomasMonthRatio) ? 1 - tomasMonthRatio : NaN;
    const tomasReferenceCost = Number.isFinite(financeReferenceCost) && Number.isFinite(tomasMonthRatio)
      ? financeReferenceCost * tomasMonthRatio
      : NaN;
    const parentsReferenceCost = Number.isFinite(financeReferenceCost) && Number.isFinite(tomasReferenceCost)
      ? Math.max(0, financeReferenceCost - tomasReferenceCost)
      : NaN;

    const issues = [];
'''
    card = replace_once(card, finance_anchor, finance_new, "finance projection")

    card = replace_once(
        card,
        '''      price, effectivePrice, costPerHour, monthEnergy, fixedMonthly,
      month: {
''',
        '''      price, effectivePrice, costPerHour, monthEnergy, fixedMonthly, advanceMonthly,
      finance: {
        projectionReady,
        projectedMonthEnergy,
        projectedMonthCost,
        referenceCost: financeReferenceCost,
        overAdvance,
        overAdvanceAmount,
        tomasMonthRatio,
        parentsMonthRatio,
        tomasReferenceCost,
        parentsReferenceCost,
      },
      month: {
''',
        "analysis return finance",
    )

    card = replace_once(
        card,
        '''      a.monthEnergy, a.fixedMonthly, a.month.parents, a.month.total, a.month.cost, a.month.complete, a.month.estimated,
''',
        '''      a.monthEnergy, a.fixedMonthly, a.advanceMonthly,
      a.finance.projectionReady, a.finance.projectedMonthCost, a.finance.referenceCost,
      a.finance.overAdvance, a.finance.overAdvanceAmount,
      a.finance.tomasMonthRatio, a.finance.parentsMonthRatio,
      a.finance.tomasReferenceCost, a.finance.parentsReferenceCost,
      a.month.parents, a.month.total, a.month.cost, a.month.complete, a.month.estimated,
''',
        "render key finance",
    )

    render_anchor = '''    const rateDetail = Number.isFinite(a.effectivePrice)
      ? `${a.month.complete ? "konečná efektivní cena" : "odhad konečné efektivní ceny"} ${finalPriceText}`
      : "Konečná cena zatím není dostupná";

    let historyHtml = "";
'''
    render_new = '''    const rateDetail = Number.isFinite(a.effectivePrice)
      ? `${a.month.complete ? "konečná efektivní cena" : "odhad konečné efektivní ceny"} ${finalPriceText}`
      : "Konečná cena zatím není dostupná";

    const advanceText = Number.isFinite(a.advanceMonthly) && a.advanceMonthly > 0
      ? `${this._fmt(a.advanceMonthly, 0)} Kč`
      : "—";
    const projectedMonthCostText = Number.isFinite(a.finance.projectedMonthCost)
      ? `${this._fmt(a.finance.projectedMonthCost, 0)} Kč`
      : "—";
    const financeReferenceText = Number.isFinite(a.finance.referenceCost)
      ? `${this._fmt(a.finance.referenceCost, 0)} Kč`
      : monthCostText;
    const financeHeadlineLabel = a.finance.overAdvance
      ? "Odhad měsíce"
      : (Number.isFinite(a.advanceMonthly) && a.advanceMonthly > 0 ? "Záloha" : monthCostLabel);
    const financeHeadlineDetail = a.finance.overAdvance
      ? `+${this._fmt(a.finance.overAdvanceAmount, 0)} Kč nad zálohu ${advanceText}`
      : (a.finance.projectionReady
          ? `odhad měsíce ${projectedMonthCostText}`
          : "odhad měsíce po prvních 48 h");
    const monthNameRaw = new Intl.DateTimeFormat("cs-CZ", { month: "long" }).format(new Date());
    const monthName = monthNameRaw ? monthNameRaw.charAt(0).toUpperCase() + monthNameRaw.slice(1) : "Tento měsíc";
    const financeSplitReady = Number.isFinite(a.finance.tomasReferenceCost)
      && Number.isFinite(a.finance.parentsReferenceCost);
    const financeSplitLabel = `${monthName} · poměrný podíl${a.month.estimated ? " (odhad)" : ""}`;
    const financeSplitText = financeSplitReady
      ? `Tomáš ${this._fmt(a.finance.tomasReferenceCost, 0)} Kč · rodiče ${this._fmt(a.finance.parentsReferenceCost, 0)} Kč`
      : "Poměrný podíl se dopočítává";

    let historyHtml = "";
'''
    card = replace_once(card, render_anchor, render_new, "render finance text")

    card = replace_once(
        card,
        '''            <span>T ${this._fmt(smartTomasKwh, 1)} kWh · R ${this._fmt(smartParentsKwh, 1)} kWh · od 20. 8.</span>
''',
        '''            <span>Tomáš ${this._fmt(smartTomasKwh, 1)} kWh · rodiče ${this._fmt(smartParentsKwh, 1)} kWh · od 20. 8.</span>
''',
        "smart kWh labels",
    )
    card = replace_once(
        card,
        '''              <b>T ${this._fmt(smartTomasPct, 0)} %</b>
''',
        '''              <b>${this._fmt(smartTomasPct, 0)} %</b>
''',
        "Tomáš percent prefix",
    )
    card = replace_once(
        card,
        '''              <b>R ${this._fmt(smartParentsPct, 0)} %</b>
''',
        '''              <b>${this._fmt(smartParentsPct, 0)} %</b>
''',
        "parents percent prefix",
    )

    css_anchor = '''        .monthline {
          display:flex;
'''
    css_new = '''        .rate.rate-over {
          outline:1px solid var(--warning-color, #f9a825);
          background:color-mix(in srgb, var(--warning-color, #f9a825) 10%, transparent);
        }

        .finance-split {
          display:flex;
          align-items:baseline;
          justify-content:space-between;
          gap:8px;
          min-width:0;
          padding:3px 8px;
          border-radius:9px;
          background:rgba(127,127,127,.055);
        }

        .finance-split strong {
          font-size:11px;
          opacity:.76;
          white-space:nowrap;
        }

        .finance-split span {
          min-width:0;
          font-size:11px;
          text-align:right;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:ellipsis;
        }

        .monthline {
          display:flex;
'''
    card = replace_once(card, css_anchor, css_new, "finance split css")

    hero_old = '''            <div
              class="rate"
              title="Celkový náklad za měsíc včetně měsíčního fixu; v prvním neúplném smart měsíci jde o odhad celku"
            >
              <strong>${this._esc(monthCostText)}</strong>
              <small>${this._esc(monthCostLabel)} · vč. fixu</small>
            </div>
'''
    hero_new = '''            <div
              class="rate ${a.finance.overAdvance ? "rate-over" : ""}"
              title="Záloha je skutečný měsíční cash-flow základ. Odhad konce měsíce ji nahradí jen tehdy, když vychází výš; všechny částky už zahrnují společný měsíční fix právě jednou."
            >
              <strong>${this._esc(financeReferenceText)}</strong>
              <small>${this._esc(financeHeadlineLabel)} · ${this._esc(financeHeadlineDetail)}</small>
            </div>
'''
    card = replace_once(card, hero_old, hero_new, "hero finance")

    monthline_old = '''          <div
            class="monthline"
            title="Spotřeba obou kořenových větví za měsíc; stav dat říká, zda je období kompletní nebo dopočtené"
          >
            <strong>${this._esc(monthEnergyText)}</strong>
            <span>${this._esc(monthEnergyLabel)} · data ${this._esc(coverageText.toLowerCase())}</span>
          </div>

          ${issueHtml}
'''
    monthline_new = '''          <div
            class="monthline"
            title="Spotřeba obou kořenových větví za aktuální kalendářní měsíc; stav dat říká, zda je období kompletní nebo dopočtené"
          >
            <strong>${this._esc(monthEnergyText)}</strong>
            <span>${this._esc(monthEnergyLabel)} · data ${this._esc(coverageText.toLowerCase())}</span>
          </div>

          <div
            class="finance-split"
            title="Poměrné rozdělení stejné částky, která je nahoře: podle podílu kWh v aktuálním kalendářním měsíci. Není to účetní saldo rodičů ani částka od posledního vyúčtování."
          >
            <strong>${this._esc(financeSplitLabel)}</strong>
            <span>${this._esc(financeSplitText)}</span>
          </div>

          ${issueHtml}
'''
    card = replace_once(card, monthline_old, monthline_new, "finance split render")

    card = replace_once(
        card,
        '''    description: "Přehled Markvarce: dvě kořenové větve, barevné zatížení, dlouhodobý poměr a společná cena včetně fixu.",
''',
        '''    description: "Přehled Markvarce: dvě kořenové větve, barevné zatížení, smart poměr a měsíční záloha s vyšším odhadem při nadspotřebě.",
''',
        "card description",
    )

    config_old = '''  elektrina_fixni_poplatky_mesic:
    name: "Elektřina - fixní poplatky měsíčně"
    min: 0
    max: 2000
    step: 0.01
    unit_of_measurement: "CZK"
    icon: mdi:calendar-cash
    mode: box

utility_meter:
'''
    config_new = '''  elektrina_fixni_poplatky_mesic:
    name: "Elektřina - fixní poplatky měsíčně"
    min: 0
    max: 2000
    step: 0.01
    unit_of_measurement: "CZK"
    icon: mdi:calendar-cash
    mode: box

  elektrina_zaloha_mesic:
    name: "Elektřina - měsíční záloha"
    min: 0
    max: 20000
    step: 10
    unit_of_measurement: "CZK"
    icon: mdi:cash-sync
    mode: box

utility_meter:
'''
    config = replace_once(config, config_old, config_new, "HA advance helper")

    if '· vč. fixu' in card:
        die("visible vč. fixu marker unexpectedly remains")
    if '<b>T ${this._fmt(smartTomasPct' in card or '<b>R ${this._fmt(smartParentsPct' in card:
        die("T/R percent prefixes unexpectedly remain")
    if '#ef6c00' not in card:
        die("parents orange identity disappeared")
    if 'history_refresh_ms: 900000' not in card:
        die("15-minute smart history refresh disappeared")
    if 'history_start: "2026-08-20T15:00:00+02:00"' not in card:
        die("smart history baseline disappeared")

    if check_only:
        print("ENERGY_ADVANCE_MONTH_PATCH_20260821_CHECK_OK")
        return

    card_path.write_text(card, encoding="utf-8")
    config_path.write_text(config, encoding="utf-8")
    print("ENERGY_ADVANCE_MONTH_PATCH_20260821_OK")
    print("CARD_SHA=" + hashlib.sha256(card_path.read_bytes()).hexdigest())

if __name__ == "__main__":
    main()
