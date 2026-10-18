"""Exact-scope scan metadata never implies an unobserved population total."""
from tests.test_event_aggregation_authority import signed_scoped_event_sources
import database

def make(subject,key,title='Synthetic event'):
    scope=database._normalize_event_scope({'domain_id':'cth','subject_id':subject,'brand_focus_id':None,'global_scope':False})
    source='scope-note-a' if subject=='SUBJECT-A' else 'scope-note-b'
    return database.upsert_event({'event_key':database._event_scope_token(scope)+'.'+key,'title':title},scope=scope,mentions=[{'source_type':'note','source_id':source}])

def read(limit=1):
    return database.get_events_curated(limit,scope={'domain_id':'cth','subject_id':'SUBJECT-A','brand_focus_id':None,'global_scope':False})

def test_limit_boundary_and_other_scope_do_not_change_completeness(signed_scoped_event_sources):
    empty=read();assert empty['read_complete'] and empty['total']==0 and empty['state']=='EMPTY'
    make('SUBJECT-B','private')
    empty=read();assert empty['scanned_count']==0 and empty['read_complete']
    make('SUBJECT-A','one');one=read()
    assert one['scanned_count']==1 and one['returned_count']==1 and one['read_complete']
    make('SUBJECT-A','two');two=read()
    assert two['scanned_count']==1 and two['returned_count']==1
    assert two['truncated'] and not two['read_complete'] and two['state']=='PARTIAL'

def test_rejected_event_is_partial_not_clean_empty(signed_scoped_event_sources):
    event=make('SUBJECT-A','one')
    with signed_scoped_event_sources.transaction() as con:con.execute("UPDATE events SET title='tampered' WHERE id=?",(event,))
    result=read()
    assert result['featured']==[] and result['rejected_count']==1
    assert result['scanned_count']==1 and not result['read_complete'] and result['state']=='PARTIAL'

def test_scan_budget_is_honest_even_when_all_scanned_rows_are_noise(signed_scoped_event_sources):
    for i in range(201):make('SUBJECT-A',str(i),'核查合成资料')
    result=read()
    assert result['scanned_count']==200 and result['noise_count']==200 and result['returned_count']==0
    assert result['truncated'] and not result['read_complete'] and result['state']=='PARTIAL'
    assert result['total_semantics']=='observed_verified_rows_not_population_total'


def test_real_owner_partial_propagates_into_event_section(signed_scoped_event_sources):
    from experience_screens import _event_read_state, _curated
    first=make('SUBJECT-A','one')
    make('SUBJECT-A','two')
    material=read(1)
    state,meta=_event_read_state(material,_curated(material))
    assert state=='partial' and meta['observed_returned_count']==1
    assert 'READ_LIMIT_OR_SCAN_BUDGET' in meta['reasons']
    with signed_scoped_event_sources.transaction() as con:
        con.execute("UPDATE events SET title='tampered'")
    material=read(5)
    state,meta=_event_read_state(material,_curated(material))
    assert state=='partial' and meta['observed_returned_count']==0
    assert 'SOURCE_OR_EVENT_VERIFICATION_REJECTED' in meta['reasons']


def test_legacy_event_metadata_never_implies_completeness():
    from experience_screens import _event_read_state
    state,meta=_event_read_state({'featured':[]},[])
    assert state=='partial' and meta['reasons']==['READ_COMPLETENESS_UNVERIFIED']


def test_complete_seven_events_remain_seven_when_display_is_six(signed_scoped_event_sources):
    from experience_screens import _event_read_state, _curated, _events_items
    for i in range(7):make('SUBJECT-A','seven-'+str(i))
    material=read(10);items=_events_items(_curated(material))
    state,meta=_event_read_state(material,items)
    assert state=='ready' and meta['read_complete'] is True
    assert meta['observed_returned_count']==7 and meta['displayed_count']==6
    assert meta['display_truncated'] is True
