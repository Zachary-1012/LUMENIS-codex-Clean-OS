"""Scoped inference preserves main's heuristics without broad graph mutation."""
import json
import pytest
from tests.test_saved_document_workflow import workspace


def write(ws, command, payload, rid, scope=None):
    import event_graph as graph
    args = dict(actor=ws['actor'], scope=scope or ws['scope'], request_id=rid)
    preview = graph.prepare_scoped_graph_command(command, payload, **args)
    ws['gate'].grant_approval('db_write', resource=preview['resource'], granted_by='synthetic-review')
    return graph.write_scoped_graph_command(command, payload, resource=preview['resource'], **args)


def pair(ws, title_a='orchid', title_b='orchid', time_b='2026-01-04', scope=None, prefix='parity'):
    ids = []
    for i, (title, date) in enumerate([(title_a, '2026-01-01'), (title_b, time_b)]):
        result = write(ws, 'create', {'event_type':'marketing_event', 'title':title,
            'event_time':date}, f'{prefix}-node-{i}', scope=scope)
        ids.append(result['output'][0])
    return ids


@pytest.mark.parametrize('title_a,title_b,time_b,payload,expected', [
    ('orchid','orchid','2026-01-04',{},'follow'),
    ('orchid violet jasmine','orchid violet jasmine','2026-01-04',{},'derive'),
    ('orchid','orchid','2026-01-02',{},'parallel'),
    ('orchid','orchid','2026-01-01',{},'parallel'),
    ('orchid','orchid','2026-01-02',{'parallel_hours':12},'follow'),
    ('orchid','orchid','2026-01-02',{'parallel_hours':24.5},'parallel'),
    ('orchid','violet','2026-01-02',{},None),
    ('orchid','orchid','2026-02-02',{},None),
    ('orchid','orchid','not-a-date',{},None),
])
def test_main_inference_semantics(workspace,title_a,title_b,time_b,payload,expected):
    import event_graph as graph
    pair(workspace,title_a,title_b,time_b)
    result = write(workspace,'infer',payload,'parity-infer-001')
    assert [r['type'] for r in result['output']] == ([] if expected is None else [expected])
    rows = graph.read_scoped_graph(actor=workspace['actor'],scope=workspace['scope'])['relations']
    for row in rows:
        assert row['evidence']['claim_type']=='automatic_inference'
        assert row['evidence']['causality_verified'] is False
        assert row['relation_type'] != 'trigger'


def test_recompute_new_request_keeps_manual_and_other_scope(workspace):
    import event_graph as graph
    ws=workspace
    a,b=pair(ws)
    other={**ws['scope'],'domain_id':'zbmp'}
    pair(ws,scope=other,prefix='other-scope')
    write(ws,'infer',{},'other-infer-001',scope=other)
    other_before=graph.read_scoped_graph(actor=ws['actor'],scope=other)
    write(ws,'relation',{'source_event_id':a,'target_event_id':b,'relation_type':'trigger',
        'evidence':'Manual hypothesis'},'manual-trigger-001')
    write(ws,'infer',{},'repeat-infer-001')
    write(ws,'infer',{},'repeat-infer-002')
    rows=graph.read_scoped_graph(actor=ws['actor'],scope=ws['scope'])['relations']
    assert sorted(r['relation_type'] for r in rows)==['follow','trigger']
    assert next(r for r in rows if r['relation_type']=='follow')['evidence']['request_id']=='repeat-infer-002'
    assert next(r for r in rows if r['relation_type']=='trigger')['evidence']['request_id']=='manual-trigger-001'
    assert graph.read_scoped_graph(actor=ws['actor'],scope=other)==other_before
    write(ws,'infer',{'days_window':1},'repeat-infer-003')
    assert [r['relation_type'] for r in graph.read_scoped_graph(actor=ws['actor'],scope=ws['scope'])['relations']]==['trigger']


def test_preview_pins_relations_and_manual_same_kind_survives(workspace):
    import event_graph as graph
    ws=workspace
    a,b=pair(ws)
    args=dict(actor=ws['actor'],scope=ws['scope'],request_id='preview-infer-001')
    preview=graph.prepare_scoped_graph_command('infer',{},**args)
    write(ws,'relation',{'source_event_id':a,'target_event_id':b,'relation_type':'follow',
        'evidence':'Manual statement'},'manual-follow-001')
    ws['gate'].grant_approval('db_write',resource=preview['resource'],granted_by='synthetic-review')
    with pytest.raises(PermissionError,match='GRAPH_PREVIEW_CHANGED'):
        graph.write_scoped_graph_command('infer',{},resource=preview['resource'],**args)
    write(ws,'infer',{},'preserve-manual-001')
    rows=graph.read_scoped_graph(actor=ws['actor'],scope=ws['scope'])['relations']
    assert len(rows)==1 and rows[0]['evidence']['claim_type']=='user_statement'


@pytest.mark.parametrize('value',[True,False,'invalid',None,float('inf'),float('nan'),'Infinity','NaN'])
def test_parallel_hours_strict(workspace,value):
    import event_graph as graph
    with pytest.raises(ValueError):
        graph.prepare_scoped_graph_command('infer',{'parallel_hours':value},actor=workspace['actor'],
            scope=workspace['scope'],request_id='invalid-hours-001')


def test_rebuild_rollback_on_final_authority_revocation(workspace,monkeypatch):
    import event_graph as graph
    from lumenis.shared.reporting import saved_work
    ws=workspace
    pair(ws)
    write(ws,'infer',{},'rollback-original-001')
    before=graph.read_scoped_graph(actor=ws['actor'],scope=ws['scope'])
    original=saved_work._check_effect
    calls=[]
    def check(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:
            raise PermissionError('SYNTHETIC_FINAL_REVOCATION')
        return original(*args,**kwargs)
    monkeypatch.setattr(saved_work,'_check_effect',check)
    with pytest.raises(PermissionError,match='SYNTHETIC_FINAL_REVOCATION'):
        write(ws,'infer',{'days_window':1},'rollback-rebuild-001')
    assert graph.read_scoped_graph(actor=ws['actor'],scope=ws['scope'])==before


def test_description_overlap_is_not_title_evidence(workspace):
    import event_graph as graph
    ws=workspace
    for i,title in enumerate(['orchid','violet']):
        write(ws,'create',{'event_type':'marketing_event','title':title,
            'description':'common repeated boilerplate','event_time':f'2026-01-0{i+1}'},f'description-node-{i}')
    result=write(ws,'infer',{},'description-infer-001')
    assert result['output']==[]
    assert graph.read_scoped_graph(actor=ws['actor'],scope=ws['scope'])['relations']==[]


def test_rebuild_does_not_clean_unverified_legacy_rows(workspace):
    import event_graph as graph
    ws=workspace
    a,b=pair(ws)
    with ws['repo'].transaction() as con:
        con.execute('INSERT INTO event_graph_relations(source_event_id,target_event_id,relation_type,evidence,confidence,created_at) VALUES(?,?,?,?,?,?)',
            (a,b,'parallel','[auto] legacy unscoped',0.5,'2026-01-01'))
    result=write(ws,'infer',{},'legacy-preserve-001')
    assert result['result']['dropped_auto']==0
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute("SELECT evidence FROM event_graph_relations WHERE relation_type='parallel'").fetchone()[0]=='[auto] legacy unscoped'
    assert graph.read_scoped_graph(actor=ws['actor'],scope=ws['scope'])['rejected']==1


@pytest.mark.parametrize('payload,time_b,expected', [
    ({'days_window':800,'parallel_hours':0},'2028-01-01','follow'),
    ({'days_window':'800','parallel_hours':'0'},'2028-01-01','follow'),
    ({'days_window':'  +800  ','parallel_hours':'36.5'},'2028-01-01','follow'),
    ({'days_window':-1,'parallel_hours':-1},'2026-01-01',None),
    ({'days_window':0,'parallel_hours':36},'2026-01-02','parallel'),
    ({'days_window':3.9,'parallel_hours':-1},'2026-01-04','follow'),
])
def test_legacy_numeric_windows_no_arbitrary_year_cap(workspace,payload,time_b,expected):
    pair(workspace,time_b=time_b)
    result=write(workspace,'infer',payload,'legacy-window-001')
    assert [r['type'] for r in result['output']]==([] if expected is None else [expected])


@pytest.mark.parametrize('value',[True,False,'3.5','invalid',None,float('inf'),float('nan')])
def test_invalid_day_window(workspace,value):
    import event_graph as graph
    with pytest.raises(ValueError):
        graph.prepare_scoped_graph_command('infer',{'days_window':value},actor=workspace['actor'],
            scope=workspace['scope'],request_id='invalid-days-001')
