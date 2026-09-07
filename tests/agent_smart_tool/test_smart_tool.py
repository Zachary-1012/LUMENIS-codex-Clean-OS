# -*- coding: utf-8 -*-
"""
agent_smart_tool 测试用例
===========================
覆盖：参数校验通过、参数缺失自动补默认、参数类型错误自动纠错、
执行成功、执行失败重试、不可重试异常、自描述输出、与ToolDefinition兼容。
"""
import pytest

from agent_smart_tool import (
    SmartTool,
    wrap_tool,
    ToolExecutionResult,
    SmartToolRegistry,
    from_tool_definition,
    RetryPolicy,
    ParamCorrector,
    NO_RETRY_POLICY,
)


# ── 测试用工具 ─────────────────────────────────────────────────

class _AddTool(SmartTool):
    """简单加法工具，用于测试。"""
    tool_id = "test_add"
    name = "加法工具"
    description = "将两个数相加"
    params = [
        {"name": "a", "type": "integer", "required": True, "default": None, "enum": []},
        {"name": "b", "type": "integer", "required": False, "default": 10, "enum": []},
    ]
    permission_level = "read"
    risk_level = "LOW"

    def _run(self, params):
        return params.get("a", 0) + params.get("b", 0)


class _FailingTool(SmartTool):
    """总是失败的工具，用于测试重试。"""
    tool_id = "test_fail"
    name = "失败工具"
    description = "总是抛出 ConnectionError"
    params = []
    call_count = 0

    def _run(self, params):
        type(self).call_count += 1
        raise ConnectionError("simulated connection failure")


class _ValueErrorTool(SmartTool):
    """抛出不可重试异常的工具。"""
    tool_id = "test_value_error"
    name = "值错误工具"
    description = "总是抛出 ValueError"
    params = []

    def _run(self, params):
        raise ValueError("invalid value")


# ── 1. 参数校验通过 ────────────────────────────────────────────

class TestParamValidationPass:
    """合法参数应校验通过。"""

    def test_valid_params_no_errors(self):
        tool = _AddTool()
        corrected, changes, errors = tool.validate_params({"a": 5, "b": 3})
        assert errors == []
        assert corrected == {"a": 5, "b": 3}

    def test_valid_params_only_required(self):
        tool = _AddTool()
        corrected, changes, errors = tool.validate_params({"a": 5})
        assert errors == []
        # b 应被填充默认值 10
        assert corrected["b"] == 10
        assert len(changes) == 1
        assert changes[0]["action"] == "fill_default"

    def test_empty_params_for_no_param_tool(self):
        tool = _FailingTool(retry_policy=NO_RETRY_POLICY)
        corrected, changes, errors = tool.validate_params({})
        assert errors == []


# ── 2. 参数缺失自动补默认 ──────────────────────────────────────

class TestParamDefaultFill:
    """缺失的可选参数应自动填充默认值。"""

    def test_fill_optional_default(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "x", "type": "integer", "required": False, "default": 42, "enum": []},
        ])
        corrected, changes = corrector.correct({})
        assert corrected["x"] == 42
        assert changes[0]["action"] == "fill_default"

    def test_required_not_filled(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "x", "type": "integer", "required": True, "default": None, "enum": []},
        ])
        corrected, changes = corrector.correct({})
        assert "x" not in corrected
        assert changes == []

    def test_no_default_no_fill(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "x", "type": "string", "required": False, "default": None, "enum": []},
        ])
        corrected, changes = corrector.correct({})
        assert "x" not in corrected

    def test_execute_fills_default(self):
        tool = _AddTool()
        result = tool.execute({"a": 5})  # b 缺失
        assert result.success is True
        assert result.data == 15  # 5 + 10(default)
        assert result.corrected_params is not None
        assert result.corrected_params["b"] == 10


# ── 3. 参数类型错误自动纠错 ────────────────────────────────────

class TestParamTypeCoercion:
    """类型不匹配且可转换时应自动纠错。"""

    def test_string_to_int(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "x", "type": "integer", "required": True, "default": None, "enum": []},
        ])
        corrected, changes = corrector.correct({"x": "42"})
        assert corrected["x"] == 42
        assert changes[0]["action"] == "type_coerce"

    def test_string_to_bool_true(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "flag", "type": "boolean", "required": False, "default": False, "enum": []},
        ])
        corrected, _ = corrector.correct({"flag": "yes"})
        assert corrected["flag"] is True

    def test_string_to_bool_false(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "flag", "type": "boolean", "required": False, "default": True, "enum": []},
        ])
        corrected, _ = corrector.correct({"flag": "no"})
        assert corrected["flag"] is False

    def test_int_to_string(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "name", "type": "string", "required": True, "default": None, "enum": []},
        ])
        corrected, changes = corrector.correct({"name": 123})
        assert corrected["name"] == "123"
        assert changes[0]["action"] == "type_coerce"

    def test_uncoercible_unchanged(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "x", "type": "integer", "required": True, "default": None, "enum": []},
        ])
        corrected, changes = corrector.correct({"x": "not_a_number"})
        assert corrected["x"] == "not_a_number"  # 转换失败，保持原值
        # 由 validate 报错

    def test_execute_with_type_coercion(self):
        tool = _AddTool()
        result = tool.execute({"a": "5", "b": "3"})  # 字符串应转为 int
        assert result.success is True
        assert result.data == 8


# ── 4. 执行成功 ─────────────────────────────────────────────────

class TestExecutionSuccess:
    """工具执行成功应返回正确结果。"""

    def test_basic_execution(self):
        tool = _AddTool()
        result = tool.execute({"a": 3, "b": 4})
        assert isinstance(result, ToolExecutionResult)
        assert result.success is True
        assert result.data == 7
        assert result.error is None
        assert result.retries == 0
        assert result.duration_ms >= 0

    def test_execution_with_call_syntax(self):
        tool = _AddTool()
        result = tool(a=10, b=20)
        assert result.success is True
        assert result.data == 30

    def test_execution_id_unique(self):
        tool = _AddTool()
        r1 = tool.execute({"a": 1})
        r2 = tool.execute({"a": 2})
        assert r1.execution_id != r2.execution_id

    def test_execution_evidence(self):
        tool = _AddTool()
        result = tool.execute({"a": 1, "b": 2})
        assert "validation" in result.evidence
        assert "security_gates" in result.evidence
        assert "execution" in result.evidence
        assert result.evidence["execution"]["attempts"][0]["success"] is True

    def test_last_result(self):
        tool = _AddTool()
        assert tool.last_result is None
        tool.execute({"a": 1})
        assert tool.last_result is not None
        assert tool.last_result.success is True

    def test_to_dict(self):
        tool = _AddTool()
        result = tool.execute({"a": 1, "b": 2})
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"] == 3
        assert "execution_id" in d


# ── 5. 执行失败重试 ─────────────────────────────────────────────

class TestExecutionRetry:
    """可重试异常应自动重试。"""

    def test_retry_on_connection_error(self):
        _FailingTool.call_count = 0
        policy = RetryPolicy(max_retries=2, backoff_seconds=0.01)
        tool = _FailingTool(retry_policy=policy)
        result = tool.execute({})
        assert result.success is False
        assert result.retries == 2
        assert _FailingTool.call_count == 3  # 1 首次 + 2 重试
        assert "ConnectionError" in result.error

    def test_retry_evidence(self):
        _FailingTool.call_count = 0
        policy = RetryPolicy(max_retries=1, backoff_seconds=0.01)
        tool = _FailingTool(retry_policy=policy)
        result = tool.execute({})
        attempts = result.evidence["execution"]["attempts"]
        assert len(attempts) == 2
        assert attempts[0]["success"] is False
        assert attempts[1]["success"] is False

    def test_retry_policy_is_retryable(self):
        policy = RetryPolicy()
        assert policy.is_retryable(ConnectionError()) is True
        assert policy.is_retryable(TimeoutError()) is True
        assert policy.is_retryable(ValueError()) is False
        assert policy.is_retryable(TypeError()) is False

    def test_retry_backoff(self):
        policy = RetryPolicy(backoff_seconds=0.5, max_backoff_seconds=10)
        assert policy.backoff_for_attempt(1) == 0.5
        assert policy.backoff_for_attempt(2) == 1.0
        assert policy.backoff_for_attempt(3) == 2.0
        assert policy.backoff_for_attempt(10) == 10.0  # 上限


# ── 6. 不可重试异常 ─────────────────────────────────────────────

class TestNonRetryableException:
    """不可重试异常应立即失败，不重试。"""

    def test_value_error_no_retry(self):
        tool = _ValueErrorTool(retry_policy=RetryPolicy(max_retries=3, backoff_seconds=0.01))
        result = tool.execute({})
        assert result.success is False
        assert result.retries == 0
        assert "ValueError" in result.error

    def test_no_retry_policy(self):
        _FailingTool.call_count = 0
        tool = _FailingTool(retry_policy=NO_RETRY_POLICY)
        result = tool.execute({})
        assert result.retries == 0
        assert _FailingTool.call_count == 1

    def test_param_validation_error_no_retry(self):
        tool = _AddTool()
        # 缺少必填参数 a
        result = tool.execute({})
        assert result.success is False
        assert result.retries == 0
        assert "parameter validation failed" in result.error


# ── 7. 自描述输出 ───────────────────────────────────────────────

class TestSelfDescribe:
    """self_describe() 应返回 ToolDefinition 兼容 dict。"""

    def test_self_describe_fields(self):
        tool = _AddTool()
        desc = tool.self_describe()
        assert desc["tool_id"] == "test_add"
        assert desc["name"] == "加法工具"
        assert desc["description"] == "将两个数相加"
        assert desc["category"] == "general"
        assert desc["permission_level"] == "read"
        assert desc["risk_level"] == "LOW"
        assert desc["enabled"] is True
        assert desc["version"] == "1.0.0"
        assert len(desc["params"]) == 2

    def test_self_describe_param_schema(self):
        tool = _AddTool()
        desc = tool.self_describe()
        param_a = desc["params"][0]
        assert param_a["name"] == "a"
        assert param_a["type"] == "integer"
        assert param_a["required"] is True

    def test_wrap_tool_self_describe(self):
        @wrap_tool
        def greet(name: str = "world", count: int = 1):
            """问候函数"""
            return f"Hello {name}" * count
        desc = greet.self_describe()
        assert desc["tool_id"] == "greet"
        assert desc["name"] == "greet"
        assert "问候函数" in desc["description"]
        param_names = [p["name"] for p in desc["params"]]
        assert "name" in param_names
        assert "count" in param_names


# ── 8. 与 ToolDefinition 兼容 ───────────────────────────────────

class TestToolDefinitionCompatibility:
    """from_tool_definition 应能从 ToolDefinition 兼容结构构建 SmartTool。"""

    def test_from_dict_definition(self):
        tool_def = {
            "tool_id": "dict_tool",
            "name": "字典工具",
            "description": "从 dict 构建",
            "params": [
                {"name": "x", "type": "integer", "required": True, "default": None, "enum": []},
            ],
            "permission_level": "read",
            "risk_level": "LOW",
            "api_route": "/api/test",
        }
        tool = from_tool_definition(tool_def, handler=lambda p: p["x"] * 2)
        assert tool.tool_id == "dict_tool"
        result = tool.execute({"x": 5})
        assert result.success is True
        assert result.data == 10

    def test_from_tool_definition_no_handler(self):
        """无 handler 时应返回 api_route 信息而非崩溃。"""
        tool_def = {
            "tool_id": "no_handler",
            "name": "无handler",
            "description": "测试",
            "params": [],
            "api_route": "/api/external",
        }
        tool = from_tool_definition(tool_def)
        result = tool.execute({})
        assert result.success is True
        assert result.data["api_route"] == "/api/external"
        assert "no handler" in result.data["note"]

    def test_from_tool_definition_with_enum_objects(self):
        """模拟带枚举值的 ToolParam 对象。"""
        class FakeParam:
            def __init__(self, name, type, required, default, enum):
                self.name = name
                self.type = type
                self.required = required
                self.default = default
                self.enum = enum

        class FakeToolDef:
            tool_id = "fake_tool"
            name = "模拟工具"
            description = "模拟 ToolDefinition"
            category = "test"
            keywords = ["test"]
            params = [FakeParam("mode", "string", False, "a", ["a", "b", "c"])]
            permission_level = "read"
            risk_level = "LOW"
            requires_approval = False
            api_route = ""
            version = "1.0.0"
            handler = None

        tool = from_tool_definition(FakeToolDef(), handler=lambda p: p.get("mode", "a"))
        result = tool.execute({"mode": "b"})
        assert result.success is True
        assert result.data == "b"

    def test_self_describe_matches_tool_definition_contract(self):
        """self_describe 输出应包含 ToolDefinition.to_dict() 的所有关键字段。"""
        tool = _AddTool()
        desc = tool.self_describe()
        required_fields = ["tool_id", "name", "description", "category", "keywords",
                           "params", "permission_level", "risk_level", "requires_approval",
                           "api_route", "enabled", "version"]
        for field_name in required_fields:
            assert field_name in desc, f"missing field: {field_name}"


# ── 9. wrap_tool 装饰器 ─────────────────────────────────────────

class TestWrapTool:
    """wrap_tool 装饰器测试。"""

    def test_basic_wrap(self):
        @wrap_tool
        def multiply(x: int, y: int = 2):
            return x * y
        result = multiply.execute({"x": 5})
        assert result.success is True
        assert result.data == 10

    def test_wrap_with_params(self):
        @wrap_tool(tool_id="custom_id", name="自定义工具")
        def do_something(x: int = 0):
            return x + 1
        assert do_something.tool_id == "custom_id"
        assert do_something.name == "自定义工具"
        result = do_something.execute({"x": 5})
        assert result.data == 6

    def test_wrap_type_coercion(self):
        @wrap_tool
        def add_one(x: int = 0):
            return x + 1
        result = add_one.execute({"x": "41"})
        assert result.success is True
        assert result.data == 42

    def test_wrap_retry(self):
        call_count = {"n": 0}

        @wrap_tool(retry_policy=RetryPolicy(max_retries=2, backoff_seconds=0.01))
        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("fail")
            return "success"

        result = flaky.execute({})
        assert result.success is True
        assert result.data == "success"
        assert result.retries == 2
        assert call_count["n"] == 3

    def test_wrap_docstring_as_description(self):
        @wrap_tool
        def documented():
            """这是一个有文档的函数。"""
            return True
        assert "这是一个有文档的函数" in documented.description


# ── 10. SmartToolRegistry ───────────────────────────────────────

class TestSmartToolRegistry:
    """注册表测试。"""

    def test_register_and_get(self):
        registry = SmartToolRegistry()
        tool = _AddTool()
        registry.register(tool)
        assert registry.has("test_add")
        retrieved = registry.get("test_add")
        assert retrieved is tool

    def test_unregister(self):
        registry = SmartToolRegistry()
        tool = _AddTool()
        registry.register(tool)
        registry.unregister("test_add")
        assert not registry.has("test_add")
        assert registry.get("test_add") is None

    def test_list_tools(self):
        registry = SmartToolRegistry()
        registry.register(_AddTool())
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["tool_id"] == "test_add"

    def test_list_ids(self):
        registry = SmartToolRegistry()
        registry.register(_AddTool())
        assert registry.list_ids() == ["test_add"]

    def test_execute_via_registry(self):
        registry = SmartToolRegistry()
        registry.register(_AddTool())
        result = registry.execute("test_add", {"a": 3, "b": 4})
        assert result.success is True
        assert result.data == 7

    def test_execute_unknown_tool(self):
        registry = SmartToolRegistry()
        result = registry.execute("nonexistent", {})
        assert result.success is False
        assert "not found" in result.error

    def test_len_and_contains(self):
        registry = SmartToolRegistry()
        assert len(registry) == 0
        registry.register(_AddTool())
        assert len(registry) == 1
        assert "test_add" in registry

    def test_register_non_smart_tool_raises(self):
        registry = SmartToolRegistry()
        with pytest.raises(TypeError):
            registry.register("not a tool")


# ── 11. ParamCorrector 进阶 ─────────────────────────────────────

class TestParamCorrectorAdvanced:
    """ParamCorrector 进阶测试。"""

    def test_from_function(self):
        def sample(x: int, y: str = "hello", z: float = 1.5):
            pass
        corrector = ParamCorrector.from_function(sample)
        names = [p["name"] for p in corrector.param_schemas]
        assert names == ["x", "y", "z"]
        assert corrector.param_schemas[0]["required"] is True
        assert corrector.param_schemas[1]["required"] is False
        assert corrector.param_schemas[1]["default"] == "hello"

    def test_enum_validation(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "mode", "type": "string", "required": True, "default": None, "enum": ["a", "b"]},
        ])
        ok, errors = corrector.validate({"mode": "c"})
        assert ok is False
        assert len(errors) == 1

    def test_enum_not_auto_corrected(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "mode", "type": "string", "required": False, "default": "a", "enum": ["a", "b"]},
        ])
        corrected, changes = corrector.correct({"mode": "c"})
        assert corrected["mode"] == "c"  # 不自动纠错
        assert any(c["action"] == "enum_mismatch" for c in changes)

    def test_validate_missing_required(self):
        corrector = ParamCorrector(param_schemas=[
            {"name": "x", "type": "integer", "required": True, "default": None, "enum": []},
        ])
        ok, errors = corrector.validate({})
        assert ok is False
        assert "missing required param: x" in errors[0]

    def test_non_dict_params(self):
        corrector = ParamCorrector(param_schemas=[])
        corrected, changes = corrector.correct("not a dict")
        assert corrected == {}
        ok, errors = corrector.validate("not a dict")
        assert ok is False


# ── 12. 安全网关（降级模式） ────────────────────────────────────

class TestSecurityGatesFallback:
    """安全网关不存在时应仅记录，不阻断。"""

    def test_gates_recorded_in_evidence(self):
        tool = _AddTool(use_security_gates=True)
        result = tool.execute({"a": 1, "b": 2})
        assert "security_gates" in result.evidence
        # 网关可用性信息应被记录
        assert "permission_gate_available" in result.evidence["security_gates"]
        assert "execution_chain_available" in result.evidence["security_gates"]

    def test_disabled_gates(self):
        tool = _AddTool(use_security_gates=False)
        result = tool.execute({"a": 1, "b": 2})
        assert result.success is True
        assert result.evidence["security_gates"]["checks"].get("skipped") == "use_security_gates=False"

    def test_gates_dont_block_when_unavailable(self):
        """网关模块不存在时，工具应正常执行（仅记录）。"""
        tool = _AddTool()
        result = tool.execute({"a": 5, "b": 5})
        assert result.success is True
        assert result.data == 10
