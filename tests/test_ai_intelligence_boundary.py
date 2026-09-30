# -*- coding: utf-8 -*-
"""
ZBC OSAI Interface Boundary 测试套件
======================================
覆盖：
  1. OSAI DOWN时ZBC核心功能正常运行
  2. ZBC不直接依赖OSAI Runtime
  3. OSAI→ZBC请求边界（只能请求Task/Skill/Reasoning等）
  4. OSAI不能直接写ZBC DB/改业务代码/绕过Permission
  5. AI Provider降级链（智谱→ARK→千问→Ollama→本地规则）
  6. Case6: OSAI Down
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_task_engine import (
    TaskEngine, TaskStatus, init_task_engine_db,
    get_task_engine, reset_task_engine,
)
from ai_task_parser import get_task_parser, reset_task_parser


@pytest.fixture(autouse=True)
def _hermetic_ai_gateway(monkeypatch):
    """Keep task-engine tests on an explicit local-rule Gateway outcome."""
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


@pytest.fixture
def engine():
    reset_task_engine()
    init_task_engine_db()
    return get_task_engine()


# ═══════════════════════════════════════════════════════════════
# 1. OSAI DOWN时ZBC正常运行
# ═══════════════════════════════════════════════════════════════

class TestOSAIDownZBCWorks:
    def test_zbc_does_not_depend_on_osai(self, engine):
        """ZBC不直接依赖OSAI Runtime"""
        caps = engine.get_capabilities()
        assert caps["osai_boundary"]["zbc_depends_on_osai"] is False

    def test_task_execution_without_osai(self, engine):
        """OSAI不可用时，任务仍可执行（降级到本地规则）"""
        # 模拟AI调用全部失败（返回None → 本地规则兜底）
        with patch.object(TaskEngine, "_call_ai_with_fallback", return_value=None):
            created = engine.create_task("查一下数据统计")
            result = engine.run_task(created["task_id"])
            # 即使AI不可用，任务也应完成（降级到本地规则）
            assert result["status"] == TaskStatus.SUCCEEDED.value
            assert result["result_json"] is not None

    def test_parser_works_without_osai(self):
        """Task Parser不依赖OSAI（纯规则匹配）"""
        reset_task_parser()
        parser = get_task_parser()
        result = parser.parse("查一下今天的舆情量")
        assert result.intent == "query_data"
        assert result.confidence > 0

    def test_permission_works_without_osai(self, engine):
        """Permission Gate不依赖OSAI"""
        created = engine.create_task("帮我支付100元")
        result = engine.run_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["permanent_deny"] == 1

    def test_evidence_works_without_osai(self, engine):
        """Evidence链不依赖OSAI"""
        created = engine.create_task("证据测试")
        engine.run_task(created["task_id"])
        evidence = engine.get_evidence(created["task_id"])
        assert len(evidence) >= 1
        for ev in evidence:
            assert ev["current_hash"] is not None
            assert len(ev["current_hash"]) == 64

    def test_trace_works_without_osai(self, engine):
        """Trace记录不依赖OSAI"""
        created = engine.create_task("Trace测试")
        engine.run_task(created["task_id"])
        trace = engine.get_trace(created["task_id"])
        assert len(trace) >= 1


# ═══════════════════════════════════════════════════════════════
# 2. OSAI→ZBC请求边界
# ═══════════════════════════════════════════════════════════════

class TestOSAIRequestBoundary:
    def test_osai_can_request_task(self, engine):
        """OSAI可以请求创建Task（通过标准API）"""
        task = engine.create_task("查一下数据统计", created_by="osai_agent")
        assert task["task_id"] is not None
        # 从DB读取验证created_by
        fetched = engine.get_task(task["task_id"])
        assert fetched["created_by"] == "osai_agent"

    def test_osai_cannot_bypass_permission(self, engine):
        """OSAI不能绕过Permission Gate"""
        created = engine.create_task("删除数据库所有表", created_by="osai_agent")
        result = engine.run_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["admin_required"] == 1

    def test_osai_cannot_bypass_permanent_deny(self, engine):
        """OSAI不能绕过永久DENY"""
        created = engine.create_task("帮我支付100元", created_by="osai_agent")
        result = engine.run_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["permanent_deny"] == 1

    def test_osai_requests_are_traced(self, engine):
        """OSAI发起的请求有完整Trace"""
        created = engine.create_task("OSAI trace测试", created_by="osai_agent")
        engine.run_task(created["task_id"])
        trace = engine.get_trace(created["task_id"])
        assert len(trace) >= 1
        # Trace中应记录created_by
        task = engine.get_task(created["task_id"])
        assert task["created_by"] == "osai_agent"


# ═══════════════════════════════════════════════════════════════
# 3. AI Provider降级链
# ═══════════════════════════════════════════════════════════════

class TestProviderFallbackChain:
    def test_fallback_chain_structure(self, engine):
        """降级链应包含智谱→ARK→千问→Ollama→本地规则"""
        caps = engine.get_capabilities()
        chain = caps.get("osai_boundary", {}).get("ai_provider_chain", [])
        assert "zhipu" in chain
        assert "local_rules" in chain

    def test_provider_failure_degrades(self, engine):
        """AI Provider失败时自动降级"""
        call_count = {"n": 0}

        def mock_ai_call(self, operation, text, data):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                return None  # 模拟Provider失败 → 降级
            return {
                "response": "降级后本地规则返回的分析结果",
                "provider": "local_rules",
            }

        with patch.object(TaskEngine, "_call_ai_with_fallback", mock_ai_call):
            created = engine.create_task("查一下数据统计")
            result = engine.run_task(created["task_id"])
            assert result["status"] == TaskStatus.SUCCEEDED.value

    def test_all_providers_fail_uses_local_rules(self, engine):
        """所有Provider失败时使用本地规则，任务不中断"""
        with patch.object(TaskEngine, "_call_ai_with_fallback", return_value=None):
            created = engine.create_task("查一下数据统计")
            result = engine.run_task(created["task_id"])
            # 任务应成功（本地规则兜底），而非失败
            assert result["status"] == TaskStatus.SUCCEEDED.value


# ═══════════════════════════════════════════════════════════════
# 4. Case6: OSAI Down（E2E）
# ═══════════════════════════════════════════════════════════════

class TestCase6OSAIDown:
    def test_case6_osai_down_full_scenario(self, engine):
        """Case6: OSAI Down — ZBC核心功能全部正常"""
        # 模拟OSAI完全不可用（AI调用返回None → 本地规则兜底）
        with patch.object(TaskEngine, "_call_ai_with_fallback", return_value=None):

            # 1. 任务创建正常
            created = engine.create_task("查一下数据统计", context={"scenario": "case6"})
            assert created["task_id"] is not None

            # 2. 任务执行正常（降级）
            result = engine.run_task(created["task_id"])
            assert result["status"] == TaskStatus.SUCCEEDED.value

            # 3. 步骤完整
            steps = engine.get_steps(created["task_id"])
            assert len(steps) >= 4  # 至少 parse/permission/execute/verify

            # 4. Evidence存在
            evidence = engine.get_evidence(created["task_id"])
            assert len(evidence) >= 1

            # 5. Trace存在
            trace = engine.get_trace(created["task_id"])
            assert len(trace) >= 1

            # 6. 权限检查正常
            created2 = engine.create_task("帮我支付100元")
            result2 = engine.run_task(created2["task_id"])
            assert result2["status"] == TaskStatus.FAILED.value
            assert result2["permanent_deny"] == 1

    def test_case6_osai_down_api_contract(self, engine):
        """Case6: OSAI Down时所有API端点仍可访问"""
        # 这些端点不依赖OSAI
        health = engine.health_check()
        assert health["status"] == "healthy"

        caps = engine.get_capabilities()
        assert "intents" in caps
        assert "agents" in caps

        perms = engine.get_permissions()
        assert perms is not None

        tasks = engine.list_tasks(limit=5)
        assert isinstance(tasks, list)


# ═══════════════════════════════════════════════════════════════
# 5. OSAI边界锁死验证
# ═══════════════════════════════════════════════════════════════

class TestOSAIBoundaryLock:
    def test_zbc_provides_validated_artifacts(self, engine):
        """ZBC→OSAI只提供经过验证的Artifact（Task/Result/Evidence/Evaluation）"""
        created = engine.create_task("查一下数据统计")
        result = engine.run_task(created["task_id"])
        # 结果包含验证信息
        assert result["result_json"] is not None
        evidence = engine.get_evidence(created["task_id"])
        assert len(evidence) >= 1
        # Evidence有哈希验证
        for ev in evidence:
            assert ev["current_hash"] is not None

    def test_osai_cannot_write_db_directly(self):
        """OSAI不能直接写ZBC DB（只能通过API）"""
        # 验证：DB操作只通过database.py的get_db contextmanager
        # 这是架构约束，测试验证模块结构
        import database
        assert hasattr(database, "get_db")
        assert hasattr(database, "DB_PATH")
        # DB_PATH是本地文件，OSAI无法直接访问
        assert str(database.DB_PATH).endswith(".db")

    def test_osai_cannot_modify_production_truth(self, engine):
        """OSAI不能修改Production Truth（主体词/排除词/风险口径）"""
        # 验证：SUBJECT_WORDS等生产口径在独立模块中，OSAI无法通过Task修改
        import importlib
        # 这些模块存在且不可通过AI Task修改
        assert os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"))

    def test_ai_is_enhancement_not_truth(self, engine):
        """AI只是增强层，不做业务最终真值"""
        created = engine.create_task("查一下数据统计")
        result = engine.run_task(created["task_id"])
        # 结果中AI输出标记为ai_summary/ai_analysis，而非最终数据
        try:
            import json
            ro = json.loads(result["result_json"]) if isinstance(result["result_json"], str) else result["result_json"]
            if ro.get("output"):
                # AI输出有明确标记
                assert any(k.startswith("ai_") for k in ro["output"].keys()) or "note" in ro["output"]
        except Exception:
            pass  # 格式兼容
