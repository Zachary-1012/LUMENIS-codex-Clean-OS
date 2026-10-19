import sqlite3
import pytest
from tests.test_growth_business_review import outcome, feedback
from tests.test_business_decision_workflow import work, step, workspace
from tests.test_source_brief_job import job_db


def test_source_changed_at_evaluation_boundary_has_no_new_evaluation(work):
    service, inputs, db = work
    current = outcome(service, inputs)
    with sqlite3.connect(db) as con:
        before = con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]
    original = inputs['authorize']
    def boundary(operation):
        result = original(operation)
        if operation == 'evaluate':
            # Deterministic interleaving at the documented side-write boundary.
            # Another writer can commit here because the Evidence transaction ended.
            with sqlite3.connect(db, timeout=1) as con:
                con.execute("UPDATE canonical_data SET content='Changed during evaluation boundary' WHERE source_id=?", (inputs['options'][0]['source_ids'][0],))
        return result
    with pytest.raises((RuntimeError, PermissionError, ValueError)):
        step(service,{**inputs,'authorize':boundary},current,'review',feedback(inputs['options'][0]['source_ids'][0]),'independent-race-01')
    with sqlite3.connect(db) as con:
        after = con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]
    assert after == before, 'Evaluation side-write committed after current source changed'
