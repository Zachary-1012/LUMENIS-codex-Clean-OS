# -*- coding: utf-8 -*-
"""当前生产采集边界：只允许香港/国际 RedNote，不触发真实平台。"""
import asyncio
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def test_bridge_defaults_to_hk_collection_identity(monkeypatch):
    import xhs_cookie_bridge as bridge

    monkeypatch.setattr(bridge, '_ACTIVE_ACCOUNT', None)
    monkeypatch.delenv('XHS_COOKIE_FILE_OVERRIDE', raising=False)
    assert bridge._canonical_account_name() == bridge.XHS_RETINAUT_NAME
    assert bridge.cdp_port_for() == 9223
    assert bridge.home_url_for().startswith('https://www.rednote.com')
    assert bridge.collection_policy_gate(account=bridge.XHS_RETINAUT_NAME)['ok'] is True


def test_bridge_blocks_mainland_before_platform_request():
    import xhs_cookie_bridge as bridge

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
    worker = 'https://browser-worker.example:9223'

    monkeypatch.setattr(collector, '_resolve_server_cdp_url', lambda cdp_url=None: (worker, ''))
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
    assert result['channel'] == 'authorized_browser_worker'


def test_collector_without_explicit_worker_fails_closed_before_collection(monkeypatch):
    """无 server-owned worker 时不得回退到 localhost 或独立浏览器。"""
    import collector
    import xhs_cookie_bridge as bridge

    monkeypatch.setattr(
        collector, '_resolve_server_cdp_url',
        lambda cdp_url=None: ('', 'COLLECTOR_ENDPOINT_NOT_CONFIGURED'),
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


def test_cookie_status_recognizes_private_runtime_source(monkeypatch, tmp_path):
    import app as app_module
    import xhs_cookie_bridge as bridge

    (tmp_path / 'private').mkdir()
    (tmp_path / 'private' / 'xhs_cookie_retinaut.txt').write_text(
        'retinaut_cookie=test-only', encoding='utf-8'
    )
    monkeypatch.setattr(bridge, 'DATA_DIR', str(tmp_path))
    with app_module.app.test_request_context('/api/cookies/import/status'):
        response = app_module.api_cookies_import_status()
    payload = response.get_json()
    assert payload['status']['xhs_source_exists'] is True
    assert payload['status']['xhs']['source'] == 'private_cookie_file'


def test_collect_all_returns_stable_tuple_when_kind_blocked():
    import collector

    notes, results = collector.collect_all(keywords=['广州太古汇'], kind='event')
    assert notes == []
    assert results and results[0]['error'] == 'KIND_POLICY_BLOCKED'


def test_p0_orchestrator_blocks_cn_before_select():
    import xhs_p0_orchestrator as orchestrator
    import xhs_cookie_bridge as bridge

    result = orchestrator.trigger_collection(account_name=bridge.XHS_CN_PRIMARY_NAME)
    assert result['ok'] is False
    assert result['code'] == 'account_paused'


def test_private_v2_client_never_reaches_network():
    from collector_v2.xhs.client import XHSClient

    async def invoke():
        with pytest.raises(RuntimeError, match='非生产路径'):
            await XHSClient(cookie='test').request('GET', 'https://edith.xiaohongshu.com/test')

    asyncio.run(invoke())


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
