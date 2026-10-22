from __future__ import annotations

import contextlib
import hashlib
import json
import threading
from unittest.mock import patch

import pytest

import app as product_core
import run_supervised


class _ProbeConnection:
    def __init__(self, marker):
        self.marker = marker
        self.sql = None

    def execute(self, sql: str):
        self.sql = sql
        return self

    def fetchone(self):
        return self.marker


class _ReadOnlyRepository:
    def __init__(self, marker=None, failure=None):
        self.connection_value = _ProbeConnection(marker)
        self.failure = failure
        self.options = None

    @contextlib.contextmanager
    def connection(self, **kwargs):
        self.options = kwargs
        if self.failure:
            raise self.failure
        yield self.connection_value


def test_healthz_requires_existing_canonical_notes_schema_and_read_only_connection(monkeypatch):
    repository = _ReadOnlyRepository(marker=(1,))
    monkeypatch.setattr(product_core, 'get_repository', lambda: repository)

    response = product_core.app.test_client().get('/healthz')

    assert response.status_code == 200
    assert response.get_json() == {
        'ok': True,
        'status': 'healthy',
        'dependencies': {'database': 'ok'},
        'version': product_core.APP_VERSION,
        'service': 'lumenis-core',
        'core_instance': dict(product_core._CORE_INSTANCE),
        'runtime': {
            'web_server': product_core._CORE_SERVER_KIND,
            'scheduler': product_core._scheduler_runtime_state(),
        },
    }
    assert repository.options == {'read_only': True, 'wal': False}
    assert repository.connection_value.sql == (
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='notes'"
    )


def test_healthz_reports_database_failure_as_unavailable_without_leaking_error(monkeypatch):
    repository = _ReadOnlyRepository(failure=OSError('private database path detail'))
    monkeypatch.setattr(product_core, 'get_repository', lambda: repository)

    response = product_core.app.test_client().get('/healthz')

    assert response.status_code == 503
    payload = response.get_json()
    assert payload['ok'] is False
    assert payload['status'] == 'unavailable'
    assert payload['dependencies'] == {'database': 'unavailable'}
    assert 'private database path detail' not in response.get_data(as_text=True)
    assert repository.options == {'read_only': True, 'wal': False}


def test_healthz_rejects_database_without_required_canonical_table(monkeypatch):
    repository = _ReadOnlyRepository(marker=None)
    monkeypatch.setattr(product_core, 'get_repository', lambda: repository)

    response = product_core.app.test_client().get('/healthz')

    assert response.status_code == 503
    assert response.get_json()['dependencies'] == {'database': 'unavailable'}


def test_healthz_missing_database_is_unavailable_without_creating_file(monkeypatch, tmp_path):
    missing = tmp_path / 'must-remain-absent.sqlite3'
    monkeypatch.setenv('ZBC_DB_PATH', str(missing))

    response = product_core.app.test_client().get('/healthz')

    assert response.status_code == 503
    assert response.get_json()['dependencies'] == {'database': 'unavailable'}
    assert not missing.exists()


def test_product_server_defaults_to_installed_waitress_without_development_fallback(monkeypatch):
    import waitress

    monkeypatch.delenv('ZB_WSGI', raising=False)
    monkeypatch.delenv('ZB_WSGI_THREADS', raising=False)
    monkeypatch.setattr(product_core, '_CORE_SERVER_KIND', 'not_started')
    calls = []
    application = object()
    monkeypatch.setattr(waitress, 'serve', lambda app, **kwargs: calls.append((app, kwargs)))
    product_core._serve_product_core(application, '127.0.0.1', 8123)
    assert calls == [(application, {'host': '127.0.0.1', 'port': 8123, 'threads': 8})]
    assert product_core._CORE_SERVER_KIND == 'waitress'


@pytest.mark.parametrize('server,threads,error', [
    ('unknown', '8', 'ZB_WSGI must'),
    ('waitress', '0', 'ZB_WSGI_THREADS must'),
    ('waitress', '257', 'ZB_WSGI_THREADS must'),
    ('waitress', 'invalid', 'invalid literal'),
])
def test_invalid_server_configuration_cannot_silently_start_development_server(
    monkeypatch, server, threads, error
):
    monkeypatch.setenv('ZB_WSGI', server)
    monkeypatch.setenv('ZB_WSGI_THREADS', threads)
    with pytest.raises(ValueError, match=error):
        product_core._serve_product_core(object(), '127.0.0.1', 8123)


def test_waitress_failure_propagates_without_fallback(monkeypatch):
    import waitress

    monkeypatch.setenv('ZB_WSGI', 'waitress')
    monkeypatch.setattr(product_core, '_CORE_SERVER_KIND', 'not_started')
    def failed(*args, **kwargs):
        raise OSError('port is already in use')
    monkeypatch.setattr(waitress, 'serve', failed)
    with pytest.raises(OSError, match='port is already in use'):
        product_core._serve_product_core(object(), '127.0.0.1', 8123)


def test_runtime_scheduler_observation_distinguishes_not_started_failed_and_stopping(monkeypatch):
    from types import SimpleNamespace

    stop = threading.Event()
    monkeypatch.setattr(product_core, '_SCHEDULER_STOP', stop)
    monkeypatch.setattr(product_core, '_SCHEDULER_THREAD', None)
    assert product_core._scheduler_runtime_state() == 'not_started'
    for alive, expected in [(True, 'running'), (False, 'unavailable')]:
        monkeypatch.setattr(product_core, '_SCHEDULER_THREAD', SimpleNamespace(is_alive=lambda alive=alive: alive))
        assert product_core._scheduler_runtime_state() == expected
    stop.set()
    for alive, expected in [(True, 'stopping'), (False, 'stopped')]:
        monkeypatch.setattr(product_core, '_SCHEDULER_THREAD', SimpleNamespace(is_alive=lambda alive=alive: alive))
        assert product_core._scheduler_runtime_state() == expected


class _HTTPResponse:
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size):
        return json.dumps(self.payload).encode('utf-8')[:size]


def test_supervisor_rejects_non_200_and_incomplete_or_unhealthy_payloads():
    healthy = {'ok': True, 'status': 'healthy', 'dependencies': {'database': 'ok'}}
    unavailable = {'ok': False, 'status': 'unavailable', 'dependencies': {'database': 'unavailable'}}
    cases = (
        (200, healthy, True),
        (503, unavailable, False),
        (404, unavailable, False),
        (200, unavailable, False),
        (200, {'ok': True, 'status': 'healthy'}, False),
    )
    for status, payload, expected in cases:
        with patch.object(run_supervised.urllib.request, 'urlopen', return_value=_HTTPResponse(status, payload)):
            assert run_supervised.http_health(8201) is expected


def test_core_entry_identity_is_frozen_and_rejects_a_changed_startup_target(tmp_path):
    import pytest

    entry = tmp_path / 'app.py'
    original = b'print("original")\n'
    entry.write_bytes(original)
    expected = hashlib.sha256(original).hexdigest()
    identity = product_core._core_instance_identity(entry, {
        'LUMENIS_CORE_LAUNCH_ID': 'a' * 32,
        'LUMENIS_CORE_BOOT_ID': 'b' * 32,
        'LUMENIS_CORE_ENTRY_SHA256': expected,
    })
    assert dict(identity) == {
        'launch_id': 'a' * 32,
        'boot_id': 'b' * 32,
        'entry_sha256': expected,
    }
    entry.write_bytes(b'print("changed")\n')
    assert identity['entry_sha256'] == expected
    with pytest.raises(TypeError):
        identity['entry_sha256'] = 'c' * 64
    with pytest.raises(RuntimeError, match='does not match'):
        product_core._core_instance_identity(entry, {'LUMENIS_CORE_ENTRY_SHA256': expected})


def test_core_entry_identity_rejects_malformed_attempt_identifiers(tmp_path):
    import pytest

    entry = tmp_path / 'app.py'
    entry.write_bytes(b'pass\n')
    for field in ('LUMENIS_CORE_LAUNCH_ID', 'LUMENIS_CORE_BOOT_ID'):
        with pytest.raises(RuntimeError, match='Invalid Core startup'):
            product_core._core_instance_identity(entry, {field: 'invalid/private/path'})


def test_supervisor_health_is_bound_to_current_launch_boot_and_entry():
    identity = {'launch_id': 'a' * 32, 'boot_id': 'b' * 32, 'entry_sha256': 'c' * 64}
    expected = {
        'expected_launch_id': identity['launch_id'],
        'expected_boot_id': identity['boot_id'],
        'expected_entry_sha256': identity['entry_sha256'],
    }
    healthy = {'ok': True, 'status': 'healthy', 'dependencies': {'database': 'ok'}}
    cases = [({}, False), (identity, True)]
    for field, value in identity.items():
        cases.append(({**identity, field: 'd' * len(value)}, False))
    for observed, accepted in cases:
        payload = {**healthy, 'core_instance': observed}
        with patch.object(run_supervised.urllib.request, 'urlopen', return_value=_HTTPResponse(200, payload)):
            assert run_supervised.http_health(8201, **expected) is accepted
