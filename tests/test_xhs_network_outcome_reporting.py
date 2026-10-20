import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import network_adaptive
import xhs_cookie_bridge as bridge


def _synthetic_plan(keywords):
    queries = tuple(
        SimpleNamespace(
            keyword=keyword,
            product_id='CTH',
            domain_id='CTH',
            scope={
                'domain_id': 'cth',
                'subject_id': f'SUBJECT-{index}',
                'brand_focus_id': None,
                'global_scope': False,
            },
        )
        for index, keyword in enumerate(keywords)
    )
    return SimpleNamespace(
        queries=queries,
        keywords=list(keywords),
        is_runnable=True,
        to_dict=lambda: {'keywords': list(keywords)},
    )


def _run_synthetic_sync(monkeypatch, tmp_path, outcomes, search_runner=None):
    keywords = [f'synthetic-query-{index}' for index in range(len(outcomes))]
    plan = _synthetic_plan(keywords)
    monkeypatch.setattr(bridge, '_resolve_acquisition_plan', lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(bridge, 'collection_policy_gate', lambda **_kwargs: {'ok': True})
    monkeypatch.setattr(bridge, 'select_account', lambda _account: (True, 'isolated test identity'))
    monkeypatch.setattr(bridge, 'is_test_mode', lambda: True)
    monkeypatch.setattr(bridge, 'is_user_paused', lambda: None)
    monkeypatch.setattr(bridge, 'cookie_configured', lambda: True)
    monkeypatch.setattr(bridge, '_write_collection_log', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bridge, '_load_scoped_pending_analysis', lambda *_args, **_kwargs: ({}, {}, 0, []))
    monkeypatch.setattr(bridge, 'clear_circuit', lambda: None)
    monkeypatch.setattr(bridge.cache_manager, 'get_cache_status', lambda: {})
    # The scoped binder is not called when no notes are present. Bypass the
    # adapter package's eager optional integrations in this no-write test.
    adapters = ModuleType('lumenis.system.collector.adapters')
    adapters.__path__ = []
    secondary = ModuleType('lumenis.system.collector.adapters.secondary_collection')
    secondary.bind_collected_social_scope = lambda *_args, **_kwargs: {'ok': True}
    monkeypatch.setitem(sys.modules, 'lumenis.system.collector.adapters', adapters)
    monkeypatch.setitem(sys.modules, 'lumenis.system.collector.adapters.secondary_collection', secondary)
    monkeypatch.setattr(bridge.network_adaptive, 'get_adaptive_settings', lambda: {
        'current_scroll_limit': 6,
        'current_delay_seconds': 2,
        'auto_reduced': False,
    })
    health_dir = tmp_path / 'network-cache'
    monkeypatch.setattr(network_adaptive, 'HEALTH_LOG', health_dir / 'health.json')
    monkeypatch.setattr(network_adaptive, 'CACHE_DIR', health_dir)
    runner = search_runner or (
        lambda keyword, _max_scroll: dict(outcomes[keywords.index(keyword)])
    )
    monkeypatch.setattr(bridge, '_run_search', runner)

    return bridge.sync(keywords=keywords, max_scroll=1, account=bridge.XHS_RETINAUT_NAME)


def test_repeated_empty_and_success_without_new_rows_keep_network_healthy(tmp_path, monkeypatch):
    for _ in range(4):
        result = _run_synthetic_sync(
            monkeypatch,
            tmp_path,
            [{'state': 'EMPTY', 'total': 0, 'notes': []}],
        )
        health = network_adaptive._load_health()
        assert result['task_state'] == 'EMPTY'
        assert health['current_status'] == network_adaptive.NetworkStatus.NORMAL
        assert health['consecutive_failures'] == 0

    # A valid SUCCESS response can yield no inserted/updated rows (for example,
    # when the batch contains only already-seen results).
    result = _run_synthetic_sync(
        monkeypatch,
        tmp_path,
        [{'state': 'SUCCESS', 'total': 0, 'notes': []}],
    )
    health = network_adaptive._load_health()
    assert result['task_state'] == 'SUCCESS'
    assert result['inserted'] + result['updated'] == 0
    assert health['current_status'] == network_adaptive.NetworkStatus.NORMAL
    assert health['consecutive_failures'] == 0
    assert health['last_successful_collection']


def test_network_errors_accumulate_and_reach_offline(tmp_path, monkeypatch):
    for expected_failures in (1, 2, 3):
        result = _run_synthetic_sync(
            monkeypatch,
            tmp_path,
            [{'state': 'NETWORK_ERROR', 'total': 0, 'notes': [], 'error': 'synthetic timeout'}],
        )
        health = network_adaptive._load_health()
        assert result['task_state'] == 'NETWORK_ERROR'
        assert health['consecutive_failures'] == expected_failures
    assert health['current_status'] == network_adaptive.NetworkStatus.OFFLINE


def test_blocked_keywords_record_one_risk_event_per_task(tmp_path, monkeypatch):
    result = _run_synthetic_sync(
        monkeypatch,
        tmp_path,
        [
            {'state': 'BLOCKED', 'total': 0, 'notes': [], 'blocked_reason': 'SYNTHETIC_BLOCK',
             'risk_info': {'is_risk': True, 'risk_type': 'synthetic-risk', 'severity': 'high'}},
            {'state': 'CAPTCHA', 'total': 0, 'notes': [], 'blocked_reason': 'SYNTHETIC_CAPTCHA'},
        ],
    )
    health = network_adaptive._load_health()
    assert result['task_state'] == 'BLOCKED'
    assert health['current_status'] == network_adaptive.NetworkStatus.BLOCKED
    assert health['consecutive_failures'] == 1
    assert len(health['risk_events']) == 1
    assert health['risk_events'][0]['type'] == 'synthetic-risk'


def test_blocked_keyword_reduces_pacing_before_next_search(tmp_path, monkeypatch):
    seen_settings = []

    def search_runner(_keyword, _max_scroll):
        seen_settings.append(network_adaptive._load_health()['adaptive_settings'].copy())
        if len(seen_settings) == 1:
            return {
                'state': 'BLOCKED', 'total': 0, 'notes': [],
                'blocked_reason': 'SYNTHETIC_BLOCK',
                'risk_info': {
                    'is_risk': True, 'risk_type': 'synthetic-risk', 'severity': 'high',
                },
            }
        return {'state': 'SUCCESS', 'total': 0, 'notes': []}

    result = _run_synthetic_sync(
        monkeypatch,
        tmp_path,
        [{'state': 'BLOCKED'}, {'state': 'SUCCESS'}],
        search_runner=search_runner,
    )

    health = network_adaptive._load_health()
    assert result['task_state'] == 'PARTIAL_BLOCKED'
    assert seen_settings[0]['current_scroll_limit'] == 6
    assert seen_settings[1]['current_scroll_limit'] == 4
    assert seen_settings[1]['current_delay_seconds'] == 5
    assert seen_settings[1]['auto_reduced'] is True
    assert health['consecutive_failures'] == 1
    assert len(health['risk_events']) == 1


def test_empty_create_task_reports_valid_response_to_adaptive_engine(monkeypatch):
    import adaptive_engine

    bridge_module = bridge
    monkeypatch.setattr(bridge_module, '_resolve_acquisition_plan', lambda *_args: _synthetic_plan(['empty-query']))
    monkeypatch.setattr(bridge_module, 'collection_policy_gate', lambda **_kwargs: {'ok': True})
    monkeypatch.setattr(bridge_module, 'select_account', lambda _account: (True, 'synthetic identity'))
    monkeypatch.setattr(bridge_module, 'verify_account', lambda: (True, 'synthetic identity'))
    monkeypatch.setattr(bridge_module, 'is_user_paused', lambda: None)
    monkeypatch.setattr(bridge_module, 'is_test_mode', lambda: True)
    monkeypatch.setattr(bridge_module, 'record_run', lambda _run_type: None)
    monkeypatch.setattr(bridge_module, 'get_circuit_state', lambda: {'open': False})
    monkeypatch.setattr(bridge_module, 'sync', lambda *_args, **_kwargs: {
        'task_state': 'EMPTY', 'inserted': 0, 'updated': 0, 'blocked': '',
    })
    monkeypatch.setattr(bridge_module, '_shadow_record_result', lambda *_args, **_kwargs: None)

    class ImmediateThread:
        def __init__(self, *, target, **_kwargs):
            self.target = target

        def start(self):
            self.target()

    class IsolatedLock:
        def acquire(self, *, blocking):
            assert blocking is False
            return True

        def release(self):
            return None

    monkeypatch.setattr(bridge_module.threading, 'Thread', ImmediateThread)
    monkeypatch.setattr(bridge_module, '_lock', IsolatedLock())
    feedback = []
    monkeypatch.setattr(
        adaptive_engine.adaptive_engine,
        'report_collection_result',
        lambda **kwargs: feedback.append(kwargs),
    )

    task_id = bridge_module.create_task(
        keywords=['empty-query'], account=bridge_module.XHS_RETINAUT_NAME,
    )
    try:
        assert bridge_module.get_task(task_id)['status'] == 'done'
        assert len(feedback) == 1
        assert feedback[0]['success'] is True
        assert feedback[0]['notes_count'] == 0
        assert feedback[0]['error'] is None
    finally:
        bridge_module._tasks.pop(task_id, None)


def test_search_preserves_block_risk_without_reporting_before_task_summary(tmp_path, monkeypatch):
    private = tmp_path / 'private'
    profile = private / 'profiles' / 'xhs-retinaut'
    profile.mkdir(parents=True)
    cookie = private / 'xhs_cookie_retinaut.txt'
    cookie.write_text('synthetic cookie', encoding='utf-8')
    monkeypatch.setattr(bridge, 'PRIVATE_DATA_DIR', str(private))
    monkeypatch.setattr(bridge, 'DEFAULT_COLLECTION_ACCOUNT', bridge.XHS_RETINAUT_NAME)
    monkeypatch.setattr(bridge, 'XHS_RETINAUT', 'synthetic-approved-user')
    monkeypatch.setattr(bridge, 'ACCOUNT_PROFILES', {
        bridge.XHS_RETINAUT_NAME: (str(cookie), str(profile)),
    })
    monkeypatch.setattr(bridge, '_ACTIVE_ACCOUNT', None)
    monkeypatch.setattr(bridge, '_extract_user_id_from_cookie_text', lambda _text: 'synthetic-approved-user')
    monkeypatch.setattr(bridge, 'collection_policy_gate', lambda **_kwargs: {'ok': True})
    monkeypatch.setattr(bridge, 'cdp_url_for', lambda **_kwargs: 'http://127.0.0.1:9234')
    monkeypatch.setattr(bridge.time, 'sleep', lambda _seconds: None)
    health_dir = tmp_path / 'health-cache'
    monkeypatch.setattr(network_adaptive, 'HEALTH_LOG', health_dir / 'health.json')
    monkeypatch.setattr(network_adaptive, 'CACHE_DIR', health_dir)
    monkeypatch.setattr(network_adaptive, 'get_adaptive_settings', lambda: {
        'current_scroll_limit': 6,
        'current_delay_seconds': 0,
        'auto_reduced': False,
    })

    class SyntheticCompletedProcess:
        returncode = 0

        def poll(self):
            return 0

    def write_blocked_result(command, **_kwargs):
        output = Path(command[command.index('--output') + 1])
        output.write_text(json.dumps({
            'state': 'BLOCKED',
            'blocked_reason': 'SYNTHETIC_BLOCK',
            'total': 0,
            'notes': [],
        }), encoding='utf-8')
        return SyntheticCompletedProcess()

    report_calls = []
    monkeypatch.setattr(bridge.subprocess, 'Popen', write_blocked_result)
    monkeypatch.setattr(
        network_adaptive,
        'report_collection_result',
        lambda *args, **kwargs: report_calls.append((args, kwargs)),
    )

    result = bridge._run_search('synthetic query')

    assert result['state'] == 'BLOCKED'
    assert result['risk_info']['is_risk'] is True
    assert result['risk_info']['risk_type'] == 'SYNTHETIC_BLOCK'
    assert report_calls == []


def test_risk_info_is_retained_independently_of_empty_state(tmp_path, monkeypatch):
    result = _run_synthetic_sync(
        monkeypatch,
        tmp_path,
        [{'state': 'EMPTY', 'total': 0, 'notes': [],
          'risk_info': {'is_risk': True, 'risk_type': 'synthetic-risk', 'severity': 'medium'}}],
    )
    health = network_adaptive._load_health()
    assert result['task_state'] == 'EMPTY'
    assert health['current_status'] == network_adaptive.NetworkStatus.BLOCKED
    assert health['risk_events'][0]['type'] == 'synthetic-risk'
    assert health['consecutive_failures'] == 1


def test_unknown_state_is_not_treated_as_success(tmp_path, monkeypatch):
    result = _run_synthetic_sync(
        monkeypatch,
        tmp_path,
        [{'state': 'UNRECOGNIZED', 'total': 7, 'notes': [], 'error': 'synthetic unknown state'}],
    )
    health = network_adaptive._load_health()
    assert result['task_state'] == 'NETWORK_ERROR'
    assert result['state_counts'] == {'NETWORK_ERROR': 1}
    assert health['current_status'] == network_adaptive.NetworkStatus.DEGRADED
    assert health['consecutive_failures'] == 1


def test_partial_results_remain_partial_and_count_once(tmp_path, monkeypatch):
    result = _run_synthetic_sync(
        monkeypatch,
        tmp_path,
        [
            {'state': 'EMPTY', 'total': 0, 'notes': []},
            {'state': 'NETWORK_ERROR', 'total': 0, 'notes': [], 'error': 'synthetic timeout'},
        ],
    )
    health = network_adaptive._load_health()
    assert result['task_state'] == 'PARTIAL_BLOCKED'
    assert health['current_status'] == network_adaptive.NetworkStatus.DEGRADED
    assert health['consecutive_failures'] == 1
