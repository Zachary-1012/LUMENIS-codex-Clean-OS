# -*- coding: utf-8 -*-
"""
Unit tests for agent_adaptive_ui.panel
覆盖：空 run_state、完整 run_state、风险升级时面板优先级、
证据面板生成、下一步动作生成、面板 JSON 序列化、路由蓝图存在、多面板排序
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_adaptive_ui.panel import (
    PanelType,
    AdaptivePanel,
    PanelComponent,
    AdaptivePanelGenerator,
    get_adaptive_panel,
)
from agent_adaptive_ui.routes import adaptive_ui_bp


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def generator():
    return AdaptivePanelGenerator(max_panels=10)


@pytest.fixture
def empty_run_state():
    return {}


@pytest.fixture
def full_run_state():
    return {
        "status": "running",
        "goal": "分析今日广州太古汇舆情趋势",
        "agent_id": "agent_test_001",
        "task_id": "task_test_001",
        "risk_level": "high",
        "current_step": 2,
        "error": "",
        "metrics": {
            "steps": 5,
            "completed_steps": 2,
            "failed_steps": 1,
            "duration_ms": 12500,
            "cost": 0.015,
            "replans": 1,
            "retries": 2,
        },
        "plan": {
            "total_steps": 5,
            "steps": [
                {"index": 0, "action": "采集小红书笔记", "status": "completed", "tool": "xhs_collector", "risk_level": "low"},
                {"index": 1, "action": "主体过滤", "status": "completed", "tool": "subject_filter", "risk_level": "low"},
                {"index": 2, "action": "风险评估", "status": "running", "tool": "risk_engine", "risk_level": "medium"},
                {"index": 3, "action": "事件聚合", "status": "pending", "tool": "event_aggregator", "risk_level": "low"},
                {"index": 4, "action": "生成日报", "status": "pending", "tool": "report_generator", "risk_level": "low"},
            ],
        },
        "evaluation": {
            "overall_score": 0.75,
            "grade": "B",
            "goal_completion": {"name": "goal_completion", "score": 0.8, "weight": 0.35, "reasoning": "部分达成"},
            "step_efficiency": {"name": "step_efficiency", "score": 0.7, "weight": 0.25, "reasoning": "有重规划"},
            "cost_efficiency": {"name": "cost_efficiency", "score": 0.9, "weight": 0.20, "reasoning": "成本低"},
            "safety_compliance": {"name": "safety_compliance", "score": 1.0, "weight": 0.20, "reasoning": "无拦截"},
            "recommendations": ["优化规划步骤分解", "检查工具稳定性"],
        },
        "evidence": [
            {"evidence_id": "ev_001", "evidence_type": "collection", "content": "采集到 150 条笔记", "authenticity_score": 0.95, "timestamp": "2026-09-07T10:00:00Z"},
            {"evidence_id": "ev_002", "evidence_type": "risk", "content": "发现 3 条高风险内容", "authenticity_score": 0.88, "timestamp": "2026-09-07T10:05:00Z"},
        ],
        "transitions": [
            {"from_state": "idle", "to_state": "planning", "reason": "start", "timestamp": "2026-09-07T10:00:00Z"},
            {"from_state": "planning", "to_state": "executing", "reason": "plan ready", "timestamp": "2026-09-07T10:01:00Z"},
        ],
    }


# ──────────────────────────────────────────────────────────────
# 1. 空 run_state 测试
# ──────────────────────────────────────────────────────────────

class TestEmptyRunState:
    def test_empty_state_generates_summary_only(self, generator, empty_run_state):
        """空 run_state 至少生成摘要面板。"""
        panels = generator.generate("run_empty", empty_run_state)
        assert len(panels) >= 1
        # 第一个应该是摘要
        assert panels[0].panel_type == PanelType.SUMMARY

    def test_empty_state_no_crash(self, generator):
        """空状态不抛异常。"""
        panels = generator.generate("run_empty2", None)
        assert isinstance(panels, list)
        assert all(isinstance(p, AdaptivePanel) for p in panels)


# ──────────────────────────────────────────────────────────────
# 2. 完整 run_state 测试
# ──────────────────────────────────────────────────────────────

class TestFullRunState:
    def test_full_state_generates_multiple_panels(self, generator, full_run_state):
        """完整状态生成多种面板。"""
        panels = generator.generate("run_full", full_run_state)
        panel_types = {p.panel_type for p in panels}
        assert PanelType.SUMMARY in panel_types
        assert PanelType.ACTION_PANEL in panel_types
        assert PanelType.DATA_CARD in panel_types

    def test_summary_panel_has_goal(self, generator, full_run_state):
        """摘要面板包含目标。"""
        panels = generator.generate("run_full", full_run_state)
        summary = next(p for p in panels if p.panel_type == PanelType.SUMMARY)
        goal_comp = next(c for c in summary.components if c.title == "目标")
        assert "广州太古汇" in goal_comp.data["content"]

    def test_metrics_in_summary(self, generator, full_run_state):
        """摘要面板包含指标。"""
        panels = generator.generate("run_full", full_run_state)
        summary = next(p for p in panels if p.panel_type == PanelType.SUMMARY)
        titles = {c.title for c in summary.components}
        assert "已完成步骤" in titles
        assert "耗时" in titles


# ──────────────────────────────────────────────────────────────
# 3. 风险升级时面板优先级测试
# ──────────────────────────────────────────────────────────────

class TestRiskPriority:
    def test_critical_risk_action_panel_top_priority(self, generator):
        """critical 风险时操作面板优先级最高。"""
        state = {"status": "failed", "risk_level": "critical", "error": "权限被拒绝"}
        panels = generator.generate("run_critical", state)
        action = next(p for p in panels if p.panel_type == PanelType.ACTION_PANEL)
        assert action.priority <= 5
        # 操作面板应该在最前面
        assert panels[0].panel_type in (PanelType.ACTION_PANEL, PanelType.DATA_CARD)

    def test_low_risk_lower_priority(self, generator):
        """low 风险时操作面板优先级较低。"""
        state = {"status": "running", "risk_level": "low"}
        panels = generator.generate("run_low", state)
        action = next(p for p in panels if p.panel_type == PanelType.ACTION_PANEL)
        assert action.priority >= 40

    def test_waiting_approval_high_priority(self, generator):
        """等待审批时优先级高。"""
        state = {"status": "waiting_approval", "risk_level": "medium"}
        panels = generator.generate("run_wait", state)
        action = next(p for p in panels if p.panel_type == PanelType.ACTION_PANEL)
        assert action.priority <= 5
        assert "批准" in action.components[0].actions[0]["label"]


# ──────────────────────────────────────────────────────────────
# 4. 证据面板生成测试
# ──────────────────────────────────────────────────────────────

class TestEvidenceView:
    def test_evidence_panel_generated(self, generator, full_run_state):
        """有证据时生成证据面板。"""
        panels = generator.generate("run_ev", full_run_state)
        evidence_panels = [p for p in panels if p.panel_type == PanelType.EVIDENCE_DRILLDOWN]
        assert len(evidence_panels) == 1
        ev = evidence_panels[0]
        assert len(ev.evidence_refs) == 2
        assert "ev_001" in ev.evidence_refs

    def test_no_evidence_no_panel(self, generator):
        """无证据时不生成证据面板。"""
        state = {"status": "running", "evidence": [], "evaluation": {}, "transitions": []}
        panels = generator.generate("run_no_ev", state)
        evidence_panels = [p for p in panels if p.panel_type == PanelType.EVIDENCE_DRILLDOWN]
        assert len(evidence_panels) == 0

    def test_evidence_panel_has_evaluation_table(self, generator, full_run_state):
        """证据面板包含评估维度表格。"""
        panels = generator.generate("run_ev2", full_run_state)
        ev = next(p for p in panels if p.panel_type == PanelType.EVIDENCE_DRILLDOWN)
        table_comp = next((c for c in ev.components if c.component_type == "table"), None)
        assert table_comp is not None
        assert len(table_comp.data["rows"]) == 4


# ──────────────────────────────────────────────────────────────
# 5. 下一步动作生成测试
# ──────────────────────────────────────────────────────────────

class TestNextSteps:
    def test_next_steps_from_plan(self, generator, full_run_state):
        """从 plan 中提取未完成步骤。"""
        panels = generator.generate("run_next", full_run_state)
        next_panel = next(p for p in panels if p.panel_type == PanelType.NEXT_STEPS)
        items = next_panel.components[0].data["items"]
        assert len(items) >= 2
        # 应该包含 running 和 pending 状态的步骤
        statuses = {item["status"] for item in items}
        assert "running" in statuses
        assert "pending" in statuses

    def test_next_steps_completed_with_recommendations(self, generator):
        """完成状态时使用评估建议。"""
        state = {
            "status": "completed",
            "evaluation": {
                "recommendations": ["建议优化采集频率", "建议增加主体词"],
            },
        }
        panels = generator.generate("run_done", state)
        next_panel = next(p for p in panels if p.panel_type == PanelType.NEXT_STEPS)
        items = next_panel.components[0].data["items"]
        assert len(items) == 2
        assert "采集频率" in items[0]["action"]

    def test_no_next_steps_for_unknown(self, generator):
        """未知状态且无 plan 时不生成下一步面板。"""
        state = {"status": "unknown"}
        panels = generator.generate("run_unknown", state)
        next_panels = [p for p in panels if p.panel_type == PanelType.NEXT_STEPS]
        assert len(next_panels) == 0


# ──────────────────────────────────────────────────────────────
# 6. 面板 JSON 序列化测试
# ──────────────────────────────────────────────────────────────

class TestJsonSerialization:
    def test_panel_to_dict_json_serializable(self, generator, full_run_state):
        """面板 to_dict 结果可 JSON 序列化。"""
        panels = generator.generate("run_json", full_run_state)
        for p in panels:
            d = p.to_dict()
            json_str = json.dumps(d, ensure_ascii=False, default=str)
            assert isinstance(json_str, str)
            # 反序列化回来
            restored = json.loads(json_str)
            assert restored["panel_id"] == p.panel_id

    def test_panel_type_in_dict_is_string(self, generator, full_run_state):
        """to_dict 中 panel_type 是字符串值。"""
        panels = generator.generate("run_json2", full_run_state)
        for p in panels:
            d = p.to_dict()
            assert isinstance(d["panel_type"], str)
            assert d["panel_type"] == p.panel_type.value

    def test_get_adaptive_panel_returns_json_compatible(self, full_run_state):
        """get_adaptive_panel 返回 JSON 兼容 dict。"""
        result = get_adaptive_panel("run_conv", full_run_state)
        json_str = json.dumps(result, ensure_ascii=False, default=str)
        restored = json.loads(json_str)
        assert restored["run_id"] == "run_conv"
        assert restored["count"] == len(restored["panels"])
        assert "generated_at" in restored


# ──────────────────────────────────────────────────────────────
# 7. 路由蓝图存在测试
# ──────────────────────────────────────────────────────────────

class TestBlueprint:
    def test_blueprint_exists(self):
        """蓝图对象存在且配置正确。"""
        assert adaptive_ui_bp is not None
        assert adaptive_ui_bp.name == "adaptive_ui"
        assert adaptive_ui_bp.url_prefix == "/api/agent"

    def test_blueprint_has_routes(self):
        """蓝图注册了预期的路由。"""
        # deferred_functions 是注册路由时延迟执行的函数列表
        assert hasattr(adaptive_ui_bp, "deferred_functions")
        assert len(adaptive_ui_bp.deferred_functions) >= 2

    def test_import_blueprint_from_package(self):
        """可从包顶层导入蓝图。"""
        from agent_adaptive_ui import adaptive_ui_bp as bp
        assert bp is not None
        assert bp.name == "adaptive_ui"


# ──────────────────────────────────────────────────────────────
# 8. 多面板排序测试
# ──────────────────────────────────────────────────────────────

class TestPanelSorting:
    def test_panels_sorted_by_priority(self, generator, full_run_state):
        """面板按 priority 升序排列。"""
        panels = generator.generate("run_sort", full_run_state)
        priorities = [p.priority for p in panels]
        assert priorities == sorted(priorities)

    def test_max_panels_limit(self):
        """max_panels 限制生效。"""
        gen = AdaptivePanelGenerator(max_panels=2)
        state = {
            "status": "failed",
            "risk_level": "critical",
            "metrics": {"failed_steps": 3, "replans": 2},
            "evidence": [{"id": "e1", "content": "test"}],
            "evaluation": {"overall_score": 0.5, "safety_compliance": {"score": 0.4}},
        }
        panels = gen.generate("run_limit", state)
        assert len(panels) <= 2

    def test_failed_step_card_high_priority(self, generator, full_run_state):
        """失败步骤卡片优先级较高。"""
        panels = generator.generate("run_fail_card", full_run_state)
        failed_cards = [
            p for p in panels
            if p.panel_type == PanelType.DATA_CARD and "失败" in p.title
        ]
        assert len(failed_cards) == 1
        assert failed_cards[0].priority <= 20
