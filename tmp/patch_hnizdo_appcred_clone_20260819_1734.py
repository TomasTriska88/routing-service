#!/usr/bin/env python3
"""Deploy a narrow native application-credential clone command into chatgpt_bridge."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

INIT = Path("/config/custom_components/chatgpt_bridge/__init__.py")
MODULE = Path("/config/custom_components/chatgpt_bridge/application_credentials_ops.py")
TEST = Path("/config/tests/test_chatgpt_bridge_application_credentials.py")
EXPECTED_INIT_SHA = "6974bc8631a0eaaf807110f7434532da5f1579bfa5194142236da2bfd7121717"
MODULE_SHA = "3b31a6bc02f979ca807b5fc567bea7a274344c1ebf4bea93fffb16c47599994d"
TEST_SHA = "106fcf7fedb5dd675027c2f83cee9bd91fae350a4703363d2bd3b28529d0c9bd"
BACKUP = Path("/config/custom_components/chatgpt_bridge/__init__.py.bak-appcred-clone-20260819-1734")

MODULE_TEXT = '''"""Narrow application credential operations for the ChatGPT bridge."""

from __future__ import annotations

from typing import Any

from homeassistant.components import application_credentials
from homeassistant.components.application_credentials import async_import_client_credential
from homeassistant.core import HomeAssistant


async def async_clone_application_credential(
    hass: HomeAssistant, value: dict[str, Any]
) -> dict[str, Any]:
    """Clone exactly one application credential using Home Assistant's native API."""
    source_domain = str(value.get("source_domain", "")).strip()
    target_domain = str(value.get("target_domain", "")).strip()

    if not source_domain or not target_domain:
        raise ValueError("source_domain and target_domain are required")
    if source_domain == target_domain:
        raise ValueError("source_domain and target_domain must differ")

    storage = hass.data.get(application_credentials.DATA_COMPONENT)
    if storage is None:
        raise ValueError("application_credentials integration is not setup")

    sources = storage.async_client_credentials(source_domain)
    if len(sources) != 1:
        raise ValueError(
            f"expected exactly one credential for source domain {source_domain}, "
            f"found {len(sources)}"
        )
    credential = next(iter(sources.values()))

    targets_before = storage.async_client_credentials(target_domain)
    if targets_before:
        if len(targets_before) == 1:
            existing = next(iter(targets_before.values()))
            if (
                existing.client_id == credential.client_id
                and existing.client_secret == credential.client_secret
            ):
                return {
                    "ok": True,
                    "result": "application_credential_already_present",
                    "source_domain": source_domain,
                    "target_domain": target_domain,
                    "name": credential.name or "",
                    "target_count": 1,
                }
        raise ValueError(
            f"target domain {target_domain} already has "
            f"{len(targets_before)} credential(s)"
        )

    await async_import_client_credential(
        hass,
        target_domain,
        credential,
        auth_domain=target_domain,
    )

    targets_after = storage.async_client_credentials(target_domain)
    if len(targets_after) != 1:
        raise RuntimeError(
            f"target credential count after import is {len(targets_after)}"
        )
    imported = next(iter(targets_after.values()))
    if (
        imported.client_id != credential.client_id
        or imported.client_secret != credential.client_secret
    ):
        raise RuntimeError("target credential does not match source")

    return {
        "ok": True,
        "result": "application_credential_cloned",
        "source_domain": source_domain,
        "target_domain": target_domain,
        "name": credential.name or "",
        "target_count": 1,
    }
'''

TEST_TEXT = '''#!/usr/bin/env python3
"""Regression checks for the bridge application-credential clone operation."""

from __future__ import annotations

import asyncio
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path("/config")
MODULE_PATH = ROOT / "custom_components/chatgpt_bridge/application_credentials_ops.py"
INIT_PATH = ROOT / "custom_components/chatgpt_bridge/__init__.py"


def load_module():
    spec = importlib.util.spec_from_file_location("chatgpt_bridge_appcred_ops_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load application_credentials_ops module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeStorage:
    def __init__(self, source_items, target_items=None):
        self.by_domain = {
            "google_sheets": dict(source_items),
            "google": dict(target_items or {}),
        }

    def async_client_credentials(self, domain):
        return dict(self.by_domain.get(domain, {}))


def credential(client_id="client-id-secret-test", client_secret="client-secret-test", name="Home Assistant"):
    return SimpleNamespace(
        client_id=client_id,
        client_secret=client_secret,
        name=name,
    )


async def main():
    module = load_module()

    source = credential()
    storage = FakeStorage({"source": source})
    hass = SimpleNamespace(data={module.application_credentials.DATA_COMPONENT: storage})
    calls = []

    async def fake_import(hass_arg, domain, credential_arg, auth_domain=None):
        assert hass_arg is hass
        assert domain == "google"
        assert auth_domain == "google"
        assert credential_arg is source
        calls.append((domain, auth_domain))
        storage.by_domain["google"] = {"imported": credential_arg}

    module.async_import_client_credential = fake_import

    result = await module.async_clone_application_credential(
        hass,
        {"source_domain": "google_sheets", "target_domain": "google"},
    )
    assert result["ok"] is True
    assert result["result"] == "application_credential_cloned"
    assert result["source_domain"] == "google_sheets"
    assert result["target_domain"] == "google"
    assert result["target_count"] == 1
    assert calls == [("google", "google")]
    serialized = json.dumps(result, sort_keys=True)
    assert source.client_id not in serialized
    assert source.client_secret not in serialized

    second = await module.async_clone_application_credential(
        hass,
        {"source_domain": "google_sheets", "target_domain": "google"},
    )
    assert second["result"] == "application_credential_already_present"
    assert calls == [("google", "google")]

    try:
        await module.async_clone_application_credential(
            hass,
            {"source_domain": "google", "target_domain": "google"},
        )
    except ValueError as err:
        assert "must differ" in str(err)
    else:
        raise AssertionError("same source/target must fail")

    conflict = credential(client_id="different", client_secret="different")
    conflict_storage = FakeStorage({"source": source}, {"other": conflict})
    conflict_hass = SimpleNamespace(
        data={module.application_credentials.DATA_COMPONENT: conflict_storage}
    )
    try:
        await module.async_clone_application_credential(
            conflict_hass,
            {"source_domain": "google_sheets", "target_domain": "google"},
        )
    except ValueError as err:
        assert "already has" in str(err)
    else:
        raise AssertionError("target conflict must fail")

    multi_storage = FakeStorage({"a": source, "b": credential(client_id="two")})
    multi_hass = SimpleNamespace(
        data={module.application_credentials.DATA_COMPONENT: multi_storage}
    )
    try:
        await module.async_clone_application_credential(
            multi_hass,
            {"source_domain": "google_sheets", "target_domain": "google"},
        )
    except ValueError as err:
        assert "exactly one" in str(err)
    else:
        raise AssertionError("multiple source credentials must fail")

    module_source = MODULE_PATH.read_text(encoding="utf-8")
    init_source = INIT_PATH.read_text(encoding="utf-8")
    assert ".storage" not in module_source
    tree = ast.parse(module_source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            keys = {
                key.value
                for key in node.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            assert "client_id" not in keys
            assert "client_secret" not in keys
    assert 'if command == "application_credentials_clone":' in init_source
    assert "async_clone_application_credential" in init_source

    print("CHATGPT_BRIDGE_APPLICATION_CREDENTIALS_REGRESSION_OK")


if __name__ == "__main__":
    asyncio.run(main())
'''

ANCHOR = '''            if command == "energy_set_price_entity":
                from .energy_ops import async_energy_set_price_entity
                return await asyncio.wait_for(
                    async_energy_set_price_entity(hass, value),
                    timeout=command_timeout,
                )

            if command == "zha_network":
'''
REPLACEMENT = '''            if command == "energy_set_price_entity":
                from .energy_ops import async_energy_set_price_entity
                return await asyncio.wait_for(
                    async_energy_set_price_entity(hass, value),
                    timeout=command_timeout,
                )

            if command == "application_credentials_clone":
                from .application_credentials_ops import (
                    async_clone_application_credential,
                )
                return await asyncio.wait_for(
                    async_clone_application_credential(hass, value),
                    timeout=command_timeout,
                )

            if command == "zha_network":
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, text: str, mode: int | None = None) -> None:
    tmp = path.with_name(path.name + ".tmp-appcred-clone")
    tmp.write_text(text, encoding="utf-8")
    if mode is not None:
        os.chmod(tmp, mode)
    os.replace(tmp, path)


def rollback() -> None:
    if BACKUP.exists():
        shutil.copy2(BACKUP, INIT)
    MODULE.unlink(missing_ok=True)
    TEST.unlink(missing_ok=True)
    print("CHATGPT_BRIDGE_APPCRED_ROLLBACK_OK")


if sha(INIT) != EXPECTED_INIT_SHA:
    raise SystemExit(f"INIT_SHA_MISMATCH {sha(INIT)} != {EXPECTED_INIT_SHA}")
if MODULE.exists() or TEST.exists():
    raise SystemExit("TARGET_MODULE_OR_TEST_ALREADY_EXISTS")
if BACKUP.exists():
    raise SystemExit(f"BACKUP_ALREADY_EXISTS {BACKUP}")

source = INIT.read_text(encoding="utf-8")
if source.count(ANCHOR) != 1:
    raise SystemExit(f"DISPATCH_ANCHOR_COUNT {source.count(ANCHOR)}")
new_source = source.replace(ANCHOR, REPLACEMENT, 1)

compile(new_source, str(INIT), "exec")
compile(MODULE_TEXT, str(MODULE), "exec")
compile(TEST_TEXT, str(TEST), "exec")

shutil.copy2(INIT, BACKUP)
try:
    atomic_write(MODULE, MODULE_TEXT, 0o644)
    atomic_write(TEST, TEST_TEXT, 0o644)
    atomic_write(INIT, new_source, INIT.stat().st_mode & 0o777)

    if sha(MODULE) != MODULE_SHA:
        raise RuntimeError("module hash mismatch after write")
    if sha(TEST) != TEST_SHA:
        raise RuntimeError("test hash mismatch after write")

    proc = subprocess.run(
        [sys.executable, str(TEST)],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"regression test failed rc={proc.returncode}")

except Exception:
    rollback()
    raise

print(f"INIT_BYTES={len(INIT.read_bytes())}")
print(f"INIT_SHA256={sha(INIT)}")
print(f"MODULE_BYTES={len(MODULE.read_bytes())}")
print(f"MODULE_SHA256={sha(MODULE)}")
print(f"TEST_BYTES={len(TEST.read_bytes())}")
print(f"TEST_SHA256={sha(TEST)}")
print(f"BACKUP={BACKUP}")
print("CHATGPT_BRIDGE_APPCRED_PATCH_OK")
