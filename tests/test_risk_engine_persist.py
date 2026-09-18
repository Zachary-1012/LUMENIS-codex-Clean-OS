# -*- coding: utf-8 -*-
"""T-P0A-1 RiskEngine 可选崩溃持久化（state_file）规范单测。

默认不传 state_file = 纯内存，行为与旧版完全一致；显式传入才落盘/恢复。
"""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lumenis.system.collector.guard.risk_engine import RiskEngine, _TRIPPED_BANDS  # noqa: E402


def test_default_no_state_file_pure_memory(tmp_path):
    """默认不传 state_file：不创建任何文件，纯内存行为。"""
    r = RiskEngine()
    assert r.state_file is None
    r.record_failure('rate_limited')
    assert not list(tmp_path.glob('*.json'))


def test_persist_and_restore(tmp_path):
    """传入 state_file：熔断状态落盘，重启后恢复。"""
    sf = str(tmp_path / 'risk_state.json')
    r = RiskEngine(state_file=sf)
    assert os.path.isdir(tmp_path), '构造时应确保目录存在'
    assert not os.path.exists(sf), '首次落盘前不应生成文件'
    r.record_failure('rate_limited')  # 冷却
    assert os.path.exists(sf), 'record_failure 应触发落盘'
    with open(sf, encoding='utf-8') as f:
        d = json.load(f)
    assert d['_last_band'] == 'COOLDOWN'
    assert d['opened_at'] is not None

    # 重启恢复：新实例读到同一状态
    r2 = RiskEngine(reset_timeout=300, state_file=sf)
    assert r2._last_band == 'COOLDOWN'
    assert r2.opened_at is not None
    assert r2.score == r.score


def test_restore_cooldown_expired_goes_half_open(tmp_path):
    """冷却在重启期间已到期：恢复为半开试探，而非恢复后立刻全速。"""
    sf = str(tmp_path / 'risk_state.json')
    r = RiskEngine(reset_timeout=60, state_file=sf)
    r.record_failure('security_page')  # CIRCUIT_OPEN
    # 模拟重启经过了 reset_timeout
    with open(sf, encoding='utf-8') as f:
        d = json.load(f)
    d['opened_at'] = time.time() - 120  # 已冷却 120s > 60s
    with open(sf, 'w', encoding='utf-8') as f:
        json.dump(d, f)

    r2 = RiskEngine(reset_timeout=60, state_file=sf)
    assert r2.half_open is True, '冷却到期应转半开，不应恢复后立刻全速'
    snap = r2.snapshot()
    assert snap['lifecycle'] == 'RECOVERING'
    assert snap['should_stop_request'] is False, '半开期应放行探测'


def test_restore_corrupt_file_ignored(tmp_path):
    """损坏/缺失的状态文件：按全新引擎启动，不阻断。"""
    sf = str(tmp_path / 'risk_state.json')
    with open(sf, 'w', encoding='utf-8') as f:
        f.write('{not valid json')
    r = RiskEngine(state_file=sf)
    assert r.score == 0
    assert r.opened_at is None
    assert r.lifecycle_state() == 'NORMAL'


def test_persist_after_full_recovery(tmp_path):
    """半开探测通过完全恢复后：状态文件应更新为闭合（opened_at 清空）。"""
    sf = str(tmp_path / 'risk_state.json')
    r = RiskEngine(reset_timeout=60, half_open_success_threshold=1, state_file=sf)
    r.record_failure('rate_limited')
    with open(sf, encoding='utf-8') as f:
        d = json.load(f)
    d['opened_at'] = time.time() - 120
    with open(sf, 'w', encoding='utf-8') as f:
        json.dump(d, f)
    r2 = RiskEngine(reset_timeout=60, half_open_success_threshold=1, state_file=sf)
    assert r2.half_open is True
    r2.record_success()  # 半开成功一次 -> 完全闭合
    with open(sf, encoding='utf-8') as f:
        d2 = json.load(f)
    assert d2['opened_at'] is None
    assert d2['half_open'] is False
    assert d2['score'] == 0
