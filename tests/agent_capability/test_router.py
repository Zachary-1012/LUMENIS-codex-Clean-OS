# -*- coding: utf-8 -*-
"""Capability Router 单元测试 — 真实操作，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_capability.router import (
    CapabilityRouter, ToolDefinition, ToolParam, ToolRiskLevel,
    ToolPermissionLevel, ToolExecutionResult, ToolActorContext, CORE_TOOLS,
)


class TestToolDefinition:
    def test_validate_params_required(self):
        tool = ToolDefinition(
            tool_id="test", name="test", description="test",
            params=[ToolParam("q", "string", True, "query")],
        )
        ok, msg = tool.validate_params({})
        assert ok is False
        assert "missing required param: q" in msg

    def test_validate_params_enum(self):
        tool = ToolDefinition(
            tool_id="test", name="test", description="test",
            params=[ToolParam("type", "string", False, "", "a", ["a", "b"])],
        )
        ok, _ = tool.validate_params({"type": "c"})
        assert ok is False
        ok, _ = tool.validate_params({"type": "a"})
        assert ok is True

    def test_validate_params_ok(self):
        tool = ToolDefinition(
            tool_id="test", name="test", description="test",
            params=[ToolParam("q", "string", True)],
        )
        ok, msg = tool.validate_params({"q": "hello"})
        assert ok is True

    def test_to_dict(self):
        tool = ToolDefinition(
            tool_id="test", name="test", description="test",
            risk_level=ToolRiskLevel.HIGH,
            permission_level=ToolPermissionLevel.WRITE,
            requires_approval=True,
        )
        d = tool.to_dict()
        assert d["tool_id"] == "test"
        assert d["risk_level"] == "HIGH"
        assert d["permission_level"] == "write"
        assert d["requires_approval"] is True
        assert "handler" not in d


class TestCapabilityRouter:
    def test_core_tools_registered(self):
        router = CapabilityRouter(enabled=True)
        tools = router.list_tools()
        assert len(tools) == 12
        tool_ids = [t.tool_id for t in tools]
        assert "note_search" in tool_ids
        assert "event_query" in tool_ids
        assert "collection_trigger" in tool_ids
        assert "report_generate" in tool_ids
        assert "ai_analyze" in tool_ids

    def test_register_tool(self):
        router = CapabilityRouter(enabled=True)
        new_tool = ToolDefinition(
            tool_id="custom_tool", name="自定义", description="测试",
        )
        assert router.register_tool(new_tool) is True
        assert router.get_tool("custom_tool") is not None

    def test_unregister_tool(self):
        router = CapabilityRouter(enabled=True)
        assert router.unregister_tool("note_search") is True
        assert router.get_tool("note_search") is None

    def test_list_tools_by_category(self):
        router = CapabilityRouter(enabled=True)
        monitor_tools = router.list_tools(category="monitor")
        assert len(monitor_tools) == 1
        assert monitor_tools[0].tool_id == "note_search"

    def test_list_tools_by_risk(self):
        router = CapabilityRouter(enabled=True)
        high_risk = router.list_tools(risk_level=ToolRiskLevel.HIGH)
        assert len(high_risk) >= 1
        assert all(t.risk_level == ToolRiskLevel.HIGH for t in high_risk)

    def test_select_tool_note_search(self):
        router = CapabilityRouter(enabled=True)
        tool = router.select_tool("搜索小红书笔记关于排队的内容")
        assert tool is not None
        assert tool.tool_id == "note_search"

    def test_select_tool_event_query(self):
        router = CapabilityRouter(enabled=True)
        tool = router.select_tool("查询最近的舆情事件")
        assert tool is not None
        assert tool.tool_id == "event_query"

    def test_select_tool_collection_trigger(self):
        router = CapabilityRouter(enabled=True)
        tool = router.select_tool("触发小红书采集任务")
        assert tool is not None
        assert tool.tool_id == "collection_trigger"

    def test_select_tool_report_generate(self):
        router = CapabilityRouter(enabled=True)
        tool = router.select_tool("生成今日舆情日报")
        assert tool is not None
        assert tool.tool_id == "report_generate"

    def test_select_tool_no_match(self):
        router = CapabilityRouter(enabled=True)
        tool = router.select_tool("zzz_nonexistent_xyz_123")
        assert tool is None

    def test_select_tools_top_n(self):
        router = CapabilityRouter(enabled=True)
        tools = router.select_tools("分析舆情趋势和风险", limit=3)
        assert len(tools) <= 3
        assert len(tools) >= 1

    def test_execute_tool_not_found(self):
        router = CapabilityRouter(enabled=True)
        result = router.execute_tool("nonexistent", {})
        assert result.success is False
        assert "not found" in result.error

    def test_execute_tool_param_validation(self):
        router = CapabilityRouter(enabled=True)
        # note_search 需要 query 参数
        result = router.execute_tool("note_search", {})
        assert result.success is False
        assert "missing required param" in result.error

    def test_execute_tool_with_handler(self):
        router = CapabilityRouter(
            enabled=True,
            actor_authorizer=lambda actor, tool: actor.user_id == 7 and tool.tool_id == "handler_test",
        )
        # 注册一个带 handler 的 tool
        def mock_handler(query="", limit=10):
            return {"results": [{"id": 1, "title": query}]}
        tool = ToolDefinition(
            tool_id="handler_test", name="测试", description="test",
            params=[ToolParam("query", "string", True)],
            handler=mock_handler,
        )
        router.register_tool(tool)
        actor = ToolActorContext(7, "user", "CTH", "cth", "cth_analyst")
        result = router.execute_tool("handler_test", {"query": "hello"}, actor_context=actor)
        assert result.success is True
        assert result.data["results"][0]["title"] == "hello"

    def test_execution_fails_closed_without_trusted_actor(self):
        router = CapabilityRouter(enabled=True)
        called = []
        router.register_tool(ToolDefinition(
            tool_id="actor_required", name="actor required", description="test",
            params=[], handler=lambda: called.append(True),
        ))
        result = router.execute_tool("actor_required", {})
        assert result.success is False
        assert result.error == "trusted actor context required"
        assert called == []

    def test_execution_fails_closed_without_server_actor_authorizer(self):
        router = CapabilityRouter(enabled=True)
        called = []
        router.register_tool(ToolDefinition(
            tool_id="actor_authorizer_required", name="actor authorization required",
            description="test", params=[], handler=lambda: called.append(True),
        ))
        actor = ToolActorContext(7, "user", "CTH", "cth", "cth_analyst")

        result = router.execute_tool("actor_authorizer_required", {}, actor_context=actor)

        assert result.success is False
        assert result.error == "trusted actor authorization validator not configured"
        assert called == []

    def test_execution_scope_comes_from_actor_not_tool_params(self, monkeypatch):
        import lumenis.shared.agents.skills.execution as execution

        captured = {}
        monkeypatch.setattr(execution, "check_permission", lambda ctx, user_role="user": (
            captured.setdefault("ctx", ctx) and {"allowed": True, "reason": "test"}
        ))
        monkeypatch.setattr(execution, "action_firewall", lambda ctx: {"allowed": True})
        monkeypatch.setattr(execution, "effect_fence", lambda ctx: {"allowed": True})
        monkeypatch.setattr(execution, "execute_skill", lambda ctx, handler=None: {
            "success": True, "result": {"ok": True}
        })
        monkeypatch.setattr(execution, "build_evidence", lambda ctx: {"ok": True})
        monkeypatch.setattr(execution, "evaluate_execution", lambda ctx: {"status": "ok"})
        monkeypatch.setattr(execution, "write_trace", lambda *args, **kwargs: None)

        router = CapabilityRouter(
            enabled=True,
            actor_authorizer=lambda actor, tool: actor.user_id == 9 and tool.tool_id == "scoped_tool",
        )
        router.register_tool(ToolDefinition(
            tool_id="scoped_tool", name="scoped", description="test",
            params=[], handler=lambda **kwargs: {"ok": True},
        ))
        actor = ToolActorContext(9, "user", "BMP", "zbmp", "zbmp_analyst")
        result = router.execute_tool(
            "scoped_tool",
            {"domain": "cth", "product": "CTH", "user_id": 1},
            actor_context=actor,
        )
        assert result.success is True
        ctx = captured["ctx"]
        assert (ctx.user_id, ctx.domain, ctx.product, ctx.permission_role) == (
            9, "zbmp", "BMP", "zbmp_analyst"
        )

    def test_execute_tool_disabled_router(self):
        router = CapabilityRouter(enabled=False)
        result = router.execute_tool("note_search", {"query": "test"})
        assert result.success is False
        assert "disabled" in result.error

    def test_high_risk_tool_requires_approval(self):
        router = CapabilityRouter(enabled=True)
        tool = router.get_tool("collection_trigger")
        assert tool.requires_approval is True
        assert tool.risk_level == ToolRiskLevel.HIGH
        assert tool.permission_level == ToolPermissionLevel.WRITE

    def test_stats(self):
        router = CapabilityRouter(enabled=True)
        s = router.stats()
        assert s["registered_tools"] == 12
        assert "tools_by_category" in s
        assert "tools_by_risk" in s
        assert s["tools_by_risk"]["LOW"] >= 5

    def test_core_tools_have_categories(self):
        categories = set(t.category for t in CORE_TOOLS)
        assert "monitor" in categories
        assert "events" in categories
        assert "analysis" in categories
        assert "risk" in categories
        assert "collection" in categories
        assert "reports" in categories
        assert "ai" in categories
        assert "system" in categories
