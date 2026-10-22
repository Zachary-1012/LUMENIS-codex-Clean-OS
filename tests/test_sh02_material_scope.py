import sqlite3
from types import SimpleNamespace

import pytest
from flask import Flask

import experience_runtime as runtime
import experience_screens as screens
from tests.test_canonical_scope_read import _persist_verified, scope_db  # noqa: F401


@pytest.fixture
def library(request, monkeypatch):
    db_path = request.getfixturevalue("scope_db")
    import lumenis.auth.service as auth
    from lumenis.system.security import permission

    state = {'allowed': True, 'actor': 7}
    monkeypatch.setattr(auth, 'get_current_user', lambda **kw: {'id': state['actor']})
    monkeypatch.setattr(permission, 'check_actor_scope_permission', lambda *a, **kw:
        SimpleNamespace(allowed=state['allowed'], verification_state='verified'))
    monkeypatch.setattr(runtime, '_all_builders', lambda: {'SH-02': screens._build_sh02})
    with sqlite3.connect(db_path) as con:
        _persist_verified(con, 'cth-source', product='CTH', domain='cth', subject='SUBJ-A')
        _, state['evidence_id'] = _persist_verified(
            con, 'brand-source', product='ZBMP', domain='zbmp', brand='BRAND-A')
    app = Flask(__name__)
    app.register_blueprint(runtime.experience_bp)
    return app.test_client(), state, db_path


def test_shared_materials_use_verified_canonical_rows_across_domains(library):
    client, _, _ = library
    response = client.get('/api/experience/screen/SH-02')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    value = response.get_json()
    assert value['permission']['read'] is True
    rows = value['data']['evidence']
    assert {row['summary'] for row in rows} == {'cth-source', 'brand-source'}
    assert all(row['published_at'] is None and row['freshness'] == 'UNKNOWN' for row in rows)
    assert all(row['projection']['integrity']['verified'] for row in rows)
    assert all(row['projection']['scope']['global_all_granted'] for row in rows)
    assert {row['projection']['stored_scope']['domain_id'] for row in rows} == {'cth', 'zbmp'}


def test_tampered_source_is_not_rendered_and_incompleteness_is_explicit(library):
    client, state, path = library
    with sqlite3.connect(path) as con:
        con.execute('UPDATE app_evidence_records SET outputs_json=? WHERE id=?',
                    ('{"tampered":true}', state['evidence_id']))
    value = client.get('/api/experience/screen/SH-02').get_json()
    assert [row['summary'] for row in value['data']['evidence']] == ['cth-source']
    assert value['data']['partial'] is True


def test_denial_and_mid_read_revocation_never_return_material(library, monkeypatch):
    client, state, _ = library
    state['allowed'] = False
    response = client.get('/api/experience/screen/SH-02')
    assert response.status_code == 403 and 'data' not in response.get_json()
    state['allowed'] = True
    original = screens._build_sh02

    def revoke(**kw):
        value = original(**kw)
        state['actor'] = 8
        return value

    monkeypatch.setattr(runtime, '_all_builders', lambda: {'SH-02': revoke})
    response = client.get('/api/experience/screen/SH-02')
    assert response.status_code == 403 and 'data' not in response.get_json()


def test_missing_storage_is_unavailable_not_empty_and_recovers(library, monkeypatch):
    client, _, _ = library
    import canonical_data
    original = canonical_data.list_scoped_canonical

    def fail(*a, **kw):
        raise sqlite3.OperationalError('private-path-detail')

    monkeypatch.setattr(canonical_data, 'list_scoped_canonical', fail)
    response = client.get('/api/experience/screen/SH-02')
    assert response.status_code == 503 and 'data' not in response.get_json()
    assert 'private-path-detail' not in response.get_data(as_text=True)
    monkeypatch.setattr(canonical_data, 'list_scoped_canonical', original)
    assert len(client.get('/api/experience/screen/SH-02').get_json()['data']['evidence']) == 2
