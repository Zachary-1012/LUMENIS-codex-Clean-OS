# -*- coding: utf-8 -*-
"""四层联动端到端模拟链（P1-A 后增强；不跑网络/浏览器）。

把采集韧性四层整合为一条真实采集循环：
  1. RuntimeSwitch  运维总闸（enabled/disabled × dry_run）—— 最高层，覆盖一切
  2. RiskEngine     连续风险分 + 六态熔断（COOLDOWN/FROZEN 停止）
  3. ScheduleAdapter should_stop + 恢复期 DLQ 自动重放（RECOVERING/RECOVERED）
  4. DLQ            失败任务捕获 + 恢复重放补采（数据零丢失）

场景：
  A 四层完整流转：正常 -> 连续失败熔断(停止+失败入DLQ) -> 冷却 -> 半开 -> 恢复 -> DLQ重放补采
  B 运维总闸覆盖：disabled 时即使风险正常也全部抑制（请求=0）
  C dry_run 演练：评估全开、请求=0、记录 would-have
"""
import time

import pytest

from lumenis.system.collector.guard.dlq_replay import DeadLetterQueue
from lumenis.system.collector.guard.risk_engine import RiskEngine
from lumenis.system.collector.guard.runtime_switch import RuntimeSwitch
from lumenis.system.collector.guard.schedule_adapter import maybe_replay_dlq, should_stop_schedule


def _mk_risk(**kw):
    kw.setdefault("reset_timeout", 0.3)
    kw.setdefault("recovered_window_s", 0.2)
    return RiskEngine(**kw)


def _mk_switch(tmp_path):
    return RuntimeSwitch(state_path=str(tmp_path / "switch.json"),
                         audit_path=str(tmp_path / "audit.jsonl"))


def _mk_dlq(tmp_path):
    return DeadLetterQueue(path=str(tmp_path / "dlq.jsonl"), max_attempts=3)


def run_four_layer_loop(keywords, run_one, risk, dlq, sw, factor_error=30,
                        max_probe_ok=1):
    """四层联动采集循环。

    run_one(kw) -> {'ok':bool, 'error':str}
    返回: {collected, requests, dlq_replayed, stop_reason, would_have}
    """
    out = {"collected": [], "requests": 0, "dlq_replayed": 0,
           "stop_reason": None, "would_have": []}
    collected = []
    for kw in keywords:
        # 1) 运维总闸（最高层）
        if not sw.is_enabled():
            out["stop_reason"] = "kill_switch"
            break
        if sw.is_dry_run():
            out["would_have"].append({"kw": kw, "state": "DRY_RUN"})
            continue
        # 2) RiskEngine 熔断判定
        snap = risk.snapshot()
        if snap["should_stop_request"]:
            out["stop_reason"] = "risk:" + snap["lifecycle"]
            break
        # 3) Schedule 联动
        if should_stop_schedule(snap.get("lifecycle_action")):
            out["stop_reason"] = "schedule:" + snap["lifecycle"]
            break
        # 4) 真实请求
        res = run_one(kw)
        out["requests"] += 1
        if res["ok"]:
            risk.record_success()
            collected.append(kw)
            # 半开期成功一次 -> 恢复
            if snap.get("half_open"):
                if max_probe_ok <= 0:
                    break
                max_probe_ok -= 1
        else:
            risk.record_failure(factor_error)
            dlq.enqueue(kw, error=res.get("error", "unknown"))  # 失败入 DLQ
        # 恢复期（RECOVERING/RECOVERED）触发 DLQ 重放
        act = risk.snapshot().get("lifecycle_action")
        r = maybe_replay_dlq(act, handler=run_one, dlq=dlq)
        if r and not r.get("dry"):
            out["dlq_replayed"] += r["replayed"]
            if r["replayed"]:
                collected.append("replay:" + kw)
    out["collected"] = collected
    return out


def test_scene_a_four_layer_full_flow(tmp_path):
    """A: 正常 -> 连续失败熔断(入DLQ) -> 冷却 -> 半开 -> 恢复 -> DLQ重放。"""
    risk = _mk_risk()
    dlq = _mk_dlq(tmp_path)
    sw = _mk_switch(tmp_path)
    calls = {"n": 0}

    def run(kw):
        calls["n"] += 1
        # 前 6 次失败（触发熔断），之后成功（模拟恢复）
        return {"ok": calls["n"] > 6, "error": "" if calls["n"] > 6 else "security_page"}

    out = run_four_layer_loop(["k1"] * 12, run, risk, dlq, sw)
    # 熔断提前停止（6 次失败 -> COOLDOWN）
    assert out["stop_reason"] and out["stop_reason"].startswith("risk:")
    assert out["requests"] <= 8
    # 失败任务已入 DLQ
    assert dlq.stats()["pending"] >= 1
    # 冷却后恢复并重放（dlq.replay 调 handler(keyword, context)，需双参适配）
    time.sleep(0.6)
    act = risk.snapshot().get("lifecycle_action")
    assert act in ("probe_only", "ramp_up"), "冷却后应进入恢复态, got=%s" % act
    risk.record_success()
    r = maybe_replay_dlq(risk.snapshot().get("lifecycle_action"),
                         handler=lambda kw, ctx: run(kw), dlq=dlq)
    assert r is not None and r["dry"] is False
    assert dlq.stats()["pending"] == 0  # 恢复期重放清空


def test_scene_b_kill_switch_overrides(tmp_path):
    """B: 运维总闸 disabled 覆盖一切——即使风险正常也全部抑制（请求=0）。"""
    risk = _mk_risk()
    dlq = _mk_dlq(tmp_path)
    sw = _mk_switch(tmp_path)
    sw.set_enabled(False, reason="incident", actor="ops")
    out = run_four_layer_loop(["k1", "k2", "k3"], lambda kw: {"ok": True, "error": ""},
                              risk, dlq, sw)
    assert out["stop_reason"] == "kill_switch"
    assert out["requests"] == 0  # 总闸覆盖：一个请求都不发
    assert dlq.stats()["pending"] == 0  # 也未入队


def test_scene_c_dry_run_observes_only(tmp_path):
    """C: dry_run 演练——评估全开、请求=0、记录 would-have。"""
    risk = _mk_risk()
    dlq = _mk_dlq(tmp_path)
    sw = _mk_switch(tmp_path)
    sw.set_dry_run(True)
    out = run_four_layer_loop(["k1", "k2"], lambda kw: {"ok": True, "error": ""},
                              risk, dlq, sw)
    assert out["requests"] == 0
    assert len(out["would_have"]) == 2  # 全部记录 would-have
    assert out["would_have"][0]["state"] == "DRY_RUN"
    assert out["stop_reason"] is None  # dry_run 不视为故障


def test_scene_d_recovery_triggers_replay(tmp_path):
    """D: 恢复期(RECOVERING/RECOVERED) DLQ 重放被 schedule 触发。"""
    risk = _mk_risk()
    dlq = _mk_dlq(tmp_path)
    sw = _mk_switch(tmp_path)
    # 制造一个失败任务
    dlq.enqueue("lost_kw", error="net_timeout")
    # 恢复态触发
    r = maybe_replay_dlq("ramp_up", handler=lambda kw, ctx: {"ok": True, "error": ""},
                         dlq=dlq)
    assert r is not None and r["replayed"] >= 1
    assert dlq.stats()["pending"] == 0
