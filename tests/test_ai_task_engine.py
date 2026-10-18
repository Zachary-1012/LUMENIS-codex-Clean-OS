# -*- coding: utf-8 -*-
"""
ZBC AI Task Engine 测试套件
=============================
覆盖：
  1. Task Parser：Intent分类/实体提取/风险等级判定
  2. Agent Registry：Agent注册/Intent匹配/Skill选择
  3. Task Engine：创建/解析/Agent选择/权限/执行/验证/Trace
  4. Evidence链式哈希完整性
  5. 正常任务执行闭环（Case1: 信息搜索）
  6. 任务取消
  7. 熔断器
"""
import os
import sys
import hashlib
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_task_parser import (
    TaskParser, Intent, TaskRiskLevel, ParsedTask,
    get_task_parser, reset_task_parser,
)
from ai_agent_registry import (
    AgentSpec, AgentRegistry, get_agent_registry, reset_agent_registry,
)
from ai_task_engine import (
    TaskEngine, TaskStatus, StepPhase, CircuitBreaker,
    init_task_engine_db, get_task_engine, reset_task_engine,
)


@pytest.fixture(autouse=True)
def _hermetic_ai_gateway(monkeypatch):
    """Prevent workstation provider settings from starting real inference."""
    from lumenis.system.ai_gateway import core as ai_gateway

    monkeypatch.setattr(
        ai_gateway,
        "ai_status",
        lambda: {
            "enabled": False,
            "provider": "local_rule",
            "model": "deterministic_rule",
            "runtime": "rule",
            "running": False,
        },
    )
    monkeypatch.setattr(
        ai_gateway,
        "chat",
        lambda *args, **kwargs: (
            None,
            "rule",
            {"provider": "rule", "model": "deterministic_rule"},
        ),
    )


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def parser():
    reset_task_parser()
    return get_task_parser()


@pytest.fixture
def registry():
    reset_agent_registry()
    return get_agent_registry()


@pytest.fixture
def engine():
    reset_task_engine()
    init_task_engine_db()
    from database import get_db
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS notes (note_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY)")
    return get_task_engine()


# ═══════════════════════════════════════════════════════════════
# 1. Task Parser 测试
# ═══════════════════════════════════════════════════════════════

class TestTaskParser:
    def test_query_data_intent(self, parser):
        result = parser.parse("查一下今天的舆情量")
        assert result.intent == Intent.QUERY_DATA
        assert result.confidence > 0

    def test_summarize_intent(self, parser):
        result = parser.parse("总结一下今天的数据")
        assert result.intent == Intent.SUMMARIZE

    def test_generate_report_intent(self, parser):
        result = parser.parse("生成周报")
        assert result.intent == Intent.GENERATE_REPORT

    def test_compare_intent(self, parser):
        result = parser.parse("对比一下上周和本周的数据")
        assert result.intent == Intent.COMPARE

    def test_risk_explain_intent(self, parser):
        result = parser.parse("解释风险原因")
        assert result.intent == Intent.RISK_EXPLAIN

    def test_unknown_intent(self, parser):
        result = parser.parse("asdfghjkl随机无意义文本xyz")
        assert result.intent == Intent.UNKNOWN
        # UNKNOWN 应为 L3（fail-closed）
        assert result.risk_level == TaskRiskLevel.L3

    def test_empty_input(self, parser):
        result = parser.parse("")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == 0.0

    def test_entity_extraction_date(self, parser):
        result = parser.parse("查一下2026年9月1日的舆情数据")
        assert "date" in result.entities
        assert len(result.entities["date"]) > 0

    def test_entity_extraction_platform(self, parser):
        result = parser.parse("小红书上有多少条笔记")
        assert "platform" in result.entities
        assert "小红书" in result.entities["platform"]

    def test_permanent_deny_payment(self, parser):
        result = parser.parse("帮我支付100元")
        assert result.permanent_deny is True
        assert result.risk_level == TaskRiskLevel.L4

    def test_admin_required_delete(self, parser):
        result = parser.parse("删除数据库所有表")
        assert result.admin_required is True
        assert result.risk_level == TaskRiskLevel.L4

    def test_human_approval_publish(self, parser):
        result = parser.parse("帮我发布一条小红书笔记")
        assert result.human_approval_required is True
        assert result.risk_level == TaskRiskLevel.L3

    def test_human_approval_login(self, parser):
        result = parser.parse("帮我登录账号")
        assert result.human_approval_required is True

    def test_l0_risk_for_query(self, parser):
        result = parser.parse("查一下数据统计")
        assert result.risk_level == TaskRiskLevel.L0

    def test_l1_risk_for_analysis(self, parser):
        result = parser.parse("分析原因")
        assert result.risk_level == TaskRiskLevel.L1

    def test_l2_risk_for_browser(self, parser):
        result = parser.parse("打开浏览器搜索一下")
        assert result.risk_level == TaskRiskLevel.L2

    def test_list_intents(self, parser):
        intents = parser.list_intents()
        assert len(intents) >= 12
        intent_values = [i["intent"] for i in intents]
        assert "query_data" in intent_values
        assert "generate_report" in intent_values


# ═══════════════════════════════════════════════════════════════
# 2. Agent Registry 测试
# ═══════════════════════════════════════════════════════════════

class TestAgentRegistry:
    def test_builtin_agents_registered(self, registry):
        agents = registry.list_all()
        assert len(agents) >= 4

    def test_data_query_agent_exists(self, registry):
        agent = registry.get("data_query_agent")
        assert agent is not None
        assert "query_data" in agent.capabilities

    def test_analysis_agent_exists(self, registry):
        agent = registry.get("analysis_agent")
        assert agent is not None
        assert "reason" in agent.capabilities

    def test_report_agent_exists(self, registry):
        agent = registry.get("report_agent")
        assert agent is not None
        assert "generate_report" in agent.capabilities

    def test_browser_agent_exists(self, registry):
        agent = registry.get("browser_agent")
        assert agent is not None
        assert "open_browser" in agent.capabilities

    def test_find_agents_for_query_intent(self, registry):
        agents = registry.find_agents_for_intent(Intent.QUERY_DATA)
        assert len(agents) >= 1
        assert any(a.agent_id == "data_query_agent" for a in agents)

    def test_select_best_agent_for_query(self, registry):
        agent = registry.select_best_agent(Intent.QUERY_DATA)
        assert agent is not None
        assert agent.agent_id == "data_query_agent"

    def test_select_best_agent_for_report(self, registry):
        agent = registry.select_best_agent(Intent.GENERATE_REPORT)
        assert agent is not None
        assert agent.agent_id == "report_agent"

    def test_select_best_agent_for_unknown(self, registry):
        agent = registry.select_best_agent(Intent.UNKNOWN)
        assert agent is None

    def test_select_skills_fallback_chain(self, registry):
        agent = registry.get("data_query_agent")
        skills = registry.select_skills(agent, Intent.QUERY_DATA)
        assert isinstance(skills, list)
        # 至少包含 preferred_skills
        for s in agent.preferred_skills:
            assert s in skills

    def test_register_custom_agent(self, registry):
        spec = AgentSpec(
            agent_id="test_agent",
            name="Test Agent",
            description="Test",
            capabilities=["query_data"],
            required_permission="READ",
            risk_level=TaskRiskLevel.L0,
        )
        result = registry.register(spec)
        assert result is True
        assert registry.has("test_agent")

    def test_stats(self, registry):
        stats = registry.stats()
        assert "total" in stats
        assert stats["total"] >= 4
        assert "capabilities_covered" in stats

    def test_capabilities_matrix(self, registry):
        matrix = registry.get_capabilities_matrix()
        assert "agents" in matrix
        assert "intent_to_agents" in matrix
        assert "stats" in matrix


# ═══════════════════════════════════════════════════════════════
# 3. Task Engine 测试
# ═══════════════════════════════════════════════════════════════

class TestTaskEngine:
    def test_health_check(self, engine):
        health = engine.health_check()
        assert health["status"] == "healthy"
        assert health["db"] == "connected"

    def test_create_task(self, engine):
        task = engine.create_task("测试任务", context={"page": "/test"})
        assert task["task_id"] is not None
        assert task["status"] == TaskStatus.PENDING.value
        assert task["user_input"] == "测试任务"

    def test_get_task(self, engine):
        created = engine.create_task("获取测试")
        fetched = engine.get_task(created["task_id"])
        assert fetched is not None
        assert fetched["task_id"] == created["task_id"]

    def test_get_nonexistent_task(self, engine):
        result = engine.get_task("nonexistent_task_id")
        assert result is None

    def test_list_tasks(self, engine):
        engine.create_task("列表测试1")
        engine.create_task("列表测试2")
        tasks = engine.list_tasks(limit=10)
        assert len(tasks) >= 2

    def test_parse_task_query(self, engine):
        created = engine.create_task("查一下今天舆情量统计")
        parsed = engine.parse_task(created["task_id"])
        assert parsed["intent"] == "query_data"
        assert parsed["status"] in ("ready", "parsing", "pending")

    def test_parse_permanent_deny(self, engine):
        created = engine.create_task("帮我支付100元")
        result = engine.parse_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["permanent_deny"] == 1

    def test_parse_admin_required(self, engine):
        created = engine.create_task("删除数据库所有表")
        result = engine.parse_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["admin_required"] == 1

    def test_parse_human_approval(self, engine):
        created = engine.create_task("帮我发布一条笔记")
        result = engine.parse_task(created["task_id"])
        assert result["status"] == TaskStatus.AWAITING_APPROVAL.value
        assert result["human_approval_required"] == 1

    def test_select_agent_and_skill(self, engine):
        created = engine.create_task("查一下数据统计")
        engine.parse_task(created["task_id"])
        result = engine.select_agent_and_skill(created["task_id"])
        assert result["agent_id"] == "data_query_agent"

    def test_check_permission_l0(self, engine):
        created = engine.create_task("查一下数据统计")
        engine.parse_task(created["task_id"])
        engine.select_agent_and_skill(created["task_id"])
        result = engine.check_permission(created["task_id"])
        assert result["status"] == TaskStatus.READY.value
        assert result["permission_result"] is not None

    def test_execute_task_query(self, engine):
        created = engine.create_task("查一下数据统计")
        result = engine.run_task(created["task_id"])
        # Database execution is observed, but this generic query has no independent Owner Outcome.
        assert result["status"] == TaskStatus.FAILED.value
        assert result["result"]["output"]["error"] == "SCOPED_SOURCE_OWNER_REQUIRED"
        assert result["error"] == "SCOPED_SOURCE_OWNER_REQUIRED"
        assert result["result_json"] is not None

    def test_full_call_chain_case1(self, engine):
        """Isolated routing trace; deliberately not complete user acceptance."""
        created = engine.create_task("帮我查一下今天太古汇的舆情量统计", context={"current_page": "/dashboard"})
        result = engine.run_task(created["task_id"])

        # Routing/permission/execution records do not establish a user outcome.
        assert result["status"] == TaskStatus.FAILED.value
        assert result["result"]["output"]["error"] == "SCOPED_SOURCE_OWNER_REQUIRED"
        assert result["result"]["verification"]["verified"] is False
        assert result["error"] == "SCOPED_SOURCE_OWNER_REQUIRED"
        # Intent正确
        assert result["intent"] == "query_data"
        # Agent正确
        assert result["agent_id"] == "data_query_agent"
        # 风险L0
        assert result["risk_level"] == "L0"
        # 权限通过
        assert result["permission_result"] is not None

        # 步骤完整（至少包含 parse/agent_select/skill_select/permission/execute/verify）
        steps = engine.get_steps(created["task_id"])
        step_phases = [s["phase"] for s in steps]
        assert "parse" in step_phases
        assert "agent_select" in step_phases
        assert "permission" in step_phases
        assert "execute" in step_phases
        assert "verify" in step_phases

        # Evidence存在
        evidence = engine.get_evidence(created["task_id"])
        assert len(evidence) >= 1

        # Trace存在
        trace = engine.get_trace(created["task_id"])
        assert len(trace) >= 1

    def test_evidence_chain_hash_integrity(self, engine):
        """Evidence链式哈希完整性验证"""
        created = engine.create_task("链式哈希测试")
        engine.run_task(created["task_id"])
        evidence = engine.get_evidence(created["task_id"])
        assert len(evidence) >= 1

        prev_hash = None
        for ev in evidence:
            assert ev["current_hash"] is not None
            assert len(ev["current_hash"]) == 64  # SHA256
            if prev_hash:
                assert ev["previous_hash"] == prev_hash
            # 重新计算验证
            p = ev["previous_hash"] or "genesis"
            raw = p + "|" + ev["evidence_id"] + "|" + ev["task_id"] + "|" + ev["content"] + "|" + ev["created_at"]
            expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            assert expected == ev["current_hash"], f"Hash mismatch at {ev['evidence_id']}"
            prev_hash = ev["current_hash"]

    def test_cancel_task(self, engine):
        created = engine.create_task("取消测试")
        result = engine.cancel_task(created["task_id"], reason="test cancel")
        assert result["status"] == TaskStatus.CANCELLED.value
        assert result["error"] == "test cancel"

    def test_approve_task(self, engine):
        created = engine.create_task("帮我发布一条笔记")
        engine.parse_task(created["task_id"])  # → awaiting_approval
        approved = engine.approve_task(created["task_id"], approved_by="tester", approval_note="test")
        assert approved["status"] == TaskStatus.READY.value
        assert approved["approved_by"] == "tester"
        assert approved["approval_token"] is not None

    def test_capabilities(self, engine):
        caps = engine.get_capabilities()
        assert "intents" in caps
        assert "agents" in caps
        assert "circuit_breaker" in caps
        assert "osai_boundary" in caps
        assert caps["osai_boundary"]["zbc_depends_on_osai"] is False

    def test_get_permissions(self, engine):
        perms = engine.get_permissions()
        assert perms is not None
        # PermissionGate 可用或降级
        assert "enabled_permissions" in perms or "permission_gate" in perms


# ═══════════════════════════════════════════════════════════════
# 4. Circuit Breaker 测试
# ═══════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=1)
        assert cb.can_execute() is True
        assert cb.get_state()["state"] == "closed"

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.can_execute() is False
        assert cb.get_state()["state"] == "open"

    def test_recovery_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=1)
        cb.record_failure()
        assert cb.can_execute() is False
        import time
        time.sleep(1.5)
        assert cb.can_execute() is True  # half_open
        assert cb.get_state()["state"] == "half_open"

    def test_success_resets(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.get_state()["state"] == "closed"
        assert cb.get_state()["failure_count"] == 0


# ═══════════════════════════════════════════════════════════════
# 5. DB Migration 测试（向后兼容）
# ═══════════════════════════════════════════════════════════════

class TestDBMigration:
    def test_tables_exist(self, engine):
        import sqlite3
        from ai_task_engine import DB_PATH
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "ai_task" in tables
        assert "ai_task_step" in tables
        assert "ai_task_evidence" in tables
        assert "ai_task_trace" in tables

    def test_evidence_hash_columns_exist(self, engine):
        import sqlite3
        from ai_task_engine import DB_PATH
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(ai_task_evidence)").fetchall()}
        assert "previous_hash" in cols
        assert "current_hash" in cols

    def test_migration_idempotent(self, engine):
        # 重复执行不应报错
        init_task_engine_db()
        init_task_engine_db()
        assert True  # 无异常即通过
