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
