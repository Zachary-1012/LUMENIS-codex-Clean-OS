# -*- coding: utf-8 -*-
"""[Legacy] Zachary OS AI · Agent Security Guard（AI Agent 安全防护层 · Legacy 保留）

⚠️ Legacy 模块：Phase 3 后，全局权限控制由 lumenis.system.security.PermissionGate 和 security_boundary.py（AIAgentLayer）统一编排。本模块保留 Prompt Injection 五层防御（输入净化/指令检测/参数校验/输出过滤/蜜罐），与全局 Gate 互补，不替代、不删除。

Zachary OS AI · Agent Security Guard（AI Agent 安全防护层）

Contract：OSAI 研究侧 → ZBC 生产侧。
基于 2025-2026 最新 Prompt Injection 研究（分层防御流水线、ToolLeak 攻击、蜜罐动作）实现。

核心原则（来自 Swept AI / Anthropic / OpenAI 安全研究共识）：
  1. 安全边界写进代码，不写进提示词。提示词是建议，代码是法律。
  2. 确定性过滤优先于模型判断：不依赖 AI 自己识别注入，用硬编码规则拦截。
  3. 最小权限：AI Agent 只能调用白名单工具，不能直接访问 cookie/密钥/文件系统。
  4. 分层防御：输入净化 → 指令检测 → 参数校验 → 输出过滤 → 蜜罐诱捕，多层叠加减少盲区。

防御层：
  L1 输入净化 (sanitize_input)      — 对外部输入（网页文本/用户输入）去除疑似注入指令
  L2 指令检测 (is_instruction_attempt) — 检测 "ignore previous instructions" 等注入模式
  L3 工具参数校验 (validate_tool_call) — 硬编码校验 AI 调用的工具参数，防 ToolLeak
  L4 输出过滤 (filter_output)          — 过滤 AI 输出中的敏感信息（系统提示词/cookie/密钥）
  L5 蜜罐动作 (HONEYPOT_ACTIONS)       — 定义诱饵工具，被调用即告警（高级功能，预留接口）

不做：
  - 不依赖模型自身判断是否被注入（不可靠）
  - 不在提示词里写"不要被注入"（无效，攻击者会覆盖）
  - 不做完整的沙箱隔离（需要操作系统级支持，超出本模块范围）
"""
from __future__ import annotations
import re
from typing import Any

# ── L2: 指令注入检测模式（基于 OWASP LLM Top 10 + 2025-2026 研究） ──
# 这些模式匹配常见的 Prompt Injection 攻击向量
INJECTION_PATTERNS = [
    # 直接指令覆盖
    (r'(?i)\bignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|commands?)\b', 'direct_override'),
    (r'(?i)\bdisregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)\b', 'direct_override'),
    (r'(?i)\bforget\s+(everything|all|your\s+instructions?|your\s+rules?)\b', 'direct_override'),
    # 身份冒充
    (r'(?i)\byou\s+are\s+now\b', 'identity_hijack'),
    (r'(?i)\bfrom\s+now\s+on\s+you\s+are\b', 'identity_hijack'),
    (r'(?i)\bact\s+as\s+(if\s+you\s+are\s+)?(a\s+)?(system|admin|developer|root)\b', 'privilege_escalation'),
    # 系统提示词窃取（ToolLeak 攻击向量）
    (r'(?i)\b(reveal|show|display|print|output|repeat|echo|recite|summarize|extract)\s+(your\s+)?(system\s+)?(prompt|instructions?|rules?|initial\s+message)\b', 'prompt_extraction'),
    (r'(?i)\bwhat\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions?|rules?)\b', 'prompt_extraction'),
    # 工具调用注入
    (r'(?i)\b(call|invoke|execute|run)\s+(the\s+)?(tool|function|command|api)\b', 'tool_injection'),
    # 数据外泄
    (r'(?i)\b(send|email|post|upload|transfer|exfiltrate)\s+(the\s+)?(data|content|information|cookies?|tokens?|secrets?|keys?)\b', 'data_exfiltration'),
    # 代码执行
    (r'(?i)\b(eval|exec|system|os\.system|subprocess|shell|bash|cmd)\s*\(', 'code_execution'),
    # 越权访问
    (r'(?i)\b(access|read|write|delete|modify)\s+(the\s+)?(cookie|token|secret|key|password|credential|env|environment)\b', 'unauthorized_access'),
]

# 编译正则
_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), label) for p, label in INJECTION_PATTERNS]

# ── L4: 敏感信息过滤模式 ──
SENSITIVE_PATTERNS = [
    (r'(?i)(system\s*prompt|initial\s*instruction|developer\s*message)\s*[:=]\s*.+', '[REDACTED: system prompt]'),
    (r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|refresh[_-]?token)\s*[:=]\s*[A-Za-z0-9_\-]{8,}', '[REDACTED: credential]'),
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*\S+', '[REDACTED: password]'),
    (r'web_session\s*=\s*[A-Za-z0-9]+', '[REDACTED: session cookie]'),
    (r'id_token\s*=\s*[A-Za-z0-9+/=]+', '[REDACTED: id token]'),
    (r'(?i)sk-[A-Za-z0-9]{20,}', '[REDACTED: API key]'),
    (r'(?i)ghp_[A-Za-z0-9]{20,}', '[REDACTED: GitHub token]'),
]
_COMPILED_SENSITIVE = [(re.compile(p), repl) for p, repl in SENSITIVE_PATTERNS]

# ── L3: 工具白名单（AI Agent 允许调用的工具） ──
# 只有在白名单内的工具才能被 AI 调用，且参数有硬编码校验
ALLOWED_TOOLS = {
    "search_notes": {
        "description": "搜索舆情笔记",
        "required_params": ["query"],
        "max_query_length": 500,
        "allowed_params": {"query", "limit", "offset", "date_from", "date_to"},
    },
    "get_events": {
        "description": "获取舆情事件",
        "required_params": [],
        "allowed_params": {"limit", "offset", "severity", "status"},
    },
    "generate_report": {
        "description": "生成舆情报告",
        "required_params": ["report_type"],
        "allowed_params": {"report_type", "date_from", "date_to", "format"},
    },
    "query_database": {
        "description": "查询数据库（只读）",
        "required_params": ["sql"],
        "max_sql_length": 2000,
        "allowed_params": {"sql", "params"},
        "read_only": True,  # 只允许 SELECT
    },
    "analyze_sentiment": {
        "description": "分析情感倾向",
        "required_params": ["text"],
        "max_text_length": 10000,
        "allowed_params": {"text", "model"},
    },
}

# ── L5: 蜜罐动作（预留接口） ──
# 定义诱饵工具，如果 AI 调用这些工具，说明可能被注入，立即告警
HONEYPOT_ACTIONS = {
    "reveal_system_prompt": {
        "description": "蜜罐：诱饵工具，被调用即告警",
        "alert_level": "CRITICAL",
        "action": "log_and_block",
    },
    "export_cookies": {
        "description": "蜜罐：诱饵工具，被调用即告警",
        "alert_level": "CRITICAL",
        "action": "log_and_block",
    },
    "execute_shell": {
        "description": "蜜罐：诱饵工具，被调用即告警",
        "alert_level": "CRITICAL",
        "action": "log_and_block",
    },
}


def is_instruction_attempt(text: str) -> dict[str, Any]:
    """L2: 检测文本是否包含 Prompt Injection 指令。

    返回:
      {
        "is_injection": bool,
        "matches": [{"pattern": str, "label": str, "matched_text": str}, ...],
        "risk_level": "low" | "medium" | "high" | "critical"
      }
    """
    if not text or not isinstance(text, str):
        return {"is_injection": False, "matches": [], "risk_level": "low"}

    matches = []
    for pattern, label in _COMPILED_PATTERNS:
        for m in pattern.finditer(text):
            matches.append({
                "pattern": pattern.pattern[:60],
                "label": label,
                "matched_text": m.group(0)[:100],
            })

    if not matches:
        return {"is_injection": False, "matches": [], "risk_level": "low"}

    # 风险分级
    labels = {m["label"] for m in matches}
    if "prompt_extraction" in labels or "code_execution" in labels or "unauthorized_access" in labels:
        risk = "critical"
    elif "identity_hijack" in labels or "privilege_escalation" in labels or "data_exfiltration" in labels:
        risk = "high"
    elif "direct_override" in labels or "tool_injection" in labels:
        risk = "medium"
    else:
        risk = "low"

    return {"is_injection": True, "matches": matches, "risk_level": risk}


def sanitize_input(text: str, mode: str = "filter") -> str:
    """L1: 输入净化，去除疑似注入指令。

    Args:
      text: 待净化的文本
      mode: "filter" = 移除匹配行；"mask" = 用 [REDACTED] 替换；"tag" = 保留但标记

    Returns:
      净化后的文本
    """
    if not text or not isinstance(text, str):
        return text or ""

    result = text
    for pattern, label in _COMPILED_PATTERNS:
        if mode == "filter":
            # 移除包含注入指令的整行
            lines = result.split("\n")
            result = "\n".join(line for line in lines if not pattern.search(line))
        elif mode == "mask":
            result = pattern.sub("[REDACTED: injection attempt]", result)
        elif mode == "tag":
            result = pattern.sub(lambda m: f"[INJECTION_DETECTED:{label}] {m.group(0)} [/INJECTION_DETECTED]", result)

    return result


def validate_tool_call(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """L3: 硬编码校验 AI 调用的工具参数，防止 ToolLeak 攻击和越权调用。

    ToolLeak 攻击：攻击者把参数名设成 "note": "system prompt"，模型把系统提示词当表单字段填入。
    防御：硬编码校验参数名和值，不允许未知参数，不允许参数值包含系统提示词/cookie/密钥。

    Returns:
      {
        "allowed": bool,
        "reason": str,
        "sanitized_params": dict,
        "risk_level": str
      }
    """
    # 1. 检查是否是蜜罐工具
    if tool_name in HONEYPOT_ACTIONS:
        hp = HONEYPOT_ACTIONS[tool_name]
        return {
            "allowed": False,
            "reason": f"HONEYPOT TRIGGERED: {tool_name} is a decoy tool. Possible prompt injection.",
            "sanitized_params": {},
            "risk_level": hp["alert_level"],
            "honeypot": True,
        }

    # 2. 检查工具是否在白名单
    if tool_name not in ALLOWED_TOOLS:
        return {
            "allowed": False,
            "reason": f"Tool '{tool_name}' not in allowed tools whitelist",
            "sanitized_params": {},
            "risk_level": "high",
        }

    tool_def = ALLOWED_TOOLS[tool_name]
    sanitized = {}
    issues = []

    # 3. 校验必填参数
    for req in tool_def.get("required_params", []):
        if req not in params or params[req] is None or params[req] == "":
            issues.append(f"Missing required parameter: {req}")

    # 4. 校验参数名（只允许白名单参数，防 ToolLeak）
    allowed_params = tool_def.get("allowed_params", set())
    for key, value in params.items():
        if key not in allowed_params:
            issues.append(f"Unknown parameter '{key}' not in allowed params for tool '{tool_name}'")
            continue

        # 5. 校验参数值类型
        if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
            issues.append(f"Parameter '{key}' has invalid type: {type(value).__name__}")
            continue

        # 6. 校验参数值长度
        if isinstance(value, str):
            max_len = tool_def.get(f"max_{key}_length", tool_def.get("max_query_length", 5000))
            if len(value) > max_len:
                issues.append(f"Parameter '{key}' exceeds max length {max_len} (got {len(value)})")
                continue

            # 7. 校验参数值不包含注入指令（防 ToolLeak：参数值里藏系统提示词）
            injection_check = is_instruction_attempt(value)
            if injection_check["is_injection"]:
                issues.append(f"Parameter '{key}' contains possible injection: {injection_check['matches'][0]['label']}")
                # 净化参数值
                value = sanitize_input(value, mode="mask")

            # 8. 校验参数值不包含敏感信息
            for sp, repl in _COMPILED_SENSITIVE:
                if sp.search(value):
                    issues.append(f"Parameter '{key}' contains sensitive info, redacted")
                    value = sp.sub(repl, value)

        sanitized[key] = value

    # 9. 只读工具校验（query_database 只允许 SELECT）
    if tool_def.get("read_only") and "sql" in sanitized:
        sql = sanitized["sql"].strip().upper()
        if not sql.startswith("SELECT") and not sql.startswith("WITH"):
            issues.append(f"Read-only tool '{tool_name}' only allows SELECT/WITH queries")
            sanitized["sql"] = ""

    if issues:
        return {
            "allowed": False,
            "reason": "; ".join(issues[:5]),
            "sanitized_params": sanitized,
            "risk_level": "high" if any("Unknown parameter" in i or "injection" in i.lower() for i in issues) else "medium",
        }

    return {
        "allowed": True,
        "reason": "OK",
        "sanitized_params": sanitized,
        "risk_level": "low",
    }


def filter_output(text: str) -> str:
    """L4: 过滤 AI 输出中的敏感信息（系统提示词/cookie/密钥/Token）。

    确定性过滤，不依赖模型判断。
    """
    if not text or not isinstance(text, str):
        return text or ""

    result = text
    for pattern, repl in _COMPILED_SENSITIVE:
        result = pattern.sub(repl, result)
    return result


def security_audit(text: str, tool_name: str = None, params: dict = None) -> dict[str, Any]:
    """综合安全审计：对输入+工具调用+输出进行全链路检查。

    Returns:
      {
        "input_check": {...},
        "tool_check": {...} or None,
        "output_filtered": str,
        "overall_risk": "low" | "medium" | "high" | "critical",
        "blocked": bool,
        "recommendations": [str, ...]
      }
    """
    input_check = is_instruction_attempt(text)
    tool_check = validate_tool_call(tool_name, params) if tool_name else None

    output_filtered = filter_output(text)

    risks = [input_check["risk_level"]]
    if tool_check:
        risks.append(tool_check["risk_level"])

    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    overall_risk = max(risks, key=lambda r: risk_order.get(r, 0))

    blocked = (
        input_check["risk_level"] == "critical"
        or (tool_check and not tool_check["allowed"])
    )

    recommendations = []
    if input_check["is_injection"]:
        recommendations.append(f"Input contains {len(input_check['matches'])} injection pattern(s): {[m['label'] for m in input_check['matches']]}")
    if tool_check and not tool_check["allowed"]:
        recommendations.append(f"Tool call blocked: {tool_check['reason']}")
    if output_filtered != text:
        recommendations.append("Output was filtered to remove sensitive info")

    return {
        "input_check": input_check,
        "tool_check": tool_check,
        "output_filtered": output_filtered,
        "overall_risk": overall_risk,
        "blocked": blocked,
        "recommendations": recommendations,
    }


# ── 便捷常量导出 ──
__all__ = [
    "is_instruction_attempt",
    "sanitize_input",
    "validate_tool_call",
    "filter_output",
    "security_audit",
    "ALLOWED_TOOLS",
    "HONEYPOT_ACTIONS",
    "INJECTION_PATTERNS",
]

# Phase 13: module status (LEGACY - preserved, not deleted)
_MODULE_STATUS = "LEGACY"
_LEGACY_REASON = "Phase 3+ global permission controlled by permission_gate.py + security_boundary.py; this module retains prompt-injection 5-layer defense as complementary layer"
_PHASE13_COMPAT = "agent_boundary.ActionFirewall supersedes tool whitelist for new code; ALLOWED_TOOLS preserved for backward compat"

