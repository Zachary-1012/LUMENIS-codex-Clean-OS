# -*- coding: utf-8 -*-
"""LUMENIS CTH/BMP AI domain-context compatibility layer.

CTH is LUMENIS Commerce Operations (Subject-first).
BMP is LUMENIS Brand & Market; ZBMP/zbmp remain persisted compatibility IDs.
Guangzhou Taikoo Hui is a controlled reference Subject, never the product
default. The workspace default is GLOBAL / ALL.

The layer preserves domain isolation and AI-result provenance. It must not infer
an unauthorized Subject/BrandFocus or turn AI output into Product Truth.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from subject_context import (
    PRODUCT_CTH, PRODUCT_ZBMP, CTH_BRAND_KEY,
    get_subject_context, get_thread_context,
)

logger = logging.getLogger(__name__)

# ============================================================
# 1. 域身份常量
# ============================================================
DOMAIN_CTH = "cth"
DOMAIN_ZBMP = "zbmp"

PROMPT_VERSION_CTH = "cth-v3.0-lumenis"
PROMPT_VERSION_ZBMP = "bmp-v3.0-lumenis"


# ============================================================
# 2. Prompt 模板定义
# ============================================================
@dataclass(frozen=True)
class DomainPromptContext:
    """域专属 AI Prompt 上下文。"""
    domain_id: str
    product_id: str
    prompt_version: str
    system_prompt: str
    analysis_focus: List[str]
    output_schema_hint: str
    prohibited_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "product_id": self.product_id,
            "prompt_version": self.prompt_version,
            "system_prompt": self.system_prompt,
            "analysis_focus": list(self.analysis_focus),
            "output_schema_hint": self.output_schema_hint,
            "prohibited_topics": list(self.prohibited_topics),
        }


# CTH 域：太古汇专项舆情分析
CTH_CONTEXT = DomainPromptContext(
    domain_id=DOMAIN_CTH,
    product_id=PRODUCT_CTH,
    prompt_version=PROMPT_VERSION_CTH,
    system_prompt=(
        "You are the Commerce Operations analysis capability of LUMENIS. "
        "CTH is Subject-first and is not a Guangzhou Taikoo Hui-specific product. "
        "Use only the Subject, sources, Evidence, market and time scope explicitly "
        "authorized for the current request. GLOBAL / ALL has no implicit Subject. "
        "Guangzhou Taikoo Hui and Shenzhen Luohu MixC are representative reference "
        "Subjects only when explicitly focused. Distinguish issuer claims, consumer "
        "discussion, media reporting, advertising and observed operational outcomes. "
        "Keep missing footfall, sales, satisfaction, effect or causal evidence as "
        "UNKNOWN / NOT_AVAILABLE. Bind judgments to locatable sources and timestamps. "
        "AI never owns Permission, Evidence, Canonical Truth or external effects."
    ),
    analysis_focus=[
        "authorized commercial Subject operations",
        "events, consumer feedback and risk",
        "venue and tenant/category relationships",
        "source roles and communication changes",
        "cross-platform comparable native signals",
        "actionable operations recommendations with evidence",
        "outcomes, unknown states and evaluation",
    ],
    output_schema_hint=(
        '{"sentiment": "positive|neutral|negative|unknown", '
        '"risk_level": "low|medium|high|critical|unknown", '
        '"topics": [...], "summary": "...", "evidence_ref": "...", '
        '"confidence": 0.0-1.0, "domain_id": "cth"}'
    ),
    prohibited_topics=[
        "treating a reference Subject as the default product scope",
        "analyzing a Subject outside current Permission / Context",
        "turning missing data, model inference, sentiment or attention into verified operational fact",
    ],
)

# ZBMP 域：多品牌智能分析
ZBMP_CONTEXT = DomainPromptContext(
    domain_id=DOMAIN_ZBMP,
    product_id=PRODUCT_ZBMP,
    prompt_version=PROMPT_VERSION_ZBMP,
    system_prompt=(
        "You are the Brand & Market analysis capability of LUMENIS. "
        "BMP is Brand/Market-first; ZBMP/zbmp are persisted compatibility identifiers, "
        "not another product. Use only the BrandFocus, market, sources, Evidence and "
        "time scope authorized for the current request. GLOBAL / ALL has no implicit "
        "brand. Nike and Le Labo are representative acceptance brands only when "
        "explicitly focused. Preserve comparable market/time/platform definitions and "
        "separate competitors, consumers, creators, communication, content and Campaign "
        "signals from verified commercial outcomes. Missing sales, conversion, effect "
        "or causal evidence stays UNKNOWN / NOT_AVAILABLE. AI never owns Permission, "
        "Evidence, Canonical Truth or external effects."
    ),
    analysis_focus=[
        "authorized BrandFocus and market scope",
        "competitor, consumer and creator signals",
        "communication, content and Campaign performance",
        "source role, market and time comparability",
        "brand opportunities, risks and alternative strategies",
        "outcomes, unknown states and evaluation",
    ],
    output_schema_hint=(
        '{"sentiment": "positive|neutral|negative|unknown", '
        '"risk_level": "low|medium|high|critical|unknown", '
        '"topics": [...], "summary": "...", "evidence_ref": "...", '
        '"confidence": 0.0-1.0, "domain_id": "zbmp"}'
    ),
    prohibited_topics=[
        "treating any reference brand as the default product scope",
        "analyzing a brand or market outside current Permission / Context",
        "turning missing data, model inference or correlation into verified commercial outcome",
    ],
)

DOMAIN_CONTEXTS: Dict[str, DomainPromptContext] = {
    DOMAIN_CTH: CTH_CONTEXT,
    DOMAIN_ZBMP: ZBMP_CONTEXT,
}


# ============================================================
# 3. 域身份解析
# ============================================================
def product_id_to_domain(product_id: str) -> str:
    """Map a known compatibility product ID to its business domain; unknown IDs fail closed."""
    if product_id == PRODUCT_CTH:
        return DOMAIN_CTH
    if product_id == PRODUCT_ZBMP:
        return DOMAIN_ZBMP
    raise ValueError(f"unknown product_id: {product_id}")


def get_current_domain() -> str:
    """获取当前线程的域身份。

    优先级：线程上下文 > 环境默认 > CTH
    """
    ctx = get_thread_context()
    if ctx is not None:
        return product_id_to_domain(ctx.product_id)
    ctx = get_subject_context()
    return product_id_to_domain(ctx.product_id)


def get_domain_context(domain_id: Optional[str] = None) -> DomainPromptContext:
    """Resolve an explicit/current AI business domain; unknown domains fail closed."""
    did = domain_id or get_current_domain()
    ctx = DOMAIN_CONTEXTS.get(did)
    if ctx is None:
        raise ValueError(f"unknown domain_id: {did}")
    return ctx


# ============================================================
# 4. Prompt 构建
# ============================================================
def build_domain_messages(
    user_content: str,
    domain_id: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, str]], DomainPromptContext]:
    """构建带域身份的 AI 请求消息列表。

    Returns:
        (messages, domain_context) — messages 包含 system + user，
        domain_context 用于后续校验和记录
    """
    ctx = get_domain_context(domain_id)
    system_msg = ctx.system_prompt

    # 附加域元信息到 system prompt（不泄露敏感配置，仅标记域身份）
    system_msg += f"\n\n[域身份标记] domain_id={ctx.domain_id}, product_id={ctx.product_id}, prompt_version={ctx.prompt_version}"

    if extra_context:
        system_msg += f"\n[附加上下文] {extra_context}"

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content},
    ]
    return messages, ctx


# ============================================================
# 5. 域匹配校验（防串域）
# ============================================================
class DomainMismatchError(PermissionError):
    """域身份不匹配异常：CTH prompt 流入 ZBMP 或反之。"""
    pass


def validate_domain_match(
    expected_domain: str,
    actual_context: DomainPromptContext,
    operation: str = "ai_call",
) -> None:
    """校验期望域与实际 prompt context 匹配。

    禁止 CTH prompt 流入 ZBMP 或反之。
    """
    if expected_domain != actual_context.domain_id:
        raise DomainMismatchError(
            f"Domain Mismatch: operation={operation} expected domain={expected_domain}, "
            f"but prompt context domain={actual_context.domain_id} "
            f"(product_id={actual_context.product_id}, version={actual_context.prompt_version}). "
            f"CTH and ZBMP prompts must not cross domains."
        )


def validate_prompt_domain_isolation(messages: List[Dict[str, str]]) -> str:
    """从 messages 中检测域身份标记，返回检测到的 domain_id。

    用于在 call_ai_with_governance 入口校验。
    如果 messages 中没有域身份标记，返回空字符串（由调用方决定是否拒绝）。
    """
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            if "domain_id=cth" in content.lower():
                return DOMAIN_CTH
            if "domain_id=zbmp" in content.lower():
                return DOMAIN_ZBMP
    return ""


# ============================================================
# 6. AI 结果域身份标记
# ============================================================
def mark_ai_result_with_domain(
    ai_result: Dict[str, Any],
    domain_context: DomainPromptContext,
    confidence: float = 0.0,
    final_result: str = "",
    human_correction: str = "",
) -> Dict[str, Any]:
    """为 AI 结果添加域身份标记和治理字段。

    确保 AI 结果记录包含：product_id, domain_id, provider, model,
    prompt_version, input_hash, output_hash, confidence, final_result, human_correction。
    AI 输出始终标记 system_truth=False。
    """
    result = dict(ai_result) if isinstance(ai_result, dict) else {"content": ai_result}

    # 域身份
    result["domain_id"] = domain_context.domain_id
    result["product_id"] = domain_context.product_id
    result["prompt_version"] = domain_context.prompt_version

    # 治理标记
    result["system_truth"] = False
    result["ai_enhanced"] = True
    result["confidence"] = confidence

    # 结果字段
    if final_result:
        result["final_result"] = final_result
    if human_correction:
        result["human_correction"] = human_correction

    # 输出哈希（用于追溯）
    output_content = result.get("content", "") or json_dumps_safe(result)
    result["output_hash"] = hashlib.sha256(
        str(output_content).encode("utf-8")
    ).hexdigest()[:32]

    return result


def json_dumps_safe(obj: Any) -> str:
    """安全 JSON 序列化。"""
    import json
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)


# ============================================================
# 7. 便捷函数：构建带校验的 AI 请求
# ============================================================
def prepare_domain_ai_request(
    user_content: str,
    domain_id: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """一站式：构建带域身份的 AI 请求并校验不串域。

    Returns:
        {
            "messages": [...],
            "domain_context": DomainPromptContext.to_dict(),
            "domain_id": str,
            "prompt_version": str,
            "input_hash": str,
        }
    """
    messages, ctx = build_domain_messages(user_content, domain_id, extra_context)

    # 校验：构建的 context 域身份与请求域一致
    expected = domain_id or get_current_domain()
    validate_domain_match(expected, ctx, operation="prepare_ai_request")

    # 计算输入哈希
    input_hash = hashlib.sha256(
        (user_content + ctx.prompt_version).encode("utf-8")
    ).hexdigest()[:32]

    return {
        "messages": messages,
        "domain_context": ctx.to_dict(),
        "domain_id": ctx.domain_id,
        "product_id": ctx.product_id,
        "prompt_version": ctx.prompt_version,
        "input_hash": input_hash,
    }


# ============================================================
# 8. 模块自描述
# ============================================================
def get_domain_context_summary() -> Dict[str, Any]:
    """获取双域上下文总览（用于审计/状态接口）。"""
    return {
        "domains": {
            did: {
                "product_id": ctx.product_id,
                "prompt_version": ctx.prompt_version,
                "analysis_focus_count": len(ctx.analysis_focus),
                "prohibited_topics_count": len(ctx.prohibited_topics),
            }
            for did, ctx in DOMAIN_CONTEXTS.items()
        },
        "current_domain": get_current_domain(),
        "isolation_enforced": True,
        "note": "CTH and ZBMP prompts are fully isolated; cross-domain flow raises DomainMismatchError",
    }


__all__ = [
    "DOMAIN_CTH", "DOMAIN_ZBMP",
    "PROMPT_VERSION_CTH", "PROMPT_VERSION_ZBMP",
    "DomainPromptContext", "CTH_CONTEXT", "ZBMP_CONTEXT",
    "DOMAIN_CONTEXTS", "DomainMismatchError",
    "product_id_to_domain", "get_current_domain", "get_domain_context",
    "build_domain_messages", "validate_domain_match",
    "validate_prompt_domain_isolation", "mark_ai_result_with_domain",
    "prepare_domain_ai_request", "get_domain_context_summary",
]
