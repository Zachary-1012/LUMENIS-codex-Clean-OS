# -*- coding: utf-8 -*-
"""Zachary OS AI · Browser Policy Engine（浏览器策略引擎）
对齐 CTR-BROWSER-RUNTIME-P0-01 P0-BR-04 + 指令 §九 Policy/Permission。
任何自适应执行必须：Detect → Classify → Policy Check → Permission Check → Execute / Safe Stop。

本引擎复用 safety_boundary.py 的安全级别体系（SAFE/CAUTION/NEED_CONFIRM/FORBIDDEN），
叠加浏览器导航域名白名单 + 操作类型策略。

允许（默认）：
  - 用户自己的文件、用户授权的数据、公开网页、合法 API、合法数据解析
  - 编码/文件格式转换、页面结构适配、浏览器兼容性测试、合法授权环境中的自动化

禁止自动执行（→ Safe Stop + Evidence + Human Review）：
  - 第三方账号破解、密码破解、窃取 Cookie/Session、绕过身份认证
  - CAPTCHA 绕过、DRM 绕过、付费权限绕过、明确访问控制绕过、平台安全机制绕过
  - 无限风控重试

红线：不包含 ZBC 产品业务规则；不读写 Cookie/Token/密钥。
"""
from __future__ import annotations
import enum
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

try:
    from safety_boundary import (
        BoundaryControlEngine, OperationType, SafetyLevel, boundary_control_engine,
    )
except Exception:  # 独立运行兜底
    BoundaryControlEngine = None
    OperationType = None
    SafetyLevel = None
    boundary_control_engine = None


class PolicyDecision(str, enum.Enum):
    ALLOW = "allow"
    CAUTION = "caution"          # 自动执行但记录详细日志
    NEED_CONFIRM = "need_confirm"
    SAFE_STOP = "safe_stop"      # 禁止自动执行 + Evidence + Human Review


# 导航域名白名单（公开合法站点；ZBC 产品域由 ZBC 侧扩展，本层保持通用）
DEFAULT_ALLOWED_DOMAINS = (
    "xiaohongshu.com", "www.xiaohongshu.com",
    "rednote.com", "www.rednote.com",
    "github.com", "www.github.com",
    "baidu.com", "www.baidu.com",
    "bing.com", "www.bing.com",
    "google.com", "www.google.com",
)

# 危险动作特征（命中 → SAFE_STOP）
_DANGEROUS_PATTERNS = (
    r"cookie", r"password", r"credential", r"token", r"session",
    r"bypass", r"captcha", r"drm", r"crack", r"exploit",
    r"inject", r"csrf", r"sql",
)

_SAFE_PATTERNS = (
    r"^https?://", r"\.(html?|json|xml|csv|txt|md|pdf|docx?|xlsx?|png|jpe?g|gif|webp|mp4|mp3|srt|vtt)$",
)


@dataclass
class PolicyCheckResult:
    decision: PolicyDecision
    reason: str
    operation: str
    target: Optional[str] = None
    safety_level: Optional[str] = None
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())


class BrowserPolicyEngine:
    """浏览器策略引擎：导航 + 动作 + 目标 三重策略检查。"""

    def __init__(self, allowed_domains: Optional[tuple] = None):
        self.allowed_domains = tuple(allowed_domains or DEFAULT_ALLOWED_DOMAINS)
        self._boundary = None
        if BoundaryControlEngine is not None and boundary_control_engine is not None:
            self._boundary = boundary_control_engine

    # ---------- 域名策略 ----------
    def _domain_allowed(self, url: str) -> bool:
        try:
            from urllib.parse import urlparse
            host = (urlparse(url).netloc or "").lower()
            if not host:
                return False
            # 精确匹配或子域后缀匹配
            for d in self.allowed_domains:
                if host == d or host.endswith("." + d.lstrip(".")):
                    return True
            return False
        except Exception:
            return False

    def check_navigation(self, url: str) -> PolicyCheckResult:
        """导航前策略检查（R2）：域名白名单 + 协议安全。"""
        if not isinstance(url, str) or not url:
            return PolicyCheckResult(PolicyDecision.SAFE_STOP, "empty url", "navigate")
        if not re.match(r"^https?://", url, re.I):
            return PolicyCheckResult(PolicyDecision.SAFE_STOP, "non-http(s) url", "navigate", url)
        if not self._domain_allowed(url):
            return PolicyCheckResult(PolicyDecision.SAFE_STOP, f"domain not in whitelist: {url}", "navigate", url)
        return PolicyCheckResult(PolicyDecision.ALLOW, "domain allowed", "navigate", url)

    # ---------- 动作策略 ----------
    def check_action(self, action: str, target: Any = None) -> PolicyCheckResult:
        """动作策略检查（R3）：危险模式 → SAFE_STOP；需要确认的操作 → NEED_CONFIRM。"""
        action_l = (action or "").lower()
        # 危险特征
        for pat in _DANGEROUS_PATTERNS:
            if re.search(pat, action_l):
                return PolicyCheckResult(
                    PolicyDecision.SAFE_STOP, f"dangerous action pattern: {pat}", action, str(target)[:200]
                )
        # 需要人工确认的动作
        confirm_actions = ("delete", "remove", "drop", "alter", "update sql", "batch")
        for c in confirm_actions:
            if c in action_l:
                return PolicyCheckResult(
                    PolicyDecision.NEED_CONFIRM, f"action requires confirmation: {c}", action, str(target)[:200]
                )
        # 只读/安全动作
        read_actions = ("read", "get", "search", "navigate", "snapshot", "screenshot", "observe", "extract")
        for r in read_actions:
            if r in action_l:
                return PolicyCheckResult(PolicyDecision.ALLOW, "read/observe action", action)
        # 常规写动作（click/type 等）→ CAUTION（记录详细日志）
        return PolicyCheckResult(PolicyDecision.CAUTION, "regular action, log detailed", action)

    # ---------- 目标策略 ----------
    def check_target(self, target: str) -> PolicyCheckResult:
        """目标内容策略检查：合法文件/URL/数据格式放行。"""
        if not isinstance(target, str) or not target:
            return PolicyCheckResult(PolicyDecision.ALLOW, "empty target", "target")
        target_l = target.lower()
        for pat in _DANGEROUS_PATTERNS:
            if re.search(pat, target_l):
                return PolicyCheckResult(
                    PolicyDecision.SAFE_STOP, f"dangerous target pattern: {pat}", "target", target[:200]
                )
        for pat in _SAFE_PATTERNS:
            if re.search(pat, target_l):
                return PolicyCheckResult(PolicyDecision.ALLOW, "safe target format", "target", target[:200])
        return PolicyCheckResult(PolicyDecision.ALLOW, "target allowed (generic)", "target", target[:200])

    # ---------- 统一入口：Detect → Classify → Policy Check → Permission Check → Execute / Safe Stop ----------
    def evaluate(self, operation: str, url: Optional[str] = None,
                 target: Any = None) -> PolicyCheckResult:
        """五步策略门（对齐指令 §九）：导航+动作+目标 全检查。"""
        # 1. 目标检查
        if target is not None:
            t = self.check_target(str(target))
            if t.decision == PolicyDecision.SAFE_STOP:
                return t
        # 2. 动作检查
        a = self.check_action(operation)
        if a.decision in (PolicyDecision.SAFE_STOP, PolicyDecision.NEED_CONFIRM):
            return a
        # 3. 导航检查（仅 navigate 类操作）
        if "navigate" in (operation or "").lower() and url:
            n = self.check_navigation(url)
            if n.decision == PolicyDecision.SAFE_STOP:
                return n
        # 4. 与 safety_boundary 联动（若可用）
        if self._boundary is not None and OperationType is not None:
            level = self._boundary.get_safety_level(OperationType.READ.value)
            # 若边界引擎判定禁止，则 Safe Stop
            if level and getattr(level, "value", "") == "forbidden":
                return PolicyCheckResult(PolicyDecision.SAFE_STOP, "safety_boundary forbidden", operation, str(target)[:200])
        return PolicyCheckResult(PolicyDecision.ALLOW, "policy gate passed", operation, str(target)[:200])


# 全局实例
browser_policy_engine = BrowserPolicyEngine()