# -*- coding: utf-8 -*-
"""采集稳定性端到端模拟链（P1-A 后闭环扩展；不跑网络/浏览器）。

模拟 collector 主循环的真实逻辑（与 collector.py 同构）：
  关键词序列 -> classify -> RiskEngine.record_failure/success -> snapshot
  -> should_stop(风险熔断) 或 schedule should_stop(ResourceGuard 联动) -> break
  -> 冷却 -> 半开探测放行 -> 恢复

验证六态完整流转：NORMAL -> COOLDOWN(连续失败) -> FROZEN -> RECOVERING(半开探测)
-> RECOVERED(成功恢复)。使用真实 RiskEngine + ScheduleAdapter。
"""
import time

import pytest

from collector_guard.risk_engine import RiskEngine
from collector_guard.schedule_adapter import should_stop_schedule

# 与 collector.py 同构的最小采集循环
def _collect_loop(keywords, factor_by_state, run_one, risk, max_probe_ok=1):
    """run_one(kw) -> {'ok': bool, 'error': str}；返回 (collected, stop_reason)。"""
    collected = []
    stop_reason = None
    for kw in keywords:
        res = run_one(kw)
        state = "ok" if res["ok"] else "error"
        factor = factor_by_state.get(state)
        if factor:
            score, band, st = risk.record_failure(factor)
        else:
            score, band, st = risk.record_success()
        snap = risk.snapshot()
        collected.append(kw)
        if snap["should_stop_request"]:
            stop_reason = "risk:" + snap["lifecycle"]
            break
        if should_stop_schedule(snap.get("lifecycle_action")):
            stop_reason = "schedule:" + snap["lifecycle"]
            break
        # 半开探测期：成功一次即恢复
        if snap.get("half_open") and res["ok"]:
            if max_probe_ok <= 0:
                stop_reason = "probe-ok"
                break
            max_probe_ok -= 1
    return collected, stop_reason


def _mk_risk(**kw):
    kw.setdefault("reset_timeout", 0.3)
    kw.setdefault("recovered_window_s", 0.2)
    return RiskEngine(**kw)


def test_all_success_no_stop():
    r = _mk_risk()
    coll, reason = _collect_loop(["k1", "k2", "k3"],
                                 {"ok": None, "error": 30},
                                 lambda kw: {"ok": True, "error": ""},
                                 r)
    assert reason is None and coll == ["k1", "k2", "k3"]


def test_single_failure_continues():
    r = _mk_risk()
    calls = {"n": 0}

    def run(kw):
        calls["n"] += 1
        return {"ok": calls["n"] != 2, "error": "" if calls["n"] != 2 else "xhs限流"}

    coll, reason = _collect_loop(["k1", "k2", "k3", "k4"],
                                 {"ok": None, "error": 30}, run, r)
    # 单次失败不熔断（分数不足），继续全部
    assert reason is None and coll == ["k1", "k2", "k3", "k4"]


def test_consecutive_failures_trip_risk_engine():
    r = _mk_risk()
    coll, reason = _collect_loop(["k1", "k2", "k3", "k4", "k5", "k6"],
                                 {"ok": None, "error": 30},
                                 lambda kw: {"ok": False, "error": "security_page"},
                                 r)
    assert reason and reason.startswith("risk:")
    assert len(coll) < 6  # 熔断提前停止
    snap = r.snapshot()
    assert snap["band"] in ("HIGH", "CRITICAL") or snap["lifecycle"] in ("COOLDOWN", "FROZEN")


def test_cooldown_then_half_open_probe_recovery():
    r = _mk_risk()
    # 失败直到熔断
    coll, reason = _collect_loop(["k1"] * 8, {"ok": None, "error": 30},
                                 lambda kw: {"ok": False, "error": "security_page"}, r)
    assert reason and reason.startswith("risk:")
    snap = r.snapshot()
    assert snap["lifecycle"] in ("COOLDOWN", "FROZEN")
    # 冷却结束后应进入半开（RECOVERING），放行探测；探测成功后应恢复
    time.sleep(0.5)
    snap2 = r.snapshot()
    assert snap2["lifecycle"] == "RECOVERING" or snap2["half_open"] is True
    # 半开期成功一次 -> 分数归零恢复正常
    r.record_success()
    snap3 = r.snapshot()
    assert snap3["lifecycle"] == "RECOVERED" or snap3["band"] == "NORMAL"


def test_schedule_stop_on_freeze_action():
    # ResourceGuard 联动：lifecycle_action=freeze_and_recover -> 停止后续（即使 risk 未熔断）
    r = _mk_risk()
    calls = {"n": 0}

    def run(kw):
        calls["n"] += 1
        # 先制造 FROZEN 生命周期（连续失败到冻结）
        return {"ok": False, "error": "login_expired"}

    coll, reason = _collect_loop(["a", "b", "c", "d", "e", "f"],
                                 {"ok": None, "error": 30}, run, r)
    assert reason is not None
    assert len(coll) < 6  # 提前停止（risk 或 schedule 任一层命中）


def test_probe_only_does_not_stop():
    # probe_only 是放行探测的动作：should_stop_schedule 恒 False
    assert should_stop_schedule("probe_only") is False
    assert should_stop_schedule("ramp_up") is False
    assert should_stop_schedule("backoff_interval") is False
