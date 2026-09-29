# -*- coding: utf-8 -*-
"""Zachary OS AI · Browser Runtime Contract（浏览器运行时契约层）
对齐 CTR-BROWSER-RUNTIME-P0-01：Browser Contract → Router → Adapter → Provider 分层。
本文件：Contract 接口 + Browser State Machine + BEEP 执行协议 + 失败分类。
设计原则：
  - 调用方只依赖本层接口，禁止直接 new Provider。
  - 写操作必须走 BEEP（Precondition→Observe→Plan→Action→Post-condition→Evidence→Decision→Next）。
  - 所有动作必须产生 Evidence，禁止 "点击后默认成功"。
  - 失败必须分类（transient/session/page_changed/permission/platform_risk/unknown），禁止无限重试。
红线：不包含任何 ZBC 产品业务规则；不读写 Cookie/Token/密钥。
"""
from __future__ import annotations
import enum
import time
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

# ---------- Browser State Machine（对齐指令 §八） ----------
class BrowserState(str, enum.Enum):
    INIT = "INIT"
    BROWSER_READY = "BROWSER_READY"
    PAGE_READY = "PAGE_READY"
    SESSION_VALID = "SESSION_VALID"
    TASK_READY = "TASK_READY"
    ACTION = "ACTION"
    VERIFY = "VERIFY"
    SUCCESS = "SUCCESS"
    VERIFY_FAILED = "VERIFY_FAILED"
    CLASSIFY_FAILURE = "CLASSIFY_FAILURE"


# 成功路径状态顺序（用于状态机推进校验）
_SUCCESS_PATH = [
    BrowserState.INIT,
    BrowserState.BROWSER_READY,
    BrowserState.PAGE_READY,
    BrowserState.SESSION_VALID,
    BrowserState.TASK_READY,
    BrowserState.ACTION,
    BrowserState.VERIFY,
    BrowserState.SUCCESS,
]


class FailureClass(str, enum.Enum):
    """失败分类（对齐指令 §八 至少 5 类）"""
    TRANSIENT = "transient"          # 瞬时错误 → 有限 Retry
    SESSION = "session"              # Session 失效 → Re-auth / Stop
    PAGE_CHANGED = "page_changed"    # 页面结构变化 → Re-observe
    PERMISSION = "permission"        # 权限不足 → Policy / Stop
    PLATFORM_RISK = "platform_risk"  # 平台风控 → Cooldown / Stop
    UNKNOWN = "unknown"              # 未知 → Evidence + Safe Stop


class BrowserAvailability(str, enum.Enum):
    """Business-facing availability state shared by every browser provider."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


_SECRET_FIELD = re.compile(
    r"cookie|authorization|bearer|password|passwd|secret|api[_-]?key|"
    r"token|session(?:[_-]?id)?|cdp[_-]?url|"
    r"storage[_-]?state|user[_-]?data[_-]?dir|websocketdebuggerurl",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(cookie|set-cookie)\s*[:=]\s*[^\r\n]*|"
    r"\b(authorization|bearer|password|passwd|secret|api[_-]?key|"
    r"access[_-]?token|refresh[_-]?token|id[_-]?token|token|"
    r"session(?:[_-]?id)?|cdp[_-]?url)"
    r"\s*[:=]\s*[^\s,;&]+"
)
_BEARER_VALUE = re.compile(r"(?i)\bBearer\s+[^\s,;]+")
_URL_IN_TEXT = re.compile(r"(?i)\b(?:https?|wss?)://[^\s\"'<>]+")


def safe_browser_url(value: Any) -> Optional[str]:
    """Keep source identity while stripping URL credentials, query and fragments.

    CDP websocket paths carry browser-scoped debugger identifiers, so only the
    local endpoint origin is retained for those URLs.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        parts = urlsplit(value)
        if not parts.scheme or not parts.hostname:
            return None
        host = parts.hostname
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        netloc = f"{host}:{parts.port}" if parts.port else host
        path = "/[redacted]" if parts.scheme.lower() in ("ws", "wss") else parts.path
        return urlunsplit((parts.scheme, netloc, path, "", ""))
    except (TypeError, ValueError):
        return None


def sanitize_runtime_value(value: Any, key: Optional[str] = None) -> Any:
    """Redact credential-bearing fields and values before tracing runtime data."""
    if key and _SECRET_FIELD.search(key):
        return "[redacted]"
    if isinstance(value, Mapping):
        return {
            str(item_key): sanitize_runtime_value(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_runtime_value(item) for item in value]
    if isinstance(value, str):
        cleaned = _BEARER_VALUE.sub("Bearer [redacted]", value)
        cleaned = _SECRET_ASSIGNMENT.sub("[redacted]", cleaned)

        def replace_url(match: re.Match) -> str:
            safe = safe_browser_url(match.group(0))
            return safe or "[redacted URL]"

        return _URL_IN_TEXT.sub(replace_url, cleaned)[:500]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize_runtime_value(str(value))


def safe_browser_error(error: Any) -> str:
    """Return a useful stable error summary without echoing runtime secrets."""
    failure = classify_browser_failure(error)
    return {
        FailureClass.TRANSIENT: "The browser connection is unavailable.",
        FailureClass.SESSION: "The browser session needs attention.",
        FailureClass.PAGE_CHANGED: "The page could not be confirmed.",
        FailureClass.PERMISSION: "This browser action is unavailable for the current access level.",
        FailureClass.PLATFORM_RISK: "The platform requested a pause.",
        FailureClass.UNKNOWN: "The browser operation could not be confirmed.",
    }[failure]


def browser_health_result(
    provider: str,
    connection_state: str,
    *,
    error: Any = None,
    error_code: Optional[str] = None,
) -> dict:
    """Build the one browser health shape; provider details stay diagnostic."""
    connection_state = str(connection_state or "unavailable").lower()
    available = connection_state == "connected" and error is None
    legacy_status = "up" if available else "degraded" if connection_state == "degraded" else "down"
    failure = classify_browser_failure(error) if error is not None else None
    if error_code is None:
        if connection_state == "disconnected":
            error_code = "browser_disconnected"
        elif error is not None:
            error_code = {
                FailureClass.TRANSIENT: "connection_unavailable",
                FailureClass.SESSION: "session_attention_required",
                FailureClass.PAGE_CHANGED: "page_unavailable",
                FailureClass.PERMISSION: "permission_denied",
                FailureClass.PLATFORM_RISK: "platform_pause_required",
                FailureClass.UNKNOWN: "runtime_unavailable",
            }[failure]
        elif connection_state != "connected":
            error_code = "browser_unavailable"

    diagnostics = {
        "provider": str(provider or "unknown").lower(),
        "connection_state": connection_state,
        "status": legacy_status,
        "error_code": error_code,
        "failure_class": failure.value if failure else (
            FailureClass.TRANSIENT.value if connection_state == "disconnected" else None
        ),
        "message": safe_browser_error(error) if error is not None else (
            "The browser connection was lost." if connection_state == "disconnected" else None
        ),
    }
    return {
        "display_name": {
            "zh-CN": "内部浏览器",
            "en": "Internal Browser",
            "ko": "내부 브라우저",
        },
        "state": (
            BrowserAvailability.AVAILABLE.value if available else
            BrowserAvailability.DEGRADED.value if connection_state == "degraded" else
            BrowserAvailability.UNAVAILABLE.value
        ),
        "available": available,
        "diagnostics": diagnostics,
    }


def classify_browser_failure(error: Any) -> FailureClass:
    """Classify a runtime error before recovery; risky states never retry."""
    e = str(error or "").lower()
    e = _SECRET_ASSIGNMENT.sub(" ", e)
    e = _BEARER_VALUE.sub(" ", e)
    e = _URL_IN_TEXT.sub(" ", e)
    if any(k in e for k in ("429", "rate limit", "rate-limit", "too many requests", "captcha", "risk control")):
        return FailureClass.PLATFORM_RISK
    if any(k in e for k in ("login", "session", "auth", "unauthorized", "logged out", "401")):
        return FailureClass.SESSION
    if any(k in e for k in ("permission", "forbidden", "denied", "403")):
        return FailureClass.PERMISSION
    if any(k in e for k in ("not found", "selector", "no such element", "page changed", "target closed")):
        return FailureClass.PAGE_CHANGED
    if any(k in e for k in ("blocked", "safe_stop", "whitelist", "policy block", "policy reject")):
        return FailureClass.PLATFORM_RISK
    if any(k in e for k in ("timeout", "timed out", "connection reset", "connection refused", "network", "socket", "disconnected")):
        return FailureClass.TRANSIENT
    return FailureClass.UNKNOWN


# 失败分类 → 处理策略
FAILURE_POLICY: dict[FailureClass, str] = {
    FailureClass.TRANSIENT: "limited_retry",
    FailureClass.SESSION: "re_auth_or_stop",
    FailureClass.PAGE_CHANGED: "re_observe",
    FailureClass.PERMISSION: "policy_or_stop",
    FailureClass.PLATFORM_RISK: "cooldown_or_stop",
    FailureClass.UNKNOWN: "evidence_and_safe_stop",
}

MAX_RETRY = 3  # 禁止无限重试


# ---------- BEEP 执行协议（对齐指令 §七） ----------
class BEEPStep(str, enum.Enum):
    PRECONDITION = "precondition"
    OBSERVE = "observe"
    PLAN = "plan"
    ACTION = "action"
    POST_CONDITION = "post_condition"
    EVIDENCE = "evidence"
    DECISION = "decision"
    NEXT = "next"


@dataclass
class BEEPTrace:
    """一次 BEEP 执行的完整追踪（Evidence）"""
    action: str
    url: Optional[str] = None
    provider: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    steps: list[dict] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    failure_class: Optional[str] = None
    retry_count: int = 0

    def add_step(self, step: str, detail: Any = None, ok: bool = True):
        self.steps.append({
            "step": step,
            "detail": sanitize_runtime_value(detail),
            "ok": ok,
            "ts": datetime.now().isoformat(),
        })

    def to_evidence(self) -> dict:
        """转为 Evidence 记录（不含任何密钥）"""
        return {
            "action": sanitize_runtime_value(self.action),
            "url": safe_browser_url(self.url),
            "provider": sanitize_runtime_value(self.provider),
            "started_at": self.started_at,
            "steps": self.steps,
            "result": self.result,
            "error": safe_browser_error(self.error) if self.error else None,
            "failure_class": self.failure_class,
            "retry_count": self.retry_count,
        }


class BEEPExecutor:
    """BEEP 协议执行器：包装任意动作函数为 BEEP 全链路。"""

    def __init__(self, max_retry: int = MAX_RETRY):
        try:
            requested_retries = int(max_retry)
        except (TypeError, ValueError):
            requested_retries = MAX_RETRY
        self.max_retry = max(1, min(requested_retries, MAX_RETRY))

    def run(self, action_name: str, action_fn: Callable[[], Any],
            verify_fn: Optional[Callable[[Any], bool]] = None,
            precondition_fn: Optional[Callable[[], Any]] = None,
            observe_fn: Optional[Callable[[], Any]] = None,
            url: Optional[str] = None, provider: Optional[str] = None,
            on_evidence: Optional[Callable[[dict], None]] = None,
            retry_safe: bool = False) -> BEEPTrace:
        """执行 BEEP 全链路：Precondition→Observe→Plan→Action→Post-condition→Evidence→Decision→Next。

        规则：
          - Action 重试需显式声明幂等性；有限重试（≤ max_retry），禁止无限重试。
          - 未通过 verify 视为 VERIFY_FAILED → CLASSIFY_FAILURE。
          - 每次执行结束后回调 on_evidence(trace.to_evidence())。
        """
        trace = BEEPTrace(action=action_name, url=url, provider=provider)

        # Precondition
        try:
            if precondition_fn is not None:
                pre = precondition_fn()
                trace.add_step(BEEPStep.PRECONDITION.value, pre)
                if pre is False:
                    trace.result = "SKIP_PRECONDITION"
                    trace.error = "precondition not met"
                    if on_evidence:
                        on_evidence(trace.to_evidence())
                    return trace
        except Exception as e:
            trace.failure_class = classify_browser_failure(e).value
            trace.add_step(BEEPStep.PRECONDITION.value, safe_browser_error(e), ok=False)
            trace.result = "FAILED"
            trace.error = safe_browser_error(e)
            if on_evidence:
                on_evidence(trace.to_evidence())
            return trace

        # Observe（前置观察）
        try:
            if observe_fn is not None:
                obs = observe_fn()
                trace.add_step(BEEPStep.OBSERVE.value, obs)
        except Exception as e:
            trace.failure_class = classify_browser_failure(e).value
            trace.add_step(BEEPStep.OBSERVE.value, safe_browser_error(e), ok=False)
            trace.result = "FAILED"
            trace.error = safe_browser_error(e)
            if on_evidence:
                on_evidence(trace.to_evidence())
            return trace

        # Plan（记录动作计划）
        trace.add_step(BEEPStep.PLAN.value, action_name)

        # Action + Verify（有限重试）
        attempt = 0
        last_error = None
        while attempt < self.max_retry:
            attempt += 1
            trace.retry_count = attempt
            try:
                result = action_fn()
                if isinstance(result, Mapping) and result.get("ok") is False:
                    raise RuntimeError(result.get("error") or "browser operation unavailable")
                trace.add_step(BEEPStep.ACTION.value, result, ok=True)
                # Post-condition / Verify
                if verify_fn is not None:
                    try:
                        ok = bool(verify_fn(result))
                    except Exception as e:
                        raise _VerifyError("post-condition could not be checked") from e
                    trace.add_step(BEEPStep.POST_CONDITION.value, f"verify={ok}", ok=ok)
                    if not ok:
                        raise _VerifyError("post-condition verify failed")
                else:
                    trace.add_step(BEEPStep.POST_CONDITION.value, "no verify_fn")
                trace.result = "SUCCESS"
                trace.add_step(BEEPStep.EVIDENCE.value, "recorded")
                trace.add_step(BEEPStep.DECISION.value, "success")
                break
            except _VerifyError as e:
                trace.failure_class = FailureClass.PAGE_CHANGED.value
                last_error = safe_browser_error(e)
                trace.add_step(BEEPStep.ACTION.value, f"verify failed (attempt {attempt})", ok=False)
                if retry_safe and attempt < self.max_retry:
                    time.sleep(0.2 * attempt)
                    continue
                break
            except Exception as e:
                failure = classify_browser_failure(e)
                trace.failure_class = failure.value
                last_error = safe_browser_error(e)
                trace.add_step(BEEPStep.ACTION.value, f"{failure.value} failure (attempt {attempt})", ok=False)
                if failure != FailureClass.TRANSIENT or not retry_safe or attempt >= self.max_retry:
                    break
                time.sleep(0.2 * attempt)  # 有限退避，只对可恢复连接错误重试

        if trace.result != "SUCCESS":
            trace.result = "VERIFY_FAILED"
            trace.error = last_error or "unknown failure"
            trace.add_step(BEEPStep.DECISION.value, f"classify_failure -> {trace.failure_class or FailureClass.UNKNOWN.value}")

        if on_evidence:
            on_evidence(trace.to_evidence())
        return trace


class _VerifyError(Exception):
    """内部：verify 未通过"""


# ---------- Browser Contract 抽象接口 ----------
class BrowserContract:
    """Browser Runtime 统一接口。Adapter 必须实现本接口。"""

    def navigate(self, url: str, **kw) -> dict: ...       # 导航
    def snapshot(self, **kw) -> dict: ...                 # 快照
    def screenshot(self, path: Optional[str] = None, **kw) -> dict: ...  # 截图
    def click(self, selector: str, **kw) -> dict: ...     # 点击（BEEP）
    def type_text(self, selector: str, text: str, **kw) -> dict: ...   # 输入
    def get_text(self, selector: str, **kw) -> str: ...   # 读文本
    def wait_for(self, selector: str, timeout: int = 10, **kw) -> bool: ...  # 等待
    def evaluate(self, js: str, **kw) -> Any: ...         # 执行 JS（受限）
    def health(self) -> dict: ...                         # Browser Health
    def close(self, **kw) -> None: ...                    # 关闭

    @staticmethod
    def classify_failure(error: str) -> FailureClass:
        """根据错误信息粗分类失败（可被 Adapter 覆盖）。"""
        return classify_browser_failure(error)

    @staticmethod
    def state_sequence() -> list[str]:
        """返回成功路径状态序列（用于状态机校验）。"""
        return [s.value for s in _SUCCESS_PATH]
