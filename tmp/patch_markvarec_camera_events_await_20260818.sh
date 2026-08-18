#!/bin/sh
set -eu
docker exec -i homeassistant python3 - <<'PY'
from pathlib import Path
import hashlib, os, py_compile, shutil, time
path=Path('/config/custom_components/markvarec_camera_events/__init__.py')
raw=path.read_bytes()
expected='70d07d7b2e15cc86e3ee549029daba2a3ee6af469917a3eebdd8f3d7c1b49a8f'
actual=hashlib.sha256(raw).hexdigest()
if actual != expected:
    raise SystemExit(f'unexpected source sha256: {actual}')
text=raw.decode('utf-8')
old='    hass.data[IMAGE_DATA_COMPONENT].async_add_entities([pending_image])\n'
new='    await hass.data[IMAGE_DATA_COMPONENT].async_add_entities([pending_image])\n'
if text.count(old) != 1:
    raise SystemExit(f'expected exactly one registration line, found {text.count(old)}')
backup=path.with_name(path.name + '.bak-await-' + time.strftime('%Y%m%d-%H%M%S'))
shutil.copy2(path, backup)
tmp=path.with_name(path.name + '.new')
tmp.write_text(text.replace(old,new), encoding='utf-8')
py_compile.compile(str(tmp), doraise=True)
os.replace(tmp,path)
patched=hashlib.sha256(path.read_bytes()).hexdigest()
print('CAMERA_INBOX_IMAGE_AWAIT_PATCHED')
print('BACKUP='+str(backup))
print('SHA256='+patched)
PY
