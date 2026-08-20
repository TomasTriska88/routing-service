#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path.home() / ".local" / "share" / "markvarec-pnd"
PND = BASE / "upstream" / "pnd.py"
RUNNER = BASE / "run_standalone.py"
TEST = BASE / "tests" / "test_server_error_regression.py"
EXPECTED_PND = "367fad54adfd97d49457c22fbf318c5e42655f7c8b09e6907ac85eca5d735d19"
EXPECTED_RUNNER = "a31b02c9e388e26fbf305cb8545229bc1468343574e00d56b273555330aca594"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 anchor, got {count}")
    return text.replace(old, new, 1)


def patch_pnd(text: str) -> str:
    anchor = "def _classify_login_failure("
    if text.count(anchor) != 1:
        raise RuntimeError("unexpected login-classifier anchor")
    helper = '''class PNDServerError(RuntimeError):
    """Authenticated PND backend returned its internal server-error page."""

    pnd_status = "server_error"


def _classify_authenticated_dashboard_message(message_texts):
    normalized = " ".join(str(value or "") for value in (message_texts or []))
    normalized = " ".join(normalized.replace("\\xa0", " ").split()).casefold()
    if "interní chyba serveru" in normalized:
        return "server_error"
    if "vnitřní chyba" in normalized and "server" in normalized:
        return "server_error"
    if "internal server error" in normalized:
        return "server_error"
    return None


'''
    text = text.replace(anchor, helper + anchor, 1)

    text = once(
        text,
        're.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\\\.[A-Za-z]{2,}", "[EMAIL]", value)',
        're.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "[EMAIL]", value)',
        "email sanitizer",
    )
    text = once(text, 're.sub(r"\\\\d{5,}", "[NUM]", value)', 're.sub(r"\\d{5,}", "[NUM]", value)', "number sanitizer")
    text = once(text, 're.sub(r"\\\\s+", " ", value)', 're.sub(r"\\s+", " ", value)', "space sanitizer")

    return_anchor = '            return re.sub(r"\\s+", " ", value).strip()[:160]\n\n'
    probe = '''            return re.sub(r"\\s+", " ", value).strip()[:160]

        # A successful login can still land on the authenticated ČEZ error
        # page. Classify that before treating the page as a changed layout.
        try:
            server_message_texts = []
            for message_selector in (".pnd-message", ".pnd-header", ".pnd-message-footer"):
                for element in driver.find_elements(By.CSS_SELECTOR, message_selector)[:5]:
                    text_value = str(element.text or "").strip()
                    if text_value:
                        server_message_texts.append(text_value)
            dashboard_status = None
            if _is_authenticated_pnd_url(str(driver.current_url or "")):
                dashboard_status = _classify_authenticated_dashboard_message(server_message_texts)
        except Exception as server_probe_error:
            dashboard_status = None
            print("PND_SERVER_ERROR_PROBE_ERROR=" + type(server_probe_error).__name__)

        if dashboard_status == "server_error":
            print("PND_DASHBOARD_STATUS=server_error")
            self.set_state_safe(f"binary_sensor.pnd_script_running{self.suffix}", state="off")
            self.set_state_safe(
                f"sensor.pnd_script_status{self.suffix}",
                state="Error",
                attributes={"status": "Portál naměřených dat právě vrací interní chybu serveru."},
            )
            try:
                driver.quit()
            except Exception:
                pass
            raise PNDServerError("PND authenticated portal returned server_error") from dashboard_layout_error

'''
    return once(text, return_anchor, probe, "server-error probe")


def patch_runner(text: str) -> str:
    text = once(text, "import traceback\n", "import traceback\nimport time\n", "time import")
    text = once(
        text,
        'TZ = ZoneInfo("Europe/Prague")\n',
        'TZ = ZoneInfo("Europe/Prague")\nSERVER_ERROR_MAX_ATTEMPTS = 3\nSERVER_ERROR_RETRY_DELAYS = (10, 20)\n',
        "retry constants",
    )
    old_run = '''    try:
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
'''
    new_run = '''    upstream = None
    attempts = 0
    try:
        import pnd as upstream

        app = None
        for attempt in range(1, SERVER_ERROR_MAX_ATTEMPTS + 1):
            attempts = attempt
            app = upstream.pnd()
            app.args = {
                "PNDUserName": username,
                "PNDUserPassword": password,
                "DownloadFolder": str(DATA),
                "DataInterval": interval,
                "ELM": elm,
            }
            app.initialize()
            try:
                app.run_pnd("run_pnd", {}, {})
                break
            except Exception as run_exc:
                is_server_error = isinstance(run_exc, getattr(upstream, "PNDServerError", ()))
                if not is_server_error or attempt >= SERVER_ERROR_MAX_ATTEMPTS:
                    raise
                delay = SERVER_ERROR_RETRY_DELAYS[attempt - 1]
                print(
                    f"PND_SERVER_ERROR_RETRY={attempt}/{SERVER_ERROR_MAX_ATTEMPTS} delay_seconds={delay}",
                    file=sys.stderr,
                )
                time.sleep(delay)

        if app is None:
            raise RuntimeError("PND collector did not start.")
        states = app._states
'''
    text = once(text, old_run, new_run, "runner execution")
    old_exc = '''    except Exception as exc:
        payload = _base_state("error")
        text = f"{type(exc).__name__}: {exc}".replace(username, "<redacted>")
        payload["error"] = text[:500]
        payload["message"] = "Načtení naměřených dat selhalo."
        _write_json(STATE, payload)
        traceback.print_exc()
        return 1
'''
    new_exc = '''    except Exception as exc:
        is_server_error = bool(
            upstream is not None
            and isinstance(exc, getattr(upstream, "PNDServerError", ()))
        )
        payload = _base_state("server_error" if is_server_error else "error")
        text = f"{type(exc).__name__}: {exc}"
        for secret in (username, password):
            if secret:
                text = text.replace(secret, "<redacted>")
        payload["error"] = text[:500]
        if is_server_error:
            payload["message"] = "Portál naměřených dat právě vrací interní chybu serveru."
            payload["retry_attempts"] = attempts
            print(f"PND_RUN_STATUS=server_error attempts={attempts}", file=sys.stderr)
        else:
            payload["message"] = "Načtení naměřených dat selhalo."
            traceback.print_exc()
        _write_json(STATE, payload)
        return 1
'''
    return once(text, old_exc, new_exc, "runner exception")


TEST_TEXT = r'''#!/usr/bin/env python3
import ast
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
target = BASE / "upstream" / "pnd.py"
runner_path = BASE / "run_standalone.py"
src = target.read_text(encoding="utf-8")
runner = runner_path.read_text(encoding="utf-8")

tree = ast.parse(src)
wanted = {"_classify_authenticated_dashboard_message", "_classify_login_failure", "_is_authenticated_pnd_url", "PNDServerError"}
nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and getattr(n, "name", None) in wanted]
assert {n.name for n in nodes} == wanted
module = ast.Module(body=nodes, type_ignores=[])
ast.fix_missing_locations(module)
ns = {}
exec(compile(module, str(target), "exec"), ns)

classify_dashboard = ns["_classify_authenticated_dashboard_message"]
classify_login = ns["_classify_login_failure"]
is_authenticated = ns["_is_authenticated_pnd_url"]
server_error_cls = ns["PNDServerError"]
auth_url = "https://pnd.cezdistribuce.cz/cezpnd2/external/dashboard/view"
messages = ["INTERNÍ CHYBA SERVERU", "Při zpracování požadavku došlo k vnitřní chybě."]
assert is_authenticated(auth_url)
assert classify_dashboard(messages) == "server_error"
assert classify_dashboard(["Běžný dashboard bez chyby"]) is None
assert classify_login(auth_url, " ".join(messages)) != "invalid_credentials"
assert issubclass(server_error_cls, RuntimeError)

server_pos = src.index("PND_DASHBOARD_STATUS=server_error")
layout_pos = src.index("PND_DASHBOARD_LAYOUT=legacy_pnd_window_missing")
meter_pos = src.index("PND_TARGET_METER_PRESENT=")
assert server_pos < layout_pos < meter_pos
assert "driver.quit()" in src[server_pos:layout_pos]
assert 'element.get_attribute("value")' not in src
assert 'print(driver.page_source)' not in src
assert 'r"\\d{5,}"' in src
assert 'r"\\\\d{5,}"' not in src
assert 'r"\\s+"' in src
assert 'r"\\\\s+"' not in src
assert 'r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"' in src

assert "import time" in runner
assert "SERVER_ERROR_MAX_ATTEMPTS = 3" in runner
assert "SERVER_ERROR_RETRY_DELAYS = (10, 20)" in runner
assert "PND_SERVER_ERROR_RETRY=" in runner
assert "time.sleep(delay)" in runner
assert '_base_state("server_error" if is_server_error else "error")' in runner
assert "PND_RUN_STATUS=server_error" in runner
assert 'payload["retry_attempts"] = attempts' in runner
assert "for secret in (username, password):" in runner
print("PND_SERVER_ERROR_REGRESSION_OK")
'''


def main() -> int:
    if sha(PND) != EXPECTED_PND:
        raise RuntimeError(f"unexpected pnd sha={sha(PND)}")
    if sha(RUNNER) != EXPECTED_RUNNER:
        raise RuntimeError(f"unexpected runner sha={sha(RUNNER)}")
    if TEST.exists():
        raise RuntimeError("server-error test already exists")

    bp = PND.with_name(PND.name + ".bak-servererr-20260820")
    br = RUNNER.with_name(RUNNER.name + ".bak-servererr-20260820")
    shutil.copy2(PND, bp)
    shutil.copy2(RUNNER, br)
    try:
        PND.write_text(patch_pnd(PND.read_text(encoding="utf-8")), encoding="utf-8")
        RUNNER.write_text(patch_runner(RUNNER.read_text(encoding="utf-8")), encoding="utf-8")
        TEST.write_text(TEST_TEXT, encoding="utf-8")
        TEST.chmod(0o755)
        for path in (PND, RUNNER, TEST):
            py_compile.compile(str(path), doraise=True)
        for test in sorted((BASE / "tests").glob("test_*regression.py")):
            print(f"RUN_TEST={test.name}")
            subprocess.run([sys.executable, str(test)], check=True)
        print(f"PND_PY_SHA256={sha(PND)}")
        print(f"PND_RUNNER_SHA256={sha(RUNNER)}")
        print(f"PND_SERVERERR_TEST_SHA256={sha(TEST)}")
        print("PND_SERVERERR_PATCH_TESTS_OK")
        return 0
    except Exception:
        shutil.copy2(bp, PND)
        shutil.copy2(br, RUNNER)
        try:
            TEST.unlink()
        except FileNotFoundError:
            pass
        print("PND_SERVERERR_PATCH_ROLLED_BACK", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
