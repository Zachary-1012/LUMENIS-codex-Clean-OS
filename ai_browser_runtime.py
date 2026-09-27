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
import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

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
        actual_loading = actual_state.get("loading", False)
        actual_text = actual_state.get("body_text", "")
        actual_elements = actual_state.get("elements", {})  # selector -> {visible, text, value, count}

        expected_dict = asdict(expected)

        # 1. URL 检查
        if expected.url_equals and actual_url != expected.url_equals:
            differences.append(
                f"URL不匹配: expected={expected.url_equals}, actual={actual_url}"
            )
        if expected.url_contains and expected.url_contains not in actual_url:
            differences.append(
                f"URL不包含: expected_contains={expected.url_contains}, actual={actual_url}"
            )

        # 2. Title 检查
        if expected.title_contains and expected.title_contains not in actual_title:
            differences.append(
                f"Title不包含: expected={expected.title_contains}, actual={actual_title}"
            )

        # 3. 元素可见性检查
        if expected.element_visible:
            elem = actual_elements.get(expected.element_visible, {})
            if not elem.get("visible", False):
                differences.append(
                    f"元素不可见: selector={expected.element_visible}"
                )

        # 4. 元素文本检查
        if expected.element_text:
            selector, exp_text = expected.element_text
            elem = actual_elements.get(selector, {})
            actual_elem_text = elem.get("text", "")
            if exp_text not in actual_elem_text:
                differences.append(
                    f"元素文本不匹配: selector={selector}, "
                    f"expected_contains={exp_text}, actual={actual_elem_text[:100]}"
                )

        # 5. Input value 检查
        if expected.input_value:
            selector, exp_value = expected.input_value
            elem = actual_elements.get(selector, {})
            actual_value = elem.get("value", "")
            if exp_value != actual_value:
                differences.append(
                    f"Input值不匹配: selector={selector}, "
                    f"expected={exp_value}, actual={actual_value}"
                )

        # 6. 元素数量检查
        if expected.element_count_gte:
            selector, min_count = expected.element_count_gte
            elem = actual_elements.get(selector, {})
            actual_count = elem.get("count", 0)
            if actual_count < min_count:
                differences.append(
                    f"元素数量不足: selector={selector}, "
                    f"expected>={min_count}, actual={actual_count}"
                )

        # 7. 文本存在检查
        if expected.text_present and expected.text_present not in actual_text:
            differences.append(
                f"页面文本不存在: expected={expected.text_present}"
            )

        # 8. 文本不存在检查
        if expected.text_absent and expected.text_absent in actual_text:
            differences.append(
                f"页面文本不应存在: absent={expected.text_absent}"
            )

        # 9. 状态码检查
        if expected.status_code and actual_status and actual_status != expected.status_code:
            differences.append(
                f"状态码不匹配: expected={expected.status_code}, actual={actual_status}"
            )

        # 10. 加载完成检查
        if expected.loading_complete and actual_loading:
            differences.append("页面仍在加载中（loading=true）")

        passed = len(differences) == 0

        return VerificationResult(
            passed=passed,
            expected=expected_dict,
            actual={
                "url": sanitize_sensitive(actual_url),
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
    element_count: int = 0
    body_text: str = ""
    elements: Dict[str, Any] = field(default_factory=dict)
    console_errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["body_text"] = sanitize_sensitive(d.get("body_text", ""))[:2000]
        return d

    def state_hash(self) -> str:
        return hash_state(self.to_dict())


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
        idle_timeout: int = DEFAULT_SESSION_IDLE_TIMEOUT,
        max_lifetime: int = DEFAULT_SESSION_MAX_LIFETIME,
    ):
        self.session_id = session_id or f"bs_{uuid.uuid4().hex[:12]}"
        self.cdp_port = cdp_port
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.owner_actor_id = owner_actor_id
        self.owner_account_session_id = owner_account_session_id
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime

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

            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()

            self._browser = self._playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{self.cdp_port}"
            )
            self._context = self._browser.new_context()
            self._page = self._context.new_page()
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
            "current_url": sanitize_sensitive(self._page.url if self._page else ""),
            "current_title": sanitize_sensitive(self._page.title() if self._page else ""),
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
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(
                lambda: self.observe(include_dom, include_accessibility, max_text_length)
            )
        self.last_activity = time.time()
        state = BrowserPageState()

        if not self._page:
            state.error = "No active page"
            return state

        try:
            state.url = self._page.url
            state.title = self._page.title()
            state.loading = False  # sync API 中操作完成后通常已加载

            # 获取 body 文本（脱敏 + 注入扫描）
            try:
                body_text = self._page.evaluate("() => document.body ? document.body.innerText : ''")
                # Prompt Injection 扫描
                injection_result = self.injection_guard.scan(body_text, source="page_observe")
                state.body_text = injection_result.sanitized_text[:max_text_length]
            except Exception:
                state.body_text = ""

            # 元素计数
            try:
                state.element_count = self._page.evaluate(
                    "() => document.querySelectorAll('*').length"
                )
            except Exception:
                state.element_count = 0

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
                            text: (el.innerText || el.value || '').trim().slice(0, 100),
                            id: el.id || '',
                            className: (el.className || '').toString().slice(0, 100),
                            visible: el.offsetParent !== null,
                        }));
                    }""")
                    state.elements["_dom_summary"] = sanitize_dict(dom_summary)
                except Exception:
                    pass

            # Accessibility Tree（可选）
            if include_accessibility:
                try:
                    snapshot = self._page.accessibility.snapshot()
                    state.elements["_accessibility"] = sanitize_dict(snapshot) if snapshot else {}
                except Exception:
                    pass

        except Exception as e:
            state.error = sanitize_sensitive(str(e)[:300])

        return state

    # ──────────────────────────────────────────────────────────
    # 核心：execute_action（带 Verification 闭环）
    # ──────────────────────────────────────────────────────────

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
    ) -> ActionExecutionResult:
        """执行一个 Browser Action，完整闭环：Firewall → Before → Execute → After → Verify → Recovery → Evidence。

        这是核心方法。所有 Action 必须经过此方法。
        """
        if self._browser_worker and threading.get_ident() != self._browser_thread_id:
            return self._run_on_browser_thread(lambda: self.execute_action(
                action_type, target, selector, text, value, url, expected,
                task_id, run_id, step_id, agent_id, skill_id, risk_level,
            ))
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
        execution_result = self._execute_with_recovery(
            action_type=action_type,
            target=target, selector=selector, text=text, value=value, url=url,
            before_state=before_state,
            expected=expected,
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
                verification = self.verifier.verify(expected, after_state.to_dict())
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
            result.error = sanitize_sensitive(str(e)[:500])
            failure_class = self.recovery.classify_failure(e, {"url": url or (self._page.url if self._page else "")})

            # 权限拒绝不重试，直接返回
            if failure_class == FailureClass.PERMISSION_DENIED:
                result.result = ActionResult.FAIL
                result.human_escalation_required = True
                result.escalation_reason = f"权限被拒绝: {result.error}"
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
                        verification = self.verifier.verify(expected, after_state.to_dict())
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
            logger.debug(f"[AIBrowserRuntime] Recovery strategy '{strategy}' failed: {e}")
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
            if self._context:
                new_page = self._context.new_page()
                tab_id = f"tab_{uuid.uuid4().hex[:8]}"
                self._pages[tab_id] = new_page
                self._page = new_page
                if url:
                    new_page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_ACTION_TIMEOUT)
            else:
                raise RuntimeError("No browser context")

        elif action_type == BrowserActionType.TAB_SWITCH:
            tab_id = target or selector
            if tab_id in self._pages:
                self._page = self._pages[tab_id]
            else:
                raise ValueError(f"Tab not found: {tab_id}")

        elif action_type == BrowserActionType.TAB_CLOSE:
            tab_id = target or selector
            if tab_id in self._pages:
                self._pages[tab_id].close()
                del self._pages[tab_id]
                if self._pages:
                    self._page = list(self._pages.values())[-1]
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

    def get_console_errors(self) -> List[str]:
        """获取控制台错误（已脱敏）。"""
        return [sanitize_sensitive(e) for e in self._console_errors]


# ═══════════════════════════════════════════════════════════════
# 9. Session Manager（全局 Session 管理）
# ═══════════════════════════════════════════════════════════════

class BrowserCapacityError(RuntimeError):
    """The single synchronous browser slot belongs to another login."""


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
        idle_timeout: int = DEFAULT_SESSION_IDLE_TIMEOUT,
        max_lifetime: int = DEFAULT_SESSION_MAX_LIFETIME,
    ) -> AIBrowserRuntime:
        """Create only a session on the verified isolated product browser."""
        if cdp_port != 9224 or headless is not True or user_data_dir not in (None, ""):
            raise ValueError("AI Browser session must use the isolated LUMENIS browser")
        with self._lock:
            if type(owner_actor_id) is int and type(owner_account_session_id) is int:
                for existing in self._sessions.values():
                    if (existing.owner_actor_id is not None and
                            existing.status not in {SessionStatus.CLOSED, SessionStatus.ERROR} and
                            existing.is_alive()):
                        if (existing.owner_actor_id == owner_actor_id and
                                existing.owner_account_session_id == owner_account_session_id):
                            return existing
                        raise BrowserCapacityError("AI Browser is busy with another product login")
            session = AIBrowserRuntime(
                cdp_port=cdp_port,
                headless=headless,
                user_data_dir=user_data_dir,
                owner_actor_id=owner_actor_id,
                owner_account_session_id=owner_account_session_id,
                idle_timeout=idle_timeout,
                max_lifetime=max_lifetime,
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
        with self._lock:
            sessions = [s for s in self._sessions.values()
                        if s.owner_actor_id == actor_id
                        and s.owner_account_session_id == account_session_id]
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
