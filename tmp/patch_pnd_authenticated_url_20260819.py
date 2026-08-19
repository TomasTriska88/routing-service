#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import shutil

BASE = Path("/home/lina/.local/share/markvarec-pnd")
SRC = BASE / "upstream" / "pnd.py"
TEST = BASE / "tests" / "test_login_failure_regression.py"

src = SRC.read_text(encoding="utf-8")
test = TEST.read_text(encoding="utf-8")

helper_anchor = '''    return "unexpected_login_state"

class pnd(hass.Hass):
'''
helper_replacement = '''    return "unexpected_login_state"

def _is_authenticated_pnd_url(current_url):
    """Return True only for an authenticated external PND page."""
    url = str(current_url or "").strip().casefold()
    return url.startswith("https://pnd.cezdistribuce.cz/cezpnd2/external/")

class pnd(hass.Hass):
'''
if helper_anchor not in src:
    raise SystemExit("helper anchor not found")
src = src.replace(helper_anchor, helper_replacement, 1)

old_wait = '''        h1_element = wait.until(EC.presence_of_element_located((By.XPATH, f"//h1[contains(text(), '{h1_text}')]")))
'''
new_wait = '''        wait.until(lambda d: _is_authenticated_pnd_url(d.current_url) or bool(d.find_elements(By.XPATH, f"//h1[contains(text(), '{h1_text}')]")))
        authenticated_url = _is_authenticated_pnd_url(driver.current_url)
        h1_matches = driver.find_elements(By.XPATH, f"//h1[contains(text(), '{h1_text}')]" )
        h1_element = h1_matches[0] if h1_matches else None
'''
if old_wait not in src:
    raise SystemExit("login wait anchor not found")
src = src.replace(old_wait, new_wait, 1)

old_success = '''    if h1_element:
        print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + f"H1 tag with text '{h1_text}' is present.")
'''
new_success = '''    if authenticated_url:
        print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": Authenticated PND URL detected.")
    elif h1_element:
        print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + f"H1 tag with text '{h1_text}' is present.")
'''
if old_success not in src:
    raise SystemExit("login success anchor not found")
src = src.replace(old_success, new_success, 1)

old_test_extract = '''fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_classify_login_failure")
module = ast.Module(body=[fn], type_ignores=[])
ast.fix_missing_locations(module)
ns = {}
exec(compile(module, str(target), "exec"), ns)
classify = ns["_classify_login_failure"]
'''
new_test_extract = '''fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_classify_login_failure")
auth_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_authenticated_pnd_url")
module = ast.Module(body=[fn, auth_fn], type_ignores=[])
ast.fix_missing_locations(module)
ns = {}
exec(compile(module, str(target), "exec"), ns)
classify = ns["_classify_login_failure"]
is_authenticated = ns["_is_authenticated_pnd_url"]
'''
if old_test_extract not in test:
    raise SystemExit("test extraction anchor not found")
test = test.replace(old_test_extract, new_test_extract, 1)

test_anchor = '''assert classify(
    "https://example.invalid/unexpected",
    "Unexpected page",
) == "unexpected_login_state"

'''
test_insert = '''assert classify(
    "https://example.invalid/unexpected",
    "Unexpected page",
) == "unexpected_login_state"

assert is_authenticated(
    "https://pnd.cezdistribuce.cz/cezpnd2/external/dashboard/view"
)
assert is_authenticated(
    "https://PND.CEZDISTRIBUCE.CZ/cezpnd2/external/measurements"
)
assert not is_authenticated(
    "https://mepas.cez.cz/cas/login?service=x"
)
assert not is_authenticated(
    "https://pnd.cezdistribuce.cz/cezpnd2/login/oauth2/code/mepas-external"
)

'''
if test_anchor not in test:
    raise SystemExit("test assertion anchor not found")
test = test.replace(test_anchor, test_insert, 1)

test_tail_anchor = '''assert 'raise RuntimeError(f"PND login failed: {login_failure}")' in src
print("PND_LOGIN_FAILURE_REGRESSION_OK")
'''
test_tail_new = '''assert 'raise RuntimeError(f"PND login failed: {login_failure}")' in src
assert "Authenticated PND URL detected." in src
print("PND_LOGIN_FAILURE_REGRESSION_OK")
'''
if test_tail_anchor not in test:
    raise SystemExit("test tail anchor not found")
test = test.replace(test_tail_anchor, test_tail_new, 1)

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
src_backup = SRC.with_name(SRC.name + f".bak-auth-url-{stamp}")
test_backup = TEST.with_name(TEST.name + f".bak-auth-url-{stamp}")
shutil.copy2(SRC, src_backup)
shutil.copy2(TEST, test_backup)

SRC.write_text(src, encoding="utf-8")
TEST.write_text(test, encoding="utf-8")

print("PND_AUTH_URL_PATCH_WRITE_OK")
print(f"SRC_BACKUP={src_backup}")
print(f"TEST_BACKUP={test_backup}")
