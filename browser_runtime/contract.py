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
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

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
    retry_count: int = 0

    def add_step(self, step: str, detail: Any = None, ok: bool = True):
        self.steps.append({
            "step": step,
            "detail": detail if detail is None else str(detail)[:500],
            "ok": ok,
            "ts": datetime.now().isoformat(),
        })

    def to_evidence(self) -> dict:
        """转为 Evidence 记录（不含任何密钥）"""
        return {
            "action": self.action,
            "url": self.url,
            "provider": self.provider,
            "started_at": self.started_at,
            "steps": self.steps,
            "result": self.result,
            "error": str(self.error)[:500] if self.error else None,
            "retry_count": self.retry_count,
        }


class BEEPExecutor:
    """BEEP 协议执行器：包装任意动作函数为 BEEP 全链路。"""

    def __init__(self, max_retry: int = MAX_RETRY):
        self.max_retry = max_retry

    def run(self, action_name: str, action_fn: Callable[[], Any],
            verify_fn: Optional[Callable[[Any], bool]] = None,
            precondition_fn: Optional[Callable[[], Any]] = None,
            observe_fn: Optional[Callable[[], Any]] = None,
            url: Optional[str] = None, provider: Optional[str] = None,
            on_evidence: Optional[Callable[[dict], None]] = None) -> BEEPTrace:
        """执行 BEEP 全链路：Precondition→Observe→Plan→Action→Post-condition→Evidence→Decision→Next。

        规则：
          - 有限重试（≤ max_retry），禁止无限重试。
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
            trace.add_step(BEEPStep.PRECONDITION.value, f"error: {e}", ok=False)
            trace.result = "FAILED"
            trace.error = str(e)
            if on_evidence:
                on_evidence(trace.to_evidence())
            return trace

        # Observe（前置观察）
        try:
            if observe_fn is not None:
                obs = observe_fn()
                trace.add_step(BEEPStep.OBSERVE.value, obs)
        except Exception as e:
            trace.add_step(BEEPStep.OBSERVE.value, f"error: {e}", ok=False)
            trace.result = "FAILED"
            trace.error = str(e)
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
                trace.add_step(BEEPStep.ACTION.value, result, ok=True)
                # Post-condition / Verify
                if verify_fn is not None:
                    ok = bool(verify_fn(result))
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
                last_error = str(e)
                trace.add_step(BEEPStep.ACTION.value, f"verify failed (attempt {attempt})", ok=False)
                time.sleep(0.2 * attempt)  # 有限退避
            except Exception as e:
                last_error = str(e)
                trace.add_step(BEEPStep.ACTION.value, f"error (attempt {attempt}): {e}", ok=False)
                time.sleep(0.2 * attempt)

        if trace.result != "SUCCESS":
            trace.result = "VERIFY_FAILED"
            trace.error = last_error or "unknown failure"
            trace.add_step(BEEPStep.DECISION.value, f"classify_failure -> {FailureClass.UNKNOWN.value}")

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
        e = (error or "").lower()
        if any(k in e for k in ("timeout", "timed out", "connection reset", "network", "socket")):
            return FailureClass.TRANSIENT
        if any(k in e for k in ("login", "session", "auth", "unauthorized", "logged out")):
            return FailureClass.SESSION
        if any(k in e for k in ("not found", "selector", "no such element", "page changed")):
            return FailureClass.PAGE_CHANGED
        if any(k in e for k in ("permission", "forbidden", "denied", "captcha", "risk", "blocked")):
            return FailureClass.PERMISSION if "permission" in e or "forbidden" in e else FailureClass.PLATFORM_RISK
        # Policy Gate 拒绝（domain 白名单 / safe_stop）→ 平台风控级处理（Cooldown/Stop），不允许重试
        if any(k in e for k in ("safe_stop", "whitelist", "policy block", "policy reject")):
            return FailureClass.PLATFORM_RISK
        return FailureClass.UNKNOWN

    @staticmethod
    def state_sequence() -> list[str]:
        """返回成功路径状态序列（用于状态机校验）。"""
        return [s.value for s in _SUCCESS_PATH]