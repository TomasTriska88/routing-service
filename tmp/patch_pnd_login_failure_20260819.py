#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path

BASE = Path("/home/lina/.local/share/markvarec-pnd")
TEST_DIR = BASE / "tests"

def find_target() -> Path:
    matches = []
    for p in BASE.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if "alertWidget__content" in text and "class pnd(" in text:
            matches.append(p)
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one PND source with stale alert selector, found {len(matches)}: {matches}")
    return matches[0]

HELPER = r'''
def _classify_login_failure(current_url, body_text):
    # Classify a failed MEPAS/PND login without logging credentials or page contents.
    text = " ".join(str(body_text or "").replace("\xa0", " ").split()).casefold()
    url = str(current_url or "").casefold()

    invalid_markers = (
        "authentication attempt has failed",
        "invalid credentials",
        "please verify and try again",
        "neplatné přihlašovací údaje",
        "nesprávné přihlašovací údaje",
        "chybné přihlašovací údaje",
    )
    if any(marker in text for marker in invalid_markers):
        return "invalid_credentials"

    mfa_markers = (
        "ověřovací kód",
        "jednorázový kód",
        "verification code",
        "one-time code",
        "two-factor",
        "multi-factor",
        "mfa",
        "otp",
    )
    if any(marker in text for marker in mfa_markers):
        return "mfa_required"

    if "mepas.cez.cz/cas/login" in url:
        return "login_page_remains"

    return "unexpected_login_state"
'''.strip("\n")

OLD_BLOCK = r'''    try:
        h1_element = wait.until(EC.presence_of_element_located((By.XPATH, f"//h1[contains(text(), '{h1_text}')]")))
    except:
        alert_widget_content = driver.find_element(By.CLASS_NAME, "alertWidget__content").text
        print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + f"{Colors.RED}ERROR: {alert_widget_content}{Colors.RESET}")
        self.set_state(f"sensor.pnd_script_status{self.suffix}", state="Error", attributes={
        "status": "ERROR: Není možné se přihlásit do aplikace",
        "friendly_name": "PND Script Status"
        })
        raise Exception(f"Unable to login to the app")
'''

NEW_BLOCK = r'''    try:
        h1_element = wait.until(EC.presence_of_element_located((By.XPATH, f"//h1[contains(text(), '{h1_text}')]")))
    except Exception as login_wait_ex:
        try:
            visible_body_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            visible_body_text = ""
        login_failure = _classify_login_failure(driver.current_url, visible_body_text)
        print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + f"{Colors.RED}PND_LOGIN_FAILURE={login_failure}{Colors.RESET}")
        self.set_state(f"binary_sensor.pnd_running{self.suffix}", state="off")
        self.set_state(f"sensor.pnd_script_status{self.suffix}", state="Error", attributes={
        "status": f"ERROR: Přihlášení do PND selhalo ({login_failure})",
        "friendly_name": "PND Script Status"
        })
        raise RuntimeError(f"PND login failed: {login_failure}") from login_wait_ex
'''

TEST_SOURCE = r'''#!/usr/bin/env python3
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
matches = []
for p in SOURCE.rglob("*.py"):
    if p == Path(__file__):
        continue
    try:
        t = p.read_text(encoding="utf-8")
    except Exception:
        continue
    if "class pnd(" in t and "_classify_login_failure" in t:
        matches.append(p)
assert len(matches) == 1, matches
target = matches[0]
src = target.read_text(encoding="utf-8")

tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_classify_login_failure")
module = ast.Module(body=[fn], type_ignores=[])
ast.fix_missing_locations(module)
ns = {}
exec(compile(module, str(target), "exec"), ns)
classify = ns["_classify_login_failure"]

assert classify(
    "https://mepas.cez.cz/cas/login?service=x",
    "Authentication attempt has failed, likely due to invalid credentials. Please verify and try again.",
) == "invalid_credentials"
assert classify(
    "https://mepas.cez.cz/cas/login?service=x",
    "Pro pokračování zadejte ověřovací kód.",
) == "mfa_required"
assert classify(
    "https://mepas.cez.cz/cas/login?service=x",
    "Zadejte své uživatelské jméno a heslo",
) == "login_page_remains"
assert classify(
    "https://example.invalid/unexpected",
    "Unexpected page",
) == "unexpected_login_state"

assert "alertWidget__content" not in src
assert 'body.screenshot(self.download_folder+"/00.png")' not in src
assert "PND_LOGIN_FAILURE=" in src
assert 'raise RuntimeError(f"PND login failed: {login_failure}")' in src
print("PND_LOGIN_FAILURE_REGRESSION_OK")
'''

def main() -> None:
    target = find_target()
    src = target.read_text(encoding="utf-8")

    if "_classify_login_failure" in src:
        raise RuntimeError("login failure helper already present; refusing ambiguous repeat patch")
    if src.count(OLD_BLOCK) != 1:
        raise RuntimeError("expected exactly one stale login failure block")
    screenshot_line = '        body.screenshot(self.download_folder+"/00.png")\n'
    if src.count(screenshot_line) != 1:
        raise RuntimeError("expected exactly one credential-stage screenshot")

    anchor = "class pnd(hass.Hass):"
    if src.count(anchor) != 1:
        raise RuntimeError("class anchor mismatch")
    src = src.replace(anchor, HELPER + "\n\n" + anchor, 1)
    src = src.replace(screenshot_line, "", 1)
    src = src.replace(OLD_BLOCK, NEW_BLOCK, 1)

    ast.parse(src)
    if "alertWidget__content" in src:
        raise RuntimeError("stale alert selector still present")
    if "/00.png" in src:
        raise RuntimeError("credential-stage screenshot still present")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target.with_name(target.name + f".bak-login-failure-{stamp}")
    shutil.copy2(target, backup)

    tmp = target.with_name(target.name + f".tmp-login-failure-{os.getpid()}")
    tmp.write_text(src, encoding="utf-8")
    os.replace(tmp, target)

    TEST_DIR.mkdir(parents=True, exist_ok=True)
    test_path = TEST_DIR / "test_login_failure_regression.py"
    test_path.write_text(TEST_SOURCE, encoding="utf-8")
    os.chmod(test_path, 0o755)

    compile(target.read_text(encoding="utf-8"), str(target), "exec")
    compile(test_path.read_text(encoding="utf-8"), str(test_path), "exec")

    print(f"PND_TARGET={target}")
    print(f"PND_BACKUP={backup}")
    print(f"PND_TARGET_SHA256={hashlib.sha256(target.read_bytes()).hexdigest()}")
    print(f"PND_TEST={test_path}")
    print(f"PND_TEST_SHA256={hashlib.sha256(test_path.read_bytes()).hexdigest()}")
    print("PND_LOGIN_FAILURE_PATCH_OK")

if __name__ == "__main__":
    main()
