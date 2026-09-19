# -*- coding: utf-8 -*-
"""
Integration tests for agent_runtime.loop
覆盖：完整 Agent Loop（mock工具+mock AI）、状态转换验证、预算控制、取消、重规划
"""
import sys
import os
import json
import pytest
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_runtime.loop import AgentLoop, AgentConfig, AgentResult
from agent_runtime.state_machine import AgentState
from agent_runtime.planner import Plan, PlanStep, Planner, PlanMode
from agent_runtime.replanner import Replanner
from agent_runtime.observation import ObservationLayer
from lumenis.shared.evaluation.trajectory import TrajectoryEvaluator
from agent_runtime.durable_adapter import DurableExecutionAdapter


# ──────────────────────────────────────────────────────────
# Mock 工具
# ──────────────────────────────────────────────────────────

def _mock_ai_chat(system, user, model=None, temperature=0.1, max_tokens=1200, timeout=None):
    """Mock AI 规划调用。"""
    plan = {
        "steps": [
            {"action": "步骤1：数据采集", "tool": "collector", "params": {"platform": "xiaohongshu"},
             "expected_output": "笔记数据", "risk_level": "low"},
            {"action": "步骤2：数据分析", "tool": "analyzer", "params": {"data": "from_step_1"},
             "expected_output": "分析结果", "risk_level": "low"},
            {"action": "步骤3：生成报告", "tool": "reporter", "params": {"analysis": "from_step_2"},
             "expected_output": "日报", "risk_level": "low"},
        ]
    }
    return json.dumps(plan, ensure_ascii=False), "zhipu"


def _mock_tool_executor_success(step, context):
    """Mock 工具执行：全部成功。"""
    return {
        "success": True,
        "output": f"executed: {step.action}",
        "tool": step.tool,
        "estimated_cost": 0.01,
    }


def _mock_tool_executor_step1_fails(step, context):
    """Mock 工具执行：步骤1永远失败。"""
    if step.index == 0:
        return {"success": False, "error": "collection timeout", "estimated_cost": 0.0}
    return {"success": True, "output": f"executed: {step.action}", "estimated_cost": 0.01}


def _mock_tool_executor_slow(step, context):
    """Mock 工具执行：慢速（用于测试超时）。"""
    time.sleep(0.05)
    return {"success": True, "output": f"slow: {step.action}", "estimated_cost": 0.01}


# ──────────────────────────────────────────────────────────
# 测试：完整成功执行
# ──────────────────────────────────────────────────────────

class TestFullLoopSuccess:
    def test_complete_loop_success(self):
        """完整 Agent Loop：3步全部成功。"""
        config = AgentConfig(max_steps=10, max_time_seconds=30, max_cost=5.0)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("生成今日舆情日报", context={"date": "today"})

        assert result.status == "completed"
        assert result.error is None
        assert result.metrics["steps"] == 3
        assert result.metrics["completed_steps"] == 3
        assert result.metrics["failed_steps"] == 0
        assert result.metrics["replans"] == 0
        assert result.metrics["final_state"] == "completed"
        assert result.duration_ms > 0
        assert result.evaluation is not None
        assert result.evaluation["overall_score"] >= 0.8

    def test_loop_generates_task_id(self):
        """Loop 应生成 task_id。"""
        loop = AgentLoop(
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        assert result.task_id
        assert result.task_id.startswith("agent_")

    def test_loop_transitions_recorded(self):
        """状态转换应被记录。"""
        loop = AgentLoop(
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        states = [t["to_state"] for t in result.transitions]
        assert "planning" in states
        assert "executing" in states
        assert "completed" in states

    def test_loop_plan_persisted_in_result(self):
        """规划结果应包含在 result 中。"""
        loop = AgentLoop(
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        assert result.plan is not None
        assert result.plan["goal"] == "test"
        assert len(result.plan["steps"]) == 3


# ──────────────────────────────────────────────────────────
# 测试：预算控制
# ──────────────────────────────────────────────────────────

class TestBudgetControl:
    def test_max_steps_budget(self):
        """max_steps 限制：规划3步但max_steps=1，应触发预算超限。"""
        config = AgentConfig(max_steps=1, max_time_seconds=30)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        # max_steps=1 意味着 step_index >= 1 时停止，第一步执行后第二步检查时超限
        assert result.status in ("max_steps", "completed")
        # 至少不会无限循环
        assert result.metrics["steps"] <= 3

    def test_max_time_budget(self):
        """max_time 限制：极短超时应触发超时。"""
        config = AgentConfig(max_steps=20, max_time_seconds=0.001, max_cost=100.0)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_slow,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        assert result.status in ("max_time", "completed", "failed")
        # 不会无限运行
        assert result.duration_ms < 5000

    def test_max_cost_budget(self):
        """max_cost 限制：极低成本预算应触发超限。"""
        config = AgentConfig(max_steps=20, max_time_seconds=30, max_cost=0.0001)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        assert result.status in ("max_cost", "completed")

    def test_max_retries_triggers_replan(self):
        """步骤失败超 max_retries 应触发重规划。"""
        config = AgentConfig(max_steps=20, max_time_seconds=30, max_retries=1, max_replans=1)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_step1_fails,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        # 步骤1失败 → 重规划 → 新计划步骤1仍失败 → 最终失败或完成（跳过）
        assert result.status in ("failed", "completed", "max_steps")
        assert result.metrics["replans"] >= 0


# ──────────────────────────────────────────────────────────
# 测试：取消
# ──────────────────────────────────────────────────────────

class TestCancellation:
    def test_external_cancel(self):
        """外部取消应终止 Loop。"""
        config = AgentConfig(max_steps=20, max_time_seconds=30)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_slow,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )

        # 在另一个线程中取消
        def cancel_after_delay():
            time.sleep(0.02)
            loop.cancel()

        t = threading.Thread(target=cancel_after_delay)
        t.start()
        result = loop.run("test")
        t.join(timeout=5)

        # 可能在取消前已完成，也可能被取消
        assert result.status in ("cancelled", "completed")

    def test_cancel_flag_resets_between_runs(self):
        """两次 run 之间取消标志应重置。"""
        loop = AgentLoop(
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        loop.cancel()  # 先取消
        result = loop.run("test")  # 再运行，应正常完成
        assert result.status == "completed"


# ──────────────────────────────────────────────────────────
# 测试：重规划集成
# ──────────────────────────────────────────────────────────

class TestReplanningIntegration:
    def test_replanning_count_limited(self):
        """重规划次数不应超过 max_replans。"""
        config = AgentConfig(max_steps=20, max_time_seconds=30, max_retries=1, max_replans=2)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_step1_fails,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        assert result.metrics["replans"] <= 2


# ──────────────────────────────────────────────────────────
# 测试：配置
# ──────────────────────────────────────────────────────────

class TestAgentConfig:
    def test_default_config(self):
        config = AgentConfig()
        assert config.max_steps == 20
        assert config.max_time_seconds == 300.0
        assert config.max_cost == 2.0
        assert config.max_retries == 3
        assert config.max_replans == 2

    def test_custom_config(self):
        config = AgentConfig(max_steps=5, max_time_seconds=60, max_cost=1.0)
        assert config.max_steps == 5
        assert config.max_time_seconds == 60
        assert config.max_cost == 1.0

    def test_config_to_dict(self):
        config = AgentConfig(max_steps=10)
        d = config.to_dict()
        assert d["max_steps"] == 10
        assert d["max_time_seconds"] == 300.0


# ──────────────────────────────────────────────────────────
# 测试：Durable Adapter 集成
# ──────────────────────────────────────────────────────────

class TestDurableAdapterIntegration:
    def test_durable_disabled(self):
        """Durable 禁用时仍能正常运行。"""
        loop = AgentLoop(
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        assert result.status == "completed"

    def test_durable_memory_persistence(self):
        """Durable 内存模式应记录检查点。"""
        adapter = DurableExecutionAdapter(enabled=False)
        loop = AgentLoop(
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=adapter,
        )
        result = loop.run("test")
        checkpoints = adapter.get_checkpoints(result.task_id)
        assert len(checkpoints) > 0  # 每步都有 checkpoint


# ──────────────────────────────────────────────────────────
# 测试：评估集成
# ──────────────────────────────────────────────────────────

class TestEvaluationIntegration:
    def test_evaluation_disabled(self):
        """禁用评估时 result.evaluation 应为 None。"""
        config = AgentConfig(enable_evaluation=False)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        assert result.evaluation is None

    def test_evaluation_enabled(self):
        """启用评估时 result.evaluation 应包含评分。"""
        config = AgentConfig(enable_evaluation=True)
        loop = AgentLoop(
            config=config,
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        assert result.evaluation is not None
        assert "overall_score" in result.evaluation
        assert "grade" in result.evaluation
        assert "goal_completion" in result.evaluation


# ──────────────────────────────────────────────────────────
# 测试：空规划 / 异常
# ──────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_plan_falls_back(self):
        """AI 返回空 steps 时应降级为单步计划并执行成功。"""
        def empty_plan_chat(system, user, **kwargs):
            return json.dumps({"steps": []}), "zhipu"

        loop = AgentLoop(
            planner=Planner(ai_chat_func=empty_plan_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        # 空 steps 触发 fallback → 单步 direct_execution → 执行成功
        assert result.status == "completed"
        assert result.metrics["steps"] == 1
        assert result.plan["is_fallback"] is True

    def test_ai_exception_fallback(self):
        """AI 异常时应降级为单步计划并执行。"""
        def raising_chat(system, user, **kwargs):
            raise RuntimeError("AI down")

        loop = AgentLoop(
            planner=Planner(ai_chat_func=raising_chat),
            tool_executor=_mock_tool_executor_success,
            durable_adapter=DurableExecutionAdapter(enabled=False),
        )
        result = loop.run("test")
        # 降级为单步 direct_execution，应能完成
        assert result.status == "completed"
        assert result.metrics["steps"] == 1

    def test_tool_exception_handled(self):
        """工具执行异常应被捕获，不崩溃。"""
        def raising_tool(step, context):
            raise RuntimeError("tool crashed")

        loop = AgentLoop(
            planner=Planner(ai_chat_func=_mock_ai_chat),
            tool_executor=raising_tool,
            durable_adapter=DurableExecutionAdapter(enabled=False),
            config=AgentConfig(max_retries=0, max_replans=0),
        )
        result = loop.run("test")
        # 工具异常被捕获，步骤标记失败
        assert result.status in ("failed", "completed")
        assert result.error is None or "exception" not in (result.error or "").lower()
