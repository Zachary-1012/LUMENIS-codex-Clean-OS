# -*- coding: utf-8 -*-
"""EMV（Earned Media Value）估算引擎 · FUNC-CONTENT-04 · MET-CONTENT-04。

依据：PCCC IC-021 §2（earned media value 替代 AVE 口径，纳入 Metric Registry 与统一报告模板）。
口径红线（契约 Gate）：
  - EMV 是**展示性估算指标**，必须显式标注"估算口径 + CPM 来源"；
  - 必须基于真实曝光/互动数据（likes/comments/collects/shares）与明确 CPM 假设；
  - 无可用数据时返回 NOT_AVAILABLE，禁止估 0 / 伪装 0；
  - 不修改任何既有 MET-RISK/MET-CONTENT 计算逻辑（防数字真相漂移）。

本模块为纯函数层（不含 Runtime/采集），供报告引擎与 API 消费。
"""
from __future__ import annotations

from typing import Any

# 唯一 CPM 假设源（估算口径，须登记来源；替换时改此常量即可，禁止散落魔数）
# 口径说明：行业公开参考区间 3~15 元/千次曝光（中国社交媒体信息流均值口径，2026 公开行业参考，待季度校准）
CPM_REFERENCE_CN = 8.0          # 元 / 千次曝光（CPM 基准，来源见 EVIDENCE 文档）
CPM_REFERENCE_SOURCE = "行业公开参考区间 3~15 元/千次曝光的中间值（2026，估算口径，非官方媒体投放成本）"
# 互动折算：曝光估算 = 互动量 × 互动-曝光折算系数（互动率反推，行业均值 3% 口径）
INTERACTION_EXPOSURE_RATIO = 33.3   # 1 次互动 ≈ 33.3 次曝光（≈ 1/3% 互动率口径，估算）
# 互动质量权重：不同互动类型对"媒体价值"的贡献差异（分享/收藏 > 评论 > 点赞）
W_ENGAGE = 1.0
W_COMMENT = 1.5
W_COLLECT = 1.8
W_SHARE = 2.5


def calculate_emv(likes: Any = None, comments: Any = None,
                  collects: Any = None, shares: Any = None,
                  cpm: float | None = None,
                  exposure_ratio: float | None = None) -> dict:
    """计算单条笔记 EMV（估算）。

    公式：曝光 ≈ (likes*W_ENGAGE + comments*W_COMMENT + collects*W_COLLECT
                   + shares*W_SHARE) * exposure_ratio
          EMV = 曝光 / 1000 * cpm

    返回：结构化结果，含估算口径标注；无互动数据返回 NOT_AVAILABLE。
    """
    def _num(v):
        try:
            f = float(v)
            return f if f > 0 else 0.0
        except (TypeError, ValueError):
            return 0.0

    likes = _num(likes)
    comments = _num(comments)
    collects = _num(collects)
    shares = _num(shares)

    weighted = (likes * W_ENGAGE + comments * W_COMMENT
                + collects * W_COLLECT + shares * W_SHARE)
    if weighted <= 0:
        return {
            "status": "NOT_AVAILABLE",
            "message": "无可用互动数据，EMV 不估算（禁止估 0）",
            "emv_yuan": None,
            "exposure": None,
            "cpm": None,
            "basis": "互动数据缺失",
            "is_estimate": True,
        }

    cpm = cpm if cpm is not None else CPM_REFERENCE_CN
    ratio = exposure_ratio if exposure_ratio is not None else INTERACTION_EXPOSURE_RATIO
    exposure = weighted * ratio
    emv = round(exposure / 1000.0 * cpm, 2)
    return {
        "status": "OK",
        "emv_yuan": emv,
        "exposure": round(exposure, 1),
        "weighted_interaction": round(weighted, 1),
        "cpm": cpm,
        "cpm_source": CPM_REFERENCE_SOURCE if cpm == CPM_REFERENCE_CN else "自定义 CPM（调用方指定）",
        "exposure_ratio": ratio,
        "is_estimate": True,  # 契约红线：EMV 永远为估算口径
        "disclaimer": "估算口径，非官方媒体投放成本；CPM 来源见 EVIDENCE 文档",
        "basis": "真实互动(likes/comments/collects/shares) × 互动-曝光折算 × CPM",
    }


def aggregate_emv(notes: list[dict], cpm: float | None = None,
                  exposure_ratio: float | None = None) -> dict:
    """汇总一批笔记的 EMV（用于周期报告：日报/周报/月报/年报）。

    参数 notes：真实笔记字典列表（含 likes/comments/collects/shares）。
    返回：汇总 EMV + 明细 + 可用率（可用笔记占比，体现数据完整度）。
    """
    items = []
    total_emv = 0.0
    total_exposure = 0.0
    available = 0
    total = len(notes)
    for n in notes:
        r = calculate_emv(n.get("likes"), n.get("comments"),
                          n.get("collects"), n.get("shares"),
                          cpm=cpm, exposure_ratio=exposure_ratio)
        items.append({
            "note_id": n.get("note_id", ""),
            "author": n.get("author_nickname", ""),
            "title": (n.get("title") or "")[:50],
            "sentiment": n.get("sentiment", "neutral"),
            **r,
        })
        if r["status"] == "OK":
            available += 1
            total_emv += r["emv_yuan"]
            total_exposure += r["exposure"]
    return {
        "status": "OK" if available else "NOT_AVAILABLE",
        "emv_total_yuan": round(total_emv, 2),
        "exposure_total": round(total_exposure, 1),
        "note_count": total,
        "available_count": available,
        "coverage": round(available / total, 4) if total else 0.0,
        "is_estimate": True,
        "disclaimer": "估算口径，非官方媒体投放成本；CPM 来源见 EVIDENCE 文档",
        "cpm": cpm if cpm is not None else CPM_REFERENCE_CN,
        "cpm_source": CPM_REFERENCE_SOURCE if cpm is None else "自定义 CPM（调用方指定）",
        "items": items,
    }


# ============================================================
# IC-021 增强：按平台规则配置 EMV 系数
# ============================================================
# 不同平台的 CPM 系数和互动-曝光折算系数差异
# 基于各平台公开行业参考（2026），估算口径，待季度校准
PLATFORM_EMV_CONFIG = {
    "xhs": {
        "name": "小红书",
        "cpm_multiplier": 1.2,       # 小红书 CPM 相对基准偏高（种草属性强）
        "exposure_ratio": 33.3,       # 互动-曝光折算
        "weight_likes": 1.0,
        "weight_comments": 1.5,
        "weight_collects": 1.8,       # 小红书收藏价值高
        "weight_shares": 2.5,
        "source": "小红书种草平台行业参考 CPM 区间（2026，估算口径）",
    },
    "weibo": {
        "name": "微博",
        "cpm_multiplier": 0.8,        # 微博 CPM 相对基准偏低
        "exposure_ratio": 50.0,       # 微博曝光-互动比更高（公域流量大）
        "weight_likes": 1.0,
        "weight_comments": 1.3,
        "weight_collects": 1.2,
        "weight_shares": 2.0,         # 微博转发价值高
        "source": "微博公开信息流行业参考（2026，估算口径）",
    },
    "douyin": {
        "name": "抖音",
        "cpm_multiplier": 1.0,
        "exposure_ratio": 40.0,
        "weight_likes": 1.0,
        "weight_comments": 1.4,
        "weight_collects": 1.5,
        "weight_shares": 2.2,
        "source": "抖音短视频平台行业参考（2026，估算口径）",
    },
    "wechat": {
        "name": "微信",
        "cpm_multiplier": 1.5,        # 微信生态 CPM 偏高（私域价值）
        "exposure_ratio": 25.0,
        "weight_likes": 1.0,
        "weight_comments": 1.6,
        "weight_collects": 1.5,
        "weight_shares": 3.0,         # 微信分享/在看价值极高
        "source": "微信公众号/视频号行业参考（2026，估算口径）",
    },
    "bilibili": {
        "name": "B站",
        "cpm_multiplier": 0.9,
        "exposure_ratio": 35.0,
        "weight_likes": 1.0,
        "weight_comments": 1.5,
        "weight_collects": 2.0,       # B站收藏价值高
        "weight_shares": 2.0,
        "source": "B站社区行业参考（2026，估算口径）",
    },
    "default": {
        "name": "默认/其他平台",
        "cpm_multiplier": 1.0,
        "exposure_ratio": 33.3,
        "weight_likes": 1.0,
        "weight_comments": 1.5,
        "weight_collects": 1.8,
        "weight_shares": 2.5,
        "source": "行业通用基准（2026，估算口径）",
    },
}

# 平台别名映射（兼容不同数据源的平台命名）
PLATFORM_ALIASES = {
    "小红书": "xhs", "rednote": "xhs", "red": "xhs", "xhs": "xhs",
    "微博": "weibo", "weibo": "weibo", "wb": "weibo",
    "抖音": "douyin", "douyin": "douyin", "dy": "douyin", "tiktok": "douyin",
    "微信": "wechat", "wechat": "wechat", "wx": "wechat", "公众号": "wechat",
    "b站": "bilibili", "bilibili": "bilibili", "bili": "bilibili",
}


def normalize_platform(platform: str) -> str:
    """规范化平台名称，返回 PLATFORM_EMV_CONFIG 的 key。"""
    if not platform:
        return "default"
    key = platform.strip().lower()
    return PLATFORM_ALIASES.get(key, PLATFORM_ALIASES.get(platform.strip(), "default"))


def calculate_emv_by_platform(
    likes=None, comments=None, collects=None, shares=None,
    platform: str = "default",
    base_cpm: float | None = None,
) -> dict:
    """按平台配置计算 EMV（IC-021 增强）。

    使用平台专属的 CPM 系数、曝光折算系数和互动权重。
    """
    cfg = PLATFORM_EMV_CONFIG.get(normalize_platform(platform), PLATFORM_EMV_CONFIG["default"])
    cpm = (base_cpm if base_cpm is not None else CPM_REFERENCE_CN) * cfg["cpm_multiplier"]

    def _num(v):
        try:
            f = float(v)
            return f if f > 0 else 0.0
        except (TypeError, ValueError):
            return 0.0

    likes = _num(likes)
    comments = _num(comments)
    collects = _num(collects)
    shares = _num(shares)

    weighted = (likes * cfg["weight_likes"] + comments * cfg["weight_comments"]
                + collects * cfg["weight_collects"] + shares * cfg["weight_shares"])

    if weighted <= 0:
        return {
            "status": "NOT_AVAILABLE",
            "message": f"无可用互动数据，EMV 不估算（平台={cfg['name']}）",
            "emv_yuan": None,
            "exposure": None,
            "platform": platform,
            "platform_normalized": normalize_platform(platform),
            "is_estimate": True,
        }

    exposure = weighted * cfg["exposure_ratio"]
    emv = round(exposure / 1000.0 * cpm, 2)

    return {
        "status": "OK",
        "emv_yuan": emv,
        "exposure": round(exposure, 1),
        "weighted_interaction": round(weighted, 1),
        "platform": platform,
        "platform_normalized": normalize_platform(platform),
        "platform_name": cfg["name"],
        "cpm": round(cpm, 2),
        "cpm_base": base_cpm if base_cpm is not None else CPM_REFERENCE_CN,
        "cpm_multiplier": cfg["cpm_multiplier"],
        "exposure_ratio": cfg["exposure_ratio"],
        "weights": {
            "likes": cfg["weight_likes"],
            "comments": cfg["weight_comments"],
            "collects": cfg["weight_collects"],
            "shares": cfg["weight_shares"],
        },
        "cpm_source": cfg["source"],
        "is_estimate": True,
        "disclaimer": "估算口径，非官方媒体投放成本；平台系数基于行业参考（2026）",
        "ic_reference": "IC-021",
    }


def aggregate_emv_by_platform(notes: list[dict], base_cpm: float | None = None) -> dict:
    """按平台分组汇总 EMV（IC-021 增强）。

    返回各平台的 EMV 汇总 + 总计。
    """
    platform_totals = {}
    all_items = []
    grand_total_emv = 0.0
    grand_total_exposure = 0.0
    available = 0
    total = len(notes)

    for n in notes:
        platform = n.get("source_platform") or n.get("platform") or "default"
        r = calculate_emv_by_platform(
            n.get("likes"), n.get("comments"),
            n.get("collects"), n.get("shares"),
            platform=platform, base_cpm=base_cpm,
        )
        item = {
            "note_id": n.get("note_id", ""),
            "platform": platform,
            **r,
        }
        all_items.append(item)

        if r["status"] == "OK":
            available += 1
            grand_total_emv += r["emv_yuan"]
            grand_total_exposure += r["exposure"]
            pkey = r["platform_normalized"]
            if pkey not in platform_totals:
                platform_totals[pkey] = {
                    "platform_name": r["platform_name"],
                    "emv_yuan": 0.0,
                    "exposure": 0.0,
                    "note_count": 0,
                }
            platform_totals[pkey]["emv_yuan"] += r["emv_yuan"]
            platform_totals[pkey]["exposure"] += r["exposure"]
            platform_totals[pkey]["note_count"] += 1

    # 四舍五入
    for pkey in platform_totals:
        platform_totals[pkey]["emv_yuan"] = round(platform_totals[pkey]["emv_yuan"], 2)
        platform_totals[pkey]["exposure"] = round(platform_totals[pkey]["exposure"], 1)

    return {
        "status": "OK" if available else "NOT_AVAILABLE",
        "emv_total_yuan": round(grand_total_emv, 2),
        "exposure_total": round(grand_total_exposure, 1),
        "note_count": total,
        "available_count": available,
        "coverage": round(available / total, 4) if total else 0.0,
        "by_platform": platform_totals,
        "platform_count": len(platform_totals),
        "is_estimate": True,
        "disclaimer": "估算口径，非官方媒体投放成本；按平台系数计算（IC-021）",
        "ic_reference": "IC-021",
        "items": all_items,
    }


def get_emv_platform_config() -> dict:
    """获取 EMV 平台配置（用于审计/API 展示）。"""
    return {
        "ic_reference": "IC-021",
        "base_cpm": CPM_REFERENCE_CN,
        "base_cpm_source": CPM_REFERENCE_SOURCE,
        "platforms": {
            key: {
                "name": cfg["name"],
                "cpm_multiplier": cfg["cpm_multiplier"],
                "effective_cpm": round(CPM_REFERENCE_CN * cfg["cpm_multiplier"], 2),
                "exposure_ratio": cfg["exposure_ratio"],
                "weights": {
                    "likes": cfg["weight_likes"],
                    "comments": cfg["weight_comments"],
                    "collects": cfg["weight_collects"],
                    "shares": cfg["weight_shares"],
                },
                "source": cfg["source"],
            }
            for key, cfg in PLATFORM_EMV_CONFIG.items()
        },
        "platform_aliases": PLATFORM_ALIASES,
        "hard_constraints": [
            "EMV is always an estimate (is_estimate=True)",
            "No data returns NOT_AVAILABLE (never fabricate 0)",
            "Platform coefficients are configurable and sourced",
        ],
    }


# ============================================================
# IC-021: 注册到 function_registry
# ============================================================
def register_emv_to_function_registry():
    """将 EMV 指标注册到 function_registry（幂等）。

    注册内容：
    - metrics.emv.calculate: 单条 EMV 计算
    - metrics.emv.aggregate: 批量 EMV 汇总
    - metrics.emv.by_platform: 按平台 EMV 计算
    - metrics.emv.aggregate_by_platform: 按平台分组汇总
    """
    try:
        import function_registry as fr
        # 检查是否已有注册机制
        if hasattr(fr, "register_function"):
            fr.register_function(
                "metrics.emv.calculate",
                calculate_emv,
                description="计算单条内容 EMV（Earned Media Value），基于互动量和 CPM 估算",
                category="metrics",
                ic_reference="IC-021",
            )
            fr.register_function(
                "metrics.emv.aggregate",
                aggregate_emv,
                description="批量汇总 EMV，用于周期报告",
                category="metrics",
                ic_reference="IC-021",
            )
            fr.register_function(
                "metrics.emv.by_platform",
                calculate_emv_by_platform,
                description="按平台专属系数计算 EMV（小红书/微博/抖音/微信/B站）",
                category="metrics",
                ic_reference="IC-021",
            )
            fr.register_function(
                "metrics.emv.aggregate_by_platform",
                aggregate_emv_by_platform,
                description="按平台分组汇总 EMV，返回各平台 EMV 占比",
                category="metrics",
                ic_reference="IC-021",
            )
            return {"registered": True, "count": 4, "method": "register_function"}
        # 如果没有 register_function，尝试 FUNCTION_MAP 追加
        elif hasattr(fr, "FUNCTION_MAP"):
            emv_entries = [
                {"id": "metrics.emv.calculate", "page": "metrics", "label": "EMV计算",
                 "targets": ["emv"], "keywords": ["EMV", "媒体价值", "earned media", "CPM"]},
                {"id": "metrics.emv.aggregate", "page": "metrics", "label": "EMV汇总",
                 "targets": ["emv"], "keywords": ["EMV汇总", "媒体价值汇总"]},
                {"id": "metrics.emv.by_platform", "page": "metrics", "label": "平台EMV",
                 "targets": ["emv"], "keywords": ["平台EMV", "小红书EMV", "微博EMV"]},
            ]
            existing_ids = {e.get("id") for e in fr.FUNCTION_MAP}
            added = 0
            for entry in emv_entries:
                if entry["id"] not in existing_ids:
                    fr.FUNCTION_MAP.append(entry)
                    added += 1
            return {"registered": True, "count": added, "method": "FUNCTION_MAP append"}
        else:
            return {"registered": False, "reason": "function_registry has no register_function or FUNCTION_MAP"}
    except ImportError:
        return {"registered": False, "reason": "function_registry not available"}
    except Exception as e:
        return {"registered": False, "reason": f"registration failed: {e}"}


# 模块加载时自动注册（幂等，失败不阻断）
try:
    _emv_registration_result = register_emv_to_function_registry()
except Exception:
    _emv_registration_result = {"registered": False, "reason": "auto-register exception"}
