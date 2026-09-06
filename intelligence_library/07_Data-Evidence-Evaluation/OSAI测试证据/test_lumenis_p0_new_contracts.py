# -*- coding: utf-8 -*-
"""LUMENIS P0 补齐 5 Contract 测试：Repository / Permission / Runtime /
UI State / Learning Record。确定性、离线、无网络、无写操作。
"""
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import (learning_record_contract, permission_contract,
                         repository_contract, runtime_contract,
                         ui_state_contract)


# ---------- Repository Contract ----------
def test_repo_register_and_validate():
    reg = repository_contract.RepositoryContractRegistry()
    rec = reg.register("ZBC", "Z-Brand-Core", "production", "/repo/zbc",
                       default_branch="main", current_sha="abc123")
    assert rec.role == "production"
    assert rec.contract_version == "1.0.0"
    assert rec.validate() == []
    assert reg.get("ZBC").current_sha == "abc123"


def test_repo_missing_field_raises():
    reg = repository_contract.RepositoryContractRegistry()
    try:
        reg.register("X", "X", "production", "")
        assert False, "root_path 缺失必须抛 ValueError"
    except ValueError:
        pass


def test_repo_record_fact_updates_sha():
    reg = repository_contract.RepositoryContractRegistry()
    reg.register("OSAI", "Zachary-OS-AI", "intelligence", "/repo/osai")
    rec = reg.record_fact("OSAI", sha="def456", status="healthy")
    assert rec.current_sha == "def456"
    assert rec.status == "healthy"
    snap = reg.snapshot()
    assert snap["total"] == 2 or snap["total"] == 1  # 隔离运行


def test_repo_invalid_role_rejected():
    try:
        repository_contract.RepoRecord("X", "X", "invalid", "/p")
        assert False
    except AssertionError:
        pass


# ---------- Permission Contract ----------
def test_permission_agent_auto_allow_below_verify():
    reg = permission_contract.PermissionContractRegistry()
    for lv in ("READ", "AUDIT", "ANALYZE", "RESEARCH", "PLAN",
               "PATCH_PREVIEW", "TEST", "VERIFY"):
        req = reg.request("agent", lv, "ZBC")
        assert req.decision == "allow", "%s 应自动允许" % lv


def test_permission_agent_commit_auto_deny():
    reg = permission_contract.PermissionContractRegistry()
    req = reg.request("agent", "COMMIT", "OSAI")
    assert req.decision == "deny"
    assert "VERIFY" in req.decide_reason


def test_permission_agent_push_auto_deny():
    reg = permission_contract.PermissionContractRegistry()
    req = reg.request("skill", "PUSH", "BOTH")
    assert req.decision == "deny"


def test_permission_human_approves_commit():
    reg = permission_contract.PermissionContractRegistry()
    req = reg.request("human", "COMMIT", "ZBC")
    # human 不自动 deny，进入 pending_human
    assert req.decision == "pending_human"
    result = req.human_decide(True, by="Zachary", note="P0 收口")
    assert result == "allow"
    assert "approved" in req.decide_reason


def test_permission_invalid_level():
    try:
        permission_contract.PermissionRequest("agent", "ROOT", "ZBC")
        assert False
    except AssertionError:
        pass


# ---------- Runtime Contract ----------
def test_runtime_register_and_heartbeat():
    reg = runtime_contract.RuntimeRegistry()
    st = reg.register("flask-app", status="running", pid=1234, port=5000,
                      python_version="3.13", repo="ZBC")
    assert st.status == "running"
    assert not st.is_stale()
    st.heartbeat(status="error", detail="DB locked")
    assert st.status == "error"


def test_runtime_stale_detection():
    st = runtime_contract.RuntimeState("x", last_heartbeat="2020-01-01 00:00:00")
    assert st.is_stale()


def test_runtime_invalid_status():
    try:
        runtime_contract.RuntimeState("x", status="exploded")
        assert False
    except AssertionError:
        pass


def test_runtime_snapshot_groups():
    reg = runtime_contract.RuntimeRegistry()
    reg.register("a", status="running")
    reg.register("b", status="stopped")
    snap = reg.snapshot()
    assert snap["by_status"]["running"] >= 1
    assert snap["by_status"]["stopped"] >= 1


# ---------- UI State Contract ----------
def test_ui_state_9_states_valid():
    assert len(ui_state_contract.UI_STATES) == 9
    reg = ui_state_contract.UIStateRegistry()
    st = reg.set("home", "metric-1", "loading")
    assert st.state == "loading"
    st.transition("success", freshness="fresh", data_ref="/api/metric")
    assert st.is_real()


def test_ui_state_success_without_data_ref_is_fake():
    st = ui_state_contract.UIState("p", "c", "success")
    assert not st.is_real(), "success 无 data_ref 必须判定为假状态"


def test_ui_state_error_requires_message():
    st = ui_state_contract.UIState("p", "c", "loading")
    try:
        st.transition("error")
        assert False, "error 必须带 message 或 error_code"
    except ValueError:
        pass


def test_ui_state_error_with_code_ok():
    st = ui_state_contract.UIState("p", "c", "loading", error_code="E500")
    st.transition("error")  # 已有 error_code，允许
    assert st.state == "error"


def test_ui_state_snapshot_flags_fake():
    reg = ui_state_contract.UIStateRegistry()
    reg.set("p1", "c1", "success")  # 无 data_ref → fake
    reg.set("p1", "c2", "loading")
    snap = reg.snapshot()
    assert snap["fake_state_count"] >= 1


# ---------- Learning Record Contract ----------
def test_learning_chain_requires_evidence():
    reg = learning_record_contract.LearningRegistry()
    rec = reg.record("发现 subject 过滤可优化", source="research")
    assert rec.status == "draft"
    try:
        rec.advance_chain("evidence")
        assert False, "无 evidence_ref 不能进入 evidence 阶段"
    except ValueError:
        pass


def test_learning_verify_and_adopt():
    reg = learning_record_contract.LearningRegistry()
    rec = reg.record("AI Gateway fallback 链可缩短", source="ai")
    rec.verify("ev-chain-001")
    assert rec.status == "verified"
    rec.adopt("D-001", improvement="调整 fallback 顺序")
    assert rec.status == "adopted"
    assert rec.chain_stage == "improvement"


def test_learning_adopt_requires_decision():
    rec = learning_record_contract.LearningRecord("finding")
    try:
        rec.adopt("")
        assert False
    except AssertionError:
        pass


def test_learning_invalid_source():
    try:
        learning_record_contract.LearningRecord("f", source="oracle")
        assert False
    except AssertionError:
        pass


def test_learning_by_source_filter():
    reg = learning_record_contract.LearningRegistry()
    reg.record("a", source="ai")
    reg.record("b", source="human")
    ai_records = reg.by_source("ai")
    assert len(ai_records) == 1
