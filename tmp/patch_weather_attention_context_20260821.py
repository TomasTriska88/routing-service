#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WEATHER = Path("/config/www/lina-weather-card.js")
CONTEXT = Path("/config/www/markvarec-domain-context.json")
TEST = Path("/config/tests/test_lina_weather_attention_context_regression.py")
EXPECTED_SHA = "3aa526de87e25742da90c6d83dfc9fb83e1f441db2ca41e7ba3e5c86ec2e802e"
TAG = "20260821-attention-context-r1"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)

def build_context() -> dict:
    now = datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")
    return {
        "schema_version": 1,
        "updated_at": now,
        "managed_by": "Hnízdo Knowledge Sync",
        "priority_contract": ["critical", "action", "watch", "info", "normal"],
        "domains": {
            "weather": {
                "lifecycle": "active",
                "uncertainty": "confirmed",
                "attention": {
                    "wind_relevant": "watch",
                    "wind_with_imminent_rain_or_storm": "action",
                    "active_lightning": "critical",
                    "physical_impact": "critical",
                    "critical_numeric_wind_threshold": None
                },
                "local_risks": {
                    "tree_hazard": {
                        "lifecycle": "active",
                        "uncertainty": "confirmed"
                    }
                }
            },
            "climate": {
                "lifecycle": "active",
                "uncertainty": "confirmed",
                "devices": {
                    "concept_qh4100_smart": {
                        "lifecycle": "defective",
                        "uncertainty": "confirmed",
                        "replacement_available": True,
                        "replacement_identity": None,
                        "replacement_ha_integration": "unknown"
                    }
                }
            },
            "security": {
                "lifecycle": "active",
                "uncertainty": "confirmed"
            },
            "water": {
                "lifecycle": "active",
                "uncertainty": "confirmed",
                "devices": {
                    "gardena_4700_2": {
                        "lifecycle": "return_pending",
                        "uncertainty": "confirmed",
                        "long_term_available_2026": False
                    }
                }
            },
            "energy": {
                "lifecycle": "active",
                "uncertainty": "confirmed"
            },
            "lina": {
                "lifecycle": "active",
                "uncertainty": "confirmed"
            }
        }
    }

CONTEXT_METHODS = r'''
  connectedCallback() {
    this._loadDomainContext();
  }

  async _loadDomainContext() {
    if (this._domainContextLoaded || this._domainContextLoading) return;
    this._domainContextLoading = true;
    try {
      const response = await fetch("/local/markvarec-domain-context.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`domain context HTTP ${response.status}`);
      const model = await response.json();
      if (Number(model?.schema_version) !== 1 ||
          !Array.isArray(model?.priority_contract) ||
          !model?.domains?.weather) {
        throw new Error("invalid Markvarec domain context");
      }
      this._domainContext = model;
    } catch (_) {
      this._domainContext = null;
    } finally {
      this._domainContextLoading = false;
      this._domainContextLoaded = true;
      this._renderKey = "";
      this._render(true);
    }
  }

  _weatherAttentionPolicy() {
    const allowed = new Set(["critical", "action", "watch", "info", "normal"]);
    const attention = this._domainContext?.domains?.weather?.attention || {};
    const pick = (key, fallback) => allowed.has(attention[key]) ? attention[key] : fallback;
    return {
      windRelevant: pick("wind_relevant", "watch"),
      compoundWind: pick("wind_with_imminent_rain_or_storm", "action"),
      activeLightning: pick("active_lightning", "critical"),
    };
  }

'''

ATTENTION_CALC = r'''    const activeLightning = ["lightning","lightning-rainy"].includes(condRaw);
    const stormSoon = activeLightning || hourly.slice(0,3).some(
      f => ["lightning","lightning-rainy"].includes(String(f?.condition || ""))
    );
    const compoundWind = windRelevant && (rainSoon || stormSoon);
    const attentionPolicy = this._weatherAttentionPolicy();
    const weatherAttention = activeLightning ? attentionPolicy.activeLightning :
      compoundWind ? attentionPolicy.compoundWind :
      windRelevant ? attentionPolicy.windRelevant : "normal";
    const attentionClass = weatherAttention !== "normal" ? `attention-${weatherAttention}` : "";
'''

CSS = r'''
        ha-card.attention-watch {
          box-shadow:inset 0 0 0 2px rgba(255,193,7,.42),0 0 18px rgba(255,193,7,.14);
        }
        ha-card.attention-action {
          box-shadow:inset 0 0 0 2px rgba(255,152,0,.58),0 0 22px rgba(255,152,0,.22);
        }
        ha-card.attention-critical {
          box-shadow:inset 0 0 0 2px rgba(244,67,54,.78),0 0 28px rgba(244,67,54,.32);
        }
        .wrap.attention-watch {
          background:radial-gradient(circle at 82% 12%,rgba(255,193,7,.16),transparent 37%),var(--ha-card-background,var(--card-background-color,#fff));
        }
        .wrap.attention-action {
          background:radial-gradient(circle at 82% 12%,rgba(255,152,0,.23),transparent 40%),var(--ha-card-background,var(--card-background-color,#fff));
        }
        .wrap.attention-critical {
          background:radial-gradient(circle at 82% 12%,rgba(244,67,54,.30),transparent 43%),var(--ha-card-background,var(--card-background-color,#fff));
        }
'''

TEST_CONTENT = r'''#!/usr/bin/env python3
import json
import re
from pathlib import Path

weather = Path("/config/www/lina-weather-card.js").read_text(encoding="utf-8")
context = json.loads(Path("/config/www/markvarec-domain-context.json").read_text(encoding="utf-8"))

assert context["schema_version"] == 1
assert context["priority_contract"] == ["critical", "action", "watch", "info", "normal"]
assert set(context["domains"]) == {"weather", "climate", "security", "water", "energy", "lina"}

att = context["domains"]["weather"]["attention"]
assert att["wind_relevant"] == "watch"
assert att["wind_with_imminent_rain_or_storm"] == "action"
assert att["active_lightning"] == "critical"
assert att["critical_numeric_wind_threshold"] is None

qh = context["domains"]["climate"]["devices"]["concept_qh4100_smart"]
assert qh["lifecycle"] == "defective"
assert qh["replacement_available"] is True
assert qh["replacement_identity"] is None
assert qh["replacement_ha_integration"] == "unknown"

gardena = context["domains"]["water"]["devices"]["gardena_4700_2"]
assert gardena["lifecycle"] == "return_pending"
assert gardena["long_term_available_2026"] is False

assert 'fetch("/local/markvarec-domain-context.json", { cache: "no-store" })' in weather
assert 'this._domainContext = null;' in weather
assert 'windRelevant: pick("wind_relevant", "watch")' in weather
assert 'compoundWind: pick("wind_with_imminent_rain_or_storm", "action")' in weather
assert 'activeLightning: pick("active_lightning", "critical")' in weather
assert 'const activeLightning = ["lightning","lightning-rainy"].includes(condRaw);' in weather
assert 'const compoundWind = windRelevant && (rainSoon || stormSoon);' in weather
assert 'attention-${weatherAttention}' in weather
assert 'ha-card.attention-watch' in weather
assert 'ha-card.attention-action' in weather
assert 'ha-card.attention-critical' in weather
assert '<ha-card class="${cardClass}">' in weather
assert '<div class="wrap ${cardClass}">' in weather

critical_window = weather[weather.index("const activeLightning"):weather.index("const renderKey")]
assert not re.search(r'windKmh\s*[><=].*critical|gustKmh\s*[><=].*critical', critical_window, re.I)

print("WEATHER_ATTENTION_CONTEXT_REGRESSION_OK")
'''

def build_weather(source: str) -> str:
    if "markvarec-domain-context.json" in source:
        raise SystemExit("weather already contains domain-context integration")
    if "connectedCallback()" in source:
        raise SystemExit("weather already has connectedCallback; inspect before patching")
    source = replace_once(
        source,
        "  _windUnit() {",
        CONTEXT_METHODS + "  _windUnit() {",
        "insert context methods",
    )
    gust_block = '''    const gustRelevant = Number.isFinite(gustKmh) &&
      (!Number.isFinite(windKmh) || gustKmh >= Math.max(windKmh * 1.45, windKmh + 8));
'''
    source = replace_once(
        source,
        gust_block,
        gust_block + ATTENTION_CALC,
        "insert attention calculation",
    )
    source = replace_once(
        source,
        "      radar,nextRain,tempTrend,irr,hourly,daily,pressureTrend\n",
        "      radar,nextRain,tempTrend,irr,hourly,daily,pressureTrend,weatherAttention,this._domainContext?.updated_at || null\n",
        "render key",
    )
    source = replace_once(
        source,
        '    const accentClass = rainSoon ? "rain" : hot ? "hot" : frost ? "frost" : "calm";\n',
        '    const accentClass = rainSoon ? "rain" : hot ? "hot" : frost ? "frost" : "calm";\n'
        '    const cardClass = [accentClass, attentionClass].filter(Boolean).join(" ");\n',
        "card class",
    )
    source = replace_once(
        source,
        '        .frost .current { border-radius:13px; background:rgba(3,169,244,.09); }\n',
        '        .frost .current { border-radius:13px; background:rgba(3,169,244,.09); }\n' + CSS,
        "attention CSS",
    )
    source = replace_once(
        source,
        '<ha-card class="${accentClass}">',
        '<ha-card class="${cardClass}">',
        "ha-card class",
    )
    source = replace_once(
        source,
        '<div class="wrap ${accentClass}">',
        '<div class="wrap ${cardClass}">',
        "wrap class",
    )
    return source

def verify_outputs(weather_text: str, context: dict) -> None:
    if 'const activeLightning = ["lightning","lightning-rainy"].includes(condRaw);' not in weather_text:
        raise SystemExit("missing activeLightning")
    if 'const compoundWind = windRelevant && (rainSoon || stormSoon);' not in weather_text:
        raise SystemExit("missing compound wind")
    if context["domains"]["weather"]["attention"]["critical_numeric_wind_threshold"] is not None:
        raise SystemExit("critical numeric wind threshold must remain null")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.check == args.apply:
        raise SystemExit("choose exactly one of --check or --apply")

    if not WEATHER.exists():
        raise SystemExit(f"missing {WEATHER}")
    current_sha = sha256(WEATHER)
    if current_sha != EXPECTED_SHA:
        raise SystemExit(f"unexpected weather SHA {current_sha}; expected {EXPECTED_SHA}")
    if CONTEXT.exists():
        raise SystemExit(f"{CONTEXT} already exists; inspect before overwriting")

    source = WEATHER.read_text(encoding="utf-8")
    updated = build_weather(source)
    context = build_context()
    verify_outputs(updated, context)

    if args.check:
        print(f"INPUT_SHA={current_sha}")
        print(f"OUTPUT_BYTES={len(updated.encode('utf-8'))}")
        print(f"OUTPUT_SHA={hashlib.sha256(updated.encode('utf-8')).hexdigest()}")
        print("PATCH_CHECK_OK")
        return

    stamp = datetime.now(ZoneInfo("Europe/Prague")).strftime("%Y%m%d-%H%M%S")
    weather_backup = WEATHER.with_name(WEATHER.name + f".bak-attention-context-{stamp}")
    shutil.copy2(WEATHER, weather_backup)

    weather_tmp = WEATHER.with_suffix(WEATHER.suffix + ".attention-context.tmp")
    context_tmp = CONTEXT.with_suffix(CONTEXT.suffix + ".tmp")
    test_tmp = TEST.with_suffix(TEST.suffix + ".tmp")
    weather_tmp.write_text(updated, encoding="utf-8")
    context_tmp.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    test_tmp.write_text(TEST_CONTENT, encoding="utf-8")

    json.loads(context_tmp.read_text(encoding="utf-8"))
    compile(test_tmp.read_text(encoding="utf-8"), str(test_tmp), "exec")
    verify_outputs(weather_tmp.read_text(encoding="utf-8"), json.loads(context_tmp.read_text(encoding="utf-8")))

    os.replace(weather_tmp, WEATHER)
    os.replace(context_tmp, CONTEXT)
    os.replace(test_tmp, TEST)

    print(f"BACKUP={weather_backup}")
    print(f"WEATHER_SHA={sha256(WEATHER)}")
    print(f"WEATHER_BYTES={WEATHER.stat().st_size}")
    print(f"CONTEXT_SHA={sha256(CONTEXT)}")
    print(f"CONTEXT_BYTES={CONTEXT.stat().st_size}")
    print(f"TEST_SHA={sha256(TEST)}")
    print(f"RESOURCE_TAG={TAG}")
    print("PATCH_APPLY_OK")

if __name__ == "__main__":
    main()
