from pathlib import Path
import hashlib
import shutil
import time

BASE = Path("/home/lina/.local/share/markvarec-pnd")
SRC = BASE / "upstream" / "pnd.py"
TEST = BASE / "tests" / "test_app_version_optional_regression.py"

old = '    # Get the app version\n    version_element = driver.find_element(By.XPATH, "//div[contains(text(), \'Verze aplikace:\')]")\n    version_text = (version_element.get_attribute("textContent") or version_element.text or "").replace("\\xa0", " ")\n    parts = version_text.split(":", 1)\n    version_number = parts[1].strip() if len(parts) > 1 else version_text.strip()\n    version_number = str(version_number).strip() or "unknown"\n    self.set_state_safe(f"sensor.pnd_app_version{self.suffix}", state=version_number, attributes={\n        "friendly_name": "PND App Version",\n    })\n    print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + f"App Version: {version_number}")\n\n    first_pnd_window = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".pnd-window")))\n'
new = '    # The app-version label is diagnostic only and is not present on every PND dashboard build.\n    version_number = "unknown"\n    try:\n        version_elements = driver.find_elements(By.XPATH, "//div[contains(text(), \'Verze aplikace:\')]")\n        if version_elements:\n            version_element = version_elements[0]\n            version_text = (version_element.get_attribute("textContent") or version_element.text or "").replace("\\xa0", " ")\n            parts = version_text.split(":", 1)\n            version_number = parts[1].strip() if len(parts) > 1 else version_text.strip()\n            version_number = str(version_number).strip() or "unknown"\n    except Exception as version_error:\n        print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + f"PND app version is unavailable: {type(version_error).__name__}")\n    self.set_state_safe(f"sensor.pnd_app_version{self.suffix}", state=version_number, attributes={\n        "friendly_name": "PND App Version",\n    })\n    print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + f"App Version: {version_number}")\n\n    first_pnd_window = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".pnd-window")))\n'

source = SRC.read_text(encoding="utf-8")
assert "Authenticated PND URL detected." in source, "Expected authenticated-URL compatibility patch is missing"
assert source.count(old) == 1, f"Expected exactly one legacy app-version block, found {source.count(old)}"

stamp = time.strftime("%Y%m%d-%H%M%S")
src_backup = SRC.with_name(f"pnd.py.bak-appversion-{stamp}")
test_backup = None
shutil.copy2(SRC, src_backup)
if TEST.exists():
    test_backup = TEST.with_name(f"{TEST.name}.bak-{stamp}")
    shutil.copy2(TEST, test_backup)

patched = source.replace(old, new, 1)
SRC.write_text(patched, encoding="utf-8")

test_source = 'from pathlib import Path\n\nSRC = Path("/home/lina/.local/share/markvarec-pnd/upstream/pnd.py")\ntext = SRC.read_text(encoding="utf-8")\n\nassert \'Authenticated PND URL detected.\' in text\nassert \'version_number = "unknown"\' in text\nassert \'version_elements = driver.find_elements(By.XPATH, "//div[contains(text(), \\\'Verze aplikace:\\\')]" )\'.replace(\'" )\', \'")\') in text\nassert \'version_element = driver.find_element(By.XPATH, "//div[contains(text(), \\\'Verze aplikace:\\\')]" )\'.replace(\'" )\', \'")\') not in text\n\nversion_pos = text.index(\'# The app-version label is diagnostic only\')\nwindow_pos = text.index(\'first_pnd_window = wait.until\', version_pos)\nassert version_pos < window_pos\n\nprint("PND_APP_VERSION_OPTIONAL_REGRESSION_OK")\n'
TEST.write_text(test_source, encoding="utf-8")

print(f"SRC_BACKUP={src_backup}")
print(f"TEST_BACKUP={test_backup or ''}")
print(f"SRC_SHA256={hashlib.sha256(SRC.read_bytes()).hexdigest()}")
print(f"TEST_SHA256={hashlib.sha256(TEST.read_bytes()).hexdigest()}")
print("PND_APP_VERSION_OPTIONAL_PATCH_APPLIED")
