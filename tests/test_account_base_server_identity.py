import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_independent_growth_real_app import real_app

PATH='/api/system/account'
H={'Authorization':'Bearer synthetic-session-201'}

def snapshot(ws):
    with ws['repo'].connection(read_only=True,wal=False) as con:
        return {t:[tuple(r) for r in con.execute('SELECT * FROM '+t)] for t in ('v4_users','v4_sessions')}

def test_current_identity_minimal_and_zero_write(real_app):
    before=snapshot(real_app)
    r=real_app['api'].get(PATH,headers=H)
    assert r.status_code==200
    b=r.get_json();assert b['success'] is True
    assert set(b['data'])=={'id','username','role','display_name'}
    assert b['data']['id']==201
    assert snapshot(real_app)==before

@pytest.mark.parametrize('mode',['anonymous','basic','fake_cookie','forged_actor','unknown_token'])
def test_no_account_identity_never_available(real_app,mode):
    api=real_app['api'];kw={}
    if mode=='basic':kw['auth']=('synthetic-user','synthetic-password')
    if mode=='fake_cookie':api.set_cookie('zbmp_domain_grant','1')
    if mode=='forged_actor':kw['headers']={'X-Actor-ID':'201'}
    if mode=='unknown_token':kw['headers']={'Authorization':'Bearer absent-session'}
    before=snapshot(real_app);r=api.get(PATH,**kw)
    assert r.status_code==401
    assert r.get_json()['success'] is False
    assert r.get_json()['data'] is None
    assert snapshot(real_app)==before

@pytest.mark.parametrize('change',['revoked','inactive','expired'])
def test_identity_freshness_read_only(real_app,change):
    assert real_app['api'].get(PATH,headers=H).status_code==200
    with real_app['repo'].transaction() as con:
        if change=='revoked':con.execute('DELETE FROM v4_sessions WHERE user_id=201')
        elif change=='inactive':con.execute("UPDATE v4_users SET status='inactive' WHERE id=201")
        else:con.execute("UPDATE v4_sessions SET expires_at='2000-01-01 00:00:00' WHERE user_id=201")
    before=snapshot(real_app);r=real_app['api'].get(PATH,headers=H)
    assert r.status_code==401
    assert snapshot(real_app)==before

def test_owner_failure_is_unavailable_without_exception_disclosure(real_app,monkeypatch):
    import lumenis.auth.service as service
    def fail(**kw):
        assert kw=={'read_only':True}
        raise RuntimeError('synthetic-sensitive-error')
    monkeypatch.setattr(service,'get_current_user',fail)
    before=snapshot(real_app);r=real_app['api'].get(PATH,headers=H)
    assert r.status_code==503
    assert r.get_json()['error']=='ACCOUNT_UNAVAILABLE'
    assert r.get_json()['success'] is False
    assert 'synthetic-sensitive-error' not in r.get_data(as_text=True)
    assert snapshot(real_app)==before
