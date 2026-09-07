# -*- coding: utf-8 -*-
"""
Situational Awareness — 情境感知核心模块
==========================================
Context → Situation → Intent → Action 推理链。

Agent 不只读取用户 Prompt，还实时理解：
  - 当前页面 / 活跃模块
  - 任务阶段
  - 系统状态（DB / AI / 采集 / 工具）
  - 风险等级
  - 可用能力
  - 历史上下文
  - 用户意图
  - 建议动作

设计原则：
  - 规则驱动为默认，AI 辅助为可插拔可选（不依赖外部 API）
  - 所有推断可解释、可追溯（evidence 字段）
  - 低置信度时显式标记，不伪装高置信
  - 只读感知，不修改任何系统状态
  - 与 agent_runtime.observation / loop / planner 兼容（import 或 dict 兼容）

与现有基础层对齐：
  - agent_runtime.observation.Observation : 系统状态来源
  - agent_runtime.loop.AgentLoop / AgentConfig / AgentResult : 任务阶段来源
  - agent_runtime.planner.RiskLevel : 风险等级枚举（LOW/MEDIUM/HIGH/CRITICAL）
  - agent_runtime.state_machine.AgentState : Agent 运行状态
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────
# 风险等级：优先复用 agent_runtime.planner.RiskLevel，
# 不可用时降级为本地字符串常量（dict 兼容模式）
# ─────────────────────────────────────────────────────────────
try:
    from agent_runtime.planner import RiskLevel as _RuntimeRiskLevel
    RISK_LOW = _RuntimeRiskLevel.LOW.value
    RISK_MEDIUM = _RuntimeRiskLevel.MEDIUM.value
    RISK_HIGH = _RuntimeRiskLevel.HIGH.value
    RISK_CRITICAL = _RuntimeRiskLevel.CRITICAL.value
except Exception:
    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"
    RISK_CRITICAL = "critical"

RISK_ORDER = {RISK_LOW: 0, RISK_MEDIUM: 1, RISK_HIGH: 2, RISK_CRITICAL: 3}

# 系统状态常量
SYS_HEALTHY = "healthy"
SYS_DEGRADED = "degraded"
SYS_UNAVAILABLE = "unavailable"
SYS_UNKNOWN = "unknown"

# 任务阶段常量
PHASE_IDLE = "idle"
PHASE_PLANNING = "planning"
PHASE_EXECUTING = "executing"
PHASE_OBSERVING = "observing"
PHASE_REPLANNING = "replanning"
PHASE_WAITING_APPROVAL = "waiting_approval"
PHASE_COMPLETED = "completed"
PHASE_FAILED = "failed"

# 意图常量
INTENT_MONITOR = "monitor"
INTENT_ANALYZE = "analyze"
INTENT_REPORT = "report"
INTENT_COLLECT = "collect"
INTENT_CONFIGURE = "configure"
INTENT_TROUBLESHOOT = "troubleshoot"
INTENT_QUERY = "query"
INTENT_UNKNOWN = "unknown"

# 建议动作常量
ACTION_CONTINUE = "continue"
ACTION_PAUSE = "pause"
ACTION_REPLAN = "replan"
ACTION_ESCALATE = "escalate"
ACTION_NOTIFY = "notify"
ACTION_SWITCH_MODULE = "switch_module"
ACTION_SEEK_APPROVAL = "seek_approval"
ACTION_NOOP = "noop"


@dataclass
class Situation:
    """结构化情境对象 — Context→Situation 推理产物。

    字段说明：
      current_page         : 当前页面标识（如 /dashboard, /events, /reports）
      active_module        : 活跃业务模块（如 monitor, risk, events, collection, report）
      task_phase           : 任务阶段（idle/planning/executing/observing/replanning/...）
      system_status        : 系统整体状态（healthy/degraded/unavailable/unknown）
      risk_level           : 当前风险等级（low/medium/high/critical）
      available_capabilities: 当前可用能力列表（tool_id 或 capability 名称）
      recent_context       : 最近上下文摘要（历史交互、前一步结果等）
      user_intent          : 推断的用户意图
      suggested_action     : 建议的下一步动作
      confidence           : 推断置信度 (0.0 ~ 1.0)
      timestamp            : 情境生成时间（ISO 8601 UTC）
      situation_id         : 情境唯一标识
      evidence             : 推断证据链（可解释、可追溯）
    """
    current_page: str = ""
    active_module: str = ""
    task_phase: str = PHASE_IDLE
    system_status: str = SYS_UNKNOWN
    risk_level: str = RISK_LOW
    available_capabilities: List[str] = field(default_factory=list)
    recent_context: Dict[str, Any] = field(default_factory=dict)
    user_intent: str = INTENT_UNKNOWN
    suggested_action: str = ACTION_NOOP
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    situation_id: str = field(default_factory=lambda: f"sit_{uuid.uuid4().hex[:12]}")
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。"""
        return asdict(self)

    def is_risk_elevated(self) -> bool:
        """风险是否升级（≥ medium）。"""
        return RISK_ORDER.get(self.risk_level, 0) >= RISK_ORDER[RISK_MEDIUM]

    def is_system_healthy(self) -> bool:
        """系统是否健康。"""
        return self.system_status == SYS_HEALTHY

    def is_low_confidence(self, threshold: float = 0.4) -> bool:
        """是否低置信度。"""
        return self.confidence < threshold


# ─────────────────────────────────────────────────────────────
# 规则引擎：从 context 推断各维度
# ─────────────────────────────────────────────────────────────

# 页面 → 模块映射规则
_PAGE_MODULE_RULES: List[Tuple[str, str]] = [
    ("/dashboard", "monitor"),
    ("/monitor", "monitor"),
    ("/舆情监测", "monitor"),
    ("/risk", "risk"),
    ("/风险", "risk"),
    ("/events", "events"),
    ("/事件", "events"),
    ("/collection", "collection"),
    ("/采集", "collection"),
    ("/report", "report"),
    ("/报告", "report"),
    ("/analytics", "analytics"),
    ("/数据分析", "analytics"),
    ("/brand", "brand"),
    ("/品牌", "brand"),
    ("/settings", "settings"),
    ("/系统设置", "settings"),
    ("/notes", "notes"),
    ("/笔记", "notes"),
]

# 意图关键词规则
_INTENT_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    (INTENT_MONITOR, ["监测", "监控", "实时", "盯", "watch", "monitor"]),
    (INTENT_ANALYZE, ["分析", "趋势", "归因", "对比", "analyze", "trend", "insight"]),
    (INTENT_REPORT, ["报告", "日报", "周报", "月报", "生成报告", "report", "daily"]),
    (INTENT_COLLECT, ["采集", "抓取", "同步", "collect", "crawl", "sync"]),
    (INTENT_CONFIGURE, ["配置", "设置", "规则", "参数", "configure", "setting", "rule"]),
    (INTENT_TROUBLESHOOT, ["故障", "异常", "报错", "修复", "恢复", "troubleshoot", "error", "fix"]),
    (INTENT_QUERY, ["查询", "搜索", "查找", "详情", "query", "search", "find"]),
]


def _infer_module_from_page(page: str) -> str:
    """从页面路径推断活跃模块。"""
    if not page:
        return ""
    page_lower = page.lower()
    for pattern, module in _PAGE_MODULE_RULES:
        if pattern.lower() in page_lower:
            return module
    return ""


def _infer_intent_from_prompt(prompt: str) -> Tuple[str, float]:
    """从用户 prompt 推断意图，返回 (intent, confidence)。"""
    if not prompt:
        return INTENT_UNKNOWN, 0.0
    prompt_lower = prompt.lower()
    best_intent = INTENT_UNKNOWN
    best_hits = 0
    for intent, keywords in _INTENT_KEYWORD_RULES:
        hits = sum(1 for kw in keywords if kw.lower() in prompt_lower)
        if hits > best_hits:
            best_hits = hits
            best_intent = intent
    if best_hits == 0:
        return INTENT_UNKNOWN, 0.1
    confidence = min(0.95, 0.4 + best_hits * 0.2)
    return best_intent, confidence


def _infer_system_status(metrics: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """从系统指标推断整体状态，返回 (status, evidence)。"""
    evidence: Dict[str, Any] = {"checks": {}}
    if not metrics:
        return SYS_UNKNOWN, {"reason": "no metrics provided"}

    db_status = str(metrics.get("db_status", "")).lower()
    ai_status = str(metrics.get("ai_status", "")).lower()
    collection_status = str(metrics.get("collection_status", "")).lower()

    evidence["checks"]["db"] = db_status or "unknown"
    evidence["checks"]["ai"] = ai_status or "unknown"
    evidence["checks"]["collection"] = collection_status or "unknown"

    statuses = [s for s in (db_status, ai_status, collection_status) if s]
    if not statuses:
        return SYS_UNKNOWN, evidence

    if any(s in ("unavailable", "error", "down") for s in statuses):
        evidence["reason"] = "at least one subsystem unavailable"
        return SYS_UNAVAILABLE, evidence
    if any(s in ("degraded", "warning", "slow") for s in statuses):
        evidence["reason"] = "at least one subsystem degraded"
        return SYS_DEGRADED, evidence
    if all(s in ("ok", "healthy", "running", "up") for s in statuses):
        evidence["reason"] = "all subsystems healthy"
        return SYS_HEALTHY, evidence
    return SYS_UNKNOWN, evidence


def _infer_risk_level(risk_state: Dict[str, Any], system_status: str) -> Tuple[str, Dict[str, Any]]:
    """从风险状态和系统状态推断风险等级，返回 (risk_level, evidence)。"""
    evidence: Dict[str, Any] = {}
    if risk_state:
        explicit = str(risk_state.get("level", "")).lower()
        if explicit in RISK_ORDER:
            evidence["source"] = "explicit risk_state.level"
            return explicit, evidence
        active_alerts = risk_state.get("active_alerts", 0)
        if isinstance(active_alerts, int):
            evidence["active_alerts"] = active_alerts
            if active_alerts >= 5:
                return RISK_CRITICAL, evidence
            if active_alerts >= 3:
                return RISK_HIGH, evidence
            if active_alerts >= 1:
                return RISK_MEDIUM, evidence

    # 系统状态降级时风险至少 medium
    if system_status == SYS_UNAVAILABLE:
        evidence["source"] = "system unavailable → risk elevated"
        return RISK_HIGH, evidence
    if system_status == SYS_DEGRADED:
        evidence["source"] = "system degraded → risk elevated"
        return RISK_MEDIUM, evidence

    evidence["source"] = "no explicit risk, system healthy"
    return RISK_LOW, evidence


def _infer_suggested_action(
    task_phase: str,
    system_status: str,
    risk_level: str,
    confidence: float,
) -> Tuple[str, Dict[str, Any]]:
    """推断建议动作，返回 (action, evidence)。"""
    evidence: Dict[str, Any] = {}
    # 系统不可用 → 暂停
    if system_status == SYS_UNAVAILABLE:
        evidence["reason"] = "system unavailable"
        return ACTION_PAUSE, evidence
    # 高风险 → 升级/通知
    if risk_level in (RISK_HIGH, RISK_CRITICAL):
        evidence["reason"] = f"risk level={risk_level}"
        return ACTION_ESCALATE, evidence
    # 低置信度且在执行中 → 重规划
    if confidence < 0.4 and task_phase == PHASE_EXECUTING:
        evidence["reason"] = "low confidence during execution"
        return ACTION_REPLAN, evidence
    # 等待审批
    if task_phase == PHASE_WAITING_APPROVAL:
        evidence["reason"] = "waiting for approval"
        return ACTION_SEEK_APPROVAL, evidence
    # 正常继续
    if task_phase in (PHASE_PLANNING, PHASE_EXECUTING, PHASE_OBSERVING):
        evidence["reason"] = "normal progression"
        return ACTION_CONTINUE, evidence
    evidence["reason"] = "idle or terminal"
    return ACTION_NOOP, evidence


def _extract_capabilities(context: Dict[str, Any]) -> List[str]:
    """从 context 提取可用能力列表。"""
    caps = context.get("available_capabilities")
    if isinstance(caps, list):
        return [str(c) for c in caps if c]
    tool_status = context.get("tool_status", {})
    if isinstance(tool_status, dict):
        return [name for name, status in tool_status.items()
                if str(status).lower() in ("available", "ok", "up", "enabled")]
    return []


# ─────────────────────────────────────────────────────────────
# SituationAnalyzer — Context→Situation→Intent→Action 推理链
# ─────────────────────────────────────────────────────────────

class SituationAnalyzer:
    """情境分析器：封装 Context → Situation → Intent → Action 推理链。

    支持规则驱动（默认）+ 可插拔 AI 辅助。
    AI 辅助通过 ai_assist_func 注入，签名：
        ai_assist_func(context: dict, partial_situation: dict) -> dict
    返回的 dict 可覆盖 intent / suggested_action / confidence，
    但始终保留规则推断作为 evidence 中的 baseline。

    用法：
        analyzer = SituationAnalyzer()
        situation = analyzer.analyze(context)
        intent = analyzer.intent(situation)
    """

    def __init__(
        self,
        ai_assist_func: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = None,
        min_confidence: float = 0.3,
    ):
        """
        Args:
            ai_assist_func: 可选 AI 辅助函数（不依赖外部 API，由调用方注入）
            min_confidence: 最低置信度阈值，低于此值标记 low_confidence
        """
        self._ai_assist = ai_assist_func
        self._min_confidence = min_confidence
        self._last_situation: Optional[Situation] = None

    @property
    def last_situation(self) -> Optional[Situation]:
        """获取上一次分析的情境。"""
        return self._last_situation

    def analyze(self, context: Optional[Dict[str, Any]] = None) -> Situation:
        """执行完整推理链：Context → Situation → Intent → Action。

        Args:
            context: 上下文字典，可包含：
                - user_prompt: 用户输入
                - current_page: 当前页面
                - module: 活跃模块（显式指定则优先）
                - task_phase: 任务阶段
                - system_metrics: 系统指标 {db_status, ai_status, collection_status, ...}
                - risk_state: 风险状态 {level, active_alerts, ...}
                - history: 历史上下文
                - available_capabilities: 可用能力列表
                - tool_status: 工具状态 dict
                - observation: agent_runtime Observation 对象或 dict

        Returns:
            Situation 结构化情境对象
        """
        context = context or {}
        evidence: Dict[str, Any] = {"rules_applied": [], "ai_assisted": False}

        # 1. 页面 & 模块
        current_page = str(context.get("current_page", ""))
        explicit_module = str(context.get("module", "")).strip()
        if explicit_module:
            active_module = explicit_module
            evidence["rules_applied"].append("module from explicit context.module")
        else:
            active_module = _infer_module_from_page(current_page)
            if active_module:
                evidence["rules_applied"].append(f"module inferred from page: {current_page}")

        # 2. 任务阶段
        task_phase = str(context.get("task_phase", PHASE_IDLE)).lower()
        if task_phase not in (PHASE_IDLE, PHASE_PLANNING, PHASE_EXECUTING,
                               PHASE_OBSERVING, PHASE_REPLANNING, PHASE_WAITING_APPROVAL,
                               PHASE_COMPLETED, PHASE_FAILED):
            task_phase = PHASE_IDLE

        # 3. 系统状态
        system_metrics = context.get("system_metrics", {})
        if not isinstance(system_metrics, dict):
            system_metrics = {}
        # 兼容 observation 对象/dict
        obs = context.get("observation")
        if obs is not None:
            obs_dict = obs.to_dict() if hasattr(obs, "to_dict") else (
                obs if isinstance(obs, dict) else {}
            )
            for key in ("db_status", "ai_status", "collection_status"):
                if key not in system_metrics and key in obs_dict:
                    system_metrics[key] = obs_dict[key]
        system_status, sys_evidence = _infer_system_status(system_metrics)
        evidence["system_status_evidence"] = sys_evidence

        # 4. 风险等级
        risk_state = context.get("risk_state", {})
        if not isinstance(risk_state, dict):
            risk_state = {}
        risk_level, risk_evidence = _infer_risk_level(risk_state, system_status)
        evidence["risk_evidence"] = risk_evidence

        # 5. 可用能力
        available_capabilities = _extract_capabilities(context)

        # 6. 最近上下文
        recent_context: Dict[str, Any] = {}
        history = context.get("history")
        if isinstance(history, list) and history:
            recent_context["last_n"] = history[-3:]
        elif isinstance(history, dict):
            recent_context.update(history)
        user_prompt = str(context.get("user_prompt", ""))
        if user_prompt:
            recent_context["user_prompt"] = user_prompt[:500]

        # 7. 意图推断（规则）
        intent, intent_confidence = _infer_intent_from_prompt(user_prompt)
        evidence["intent_rule_baseline"] = {
            "intent": intent, "confidence": round(intent_confidence, 3),
        }

        # 8. 综合置信度
        confidence = intent_confidence
        if active_module:
            confidence = min(1.0, confidence + 0.1)
        if system_status == SYS_UNKNOWN:
            confidence = max(0.0, confidence - 0.15)
        confidence = round(min(1.0, max(0.0, confidence)), 3)

        # 9. 建议动作（规则）
        suggested_action, action_evidence = _infer_suggested_action(
            task_phase, system_status, risk_level, confidence
        )
        evidence["action_evidence"] = action_evidence

        # 10. AI 辅助（可选）
        if self._ai_assist is not None:
            try:
                partial = {
                    "current_page": current_page,
                    "active_module": active_module,
                    "task_phase": task_phase,
                    "system_status": system_status,
                    "risk_level": risk_level,
                    "intent_baseline": intent,
                    "confidence_baseline": confidence,
                }
                ai_out = self._ai_assist(context, partial)
                if isinstance(ai_out, dict):
                    if "intent" in ai_out and ai_out["intent"]:
                        evidence["ai_override"] = {"intent": ai_out["intent"]}
                        intent = str(ai_out["intent"])
                    if "suggested_action" in ai_out and ai_out["suggested_action"]:
                        suggested_action = str(ai_out["suggested_action"])
                    if "confidence" in ai_out and isinstance(ai_out["confidence"], (int, float)):
                        confidence = round(float(ai_out["confidence"]), 3)
                    evidence["ai_assisted"] = True
            except Exception as e:
                evidence["ai_error"] = str(e)[:200]

        # 低置信度标记
        if confidence < self._min_confidence:
            evidence["low_confidence"] = True
            suggested_action = ACTION_REPLAN if task_phase == PHASE_EXECUTING else suggested_action

        situation = Situation(
            current_page=current_page,
            active_module=active_module,
            task_phase=task_phase,
            system_status=system_status,
            risk_level=risk_level,
            available_capabilities=available_capabilities,
            recent_context=recent_context,
            user_intent=intent,
            suggested_action=suggested_action,
            confidence=confidence,
            evidence=evidence,
        )
        self._last_situation = situation
        return situation

    def intent(self, situation: Situation) -> str:
        """从情境推断意图（兼容独立调用）。"""
        if situation.user_intent and situation.user_intent != INTENT_UNKNOWN:
            return situation.user_intent
        prompt = situation.recent_context.get("user_prompt", "")
        intent, _ = _infer_intent_from_prompt(prompt)
        return intent

    def reset(self) -> None:
        """重置分析器状态。"""
        self._last_situation = None


# ─────────────────────────────────────────────────────────────
# 模块级便捷函数
# ─────────────────────────────────────────────────────────────

_default_analyzer: Optional[SituationAnalyzer] = None


def get_situation(context: Optional[Dict[str, Any]] = None) -> Situation:
    """主入口函数：从 context 字典构建结构化 Situation。

    这是模块级便捷函数，内部使用默认 SituationAnalyzer（规则驱动，无 AI）。
    需要 AI 辅助或自定义配置时，请直接实例化 SituationAnalyzer。

    Args:
        context: 上下文字典（详见 SituationAnalyzer.analyze）

    Returns:
        Situation 结构化情境对象
    """
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = SituationAnalyzer()
    return _default_analyzer.analyze(context)


def intent_from_situation(situation: Situation) -> str:
    """从情境对象推断用户意图。

    Args:
        situation: Situation 对象

    Returns:
        意图字符串（monitor/analyze/report/collect/configure/troubleshoot/query/unknown）
    """
    analyzer = SituationAnalyzer()
    return analyzer.intent(situation)
