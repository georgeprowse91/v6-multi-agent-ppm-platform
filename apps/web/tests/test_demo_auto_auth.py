import importlib
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / 'src'

if 'email_validator' not in sys.modules:
    module = types.ModuleType('email_validator')
    module.EmailNotValidError = ValueError
    module.validate_email = lambda value, **kwargs: types.SimpleNamespace(email=value)
    sys.modules['email_validator'] = module

if 'event_bus' not in sys.modules:
    module = types.ModuleType('event_bus')
    module.EventHandler = object
    module.EventRecord = dict

    class _Bus:
        async def publish(self, *args, **kwargs):
            return None

    module.ServiceBusEventBus = _Bus
    module.get_event_bus = lambda *args, **kwargs: _Bus()
    sys.modules['event_bus'] = module

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _build_client(monkeypatch: pytest.MonkeyPatch, demo_mode: bool) -> TestClient:
    monkeypatch.setenv('ENVIRONMENT', 'test')
    monkeypatch.setenv('AUTH_DEV_MODE', 'false')
    monkeypatch.setenv('DEMO_MODE', 'true' if demo_mode else 'false')

    import main  # noqa: E402

    main = importlib.reload(main)
    return TestClient(main.app)


def test_demo_mode_root_request_auto_bootstraps_session(monkeypatch: pytest.MonkeyPatch):
    with _build_client(monkeypatch, demo_mode=True) as client:
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 307
        assert response.headers['location'] == '/app?project_id=demo-predictive'
        assert 'ppm_session=' in response.headers.get('set-cookie', '')

        session_response = client.get('/v1/session')
        assert session_response.status_code == 200
        payload = session_response.json()
        assert payload['authenticated'] is True
        assert payload['subject'] == 'demo-user'
        assert payload['tenant_id'] == 'demo-tenant'
        assert payload['permissions']


def test_production_mode_does_not_auto_bootstrap_demo_session(monkeypatch: pytest.MonkeyPatch):
    with _build_client(monkeypatch, demo_mode=False) as client:
        response = client.get('/', follow_redirects=False)
        assert response.status_code != 307 or response.headers.get('location') != '/app?project_id=demo-predictive'

        session_response = client.get('/v1/session')
        assert session_response.status_code == 200
        payload = session_response.json()
        assert payload == {'authenticated': False, 'subject': None, 'tenant_id': None, 'roles': None, 'permissions': None}


def test_demo_mode_app_request_auto_bootstraps_session(monkeypatch: pytest.MonkeyPatch):
    with _build_client(monkeypatch, demo_mode=True) as client:
        response = client.get('/app', follow_redirects=False)
        assert response.status_code == 307
        assert response.headers['location'] == '/app?project_id=demo-predictive'
