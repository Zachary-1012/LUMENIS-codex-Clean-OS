# -*- coding: utf-8 -*-
"""D2 动态调度闭环补齐：worker 未预期异常也必须回写统一规划器并进入网络退避。

纯逻辑、不触网、不连浏览器；用 state_file=None/store=None 的内存态 planner，
绝不污染生产 data/ 调度状态与 schedule_decisions 审计表。
"""
import os
import sys
import importlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _fresh_bridge():
    import xhs_cookie_bridge as xcb
    importlib.reload(xcb)
    return xcb


def test_exception_feeds_planner_network_backoff(monkeypatch):
    """sync 未兜住的异常 -> NETWORK_ERROR 回写 -> 立即决策必须被间隔退避拦下（不高频重试）。"""
    import lumenis.system.collector.adapters.scheduling as sch
    # 内存态规划器：state_file=None 不加载/不落盘，store=None 不写审计库
    mem_planner = sch.PlatformSchedulePlanner(state_file=None, store=None)
    monkeypatch.setattr(sch, 'get_planner', lambda *a, **k: mem_planner, raising=False)

    xcb = _fresh_bridge()
    now = datetime.now()
    # 对齐 worker except 分支新增的回写调用
    xcb._shadow_record_result('NETWORK_ERROR', 0, 'unexpected boom', 'auto')

    st = mem_planner.decider('xhs').state
    assert st.last_canon == 'NETWORK_ERROR', st.last_canon
    assert st.consecutive_network_fail == 1
    assert st.last_run_at is not None
    # 网络退避基准 60s：刚回写即决策，elapsed≈0 未达间隔，必须不放行
    dec = mem_planner.decide('xhs', now=now)
    assert dec.allow is False
    assert dec.reason_code == 'WAIT_INTERVAL', dec.reason_code


def test_three_network_fails_enter_cooldown(monkeypatch):
    """连续网络失败达到 network_fail_to_cooldown(=3) 后进入 IN_COOLDOWN，更强拦截。"""
    import lumenis.system.collector.adapters.scheduling as sch
    mem_planner = sch.PlatformSchedulePlanner(state_file=None, store=None)
    monkeypatch.setattr(sch, 'get_planner', lambda *a, **k: mem_planner, raising=False)
    xcb = _fresh_bridge()
    for _ in range(3):
        xcb._shadow_record_result('NETWORK_ERROR', 0, 'boom', 'auto')
    st = mem_planner.decider('xhs').state
    assert st.consecutive_network_fail == 3
    assert st.cooldown_until is not None
    dec = mem_planner.decide('xhs', now=datetime.now())
    assert dec.allow is False
    assert dec.reason_code == 'IN_COOLDOWN', dec.reason_code


def test_shadow_record_fail_open(monkeypatch):
    """规划器自身抛错时 _shadow_record_result 必须吞掉，绝不向上冒泡阻断采集主流程。"""
    import lumenis.system.collector.adapters.scheduling as sch

    class _Boom:
        def record_result(self, *a, **k):
            raise RuntimeError('planner down')

    monkeypatch.setattr(sch, 'get_planner', lambda *a, **k: _Boom(), raising=False)
    xcb = _fresh_bridge()
    xcb._shadow_record_result('SUCCESS', 1, '', 'manual')  # 不抛即通过
