"""Event/risk provenance comes from the current signed owner, not view flags."""
from tests.test_event_aggregation_authority import signed_scoped_event_sources
from tests.test_curated_event_completeness import make,read
import database

def test_event_projection_uses_real_evidence_identity_and_scope(signed_scoped_event_sources):
    event=make('SUBJECT-A','proof')
    row=read()['featured'][0];proof=row['scope_evidence']
    assert row['id']==event and proof['id']==int(row['scope_evidence_ref'])
    assert proof['stored_scope']=={'domain_id':'cth','product_id':'CTH','global':False,'subject_id':'SUBJECT-A'}
    assert proof['integrity']['verified'] and proof['integrity']['assurance']=='writer-authenticated'
    assert len(proof['integrity']['digest'])==64
    with signed_scoped_event_sources.transaction() as con:
        con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",(proof['id'],))
    rejected=read()
    assert rejected['featured']==[] and rejected['rejected_count']==1

def test_risk_source_projection_is_current_signed_scope(signed_scoped_event_sources):
    scope={'domain_id':'cth','subject_id':'SUBJECT-A','brand_focus_id':None,'global_scope':False}
    result=database.get_scoped_event_source_rows(scope,source_types=('note',))
    assert result['sources']
    for row in result['sources']:
        proof=row['scope_evidence']
        assert proof['id']==int(row['scope_evidence_ref'])
        assert proof['stored_scope']['subject_id']=='SUBJECT-A'
        assert proof['integrity']['verified'] is True
    with signed_scoped_event_sources.transaction() as con:
        con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",(result['sources'][0]['scope_evidence']['id'],))
    rejected=database.get_scoped_event_source_rows(scope,source_types=('note',))
    assert rejected['rejected_count']>0
    assert all(row['scope_evidence']['id']!=result['sources'][0]['scope_evidence']['id'] for row in rejected['sources'])
