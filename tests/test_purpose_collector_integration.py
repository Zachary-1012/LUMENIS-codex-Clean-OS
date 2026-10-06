"""Signed purpose plans reach the real Collector, Permission and five-table write.

Only platform transport is simulated. Synthetic posts are not live coverage.
"""
import hashlib
import hmac
import json
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


def _setup(case, tmp_path, monkeypatch, platform, *, revoke=False):
    from lumenis.system import security
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
                'content': REGISTERED_NAME + ' service opening information',
                'url': 'https://public.example.test/post/' + identity,
                'publish_datetime': '2026-10-01T08:00:00+00:00',
                'raw': {spec.content_id: identity, spec.published_at: '2026-10-01T08:00:00+00:00',
                        spec.like_field: 0},
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
        'notes': 1, 'canonical_data': 1, 'app_evidence_records': 1,
        'platform_contents': 1, 'metric_snapshots': 1,
    }
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
