"""Native-page research/save/revision/recovery with explicit synthetic acquisition.

The real Collector Producer, Artifact, Permission and SavedWork owners execute
on disposable data. No fixture is claimed as a real customer's comments.
"""
import pytest

import intelligence_library_api as library
from lumenis.shared.database import DatabaseRepository
from lumenis.shared.reporting import saved_work
from tests import test_collector_comment_pages as original
from tests import test_collector_transaction_truth as collector
from tests.test_comment_page_source_use import page_request, grant

collector_case = collector.collector_case
comments_case = original.comments_case


@pytest.fixture
def case(comments_case, monkeypatch):
    value = comments_case
    repo = DatabaseRepository(str(value['db_path']))
    monkeypatch.setattr(library,'get_repository',lambda:repo)
    monkeypatch.setattr(saved_work,'get_repository',lambda:repo)
    value['repo'] = repo
    return value


def save(case, evidence_ids, *, question='What do the observed comments support and leave unknown?', request_id='comment-research-save-0001', **changes):
    return library.save_comment_research(actor=case['actor'],scope=case['scope'],question=question,
        evidence_ids=evidence_ids,request_id=request_id,**changes)


def test_comment_analysis_save_v1_v2_reopen_export_and_independent_exact_grants(case, monkeypatch):
    first, source, request, con = page_request(case,monkeypatch)
    try:
        evidence_id = first['evidence_ref']
        with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
            library.analyze_comment_research(actor=case['actor'],scope=case['scope'],question='What was observed?',evidence_ids=[evidence_id])
        grant(case,request,'research_reference')
        analysis = library.analyze_comment_research(actor=case['actor'],scope=case['scope'],question='What was observed?',evidence_ids=[evidence_id])
        counts = analysis['analysis']['statistics']
        assert counts['observed_record_count'] == 2 and counts['reply_identifier_observed_count'] == 1
        assert counts['likes']['known_observation_count'] == 1 and counts['likes']['missing_observation_count'] == 1
        assert counts['likes']['sum_known_observations'] == 0 and counts['likes']['deduplicated_total'] is None
        assert counts['comment_population_total'] is None
        with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
            save(case,[evidence_id])
        grant(case,request,'quote_reference')
        before = case['repo'].query_one('SELECT COUNT(*) FROM app_evidence_records')[0]
        saved = save(case,[evidence_id])
        artifact_id = saved['artifact']['artifact_id']
        assert saved['receipt']['sources'][0]['source_id'] == 'comment-page:'+str(evidence_id)
        assert saved['receipt']['sources'][0]['parent_source_id'] == case['source_id']
        assert saved['document']['citations'][0]['quote'] == 'First source statement'
        assert saved['document']['payload']['comment_research']['analysis']['ai_execution'] == 'NOT_RUN'
        reviews = [{'evidence_id':evidence_id,'comment_index':1,'relationship':'qualifies',
                    'rationale':'The reply is additional source context; no independent customer outcome is established.'}]
        revised = save(case,[evidence_id],request_id='comment-research-revision-0002',reviews=reviews,
            work_id=saved['document']['work_id'],previous_artifact_id=artifact_id,expected_draft_digest=saved['document']['draft_digest'])
        assert revised['document']['version'] == 2 and revised['document']['parent_sha256'] == saved['artifact']['sha256']
        assert revised['document']['payload']['comment_research']['analysis']['review_relationship_counts']['qualifies'] == 1
        assert saved_work.reopen_work(artifact_id,actor=case['actor'],scope=case['scope'])['document'] == saved['document']
        assert save(case,[evidence_id])['artifact'] == saved['artifact']
        output = saved_work.export_work(revised['artifact']['artifact_id'],actor=case['actor'],scope=case['scope'],format='md')
        assert 'First source statement' in output['content'].decode('utf-8')
        assert case['repo'].query_one('SELECT COUNT(*) FROM app_evidence_records')[0] == before
    finally:
        con.close()


@pytest.mark.parametrize('purpose',['research_reference','quote_reference'])
def test_revoke_blocks_saved_read_export_and_restore_recovers_original_bytes(case, monkeypatch, purpose):
    page, source, request, con = page_request(case,monkeypatch)
    try:
        _, research = grant(case,request,'research_reference')
        _, quote = grant(case,request,'quote_reference')
        saved = save(case,[page['evidence_ref']])
        case['gate'].revoke_approval(research if purpose == 'research_reference' else quote)
        for read in (saved_work.reopen_work,saved_work.export_work):
            with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
                read(saved['artifact']['artifact_id'],actor=case['actor'],scope=case['scope'])
        grant(case,request,purpose)
        recovered = saved_work.reopen_work(saved['artifact']['artifact_id'],actor=case['actor'],scope=case['scope'])
        assert recovered['artifact'] == saved['artifact'] and recovered['document'] == saved['document']
    finally:
        con.close()


def test_next_page_requires_its_own_grants_and_no_parent_post_promotion(case, monkeypatch):
    page, source, request, con = page_request(case,monkeypatch)
    try:
        grant(case,request,'research_reference');grant(case,request,'quote_reference')
        second = original.collect(case,monkeypatch,continuation=page['continuation'])
        with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
            save(case,[page['evidence_ref'],second['evidence_ref']])
        from lumenis.system.collector.adapters.secondary_collection import read_comment_page_original
        original_page = read_comment_page_original(second['page_ref'],actor=case['actor'],scope=case['scope'],connection=con)
        second_request = {**request,'source_evidence_ref':second['page_ref'],'source_fingerprint':original_page['sha256'],
                          'body_sha256':original_page['document']['body_sha256']}
        grant(case,second_request,'research_reference');grant(case,second_request,'quote_reference')
        saved = save(case,[page['evidence_ref'],second['evidence_ref']])
        assert saved['document']['payload']['comment_research']['analysis']['statistics']['observed_record_count'] == 3
        assert len({item['source_id'] for item in saved['receipt']['sources']}) == 2
        assert all(item['rights'] == 'UNKNOWN' for item in saved['receipt']['sources'])
    finally:
        con.close()


def test_commit_revocation_before_lease_cannot_publish_report(case, monkeypatch):
    page, source, request, con = page_request(case,monkeypatch)
    try:
        grant(case,request,'research_reference')
        _,token = grant(case,request,'quote_reference')
        previous = library.comment_source_commit_guard
        def revoked(*args,**kwargs):
            case['gate'].revoke_approval(token)
            return previous(*args,**kwargs)
        monkeypatch.setattr(library,'comment_source_commit_guard',revoked)
        before = case['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]
        with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
            save(case,[page['evidence_ref']])
        assert case['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0] == before
    finally:
        con.close()


def test_comment_page_remains_unverified_fact_and_parent_withdrawal_invalidates_result(case, monkeypatch):
    page, source, request, con = page_request(case,monkeypatch)
    try:
        grant(case,request,'research_reference');grant(case,request,'quote_reference')
        context = saved_work.authorize_saved_work(case['actor'],case['scope'],action='read',connection=con)
        with pytest.raises(ValueError,match='LIBRARY_KNOWLEDGE_NOT_ADMITTED'):
            library.verified_research_source(con,page['evidence_ref'],actor=case['actor'],context=context,facts_only=True)
        saved = save(case,[page['evidence_ref']])
        with case['repo'].transaction() as other:
            other.execute("UPDATE lumenis_subject_registry SET status='disabled' WHERE subject_id=?",(case['scope']['subject_id'],))
        with pytest.raises(ValueError,match='WORK_PERMISSION_DENIED'):
            saved_work.reopen_work(saved['artifact']['artifact_id'],actor=case['actor'],scope=case['scope'])
    finally:
        con.close()


def test_saved_unquoted_native_creation_input_still_requires_both_purposes(case,monkeypatch):
    page,source,request,con = page_request(case,monkeypatch)
    try:
        grant(case,request,'research_reference')
        payload = {'creation':{'source_bindings':[{'evidence_id':page['evidence_ref']}]}}
        options = dict(actor=case['actor'],scope=case['scope'],title='Unquoted source-derived draft',
            markdown='A derived draft still depends on a source.',kind='research',payload=payload,citations=[],
            request_id='unquoted-comment-source-0001')
        with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
            saved_work.save_work(**options)
        _,quote_token = grant(case,request,'quote_reference')
        saved = saved_work.save_work(**options)
        case['gate'].revoke_approval(quote_token)
        with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
            saved_work.reopen_work(saved['artifact']['artifact_id'],actor=case['actor'],scope=case['scope'])
    finally:
        con.close()


def test_source_quote_cannot_be_saved_as_ordinary_unapproved_evidence(case,monkeypatch):
    page,source,request,con = page_request(case,monkeypatch)
    try:
        grant(case,request,'research_reference')
        citation = {'evidence_id':page['evidence_ref'],'start':0,'end':22,'quote':'First source statement'}
        options = dict(actor=case['actor'],scope=case['scope'],title='Exact observed statement',
            markdown='A source statement does not verify an outcome.',kind='research',payload={},citations=[citation],
            request_id='comment-quote-write-0001')
        with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
            saved_work.save_work(**options)
        grant(case,request,'quote_reference')
        saved = saved_work.save_work(**options)
        assert saved['document']['citations'][0]['quote'] == citation['quote']
    finally:
        con.close()


def test_original_storage_failure_recovers_same_observations_then_saves_research(case,monkeypatch):
    stage = saved_work._stage_bytes
    monkeypatch.setattr(saved_work,'_stage_bytes',lambda *args,**kwargs:(_ for _ in ()).throw(OSError('isolated storage fault')))
    page = original.collect(case,monkeypatch)
    assert page['original_source']['status'] == 'UNAVAILABLE'
    with pytest.raises(LookupError,match='COMMENT_ORIGINAL_ARTIFACT_UNAVAILABLE'):
        library.analyze_comment_research(actor=case['actor'],scope=case['scope'],question='What was observed?',evidence_ids=[page['evidence_ref']])
    monkeypatch.setattr(saved_work,'_stage_bytes',stage)
    recovered = case['entry'].recover_comment_page_original(page['page_ref'],actor=case['actor'],scope=case['scope'])
    assert recovered['document']['observations'] == page['comments'] and len(case['calls']) == 1
    con = case['repo'].connect()
    try:
        request = dict(scope=case['scope'],source_evidence_ref=page['page_ref'],source_fingerprint=recovered['sha256'],
            body_sha256=recovered['document']['body_sha256'],source_version='collector-native-comments/2',connection=con)
        grant(case,request,'research_reference');grant(case,request,'quote_reference')
        before = case['repo'].query_one('SELECT COUNT(*) FROM app_evidence_records')[0]
        result = save(case,[page['evidence_ref']])
        assert result['document']['payload']['comment_research']['analysis']['statistics']['observed_record_count'] == 2
        assert case['repo'].query_one('SELECT COUNT(*) FROM app_evidence_records')[0] == before
    finally:
        con.close()


def test_product_http_confirm_analyze_save_export_and_revoke_without_test_grant(case,monkeypatch):
    page = original.collect(case,monkeypatch)
    app = case['client'].application
    app.register_blueprint(library.intelligence_library_bp)
    source_url = '/api/intelligence/library/comments/'+str(page['evidence_ref'])+'/source-use'
    headers = case['focus_headers']
    declaration = {'rights':'public-reference-only',
        'statement':'This isolated source is approved only for internal reference and quotation; no training/publication.'}
    from lumenis.system.security.permission import PermissionLevel
    case['gate'].grant_permission(PermissionLevel.HUMAN_APPROVAL)
    prepared = None
    for purpose in ('research_reference','quote_reference'):
        response = case['client'].post(source_url,headers=headers,json={
            'mode':'prepare','purpose':purpose,'rights_declaration':declaration})
        assert response.status_code == 200,response.get_json()
        prepared = response.get_json()['result']
        assert prepared['source_use_granted'] is False
        rejected = case['client'].post(source_url,headers=headers,json={'mode':'confirm','purpose':purpose,
            'rights_declaration':declaration,'confirmed':True,'confirmed_resource':'stale-resource'})
        assert rejected.status_code == 403
        approved = case['client'].post(source_url,headers=headers,json={'mode':'confirm','purpose':purpose,
            'rights_declaration':declaration,'confirmed':True,'confirmed_resource':prepared['resource']})
        assert approved.status_code == 200,approved.get_json()
        assert approved.get_json()['result']['source_use_granted'] is True
    base = '/api/intelligence/library/comment-research'
    response = case['client'].post(base,headers=headers,json={'mode':'analyze','question':'What is directly observed?',
        'evidence_ids':[page['evidence_ref']]})
    assert response.status_code == 200,response.get_json()
    response = case['client'].post(base,headers=headers,json={'mode':'save','question':'What is directly observed?',
        'evidence_ids':[page['evidence_ref']],'request_id':'http-comment-research-0001'})
    assert response.status_code == 200,response.get_json()
    saved = response.get_json()['result']
    assert saved['document']['citations']
    revoked = case['client'].post(source_url,headers=headers,json={'mode':'revoke','purpose':'quote_reference',
        'confirmed':True,**{key:prepared[key] for key in ('source_fingerprint','body_sha256','source_version')}})
    assert revoked.status_code == 200,revoked.get_json()
    assert revoked.get_json()['result']['state'] == 'REVOKED_NO_READ_GRANTED'
    with pytest.raises(PermissionError,match='COMMENT_SOURCE_USE_APPROVAL_REQUIRED'):
        saved_work.export_work(saved['artifact']['artifact_id'],actor=case['actor'],scope=case['scope'],format='md')
    cross = case['client'].post(base,headers={**headers,'Origin':'https://foreign.invalid'},json={
        'mode':'analyze','question':'What is directly observed?','evidence_ids':[page['evidence_ref']]})
    assert cross.status_code == 403
