# -*- coding: utf-8 -*-
"""
Unit tests for agent_runtime.observation
覆盖：观察者注册、DB状态观察、AI状态观察、工具状态观察、环境变化检测
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_runtime.observation import (
    Observation, ObservationLayer, BaseObserver,
    DBStatusObserver, AIStatusObserver, ToolStatusObserver, CollectionStatusObserver,
)


class TestObservationDataclass:
    def test_default_values(self):
        obs = Observation(agent_id="test", step=1)
        assert obs.agent_id == "test"
        assert obs.step == 1
        assert obs.db_status == "unknown"
        assert obs.ai_status == "unknown"
        assert obs.environment_changed is False
        assert obs.changed_fields == []

    def test_to_dict(self):
        obs = Observation(agent_id="test", step=1, db_status="ok")
        d = obs.to_dict()
        assert d["agent_id"] == "test"
        assert d["db_status"] == "ok"
        assert "timestamp" in d

    def test_to_json(self):
        obs = Observation(agent_id="test", step=1)
        j = obs.to_json()
        assert '"agent_id": "test"' in j


class TestCustomObserver:
    def test_custom_observer(self):
        class MyObserver(BaseObserver):
            name = "my_observer"
            def observe(self, context=None):
                return {"status": "ok", "value": 42}

        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        layer.register_observer(MyObserver())
        obs = layer.observe(step=0)
        assert obs.extra["my_observer"]["value"] == 42

    def test_unregister_observer(self):
        class MyObserver(BaseObserver):
            name = "temp_observer"
            def observe(self, context=None):
                return {"value": 1}

        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        layer.register_observer(MyObserver())
        layer.unregister_observer("temp_observer")
        obs = layer.observe(step=0)
        assert "temp_observer" not in obs.extra


class TestDBStatusObserver:
    def test_injected_query_func(self):
        observer = DBStatusObserver(query_func=lambda: {"status": "ok", "tables": {"notes": 100}})
        result = observer.observe()
        assert result["status"] == "ok"
        assert result["tables"]["notes"] == 100

    def test_db_unavailable(self):
        observer = DBStatusObserver(db_path="/nonexistent/path.db")
        result = observer.observe()
        assert result["status"] == "unavailable"


class TestAIStatusObserver:
    def test_injected_health_func(self):
        observer = AIStatusObserver(health_func=lambda: {
            "status": "ok", "provider": "zhipu", "circuit_state": "CLOSED"
        })
        result = observer.observe()
        assert result["status"] == "ok"
        assert result["provider"] == "zhipu"
        assert result["circuit_state"] == "CLOSED"


class TestToolStatusObserver:
    def test_injected_registry_func(self):
        observer = ToolStatusObserver(tool_registry_func=lambda: {
            "tools": {"skill_1": "available", "skill_2": "unavailable"}
        })
        result = observer.observe()
        assert result["tools"]["skill_1"] == "available"


class TestCollectionStatusObserver:
    def test_injected_func(self):
        observer = CollectionStatusObserver(collection_func=lambda: {
            "status": "running", "stats": {"last_hour_count": 50}
        })
        result = observer.observe()
        assert result["status"] == "running"
        assert result["stats"]["last_hour_count"] == 50


class TestObservationLayer:
    def test_observe_with_previous_result(self):
        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        obs = layer.observe(
            step=1,
            previous_result={"output": "data"},
            previous_error=None,
            previous_duration_ms=150.5,
        )
        assert obs.previous_step_result == {"output": "data"}
        assert obs.previous_step_duration_ms == 150.5
        assert obs.previous_step_error is None

    def test_observe_with_error(self):
        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        obs = layer.observe(step=2, previous_error="timeout")
        assert obs.previous_step_error == "timeout"

    def test_environment_change_detection(self):
        """测试环境变化检测：两次观察状态不同时标记 changed。"""
        class VariableObserver(BaseObserver):
            name = "db_status"
            def __init__(self):
                self.call_count = 0
            def observe(self, context=None):
                self.call_count += 1
                status = "ok" if self.call_count == 1 else "degraded"
                return {"status": status, "tables": {}}

        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        observer = VariableObserver()
        layer.register_observer(observer)

        obs1 = layer.observe(step=0)
        assert obs1.db_status == "ok"
        assert obs1.environment_changed is False

        obs2 = layer.observe(step=1)
        assert obs2.db_status == "degraded"
        assert obs2.environment_changed is True
        assert "db_status" in obs2.changed_fields

    def test_no_environment_change(self):
        class StableObserver(BaseObserver):
            name = "db_status"
            def observe(self, context=None):
                return {"status": "ok", "tables": {}}

        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        layer.register_observer(StableObserver())
        layer.observe(step=0)
        obs2 = layer.observe(step=1)
        assert obs2.environment_changed is False

    def test_get_last_observation(self):
        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        assert layer.get_last_observation() is None
        layer.observe(step=0)
        assert layer.get_last_observation() is not None
        assert layer.get_last_observation().step == 0

    def test_reset(self):
        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        layer.observe(step=0)
        layer.reset()
        assert layer.get_last_observation() is None

    def test_observer_exception_handled(self):
        class BadObserver(BaseObserver):
            name = "bad_observer"
            def observe(self, context=None):
                raise RuntimeError("observer failed")

        layer = ObservationLayer(agent_id="test", auto_register_default=False)
        layer.register_observer(BadObserver())
        # 不应抛出异常
        obs = layer.observe(step=0)
        assert "bad_observer_error" in obs.extra

    def test_multiple_observers(self):
        class O1(BaseObserver):
            name = "o1"
            def observe(self, context=None):
                return {"v": 1}
        class O2(BaseObserver):
            name = "o2"
            def observe(self, context=None):
                return {"v": 2}

        layer = ObservationLayer(agent_id="test", observers=[O1(), O2()], auto_register_default=False)
        obs = layer.observe(step=0)
        assert obs.extra["o1"]["v"] == 1
        assert obs.extra["o2"]["v"] == 2
