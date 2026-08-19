#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/config/custom_components/markvarec_pnd")
TESTS = Path("/config/tests")
STAMP = "20260819-pnd-reconfigure-r1"
DEFAULT_ELM = "2455005544"

FILES = {
    "const.py": '''DOMAIN = "markvarec_pnd"\nCONF_ELM = "elm"\nDEFAULT_ELM = "2455005544"\n''',
    "config_flow.py": '''from __future__ import annotations\n\nimport voluptuous as vol\n\nfrom homeassistant import config_entries\nfrom homeassistant.const import CONF_PASSWORD, CONF_USERNAME\nfrom homeassistant.helpers.selector import (\n    TextSelector,\n    TextSelectorConfig,\n    TextSelectorType,\n)\n\nfrom .const import CONF_ELM, DEFAULT_ELM, DOMAIN\n\n\ndef _schema(*, username_default: str | None = None, elm_default: str = DEFAULT_ELM):\n    username_key = (\n        vol.Required(CONF_USERNAME, default=username_default)\n        if username_default\n        else vol.Required(CONF_USERNAME)\n    )\n    return vol.Schema(\n        {\n            username_key: TextSelector(\n                TextSelectorConfig(\n                    type=TextSelectorType.EMAIL,\n                    autocomplete="username",\n                )\n            ),\n            # Never prefill the password during reconfiguration.\n            vol.Required(CONF_PASSWORD): TextSelector(\n                TextSelectorConfig(\n                    type=TextSelectorType.PASSWORD,\n                    autocomplete="current-password",\n                )\n            ),\n            vol.Required(CONF_ELM, default=elm_default or DEFAULT_ELM): TextSelector(\n                TextSelectorConfig(type=TextSelectorType.TEXT)\n            ),\n        }\n    )\n\n\ndef _validate(user_input):\n    errors = {}\n    username = str(user_input.get(CONF_USERNAME, "")).strip()\n    password = str(user_input.get(CONF_PASSWORD, ""))\n    elm = str(user_input.get(CONF_ELM, "")).strip()\n\n    if not username:\n        errors[CONF_USERNAME] = "required"\n    if not password:\n        errors[CONF_PASSWORD] = "required"\n    if not elm:\n        errors[CONF_ELM] = "required"\n    elif not elm.isdigit():\n        errors[CONF_ELM] = "invalid_elm"\n\n    return errors, username, password, elm\n\n\nclass MarkvarecPNDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):\n    \"\"\"Configure the Markvarec ČEZ measured-data collector.\"\"\"\n\n    VERSION = 1\n\n    async def async_step_user(self, user_input=None):\n        \"\"\"Collect credentials from the normal Home Assistant UI.\"\"\"\n        errors = {}\n\n        if user_input is not None:\n            errors, username, password, elm = _validate(user_input)\n            if not errors:\n                return self.async_create_entry(\n                    title="Portál naměřených dat",\n                    data={\n                        CONF_USERNAME: username,\n                        CONF_PASSWORD: password,\n                        CONF_ELM: elm,\n                    },\n                )\n\n        return self.async_show_form(\n            step_id="user",\n            data_schema=_schema(),\n            errors=errors,\n        )\n\n    async def async_step_reconfigure(self, user_input=None):\n        \"\"\"Allow credentials and meter number to be corrected from HA UI.\"\"\"\n        errors = {}\n        entry = self._get_reconfigure_entry()\n        username_default = str(entry.data.get(CONF_USERNAME, "")).strip() or None\n        elm_default = str(entry.data.get(CONF_ELM, "")).strip() or DEFAULT_ELM\n\n        if user_input is not None:\n            errors, username, password, elm = _validate(user_input)\n            if not errors:\n                return self.async_update_reload_and_abort(\n                    entry,\n                    data_updates={\n                        CONF_USERNAME: username,\n                        CONF_PASSWORD: password,\n                        CONF_ELM: elm,\n                    },\n                )\n\n        return self.async_show_form(\n            step_id="reconfigure",\n            data_schema=_schema(\n                username_default=username_default,\n                elm_default=elm_default,\n            ),\n            errors=errors,\n        )\n''',
    "translations/cs.json": json.dumps(
        {
            "title": "ČEZ – naměřená data",
            "config": {
                "step": {
                    "user": {
                        "title": "Přihlášení k Portálu naměřených dat",
                        "description": "Přihlašovací údaje zůstanou pouze v lokálním Home Assistantu na Prckovi. Neposílají se přes ChatGPT ani Google Sheets.",
                        "data": {"username": "E-mail", "password": "Heslo", "elm": "Číslo elektroměru"},
                        "data_description": {
                            "username": "E-mail používaný pro přihlášení k ČEZ Distribuci.",
                            "password": "Heslo k účtu ČEZ Distribuce.",
                            "elm": "Číslo fakturačního elektroměru. Pro Markvarec musí být ověřeno před použitím naměřených dat.",
                        },
                    },
                    "reconfigure": {
                        "title": "Překonfigurovat Portál naměřených dat",
                        "description": "ČEZ odmítl aktuálně uložené přihlášení. Zkontroluj e-mail, zadej heslo znovu a ponech správné číslo fakturačního elektroměru. Heslo se z bezpečnostních důvodů nepředvyplňuje.",
                        "data": {"username": "E-mail", "password": "Heslo", "elm": "Číslo elektroměru"},
                        "data_description": {
                            "username": "E-mail používaný pro přihlášení k ČEZ Distribuci.",
                            "password": "Zadej heslo znovu; stávající heslo se nikdy nezobrazuje.",
                            "elm": "Fakturační elektroměr Markvarce: 2455005544.",
                        },
                    },
                },
                "error": {
                    "required": "Toto pole je povinné.",
                    "invalid_elm": "Číslo elektroměru může obsahovat pouze číslice.",
                },
            },
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n",
    "translations/en.json": json.dumps(
        {
            "title": "ČEZ measured data",
            "config": {
                "step": {
                    "user": {
                        "title": "Measured Data Portal sign-in",
                        "description": "Credentials remain only in the local Home Assistant instance on Prcek. They are not sent through ChatGPT or Google Sheets.",
                        "data": {"username": "Email", "password": "Password", "elm": "Meter number"},
                        "data_description": {
                            "username": "Email used to sign in to ČEZ Distribuce.",
                            "password": "Password for the ČEZ Distribuce account.",
                            "elm": "Billing meter number. It must be verified before measured data is used.",
                        },
                    },
                    "reconfigure": {
                        "title": "Reconfigure Measured Data Portal",
                        "description": "ČEZ rejected the currently stored sign-in. Check the email, enter the password again, and keep the correct billing meter number. The password is never prefilled.",
                        "data": {"username": "Email", "password": "Password", "elm": "Meter number"},
                        "data_description": {
                            "username": "Email used to sign in to ČEZ Distribuce.",
                            "password": "Enter the password again; the current password is never displayed.",
                            "elm": "Markvarec billing meter: 2455005544.",
                        },
                    },
                },
                "error": {
                    "required": "This field is required.",
                    "invalid_elm": "The meter number may contain digits only.",
                },
            },
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n",
}

TEST = '''from pathlib import Path\nimport json\n\nROOT = Path("/config/custom_components/markvarec_pnd")\nflow = (ROOT / "config_flow.py").read_text(encoding="utf-8")\nconst = (ROOT / "const.py").read_text(encoding="utf-8")\ncs = json.loads((ROOT / "translations/cs.json").read_text(encoding="utf-8"))\nen = json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8"))\n\nassert 'DEFAULT_ELM = "2455005544"' in const\nassert "async def async_step_reconfigure" in flow\nassert "self._get_reconfigure_entry()" in flow\nassert "self.async_update_reload_and_abort(" in flow\nassert "vol.Required(CONF_ELM" in flow\nassert "vol.Optional(CONF_ELM" not in flow\nassert "entry.data.get(CONF_PASSWORD" not in flow\nassert 'vol.Required(CONF_PASSWORD)' in flow\nassert 'step_id="reconfigure"' in flow\nassert cs["config"]["step"]["reconfigure"]["data_description"]["elm"].endswith("2455005544.")\nassert en["config"]["step"]["reconfigure"]["data_description"]["elm"].endswith("2455005544.")\nprint("MARKVAREC_PND_RECONFIGURE_REGRESSION_OK")\n'''


def main() -> None:
    if not ROOT.is_dir():
        raise SystemExit(f"missing integration: {ROOT}")
    TESTS.mkdir(parents=True, exist_ok=True)

    # Fail closed if live files no longer match the integration family we expect.
    current = (ROOT / "config_flow.py").read_text(encoding="utf-8")
    if "class MarkvarecPNDConfigFlow" not in current or "async_step_user" not in current:
        raise SystemExit("unexpected live config_flow.py")

    backups = []
    try:
        for relative, content in FILES.items():
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                backup = target.with_name(target.name + f".bak-{STAMP}")
                backup.write_bytes(target.read_bytes())
                backups.append((target, backup))
            target.write_text(content, encoding="utf-8")

        test_path = TESTS / "test_markvarec_pnd_config_flow_regression.py"
        test_path.write_text(TEST, encoding="utf-8")
        print("MARKVAREC_PND_RECONFIGURE_PATCH_WRITTEN")
    except Exception:
        for target, backup in reversed(backups):
            if backup.exists():
                target.write_bytes(backup.read_bytes())
        raise


if __name__ == "__main__":
    main()
