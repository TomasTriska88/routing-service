from pathlib import Path
import shutil

P = Path("/config/custom_components/chatgpt_bridge/__init__.py")
B = Path("/config/custom_components/chatgpt_bridge/__init__.py.bak-lovelace-resource-20260820")
text = P.read_text(encoding="utf-8")
needle = '            if command == "lovelace_resource_update":\n'
if needle in text:
    print("LOVELACE_DISPATCH_ALREADY_PRESENT")
else:
    anchor = '''            if command == "application_credentials_clone":
'''
    if text.count(anchor) != 1:
        raise SystemExit(f"expected one application_credentials_clone anchor, got {text.count(anchor)}")
    insert = '''            if command == "lovelace_resource_update":
                from .lovelace_ops import async_lovelace_resource_update
                return await asyncio.wait_for(
                    async_lovelace_resource_update(hass, value),
                    timeout=command_timeout,
                )

'''
    if not B.exists():
        shutil.copy2(P, B)
    text = text.replace(anchor, insert + anchor, 1)
    P.write_text(text, encoding="utf-8")
    print("LOVELACE_DISPATCH_PATCHED")

final = P.read_text(encoding="utf-8")
if final.count(needle) != 1:
    raise SystemExit("lovelace_resource_update dispatch count is not exactly one")
print("LOVELACE_DISPATCH_COUNT=1")
