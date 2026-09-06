# -*- coding: utf-8 -*-
"""LUMENIS Engine Layer 测试（PHASE 2 Foundation）。

验证 LocalEngine / CloudEngine / CodingEngine 的 Contract、路由、健康检查、
Evidence 记录、降级逻辑。不实际调用外部 API。
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import engine_layer, ai_gateway


def test_engine_classes_exist():
    assert hasattr(engine_layer, "LocalEngine")
    assert hasattr(engine_layer, "CloudEngine")
    assert hasattr(engine_layer, "CodingEngine")
    assert hasattr(engine_layer, "BaseEngine")
    assert hasattr(engine_layer, "get_engine")
    assert hasattr(engine_layer, "engine_snapshot")


def test_engine_factory():
    for name in ("local", "cloud", "coding"):
        eng = engine_layer.get_engine(name)
        assert eng is not None
        assert eng.engine_type == name


def test_engine_health_check():
    eng = engine_layer.CloudEngine()
    hc = eng.health_check()
    assert "engine" in hc
    assert "provider" in hc
    assert "model" in hc
    assert "available" in hc


def test_engine_route_returns_tuple():
    eng = engine_layer.CloudEngine()
    provider, model, meta = eng.route("daily")
    assert isinstance(provider, (str, type(None)))
    assert isinstance(model, (str, type(None)))
    assert isinstance(meta, dict)


def test_coding_engine_forces_deep_route():
    eng = engine_layer.CodingEngine()
    provider, model, meta = eng.route()
    # Coding Engine 走 deep 路由配置（TASK_ROUTES["deep"]），不断言具体 provider
    # 因为环境可能无 zhipu key，会 fallback 到 qwen/ollama
    deep_cfg = ai_gateway.TASK_ROUTES["deep"]
    assert deep_cfg["primary"] == "zhipu"
    # provider 必须是 deep 路由的 primary 或 fallback 之一
    valid_providers = [deep_cfg["primary"]] + deep_cfg.get("fallback", [])
    assert provider in valid_providers or provider is None


def test_engine_execute_no_provider_fallback():
    """无可用 Provider 时返回 fallback，不抛异常。"""
    # 临时清空 PROVIDERS 模拟无可用
    original = ai_gateway.PROVIDERS
    ai_gateway.PROVIDERS = {}
    try:
        eng = engine_layer.CloudEngine()
        result = eng.execute("test", "daily")
        assert result["ok"] is False
        assert "fallback" in result
        assert result["evidence"]["success"] is False
    finally:
        ai_gateway.PROVIDERS = original


def test_engine_evidence_recorded():
    eng = engine_layer.CloudEngine()
    # 无 key 时 execute 会走降级，但 evidence 必须记录
    result = eng.execute("test prompt", "daily")
    assert eng.last_evidence is not None
    ev = eng.last_evidence
    assert "trace_id" in ev
    assert "provider" in ev
    assert "model" in ev
    assert "latency_ms" in ev
    assert "timestamp" in ev


def test_engine_snapshot():
    snap = engine_layer.engine_snapshot()
    assert "local" in snap
    assert "cloud" in snap
    assert "coding" in snap
    for name in ("local", "cloud", "coding"):
        assert "health" in snap[name]
        assert "supported_tasks" in snap[name]


def test_local_engine_supported_tasks():
    eng = engine_layer.LocalEngine()
    assert "local_only" in eng.supported_tasks
    assert "daily" in eng.supported_tasks


def test_cloud_engine_supported_tasks():
    eng = engine_layer.CloudEngine()
    assert "daily" in eng.supported_tasks
    assert "deep" in eng.supported_tasks
    assert "vision" in eng.supported_tasks


def test_engines_registered_in_factory():
    assert set(engine_layer.ENGINES.keys()) == {"local", "cloud", "coding"}


def test_make_evidence_structure():
    ev = engine_layer._make_evidence("zhipu", "glm-4.5-air", "daily", 123.45,
                                     tokens_in=100, tokens_out=50)
    assert ev["provider"] == "zhipu"
    assert ev["model"] == "glm-4.5-air"
    assert ev["task_type"] == "daily"
    assert ev["latency_ms"] == 123.45
    assert ev["tokens_in"] == 100
    assert ev["tokens_out"] == 50
    assert ev["success"] is True
    assert len(ev["trace_id"]) == 12


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
