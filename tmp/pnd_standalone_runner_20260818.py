#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path.home() / ".local" / "share" / "markvarec-pnd"
CONFIG_DIR = Path.home() / ".config" / "markvarec-pnd"
CREDENTIALS = CONFIG_DIR / "credentials.json"
CONFIG = CONFIG_DIR / "config.json"
STATE = BASE / "state.json"
DATA = BASE / "data"
UPSTREAM_COMMIT = "4d73ffa0d9dff5a6868af6b07cd69d79a7b57460"
SOURCE = "ČEZ Distribuce – Portál naměřených dat"
TZ = ZoneInfo("Europe/Prague")


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _state_value(states: dict, entity_id: str):
    item = states.get(entity_id) or {}
    return item.get("state")


def _state_attrs(states: dict, entity_id: str) -> dict:
    item = states.get(entity_id) or {}
    attrs = item.get("attributes") or {}
    return attrs if isinstance(attrs, dict) else {}


def _as_float(value):
    if value is None:
        return None
    try:
        return round(float(str(value).replace(",", ".")), 6)
    except (TypeError, ValueError):
        return None


def _month_interval(now: datetime) -> str:
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if end <= start:
        end = now
    return f"{start:%d.%m.%Y %H:%M} - {end:%d.%m.%Y %H:%M}"


def _base_state(status: str) -> dict:
    old = _read_json(STATE, {})
    payload = {
        "status": status,
        "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source": SOURCE,
        "upstream_commit": UPSTREAM_COMMIT,
        "collector_version": 1,
    }
    for key in (
        "elm",
        "yesterday_kwh",
        "yesterday_date",
        "month_kwh",
        "month_start",
        "interval_end",
        "portal_version",
    ):
        if key in old:
            payload[key] = old[key]
    return payload


def main() -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    creds = _read_json(CREDENTIALS, {})
    config = _read_json(CONFIG, {})
    username = str(creds.get("username") or "").strip()
    password = str(creds.get("password") or "")
    if not username or not password:
        payload = _base_state("not_configured")
        payload["message"] = "Přihlašovací údaje zatím nejsou lokálně nastavené."
        _write_json(STATE, payload)
        return 0

    now = datetime.now(TZ)
    elm = str(config.get("elm") or "").strip()
    interval = _month_interval(now)

    try:
        import pnd as upstream

        app = upstream.pnd()
        app.args = {
            "PNDUserName": username,
            "PNDUserPassword": password,
            "DownloadFolder": str(DATA),
            "DataInterval": interval,
            "ELM": elm,
        }
        app.initialize()
        app.run_pnd("run_pnd", {}, {})
        states = app._states

        resolved_elm = str(getattr(app, "ELM", "") or "").strip()
        if resolved_elm and resolved_elm != elm:
            config["elm"] = resolved_elm
            _write_json(CONFIG, config)

        yesterday_entity = "sensor.pnd_consumption"
        month_entity = "sensor.pnd_total_interval_consumption"
        version_entity = "sensor.pnd_app_version"
        yesterday = _as_float(_state_value(states, yesterday_entity))
        month = _as_float(_state_value(states, month_entity))
        yesterday_date = _state_attrs(states, yesterday_entity).get("date")
        portal_version = _state_value(states, version_entity)

        if yesterday is None and month is None:
            raise RuntimeError("Portál doběhl bez použitelných údajů o spotřebě.")

        payload = _base_state("ok")
        payload.update(
            {
                "elm": resolved_elm or elm or None,
                "yesterday_kwh": yesterday,
                "yesterday_date": yesterday_date,
                "month_kwh": month,
                "month_start": now.replace(day=1).date().isoformat(),
                "interval_end": now.date().isoformat(),
                "portal_version": str(portal_version) if portal_version is not None else None,
                "message": "Naměřená data byla úspěšně načtena.",
            }
        )
        _write_json(STATE, payload)
        return 0
    except Exception as exc:
        payload = _base_state("error")
        text = f"{type(exc).__name__}: {exc}".replace(username, "<redacted>")
        payload["error"] = text[:500]
        payload["message"] = "Načtení naměřených dat selhalo."
        _write_json(STATE, payload)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
