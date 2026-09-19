# -*- coding: utf-8 -*-
"""
ZBC Security Boundary（分层安全边界 · Phase 3）
===================================================
四层安全边界架构，每一层独立 validate() + health_check()。

层级：
  L1 EdgeLayer         — 边缘层（WAF/TLS/HSTS/rate_limit 占位）
                         ⚠️ 当前为应用层防护占位，**不是**真正的网络 WAF。
                         真正的网络 WAF 应由反向代理/云厂商提供，本层只做应用内
                         速率限制和请求头校验的占位接口。
  L2 ApplicationLayer  — 应用层（Auth/RBAC/CSRF/CSP/XSS/SQLi/SSRF/路径遍历/命令白名单）
  L3 AIAgentLayer      — AI Agent 层（PermissionGate 集成/Action Firewall/工具白名单/
                         身份绑定/幂等性/人工审批）
  L4 DataLayer         — 数据层（敏感数据/密钥检测/凭证隔离/审计追踪）

设计原则（AGENTS.md）：
  - 安全边界写进代码，不写进提示词
  - 确定性过滤优先于模型判断
  - 最小权限 + 分层防御
  - 不删除现有安全模块，本文件是统一编排入口
"""
from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from lumenis.system.security import (
    PermissionGate,
    PermissionLevel,
    RiskLevel,
    OperationType,
    PermissionResult,
    get_permission_gate,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 通用：层验证结果
# ═══════════════════════════════════════════════════════════════

@dataclass
class LayerValidationResult:
    """单层验证结果。"""
    layer: str
    passed: bool
    score: int                          # 0-100
    checks_total: int
    checks_passed: int
    checks_failed: int
    findings: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "passed": self.passed,
            "score": self.score,
            "checks_total": self.checks_total,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "findings": self.findings,
            "timestamp": self.timestamp,
        }


@dataclass
class BoundaryValidationResult:
    """全边界验证结果（四层汇总）。"""
    overall_passed: bool
    overall_score: int
    layers: Dict[str, LayerValidationResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_passed": self.overall_passed,
            "overall_score": self.overall_score,
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════
# L1: EdgeLayer（边缘层占位）
# ═══════════════════════════════════════════════════════════════

class EdgeLayer:
    """边缘层（WAF/TLS/HSTS/rate_limit 占位）。

    ⚠️ 重要声明：
      本层是**应用层防护占位**，不是真正的网络 WAF。
      真正的网络 WAF（如 ModSecurity、Cloudflare、阿里云 WAF）应部署在
      反向代理/负载均衡层，本层只提供应用内可实现的：
        - 请求速率限制（内存计数器）
        - 安全响应头校验（HSTS/CSP/X-Frame-Options 占位）
        - TLS 配置检查占位
      不实现：包过滤、DDoS 防护、协议层解析。
    """

    LAYER_NAME = "edge"

    def __init__(
        self,
        rate_limit_per_minute: int = 60,
        rate_limit_burst: int = 10,
    ):
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_burst = rate_limit_burst
        # 内存速率计数器：client_id → [timestamps]
        self._rate_counters: Dict[str, List[float]] = {}
        self._rate_lock = threading.Lock()

        # 推荐安全响应头（占位，实际由反向代理设置）
        self.recommended_headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    def check_rate_limit(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """检查客户端速率限制。

        Returns:
            (allowed, info) — allowed=False 表示触发限流
        """
        now = datetime.now().timestamp()
        window_start = now - 60.0
        with self._rate_lock:
            if client_id not in self._rate_counters:
                self._rate_counters[client_id] = []
            # 清理过期时间戳
            self._rate_counters[client_id] = [
                ts for ts in self._rate_counters[client_id] if ts > window_start
            ]
            count = len(self._rate_counters[client_id])
            if count >= self.rate_limit_per_minute:
                return False, {
                    "client_id": client_id,
                    "count": count,
                    "limit": self.rate_limit_per_minute,
                    "window_seconds": 60,
                    "reason": "rate_limit_exceeded",
                }
            self._rate_counters[client_id].append(now)
            return True, {
                "client_id": client_id,
                "count": count + 1,
                "limit": self.rate_limit_per_minute,
            }

    def validate_security_headers(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """校验响应头是否包含推荐安全头。

        注意：这是校验/提示功能，不强制设置（实际由反向代理负责）。
        """
        findings = []
        for header, recommended in self.recommended_headers.items():
            actual = headers.get(header)
            if actual is None:
                findings.append({
                    "check": f"header_missing:{header}",
                    "severity": "medium",
                    "message": f"缺少安全响应头 {header}（推荐值: {recommended}）",
                    "note": "应由反向代理/负载均衡设置，本层仅做校验提示",
                })
        return findings

    def validate(self, context: Optional[Dict[str, Any]] = None) -> LayerValidationResult:
        """边缘层验证。"""
        findings: List[Dict[str, Any]] = []
        checks_total = 3
        checks_passed = 0

        # Check 1: 速率限制配置合理性
        if self.rate_limit_per_minute > 0:
            checks_passed += 1
        else:
            findings.append({
                "check": "rate_limit_config",
                "severity": "high",
                "message": "速率限制未启用（rate_limit_per_minute=0）",
            })

        # Check 2: 安全响应头推荐配置存在
        if len(self.recommended_headers) >= 3:
            checks_passed += 1
        else:
            findings.append({
                "check": "security_headers_config",
                "severity": "medium",
                "message": "安全响应头推荐配置不足",
            })

        # Check 3: 声明非网络 WAF（文档完整性）
        checks_passed += 1  # 本层代码已明确声明

        # 如果 context 包含实际响应头，做校验
        if context and "response_headers" in context:
            header_findings = self.validate_security_headers(context["response_headers"])
            findings.extend(header_findings)
            if not header_findings:
                checks_passed += 1
                checks_total += 1

        score = int(checks_passed / checks_total * 100) if checks_total else 0
        checks_failed = checks_total - checks_passed
        passed = checks_failed == 0
        return LayerValidationResult(
            layer=self.LAYER_NAME,
            passed=passed,
            score=score,
            checks_total=checks_total,
            checks_passed=checks_passed,
            checks_failed=checks_total - checks_passed,
            findings=findings,
        )

    def health_check(self) -> Dict[str, Any]:
        """边缘层健康检查。"""
        with self._rate_lock:
            tracked_clients = len(self._rate_counters)
        return {
            "layer": self.LAYER_NAME,
            "status": "healthy",
            "is_network_waf": False,
            "note": "应用层防护占位，非网络 WAF",
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_burst": self.rate_limit_burst,
            "tracked_clients": tracked_clients,
            "recommended_headers_count": len(self.recommended_headers),
            "timestamp": datetime.now().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# L2: ApplicationLayer（应用层）
# ═══════════════════════════════════════════════════════════════

class ApplicationLayer:
    """应用层安全（Auth/RBAC/CSRF/CSP/XSS/SQLi/SSRF/路径遍历/命令白名单）。

    本层整合应用级安全检查，与现有 agent_security.py（Prompt Injection 防御）
    和 security_scanner.py（代码扫描）互补，不替代。
    """

    LAYER_NAME = "application"

    # 危险函数模式（用于运行时检测，非静态扫描）
    DANGEROUS_PATTERNS = [
        (r'\beval\s*\(', 'code_execution:eval'),
        (r'\bexec\s*\(', 'code_execution:exec'),
        (r'\bos\.system\s*\(', 'command_injection:os_system'),
        (r'\bsubprocess\.(call|Popen|run)\s*\([^)]*shell\s*=\s*True', 'command_injection:shell_true'),
        (r'\b__import__\s*\(', 'dynamic_import'),
        (r'\bpickle\.loads\s*\(', 'deserialization:pickle'),
    ]
    _COMPILED_DANGEROUS = [(re.compile(p), label) for p, label in DANGEROUS_PATTERNS]

    # XSS 模式
    XSS_PATTERNS = [
        (r'(?i)<\s*script[^>]*>', 'xss:script_tag'),
        (r'(?i)javascript\s*:', 'xss:javascript_uri'),
        (r'(?i)on\w+\s*=', 'xss:event_handler'),
    ]
    _COMPILED_XSS = [(re.compile(p), label) for p, label in XSS_PATTERNS]

    # SQL 注入模式（基础检测，真正防护应使用参数化查询）
    SQLI_PATTERNS = [
        (r"(?i)('|\"|;)\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)\b", 'sqli:stacked_query'),
        (r"(?i)\bUNION\s+SELECT\b", 'sqli:union_select'),
        (r"(?i)\bOR\s+1\s*=\s*1\b", 'sqli:tautology'),
        (r"(?i)--\s*$", 'sqli:comment_termination'),
    ]
    _COMPILED_SQLI = [(re.compile(p), label) for p, label in SQLI_PATTERNS]

    # 路径遍历模式
    PATH_TRAVERSAL_PATTERNS = [
        (r'\.\./', 'path_traversal:relative'),
        (r'\.\.\\', 'path_traversal:windows_relative'),
        (r'(?i)%2e%2e%2f', 'path_traversal:url_encoded'),
        (r'(?i)/etc/passwd', 'path_traversal:etc_passwd'),
        (r'(?i)c:\\windows', 'path_traversal:windows_system'),
    ]
    _COMPILED_PATH = [(re.compile(p), label) for p, label in PATH_TRAVERSAL_PATTERNS]

    # SSRF 模式（内网地址）
    SSRF_PATTERNS = [
        (r'(?i)https?://127\.', 'ssrf:loopback'),
        (r'(?i)https?://10\.', 'ssrf:private_10'),
        (r'(?i)https?://192\.168\.', 'ssrf:private_192'),
        (r'(?i)https?://172\.(1[6-9]|2\d|3[01])\.', 'ssrf:private_172'),
        (r'(?i)https?://localhost', 'ssrf:localhost'),
        (r'(?i)https?://169\.254\.', 'ssrf:link_local'),
    ]
    _COMPILED_SSRF = [(re.compile(p), label) for p, label in SSRF_PATTERNS]

    # 命令白名单（允许的外部命令）
    COMMAND_ALLOWLIST: Set[str] = {
        "git", "python", "python3", "pip", "pip3",
        "node", "npm", "npx",
        "echo", "ls", "dir", "cat", "type",
        "pytest", "flake8", "black", "mypy",
    }

    def __init__(self):
        self._csrf_tokens: Dict[str, str] = {}
        self._csrf_lock = threading.Lock()

    # ── 输入验证 ──

    def detect_xss(self, text: str) -> List[Dict[str, Any]]:
        """检测 XSS 模式。"""
        if not text or not isinstance(text, str):
            return []
        findings = []
        for pattern, label in self._COMPILED_XSS:
            for m in pattern.finditer(text):
                findings.append({"label": label, "match": m.group(0)[:80]})
        return findings

    def detect_sqli(self, text: str) -> List[Dict[str, Any]]:
        """检测 SQL 注入模式（基础，参数化查询才是根本防护）。"""
        if not text or not isinstance(text, str):
            return []
        findings = []
        for pattern, label in self._COMPILED_SQLI:
            for m in pattern.finditer(text):
                findings.append({"label": label, "match": m.group(0)[:80]})
        return findings

    def detect_path_traversal(self, path: str) -> List[Dict[str, Any]]:
        """检测路径遍历。"""
        if not path or not isinstance(path, str):
            return []
        findings = []
        for pattern, label in self._COMPILED_PATH:
            if pattern.search(path):
                findings.append({"label": label, "path": path[:100]})
        return findings

    def detect_ssrf(self, url: str) -> List[Dict[str, Any]]:
        """检测 SSRF（内网地址请求）。"""
        if not url or not isinstance(url, str):
            return []
        findings = []
        for pattern, label in self._COMPILED_SSRF:
            if pattern.search(url):
                findings.append({"label": label, "url": url[:100]})
        return findings

    def detect_dangerous_code(self, code: str) -> List[Dict[str, Any]]:
        """检测危险代码模式。"""
        if not code or not isinstance(code, str):
            return []
        findings = []
        for pattern, label in self._COMPILED_DANGEROUS:
            for m in pattern.finditer(code):
                findings.append({"label": label, "match": m.group(0)[:80]})
        return findings

    # ── 命令白名单 ──

    def is_command_allowed(self, command: str) -> Tuple[bool, str]:
        """检查命令是否在白名单内。

        Args:
            command: 命令名（如 "git", "rm"）

        Returns:
            (allowed, reason)
        """
        cmd = command.strip().lower()
        # 提取基础命令名（去除路径）
        base = os.path.basename(cmd).split()[0] if cmd else ""
        if base in self.COMMAND_ALLOWLIST:
            return True, f"命令 {base} 在白名单内"
        return False, f"命令 {base} 不在白名单内（白名单: {sorted(self.COMMAND_ALLOWLIST)}）"

    # ── CSRF ──

    def generate_csrf_token(self, session_id: str) -> str:
        """生成 CSRF 令牌。"""
        import secrets
        token = secrets.token_hex(32)
        with self._csrf_lock:
            self._csrf_tokens[session_id] = token
        return token

    def validate_csrf_token(self, session_id: str, token: str) -> bool:
        """校验 CSRF 令牌。"""
        with self._csrf_lock:
            expected = self._csrf_tokens.get(session_id)
            if expected and expected == token:
                return True
        return False

    # ── 统一验证 ──

    def validate_input(
        self,
        text: str,
        checks: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """对输入文本执行多维度安全检查。

        Args:
            text: 待检查文本
            checks: 要执行的检查集合（None 则全部）
                    可选: xss, sqli, path_traversal, ssrf, dangerous_code

        Returns:
            {"safe": bool, "findings": {...}, "blocked": bool}
        """
        if checks is None:
            checks = {"xss", "sqli", "path_traversal", "ssrf", "dangerous_code"}
        all_findings: Dict[str, List] = {}
        if "xss" in checks:
            all_findings["xss"] = self.detect_xss(text)
        if "sqli" in checks:
            all_findings["sqli"] = self.detect_sqli(text)
        if "path_traversal" in checks:
            all_findings["path_traversal"] = self.detect_path_traversal(text)
        if "ssrf" in checks:
            all_findings["ssrf"] = self.detect_ssrf(text)
        if "dangerous_code" in checks:
            all_findings["dangerous_code"] = self.detect_dangerous_code(text)

        total_findings = sum(len(v) for v in all_findings.values())
        # 高危检查（sqli/dangerous_code/path_traversal）命中则 blocked
        blocked = any(
            len(all_findings.get(k, [])) > 0
            for k in ("sqli", "dangerous_code", "path_traversal")
        )
        return {
            "safe": total_findings == 0,
            "blocked": blocked,
            "findings": all_findings,
            "total_findings": total_findings,
        }

    def validate(self, context: Optional[Dict[str, Any]] = None) -> LayerValidationResult:
        """应用层验证。"""
        findings: List[Dict[str, Any]] = []
        checks_total = 6
        checks_passed = 0

        # Check 1: XSS 检测模式已编译
        if self._COMPILED_XSS:
            checks_passed += 1
        else:
            findings.append({"check": "xss_patterns", "severity": "high", "message": "XSS 检测模式未加载"})

        # Check 2: SQLi 检测模式已编译
        if self._COMPILED_SQLI:
            checks_passed += 1
        else:
            findings.append({"check": "sqli_patterns", "severity": "high", "message": "SQLi 检测模式未加载"})

        # Check 3: 路径遍历检测模式已编译
        if self._COMPILED_PATH:
            checks_passed += 1
        else:
            findings.append({"check": "path_patterns", "severity": "high", "message": "路径遍历检测模式未加载"})

        # Check 4: SSRF 检测模式已编译
        if self._COMPILED_SSRF:
            checks_passed += 1
        else:
            findings.append({"check": "ssrf_patterns", "severity": "medium", "message": "SSRF 检测模式未加载"})

        # Check 5: 命令白名单非空
        if self.COMMAND_ALLOWLIST:
            checks_passed += 1
        else:
            findings.append({"check": "command_allowlist", "severity": "high", "message": "命令白名单为空"})

        # Check 6: 危险代码检测模式已编译
        if self._COMPILED_DANGEROUS:
            checks_passed += 1
        else:
            findings.append({"check": "dangerous_patterns", "severity": "high", "message": "危险代码检测模式未加载"})

        score = int(checks_passed / checks_total * 100) if checks_total else 0
        return LayerValidationResult(
            layer=self.LAYER_NAME,
            passed=checks_passed == checks_total,
            score=score,
            checks_total=checks_total,
            checks_passed=checks_passed,
            checks_failed=checks_total - checks_passed,
            findings=findings,
        )

    def health_check(self) -> Dict[str, Any]:
        """应用层健康检查。"""
        return {
            "layer": self.LAYER_NAME,
            "status": "healthy",
            "xss_patterns": len(self._COMPILED_XSS),
            "sqli_patterns": len(self._COMPILED_SQLI),
            "path_traversal_patterns": len(self._COMPILED_PATH),
            "ssrf_patterns": len(self._COMPILED_SSRF),
            "dangerous_code_patterns": len(self._COMPILED_DANGEROUS),
            "command_allowlist_size": len(self.COMMAND_ALLOWLIST),
            "active_csrf_sessions": len(self._csrf_tokens),
            "timestamp": datetime.now().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# L3: AIAgentLayer（AI Agent 层）
# ═══════════════════════════════════════════════════════════════

class AIAgentLayer:
    """AI Agent security adapter over the canonical SYSTEM security owners.

    Tool allowlisting and identity binding are Agent-layer context checks.
    Permission and Action Firewall decisions are delegated to
    :mod:`lumenis.system.security`.
    """

    LAYER_NAME = "ai_agent"

    def __init__(
        self,
        gate: Optional[PermissionGate] = None,
        tool_allowlist: Optional[Set[str]] = None,
    ):
        self.gate = gate or get_permission_gate()
        self.tool_allowlist: Set[str] = tool_allowlist or {
            "search_notes", "get_events", "generate_report",
            "query_database", "analyze_sentiment",
            "get_audit_log", "health_check",
        }
        self._identity_bindings: Dict[str, Set[OperationType]] = {}
        self._identity_lock = threading.Lock()

    def is_tool_allowed(self, tool_name: str) -> Tuple[bool, str]:
        if tool_name in self.tool_allowlist:
            return True, f"工具 {tool_name} 在白名单内"
        return False, f"工具 {tool_name} 不在白名单内"

    def register_tool(self, tool_name: str) -> None:
        self.tool_allowlist.add(tool_name)

    def unregister_tool(self, tool_name: str) -> None:
        self.tool_allowlist.discard(tool_name)

    def bind_identity(self, agent_id: str, operations: Set[OperationType]) -> None:
        with self._identity_lock:
            self._identity_bindings[agent_id] = set(operations)

    def unbind_identity(self, agent_id: str) -> None:
        with self._identity_lock:
            self._identity_bindings.pop(agent_id, None)

    def check_identity_binding(
        self, agent_id: str, operation: OperationType
    ) -> Tuple[bool, str]:
        with self._identity_lock:
            allowed_ops = self._identity_bindings.get(agent_id)
        if allowed_ops is None:
            return False, f"Agent {agent_id} 未绑定身份"
        if operation in allowed_ops:
            return True, f"Agent {agent_id} 允许操作 {operation.value}"
        return False, f"Agent {agent_id} 不允许操作 {operation.value}"

    @staticmethod
    def _agent_action(operation_type: OperationType):
        from lumenis.system.security import AgentAction
        if operation_type == OperationType.DATA_EXPORT:
            return AgentAction.EXPORT
        if operation_type in {OperationType.DB_WRITE, OperationType.FILE_WRITE, OperationType.DATA_IMPORT}:
            return AgentAction.WRITE
        if operation_type == OperationType.CONFIG_MODIFY:
            return AgentAction.COMMIT
        if operation_type == OperationType.RUNTIME_OPERATION:
            return AgentAction.DEPLOY
        if operation_type in {OperationType.DATA_DELETE, OperationType.AD_EXECUTE}:
            return AgentAction.PUSH
        return AgentAction.ANALYZE

    def check_action_firewall(self, action_name: str) -> Dict[str, Any]:
        """Compatibility-facing method backed only by canonical Action Firewall."""
        from lumenis.system.security import ActionRequest, AgentAction, validate_action
        req = ActionRequest(
            identity="security_boundary:audit",
            intent=f"audit tool action {action_name}",
            tool=action_name,
            parameters={},
            target="",
            scope="system",
            action=AgentAction.ANALYZE,
        )
        result = validate_action(req)
        return {
            "action": "allow" if result.allowed else "block",
            "reason": result.reason,
            "canonical": True,
            "checks": result.checks,
        }

    def check_ai_action(
        self,
        agent_id: str,
        tool_name: str,
        operation_type: OperationType,
        risk_level: Optional[RiskLevel] = None,
        resource: Optional[str] = None,
        operation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run identity/tool context checks then canonical Permission + Firewall."""
        checks: Dict[str, Any] = {}

        tool_ok, tool_reason = self.is_tool_allowed(tool_name)
        checks["tool_allowlist"] = {"allowed": tool_ok, "reason": tool_reason}
        if not tool_ok:
            return {
                "allowed": False, "blocked_at": "tool_allowlist",
                "reason": tool_reason, "permission_result": None, "checks": checks,
            }

        id_ok, id_reason = self.check_identity_binding(agent_id, operation_type)
        checks["identity_binding"] = {"allowed": id_ok, "reason": id_reason}
        if not id_ok:
            return {
                "allowed": False, "blocked_at": "identity_binding",
                "reason": id_reason, "permission_result": None, "checks": checks,
            }

        perm_result = self.gate.check(
            operation_type=operation_type,
            resource=resource,
            risk_level=risk_level,
            caller=f"ai_agent:{agent_id}",
            operation_id=operation_id,
        )
        checks["permission_gate"] = perm_result.to_dict()
        if not perm_result.allowed:
            return {
                "allowed": False, "blocked_at": "permission_gate",
                "reason": perm_result.reason,
                "permission_result": perm_result, "checks": checks,
            }

        from lumenis.system.security import ActionRequest, validate_action
        req = ActionRequest(
            identity=f"ai_agent:{agent_id}",
            intent=f"execute {tool_name}",
            tool=tool_name,
            parameters={},
            target=resource or "",
            scope="system",
            action=self._agent_action(operation_type),
        )
        firewall = validate_action(req, permission_result=perm_result)
        checks["action_firewall"] = firewall.to_dict()
        if not firewall.allowed:
            return {
                "allowed": False, "blocked_at": "action_firewall",
                "reason": firewall.reason,
                "permission_result": perm_result, "checks": checks,
            }

        return {
            "allowed": True, "blocked_at": None,
            "reason": "全部安全检查通过",
            "permission_result": perm_result, "checks": checks,
        }

    def validate(self, context: Optional[Dict[str, Any]] = None) -> LayerValidationResult:
        findings: List[Dict[str, Any]] = []
        checks_total = 5
        checks_passed = 0

        gate_health = self.gate.health_check()
        if gate_health["status"] == "healthy":
            checks_passed += 1
        else:
            findings.append({"check": "permission_gate", "severity": "critical", "message": "PermissionGate 不健康"})

        if self.tool_allowlist:
            checks_passed += 1
        else:
            findings.append({"check": "tool_allowlist", "severity": "high", "message": "工具白名单为空"})

        try:
            fw = self.check_action_firewall("delete_records")
            if fw.get("action") == "block" and fw.get("canonical") is True:
                checks_passed += 1
            else:
                findings.append({"check": "action_firewall", "severity": "high", "message": "canonical Action Firewall 未阻止危险动作"})
        except Exception as exc:
            findings.append({"check": "action_firewall", "severity": "critical", "message": str(exc)})

        if self.gate.fail_closed:
            checks_passed += 1
        else:
            findings.append({"check": "fail_closed", "severity": "medium", "message": "PermissionGate fail_closed=False"})

        if self.gate.require_human_approval(RiskLevel.HIGH):
            checks_passed += 1
        else:
            findings.append({"check": "human_approval_policy", "severity": "critical", "message": "高风险操作未要求人工审批"})

        score = int(checks_passed / checks_total * 100) if checks_total else 0
        return LayerValidationResult(
            layer=self.LAYER_NAME,
            passed=checks_passed == checks_total,
            score=score,
            checks_total=checks_total,
            checks_passed=checks_passed,
            checks_failed=checks_total - checks_passed,
            findings=findings,
        )

    def health_check(self) -> Dict[str, Any]:
        return {
            "layer": self.LAYER_NAME,
            "status": "healthy",
            "permission_gate": self.gate.health_check(),
            "tool_allowlist_size": len(self.tool_allowlist),
            "tool_allowlist": sorted(self.tool_allowlist),
            "action_firewall_owner": "lumenis.system.security.action_firewall",
            "identity_bindings": len(self._identity_bindings),
            "timestamp": datetime.now().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# L4: DataLayer（数据层）
# ═══════════════════════════════════════════════════════════════

class DataLayer:
    """数据层安全（敏感数据/密钥检测/凭证隔离/审计追踪）。

    与 security_scanner.py（静态代码扫描）互补：
      security_scanner.py 负责代码仓库的静态扫描，
      本层负责运行时数据的敏感信息检测和凭证隔离。
    """

    LAYER_NAME = "data"

    # 敏感信息模式（运行时检测）
    SENSITIVE_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{16,})', 'credential:api_key'),
        (r'(?i)(secret|access[_-]?token|refresh[_-]?token)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{16,})', 'credential:token'),
        (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?(\S{6,})', 'credential:password'),
        (r'(?i)(private[_-]?key)\s*[:=]\s*["\']?([A-Za-z0-9+/=\s]{16,})', 'credential:private_key'),
        (r'\bAKIA[0-9A-Z]{16}\b', 'credential:aws_access_key'),
        (r'\bsk-[A-Za-z0-9]{20,}\b', 'credential:openai_key'),
        (r'\bark-[0-9a-f]{8,}-[0-9a-f]{4,}\b', 'credential:volcano_ark_key'),
        (r'\b[0-9a-f]{32}\.[0-9a-zA-Z]{20,}\b', 'credential:zhipu_key'),
        (r'\bghp_[A-Za-z0-9]{20,}\b', 'credential:github_token'),
        (r'web_session\s*=\s*[A-Za-z0-9]+', 'credential:session_cookie'),
        (r'(?i)(cookie|session[_-]?id)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{16,})', 'credential:cookie_session'),
    ]
    _COMPILED_SENSITIVE = [(re.compile(p), label) for p, label in SENSITIVE_PATTERNS]

    # PII 模式
    PII_PATTERNS = [
        (r'\b1[3-9]\d{9}\b', 'pii:phone_cn'),
        (r'\b\d{17}[\dXx]\b', 'pii:id_card_cn'),
        (r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b', 'pii:email'),
        (r'(?i)(name|姓名)\s*[:=]\s*["\']?([\u4e00-\u9fa5]{2,4})', 'pii:name'),
    ]
    _COMPILED_PII = [(re.compile(p), label) for p, label in PII_PATTERNS]

    # 凭证隔离目录（这些目录/文件不应被导出或日志记录）
    CREDENTIAL_ISOLATION_PATHS = [
        ".env", ".env.local", ".env.production",
        "config/secrets.json", "config/credentials.json",
        "data/cookies.json", "data/session.json",
    ]

    def __init__(self, audit_log_callback: Optional[Callable] = None):
        self._audit_callback = audit_log_callback
        # 敏感数据检测计数
        self._detection_stats: Dict[str, int] = {}
        self._stats_lock = threading.Lock()

    # ── 敏感数据检测 ──

    def detect_sensitive_data(self, text: str) -> List[Dict[str, Any]]:
        """检测文本中的敏感信息（密钥/Token/密码等）。"""
        if not text or not isinstance(text, str):
            return []
        findings = []
        for pattern, label in self._COMPILED_SENSITIVE:
            for m in pattern.finditer(text):
                findings.append({
                    "label": label,
                    "match_preview": m.group(0)[:20] + "...[REDACTED]",
                    "position": m.start(),
                })
                with self._stats_lock:
                    self._detection_stats[label] = self._detection_stats.get(label, 0) + 1
        return findings

    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """检测 PII（个人身份信息）。"""
        if not text or not isinstance(text, str):
            return []
        findings = []
        for pattern, label in self._COMPILED_PII:
            for m in pattern.finditer(text):
                findings.append({
                    "label": label,
                    "match_preview": m.group(0)[:10] + "...[REDACTED]",
                })
        return findings

    def redact_sensitive_data(self, text: str) -> str:
        """脱敏：替换文本中的敏感信息。"""
        if not text or not isinstance(text, str):
            return text or ""
        result = text
        for pattern, label in self._COMPILED_SENSITIVE:
            result = pattern.sub(f"[REDACTED:{label}]", result)
        return result

    # ── 凭证隔离 ──

    def is_credential_path(self, path: str) -> bool:
        """检查路径是否属于凭证隔离范围。"""
        normalized = path.replace("\\", "/").lower()
        for isolated in self.CREDENTIAL_ISOLATION_PATHS:
            if normalized.endswith(isolated.lower()) or isolated.lower() in normalized:
                return True
        return False

    def check_export_safety(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """检查导出文件的安全性。

        Returns:
            {"safe": bool, "blocked": bool, "reasons": [...]}
        """
        reasons = []
        blocked = False

        # 检查路径是否为凭证文件
        if self.is_credential_path(file_path):
            reasons.append(f"文件路径属于凭证隔离范围: {file_path}")
            blocked = True

        # 检查内容是否含敏感信息
        if content:
            sensitive = self.detect_sensitive_data(content)
            if sensitive:
                reasons.append(f"内容包含 {len(sensitive)} 处敏感信息: {[f['label'] for f in sensitive]}")
                blocked = True

        return {
            "safe": not reasons,
            "blocked": blocked,
            "reasons": reasons,
        }

    # ── 审计追踪 ──

    def log_data_access(
        self,
        action: str,
        resource: str,
        caller: str,
        sensitive: bool = False,
    ) -> str:
        """记录数据访问审计。

        Returns:
            audit_id
        """
        import hashlib
        import uuid
        audit_id = "data_aud_" + hashlib.sha256(
            f"{uuid.uuid4().hex}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        entry = {
            "audit_id": audit_id,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "resource": resource,
            "caller": caller,
            "sensitive": sensitive,
        }
        if self._audit_callback:
            try:
                self._audit_callback(entry)
            except Exception as e:
                logger.warning(f"[DataLayer] 审计回调失败: {e}")
        logger.info(f"[DataLayer] 数据访问审计: {action} on {resource} by {caller}")
        return audit_id

    def get_detection_stats(self) -> Dict[str, int]:
        """获取敏感数据检测统计。"""
        with self._stats_lock:
            return dict(self._detection_stats)

    # ── 统一验证 ──

    def validate(self, context: Optional[Dict[str, Any]] = None) -> LayerValidationResult:
        """数据层验证。"""
        findings: List[Dict[str, Any]] = []
        checks_total = 4
        checks_passed = 0

        # Check 1: 敏感信息检测模式已编译
        if self._COMPILED_SENSITIVE:
            checks_passed += 1
        else:
            findings.append({"check": "sensitive_patterns", "severity": "high", "message": "敏感信息检测模式未加载"})

        # Check 2: PII 检测模式已编译
        if self._COMPILED_PII:
            checks_passed += 1
        else:
            findings.append({"check": "pii_patterns", "severity": "medium", "message": "PII 检测模式未加载"})

        # Check 3: 凭证隔离路径已配置
        if self.CREDENTIAL_ISOLATION_PATHS:
            checks_passed += 1
        else:
            findings.append({"check": "credential_isolation", "severity": "high", "message": "凭证隔离路径未配置"})

        # Check 4: 脱敏功能可用（redact 不抛异常）
        try:
            test_result = self.redact_sensitive_data("api_key=PLACEHOLDER_REDACTION_TEST_0123456789")
            if "REDACTED" in test_result:
                checks_passed += 1
            else:
                findings.append({"check": "redaction", "severity": "high", "message": "脱敏功能未生效"})
        except Exception as e:
            findings.append({"check": "redaction", "severity": "critical", "message": f"脱敏功能异常: {e}"})

        score = int(checks_passed / checks_total * 100) if checks_total else 0
        return LayerValidationResult(
            layer=self.LAYER_NAME,
            passed=checks_passed == checks_total,
            score=score,
            checks_total=checks_total,
            checks_passed=checks_passed,
            checks_failed=checks_total - checks_passed,
            findings=findings,
        )

    def health_check(self) -> Dict[str, Any]:
        """数据层健康检查。"""
        return {
            "layer": self.LAYER_NAME,
            "status": "healthy",
            "sensitive_patterns": len(self._COMPILED_SENSITIVE),
            "pii_patterns": len(self._COMPILED_PII),
            "credential_isolation_paths": len(self.CREDENTIAL_ISOLATION_PATHS),
            "detection_stats": self.get_detection_stats(),
            "audit_callback_configured": self._audit_callback is not None,
            "timestamp": datetime.now().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# 统一编排：SecurityBoundary
# ═══════════════════════════════════════════════════════════════

class SecurityBoundary:
    """四层安全边界统一编排器。

    整合 EdgeLayer / ApplicationLayer / AIAgentLayer / DataLayer，
    提供统一 validate() 和 health_check() 入口。

    不替代现有安全模块，是统一编排和状态汇总入口。
    """

    def __init__(
        self,
        gate: Optional[PermissionGate] = None,
        edge: Optional[EdgeLayer] = None,
        application: Optional[ApplicationLayer] = None,
        ai_agent: Optional[AIAgentLayer] = None,
        data: Optional[DataLayer] = None,
    ):
        self.gate = gate or get_permission_gate()
        self.edge = edge or EdgeLayer()
        self.application = application or ApplicationLayer()
        self.ai_agent = ai_agent or AIAgentLayer(gate=self.gate)
        self.data = data or DataLayer()

    def validate(self, context: Optional[Dict[str, Any]] = None) -> BoundaryValidationResult:
        """执行全四层安全边界验证。"""
        layers = {
            "edge": self.edge.validate(context),
            "application": self.application.validate(context),
            "ai_agent": self.ai_agent.validate(context),
            "data": self.data.validate(context),
        }
        overall_passed = all(l.passed for l in layers.values())
        total_score = sum(l.score for l in layers.values())
        overall_score = int(total_score / len(layers)) if layers else 0
        return BoundaryValidationResult(
            overall_passed=overall_passed,
            overall_score=overall_score,
            layers=layers,
        )

    def health_check(self) -> Dict[str, Any]:
        """全四层健康检查。"""
        return {
            "status": "healthy",
            "permission_gate": self.gate.health_check(),
            "layers": {
                "edge": self.edge.health_check(),
                "application": self.application.health_check(),
                "ai_agent": self.ai_agent.health_check(),
                "data": self.data.health_check(),
            },
            "timestamp": datetime.now().isoformat(),
        }

    def get_status(self) -> Dict[str, Any]:
        """获取完整安全边界状态。"""
        return {
            "health": self.health_check(),
            "validation": self.validate().to_dict(),
            "permission_gate_status": self.gate.get_status(),
        }


# ═══════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════

_default_boundary: Optional[SecurityBoundary] = None
_boundary_lock = threading.Lock()


def get_security_boundary() -> SecurityBoundary:
    """获取全局 SecurityBoundary 单例。"""
    global _default_boundary
    if _default_boundary is None:
        with _boundary_lock:
            if _default_boundary is None:
                _default_boundary = SecurityBoundary()
    return _default_boundary


def reset_security_boundary() -> None:
    """重置全局单例（测试用）。"""
    global _default_boundary
    with _boundary_lock:
        _default_boundary = None


# ═══════════════════════════════════════════════════════════════
# 导出
# ═══════════════════════════════════════════════════════════════

__all__ = [
    "LayerValidationResult",
    "BoundaryValidationResult",
    "EdgeLayer",
    "ApplicationLayer",
    "AIAgentLayer",
    "DataLayer",
    "SecurityBoundary",
    "get_security_boundary",
    "reset_security_boundary",
]
