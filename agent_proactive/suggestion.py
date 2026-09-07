# -*- coding: utf-8 -*-
"""
Suggestion Generator — 建议生成与审批流程
==========================================
从 Signal 生成 SuggestedAction，并通过 ApprovalFlow 状态机管理审批。

硬约束：
  - action_type 默认 require_approval，不得默认 auto_execute
  - 每个 SuggestedAction 必须携带 rollback_plan（可撤销）
  - 所有建议可解释、可追踪
  - 不直接执行任何操作，仅生成建议与管理审批状态

模块清单：
  - SuggestedAction  : 建议动作数据结构
  - SuggestionGenerator : 从 Signal 生成建议
  - ApprovalFlow     : 审批流程状态机（PENDING/APPROVED/REJECTED/EXPIRED）
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .detector import Signal, SignalType, SignalSeverity


# ──────────────────────────────────────────────────────────────
# 枚举与数据结构
# ──────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    """建议动作类型。"""
    NOTIFY = "notify"                    # 仅通知，不执行
    AUTO_EXECUTE = "auto_execute"        # 自动执行（仅限低风险、可回滚操作）
    REQUIRE_APPROVAL = "require_approval"  # 需要人工审批（默认）


class ApprovalStatus(str, Enum):
    """审批状态。"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RiskLevel(str, Enum):
    """建议动作风险等级。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SuggestedAction:
    """建议动作。

    每个建议必须携带 rollback_plan，确保可撤销。
    action_type 默认 require_approval，不默认自动执行。
    """
    action_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:12]}")
    title: str = ""
    description: str = ""
    action_type: str = ActionType.REQUIRE_APPROVAL.value  # 默认需要审批
    estimated_impact: str = ""
    risk_level: str = RiskLevel.LOW.value
    rollback_plan: str = ""                                # 必须有回滚计划
    evidence_refs: List[str] = field(default_factory=list)
    signal_id: str = ""
    signal_type: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approval_status: str = ApprovalStatus.PENDING.value
    approved_by: str = ""
    approved_at: str = ""
    rejected_reason: str = ""
    expires_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_auto_executable(self) -> bool:
        """是否可自动执行（仅 auto_execute 且低风险）。"""
        return (
            self.action_type == ActionType.AUTO_EXECUTE.value
            and self.risk_level == RiskLevel.LOW.value
            and self.approval_status == ApprovalStatus.APPROVED.value
        )


# ──────────────────────────────────────────────────────────────
# 建议模板（按 SignalType 映射）
# ──────────────────────────────────────────────────────────────

_SUGGESTION_TEMPLATES: Dict[str, Dict[str, str]] = {
    SignalType.ANOMALY.value: {
        "title": "排查系统指标异常",
        "description": "系统指标超出阈值，建议检查相关服务状态、日志与资源占用，"
                       "确认是否影响采集与分析主链路。",
        "estimated_impact": "排查期间可能短暂增加系统负载，不影响生产数据。",
        "risk_level": RiskLevel.LOW.value,
        "rollback_plan": "排查为只读操作，无需回滚；若触发了临时限流，取消限流即可恢复。",
    },
    SignalType.RISK_ESCALATION.value: {
        "title": "确认风险升级并启动响应",
        "description": "系统风险等级上升或告警激增，建议人工确认风险来源，"
                       "评估是否需要启动舆情响应或系统降级。",
        "estimated_impact": "确认操作不改变生产数据；若启动降级可能暂时关闭非核心功能。",
        "risk_level": RiskLevel.MEDIUM.value,
        "rollback_plan": "若启动了降级策略，在风险解除后恢复原配置即可。",
    },
    SignalType.TASK_BLOCKED.value: {
        "title": "介入处理阻塞任务",
        "description": "任务长时间无进展或重试过多，建议人工检查任务状态、"
                       "错误日志与依赖服务，决定是继续等待、重试还是取消。",
        "estimated_impact": "人工介入不影响其他任务；若取消任务，该任务进度将丢失。",
        "risk_level": RiskLevel.MEDIUM.value,
        "rollback_plan": "若误取消任务，可从最近 checkpoint 恢复（如有）；"
                         "否则需重新提交任务。",
    },
    SignalType.DATA_MISSING.value: {
        "title": "修复数据缺失与采集断流",
        "description": "检测到关键表缺失、字段空率过高或采集断流，"
                       "建议检查采集链路、Auth 状态与数据库完整性。",
        "estimated_impact": "修复操作可能触发补采，增加短期负载；不删除现有数据。",
        "risk_level": RiskLevel.MEDIUM.value,
        "rollback_plan": "补采数据可通过时间范围筛选删除；配置变更可还原为修复前快照。",
    },
    SignalType.TREND_CHANGE.value: {
        "title": "分析趋势变化原因",
        "description": "指标趋势发生显著变化，建议结合事件日历、营销活动与"
                       "外部因素分析变化原因，判断是否需要调整监测策略。",
        "estimated_impact": "分析为只读操作，不影响生产。",
        "risk_level": RiskLevel.LOW.value,
        "rollback_plan": "纯分析操作，无需回滚。",
    },
    SignalType.PERFORMANCE_DEGRADE.value: {
        "title": "排查性能退化",
        "description": "系统性能相对基线明显退化，建议检查慢查询、资源瓶颈、"
                       "第三方依赖延迟与缓存命中率。",
        "estimated_impact": "排查为只读操作；若调整缓存或连接池参数可能短暂影响响应。",
        "risk_level": RiskLevel.LOW.value,
        "rollback_plan": "参数调整可还原为退化前配置。",
    },
    SignalType.BETTER_PATH.value: {
        "title": "评估更优执行路径",
        "description": "系统检测到一条可能更优的执行路径，建议评估其可行性、"
                       "风险与收益后决定是否采纳。",
        "estimated_impact": "评估为只读操作；采纳后可能改变执行流程。",
        "risk_level": RiskLevel.LOW.value,
        "rollback_plan": "若采纳后效果不佳，可切换回原执行路径。",
    },
}


# ──────────────────────────────────────────────────────────────
# SuggestionGenerator
# ──────────────────────────────────────────────────────────────

class SuggestionGenerator:
    """从 Signal 生成 SuggestedAction。

    用法：
        gen = SuggestionGenerator()
        action = gen.generate_suggestion(signal)
        batch = gen.generate_batch([signal1, signal2])
    """

    def __init__(
        self,
        templates: Optional[Dict[str, Dict[str, str]]] = None,
        default_expiry_minutes: int = 60,
    ):
        """
        Args:
            templates: 自定义建议模板（按 signal_type 映射），None 则使用内置
            default_expiry_minutes: 建议默认过期时间（分钟）
        """
        self._templates = templates or _SUGGESTION_TEMPLATES
        self._default_expiry_minutes = default_expiry_minutes

    def generate_suggestion(
        self, signal: Signal, context: Optional[Dict[str, Any]] = None
    ) -> SuggestedAction:
        """从单个 Signal 生成建议动作。

        Args:
            signal: 检测到的信号
            context: 附加上下文（可选）

        Returns:
            SuggestedAction，action_type 默认 require_approval
        """
        template = self._templates.get(signal.signal_type, {
            "title": "处理系统信号",
            "description": f"检测到信号：{signal.title}，建议人工评估并处理。",
            "estimated_impact": "评估为只读操作。",
            "risk_level": RiskLevel.LOW.value,
            "rollback_plan": "纯评估操作，无需回滚。",
        })

        # 根据信号严重度调整风险等级
        risk_level = template.get("risk_level", RiskLevel.LOW.value)
        if signal.severity == SignalSeverity.CRITICAL.value:
            risk_level = RiskLevel.HIGH.value
        elif signal.severity == SignalSeverity.WARNING.value:
            if risk_level == RiskLevel.LOW.value:
                risk_level = RiskLevel.LOW.value  # 保持低风险
            else:
                risk_level = RiskLevel.MEDIUM.value

        # CRITICAL 信号的 action_type 必须为 require_approval
        action_type = ActionType.REQUIRE_APPROVAL.value
        if (
            signal.severity == SignalSeverity.INFO.value
            and risk_level == RiskLevel.LOW.value
        ):
            # INFO 且低风险可设为 notify，但仍不自动执行
            action_type = ActionType.NOTIFY.value

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=self._default_expiry_minutes)
        ).isoformat()

        return SuggestedAction(
            title=template.get("title", "处理系统信号"),
            description=template.get("description", ""),
            action_type=action_type,
            estimated_impact=template.get("estimated_impact", ""),
            risk_level=risk_level,
            rollback_plan=template.get("rollback_plan", "操作可撤销，还原为执行前状态。"),
            evidence_refs=list(signal.evidence_refs),
            signal_id=signal.signal_id,
            signal_type=signal.signal_type,
            expires_at=expires_at,
        )

    def generate_batch(
        self, signals: List[Signal], context: Optional[Dict[str, Any]] = None
    ) -> List[SuggestedAction]:
        """批量生成建议。

        Args:
            signals: 信号列表
            context: 附加上下文

        Returns:
            SuggestedAction 列表，与输入信号一一对应
        """
        return [self.generate_suggestion(sig, context) for sig in signals]


# ──────────────────────────────────────────────────────────────
# ApprovalFlow 审批流程状态机
# ──────────────────────────────────────────────────────────────

# 合法状态转换
_VALID_APPROVAL_TRANSITIONS: Dict[ApprovalStatus, set] = {
    ApprovalStatus.PENDING: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED},
    ApprovalStatus.APPROVED: set(),       # 终态
    ApprovalStatus.REJECTED: set(),       # 终态
    ApprovalStatus.EXPIRED: set(),        # 终态
}


class ApprovalFlow:
    """审批流程状态机。

    管理 SuggestedAction 的审批生命周期：PENDING → APPROVED / REJECTED / EXPIRED。
    所有转换可追踪、可审计。

    用法：
        flow = ApprovalFlow(action)
        flow.approve(approver="admin")
        flow.reject(reason="风险过高")
        flow.expire()
    """

    def __init__(self, action: SuggestedAction):
        """
        Args:
            action: 关联的 SuggestedAction
        """
        self._action = action
        self._status = ApprovalStatus(action.approval_status)
        self._history: List[Dict[str, Any]] = []

    @property
    def status(self) -> ApprovalStatus:
        return self._status

    @property
    def action(self) -> SuggestedAction:
        return self._action

    def can_transition_to(self, target: ApprovalStatus) -> bool:
        """检查是否可转换到目标状态。"""
        return target in _VALID_APPROVAL_TRANSITIONS.get(self._status, set())

    def approve(self, approver: str = "", note: str = "") -> ApprovalStatus:
        """批准建议。

        Args:
            approver: 审批人标识
            note: 审批备注

        Returns:
            转换后的状态

        Raises:
            ValueError: 非法状态转换
        """
        self._transition(ApprovalStatus.APPROVED)
        self._action.approval_status = ApprovalStatus.APPROVED.value
        self._action.approved_by = approver
        self._action.approved_at = datetime.now(timezone.utc).isoformat()
        self._record("approve", {"approver": approver, "note": note})
        return self._status

    def reject(self, reason: str = "", rejecter: str = "") -> ApprovalStatus:
        """拒绝建议。

        Args:
            reason: 拒绝原因
            rejecter: 拒绝人标识

        Returns:
            转换后的状态

        Raises:
            ValueError: 非法状态转换
        """
        self._transition(ApprovalStatus.REJECTED)
        self._action.approval_status = ApprovalStatus.REJECTED.value
        self._action.rejected_reason = reason
        self._record("reject", {"rejecter": rejecter, "reason": reason})
        return self._status

    def expire(self) -> ApprovalStatus:
        """标记建议过期。

        Returns:
            转换后的状态

        Raises:
            ValueError: 非法状态转换
        """
        self._transition(ApprovalStatus.EXPIRED)
        self._action.approval_status = ApprovalStatus.EXPIRED.value
        self._record("expire", {})
        return self._status

    def check_expiry(self) -> bool:
        """检查是否已过期，若过期则自动转换为 EXPIRED。

        Returns:
            True 表示已过期（本次调用触发了转换或已处于 EXPIRED）
        """
        if self._status != ApprovalStatus.PENDING:
            return self._status == ApprovalStatus.EXPIRED

        if not self._action.expires_at:
            return False

        try:
            expiry = datetime.fromisoformat(self._action.expires_at)
            if datetime.now(timezone.utc) >= expiry:
                self.expire()
                return True
        except (ValueError, TypeError):
            pass
        return False

    def history(self) -> List[Dict[str, Any]]:
        """获取审批历史记录。"""
        return list(self._history)

    def _transition(self, target: ApprovalStatus) -> None:
        """执行状态转换，非法则抛异常。"""
        if target not in _VALID_APPROVAL_TRANSITIONS.get(self._status, set()):
            raise ValueError(
                f"Illegal approval transition: {self._status.value} -> {target.value}"
            )
        self._status = target

    def _record(self, action_name: str, detail: Dict[str, Any]) -> None:
        """记录审批操作。"""
        self._history.append({
            "action": action_name,
            "from_status": self._status.value,
            "to_status": self._status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        })


# ──────────────────────────────────────────────────────────────
# 模块级便捷函数
# ──────────────────────────────────────────────────────────────

_default_generator: Optional[SuggestionGenerator] = None


def _get_default_generator() -> SuggestionGenerator:
    global _default_generator
    if _default_generator is None:
        _default_generator = SuggestionGenerator()
    return _default_generator


def generate_suggestion(signal: Signal) -> SuggestedAction:
    """模块级便捷函数：使用默认生成器从 Signal 创建建议。

    Args:
        signal: 检测到的信号

    Returns:
        SuggestedAction（默认 require_approval，携带 rollback_plan）
    """
    return _get_default_generator().generate_suggestion(signal)
