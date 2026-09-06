# -*- coding: utf-8 -*-
"""LUMENIS P0 Contracts 测试 — 5 个契约模块 + 包导出 + git_commit_push 权限门。

确定性、离线、无网络、无 API key、无 git 写操作。
对齐 contracts/P0-04~P0-08 Markdown schema（Markdown 优先于 spec）。
"""
import os
import sys
import tempfile
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import osai_engine
from osai_engine import (evidence_chain, evaluation_contract, lifecycle_contract,
                         task_contract, tools, trace_contract)


# ---------- P0-04 Task Contract ----------
def test_task_create_with_scope_forbidden_flow():
    r = task_contract.TaskRegistry()
    t = r.create("补齐契约模块", "WINDOW-A", "OSAI",
                 scope="osai_engine/task_contract.py",
                 forbidden="osai_engine/orchestrator.py",
                 acceptance="pytest 全过")
    # task_id 格式 T-YYYYMMDD-xxxx
    assert t.task_id.startswith("T-")
    assert len(t.task_id) == len("T-YYYYMMDD-xxxx")
    assert t.owner == "WINDOW-A"
    assert t.repo == "OSAI"
    assert t.scope == "osai_engine/task_contract.py"
    assert t.forbidden == "osai_engine/orchestrator.py"
    assert t.lifecycle in lifecycle_contract.LIFECYCLE_STATES
    assert t.status == "pending"
    # get
    assert r.get(t.task_id) is t
    # update_status
    r.update_status(t.task_id, "running")
    assert r.get(t.task_id).status == "running"
    # attach_evidence
    r.attach_evidence(t.task_id, "ev-chain-001")
    assert t.evidence_ref == ["ev-chain-001"]
    # 重复 attach 不重复
    r.attach_evidence(t.task_id, "ev-chain-001")
    assert t.evidence_ref == ["ev-chain-001"]
    # snapshot
    snap = r.snapshot()
    assert snap["total"] == 1
    assert snap["by_status"]["running"] == 1
    assert len(snap["tasks"]) == 1


def test_task_without_scope_is_blocked():
    r = task_contract.TaskRegistry()
    t = r.create("无 scope 任务", "HUMAN", "BOTH", forbidden="anything")
    assert t.status == "blocked"
    assert t.block_reason  # 记录了原因
    assert "scope" in t.block_reason


def test_task_without_forbidden_is_blocked():
    r = task_contract.TaskRegistry()
    t = r.create("无 forbidden 任务", "WINDOW-B", "ZBC", scope="file.py")
    assert t.status == "blocked"
    assert "forbidden" in t.block_reason


# ---------- P0-05 Trace Contract ----------
def test_trace_start_add_span_end_ordered():
    r = trace_contract.TraceRegistry()
    tr = r.start("T-20260905-0001")
    assert tr.trace_id
    assert tr.task_id == "T-20260905-0001"
    assert tr.started_at
    assert tr.ended_at is None

    # add_span ×3，含 sha_before/sha_after
    s1 = r.add_span(tr.trace_id, "agent", "inspect", target="osai_engine/config.py",
                     result="ok", sha_before="abc123", sha_after="abc123")
    s2 = r.add_span(tr.trace_id, "skill", "plan", target="task_contract.py",
                     result="ok", evidence_ref="ev-001", lifecycle="PLAN")
    s3 = r.add_span(tr.trace_id, "human", "review", target="PR#42",
                     result="approved", sha_before="def456", sha_after="ghi789")

    # add_span 自动填 ts
    assert s1.ts and s2.ts and s3.ts
    assert s1.actor == "agent"
    assert s2.evidence_ref == "ev-001"
    assert s3.sha_after == "ghi789"

    r.end(tr.trace_id)
    snap = r.snapshot(tr.trace_id)
    assert len(snap["spans"]) == 3
    # 有序
    assert [s["action"] for s in snap["spans"]] == ["inspect", "plan", "review"]
    assert [s["actor"] for s in snap["spans"]] == ["agent", "skill", "human"]
    assert snap["ended_at"] is not None


# ---------- P0-06 Evidence Chain ----------
def test_evidence_chain_14_nodes_build_and_persist():
    r = evidence_chain.EvidenceChainRegistry()
    c = r.create("T-20260905-0001")
    assert c.evidence_id
    assert c.task_id == "T-20260905-0001"
    assert c.created_at

    # add_node 覆盖全部 15 类型（含 error 失败节点）
    for nt in evidence_chain.CHAIN_NODE_TYPES:
        r.add_node(c.evidence_id, nt, "ref:%s" % nt, detail="detail:%s" % nt,
                   actor="agent")

    assert len(evidence_chain.CHAIN_NODE_TYPES) == 15

    # build() 有 15 节点且类型均合法
    built = r.build(c.evidence_id)
    assert len(built["nodes"]) == 15
    node_types = [n["node_type"] for n in built["nodes"]]
    assert node_types == evidence_chain.CHAIN_NODE_TYPES
    for nt in node_types:
        assert nt in evidence_chain.CHAIN_NODE_TYPES
    # 节点字段完整
    for n in built["nodes"]:
        assert "ref" in n and "detail" in n and "actor" in n and "ts" in n

    # append-only：再次 build 仍 15 节点
    assert len(r.build(c.evidence_id)["nodes"]) == 15

    # persist 写 JSON（tempfile 目录，不污染仓库 evidence/）
    with tempfile.TemporaryDirectory() as td:
        path = r.persist(c.evidence_id, chains_dir=td)
        assert os.path.exists(path)
        assert path.endswith("%s.json" % c.evidence_id)
        import json
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["evidence_id"] == c.evidence_id
        assert len(data["nodes"]) == 15

    # snapshot
    snap = r.snapshot()
    assert snap["total"] == 1
    assert len(snap["chains"]) == 1


def test_evidence_chain_invalid_node_type_rejected():
    r = evidence_chain.EvidenceChainRegistry()
    c = r.create("T-20260905-0002")
    try:
        r.add_node(c.evidence_id, "invalid_type", "ref")
        assert False, "非法节点类型必须抛出 AssertionError"
    except AssertionError:
        pass


# ---------- P0-07 Evaluation Contract ----------
def test_evaluation_mean_and_thresholds():
    r = evaluation_contract.EvaluationRegistry()

    # ≥80 → passed
    ev_pass = r.evaluate("patch", "osai_engine/config.py",
                          {"correctness": 90, "completeness": 85, "performance": 80,
                           "safety": 95, "compliance": 90})
    expected = round((90 + 85 + 80 + 95 + 90) / 5, 1)
    assert ev_pass.overall == expected
    assert ev_pass.overall >= 80
    assert ev_pass.status == "passed"
    assert len(ev_pass.criteria) == 5

    # 60-80 → needs_review
    ev_review = r.evaluate("skill", "S01",
                            {"correctness": 70, "completeness": 65, "performance": 75,
                             "safety": 70, "compliance": 70})
    assert 60 <= ev_review.overall < 80
    assert ev_review.status == "needs_review"

    # <60 → failed
    ev_fail = r.evaluate("agent", "agent-1",
                          {"correctness": 50, "completeness": 40, "performance": 55,
                           "safety": 60, "compliance": 45})
    assert ev_fail.overall < 60
    assert ev_fail.status == "failed"

    # get
    assert r.get(ev_pass.eval_id) is ev_pass
    assert r.get("nonexistent") is None

    # by_target
    assert r.by_target("osai_engine/config.py") == [ev_pass]
    assert r.by_target("S01") == [ev_review]

    # evidence_ref 引用 evidence_chain id
    ev_ev = r.evaluate("task", "T-001",
                        {"correctness": 100, "completeness": 100, "performance": 100,
                         "safety": 100, "compliance": 100},
                        evidence_ref="ev-chain-abc")
    assert ev_ev.evidence_ref == "ev-chain-abc"
    assert ev_ev.status == "passed"


# ---------- P0-08 Lifecycle Contract ----------
def test_lifecycle_forward_to_retire():
    lt = lifecycle_contract.LifecycleTracker("e-1", entity_type="task")
    assert lt.current == "DISCOVER"
    # 正向逐态推进到 RETIRE
    for st in lifecycle_contract.LIFECYCLE_STATES[1:]:
        assert lt.transition(st, actor="agent", detail="推进到 %s" % st), \
            "向前迁移必须成功: %s" % st
    assert lt.current == "RETIRE"
    # history 包含全部 15 态（init + 14 次 transition）
    assert len(lt.history) == 15
    assert [h["state"] for h in lt.history] == lifecycle_contract.LIFECYCLE_STATES


def test_lifecycle_retire_terminal():
    lt = lifecycle_contract.LifecycleTracker("e-2", entity_type="skill")
    for st in lifecycle_contract.LIFECYCLE_STATES[1:]:
        lt.transition(st)
    # RETIRE 后任何 transition 返回 False
    assert lt.transition("DISCOVER") is False
    assert lt.transition("RETIRE") is False
    assert lt.transition("RELEASE") is False
    assert lt.current == "RETIRE"


def test_lifecycle_skip_level_rejected():
    lt = lifecycle_contract.LifecycleTracker("e-3", entity_type="feature")
    # 跳级 DISCOVER→IMPLEMENT 返回 False
    assert lt.transition("IMPLEMENT") is False
    assert lt.current == "DISCOVER"
    # 跳级 DISCOVER→RELEASE 返回 False
    assert lt.transition("RELEASE") is False
    # 合法推进 DISCOVER→REQUIREMENT
    assert lt.transition("REQUIREMENT") is True
    assert lt.current == "REQUIREMENT"
    # 从 REQUIREMENT 跳级到 TEST 返回 False
    assert lt.transition("TEST") is False


def test_lifecycle_allowed_next():
    lt = lifecycle_contract.LifecycleTracker("e-4", entity_type="contract")
    # DISCOVER 的下一个是 REQUIREMENT
    assert lt.allowed_next() == ["REQUIREMENT"]
    lt.transition("REQUIREMENT")
    assert lt.allowed_next() == ["RESEARCH"]
    # 推进到 RETIRE
    for st in lifecycle_contract.LIFECYCLE_STATES[2:]:
        lt.transition(st)
    # RETIRE 后 allowed_next 为空
    assert lt.allowed_next() == []
    # snapshot
    snap = lt.snapshot()
    assert snap["entity_id"] == "e-4"
    assert snap["current"] == "RETIRE"
    assert len(snap["history"]) == 15


def test_lifecycle_invalid_state_rejected():
    lt = lifecycle_contract.LifecycleTracker("e-5")
    assert lt.transition("INVALID_STATE") is False
    assert lt.current == "DISCOVER"


# ---------- 包导出：36 子模块均可访问 ----------
def test_import_all_39_submodules():
    expected = ["agent", "agent_identity", "agent_integration", "ai_gateway",
                "browser_capability", "browser_executor", "canonical_skill_registry", "config",
                "context_runtime", "delegation", "engine_layer", "engine_runtime",
                "engineering_loop", "evidence", "evidence_chain", "evaluation_contract",
                "harness_runtime", "learning_record_contract", "lifecycle_contract",
                "llm", "observability", "orchestrator", "permission_contract",
                "permission_gate", "repository_contract", "repository_registry",
                "research", "research_pipeline", "rules", "skill_registry",
                "skill_manifest", "skill_selector", "skill_invocation", "skill_sync",
                "task_contract", "tools", "trace_contract", "runtime_contract",
                "ui_state_contract"]
    assert len(osai_engine.__all__) == 39
    assert set(osai_engine.__all__) == set(expected)
    for name in expected:
        assert hasattr(osai_engine, name), "缺少子模块: %s" % name


# ---------- tools.git_commit_push 默认 deny 且不执行 git ----------
def test_git_commit_push_denied_no_git_write():
    old = os.environ.pop("OSAI_COMMIT_POLICY", None)
    try:
        with unittest.mock.patch("osai_engine.tools.subprocess.run") as mock_run:
            ok, out = tools.git_commit_push("D:\\Zachary OS AI", "should-not-run")
            assert ok is False
            assert "PERMISSION_DENIED" in out
            # 不执行任何 git 命令（subprocess.run 未被调用）
            mock_run.assert_not_called()
    finally:
        if old is not None:
            os.environ["OSAI_COMMIT_POLICY"] = old
