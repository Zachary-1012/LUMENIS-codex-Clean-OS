from copy import deepcopy
import pytest
from lumenis.system.collector.acquisition_plan import (
    build_acquisition_plan, AcquisitionPlanError, assess_query_relevance,
)

ROWS = [
    {'subject_id':'SUBJ-MALL','domain_id':'CTH','subject_type':'company',
     'name_en':'Harbor Mall','name_zh':'海港商场','status':'configured'},
    {'subject_id':'SUBJ-BRAND','brand_focus_id':'BRAND-ONE','domain_id':'BMP','subject_type':'brand',
     'name_en':'Brand One','status':'configured'},
]
REQUEST = {'domain_id':'CTH','scope_key':'SUBJ-MALL','aliases':['海港商场'],
    'purpose':'消费者停车与服务体验','dimension':'consumer_experience',
    'platforms':['x','douyin'],'geography_terms':['广州'],'topic_terms':['停车 体验','服务 评价'],
    'exclude_terms':['异地分店'],'market_typed_ref':None}

def plan(requests=None, **kw):
    return build_acquisition_plan(registry_loader=lambda:deepcopy(ROWS),
        business_requests=deepcopy(requests if requests is not None else [REQUEST]), **kw)

def test_purpose_bound_query_keeps_identity_period_and_unregistered_market_separate():
    p=plan()
    assert len(p.queries)==4
    assert {q.keyword for q in p.queries}=={'海港商场 广州 停车 体验','海港商场 广州 服务 评价'}
    assert {q.business_context['platform'] for q in p.queries}=={'x','douyin'}
    assert all(q.subject_id=='SUBJ-MALL' for q in p.queries)
    assert all(q.business_context['market_typed_ref'] is None for q in p.queries)
    assert all(q.business_context['publication_since'] is None for q in p.queries)
    assert all(q.business_context['publication_until'] is None for q in p.queries)
    assert all(q.business_context['source_use_grant'] is None for q in p.queries)
    assert all(q.to_dict()['scope_role']=='PLANNED_TARGET_NOT_VERIFIED_SOURCE_BINDING' for q in p.queries)

def test_selected_facet_does_not_generate_unselected_global_catalog_topics():
    r=deepcopy(REQUEST);r['topic_terms']=['服务 评价'];r['platforms']=['wechat']
    p=plan([r])
    assert p.total_queries==1
    assert p.queries[0].business_context['dimension']=='consumer_experience'
    assert '联名' not in p.queries[0].keyword
    assert 'Brand One' not in p.queries[0].keyword


def native_record(**changes):
    return {'native_id':'POST-TIME', 'source_url':'https://example.org/p/time',
            'content':'海港商场 广州 停车 体验',
            'published_at':'2025-03-02T08:00:00+08:00',
            'capture_observation_utc':'2026-10-08T00:00:00Z', **changes}


def test_no_global_cutoff_accepts_history_and_explicit_task_period_still_filters():
    record=native_record()
    assert assess_query_relevance(record, plan().queries[0])['status']=='CANDIDATE_TASK_RELEVANT'
    request=deepcopy(REQUEST)
    request['publication_since']='2026-01-01'
    query=plan([request]).queries[0]
    assert query.business_context['publication_since']=='2026-01-01'
    assert assess_query_relevance(record, query)['status']=='OUTSIDE_REQUESTED_PUBLICATION_PERIOD'
    request['publication_since']='2024-01-01'
    request['publication_until']='2025-03-01'
    assert assess_query_relevance(record, plan([request]).queries[0])['status']=='OUTSIDE_REQUESTED_PUBLICATION_PERIOD'


def test_offset_instant_boundaries_and_source_calendar_dates_are_distinct():
    request=deepcopy(REQUEST)
    request.update(publication_since='2025-03-02T00:00:00Z',
                   publication_until='2025-03-02T00:00:00Z')
    record=native_record()
    assert assess_query_relevance(record, plan([request]).queries[0])['status']=='CANDIDATE_TASK_RELEVANT'
    request.update(publication_since='2025-03-02', publication_until='2025-03-02')
    result=assess_query_relevance(native_record(published_at='2025-03-02T00:05:00+09:00'),
                                 plan([request]).queries[0])
    assert result['status']=='CANDIDATE_TASK_RELEVANT'


def test_mixed_date_and_instant_bounds_use_observed_offset_without_early_rejection():
    request=deepcopy(REQUEST)
    request.update(publication_since='2025-03-02',
                   publication_until='2025-03-01T23:00:00Z')
    result=assess_query_relevance(native_record(published_at='2025-03-02T00:05:00+09:00'),
                                 plan([request]).queries[0])
    assert result['status']=='CANDIDATE_TASK_RELEVANT'


def test_explicit_until_neither_replaces_capture_nor_allows_future_publication():
    request=deepcopy(REQUEST)
    request['publication_until']='2029-01-01T00:00:00Z'
    query=plan([request]).queries[0]
    missing=assess_query_relevance(native_record(capture_observation_utc=None), query)
    assert 'ACTUAL_CAPTURE_CUTOFF_MISSING' in missing['reasons']
    future=assess_query_relevance(native_record(published_at='2027-01-01T00:00:00Z'), query)
    assert 'PUBLICATION_AFTER_ACTUAL_OBSERVATION' in future['reasons']
    assert future['admitted'] is False


@pytest.mark.parametrize('change', [
    {'publication_since':'2025-03-02T08:00:00'},
    {'publication_until':'not-a-date'},
    {'publication_since':False},
    {'publication_since':'2027-01-01', 'publication_until':'2026-12-31'},
    {'publication_since':'2025-03-02T00:00:01Z', 'publication_until':'2025-03-02T00:00:00Z'},
])
def test_invalid_or_reversed_period_rejected_before_collection(change):
    request=deepcopy(REQUEST)
    request.update(change)
    with pytest.raises(AcquisitionPlanError):
        plan([request])


def test_changed_explicit_period_invalidates_query_continuation():
    first=plan(max_queries=1)
    request=deepcopy(REQUEST)
    request['publication_since']='2025-01-01'
    with pytest.raises(AcquisitionPlanError, match='continuation'):
        plan([request], continuation=first.next_cursor)


def test_semantic_expansion_generates_real_additive_queries_without_source_claims():
    request=deepcopy(REQUEST)
    request['topic_terms']=['停车 体验']
    request['task_semantic_expansion']={'term':'服务 评价', 'reason':'Task explicitly requests service feedback'}
    before=deepcopy(request)
    result=plan([request])
    assert len(result.queries)==4
    assert {q.keyword for q in result.queries}=={'海港商场 广州 停车 体验','海港商场 广州 服务 评价'}
    expanded=[q for q in result.queries if q.keyword.endswith('服务 评价')]
    assert len(expanded)==2
    assert all(q.business_context['query_origin']=='TASK_SEMANTIC_EXPANSION' for q in expanded)
    assert all(q.business_context['source_use_grant'] is None and
               q.business_context['native_scope_bound'] is False for q in expanded)
    assert request==before


def test_existing_expansion_term_is_not_duplicated_and_expansion_can_supply_selected_facet():
    request=deepcopy(REQUEST)
    request['task_semantic_expansion']={'term':'服务 评价', 'reason':'Current task intent'}
    assert plan([request]).total_queries==4
    request['topic_terms']=[]
    result=plan([request])
    assert result.total_queries==2
    assert all(q.keyword.endswith('服务 评价') for q in result.queries)


@pytest.mark.parametrize('expansion', ['unbound term', {'term':'服务 评价'},
                                     {'term':'', 'reason':'Task intent'}])
def test_unexplained_semantic_expansion_rejected(expansion):
    request=deepcopy(REQUEST)
    request['task_semantic_expansion']=expansion
    with pytest.raises(AcquisitionPlanError):
        plan([request])

def test_bounded_continuation_visits_every_query_without_duplicates():
    first=plan(max_queries=2)
    second=plan(max_queries=2, continuation=first.next_cursor)
    assert first.total_queries==second.total_queries==4
    assert first.truncated is True and first.next_cursor['offset']==2
    assert second.next_cursor is None and second.truncated is False
    all_queries=first.queries+second.queries
    assert len({(q.keyword,q.business_context['platform']) for q in all_queries})==4

def test_changed_scope_or_purpose_rejects_stale_continuation():
    first=plan(max_queries=1)
    r=deepcopy(REQUEST);r['purpose']='另一个团队的任务'
    with pytest.raises(AcquisitionPlanError, match='continuation'):
        plan([r], continuation=first.next_cursor)

def test_legacy_registry_plan_also_has_complete_batch_continuation():
    rows=deepcopy(ROWS)
    rows[0]['keywords']=[f'alias-{i}' for i in range(90)]
    collected=[];cursor=None
    while True:
        p=build_acquisition_plan(registry_loader=lambda:rows,max_queries=64,continuation=cursor)
        collected.extend(p.queries)
        if p.next_cursor is None:break
        cursor=p.next_cursor
    assert len(collected)==93
    assert len({(q.keyword,q.scope_key) for q in collected})==93

@pytest.mark.parametrize('change',[{'purpose':''},{'dimension':'all_topics'},
    {'aliases':['not registered']},{'scope_key':'SUBJ-OTHER'},
    {'platforms':[]},{'topic_terms':[]},{'publication_since':'2025-02-30'}])
def test_missing_or_unapproved_task_binding_is_rejected(change):
    r=deepcopy(REQUEST);r.update(change)
    with pytest.raises(AcquisitionPlanError):plan([r])

def test_known_source_tracking_requires_matching_identity_evidence():
    r=deepcopy(REQUEST);r['topic_terms']=[]
    r['tracking_sources']=[{'url':'https://example.org/official/post-1','scope_key':'SUBJ-MALL','evidence_ref':'EVIDENCE-LOCATABLE-1'}]
    p=plan([r])
    assert p.queries[0].business_context['task_type']=='TRACKING'
    assert p.queries[0].business_context['source_identity_evidence_ref']=='EVIDENCE-LOCATABLE-1'
    assert p.queries[0].business_context['source_use_grant'] is None
    r['tracking_sources'][0]['scope_key']='SUBJ-OTHER'
    with pytest.raises(AcquisitionPlanError):plan([r])

@pytest.mark.parametrize('url',['http://127.0.0.1:9222/','https://user:password@example.org/',
    'https://example.org/?access_token=secret'])
def test_private_or_credential_tracking_target_rejected(url):
    r=deepcopy(REQUEST);r['tracking_sources']=[{'url':url,'scope_key':'SUBJ-MALL','evidence_ref':'E-1'}]
    with pytest.raises(AcquisitionPlanError):plan([r])

def test_new_entity_discovery_keeps_canonical_identity_unassigned():
    r={'domain_id':'BMP','purpose':'中国在营小众品牌发现','dimension':'identity_discovery',
       'platforms':['xhs'],'geography_terms':['中国'],'topic_terms':['小众 香氛 品牌'],
       'unregistered_discovery':True}
    q=plan([r]).queries[0]
    assert q.subject_id is None and q.brand_focus_id is None
    assert q.registry_id=='' and q.scope['global_scope'] is True
    assert q.business_context['native_scope_bound'] is False

def test_name_hit_without_task_topic_is_not_admitted_and_raw_is_unchanged():
    q=plan().queries[0]
    raw={'native_id':'POST-1','source_url':'https://example.org/p/1','published_at':'2026-10-03T00:00:00Z',
         'content':'海港商场 广州 季度财报'}
    before=deepcopy(raw)
    result=assess_query_relevance(raw,q)
    assert result['status']=='REVIEW_REQUIRED' and 'TASK_TOPIC_NOT_OBSERVED' in result['reasons']
    assert result['admitted'] is False and result['entity_scope_verified'] is False
    assert raw==before

def test_foreign_entity_boundary_and_missing_publication_stay_reviewable():
    q=plan().queries[0]
    excluded=assess_query_relevance({'content':'海港商场 异地分店 停车 体验'},q)
    assert excluded['status']=='EXCLUDED_TASK_BOUNDARY'
    missing=assess_query_relevance({'native_id':'1','source_url':'https://example.org/',
        'content':'广州 停车 体验'},q)
    assert 'ENTITY_ALIAS_NOT_OBSERVED' in missing['reasons']
    assert 'NATIVE_PUBLICATION_UNKNOWN' in missing['reasons']

def test_relevant_content_remains_derivative_candidate_not_permission_or_truth():
    q=plan().queries[0]
    result=assess_query_relevance({'native_id':'1','source_url':'https://example.org/',
        'published_at':'2026-10-03T00:00:00Z','capture_observation_utc':'2026-10-03T01:00:00Z','content':'海港商场 广州 停车 体验'},q)
    assert result['status']=='CANDIDATE_TASK_RELEVANT'
    assert result['derivative'] is True and result['admitted'] is False
    assert result['source_use_grant'] is None


@pytest.mark.parametrize('stamp,code', [('2025-12-30T00:00:00Z','OUTSIDE_REQUESTED_PUBLICATION_PERIOD'),
    ('2027-01-01T00:00:00Z','REVIEW_REQUIRED'), ('09-30','REVIEW_REQUIRED'), ('2026-10-03T00:00:00','REVIEW_REQUIRED')])
def test_native_time_must_fit_actual_observation_and_keep_unknown_unassigned(stamp,code):
    request=deepcopy(REQUEST)
    request['publication_since']='2026-01-01'
    q=plan([request]).queries[0]
    result=assess_query_relevance({'native_id':'1','source_url':'https://example.org/',
        'published_at':stamp,'capture_observation_utc':'2026-10-03T01:00:00Z',
        'content':'海港商场 广州 停车 体验'},q)
    assert result['status']==code
    assert result['admitted'] is False


def test_composite_topic_terms_do_not_require_adjacent_verbatim_phrase():
    q=plan().queries[0]
    result=assess_query_relevance({'native_id':'1','source_url':'https://example.org/',
        'published_at':'2026-10-03T00:00:00Z','capture_observation_utc':'2026-10-03T01:00:00Z',
        'content':'广州 海港商场 停车收费清晰，购物体验良好'},q)
    assert result['status']=='CANDIDATE_TASK_RELEVANT' and result['admitted'] is False



def test_other_existing_platforms_are_retained_beyond_primary_six():
    r=deepcopy(REQUEST);r['platforms']=['bilibili','weibo']
    p=plan([r])
    assert {q.business_context['platform'] for q in p.queries}=={'bilibili','weibo'}


def test_new_entity_discovery_does_not_wait_for_a_completed_registry():
    r={'domain_id':'BMP','purpose':'中国小众品牌发现','dimension':'identity_discovery',
       'platforms':['xhs'],'geography_terms':['中国'],'topic_terms':['小众 香氛 品牌'],
       'unregistered_discovery':True}
    p=build_acquisition_plan(registry_loader=lambda:[],business_requests=[r])
    assert p.is_runnable is True and p.status=='STAGED'
    assert p.queries[0].brand_focus_id is None
    assert p.registry_counts=={'CTH':0,'BMP':0}


def test_one_retired_rednote_policy_does_not_block_other_named_platform_planning(monkeypatch):
    import lumenis.system.collector.acquisition_plan as module
    monkeypatch.setattr(module,'_safe_policy_metadata',lambda policy:({'status':'UNAVAILABLE'},{}))
    r=deepcopy(REQUEST);r['platforms']=['x']
    p=plan([r])
    assert p.is_runnable is True
    assert p.source_policy['identity_or_source_use_granted'] is False
