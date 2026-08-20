#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, sys
from datetime import datetime

ROOT = Path("/config")
STAGE = Path("/tmp/markvarec-attention-r1")
HOME = ROOT / "www/lina-home-card.js"
SCRIPTS = ROOT / "scripts.yaml"
AUTOS = ROOT / "automations.yaml"
TESTS = ROOT / "tests"

JS_METHODS = '\n  _attentionMeta(card) {\n    return {\n      lina: { tag: "lina-home-card", label: "Lina" },\n      weather: { tag: "lina-weather-card", label: "Počasí" },\n      security: { tag: "lina-security-card", label: "Bezpečnost" },\n      climate: { tag: "lina-climate-safety-card", label: "Klima" },\n      energy: { tag: "lina-energy-card", label: "Energie" },\n      water: { tag: "lina-rainwater-card", label: "Voda" },\n    }[card] || null;\n  }\n\n  _ensureAttentionSubscription() {\n    if (!this.isConnected || !this._hass?.connection || this._attentionUnsubscribe || this._attentionSubscribePending) return;\n    const pending = this._hass.connection.subscribeEvents(\n      event => this._handleAttentionEvent(event),\n      "markvarec_attention"\n    );\n    this._attentionSubscribePending = Promise.resolve(pending)\n      .then(unsub => {\n        this._attentionSubscribePending = null;\n        if (!this.isConnected) {\n          try { if (typeof unsub === "function") unsub(); } catch (_) {}\n          return;\n        }\n        this._attentionUnsubscribe = typeof unsub === "function" ? unsub : null;\n      })\n      .catch(() => { this._attentionSubscribePending = null; });\n  }\n\n  _teardownAttention() {\n    try { if (typeof this._attentionUnsubscribe === "function") this._attentionUnsubscribe(); } catch (_) {}\n    this._attentionUnsubscribe = null;\n    for (const entry of this._attentionTimers.values()) {\n      window.clearTimeout(entry.timer);\n      try { entry.restore(); } catch (_) {}\n    }\n    this._attentionTimers.clear();\n    if (this._attentionToastTimer) window.clearTimeout(this._attentionToastTimer);\n    this._attentionToastTimer = null;\n    this._attentionToast?.remove?.();\n    this._attentionToast = null;\n  }\n\n  _findAttentionTargets(selector) {\n    const out = [];\n    const seenRoots = new Set();\n    const walk = root => {\n      if (!root || seenRoots.has(root) || typeof root.querySelectorAll !== "function") return;\n      seenRoots.add(root);\n      root.querySelectorAll(selector).forEach(el => out.push(el));\n      root.querySelectorAll("*").forEach(el => {\n        if (el.shadowRoot) walk(el.shadowRoot);\n      });\n    };\n    walk(document);\n    return [...new Set(out)];\n  }\n\n  _handleAttentionEvent(event) {\n    const data = event?.data || {};\n    const card = String(data.card || "").toLowerCase();\n    const meta = this._attentionMeta(card);\n    if (!meta) return;\n\n    const allowed = new Set(["critical", "action", "watch", "info", "recovery"]);\n    const requested = String(data.level || "info").toLowerCase();\n    const level = allowed.has(requested) ? requested : "info";\n    const rawTtl = Number(data.ttl_ms);\n    const ttl = Math.min(60000, Math.max(2000, Number.isFinite(rawTtl) ? rawTtl : 6000));\n    const title = String(data.title || `${meta.label} · změna`).slice(0, 100);\n    const message = String(data.message || title).slice(0, 260);\n    const key = String(data.key || `${card}:${level}:${title}:${message}`).slice(0, 300);\n    const now = Date.now();\n    const last = this._attentionLastEvents.get(key) || 0;\n    if (now - last < 1200) return;\n    this._attentionLastEvents.set(key, now);\n    if (this._attentionLastEvents.size > 80) {\n      for (const [oldKey, stamp] of this._attentionLastEvents) {\n        if (now - stamp > 120000) this._attentionLastEvents.delete(oldKey);\n      }\n    }\n\n    this._highlightAttention(card, meta, level, ttl);\n    this._showAttentionToast(meta.label, title, message, level, ttl);\n  }\n\n  _highlightAttention(card, meta, level, ttl) {\n    const old = this._attentionTimers.get(card);\n    if (old) {\n      window.clearTimeout(old.timer);\n      try { old.restore(); } catch (_) {}\n      this._attentionTimers.delete(card);\n    }\n\n    const targets = this._findAttentionTargets(meta.tag);\n    if (!targets.length) return;\n    const palette = {\n      critical: { color: "rgba(244,67,54,.98)", shadow: "rgba(244,67,54,.88)", scale: 1.032 },\n      action: { color: "rgba(255,152,0,.98)", shadow: "rgba(255,152,0,.78)", scale: 1.026 },\n      watch: { color: "rgba(255,193,7,.98)", shadow: "rgba(255,193,7,.70)", scale: 1.022 },\n      info: { color: "rgba(66,165,245,.96)", shadow: "rgba(66,165,245,.62)", scale: 1.018 },\n      recovery: { color: "rgba(76,175,80,.96)", shadow: "rgba(76,175,80,.60)", scale: 1.018 },\n    }[level];\n    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;\n    const token = `${Date.now()}-${Math.random().toString(36).slice(2)}`;\n    const previous = targets.map(el => ({\n      el,\n      transform: el.style.transform,\n      filter: el.style.filter,\n      transition: el.style.transition,\n      outline: el.style.outline,\n      outlineOffset: el.style.outlineOffset,\n      borderRadius: el.style.borderRadius,\n      zIndex: el.style.zIndex,\n      position: el.style.position,\n      willChange: el.style.willChange,\n    }));\n\n    targets.forEach(el => {\n      el.dataset.markvarecAttention = level;\n      el.dataset.markvarecAttentionToken = token;\n      el.style.transition = reduced ? "none" : "transform .18s ease, filter .18s ease, outline-color .18s ease";\n      if (!reduced) el.style.transform = `scale(${palette.scale})`;\n      el.style.filter = `brightness(1.06) drop-shadow(0 0 18px ${palette.shadow})`;\n      el.style.outline = `3px solid ${palette.color}`;\n      el.style.outlineOffset = "-3px";\n      el.style.borderRadius = "16px";\n      el.style.zIndex = "50";\n      if (!el.style.position) el.style.position = "relative";\n      el.style.willChange = reduced ? "filter" : "transform, filter";\n    });\n\n    const restore = () => {\n      previous.forEach(p => {\n        if (p.el.dataset.markvarecAttentionToken !== token) return;\n        delete p.el.dataset.markvarecAttention;\n        delete p.el.dataset.markvarecAttentionToken;\n        p.el.style.transform = p.transform;\n        p.el.style.filter = p.filter;\n        p.el.style.transition = p.transition;\n        p.el.style.outline = p.outline;\n        p.el.style.outlineOffset = p.outlineOffset;\n        p.el.style.borderRadius = p.borderRadius;\n        p.el.style.zIndex = p.zIndex;\n        p.el.style.position = p.position;\n        p.el.style.willChange = p.willChange;\n      });\n    };\n    const timer = window.setTimeout(() => {\n      restore();\n      const current = this._attentionTimers.get(card);\n      if (current?.token === token) this._attentionTimers.delete(card);\n    }, ttl);\n    this._attentionTimers.set(card, { timer, restore, token });\n  }\n\n  _showAttentionToast(label, title, message, level, ttl) {\n    const colors = {\n      critical: "#ef5350",\n      action: "#ffa726",\n      watch: "#fdd835",\n      info: "#42a5f5",\n      recovery: "#66bb6a",\n    };\n    if (!this._attentionToast) {\n      const toast = document.createElement("div");\n      toast.id = "markvarec-attention-toast";\n      toast.setAttribute("role", "status");\n      toast.setAttribute("aria-live", "polite");\n      Object.assign(toast.style, {\n        position: "fixed",\n        top: "18px",\n        left: "50%",\n        transform: "translateX(-50%)",\n        zIndex: "10000",\n        maxWidth: "min(760px, calc(100vw - 36px))",\n        boxSizing: "border-box",\n        padding: "11px 15px",\n        borderRadius: "14px",\n        background: "rgba(20,24,30,.94)",\n        color: "#fff",\n        boxShadow: "0 10px 34px rgba(0,0,0,.34)",\n        backdropFilter: "blur(10px)",\n        pointerEvents: "none",\n        display: "grid",\n        gap: "2px",\n        fontFamily: "var(--paper-font-body1_-_font-family, sans-serif)",\n      });\n      document.body.appendChild(toast);\n      this._attentionToast = toast;\n    }\n    const toast = this._attentionToast;\n    toast.replaceChildren();\n    toast.style.border = `2px solid ${colors[level] || colors.info}`;\n    const head = document.createElement("strong");\n    head.textContent = title || `${label} · změna`;\n    head.style.fontSize = "16px";\n    head.style.lineHeight = "1.2";\n    const body = document.createElement("span");\n    body.textContent = message || title || label;\n    body.style.fontSize = "14px";\n    body.style.lineHeight = "1.3";\n    body.style.opacity = ".92";\n    toast.append(head, body);\n    toast.hidden = false;\n\n    if (this._attentionToastTimer) window.clearTimeout(this._attentionToastTimer);\n    this._attentionToastTimer = window.setTimeout(() => {\n      if (this._attentionToast) this._attentionToast.hidden = true;\n      this._attentionToastTimer = null;\n    }, ttl);\n  }\n'
SCRIPT_BLOCK = 'lina_pozornost:\n  alias: "Lina - zvýraznit pozornost v Hnízdě"\n  description: "Jednotný vizuální attention event bus pro šest chytrých karet Hnízda. Sám nikdy nemluví; hlas se rozhoduje odděleně přes dual-output gate."\n  mode: parallel\n  max: 20\n  fields:\n    card:\n      description: "Cílová karta: lina, weather, security, climate, energy nebo water."\n      example: "security"\n    level:\n      description: "Přechodná vizuální úroveň: critical, action, watch, info nebo recovery."\n      example: "action"\n    title:\n      description: "Krátký nadpis změny."\n      example: "Venkovní zámek odemčený"\n    message:\n      description: "Samostatně srozumitelný stručný kontext změny."\n      example: "Při aktivním zabezpečení se právě odemkl venkovní zámek."\n    key:\n      description: "Stabilní deduplikační klíč stejného typu události."\n      example: "security-lock-unlocked"\n    ttl_ms:\n      description: "Doba vizuálního zvýraznění v milisekundách; frontend ji bezpečně omezí na 2–60 s."\n      example: 10000\n  sequence:\n    - variables:\n        card_key: >-\n          {{ card | default(\'lina\', true) | string | lower }}\n        level_key: >-\n          {% set raw = level | default(\'info\', true) | string | lower %}\n          {{ raw if raw in [\'critical\',\'action\',\'watch\',\'info\',\'recovery\'] else \'info\' }}\n        ttl_value: >-\n          {% set raw = ttl_ms | default(6000, true) | int(6000) %}\n          {{ [60000, [2000, raw] | max] | min }}\n    - condition: template\n      value_template: >-\n        {{ card_key in [\'lina\',\'weather\',\'security\',\'climate\',\'energy\',\'water\'] }}\n    - event: markvarec_attention\n      event_data:\n        card: "{{ card_key }}"\n        level: "{{ level_key }}"\n        title: "{{ title | default(\'\', true) | string }}"\n        message: "{{ message | default(\'\', true) | string }}"\n        key: "{{ key | default(\'\', true) | string }}"\n        ttl_ms: "{{ ttl_value }}"\n'
AUTOMATION_BLOCK = '- id: \'markvarec_hnizdo_attention_security\'\n  alias: "Markvarec - Hnízdo - zvýraznění změn zabezpečení"\n  description: "Okamžitá vizuální vrstva pozornosti pro skutečné změny zabezpečení a venkovního zámku. Nemění security reakce ani hlas; stávající 2min hlas zámku zůstává samostatná deduplikovaná cesta."\n  mode: queued\n  max: 10\n  triggers:\n    - trigger: state\n      entity_id: binary_sensor.tz3000_a33rw7ou_ts0203_3\n      from: "off"\n      to: "on"\n      id: lock_unlocked\n    - trigger: state\n      entity_id: binary_sensor.tz3000_a33rw7ou_ts0203_3\n      from: "on"\n      to: "off"\n      id: lock_locked\n    - trigger: state\n      entity_id: binary_sensor.zabezpeceni_zahrady_aktivni\n      from: "off"\n      to: "on"\n      id: security_armed\n    - trigger: state\n      entity_id: binary_sensor.zabezpeceni_zahrady_aktivni\n      from: "on"\n      to: "off"\n      id: security_disarmed\n  actions:\n    - choose:\n        - conditions:\n            - condition: trigger\n              id: lock_unlocked\n            - condition: state\n              entity_id: binary_sensor.zabezpeceni_zahrady_aktivni\n              state: "on"\n          sequence:\n            - action: script.lina_pozornost\n              data:\n                card: security\n                level: action\n                title: "Venkovní zámek odemčený"\n                message: "Při aktivním zabezpečení se právě odemkl venkovní zámek."\n                key: security-lock-unlocked\n                ttl_ms: 10000\n        - conditions:\n            - condition: trigger\n              id: lock_locked\n            - condition: state\n              entity_id: binary_sensor.zabezpeceni_zahrady_aktivni\n              state: "on"\n          sequence:\n            - action: script.lina_pozornost\n              data:\n                card: security\n                level: recovery\n                title: "Venkovní zámek zajištěn"\n                message: "Venkovní zámek je při aktivním zabezpečení znovu zajištěný."\n                key: security-lock-locked\n                ttl_ms: 5000\n        - conditions:\n            - condition: trigger\n              id: security_armed\n          sequence:\n            - choose:\n                - conditions:\n                    - condition: state\n                      entity_id: binary_sensor.tz3000_a33rw7ou_ts0203_3\n                      state: "on"\n                  sequence:\n                    - action: script.lina_pozornost\n                      data:\n                        card: security\n                        level: action\n                        title: "Zabezpečení aktivní, zámek odemčený"\n                        message: "Markvarec je zastřežený, ale venkovní zámek je odemčený."\n                        key: security-armed-lock-unlocked\n                        ttl_ms: 10000\n              default:\n                - action: script.lina_pozornost\n                  data:\n                    card: security\n                    level: info\n                    title: "Markvarec zastřežen"\n                    message: "Venkovní zabezpečení se právě aktivovalo."\n                    key: security-armed\n                    ttl_ms: 6000\n        - conditions:\n            - condition: trigger\n              id: security_disarmed\n          sequence:\n            - action: script.lina_pozornost\n              data:\n                card: security\n                level: recovery\n                title: "Markvarec odstřežen"\n                message: "Venkovní zabezpečení se právě deaktivovalo."\n                key: security-disarmed\n                ttl_ms: 5000\n'
JS_TEST = 'const fs = require("fs");\nconst file = process.argv[2];\nif (!file) throw new Error("usage: node test_lina_attention_regression.js <lina-home-card.js>");\nconst s = fs.readFileSync(file, "utf8");\nconst must = [\n  "markvarec_attention",\n  "subscribeEvents(",\n  "_handleAttentionEvent(event)",\n  "_highlightAttention(card, meta, level, ttl)",\n  "_showAttentionToast(label, title, message, level, ttl)",\n  "prefers-reduced-motion: reduce",\n  "lina-home-card",\n  "lina-weather-card",\n  "lina-security-card",\n  "lina-climate-safety-card",\n  "lina-energy-card",\n  "lina-rainwater-card",\n  "markvarecAttention",\n  "Math.min(60000, Math.max(2000",\n  "replaceChildren()",\n  "textContent =",\n];\nfor (const token of must) {\n  if (!s.includes(token)) throw new Error(`missing attention contract: ${token}`);\n}\nconst a = s.indexOf("_attentionMeta(card)");\nconst b = s.indexOf("getCardSize()", a);\nif (a < 0 || b < 0) throw new Error("attention method section not found");\nconst section = s.slice(a, b);\nif (section.includes(".innerHTML")) throw new Error("attention layer must not inject untrusted HTML");\nif (section.includes(".style.width") || section.includes(".style.height")) {\n  throw new Error("attention layer must not resize the stable 3x2 grid");\n}\nif (!section.includes("el.style.transform = `scale(")) throw new Error("optical lift missing");\nif (!section.includes("el.style.outline =")) throw new Error("attention outline missing");\nif (!section.includes("drop-shadow")) throw new Error("attention halo missing");\nconsole.log("LINA_ATTENTION_FRONTEND_REGRESSION_OK");\n'
HA_TEST = 'from pathlib import Path\nscripts = Path("/config/scripts.yaml").read_text(encoding="utf-8")\nautos = Path("/config/automations.yaml").read_text(encoding="utf-8")\n\nassert "\\nlina_pozornost:\\n" in "\\n" + scripts\ns0 = scripts.index("lina_pozornost:")\nsblock = scripts[s0:]\nassert "event: markvarec_attention" in sblock\nfor card in ("lina","weather","security","climate","energy","water"):\n    assert card in sblock\nassert "script.lina_mluv" not in sblock\n\nmarker = "- id: \'markvarec_hnizdo_attention_security\'"\nassert marker in autos\na0 = autos.index(marker)\na1 = autos.find("\\n- id:", a0 + len(marker))\nablock = autos[a0:] if a1 < 0 else autos[a0:a1]\nfor trigger_id in ("lock_unlocked","lock_locked","security_armed","security_disarmed"):\n    assert f"id: {trigger_id}" in ablock\nassert "from: \\"off\\"\\n      to: \\"on\\"" in ablock\nassert "from: \\"on\\"\\n      to: \\"off\\"" in ablock\nassert "action: script.lina_pozornost" in ablock\nassert "for:" not in ablock\nassert "card: security" in ablock\nassert "security-lock-unlocked" in ablock\n\nvoice_marker = "- id: \'markvarec_lina_venkovni_dvere_hlas\'"\nassert voice_marker in autos\nv0 = autos.index(voice_marker)\nv1 = autos.find("\\n- id:", v0 + len(voice_marker))\nvblock = autos[v0:] if v1 < 0 else autos[v0:v1]\nassert \'to: "on"\' in vblock\nassert \'for: "00:02:00"\' in vblock\nassert "action: script.lina_mluv" in vblock\n\nprint("LINA_ATTENTION_HA_REGRESSION_OK")\n'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, content):
    Path(path).write_text(content, encoding="utf-8")

def stage():
    STAGE.mkdir(parents=True, exist_ok=True)
    home = HOME.read_text(encoding="utf-8")
    scripts = SCRIPTS.read_text(encoding="utf-8")
    autos = AUTOS.read_text(encoding="utf-8")
    if "markvarec_attention" in home or "lina_pozornost:" in scripts or "markvarec_hnizdo_attention_security" in autos:
        raise RuntimeError("attention system already present; refuse duplicate stage")

    source = {"home": sha(HOME), "scripts": sha(SCRIPTS), "autos": sha(AUTOS)}

    constructor_anchor = '    this._calendarRefreshPending = false;\n  }'
    constructor_add = '    this._calendarRefreshPending = false;\n    this._attentionUnsubscribe = null;\n    this._attentionSubscribePending = null;\n    this._attentionTimers = new Map();\n    this._attentionLastEvents = new Map();\n    this._attentionToastTimer = null;\n    this._attentionToast = null;\n  }'
    if home.count(constructor_anchor) != 1:
        raise RuntimeError("constructor anchor mismatch")
    home = home.replace(constructor_anchor, constructor_add, 1)

    connected_anchor = '  connectedCallback() {\n    if (!this._agendaTimer) {'
    connected_add = '  connectedCallback() {\n    this._ensureAttentionSubscription();\n    if (!this._agendaTimer) {'
    if home.count(connected_anchor) != 1:
        raise RuntimeError("connectedCallback anchor mismatch")
    home = home.replace(connected_anchor, connected_add, 1)

    disconnected_anchor = '    this._agendaTimer = null;\n  }\n\n  set hass(hass) {\n    this._hass = hass;'
    disconnected_add = '    this._agendaTimer = null;\n    this._teardownAttention();\n  }\n\n  set hass(hass) {\n    this._hass = hass;\n    this._ensureAttentionSubscription();'
    if home.count(disconnected_anchor) != 1:
        raise RuntimeError("disconnected/hass anchor mismatch")
    home = home.replace(disconnected_anchor, disconnected_add, 1)

    methods_anchor = '  getCardSize() { return 5; }'
    if home.count(methods_anchor) != 1:
        raise RuntimeError("method insertion anchor mismatch")
    home = home.replace(methods_anchor, JS_METHODS + "\n" + methods_anchor, 1)

    if not scripts.endswith("\n"):
        scripts += "\n"
    scripts += "\n" + SCRIPT_BLOCK
    if not autos.endswith("\n"):
        autos += "\n"
    autos += "\n" + AUTOMATION_BLOCK

    write(STAGE / "lina-home-card.js", home)
    write(STAGE / "scripts.yaml", scripts)
    write(STAGE / "automations.yaml", autos)
    write(STAGE / "test_lina_attention_regression.js", JS_TEST)
    write(STAGE / "test_lina_attention_ha_regression.py", HA_TEST)
    write(STAGE / "meta.json", json.dumps(source, sort_keys=True))
    print("ATTENTION_STAGE_OK")
    print("SOURCE_HOME_SHA=" + source["home"])
    print("STAGED_HOME_SHA=" + sha(STAGE / "lina-home-card.js"))
    print("SOURCE_SCRIPTS_SHA=" + source["scripts"])
    print("SOURCE_AUTOS_SHA=" + source["autos"])

def deploy():
    meta = json.loads((STAGE / "meta.json").read_text(encoding="utf-8"))
    current = {"home": sha(HOME), "scripts": sha(SCRIPTS), "autos": sha(AUTOS)}
    if current != meta:
        raise RuntimeError("live source changed after staging; re-stage required: " + json.dumps(current, sort_keys=True))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = {
        "home": str(HOME) + ".bak-attention-" + stamp,
        "scripts": str(SCRIPTS) + ".bak-attention-" + stamp,
        "autos": str(AUTOS) + ".bak-attention-" + stamp,
    }
    shutil.copy2(HOME, backups["home"])
    shutil.copy2(SCRIPTS, backups["scripts"])
    shutil.copy2(AUTOS, backups["autos"])
    shutil.copy2(STAGE / "lina-home-card.js", HOME)
    shutil.copy2(STAGE / "scripts.yaml", SCRIPTS)
    shutil.copy2(STAGE / "automations.yaml", AUTOS)
    TESTS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STAGE / "test_lina_attention_regression.js", TESTS / "test_lina_attention_regression.js")
    shutil.copy2(STAGE / "test_lina_attention_ha_regression.py", TESTS / "test_lina_attention_ha_regression.py")
    write(STAGE / "deploy.json", json.dumps(backups, sort_keys=True))
    print("ATTENTION_DEPLOY_FILES_OK")
    print("HOME_SHA=" + sha(HOME))
    print("BACKUP_HOME=" + backups["home"])
    print("BACKUP_SCRIPTS=" + backups["scripts"])
    print("BACKUP_AUTOS=" + backups["autos"])

def rollback():
    deploy_file = STAGE / "deploy.json"
    if not deploy_file.exists():
        raise RuntimeError("no deployment metadata")
    backups = json.loads(deploy_file.read_text(encoding="utf-8"))
    shutil.copy2(backups["home"], HOME)
    shutil.copy2(backups["scripts"], SCRIPTS)
    shutil.copy2(backups["autos"], AUTOS)
    for p in (TESTS / "test_lina_attention_regression.js", TESTS / "test_lina_attention_ha_regression.py"):
        if p.exists():
            p.unlink()
    print("ATTENTION_ROLLBACK_OK")
    print("HOME_SHA=" + sha(HOME))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "stage":
        stage()
    elif mode == "deploy":
        deploy()
    elif mode == "rollback":
        rollback()
    else:
        raise SystemExit("usage: deploy_attention.py stage|deploy|rollback")
