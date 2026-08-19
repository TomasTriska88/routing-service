#!/bin/sh
set -eu

STAMP=20260819-1220
BASE="$HOME/.local/share/markvarec-pnd"
BINDIR="$HOME/.local/bin"
TMP=$(mktemp -d /tmp/markvarec-pnd-ha-ui.XXXXXX)
RUN="$BINDIR/markvarec-pnd-run"
RUN_BAK="$RUN.bak-ha-ui-$STAMP"

cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT INT TERM

mkdir -p "$TMP/markvarec_pnd/translations"

cat > "$TMP/markvarec_pnd/manifest.json" <<'EOF'
{
  "domain": "markvarec_pnd",
  "name": "ČEZ – naměřená data",
  "version": "0.1.0",
  "config_flow": true,
  "single_config_entry": true,
  "integration_type": "service",
  "iot_class": "cloud_polling",
  "documentation": "https://github.com/ondrejvysek/HomeAssistant-CEZDistribuce-PND",
  "codeowners": ["@TomasTriska88"],
  "requirements": []
}
EOF

cat > "$TMP/markvarec_pnd/const.py" <<'EOF'
DOMAIN = "markvarec_pnd"
CONF_ELM = "elm"
EOF

cat > "$TMP/markvarec_pnd/__init__.py" <<'EOF'
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Store PND credentials as a normal local Home Assistant config entry."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the local PND credential holder."""
    return True
EOF

cat > "$TMP/markvarec_pnd/config_flow.py" <<'EOF'
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_ELM, DOMAIN


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
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
        vol.Optional(CONF_ELM, default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
    }
)


class MarkvarecPNDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure the Markvarec ČEZ measured-data collector."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Collect credentials from the normal Home Assistant UI."""
        errors = {}

        if user_input is not None:
            username = str(user_input.get(CONF_USERNAME, "")).strip()
            password = str(user_input.get(CONF_PASSWORD, ""))
            elm = str(user_input.get(CONF_ELM, "")).strip()

            if not username:
                errors[CONF_USERNAME] = "required"
            if not password:
                errors[CONF_PASSWORD] = "required"
            if elm and not elm.isdigit():
                errors[CONF_ELM] = "invalid_elm"

            if not errors:
                return self.async_create_entry(
                    title="Portál naměřených dat",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_ELM: elm,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
EOF

cat > "$TMP/markvarec_pnd/translations/cs.json" <<'EOF'
{
  "title": "ČEZ – naměřená data",
  "config": {
    "step": {
      "user": {
        "title": "Přihlášení k Portálu naměřených dat",
        "description": "Přihlašovací údaje zůstanou pouze v lokálním Home Assistantu na Prckovi. Neposílají se přes ChatGPT ani Google Sheets.",
        "data": {
          "username": "E-mail",
          "password": "Heslo",
          "elm": "Číslo elektroměru (volitelné)"
        },
        "data_description": {
          "username": "E-mail používaný pro přihlášení k ČEZ Distribuci.",
          "password": "Heslo k účtu ČEZ Distribuce.",
          "elm": "Nech prázdné, pokud je na účtu jediný elektroměr. Sběrač se jej pokusí vybrat automaticky."
        }
      }
    },
    "error": {
      "required": "Toto pole je povinné.",
      "invalid_elm": "Číslo elektroměru může obsahovat pouze číslice."
    }
  }
}
EOF

cat > "$TMP/markvarec_pnd/translations/en.json" <<'EOF'
{
  "title": "ČEZ measured data",
  "config": {
    "step": {
      "user": {
        "title": "Measured Data Portal sign-in",
        "description": "Credentials remain only in the local Home Assistant instance on Prcek. They are not sent through ChatGPT or Google Sheets.",
        "data": {
          "username": "Email",
          "password": "Password",
          "elm": "Meter number (optional)"
        },
        "data_description": {
          "username": "Email used to sign in to ČEZ Distribuce.",
          "password": "Password for the ČEZ Distribuce account.",
          "elm": "Leave blank when the account has a single meter; the collector will try to select it automatically."
        }
      }
    },
    "error": {
      "required": "This field is required.",
      "invalid_elm": "The meter number may contain digits only."
    }
  }
}
EOF

cat > "$TMP/markvarec-pnd-run" <<'EOF'
#!/bin/sh
set -eu

BASE="$HOME/.local/share/markvarec-pnd"
CFGDIR="$HOME/.config/markvarec-pnd"
CRED="$CFGDIR/credentials.json"
CONFIG="$CFGDIR/config.json"
SYNC=$(mktemp "$BASE/.ha-entry.XXXXXX")

mkdir -p "$BASE/bin" "$CFGDIR"
chmod 700 "$CFGDIR"
umask 077

cleanup() {
    rm -f "$SYNC" "$CRED"
}
trap cleanup EXIT INT TERM

# Read the standard HA ConfigEntry from inside the container without ever
# printing credentials to the systemd journal or bridge.
if docker exec -i homeassistant python3 - >"$SYNC" 2>/dev/null <<'PY'
import json
import sys

domain = "markvarec_pnd"
path = "/config/.storage/core.config_entries"
with open(path, "r", encoding="utf-8") as handle:
    entries = json.load(handle).get("data", {}).get("entries", [])

matches = [entry for entry in entries if entry.get("domain") == domain]
if len(matches) != 1:
    raise SystemExit(42)

data = matches[0].get("data") or {}
payload = {
    "username": data.get("username", ""),
    "password": data.get("password", ""),
    "elm": data.get("elm", ""),
}
sys.stdout.write(json.dumps(payload, ensure_ascii=False))
PY
then
    python3 - "$SYNC" "$CRED" "$CONFIG" <<'PY'
import json
import os
import sys
from pathlib import Path

source = Path(sys.argv[1])
cred_path = Path(sys.argv[2])
config_path = Path(sys.argv[3])
data = json.loads(source.read_text(encoding="utf-8"))

username = str(data.get("username") or "").strip()
password = str(data.get("password") or "")
elm = str(data.get("elm") or "").strip()
if not username or not password:
    raise SystemExit("Home Assistant PND config entry is missing credentials")

cred_path.write_text(
    json.dumps({"username": username, "password": password}, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
os.chmod(cred_path, 0o600)

# Preserve an automatically discovered meter number. Only overwrite it when
# the user explicitly filled the optional meter field in Home Assistant.
if elm:
    config_path.write_text(
        json.dumps({"elm": elm}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.chmod(config_path, 0o600)
PY
else
    rm -f "$CRED"
fi

GECKO=$(find "$HOME/.cache/selenium" -type f -name geckodriver -perm -u+x 2>/dev/null | sort | tail -n 1)
if [ -n "$GECKO" ]; then
    ln -sf "$GECKO" "$BASE/bin/geckodriver"
fi

export MARKVAREC_GECKODRIVER="$BASE/bin/geckodriver"
export PATH="$BASE/bin:$PATH"
export PYTHONPATH="$BASE/shim:$BASE/vendor:$BASE/upstream"

set +e
python3 "$BASE/run_standalone.py"
RC=$?
set -e

if [ -f "$BASE/state.json" ]; then
    docker cp "$BASE/state.json" homeassistant:/config/pnd_state.json >/dev/null 2>&1 || true
fi

exit "$RC"
EOF
chmod 700 "$TMP/markvarec-pnd-run"

python3 -m py_compile \
  "$TMP/markvarec_pnd/__init__.py" \
  "$TMP/markvarec_pnd/config_flow.py" \
  "$TMP/markvarec_pnd/const.py"

cp "$RUN" "$RUN_BAK"
cp "$TMP/markvarec-pnd-run" "$RUN"
chmod 700 "$RUN"

docker exec homeassistant sh -lc '
  set -eu
  rm -rf /config/custom_components/markvarec_pnd
  mkdir -p /config/custom_components/markvarec_pnd
'
docker cp "$TMP/markvarec_pnd/." homeassistant:/config/custom_components/markvarec_pnd/

docker exec homeassistant python3 -m py_compile \
  /config/custom_components/markvarec_pnd/__init__.py \
  /config/custom_components/markvarec_pnd/config_flow.py \
  /config/custom_components/markvarec_pnd/const.py

set +e
CHECK=$(docker exec homeassistant python -m homeassistant --script check_config -c /config 2>&1)
RC=$?
set -e
printf '%s\n' "$CHECK"

if [ "$RC" -ne 0 ] || printf '%s\n' "$CHECK" | grep -Fqi 'could not be validated and has been disabled'; then
  cp "$RUN_BAK" "$RUN"
  docker exec homeassistant rm -rf /config/custom_components/markvarec_pnd
  echo PND_HA_UI_INSTALL_ROLLED_BACK
  exit 82
fi

# Desktop credential entry is deliberately retired: the user configures PND
# from Home Assistant on a phone or regular computer.
rm -f "$BINDIR/markvarec-pnd-setup"
rm -f "$HOME/Plocha/CEZ-namerena-data.desktop" "$HOME/Desktop/CEZ-namerena-data.desktop"

echo PND_HA_UI_INSTALL_OK
echo PND_HA_DOMAIN=markvarec_pnd
echo PND_RUN_WRAPPER_SHA256=$(sha256sum "$RUN" | awk '{print $1}')
