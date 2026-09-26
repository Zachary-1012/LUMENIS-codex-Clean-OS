from __future__ import annotations

import contextlib
import json
from unittest.mock import patch
from pathlib import Path

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
        'service': 'taikoo-monitor',
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
