# -*- coding: utf-8 -*-
"""PHASE 3 — Engine Runtime / Context Runtime / Observability 测试。

覆盖：
- EngineRuntime: Execution Record / 状态 / 预算 / Cooldown / Fallback / 健康检查
- ContextBuilder: Selection / Budget / Hash / Version / 缓存
- Observability: Logs / Metrics / Traces / Snapshot
"""
import os
import sys
import time
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import engine_runtime, context_runtime, observability
from osai_engine.engine_runtime import (
    EngineRuntime, make_execution_record,
    STATUS_SUCCESS, STATUS_FAILED, STATUS_TIMEOUT, STATUS_UNAVAILABLE,
    STATUS_FALLBACK, STATUS_BLOCKED, STATUS_DEGRADED, ALL_STATUSES,
)
from osai_engine.context_runtime import (
    ContextBuilder, ALL_CONTEXT_TYPES,
    CTX_REPOSITORY, CTX_TASK, CTX_EVIDENCE, CTX_RUNTIME,
)
from osai_engine.observability import (
    Observability, Metric, TraceSpan,
    LOG_INFO, LOG_WARN, LOG_ERROR,
)


# ============ Engine Runtime 测试 ============

class TestExecutionRecord:
    def test_make_record_has_all_fields(self):
        rec = make_execution_record(task_id="t001", engine_type="cloud",
                                     provider="zhipu", model="glm-4.5-air",
                                     task_type="daily")
        required = ["request_id", "trace_id", "task_id", "engine_id",
                    "engine_type", "provider", "model", "task_type",
                    "start_time", "end_time", "latency_ms",
                    "input_tokens", "output_tokens", "status", "error",
                    "fallback_chain", "retry_count", "evidence_id",
                    "evaluation_id", "content", "context_hash", "context_size"]
        for f in required:
            assert f in rec, f"missing field: {f}"
        assert rec["task_id"] == "t001"
        assert rec["status"] == "PENDING"
        assert rec["request_id"].startswith("req_")
        assert rec["trace_id"].startswith("trc_")

    def test_all_statuses_defined(self):
        assert len(ALL_STATUSES) == 7
        for s in [STATUS_SUCCESS, STATUS_FAILED, STATUS_TIMEOUT,
                  STATUS_UNAVAILABLE, STATUS_FALLBACK, STATUS_BLOCKED, STATUS_DEGRADED]:
            assert s in ALL_STATUSES


class TestEngineRuntime:
    def test_runtime_init(self):
        rt = EngineRuntime(max_retry=1, timeout=30, budget_tokens=1000)
        assert rt.max_retry == 1
        assert rt.timeout == 30
        assert rt.budget_tokens == 1000

    def test_budget_exceeded_blocks(self):
        rt = EngineRuntime(budget_tokens=0)  # 预算为 0
        result = rt.execute("t_budget", "test prompt", "daily")
        assert result["ok"] is False
        assert result["status"] == STATUS_BLOCKED
        assert "budget_exceeded" in result["record"]["error"]

    def test_no_provider_unavailable(self, monkeypatch):
        """所有 Provider 不可用时返回 UNAVAILABLE。"""
        monkeypatch.setattr(engine_runtime.ai_gateway, "route",
                            lambda t="daily": (None, None, {"error": "no provider"}))
        rt = EngineRuntime()
        result = rt.execute("t_noprov", "test", "daily")
        assert result["ok"] is False
        assert result["status"] == STATUS_UNAVAILABLE

    def test_health_check_structure(self):
        rt = EngineRuntime()
        hc = rt.health_check()
        assert "gateway" in hc
        assert "engines" in hc
        assert "runtime" in hc
        assert "local" in hc["engines"]
        assert "cloud" in hc["engines"]
        assert "coding" in hc["engines"]
        assert hc["runtime"]["max_retry"] == rt.max_retry

    def test_get_records(self):
        rt = EngineRuntime(budget_tokens=0)
        rt.execute("t1", "p1", "daily")
        rt.execute("t2", "p2", "daily")
        records = rt.get_records()
        assert len(records) >= 2
        assert records[0]["task_id"] in ("t1", "t2")

    def test_get_records_by_status(self):
        rt = EngineRuntime(budget_tokens=0)
        rt.execute("t1", "p1", "daily")
        blocked = rt.get_records(status=STATUS_BLOCKED)
        assert len(blocked) >= 1
        assert all(r["status"] == STATUS_BLOCKED for r in blocked)

    def test_reset_budget(self):
        rt = EngineRuntime(budget_tokens=0)
        rt.execute("t1", "p1", "daily")
        assert rt._token_usage == 0  # blocked 不消耗
        rt.reset_budget()
        assert rt._token_usage == 0

    def test_auto_select_engine(self):
        rt = EngineRuntime()
        assert rt._auto_select_engine("local_only") == "local"
        assert rt._auto_select_engine("deep") == "coding"
        assert rt._auto_select_engine("daily") == "cloud"
        assert rt._auto_select_engine("vision") == "cloud"

    def test_evidence_from_record(self):
        rt = EngineRuntime()
        rec = make_execution_record(task_id="t_ev", provider="zhipu",
                                     model="glm-4.5-air", task_type="daily")
        rec["status"] = STATUS_SUCCESS
        rec["latency_ms"] = 100.5
        rec["input_tokens"] = 50
        rec["output_tokens"] = 100
        ev = rt._evidence_from_record(rec)
        assert ev["trace_id"] == rec["trace_id"]
        assert ev["provider"] == "zhipu"
        assert ev["success"] is True
        assert ev["status"] == STATUS_SUCCESS
        assert ev["tokens_in"] == 50
        assert ev["tokens_out"] == 100

    def test_runtime_snapshot(self):
        snap = engine_runtime.runtime_snapshot()
        assert "gateway" in snap
        assert "engines" in snap
        assert "runtime" in snap


# ============ Context Runtime 测试 ============

class TestContextBuilder:
    def test_init(self):
        cb = ContextBuilder(max_tokens=2000, max_chars=8000)
        assert cb.max_tokens == 2000
        assert cb.max_chars == 8000

    def test_build_empty_context(self):
        cb = ContextBuilder(include_runtime=False)
        result = cb.build({}, "daily", base_prompt="hello")
        assert result["prompt"] == "hello"
        assert result["size"] == len("hello")
        assert result["sources"] == []
        assert result["truncated"] is False

    def test_build_with_repository_context(self):
        cb = ContextBuilder(include_runtime=False)
        ctx = {"repository": {"name": "ZBC", "sha": "abc123def456",
                               "branch": "main", "files": ["app.py", "config.py"]}}
        # repository context 只在 deep 任务中被选择
        result = cb.build(ctx, "deep", base_prompt="analyze")
        assert "ZBC" in result["prompt"]
        assert "repository" in result["sources"]
        assert result["contexts"]["repository"]["name"] == "ZBC"
        assert result["hash"]  # 非空

    def test_build_with_task_context(self):
        cb = ContextBuilder(include_runtime=False)
        ctx = {"task": {"task_id": "t001", "description": "分析舆情数据",
                         "priority": "high"}}
        result = cb.build(ctx, "daily", base_prompt="go")
        assert "t001" in result["prompt"]
        assert "分析舆情数据" in result["prompt"]
        assert "task" in result["sources"]

    def test_build_with_evidence_context(self):
        cb = ContextBuilder(include_runtime=False)
        ctx = {"evidence": [
            {"source": "api", "content": "负面评论增加", "confidence": 0.9},
            {"source": "db", "content": "风险等级上升", "confidence": 0.8},
        ]}
        result = cb.build(ctx, "daily", base_prompt="summarize")
        assert "负面评论增加" in result["prompt"]
        assert "evidence" in result["sources"]
        assert result["contexts"]["evidence"]["evidence_count"] == 2

    def test_evidence_truncation(self):
        """超过 5 条 evidence 时截断。"""
        cb = ContextBuilder(include_runtime=False)
        ctx = {"evidence": [{"source": f"s{i}", "content": f"content{i}",
                              "confidence": 0.5} for i in range(10)]}
        result = cb.build(ctx, "daily")
        assert result["contexts"]["evidence"]["truncated"] is True
        assert result["contexts"]["evidence"]["evidence_count"] == 10

    def test_context_selection_daily(self):
        """daily 任务只选择 task/evidence/skill/runtime。"""
        cb = ContextBuilder(include_runtime=False)
        ctx = {
            "repository": {"name": "ZBC"},
            "task": {"task_id": "t1"},
            "evidence": [{"source": "a", "content": "b"}],
            "session": {"session_id": "s1", "history": []},
        }
        result = cb.build(ctx, "daily")
        assert "task" in result["sources"]
        assert "evidence" in result["sources"]
        # daily 不选 repository 和 session
        assert "repository" not in result["sources"]
        assert "session" not in result["sources"]

    def test_context_selection_deep(self):
        """deep 任务选择更多 Context。"""
        cb = ContextBuilder(include_runtime=False)
        ctx = {
            "repository": {"name": "ZBC"},
            "task": {"task_id": "t1"},
            "evidence": [{"source": "a", "content": "b"}],
        }
        result = cb.build(ctx, "deep")
        assert "repository" in result["sources"]
        assert "task" in result["sources"]
        assert "evidence" in result["sources"]

    def test_runtime_context_auto_injected(self):
        cb = ContextBuilder(include_runtime=True)
        result = cb.build({}, "daily")
        assert "runtime" in result["sources"]
        assert "Runtime" in result["prompt"]

    def test_budget_truncation(self):
        cb = ContextBuilder(max_chars=50, include_runtime=False)
        ctx = {"task": {"task_id": "t1", "description": "x" * 200}}
        result = cb.build(ctx, "daily")
        assert result["truncated"] is True
        assert result["size"] <= 50 + len("\n...[truncated]")

    def test_hash_deterministic(self):
        cb = ContextBuilder(include_runtime=False)
        ctx = {"task": {"task_id": "t1", "description": "test"}}
        r1 = cb.build(ctx, "daily")
        r2 = cb.build(ctx, "daily")
        assert r1["hash"] == r2["hash"]
        assert r1["version"] == r2["version"]

    def test_hash_changes_with_content(self):
        cb = ContextBuilder(include_runtime=False)
        r1 = cb.build({"task": {"task_id": "t1"}}, "daily")
        r2 = cb.build({"task": {"task_id": "t2"}}, "daily")
        assert r1["hash"] != r2["hash"]

    def test_cache_reuse(self):
        cb = ContextBuilder(include_runtime=False)
        r1 = cb.build({"task": {"task_id": "t1"}}, "daily")
        cached = cb.get_cached(r1["hash"])
        assert cached is not None
        assert cached["hash"] == r1["hash"]

    def test_clear_cache(self):
        cb = ContextBuilder(include_runtime=False)
        cb.build({"task": {"task_id": "t1"}}, "daily")
        assert len(cb._cache) == 1
        cb.clear_cache()
        assert len(cb._cache) == 0

    def test_all_context_types(self):
        assert len(ALL_CONTEXT_TYPES) == 6
        for ct in [CTX_REPOSITORY, CTX_TASK, "skill", CTX_EVIDENCE,
                    CTX_RUNTIME, "session"]:
            assert ct in ALL_CONTEXT_TYPES

    def test_context_snapshot(self):
        snap = context_runtime.context_snapshot()
        assert "max_tokens" in snap
        assert "max_chars" in snap
        assert "supported_types" in snap
        assert len(snap["supported_types"]) == 6


# ============ Observability 测试 ============

class TestMetric:
    def test_metric_incr(self):
        m = Metric("test")
        m.incr(1)
        m.incr(2)
        assert m.count == 2
        assert m.sum == 3
        assert m.avg == 1.5

    def test_metric_min_max(self):
        m = Metric("test")
        m.observe(10)
        m.observe(5)
        m.observe(20)
        assert m.min == 5
        assert m.max == 20

    def test_metric_tags(self):
        m = Metric("test")
        m.incr(tags={"provider": "zhipu"})
        m.incr(tags={"provider": "zhipu"})
        m.incr(tags={"provider": "ark"})
        assert m.tags["provider=zhipu"] == 2
        assert m.tags["provider=ark"] == 1

    def test_metric_to_dict(self):
        m = Metric("test")
        m.incr(5)
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["count"] == 1
        assert d["sum"] == 5
        assert d["avg"] == 5


class TestObservabilityLogs:
    def test_log_record(self):
        obs = Observability(log_level=LOG_INFO)
        obs.log("INFO", "test message", task_id="t1")
        logs = obs.get_logs()
        assert len(logs) >= 1
        assert logs[0]["message"] == "test message"
        assert logs[0]["level"] == "INFO"
        assert logs[0]["fields"]["task_id"] == "t1"

    def test_log_level_filter(self):
        obs = Observability(log_level=LOG_WARN)
        obs.log("INFO", "should be filtered")
        obs.log("WARN", "should pass")
        logs = obs.get_logs()
        assert all(l["level"] != "INFO" for l in logs)
        assert any(l["level"] == "WARN" for l in logs)

    def test_log_sensitive_fields_filtered(self):
        obs = Observability(log_level=LOG_INFO)
        obs.log("INFO", "test", api_key="secret123", token="tok456",
                password="pass789", task_id="t1")
        logs = obs.get_logs()
        fields = logs[0]["fields"]
        assert "api_key" not in fields
        assert "token" not in fields
        assert "password" not in fields
        assert fields["task_id"] == "t1"

    def test_get_logs_by_level(self):
        obs = Observability(log_level=LOG_INFO)
        obs.log("INFO", "info msg")
        obs.log("ERROR", "error msg")
        errors = obs.get_logs(level="ERROR")
        assert all(l["level"] == "ERROR" for l in errors)


class TestObservabilityMetrics:
    def test_metric_incr(self):
        obs = Observability()
        obs.metric_incr("ai.calls", tags={"provider": "zhipu"})
        obs.metric_incr("ai.calls", tags={"provider": "zhipu"})
        m = obs.get_metric("ai.calls")
        assert m["count"] == 2
        assert m["tags"]["provider=zhipu"] == 2

    def test_metric_observe(self):
        obs = Observability()
        obs.metric_observe("ai.latency_ms", 100.0)
        obs.metric_observe("ai.latency_ms", 200.0)
        m = obs.get_metric("ai.latency_ms")
        assert m["count"] == 2
        assert m["avg"] == 150.0
        assert m["min"] == 100.0
        assert m["max"] == 200.0

    def test_get_metrics_all(self):
        obs = Observability()
        obs.metric_incr("m1")
        obs.metric_incr("m2")
        all_m = obs.get_metrics()
        assert "m1" in all_m
        assert "m2" in all_m


class TestObservabilityTraces:
    def test_trace_start_end(self):
        obs = Observability()
        span = obs.trace_start("ai_call", provider="zhipu")
        assert span.status == "running"
        assert span.trace_id
        assert span.span_id
        time.sleep(0.01)
        obs.trace_end(span.span_id, "ok")
        assert span.status == "ok"
        assert span.duration_ms is not None
        assert span.duration_ms > 0

    def test_trace_context_manager(self):
        obs = Observability()
        with obs.trace("test_op", task_id="t1") as span:
            assert span.status == "running"
            span.attributes["result"] = "success"
        assert span.status == "ok"
        assert span.attributes["result"] == "success"
        assert span.duration_ms is not None

    def test_trace_context_manager_error(self):
        obs = Observability()
        try:
            with obs.trace("failing_op"):
                raise ValueError("test error")
        except ValueError:
            pass
        traces = obs.get_recent_traces()
        assert len(traces) >= 1
        spans = traces[-1]["spans"]
        assert any(s["status"] == "error" for s in spans)

    def test_get_trace(self):
        obs = Observability()
        span = obs.trace_start("op1", trace_id="trace_abc")
        obs.trace_end(span.span_id)
        trace = obs.get_trace("trace_abc")
        assert len(trace) == 1
        assert trace[0]["name"] == "op1"

    def test_trace_span_attributes(self):
        obs = Observability()
        span = obs.trace_start("op", model="glm-4.5-air", tokens=100)
        assert span.attributes["model"] == "glm-4.5-air"
        assert span.attributes["tokens"] == 100


class TestObservabilitySnapshot:
    def test_snapshot_structure(self):
        obs = Observability()
        obs.log("INFO", "test")
        obs.metric_incr("m1")
        snap = obs.snapshot()
        assert "metrics" in snap
        assert "logs_count" in snap
        assert "traces_count" in snap
        assert "active_spans" in snap
        assert "log_level" in snap
        assert "recent_logs" in snap
        assert snap["logs_count"] >= 1

    def test_reset(self):
        obs = Observability()
        obs.log("INFO", "test")
        obs.metric_incr("m1")
        obs.reset()
        assert obs.get_metrics() == {}
        assert obs.get_logs() == []


# ============ 集成测试：Runtime + Context + Observability ============

class TestIntegration:
    def test_runtime_with_context_builder(self):
        """EngineRuntime 集成 ContextBuilder。"""
        cb = ContextBuilder(include_runtime=False)
        rt = EngineRuntime(context_builder=cb.build, budget_tokens=0)
        ctx = {"task": {"task_id": "int_t1", "description": "集成测试"}}
        result = rt.execute("int_t1", "prompt", "daily", context=ctx)
        # budget=0 会 BLOCKED，但 context 应该已被处理
        assert result["record"]["context_hash"]  # 非空
        assert result["record"]["context_size"] > 0

    def test_observability_records_runtime(self):
        """Observability 记录 Engine Runtime 调用。"""
        obs = Observability()
        rt = EngineRuntime(budget_tokens=0)
        with obs.trace("engine_execute", task_id="obs_t1"):
            result = rt.execute("obs_t1", "prompt", "daily")
            obs.metric_incr("engine.calls",
                            tags={"status": result["status"]})
        m = obs.get_metric("engine.calls")
        assert m["count"] == 1
        traces = obs.get_recent_traces()
        assert len(traces) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
