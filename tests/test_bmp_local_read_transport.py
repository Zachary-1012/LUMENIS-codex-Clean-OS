"""Overview transport projection never substitutes for a Permission principal."""
import json
import pytest
from tests.test_bmp03_platform_consumption import scoped, client, workspace

SCREENS = ('BMP-03', 'BMP-04', 'BMP-09', 'BMP-10')

@pytest.fixture
def ready(scoped):
    import database
    from lumenis.shared.database import migrations
    database.init_db()
    migrations.migrate()
    return scoped


def binding(body):
    return body.get('observation_read_binding') or body.get('source_read_binding') or body.get('report_screen_binding') or body.get('focus_binding') or body['global_binding']


@pytest.mark.parametrize('screen', SCREENS)
@pytest.mark.parametrize('focus', [False, True])
def test_local_projection_from_original_guard(ready, screen, focus):
    http, ws, a, b, h, two, eid = ready
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = True
    headers = {k: v for k, v in h.items() if k != 'Authorization'} if focus else {}
    response = http.get('/api/experience/screen/' + screen, headers=headers)
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    scope = binding(body)
    assert scope['read_transport'] == {
        'contract': 'lumenis.local-read-transport.v1',
        'module': 'brand_market_overview', 'action': 'read', 'verified': True,
    }
    assert scope['policy'] == 'local-workspace-read-v1'
    assert scope['actor_scope'] == 'anonymous_read'
    assert scope['global_all_granted'] is False
    assert scope.get('actor_id') is None
    assert 'principal_kind' not in scope and 'principal_ref' not in scope
    if screen == 'BMP-09':
        report = body['report_authorization']
        assert report['module'] == 'reports' and report['action'] == 'read'
        assert report['context']['principal_kind'] == 'local_workspace'
        assert report['context']['principal_ref'] == 'workspace:local'
        assert 'actor_id' not in report['context']


@pytest.mark.parametrize('screen', SCREENS)
def test_account_projection_does_not_gain_local_transport(ready, screen):
    http, ws, a, b, h, two, eid = ready
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = True
    ws['repo'].execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'ZBMP','reports','read',?)", (json.dumps({'brand_focus_ids': [a['brand_focus_id']]}),))
    response = http.get('/api/experience/screen/' + screen, headers=h)
    assert response.status_code == 200, response.get_json()
    scope = binding(response.get_json())
    assert scope['policy'] == 'actor-exact-scope-v1'
    assert scope['actor_scope'] == 'authenticated'
    assert 'read_transport' not in scope


@pytest.mark.parametrize('screen', SCREENS)
@pytest.mark.parametrize('headers', [
    {'Host': 'hostile.invalid'}, {'Origin': 'https://hostile.invalid'},
    {'Forwarded': 'for=127.0.0.1'}, {'X-Forwarded-For': '127.0.0.1'},
    {'Authorization': 'Bearer invalid'}, {'Cookie': 'cth_poms_v4_session='},
])
def test_untrusted_transport_cannot_emit_local_descriptor(ready, screen, headers):
    http, ws, *_ = ready
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = True
    response = ws['app'].test_client(use_cookies=False).get('/api/experience/screen/' + screen, headers=headers)
    assert response.status_code >= 400
    assert 'read_transport' not in json.dumps(response.get_json())


@pytest.mark.parametrize('screen', SCREENS)
def test_client_labels_do_not_open_closed_workspace(ready, screen):
    http, ws, *_ = ready
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    headers = {'X-Lumenis-Read-Transport': 'lumenis.local-read-transport.v1',
               'X-Principal-Ref': 'workspace:local', 'X-Actor-ID': '1'}
    response = ws['app'].test_client(use_cookies=False).get('/api/experience/screen/' + screen, headers=headers)
    assert response.status_code >= 400
    assert 'read_transport' not in json.dumps(response.get_json())


@pytest.mark.parametrize('screen', SCREENS)
def test_workspace_closure_during_read_does_not_release_payload(ready, screen, monkeypatch):
    http, ws, *_ = ready
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = True
    import experience_runtime
    original_lookup = experience_runtime._all_builders
    def lookup():
        builders = original_lookup()
        original = builders[screen]
        def close(**kwargs):
            result = original(**kwargs)
            ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
            return result
        return {**builders, screen: close}
    monkeypatch.setattr(experience_runtime, '_all_builders', lookup)
    response = http.get('/api/experience/screen/' + screen)
    assert response.status_code >= 400
    assert 'source-a' not in response.get_data(as_text=True)
    assert 'read_transport' not in response.get_data(as_text=True)
