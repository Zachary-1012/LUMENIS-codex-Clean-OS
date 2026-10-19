"""Signed purpose plans reach the real Collector, Permission and five-table write.

Only platform transport is simulated. Synthetic posts are not live coverage.
"""
import hashlib
import hmac
import json
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from tests.test_collector_transaction_truth import collector_case, REGISTERED_NAME, _pipeline_counts
from lumenis.system.collector.acquisition_plan import build_acquisition_plan
from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
from lumenis.system.collector.adapters.platform_naming import get_platform_fields, normalize_platform
from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
    PURPOSE_POLICY, _canonical_config, load_prelaunch_baseline_config,
    maintenance_authorization, purpose_baseline_config, run_due_prelaunch_baseline,
)
from lumenis.system.collector.adapters.scheduling.store import ScheduleDecisionStore


@pytest.fixture(autouse=True)
def isolated_business_task_store(tmp_path, monkeypatch):
    from lumenis.system.collector.guard import task_queue
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', str(tmp_path/'business-tasks.db'))


def _setup(case, tmp_path, monkeypatch, platform, *, revoke=False, complete_original=True):
    from lumenis.system import security
    from shared_artifacts import ensure_artifact_table
    ensure_artifact_table()
    scope = case['scope']
    query = build_acquisition_plan(business_requests=[{
        'domain_id': 'CTH', 'scope_key': scope['subject_id'],
        'purpose': 'Review new store service', 'dimension': 'venue_operations',
        'platforms': [platform], 'topic_terms': ['service'],
    }], registry_loader=lambda: [{
        'domain_id': 'CTH', 'subject_id': scope['subject_id'], 'subject_type': 'company',
        'name_en': REGISTERED_NAME, 'name_zh': '注册港湾商业主体', 'status': 'active',
    }]).queries[0]
    config = purpose_baseline_config([{'status': 'READY', 'queries': [query.to_dict()]}],
        source_version='synthetic-source-v1', scope_version='test-registry-v1',
        authorization_ref='explicit-isolated-service-grant')
    config['enabled'] = True
    path = tmp_path/'signed-purpose.json'
    key = 'synthetic-key-not-production'
    def save():
        config['hmac'] = {'algorithm': 'HMAC-SHA256', 'value': hmac.new(
            key.encode(), _canonical_config(config), hashlib.sha256).hexdigest()}
        path.write_text(json.dumps(config), encoding='utf-8')
    save()
    monkeypatch.setenv('LUMENIS_PRELAUNCH_BASELINE_CONFIG', str(path))
    monkeypatch.setenv('LUMENIS_PRELAUNCH_BASELINE_HMAC_KEY', key)
    gate = case['permission'].PermissionGate()
    monkeypatch.setattr(security, 'get_permission_gate', lambda: gate)
    monkeypatch.setattr(case['permission'], 'get_permission_gate', lambda: gate)
    canonical = normalize_platform(platform)
    calls = []
    spec = get_platform_fields(canonical)
    identity = 'abcdef0123456789abcdef01' if platform == 'xhs' else '7654321098765432100'
    body = REGISTERED_NAME + ' service opening information'
    # Synthetic native-detail observations only. These URLs are identifiers;
    # this fixture never requests a real platform or grants downstream rights.
    hosts = {'xhs': 'www.rednote.com', 'douyin': 'www.douyin.com', 'x': 'x.com',
             'instagram': 'www.instagram.com', 'facebook': 'www.facebook.com',
             'wechat': 'mp.weixin.qq.com'}
    details = ({'detail_fetched': True, 'detail_identity_verified': True,
                'detail_observation': {'status': 'SUCCESS', 'body_kind': 'NATIVE_POST_BODY',
                                       'body': body}} if complete_original else {})
    class Transport:
        def health_check(self, **kwargs):
            return CollectionResult(CollectionStatus.SUCCESS, canonical)
        def search(self, keyword, **kwargs):
            calls.append(keyword)
            if revoke:
                config['enabled'] = False
                save()
            return CollectionResult(CollectionStatus.SUCCESS, canonical, raw_count=1, items=[{
                'platform_content_id': identity,
                'title': REGISTERED_NAME + ' service',
                'content': body,
                'url': 'https://' + hosts[platform] + '/post/' + identity,
                'publish_datetime': '2026-10-01T08:00:00+00:00',
                'raw': {spec.content_id: identity, spec.published_at: '2026-10-01T08:00:00+00:00',
                        spec.like_field: 0, **details},
            }])
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _: Transport())
    monkeypatch.setitem(case['surface']._last_action, canonical, 0.0)
    return path, calls, config, save, query, gate


@pytest.mark.parametrize('platform', ['xhs', 'douyin', 'x', 'instagram', 'facebook', 'wechat'])
def test_signed_scheduler_uses_actual_collector_transaction_for_six_platforms(
        collector_case, tmp_path, monkeypatch, platform):
    case = collector_case
    path, calls, _, _, _, gate = _setup(case, tmp_path, monkeypatch, platform)
    now = datetime.now(timezone.utc)
    result = run_due_prelaunch_baseline(config_path=str(path), now=now,
        store=ScheduleDecisionStore(str(tmp_path/'schedule.db')))
    assert calls and result['summary']['succeeded'] == 1, result
    actual = next(r['result'] for r in result['runs'] if r.get('result'))
    assert actual['scope_status'] == 'VERIFIED' and actual['refresh_verified'] is True
    assert _pipeline_counts(case['db_path']) == {
        'notes': 1, 'canonical_data': 1, 'app_evidence_records': 3,
        'platform_contents': 1, 'metric_snapshots': 1,
    }
    import sqlite3
    with sqlite3.connect(case['db_path']) as conn:
        features = dict(conn.execute('SELECT feature_id,COUNT(*) FROM app_evidence_records GROUP BY feature_id'))
        assert features == {'PRELAUNCH_' + normalize_platform(platform).upper() + '_COLLECT': 1,
                            'COLLECTED_SOURCE': 1, 'COLLECTOR_SOURCE_INTAKE_OUTCOME': 1}
    assert actual['source_intake']['originals_saved'] == 1
    assert actual['source_intake']['originals_pending'] == 0
    assert actual['source_intake']['owned_inference'] == 'NOT_RUN'
    assert not gate.has_permission(case['permission'].PermissionLevel.COMMIT)
    assert not gate._approvals


def test_signed_purpose_revocation_during_fetch_prevents_all_five_writes(
        collector_case, tmp_path, monkeypatch):
    case = collector_case
    path, calls, *_ = _setup(case, tmp_path, monkeypatch, 'x', revoke=True)
    result = run_due_prelaunch_baseline(config_path=str(path),
        store=ScheduleDecisionStore(str(tmp_path/'schedule.db')))
    assert len(calls) == 1
    assert result['summary']['failed'] == 1
    assert _pipeline_counts(case['db_path']) == {
        'notes': 0, 'canonical_data': 0, 'app_evidence_records': 0,
        'platform_contents': 0, 'metric_snapshots': 0,
    }


def test_service_grant_binds_full_purpose_and_batch_bound(collector_case, tmp_path, monkeypatch):
    path, _, _, _, query, gate = _setup(collector_case, tmp_path, monkeypatch, 'x')
    plan = load_prelaunch_baseline_config(str(path))['plans'][0]
    auth = maintenance_authorization(plan)
    request = {'source_url': query.keyword, 'platform': 'x',
               'scope': collector_case['scope'], 'business_query': query,
               'max_results': plan.max_results}
    assert gate.check_prelaunch_maintenance(auth, **request).allowed
    assert not gate.check_prelaunch_maintenance(auth, **{**request, 'max_results': plan.max_results + 1}).allowed
    altered = replace(query, business_context={**query.business_context, 'topic_terms': ['another-topic']})
    assert not gate.check_prelaunch_maintenance(auth, **{**request, 'business_query': altered}).allowed
    assert not gate.check_prelaunch_maintenance(auth, **{**request, 'business_query': None}).allowed


def test_existing_http_entry_forwards_task_purpose_to_real_collector(collector_case, monkeypatch):
    from tests.test_collector_transaction_truth import URL
    case = collector_case
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    class Transport:
        def health_check(self, **kwargs):
            return CollectionResult(CollectionStatus.SUCCESS, 'x')
        def search(self, keyword, **kwargs):
            return CollectionResult(CollectionStatus.SUCCESS, 'x', raw_count=1, items=[{
                'platform_content_id':'8765432101234567890',
                'title':REGISTERED_NAME+' service', 'content':REGISTERED_NAME+' service observed',
                'url':'https://public.example.test/observed',
                'publish_datetime':'2026-10-01T08:00:00+00:00',
                'raw':{'tweet_id':'8765432101234567890','created_at':'2026-10-01T08:00:00+00:00'},
            }])
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _: Transport())
    monkeypatch.setitem(case['surface']._last_action, 'x', 0.0)
    body={'operator':'human','confirm_read_only':True,'business_requests':[{
        'domain_id':'CTH','scope_key':case['scope']['subject_id'],
        'purpose':'Review service discussion','dimension':'venue_operations',
        'platforms':['x'],'topic_terms':['service'],
    }]}
    def send(value):
        return case['client'].post(URL, headers=case['focus_headers'], json=value)
    first=send(body).get_json()
    assert 'runs' in first, first
    result=first['runs'][0]['result']
    assert result['status']=='APPROVAL_REQUIRED'
    case['gate'].grant_approval(case['permission'].OperationType.DATA_IMPORT.value,
        resource=result['approval_resource'],granted_by='isolated explicit source approval')
    completed=send(body).get_json()
    assert completed['status']=='BATCH_COMPLETED' and completed['ok'] is True, completed
    assert completed['runs'][0]['result']['native_fields_synced']==1
    assert completed['query_plan']['queries'][0]['business_context']['purpose']=='Review service discussion'
    resumed = send({**body, 'checkpoint': completed['checkpoint']})
    assert resumed.status_code == 200, resumed.get_json()
    expected_cached = case['surface']._historical_business_result(completed)
    assert resumed.get_json() == expected_cached
    assert send(body).get_json() == expected_cached
    forged = {**completed['checkpoint'], 'completed_query_keys': ['f' * 64]}
    assert send({**body, 'checkpoint': forged}).status_code == 400
    changed = json.loads(json.dumps(body))
    changed['business_requests'][0]['purpose'] = 'Different source purpose'
    assert send({**changed, 'checkpoint': completed['checkpoint']}).status_code == 400
    from tests.test_collector_durable_compatibility import assert_committed_once
    assert_committed_once(case)
    # New independent process reads the same task and returns the immutable
    # terminal result through the actual local-workspace scope checker.
    import os, subprocess, sys
    from lumenis.system.collector.guard import task_queue
    env = {**os.environ, 'ZBC_DB_PATH': str(case['db_path']),
           'ZBC_DATA_DIR': str(Path(task_queue.DEFAULT_PATH).parent)}
    script = """
import json
from flask import Flask
from lumenis.system.collector.adapters import secondary_collection as entry
from lumenis.system.collector.guard import task_queue
from lumenis.system.security.permission import resolve_local_workspace_principal
task_queue.DEFAULT_PATH = QUEUE_PATH
app=Flask(__name__); app.config['LUMENIS_OPEN_WORKSPACE']=True
with app.test_request_context('/', headers=HEADERS, environ_base={'REMOTE_ADDR': '127.0.0.1'}):
    actor=resolve_local_workspace_principal(module='collector', action='write')
    entry.collect_search=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('terminal task executed sources'))
    result=entry.collect_business_queries(BODY['business_requests'], actor=actor, scopes={'cth': SCOPE}, checkpoint=CHECKPOINT)
    print(json.dumps(result))
"""
    script = ('QUEUE_PATH='+repr(task_queue.DEFAULT_PATH)+'\nHEADERS='+repr(case['focus_headers'])+
              '\nBODY='+repr(body)+'\nSCOPE='+repr(case['scope'])+'\nCHECKPOINT='+repr(completed['checkpoint'])+'\n'+script)
    reopened = subprocess.check_output([sys.executable, '-c', script], env=env, text=True)
    assert json.loads(reopened.splitlines()[-1]) == expected_cached

@pytest.mark.parametrize('platform', ['xhs', 'douyin', 'x', 'instagram', 'facebook', 'wechat'])
def test_incomplete_native_detail_remains_pending(collector_case, tmp_path, monkeypatch, platform):
    case = collector_case
    path, calls, *_ = _setup(case, tmp_path, monkeypatch, platform, complete_original=False)
    result = run_due_prelaunch_baseline(config_path=str(path),
        store=ScheduleDecisionStore(str(tmp_path/'schedule.db')))
    assert len(calls) == 1 and result['summary']['failed'] == 1
    actual = next(run['result'] for run in result['runs'] if run.get('result'))
    assert actual['status'] == 'PARTIAL_SOURCE_INTAKE_PENDING'
    assert actual['source_intake']['originals_saved'] == 0
    assert actual['source_intake']['originals_pending'] == 1
    assert actual['refresh_verified'] is False


def test_committed_partial_receipt_requires_new_request_not_blind_retry(collector_case, tmp_path, monkeypatch):
    case = collector_case
    path, calls, _, _, query, _ = _setup(case, tmp_path, monkeypatch, 'x', complete_original=False)
    plan = load_prelaunch_baseline_config(str(path))['plans'][0]
    auth = maintenance_authorization(plan)
    kwargs = dict(max_results=plan.max_results, operator='prelaunch_maintenance',
        scope=case['scope'], prelaunch_local_import=True, prelaunch_authorization=auth,
        business_query=query, operation_key='isolated-owned-partial-operation')
    committed = case['surface'].collect_search('x', query.keyword, **kwargs)
    assert committed['status'] == 'PARTIAL_COMMITTED', committed
    assert committed['source_status'] == 'PARTIAL_SOURCE_INTAKE_PENDING'
    assert committed['new_collection_required'] is True and committed['retry_safe'] is False
    assert committed['canonical_synced'] == 1
    counts = _pipeline_counts(case['db_path'])
    recovered = case['surface'].collect_search('x', query.keyword, **kwargs)
    assert recovered['status'] == 'PARTIAL_COMMITTED' and recovered['commit_reconciled'] is True
    assert recovered['refresh_verified'] is False and len(calls) == 1
    assert _pipeline_counts(case['db_path']) == counts


def test_new_registered_subject_flows_through_signed_registry_plan_and_collector(
        collector_case, tmp_path, monkeypatch):
    from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
        _purpose_query,
        maintenance_authorization,
    )

    case = collector_case
    path, calls, config, save, _query, gate = _setup(case, tmp_path, monkeypatch, 'x')
    config['sources'] = []
    config['registry_expansion'] = {
        'schema_version': 1,
        'source_version': 'registered-subjects-v1',
        'scope_version': 'current-registry-v1',
        'authorization_ref': 'isolated-approved-cth-purpose-scope',
        'cadence_seconds': 3600,
        'max_results': 1,
        'templates': [{
            'domain_id': 'CTH', 'purpose': 'Review commercial venue activity',
            'dimension': 'venue_operations', 'platforms': ['x'],
            'acquisition_stage': 'SUBJECT_INTAKE',
        }],
    }
    save()
    loaded = load_prelaunch_baseline_config(str(path))
    plans = [plan for plan in loaded['plans']
             if plan.subject_id == case['scope']['subject_id']]
    assert plans
    selected = next(plan for plan in plans
                    if REGISTERED_NAME in plan.purpose_query['keyword'])
    assert selected.end_user_auto is False
    assert selected.internal_auto_opt_in is True
    request = {
        'source_url': selected.source_url,
        'platform': selected.platform,
        'scope': {'domain_id': selected.domain_id,
                  'subject_id': selected.subject_id,
                  'brand_focus_id': selected.brand_focus_id},
        'business_query': _purpose_query(selected.purpose_query),
        'max_results': selected.max_results,
    }
    assert gate.check_prelaunch_maintenance(
        maintenance_authorization(selected), **request).allowed

    now = datetime.now(timezone.utc)
    schedule = ScheduleDecisionStore(str(tmp_path / 'dynamic-schedule.db'))
    for plan in plans:
        if plan.plan_id == selected.plan_id:
            continue
        attempt, _decision = schedule.claim_public_baseline_attempt(plan, now=now)
        assert attempt
        assert schedule.finish_public_baseline_attempt(
            plan, attempt, success=True, now=now)
    result = run_due_prelaunch_baseline(
        config_path=str(path), now=now, store=schedule)
    assert result['summary']['succeeded'] == 1, result
    assert calls == [selected.source_url]
    actual = next(item['result'] for item in result['runs'] if item.get('result'))
    assert actual['scope_status'] == 'VERIFIED'
    assert actual['refresh_verified'] is True
    assert _pipeline_counts(case['db_path']) == {
        'notes': 1, 'canonical_data': 1, 'app_evidence_records': 3,
        'platform_contents': 1, 'metric_snapshots': 1,
    }


def test_pending_source_recovers_only_from_currently_signed_original_binding(
        collector_case, tmp_path, monkeypatch):
    import sqlite3

    from lumenis.importer.documents import _source_bytes
    from lumenis.system.collector.adapters import secondary_collection

    case = collector_case
    path, calls, config, save, _query, _gate = _setup(case, tmp_path, monkeypatch, 'x')
    original_source = dict(config['sources'][0])
    surface = case['surface']
    with monkeypatch.context() as scoped:
        scoped.setattr(
            surface, '_persist_collected_source_original',
            lambda *args, **kwargs: (_ for _ in ()).throw(
                ValueError('COLLECTED_SOURCE_WRITE_UNAVAILABLE')),
        )
        result = run_due_prelaunch_baseline(
            config_path=str(path), now=datetime.now(timezone.utc),
            store=ScheduleDecisionStore(str(tmp_path / 'recovery-schedule.db')))
    assert result['summary']['failed'] == 1
    collected = next(item['result'] for item in result['runs'] if item.get('result'))
    assert collected['status'] == 'PARTIAL_SOURCE_INTAKE_PENDING'
    assert collected['source_intake']['originals_pending'] == 1
    before = _pipeline_counts(case['db_path'])
    assert before['canonical_data'] == 1
    assert before['app_evidence_records'] == 3

    current_source = {
        **original_source,
        'source_key': original_source['source_key'] + ':v2',
        'source_version': 'source/v2',
        'scope_version': 'scope/v2',
        'authorization_ref': 'isolated-approved-source-v2',
        'plan_version': 'plan-v2',
    }
    config['sources'] = [current_source]
    config['plan_version'] = 'plan-v2'
    config['recovery_sources'] = []
    save()
    denied = secondary_collection.recover_prelaunch_pending_sources()
    assert denied['status'] == 'PARTIAL'
    assert denied['network_collection'] is False
    assert denied['canonical_rows_created'] == 0
    assert any(item.get('status') == 'PENDING' for item in denied['results'])
    assert _pipeline_counts(case['db_path']) == before

    config['recovery_sources'] = [original_source]
    save()
    recovered = secondary_collection.recover_prelaunch_pending_sources()
    assert recovered['status'] == 'COMPLETED', recovered
    assert recovered['saved'] == 1
    assert recovered['network_collection'] is False
    assert recovered['canonical_rows_created'] == 0
    assert calls == [original_source['source_url']]
    after = _pipeline_counts(case['db_path'])
    assert after['canonical_data'] == before['canonical_data']
    assert after['app_evidence_records'] == before['app_evidence_records'] + 2
    with sqlite3.connect(case['db_path']) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM app_evidence_records WHERE feature_id='COLLECTED_SOURCE'"
        ).fetchone()
        assert row is not None
        source_record = dict(row)
        metadata = json.loads(source_record['collection_metadata'])
        assert metadata['entity_assignment']['state'] == 'PENDING'
        assert metadata['provenance']['rights']['status'] == 'UNREVIEWED'
        source_bytes, _artifact = _source_bytes(
            connection, {**source_record, 'provenance': metadata})
        assert json.loads(source_bytes)['entity_assignment']['reason'] == (
            'SOURCE_ENTITY_IDENTITY_UNCONFIRMED')

    replayed = secondary_collection.recover_prelaunch_pending_sources()
    assert replayed['status'] == 'COMPLETED'
    assert replayed['saved'] == 0
    assert _pipeline_counts(case['db_path']) == after


def test_new_registered_bmp_brand_flows_through_signed_plan_and_collector(
        collector_case, tmp_path, monkeypatch):
    import sqlite3

    from lumenis.system.collector.adapters.base import (
        CollectionResult,
        CollectionStatus,
    )
    from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
        _purpose_query,
        maintenance_authorization,
    )
    from subject_registry import add_subject

    case = collector_case
    path, _cth_calls, config, save, _query, gate = _setup(
        case, tmp_path, monkeypatch, 'x')
    brand_name = 'Independent Brand Workshop'
    brand, created = add_subject({
        'domain_id': 'BMP', 'subject_type': 'brand',
        'name_en': brand_name, 'name_zh': brand_name,
        'industry': 'consumer products', 'keywords': [],
    })
    assert created
    config['sources'] = []
    config['registry_expansion'] = {
        'schema_version': 1,
        'source_version': 'registered-brands-v1',
        'scope_version': 'current-registry-v1',
        'authorization_ref': 'isolated-approved-bmp-purpose-scope',
        'cadence_seconds': 3600,
        'max_results': 1,
        'templates': [{
            'domain_id': 'BMP', 'purpose': 'Review registered brand market activity',
            'dimension': 'market_activity', 'platforms': ['x'],
            'acquisition_stage': 'SUBJECT_INTAKE',
        }],
    }
    save()

    spec = get_platform_fields('x')
    platform_calls = []

    class BrandTransport:
        def health_check(self, **kwargs):
            return CollectionResult(CollectionStatus.SUCCESS, 'x')

        def search(self, keyword, **kwargs):
            platform_calls.append(keyword)
            body = brand_name + ' announces a product update'
            raw = {spec.content_id: '9876543210987654321',
                   spec.published_at: '2026-10-01T08:00:00+00:00', spec.like_field: 0,
                   'detail_observation': {
                       'status': 'SUCCESS', 'body_kind': 'NATIVE_POST_BODY', 'body': body,
                   }}
            return CollectionResult(CollectionStatus.SUCCESS, 'x', raw_count=1, items=[{
                'platform_content_id': '9876543210987654321',
                'title': brand_name + ' market update', 'content': body,
                'url': 'https://x.com/status/9876543210987654321',
                'publish_datetime': '2026-10-01T08:00:00+00:00', 'raw': raw,
            }])

    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _platform: BrandTransport())
    monkeypatch.setitem(case['surface']._last_action, 'x', 0.0)
    loaded = load_prelaunch_baseline_config(str(path))
    plans = [plan for plan in loaded['plans'] if plan.brand_focus_id == brand['brand_focus_id']]
    assert plans
    selected = next(plan for plan in plans if brand_name in plan.purpose_query['keyword'])
    assert selected.domain_id == 'bmp' and selected.subject_id is None
    assert selected.end_user_auto is False
    scope = {'domain_id': 'bmp', 'subject_id': None,
             'brand_focus_id': brand['brand_focus_id']}
    assert gate.check_prelaunch_maintenance(
        maintenance_authorization(selected), source_url=selected.source_url,
        platform='x', scope=scope, business_query=_purpose_query(selected.purpose_query),
        max_results=selected.max_results).allowed

    now = datetime.now(timezone.utc)
    schedule = ScheduleDecisionStore(str(tmp_path / 'bmp-dynamic-schedule.db'))
    for plan in plans:
        if plan.plan_id == selected.plan_id:
            continue
        attempt, _decision = schedule.claim_public_baseline_attempt(plan, now=now)
        assert attempt
        assert schedule.finish_public_baseline_attempt(plan, attempt, success=True, now=now)
    result = run_due_prelaunch_baseline(config_path=str(path), now=now, store=schedule)
    assert result['summary']['succeeded'] == 1, result
    assert len(platform_calls) == 1
    actual = next(item['result'] for item in result['runs'] if item.get('result'))
    assert actual['scope_status'] == 'VERIFIED' and actual['refresh_verified'] is True
    assert _pipeline_counts(case['db_path']) == {
        'notes': 1, 'canonical_data': 1, 'app_evidence_records': 3,
        'platform_contents': 1, 'metric_snapshots': 1,
    }
    with sqlite3.connect(case['db_path']) as connection:
        product = connection.execute(
            "SELECT product_id, domain_id, brand_focus_id FROM canonical_data"
        ).fetchone()
    assert product == ('ZBMP', 'zbmp', brand['brand_focus_id'])


def test_recovery_capability_cannot_be_used_for_network_collection(collector_case, tmp_path, monkeypatch):
    case = collector_case
    path, calls, config, save, query, gate = _setup(case, tmp_path, monkeypatch, 'x')
    plan = load_prelaunch_baseline_config(str(path))['plans'][0]
    decision = gate.check_prelaunch_maintenance(maintenance_authorization(plan, recovery_only=True),
        source_url=plan.source_url, platform=plan.platform, scope=case['scope'],
        business_query=query, max_results=plan.max_results)
    assert decision.allowed is False and calls == []


def test_recovery_rechecks_revocation_after_staging_before_commit(collector_case, tmp_path, monkeypatch):
    from lumenis.system.collector.adapters import secondary_collection as owner
    case = collector_case
    path, calls, config, save, query, gate = _setup(case, tmp_path, monkeypatch, 'x')
    with monkeypatch.context() as scoped:
        scoped.setattr(owner, '_persist_collected_source_original',
            lambda *a, **k: (_ for _ in ()).throw(ValueError('COLLECTED_SOURCE_WRITE_UNAVAILABLE')))
        result = run_due_prelaunch_baseline(config_path=str(path), now=datetime.now(timezone.utc),
            store=ScheduleDecisionStore(str(tmp_path/'recover-revocation-schedule.db')))
    assert result['summary']['failed'] == 1
    before = _pipeline_counts(case['db_path'])
    original = owner._persist_pending_live_observations
    def revoke_after_stage(*args, **kwargs):
        value = original(*args, **kwargs)
        config['enabled'] = False
        save()
        return value
    monkeypatch.setattr(owner, '_persist_pending_live_observations', revoke_after_stage)
    recovered = owner.recover_prelaunch_pending_sources()
    assert recovered['saved'] == 0 and recovered['status'] == 'PARTIAL', recovered
    assert recovered['network_collection'] is False
    assert _pipeline_counts(case['db_path']) == before
    assert len(calls) == 1


def test_business_batch_http_rejects_unsupported_reference_without_collection(collector_case, monkeypatch):
    from tests.test_collector_transaction_truth import URL
    case = collector_case
    monkeypatch.setattr(case['surface'], 'collect_business_queries',
        lambda *a, **k: pytest.fail('unsupported field must be rejected before collection'))
    body = {'operator':'human','confirm_read_only':True,'reference':'uncontracted',
            'business_requests':[{'domain_id':'CTH','scope_key':case['scope']['subject_id'],
                'purpose':'Review service discussion','dimension':'venue_operations',
                'platforms':['x'],'topic_terms':['service']}]}
    response = case['client'].post(URL, headers=case['focus_headers'], json=body)
    assert response.status_code == 400
