"""Signed public service grants survive restart without granting user writes."""
import hashlib
import hmac
import json

import pytest

from lumenis.system.security import permission
from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
    _canonical_config, load_prelaunch_baseline_config, maintenance_authorization,
)


@pytest.fixture
def signed_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(permission, '_TESTING_BYPASS_ENABLED', False)
    monkeypatch.setenv('PERMISSION_GATE_TESTING', '0')
    monkeypatch.setenv('LUMENIS_PRELAUNCH_BASELINE_HMAC_KEY', 'isolated-test-key')
    path = tmp_path / 'plan.json'
    monkeypatch.setenv('LUMENIS_PRELAUNCH_BASELINE_CONFIG', str(path))
    data = {
        'schema_version': 1, 'plan_version': 'prelaunch-v1',
        'policy_id': 'public-read-only-exact-import-v1', 'enabled': True,
        'end_user_auto': False, 'sources': [{
            'source_key': 'official-news', 'source_version': 'v1',
            'platform': 'public_http', 'source_url': 'https://example.org/news',
            'domain_id': 'bmp', 'brand_focus_id': 'brand-1',
            'scope_version': 'v18', 'cadence_seconds': 86400,
            'authorization_ref': 'owner-explicit-prelaunch-public-baseline',
        }],
    }
    def save():
        data['hmac'] = {'algorithm': 'HMAC-SHA256', 'value': hmac.new(
            b'isolated-test-key', _canonical_config(data), hashlib.sha256).hexdigest()}
        path.write_text(json.dumps(data), encoding='utf-8')
    save()
    plan = load_prelaunch_baseline_config(str(path))['plans'][0]
    auth = maintenance_authorization(plan)
    request = {'source_url': plan.source_url, 'platform': plan.platform,
               'scope': {'domain_id': 'bmp', 'subject_id': None, 'brand_focus_id': 'brand-1'}}
    return path, data, save, auth, request


def test_service_grant_survives_gate_restart_without_human_tokens(signed_plan):
    _, _, _, auth, request = signed_plan
    for gate in (permission.PermissionGate(), permission.PermissionGate()):
        assert gate.check_prelaunch_maintenance(auth, **request).allowed
        assert not gate.has_permission(permission.PermissionLevel.COMMIT)
        assert not gate._approvals
        assert not gate.check(
            permission.OperationType.DATA_IMPORT, 'another-write', domain_id='bmp',
        ).allowed


@pytest.mark.parametrize('change', ['url', 'brand', 'domain', 'platform'])
def test_service_grant_cannot_expand_scope(signed_plan, change):
    _, _, _, auth, request = signed_plan
    if change == 'url': request['source_url'] += '/other'
    if change == 'brand': request['scope']['brand_focus_id'] = 'brand-2'
    if change == 'domain': request['scope'] = {'domain_id': 'cth', 'subject_id': 'subject-1'}
    if change == 'platform': request['platform'] = 'xhs'
    assert not permission.PermissionGate().check_prelaunch_maintenance(auth, **request).allowed


@pytest.mark.parametrize('change', ['disable', 'tamper', 'missing', 'key_missing', 'test_bypass'])
def test_reused_token_cannot_outlive_revocation_or_invalid_config(signed_plan, monkeypatch, change):
    path, data, save, auth, request = signed_plan
    gate = permission.PermissionGate()
    assert gate.check_prelaunch_maintenance(auth, **request).allowed
    if change == 'disable':
        data['enabled'] = False
        save()
    elif change == 'tamper':
        data['sources'][0]['authorization_ref'] = 'tampered'
        path.write_text(json.dumps(data), encoding='utf-8')
    elif change == 'missing': path.unlink()
    elif change == 'key_missing': monkeypatch.delenv('LUMENIS_PRELAUNCH_BASELINE_HMAC_KEY')
    else: monkeypatch.setenv('PERMISSION_GATE_TESTING', '1')
    assert not gate.check_prelaunch_maintenance(auth, **request).allowed


def test_revocation_during_fetch_stops_before_raw_evidence_or_canonical_writes(
        signed_plan, monkeypatch):
    path, data, save, auth, request = signed_plan
    from lumenis.system import security
    from lumenis.system.collector.adapters import secondary_collection as surface
    from lumenis.system.collector.adapters import multi_platform_import
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus

    writes = []
    gate = permission.PermissionGate()
    monkeypatch.setattr(security, 'get_permission_gate', lambda: gate)
    monkeypatch.setattr(surface, '_validate_prelaunch_registry', lambda _scope: None)
    monkeypatch.setattr(surface, '_adapter_health', lambda *_args, **_kwargs: {
        'status': 'SUCCESS', 'ready': True, 'can_attempt': True,
    })
    monkeypatch.setitem(surface._last_action, 'public_http', 0.0)

    class RevokingAdapter:
        def search(self, _source, **_kwargs):
            data['enabled'] = False
            save()
            return CollectionResult(
                status=CollectionStatus.SUCCESS, platform='public_http', raw_count=1,
                items=[{'platform_content_id': 'fixture-post',
                        'title': 'Fixture source result', 'content': 'Candidate body',
                        'url': 'https://example.org/items/fixture-post'}],
            )

    monkeypatch.setattr(surface, '_get_runtime_adapter', lambda _platform: RevokingAdapter())
    monkeypatch.setattr(multi_platform_import, 'import_multi_platform_records',
                        lambda *_args, **_kwargs: writes.append('raw-or-canonical'))
    monkeypatch.setattr(surface, '_write_prelaunch_evidence',
                        lambda *_args, **_kwargs: writes.append('evidence'))
    monkeypatch.setattr(surface, '_write_evidence',
                        lambda *_args, **_kwargs: writes.append('evidence'))
    monkeypatch.setattr(surface, '_persist_prelaunch_scope',
                        lambda *_args, **_kwargs: writes.append('canonical-scope'))

    result = surface.collect_search(
        request['platform'], request['source_url'], max_results=1,
        operator='prelaunch_maintenance', scope=request['scope'], actor=None,
        prelaunch_local_import=True, prelaunch_authorization=auth,
    )

    assert result['status'] == 'SCOPE_UNAUTHORIZED'
    assert result['ok'] is False
    assert writes == []
