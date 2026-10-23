# -*- coding: utf-8 -*-
"""
ZBC AI Browser Runtime — Production-Ready Browser Agent Runtime
=================================================================
调用链：AI Agent → Browser Skill → Permission Gate → Browser Runtime
       → Observe → Reason → Plan → Action → Verify → Evidence → Trace

核心差异化：每个 Action 必须经过 Verification 闭环，
禁止 AI 说"点击成功"就认定成功。

设计原则（AGENTS.md）：
  - 先审计、再修改；先兼容、再重构；先旁路、再切换；先验证、再交付
  - 系统内循环优先于 AI
  - 数据失败必须显式，不得静默成 0 条
  - 敏感凭证不得进入 Prompt/LLM Context/Evidence 明文
  - 小红书官方账号一律只读

本模块不重写已有 collector_v2/browser_session.py / browser_surface.py，
而是作为上层 AI Runtime 编排层，可复用 CDP 连接。
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import math
import os
import re
import secrets
import sqlite3
import struct
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 1. 常量与枚举
# ═══════════════════════════════════════════════════════════════

from lumenis.shared.database import DatabaseRepository, get_repository, main_db_path

DB_PATH = main_db_path()

# Session 生命周期配置（秒）
DEFAULT_SESSION_IDLE_TIMEOUT = 600      # 空闲 10 分钟自动关闭
DEFAULT_SESSION_MAX_LIFETIME = 3600     # 最大生命周期 1 小时
DEFAULT_ACTION_TIMEOUT = 30000           # 单 Action 超时（ms）
MAX_OBSERVATION_TEXT_LENGTH = 2000
MAX_HUMAN_LINKS = 40
MAX_HUMAN_LINK_SCAN = 1000
MAX_HUMAN_LINK_LABEL_LENGTH = 160
MAX_HUMAN_LINK_URL_LENGTH = 2048

# Circuit Breaker 配置
CB_FAILURE_THRESHOLD = 5                 # 连续失败 N 次熔断
CB_COOLDOWN_SECONDS = 30                 # 熔断冷却时间

# Evidence 截图目录
EVIDENCE_SCREENSHOT_DIR = os.environ.get(
    "ZBC_BROWSER_EVIDENCE_DIR",
    str(Path(__file__).parent / "data" / "browser_evidence"),
)

# ZBC Lifecycle Contract V1.0 (bypass-mode)
try:
    from lifecycle_mixin import LifecycleMixin as _LifecycleMixin
    _LIFECYCLE_AVAILABLE = True
except Exception:
    _LifecycleMixin = None
    _LIFECYCLE_AVAILABLE = False


class BrowserActionType(str, Enum):
    """Browser Action 类型枚举。"""
    NAVIGATE = "navigate"
    BACK = "back"
    FORWARD = "forward"
    RELOAD = "reload"
    CLICK = "click"
    INPUT = "input"
    SELECT = "select"
    SCROLL = "scroll"
    KEYBOARD = "keyboard"
    WAIT = "wait"
    TAB_NEW = "tab_new"
    TAB_SWITCH = "tab_switch"
    TAB_CLOSE = "tab_close"
    SCREENSHOT = "screenshot"
    OBSERVE = "observe"
    SEARCH = "search"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    STOP = "stop"


HUMAN_CONTROL_ACTIONS = ("navigate", "back", "forward", "reload", "scroll", "open_link")


class ActionResult(str, Enum):
    """Action 验证结果。"""
    PASS = "PASS"
    FAIL = "FAIL"
    RETRY = "RETRY"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    SKIPPED = "SKIPPED"


class SessionStatus(str, Enum):
    """Browser Session 状态。"""
    CREATED = "created"
    RUNNING = "running"
    IDLE = "idle"
    NEED_VERIFY = "need_verify"
    COOLING_DOWN = "cooling_down"
    BLOCKED = "blocked"
    ERROR = "error"
    CLOSED = "closed"


class BrowserHumanControlError(RuntimeError):
    """A browser action conflicts with the server-owned human control lease."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class BrowserFrameStaleError(RuntimeError):
    """A human action refers to a frame that is no longer current."""

    def __init__(self, code: str = "BROWSER_FRAME_STALE"):
        super().__init__(code)
        self.code = code


class BrowserLinkError(RuntimeError):
    """A server-resolved page link is unavailable or no longer current."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


_HUMAN_LINK_SNAPSHOT_JS = f"""() => {{
    const anchors = document.getElementsByTagName('a');
    const scanLimit = Math.min(anchors.length, {MAX_HUMAN_LINK_SCAN});
    const links = [];
    for (let index = 0; index < scanLimit && links.length < {MAX_HUMAN_LINKS}; index++) {{
        const element = anchors[index];
        if (!element || !element.hasAttribute('href')) continue;
        const href = element.href || '';
        if (!href || href.length > {MAX_HUMAN_LINK_URL_LENGTH}) continue;
        let parsed;
        try {{ parsed = new URL(href); }} catch (_) {{ continue; }}
        if ((parsed.protocol !== 'http:' && parsed.protocol !== 'https:') ||
                parsed.username || parsed.password) continue;
        const rect = element.getBoundingClientRect();
        const style = window.getComputedStyle(element);
        const visible = rect.width > 0 && rect.height > 0 && rect.right > 0 &&
            rect.bottom > 0 && rect.left < window.innerWidth &&
            rect.top < window.innerHeight && element.getClientRects().length > 0 &&
            style.display !== 'none' && style.visibility !== 'hidden' &&
            style.opacity !== '0';
        if (!visible) continue;
        const label = (element.innerText || element.getAttribute('aria-label') ||
            element.getAttribute('title') || element.textContent || '')
            .replace(/\\s+/g, ' ').trim().slice(0, 500);
        links.push({{index, href, label}});
    }}
    return links;
}}"""


_HUMAN_LINK_RESOLVE_JS = f"""index => {{
    if (!Number.isInteger(index) || index < 0) return null;
    const anchors = document.getElementsByTagName('a');
    if (index >= Math.min(anchors.length, {MAX_HUMAN_LINK_SCAN})) return null;
    const element = anchors[index];
    if (!element || !element.hasAttribute('href')) return null;
    const href = element.href || '';
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    const visible = rect.width > 0 && rect.height > 0 && rect.right > 0 &&
        rect.bottom > 0 && rect.left < window.innerWidth &&
        rect.top < window.innerHeight && element.getClientRects().length > 0 &&
        style.display !== 'none' && style.visibility !== 'hidden' &&
        style.opacity !== '0';
    const label = (element.innerText || element.getAttribute('aria-label') ||
        element.getAttribute('title') || element.textContent || '')
        .replace(/\\s+/g, ' ').trim().slice(0, 500);
    return {{index, href, label, visible}};
}}"""


def _bounded_human_link_text(raw: str) -> str:
    bounded = []
    used_units = 0
    for character in raw:
        units = 2 if ord(character) > 0xFFFF else 1
        if used_units + units > MAX_HUMAN_LINK_LABEL_LENGTH:
            break
        bounded.append(character)
        used_units += units
    return "".join(bounded)


def _safe_human_link_label(value: Any, destination: str) -> str:
    """Return plain, bounded UI text for a page link."""
    raw = value if isinstance(value, str) else ""
    raw = sanitize_sensitive(raw)
    raw = redact_browser_url_queries(raw)
    raw = re.sub(r"[\x00-\x1f\x7f]", " ", raw)
    raw = " ".join(raw.split())
    label = _bounded_human_link_text(raw)
    return label or _bounded_human_link_text(destination)


def _approved_human_link_destination(value: Any) -> str | None:
    """Return a redacted display URL only when current browser policy allows it."""
    if (not isinstance(value, str) or not value
            or len(value) > MAX_HUMAN_LINK_URL_LENGTH
            or any(ord(char) < 0x20 or ord(char) == 0x7f for char in value)):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            return None
        _ = parsed.port
    except ValueError:
        return None

    import browser_surface

    host = parsed.hostname
    if browser_surface._is_platform_internal_host(host):
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if browser_surface._is_internal_host(host):
            return None

    policy = browser_surface.evaluate_navigation(value)
    if not isinstance(policy, dict) or policy.get("allowed") is not True:
        return None
    return safe_browser_display_url(value) or None


class BrowserSessionBindingError(ValueError):
    """The requested task/run binding conflicts with the immutable session binding."""

    def __init__(self, code: str = "BROWSER_TASK_BINDING_CONFLICT"):
        super().__init__(code)
        self.code = code


class FailureClass(str, Enum):
    """失败分类（用于 Recovery 决策）。"""
    PAGE_ERROR = "page_error"           # 404/500/崩溃
    SELECTOR_ERROR = "selector_error"   # 元素找不到
    SESSION_ERROR = "session_error"     # 登录失效/Cookie过期
    NETWORK_ERROR = "network_error"     # 网络错误
    TIMEOUT_ERROR = "timeout_error"     # 超时
    UNKNOWN_STATE = "unknown_state"     # 未知状态
    PERMISSION_DENIED = "permission_denied"  # 越权/只读保护拦截


# ═══════════════════════════════════════════════════════════════
# 2. 敏感凭证脱敏器（Credential Sanitizer）
# ═══════════════════════════════════════════════════════════════

# 敏感信息正则模式（用于从页面内容/DOM/日志/Evidence中脱敏）
_SENSITIVE_PATTERNS = [
    # Consume the complete credential value before generic key/token patterns.
    # Deliberately conservative for unquoted header lines; this is not an
    # exhaustive secret detector and may remove adjacent same-line prose.
    (r"(?i)\b(?:proxy-)?authorization[\"']?\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\r\n}]+)",
     'Authorization=[REDACTED]'),
    (r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9_+/=.-]+", '[AUTH_REDACTED]'),
    (r"(?i)\b(signature|x-amz-signature)[\"']?\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\r\n}]+)",
     r'\1=[REDACTED]'),
    # Browser content signatures and anti-CSRF values are never research material.
    (r'(?i)\b(xsec_token|csrf[_-]?token|xsrf[_-]?token|authorization|x-amz-signature|signature)\s*["\']?\s*[:=]\s*["\']?[^"\'\s,;}]+',
     r'\1=[REDACTED]'),
    # JWT format (xxx.yyy.zzz) — 先匹配，避免被其他模式截断
    (r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b', '[JWT_REDACTED]'),
    # JSON 格式的敏感键值对："token":"value" / 'cookie': 'value'
    (r'(?i)["\'](cookie|session[_-]?id|sessionid|session|token|access[_-]?token|refresh[_-]?token|api[_-]?key|secret[_-]?key|auth[_-]?token|password|passwd|pwd|oauth[_-]?token|client[_-]?secret|client[_-]?id|bearer)["\']\s*:\s*["\'][^"\']*["\']',
     r'"\1":[REDACTED]'),
    # Cookie / Session 值（key=value 格式）
    (r'(?i)\b(cookie|session[_-]?id|sessionid|session|jsessionid|phpsessid)\s*=\s*["\']?[A-Za-z0-9_\-\.]+["\']?',
     r'\1=[REDACTED]'),
    # Cookie 头中的 Set-Cookie: key=value 格式
    (r'(?i)(set-cookie|cookie)\s*:\s*([A-Za-z0-9_\-]+)=[A-Za-z0-9_\-\.%]+',
     r'\1: \2=[REDACTED]'),
    # Token / Bearer / API Key (header 格式: token: value)
    (r'(?i)\b(bearer|token|access[_-]?token|refresh[_-]?token|api[_-]?key|secret[_-]?key|auth[_-]?token)\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]+["\']?',
     r'\1=[REDACTED]'),
    # Password / Passwd
    (r'(?i)\b(password|passwd|pwd)\s*[:=]\s*["\']?[^"\'\s,;}]+["\']?',
     r'\1=[REDACTED]'),
    # OAuth
    (r'(?i)\b(oauth[_-]?token|client[_-]?secret|client[_-]?id)\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]+["\']?',
     r'\1=[REDACTED]'),
    # AWS / 云密钥
    (r'(?i)(aws[_-]?access[_-]?key|aws[_-]?secret[_-]?key|AKIA[0-9A-Z]{16})',
     '[CLOUD_KEY_REDACTED]'),
    # 手机号（中国）
    (r'\b1[3-9]\d{9}\b', '[PHONE_REDACTED]'),
    # 身份证号
    (r'\b[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b',
     '[ID_CARD_REDACTED]'),
    # 邮箱（部分脱敏）
    (r'\b([a-zA-Z0-9._%+-]{1,3})[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
     r'\1***@\2'),
]

_COMPILED_SENSITIVE = [(re.compile(p), r) for p, r in _SENSITIVE_PATTERNS]


def sanitize_sensitive(text: str) -> str:
    """对文本中的敏感凭证进行脱敏。

    任何进入 AI Context / Evidence / Logs 的页面内容必须经过此函数。
    """
    if not text:
        return text or ""
    result = text
    for pattern, replacement in _COMPILED_SENSITIVE:
        result = pattern.sub(replacement, result)
    return result


def safe_browser_display_url(value: Any) -> str:
    """Show a page address without URL credentials, query tokens or fragments."""
    if value == "about:blank":
        return value
    if not isinstance(value, str):
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return ""
        host = parsed.hostname
        if ":" in host:
            host = f"[{host}]"
        netloc = f"{host}:{parsed.port}" if parsed.port else host
        return sanitize_sensitive(urlunsplit((parsed.scheme, netloc, parsed.path, "", "")))
    except ValueError:
        return ""


_BROWSER_URL_IN_TEXT = re.compile(r"""https?://[^\s\"'<>]+""", re.IGNORECASE)


def redact_browser_url_queries(value: str) -> str:
    """Remove URL queries/fragments from browser error text before storage/logging."""
    if not value:
        return value or ""

    def redact(match: re.Match) -> str:
        candidate = match.group(0)
        suffix = ""
        while candidate and candidate[-1] in ".,;:)]}":
            suffix = candidate[-1] + suffix
            candidate = candidate[:-1]
        display = safe_browser_display_url(candidate)
        return (display or "[browser URL redacted]") + suffix

    return _BROWSER_URL_IN_TEXT.sub(redact, value)


# 敏感 key 列表（用于 sanitize_dict 中按 key 脱敏值）
_SENSITIVE_KEYS = {
    "cookie", "cookies", "session", "session_id", "sessionid", "token",
    "access_token", "refresh_token", "api_key", "secret_key", "auth_token",
    "password", "passwd", "pwd", "oauth_token", "client_secret", "client_id",
    "bearer", "authorization", "secret", "credential", "credentials",
    "aws_access_key", "aws_secret_key", "private_key",
}


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """递归对字典中的字符串值进行脱敏。

    两种脱敏策略：
    1. 值内容脱敏：对字符串值运行 sanitize_sensitive（匹配 key=value 模式）
    2. 敏感 key 脱敏：当 key 本身是敏感字段名时，值直接替换为 [REDACTED]
    """
    if not isinstance(data, dict):
        return data
    result = {}
    for k, v in data.items():
        key_lower = k.lower() if isinstance(k, str) else ""
        if isinstance(v, str):
            # 敏感 key：值直接脱敏
            if key_lower in _SENSITIVE_KEYS:
                result[k] = "[REDACTED]"
            else:
                result[k] = sanitize_sensitive(v)
        elif isinstance(v, dict):
            result[k] = sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [sanitize_dict(i) if isinstance(i, dict)
                          else (sanitize_sensitive(i) if isinstance(i, str) else i)
                          for i in v]
        else:
            result[k] = v
    return result


def hash_state(state: Dict[str, Any]) -> str:
    """对页面状态生成哈希摘要（不含Cookie/Token，用于Evidence中的before/after对比）。"""
    # 只取安全字段
    safe_fields = {}
    for key in ("url", "title", "status_code", "element_count", "body_text_hash",
                "visible_text_hash", "loading", "error"):
        if key in state:
            val = state[key]
            if isinstance(val, str):
                safe_fields[key] = sanitize_sensitive(val)
            else:
                safe_fields[key] = val
    raw = json.dumps(safe_fields, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════
# 3. Prompt Injection 防护
# ═══════════════════════════════════════════════════════════════

# 注入检测模式（复用 agent_security.py 的模式，独立编译避免耦合）
_INJECTION_PATTERNS = [
    (r'(?i)\bignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|commands?)\b', 'direct_override'),
    (r'(?i)\bdisregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)\b', 'direct_override'),
    (r'(?i)\bforget\s+(everything|all|your\s+instructions?|your\s+rules?)\b', 'direct_override'),
    (r'(?i)\byou\s+are\s+now\b', 'identity_hijack'),
    (r'(?i)\bfrom\s+now\s+on\s+you\s+are\b', 'identity_hijack'),
    (r'(?i)\bact\s+as\s+(if\s+you\s+are\s+)?(a\s+)?(system|admin|developer|root)\b', 'privilege_escalation'),
    (r'(?i)\b(reveal|show|display|print|output|repeat|echo|recite|summarize|extract)\s+(your\s+)?(system\s+)?(prompt|instructions?|rules?|initial\s+message)\b', 'prompt_extraction'),
    (r'(?i)\bwhat\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions?|rules?)\b', 'prompt_extraction'),
    (r'(?i)\b(send|email|post|upload|transfer|exfiltrate)\s+(the\s+|your\s+)?(data|content|information|cookies?|tokens?|secrets?|keys?|passwords?)\b', 'data_exfiltration'),
    (r'(?i)\b(upload|send|transfer)\s+(your\s+|the\s+)?(cookie|token|password|secret|credential)\b', 'credential_theft'),
    (r'(?i)\b(execute|perform|make)\s+(a\s+)?(payment|transaction|purchase|order)\b', 'financial_action'),
    (r'(?i)\bdisable\s+(the\s+|all\s+)?(safety|security|protection|filter|guard|firewall)\b', 'safety_disable'),
    (r'(?i)\b(turn\s+off|switch\s+off|bypass|override)\s+(the\s+|all\s+)?(safety|security|protection|permission|firewall)\b', 'safety_disable'),
    (r'(?i)\b(grant|give|elevate|escalate)\s+(admin|root|superuser|full)\s+(access|permission|privilege)\b', 'privilege_escalation'),
    (r'(?i)\b(grant|give|elevate|escalate)\s+(the\s+)?(admin|root|superuser)\b', 'privilege_escalation'),
    (r'(?i)\b(follow|obey|comply\s+with)\s+(these|the\s+following|new)\s+(instructions?|rules?|commands?)\b', 'instruction_replacement'),
    # 中文注入模式
    (r'忽略(之前|上述|前面|所有|全部)(的)?(所有|全部)?(指令|提示|规则|命令)', 'direct_override_zh'),
    (r'忘记(你的|所有|全部)(的)?(指令|规则|提示)', 'direct_override_zh'),
    (r'你现在是(系统|管理员|开发者|root|超级用户)', 'identity_hijack_zh'),
    (r'(上传|发送|泄露|导出)(你的|系统的|所有)?(cookie|token|密码|密钥|凭证|cookies|tokens)', 'credential_theft_zh'),
    (r'(执行|进行|发起)(付款|支付|转账|交易|购买|下单)', 'financial_action_zh'),
    (r'(关闭|禁用|绕过|解除|跳过)(安全|防护|权限|防火墙|过滤|验证)', 'safety_disable_zh'),
    (r'(提升|授予|给予|获取)(管理员|root|超级用户|全部|所有)(的)?(权限|访问|特权)', 'privilege_escalation_zh'),
    (r'(遵循|遵守|按照)(以下|这些|新的)(指令|规则|命令)', 'instruction_replacement_zh'),
]

_COMPILED_INJECTION = [(re.compile(p), label) for p, label in _INJECTION_PATTERNS]


@dataclass
class InjectionDetection:
    """Prompt Injection 检测结果。"""
    detected: bool
    patterns: List[str] = field(default_factory=list)
    original_snippet: str = ""
    sanitized_text: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PromptInjectionGuard:
    """网页内容 Prompt Injection 防护器。

    网页内容 = Untrusted Input。网页中的指令不得覆盖 System Policy /
    Permission / Action Firewall。
    """

    def __init__(self):
        self._detection_log: List[InjectionDetection] = []
        self._lock = threading.Lock()

    def scan(self, text: str, source: str = "web_content") -> InjectionDetection:
        """扫描文本中的 Prompt Injection 模式。

        Args:
            text: 待扫描文本（通常是网页内容/DOM文本）
            source: 内容来源标记

        Returns:
            InjectionDetection 结果
        """
        if not text:
            return InjectionDetection(detected=False, sanitized_text="")

        detected_patterns = []
        for pattern, label in _COMPILED_INJECTION:
            if pattern.search(text):
                detected_patterns.append(label)

        # 对检测到注入的文本进行标记（不删除原文，而是标记为untrusted）
        sanitized = text
        if detected_patterns:
            # 保留原文但标记来源为不可信
            sanitized = f"[UNTRUSTED_WEB_CONTENT] {text}"
            logger.warning(
                f"[PromptInjectionGuard] 检测到注入模式: {detected_patterns} "
                f"source={source}"
            )

        result = InjectionDetection(
            detected=bool(detected_patterns),
            patterns=detected_patterns,
            original_snippet=sanitize_sensitive(text[:200]),
            sanitized_text=sanitize_sensitive(sanitized),
        )

        with self._lock:
            self._detection_log.append(result)
            if len(self._detection_log) > 1000:
                self._detection_log = self._detection_log[-1000:]

        return result

    def is_safe_for_ai_context(self, text: str) -> bool:
        """判断文本是否安全进入 AI Context（有注入模式仍可进入，但必须标记）。"""
        result = self.scan(text)
        # 注入内容可以进入 AI Context，但必须被标记为 untrusted
        # 关键是：AI 不能因为网页内容而提升权限或执行越权操作
        return True  # 始终允许进入，但调用方必须使用 sanitized_text

    def get_detection_stats(self) -> Dict[str, Any]:
        """获取检测统计。"""
        with self._lock:
            total = len(self._detection_log)
            detected = sum(1 for d in self._detection_log if d.detected)
            pattern_counts: Dict[str, int] = {}
            for d in self._detection_log:
                for p in d.patterns:
                    pattern_counts[p] = pattern_counts.get(p, 0) + 1
        return {
            "total_scans": total,
            "injections_detected": detected,
            "detection_rate": f"{(detected / total * 100):.1f}%" if total else "0%",
            "top_patterns": sorted(pattern_counts.items(), key=lambda x: -x[1])[:10],
        }


# 全局单例
_default_injection_guard: Optional[PromptInjectionGuard] = None


def get_injection_guard() -> PromptInjectionGuard:
    global _default_injection_guard
    if _default_injection_guard is None:
        _default_injection_guard = PromptInjectionGuard()
    return _default_injection_guard


# ═══════════════════════════════════════════════════════════════
# 4. Action Firewall（只读保护 / 越权拦截）
# ═══════════════════════════════════════════════════════════════

# 小红书等平台官方账号只读保护：禁止的写操作选择器/文本
_READONLY_BLOCKED_ACTIONS = {
    "follow", "unfollow", "like", "unlike", "collect", "uncollect",
    "comment", "publish", "post", "share", "dm", "message", "私信",
    "关注", "取关", "点赞", "收藏", "评论", "发布", "转发",
    "logout", "switch_account", "退出登录", "切换账号",
    "settings", "修改资料", "edit_profile",
}

# 写操作按钮的常见选择器特征（用于智能检测）
_WRITE_ACTION_INDICATORS = [
    r'(?i)(follow|following|fans|like|heart|collect|bookmark|star|comment|publish|post|share|send|submit)\b',
    r'(关注|粉丝|点赞|喜欢|收藏|评论|发布|转发|发送|提交)',
]


class ActionFirewall:
    """Browser Action 防火墙。

    硬红线：小红书等平台官方账号一律只读，禁止任何写操作。
    网页内容无法提升权限。
    """

    def __init__(self, readonly_mode: bool = True):
        self.readonly_mode = readonly_mode
        self._blocked_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def check_action(
        self,
        action_type: BrowserActionType,
        target: str = "",
        selector: str = "",
        text: str = "",
        url: str = "",
    ) -> Tuple[bool, str]:
        """检查 Action 是否被防火墙允许。

        Returns:
            (allowed, reason)
        """
        # 上传操作始终需要 L3 人工审批
        if action_type == BrowserActionType.UPLOAD:
            return False, "UPLOAD 操作需要 L3 人工审批（Action Firewall）"

        if not self.readonly_mode:
            return True, "readonly_mode=False"

        # 检查目标描述中的写操作关键词
        combined = f"{target} {selector} {text}".lower()
        for blocked in _READONLY_BLOCKED_ACTIONS:
            if blocked in combined:
                reason = (
                    f"Action Firewall 拦截：检测到写操作关键词 '{blocked}'。"
                    f"官方账号只读保护生效（AGENTS.md §7）。"
                    f"action={action_type.value}, target={sanitize_sensitive(target[:100])}"
                )
                self._log_blocked(action_type, target, selector, text, reason)
                return False, reason

        # 检查选择器中的写操作指示器
        for indicator in _WRITE_ACTION_INDICATORS:
            if re.search(indicator, combined):
                # 进一步确认：如果是 click/input 操作且指示器匹配，拦截
                if action_type in (BrowserActionType.CLICK, BrowserActionType.INPUT):
                    reason = (
                        f"Action Firewall 拦截：选择器/文本匹配写操作指示器。"
                        f"官方账号只读保护生效。action={action_type.value}"
                    )
                    self._log_blocked(action_type, target, selector, text, reason)
                    return False, reason

        return True, "allowed"

    def _log_blocked(self, action_type, target, selector, text, reason):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action_type.value,
            "target": sanitize_sensitive(target[:200]),
            "selector": sanitize_sensitive(selector[:200]),
            "text": sanitize_sensitive(text[:200]),
            "reason": reason,
        }
        with self._lock:
            self._blocked_log.append(entry)
            if len(self._blocked_log) > 500:
                self._blocked_log = self._blocked_log[-500:]
        logger.warning(f"[ActionFirewall] {reason}")

    def get_blocked_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._blocked_log)
            by_action: Dict[str, int] = {}
            for entry in self._blocked_log:
                a = entry["action"]
                by_action[a] = by_action.get(a, 0) + 1
        return {
            "total_blocked": total,
            "readonly_mode": self.readonly_mode,
            "by_action": by_action,
            "recent": self._blocked_log[-10:] if self._blocked_log else [],
        }


# 全局单例
_default_firewall: Optional[ActionFirewall] = None


def get_action_firewall() -> ActionFirewall:
    global _default_firewall
    if _default_firewall is None:
        _default_firewall = ActionFirewall(readonly_mode=True)
    return _default_firewall


# ═══════════════════════════════════════════════════════════════
# 5. Browser Evidence 存储
# ═══════════════════════════════════════════════════════════════

BROWSER_EVIDENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS browser_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    run_id TEXT,
    step_id TEXT,
    agent_id TEXT,
    skill_id TEXT,
    session_id TEXT,
    action TEXT NOT NULL,
    target TEXT,
    selector TEXT,
    timestamp TEXT NOT NULL,
    before_state TEXT,
    after_state TEXT,
    before_state_hash TEXT,
    after_state_hash TEXT,
    result TEXT NOT NULL,
    evidence_path TEXT,
    dom_snapshot TEXT,
    console_errors TEXT,
    verification TEXT,
    expected_state TEXT,
    actual_state TEXT,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    recovery_strategy TEXT,
    risk_level TEXT DEFAULT 'medium',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_browser_evidence_session ON browser_evidence(session_id);
CREATE INDEX IF NOT EXISTS idx_browser_evidence_task ON browser_evidence(task_id);
CREATE INDEX IF NOT EXISTS idx_browser_evidence_result ON browser_evidence(result);
CREATE INDEX IF NOT EXISTS idx_browser_evidence_timestamp ON browser_evidence(timestamp);
"""


def init_browser_evidence_db() -> bool:
    """初始化 browser_evidence 表（向后兼容，CREATE IF NOT EXISTS）。"""
    try:
        os.makedirs(os.path.dirname(main_db_path()), exist_ok=True)
        conn = get_repository().connect(timeout=30)
        conn.executescript(BROWSER_EVIDENCE_SCHEMA)
        conn.commit()
        conn.close()
        logger.info("[BrowserEvidence] browser_evidence 表初始化完成（向后兼容）")
        return True
    except Exception as e:
        logger.error(f"[BrowserEvidence] 表初始化失败: {e}")
        return False


@dataclass
class BrowserEvidenceRecord:
    """单条 Browser Evidence 记录。"""
    action: str
    timestamp: str
    result: str
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    agent_id: Optional[str] = None
    skill_id: Optional[str] = None
    session_id: Optional[str] = None
    target: Optional[str] = None
    selector: Optional[str] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    before_state_hash: Optional[str] = None
    after_state_hash: Optional[str] = None
    evidence_path: Optional[str] = None
    dom_snapshot: Optional[str] = None
    console_errors: Optional[str] = None
    verification: Optional[str] = None
    expected_state: Optional[str] = None
    actual_state: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    recovery_strategy: Optional[str] = None
    risk_level: str = "medium"


class BrowserEvidenceStore:
    """Browser Evidence 存储层。

    每个关键 Action 都记录 Evidence，包含 before/after 状态、
    验证结果、截图路径、错误信息（全部脱敏）。
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or main_db_path()
        self._screenshot_dir = EVIDENCE_SCREENSHOT_DIR
        os.makedirs(self._screenshot_dir, exist_ok=True)
        # 使用实例 db_path 初始化表（向后兼容）
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = DatabaseRepository(self.db_path).connect(timeout=30)
        conn.executescript(BROWSER_EVIDENCE_SCHEMA)
        conn.commit()
        conn.close()

    def record(self, record: BrowserEvidenceRecord) -> int:
        """写入一条 Evidence 记录。所有字符串字段自动脱敏。"""
        # 脱敏处理
        safe_target = sanitize_sensitive(record.target or "")[:500]
        safe_selector = sanitize_sensitive(record.selector or "")[:500]
        safe_before = sanitize_sensitive(record.before_state or "")[:2000]
        safe_after = sanitize_sensitive(record.after_state or "")[:2000]
        safe_dom = sanitize_sensitive(record.dom_snapshot or "")[:3000]
        safe_console = sanitize_sensitive(record.console_errors or "")[:2000]
        safe_verification = sanitize_sensitive(record.verification or "")[:2000]
        safe_expected = sanitize_sensitive(record.expected_state or "")[:1000]
        safe_actual = sanitize_sensitive(record.actual_state or "")[:1000]
        safe_error = sanitize_sensitive(record.error or "")[:1000]
        safe_recovery = sanitize_sensitive(record.recovery_strategy or "")[:500]

        try:
            conn = DatabaseRepository(self.db_path).connect(timeout=30)
            cursor = conn.execute("""
                INSERT INTO browser_evidence (
                    task_id, run_id, step_id, agent_id, skill_id, session_id,
                    action, target, selector, timestamp,
                    before_state, after_state, before_state_hash, after_state_hash,
                    result, evidence_path, dom_snapshot, console_errors,
                    verification, expected_state, actual_state, error,
                    retry_count, recovery_strategy, risk_level
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                record.task_id, record.run_id, record.step_id,
                record.agent_id, record.skill_id, record.session_id,
                record.action, safe_target, safe_selector, record.timestamp,
                safe_before, safe_after, record.before_state_hash, record.after_state_hash,
                record.result, record.evidence_path, safe_dom, safe_console,
                safe_verification, safe_expected, safe_actual, safe_error,
                record.retry_count, safe_recovery, record.risk_level,
            ))
            conn.commit()
            row_id = cursor.lastrowid
            conn.close()
            logger.debug(
                f"[BrowserEvidence] 记录 #{row_id}: action={record.action} "
                f"result={record.result} session={record.session_id}"
            )
            return row_id
        except Exception as e:
            logger.error(f"[BrowserEvidence] 写入失败: {e}")
            return -1

    def query(
        self,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        result: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """查询 Evidence 记录。"""
        try:
            conn = DatabaseRepository(self.db_path).connect(timeout=30)
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM browser_evidence WHERE 1=1"
            params: List[Any] = []
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)
            if result:
                query += " AND result = ?"
                params.append(result)
            if action:
                query += " AND action = ?"
                params.append(action)
            query += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[BrowserEvidence] 查询失败: {e}")
            return []

    def get_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取 Evidence 统计。"""
        try:
            conn = DatabaseRepository(self.db_path).connect(timeout=30)
            base_query = "SELECT result, COUNT(*) as cnt FROM browser_evidence"
            params: List[Any] = []
            if session_id:
                base_query += " WHERE session_id = ?"
                params.append(session_id)
            base_query += " GROUP BY result"
            rows = conn.execute(base_query, params).fetchall()
            total = sum(r[1] for r in rows)
            conn.close()
            return {
                "total": total,
                "by_result": {r[0]: r[1] for r in rows},
                "pass_rate": f"{(sum(r[1] for r in rows if r[0] == 'PASS') / total * 100):.1f}%" if total else "0%",
            }
        except Exception as e:
            logger.error(f"[BrowserEvidence] 统计失败: {e}")
            return {"total": 0, "by_result": {}, "pass_rate": "0%"}

    def save_screenshot(self, screenshot_bytes: bytes, session_id: str, action: str) -> str:
        """保存 Evidence 截图，返回相对路径。"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{session_id}_{action}_{timestamp}_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(self._screenshot_dir, filename)
            with open(filepath, "wb") as f:
                f.write(screenshot_bytes)
            return filepath
        except Exception as e:
            logger.error(f"[BrowserEvidence] 截图保存失败: {e}")
            return ""


# 全局单例
_default_evidence_store: Optional[BrowserEvidenceStore] = None


def get_evidence_store() -> BrowserEvidenceStore:
    global _default_evidence_store
    if _default_evidence_store is None:
        _default_evidence_store = BrowserEvidenceStore()
    return _default_evidence_store


# ═══════════════════════════════════════════════════════════════
# 6. Action Verifier（验证闭环）
# ═══════════════════════════════════════════════════════════════

@dataclass
class ExpectedState:
    """Action 执行后期望的状态变化定义。"""
    url_contains: Optional[str] = None          # URL 应包含
    url_equals: Optional[str] = None             # URL 应等于
    title_contains: Optional[str] = None         # Title 应包含
    element_visible: Optional[str] = None        # 元素应可见（selector）
    element_text: Optional[Tuple[str, str]] = None  # (selector, expected_text)
    input_value: Optional[Tuple[str, str]] = None   # (selector, expected_value)
    element_count_gte: Optional[Tuple[str, int]] = None  # (selector, min_count)
    text_present: Optional[str] = None           # 页面应包含文本
    text_absent: Optional[str] = None            # 页面应不包含文本
    status_code: Optional[int] = None            # HTTP 状态码
    loading_complete: bool = True                 # 页面应加载完成
    custom_check: Optional[str] = None            # 自定义检查描述


@dataclass
class VerificationResult:
    """验证结果。"""
    passed: bool
    expected: Dict[str, Any]
    actual: Dict[str, Any]
    differences: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ActionVerifier:
    """Action 验证器：Expected → Actual → Verify → PASS/FAIL。

    硬要求：禁止 AI 说"点击成功"就认定成功。必须经过状态比对。
    """

    def __init__(self):
        pass

    def verify(
        self,
        expected: ExpectedState,
        actual_state: Dict[str, Any],
    ) -> VerificationResult:
        """比对期望状态与实际状态。

        Args:
            expected: 期望的状态变化
            actual_state: 实际页面状态（url/title/elements/status_code等）

        Returns:
            VerificationResult
        """
        differences = []
        actual_url = actual_state.get("url", "")
        actual_title = actual_state.get("title", "")
        actual_status = actual_state.get("status_code")
        actual_loading = actual_state.get("loading")
        actual_text = actual_state.get("body_text", "")
        actual_elements = actual_state.get("elements", {})  # selector -> {visible, text, value, count}

        expected_dict = asdict(expected)

        if actual_state.get("error"):
            differences.append("页面观察失败，无法确认操作结果")

        # 1. URL 检查
        if expected.url_equals and actual_url != expected.url_equals:
            differences.append("URL不匹配")
        if expected.url_contains and expected.url_contains not in actual_url:
            differences.append("URL不包含要求的内容")

        # 2. Title 检查
        if expected.title_contains and expected.title_contains not in actual_title:
            differences.append(
                f"Title不包含: expected={expected.title_contains}, actual={actual_title}"
            )

        # 3. 元素可见性检查
        if expected.element_visible:
            elem = actual_elements.get(expected.element_visible, {})
            if elem.get("visible") is not True:
                differences.append(
                    f"元素不可见: selector={expected.element_visible}"
                )

        # 4. 元素文本检查
        if expected.element_text:
            selector, exp_text = expected.element_text
            elem = actual_elements.get(selector, {})
            actual_elem_text = elem.get("text")
            if not isinstance(actual_elem_text, str) or not isinstance(exp_text, str) or exp_text not in actual_elem_text:
                differences.append(
                    f"元素文本不匹配: selector={selector}, "
                    f"expected_contains={exp_text}, actual={str(actual_elem_text)[:100]}"
                )

        # 5. Input value 检查
        if expected.input_value:
            selector, exp_value = expected.input_value
            elem = actual_elements.get(selector, {})
            actual_value = elem.get("value")
            if exp_value != actual_value:
                differences.append(
                    f"Input值不匹配: selector={selector}, "
                    f"expected={exp_value}, actual={actual_value}"
                )

        # 6. 元素数量检查
        if expected.element_count_gte:
            selector, min_count = expected.element_count_gte
            elem = actual_elements.get(selector, {})
            actual_count = elem.get("count")
            if type(min_count) is not int or min_count < 0 or type(actual_count) is not int or actual_count < min_count:
                differences.append(
                    f"元素数量不足: selector={selector}, "
                    f"expected>={min_count}, actual={actual_count}"
                )

        # 7. 文本存在检查
        if expected.text_present and expected.text_present not in actual_text:
            differences.append(
                f"页面文本不存在: expected={expected.text_present}"
            )

        # Missing/truncated text cannot prove that a requested string is absent.
        if expected.text_absent and ("body_text" not in actual_state or
                "body_text" in actual_state.get("truncated_fields", []) or
                "body_text" in actual_state.get("observation_errors", {})):
            differences.append("正文不完整，无法验证文本不存在")
        if expected.custom_check is not None:
            differences.append("自定义检查未绑定实际验证器")

        # 8. 文本不存在检查
        if expected.text_absent and expected.text_absent in actual_text:
            differences.append(
                f"页面文本不应存在: absent={expected.text_absent}"
            )

        # 9. 状态码检查
        if expected.status_code is not None and (type(actual_status) is not int or actual_status != expected.status_code):
            differences.append(
                f"状态码不匹配: expected={expected.status_code}, actual={actual_status}"
            )

        # 10. 加载完成检查
        if expected.loading_complete and actual_loading is not False:
            differences.append("页面加载未证实完成（loading不是明确false）")

        passed = len(differences) == 0
        # Full URLs are used above only for comparisons. Verification is also
        # persisted in Evidence, so query credentials must not escape here.
        expected_dict["url_equals"] = (
            safe_browser_display_url(expected.url_equals) if expected.url_equals else None
        )
        expected_dict["url_contains"] = "[REDACTED]" if expected.url_contains else None

        return VerificationResult(
            passed=passed,
            expected=expected_dict,
            actual={
                "url": safe_browser_display_url(actual_url),
                "title": sanitize_sensitive(actual_title),
                "status_code": actual_status,
                "loading": actual_loading,
            },
            differences=differences,
        )


# ═══════════════════════════════════════════════════════════════
# 7. Failure Recovery + Circuit Breaker
# ═══════════════════════════════════════════════════════════════

class CircuitBreaker:
    """熔断器：连续失败 N 次后熔断，冷却后恢复。"""

    def __init__(
        self,
        failure_threshold: int = CB_FAILURE_THRESHOLD,
        cooldown_seconds: int = CB_COOLDOWN_SECONDS,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._open = False
        self._lock = threading.Lock()

    def record_success(self):
        """记录成功，重置失败计数。"""
        with self._lock:
            self._failure_count = 0
            self._open = False

    def record_failure(self) -> bool:
        """记录失败。返回 True 表示触发熔断。"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._open = True
                logger.warning(
                    f"[CircuitBreaker] 熔断触发: failure_count={self._failure_count}, "
                    f"threshold={self.failure_threshold}"
                )
                return True
            return False

    def is_open(self) -> bool:
        """检查熔断器是否打开（熔断中）。"""
        with self._lock:
            if not self._open:
                return False
            # 检查冷却期是否已过
            if self._last_failure_time and (time.time() - self._last_failure_time) > self.cooldown_seconds:
                self._open = False
                self._failure_count = 0
                logger.info("[CircuitBreaker] 冷却期已过，熔断器半开（允许试探性请求）")
                return False
            return True

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "open": self._open,
                "failure_count": self._failure_count,
                "threshold": self.failure_threshold,
                "cooldown_seconds": self.cooldown_seconds,
                "last_failure_time": (
                    datetime.fromtimestamp(self._last_failure_time).isoformat()
                    if self._last_failure_time else None
                ),
            }

    def reset(self):
        """强制重置熔断器。"""
        with self._lock:
            self._failure_count = 0
            self._open = False
            self._last_failure_time = None


@dataclass
class RecoveryAttempt:
    """一次 Recovery 尝试记录。"""
    strategy: str
    success: bool
    detail: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class FailureRecovery:
    """失败恢复器：Retry → Alternative Selector → Alternative Strategy → Recovery → Human Escalation。"""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker()
        self._recovery_log: List[RecoveryAttempt] = []

    def classify_failure(self, error: Exception, context: Dict[str, Any]) -> FailureClass:
        """根据错误信息和上下文分类失败类型。

        分类顺序很重要：越具体的类型越先检查。
        """
        error_str = str(error).lower()

        # 1. 权限拒绝（最高优先级，不重试）
        if any(kw in error_str for kw in ["permission", "denied", "readonly", "firewall", "blocked", "forbidden"]):
            return FailureClass.PERMISSION_DENIED

        # 2. 网络错误（econn/enotfound/dns 等具体网络错误）
        if any(kw in error_str for kw in ["econn", "enotfound", "econnrefused", "econnreset",
                                             "dns", "network error", "connection refused",
                                             "connection reset", "name or service not known"]):
            return FailureClass.NETWORK_ERROR

        # 3. 选择器错误（元素找不到/不可见/等待选择器超时）
        if any(kw in error_str for kw in ["selector", "element not found", "no element found",
                                             "not visible", "waiting for selector", "strict mode violation",
                                             "element was detached"]):
            return FailureClass.SELECTOR_ERROR

        # 4. Session 错误（登录失效/Cookie过期/未授权）
        if any(kw in error_str for kw in ["session expired", "cookie expired", "login required",
                                             "unauthorized", "401", "403", "need login",
                                             "session invalid", "authentication failed"]):
            return FailureClass.SESSION_ERROR

        # 5. 页面错误（404/500/崩溃）— 注意 "not found" 只有在不是 element/enotfound 时才算页面错误
        if any(kw in error_str for kw in ["404", "500", "server error", "page crash",
                                             "crashed", "page.goto", "net::err", "ERR_NAME_NOT_RESOLVED"]):
            return FailureClass.PAGE_ERROR

        # 6. 超时错误
        if any(kw in error_str for kw in ["timeout", "exceeded", "timed out", "time out"]):
            return FailureClass.TIMEOUT_ERROR

        # 7. 通用网络连接问题
        if any(kw in error_str for kw in ["connection", "network", "disconnected"]):
            return FailureClass.NETWORK_ERROR

        return FailureClass.UNKNOWN_STATE

    def get_recovery_strategies(self, failure_class: FailureClass) -> List[str]:
        """根据失败类型返回恢复策略链。"""
        strategies = {
            FailureClass.PAGE_ERROR: [
                "reload_page",
                "navigate_back_then_forward",
                "wait_and_retry",
                "human_escalation",
            ],
            FailureClass.SELECTOR_ERROR: [
                "retry_same_selector",
                "alternative_css_selector",
                "xpath_selector",
                "accessibility_tree",
                "text_match",
                "coordinate_click",
                "scroll_then_click",
                "human_escalation",
            ],
            FailureClass.SESSION_ERROR: [
                "mark_need_verify",
                "wait_for_human_reauth",
                "human_escalation",
            ],
            FailureClass.NETWORK_ERROR: [
                "retry_exponential_backoff",
                "retry_exponential_backoff_2",
                "reload_page",
                "human_escalation",
            ],
            FailureClass.TIMEOUT_ERROR: [
                "increase_timeout_retry",
                "wait_for_network_idle",
                "reload_page",
                "human_escalation",
            ],
            FailureClass.PERMISSION_DENIED: [
                "human_escalation",  # 权限拒绝直接升级人工，不重试
            ],
            FailureClass.UNKNOWN_STATE: [
                "stop_and_capture_evidence",
                "human_escalation",
            ],
        }
        return strategies.get(failure_class, ["human_escalation"])

    def log_recovery(self, strategy: str, success: bool, detail: str = ""):
        attempt = RecoveryAttempt(strategy=strategy, success=success, detail=sanitize_sensitive(detail[:300]))
        self._recovery_log.append(attempt)
        if len(self._recovery_log) > 500:
            self._recovery_log = self._recovery_log[-500:]

    def get_recovery_stats(self) -> Dict[str, Any]:
        total = len(self._recovery_log)
        success = sum(1 for r in self._recovery_log if r.success)
        by_strategy: Dict[str, int] = {}
        for r in self._recovery_log:
            by_strategy[r.strategy] = by_strategy.get(r.strategy, 0) + 1
        return {
            "total_attempts": total,
            "success_count": success,
            "success_rate": f"{(success / total * 100):.1f}%" if total else "0%",
            "by_strategy": by_strategy,
            "circuit_breaker": self.circuit_breaker.get_state(),
        }


# ═══════════════════════════════════════════════════════════════
# 8. AI Browser Runtime（核心编排类）
# ═══════════════════════════════════════════════════════════════

@dataclass
class BrowserPageState:
    """页面状态快照（用于 Observe 和 Verification）。"""
    url: str = ""
    title: str = ""
    loading: bool = False
    status_code: Optional[int] = None
    error: Optional[str] = None
    element_count: int | None = None
    body_text: str = ""
    elements: Dict[str, Any] = field(default_factory=dict)
    console_errors: List[str] = field(default_factory=list)
    observation_errors: dict[str, str] = field(default_factory=dict)
    truncated_fields: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["url"] = safe_browser_display_url(self.url)
        d["body_text"] = sanitize_sensitive(self.body_text)[:MAX_OBSERVATION_TEXT_LENGTH]
        return sanitize_dict(d)

    def state_hash(self) -> str:
        return hash_state(self.to_dict())

    def verification_state(self) -> dict[str, Any]:
        """Raw URL is for in-memory comparisons only, never API/Evidence output."""
        return {**self.to_dict(), "url": self.url}


@dataclass
class ActionExecutionResult:
    """Action 执行完整结果（含验证和Evidence）。"""
    success: bool
    action: str
    result: ActionResult
    verification: Optional[VerificationResult] = None
    evidence_id: int = -1
    error: Optional[str] = None
    recovery_attempts: List[RecoveryAttempt] = field(default_factory=list)
    before_state: Optional[BrowserPageState] = None
    after_state: Optional[BrowserPageState] = None
    human_escalation_required: bool = False
    escalation_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "result": self.result.value,
            "verification": self.verification.to_dict() if self.verification else None,
            "evidence_id": self.evidence_id,
            "error": sanitize_sensitive(self.error or ""),
            "recovery_attempts": [asdict(r) for r in self.recovery_attempts],
            "human_escalation_required": self.human_escalation_required,
            "escalation_reason": self.escalation_reason,
        }


class AIBrowserRuntime:
    """AI Browser Runtime 核心编排类。

    调用链：Observe → Reason → Plan → Action → Verify → Evidence → Trace

    本类封装 Playwright 操作，每个 Action 都经过：
    1. Action Firewall 检查（只读保护）
    2. Permission Gate 检查（权限）
    3. 执行前状态捕获（before_state）
    4. Action 执行
    5. 执行后状态捕获（after_state）
    6. Verification 比对（Expected vs Actual）
    7. 失败 Recovery（Retry → Alternative → Human）
    8. Evidence 记录（全链路脱敏）
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        cdp_port: int = 9224,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        owner_actor_id: Optional[int] = None,
        owner_account_session_id: Optional[int] = None,
        owner_principal_ref: Optional[str] = None,
        idle_timeout: int = DEFAULT_SESSION_IDLE_TIMEOUT,
        max_lifetime: int = DEFAULT_SESSION_MAX_LIFETIME,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ):
        self.session_id = session_id or f"bs_{uuid.uuid4().hex[:12]}"
        self.cdp_port = cdp_port
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.owner_actor_id = owner_actor_id
        self.owner_account_session_id = owner_account_session_id
        if owner_principal_ref is not None and owner_principal_ref != "workspace:local":
            raise ValueError("AI Browser principal must be the server-issued local workspace")
        if owner_principal_ref is not None and (
            owner_actor_id is not None or owner_account_session_id is not None
        ):
            raise ValueError("AI Browser account and workspace owners cannot be mixed")
        self.owner_principal_ref = owner_principal_ref
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime
        if (task_id is None) != (run_id is None):
            raise BrowserSessionBindingError("BROWSER_TASK_BINDING_PAIR_REQUIRED")
        for trace_value in (task_id, run_id):
            if trace_value is not None and (
                not isinstance(trace_value, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", trace_value)
            ):
                raise BrowserSessionBindingError("BROWSER_TASK_BINDING_INVALID")
        # These values may be supplied by a UI, but this runtime slice has no
        # server-owned Task/Run resolver. Never use a client claim as Evidence
        # lineage. Keep the claim visible for diagnostics and mark it honestly.
        self.task_id = task_id
        self.run_id = run_id
        self.task_binding_status = "UNVERIFIED" if task_id is not None else "UNBOUND"
        self._server_task_admission = None
        self._server_task_actor = None

        # 状态
        self.status = SessionStatus.CREATED
        self.created_at = time.time()
        self.last_activity = time.time()

        # Playwright 实例（延迟初始化）
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._pages: Dict[str, Any] = {}  # tab_id -> page
        self._target_id: Optional[str] = None
        self._page_revision = 0
        self._latest_frame_binding: Optional[Dict[str, Any]] = None
        self._latest_frame_image_sha256: Optional[str] = None
        # In-memory document identity only; the raw URL is never returned.
        self._latest_frame_document_url: str | None = None
        self._last_navigation_at = 0.0
        self.engine_label = ""

        # Human control is a short-lived, server-owned exclusive lease. Only a
        # digest is retained; the bearer token is returned once and never logged.
        self._control_lock = threading.RLock()
        self._human_control_token_digest: Optional[str] = None
        self._human_control_expires_at = 0.0
        self._active_control_actions = 0
        self._human_link_lock = threading.Lock()
        self._human_link_choices: dict[str, dict[str, Any]] = {}
        self._human_link_frame_binding: dict[str, Any] | None = None
        self._human_link_lease_digest: str | None = None
        self._active_human_link_navigation_guard: dict[str, bool] | None = None

        # 组件
        self.verifier = ActionVerifier()
        self.recovery = FailureRecovery()
        self.evidence_store = get_evidence_store()
        self.firewall = get_action_firewall()
        self.injection_guard = get_injection_guard()

        # 控制台错误捕获
        self._console_errors: List[str] = []

        # 锁
        self._lock = threading.Lock()
        self._closed = False
        self._worker_lock = threading.Lock()
        self._browser_worker: Optional[ThreadPoolExecutor] = None
        self._browser_thread_id: Optional[int] = None

        logger.info(
            f"[AIBrowserRuntime] Session 创建: {self.session_id}, "
            f"cdp_port={cdp_port}, headless={headless}"
        )

    # ──────────────────────────────────────────────────────────
    # Session 生命周期
    # ──────────────────────────────────────────────────────────

    def _run_on_browser_thread(self, operation: Callable[[], Any], *, start_worker: bool = False) -> Any:
        """Keep Playwright's synchronous objects on the thread that created them."""
        if threading.get_ident() == self._browser_thread_id:
            return operation()
        with self._worker_lock:
            if self._browser_worker is None and start_worker and not self._closed:
                self._browser_worker = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="lumenis-ai-browser"
                )
            worker = self._browser_worker
            future = worker.submit(self._browser_thread_operation, operation) if worker else None
        return future.result() if future else operation()

    def _browser_thread_operation(self, operation: Callable[[], Any]) -> Any:
        self._browser_thread_id = threading.get_ident()
        return operation()

    def start(self) -> bool:
        """Attach only to the verified LUMENIS browser and own a fresh context."""
        if self._closed:
            return False
        if threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(self.start, start_worker=True)
        if self.status == SessionStatus.RUNNING:
            return True
        try:
            import browser_surface

            if self.cdp_port != browser_surface.GENERAL_CDP_PORT or not self.headless or self.user_data_dir:
                raise PermissionError("AI Browser requires the isolated LUMENIS browser session")
            ready = browser_surface.ensure_general_browser()
            if not ready.get("ok") or not browser_surface.general_browser_online():
                raise PermissionError("LUMENIS browser session is unavailable or unverified")
            engine = ready.get("browser")
            if engine not in {"chrome", "edge"}:
                raise PermissionError("LUMENIS browser engine is unverified")

            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()

            self._browser = self._playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{self.cdp_port}"
            )
            self._context = self._browser.new_context()
            self._page = self._context.new_page()
            self._target_id = f"bt_{uuid.uuid4().hex}"
            self._page_revision = 0
            self._last_navigation_at = 0.0
            self.engine_label = "Chrome" if engine == "chrome" else "Edge"
            logger.info("[AIBrowserRuntime] 已连接序境隔离浏览器并创建专属页面")

            # 注册控制台错误监听
            if self._page:
                self._page.on("console", self._on_console)
                self._page.on("pageerror", self._on_page_error)

            self.status = SessionStatus.RUNNING
            self.last_activity = time.time()
            return True
        except Exception as e:
            self.status = SessionStatus.ERROR
            try:
                if self._context:
                    self._context.close()
                if self._playwright:
                    self._playwright.stop()
            except Exception:
                pass
            self._page = self._context = self._browser = self._playwright = None
            self._target_id = None
            self.engine_label = ""
            logger.error("[AIBrowserRuntime] 启动失败: %s", sanitize_sensitive(str(e)))
            return False

    def _on_console(self, msg):
        """控制台消息监听（只记录 error 级别）。"""
        try:
            if msg.type == "error":
                self._console_errors.append(sanitize_sensitive(msg.text[:500]))
                if len(self._console_errors) > 100:
                    self._console_errors = self._console_errors[-100:]
        except Exception:
            pass

    def _on_page_error(self, err):
        """页面错误监听。"""
        try:
            self._console_errors.append(f"PAGE_ERROR: {sanitize_sensitive(str(err)[:500])}")
        except Exception:
            pass

    def is_alive(self) -> bool:
        """检查 Session 是否存活（含空闲超时和最大生命周期检查）。"""
        if self._closed:
            return False
        now = time.time()
        # 最大生命周期
        if now - self.created_at > self.max_lifetime:
            logger.info(f"[AIBrowserRuntime] Session 超过最大生命周期，自动关闭: {self.session_id}")
            self.close()
            return False
        # 空闲超时
        if now - self.last_activity > self.idle_timeout:
            logger.info(f"[AIBrowserRuntime] Session 空闲超时，自动关闭: {self.session_id}")
            self.close()
            return False
        return True

    def close(self):
        """关闭 Browser Session，释放资源。"""
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            worker = self._browser_worker
            try:
                return self._run_on_browser_thread(self.close)
            finally:
                worker.shutdown(wait=True)
                with self._worker_lock:
                    if self._browser_worker is worker:
                        self._browser_worker = None
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self.status = SessionStatus.CLOSED
            with self._control_lock:
                self._human_control_token_digest = None
                self._human_control_expires_at = 0.0
            self._invalidate_human_links()
            self._latest_frame_binding = None
            self._latest_frame_image_sha256 = None
            self._latest_frame_document_url = None
            try:
                if self._page:
                    self._page.close()
            except Exception:
                pass
            try:
                if self._context:
                    self._context.close()
            except Exception:
                pass
            try:
                if self._playwright:
                    self._playwright.stop()
            except Exception:
                pass
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._target_id = None
            logger.info(f"[AIBrowserRuntime] Session 已关闭: {self.session_id}")

    def get_status(self) -> Dict[str, Any]:
        """获取 Session 状态。"""
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(self.get_status)
        now = time.time()
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_activity": datetime.fromtimestamp(self.last_activity).isoformat(),
            "idle_seconds": int(now - self.last_activity),
            "lifetime_seconds": int(now - self.created_at),
            "idle_timeout": self.idle_timeout,
            "max_lifetime": self.max_lifetime,
            "current_url": safe_browser_display_url(self._page.url if self._page else ""),
            "current_title": sanitize_sensitive(self._page.title() if self._page else ""),
            "target_id": self._target_id,
            "page_revision": self._page_revision,
            "task_binding_status": self.task_binding_status,
            "task_binding_verified": False,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "human_control_active": self.is_human_control_active(),
            "human_control_expires_at": self._human_control_expiry_iso(),
            "human_actions": list(HUMAN_CONTROL_ACTIONS),
            "human_actions_require_lease": True,
            "engine_label": self.engine_label,
            "allowed_actions": ["navigate", "reload", "frame"]
            if self.status == SessionStatus.RUNNING and self._page else [],
            "circuit_breaker": self.recovery.circuit_breaker.get_state(),
            "console_errors_count": len(self._console_errors),
        }

    # ──────────────────────────────────────────────────────────
    # Observe（观察页面）
    # ──────────────────────────────────────────────────────────

    def observe(
        self,
        include_dom: bool = False,
        include_accessibility: bool = False,
        max_text_length: int = 2000,
    ) -> BrowserPageState:
        """观察当前页面状态，返回脱敏后的页面快照。

        网页内容标记为 untrusted_content，经过 Prompt Injection 扫描和敏感信息脱敏。
        """
        if (type(include_dom) is not bool or type(include_accessibility) is not bool
                or type(max_text_length) is not int
                or not 0 <= max_text_length <= MAX_OBSERVATION_TEXT_LENGTH):
            raise ValueError("BROWSER_OBSERVATION_OPTIONS_INVALID")
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(
                lambda: self.observe(include_dom, include_accessibility, max_text_length)
            )
        self._check_bound_task_operation(BrowserActionType.OBSERVE)
        self.last_activity = time.time()
        state = BrowserPageState()

        if not self._page:
            state.error = "No active page"
            return state

        try:
            state.url = self._page.url
            state.title = self._page.title()
            state.loading = None  # Unknown until this observation reads document.readyState.

            # 获取 body 文本（脱敏 + 注入扫描）
            try:
                # Bound the browser-to-Python transfer, including the scan input.
                extracted = self._page.evaluate(
                    "limit => { const text = document.body ? document.body.innerText : ''; "
                    "return {text: text.slice(0, limit), truncated: text.length > limit, ready_state: document.readyState}; }",
                    max_text_length,
                )
                ready_state = extracted.get("ready_state")
                if ready_state in {"loading", "interactive", "complete"}:
                    state.loading = ready_state != "complete"
                else:
                    state.observation_errors["loading"] = "BROWSER_READY_STATE_UNAVAILABLE"
                body_text = extracted["text"]
                if extracted["truncated"]:
                    state.truncated_fields.append("body_text")
                # Prompt Injection 扫描
                injection_result = self.injection_guard.scan(body_text, source="page_observe")
                state.body_text = injection_result.sanitized_text[:max_text_length]
            except Exception:
                state.body_text = ""
                state.error = "BROWSER_PAGE_TEXT_UNAVAILABLE"
                state.observation_errors["body_text"] = state.error

            # 元素计数
            try:
                state.element_count = self._page.evaluate(
                    "() => document.querySelectorAll('*').length"
                )
            except Exception:
                state.element_count = None
                state.observation_errors["element_count"] = "BROWSER_ELEMENT_COUNT_UNAVAILABLE"

            # 控制台错误
            state.console_errors = list(self._console_errors[-10:])

            # DOM 摘要（可选）
            if include_dom:
                try:
                    dom_summary = self._page.evaluate("""() => {
                        const els = document.querySelectorAll('a,button,input,select,textarea,[role=button]');
                        return Array.from(els).slice(0, 50).map(el => ({
                            tag: el.tagName,
                            type: el.type || '',
                            text: (el.innerText || '').trim().slice(0, 100),
                            id: (el.id || '').slice(0, 100),
                            className: (el.className || '').toString().slice(0, 100),
                            visible: el.offsetParent !== null,
                        }));
                    }""")
                    state.elements["_dom_summary"] = sanitize_dict(dom_summary)
                except Exception:
                    state.observation_errors["dom"] = "BROWSER_DOM_UNAVAILABLE"

            # Accessibility Tree（可选）
            if include_accessibility:
                try:
                    snapshot = self._page.accessibility.snapshot()
                    budget = [128]

                    def bounded_node(node, depth=0):
                        if not isinstance(node, dict):
                            return {}
                        if depth > 6 or budget[0] <= 0:
                            if "accessibility" not in state.truncated_fields:
                                state.truncated_fields.append("accessibility")
                            return {}
                        budget[0] -= 1
                        # Never return input values, including passwords, from
                        # a page's accessibility tree.
                        result = {key: str(node[key])[:200] for key in ("role", "name") if key in node}
                        children = node.get("children", [])
                        if isinstance(children, list):
                            if depth >= 6 and children:
                                state.truncated_fields.append("accessibility")
                                return result
                            result["children"] = []
                            for child in children[:budget[0]]:
                                if budget[0] <= 0:
                                    state.truncated_fields.append("accessibility")
                                    break
                                result["children"].append(bounded_node(child, depth + 1))
                            if len(result["children"]) < len(children):
                                state.truncated_fields.append("accessibility")
                        return result

                    state.elements["_accessibility"] = sanitize_dict(bounded_node(snapshot))
                    state.truncated_fields = list(dict.fromkeys(state.truncated_fields))
                except Exception:
                    state.observation_errors["accessibility"] = "BROWSER_ACCESSIBILITY_UNAVAILABLE"

        except Exception as e:
            state.error = sanitize_sensitive(str(e)[:300])

        # Revoke read access before releasing collected page data, outside the
        # observation error fallback so a denial cannot return stale content.
        self._check_bound_task_operation(BrowserActionType.OBSERVE)
        return state

    # ──────────────────────────────────────────────────────────
    # 核心：execute_action（带 Verification 闭环）
    # ──────────────────────────────────────────────────────────

    def extract(self, options: dict, *, _capture_context=None) -> dict:
        """Extract an already-open page without navigating or granting SourceUse.

        The actor gate is owned by the API. This method owns page binding,
        browser-thread confinement, human-control exclusion and bounded capture.
        """
        from concurrent.futures import TimeoutError as FutureTimeout
        from lumenis.system.collector.runtime.browser_extract import (
            BrowserExtractionError, CAPTURE_SCRIPT, check_deadline,
            format_capture, validate_extract_request, same_document_url, capture_structure,
            select_page_context,
        )
        options = validate_extract_request(options)
        deadline = (_capture_context['deadline'] if _capture_context is not None
                    else time.monotonic() + options['timeout_ms'] / 1000.0)

        operation_id = str(uuid.uuid4())
        outcome_lock = threading.Lock()
        outcome = {'state': 'NOT_STARTED', 'cancelled': False, 'evidence_id': None}

        def timeout_error():
            with outcome_lock:
                outcome['cancelled'] = True
                state = outcome['state']
                details = {
                    'operation_id': operation_id, 'session_id': self.session_id,
                    'persistence_outcome': state,
                    'retry_safe': state == 'NOT_STARTED',
                    'receipt_query': f'/api/browser/sessions/{self.session_id}/evidence',
                }
                if outcome['evidence_id'] is not None:
                    details['evidence_id'] = outcome['evidence_id']
                return BrowserExtractionError('BROWSER_EXTRACTION_TIMEOUT', **details)

        if _capture_context is not None:
            _capture_context['timeout_error'] = timeout_error

        def operation():
            if time.monotonic() >= deadline:
                raise timeout_error()
            self._begin_control_action(control_mode="agent", human_control_token=None)
            cdp = None
            try:
                if self.status != SessionStatus.RUNNING or self._closed or self._page is None:
                    raise BrowserExtractionError('BROWSER_EXTRACTION_SESSION_NOT_RUNNING')
                self._check_bound_task_operation(BrowserActionType.OBSERVE)
                expected_url = options['url']
                if expected_url is None:
                    expected_url = validate_extract_request({
                        'url': self._page.url, 'formats': options['formats'],
                        'timeout_ms': options['timeout_ms'],
                    })['url']
                if not same_document_url(self._page.url, expected_url):
                    raise BrowserExtractionError('BROWSER_EXTRACTION_NAVIGATION_REQUIRED')
                revision = self._page_revision
                target_id = self._target_id
                if ('question' in options and (
                        revision != options['page_revision'] or target_id != options['target_id'])):
                    raise BrowserExtractionError('BROWSER_EXTRACTION_PAGE_CHANGED')
                allowed, _reason = self.firewall.check_action(
                    BrowserActionType.OBSERVE, url=expected_url)
                if not allowed:
                    raise BrowserExtractionError('BROWSER_EXTRACTION_PERMISSION_DENIED')
                check_deadline(deadline)
                cdp = self._context.new_cdp_session(self._page)
                frame = cdp.send('Page.getFrameTree')['frameTree']['frame']['id']
                world = cdp.send('Page.createIsolatedWorld', {
                    'frameId': frame, 'worldName': 'lumenis-read-only-extract',
                    'grantUniveralAccess': False,
                })
                check_deadline(deadline)
                result = cdp.send('Runtime.evaluate', {
                    'expression': CAPTURE_SCRIPT,
                    'contextId': world['executionContextId'],
                    'returnByValue': True,
                    'awaitPromise': False,
                    'timeout': max(1, int((deadline - time.monotonic()) * 1000)),
                })
                check_deadline(deadline)
                if result.get('exceptionDetails'):
                    raise BrowserExtractionError('BROWSER_EXTRACTION_CAPTURE_UNAVAILABLE')
                capture = result.get('result', {}).get('value')
                if type(capture) is not dict:
                    raise BrowserExtractionError('BROWSER_EXTRACTION_CAPTURE_INVALID')
                if capture.get('interaction_required') is True:
                    raise BrowserExtractionError('BROWSER_EXTRACTION_HUMAN_REQUIRED')
                if (not same_document_url(capture.get('url'), expected_url) or not same_document_url(self._page.url, expected_url)
                        or self._page_revision != revision or self._target_id != target_id
                        or self.status != SessionStatus.RUNNING or self._closed):
                    raise BrowserExtractionError('BROWSER_EXTRACTION_PAGE_CHANGED')
                def safe_text(value):
                    scanned = self.injection_guard.scan(value, source='browser_extract')
                    return redact_browser_url_queries(sanitize_sensitive(scanned.sanitized_text))
                formats = format_capture(capture, options['formats'], safe_text)
                structure = capture_structure(capture, safe_text)
                page_context = (select_page_context(structure, safe_text(options['question']))
                                if 'question' in options else None)
                check_deadline(deadline)
                captured_at = datetime.now(timezone.utc).isoformat()
                metadata = {
                    'url': safe_browser_display_url(capture['url']),
                    'title': safe_text(str(capture.get('title', ''))[:300]),
                    'page_revision': revision,
                    'captured_at': captured_at,
                }
                truncated = capture.get('truncated') is True
                digest = hashlib.sha256(json.dumps({'formats': formats, 'structure': structure}, sort_keys=True,
                    ensure_ascii=False).encode('utf-8')).hexdigest()
                # Only hashes/locators enter Browser Evidence. Bodies are returned
                # to the owner; saving requires the existing SavedWork workflow.
                with outcome_lock:
                    check_deadline(deadline)
                    if outcome['cancelled']:
                        raise BrowserExtractionError('BROWSER_EXTRACTION_TIMEOUT')
                    outcome['state'] = 'UNKNOWN'
                evidence_id = self._record_evidence(
                    action='extract', timestamp=captured_at, result='PARTIAL' if truncated else 'PASS',
                    target=metadata['url'], after_state_hash=digest,
                    verification=json.dumps({
                        'operation_id': operation_id, 'formats': list(formats), 'page_revision': revision,
                        'truncated': truncated, 'source_capture': 'NOT_IMPORTED',
                        'source_use': 'NOT_ADMITTED', 'untrusted_content': True,
                    }), risk_level='low',
                )
                if type(evidence_id) is not int or evidence_id <= 0:
                    raise BrowserExtractionError('BROWSER_EXTRACTION_EVIDENCE_UNAVAILABLE',
                        operation_id=operation_id, persistence_outcome='UNKNOWN', retry_safe=False,
                        receipt_query=f'/api/browser/sessions/{self.session_id}/evidence')
                with outcome_lock:
                    outcome.update(state='COMMITTED', evidence_id=evidence_id)
                if time.monotonic() >= deadline:
                    raise timeout_error()
                self.last_activity = time.time()
                self._check_bound_task_operation(BrowserActionType.OBSERVE)
                return {
                    'ok': True, 'session_id': self.session_id, 'formats': formats, 'structure': structure,
                    'operation_id': operation_id, 'persistence_outcome': 'COMMITTED',
                    'metadata': metadata, 'evidence_id': evidence_id,
                    'untrusted_content': True, 'ai_used': False,
                    'source_capture': 'NOT_IMPORTED', 'source_use': 'NOT_ADMITTED',
                    'partial': truncated, 'truncated': truncated,
                    'format_semantics': 'sanitized_visible_document',
                    'capture_scope': 'main_frame_visible_light_dom',
                    **({'page_context': page_context} if page_context is not None else {}),
                }
            except BrowserExtractionError as exc:
                if exc.code == 'BROWSER_EXTRACTION_TIMEOUT':
                    raise timeout_error() from None
                raise
            except BrowserHumanControlError:
                raise
            except PermissionError:
                raise BrowserExtractionError('BROWSER_EXTRACTION_PERMISSION_DENIED') from None
            except Exception:
                if time.monotonic() >= deadline:
                    raise timeout_error() from None
                with outcome_lock:
                    persistence_started = outcome['state'] != 'NOT_STARTED'
                if persistence_started:
                    raise BrowserExtractionError('BROWSER_EXTRACTION_EVIDENCE_UNAVAILABLE',
                        operation_id=operation_id, persistence_outcome='UNKNOWN', retry_safe=False,
                        receipt_query=f'/api/browser/sessions/{self.session_id}/evidence') from None
                raise BrowserExtractionError('BROWSER_EXTRACTION_CAPTURE_UNAVAILABLE') from None
            finally:
                if cdp is not None:
                    try:
                        cdp.detach()
                    except Exception:
                        pass
                self._end_control_action()

        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            with self._worker_lock:
                future = self._browser_worker.submit(self._browser_thread_operation, operation)
            try:
                return future.result(timeout=max(0.001, deadline - time.monotonic()))
            except FutureTimeout:
                # A running SQLite commit cannot be cancelled. Report its outcome
                # honestly and correlate it through the existing Evidence owner.
                future.cancel()
                raise timeout_error() from None
        result = operation()
        if time.monotonic() >= deadline:
            raise timeout_error()
        return result

    def capture_command(self, data: dict, *, _capture_context=None) -> dict:
        """One deterministic handler for trusted UI and authorized AI callers.

        Authentication is always performed by the existing API/agent boundary;
        a caller-supplied initiator/actor/permission is deliberately not accepted.
        Captures are temporary, not a second Source or persistence store.
        """
        import copy
        from lumenis.system.collector.runtime.browser_extract import (
            BrowserExtractionError, CAPTURE_TTL_SECONDS, validate_capture_command,
            select_capture, same_document_url,
        )
        data = validate_capture_command(data)
        if _capture_context is None:
            _capture_context = {'deadline': time.monotonic() + data.get('timeout_ms', 10000) / 1000.0}
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            from concurrent.futures import TimeoutError as FutureTimeout
            with self._worker_lock:
                future = self._browser_worker.submit(self._browser_thread_operation,
                    lambda: self.capture_command(data, _capture_context=_capture_context))
            try:
                return future.result(timeout=max(0.001, _capture_context['deadline'] - time.monotonic()))
            except FutureTimeout:
                cancelled = future.cancel()
                timeout_error = _capture_context.get('timeout_error')
                if timeout_error is not None:
                    raise timeout_error() from None
                raise BrowserExtractionError('BROWSER_CAPTURE_TIMEOUT',
                    persistence_outcome='NOT_STARTED' if cancelled else 'UNKNOWN',
                    retry_safe=cancelled, request_id=data.get('request_id'),
                    receipt_query=f'/api/browser/sessions/{self.session_id}/evidence') from None
        if time.monotonic() >= _capture_context['deadline']:
            raise BrowserExtractionError('BROWSER_CAPTURE_TIMEOUT',
                persistence_outcome='NOT_STARTED', retry_safe=True)
        command = data['command']
        if command == 'capabilities':
            return {'ok': True, 'schema': 'lumenis.browser-capture/v1',
                    'commands': ['preview', 'select', 'discard'],
                    'entrypoints': ['user', 'authorized_agent'], 'ai_required': False,
                    'agent_dispatch_state': 'UNBOUND', 'model_execution': 'NOT_RUN',
                    'availability': 'AVAILABLE' if self.status == SessionStatus.RUNNING and not self._closed else 'UNAVAILABLE',
                    'source_capture': 'NOT_IMPORTED', 'source_use': 'NOT_ADMITTED',
                    'source_admission': {'state': 'REQUIRES_APPROVAL', 'kind': 'SANITIZED_SNAPSHOT',
                        'commands': ['source_prepare','source_import','source_use_prepare'],
                        'original_resource_sha256': None},
                    'save_owner': 'SavedWork', 'saved_note_authenticity': 'USER_AUTHORED_NOT_VERIFIED',
                    'human_lease_policy': 'RELEASE_BEFORE_CAPTURE',
                    'capture_ttl_seconds': CAPTURE_TTL_SECONDS,
                    'persistence': 'SESSION_EPHEMERAL', 'restart_requires_new_capture': True}
        cache = getattr(self, '_capture_previews', None)
        if cache is None:
            cache = self._capture_previews = {}
        def valid(entry):
            if entry.get('discarded'):
                raise BrowserExtractionError('BROWSER_CAPTURE_CANCELLED')
            if time.monotonic() >= entry['expires']:
                entry['result'] = None
                raise BrowserExtractionError('BROWSER_CAPTURE_EXPIRED')
            if (self._closed or self.status != SessionStatus.RUNNING
                    or self._target_id != entry['target_id'] or self._page_revision != entry['revision']
                    or self._page is None or not same_document_url(self._page.url, entry['url'])):
                raise BrowserExtractionError('BROWSER_CAPTURE_STALE')
            allowed, _ = self.firewall.check_action(BrowserActionType.OBSERVE, url=entry['url'])
            if not allowed:
                raise BrowserExtractionError('BROWSER_EXTRACTION_PERMISSION_DENIED')
        if command == 'preview':
            options = {k:v for k,v in data.items() if k not in {'command', 'request_id'}}
            fingerprint = hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()
            old = next((e for e in cache.values() if e['request_id'] == data['request_id']), None)
            if old:
                self._begin_control_action(control_mode='agent', human_control_token=None)
                try:
                    if old['fingerprint'] != fingerprint:
                        raise BrowserExtractionError('BROWSER_CAPTURE_REQUEST_CONFLICT')
                    # Terminal receipts contain no page body. API actor/session
                    # authorization still applies, independently of page expiry,
                    # navigation and page-read permission. Never execute twice.
                    if old.get('error'):
                        if time.monotonic() >= old['expires']:
                            old['result'] = None
                        raise BrowserExtractionError(old['error']['code'], **old['error']['details'])
                    valid(old)
                    return copy.deepcopy(old['result'])
                finally:
                    self._end_control_action()
            # Fail closed instead of evicting a request and silently replaying it.
            if len(cache) >= 16:
                raise BrowserExtractionError('BROWSER_CAPTURE_SESSION_LIMIT')
            target, revision = self._target_id, self._page_revision
            capture_id = 'cap_' + uuid.uuid4().hex
            entry = cache[capture_id] = {'request_id': data['request_id'], 'fingerprint': fingerprint,
                                'target_id': target, 'revision': revision, 'url': options['url'],
                                'expires': time.monotonic()+CAPTURE_TTL_SECONDS, 'result': None}
            try:
                result = self.extract(options, _capture_context=_capture_context)
                if self._target_id != target or self._page_revision != revision:
                    raise BrowserExtractionError('BROWSER_CAPTURE_STALE')
                result.update(capture_id=capture_id, schema='lumenis.browser-capture/v1',
                              capture_ttl_seconds=CAPTURE_TTL_SECONDS, persistence='SESSION_EPHEMERAL')
                entry['result'] = copy.deepcopy(result)
                return result
            except BrowserHumanControlError:
                # The lease gate runs before any capture or persistence. Denial
                # is safely retryable and must not consume the 16-record budget.
                cache.pop(capture_id, None)
                raise
            except BrowserExtractionError as exc:
                # An uncertain write stays queryable; repeating request_id never recaptures.
                entry['error'] = {'code': exc.code, 'details': dict(exc.details)}
                raise
            except Exception:
                entry['error'] = {'code': 'BROWSER_CAPTURE_UNAVAILABLE', 'details': {}}
                raise
        self._begin_control_action(control_mode='agent', human_control_token=None)
        try:
            entry = cache.get(data['capture_id'])
            if entry is None:
                raise BrowserExtractionError('BROWSER_CAPTURE_NOT_FOUND')
            if command == 'discard':
                entry['discarded'] = True
                entry['result'] = None
                entry['url'] = ''
                return {'ok': True, 'capture_id': data['capture_id'], 'state': 'CANCELLED',
                        'scope': 'LOCAL_PREVIEW_ONLY', 'source_capture': 'NOT_IMPORTED'}
            valid(entry)
            if entry.get('error'):
                raise BrowserExtractionError(entry['error']['code'], **entry['error']['details'])
            result = entry['result']
            selection = select_capture(result, data)
            return {'ok': True, 'capture_id': data['capture_id'], 'selection': selection,
                    'metadata': copy.deepcopy(result['metadata']), 'evidence_id': result['evidence_id'],
                    'untrusted_content': True, 'source_capture': 'NOT_IMPORTED', 'source_use': 'NOT_ADMITTED',
                    'source_verification': 'NOT_VERIFIED',
                    'saved_note_authenticity': 'USER_AUTHORED_NOT_VERIFIED'}
        finally:
            self._end_control_action()

    def snapshot_for_source(self, capture_id: str, *, _deadline=None):
        """Server-only source resolver; admission and persistence belong to Collector."""
        import copy
        from concurrent.futures import TimeoutError as FutureTimeout
        from lumenis.system.collector.runtime.browser_extract import (
            BrowserExtractionError, make_source_snapshot, same_document_url)
        deadline = _deadline if _deadline is not None else time.monotonic() + 10
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            with self._worker_lock:
                future = self._browser_worker.submit(self._browser_thread_operation,
                    lambda: self.snapshot_for_source(capture_id, _deadline=deadline))
            try:
                return future.result(timeout=max(.001, deadline-time.monotonic()))
            except FutureTimeout:
                future.cancel()
                raise BrowserExtractionError('BROWSER_CAPTURE_TIMEOUT') from None
        if time.monotonic() >= deadline:
            raise BrowserExtractionError('BROWSER_CAPTURE_TIMEOUT')
        self._begin_control_action(control_mode='agent', human_control_token=None)
        try:
            entry = getattr(self, '_capture_previews', {}).get(capture_id)
            if not entry or entry.get('discarded') or not entry.get('result'):
                raise BrowserExtractionError('BROWSER_CAPTURE_NOT_FOUND')
            if time.monotonic() >= entry['expires']:
                entry['result'] = None
                raise BrowserExtractionError('BROWSER_CAPTURE_EXPIRED')
            if (self._closed or self.status != SessionStatus.RUNNING or self._page is None
                    or self._target_id != entry['target_id'] or self._page_revision != entry['revision']
                    or not same_document_url(self._page.url, entry['url'])):
                raise BrowserExtractionError('BROWSER_CAPTURE_STALE')
            if not self.firewall.check_action(BrowserActionType.OBSERVE, url=entry['url'])[0]:
                raise BrowserExtractionError('BROWSER_EXTRACTION_PERMISSION_DENIED')
            return make_source_snapshot(copy.deepcopy(entry['result']),
                target_id=entry['target_id'], page_revision=entry['revision'])
        finally:
            self._end_control_action()

    def _expire_human_control_locked(self) -> None:
        if self._human_control_token_digest and time.time() >= self._human_control_expires_at:
            self._human_control_token_digest = None
            self._human_control_expires_at = 0.0

    def is_human_control_active(self) -> bool:
        with self._control_lock:
            self._expire_human_control_locked()
            return self._human_control_token_digest is not None

    def _human_control_expiry_iso(self) -> Optional[str]:
        with self._control_lock:
            self._expire_human_control_locked()
            if self._human_control_token_digest is None:
                return None
            return datetime.fromtimestamp(
                self._human_control_expires_at, tz=timezone.utc
            ).isoformat()

    def acquire_human_control(self, lease_seconds: int = 120) -> Dict[str, Any]:
        """Acquire a short-lived exclusive lease for the authenticated session owner."""
        if self.status != SessionStatus.RUNNING or self._closed:
            raise BrowserHumanControlError("BROWSER_SESSION_NOT_RUNNING")
        if type(lease_seconds) is not int:
            raise BrowserHumanControlError("BROWSER_HUMAN_LEASE_TTL_INVALID")
        lease_seconds = max(30, min(lease_seconds, 300))
        with self._control_lock:
            self._expire_human_control_locked()
            if self._active_control_actions:
                raise BrowserHumanControlError("BROWSER_ACTION_IN_PROGRESS")
            if self._human_control_token_digest is not None:
                raise BrowserHumanControlError("BROWSER_HUMAN_CONTROL_ACTIVE")
            token = secrets.token_urlsafe(32)
            self._human_control_token_digest = hashlib.sha256(
                token.encode("utf-8")
            ).hexdigest()
            self._human_control_expires_at = time.time() + lease_seconds
            expires_at = datetime.fromtimestamp(
                self._human_control_expires_at, tz=timezone.utc
            ).isoformat()
        self._invalidate_human_links()
        return {
            "lease_token": token,
            "lease_ttl_seconds": lease_seconds,
            "lease_expires_at": expires_at,
        }

    def release_human_control(self, token: Optional[str]) -> bool:
        """Release exactly the current session lease without logging its token."""
        if not isinstance(token, str) or not token or len(token) > 256:
            raise BrowserHumanControlError("BROWSER_HUMAN_LEASE_REQUIRED")
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._control_lock:
            self._expire_human_control_locked()
            current = self._human_control_token_digest
            if current is None:
                raise BrowserHumanControlError("BROWSER_HUMAN_LEASE_EXPIRED")
            if not hmac.compare_digest(current, digest):
                raise BrowserHumanControlError("BROWSER_HUMAN_LEASE_INVALID")
            if self._active_control_actions:
                raise BrowserHumanControlError("BROWSER_ACTION_IN_PROGRESS")
            self._human_control_token_digest = None
            self._human_control_expires_at = 0.0
        self._invalidate_human_links()
        return True

    def bind_task_admission(self, admission, *, actor):
        """Internal original-Task bridge; a metadata seal never grants browser effects.

        HTTP callers cannot supply this sealed object. The existing API keeps
        client task/run strings UNVERIFIED and existing capacity isolation.
        """
        with self._control_lock:
            from lumenis.system.security.permission import TaskOperationalWriteAdmission
            if type(admission) is not TaskOperationalWriteAdmission:
                raise PermissionError("BROWSER_TASK_ADMISSION_REQUIRED")
            if self._closed or self.task_id not in (None, admission.task_id) or self.run_id not in (None, admission.run_id):
                raise PermissionError("BROWSER_TASK_BINDING_CONFLICT")
            if self._active_control_actions or (self._server_task_admission is not None and self._server_task_admission is not admission):
                raise PermissionError("BROWSER_TASK_BINDING_BUSY_OR_IMMUTABLE")
            prior = (self._server_task_admission, self._server_task_actor)
            self._server_task_admission, self._server_task_actor = admission, (dict(actor) if isinstance(actor, dict) else actor)
            try:
                self._check_bound_task_operation(BrowserActionType.OBSERVE)
            except Exception:
                self._server_task_admission, self._server_task_actor = prior
                raise
            self.task_id, self.run_id = admission.task_id, admission.run_id
            self.task_binding_status = "BOUND"

    def _check_bound_task_operation(self, action_type, **arguments):
        admission = getattr(self, "_server_task_admission", None)
        if admission is None:
            return  # Existing unbound/manual browser path remains unchanged.
        from lumenis.system.security.permission import get_permission_gate, OperationType
        context = self._check_bound_task_owner(admission)
        resource = "browser-task-operation:v1:" + hashlib.sha256(json.dumps({
            "session": self.session_id, "target": self._target_id,
            "task": admission.task_id, "run": admission.run_id,
            "scope": context["scope"], "domain": context["domain_id"],
            "action": action_type.value, "arguments": arguments,
        }, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        # authorized_context supplies a fixed analyst role for local tools, not
        # the account browser grant. Scope and SYSTEM/browser grant were both
        # checked above against original account owners, never a client role.
        browser = get_permission_gate().check(OperationType.BROWSER_OPERATION,
            resource=resource, caller="ai_browser_runtime.bound_task",
            domain_id=context["domain_id"])
        if not browser.allowed:
            raise PermissionError("BROWSER_OPERATION_PERMISSION_DENIED")
        # Gate evaluation can itself take time: never reuse its earlier Owner snapshot.
        self._check_bound_task_owner(admission)

    def _check_bound_task_owner(self, admission, *, attempt_guarded=False):
        from ai_task_engine import get_task_engine
        from agent_runtime.task_binding import authorized_context
        decision = admission.check("ai_task", fields={"status"})
        if not decision.allowed:
            raise PermissionError("BROWSER_TASK_ATTEMPT_OR_SCOPE_REVOKED")
        if not attempt_guarded:
            attempt = admission.queue.get(admission.queue_task_id)
            payload = attempt.get("payload", {}) if attempt else {}
            deadline = payload.get("deadline_at")
            if (payload.get("cancel_requested") is True or
                    (deadline is not None and (type(deadline) not in (int, float) or not time.time() < deadline))):
                raise PermissionError("BROWSER_TASK_CANCELLED_OR_EXPIRED")
        task = get_task_engine().get_task(admission.task_id)
        if not task or task.get("status") in {"succeeded", "failed", "cancelled"}:
            raise PermissionError("BROWSER_TASK_NOT_ACTIVE")
        context = authorized_context(task, self._server_task_actor)
        actor_id = context.get("actor_id")
        if actor_id != self.owner_actor_id:
            raise PermissionError("BROWSER_TASK_ACTOR_MISMATCH")
        if actor_id is not None:
            from account.models import get_db
            from account.authorization import check_dual_domain_permission
            con = get_db()
            try:
                row = con.execute("SELECT user_id,expires_at FROM v4_sessions WHERE id=?", (self.owner_account_session_id,)).fetchone()
            finally:
                con.close()
            if not row or row["user_id"] != actor_id or row["expires_at"] < time.strftime("%Y-%m-%d %H:%M:%S"):
                raise PermissionError("BROWSER_ACCOUNT_SESSION_REVOKED")
            if not check_dual_domain_permission(actor_id, "SYSTEM", module="browser", action="write"):
                raise PermissionError("BROWSER_PERMISSION_REVOKED")
        else:
            from lumenis.system.security.permission import resolve_local_workspace_principal
            principal = resolve_local_workspace_principal(module="browser", action="write")
            if self.owner_principal_ref != "workspace:local" or principal is None:
                raise PermissionError("BROWSER_TASK_WORKSPACE_MISMATCH")
        return context

    def _resolve_task_trace(
        self, task_id: Optional[str], run_id: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        if self.task_binding_status == "UNVERIFIED":
            # A client-provided trace is not an authoritative association. Reject
            # contradictory claims, but keep Evidence unbound until an existing
            # server-owned Task/Run resolver is connected.
            if task_id not in (None, self.task_id) or run_id not in (None, self.run_id):
                raise BrowserSessionBindingError("BROWSER_TASK_BINDING_CONFLICT")
            return None, None
        if self.task_binding_status != "BOUND":
            # A trace supplied only on an action is not an authoritative
            # association. Keep the browser operation usable and Evidence unbound.
            return None, None
        if task_id not in (None, self.task_id) or run_id not in (None, self.run_id):
            raise BrowserSessionBindingError("BROWSER_TASK_BINDING_CONFLICT")
        return self.task_id, self.run_id

    def _begin_control_action(
        self, *, control_mode: str, human_control_token: Optional[str]
    ) -> None:
        if control_mode not in {"agent", "human"}:
            raise BrowserHumanControlError("BROWSER_CONTROL_MODE_INVALID")
        with self._control_lock:
            self._expire_human_control_locked()
            active = self._human_control_token_digest is not None
            if control_mode == "human":
                if (not isinstance(human_control_token, str) or not human_control_token
                        or len(human_control_token) > 256):
                    raise BrowserHumanControlError("BROWSER_HUMAN_LEASE_REQUIRED")
                if not active:
                    raise BrowserHumanControlError("BROWSER_HUMAN_LEASE_EXPIRED")
                supplied = hashlib.sha256(human_control_token.encode("utf-8")).hexdigest()
                if not hmac.compare_digest(self._human_control_token_digest, supplied):
                    raise BrowserHumanControlError("BROWSER_HUMAN_LEASE_INVALID")
            elif active:
                raise BrowserHumanControlError("BROWSER_HUMAN_CONTROL_ACTIVE")
            self._active_control_actions += 1

    def _end_control_action(self) -> None:
        with self._control_lock:
            self._active_control_actions = max(0, self._active_control_actions - 1)

    def _current_viewport(self) -> Dict[str, Any]:
        if not self._page:
            raise BrowserFrameStaleError("BROWSER_FRAME_UNAVAILABLE")
        value = self._page.evaluate(
            "() => ({width: window.innerWidth, height: window.innerHeight, "
            "dpr: window.devicePixelRatio || 1})"
        )
        if not isinstance(value, dict):
            raise BrowserFrameStaleError("BROWSER_FRAME_UNAVAILABLE")
        width, height, dpr = value.get("width"), value.get("height"), value.get("dpr")
        if (type(width) is not int or width <= 0 or type(height) is not int or height <= 0
                or isinstance(dpr, bool) or not isinstance(dpr, (int, float))
                or not math.isfinite(float(dpr)) or float(dpr) <= 0):
            raise BrowserFrameStaleError("BROWSER_FRAME_UNAVAILABLE")
        return {"width": width, "height": height, "dpr": round(float(dpr), 3)}

    def assert_current_frame_binding(self, binding: Any, *, verify_image: bool = True) -> None:
        """Reject missing, stale, altered or viewport-mismatched human frame input."""
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(lambda: self.assert_current_frame_binding(
                binding, verify_image=verify_image,
            ))
        if not isinstance(binding, dict):
            raise BrowserFrameStaleError("BROWSER_FRAME_BINDING_REQUIRED")
        viewport = binding.get("viewport")
        if (set(binding) != {"frame_id", "target_id", "page_revision", "viewport"}
                or not isinstance(binding.get("frame_id"), str)
                or not binding["frame_id"]
                or len(binding["frame_id"]) > 128
                or not isinstance(binding.get("target_id"), str)
                or not binding["target_id"]
                or len(binding["target_id"]) > 128
                or type(binding.get("page_revision")) is not int
                or not isinstance(viewport, dict)
                or set(viewport) != {"width", "height", "dpr"}
                or type(viewport.get("width")) is not int
                or not 0 < viewport["width"] <= 32768
                or type(viewport.get("height")) is not int
                or not 0 < viewport["height"] <= 32768
                or isinstance(viewport.get("dpr"), bool)
                or not isinstance(viewport.get("dpr"), (int, float))
                or not math.isfinite(float(viewport["dpr"]))
                or not 0 < float(viewport["dpr"]) <= 16):
            raise BrowserFrameStaleError("BROWSER_FRAME_BINDING_REQUIRED")
        expected = {
            "frame_id": binding["frame_id"],
            "target_id": binding["target_id"],
            "page_revision": binding["page_revision"],
            "viewport": viewport,
        }
        if self._latest_frame_binding is None or expected != self._latest_frame_binding:
            raise BrowserFrameStaleError("BROWSER_FRAME_STALE")
        if (expected["target_id"] != self._target_id
                or expected["page_revision"] != self._page_revision
                or expected["viewport"] != self._current_viewport()):
            raise BrowserFrameStaleError("BROWSER_FRAME_STALE")
        if (self._latest_frame_document_url is None or self._page is None
                or self._page.url != self._latest_frame_document_url):
            raise BrowserFrameStaleError("BROWSER_FRAME_STALE")
        if verify_image:
            current_image = self.screenshot(full_page=False)
            if (self._latest_frame_image_sha256 is None
                    or not hmac.compare_digest(
                        hashlib.sha256(current_image).hexdigest(),
                        self._latest_frame_image_sha256,
                    )):
                raise BrowserFrameStaleError("BROWSER_FRAME_STALE")

    def _invalidate_human_links(self) -> None:
        """Discard the private link map whenever its frame/action can change."""
        with self._human_link_lock:
            self._human_link_choices.clear()
            self._human_link_frame_binding = None
            self._human_link_lease_digest = None

    def _current_frame_binding_copy(self) -> dict[str, Any]:
        binding = self._latest_frame_binding
        if not isinstance(binding, dict):
            raise BrowserFrameStaleError("BROWSER_FRAME_STALE")
        return {
            "frame_id": binding["frame_id"],
            "target_id": binding["target_id"],
            "page_revision": binding["page_revision"],
            "viewport": dict(binding["viewport"]),
        }

    def list_human_links(
        self,
        *,
        frame_binding: Any,
        human_control_token: str | None,
    ) -> dict[str, Any]:
        """List policy-approved visible anchors bound to the current human frame."""
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(lambda: self.list_human_links(
                frame_binding=frame_binding,
                human_control_token=human_control_token,
            ))
        if self.status != SessionStatus.RUNNING or self._page is None:
            raise BrowserLinkError("BROWSER_SESSION_NOT_RUNNING")
        self._begin_control_action(
            control_mode="human",
            human_control_token=human_control_token,
        )
        try:
            self._invalidate_human_links()
            self.assert_current_frame_binding(frame_binding, verify_image=False)
            binding_copy = self._current_frame_binding_copy()
            with self._control_lock:
                self._expire_human_control_locked()
                lease_digest = self._human_control_token_digest
            if lease_digest is None:
                raise BrowserHumanControlError("BROWSER_HUMAN_LEASE_EXPIRED")

            try:
                from playwright.sync_api import Error as PlaywrightError
            except ImportError:
                raise BrowserLinkError("BROWSER_LINKS_UNAVAILABLE") from None
            try:
                candidates = self._page.evaluate(_HUMAN_LINK_SNAPSHOT_JS)
            except PlaywrightError:
                raise BrowserLinkError("BROWSER_LINKS_UNAVAILABLE") from None
            if not isinstance(candidates, list):
                raise BrowserLinkError("BROWSER_LINKS_UNAVAILABLE")

            links: list[dict[str, str]] = []
            choices: dict[str, dict[str, Any]] = {}
            for candidate in candidates[:MAX_HUMAN_LINKS]:
                if not isinstance(candidate, dict):
                    continue
                index = candidate.get("index")
                href = candidate.get("href")
                if (type(index) is not int or not 0 <= index < MAX_HUMAN_LINK_SCAN
                        or not isinstance(href, str)):
                    continue
                destination = _approved_human_link_destination(href)
                if destination is None:
                    continue
                label = _safe_human_link_label(candidate.get("label"), destination)
                link_id = f"bl_{secrets.token_urlsafe(24)}"
                choices[link_id] = {
                    "frame_binding": binding_copy,
                    "index": index,
                    "href": href,
                    "label": label,
                    "destination": destination,
                }
                links.append({
                    "link_id": link_id,
                    "label": label,
                    "destination": destination,
                })

            with self._human_link_lock:
                self._human_link_choices = choices
                self._human_link_frame_binding = binding_copy
                self._human_link_lease_digest = lease_digest
            self.last_activity = time.time()
            return {"links": links, "frame_binding": binding_copy}
        finally:
            self._end_control_action()

    def open_human_link(
        self,
        *,
        link_id: str,
        frame_binding: Any,
        human_control_token: str | None,
    ) -> ActionExecutionResult:
        """Re-resolve one server-listed anchor, then navigate without DOM activation."""
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(lambda: self.open_human_link(
                link_id=link_id,
                frame_binding=frame_binding,
                human_control_token=human_control_token,
            ))
        if (not isinstance(link_id, str)
                or not re.fullmatch(r"bl_[A-Za-z0-9_-]{16,64}", link_id)):
            raise BrowserLinkError("BROWSER_LINK_STALE")
        if self.status != SessionStatus.RUNNING or self._page is None:
            raise BrowserLinkError("BROWSER_LINK_STALE")
        self._begin_control_action(
            control_mode="human",
            human_control_token=human_control_token,
        )
        try:
            try:
                self.assert_current_frame_binding(frame_binding, verify_image=False)
            except BrowserFrameStaleError:
                raise BrowserLinkError("BROWSER_LINK_STALE") from None
            binding_copy = self._current_frame_binding_copy()
            with self._human_link_lock:
                choice = self._human_link_choices.get(link_id)
                stored_binding = self._human_link_frame_binding
                stored_lease_digest = self._human_link_lease_digest
                choice = dict(choice) if isinstance(choice, dict) else None
            with self._control_lock:
                self._expire_human_control_locked()
                lease_digest = self._human_control_token_digest
            if (choice is None or stored_binding != binding_copy
                    or choice.get("frame_binding") != binding_copy
                    or stored_lease_digest is None
                    or stored_lease_digest != lease_digest):
                raise BrowserLinkError("BROWSER_LINK_STALE")

            index = choice.get("index")
            if type(index) is not int or not 0 <= index < MAX_HUMAN_LINK_SCAN:
                raise BrowserLinkError("BROWSER_LINK_STALE")
            try:
                from playwright.sync_api import Error as PlaywrightError
            except ImportError:
                raise BrowserLinkError("BROWSER_LINK_STALE") from None
            try:
                current = self._page.evaluate(_HUMAN_LINK_RESOLVE_JS, index)
            except PlaywrightError:
                raise BrowserLinkError("BROWSER_LINK_STALE") from None
            if (not isinstance(current, dict) or current.get("visible") is not True
                    or current.get("index") != index
                    or current.get("href") != choice.get("href")):
                raise BrowserLinkError("BROWSER_LINK_STALE")
            destination = _approved_human_link_destination(current.get("href"))
            label = _safe_human_link_label(current.get("label"), destination or "")
            if (destination is None or destination != choice.get("destination")
                    or label != choice.get("label")):
                raise BrowserLinkError("BROWSER_LINK_STALE")

            resolved_task_id, resolved_run_id = self._resolve_task_trace(None, None)
            return self._execute_action_impl(
                action_type=BrowserActionType.NAVIGATE,
                url=choice["href"],
                task_id=resolved_task_id,
                run_id=resolved_run_id,
                agent_id="human_direct",
                risk_level="medium",
                human_link_navigation_guard=True,
            )
        finally:
            self._end_control_action()

    def _run_with_human_link_navigation_guard(
        self,
        operation: Callable[[], ActionExecutionResult],
    ) -> ActionExecutionResult:
        """Check each main-frame document request, including redirect hops, before send."""
        if self._context is None or self._page is None:
            raise BrowserLinkError("BROWSER_NAVIGATION_GUARD_UNAVAILABLE")
        try:
            from playwright.sync_api import Error as PlaywrightError
        except ImportError:
            raise BrowserLinkError("BROWSER_NAVIGATION_GUARD_UNAVAILABLE") from None

        cdp = None
        fetch_enable_attempted = False
        guard_state = {"blocked": False, "guard_failed": False}

        def close_owned_context() -> None:
            try:
                if self._context is not None:
                    self._context.close()
            except PlaywrightError:
                pass
            self._page = None
            self._context = None
            self._target_id = None
            self.status = SessionStatus.ERROR
            self._latest_frame_binding = None
            self._latest_frame_image_sha256 = None
            self._latest_frame_document_url = None
            self._invalidate_human_links()

        try:
            cdp = self._context.new_cdp_session(self._page)
            frame_tree = cdp.send("Page.getFrameTree")
            tree = frame_tree.get("frameTree") if isinstance(frame_tree, dict) else None
            main_frame = tree.get("frame") if isinstance(tree, dict) else None
            main_frame_id = main_frame.get("id") if isinstance(main_frame, dict) else None
            if not isinstance(main_frame_id, str) or not main_frame_id:
                raise BrowserLinkError("BROWSER_NAVIGATION_GUARD_UNAVAILABLE")

            def respond(request_id: str, method: str) -> None:
                try:
                    if method == "Fetch.failRequest":
                        cdp.send(method, {
                            "requestId": request_id,
                            "errorReason": "BlockedByClient",
                        })
                    else:
                        cdp.send(method, {"requestId": request_id})
                except PlaywrightError:
                    guard_state["guard_failed"] = True
                    close_owned_context()

            def on_request_paused(event: Any) -> None:
                request_id = event.get("requestId") if isinstance(event, dict) else None
                resource_type = event.get("resourceType") if isinstance(event, dict) else None
                frame_id = event.get("frameId") if isinstance(event, dict) else None
                request = event.get("request") if isinstance(event, dict) else None
                if not isinstance(request_id, str) or not request_id:
                    guard_state["blocked"] = True
                    guard_state["guard_failed"] = True
                    close_owned_context()
                    return
                if resource_type is None:
                    guard_state["blocked"] = True
                    guard_state["guard_failed"] = True
                    close_owned_context()
                    return
                if resource_type != "Document":
                    respond(request_id, "Fetch.continueRequest")
                    return
                if not isinstance(frame_id, str) or not frame_id:
                    guard_state["blocked"] = True
                    respond(request_id, "Fetch.failRequest")
                    return
                if frame_id != main_frame_id:
                    respond(request_id, "Fetch.continueRequest")
                    return

                request_url = request.get("url") if isinstance(request, dict) else None
                try:
                    approved = _approved_human_link_destination(request_url)
                except Exception:
                    logger.exception(
                        "[AIBrowserRuntime] Human link navigation policy failed closed",
                        exc_info=False,
                    )
                    approved = None
                if approved is None:
                    guard_state["blocked"] = True
                    respond(request_id, "Fetch.failRequest")
                    return
                respond(request_id, "Fetch.continueRequest")

            cdp.on("Fetch.requestPaused", on_request_paused)
            fetch_enable_attempted = True
            cdp.send("Fetch.enable", {
                "patterns": [{
                    "urlPattern": "*",
                    "resourceType": "Document",
                    "requestStage": "Request",
                }],
            })
        except BrowserLinkError:
            cleanup_failed = False
            if cdp is not None:
                if fetch_enable_attempted:
                    try:
                        cdp.send("Fetch.disable")
                    except PlaywrightError:
                        cleanup_failed = True
                try:
                    cdp.detach()
                except PlaywrightError:
                    cleanup_failed = True
            if cleanup_failed:
                close_owned_context()
            raise
        except PlaywrightError:
            cleanup_failed = False
            if cdp is not None:
                if fetch_enable_attempted:
                    try:
                        cdp.send("Fetch.disable")
                    except PlaywrightError:
                        cleanup_failed = True
                try:
                    cdp.detach()
                except PlaywrightError:
                    cleanup_failed = True
            if cleanup_failed:
                close_owned_context()
            raise BrowserLinkError("BROWSER_NAVIGATION_GUARD_UNAVAILABLE") from None
        except Exception:
            cleanup_failed = False
            if cdp is not None:
                if fetch_enable_attempted:
                    try:
                        cdp.send("Fetch.disable")
                    except PlaywrightError:
                        cleanup_failed = True
                try:
                    cdp.detach()
                except PlaywrightError:
                    cleanup_failed = True
            if cleanup_failed:
                close_owned_context()
            logger.exception(
                "[AIBrowserRuntime] Human link navigation guard setup failed closed",
                exc_info=False,
            )
            raise BrowserLinkError("BROWSER_NAVIGATION_GUARD_UNAVAILABLE") from None

        self._active_human_link_navigation_guard = guard_state
        result: ActionExecutionResult | None = None
        cleanup_failed = False
        try:
            result = operation()
        finally:
            self._active_human_link_navigation_guard = None
            if guard_state["guard_failed"]:
                close_owned_context()
            else:
                try:
                    cdp.send("Fetch.disable")
                except PlaywrightError:
                    cleanup_failed = True
                    close_owned_context()
                if not cleanup_failed:
                    try:
                        cdp.detach()
                    except PlaywrightError:
                        cleanup_failed = True
                        close_owned_context()

        if guard_state["guard_failed"] or cleanup_failed:
            if result is not None:
                result.success = False
                result.result = ActionResult.FAIL
                result.error = (
                    "BROWSER_NAVIGATION_GUARD_FAILED" if guard_state["guard_failed"]
                    else "BROWSER_NAVIGATION_GUARD_CLEANUP_FAILED"
                )
                result.human_escalation_required = True
                result.escalation_reason = result.error
                return result
            raise BrowserLinkError("BROWSER_NAVIGATION_GUARD_FAILED")

        if guard_state["blocked"] and result is not None and result.success:
            result.success = False
            result.result = ActionResult.FAIL
            result.error = "BROWSER_LINK_DESTINATION_BLOCKED"
            result.human_escalation_required = False
            result.escalation_reason = ""
        if result is None:
            raise BrowserLinkError("BROWSER_NAVIGATION_GUARD_FAILED")
        return result

    def execute_action(
        self,
        action_type: BrowserActionType,
        target: str = "",
        selector: str = "",
        text: str = "",
        value: str = "",
        url: str = "",
        expected: Optional[ExpectedState] = None,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        step_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        skill_id: Optional[str] = None,
        risk_level: str = "medium",
        *,
        control_mode: str = "agent",
        human_control_token: Optional[str] = None,
        frame_binding: Optional[Dict[str, Any]] = None,
    ) -> ActionExecutionResult:
        """Apply control lease, immutable task trace and optional frame binding."""
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(lambda: self.execute_action(
                action_type, target, selector, text, value, url, expected,
                task_id, run_id, step_id, agent_id, skill_id, risk_level,
                control_mode=control_mode,
                human_control_token=human_control_token,
                frame_binding=frame_binding,
            ))
        if control_mode == "human":
            self.assert_current_frame_binding(frame_binding)
        self._check_bound_task_operation(action_type, target=target, selector=selector, text=text, value=value, url=url)
        resolved_task_id, resolved_run_id = self._resolve_task_trace(task_id, run_id)
        self._begin_control_action(
            control_mode=control_mode,
            human_control_token=human_control_token,
        )
        try:
            return self._execute_action_impl(
                action_type=action_type,
                target=target,
                selector=selector,
                text=text,
                value=value,
                url=url,
                expected=expected,
                task_id=resolved_task_id,
                run_id=resolved_run_id,
                step_id=step_id,
                agent_id="human_direct" if control_mode == "human" else agent_id,
                skill_id=skill_id,
                risk_level=risk_level,
            )
        finally:
            self._end_control_action()

    def _execute_action_impl(
        self,
        action_type: BrowserActionType,
        target: str = "",
        selector: str = "",
        text: str = "",
        value: str = "",
        url: str = "",
        expected: Optional[ExpectedState] = None,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        step_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        skill_id: Optional[str] = None,
        risk_level: str = "medium",
        human_link_navigation_guard: bool = False,
    ) -> ActionExecutionResult:
        """执行一个 Browser Action，完整闭环：Firewall → Before → Execute → After → Verify → Recovery → Evidence。

        这是核心方法。所有 Action 必须经过此方法。
        """
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(lambda: self.execute_action(
                action_type, target, selector, text, value, url, expected,
                task_id, run_id, step_id, agent_id, skill_id, risk_level,
            ))
        self._page_revision += 1
        self._invalidate_human_links()
        self._latest_frame_binding = None
        self._latest_frame_image_sha256 = None
        self._latest_frame_document_url = None
        if action_type in {BrowserActionType.NAVIGATE, BrowserActionType.RELOAD,
                           BrowserActionType.BACK, BrowserActionType.FORWARD}:
            self._last_navigation_at = time.monotonic()
        self.last_activity = time.time()
        timestamp = datetime.now().isoformat()

        # 1. Action Firewall 检查
        firewall_allowed, firewall_reason = self.firewall.check_action(
            action_type, target=target, selector=selector, text=text,
            url=url or (self._page.url if self._page else ""),
        )
        if not firewall_allowed:
            result = ActionExecutionResult(
                success=False,
                action=action_type.value,
                result=ActionResult.FAIL,
                error=firewall_reason,
                human_escalation_required=False,
            )
            # 记录 Evidence（被拦截的操作也要留痕）
            self._record_evidence(
                action=action_type.value, target=target, selector=selector,
                timestamp=timestamp, result=ActionResult.FAIL.value,
                error=firewall_reason, task_id=task_id, run_id=run_id,
                step_id=step_id, agent_id=agent_id, skill_id=skill_id,
                risk_level="critical",
            )
            return result

        # 2. Circuit Breaker 检查
        if self.recovery.circuit_breaker.is_open():
            cb_state = self.recovery.circuit_breaker.get_state()
            return ActionExecutionResult(
                success=False,
                action=action_type.value,
                result=ActionResult.FAIL,
                error=f"Circuit Breaker 熔断中: {cb_state}",
                human_escalation_required=True,
                escalation_reason="连续失败熔断，需要人工介入检查",
            )

        # 3. 执行前状态捕获
        before_state = self.observe()

        # 4. 执行 Action（带 Recovery）
        try:
            def execute_action() -> ActionExecutionResult:
                return self._execute_with_recovery(
                    action_type=action_type,
                    target=target, selector=selector, text=text, value=value, url=url,
                    before_state=before_state,
                    expected=expected,
                )

            if human_link_navigation_guard:
                execution_result = self._run_with_human_link_navigation_guard(
                    execute_action,
                )
            else:
                execution_result = execute_action()
        except BrowserLinkError as error:
            execution_result = ActionExecutionResult(
                success=False,
                action=action_type.value,
                result=ActionResult.FAIL,
                before_state=before_state,
                error=error.code,
                human_escalation_required=True,
                escalation_reason=error.code,
            )

        # 5. 记录 Evidence
        evidence_id = self._record_evidence(
            action=action_type.value,
            target=target,
            selector=selector,
            timestamp=timestamp,
            result=execution_result.result.value,
            before_state=json.dumps(before_state.to_dict(), ensure_ascii=False, default=str)[:2000],
            after_state=json.dumps(
                execution_result.after_state.to_dict(), ensure_ascii=False, default=str
            )[:2000] if execution_result.after_state else "",
            before_state_hash=before_state.state_hash(),
            after_state_hash=execution_result.after_state.state_hash() if execution_result.after_state else "",
            verification=json.dumps(
                execution_result.verification.to_dict(), ensure_ascii=False, default=str
            )[:2000] if execution_result.verification else "",
            expected_state=json.dumps(asdict(expected), ensure_ascii=False, default=str)[:1000] if expected else "",
            actual_state=json.dumps(
                execution_result.after_state.to_dict(), ensure_ascii=False, default=str
            )[:1000] if execution_result.after_state else "",
            error=execution_result.error,
            retry_count=len(execution_result.recovery_attempts),
            recovery_strategy=",".join(r.strategy for r in execution_result.recovery_attempts),
            task_id=task_id, run_id=run_id, step_id=step_id,
            agent_id=agent_id, skill_id=skill_id,
            risk_level=risk_level,
        )
        execution_result.evidence_id = evidence_id

        # 6. 更新 Circuit Breaker
        if execution_result.success:
            self.recovery.circuit_breaker.record_success()
        else:
            self.recovery.circuit_breaker.record_failure()

        return execution_result

    def _execute_with_recovery(
        self,
        action_type: BrowserActionType,
        target: str,
        selector: str,
        text: str,
        value: str,
        url: str,
        before_state: BrowserPageState,
        expected: Optional[ExpectedState],
    ) -> ActionExecutionResult:
        """执行 Action 并在失败时尝试 Recovery 策略链。"""
        result = ActionExecutionResult(
            success=False,
            action=action_type.value,
            result=ActionResult.FAIL,
            before_state=before_state,
        )

        try:
            # 首次执行
            self._do_execute(action_type, target=target, selector=selector,
                             text=text, value=value, url=url)
            after_state = self.observe()
            result.after_state = after_state

            # Verification
            if expected:
                verification = self.verifier.verify(expected, after_state.verification_state())
                result.verification = verification
                if verification.passed:
                    result.success = True
                    result.result = ActionResult.PASS
                    return result
                else:
                    result.error = f"Verification failed: {'; '.join(verification.differences)}"
            else:
                # 没有期望状态时，只要执行无异常即视为 PASS
                result.success = True
                result.result = ActionResult.PASS
                return result

        except Exception as e:
            link_guard = self._active_human_link_navigation_guard
            if link_guard is not None and (
                link_guard["blocked"] or link_guard["guard_failed"]
            ):
                result.result = ActionResult.FAIL
                if link_guard["guard_failed"]:
                    result.error = "BROWSER_NAVIGATION_GUARD_FAILED"
                    result.human_escalation_required = True
                    result.escalation_reason = result.error
                else:
                    result.error = "BROWSER_LINK_DESTINATION_BLOCKED"
                return result

            result.error = redact_browser_url_queries(sanitize_sensitive(str(e)[:500]))
            failure_class = self.recovery.classify_failure(e, {"url": url or (self._page.url if self._page else "")})

            # 权限拒绝不重试，直接返回
            if failure_class == FailureClass.PERMISSION_DENIED:
                result.result = ActionResult.FAIL
                result.human_escalation_required = True
                result.escalation_reason = f"权限被拒绝: {result.error}"
                return result

            # An exception may occur after the browser applied the effect. Read back
            # before any replay; page readiness alone is not an action postcondition.
            read_only_actions = {BrowserActionType.OBSERVE, BrowserActionType.SCREENSHOT,
                                 BrowserActionType.WAIT}
            meaningful_expected = expected is not None and any(
                value is not None for name, value in asdict(expected).items()
                if name not in {"loading_complete", "custom_check"}
            )
            if failure_class != FailureClass.SESSION_ERROR and meaningful_expected:
                try:
                    observed = self.observe()
                    result.after_state = observed
                    verification = self.verifier.verify(expected, observed.verification_state())
                    result.verification = verification
                    result.recovery_attempts.append(RecoveryAttempt(
                        strategy="observe_before_retry", success=verification.passed,
                        detail="postcondition checked without replaying the action"))
                    before_verification = self.verifier.verify(expected, before_state.verification_state())
                    if verification.passed and not before_verification.passed:
                        result.success = True
                        result.result = ActionResult.PASS
                        result.error = None
                        return result
                except Exception:
                    # Unknown readback does not authorize repeating a possible effect.
                    pass
            if failure_class == FailureClass.SESSION_ERROR:
                self.status = SessionStatus.NEED_VERIFY
            if action_type not in read_only_actions:
                result.result = ActionResult.HUMAN_ESCALATION
                result.human_escalation_required = True
                result.escalation_reason = "BROWSER_EFFECT_UNCERTAIN_REOBSERVE_REQUIRED"
                return result

            # 尝试 Recovery 策略链
            strategies = self.recovery.get_recovery_strategies(failure_class)
            for strategy in strategies:
                if strategy == "human_escalation":
                    break

                recovery_success = self._try_recovery_strategy(
                    strategy, action_type, target, selector, text, value, url
                )
                result.recovery_attempts.append(RecoveryAttempt(
                    strategy=strategy,
                    success=recovery_success,
                    detail=f"recovery for {action_type.value}",
                ))

                if recovery_success:
                    # Recovery 后重新验证
                    after_state = self.observe()
                    result.after_state = after_state
                    if expected:
                        verification = self.verifier.verify(expected, after_state.verification_state())
                        result.verification = verification
                        if verification.passed:
                            result.success = True
                            result.result = ActionResult.RETRY
                            return result
                    else:
                        result.success = True
                        result.result = ActionResult.RETRY
                        return result

            # 所有 Recovery 策略失败 → Human Escalation
            result.result = ActionResult.HUMAN_ESCALATION
            result.human_escalation_required = True
            result.escalation_reason = (
                f"所有 Recovery 策略失败。failure_class={failure_class.value}, "
                f"error={result.error}"
            )
            # 捕获最终状态截图作为 Evidence
            try:
                if self._page:
                    screenshot_bytes = self._page.screenshot(full_page=False)
                    evidence_path = self.evidence_store.save_screenshot(
                        screenshot_bytes, self.session_id, action_type.value
                    )
                    result.after_state = self.observe()
            except Exception:
                pass

        return result

    def _try_recovery_strategy(
        self,
        strategy: str,
        action_type: BrowserActionType,
        target: str,
        selector: str,
        text: str,
        value: str,
        url: str,
    ) -> bool:
        """尝试单个 Recovery 策略。"""
        try:
            if strategy in ("retry_same_selector", "wait_and_retry", "increase_timeout_retry"):
                time.sleep(1)
                self._do_execute(action_type, target=target, selector=selector,
                                 text=text, value=value, url=url)
                return True

            if strategy == "reload_page":
                if self._page:
                    self._page.reload(wait_until="domcontentloaded", timeout=15000)
                    time.sleep(0.5)
                    self._do_execute(action_type, target=target, selector=selector,
                                     text=text, value=value, url=url)
                    return True

            if strategy == "navigate_back_then_forward":
                if self._page:
                    self._page.go_back(wait_until="domcontentloaded", timeout=10000)
                    time.sleep(0.5)
                    self._page.go_forward(wait_until="domcontentloaded", timeout=10000)
                    return True

            if strategy in ("alternative_css_selector", "xpath_selector", "text_match", "coordinate_click"):
                # 尝试备用定位策略
                alt_selector = self._find_alternative_selector(selector, text, strategy)
                if alt_selector:
                    self._do_execute(action_type, target=target, selector=alt_selector,
                                     text=text, value=value, url=url)
                    return True

            if strategy == "scroll_then_click":
                if self._page and selector:
                    try:
                        self._page.eval_on_selector(selector, "el => el.scrollIntoView({block:'center'})")
                        time.sleep(0.3)
                    except Exception:
                        pass
                    self._do_execute(action_type, target=target, selector=selector,
                                     text=text, value=value, url=url)
                    return True

            if strategy in ("retry_exponential_backoff", "retry_exponential_backoff_2"):
                time.sleep(2 if "2" in strategy else 1)
                self._do_execute(action_type, target=target, selector=selector,
                                 text=text, value=value, url=url)
                return True

            if strategy == "wait_for_network_idle":
                if self._page:
                    self._page.wait_for_load_state("networkidle", timeout=15000)
                    self._do_execute(action_type, target=target, selector=selector,
                                     text=text, value=value, url=url)
                    return True

            if strategy == "mark_need_verify":
                self.status = SessionStatus.NEED_VERIFY
                return False  # 标记后仍需人工，不算成功

            return False
        except Exception as e:
            logger.debug(
                "[AIBrowserRuntime] Recovery strategy '%s' failed: %s",
                strategy,
                redact_browser_url_queries(sanitize_sensitive(str(e)[:500])),
            )
            return False

    def _find_alternative_selector(
        self, original_selector: str, text: str, strategy: str
    ) -> Optional[str]:
        """尝试查找备用选择器。"""
        if not self._page:
            return None
        try:
            if strategy == "text_match" and text:
                # 通过文本查找元素
                escaped_text = text.replace("'", "\\'")
                xpath = f"//*[contains(text(), '{escaped_text}')]"
                elem = self._page.query_selector(f"xpath={xpath}")
                if elem:
                    return f"xpath={xpath}"

            if strategy == "xpath_selector":
                # 尝试将 CSS 选择器转为简单 XPath（仅处理简单情况）
                if original_selector.startswith("#"):
                    xpath = f"//*[@id='{original_selector[1:]}']"
                    return f"xpath={xpath}"
                elif original_selector.startswith("."):
                    xpath = f"//*[contains(@class, '{original_selector[1:]}')]"
                    return f"xpath={xpath}"

            return None
        except Exception:
            return None

    def _do_execute(
        self,
        action_type: BrowserActionType,
        target: str = "",
        selector: str = "",
        text: str = "",
        value: str = "",
        url: str = "",
    ):
        """执行原始 Playwright 操作（不含 Verification/Recovery）。"""
        self._check_bound_task_operation(action_type, target=target, selector=selector, text=text, value=value, url=url)
        admission = getattr(self, "_server_task_admission", None)
        if admission is not None:
            # Final short dispatch admission only. The original queue fence
            # must never span browser/network acquisition. In-flight external
            # effects cannot be rolled back when authority subsequently changes.
            with admission.guard():
                self._check_bound_task_owner(admission, attempt_guarded=True)
        return self._do_execute_impl(action_type, target, selector, text, value, url)

    def _do_execute_impl(self, action_type, target="", selector="", text="", value="", url=""):
        if not self._page and action_type not in (BrowserActionType.NAVIGATE, BrowserActionType.TAB_NEW):
            raise RuntimeError("No active page. Call start() first or navigate to create a page.")

        if action_type == BrowserActionType.NAVIGATE:
            if not url:
                raise ValueError("navigate requires url parameter")
            import browser_surface

            navigation = browser_surface.evaluate_navigation(url)
            if not navigation.get("allowed"):
                raise PermissionError("AI Browser navigation is blocked by the existing browser policy")
            self._page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_ACTION_TIMEOUT)

        elif action_type == BrowserActionType.BACK:
            self._page.go_back(wait_until="domcontentloaded", timeout=15000)

        elif action_type == BrowserActionType.FORWARD:
            self._page.go_forward(wait_until="domcontentloaded", timeout=15000)

        elif action_type == BrowserActionType.RELOAD:
            self._page.reload(wait_until="domcontentloaded", timeout=15000)

        elif action_type == BrowserActionType.CLICK:
            if not selector:
                raise ValueError("click requires selector")
            self._page.click(selector, timeout=DEFAULT_ACTION_TIMEOUT)

        elif action_type == BrowserActionType.INPUT:
            if not selector:
                raise ValueError("input requires selector")
            self._page.fill(selector, value or text, timeout=DEFAULT_ACTION_TIMEOUT)

        elif action_type == BrowserActionType.SELECT:
            if not selector:
                raise ValueError("select requires selector")
            self._page.select_option(selector, value=value, timeout=DEFAULT_ACTION_TIMEOUT)

        elif action_type == BrowserActionType.SCROLL:
            scroll_y = int(value) if value else 500
            self._page.evaluate(f"() => window.scrollBy(0, {scroll_y})")

        elif action_type == BrowserActionType.KEYBOARD:
            if text:
                self._page.keyboard.type(text, delay=50)
            elif value:
                self._page.keyboard.press(value)

        elif action_type == BrowserActionType.WAIT:
            wait_ms = int(value) if value else 1000
            time.sleep(wait_ms / 1000.0)

        elif action_type == BrowserActionType.TAB_NEW:
            if url:
                import browser_surface
                navigation = browser_surface.evaluate_navigation(url)
                if not navigation.get("allowed"):
                    raise PermissionError("AI Browser navigation is blocked by the existing browser policy")
            if self._context:
                new_page = self._context.new_page()
                tab_id = f"tab_{uuid.uuid4().hex[:8]}"
                self._pages[tab_id] = new_page
                self._page = new_page
                self._target_id = f"bt_{uuid.uuid4().hex}"
                if url:
                    new_page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_ACTION_TIMEOUT)
            else:
                raise RuntimeError("No browser context")

        elif action_type == BrowserActionType.TAB_SWITCH:
            tab_id = target or selector
            if tab_id in self._pages:
                self._page = self._pages[tab_id]
                self._target_id = f"bt_{uuid.uuid4().hex}"
            else:
                raise ValueError(f"Tab not found: {tab_id}")

        elif action_type == BrowserActionType.TAB_CLOSE:
            tab_id = target or selector
            if tab_id in self._pages:
                self._pages[tab_id].close()
                del self._pages[tab_id]
                if self._pages:
                    self._page = list(self._pages.values())[-1]
                    self._target_id = f"bt_{uuid.uuid4().hex}"
                else:
                    self._page = None
                    self._target_id = None
            else:
                raise ValueError(f"Tab not found: {tab_id}")

        elif action_type == BrowserActionType.SCREENSHOT:
            # 截图由 Evidence 层处理，这里不做实际操作
            pass

        elif action_type == BrowserActionType.SEARCH:
            # 页面内文本搜索
            if text:
                found = self._page.evaluate(
                    f"""() => {{
                        const text = {json.dumps(text)};
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                        let count = 0;
                        while (walker.nextNode()) {{
                            if (walker.currentNode.textContent.includes(text)) count++;
                        }}
                        return count;
                    }}"""
                )
                return {"found": found}

        elif action_type == BrowserActionType.STOP:
            self.close()

        else:
            raise ValueError(f"Unsupported action type: {action_type.value}")

    # ──────────────────────────────────────────────────────────
    # Evidence 记录辅助
    # ──────────────────────────────────────────────────────────

    def _record_evidence(self, **kwargs) -> int:
        """记录 Browser Evidence。"""
        record = BrowserEvidenceRecord(
            action=kwargs.get("action", ""),
            timestamp=kwargs.get("timestamp", datetime.now().isoformat()),
            result=kwargs.get("result", ""),
            task_id=kwargs.get("task_id"),
            run_id=kwargs.get("run_id"),
            step_id=kwargs.get("step_id"),
            agent_id=kwargs.get("agent_id"),
            skill_id=kwargs.get("skill_id"),
            session_id=self.session_id,
            target=kwargs.get("target"),
            selector=kwargs.get("selector"),
            before_state=kwargs.get("before_state"),
            after_state=kwargs.get("after_state"),
            before_state_hash=kwargs.get("before_state_hash"),
            after_state_hash=kwargs.get("after_state_hash"),
            evidence_path=kwargs.get("evidence_path"),
            dom_snapshot=kwargs.get("dom_snapshot"),
            console_errors=kwargs.get("console_errors"),
            verification=kwargs.get("verification"),
            expected_state=kwargs.get("expected_state"),
            actual_state=kwargs.get("actual_state"),
            error=kwargs.get("error"),
            retry_count=kwargs.get("retry_count", 0),
            recovery_strategy=kwargs.get("recovery_strategy"),
            risk_level=kwargs.get("risk_level", "medium"),
        )
        return self.evidence_store.record(record)

    # ──────────────────────────────────────────────────────────
    # 便捷方法
    # ──────────────────────────────────────────────────────────

    def navigate(self, url: str, expected: Optional[ExpectedState] = None, **kwargs) -> ActionExecutionResult:
        return self.execute_action(BrowserActionType.NAVIGATE, url=url, expected=expected, **kwargs)

    def click(self, selector: str, expected: Optional[ExpectedState] = None, **kwargs) -> ActionExecutionResult:
        return self.execute_action(BrowserActionType.CLICK, selector=selector, expected=expected, **kwargs)

    def input(self, selector: str, value: str, expected: Optional[ExpectedState] = None, **kwargs) -> ActionExecutionResult:
        return self.execute_action(BrowserActionType.INPUT, selector=selector, value=value, expected=expected, **kwargs)

    def screenshot(self, full_page: bool = False) -> bytes:
        """获取当前页面截图（不经过 Action 闭环，仅供 Observe/Evidence 使用）。"""
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(lambda: self.screenshot(full_page))
        if not self._page:
            raise RuntimeError("No active page")
        return self._page.screenshot(full_page=full_page)

    def capture_frame(self) -> Dict[str, Any]:
        """Capture only this session's active page for the authorized product UI."""
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(self.capture_frame)
        self._invalidate_human_links()
        self._latest_frame_binding = None
        self._latest_frame_image_sha256 = None
        self._latest_frame_document_url = None
        if self.status != SessionStatus.RUNNING or not self._target_id:
            raise RuntimeError("Browser frame has no active authorized target")
        captured_document_url = self._page.url
        image = self.screenshot(full_page=False)
        if self._page.url != captured_document_url:
            raise BrowserFramePending("Browser document changed during frame capture")
        if len(image) < 24 or image[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("Browser frame is not a valid PNG")
        width, height = struct.unpack(">II", image[16:24])
        if width <= 0 or height <= 0:
            raise RuntimeError("Browser frame dimensions are invalid")
        if self._page.url != "about:blank":
            text_length = self._page.evaluate(
                "document.body ? document.body.innerText.trim().length : 0"
            )
            sparse_image = len(image) < max(8192, width * height // 64)
            recently_navigated = time.monotonic() - self._last_navigation_at < 3.0
            if sparse_image and text_length < 16:
                if recently_navigated:
                    raise BrowserFramePending("Browser page is still painting")
                raise BrowserFrameEmpty("Browser page has no usable visible content")
        frame_id = f"bf_{uuid.uuid4().hex}"
        viewport = self._current_viewport()
        frame_binding = {
            "frame_id": frame_id,
            "target_id": self._target_id,
            "page_revision": self._page_revision,
            "viewport": viewport,
        }
        self._latest_frame_binding = frame_binding
        self._latest_frame_image_sha256 = hashlib.sha256(image).hexdigest()
        self._latest_frame_document_url = captured_document_url
        return {
            "frame_id": frame_id,
            "target_id": self._target_id,
            "page_revision": self._page_revision,
            "viewport": viewport,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "width": width,
            "height": height,
            "image": image,
        }

    def get_console_errors(self) -> List[str]:
        """获取控制台错误（已脱敏）。"""
        return [sanitize_sensitive(e) for e in self._console_errors]


# ═══════════════════════════════════════════════════════════════
# 9. Session Manager（全局 Session 管理）
# ═══════════════════════════════════════════════════════════════

class BrowserCapacityError(RuntimeError):
    """The single synchronous browser slot belongs to another login."""


class BrowserFramePending(RuntimeError):
    """The page has not painted enough content for a useful product frame."""


class BrowserFrameEmpty(RuntimeError):
    """The page remained visually empty after the bounded paint window."""


class BrowserSessionManager:
    """全局 Browser Session 管理器。

    负责 Session 的创建、查询、关闭、空闲清理。
    AI Browser Session 与用户日常浏览 Session 隔离（独立 profile）。
    """

    # Lifecycle: session-level lifecycle workers (bypass-mode)
    _lifecycle_sessions = {}

    def __init__(self):
        self._sessions: Dict[str, AIBrowserRuntime] = {}
        self._lock = threading.Lock()
        self._cleanup_running = False

    def create_session(
        self,
        cdp_port: int = 9224,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        owner_actor_id: Optional[int] = None,
        owner_account_session_id: Optional[int] = None,
        owner_principal_ref: Optional[str] = None,
        idle_timeout: int = DEFAULT_SESSION_IDLE_TIMEOUT,
        max_lifetime: int = DEFAULT_SESSION_MAX_LIFETIME,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> AIBrowserRuntime:
        """Create only a session on the verified isolated product browser."""
        if cdp_port != 9224 or headless is not True or user_data_dir not in (None, ""):
            raise ValueError("AI Browser session must use the isolated LUMENIS browser")
        owner_key = self._owner_key(
            owner_actor_id=owner_actor_id,
            owner_account_session_id=owner_account_session_id,
            owner_principal_ref=owner_principal_ref,
        )
        with self._lock:
            if owner_key is not None:
                for existing in self._sessions.values():
                    if (self._session_owner_key(existing) is not None and
                            existing.status not in {SessionStatus.CLOSED, SessionStatus.ERROR} and
                            existing.is_alive()):
                        if self._session_owner_key(existing) == owner_key:
                            if existing.task_id != task_id or existing.run_id != run_id:
                                raise BrowserSessionBindingError(
                                    "BROWSER_TASK_BINDING_CONFLICT"
                                )
                            return existing
                        raise BrowserCapacityError("AI Browser is busy with another product login")
            session = AIBrowserRuntime(
                cdp_port=cdp_port,
                headless=headless,
                user_data_dir=user_data_dir,
                owner_actor_id=owner_actor_id,
                owner_account_session_id=owner_account_session_id,
                owner_principal_ref=owner_principal_ref,
                idle_timeout=idle_timeout,
                max_lifetime=max_lifetime,
                task_id=task_id,
                run_id=run_id,
            )
            self._sessions[session.session_id] = session
        logger.info(f"[SessionManager] Session 创建: {session.session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[AIBrowserRuntime]:
        """获取 Session。"""
        with self._lock:
            session = self._sessions.get(session_id)
        if session and not session.is_alive():
            return None
        return session

    def close_session(self, session_id: str) -> bool:
        """关闭 Session。"""
        # Lifecycle: cleanup session worker (bypass-mode)
        _lc = BrowserSessionManager._lifecycle_sessions.pop(session_id, None)
        if _lc:
            try:
                _lc.lifecycle_cleanup(reason="session_closed")
            except Exception:
                pass
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            session.close()
            logger.info(f"[SessionManager] Session 关闭: {session_id}")
            return True
        return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有活跃 Session。"""
        with self._lock:
            sessions = list(self._sessions.values())
        result = []
        for s in sessions:
            if s.is_alive():
                result.append(s.get_status())
        return result

    def list_sessions_for_actor(self, actor_id: int, account_session_id: int) -> List[Dict[str, Any]]:
        """Expose only sessions created by this authenticated product login."""
        return self.list_sessions_for_owner(
            owner_actor_id=actor_id,
            owner_account_session_id=account_session_id,
        )

    @staticmethod
    def _owner_key(
        *,
        owner_actor_id: Optional[int] = None,
        owner_account_session_id: Optional[int] = None,
        owner_principal_ref: Optional[str] = None,
    ) -> Optional[tuple[str, object, object]]:
        if type(owner_actor_id) is int and type(owner_account_session_id) is int:
            return ("account", owner_actor_id, owner_account_session_id)
        if owner_principal_ref == "workspace:local":
            return ("workspace", owner_principal_ref, "")
        return None

    @classmethod
    def _session_owner_key(cls, session: AIBrowserRuntime) -> Optional[tuple[str, object, object]]:
        return cls._owner_key(
            owner_actor_id=session.owner_actor_id,
            owner_account_session_id=session.owner_account_session_id,
            owner_principal_ref=session.owner_principal_ref,
        )

    def list_sessions_for_owner(
        self,
        *,
        owner_actor_id: Optional[int] = None,
        owner_account_session_id: Optional[int] = None,
        owner_principal_ref: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Expose only sessions belonging to one authenticated or local owner."""
        owner_key = self._owner_key(
            owner_actor_id=owner_actor_id,
            owner_account_session_id=owner_account_session_id,
            owner_principal_ref=owner_principal_ref,
        )
        if owner_key is None:
            return []
        with self._lock:
            sessions = [
                session
                for session in self._sessions.values()
                if self._session_owner_key(session) == owner_key
            ]
        return [s.get_status() for s in sessions if s.is_alive()]

    def cleanup_idle_sessions(self) -> int:
        """清理空闲/过期 Session。返回清理数量。"""
        cleaned = 0
        with self._lock:
            to_remove = []
            for sid, session in self._sessions.items():
                if not session.is_alive():
                    to_remove.append(sid)
            for sid in to_remove:
                session = self._sessions.pop(sid, None)
                if session:
                    session.close()
                    cleaned += 1
        if cleaned:
            logger.info(f"[SessionManager] 清理了 {cleaned} 个空闲/过期 Session")
        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._sessions)
            active = sum(1 for s in self._sessions.values() if s.status == SessionStatus.RUNNING)
        return {
            "total_sessions": total,
            "active_sessions": active,
            "session_ids": list(self._sessions.keys()),
        }


# 全局单例
_default_session_manager: Optional[BrowserSessionManager] = None


def get_session_manager() -> BrowserSessionManager:
    global _default_session_manager
    if _default_session_manager is None:
        _default_session_manager = BrowserSessionManager()
    return _default_session_manager


# ═══════════════════════════════════════════════════════════════
# 10. 模块导出
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # 枚举
    "BrowserActionType", "ActionResult", "SessionStatus", "FailureClass",
    # 安全
    "sanitize_sensitive", "sanitize_dict", "hash_state",
    "PromptInjectionGuard", "get_injection_guard",
    "ActionFirewall", "get_action_firewall",
    # Evidence
    "BrowserEvidenceRecord", "BrowserEvidenceStore", "get_evidence_store",
    "init_browser_evidence_db", "BROWSER_EVIDENCE_SCHEMA",
    # Verification
    "ExpectedState", "VerificationResult", "ActionVerifier",
    # Recovery
    "CircuitBreaker", "RecoveryAttempt", "FailureRecovery",
    # Runtime
    "BrowserPageState", "ActionExecutionResult", "AIBrowserRuntime",
    "BrowserSessionManager", "get_session_manager",
    # 常量
    "DB_PATH", "DEFAULT_SESSION_IDLE_TIMEOUT", "DEFAULT_SESSION_MAX_LIFETIME",
    "CB_FAILURE_THRESHOLD", "CB_COOLDOWN_SECONDS",
]
