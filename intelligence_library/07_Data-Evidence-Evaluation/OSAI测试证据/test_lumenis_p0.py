# -*- coding: utf-8 -*-
"""LUMENIS P0 Dual-Core Convergence Foundation 测试（2026-09-05）。

覆盖：Repository Registry / Cross-platform Resolver / Permission Gate /
Agent Permission Boundary / Engineering Loop / Skill Registry / AI Gateway。
全部确定性、可离线运行（不依赖网络与智谱）。
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import (ai_gateway, engineering_loop, permission_gate,
                         repository_registry, skill_registry)


# ---------- P0-01/03 Repository Registry + Cross-platform Resolver ----------
def test_registry_resolves_both_cores():
    for key in ("ZBC", "OSAI"):
        root = repository_registry.resolve_path(key)
        assert os.path.isdir(root), "%s root 必须存在: %s" % (key, root)
    assert isinstance(repository_registry.git_branch("OSAI"), str) and \
        repository_registry.git_branch("OSAI"), "branch 必须可解析"


def test_registry_python_resolver():
    py = repository_registry.resolve_python("ZBC")
    assert isinstance(py, str) and py, "解释器必须可解析"
    assert py.endswith(".exe") or "python" in os.path.basename(py), "必须是 python 解释器"


def test_registry_snapshot_fields():
    info = repository_registry.get_repo_info("OSAI")
    for f in ("name", "role", "root", "python", "branch", "sha"):
        assert f in info, "快照缺字段 %s" % f
    assert info["role"] == "intelligence"
    assert repository_registry.get_repo_info("ZBC")["role"] == "production"


def test_env_override_path():
    # 环境变量优先（ZBC_ROOT 指向 OSAI 自身也成立）
    old = os.environ.get("ZBC_ROOT")
    os.environ["ZBC_ROOT"] = repository_registry.resolve_path("OSAI")
    try:
        assert repository_registry.resolve_path("ZBC") == repository_registry.resolve_path("OSAI")
    finally:
        if old is None:
            os.environ.pop("ZBC_ROOT", None)
        else:
            os.environ["ZBC_ROOT"] = old


# ---------- P0-02/12 Permission Gate + Agent Boundary ----------
def test_gate_eleven_levels():
    g = permission_gate.gate
    assert len(permission_gate.LEVELS) == 11
    assert permission_gate.LEVELS["READ"] < permission_gate.LEVELS["PUSH"]


def test_agent_boundary_ends_at_verify():
    g = permission_gate.gate
    for lv in ("READ", "AUDIT", "ANALYZE", "RESEARCH", "PLAN", "PATCH_PREVIEW", "TEST", "VERIFY"):
        assert g.check(lv), "%s 应允许 Agent 自动化" % lv
    for lv in ("HUMAN_APPROVAL", "COMMIT", "PUSH"):
        assert not g.check(lv), "%s 必须人工/受控" % lv


def test_commit_default_denied():
    g = permission_gate.gate
    old = os.environ.get("OSAI_COMMIT_POLICY")
    os.environ.pop("OSAI_COMMIT_POLICY", None)
    try:
        allowed, reason = g.check_commit_allowed()
        assert allowed is False
        assert "PERMISSION_DENIED" in reason
    finally:
        if old is not None:
            os.environ["OSAI_COMMIT_POLICY"] = old


def test_commit_approve_via_env():
    g = permission_gate.gate
    old = os.environ.get("OSAI_COMMIT_POLICY")
    os.environ["OSAI_COMMIT_POLICY"] = "approve"
    try:
        allowed, _ = g.check_commit_allowed()
        assert allowed is True
    finally:
        if old is None:
            os.environ.pop("OSAI_COMMIT_POLICY", None)
        else:
            os.environ["OSAI_COMMIT_POLICY"] = old


def test_human_approval_record_and_verify():
    import tempfile
    # 独立 gate + 临时文件，避免污染仓库 evidence/approvals.json
    g = permission_gate.PermissionGate(
        approvals_file=os.path.join(tempfile.gettempdir(), "lumenis-test-approvals.json"))
    aid = g.require_human_approval("测试批准", repo="OSAI", by="TEST-HUMAN")
    assert aid and g.is_approved(aid)
    assert not g.is_approved("nonexistent")


# ---------- P0-11 Engineering Loop ----------
def test_loop_stage_sequence():
    loop = engineering_loop.EngineeringLoop("测试", repo="OSAI")
    assert loop.allowed_next() == ["INSPECT"]
    loop.step("INSPECT", "ok", "读取事实")
    assert "PLAN" in loop.allowed_next()
    loop.step("PLAN", "ok")
    loop.step("EXECUTE", "ok")
    loop.step("VERIFY", "failed", "单测失败")
    loop.step("REPAIR", "ok")
    assert "VERIFY" in loop.allowed_next()


def test_loop_repair_capped():
    loop = engineering_loop.EngineeringLoop("测试", repo="OSAI")
    for _ in range(engineering_loop._MAX_REPAIR + 3):
        loop.step("REPAIR", "ok")
    assert loop.repair_exhausted(), "超过上限必须报告 exhausted"
    assert loop.to_evidence_dict()["repair_count"] == engineering_loop._MAX_REPAIR, \
        "超限 REPAIR 必须被拦截，不再计数"
    assert loop.allowed_next() == [], "终止后不得再推进"
    assert loop.to_evidence_dict()["result"] == "failed", "超限必须显式 failed"


def test_loop_result_denied():
    loop = engineering_loop.EngineeringLoop("测试", repo="OSAI")
    loop.step("INSPECT", "ok")
    loop.step("HUMAN_APPROVAL", "denied", "等待人工")
    assert loop.to_evidence_dict()["result"] == "awaiting_approval"


# ---------- P0-09 Skill Registry ----------
def test_skill_catalog_72():
    r = skill_registry.registry
    snap = r.snapshot()
    assert snap["total"] == 72, "72 Skills 目录必须完整，实际 %d" % snap["total"]
    assert len(skill_registry.CATEGORIES) == 8


def test_skill_categories_balanced():
    r = skill_registry.registry
    for cat in skill_registry.CATEGORIES:
        assert len(r.by_category(cat)) >= 4, "%s 类别至少 4 个 Skill" % cat


def test_subject_protected_skills_readonly():
    r = skill_registry.registry
    for sid in skill_registry.SUBJECT_PROTECTED:
        perms = r.get(sid)["permissions"]
        assert "PUSH" not in perms and "COMMIT" not in perms and "WRITE" not in perms
        assert set(perms) <= {"READ", "AUDIT", "ANALYZE"}


def test_skill_register_custom():
    r = skill_registry.registry
    r.register("S99", name="测试 Skill", category="governance", version="0.0.1")
    assert r.get("S99")["category"] == "governance"
    r.set_status("S99", "evaluated")
    r.count_usage("S99")
    assert r.get("S99")["usage_count"] == 1
    assert r.get("S99")["status"] == "evaluated"


# ---------- P0-10 AI Gateway ----------
def test_gateway_provider_catalog():
    snap = ai_gateway.gateway_snapshot()
    for p in ("zhipu", "ollama", "gpt-oss"):
        assert p in snap["providers"]
    for p in ("ark", "qwen", "openai"):
        assert p not in snap["providers"], f"dead provider {p} should be removed"
    assert snap["providers"]["zhipu"]["models"]["strong"] == "glm-5.3"
    assert snap["providers"]["zhipu"]["models"]["vision"] == "glm-4.6v"


def test_gateway_route_daily_prefers_zhipu():
    # 不依赖真实 key：验证路由逻辑本身（可用性由 provider_available 决定）
    old = {k: os.environ.get(k) for k in ("ZHIPU_API_KEY", "ARK_API_KEY", "DASHSCOPE_API_KEY")}
    try:
        os.environ["ZHIPU_API_KEY"] = "test-key"
        p, m, meta = ai_gateway.route("daily")
        assert p == "zhipu" and m == "glm-4.5-air" and meta["primary"]
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_gateway_route_fallback_chain():
    """V4 P0-05: zhipu 不可用时 fallback 到 local ollama，不再经过 ark/qwen。"""
    old = {k: os.environ.get(k) for k in ("ZHIPU_API_KEY",)}
    try:
        os.environ.pop("ZHIPU_API_KEY", None)
        with patch.object(ai_gateway, "provider_available",
                          side_effect=lambda name: name in ("ollama", "gpt-oss")):
            p, m, meta = ai_gateway.route("daily")
            assert p == "ollama" and meta["primary"] is False and meta["fallback_of"] == "zhipu"
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
