"""Signed source → numeric candidate → user review → original Registry proposal."""
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_applied_business_statistics import _source
from lumenis.shared.reporting import business_brief, entity_candidate_review as owner


@pytest.fixture
def report(workspace, monkeypatch):
    ws = workspace
    monkeypatch.setattr(business_brief, 'get_repository', lambda: ws['repo'])
    reference = _source(ws, {'left': 'Brand A', 'right': 'Brand B'}, analysis='identity-reference')
    raw = (ws['root'] / 'identity-reference.txt').read_text()
    pair = {}
    for side, label in [('left', 'Brand A'), ('right', 'Brand B')]:
        start = raw.index(label)
        pair[side] = {'label': label, 'registry_subject_id': None,
                      'source_evidence_id': reference['evidence_id'],
                      'start': start, 'end': start + len(label), 'quote': label}
    rows = [{'id': str(i), 'partition': 'train' if i < 40 else 'test',
             'agreements': [bool(i % 2)] * 2, 'label': i % 2} for i in range(80)]
    rows.append({'id': 'pair-1', 'partition': 'candidate', 'agreements': [True, False],
                 'label': None, 'identity_pair': pair})
    source = _source(ws, {'rows': rows}, analysis='entity_matching')
    kwargs = {'actor': ws['actor'], 'scope': ws['scope']}
    result = business_brief.analyze_statistics_source(source['evidence_id'], **kwargs)
    saved = ws['work'].save_work(**result['saved_work_draft'], request_id='candidate-report-1', **kwargs)
    return ws, saved, kwargs


def _review(report, **changes):
    ws, saved, kwargs = report
    args = dict(candidate_id='pair-1', proposed_side='left', decision='PROPOSE_REGISTRATION', rationale='Explicit synthetic reviewer choice.',
                proposed_identity={'domain_id': 'BMP', 'subject_type': 'brand',
                                   'name_en': 'Brand A', 'name_zh': '合成品牌甲'}, request_id='candidate-review-1')
    args.update(changes)
    return owner.save_review(saved['artifact']['artifact_id'], **kwargs, **args)


def test_review_is_persistent_judgment_with_separate_registration(report):
    ws, saved, kwargs = report
    review = _review(report)
    identifier = review['artifact']['artifact_id']
    proposal = owner.registration_proposal(identifier, **kwargs)
    assert proposal['entries'][0]['identity']['name_en'] == 'Brand A'
    assert proposal['merge_supported'] is False
    assert proposal['registry_change'] == 'NOT_PERFORMED'
    assert ws['work'].reopen_work(identifier, **kwargs)['document']['payload']['entity_candidate_review']['identity_truth'] == 'NOT_ESTABLISHED'
    assert _review(report)['artifact']['artifact_id'] == identifier


def test_review_retraction_and_report_revision_require_new_review(report):
    ws, saved, kwargs = report
    review = _review(report)
    withdrawn = _review(report, decision='KEEP_SEPARATE', proposed_identity=None, proposed_side=None,
                        request_id='candidate-review-2', work_id=review['document']['work_id'],
                        previous_artifact_id=review['artifact']['artifact_id'])
    with pytest.raises(ValueError, match='VERSION_CHANGED'):
        owner.registration_proposal(review['artifact']['artifact_id'], **kwargs)
    with pytest.raises(ValueError, match='NOT_PROPOSED'):
        owner.registration_proposal(withdrawn['artifact']['artifact_id'], **kwargs)
    ws['work'].revise_work(saved['artifact']['artifact_id'], request_id='candidate-report-2', expected_sha256=saved['artifact']['sha256'], reason='Synthetic version change',
                          edits=[{'pointer': '/title', 'expected': saved['document']['title'], 'value': 'New report review'}], **kwargs)
    with pytest.raises(ValueError, match='VERSION_CHANGED'):
        owner.read_candidates(saved['artifact']['artifact_id'], **kwargs)


@pytest.mark.parametrize('decision', ['MERGE', 'AUTO_ACCEPT', [], None])
def test_unknown_or_automatic_identity_action_rejected(report, decision):
    with pytest.raises(ValueError, match='JUDGMENT_INVALID'):
        _review(report, decision=decision)


def test_user_edited_score_cannot_authorize_proposal(report):
    ws, saved, kwargs = report
    revised = ws['work'].revise_work(saved['artifact']['artifact_id'], request_id='candidate-forged-score', expected_sha256=saved['artifact']['sha256'], reason='User edited score',
        edits=[{'pointer': '/payload/statistics/result/candidates/0/probability', 'expected': saved['document']['payload']['statistics']['result']['candidates'][0]['probability'], 'value': 1}], **kwargs)
    with pytest.raises(ValueError, match='SOURCE_OR_RECIPE_CHANGED'):
        owner.read_candidates(revised['artifact']['artifact_id'], **kwargs)


def test_registry_exact_review_bound_prepare_apply_and_retraction(report):
    import subject_registry as registry
    from lumenis.system.security import permission
    ws, saved, kwargs = report
    with ws['repo'].transaction() as con:
        registry.ensure_schema(con)
    ws['app'].register_blueprint(registry.subject_registry_bp)
    ws['gate'].grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
    review = _review(report)
    proposal = owner.registration_proposal(review['artifact']['artifact_id'], **kwargs)
    body = {'entries': proposal['entries'], 'candidate_review': {
        'artifact_id': review['artifact']['artifact_id'], 'scope': ws['scope']}}
    client = ws['app'].test_client()
    prepared = client.post('/api/settings/subjects/batch', json=body).get_json()
    assert prepared['state'] == 'PREPARED', prepared
    applied = client.post('/api/settings/subjects/batch', json={**body, 'mode': 'apply',
        'confirm': True, 'confirmed_resource': prepared['resource']}).get_json()
    assert applied['state'] == 'COMPLETED', applied
    assert applied['results'][0]['status'] == 'CREATED'
    repeated = client.post('/api/settings/subjects/batch', json={**body, 'mode': 'apply',
        'confirm': True, 'confirmed_resource': prepared['resource']}).get_json()
    assert repeated['results'][0]['status'] == 'EXISTING'
    _review(report, decision='KEEP_SEPARATE', proposed_identity=None, proposed_side=None, request_id='candidate-withdrawal',
            work_id=review['document']['work_id'], previous_artifact_id=review['artifact']['artifact_id'])
    stale = client.post('/api/settings/subjects/batch', json={**body, 'mode': 'apply',
        'confirm': True, 'confirmed_resource': prepared['resource']})
    assert stale.status_code == 400 and 'VERSION_CHANGED' in stale.get_json()['code']


def test_source_corruption_and_foreign_scope_cannot_reopen_review(report):
    ws, saved, kwargs = report
    review = _review(report)
    foreign = {**ws['scope'], 'domain_id': 'zbmp'}
    with pytest.raises((ValueError, PermissionError)):
        owner.registration_proposal(review['artifact']['artifact_id'], actor=ws['actor'], scope=foreign)
    evidence_id = saved['document']['payload']['statistics']['source_evidence_id']
    with ws['repo'].transaction() as con:
        con.execute('UPDATE app_evidence_records SET content_hash=? WHERE id=?', ('0' * 64, evidence_id))
    with pytest.raises((ValueError, PermissionError)):
        owner.registration_proposal(review['artifact']['artifact_id'], **kwargs)


def test_prepare_rejects_entries_changed_from_review(report):
    import subject_registry as registry
    ws, saved, kwargs = report
    with ws['repo'].transaction() as con:
        registry.ensure_schema(con)
    ws['app'].register_blueprint(registry.subject_registry_bp)
    review = _review(report)
    proposal = owner.registration_proposal(review['artifact']['artifact_id'], **kwargs)
    proposal['entries'][0]['identity']['name_en'] = 'Not the reviewed identity'
    response = ws['app'].test_client().post('/api/settings/subjects/batch', json={
        'entries': proposal['entries'], 'candidate_review': {
            'artifact_id': review['artifact']['artifact_id'], 'scope': ws['scope']}})
    assert response.status_code == 400
    assert response.get_json()['code'] == 'SUBJECT_CANDIDATE_ENTRY_CHANGED'
    assert registry.list_subjects('BMP') == []


def test_generic_saved_json_cannot_copy_owner_review_receipt(report):
    from copy import deepcopy
    ws, saved, kwargs = report
    review = _review(report)
    copied = ws['work'].save_work(title='Copied editable review JSON', kind='report', markdown='Not the review owner.',
        payload=deepcopy(review['document']['payload']), citations=review['document']['citations'],
        request_id='forged-review-copy', **kwargs)
    with pytest.raises(ValueError, match='OWNER_RECEIPT_REQUIRED'):
        owner.registration_proposal(copied['artifact']['artifact_id'], **kwargs)


def test_unrelated_identity_cannot_be_presented_as_selected_candidate(report):
    with pytest.raises(ValueError, match='IDENTITY_NOT_SELECTED_CANDIDATE'):
        _review(report, proposed_identity={'domain_id': 'BMP', 'subject_type': 'brand',
                    'name_en': 'Unrelated Brand Z', 'name_zh': '无关品牌'})


def test_review_signature_corruption_rejected(report):
    ws, saved, kwargs = report
    review = _review(report)
    with ws['repo'].transaction() as con:
        con.execute('UPDATE app_evidence_records SET content_hash=? WHERE source=? AND asset_id=?',
                    ('0' * 64, 'entity_candidate_review', review['artifact']['artifact_id']))
    with pytest.raises(ValueError, match='OWNER_RECEIPT_REQUIRED'):
        owner.registration_proposal(review['artifact']['artifact_id'], **kwargs)
