"""Signed-source scope and useful nonempty CTH screen projections."""
import sqlite3

import pytest
from flask import Flask

from tests.test_scoped_source_brief import brief_db, _add_signed
import experience_runtime as runtime
import experience_screens as screens


def binding(mode='FOCUS'):
    return dict(contract='lumenis.scope-read-binding.v1', module='commercial_realtime_stream',
                policy='actor-exact-scope-v1', domain_id='CTH', product_id='CTH',
                canonical_scope=mode, subject_id='SUBJECT-A' if mode == 'FOCUS' else None,
                applied=True, read_allowed=True, scope_verified=True,
                actor_scope='authenticated', global_all_granted=mode == 'GLOBAL_ALL')


@pytest.fixture
def scoped_client(brief_db, monkeypatch):
    with sqlite3.connect(brief_db) as connection:
        _add_signed(connection, 'source-a', subject='SUBJECT-A', title='Permitted source A')
        _add_signed(connection, 'source-b', subject='SUBJECT-B', title='OTHER SUBJECT PRIVATE')
        connection.execute("UPDATE canonical_data SET sentiment='negative' WHERE source_id='source-a'")
        connection.commit()
    monkeypatch.setattr(runtime, '_all_builders', lambda: screens.SCREEN_BUILDERS)
    monkeypatch.setattr(runtime, '_cth03_read_scope', lambda: (binding(), None))
    app = Flask(__name__)
    app.register_blueprint(runtime.experience_bp)
    return app.test_client()


@pytest.mark.parametrize('sid', ['CTH-06', 'CTH-09', 'CTH-10'])
def test_exact_source_screen_returns_useful_authorized_rows(scoped_client, sid):
    response = scoped_client.get('/api/experience/screen/' + sid)
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert 'Permitted source A' in response.get_data(as_text=True)
    assert 'OTHER SUBJECT PRIVATE' not in response.get_data(as_text=True)
    assert body['binding']['subject_id'] == 'SUBJECT-A'
    assert body['binding']['read_allowed'] is True
    assert body['binding']['evidence_lineage'] == 'verified'
    if sid == 'CTH-10':
        assert body['truth']['persisted'] is False
        assert body['source_brief']['records'][0]['source_id'] == 'source-a'
    if sid == 'CTH-09':
        assert body['sections'][1]['items'][0]['evidence'][0]['canonical_ref'].startswith('evidence:canonical:')
        assert 'NOTE:' not in response.get_data(as_text=True)


@pytest.mark.parametrize('sid', ['CTH-06', 'CTH-09', 'CTH-10'])
def test_scope_denial_never_reads(scoped_client, monkeypatch, sid):
    monkeypatch.setattr(runtime, '_cth03_read_scope', lambda: (None, ({'code': 'DENIED'}, 403)))
    monkeypatch.setattr(screens, '_cth_source_material', lambda *a, **k: pytest.fail('unauthorized source read'))
    assert scoped_client.get('/api/experience/screen/' + sid).status_code == 403


@pytest.mark.parametrize('sid', ['CTH-06', 'CTH-09', 'CTH-10'])
def test_scope_change_discards_completed_projection(scoped_client, monkeypatch, sid):
    calls = []
    def authorize():
        calls.append(True)
        current = binding()
        if len(calls) > 1:
            current['subject_id'] = 'SUBJECT-B'
        return current, None
    monkeypatch.setattr(runtime, '_cth03_read_scope', authorize)
    response = scoped_client.get('/api/experience/screen/' + sid)
    assert response.status_code == 503
    assert 'Permitted source A' not in response.get_data(as_text=True)


def test_unknown_risk_never_becomes_zero_or_low(scoped_client, brief_db):
    with sqlite3.connect(brief_db) as connection:
        connection.execute("UPDATE canonical_data SET risk_level=NULL WHERE source_id='source-a'")
        connection.commit()
    body = scoped_client.get('/api/experience/screen/CTH-09').get_json()
    assert body['truth']['unknown_risk_count'] == 1
    assert body['sections'][1]['state'] == 'partial'
    assert body['sections'][1]['items'] == []
