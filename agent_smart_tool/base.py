# -*- coding: utf-8 -*-
"""
Smart Tool Base — 智能工具化核心模块
======================================
将复杂 Tool 包装成自解释、自校验、自恢复的小型执行单元。

核心能力：
  - self_describe()  : 自解释，返回 ToolDefinition 兼容 dict
  - validate_params() : 自校验，自动纠错可纠错参数
  - execute()         : 执行 + 异常捕获 + 自动重试
  - recover()         : 自恢复策略

与现有 Skill → Tool → Firewall → Effect Fence 兼容：
  - 执行时如检测到 permission_gate / action_firewall / effect_fence 存在则调用
  - 不存在则仅记录到 evidence，不绕过
  - 与 agent_capability.router.ToolDefinition 兼容（可从 ToolDefinition 构建 SmartTool）

设计原则：
  - 所有行为可解释、可追踪（每个执行结果带 evidence 字段）
  - 不改变 ZBC Production Truth
  - 不写任何 API Key 到代码
  - 纯 Python 实现，无外部依赖
  - 代码风格与现有 agent_runtime 一致
"""
from __future__ import annotations

import functools
import inspect
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from .recovery import (
    RetryPolicy,
    ParamCorrector,
    DEFAULT_RETRY_POLICY,
    NO_RETRY_POLICY,
)

# 尝试导入现有安全网关（不存在则降级为仅记录）
try:
    from permission_gate import get_permission_gate as _get_permission_gate
    _HAS_PERMISSION_GATE = True
except Exception:
    _get_permission_gate = None  # type: ignore
    _HAS_PERMISSION_GATE = False

try:
    from skill_execution_chain import action_firewall as _action_firewall, effect_fence as _effect_fence
    _HAS_EXECUTION_CHAIN = True
except Exception:
    _action_firewall = None  # type: ignore
    _effect_fence = None  # type: ignore
    _HAS_EXECUTION_CHAIN = False


# ─────────────────────────────────────────────────────────────
# ToolExecutionResult — 执行结果
# ─────────────────────────────────────────────────────────────

@dataclass
class ToolExecutionResult:
    """SmartTool 执行结果（带 evidence 可追溯）。

    Attributes:
        success: 是否成功
        data: 执行返回数据
        error: 错误信息（失败时）
        retries: 实际重试次数
        corrected_params: 纠错后的参数（None 表示未纠错）
        duration_ms: 执行耗时（毫秒）
        evidence: 证据链（可解释、可追溯）
        execution_id: 执行唯一标识
        tool_id: 工具标识
        timestamp: 执行时间（ISO 8601 UTC）
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    retries: int = 0
    corrected_params: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    execution_id: str = field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    tool_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。"""
        return asdict(self)

    @property
    def has_corrections(self) -> bool:
        """是否发生了参数纠错。"""
        return self.corrected_params is not None and bool(self.evidence.get("param_changes"))


# ─────────────────────────────────────────────────────────────
# SmartTool — 智能工具基类
# ─────────────────────────────────────────────────────────────

class SmartTool:
    """智能工具基类：自解释、自校验、自恢复。

    子类需实现 _run(params) 方法执行实际逻辑。
    或使用 wrap_tool() 装饰器将普通函数包装为 SmartTool。

    用法（子类）：
        class MyTool(SmartTool):
            tool_id = "my_tool"
            name = "我的工具"
            description = "示例工具"
            def _run(self, params):
                return {"result": params.get("x", 0) * 2}

    用法（装饰器）：
        @wrap_tool
        def my_tool(x: int = 10):
            return x * 2
    """

    # 子类覆盖这些属性
    tool_id: str = ""
    name: str = ""
    description: str = ""
    category: str = "general"
    keywords: List[str] = field(default_factory=list)
    params: List[Dict[str, Any]] = field(default_factory=list)
    permission_level: str = "read"
    risk_level: str = "LOW"
    requires_approval: bool = False
    api_route: str = ""
    version: str = "1.0.0"

    def __init__(
        self,
        retry_policy: Optional[RetryPolicy] = None,
        param_corrector: Optional[ParamCorrector] = None,
        use_security_gates: bool = True,
    ):
        """
        Args:
            retry_policy: 重试策略（None 则使用默认）
            param_corrector: 参数纠错器（None 则从 self.params 自动构建）
            use_security_gates: 是否启用 permission/firewall/fence 网关
        """
        self._retry_policy = retry_policy or DEFAULT_RETRY_POLICY
        self._param_corrector = param_corrector or ParamCorrector.from_param_list(
            self.params if isinstance(self.params, list) else []
        )
        self._use_security_gates = use_security_gates
        self._last_result: Optional[ToolExecutionResult] = None

    @property
    def last_result(self) -> Optional[ToolExecutionResult]:
        """获取上一次执行结果。"""
        return self._last_result

    # ── 自解释 ──────────────────────────────────────────────

    def self_describe(self) -> Dict[str, Any]:
        """自解释：返回 ToolDefinition 兼容 dict。

        Returns:
            与 agent_capability.router.ToolDefinition.to_dict() 兼容的字典
        """
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "keywords": list(self.keywords) if isinstance(self.keywords, list) else [],
            "params": list(self.params) if isinstance(self.params, list) else [],
            "permission_level": self.permission_level,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "api_route": self.api_route,
            "enabled": True,
            "version": self.version,
        }

    # ── 自校验 ──────────────────────────────────────────────

    def validate_params(
        self, params: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
        """自校验参数，自动纠错可纠错参数。

        Args:
            params: 输入参数字典

        Returns:
            (corrected_params, param_changes, validation_errors)
            - corrected_params: 纠错后的参数
            - param_changes: 纠错变更记录
            - validation_errors: 不可纠错的校验错误（空列表表示通过）
        """
        if not isinstance(params, dict):
            return {}, [], ["params is not a dict"]
        # 先纠错
        corrected, changes = self._param_corrector.correct(params)
        # 再校验
        ok, errors = self._param_corrector.validate(corrected)
        # enum_mismatch 的变更也应视为错误
        for change in changes:
            if change.get("action") == "enum_mismatch":
                errors.append(
                    f"param {change['param']}={change['old']!r} not in enum, not auto-corrected"
                )
        return corrected, changes, errors

    # ── 安全网关 ────────────────────────────────────────────

    def _check_security_gates(
        self, params: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """检查 permission_gate / action_firewall / effect_fence。

        存在则调用，不存在则仅记录。

        Returns:
            (allowed, reason, gate_evidence)
        """
        gate_evidence: Dict[str, Any] = {
            "permission_gate_available": _HAS_PERMISSION_GATE,
            "execution_chain_available": _HAS_EXECUTION_CHAIN,
            "checks": {},
        }

        if not self._use_security_gates:
            gate_evidence["checks"]["skipped"] = "use_security_gates=False"
            return True, "security gates disabled by config", gate_evidence

        # Permission Gate
        if _HAS_PERMISSION_GATE and _get_permission_gate is not None:
            try:
                gate = _get_permission_gate()
                # 兼容不同的 check 接口
                if hasattr(gate, "check"):
                    result = gate.check(
                        operation=self.tool_id or self.name,
                        params=params,
                        permission_level=self.permission_level,
                    )
                    allowed = bool(result) if isinstance(result, bool) else bool(result.get("allowed", True))
                    gate_evidence["checks"]["permission_gate"] = {
                        "called": True,
                        "result": str(result)[:200],
                        "allowed": allowed,
                    }
                    if not allowed:
                        return False, f"permission_gate denied: {str(result)[:200]}", gate_evidence
                else:
                    gate_evidence["checks"]["permission_gate"] = {"called": False, "reason": "no check method"}
            except Exception as e:
                gate_evidence["checks"]["permission_gate"] = {"error": str(e)[:200]}
                # 网关异常时 fail-closed？不，网关本身异常不应阻断工具，记录即可
                # 但如果是权限明确拒绝则阻断

        # Action Firewall
        if _HAS_EXECUTION_CHAIN and _action_firewall is not None:
            try:
                if callable(_action_firewall):
                    result = _action_firewall(
                        tool_id=self.tool_id,
                        params=params,
                        risk_level=self.risk_level,
                    )
                    allowed = bool(result) if isinstance(result, bool) else bool(
                        result.get("allowed", True) if isinstance(result, dict) else True
                    )
                    gate_evidence["checks"]["action_firewall"] = {
                        "called": True,
                        "result": str(result)[:200],
                        "allowed": allowed,
                    }
                    if not allowed:
                        return False, f"action_firewall blocked: {str(result)[:200]}", gate_evidence
            except Exception as e:
                gate_evidence["checks"]["action_firewall"] = {"error": str(e)[:200]}

        # Effect Fence
        if _HAS_EXECUTION_CHAIN and _effect_fence is not None:
            try:
                if callable(_effect_fence):
                    result = _effect_fence(
                        tool_id=self.tool_id,
                        params=params,
                    )
                    allowed = bool(result) if isinstance(result, bool) else bool(
                        result.get("allowed", True) if isinstance(result, dict) else True
                    )
                    gate_evidence["checks"]["effect_fence"] = {
                        "called": True,
                        "result": str(result)[:200],
                        "allowed": allowed,
                    }
                    if not allowed:
                        return False, f"effect_fence blocked: {str(result)[:200]}", gate_evidence
            except Exception as e:
                gate_evidence["checks"]["effect_fence"] = {"error": str(e)[:200]}

        return True, "all gates passed (or not available)", gate_evidence

    # ── 自恢复 ──────────────────────────────────────────────

    def recover(self, error: BaseException, attempt: int) -> bool:
        """自恢复策略：判断是否可重试并执行退避。

        Args:
            error: 捕获的异常
            attempt: 当前重试次数（从 1 开始）

        Returns:
            True 表示应继续重试，False 表示应停止
        """
        if not self._retry_policy.is_retryable(error):
            return False
        if attempt > self._retry_policy.max_retries:
            return False
        self._retry_policy.sleep(attempt)
        return True

    # ── 执行 ─────────────────────────────────────────────────

    def _run(self, params: Dict[str, Any]) -> Any:
        """实际执行逻辑（子类覆盖）。"""
        raise NotImplementedError("SmartTool subclass must implement _run()")

    def execute(self, params: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        """执行工具：校验 → 安全网关 → 执行 → 异常捕获 → 自动重试。

        Args:
            params: 输入参数字典

        Returns:
            ToolExecutionResult 执行结果（带 evidence）
        """
        params = params or {}
        start_time = time.monotonic()
        evidence: Dict[str, Any] = {
            "tool_id": self.tool_id,
            "tool_name": self.name,
            "validation": {},
            "security_gates": {},
            "execution": {"attempts": []},
        }

        # 1. 参数校验 + 纠错
        corrected, param_changes, errors = self.validate_params(params)
        evidence["validation"] = {
            "original_params": dict(params),
            "corrected_params": dict(corrected),
            "param_changes": param_changes,
            "errors": errors,
        }
        if errors:
            duration = (time.monotonic() - start_time) * 1000
            result = ToolExecutionResult(
                success=False,
                error=f"parameter validation failed: {'; '.join(errors)}",
                corrected_params=corrected,
                duration_ms=round(duration, 2),
                evidence=evidence,
                tool_id=self.tool_id,
            )
            self._last_result = result
            return result

        # 2. 安全网关
        allowed, gate_reason, gate_evidence = self._check_security_gates(corrected)
        evidence["security_gates"] = gate_evidence
        if not allowed:
            duration = (time.monotonic() - start_time) * 1000
            result = ToolExecutionResult(
                success=False,
                error=f"security gate denied: {gate_reason}",
                corrected_params=corrected,
                duration_ms=round(duration, 2),
                evidence=evidence,
                tool_id=self.tool_id,
            )
            self._last_result = result
            return result

        # 3. 执行 + 重试
        last_error: Optional[BaseException] = None
        retries = 0
        max_attempts = self._retry_policy.max_retries + 1

        for attempt in range(1, max_attempts + 1):
            attempt_start = time.monotonic()
            try:
                data = self._run(corrected)
                attempt_duration = (time.monotonic() - attempt_start) * 1000
                evidence["execution"]["attempts"].append({
                    "attempt": attempt,
                    "success": True,
                    "duration_ms": round(attempt_duration, 2),
                })
                total_duration = (time.monotonic() - start_time) * 1000
                result = ToolExecutionResult(
                    success=True,
                    data=data,
                    retries=retries,
                    corrected_params=corrected if param_changes else None,
                    duration_ms=round(total_duration, 2),
                    evidence=evidence,
                    tool_id=self.tool_id,
                )
                self._last_result = result
                return result
            except Exception as e:
                last_error = e
                attempt_duration = (time.monotonic() - attempt_start) * 1000
                evidence["execution"]["attempts"].append({
                    "attempt": attempt,
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:300],
                    "duration_ms": round(attempt_duration, 2),
                })
                # 判断是否重试
                if attempt < max_attempts and self._retry_policy.is_retryable(e):
                    retries += 1
                    self._retry_policy.sleep(retries)
                    evidence["execution"]["attempts"][-1]["will_retry"] = True
                    continue
                break

        # 所有尝试失败
        total_duration = (time.monotonic() - start_time) * 1000
        error_msg = f"{type(last_error).__name__}: {str(last_error)[:300]}" if last_error else "unknown error"
        evidence["execution"]["final_error"] = error_msg
        evidence["execution"]["total_retries"] = retries
        result = ToolExecutionResult(
            success=False,
            error=error_msg,
            retries=retries,
            corrected_params=corrected if param_changes else None,
            duration_ms=round(total_duration, 2),
            evidence=evidence,
            tool_id=self.tool_id,
        )
        self._last_result = result
        return result

    # ── 便捷调用 ─────────────────────────────────────────────

    def __call__(self, **kwargs: Any) -> ToolExecutionResult:
        """允许以函数调用方式执行：tool(param1=value1)"""
        return self.execute(kwargs)


# ─────────────────────────────────────────────────────────────
# wrap_tool — 函数装饰器
# ─────────────────────────────────────────────────────────────

def wrap_tool(
    func: Optional[Callable] = None,
    *,
    tool_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    retry_policy: Optional[RetryPolicy] = None,
    use_security_gates: bool = True,
) -> Any:
    """将普通函数包装为 SmartTool。

    自动提取函数签名做参数校验，捕获异常做重试。

    用法：
        @wrap_tool
        def my_tool(x: int = 10, y: str = "hello"):
            return {"x": x, "y": y}

        result = my_tool.execute({"x": "5"})  # 自动类型转换
        # 或
        result = my_tool(x=5)

    也可带参数：
        @wrap_tool(tool_id="custom_id", retry_policy=RetryPolicy(max_retries=3))
        def my_tool(x: int):
            return x * 2
    """
    def decorator(fn: Callable) -> SmartTool:
        # 从函数签名构建参数 schema
        corrector = ParamCorrector.from_function(fn)
        param_schemas = corrector.param_schemas

        # 构建 SmartTool 子类
        tool_id_val = tool_id or fn.__name__
        name_val = name or fn.__name__
        desc_val = description or (fn.__doc__ or "").strip() or f"SmartTool wrapper for {fn.__name__}"

        tool_class = type(
            f"SmartTool_{fn.__name__}",
            (SmartTool,),
            {
                "tool_id": tool_id_val,
                "name": name_val,
                "description": desc_val,
                "params": param_schemas,
            },
        )

        # 实例化并绑定 _run
        instance = tool_class(
            retry_policy=retry_policy,
            param_corrector=corrector,
            use_security_gates=use_security_gates,
        )

        # 绑定 _run 方法（使用原始函数）
        def _run(self, params: Dict[str, Any]) -> Any:
            # 过滤掉函数不接受的参数
            try:
                sig = inspect.signature(fn)
                accepted = {k: v for k, v in params.items() if k in sig.parameters}
            except (ValueError, TypeError):
                accepted = params
            return fn(**accepted)

        instance._run = _run.__get__(instance, tool_class)  # type: ignore

        # 保留原始函数引用
        instance._original_func = fn  # type: ignore

        return instance

    # 支持 @wrap_tool 和 @wrap_tool(...) 两种用法
    if func is not None and callable(func):
        return decorator(func)
    return decorator


# ─────────────────────────────────────────────────────────────
# SmartToolRegistry — 注册/查找
# ─────────────────────────────────────────────────────────────

class SmartToolRegistry:
    """SmartTool 注册表：注册/查找 SmartTool。

    与 agent_capability.router.CapabilityRouter 兼容：
    可从 ToolDefinition 构建 SmartTool，也可将 SmartTool 的
    self_describe() 输出注册到 CapabilityRouter。

    用法：
        registry = SmartToolRegistry()
        registry.register(my_smart_tool)
        tool = registry.get("my_tool")
        result = tool.execute({"param": "value"})
    """

    def __init__(self):
        self._tools: Dict[str, SmartTool] = {}

    def register(self, tool: SmartTool) -> None:
        """注册 SmartTool。

        Args:
            tool: SmartTool 实例
        """
        if not isinstance(tool, SmartTool):
            raise TypeError(f"expected SmartTool instance, got {type(tool).__name__}")
        if not tool.tool_id:
            raise ValueError("SmartTool must have a tool_id")
        self._tools[tool.tool_id] = tool

    def unregister(self, tool_id: str) -> None:
        """注销 SmartTool。"""
        self._tools.pop(tool_id, None)

    def get(self, tool_id: str) -> Optional[SmartTool]:
        """按 tool_id 查找 SmartTool。"""
        return self._tools.get(tool_id)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有已注册工具的自描述信息。"""
        return [tool.self_describe() for tool in self._tools.values()]

    def list_ids(self) -> List[str]:
        """列出所有已注册工具的 tool_id。"""
        return list(self._tools.keys())

    def execute(self, tool_id: str, params: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        """查找并执行工具。

        Args:
            tool_id: 工具标识
            params: 执行参数

        Returns:
            ToolExecutionResult

        Raises:
            KeyError: tool_id 未注册
        """
        tool = self.get(tool_id)
        if tool is None:
            return ToolExecutionResult(
                success=False,
                error=f"tool not found: {tool_id}",
                evidence={"reason": "tool_id not registered", "available": self.list_ids()},
                tool_id=tool_id,
            )
        return tool.execute(params)

    def has(self, tool_id: str) -> bool:
        """检查工具是否已注册。"""
        return tool_id in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._tools


# ─────────────────────────────────────────────────────────────
# 从 ToolDefinition 构建 SmartTool（兼容 agent_capability.router）
# ─────────────────────────────────────────────────────────────

def from_tool_definition(
    tool_def: Any,
    handler: Optional[Callable] = None,
    retry_policy: Optional[RetryPolicy] = None,
) -> SmartTool:
    """从 agent_capability.router.ToolDefinition 构建 SmartTool。

    Args:
        tool_def: ToolDefinition 实例或兼容 dict（含 tool_id/name/description/params/...）
        handler: 执行函数（None 则使用 tool_def.handler）
        retry_policy: 重试策略

    Returns:
        SmartTool 实例
    """
    # 提取属性
    if hasattr(tool_def, "tool_id"):
        tid = tool_def.tool_id
        tname = getattr(tool_def, "name", "")
        tdesc = getattr(tool_def, "description", "")
        tcategory = getattr(tool_def, "category", "general")
        tkeywords = list(getattr(tool_def, "keywords", []) or [])
        tparams = getattr(tool_def, "params", [])
        tperm = getattr(tool_def, "permission_level", "read")
        trisk = getattr(tool_def, "risk_level", "LOW")
        trequires = getattr(tool_def, "requires_approval", False)
        tapiroute = getattr(tool_def, "api_route", "")
        tversion = getattr(tool_def, "version", "1.0.0")
        if handler is None:
            handler = getattr(tool_def, "handler", None)
    elif isinstance(tool_def, dict):
        tid = tool_def.get("tool_id", "")
        tname = tool_def.get("name", "")
        tdesc = tool_def.get("description", "")
        tcategory = tool_def.get("category", "general")
        tkeywords = list(tool_def.get("keywords", []) or [])
        tparams = tool_def.get("params", [])
        tperm = tool_def.get("permission_level", "read")
        trisk = tool_def.get("risk_level", "LOW")
        trequires = tool_def.get("requires_approval", False)
        tapiroute = tool_def.get("api_route", "")
        tversion = tool_def.get("version", "1.0.0")
        if handler is None:
            handler = tool_def.get("handler")
    else:
        raise TypeError(f"unsupported tool_def type: {type(tool_def).__name__}")

    # 归一化 permission_level / risk_level
    if hasattr(tperm, "value"):
        tperm = tperm.value
    if hasattr(trisk, "value"):
        trisk = trisk.value

    # 构建参数 schema
    param_schemas: List[Dict[str, Any]] = []
    for p in (tparams or []):
        if hasattr(p, "name"):
            param_schemas.append({
                "name": p.name,
                "type": getattr(p, "type", "string"),
                "required": getattr(p, "required", False),
                "default": getattr(p, "default", None),
                "enum": list(getattr(p, "enum", []) or []),
            })
        elif isinstance(p, dict):
            param_schemas.append(dict(p))

    corrector = ParamCorrector(param_schemas=param_schemas)

    # 构建 SmartTool 子类
    tool_class = type(
        f"SmartTool_{tid or 'anonymous'}",
        (SmartTool,),
        {
            "tool_id": tid,
            "name": tname,
            "description": tdesc,
            "category": tcategory,
            "keywords": tkeywords,
            "params": param_schemas,
            "permission_level": str(tperm),
            "risk_level": str(trisk),
            "requires_approval": bool(trequires),
            "api_route": tapiroute,
            "version": tversion,
        },
    )

    instance = tool_class(retry_policy=retry_policy, param_corrector=corrector)

    # 绑定 handler
    if handler is not None and callable(handler):
        def _run(self, params: Dict[str, Any]) -> Any:
            return handler(params)
        instance._run = _run.__get__(instance, tool_class)  # type: ignore
    else:
        # 无 handler 时，执行返回 api_route 信息（需外部执行）
        def _run(self, params: Dict[str, Any]) -> Any:
            return {
                "tool_id": self.tool_id,
                "api_route": self.api_route,
                "params": params,
                "note": "no handler bound; execute via API route or external executor",
            }
        instance._run = _run.__get__(instance, tool_class)  # type: ignore

    return instance
