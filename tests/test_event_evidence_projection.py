"""Event IDs never stand in for Shared Evidence IDs."""
import pytest
from experience_screens import _events_items

def test_event_projection_uses_real_evidence_identity():
    row=_events_items([{'id':1,'scope_evidence_ref':'27','title':'Source-backed event'}])[0]
    assert row['event_id']==1 and row['evidence']=='EV-27' and row['evidence_ref']=='EV-27'
    assert row['evidence_state']=='REFERENCED'

@pytest.mark.parametrize('value',[None,'',0,-1,True,' 2','EV-2','unknown'])
def test_missing_or_invalid_evidence_never_synthesized(value):
    row=_events_items([{'id':99,'scope_evidence_ref':value}])[0]
    assert row['event_id']==99
    assert row['evidence'] is None and row['evidence_ref'] is None
    assert row['evidence_state']=='UNKNOWN'
