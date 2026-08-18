#!/bin/sh
set -eu
BASE=/home/lina/.local/share/markvarec-pnd
BOOT="$BASE/pip-bootstrap"
VENDOR="$BASE/vendor"
GETPIP=/tmp/markvarec-pnd-get-pip.py
mkdir -p "$BASE"
rm -rf "$BOOT" "$VENDOR"
curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$GETPIP"
python3 "$GETPIP" --disable-pip-version-check --no-warn-script-location --break-system-packages --target "$BOOT"
rm -f "$GETPIP"
PYTHONPATH="$BOOT" python3 -m pip --version
PYTHONPATH="$BOOT" python3 -m pip install --disable-pip-version-check --quiet --upgrade --target "$VENDOR" --break-system-packages selenium
PYTHONPATH="$VENDOR" python3 - <<'PY'
import selenium
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
print("SELENIUM_VERSION=" + selenium.__version__)
opts = Options()
opts.add_argument("-headless")
driver = None
try:
    driver = webdriver.Firefox(options=opts)
    driver.set_page_load_timeout(40)
    driver.get("https://pnd.cezdistribuce.cz/cezpnd2/external/dashboard/view")
    print("FINAL_HOST=" + driver.current_url.split("/")[2])
    print("TITLE=" + driver.title)
    email = driver.find_elements(By.XPATH, "//input[@placeholder='Zadejte svůj e-mail']")
    password = driver.find_elements(By.XPATH, "//input[@placeholder='Zadejte své heslo']")
    submit = driver.find_elements(By.XPATH, "//button[@type='submit' and contains(@class, 'mui-btn--primary')]")
    print(f"LOGIN_FIELDS=email:{len(email)},password:{len(password)},submit:{len(submit)}")
    if not (email and password and submit):
        raise SystemExit("PND_LOGIN_DOM_NOT_FOUND")
    print("PND_FIREFOX_ANON_E2E_OK")
finally:
    if driver is not None:
        driver.quit()
PY
find /home/lina/.cache/selenium -type f -name geckodriver -perm -u+x -print -quit 2>/dev/null | grep -q . && echo GECKODRIVER_CACHE_OK || true
echo "PND_BASE_BYTES=$(du -sb "$BASE" | awk '{print $1}')"
