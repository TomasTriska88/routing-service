from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import time
import hashlib

REST = Path('/config/custom_components/cez_distribuce/rest_client/rest_client.py')
FLOW = Path('/config/custom_components/cez_distribuce/config_flow.py')
TEST = Path('/config/tests/test_cez_login_regression.py')
stamp = time.strftime('%Y%m%d-%H%M%S')
REST_BAK = REST.with_name(REST.name + f'.bak-login-{stamp}')
FLOW_BAK = FLOW.with_name(FLOW.name + f'.bak-login-{stamp}')
TEST_BAK = TEST.with_name(TEST.name + f'.bak-login-{stamp}')

old_class = 'class AbstractCezRestClient:\n'
new_class = '''class CezAuthenticationError(Exception):
    """Raised when ČEZ explicitly rejects the supplied credentials."""


class CezLoginFlowError(Exception):
    """Raised when the ČEZ login/API flow no longer matches expectations."""


class AbstractCezRestClient:
'''

old_login = '''    def login(self, username=None, password=None):
        if username:
            self._username = username
        if password:
            self._password = password
        response = self._session.get(self._login_url)
        # Parsuje HTML a hledá skryté pole execution
        response = self._session.post(self._login_url, data={
            'username': self._username,
            'password': self._password,
            'execution': BeautifulSoup(response.text, 'html.parser').find('input', {'name': 'execution'})['value'],
            '_eventId': 'submit',
            'geolocation': ''
        })
        logging.debug(log_history(response))
        response = self._session.get(self._authorize_url)
        logging.debug(log_history(response))
'''

new_login = '''    @staticmethod
    def _find_login_form(response):
        """Return the current username/password form and all named fields.

        ČEZ has changed its CAS/MEPAS markup several times. Follow the form
        actually returned by the server instead of assuming a fixed
        ``execution`` field or POST URL.
        """
        soup = BeautifulSoup(response.text, 'html.parser')
        form = next((
            candidate for candidate in soup.find_all('form')
            if candidate.find('input', {'name': 'username'})
            and candidate.find('input', {'name': 'password'})
        ), None)
        if form is None:
            raise CezLoginFlowError(
                f'ČEZ login form not found at {response.url}'
            )

        fields = {
            item.get('name'): item.get('value') or ''
            for item in form.find_all('input')
            if item.get('name')
        }
        return form, fields

    @staticmethod
    def _is_login_form(response):
        """Return True when the response still asks for username/password."""
        soup = BeautifulSoup(response.text, 'html.parser')
        return bool(
            soup.find('input', {'name': 'username'})
            and soup.find('input', {'name': 'password'})
        )

    def login(self, username=None, password=None):
        if username:
            self._username = username
        if password:
            self._password = password

        response = self._session.get(self._login_url)
        response.raise_for_status()
        form, fields = self._find_login_form(response)
        fields['username'] = self._username or ''
        fields['password'] = self._password or ''
        fields.setdefault('_eventId', 'submit')
        fields.setdefault('geolocation', '')

        post_url = urllib.parse.urljoin(
            response.url,
            form.get('action') or self._login_url,
        )
        response = self._session.post(post_url, data=fields)
        logging.debug(log_history(response))
        response.raise_for_status()

        if self._is_login_form(response):
            raise CezAuthenticationError('ČEZ rejected the supplied credentials')

        response = self._session.get(self._authorize_url)
        logging.debug(log_history(response))
        response.raise_for_status()

        if self._is_login_form(response):
            raise CezAuthenticationError('ČEZ authentication did not complete')
'''

old_handle = '''    def _handle_login(self, func):
        for i in range(LOGIN_RETRIES):
            response = func()
            if response.status_code == 401:
                self.login()
                continue
            elif response.status_code == 200:
                return response.json()
        raise Exception('Unable to login')
'''

new_handle = '''    def _handle_login(self, func):
        for i in range(LOGIN_RETRIES):
            response = func()
            if response.status_code == 401:
                self.login()
                continue
            elif response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    content_type = response.headers.get('Content-Type', 'unknown')
                    raise CezLoginFlowError(
                        'ČEZ API returned non-JSON response '
                        f'from {response.url} ({content_type})'
                    ) from exc
        raise CezLoginFlowError('Unable to login to ČEZ')
'''

old_import = 'from .rest_client.rest_client import CezDistribuceRestClient\n'
new_import = 'from .rest_client.rest_client import CezAuthenticationError, CezDistribuceRestClient\n'

old_except = '''        except Exception as e:  # broad: external service may change
            msg = str(e).lower()
            _LOGGER.warning("Login validation failed: %s", e)
            # Heuristic: bad credentials vs connectivity
            if "401" in msg or "invalid" in msg or "unauthor" in msg:
                return "invalid_auth"
            return "cannot_connect"
'''
new_except = '''        except CezAuthenticationError as e:
            _LOGGER.warning("Login validation rejected credentials: %s", e)
            return "invalid_auth"
        except Exception as e:  # broad: external service may change
            msg = str(e).lower()
            _LOGGER.warning("Login validation failed: %s", e)
            # Keep backwards-compatible heuristics for HTTP/client exceptions.
            if "401" in msg or "invalid" in msg or "unauthor" in msg:
                return "invalid_auth"
            return "cannot_connect"
'''

test_content = r'''"""Regression checks for the ČEZ CAS/MEPAS login parser."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

MODULE_PATH = Path('/config/custom_components/cez_distribuce/rest_client/rest_client.py')
spec = importlib.util.spec_from_file_location('cez_rest_client_regression', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

LOGIN_HTML = """<!doctype html><html><body>
<form action="login" method="post">
  <input name="username" type="text" value="">
  <input name="password" type="password" value="">
  <input name="execution" type="hidden" value="dynamic-token">
  <input name="_eventId" type="hidden" value="submit">
  <input name="geolocation" type="hidden">
</form></body></html>"""
SUCCESS_HTML = '<!doctype html><html><body>Authenticated</body></html>'

class FakeResponse:
    def __init__(self, text, url, status_code=200, headers=None, json_value=None):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.headers = headers or {'Content-Type': 'text/html'}
        self.history = []
        self.is_redirect = False
        self._json_value = json_value
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')
    def json(self):
        if self._json_value is None:
            raise ValueError('not json')
        return self._json_value

class InvalidSession:
    def __init__(self):
        self.post_url = None
        self.post_data = None
    def get(self, url, **kwargs):
        return FakeResponse(LOGIN_HTML, url)
    def post(self, url, data=None, **kwargs):
        self.post_url = url
        self.post_data = dict(data or {})
        return FakeResponse(LOGIN_HTML, 'https://mepas.cez.cz/cas/login')

class SuccessSession:
    def __init__(self, authorize_url):
        self.authorize_url = authorize_url
        self.post_url = None
        self.post_data = None
    def get(self, url, **kwargs):
        if url == self.authorize_url:
            return FakeResponse(SUCCESS_HTML, url)
        return FakeResponse(LOGIN_HTML, url)
    def post(self, url, data=None, **kwargs):
        self.post_url = url
        self.post_data = dict(data or {})
        return FakeResponse(SUCCESS_HTML, 'https://mepas.cez.cz/cas/login')

def make_client():
    return module.AbstractCezRestClient('https://dip.cezdistribuce.cz/irj/portal', 'test-client')

client = make_client()
invalid = InvalidSession()
client._session = invalid
try:
    client.login('user@example.test', 'wrong')
except module.CezAuthenticationError:
    pass
else:
    raise AssertionError('invalid credentials must raise CezAuthenticationError')
assert invalid.post_url == 'https://mepas.cez.cz/cas/login', invalid.post_url
assert invalid.post_data['execution'] == 'dynamic-token'
assert invalid.post_data['username'] == 'user@example.test'
assert invalid.post_data['password'] == 'wrong'

client = make_client()
success = SuccessSession(client._authorize_url)
client._session = success
client.login('user@example.test', 'correct')
assert success.post_url == 'https://mepas.cez.cz/cas/login'
assert success.post_data['execution'] == 'dynamic-token'

missing = FakeResponse('<html><body>maintenance</body></html>', 'https://mepas.cez.cz/cas/login')
try:
    module.AbstractCezRestClient._find_login_form(missing)
except module.CezLoginFlowError:
    pass
else:
    raise AssertionError('missing form must raise CezLoginFlowError')

non_json = FakeResponse(
    '<html>session expired</html>',
    'https://dip.cezdistribuce.cz/irj/portal/rest-auth-api',
    headers={'Content-Type': 'text/html'},
)
client = make_client()
client._session = SimpleNamespace()
try:
    client._handle_login(lambda: non_json)
except module.CezLoginFlowError as exc:
    assert 'non-JSON' in str(exc)
else:
    raise AssertionError('non-JSON API response must raise CezLoginFlowError')

print('CEZ_LOGIN_REGRESSION_OK')
'''

def patch_file(path, replacements):
    text = path.read_text(encoding='utf-8')
    for old, new in replacements:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f'{path}: expected 1 occurrence, got {count}')
        text = text.replace(old, new, 1)
    path.write_text(text, encoding='utf-8')

shutil.copy2(REST, REST_BAK)
shutil.copy2(FLOW, FLOW_BAK)
if TEST.exists():
    shutil.copy2(TEST, TEST_BAK)

try:
    patch_file(REST, [(old_class, new_class), (old_login, new_login), (old_handle, new_handle)])
    patch_file(FLOW, [(old_import, new_import), (old_except, new_except)])
    TEST.parent.mkdir(parents=True, exist_ok=True)
    TEST.write_text(test_content, encoding='utf-8')
    py_compile.compile(str(REST), doraise=True)
    py_compile.compile(str(FLOW), doraise=True)
    py_compile.compile(str(TEST), doraise=True)
    subprocess.run([sys.executable, str(TEST)], check=True)
    result = subprocess.run(
        [sys.executable, '-m', 'homeassistant', '--script', 'check_config', '-c', '/config'],
        text=True, capture_output=True
    )
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    if result.returncode != 0 or 'could not be validated and has been disabled' in (result.stdout + result.stderr):
        raise RuntimeError(f'Home Assistant check_config failed: {result.returncode}')
    print('REST_SHA256=' + hashlib.sha256(REST.read_bytes()).hexdigest())
    print('FLOW_SHA256=' + hashlib.sha256(FLOW.read_bytes()).hexdigest())
    print('TEST_SHA256=' + hashlib.sha256(TEST.read_bytes()).hexdigest())
    print('CEZ_LOGIN_PATCH_VALIDATED_OK')
except Exception:
    shutil.copy2(REST_BAK, REST)
    shutil.copy2(FLOW_BAK, FLOW)
    if TEST_BAK.exists():
        shutil.copy2(TEST_BAK, TEST)
    elif TEST.exists():
        TEST.unlink()
    raise
