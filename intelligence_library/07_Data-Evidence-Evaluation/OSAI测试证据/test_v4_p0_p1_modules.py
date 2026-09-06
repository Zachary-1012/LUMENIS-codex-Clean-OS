# -*- coding: utf-8 -*-
"""V4 P0/P1 新模块测试：ActionFirewall / RuntimeGuardian / ReleaseSafety / MemoryLifecycle / ImpactAnalysis / BusinessEvidence"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine.action_firewall import ActionFirewall, HIGH_RISK_ACTIONS
from osai_engine.runtime_guardian import RuntimeGuardian
from osai_engine.release_safety import ReleaseSafetyManager
from osai_engine.memory_lifecycle import MemoryLifecycle
from osai_engine.impact_analysis import ImpactAnalyzer
from osai_engine.evidence_chain import BusinessEvidenceChain, BUSINESS_NODE_TYPES


def test_action_firewall_high_risk_deny():
    fw = ActionFirewall()
    result = fw.authorize("agent-1", "commit", parameters={"msg": "test"},
                          intent="auto_commit", task_id="T-1")
    assert result["allowed"] is False
    assert result["risk"] == "HIGH"
    assert "REQUIRES_HUMAN_APPROVAL" in result["reason"]


def test_action_firewall_high_risk_with_approval():
    fw = ActionFirewall()
    result = fw.authorize("agent-1", "push", parameters={},
                          human_approval_id="APPR-001")
    assert result["allowed"] is True
    assert result["risk"] == "HIGH"


def test_action_firewall_medium_requires_scope():
    fw = ActionFirewall()
    result = fw.authorize("agent-1", "write_file", parameters={})
    assert result["allowed"] is False
    assert "REQUIRES_SCOPE" in result["reason"]


def test_action_firewall_low_risk_allow():
    fw = ActionFirewall()
    result = fw.authorize("agent-1", "read_file", parameters={})
    assert result["allowed"] is True
    assert result["risk"] == "LOW"


def test_action_firewall_fail_close():
    fw = ActionFirewall()
    result = fw.authorize(None, None, parameters=None)
    assert result["allowed"] is False  # 异常时 fail-close


def test_runtime_guardian_lease():
    g = RuntimeGuardian()
    g.register_worker("w1")
    lease = g.acquire_lease("w1", "task-1", ttl=2)
    assert lease is not None
    assert lease.task_id == "task-1"
    # 同一 task 不能重复获取
    lease2 = g.acquire_lease("w2", "task-1")
    assert lease2 is None
    # 心跳
    assert g.heartbeat(lease.lease_id) is True
    g.release_lease(lease.lease_id)
    assert g.workers["w1"]["state"] == "IDLE"


def test_runtime_guardian_checkpoint():
    g = RuntimeGuardian()
    cp = g.save_checkpoint("task-1", "step-1", {"x": 1})
    assert cp.task_id == "task-1"
    assert g.latest_checkpoint("task-1").step == "step-1"


def test_runtime_guardian_retry_dlq():
    g = RuntimeGuardian()
    for i in range(4):
        g.record_failure("task-1", f"error-{i}")
    assert g.retry_counts["task-1"] == 4
    assert len(g.dlq) == 1  # 第4次进入 DLQ


def test_release_safety_stage_gate():
    mgr = ReleaseSafetyManager()
    rc = mgr.create_candidate("v1.0", "frontend")
    assert rc.current_stage == "SHADOW"
    # 没有 evidence 不能推进
    r = mgr.advance(rc.release_id, "REPLAY")
    assert r["ok"] is False
    # 有 evidence 可以推进
    r = mgr.advance(rc.release_id, "REPLAY",
                    evidence={"shadow_traffic_configured": True})
    assert r["ok"] is True
    assert rc.current_stage == "REPLAY"


def test_release_safety_production_requires_approval():
    mgr = ReleaseSafetyManager()
    rc = mgr.create_candidate("v1.0", "backend", rollback_plan="revert to v0.9")
    # 快速推进到 CANARY
    for stage, ev in [("REPLAY", {"shadow_traffic_configured": True}),
                      ("COMPARE", {"replay_samples_collected": True}),
                      ("CANARY", {"diff_report_generated": True, "no_regression": True})]:
        mgr.advance(rc.release_id, stage, evidence=ev)
    assert rc.current_stage == "CANARY"
    assert rc.can_production() is False  # 还没人工批准
    mgr.approve(rc.release_id, "human-admin")
    assert rc.can_production() is True


def test_memory_lifecycle():
    ml = MemoryLifecycle()
    entry = ml.create("test memory", "source-1")
    assert entry.stage == "RAW"
    # 正常晋升
    assert ml.promote(entry.memory_id, "CANDIDATE")["ok"] is True
    assert ml.promote(entry.memory_id, "VALIDATED",
                      evidence={"verified": True})["ok"] is True
    assert ml.promote(entry.memory_id, "GENERALIZABLE")["ok"] is True
    assert ml.promote(entry.memory_id, "ADMITTED")["ok"] is True
    assert len(ml.get_admitted()) == 1
    # 非法跳转
    entry2 = ml.create("mem2", "src")
    assert ml.promote(entry2.memory_id, "ADMITTED")["ok"] is False  # 不能跳级


def test_business_evidence_chain():
    bec = BusinessEvidenceChain("EVID-1", "TASK-1", "TRACE-1")
    bec.add_node("source", "url-1", "source detail")
    bec.add_node("finding", "finding-1", "finding detail")
    bec.add_node("decision", "decision-1", "decision detail")
    built = bec.build()
    assert built["chain_type"] == "business"
    assert len(built["nodes"]) == 3
    assert built["status"] == "EVIDENCE_CREATED"


def test_impact_analysis():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ia = ImpactAnalyzer(repo)
    report = ia.analyze("osai_engine/action_firewall.py")
    assert report.target_file.endswith("action_firewall.py")
    assert report.production_risk in ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN")
    assert len(report.recommendations) > 0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
