"""Real retained sources and Permission in synthetic isolated workspaces."""
import sqlite3
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_business_result_continuity import business
from api_dual_domain import BusinessDecisionWorkflow


def advance(ws, operation, payload, name):
    current = ws['current']
    result = ws['service'].advance(current['work_id'], actor_ref=ws['actor_ref'], scope=ws['domain_scope'],
        authorize=ws['authorize'], expected_revision=current['revision'], operation=operation,
        payload=payload, submission_id=name)
    ws['current'] = result
    return result


def review(ws):
    current = ws['current']
    advance(ws, 'outcome', {'source_job_id': current['source_report']['job_id'],
        'source_id': ws['options'][0]['source_ids'][0], 'quote': 'Original issuer disclosure.',
        'limits': 'Attributed original statement; no causal business effect.'}, 'sourceuse-outcome-01')
    return advance(ws, 'review', {'assessment': 'inconclusive', 'observations': 'No measured uplift.',
        'limitations': ['Synthetic source and no causal study.'], 'next_step': 'revise',
        'source_ids': ws['options'][0]['source_ids']}, 'sourceuse-review-01')


def read(ws, **changes):
    return BusinessDecisionWorkflow.read_learning_material(ws['current']['work_id'],
        **dict(actor=ws['actor'], actor_ref=ws['actor_ref'], scope=ws['domain_scope'],
               expected_revision=ws['current']['revision'], **changes))


def test_real_source_review_learning_material_exact_revision(business):
    ws = business
    with pytest.raises(RuntimeError, match='REVIEW_REQUIRED'):
        read(ws)
    current = review(ws)
    material = read(ws)
    assert material['revision'] == current['revision']
    assert material['feedback_text'] == 'No measured uplift.'
    assert material['feedback_decision'] == 'inconclusive'
    assert material['evaluation_id'] == current['evaluation']['evaluation_id']
    assert material['business_outcome'] == 'NOT_OBSERVED'
    assert material['outcome_state'] == 'SOURCE_REPORTED'
    assert material['review_evidence_ref'] == current['revision']
    with pytest.raises(RuntimeError, match='REVISION_CONFLICT'):
        BusinessDecisionWorkflow.read_learning_material(current['work_id'], actor=ws['actor'],
            actor_ref=ws['actor_ref'], scope=ws['domain_scope'], expected_revision='app_evidence_records:0')


def test_source_bytes_revoked_after_review_blocks_learning_and_replay(business):
    ws = business
    reviewed = review(ws)
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM evaluation_records WHERE evaluation_id=?', (reviewed['evaluation']['evaluation_id'],))
        source_id = ws['options'][0]['source_ids'][0]
        ref = con.execute('SELECT scope_evidence_ref FROM canonical_data WHERE source_id=?', (source_id,)).fetchone()[0]
        con.execute("UPDATE app_evidence_records SET collection_metadata='{}' WHERE id=?", (ref,))
        before = con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        read(ws)
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        advance(ws, 'review', {'assessment': 'inconclusive', 'observations': 'No measured uplift.',
            'limitations': ['Synthetic source and no causal study.'], 'next_step': 'revise',
            'source_ids': ws['options'][0]['source_ids']}, 'sourceuse-review-01')
    with ws['repo'].connection() as con:
        assert con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0] == before


def test_evaluation_boundary_external_writer_cannot_commit_derived_evaluation(business):
    ws = business
    current = review(ws)
    original = ws['authorize']
    changed = False
    def boundary(operation):
        nonlocal changed
        receipt = original(operation)
        if operation == 'evaluate' and not changed:
            changed = True
            with sqlite3.connect(ws['repo'].db_path) as con:
                con.execute("UPDATE canonical_data SET content='Changed at evaluation boundary' WHERE source_id=?",
                            (ws['options'][0]['source_ids'][0],))
        return receipt
    with ws['repo'].connection() as con:
        before = con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0]
    ws['authorize'] = boundary
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        advance(ws, 'review', {'assessment': 'not_useful', 'observations': 'Second review.',
            'limitations': ['No measured outcomes.'], 'next_step': 'revise',
            'source_ids': ws['options'][0]['source_ids']}, 'sourceuse-race-review')
    assert changed
    with ws['repo'].connection() as con:
        assert con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0] == before


def test_source_actor_cannot_borrow_another_identity(business):
    ws = business
    review(ws)
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        BusinessDecisionWorkflow.read_learning_material(ws['current']['work_id'], actor=ws['actor'],
            actor_ref='actor:987654', scope=ws['domain_scope'], expected_revision=ws['current']['revision'])
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        BusinessDecisionWorkflow.read_learning_material(ws['current']['work_id'], actor={'id': 987654},
            actor_ref=ws['actor_ref'], scope=ws['domain_scope'], expected_revision=ws['current']['revision'])


def test_retained_attachment_mutation_blocks_business_and_learning(business):
    import json
    import shared_artifacts
    ws = business
    review(ws)
    with ws['repo'].connection() as con:
        source_id = ws['options'][0]['source_ids'][0]
        evidence = con.execute('SELECT collection_metadata FROM app_evidence_records WHERE id=(SELECT scope_evidence_ref FROM canonical_data WHERE source_id=?)', (source_id,)).fetchone()
        artifact_id = json.loads(evidence[0])['source_artifact_ref']
        relative = con.execute('SELECT relative_path FROM lumenis_shared_artifacts WHERE artifact_id=?', (artifact_id,)).fetchone()[0]
        before = con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='CTH_BMP_DECISION_WORK'").fetchone()[0]
    path = shared_artifacts.artifact_root() / relative
    path.write_bytes(b'Changed retained original attachment')
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        read(ws)
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        advance(ws, 'review', {'assessment': 'useful', 'observations': 'Cannot reuse withdrawn source.',
            'limitations': ['Original no longer matches.'], 'next_step': 'retain',
            'source_ids': ws['options'][0]['source_ids']}, 'sourceuse-original-mutation')
    with ws['repo'].connection() as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='CTH_BMP_DECISION_WORK'").fetchone()[0] == before


def test_explicit_foreign_source_actor_cannot_borrow_review_actor(business):
    ws = business
    review(ws)
    foreign = BusinessDecisionWorkflow(source_actor={'id': 987654}, action_actor=ws['actor'])
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        foreign.reopen(ws['current']['work_id'], actor_ref=ws['actor_ref'], scope=ws['domain_scope'], authorize=ws['authorize'])

from tests.test_source_brief_job_routes import client as report_client, job_db, GLOBAL, URL


def test_scope_signature_alone_cannot_authorize_business_body_use(report_client):
    import shared_artifacts
    shared_artifacts.ensure_artifact_table()
    import lumenis_app_api
    from lumenis.system.security import permission
    api, app, db, entry, gate = report_client
    app.register_blueprint(lumenis_app_api.domain_api_bp)
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    headers = {**GLOBAL, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': entry['subject_id']}
    metadata = api.post(URL + '/generate', headers=headers, json={})
    assert metadata.status_code == 200
    report = metadata.get_json()['result']
    options = [{'option_id': key, 'proposal': 'Review sources.', 'rationale': 'Unverified body is not admitted.',
        'source_ids': ['brief-job-source'], 'assumptions': ['Must check source rights.'],
        'unknowns': ['No original artifact/use grant.'], 'check': 'Admit actual source first.'} for key in ['A', 'B']]
    denied = api.post('/api/experience/business-works', headers=headers, json={
        'submission_id': 'sourceuse-metadata-denied', 'source_job_id': report['job_id'],
        'kind': 'venue_operations', 'question': 'Which source may support this decision?', 'options': options})
    assert denied.status_code == 403, denied.get_json()
    assert denied.get_json()['code'] == 'SOURCE_BRIEF_SOURCE_USE_UNAVAILABLE'
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='CTH_BMP_DECISION_WORK'").fetchone()[0] == 0
