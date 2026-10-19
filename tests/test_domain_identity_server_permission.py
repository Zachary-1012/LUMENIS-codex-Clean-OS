import json
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_independent_growth_real_app import real_app

GLOBAL = {'X-Domain-Id':'zbmp','X-Product-Id':'BMP','X-Lumenis-Context-Mode':'GLOBAL_ALL'}
FOCUS = {**GLOBAL,'X-Lumenis-Context-Mode':'FOCUS','X-Brand-Focus-ID':'BRAND-ENTRY-A'}

def headers(actor=201, scope=GLOBAL):
    return {**scope,'Authorization':f'Bearer synthetic-session-{actor}'}

@pytest.fixture
def setup(real_app):
    import subject_registry
    from account.models import AUTHORIZATION_TABLES_SQL
    ws=real_app
    with ws['repo'].transaction() as con:
        subject_registry.ensure_schema(con)
        con.executescript(AUTHORIZATION_TABLES_SQL)
        con.execute("INSERT INTO lumenis_subject_registry(subject_id,brand_focus_id,domain_id,subject_type,name_en,name_zh,name_en_norm,name_zh_norm,industry,keywords_json,status,created_at,updated_at) VALUES('SUBJ-ENTRY-A','BRAND-ENTRY-A','BMP','brand','Entry Brand','测试品牌','entry brand','测试品牌','retail','[]','configured','2026-10-18','2026-10-18')")
        con.execute("UPDATE v4_users SET role='user' WHERE id=202")
    return ws

@pytest.mark.parametrize('path', ['/api/auth/zbmp-entry/status','/api/auth/domain-identity'])
def test_current_owner_scope_and_forged_cookie(setup,path):
    api=setup['api'];api.set_cookie('zbmp_domain_grant','1')
    assert api.get(path,headers=GLOBAL).status_code in (401,403)
    assert api.get(path,headers=headers(202)).status_code==403
    for scope in (GLOBAL,FOCUS):
        r=api.get(path,headers=headers(scope=scope));assert r.status_code==200,r.get_json()
        body=r.get_json();assert body['grant_created'] is False
        assert body['authorization_basis']=='CURRENT_SERVER_SCOPE_PERMISSION'
        assert body['scope']['brand_focus_id']==scope.get('X-Brand-Focus-ID')
    assert api.get(path,headers=headers(scope={**FOCUS,'X-Brand-Focus-ID':'MISSING'})).status_code==400

@pytest.mark.parametrize('path',['/api/auth/zbmp-entry/unlock','/api/auth/zbmp-entry/verify'])
def test_legacy_credential_does_not_grant_authority(setup,path):
    api=setup['api'];api.set_cookie('zbmp_domain_grant','1')
    for body in ({'key':'synthetic-no-authority'},{'code':'000000'},{}):
        assert api.post(path,headers=headers(202),json=body).status_code==403
        r=api.post(path,headers=headers(),json=body)
        assert r.status_code==200,r.get_json()
        assert r.get_json()['grant_created'] is False
        assert 'zbmp_domain_grant=;' in r.headers['Set-Cookie']
    assert api.post(path,headers=GLOBAL,json={}).status_code in (401,403)


def test_member_exact_scope_revocation_and_canonical_deletion(setup):
    ws=setup;api=ws['api']
    with ws['repo'].transaction() as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(202,'ZBMP','reports','read',?)",(json.dumps({'brand_focus_ids':['BRAND-ENTRY-A']}),))
    assert api.get('/api/auth/domain-identity',headers=headers(202,FOCUS)).status_code==200
    assert api.get('/api/auth/domain-identity',headers=headers(202,GLOBAL)).status_code==403
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM v4_member_authorizations WHERE user_id=202')
    assert api.get('/api/auth/domain-identity',headers=headers(202,FOCUS)).status_code==403
    with ws['repo'].transaction() as con:
        con.execute("DELETE FROM lumenis_subject_registry WHERE subject_id='SUBJ-ENTRY-A'")
    assert api.get('/api/auth/domain-identity',headers=headers(201,FOCUS)).status_code==400


@pytest.mark.parametrize('change',['session','inactive','role'])
def test_current_session_and_permission_not_cookie(setup,change):
    ws=setup;api=ws['api'];api.set_cookie('zbmp_domain_grant','1')
    assert api.get('/api/auth/zbmp-entry/status',headers=headers()).status_code==200
    with ws['repo'].transaction() as con:
        if change=='session':con.execute('DELETE FROM v4_sessions WHERE user_id=201')
        elif change=='inactive':con.execute("UPDATE v4_users SET status='inactive' WHERE id=201")
        else:con.execute("UPDATE v4_users SET role='user' WHERE id=201")
    assert api.get('/api/auth/zbmp-entry/status',headers=headers()).status_code in (401,403)


def test_context_required_and_leave_is_navigation_only(setup):
    api=setup['api']
    assert api.get('/api/auth/zbmp-entry/status',headers=headers(scope={})).status_code==400
    assert api.get('/api/auth/zbmp-entry/status',headers=headers(scope={**GLOBAL,'X-Product-Id':'CTH'})).status_code==400
    r=api.post('/api/auth/zbmp-entry/leave',headers=headers(),json={})
    assert r.status_code==200 and r.get_json()['permissions_changed'] is False
    assert api.get('/api/auth/zbmp-entry/status',headers=headers()).status_code==200


def test_get_does_not_modify_accounts_sessions_or_grants(setup):
    ws=setup
    def rows():
        with ws['repo'].connection(read_only=True,wal=False) as con:
            return {name:[tuple(r) for r in con.execute('SELECT * FROM '+name)] for name in ('v4_users','v4_sessions','v4_member_authorizations','lumenis_subject_registry')}
    before=rows()
    for actor in (201,202):
        ws['api'].get('/api/auth/zbmp-entry/status',headers=headers(actor))
        ws['api'].get('/api/auth/domain-identity',headers=headers(actor,FOCUS))
    assert rows()==before


def test_session_expiry_read_does_not_delete_session(setup):
    ws=setup
    with ws['repo'].transaction() as con:
        con.execute("UPDATE v4_sessions SET expires_at='2000-01-01 00:00:00' WHERE user_id=201")
    assert ws['api'].get('/api/auth/zbmp-entry/status',headers=headers()).status_code==401
    with ws['repo'].connection(read_only=True,wal=False) as con:
        assert con.execute('SELECT count(*) FROM v4_sessions WHERE user_id=201').fetchone()[0]==1
