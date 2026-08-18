#!/bin/sh
set -eu
docker exec -i homeassistant python3 - <<'PY'
from pathlib import Path
import hashlib
import json
import os
import py_compile
import shutil
import time
import yaml

stage = Path("/tmp/markvarec_ezviz_tools_stage")
dest = Path("/config/custom_components/markvarec_ezviz_tools")
config = Path("/config/configuration.yaml")
expected = {
    "__init__.py": "229edc5cf6e7a3e8f46ea74bba8cb617c6421a608c9ff36266ed05bbdd747934",
    "manifest.json": "f9d69c18bd3546ad34db8283087176b604d6b0b7f140550e36afae3eaededeee",
    "services.yaml": "a282c14b44433d744555fdb60ce9a542f9b47cd5c4a7ad264f7c7aea59fa9f3a",
}
for name, wanted in expected.items():
    raw = (stage / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != wanted:
        raise SystemExit(f"stage hash mismatch {name}: {actual}")
py_compile.compile(str(stage / "__init__.py"), doraise=True)
json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
yaml.safe_load((stage / "services.yaml").read_text(encoding="utf-8"))

stamp = time.strftime("%Y%m%d-%H%M%S")
cfg_backup = config.with_name(f"configuration.yaml.bak-ezviz-tools-{stamp}")
dest_backup = dest.with_name(f"{dest.name}.bak-{stamp}")
temp_dest = dest.with_name(f".{dest.name}.new-{stamp}")
shutil.copy2(config, cfg_backup)
if temp_dest.exists():
    shutil.rmtree(temp_dest)
shutil.copytree(stage, temp_dest)
try:
    if dest.exists():
        os.replace(dest, dest_backup)
    os.replace(temp_dest, dest)

    text = config.read_text(encoding="utf-8")
    if not any(line.strip() == "markvarec_ezviz_tools:" for line in text.splitlines()):
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\nmarkvarec_ezviz_tools:\n"
        config.write_text(text, encoding="utf-8")

    py_compile.compile(str(dest / "__init__.py"), doraise=True)
    json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    yaml.safe_load((dest / "services.yaml").read_text(encoding="utf-8"))
except Exception:
    shutil.copy2(cfg_backup, config)
    if dest.exists():
        shutil.rmtree(dest)
    if dest_backup.exists():
        os.replace(dest_backup, dest)
    raise

print("CAMERA_EZVIZ_TOOLS_INSTALLED")
print(f"CONFIG_BACKUP={cfg_backup}")
print(f"DEST_BACKUP={dest_backup if dest_backup.exists() else 'none'}")
for name in expected:
    raw=(dest/name).read_bytes()
    print(f"{name}_SHA256={hashlib.sha256(raw).hexdigest()}")
PY
