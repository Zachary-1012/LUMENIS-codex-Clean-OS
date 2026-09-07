# -*- coding: utf-8 -*-
"""
Situational Adapters — 与现有 runtime 的集成适配器
====================================================
将 AgentLoop 状态、Observation 层输出等现有结构转换为
情境感知模块可消费的 context 字典。

设计原则：
  - 只读适配，不修改源对象
  - import 失败时降级为 dict 兼容模式（不硬依赖 agent_runtime）
  - 保留原始字段在 evidence 中，可追溯
  - 与 agent_runtime.observation.Observation / loop.AgentLoop 兼容

适配函数：
  - from_agent_loop(loop_state) : 从 AgentLoop 状态提取情境上下文
  - from_observation(observation) : 从 Observation 层提取系统状态
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# 尝试导入现有基础层（失败则降级为 dict 兼容）
try:
    from agent_runtime.observation import Observation as _RuntimeObservation
    _HAS_OBSERVATION = True
except Exception:
    _RuntimeObservation = None  # type: ignore
    _HAS_OBSERVATION = False

try:
    from agent_runtime.loop import AgentLoop as _RuntimeAgentLoop, AgentConfig as _RuntimeAgentConfig
    _HAS_AGENT_LOOP = True
except Exception:
    _RuntimeAgentLoop = None  # type: ignore
    _RuntimeAgentConfig = None  # type: ignore
    _HAS_AGENT_LOOP = False

try:
    from agent_runtime.state_machine import AgentState as _RuntimeAgentState
    _HAS_AGENT_STATE = True
except Exception:
    _RuntimeAgentState = None  # type: ignore
    _HAS_AGENT_STATE = False


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """安全获取对象属性或 dict key。"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _state_to_phase(state: Any) -> str:
    """将 AgentState 枚举/字符串转换为任务阶段常量。"""
    if state is None:
        return "idle"
    state_str = str(state).lower()
    # 兼容枚举值 AgentState.PLANNING.value = "planning"
    if "." in state_str:
        state_str = state_str.split(".")[-1]
    phase_map = {
        "idle": "idle",
        "planning": "planning",
        "executing": "executing",
        "observing": "observing",
        "replanning": "replanning",
        "waiting_approval": "waiting_approval",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "failed",
    }
    return phase_map.get(state_str, "idle")


def from_agent_loop(loop_state: Dict[str, Any]) -> Dict[str, Any]:
    """从 AgentLoop 状态提取情境上下文。

    接受 AgentLoop 实例的状态快照 dict，典型字段：
      - agent_id: Agent 标识
      - state / current_state: 当前状态（AgentState 枚举或字符串）
      - config: AgentConfig dict（max_steps, max_time, ...）
      - current_step: 当前步骤索引
      - total_steps: 总步骤数
      - goal: 当前目标
      - metrics: 执行指标 {steps, duration_ms, cost, retries, replans}
      - last_error: 最近错误
      - plan: 当前 Plan dict

    Args:
        loop_state: AgentLoop 状态字典（或可 __dict__ 的对象）

    Returns:
        情境上下文字典，可直接传给 get_situation() / SituationAnalyzer.analyze()
    """
    if loop_state is None:
        return {"task_phase": "idle", "evidence": {"source": "from_agent_loop", "reason": "empty loop_state"}}

    # 兼容对象传入
    if not isinstance(loop_state, dict):
        if hasattr(loop_state, "__dict__"):
            loop_state = vars(loop_state)
        else:
            loop_state = {}

    state_val = _safe_get(loop_state, "state") or _safe_get(loop_state, "current_state")
    task_phase = _state_to_phase(state_val)

    config = _safe_get(loop_state, "config", {})
    if not isinstance(config, dict):
        config = {}

    metrics = _safe_get(loop_state, "metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}

    goal = _safe_get(loop_state, "goal", "")
    context: Dict[str, Any] = {
        "task_phase": task_phase,
        "agent_id": _safe_get(loop_state, "agent_id", ""),
        "goal": goal,
        "user_prompt": goal,  # goal 映射为 user_prompt，供意图推断使用
        "current_step": _safe_get(loop_state, "current_step", 0),
        "total_steps": _safe_get(loop_state, "total_steps", 0),
        "system_metrics": {
            "steps_executed": metrics.get("steps", 0),
            "duration_ms": metrics.get("duration_ms", 0),
            "retries": metrics.get("retries", 0),
            "replans": metrics.get("replans", 0),
        },
        "config_budget": {
            "max_steps": config.get("max_steps"),
            "max_time_seconds": config.get("max_time_seconds"),
            "max_retries": config.get("max_retries"),
            "max_replans": config.get("max_replans"),
        },
        "evidence": {
            "source": "from_agent_loop",
            "raw_state": str(state_val),
            "phase_mapped": task_phase,
        },
    }

    last_error = _safe_get(loop_state, "last_error")
    if last_error:
        context["recent_context"] = {"last_error": str(last_error)[:500]}
        context["system_metrics"]["last_error"] = str(last_error)[:200]

    # 如果状态是 failed，标记系统异常
    if task_phase == "failed":
        context["system_metrics"]["loop_status"] = "error"

    return context


def from_observation(observation: Any) -> Dict[str, Any]:
    """从 Observation 层提取系统状态上下文。

    接受 agent_runtime.observation.Observation 实例、其 to_dict() 结果、
    或兼容的 dict。提取 DB / AI / 采集 / 工具状态及前一步结果。

    Args:
        observation: Observation 对象、dict，或 None

    Returns:
        系统状态上下文字典，可合并到 get_situation() 的 context 中
    """
    if observation is None:
        return {
            "system_metrics": {},
            "evidence": {"source": "from_observation", "reason": "empty observation"},
        }

    # 转换为 dict
    if hasattr(observation, "to_dict"):
        obs_dict = observation.to_dict()
    elif isinstance(observation, dict):
        obs_dict = observation
    else:
        obs_dict = {}

    db_status = str(obs_dict.get("db_status", "unknown")).lower()
    ai_status = str(obs_dict.get("ai_status", "unknown")).lower()
    collection_status = str(obs_dict.get("collection_status", "unknown")).lower()

    # 归一化状态值
    def _normalize(s: str) -> str:
        if s in ("ok", "up", "running", "healthy"):
            return "ok"
        if s in ("degraded", "warning", "slow"):
            return "degraded"
        if s in ("unavailable", "error", "down", "failed"):
            return "unavailable"
        return s or "unknown"

    system_metrics: Dict[str, Any] = {
        "db_status": _normalize(db_status),
        "ai_status": _normalize(ai_status),
        "collection_status": _normalize(collection_status),
    }

    # DB 统计
    db_stats = obs_dict.get("db_stats", {})
    if isinstance(db_stats, dict) and db_stats:
        system_metrics["db_stats"] = db_stats

    # AI 提供者 & 熔断状态
    ai_provider = obs_dict.get("ai_provider", "")
    ai_circuit = obs_dict.get("ai_circuit_state", "")
    if ai_provider:
        system_metrics["ai_provider"] = ai_provider
    if ai_circuit:
        system_metrics["ai_circuit_state"] = ai_circuit

    # 工具状态
    tool_status = obs_dict.get("tool_status", {})
    if isinstance(tool_status, dict) and tool_status:
        system_metrics["tool_status"] = tool_status

    # 前一步结果
    prev_result = obs_dict.get("previous_step_result")
    prev_error = obs_dict.get("previous_step_error")
    prev_duration = obs_dict.get("previous_step_duration_ms", 0)

    recent_context: Dict[str, Any] = {}
    if prev_result is not None:
        recent_context["previous_step_result"] = prev_result
    if prev_error:
        recent_context["previous_step_error"] = str(prev_error)[:500]
    if prev_duration:
        recent_context["previous_step_duration_ms"] = prev_duration

    # 环境变化
    env_changed = obs_dict.get("environment_changed", False)
    changed_fields = obs_dict.get("changed_fields", [])

    context: Dict[str, Any] = {
        "system_metrics": system_metrics,
        "tool_status": tool_status if isinstance(tool_status, dict) else {},
        "recent_context": recent_context,
        "evidence": {
            "source": "from_observation",
            "observation_id": obs_dict.get("observation_id", ""),
            "step": obs_dict.get("step", 0),
            "environment_changed": env_changed,
            "changed_fields": changed_fields if isinstance(changed_fields, list) else [],
            "normalized_statuses": {
                "db": system_metrics["db_status"],
                "ai": system_metrics["ai_status"],
                "collection": system_metrics["collection_status"],
            },
        },
    }

    return context


def merge_contexts(*contexts: Dict[str, Any]) -> Dict[str, Any]:
    """合并多个情境上下文（后传入的优先级更高）。

    用于将 from_agent_loop 和 from_observation 的输出合并为
    一个完整的 context 传给 get_situation()。

    Args:
        *contexts: 多个上下文字典

    Returns:
        合并后的上下文字典
    """
    merged: Dict[str, Any] = {}
    for ctx in contexts:
        if not isinstance(ctx, dict):
            continue
        for key, value in ctx.items():
            if key == "evidence":
                # evidence 合并而非覆盖
                existing = merged.get("evidence", {})
                if isinstance(existing, dict) and isinstance(value, dict):
                    merged_evidence = dict(existing)
                    merged_evidence.update(value)
                    merged["evidence"] = merged_evidence
                else:
                    merged["evidence"] = value
            elif key == "system_metrics" and isinstance(value, dict):
                existing = merged.get("system_metrics", {})
                if isinstance(existing, dict):
                    merged_metrics = dict(existing)
                    merged_metrics.update(value)
                    merged["system_metrics"] = merged_metrics
                else:
                    merged["system_metrics"] = value
            elif key == "recent_context" and isinstance(value, dict):
                existing = merged.get("recent_context", {})
                if isinstance(existing, dict):
                    merged_rc = dict(existing)
                    merged_rc.update(value)
                    merged["recent_context"] = merged_rc
                else:
                    merged["recent_context"] = value
            else:
                merged[key] = value
    return merged
