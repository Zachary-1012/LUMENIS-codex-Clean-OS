# -*- coding: utf-8 -*-
"""
AI 双域上下文隔离（ZBC V2.0 AI+Risk+Evidence+Permission+Report 双域隔离）

CTH = Guangzhou Taikoo Hui Protected Production Domain（生产真相域）
ZBMP = Multi-Subject Brand Management Platform（多主体平台域）

核心约束：
  1. CTH prompt 不得流入 ZBMP，ZBMP prompt 不得流入 CTH
  2. AI 请求根据当前线程 SubjectContext.product_id 选择对应 Context
  3. call_ai_with_governance 入口校验 domain_id 与 prompt context 匹配
  4. AI 输出标记 system_truth=False（AI 不能替代核心规则）
  5. Rule→AI辅助→Evidence→Evaluation→Final Decision 链中域身份贯穿全链
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

PROMPT_VERSION_CTH = "cth-v2.0"
PROMPT_VERSION_ZBMP = "zbmp-v2.0"


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
        "你是广州太古汇专项舆情分析助手。你的职责是对广州太古汇（Taikoo Hui）"
        "相关的社交媒体内容（小红书、微博、抖音等）进行精准的舆情分析。\n\n"
        "分析范围严格限定于：\n"
        "- 广州太古汇商场本体及场内 199 个品牌\n"
        "- 太古汇 9 大业态（零售、餐饮、娱乐、文化、服务等）\n"
        "- 太古汇相关舆情事件、活动、消费者体验\n"
        "- 太古汇品牌声誉与客户满意度\n\n"
        "分析原则：\n"
        "1. 仅分析与太古汇直接相关的内容，不扩展到无关品牌\n"
        "2. 情感判断必须基于文本证据，不得臆测\n"
        "3. 风险评级遵循太古汇专项风险策略（舆情扩散/安全/歧视/集中负面/KOC集中传播）\n"
        "4. 输出必须包含 sentiment / risk_level / topics / summary / evidence_ref\n"
        "5. 你的输出是 AI 辅助分析，不是最终决策；最终决策由 Rule→Evidence→Evaluation 链路给出"
    ),
    analysis_focus=[
        "太古汇商场本体舆情",
        "场内199品牌动态",
        "9业态分布与表现",
        "舆情事件追踪",
        "小红书/微博/抖音平台声量",
        "消费者体验与满意度",
        "KOC/KOL传播分析",
        "太古汇品牌声誉",
    ],
    output_schema_hint=(
        '{"sentiment": "positive|neutral|negative|unknown", '
        '"risk_level": "low|medium|high|critical|unknown", '
        '"topics": [...], "summary": "...", "evidence_ref": "...", '
        '"confidence": 0.0-1.0, "domain_id": "cth"}'
    ),
    prohibited_topics=[
        "非太古汇品牌的独立分析",
        "与太古汇无关的市场宏观预测",
        "竞品的深度策略建议（仅做对比参考）",
    ],
)

# ZBMP 域：多品牌智能分析
ZBMP_CONTEXT = DomainPromptContext(
    domain_id=DOMAIN_ZBMP,
    product_id=PRODUCT_ZBMP,
    prompt_version=PROMPT_VERSION_ZBMP,
    system_prompt=(
        "你是多主体品牌管理平台（ZBMP）的品牌智能分析助手。"
        "你的职责是对多个品牌进行品牌智能分析，包括品牌传播、竞争格局、"
        "市场趋势和品牌增长视角。\n\n"
        "分析范围：\n"
        "- 多品牌传播效果与声量分析\n"
        "- 竞品动态与竞争格局\n"
        "- 行业市场趋势识别\n"
        "- 品牌增长机会与策略建议\n"
        "- 内容表现与互动分析\n\n"
        "分析原则：\n"
        "1. 多品牌视角，不局限于单一主体\n"
        "2. 竞争分析需基于可验证的数据\n"
        "3. 风险评级遵循 ZBMP 品牌风险策略（品牌声誉/竞品冲击/传播异常/用户负反馈/品牌危机）\n"
        "4. 输出必须包含 sentiment / risk_level / topics / summary / evidence_ref\n"
        "5. 你的输出是 AI 辅助分析，不是最终决策；最终决策由 Rule→Evidence→Evaluation 链路给出"
    ),
    analysis_focus=[
        "多品牌传播分析",
        "竞品冲击与竞争格局",
        "市场趋势识别",
        "品牌增长机会",
        "内容表现评估",
        "用户负反馈监测",
        "品牌声誉管理",
        "跨平台声量对比",
    ],
    output_schema_hint=(
        '{"sentiment": "positive|neutral|negative|unknown", '
        '"risk_level": "low|medium|high|critical|unknown", '
        '"topics": [...], "summary": "...", "evidence_ref": "...", '
        '"confidence": 0.0-1.0, "domain_id": "zbmp"}'
    ),
    prohibited_topics=[
        "太古汇专项舆情规则（CTH 专属）",
        "太古汇 subject_hit 过滤逻辑",
        "太古汇 199 品牌/9 业态的专项分类",
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
    """将 product_id 映射为 domain_id。"""
    if product_id == PRODUCT_CTH:
        return DOMAIN_CTH
    if product_id == PRODUCT_ZBMP:
        return DOMAIN_ZBMP
    # 默认 CTH（生产安全默认）
    return DOMAIN_CTH


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
    """获取指定域的 Prompt 上下文。默认从当前线程解析。"""
    did = domain_id or get_current_domain()
    ctx = DOMAIN_CONTEXTS.get(did)
    if ctx is None:
        logger.warning("未知 domain_id=%s，回退 CTH 上下文", did)
        ctx = CTH_CONTEXT
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
