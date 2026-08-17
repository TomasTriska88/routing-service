#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import hashlib, json, os, shutil, sys

SEC = Path("/config/www/lina-security-card.js")
CLI = Path("/config/www/lina-climate-safety-card.js")
RES = Path("/config/.storage/lovelace_resources")
MANIFEST = Path("/tmp/hnizdo_semantic_patch_manifest.json")

OLD_SEC_SHA = "38f482b42619235a86ffe49d207718493ef92a88d0266a4e50513cfa36cdaae9"
OLD_CLI_SHA = "623c5b94aaa97093ca0c69c026b19859f96c16e821efac7515fecc0452553499"
OLD_SEC_URL = "/local/lina-security-card.js?v=20260818-v1"
NEW_SEC_URL = "/local/lina-security-card.js?v=20260818-v2"
OLD_CLI_URL = "/local/lina-climate-safety-card.js?v=20260817-v1"
NEW_CLI_URL = "/local/lina-climate-safety-card.js?v=20260818-v2"

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def replace_one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)

def prepare():
    if sha(SEC) != OLD_SEC_SHA:
        raise RuntimeError(f"security source changed: {sha(SEC)}")
    if sha(CLI) != OLD_CLI_SHA:
        raise RuntimeError(f"climate source changed: {sha(CLI)}")

    sec = SEC.read_text(encoding="utf-8")
    sec = replace_one(
        sec,
        "      security_entity: 'binary_sensor.zabezpeceni_zahrady_aktivni',\n"
        "      window_entity: 'binary_sensor.tz3000_a33rw7ou_ts0203',",
        "      security_entity: 'binary_sensor.zabezpeceni_zahrady_aktivni',\n"
        "      presence_entity: 'binary_sensor.markvarec_nekdo_doma',\n"
        "      window_entity: 'binary_sensor.tz3000_a33rw7ou_ts0203',",
        "security presence config",
    )
    sec = replace_one(
        sec,
        "    const armed = this._isOn(c.security_entity);\n"
        "    const windowOpen = this._isOn(c.window_entity);\n"
        "    const insideDoorOpen = this._isOn(c.inside_door_entity);\n"
        "    // This entity is a physical lock-state sensor, NOT door-leaf position.\n"
        "    // On = unlocked according to the existing Markvarec security semantics.\n"
        "    const outsideUnlocked = this._isOn(c.outside_lock_entity);\n"
        "    const poultryPresent = this._isOn(c.poultry_entity);\n",
        "    const armed = this._isOn(c.security_entity);\n"
        "    const someoneHome = this._isOn(c.presence_entity);\n"
        "    const presenceUnknown = this._unknown(c.presence_entity);\n"
        "    const windowOpen = this._isOn(c.window_entity);\n"
        "    const insideDoorOpen = this._isOn(c.inside_door_entity);\n"
        "    // This entity is a physical lock-state sensor, NOT door-leaf position.\n"
        "    // On = unlocked according to the existing Markvarec security semantics.\n"
        "    const outsideUnlocked = this._isOn(c.outside_lock_entity);\n"
        "    // Poultry radar is advisory activity only; it never proves the birds are closed in.\n"
        "    const poultryPresent = this._isOn(c.poultry_entity);\n"
        "    const windowRisk = armed && windowOpen && !someoneHome;\n",
        "security render preamble",
    )
    sec = replace_one(
        sec,
        "    const sensorUnknown = [c.security_entity,c.window_entity,c.inside_door_entity,c.outside_lock_entity,c.poultry_entity]\n"
        "      .filter(id => this._unknown(id));",
        "    const sensorUnknown = [c.security_entity,c.window_entity,c.outside_lock_entity]\n"
        "      .filter(id => this._unknown(id));",
        "security unknown set",
    )
    sec = replace_one(
        sec,
        "    if (armed && outsideUnlocked) alarmIssues.push({ icon:'🔓', title:'Venkovní dveře jsou odemčené', detail:'Zabezpečení je aktivní', entity:c.outside_lock_entity, severity:'critical' });\n"
        "    if (armed && windowOpen) alarmIssues.push({ icon:'🪟', title:'Okno v ložnici je otevřené', detail:'Zabezpečení je aktivní', entity:c.window_entity, severity:'critical' });\n"
        "    if (armed && insideDoorOpen) alarmIssues.push({ icon:'🚪', title:'Vnitřní dveře jsou otevřené', detail:'Ložnice ↔ technická', entity:c.inside_door_entity, severity:'warn' });\n"
        "    if (sensorUnknown.length) alarmIssues.push({ icon:'⚠️', title:'Část zabezpečení nemá data', detail:`${sensorUnknown.length} ${sensorUnknown.length === 1 ? 'zdroj' : 'zdroje'}`, entity:sensorUnknown[0], severity:'warn' });",
        "    if (armed && outsideUnlocked) alarmIssues.push({ icon:'🔓', title:'Venkovní zámek je odemčený', detail:'Zabezpečení je aktivní', entity:c.outside_lock_entity, severity:'critical' });\n"
        "    if (windowRisk) alarmIssues.push({ icon:'🪟', title:'Ložnicové okno je otevřené', detail:presenceUnknown?'Přítomnost domácnosti není potvrzená; okno je zvenku snadno přístupné':'Nikdo není potvrzen doma; okno je zvenku snadno přístupné', entity:c.window_entity, severity:'critical' });\n"
        "    if (sensorUnknown.length) alarmIssues.push({ icon:'⚠️', title:'Část zabezpečení nemá data', detail:`${sensorUnknown.length} ${sensorUnknown.length === 1 ? 'zdroj' : 'zdroje'}`, entity:sensorUnknown[0], severity:'warn' });",
        "security issues",
    )
    sec = replace_one(
        sec,
        "    const items = [\n"
        "      { icon:'🪟', label:'Okno', value:this._unknown(c.window_entity)?'bez dat':windowOpen?'otevřené':'zavřené', active:windowOpen, bad:armed&&windowOpen, entity:c.window_entity },\n"
        "      { icon:'🚪', label:'Dveře', value:this._unknown(c.inside_door_entity)?'bez dat':insideDoorOpen?'otevřené':'zavřené', active:insideDoorOpen, bad:armed&&insideDoorOpen, entity:c.inside_door_entity },\n"
        "      { icon:outsideUnlocked?'🔓':'🔒', label:'Venkovní zámek', value:this._unknown(c.outside_lock_entity)?'bez dat':outsideUnlocked?'odemčený':'zamčený', active:outsideUnlocked, bad:armed&&outsideUnlocked, entity:c.outside_lock_entity },\n"
        "      { icon:'🐔', label:'Drůbež', value:this._unknown(c.poultry_entity)?'bez dat':poultryPresent?'ve voliéře':'nezjištěna', active:poultryPresent, bad:false, entity:c.poultry_entity },\n"
        "    ];",
        "    const items = [\n"
        "      { icon:'🪟', label:'Ložnicové okno', value:this._unknown(c.window_entity)?'bez dat':windowOpen?(someoneHome?'ventilace':'otevřené'):'zavřené', active:windowOpen, bad:windowRisk, entity:c.window_entity },\n"
        "      { icon:'🚪', label:'Vnitřní dveře', value:this._unknown(c.inside_door_entity)?'bez dat':insideDoorOpen?'otevřené':'zavřené', active:insideDoorOpen, bad:false, entity:c.inside_door_entity },\n"
        "      { icon:outsideUnlocked?'🔓':'🔒', label:'Venkovní zámek', value:this._unknown(c.outside_lock_entity)?'bez dat':outsideUnlocked?'odemčený':'zamčený', active:outsideUnlocked, bad:armed&&outsideUnlocked, entity:c.outside_lock_entity },\n"
        "      { icon:'🐔', label:'Voliéra', value:this._unknown(c.poultry_entity)?'bez dat':poultryPresent?'aktivita':'klid', active:poultryPresent, bad:false, entity:c.poultry_entity },\n"
        "    ];",
        "security chips",
    )
    sec = replace_one(
        sec,
        "    const renderKey = JSON.stringify([armed,windowOpen,insideDoorOpen,outsideUnlocked,poultryPresent,sensorUnknown]);",
        "    const renderKey = JSON.stringify([armed,someoneHome,presenceUnknown,windowOpen,insideDoorOpen,outsideUnlocked,poultryPresent,sensorUnknown]);",
        "security render key",
    )
    sec = replace_one(
        sec,
        "    const extras = alarmIssues.length > 1\n"
        "      ? `<div class=\"extra\">+ ${alarmIssues.length-1} ${alarmIssues.length === 2 ? 'další upozornění' : 'další upozornění'}</div>`\n"
        "      : '';",
        "    const extraItems = alarmIssues.slice(1,3);\n"
        "    const extraHidden = Math.max(0, alarmIssues.length - 3);\n"
        "    const extras = extraItems.length\n"
        "      ? `<div class=\"extra\">${extraItems.map(x => this._esc(x.title)).join(' · ')}${extraHidden ? ` · +${extraHidden} další` : ''}</div>`\n"
        "      : '';",
        "security extra issues",
    )

    cli = CLI.read_text(encoding="utf-8")
    cli = replace_one(
        cli,
        "    const forecast = this._forecastSummary();\n"
        "    const heater = this._heaterState();\n"
        "    const issues = [];",
        "    const forecast = this._forecastSummary();\n"
        "    const heater = this._heaterState();\n"
        "    const outdoorAnimalTemps = [outT, forecast.min48].filter(Number.isFinite);\n"
        "    const smallMammalRef = outdoorAnimalTemps.length ? Math.min(...outdoorAnimalTemps) : NaN;\n"
        "    const smallMammalRefLabel = Number.isFinite(forecast.min48) && (!Number.isFinite(outT) || forecast.min48 < outT) ? 'výhled do 48 h' : 'venku nyní';\n"
        "    const issues = [];",
        "climate small mammal reference",
    )
    cli = replace_one(
        cli,
        "    for (const [id, label] of [[c.bedroom_temp,\"ložnice\"],[c.technical_temp,\"technické\"],[c.quail_temp,\"křepelek\"],[c.coop_temp,\"kurníku\"]]) {\n"
        "      if (!this._valid(id)) add(1, \"?\", `Chybí teplota ${label}`, \"Bez živého čidla je lokální riziko jen odhad.\", id);\n"
        "    }\n\n"
        "    if (Number.isFinite(bedT)) {",
        "    for (const [id, label] of [[c.bedroom_temp,\"ložnice\"],[c.technical_temp,\"technické\"],[c.quail_temp,\"křepelek\"],[c.coop_temp,\"kurníku\"]]) {\n"
        "      if (!this._valid(id)) add(1, \"?\", `Chybí teplota ${label}`, \"Bez živého čidla je lokální riziko jen odhad.\", id);\n"
        "    }\n\n"
        "    // Temporary outdoor housing without dedicated local probes: rats and both guinea-pig groups.\n"
        "    // Never present this as measured cage temperature; it is a conservative outdoor/forecast proxy.\n"
        "    if (Number.isFinite(smallMammalRef)) {\n"
        "      const ref = `${smallMammalRef.toFixed(1)} °C · ${smallMammalRefLabel} · bez lokálního čidla v současných klecích.`;\n"
        "      if (smallMammalRef <= 0) add(3, \"🐀\", \"Potkani + morčata: mráz bez zateplení\", `${ref} Přesunout do chráněného tepla.`, c.weather_entity);\n"
        "      else if (smallMammalRef < 15) add(2, \"🐀\", \"Potkani + morčata: příliš chladno\", `${ref} Morčata mají být pod 15 °C přesunuta dovnitř; potkani potřebují stabilní teplé prostředí.`, c.weather_entity);\n"
        "      else if (smallMammalRef < 17) add(1, \"🐀\", \"Potkani + morčata: pod doporučeným rozmezím\", `${ref} Morčata mají ideál 17–20 °C, potkani 19–23 °C.`, c.weather_entity);\n"
        "      else if (smallMammalRef < 19) add(1, \"🐀\", \"Potkani: pod doporučeným rozmezím\", `${ref} Doporučené rozmezí pro potkany je 19–23 °C.`, c.weather_entity);\n"
        "    }\n\n"
        "    if (Number.isFinite(bedT)) {",
        "climate mammal risk block",
    )
    cli = replace_one(
        cli,
        "      if (bedT <= safeMin) add(3, \"🏠\", \"Ložnice pod bezpečným minimem\", `${bedT.toFixed(1)} °C · minimum je ${safeMin.toFixed(0)} °C.`, c.bedroom_temp);\n"
        "      else if (bedT < Math.max(18, safeMin + 2)) add(2, \"🏠\", \"Ložnice je příliš studená\", `${bedT.toFixed(1)} °C · zkontrolovat topení.`, c.bedroom_temp);",
        "      if (bedT <= safeMin) add(3, \"🐈\", \"Ložnice / kočky pod bezpečným minimem\", `${bedT.toFixed(1)} °C · minimum je ${safeMin.toFixed(0)} °C; zkontrolovat kočky a topení.`, c.bedroom_temp);\n"
        "      else if (bedT < Math.max(18, safeMin + 2)) add(2, \"🐈\", \"Ložnice se blíží bezpečnostnímu minimu\", `${bedT.toFixed(1)} °C · minimum je ${safeMin.toFixed(0)} °C; hlídat kočky a topení.`, c.bedroom_temp);",
        "climate cat semantics",
    )
    cli = replace_one(
        cli,
        "    const status = this._status(a.level);\n"
        "    const minText = Number.isFinite(a.forecast.min48) ? `${a.forecast.min48.toFixed(0)} °C` : \"—\";\n"
        "    const issueHtml = a.issues.length ? a.issues.slice(0,4).map(x => `",
        "    const status = this._status(a.level);\n"
        "    const minText = Number.isFinite(a.forecast.min48) ? `${a.forecast.min48.toFixed(0)} °C` : \"—\";\n"
        "    const criticalIssues = a.issues.filter(x => x.level === 3);\n"
        "    const otherIssues = a.issues.filter(x => x.level !== 3);\n"
        "    const visibleIssues = criticalIssues.length >= 3 ? criticalIssues : criticalIssues.concat(otherIssues.slice(0, 3 - criticalIssues.length));\n"
        "    const hiddenIssueCount = Math.max(0, a.issues.length - visibleIssues.length);\n"
        "    const issueHtml = a.issues.length ? visibleIssues.map(x => `",
        "climate priority selection",
    )
    cli = replace_one(
        cli,
        "      </button>`).join(\"\") : `<div class=\"all-good\">✓ Aktuálně bez teplotního nebo vlhkostního problému.</div>`;\n\n"
        "    this.shadowRoot.innerHTML = `",
        "      </button>`).join(\"\") : `<div class=\"all-good\">✓ Aktuálně bez teplotního nebo vlhkostního problému.</div>`;\n"
        "    const moreIssuesHtml = hiddenIssueCount ? `<div class=\"more-issues\">+ ${hiddenIssueCount} další méně důležité</div>` : \"\";\n\n"
        "    this.shadowRoot.innerHTML = `",
        "climate hidden count",
    )
    cli = replace_one(
        cli,
        "        .issues {",
        "        .more-issues { font-size:9px; opacity:.56; padding:3px 4px 0; }\n"
        "        .issues {",
        "climate more issues css",
    )
    cli = replace_one(
        cli,
        "          <div class=\"issues\">${issueHtml}</div>",
        "          <div class=\"issues\">${issueHtml}${moreIssuesHtml}</div>",
        "climate issue rendering",
    )
    cli = replace_one(
        cli,
        "      values: { outT, outH, wind, gust, bedT, bedH, techT, techH, quailT, quailH, coopT, coopH, optimum, safeMin }",
        "      values: { outT, outH, wind, gust, bedT, bedH, techT, techH, quailT, quailH, coopT, coopH, optimum, safeMin, smallMammalRef }",
        "climate render key values",
    )

    res_raw = RES.read_bytes()
    res_sha = hashlib.sha256(res_raw).hexdigest()
    res = json.loads(res_raw)
    items = res.get("data", {}).get("items", [])
    sec_hits = [x for x in items if x.get("url") == OLD_SEC_URL and x.get("type") == "module"]
    cli_hits = [x for x in items if x.get("url") == OLD_CLI_URL and x.get("type") == "module"]
    if len(sec_hits) != 1 or len(cli_hits) != 1:
        raise RuntimeError(f"resource precondition failed sec={len(sec_hits)} cli={len(cli_hits)}")
    sec_hits[0]["url"] = NEW_SEC_URL
    cli_hits[0]["url"] = NEW_CLI_URL

    sec_new = Path(str(SEC) + ".new")
    cli_new = Path(str(CLI) + ".new")
    res_new = Path(str(RES) + ".new")
    sec_new.write_text(sec, encoding="utf-8")
    cli_new.write_text(cli, encoding="utf-8")
    res_new.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    manifest = {
        "old_sec_sha": OLD_SEC_SHA,
        "old_cli_sha": OLD_CLI_SHA,
        "old_res_sha": res_sha,
        "new_sec_sha": sha(sec_new),
        "new_cli_sha": sha(cli_new),
        "new_res_sha": sha(res_new),
        "new_sec_size": sec_new.stat().st_size,
        "new_cli_size": cli_new.stat().st_size,
        "new_res_size": res_new.stat().st_size,
    }
    MANIFEST.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    print("HNIZDO_PATCH_PREPARED")
    print(json.dumps(manifest, sort_keys=True))

def commit():
    if not MANIFEST.exists():
        raise RuntimeError("manifest missing")
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sec_new = Path(str(SEC) + ".new")
    cli_new = Path(str(CLI) + ".new")
    res_new = Path(str(RES) + ".new")
    if sha(SEC) != m["old_sec_sha"] or sha(CLI) != m["old_cli_sha"] or sha(RES) != m["old_res_sha"]:
        raise RuntimeError("live precondition changed after prepare")
    if sha(sec_new) != m["new_sec_sha"] or sha(cli_new) != m["new_cli_sha"] or sha(res_new) != m["new_res_sha"]:
        raise RuntimeError("prepared file hash mismatch")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = []
    for p in (SEC, CLI, RES):
        b = Path(str(p) + f".bak-semantic-{stamp}")
        shutil.copy2(p, b)
        backups.append((p, b))
    try:
        os.replace(sec_new, SEC)
        os.replace(cli_new, CLI)
        os.replace(res_new, RES)
    except Exception:
        for p, b in backups:
            shutil.copy2(b, p)
        raise
    print("HNIZDO_PATCH_COMMITTED")
    print(f"SEC_SHA={sha(SEC)} SEC_SIZE={SEC.stat().st_size}")
    print(f"CLI_SHA={sha(CLI)} CLI_SIZE={CLI.stat().st_size}")
    print(f"RES_SHA={sha(RES)} RES_SIZE={RES.stat().st_size}")
    print("BACKUPS=" + ",".join(str(b) for _, b in backups))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    if mode == "prepare":
        prepare()
    elif mode == "commit":
        commit()
    else:
        raise SystemExit("usage: patch.py [prepare|commit]")
