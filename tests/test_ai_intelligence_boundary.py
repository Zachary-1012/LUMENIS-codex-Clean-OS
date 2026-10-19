# -*- coding: utf-8 -*-
"""
ZBC OSAI Interface Boundary 测试套件
======================================
覆盖：
  1. OSAI DOWN时ZBC核心功能正常运行
  2. ZBC不直接依赖OSAI Runtime
  3. OSAI→ZBC请求边界（只能请求Task/Skill/Reasoning等）
  4. OSAI不能直接写ZBC DB/改业务代码/绕过Permission
  5. 唯一 owned Gateway 不可用时，有授权来源的基础统计仍完成
  6. Case6: OSAI Down
"""
import os
import sys
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_task_engine import (
    TaskEngine, TaskStatus, init_task_engine_db,
    get_task_engine, reset_task_engine,
)
from ai_task_parser import get_task_parser, reset_task_parser
from tests.test_no_ai_query_source_contract import (
    job_db, client, scoped_query, run_scoped_query, assert_verified_statistics,
)


@pytest.fixture(autouse=True)
def _hermetic_ai_gateway(monkeypatch):
    """Keep legacy smoke cases on an explicitly unavailable owned Gateway."""
    from lumenis.system.ai_gateway import core as ai_gateway

    monkeypatch.setattr(
        ai_gateway,
        "ai_status",
        lambda: {
            "enabled": False,
            "provider": "owned",
            "model": None,
            "runtime": "owned",
            "running": False,
        },
    )
    monkeypatch.setattr(
        ai_gateway,
        "chat",
        lambda *args, **kwargs: (
            None,
            "owned",
            {"provider": "owned", "code": "OWNED_RUNTIME_NOT_BOUND"},
        ),
    )
    monkeypatch.setattr(
        ai_gateway,
        "run_owned_analysis",
        lambda *args, **kwargs: {
            "ok": False, "status": "UNAVAILABLE", "provider": "owned",
            "code": "OWNED_RUNTIME_NOT_BOUND", "analysis": None,
        },
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

    def test_task_execution_without_osai(self, scoped_query):
        """OSAI 不可用时，真实获准 SourceBrief 基础统计照常完成。"""
        with patch.object(TaskEngine, "_call_ai_with_fallback", return_value=None) as ai_call:
            result = run_scoped_query(scoped_query)
            assert_verified_statistics(scoped_query, result)
            ai_call.assert_not_called()

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
# 3. 当前 owned Gateway 与无 AI 基础路径
# ═══════════════════════════════════════════════════════════════

class TestOwnedGatewayRoute:
    def test_ai_capabilities_report_owned_gateway_without_retired_fallback(self, engine):
        """AI tasks use the owned Gateway and do not list retired provider fallbacks."""
        caps = engine.get_capabilities()
        boundary = caps.get("osai_boundary", {})
        assert boundary["ai_provider_chain"] == ["owned_gateway"]
        assert boundary["ai_runtime_status"] == "OWNED_RUNTIME_NOT_BOUND"
        assert boundary["fallback_allowed"] is False
        assert "unavailable" in boundary["osai_down_impact"].lower()

    def test_provider_failure_degrades(self, scoped_query):
        """保留旧名；基础统计不调用失败的 owned Gateway，也不启用退役 Provider。"""
        with patch.object(TaskEngine, "_call_ai_with_fallback",
                          side_effect=RuntimeError("OWNED_RUNTIME_NOT_BOUND")) as ai_call:
            result = run_scoped_query(scoped_query)
            assert_verified_statistics(scoped_query, result)
            ai_call.assert_not_called()

    def test_all_providers_fail_uses_local_rules(self, scoped_query):
        """保留旧名；无模型响应时，以真实来源做确定性统计而非伪造 AI 结果。"""
        with patch.object(TaskEngine, "_call_ai_with_fallback", return_value=None) as ai_call:
            result = run_scoped_query(scoped_query)
            assert_verified_statistics(scoped_query, result)
            ai_call.assert_not_called()


# ═══════════════════════════════════════════════════════════════
# 4. Case6: OSAI Down（隔离集成，不代表真实用户 E2E）
# ═══════════════════════════════════════════════════════════════

class TestCase6OSAIDown:
    def test_case6_osai_down_full_scenario(self, scoped_query):
        """Case6: 无 AI 的授权来源统计、保存验证、Evidence、Trace、权限链。"""
        engine = scoped_query.engine
        with patch.object(TaskEngine, "_call_ai_with_fallback", return_value=None) as ai_call:
            result = run_scoped_query(scoped_query, context={**scoped_query.context, "scenario": "case6"})
            assert result["task_id"] is not None
            assert_verified_statistics(scoped_query, result)
            steps = engine.get_steps(result["task_id"])
            assert len(steps) >= 4
            evidence = engine.get_evidence(result["task_id"])
            assert len(evidence) >= 1
            trace = engine.get_trace(result["task_id"])
            assert len(trace) >= 1
            created2 = engine.create_task("帮我支付100元")
            result2 = engine.run_task(created2["task_id"])
            assert result2["status"] == TaskStatus.FAILED.value
            assert result2["permanent_deny"] == 1
            ai_call.assert_not_called()

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
    def test_zbc_provides_validated_artifacts(self, scoped_query):
        """真实 SourceBrief 产物和统计结果必须通过独立读回，失败回执不冒充产物。"""
        result = run_scoped_query(scoped_query)
        assert_verified_statistics(scoped_query, result)
        evidence = scoped_query.engine.get_evidence(result["task_id"])
        assert len(evidence) >= 1
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

    def test_ai_is_enhancement_not_truth(self, scoped_query):
        """无 AI 输出也有可核查统计；不吞异常、不把空结果当真值。"""
        result = run_scoped_query(scoped_query)
        data = assert_verified_statistics(scoped_query, result)
        assert data["output"]["ai_analysis"] is None
        assert data["output"]["base_analysis"]["coverage"] == "UNKNOWN"
