# -*- coding: utf-8 -*-
"""当前生产采集边界：只允许香港/国际 RedNote，不触发真实平台。"""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def test_bridge_defaults_to_hk_collection_identity(monkeypatch):
    import cdp_helper
    import xhs_cookie_bridge as bridge

    monkeypatch.setattr(bridge, '_ACTIVE_ACCOUNT', None)
    monkeypatch.delenv('XHS_COOKIE_FILE_OVERRIDE', raising=False)
    monkeypatch.setattr(cdp_helper, 'resolve_registered_xhs_worker',
                        lambda **_kwargs: {'available': False,
                                           'code': 'XHS_REGISTERED_WORKER_UNAVAILABLE'})
    assert bridge._canonical_account_name() == bridge.XHS_RETINAUT_NAME
    assert bridge.DEFAULT_CDP_PORT == 0
    assert bridge.ACCOUNT_CDP_PORTS[bridge.XHS_RETINAUT_NAME] is None
    assert bridge.cdp_port_for() is None
    assert bridge.cdp_url_for() == ''
    assert bridge.home_url_for().startswith('https://www.rednote.com')
    assert bridge.collection_policy_gate(account=bridge.XHS_RETINAUT_NAME)['ok'] is True


def test_bridge_blocks_mainland_before_platform_request(monkeypatch):
    import xhs_cookie_bridge as bridge

    monkeypatch.setattr(bridge, '_resolve_acquisition_plan', lambda *_: SimpleNamespace(
        is_runnable=True, keywords=('广州太古汇',),
        queries=(SimpleNamespace(domain_id='CTH'),),
        to_dict=lambda: {'status': 'READY'},
    ))

    def forbidden(*_args, **_kwargs):
        raise AssertionError('Blocked personal account must not be selected or probed')

    monkeypatch.setattr(bridge, 'select_account', forbidden)

    result = bridge.sync(keywords=['广州太古汇'], account=bridge.XHS_CN_PRIMARY_NAME)
    assert result['ok'] is False
    assert result['task_state'] == 'POLICY_BLOCKED'
    assert result['collection_policy']['code'] == 'account_paused'


def test_collector_blocks_cn_before_subprocess(monkeypatch):
    import collector

    def fail_if_called(*args, **kwargs):
        raise AssertionError('策略阻断前不应启动任何采集子进程')

    monkeypatch.setattr(collector.subprocess, 'run', fail_if_called)
    result = collector.search_xiaohongshu('广州太古汇', region='cn')
    assert result['channel'] == 'policy'
    assert result['error'] in ('account_paused', 'region_paused')
    assert result['total'] == 0


def test_collector_default_artifact_path_is_protected(monkeypatch):
    """显式远程 worker 可用时，默认原始产物只能写入受保护运行数据目录。"""
    import collector
    import xhs_cookie_bridge as bridge

    seen = {}
    worker = 'https://browser-worker.example:9234'

    monkeypatch.setattr(collector, '_resolve_server_cdp_url', lambda cdp_url=None, **kwargs: (worker, ''))
    monkeypatch.setattr(collector, '_cdp_online', lambda **kwargs: True)
    monkeypatch.setattr(collector, 'CDP_SCRIPT', collector.__file__)
    monkeypatch.setattr(collector.os, 'makedirs', lambda *args, **kwargs: None)

    def fake_worker(keyword, max_scroll, output_path, **kwargs):
        seen['output_path'] = output_path
        seen['cdp_url'] = kwargs.get('cdp_url')
        return {'keyword': keyword, 'total': 0, 'notes': [],
                'error': '', 'channel': 'cdp', 'ok': True}

    monkeypatch.setattr(collector, '_search_via_cdp', fake_worker)
    result = collector.search_xiaohongshu(
        '广州太古汇', account=bridge.DEFAULT_COLLECTION_ACCOUNT)

    assert Path(seen['output_path']).parent == Path(bridge.PRIVATE_DATA_DIR)
    assert seen['cdp_url'] == worker
    assert result['channel'] == 'registered_system_browser_worker'


def test_collector_without_explicit_worker_fails_closed_before_collection(monkeypatch):
    """无 server-owned worker 时不得回退到 localhost 或独立浏览器。"""
    import collector
    import xhs_cookie_bridge as bridge

    monkeypatch.setattr(
        collector, '_resolve_server_cdp_url',
        lambda cdp_url=None, **kwargs: ('', 'COLLECTOR_ENDPOINT_NOT_CONFIGURED'),
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError('未配置远程 worker 时不应进入任何采集实现')

    monkeypatch.setattr(collector, '_search_via_cdp', fail_if_called)
    monkeypatch.setattr(collector, '_search_standalone', fail_if_called)

    result = collector.search_xiaohongshu(
        '广州太古汇', account=bridge.DEFAULT_COLLECTION_ACCOUNT)
    assert result['total'] == 0
    assert result['channel'] == 'worker'
    assert result['error'] == 'COLLECTOR_ENDPOINT_NOT_CONFIGURED'


def test_collect_all_returns_stable_tuple_when_kind_blocked():
    import collector

    notes, results = collector.collect_all(keywords=['广州太古汇'], kind='event')
    assert notes == []
    assert results and results[0]['error'] == 'KIND_POLICY_BLOCKED'


def test_p0_orchestrator_blocks_cn_before_select():
    import xhs_cookie_bridge as bridge
    import xhs_p0_orchestrator as orchestrator

    result = orchestrator.trigger_collection(account_name=bridge.XHS_CN_PRIMARY_NAME)
    assert result['ok'] is False
    assert result['code'] == 'account_paused'


def test_private_v2_client_never_reaches_network():
    from lumenis.system.collector.runtime.xhs.client import XHSClient

    async def invoke():
        with pytest.raises(RuntimeError, match='非生产路径'):
            await XHSClient(cookie='test').request('GET', 'https://edith.xiaohongshu.com/test')

    asyncio.run(invoke())


def test_guardian_recovery_uses_hk_resident_launcher(monkeypatch):
    """Guardian recovery uses the registered worker launcher, not a fixed port."""
    import auto_recovery as recovery

    calls = []

    def fake_popen(args, **kwargs):
        calls.append((list(args), kwargs))
        return object()

    engine = recovery.AutoRecoveryEngine()
    monkeypatch.setattr(recovery, '_production_cdp_config', lambda: {
        'account': 'XHS_RETINAUT', 'port': None, 'endpoint': '', 'home': '',
        'authorization_ready': True, 'available': False,
        'code': 'XHS_REGISTERED_WORKER_UNAVAILABLE',
    })
    monkeypatch.setattr(recovery.subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(recovery.time, 'sleep', lambda _seconds: None)
    monkeypatch.setattr(engine, 'check_cdp', lambda: True)

    ok, message = engine.fix_cdp_crash()

    assert ok is True
    assert 'XHS_RETINAUT' in message
    assert '9222' not in message and '9223' not in message
    assert calls
    args, kwargs = calls[0]
    assert args[-2:] == ['--account', 'XHS_RETINAUT']
    assert Path(args[-3]).parts[-2:] == ('scripts', 'start_resident_browsers.py')
    assert '9222' not in ' '.join(args)
    assert '9223' not in ' '.join(args)
    assert kwargs['cwd'] == engine.root_dir


def test_guardian_does_not_recover_without_current_registered_identity(monkeypatch):
    import auto_recovery as recovery

    calls = []
    engine = recovery.AutoRecoveryEngine()
    monkeypatch.setattr(recovery, '_production_cdp_config', lambda: {
        'account': None, 'port': None, 'endpoint': '', 'home': '',
        'authorization_ready': False, 'available': False,
        'code': 'COLLECTION_ACCOUNT_UNAVAILABLE',
    })
    monkeypatch.setattr(recovery.subprocess, 'Popen', lambda *args, **kwargs: calls.append(args))

    ok, message = engine.fix_cdp_crash()

    assert ok is False
    assert 'COLLECTION_ACCOUNT_UNAVAILABLE' in message
    assert calls == []


def test_guardian_health_uses_registered_worker_state_not_port_probe(monkeypatch):
    import auto_recovery as recovery

    config = {
        'account': 'XHS_RETINAUT', 'port': 9234,
        'endpoint': 'http://127.0.0.1:9234', 'home': '',
        'authorization_ready': True, 'available': True, 'code': '',
    }
    monkeypatch.setattr(recovery, '_production_cdp_config', lambda: config)
    engine = recovery.AutoRecoveryEngine()

    def forbidden_port_probe(*_args, **_kwargs):
        raise AssertionError('Guardian must not accept an unowned listening port')

    monkeypatch.setattr(engine, 'check_port', forbidden_port_probe)
    assert engine.check_cdp() is True

    config['available'] = False
    config['code'] = 'XHS_WORKER_IDENTITY_UNVERIFIED'
    assert engine.check_cdp() is False


def test_guardian_config_binds_dynamic_endpoint_to_current_allowlist(monkeypatch):
    import auto_recovery as recovery
    import cdp_helper
    import xhs_cookie_bridge as bridge

    account = bridge.XHS_RETINAUT_NAME
    monkeypatch.setattr(bridge, 'DEFAULT_COLLECTION_ACCOUNT', account)
    monkeypatch.setattr(bridge, 'XHS_RETINAUT', 'approved-synthetic-id')
    monkeypatch.setattr(bridge, 'ALLOWED_USER_IDS', ('approved-synthetic-id',))
    monkeypatch.setattr(bridge, 'collection_policy_gate',
                        lambda **_kwargs: {'ok': True, 'account': account, 'region': 'intl'})
    monkeypatch.setattr(bridge, 'home_url_for', lambda _account: 'https://www.rednote.com')
    monkeypatch.setattr(cdp_helper, '_registered_xhs_binding',
                        lambda _account: {'account': account, 'profile': '<registered-profile>'})
    monkeypatch.setattr(cdp_helper, 'resolve_registered_xhs_worker', lambda **_kwargs: {
        'available': True, 'account': account, 'port': 9234,
        'endpoint': 'http://127.0.0.1:9234', 'headless': True, 'loopback_only': True,
    })

    config = recovery._production_cdp_config()

    assert config['authorization_ready'] is True
    assert config['available'] is True
    assert config['endpoint'] == 'http://127.0.0.1:9234'
    assert config['port'] == 9234

    monkeypatch.setattr(bridge, 'ALLOWED_USER_IDS', ())
    denied = recovery._production_cdp_config()
    assert denied['authorization_ready'] is False
    assert denied['available'] is False
    assert denied['port'] is None


def test_is_cdp_open_requires_an_explicit_owner_resolved_port(monkeypatch):
    from lumenis.adapters import human_browser

    def forbidden_probe(*_args, **_kwargs):
        raise AssertionError('Missing port must not probe a historical endpoint')

    monkeypatch.setattr(human_browser.socket, 'socket', forbidden_probe)
    assert human_browser.is_cdp_open() is False
    assert human_browser.is_cdp_open(port=None) is False
    assert human_browser.is_cdp_open(port=0) is False
    assert human_browser.is_cdp_open(port='not-a-port') is False


def test_is_cdp_open_checks_only_the_explicit_port(monkeypatch):
    from lumenis.adapters import human_browser

    addresses = []

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def settimeout(self, _timeout):
            pass

        def connect_ex(self, address):
            addresses.append(address)
            return 0

    monkeypatch.setattr(human_browser.socket, 'socket', lambda *_args: FakeSocket())
    assert human_browser.is_cdp_open(port=9234) is True
    assert addresses == [('127.0.0.1', 9234)]


def test_bridge_status_projection_omits_worker_binding_and_identity(monkeypatch, tmp_path):
    """The status authority reports availability without serializing local bindings."""
    import json

    import cdp_helper
    import xhs_cookie_bridge as bridge

    account = bridge.XHS_RETINAUT_NAME
    cookie_file = tmp_path / 'xhs_cookie_retinaut.txt'
    cookie_file.write_text('synthetic-cookie-marker', encoding='utf-8')
    profile = tmp_path / 'profiles' / 'xhs-retinaut'
    profile.mkdir(parents=True)

    monkeypatch.setattr(bridge, 'PRIVATE_DATA_DIR', str(tmp_path))
    monkeypatch.setattr(bridge, 'DEFAULT_COLLECTION_ACCOUNT', account)
    monkeypatch.setattr(bridge, '_ACTIVE_ACCOUNT', account)
    monkeypatch.setattr(bridge, 'XHS_RETINAUT', 'synthetic-approved-user-id')
    monkeypatch.setattr(bridge, 'ALLOWED_USER_IDS', {'synthetic-approved-user-id'})
    monkeypatch.setitem(bridge.ACCOUNT_PROFILES, account,
                        (str(cookie_file), str(profile)))
    monkeypatch.setattr(
        bridge, 'collection_policy_gate',
        lambda account=None, region='intl': {
            'ok': True, 'account': account, 'region': region,
            'policy_version': 'synthetic-policy',
        },
    )
    monkeypatch.setattr(
        cdp_helper, '_registered_xhs_binding',
        lambda _account: {'profile': str(profile)},
    )
    monkeypatch.setattr(
        cdp_helper, 'resolve_registered_xhs_worker',
        lambda **_kwargs: {
            'available': True, 'port': 9234,
            'endpoint': 'http://127.0.0.1:9234',
        },
    )

    status = bridge.get_account_status()
    serialized = json.dumps(status)

    assert status['worker_available'] is True
    assert status['cookie_configured'] is True
    for private_value in (
        str(cookie_file), str(profile), 'synthetic-cookie-marker',
        'synthetic-approved-user-id', 'http://127.0.0.1:9234', '9234',
    ):
        assert private_value not in serialized


def test_system_health_uses_safe_registered_worker_contract(monkeypatch, tmp_path):
    """Health uses the session owner's dynamic worker state without exposing its endpoint."""
    import system_health_api as health
    import xhs_cookie_bridge as bridge

    monkeypatch.setattr(health, 'get_data_dir', lambda: str(tmp_path))
    monkeypatch.setattr(bridge, 'get_account_status', lambda account=None: {
        'active_account': bridge.XHS_RETINAUT_NAME,
        'collection_policy': {'ok': True, 'region': 'intl'},
        'worker_available': True,
        'cookie_configured': True,
        'cdp_port': 9234,
        'cdp_url': 'http://127.0.0.1:9234',
        'profile_path': 'private-profile',
    })

    result = health.check_collector()

    assert result['collection_account'] == 'XHS_RETINAUT'
    assert result['collection_region'] == 'intl'
    assert result['cdp_running'] is True
    assert result['browser_worker_state'] == 'REGISTERED_BACKGROUND'
    assert result['cookie_configured'] is True
    assert not {'cdp_port', 'cdp_url', 'profile_path'} & result.keys()


def _system_health_login_fixture(monkeypatch, tmp_path, *, session_state,
                                 recent_collect=False, create_notes=True):
    import sqlite3

    import system_health_api as health
    import xhs_cookie_bridge as bridge

    db_path = tmp_path / 'isolated-health.sqlite3'
    with sqlite3.connect(db_path) as connection:
        if create_notes:
            connection.execute('CREATE TABLE notes (collected_at TEXT)')
            if recent_collect:
                connection.execute(
                    "INSERT INTO notes VALUES (datetime('now', '-1 day', 'localtime'))"
                )

    monkeypatch.setattr(health, 'get_db_path', lambda: str(db_path))
    monkeypatch.setattr(bridge, 'get_account_status', lambda account=None: {
        'active_account': bridge.XHS_RETINAUT_NAME,
        'collection_policy': {'ok': True, 'region': 'intl'},
        'worker_available': True,
        'cookie_configured': True,
        'accounts': [{
            'account': bridge.XHS_RETINAUT_NAME,
            'session_state': session_state,
        }],
    })
    return health


def test_recent_collection_history_does_not_prove_current_login(monkeypatch, tmp_path):
    health = _system_health_login_fixture(
        monkeypatch, tmp_path, session_state='NOT_VERIFIED', recent_collect=True
    )

    result = health.check_login_status()

    assert result['recent_7d_collects'] == 1
    assert result['cookie_file_exists'] is True
    assert result['status'] == 'unknown'


def test_synthetic_current_session_is_reported_independently_of_zero_history(
        monkeypatch, tmp_path):
    health = _system_health_login_fixture(
        monkeypatch, tmp_path, session_state='real_session_valid'
    )

    result = health.check_login_status()

    assert result['recent_7d_collects'] == 0
    assert result['status'] == 'ok'


def test_no_history_and_no_current_session_remains_unknown(monkeypatch, tmp_path):
    health = _system_health_login_fixture(
        monkeypatch, tmp_path, session_state='NOT_VERIFIED'
    )

    result = health.check_login_status()

    assert result['recent_7d_collects'] == 0
    assert result['status'] == 'unknown'


def test_history_query_failure_is_not_misreported_as_zero(monkeypatch, tmp_path):
    health = _system_health_login_fixture(
        monkeypatch, tmp_path, session_state='NOT_VERIFIED', create_notes=False
    )

    result = health.check_login_status()

    assert result['recent_7d_collects'] is None
    assert result['status'] == 'unknown'
    assert result['message'] == '采集历史读取失败: OperationalError'


def test_health_aggregates_do_not_promote_unknown_login_to_healthy(monkeypatch):
    from flask import Flask

    import system_health_api as health
    import lumenis.shared.evidence.store as evidence_store

    monkeypatch.setattr(health, 'check_database', lambda: {
        'status': 'ok', 'notes_count': 1, 'recent_24h': 1,
    })
    monkeypatch.setattr(health, '_check_db_writable_fast', lambda: {
        'status': 'ok', 'writable': True,
    })
    monkeypatch.setattr(health, 'check_collector', lambda: {
        'status': 'ok', 'cdp_running': True, 'cookie_configured': True,
        'today_runs': 1, 'remaining_runs': 11,
    })
    monkeypatch.setattr(health, 'check_login_status', lambda: {
        'status': 'unknown', 'recent_7d_collects': 1,
        'cookie_file_exists': True,
    })
    monkeypatch.setattr(health, 'get_alerts', lambda: {
        'active_alerts': 0, 'need_manual_intervention': 0,
        'recent_alerts': [], 'latest_alert': None,
    })
    monkeypatch.setattr(health, 'get_collection_schedule', lambda: {'next_collect': ''})
    monkeypatch.setattr(health, 'get_adaptive_status', lambda: {})
    monkeypatch.setattr(evidence_store, 'get_evidence_write_failure_count', lambda _hours: 0)
    for name in (
        'check_dedup_module', 'check_subject_filter', 'check_risk_engine',
        'check_report_generator', 'check_wechat_push', 'check_email_push',
        'check_scheduler',
    ):
        monkeypatch.setattr(health, name, lambda: {'status': 'ok'})

    app = Flask(__name__)
    app.register_blueprint(health.system_health_bp)
    client = app.test_client()

    summary = client.get('/api/system/health/summary').get_json()
    assert summary['sub_lights']['auth']['light'] == 'unknown'
    assert summary['overall_status'] == 'warning'
    assert any('历史记录' in hint for hint in summary['diagnostic_hints'])

    detailed = client.get('/api/system/health/detailed').get_json()
    assert detailed['modules']['login_status']['status'] == 'unknown'
    assert detailed['status_counts']['unknown'] == 1
    assert detailed['overall_status'] == 'warning'


def _system_health_schedule_fixture(monkeypatch, tmp_path, *, notes=(), runs=None,
                                    task_runs=None):
    import json
    import sqlite3
    from datetime import datetime

    import system_health_api as health

    db_path = tmp_path / 'isolated-schedule.sqlite3'
    with sqlite3.connect(db_path) as connection:
        if notes is not None:
            connection.execute('CREATE TABLE notes (collected_at TEXT)')
            for collected_at in notes:
                if collected_at is None:
                    connection.execute(
                        "INSERT INTO notes VALUES (datetime('now','localtime'))"
                    )
                else:
                    connection.execute(
                        'INSERT INTO notes VALUES (?)', (collected_at,)
                    )
        if runs is not None:
            connection.execute(
                'CREATE TABLE collection_logs '
                '(status TEXT, started_at TEXT, finished_at TEXT)'
            )
            connection.executemany(
                "INSERT INTO collection_logs VALUES (?, "
                "datetime('now','localtime'), datetime('now','localtime'))",
                [(status,) for status in runs],
            )
    monkeypatch.setattr(health, 'get_db_path', lambda: str(db_path))
    monkeypatch.setattr(health, 'get_data_dir', lambda: str(tmp_path))
    if task_runs is not None:
        (tmp_path / 'collector_stats.json').write_text(json.dumps({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'daily_runs': task_runs,
            'daily_run_history_state': 'OBSERVED_TASK_STARTS',
        }), encoding='utf-8')
    return health


def test_schedule_separates_notes_from_keyword_observations_and_unknown_task_runs(
        monkeypatch, tmp_path):
    health = _system_health_schedule_fixture(
        monkeypatch, tmp_path,
        notes=[None],
        runs=['SUCCESS', 'EMPTY'],
    )

    result = health.get_collection_schedule()

    assert result['today_collected_notes'] == 1
    assert result['today_runs'] is None
    assert result['today_keyword_observations'] == 2
    assert result['last_24h_failures'] is None
    assert result['last_24h_unknown_runs'] is None
    assert result['last_24h_failed_keyword_observations'] == 0
    assert result['last_24h_degraded_keyword_observations'] == 0
    assert result['last_24h_unknown_keyword_observations'] == 0
    assert result['next_collect'] is None


def test_one_task_with_many_keywords_counts_one_run_and_many_observations(
        monkeypatch, tmp_path):
    import time

    health = _system_health_schedule_fixture(
        monkeypatch, tmp_path,
        notes=[], runs=['SUCCESS'] * 19 + ['BLOCKED'],
        task_runs=[time.time()],
    )

    result = health.get_collection_schedule()

    assert result['today_runs'] == 1
    assert result['today_keyword_observations'] == 20
    assert result['last_24h_failures'] is None
    assert result['last_24h_failed_keyword_observations'] == 0
    assert result['last_24h_degraded_keyword_observations'] == 1


def test_collector_task_start_stats_are_marked_as_observed(monkeypatch, tmp_path):
    import json
    import xhs_cookie_bridge as bridge

    monkeypatch.setattr(bridge, 'STATS_FILE', str(tmp_path / 'collector_stats.json'))
    monkeypatch.setattr(bridge, '_stats_loaded', True)
    monkeypatch.setattr(bridge, '_daily_runs', [])
    monkeypatch.setattr(bridge, '_daily_manual_runs', 0)
    monkeypatch.setattr(bridge, '_daily_auto_runs', 0)
    monkeypatch.setattr(bridge, '_last_run_time', None)
    monkeypatch.setattr(bridge, '_daily_run_history_state', 'OBSERVED_TASK_STARTS')

    bridge.record_run('manual')

    stats = json.loads((tmp_path / 'collector_stats.json').read_text(encoding='utf-8'))
    assert stats['daily_run_history_state'] == 'OBSERVED_TASK_STARTS'
    assert len(stats['daily_runs']) == 1


def test_unverified_task_history_does_not_turn_keyword_logs_into_task_runs(
        monkeypatch, tmp_path):
    import json
    import sqlite3
    import time
    from datetime import datetime
    import system_health_api as health

    db_path = tmp_path / 'isolated-schedule.sqlite3'
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            'CREATE TABLE collection_logs (status TEXT, started_at TEXT, finished_at TEXT)'
        )
        connection.executemany(
            "INSERT INTO collection_logs VALUES (?, datetime('now','localtime'), datetime('now','localtime'))",
            [('SUCCESS',)] * 20,
        )
    (tmp_path / 'collector_stats.json').write_text(json.dumps({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'daily_runs': [time.time() for _ in range(4)],
        'daily_run_history_state': 'UNKNOWN',
    }), encoding='utf-8')
    monkeypatch.setattr(health, 'get_db_path', lambda: str(db_path))
    monkeypatch.setattr(health, 'get_data_dir', lambda: str(tmp_path))

    result = health.get_collection_schedule()

    assert result['today_runs'] is None
    assert result['today_keyword_observations'] == 20


def test_schedule_counts_explicit_failure_records(monkeypatch, tmp_path):
    health = _system_health_schedule_fixture(
        monkeypatch, tmp_path, notes=[],
        runs=['SUCCESS', 'BLOCKED', 'AUTH_FAILED', 'NETWORK_ERROR'],
    )

    result = health.get_collection_schedule()

    assert result['today_collected_notes'] == 0
    assert result['today_runs'] is None
    assert result['today_keyword_observations'] == 4
    assert result['last_24h_failures'] is None
    assert result['last_24h_unknown_runs'] is None
    assert result['last_24h_failed_keyword_observations'] == 2
    assert result['last_24h_degraded_keyword_observations'] == 1
    assert result['last_24h_unknown_keyword_observations'] == 0


def test_schedule_missing_run_records_are_unknown_not_zero(monkeypatch, tmp_path):
    health = _system_health_schedule_fixture(
        monkeypatch, tmp_path, notes=[], runs=None
    )

    result = health.get_collection_schedule()

    assert result['today_collected_notes'] == 0
    assert result['today_runs'] is None
    assert result['last_24h_failures'] is None
    assert result['last_24h_unknown_runs'] is None


def test_schedule_unrecognized_run_status_is_not_called_success_or_failure(
        monkeypatch, tmp_path):
    health = _system_health_schedule_fixture(
        monkeypatch, tmp_path, notes=[], runs=['ACCEPTED']
    )

    result = health.get_collection_schedule()

    assert result['today_runs'] is None
    assert result['today_keyword_observations'] == 1
    assert result['last_24h_failures'] is None
    assert result['last_24h_unknown_runs'] is None
    assert result['last_24h_failed_keyword_observations'] == 0
    assert result['last_24h_degraded_keyword_observations'] == 0
    assert result['last_24h_unknown_keyword_observations'] == 1


def test_schedule_classifies_canonical_degraded_and_failed_statuses(
        monkeypatch, tmp_path):
    health = _system_health_schedule_fixture(
        monkeypatch, tmp_path, notes=[],
        runs=[
            'NEED_VERIFY', 'SESSION_EXPIRED', 'COOLING_DOWN', 'RISK_WARNING',
            'COLLECT_ERROR', 'ACCEPTED',
        ],
    )

    result = health.get_collection_schedule()

    assert result['today_runs'] is None
    assert result['today_keyword_observations'] == 6
    assert result['last_24h_failed_keyword_observations'] == 2
    assert result['last_24h_degraded_keyword_observations'] == 3
    assert result['last_24h_unknown_keyword_observations'] == 1


def test_schedule_missing_database_keeps_counts_unknown(monkeypatch, tmp_path):
    import system_health_api as health

    monkeypatch.setattr(health, 'get_db_path', lambda: str(tmp_path / 'absent.sqlite3'))

    result = health.get_collection_schedule()

    assert result['today_collected_notes'] is None
    assert result['today_runs'] is None
    assert result['today_keyword_observations'] is None
    assert result['last_24h_failures'] is None


def test_scheduler_status_uses_current_thread_observation(monkeypatch):
    import threading

    import system_health_api as health

    with monkeypatch.context() as isolated_patch:
        isolated_patch.setattr(threading, 'enumerate', lambda: [
            SimpleNamespace(name='scheduler', is_alive=lambda: True),
        ])
        result = health.check_scheduler()

    assert result['status'] == 'ok'
    assert result['scheduler_started'] is True
    assert result['auto_collect_hours'] is None
    assert result['daily_auto_runs'] is None


def test_missing_scheduler_thread_is_unknown(monkeypatch):
    import threading

    import system_health_api as health

    with monkeypatch.context() as isolated_patch:
        isolated_patch.setattr(threading, 'enumerate', lambda: [])
        result = health.check_scheduler()

    assert result['status'] == 'unknown'
    assert result['scheduler_started'] is None
    assert result['auto_collect_hours'] is None
    assert result['daily_auto_runs'] is None


def test_scheduler_observation_failure_is_not_reported_as_running(monkeypatch):
    import threading

    import system_health_api as health

    def fail_enumeration():
        raise RuntimeError('synthetic thread-list failure')

    with monkeypatch.context() as isolated_patch:
        isolated_patch.setattr(threading, 'enumerate', fail_enumeration)
        result = health.check_scheduler()

    assert result['status'] == 'error'
    assert result['scheduler_started'] is None


def test_missing_adaptive_status_does_not_invent_defaults(monkeypatch, tmp_path):
    import system_health_api as health

    monkeypatch.setattr(health, '__file__', str(tmp_path / 'system_health_api.py'))

    result = health.get_adaptive_status()

    assert result['adaptive_engine_exists'] is False
    assert result['current_strategy'] is None
    assert result['recent_success_rate'] is None
    assert result['current_delay_seconds'] is None
    assert result['risk_level'] is None


def test_partial_adaptive_status_preserves_unknown_fields(monkeypatch, tmp_path):
    import json

    import system_health_api as health

    monkeypatch.setattr(health, '__file__', str(tmp_path / 'system_health_api.py'))
    (tmp_path / 'network_adaptive.py').write_text('', encoding='utf-8')
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'adaptive_status.json').write_text(
        json.dumps({
            'current_strategy': 'cautious',
            'risk_level': 'medium',
            'current_params': {'request_delay': 9},
            'metrics': {'recent_success_rate': 78, 'last_collect_time': '2026-10-20 01:00:00'},
        }), encoding='utf-8'
    )

    result = health.get_adaptive_status()

    assert result['current_strategy'] == 'cautious'
    assert result['recent_success_rate'] == 78
    assert result['current_delay_seconds'] == 9
    assert result['risk_level'] == 'medium'


def test_adaptive_defaults_are_not_reported_as_observed_success(monkeypatch, tmp_path):
    import json
    import system_health_api as health

    monkeypatch.setattr(health, '__file__', str(tmp_path / 'system_health_api.py'))
    (tmp_path / 'network_adaptive.py').write_text('', encoding='utf-8')
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'adaptive_status.json').write_text(json.dumps({
        'current_strategy': 'normal',
        'risk_level': 'none',
        'current_params': {'request_delay': 55},
        'metrics': {'recent_success_rate': 100, 'last_collect_time': None},
    }), encoding='utf-8')

    result = health.get_adaptive_status()

    assert result['recent_success_rate'] is None
    assert result['current_delay_seconds'] == 55


def test_system_health_summary_has_no_mainland_cdp_hint():
    """健康摘要的生产提示不得再引导用户启动 9222。"""
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / 'system_health_api.py').read_text(
        encoding='utf-8'
    )
    assert "connect_ex(('127.0.0.1', 9222))" not in source
    assert 'Edge CDP 9222' not in source


def test_keepalive_status_projection_omits_worker_and_credential_details():
    """Keepalive APIs expose state without returning session endpoint or private bindings."""
    import threading
    from unittest.mock import patch

    # Importing the legacy Flask module starts its production watchdog. The
    # projection itself is pure; keep this isolated test from leaving a daemon
    # thread behind or touching runtime state.
    with patch.object(threading.Thread, 'start', autospec=True, return_value=None):
        from app import _safe_xhs_keepalive_result

    result = _safe_xhs_keepalive_result({
        'platform': 'rednote_hk',
        'status': 'logged_in',
        'is_logged_in': True,
        'cdp_url': 'http://127.0.0.1:9234',
        'cdp_port': 9234,
        'profile_path': 'private-profile',
        'cookie_file': 'private-cookie-file',
        'error': 'private exception detail',
        'message': 'raw internal message',
    })

    assert result['status'] == 'logged_in'
    assert result['is_logged_in'] is True
    assert result['message'] == '已确认登录状态'
    assert not {'cdp_url', 'cdp_port', 'profile_path', 'cookie_file',
                'error'} & result.keys()
    assert result['message'] != 'raw internal message'


def test_cdp_result_updates_canonical_collection_log(monkeypatch):
    """CDP 入口的成功结果必须覆盖旧的健康状态，不能只更新 notes。"""
    import app as app_module

    seen = []
    monkeypatch.setattr(
        app_module.db,
        'log_collection',
        lambda keyword, count, status, error='': seen.append((keyword, count, status, error)),
    )
    result = app_module._record_rednote_collection_log(
        {'ok': True, 'notes': [{'note_id': 'n-1'}], 'summary': {'keyword': '广州太古汇'}},
        '广州太古汇',
    )
    assert result['status'] == 'SUCCESS'
    assert seen == [('广州太古汇', 1, 'SUCCESS', '')]


def test_cdp_verification_result_is_not_misclassified_as_empty(monkeypatch):
    """人机验证信号优先于 0 条，必须进入 CAPTCHA 状态。"""
    import app as app_module

    seen = []
    monkeypatch.setattr(
        app_module.db,
        'log_collection',
        lambda keyword, count, status, error='': seen.append((keyword, count, status, error)),
    )
    result = app_module._record_rednote_collection_log(
        {'ok': False, 'notes': [], 'summary': {'keyword': '广州太古汇', 'verification_required': True}},
        '广州太古汇',
    )
    assert result['status'] == 'CAPTCHA'
    assert seen[0][2] == 'CAPTCHA'
