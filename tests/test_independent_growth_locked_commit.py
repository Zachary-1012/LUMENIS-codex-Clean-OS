import sqlite3
import pytest
from tests.test_growth_business_review import outcome, feedback
from tests.test_business_decision_workflow import work, step, workspace


def test_other_writer_cannot_change_source_during_evaluation_commit(work):
    service,inputs,db=work
    current=outcome(service,inputs)
    source_id=inputs['options'][0]['source_ids'][0]
    original=inputs['authorize'];blocked=[];calls=[]
    def boundary(operation):
        result=original(operation)
        if operation=='evaluate':
            calls.append(operation)
        if operation=='evaluate' and len(calls)>1:
            with sqlite3.connect(db,timeout=.01) as con:
                with pytest.raises(sqlite3.OperationalError,match='locked'):
                    con.execute("UPDATE canonical_data SET content='Concurrent change' WHERE source_id=?",(source_id,))
                blocked.append(True)
        return result
    reviewed=step(service,{**inputs,'authorize':boundary},current,'review',feedback(source_id),'independent-locked-01')
    assert blocked and reviewed['evaluation']['state']=='RECORDED'
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT content FROM canonical_data WHERE source_id=?',(source_id,)).fetchone()[0]!='Concurrent change'
        con.execute("UPDATE canonical_data SET content='Changed after commit' WHERE source_id=?",(source_id,))
    with pytest.raises((ValueError,PermissionError,RuntimeError)):
        service.reopen(current['work_id'],actor_ref=inputs['actor_ref'],scope=inputs['scope'],authorize=original)


def test_same_transaction_source_mutation_rolls_back_evaluation(work,monkeypatch):
    from lumenis.shared.evaluation import recorder
    service,inputs,db=work
    current=outcome(service,inputs)
    source_id=inputs['options'][0]['source_ids'][0]
    with sqlite3.connect(db) as con:
        before=con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]
    original=recorder.record_evaluation
    def mutate(**kwargs):
        con=kwargs['connection']
        con.execute("UPDATE canonical_data SET content='Invalidated inside commit' WHERE source_id=?",(source_id,))
        return original(**kwargs)
    monkeypatch.setattr(recorder,'record_evaluation',mutate)
    with pytest.raises((ValueError,PermissionError,RuntimeError)):
        step(service,inputs,current,'review',feedback(source_id),'independent-inner-race-01')
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]==before
        assert con.execute('SELECT content FROM canonical_data WHERE source_id=?',(source_id,)).fetchone()[0]!='Invalidated inside commit'
