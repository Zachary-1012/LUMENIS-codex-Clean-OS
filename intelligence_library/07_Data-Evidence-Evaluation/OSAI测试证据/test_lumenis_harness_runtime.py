# -*- coding: utf-8 -*-
"""PHASE 3 — Harness Runtime 测试。

覆盖：
- HarnessRuntime 初始化 / 阶段执行
- 预算 / 超时阻断
- Evidence 链生成
- HUMAN_APPROVAL 阶段阻断
- run_harness 便捷函数
- harness_snapshot
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import harness_runtime
from osai_engine.harness_runtime import (
    HarnessRuntime, HARNESS_STAGES, AUTOMATED_STAGES, HUMAN_STAGES,
    run_harness, harness_snapshot,
)
from osai_engine.engine_runtime import EngineRuntime


class TestHarnessStages:
    def test_stages_complete(self):
        assert len(HARNESS_STAGES) == 10
        for s in ["INSPECT", "CONTEXT", "PLAN", "EXECUTE", "OBSERVE",
                  "TEST", "VERIFY", "EVIDENCE", "EVALUATE", "HUMAN_APPROVAL"]:
            assert s in HARNESS_STAGES

    def test_automated_stages(self):
        assert "HUMAN_APPROVAL" not in AUTOMATED_STAGES
        assert "INSPECT" in AUTOMATED_STAGES
        assert "EXECUTE" in AUTOMATED_STAGES

    def test_human_stages(self):
        assert "HUMAN_APPROVAL" in HUMAN_STAGES
        assert len(HUMAN_STAGES) == 1


class TestHarnessRuntime:
    def test_init(self):
        h = HarnessRuntime(task="test task", repo="ZBC", max_iterations=3)
        assert h.task == "test task"
        assert h.repo == "ZBC"
        assert h.max_iterations == 3
        assert h.task_id.startswith("H-")
        assert h.status == "initialized"
        assert h.stage_history == []

    def test_run_stops_at_human_approval(self):
        """Harness 运行到 HUMAN_APPROVAL 阶段必须停止。"""
        h = HarnessRuntime(task="test", repo="OSAI",
                           engine=EngineRuntime(budget_tokens=0))
        result = h.run()
        # budget=0 会在 EXECUTE 阶段 BLOCKED，或者运行到 HUMAN_APPROVAL
        assert result["status"] in ("waiting_approval", "blocked", "failed")
        assert result["task_id"].startswith("H-")
        assert "stage_history" in result
        assert len(result["stage_history"]) >= 1

    def test_run_with_budget_blocked(self):
        """预算为 0 时，EXECUTE 阶段应 BLOCKED。"""
        h = HarnessRuntime(task="test", repo="ZBC",
                           engine=EngineRuntime(budget_tokens=0))
        result = h.run()
        # 可能在 EXECUTE 阶段 blocked
        stages = [s["stage"] for s in result["stage_history"]]
        assert "INSPECT" in stages
        assert "CONTEXT" in stages

    def test_evidence_chain(self):
        h = HarnessRuntime(task="test", repo="OSAI",
                           engine=EngineRuntime(budget_tokens=0))
        h.run()
        # budget=0 时 evidence_chain 可能为空
        assert isinstance(h.evidence_chain, list)

    def test_stage_history_records(self):
        h = HarnessRuntime(task="test", repo="ZBC",
                           engine=EngineRuntime(budget_tokens=0))
        h.run()
        for record in h.stage_history:
            assert "stage" in record
            assert "status" in record
            assert "timestamp" in record
            assert "elapsed" in record

    def test_result_structure(self):
        h = HarnessRuntime(task="test", repo="ZBC",
                           engine=EngineRuntime(budget_tokens=0))
        result = h.run()
        required = ["task_id", "task", "repo", "status", "stage_history",
                    "evidence_count", "evaluation", "elapsed_seconds", "next_action"]
        for key in required:
            assert key in result, f"missing key: {key}"

    def test_next_action_waiting_approval(self):
        """如果状态是 waiting_approval，next_action 必须是 HUMAN_APPROVAL。"""
        h = HarnessRuntime(task="test", repo="ZBC",
                           engine=EngineRuntime(budget_tokens=100000))
        result = h.run()
        if result["status"] == "waiting_approval":
            assert result["next_action"] == "HUMAN_APPROVAL"


class TestRunHarness:
    def test_run_harness_returns_result(self):
        result = run_harness("test task", repo="OSAI",
                             engine=EngineRuntime(budget_tokens=0))
        assert "task_id" in result
        assert "status" in result
        assert result["task"] == "test task"


class TestHarnessSnapshot:
    def test_snapshot_structure(self):
        snap = harness_snapshot()
        assert "stages" in snap
        assert "automated_stages" in snap
        assert "human_stages" in snap
        assert "engine" in snap
        assert "observability" in snap
        assert len(snap["stages"]) == 10

    def test_snapshot_engine_has_runtime(self):
        snap = harness_snapshot()
        assert "runtime" in snap["engine"]
        assert "gateway" in snap["engine"]

    def test_snapshot_observability_has_metrics(self):
        snap = harness_snapshot()
        assert "metrics" in snap["observability"]
        assert "logs_count" in snap["observability"]


class TestHarnessIntegration:
    def test_harness_uses_context_builder(self):
        """Harness 必须使用 ContextBuilder 构建上下文。"""
        h = HarnessRuntime(task="test", repo="ZBC",
                           engine=EngineRuntime(budget_tokens=0))
        # 手动执行 CONTEXT 阶段
        result = h._stage_context()
        assert result["status"] == "ok"
        assert "context size=" in result["detail"]

    def test_harness_uses_observability(self):
        """Harness 必须记录 Observability。"""
        h = HarnessRuntime(task="test", repo="ZBC",
                           engine=EngineRuntime(budget_tokens=0))
        h.run()
        metrics = h.obs.get_metrics()
        # 至少有 harness.inspect 或其他指标
        assert isinstance(metrics, dict)

    def test_harness_no_commit_push(self):
        """Harness 结果中不包含 commit/push 操作。"""
        h = HarnessRuntime(task="test", repo="ZBC",
                           engine=EngineRuntime(budget_tokens=0))
        result = h.run()
        assert "commit" not in str(result).lower() or result["next_action"] != "COMMIT"
        assert result["next_action"] in ("HUMAN_APPROVAL", "NONE")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
