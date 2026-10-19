"""A rejected signature is not a clean empty source collection."""
import pytest
from tests.test_bmp03_platform_consumption import scoped,client,workspace

@pytest.fixture
def ready(scoped):
    import database
    from lumenis.shared.database import migrations
    database.init_db();migrations.migrate()
    return scoped

def read(ready):
    http,ws,a,b,h,two,eid=ready
    result=http.get('/api/experience/screen/BMP-04',headers=h)
    assert result.status_code==200,result.get_json()
    return result.get_json()

def test_bmp04_signature_rejection_is_partial_not_zero(ready):
    http,ws,a,b,h,two,eid=ready
    assert read(ready)['truth']['source_count']==1
    ws['repo'].execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",(eid,))
    body=read(ready);truth=body['truth']
    assert truth['source_count'] is None and truth['observed_source_count']==0
    assert truth['source_read_complete'] is False and truth['rejected_source_count']==1
    assert truth['data_state']=='PARTIAL'
    metric=next(m for s in body['sections'] if s['type']=='kpis' for m in s['items'] if m['id']=='bmp04.total')
    assert metric['value'] is None and metric['state']=='partial'
    assert truth['heat'] is None and truth['reach'] is None

def test_bmp04_legal_empty_table_remains_empty_zero(ready):
    http,ws,a,b,h,two,eid=ready
    ws['repo'].execute('DELETE FROM canonical_data WHERE brand_focus_id=?',(a['brand_focus_id'],))
    truth=read(ready)['truth']
    assert truth['source_count']==0 and truth['source_read_complete'] is True
    assert truth['rejected_source_count']==0 and truth['data_state']=='EMPTY'

def test_bmp04_source_limit_is_partial_with_observations(ready,monkeypatch):
    import kos_engine
    original=kos_engine._read_scoped_canonical_material
    def limited(binding):
        actual=original(binding)
        return {**actual,'truncated':True}
    monkeypatch.setattr(kos_engine,'_read_scoped_canonical_material',limited)
    truth=read(ready)['truth']
    assert truth['source_count'] is None and truth['observed_source_count']==1
    assert truth['truncated'] is True and truth['data_state']=='PARTIAL'


def test_bmp04_observation_contract_has_real_actor_source_proof_and_no_performance(ready):
    http,ws,a,b,h,two,eid=ready
    body=read(ready)
    assert body['observation_contract']=='lumenis.bmp04-source-observations.v1'
    assert body['observation_read_binding']['actor_id']==body['observation_context']['actor_id']==1
    row=body['source_observations'][0]
    assert row['scope_evidence']['id']==eid
    assert row['scope_evidence']['stored_scope']['brand_focus_id']==a['brand_focus_id']
    assert row['scope_evidence']['integrity']['verified'] is True
    assert body['truth']['analysis_state']=='NOT_COMPUTED'
    assert body['truth']['heat'] is None and body['truth']['reach'] is None


def test_bmp04_revocation_after_owner_read_cannot_return_observations(ready,monkeypatch):
    import brand_propagation
    http,ws,a,b,h,two,eid=ready
    original=brand_propagation.read_scoped_propagation
    def revoke(binding):
        result=original(binding)
        ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        return result
    monkeypatch.setattr(brand_propagation,'read_scoped_propagation',revoke)
    response=http.get('/api/experience/screen/BMP-04',headers=h)
    assert response.status_code>=400
    assert 'source_observations' not in response.get_json() and 'sections' not in response.get_json()
