# -*- coding: utf-8 -*-
"""
agent_situational 测试用例
============================
覆盖：空context、完整context、风险升级、模块切换、意图推断、
低置信度、系统异常、页面跳转，以及 adapters 集成。
"""
import pytest

from agent_situational import (
    Situation,
    SituationAnalyzer,
    get_situation,
    intent_from_situation,
    from_agent_loop,
    from_observation,
    merge_contexts,
    RISK_LOW,
    RISK_MEDIUM,
    RISK_HIGH,
    RISK_CRITICAL,
    SYS_HEALTHY,
    SYS_DEGRADED,
    SYS_UNAVAILABLE,
    SYS_UNKNOWN,
    PHASE_EXECUTING,
    PHASE_IDLE,
    INTENT_ANALYZE,
    INTENT_REPORT,
    INTENT_MONITOR,
    INTENT_TROUBLESHOOT,
    INTENT_UNKNOWN,
    ACTION_ESCALATE,
    ACTION_PAUSE,
    ACTION_CONTINUE,
    ACTION_REPLAN,
)


# ── 1. 空 context ────────────────────────────────────────────

class TestEmptyContext:
    """空 context 应返回默认 Situation，不崩溃。"""

    def test_none_context(self):
        sit = get_situation(None)
        assert isinstance(sit, Situation)
        assert sit.current_page == ""
        assert sit.active_module == ""
        assert sit.task_phase == PHASE_IDLE
        assert sit.system_status == SYS_UNKNOWN
        assert sit.risk_level == RISK_LOW
        assert sit.user_intent == INTENT_UNKNOWN
        assert sit.confidence < 0.4
        assert sit.situation_id.startswith("sit_")

    def test_empty_dict(self):
        sit = get_situation({})
        assert isinstance(sit, Situation)
        assert sit.available_capabilities == []
        assert sit.recent_context == {}

    def test_analyzer_empty(self):
        analyzer = SituationAnalyzer()
        sit = analyzer.analyze()
        assert sit is analyzer.last_situation
        assert sit.is_low_confidence()


# ── 2. 完整 context ──────────────────────────────────────────

class TestFullContext:
    """完整 context 应正确填充所有字段。"""

    def test_full_context_fields(self):
        context = {
            "user_prompt": "分析今日广州太古汇舆情趋势并生成日报",
            "current_page": "/dashboard",
            "module": "monitor",
            "task_phase": "executing",
            "system_metrics": {
                "db_status": "ok",
                "ai_status": "ok",
                "collection_status": "running",
            },
            "risk_state": {"level": "low", "active_alerts": 0},
            "available_capabilities": ["note_search", "event_query", "report_generate"],
            "history": [{"step": 1, "action": "search"}, {"step": 2, "action": "analyze"}],
        }
        sit = get_situation(context)
        assert sit.current_page == "/dashboard"
        assert sit.active_module == "monitor"
        assert sit.task_phase == PHASE_EXECUTING
        assert sit.system_status == SYS_HEALTHY
        assert sit.risk_level == RISK_LOW
        assert "note_search" in sit.available_capabilities
        assert sit.user_intent in (INTENT_ANALYZE, INTENT_REPORT)
        assert sit.confidence > 0.4
        assert sit.suggested_action == ACTION_CONTINUE

    def test_full_context_evidence(self):
        context = {
            "user_prompt": "监测实时舆情",
            "system_metrics": {"db_status": "ok", "ai_status": "ok", "collection_status": "ok"},
        }
        sit = get_situation(context)
        assert "rules_applied" in sit.evidence
        assert "system_status_evidence" in sit.evidence
        assert "intent_rule_baseline" in sit.evidence


# ── 3. 风险升级 ───────────────────────────────────────────────

class TestRiskEscalation:
    """风险状态应正确推断 risk_level 和 suggested_action。"""

    def test_explicit_high_risk(self):
        sit = get_situation({
            "user_prompt": "查看风险预警",
            "risk_state": {"level": "high"},
            "system_metrics": {"db_status": "ok", "ai_status": "ok", "collection_status": "ok"},
        })
        assert sit.risk_level == RISK_HIGH
        assert sit.is_risk_elevated()
        assert sit.suggested_action == ACTION_ESCALATE

    def test_critical_risk_from_alerts(self):
        sit = get_situation({
            "user_prompt": "查询事件",
            "risk_state": {"active_alerts": 6},
            "system_metrics": {"db_status": "ok", "ai_status": "ok", "collection_status": "ok"},
        })
        assert sit.risk_level == RISK_CRITICAL
        assert sit.suggested_action == ACTION_ESCALATE

    def test_medium_risk_from_alerts(self):
        sit = get_situation({
            "user_prompt": "查询",
            "risk_state": {"active_alerts": 2},
            "system_metrics": {"db_status": "ok", "ai_status": "ok", "collection_status": "ok"},
        })
        assert sit.risk_level == RISK_MEDIUM

    def test_system_unavailable_elevates_risk(self):
        sit = get_situation({
            "user_prompt": "查询数据",
            "system_metrics": {"db_status": "unavailable", "ai_status": "ok", "collection_status": "ok"},
        })
        assert sit.system_status == SYS_UNAVAILABLE
        assert sit.risk_level == RISK_HIGH
        assert sit.suggested_action == ACTION_PAUSE


# ── 4. 模块切换 ───────────────────────────────────────────────

class TestModuleSwitching:
    """页面变化应触发模块推断变化。"""

    def test_page_to_module_mapping(self):
        cases = [
            ("/dashboard", "monitor"),
            ("/risk", "risk"),
            ("/events", "events"),
            ("/collection", "collection"),
            ("/report", "report"),
            ("/analytics", "analytics"),
            ("/brand", "brand"),
            ("/settings", "settings"),
        ]
        for page, expected_module in cases:
            sit = get_situation({"current_page": page, "user_prompt": "test"})
            assert sit.active_module == expected_module, f"page={page} expected={expected_module} got={sit.active_module}"

    def test_explicit_module_overrides_page(self):
        sit = get_situation({
            "current_page": "/dashboard",
            "module": "risk",
            "user_prompt": "test",
        })
        assert sit.active_module == "risk"

    def test_unknown_page_no_module(self):
        sit = get_situation({"current_page": "/unknown/page", "user_prompt": "test"})
        assert sit.active_module == ""


# ── 5. 意图推断 ───────────────────────────────────────────────

class TestIntentInference:
    """用户 prompt 应正确推断意图。"""

    def test_intent_analyze(self):
        sit = get_situation({"user_prompt": "分析今日舆情趋势和归因"})
        assert sit.user_intent == INTENT_ANALYZE

    def test_intent_report(self):
        sit = get_situation({"user_prompt": "生成日报和周报"})
        assert sit.user_intent == INTENT_REPORT

    def test_intent_monitor(self):
        sit = get_situation({"user_prompt": "实时监测广州太古汇舆情"})
        assert sit.user_intent == INTENT_MONITOR

    def test_intent_troubleshoot(self):
        sit = get_situation({"user_prompt": "采集异常报错了，帮我修复恢复"})
        assert sit.user_intent == INTENT_TROUBLESHOOT

    def test_intent_from_situation_function(self):
        sit = Situation(user_intent=INTENT_ANALYZE, recent_context={"user_prompt": "分析"})
        assert intent_from_situation(sit) == INTENT_ANALYZE

    def test_intent_unknown_when_no_prompt(self):
        sit = get_situation({})
        assert sit.user_intent == INTENT_UNKNOWN


# ── 6. 低置信度 ───────────────────────────────────────────────

class TestLowConfidence:
    """信息不足时应标记低置信度。"""

    def test_no_prompt_low_confidence(self):
        sit = get_situation({"current_page": "/dashboard"})
        assert sit.is_low_confidence()

    def test_unknown_system_reduces_confidence(self):
        sit_with_sys = get_situation({
            "user_prompt": "分析趋势",
            "system_metrics": {"db_status": "ok", "ai_status": "ok", "collection_status": "ok"},
        })
        sit_no_sys = get_situation({"user_prompt": "分析趋势"})
        assert sit_no_sys.confidence < sit_with_sys.confidence

    def test_low_confidence_during_execution_triggers_replan(self):
        analyzer = SituationAnalyzer(min_confidence=0.9)  # 高阈值，强制低置信
        sit = analyzer.analyze({
            "user_prompt": "分析",
            "task_phase": "executing",
            "system_metrics": {"db_status": "ok", "ai_status": "ok", "collection_status": "ok"},
        })
        assert sit.suggested_action == ACTION_REPLAN


# ── 7. 系统异常 ───────────────────────────────────────────────

class TestSystemAnomaly:
    """系统异常状态应正确推断。"""

    def test_db_unavailable(self):
        sit = get_situation({
            "user_prompt": "查询",
            "system_metrics": {"db_status": "unavailable", "ai_status": "ok", "collection_status": "ok"},
        })
        assert sit.system_status == SYS_UNAVAILABLE
        assert not sit.is_system_healthy()

    def test_ai_degraded(self):
        sit = get_situation({
            "user_prompt": "查询",
            "system_metrics": {"db_status": "ok", "ai_status": "degraded", "collection_status": "ok"},
        })
        assert sit.system_status == SYS_DEGRADED

    def test_all_healthy(self):
        sit = get_situation({
            "user_prompt": "查询",
            "system_metrics": {"db_status": "ok", "ai_status": "ok", "collection_status": "running"},
        })
        assert sit.system_status == SYS_HEALTHY
        assert sit.is_system_healthy()

    def test_no_metrics_unknown(self):
        sit = get_situation({"user_prompt": "查询"})
        assert sit.system_status == SYS_UNKNOWN


# ── 8. 页面跳转 ───────────────────────────────────────────────

class TestPageNavigation:
    """页面跳转应反映在 Situation 中。"""

    def test_consecutive_page_changes(self):
        analyzer = SituationAnalyzer()
        sit1 = analyzer.analyze({"current_page": "/dashboard", "user_prompt": "监测"})
        assert sit1.active_module == "monitor"

        sit2 = analyzer.analyze({"current_page": "/events", "user_prompt": "查看事件"})
        assert sit2.active_module == "events"
        assert sit2.current_page == "/events"

    def test_page_with_chinese_path(self):
        sit = get_situation({"current_page": "/舆情监测", "user_prompt": "test"})
        assert sit.active_module == "monitor"

    def test_page_navigation_preserves_intent(self):
        sit = get_situation({
            "current_page": "/report",
            "user_prompt": "生成日报",
        })
        assert sit.active_module == "report"
        assert sit.user_intent == INTENT_REPORT


# ── 9. Adapters 集成测试 ──────────────────────────────────────

class TestAdapters:
    """from_agent_loop / from_observation / merge_contexts 集成。"""

    def test_from_agent_loop_basic(self):
        loop_state = {
            "agent_id": "agent_001",
            "state": "executing",
            "goal": "分析舆情",
            "current_step": 3,
            "total_steps": 5,
            "metrics": {"steps": 3, "duration_ms": 1500, "retries": 1, "replans": 0},
            "config": {"max_steps": 20, "max_time_seconds": 300},
        }
        ctx = from_agent_loop(loop_state)
        assert ctx["task_phase"] == "executing"
        assert ctx["agent_id"] == "agent_001"
        assert ctx["goal"] == "分析舆情"
        assert ctx["system_metrics"]["steps_executed"] == 3

    def test_from_agent_loop_failed_state(self):
        ctx = from_agent_loop({"state": "failed", "last_error": "timeout"})
        assert ctx["task_phase"] == "failed"
        assert "last_error" in ctx["recent_context"]

    def test_from_agent_loop_empty(self):
        ctx = from_agent_loop({})
        assert ctx["task_phase"] == "idle"

    def test_from_observation_dict(self):
        obs = {
            "observation_id": "obs_123",
            "step": 2,
            "db_status": "ok",
            "ai_status": "degraded",
            "collection_status": "running",
            "ai_provider": "zhipu",
            "previous_step_result": {"data": "test"},
            "previous_step_error": None,
            "environment_changed": True,
            "changed_fields": ["ai_status"],
        }
        ctx = from_observation(obs)
        assert ctx["system_metrics"]["db_status"] == "ok"
        assert ctx["system_metrics"]["ai_status"] == "degraded"
        assert ctx["recent_context"]["previous_step_result"] == {"data": "test"}
        assert ctx["evidence"]["source"] == "from_observation"

    def test_from_observation_with_object(self):
        """模拟 Observation 对象（有 to_dict 方法）。"""
        class FakeObs:
            def to_dict(self):
                return {"db_status": "unavailable", "ai_status": "ok", "collection_status": "ok"}
        ctx = from_observation(FakeObs())
        assert ctx["system_metrics"]["db_status"] == "unavailable"

    def test_from_observation_empty(self):
        ctx = from_observation(None)
        assert ctx["system_metrics"] == {}

    def test_merge_contexts(self):
        ctx1 = from_agent_loop({"state": "executing", "goal": "test"})
        ctx2 = from_observation({"db_status": "ok", "ai_status": "ok", "collection_status": "ok"})
        merged = merge_contexts(ctx1, ctx2)
        assert merged["task_phase"] == "executing"
        assert merged["system_metrics"]["db_status"] == "ok"
        assert "goal" in merged

    def test_merge_contexts_evidence_preserved(self):
        ctx1 = {"evidence": {"source": "loop"}}
        ctx2 = {"evidence": {"source": "obs"}}
        merged = merge_contexts(ctx1, ctx2)
        assert merged["evidence"]["source"] == "obs"  # 后者覆盖

    def test_full_pipeline_with_adapters(self):
        """端到端：adapters → get_situation。"""
        loop_ctx = from_agent_loop({
            "state": "executing",
            "goal": "分析今日舆情并生成日报",
            "metrics": {"steps": 2, "duration_ms": 1000},
        })
        obs_ctx = from_observation({
            "db_status": "ok",
            "ai_status": "ok",
            "collection_status": "running",
        })
        merged = merge_contexts(loop_ctx, obs_ctx)
        merged["current_page"] = "/dashboard"
        sit = get_situation(merged)
        assert sit.task_phase == "executing"
        assert sit.system_status == SYS_HEALTHY
        assert sit.user_intent in (INTENT_ANALYZE, INTENT_REPORT)


# ── 10. SituationAnalyzer AI 辅助 ─────────────────────────────

class TestSituationAnalyzerAIAssist:
    """AI 辅助函数注入测试。"""

    def test_ai_assist_overrides_intent(self):
        def ai_func(context, partial):
            return {"intent": "custom_intent", "confidence": 0.88}
        analyzer = SituationAnalyzer(ai_assist_func=ai_func)
        sit = analyzer.analyze({"user_prompt": "测试"})
        assert sit.user_intent == "custom_intent"
        assert sit.confidence == 0.88
        assert sit.evidence["ai_assisted"] is True

    def test_ai_assist_error_fallback(self):
        def ai_func(context, partial):
            raise RuntimeError("AI unavailable")
        analyzer = SituationAnalyzer(ai_assist_func=ai_func)
        sit = analyzer.analyze({"user_prompt": "分析趋势"})
        assert "ai_error" in sit.evidence
        assert sit.user_intent == INTENT_ANALYZE  # 规则兜底

    def test_analyzer_reset(self):
        analyzer = SituationAnalyzer()
        analyzer.analyze({"user_prompt": "test"})
        assert analyzer.last_situation is not None
        analyzer.reset()
        assert analyzer.last_situation is None


# ── 11. Situation 工具方法 ────────────────────────────────────

class TestSituationMethods:
    """Situation dataclass 方法测试。"""

    def test_to_dict(self):
        sit = Situation(current_page="/test", user_intent=INTENT_ANALYZE)
        d = sit.to_dict()
        assert d["current_page"] == "/test"
        assert d["user_intent"] == INTENT_ANALYZE
        assert "situation_id" in d

    def test_is_risk_elevated(self):
        assert Situation(risk_level=RISK_LOW).is_risk_elevated() is False
        assert Situation(risk_level=RISK_MEDIUM).is_risk_elevated() is True
        assert Situation(risk_level=RISK_HIGH).is_risk_elevated() is True
        assert Situation(risk_level=RISK_CRITICAL).is_risk_elevated() is True

    def test_is_system_healthy(self):
        assert Situation(system_status=SYS_HEALTHY).is_system_healthy() is True
        assert Situation(system_status=SYS_DEGRADED).is_system_healthy() is False

    def test_is_low_confidence(self):
        assert Situation(confidence=0.2).is_low_confidence() is True
        assert Situation(confidence=0.2).is_low_confidence(threshold=0.1) is False
        assert Situation(confidence=0.9).is_low_confidence() is False
