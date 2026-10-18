"""Screen projections consume the existing scoped native-time domain reader."""
from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace

import pytest
from flask import Flask

import canonical_data
import experience_runtime as runtime
import experience_screens as screens
from lumenis.shared import database as shared_database


def binding(mode='FOCUS', local=False):
    return dict(contract='lumenis.scope-read-binding.v1', module='commercial_realtime_stream',
                policy='local-workspace-read-v1' if local else 'actor-exact-scope-v1',
                domain_id='CTH', product_id='CTH', canonical_scope=mode,
                subject_id='SUBJ-A' if mode == 'FOCUS' else None, applied=True,
                read_allowed=True, scope_verified=True,
                actor_scope='anonymous_read' if local else 'authenticated',
                global_all_granted=mode == 'GLOBAL_ALL' and not local)


def record(**changes):
    row = dict(canonical_id='CAN-A', product_id='CTH', domain_id='cth',
               subject_id='SUBJ-A', brand_focus_id='', scope_status='VERIFIED',
               source_id='SOURCE-A', publish_datetime=date.today().isoformat(),
               captured_at=date.today().isoformat() + 'T12:00:00Z', sentiment='positive',
               risk_level='low', quality_status='ok', scope_evidence={'id': 1})
    row.update(changes)
    return row


@pytest.fixture
def route(monkeypatch):
    @contextmanager
    def connection(*, read_only):
        assert read_only is True
        yield object()
    monkeypatch.setattr(shared_database, 'get_repository', lambda: SimpleNamespace(connection=connection))
    monkeypatch.setattr(runtime, '_all_builders', lambda: screens.SCREEN_BUILDERS)
    app = Flask(__name__)
    app.register_blueprint(runtime.experience_bp)
    return app.test_client()


def install_rows(monkeypatch, rows):
    def read(connection, **kwargs):
        assert kwargs['product_id'] == 'CTH'
        return dict(records=rows, candidate_count=len(rows), scanned_count=len(rows),
                    rejected_count=0, returned_count=len(rows), limit=100, truncated=False)
    monkeypatch.setattr(canonical_data, 'list_scoped_canonical', read)


@pytest.mark.parametrize('screen', ['CTH-05', 'CTH-07'])
@pytest.mark.parametrize('mode,local', [('FOCUS', False), ('GLOBAL_ALL', False), ('GLOBAL_ALL', True)])
def test_temporal_screen_preserves_scope_missing_days_and_genuine_zero(route, monkeypatch, screen, mode, local):
    current = binding(mode, local)
    calls = []
    monkeypatch.setattr(runtime, '_cth03_read_scope', lambda: (calls.append(1) or current, None))
    install_rows(monkeypatch, [record()])
    response = route.get('/api/experience/screen/' + screen)
    assert response.status_code == 200
    body = response.get_json()
    temporal = body['temporal_metrics']
    assert temporal['binding'] == current
    assert len(calls) == 3  # Route, before read, after read.
    assert temporal['days'][-1]['total']['value'] == 1
    assert temporal['days'][-1]['negative']['value'] == 0
    assert temporal['days'][0]['total']['value'] is None
    chart = next(row for row in body['sections'] if row['type'] == 'chart')
    assert len(chart['labels']) == 14
    assert chart['series'][0]['data'][0] is None
    assert 'projection' not in chart  # No fabricated aggregate Evidence.
    assert len(temporal['snapshot_sha256']) == 64
    assert body['trend_metadata']['subject'] == ('GLOBAL/ALL' if mode == 'GLOBAL_ALL' else 'SUBJ-A')


@pytest.mark.parametrize('screen', ['CTH-05', 'CTH-07'])
def test_temporal_screen_retains_unknown_native_time_and_labels(route, monkeypatch, screen):
    monkeypatch.setattr(runtime, '_cth03_read_scope', lambda: (binding(), None))
    install_rows(monkeypatch, [record(publish_datetime=None, sentiment=None, risk_level=None)])
    body = route.get('/api/experience/screen/' + screen).get_json()
    result = body['temporal_metrics']
    assert result['state'] == 'partial'
    assert result['unknown_publication_count'] == 1
    assert all(day['total']['value'] is None for day in result['days'])
    assert result['totals']['negative']['value'] is None


@pytest.mark.parametrize('screen', ['CTH-05', 'CTH-07'])
def test_temporal_dependency_failure_is_error_not_zero(route, monkeypatch, screen):
    monkeypatch.setattr(runtime, '_cth03_read_scope', lambda: (binding(), None))
    def fail(*args, **kwargs):
        raise OSError('private storage detail')
    monkeypatch.setattr(canonical_data, 'list_scoped_canonical', fail)
    response = route.get('/api/experience/screen/' + screen)
    body = response.get_json()
    assert body['temporal_metrics']['state'] == 'error'
    assert body['temporal_metrics']['totals']['total']['value'] is None
    assert 'private storage detail' not in response.get_data(as_text=True)


@pytest.mark.parametrize('screen', ['CTH-05', 'CTH-07'])
def test_scope_revocation_during_read_returns_no_data(route, monkeypatch, screen):
    calls = []
    def scope():
        calls.append(1)
        if len(calls) == 3:
            return None, ({'code': 'DENIED'}, 403)
        return binding(), None
    monkeypatch.setattr(runtime, '_cth03_read_scope', scope)
    install_rows(monkeypatch, [record()])
    response = route.get('/api/experience/screen/' + screen)
    assert response.status_code == 503
    assert response.get_json()['code'] == 'SCOPED_DATA_UNAVAILABLE'
    assert 'temporal_metrics' not in response.get_json()


@pytest.mark.parametrize('screen', ['CTH-05', 'CTH-07'])
def test_initial_scope_denial_does_not_read(route, monkeypatch, screen):
    monkeypatch.setattr(runtime, '_cth03_read_scope', lambda: (None, ({'code': 'DENIED'}, 403)))
    monkeypatch.setattr(canonical_data, 'list_scoped_canonical', lambda *a, **k: pytest.fail('unauthorized read'))
    assert route.get('/api/experience/screen/' + screen).status_code == 403
