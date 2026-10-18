import pytest
from tests.test_saved_document_workflow import workspace


def test_private_graph_scope_approval_reopen_and_relation_truth(workspace):
    import event_graph as graph
    ws=workspace; actor=ws['actor']; scope=ws['scope']
    def write(command,payload,rid):
        preview=graph.prepare_scoped_graph_command(command,payload,actor=actor,scope=scope,request_id=rid)
        kwargs=dict(actor=actor,scope=scope,request_id=rid,resource=preview['resource'])
        with pytest.raises(ValueError,match='WORK_EFFECT_PERMISSION_DENIED'):
            graph.write_scoped_graph_command(command,payload,**kwargs)
        token=ws['gate'].grant_approval('db_write',resource=preview['resource'],granted_by='synthetic-review')
        return graph.write_scoped_graph_command(command,payload,**kwargs),token
    a,_=write('create',{'event_type':'marketing_event','title':'Synthetic launch campaign','event_time':'2026-01-01'},'graph-source-001')
    b,_=write('create',{'event_type':'propagation_event','title':'Synthetic launch reaction','event_time':'2026-01-02'},'graph-source-002')
    result,token=write('relation',{'source_event_id':a['output'][0],'target_event_id':b['output'][0],
        'relation_type':'trigger','evidence':'User hypothesis only'},'graph-relation-001')
    result=graph.read_scoped_graph(actor=actor,scope=scope)
    assert len(result['events'])==2 and len(result['relations'])==1
    proof=result['relations'][0]['evidence']
    assert proof['claim_type']=='user_statement' and proof['causality_verified'] is False
    assert graph.read_scoped_graph(actor=actor,scope={**scope,'domain_id':'zbmp'})['events']==[]
    graph.reset_event_graph()
    assert graph.read_scoped_graph(actor=actor,scope=scope)['relations']==result['relations']
    inferred,_=write('infer',{'days_window':21},'graph-inference-001')
    assert inferred['output'][0]['claim_type']=='automatic_inference'
    with ws['repo'].transaction() as con:
        con.execute("UPDATE event_graph_events SET title='tampered' WHERE event_id=?",(a['output'][0],))
    final=graph.read_scoped_graph(actor=actor,scope=scope)
    assert len(final['events'])==1 and final['relations']==[] and final['rejected']==1
