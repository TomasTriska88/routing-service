#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PND_URL = "https://pnd.cezdistribuce.cz/cezpnd2/external/dashboard/view"


def main() -> int:
    cred_path = Path(sys.argv[1])
    creds = json.loads(cred_path.read_text(encoding="utf-8"))
    username = str(creds.get("username") or "").strip()
    password = str(creds.get("password") or "")
    if not username or not password:
        raise SystemExit("missing credentials")

    def redact(value: object) -> str:
        text = str(value or "")
        if username:
            text = text.replace(username, "<redacted-email>")
        if password:
            text = text.replace(password, "<redacted-password>")
        text = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "<redacted-email>", text, flags=re.I)
        return " ".join(text.split())

    options = FirefoxOptions()
    options.add_argument("--headless")
    options.set_preference("browser.download.manager.showWhenStarting", False)
    gecko = os.environ.get("MARKVAREC_GECKODRIVER", "").strip()
    driver = (
        webdriver.Firefox(service=FirefoxService(gecko), options=options)
        if gecko
        else webdriver.Firefox(options=options)
    )
    driver.set_window_size(1920, 1080)

    def snapshot(label: str) -> None:
        source_lower = driver.page_source.lower()
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            body = ""
        headings = []
        for tag in ("h1", "h2", "h3", "h4"):
            for el in driver.find_elements(By.TAG_NAME, tag)[:12]:
                txt = redact(el.text)
                if txt:
                    headings.append({"tag": tag, "text": txt[:220]})
        inputs = []
        for el in driver.find_elements(By.TAG_NAME, "input")[:20]:
            inputs.append(
                {
                    "type": el.get_attribute("type"),
                    "name": el.get_attribute("name"),
                    "id": el.get_attribute("id"),
                    "placeholder": redact(el.get_attribute("placeholder")),
                    "autocomplete": el.get_attribute("autocomplete"),
                }
            )
        buttons = []
        for el in driver.find_elements(By.TAG_NAME, "button")[:20]:
            buttons.append(
                {
                    "type": el.get_attribute("type"),
                    "id": el.get_attribute("id"),
                    "class": el.get_attribute("class"),
                    "text": redact(el.text)[:160],
                }
            )
        forms = []
        for el in driver.find_elements(By.TAG_NAME, "form")[:10]:
            forms.append(
                {
                    "action": redact(el.get_attribute("action"))[:400],
                    "method": el.get_attribute("method"),
                    "id": el.get_attribute("id"),
                    "class": el.get_attribute("class"),
                }
            )
        flags = {
            key: key in source_lower
            for key in (
                "captcha",
                "recaptcha",
                "hcaptcha",
                "otp",
                "mfa",
                "two-factor",
                "verification",
                "ověření",
                "execution",
            )
        }
        payload = {
            "label": label,
            "url": redact(driver.current_url),
            "title": redact(driver.title),
            "body_text": redact(body)[:1800],
            "headings": headings,
            "forms": forms,
            "inputs": inputs,
            "buttons": buttons,
            "flags": flags,
            "cookie_names": sorted({str(c.get("name") or "") for c in driver.get_cookies()}),
        }
        print("PND_DIAG=" + json.dumps(payload, ensure_ascii=False, sort_keys=True))

    try:
        driver.get(PND_URL)
        wait = WebDriverWait(driver, 20)
        email = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Zadejte svůj e-mail']")))
        passwd = driver.find_element(By.XPATH, "//input[@placeholder='Zadejte své heslo']")
        button = driver.find_element(By.XPATH, "//button[@type='submit' and contains(@class, 'mui-btn--primary')]")
        print("PND_LOGIN_FORM_FOUND=1")
        email.send_keys(username)
        passwd.send_keys(password)
        snapshot("before_submit")
        wait.until(EC.element_to_be_clickable(button)).click()
        previous = None
        for delay in (2, 5, 10):
            time.sleep(delay)
            current = driver.current_url
            snapshot(f"after_submit_{delay}s")
            if current != previous:
                previous = current
        print("PND_LOGIN_DIAG_OK")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
