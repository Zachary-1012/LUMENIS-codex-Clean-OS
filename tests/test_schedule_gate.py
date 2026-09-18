# -*- coding: utf-8 -*-
"""GAP-05 动态调度影子→门控三态切换测试（纯逻辑，fake planner，不连真实库）。

验证铁律：
- 默认 shadow：评估但不门控，should_run 完全等于 hard_allow（上线零行为变化）；
- canary：仅灰度名单内平台被 decision.allow 门控；
- enforce：全部平台按 allow 门控；
- 只收紧不放松：hard_allow=False 时任何模式都不可能 True；门控器异常 fail-open 到 hard_allow；
- 非法模式回退 shadow。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _Dec:
    def __init__(self, allow, reason='cooldown'):
        self.allow = allow
        self.reason_code = reason
        self.next_run_at = ''
        self.risk_status = 'normal'


class _FakePlanner:
    def __init__(self, allow=True, raise_exc=False):
        self._allow = allow
        self._raise = raise_exc
        self.calls = []

    def decide(self, platform, *, now, is_hotspot=False, trigger_source='', persist=False):
        self.calls.append(trigger_source)
        if self._raise:
            raise RuntimeError('planner down')
        return _Dec(self._allow)


class _BoomPlanner(_FakePlanner):
    def decide(self, *a, **k):
        raise RuntimeError('boom')


NOW = None


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv('ZBC_SCHED_GATE_MODE', raising=False)
    monkeypatch.delenv('ZBC_SCHED_GATE_PLATFORMS', raising=False)
    import datetime as _dt
    global NOW
    NOW = _dt.datetime(2026, 9, 1, 12, 0, 0)
    yield


def test_default_shadow_does_not_gate(monkeypatch):
    from lumenis.system.collector.adapters.scheduling import gate_should_run, gate_mode
    assert gate_mode() == 'shadow'
    # 即便决策 allow=False，shadow 也沿用固定触发 True（零行为变化）
    run, dec, mode = gate_should_run(_FakePlanner(allow=False), 'xhs', now=NOW)
    assert (run, mode) == (True, 'shadow') and dec.allow is False


def test_enforce_gates_by_allow(monkeypatch):
    from lumenis.system.collector.adapters.scheduling import gate_should_run
    monkeypatch.setenv('ZBC_SCHED_GATE_MODE', 'enforce')
    assert gate_should_run(_FakePlanner(allow=False), 'xhs', now=NOW)[0] is False
    assert gate_should_run(_FakePlanner(allow=True), 'xhs', now=NOW)[0] is True


def test_canary_only_gates_listed_platforms(monkeypatch):
    from lumenis.system.collector.adapters.scheduling import gate_should_run
    monkeypatch.setenv('ZBC_SCHED_GATE_MODE', 'canary')
    monkeypatch.setenv('ZBC_SCHED_GATE_PLATFORMS', 'web,bilibili')
    # xhs 不在灰度名单 -> 同 shadow，allow=False 也照常跑
    assert gate_should_run(_FakePlanner(allow=False), 'xhs', now=NOW)[0] is True
    # web 在名单 -> 被门控
    assert gate_should_run(_FakePlanner(allow=False), 'web', now=NOW)[0] is False
    assert gate_should_run(_FakePlanner(allow=True), 'web', now=NOW)[0] is True


def test_gate_only_tightens_never_relaxes(monkeypatch):
    from lumenis.system.collector.adapters.scheduling import gate_should_run
    monkeypatch.setenv('ZBC_SCHED_GATE_MODE', 'enforce')
    # 上游既有逻辑已判定不跑(hard_allow=False)，门控绝不可能放行
    assert gate_should_run(_FakePlanner(allow=True), 'xhs', now=NOW, hard_allow=False)[0] is False


def test_fail_open_on_planner_error(monkeypatch):
    from lumenis.system.collector.adapters.scheduling import gate_should_run
    monkeypatch.setenv('ZBC_SCHED_GATE_MODE', 'enforce')
    # enforce 下 planner 崩了也不能卡死既有调度 -> 回落到 hard_allow
    run, dec, mode = gate_should_run(_BoomPlanner(), 'xhs', now=NOW, hard_allow=True)
    assert run is True and dec is None and mode == 'enforce'
    assert gate_should_run(_BoomPlanner(), 'xhs', now=NOW, hard_allow=False)[0] is False


def test_invalid_mode_falls_back_shadow(monkeypatch):
    from lumenis.system.collector.adapters.scheduling import gate_should_run, gate_mode
    monkeypatch.setenv('ZBC_SCHED_GATE_MODE', 'nonsense')
    assert gate_mode() == 'shadow'
    assert gate_should_run(_FakePlanner(allow=False), 'xhs', now=NOW)[0] is True
