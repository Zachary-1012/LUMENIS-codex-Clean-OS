import sqlite3
import pytest
from tests.test_growth_business_review import outcome, feedback, count
from tests.test_business_decision_workflow import work, step, choose, workspace
from tests.test_source_brief_job import job_db


def test_changed_original_source_cannot_be_selected(work):
    service, inputs, db = work
    prepared = service.prepare(**inputs)
    before = count(db)
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET content='Completely changed after research' WHERE source_id=?", (inputs['options'][0]['source_ids'][0],))
    with pytest.raises((RuntimeError, PermissionError, ValueError)):
        choose(service, inputs, prepared)
    assert count(db) == before


def test_revoked_outcome_bytes_cannot_replay_evaluation_side_write(work):
    service, inputs, db = work
    current = outcome(service, inputs)
    reviewed = step(service, inputs, current, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'independent-review-01')
    with sqlite3.connect(db) as con:
        con.execute('DELETE FROM evaluation_records WHERE evaluation_id=?', (reviewed['evaluation']['evaluation_id'],))
        con.execute("UPDATE canonical_data SET content='Mutated after review' WHERE source_id=?", (inputs['options'][0]['source_ids'][0],))
        before = con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]
    with pytest.raises((RuntimeError, PermissionError, ValueError)):
        step(service, inputs, current, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'independent-review-01')
    with sqlite3.connect(db) as con:
        after = con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]
    assert after == before, 'Rejected replay persisted a new evaluation before fresh source verification'
