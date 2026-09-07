# -*- coding: utf-8 -*-
"""
Smart Tool Recovery — 恢复策略模块
====================================
提供重试策略和参数自动纠错能力，供 SmartTool 基类使用。

设计原则：
  - 可配置的重试次数、退避时间、可重试异常白名单
  - 参数纠错基于类型注解和默认值，不猜测不可纠错参数
  - 所有纠错操作记录在 evidence 中，可追溯
  - 不绕过 Permission / Action Firewall / Effect Fence
  - 纯 Python 实现，无外部依赖
"""
from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


# ─────────────────────────────────────────────────────────────
# RetryPolicy — 重试策略
# ─────────────────────────────────────────────────────────────

@dataclass
class RetryPolicy:
    """重试策略配置。

    Attributes:
        max_retries: 最大重试次数（不含首次执行）
        backoff_seconds: 基础退避秒数（实际退避 = backoff * 2^attempt）
        retryable_exceptions: 可重试异常类型元组；空元组表示所有 Exception 均可重试
        non_retryable_exceptions: 不可重试异常类型元组（优先级高于 retryable）
        max_backoff_seconds: 退避上限（秒）
    """
    max_retries: int = 2
    backoff_seconds: float = 0.5
    retryable_exceptions: Tuple[Type[BaseException], ...] = (
        ConnectionError, TimeoutError, OSError,
    )
    non_retryable_exceptions: Tuple[Type[BaseException], ...] = (
        ValueError, TypeError, KeyError, PermissionError,
    )
    max_backoff_seconds: float = 10.0

    def is_retryable(self, error: BaseException) -> bool:
        """判断异常是否可重试。

        优先级：non_retryable > retryable > 默认（有白名单则白名单外不可重试）
        """
        # 不可重试优先
        for exc_type in self.non_retryable_exceptions:
            if isinstance(error, exc_type):
                return False
        # 白名单为空 → 所有 Exception 均可重试
        if not self.retryable_exceptions:
            return isinstance(error, Exception)
        # 白名单非空 → 仅白名单内可重试
        for exc_type in self.retryable_exceptions:
            if isinstance(error, exc_type):
                return True
        return False

    def backoff_for_attempt(self, attempt: int) -> float:
        """计算第 attempt 次重试的退避时间（指数退避）。

        Args:
            attempt: 重试次数（从 1 开始）

        Returns:
            退避秒数
        """
        delay = self.backoff_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_backoff_seconds)

    def sleep(self, attempt: int) -> None:
        """执行退避等待。"""
        delay = self.backoff_for_attempt(attempt)
        if delay > 0:
            time.sleep(delay)


# 默认重试策略
DEFAULT_RETRY_POLICY = RetryPolicy()

# 不重试策略（用于不可重试操作）
NO_RETRY_POLICY = RetryPolicy(max_retries=0, backoff_seconds=0)


# ─────────────────────────────────────────────────────────────
# ParamCorrector — 参数自动纠错
# ─────────────────────────────────────────────────────────────

# 类型转换映射
_TYPE_CONVERTERS: Dict[str, Callable[[Any], Any]] = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": bool,
    "boolean": bool,
    "list": list,
    "array": list,
    "dict": dict,
    "object": dict,
}


def _coerce_bool(value: Any) -> bool:
    """智能布尔转换。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in ("true", "1", "yes", "y", "on"):
            return True
        if lower in ("false", "0", "no", "n", "off", ""):
            return False
    raise ValueError(f"cannot coerce {value!r} to bool")


def _safe_convert(value: Any, type_name: str) -> Tuple[Any, bool]:
    """安全类型转换，返回 (转换后的值, 是否成功)。"""
    type_lower = type_name.lower().strip()
    # bool 特殊处理
    if type_lower in ("bool", "boolean"):
        try:
            return _coerce_bool(value), True
        except (ValueError, TypeError):
            return value, False
    converter = _TYPE_CONVERTERS.get(type_lower)
    if converter is None:
        return value, False
    try:
        # 已经是目标类型则不转换
        if type_lower in ("str", "string") and isinstance(value, str):
            return value, True
        if type_lower in ("int", "integer") and isinstance(value, int) and not isinstance(value, bool):
            return value, True
        if type_lower in ("float", "number") and isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value), True
        if type_lower in ("list", "array") and isinstance(value, list):
            return value, True
        if type_lower in ("dict", "object") and isinstance(value, dict):
            return value, True
        return converter(value), True
    except (ValueError, TypeError):
        return value, False


@dataclass
class ParamCorrector:
    """基于类型和默认值的参数自动纠错器。

    用法：
        corrector = ParamCorrector.from_tool_definition(tool_def)
        corrected, changes = corrector.correct(params)
    """
    param_schemas: List[Dict[str, Any]] = field(default_factory=list)
    """参数 schema 列表，每个元素包含 name/type/required/default/enum。"""

    @classmethod
    def from_param_list(cls, params: List[Any]) -> "ParamCorrector":
        """从 ToolParam 列表或 dict 列表构建 ParamCorrector。"""
        schemas: List[Dict[str, Any]] = []
        for p in params:
            if hasattr(p, "name"):
                schemas.append({
                    "name": p.name,
                    "type": getattr(p, "type", "string"),
                    "required": getattr(p, "required", False),
                    "default": getattr(p, "default", None),
                    "enum": list(getattr(p, "enum", []) or []),
                })
            elif isinstance(p, dict):
                schemas.append({
                    "name": p.get("name", ""),
                    "type": p.get("type", "string"),
                    "required": p.get("required", False),
                    "default": p.get("default"),
                    "enum": list(p.get("enum", []) or []),
                })
        return cls(param_schemas=schemas)

    @classmethod
    def from_function(cls, func: Callable) -> "ParamCorrector":
        """从函数签名自动构建 ParamCorrector（用于 wrap_tool 装饰器）。"""
        schemas: List[Dict[str, Any]] = []
        try:
            sig = inspect.signature(func)
            for name, param in sig.parameters.items():
                if name in ("self", "cls"):
                    continue
                if param.kind in (inspect.Parameter.VAR_POSITIONAL,
                                   inspect.Parameter.VAR_KEYWORD):
                    continue
                type_annotation = ""
                if param.annotation is not inspect.Parameter.empty:
                    type_annotation = getattr(param.annotation, "__name__", str(param.annotation))
                default = None
                required = True
                if param.default is not inspect.Parameter.empty:
                    default = param.default
                    required = False
                schemas.append({
                    "name": name,
                    "type": type_annotation or "string",
                    "required": required,
                    "default": default,
                    "enum": [],
                })
        except (ValueError, TypeError):
            pass
        return cls(param_schemas=schemas)

    def correct(self, params: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """纠错参数，返回 (纠错后参数, 变更记录)。

        变更记录每项包含：param, action(fill_default/type_coerce/enum_fix),
        old, new, reason。

        纠错规则：
          1. 缺失的非必填参数 → 填充默认值
          2. 类型不匹配且可转换 → 类型转换
          3. enum 不匹配 → 不纠错（记录为不可纠错，由 validate 报错）
          4. 必填参数缺失 → 不填充（由 validate 报错）
        """
        if not isinstance(params, dict):
            params = {}
        corrected = dict(params)
        changes: List[Dict[str, Any]] = []

        for schema in self.param_schemas:
            name = schema.get("name", "")
            if not name:
                continue
            ptype = schema.get("type", "string")
            required = schema.get("required", False)
            default = schema.get("default")
            enum_values = schema.get("enum", [])

            # 规则1：缺失参数填充默认值
            if name not in corrected:
                if not required and default is not None:
                    corrected[name] = default
                    changes.append({
                        "param": name,
                        "action": "fill_default",
                        "old": None,
                        "new": default,
                        "reason": "missing optional param filled with default",
                    })
                continue

            value = corrected[name]

            # 规则3：enum 检查（不纠错，仅记录）
            if enum_values and value not in enum_values:
                changes.append({
                    "param": name,
                    "action": "enum_mismatch",
                    "old": value,
                    "new": value,
                    "reason": f"value not in enum {enum_values}, not auto-corrected",
                })
                continue

            # 规则2：类型转换
            if value is not None:
                converted, ok = _safe_convert(value, ptype)
                if ok and converted is not value:
                    corrected[name] = converted
                    changes.append({
                        "param": name,
                        "action": "type_coerce",
                        "old": value,
                        "new": converted,
                        "reason": f"coerced from {type(value).__name__} to {ptype}",
                    })

        return corrected, changes

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """校验参数（不纠错），返回 (是否通过, 错误列表)。"""
        errors: List[str] = []
        if not isinstance(params, dict):
            return False, ["params is not a dict"]
        for schema in self.param_schemas:
            name = schema.get("name", "")
            if not name:
                continue
            required = schema.get("required", False)
            enum_values = schema.get("enum", [])
            if required and name not in params:
                errors.append(f"missing required param: {name}")
            if name in params and enum_values and params[name] not in enum_values:
                errors.append(f"param {name} must be one of {enum_values}")
        return len(errors) == 0, errors
