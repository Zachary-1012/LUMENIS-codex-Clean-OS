# -*- coding: utf-8 -*-
"""
Adaptive Panel Generator — 自适应面板生成器
==========================================
根据 Agent Run 状态动态生成：
  - ACTION_PANEL    : 当前最需要的操作面板
  - DATA_CARD       : 关键数据卡片
  - EVIDENCE_DRILLDOWN : 证据下钻视图
  - NEXT_STEPS      : 下一步动作
  - SUMMARY         : 运行摘要

集成点（只读）：
  - agent_runtime.loop.AgentResult 结构
  - agent_runtime.evaluation.TrajectoryEvaluation
  - agent_runtime.durable_adapter.Checkpoint

不修改任何现有源码，仅读取其状态结构。
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────────────────────
# 枚举与数据类
# ──────────────────────────────────────────────────────────────

class PanelType(str, Enum):
    """面板类型枚举。"""
    ACTION_PANEL = "action_panel"
    DATA_CARD = "data_card"
    EVIDENCE_DRILLDOWN = "evidence_drilldown"
    NEXT_STEPS = "next_steps"
    SUMMARY = "summary"


@dataclass
class PanelComponent:
    """面板内组件。"""
    component_type: str               # metric / list / chart / button / text / table
    title: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdaptivePanel:
    """自适应面板。"""
    panel_id: str
    panel_type: PanelType
    title: str
    components: List[PanelComponent] = field(default_factory=list)
    priority: int = 100               # 数值越小优先级越高
    source_run_id: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["panel_type"] = self.panel_type.value
        d["components"] = [c.to_dict() for c in self.components]
        return d


# ──────────────────────────────────────────────────────────────
# 面板生成器
# ──────────────────────────────────────────────────────────────

class AdaptivePanelGenerator:
    """根据 Agent Run 状态生成自适应面板。

    用法：
        generator = AdaptivePanelGenerator()
        panels = generator.generate(run_id="run_001", run_state={...})
        for p in panels:
            print(p.title, p.priority)
    """

    # 风险状态到优先级的映射（数值越小越优先）
    RISK_PRIORITY_MAP = {
        "critical": 1,
        "high": 5,
        "medium": 20,
        "low": 50,
        "info": 80,
    }

    def __init__(self, max_panels: int = 8):
        """
        Args:
            max_panels: 单次生成最多返回的面板数量
        """
        self.max_panels = max_panels
        self._cache: Dict[str, List[AdaptivePanel]] = {}

    def generate(
        self,
        run_id: str,
        run_state: Optional[Dict[str, Any]] = None,
    ) -> List[AdaptivePanel]:
        """主方法：根据 run 状态生成面板列表（按优先级排序）。

        Args:
            run_id: Agent Run 唯一标识
            run_state: Run 状态字典，可能包含：
                - status: running / completed / failed / cancelled / waiting_approval
                - goal: 目标描述
                - agent_id / task_id
                - metrics: {steps, completed_steps, failed_steps, duration_ms, cost, ...}
                - plan: {steps: [...], total_steps, ...}
                - evaluation: TrajectoryEvaluation 的 dict 形式
                - evidence: 证据列表
                - risk_level: critical / high / medium / low / info
                - current_step: 当前步骤索引
                - error: 错误信息
                - transitions: 状态转换历史

        Returns:
            按 priority 升序排列的 AdaptivePanel 列表
        """
        run_state = run_state or {}
        panels: List[AdaptivePanel] = []

        # 1. 摘要面板（始终生成）
        summary = self._build_summary(run_id, run_state)
        if summary:
            panels.append(summary)

        # 2. 数据卡片
        data_cards = self._build_data_cards(run_id, run_state)
        panels.extend(data_cards)

        # 3. 操作面板
        action_panel = self._build_action_panel(run_id, run_state)
        if action_panel:
            panels.append(action_panel)

        # 4. 证据视图
        evidence_view = self._build_evidence_view(run_id, run_state)
        if evidence_view:
            panels.append(evidence_view)

        # 5. 下一步动作
        next_steps = self._build_next_steps(run_id, run_state)
        if next_steps:
            panels.append(next_steps)

        # 按优先级排序，限制数量
        panels.sort(key=lambda p: p.priority)
        panels = panels[: self.max_panels]

        # 缓存
        self._cache[run_id] = panels
        return panels

    # ──────────────────────────────────────────────────────────
    # 各面板构建方法
    # ──────────────────────────────────────────────────────────

    def _build_summary(
        self, run_id: str, run_state: Dict[str, Any]
    ) -> Optional[AdaptivePanel]:
        """构建运行摘要面板。"""
        status = run_state.get("status", "unknown")
        goal = run_state.get("goal", "")
        metrics = run_state.get("metrics", {}) or {}

        components = [
            PanelComponent(
                component_type="text",
                title="目标",
                data={"content": goal or "（未设置目标）"},
            ),
            PanelComponent(
                component_type="metric",
                title="运行状态",
                data={"value": status, "unit": ""},
                config={"status_color": self._status_color(status)},
            ),
        ]

        if metrics:
            components.append(PanelComponent(
                component_type="metric",
                title="已完成步骤",
                data={
                    "value": metrics.get("completed_steps", 0),
                    "unit": f"/ {metrics.get('steps', metrics.get('total_steps', '?'))}",
                },
            ))
            if "duration_ms" in metrics:
                components.append(PanelComponent(
                    component_type="metric",
                    title="耗时",
                    data={
                        "value": round(metrics["duration_ms"] / 1000, 1),
                        "unit": "s",
                    },
                ))
            if "cost" in metrics:
                components.append(PanelComponent(
                    component_type="metric",
                    title="估算成本",
                    data={"value": metrics["cost"], "unit": "USD"},
                ))

        return AdaptivePanel(
            panel_id=f"panel_summary_{uuid.uuid4().hex[:8]}",
            panel_type=PanelType.SUMMARY,
            title="运行摘要",
            components=components,
            priority=90,
            source_run_id=run_id,
            evidence_refs=[],
        )

    def _build_data_cards(
        self, run_id: str, run_state: Dict[str, Any]
    ) -> List[AdaptivePanel]:
        """构建关键数据卡片（每个关键指标一个卡片）。"""
        cards: List[AdaptivePanel] = []
        metrics = run_state.get("metrics", {}) or {}
        evaluation = run_state.get("evaluation", {}) or {}

        # 失败步骤卡片
        failed = metrics.get("failed_steps", 0)
        if failed and failed > 0:
            cards.append(AdaptivePanel(
                panel_id=f"panel_card_failed_{uuid.uuid4().hex[:8]}",
                panel_type=PanelType.DATA_CARD,
                title="失败步骤",
                components=[PanelComponent(
                    component_type="metric",
                    title="失败步骤数",
                    data={"value": failed, "unit": "步"},
                    config={"alert": True, "severity": "warning"},
                )],
                priority=15,
                source_run_id=run_id,
            ))

        # 重规划卡片
        replans = metrics.get("replans", 0)
        if replans and replans > 0:
            cards.append(AdaptivePanel(
                panel_id=f"panel_card_replan_{uuid.uuid4().hex[:8]}",
                panel_type=PanelType.DATA_CARD,
                title="重规划次数",
                components=[PanelComponent(
                    component_type="metric",
                    title="重规划",
                    data={"value": replans, "unit": "次"},
                    config={"alert": replans > 1, "severity": "info"},
                )],
                priority=30,
                source_run_id=run_id,
            ))

        # 评估综合分卡片
        if evaluation and "overall_score" in evaluation:
            grade = evaluation.get("grade", "F")
            cards.append(AdaptivePanel(
                panel_id=f"panel_card_eval_{uuid.uuid4().hex[:8]}",
                panel_type=PanelType.DATA_CARD,
                title="轨迹评估",
                components=[
                    PanelComponent(
                        component_type="metric",
                        title="综合评分",
                        data={"value": evaluation["overall_score"], "unit": ""},
                        config={"grade": grade},
                    ),
                    PanelComponent(
                        component_type="text",
                        title="等级",
                        data={"content": grade},
                    ),
                ],
                priority=40,
                source_run_id=run_id,
            ))

        # 安全合规卡片
        if evaluation and "safety_compliance" in evaluation:
            sc = evaluation["safety_compliance"]
            if isinstance(sc, dict):
                score = sc.get("score", 1.0)
                cards.append(AdaptivePanel(
                    panel_id=f"panel_card_safety_{uuid.uuid4().hex[:8]}",
                    panel_type=PanelType.DATA_CARD,
                    title="安全合规",
                    components=[PanelComponent(
                        component_type="metric",
                        title="合规评分",
                        data={"value": score, "unit": ""},
                        config={"alert": score < 0.7, "severity": "critical" if score < 0.5 else "warning"},
                    )],
                    priority=10 if score < 0.7 else 60,
                    source_run_id=run_id,
                ))

        return cards

    def _build_action_panel(
        self, run_id: str, run_state: Dict[str, Any]
    ) -> Optional[AdaptivePanel]:
        """根据当前状态构建操作面板。"""
        status = run_state.get("status", "unknown")
        risk_level = run_state.get("risk_level", "info")
        error = run_state.get("error", "")

        actions: List[Dict[str, Any]] = []
        title = "操作面板"
        priority = self.RISK_PRIORITY_MAP.get(risk_level, 50)

        if status == "waiting_approval":
            title = "等待人工审批"
            priority = 2
            actions = [
                {"action": "approve", "label": "批准执行", "style": "primary"},
                {"action": "reject", "label": "拒绝", "style": "danger"},
                {"action": "modify", "label": "修改后执行", "style": "secondary"},
            ]
        elif status == "failed":
            title = "执行失败"
            priority = 3
            actions = [
                {"action": "retry", "label": "重试当前步骤", "style": "primary"},
                {"action": "replan", "label": "重新规划", "style": "secondary"},
                {"action": "view_log", "label": "查看错误日志", "style": "text"},
            ]
        elif status == "running":
            title = "运行中"
            actions = [
                {"action": "pause", "label": "暂停", "style": "secondary"},
                {"action": "cancel", "label": "取消任务", "style": "danger"},
                {"action": "view_trace", "label": "查看执行轨迹", "style": "text"},
            ]
        elif status == "completed":
            title = "执行完成"
            actions = [
                {"action": "view_result", "label": "查看结果", "style": "primary"},
                {"action": "export_report", "label": "导出报告", "style": "secondary"},
                {"action": "run_again", "label": "重新运行", "style": "text"},
            ]
        elif status == "cancelled":
            title = "已取消"
            actions = [
                {"action": "run_again", "label": "重新运行", "style": "primary"},
            ]
        else:
            return None

        components = [PanelComponent(
            component_type="button",
            title=title,
            data={"status": status, "error": error},
            actions=actions,
            config={"risk_level": risk_level},
        )]

        if error:
            components.append(PanelComponent(
                component_type="text",
                title="错误信息",
                data={"content": error[:500]},
                config={"severity": "error"},
            ))

        return AdaptivePanel(
            panel_id=f"panel_action_{uuid.uuid4().hex[:8]}",
            panel_type=PanelType.ACTION_PANEL,
            title=title,
            components=components,
            priority=priority,
            source_run_id=run_id,
            evidence_refs=[],
        )

    def _build_evidence_view(
        self, run_id: str, run_state: Dict[str, Any]
    ) -> Optional[AdaptivePanel]:
        """构建证据下钻视图。"""
        evidence = run_state.get("evidence", []) or []
        evaluation = run_state.get("evaluation", {}) or {}
        transitions = run_state.get("transitions", []) or []

        if not evidence and not evaluation and not transitions:
            return None

        components: List[PanelComponent] = []
        evidence_refs: List[str] = []

        # 证据列表
        if evidence:
            ev_items = []
            for idx, ev in enumerate(evidence[:20]):
                if isinstance(ev, dict):
                    ev_id = ev.get("evidence_id", ev.get("id", f"ev_{idx}"))
                    evidence_refs.append(str(ev_id))
                    ev_items.append({
                        "id": ev_id,
                        "type": ev.get("evidence_type", ev.get("type", "unknown")),
                        "content": str(ev.get("content", ev.get("summary", "")))[:200],
                        "score": ev.get("authenticity_score", ev.get("score", "")),
                        "timestamp": ev.get("timestamp", ev.get("created_at", "")),
                    })
                else:
                    ev_items.append({"id": f"ev_{idx}", "content": str(ev)[:200]})
            components.append(PanelComponent(
                component_type="list",
                title=f"证据链（{len(evidence)} 条）",
                data={"items": ev_items, "total": len(evidence)},
                config={"collapsible": True, "default_expanded": False},
            ))

        # 评估维度详情
        if evaluation:
            dims = []
            for dim_name in ("goal_completion", "step_efficiency", "cost_efficiency", "safety_compliance"):
                dim = evaluation.get(dim_name)
                if isinstance(dim, dict):
                    dims.append({
                        "name": dim_name,
                        "score": dim.get("score", 0),
                        "weight": dim.get("weight", 0),
                        "reasoning": dim.get("reasoning", ""),
                    })
            if dims:
                components.append(PanelComponent(
                    component_type="table",
                    title="评估维度详情",
                    data={"rows": dims, "columns": ["name", "score", "weight", "reasoning"]},
                ))

        # 状态转换历史
        if transitions:
            trans_items = []
            for t in transitions[-10:]:
                if isinstance(t, dict):
                    trans_items.append({
                        "from": t.get("from_state", t.get("from", "")),
                        "to": t.get("to_state", t.get("to", "")),
                        "reason": t.get("reason", ""),
                        "timestamp": t.get("timestamp", ""),
                    })
            if trans_items:
                components.append(PanelComponent(
                    component_type="list",
                    title="状态转换（最近 10 条）",
                    data={"items": trans_items},
                    config={"collapsible": True},
                ))

        if not components:
            return None

        return AdaptivePanel(
            panel_id=f"panel_evidence_{uuid.uuid4().hex[:8]}",
            panel_type=PanelType.EVIDENCE_DRILLDOWN,
            title="证据与轨迹下钻",
            components=components,
            priority=35,
            source_run_id=run_id,
            evidence_refs=evidence_refs,
        )

    def _build_next_steps(
        self, run_id: str, run_state: Dict[str, Any]
    ) -> Optional[AdaptivePanel]:
        """构建下一步动作面板。"""
        status = run_state.get("status", "unknown")
        plan = run_state.get("plan", {}) or {}
        metrics = run_state.get("metrics", {}) or {}
        evaluation = run_state.get("evaluation", {}) or {}
        current_step = run_state.get("current_step", metrics.get("completed_steps", 0))

        steps: List[Dict[str, Any]] = []

        # 从 plan 中提取未完成步骤
        plan_steps = plan.get("steps", []) if isinstance(plan, dict) else []
        if plan_steps:
            for idx, ps in enumerate(plan_steps):
                if isinstance(ps, dict):
                    ps_status = ps.get("status", "pending")
                    if ps_status in ("pending", "running", "failed"):
                        steps.append({
                            "step_index": ps.get("index", idx),
                            "action": ps.get("action", ps.get("description", "")),
                            "status": ps_status,
                            "tool": ps.get("tool", ""),
                            "risk_level": ps.get("risk_level", "low"),
                        })
                        if len(steps) >= 5:
                            break

        # 如果没有 plan steps，根据状态生成建议
        if not steps:
            if status == "failed":
                steps = [
                    {"step_index": 0, "action": "分析失败原因", "status": "pending", "priority": 1},
                    {"step_index": 1, "action": "修复后重试", "status": "pending", "priority": 2},
                ]
            elif status == "completed":
                recs = evaluation.get("recommendations", []) if isinstance(evaluation, dict) else []
                for idx, rec in enumerate(recs[:5]):
                    steps.append({
                        "step_index": idx,
                        "action": rec if isinstance(rec, str) else str(rec),
                        "status": "suggested",
                        "priority": idx + 1,
                    })
            elif status == "running":
                steps = [
                    {"step_index": current_step, "action": "继续执行当前步骤", "status": "running", "priority": 1},
                ]

        if not steps:
            return None

        components = [PanelComponent(
            component_type="list",
            title="下一步动作",
            data={"items": steps, "current_step": current_step},
            actions=[
                {"action": "execute_next", "label": "执行下一步", "style": "primary"},
                {"action": "skip", "label": "跳过", "style": "secondary"},
            ],
            config={"interactive": True},
        )]

        return AdaptivePanel(
            panel_id=f"panel_next_{uuid.uuid4().hex[:8]}",
            panel_type=PanelType.NEXT_STEPS,
            title="下一步动作",
            components=components,
            priority=25,
            source_run_id=run_id,
            evidence_refs=[],
        )

    # ──────────────────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _status_color(status: str) -> str:
        """状态对应的颜色标识。"""
        color_map = {
            "running": "blue",
            "completed": "green",
            "failed": "red",
            "cancelled": "gray",
            "waiting_approval": "orange",
            "planning": "purple",
            "executing": "blue",
            "observing": "cyan",
            "replanning": "orange",
        }
        return color_map.get(status, "gray")

    def get_cached(self, run_id: str) -> Optional[List[AdaptivePanel]]:
        """获取缓存的面板（不重新生成）。"""
        return self._cache.get(run_id)

    def invalidate_cache(self, run_id: Optional[str] = None) -> None:
        """清除缓存。"""
        if run_id:
            self._cache.pop(run_id, None)
        else:
            self._cache.clear()


# ──────────────────────────────────────────────────────────────
# 便捷函数（供 Flask 路由调用）
# ──────────────────────────────────────────────────────────────

# 全局生成器单例
_default_generator: Optional[AdaptivePanelGenerator] = None


def _get_generator() -> AdaptivePanelGenerator:
    """获取全局生成器单例。"""
    global _default_generator
    if _default_generator is None:
        _default_generator = AdaptivePanelGenerator()
    return _default_generator


def get_adaptive_panel(run_id: str, run_state: Optional[Dict[str, Any]] = None) -> dict:
    """供 Flask 路由调用的便捷函数，返回 JSON 兼容 dict。

    Args:
        run_id: Agent Run ID
        run_state: Run 状态（None 则尝试从缓存或空状态生成）

    Returns:
        {
            "run_id": str,
            "generated_at": str,
            "panels": [panel_dict, ...],
            "count": int,
        }
    """
    generator = _get_generator()

    # 如果未提供 run_state，尝试从缓存获取
    if run_state is None:
        cached = generator.get_cached(run_id)
        if cached is not None:
            return {
                "run_id": run_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "panels": [p.to_dict() for p in cached],
                "count": len(cached),
                "cached": True,
            }
        run_state = {}

    panels = generator.generate(run_id, run_state)
    return {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "panels": [p.to_dict() for p in panels],
        "count": len(panels),
        "cached": False,
    }
