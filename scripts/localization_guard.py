# -*- coding: utf-8 -*-
"""跨文化本地化守卫 · scripts/localization_guard.py。

依据：PCCC IC-039 §4（序境中英韩 + 内容出海本地化契约）。
核心原则：
  - 灵魂全球统一（品牌/信任基石）+ 表达本地适配（语言/情绪/审美/合规）；
  - AI 只做变体生成与初译，本地母语者把关（AI 不决策本地化）；
  - 禁忌库命中必须 HOLD 并提示人工复核，禁止自动改写后直接发布；
  - 外部内容不可信、AI 辅助不越权、个人业务资料只存本地不上线。

本模块为**静态规则库 + 检查层**（纯函数，无 Runtime/采集），供创意引擎输出前检查。
独立开关：LOCALIZATION_GUARD_ENABLED（env 或常量），可整体关闭，不影响原内容生成路径。
"""
from __future__ import annotations

import os
from typing import Any

# ---- 独立开关（契约 §4.6 回滚：可开关，不影响原路径）----
ENABLED = os.environ.get("LOCALIZATION_GUARD_ENABLED", "1") == "1"

# ---- 文化禁忌/合规静态库（中/英/韩；命中即 HOLD）----
# 结构：{region/lang: [{pattern, reason, level}]}
# level: BLOCK（绝对禁止）/ HOLD（需人工复核）
TABOO_RULES: dict[str, list[dict]] = {
    "zh": [
        {"pattern": "最", "reason": "广告法绝对化用语（最/第一/领先）需可验证或慎用", "level": "HOLD"},
        {"pattern": "第一", "reason": "广告法绝对化用语（第一）需可验证或慎用", "level": "HOLD"},
        {"pattern": "领先", "reason": "广告法绝对化用语（领先）需可验证或慎用", "level": "HOLD"},
        {"pattern": "国家级", "reason": "广告法敏感用语（国家级）", "level": "HOLD"},
        {"pattern": "唯一", "reason": "广告法绝对化用语（唯一）", "level": "HOLD"},
        {"pattern": "顶级", "reason": "广告法绝对化用语（顶级）", "level": "HOLD"},
    ],
    "en": [
        {"pattern": "the best", "reason": "绝对化用语需可验证（best）", "level": "HOLD"},
        {"pattern": "first", "reason": "绝对化用语需可验证（first）", "level": "HOLD"},
        {"pattern": "number 1", "reason": "绝对化用语需可验证（number 1）", "level": "HOLD"},
        {"pattern": "guarantee", "reason": "绝对化承诺需可验证（guarantee）", "level": "HOLD"},
    ],
    "ko": [
        {"pattern": "최고", "reason": "绝对化用语需可验证（최고/最佳）", "level": "HOLD"},
        {"pattern": "1위", "reason": "绝对化用语需可验证（1위/第一）", "level": "HOLD"},
        {"pattern": "유일", "reason": "绝对化用语需可验证（유일/唯一）", "level": "HOLD"},
    ],
}

# 宗教/王室/文化符号禁区（跨区域，命中 BLOCK）
SYMBOL_RULES: list[dict] = [
    {"pattern": "清真", "reason": "宗教符号敏感，需按目标市场宗教规范处理", "level": "BLOCK"},
    {"pattern": "하나님", "reason": "宗教用语敏感，需本地宗教规范处理", "level": "BLOCK"},
    {"pattern": "Allah", "reason": "宗教用语敏感，需本地宗教规范处理", "level": "BLOCK"},
    {"pattern": "왕실", "reason": "王室符号敏感，需目标市场规范处理", "level": "BLOCK"},
    {"pattern": "royal", "reason": "王室符号敏感，需目标市场规范处理", "level": "HOLD"},
    {"pattern": "monarch", "reason": "王室符号敏感，需目标市场规范处理", "level": "HOLD"},
]

# 平台行为库（作为内容适配建议，非强制）
PLATFORM_BEHAVIOR: dict[str, list[str]] = {
    "zh": ["小红书/微信：种草-信任-转化链路；长图文+互动引导", "抖音：短平快，前 3 秒钩子"],
    "en": ["Instagram：视觉优先 + 故事化", "TikTok：完播率驱动，开头即高潮"],
    "ko": ["韩国平台：长 caption + 详细体验描述更受偏好", "NAVER：重搜索索引与信任内容"],
    "global": ["出海内容需适配本地平台习惯与节日节点"],
}


def check(text: str, lang: str = "zh", platform: str = "") -> dict:
    """检查一段内容是否命中文化禁忌/合规规则。

    返回：
      {
        "hold": bool,          # 是否需人工复核
        "blocked": bool,       # 是否绝对禁止
        "hits": [ {pattern, reason, level, lang} ],
        "platform_advice": [...],
        "requires_human": bool,  # 契约红线：命中必须人工确认
      }
    注意：契约红线——命中 HOLD/BLOCK 必须 HOLD 并提示人工复核，
    禁止自动改写后直接发布；AI 输出一律标记"待母语者确认"。
    """
    if not ENABLED:
        return {"hold": False, "blocked": False, "hits": [],
                "platform_advice": [], "requires_human": False,
                "disabled": True}
    if not text:
        return {"hold": False, "blocked": False, "hits": [],
                "platform_advice": [], "requires_human": False}
    text_l = text.lower()
    hits = []
    for rule in TABOO_RULES.get(lang, []):
        if rule["pattern"].lower() in text_l:
            hits.append({**rule, "lang": lang})
    for rule in SYMBOL_RULES:
        if rule["pattern"].lower() in text_l:
            hits.append({**rule, "lang": "global"})
    # 平台行为建议
    advice = list(PLATFORM_BEHAVIOR.get(lang, []))
    if platform:
        advice.append(f"平台[{platform}]适配建议见平台行为库")
    advice += list(PLATFORM_BEHAVIOR.get("global", []))
    blocked = any(h["level"] == "BLOCK" for h in hits)
    hold = bool(hits)  # 命中即需人工复核（契约红线）
    return {
        "hold": hold,
        "blocked": blocked,
        "hits": hits,
        "platform_advice": advice,
        "requires_human": hold,
        "label": "初译/变体，待母语者确认" if hold else "通过",
    }


def check_multi(text: str, langs: list[str] | None = None,
                platform: str = "") -> dict:
    """多语言同时检查（中/英/韩），返回聚合结果。"""
    langs = langs or ["zh", "en", "ko"]
    results = {}
    all_hits = []
    for lg in langs:
        r = check(text, lang=lg, platform=platform)
        results[lg] = r
        all_hits += r["hits"]
    return {
        "results": results,
        "hold": any(r["hold"] for r in results.values()),
        "blocked": any(r["blocked"] for r in results.values()),
        "all_hits": all_hits,
        "requires_human": any(r["requires_human"] for r in results.values()),
    }


# ============================================================
# IC-039: 本地化评分（与 canonical_data.CanonicalRecord 集成）
# ============================================================

def score_content(text: str, lang: str = "zh", platform: str = "") -> float:
    """计算内容的跨文化本地化评分（0-1）。

    评分规则：
    - 1.0：无任何禁忌/合规问题，可直接发布
    - 0.7-0.99：命中 HOLD 级规则（绝对化用语等），需人工复核
    - 0.3-0.69：命中多条 HOLD 规则，需重点修改
    - 0.0-0.29：命中 BLOCK 级规则（宗教/王室符号等），禁止发布
    - None：内容为空或 guard 未启用

    注意：评分仅为初筛参考，最终发布决策必须由人工确认（契约红线）。
    """
    if not ENABLED:
        return 1.0  # guard 关闭时不扣分
    if not text:
        return None

    result = check(text, lang=lang, platform=platform)
    if result.get("blocked"):
        # BLOCK 级命中：评分 0-0.3
        block_count = sum(1 for h in result["hits"] if h["level"] == "BLOCK")
        return max(0.0, 0.3 - block_count * 0.1)
    if result.get("hold"):
        # HOLD 级命中：每条扣 0.1，最低 0.3
        hold_count = len(result["hits"])
        return max(0.3, 1.0 - hold_count * 0.1)
    return 1.0


def score_multi(text: str, langs: list[str] | None = None,
                platform: str = "") -> dict:
    """多语言本地化评分（返回各语言评分及最低分）。"""
    langs = langs or ["zh", "en", "ko"]
    scores = {}
    for lg in langs:
        scores[lg] = score_content(text, lang=lg, platform=platform)
    valid_scores = [s for s in scores.values() if s is not None]
    return {
        "scores": scores,
        "min_score": min(valid_scores) if valid_scores else None,
        "max_score": max(valid_scores) if valid_scores else None,
        "avg_score": sum(valid_scores) / len(valid_scores) if valid_scores else None,
    }


def apply_to_record(record, text: str | None = None,
                    lang: str = "zh", platform: str = "") -> float | None:
    """将本地化评分应用到 CanonicalRecord。

    设置 record.localization_score 字段。
    如果 text 为 None，使用 record.title + record.content 拼接。

    Returns:
        评分值（0-1），或 None（内容为空/guard 关闭）
    """
    if text is None:
        title = getattr(record, "title", "") or ""
        content = getattr(record, "content", "") or ""
        text = f"{title} {content}".strip()
    score = score_content(text, lang=lang, platform=platform)
    record.localization_score = score
    return score


def get_localization_advice(text: str, lang: str = "zh",
                             platform: str = "") -> dict:
    """获取本地化适配建议（含评分、命中规则、修改建议）。"""
    result = check(text, lang=lang, platform=platform)
    score = score_content(text, lang=lang, platform=platform)
    suggestions = []
    for hit in result.get("hits", []):
        if hit["level"] == "BLOCK":
            suggestions.append(f"[禁止] 移除/替换 '{hit['pattern']}': {hit['reason']}")
        else:
            suggestions.append(f"[复核] 检查 '{hit['pattern']}': {hit['reason']}")
    return {
        "score": score,
        "hold": result.get("hold", False),
        "blocked": result.get("blocked", False),
        "hits": result.get("hits", []),
        "suggestions": suggestions,
        "platform_advice": result.get("platform_advice", []),
        "requires_human": result.get("requires_human", False),
    }
