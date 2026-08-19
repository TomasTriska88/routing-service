#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import os
import py_compile
import shutil

CONFIG = Path("/config/custom_components/markvarec_pnd/config_flow.py")
TEST = Path("/config/tests/test_markvarec_pnd_reconfigure.py")
EXPECTED_OLD_SHA = "1a1ccab79f35883c8eddacab6e33dfb4e9dec6628a2bf813a9b08bc4efb09fa7"

NEW_CONFIG = '''from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_ELM, DOMAIN

BILLING_METER = "2455005544"


def _schema(*, username: str | None = None) -> vol.Schema:
    username_key = (
        vol.Required(CONF_USERNAME, default=username)
        if username
        else vol.Required(CONF_USERNAME)
    )
    return vol.Schema(
        {
            username_key: TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.EMAIL,
                    autocomplete="username",
                )
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD,
                    autocomplete="current-password",
                )
            ),
            vol.Required(CONF_ELM, default=BILLING_METER): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
        }
    )


def _validated_input(user_input: dict) -> tuple[dict[str, str], dict[str, str]]:
    username = str(user_input.get(CONF_USERNAME, "")).strip()
    password = str(user_input.get(CONF_PASSWORD, ""))
    elm = str(user_input.get(CONF_ELM, "")).strip()

    errors: dict[str, str] = {}
    if not username:
        errors[CONF_USERNAME] = "required"
    if not password:
        errors[CONF_PASSWORD] = "required"
    if not elm.isdigit():
        errors[CONF_ELM] = "invalid_elm"
    elif elm != BILLING_METER:
        errors[CONF_ELM] = "wrong_meter"

    return (
        {
            CONF_USERNAME: username,
            CONF_PASSWORD: password,
            CONF_ELM: elm,
        },
        errors,
    )


class MarkvarecPNDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure the Markvarec ČEZ measured-data collector."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Collect credentials from the normal Home Assistant UI."""
        errors = {}

        if user_input is not None:
            data, errors = _validated_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Portál naměřených dat",
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Update the existing PND credentials from the Home Assistant UI."""
        entry = self._get_reconfigure_entry()
        errors = {}

        if user_input is not None:
            data, errors = _validated_input(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=data,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(
                username=str(entry.data.get(CONF_USERNAME, "")).strip() or None
            ),
            errors=errors,
        )
'''

TEST_SOURCE = '''from pathlib import Path

CONFIG_FLOW = Path("/config/custom_components/markvarec_pnd/config_flow.py")
source = CONFIG_FLOW.read_text(encoding="utf-8")

assert 'BILLING_METER = "2455005544"' in source
assert "async def async_step_reconfigure" in source
assert "self._get_reconfigure_entry()" in source
assert "self.async_update_reload_and_abort(" in source
assert "data_updates=data" in source
assert "vol.Required(CONF_PASSWORD)" in source
assert "default=password" not in source
assert "entry.data.get(CONF_PASSWORD" not in source
assert 'errors[CONF_ELM] = "wrong_meter"' in source
assert "vol.Required(CONF_ELM, default=BILLING_METER)" in source
print("PND_RECONFIGURE_REGRESSION_OK")
'''

old = CONFIG.read_bytes()
old_sha = hashlib.sha256(old).hexdigest()
if old_sha != EXPECTED_OLD_SHA:
    raise SystemExit(f"unexpected config_flow.py sha: {old_sha}")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = CONFIG.with_name(CONFIG.name + f".bak-reconfigure-{stamp}")
shutil.copy2(CONFIG, backup)


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + ".tmp-reconfigure")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


atomic_write(CONFIG, NEW_CONFIG)
TEST.parent.mkdir(parents=True, exist_ok=True)
atomic_write(TEST, TEST_SOURCE)

py_compile.compile(str(CONFIG), doraise=True)
py_compile.compile(str(TEST), doraise=True)

print("PND_RECONFIGURE_PATCHED")
print("BACKUP=" + str(backup))
print("CONFIG_SHA256=" + hashlib.sha256(CONFIG.read_bytes()).hexdigest())
print("TEST_SHA256=" + hashlib.sha256(TEST.read_bytes()).hexdigest())
