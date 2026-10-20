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

import math
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

INTERACTION_FIELDS = ("likes", "comments", "collects", "shares")
CUSTOM_CPM_ASSUMPTION_SOURCE = "调用方自定义 CPM 假设（未独立核验）"
EMV_DISCLAIMER = "估算口径，非官方媒体投放成本；CPM 来源见 EVIDENCE 文档"


def _nonnegative_finite(value: Any, field: str, *, allow_missing: bool) -> tuple[float | None, str | None]:
    """Parse an input without turning missing, malformed, or unsafe numbers into zero."""
    if value is None or (allow_missing and isinstance(value, str) and not value.strip()):
        return None, None
    if isinstance(value, bool):
        return None, f"{field} must be a finite non-negative number"
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None, f"{field} must be a finite non-negative number"
    if not math.isfinite(number) or number < 0:
        return None, f"{field} must be a finite non-negative number"
    return number, None


def _read_interactions(values: dict[str, Any]) -> tuple[dict[str, float], list[str], dict[str, str]]:
    parsed: dict[str, float] = {}
    missing: list[str] = []
    invalid: dict[str, str] = {}
    for field in INTERACTION_FIELDS:
        value, error = _nonnegative_finite(values.get(field), field, allow_missing=True)
        if error:
            invalid[field] = error
        elif value is None:
            missing.append(field)
        else:
            parsed[field] = value
    return parsed, missing, invalid


def _unavailable_emv(
    status: str,
    message: str,
    *,
    cpm: float | None,
    cpm_source: str,
    exposure_ratio: float | None,
    input_coverage: float = 0.0,
    missing_inputs: list[str] | None = None,
    invalid_inputs: dict[str, str] | None = None,
) -> dict:
    return {
        "status": status,
        "message": message,
        "emv_yuan": None,
        "exposure": None,
        "weighted_interaction": None,
        "cpm": cpm,
        "cpm_source": cpm_source,
        "exposure_ratio": exposure_ratio,
        "input_coverage": input_coverage,
        "missing_inputs": missing_inputs or [],
        "invalid_inputs": invalid_inputs or {},
        "is_estimate": True,
        "disclaimer": EMV_DISCLAIMER,
        "basis": "互动数据缺失或无效；EMV 金额不可用",
    }


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
    cpm_source = CPM_REFERENCE_SOURCE if cpm is None else CUSTOM_CPM_ASSUMPTION_SOURCE
    cpm_value, cpm_error = _nonnegative_finite(
        CPM_REFERENCE_CN if cpm is None else cpm, "cpm", allow_missing=False
    )
    ratio_value, ratio_error = _nonnegative_finite(
        INTERACTION_EXPOSURE_RATIO if exposure_ratio is None else exposure_ratio,
        "exposure_ratio", allow_missing=False,
    )
    observed, missing, invalid = _read_interactions({
        "likes": likes,
        "comments": comments,
        "collects": collects,
        "shares": shares,
    })
    if cpm_error:
        invalid["cpm"] = cpm_error
    if ratio_error:
        invalid["exposure_ratio"] = ratio_error
    if invalid:
        return _unavailable_emv(
            "INVALID_INPUT", "EMV 输入包含负数、非有限值或无效格式",
            cpm=cpm_value, cpm_source=cpm_source, exposure_ratio=ratio_value,
            input_coverage=len(observed) / len(INTERACTION_FIELDS),
            missing_inputs=missing, invalid_inputs=invalid,
        )

    input_coverage = len(observed) / len(INTERACTION_FIELDS)
    if not observed:
        return _unavailable_emv(
            "NOT_AVAILABLE", "互动数据全缺失，EMV 金额不可用",
            cpm=cpm_value, cpm_source=cpm_source, exposure_ratio=ratio_value,
            missing_inputs=missing,
        )

    weighted = (
        observed.get("likes", 0.0) * W_ENGAGE
        + observed.get("comments", 0.0) * W_COMMENT
        + observed.get("collects", 0.0) * W_COLLECT
        + observed.get("shares", 0.0) * W_SHARE
    )
    exposure = weighted * ratio_value
    emv = exposure / 1000.0 * cpm_value
    if not all(math.isfinite(value) for value in (weighted, exposure, emv)):
        return _unavailable_emv(
            "INVALID_INPUT", "EMV 计算结果超出有限数值范围",
            cpm=cpm_value, cpm_source=cpm_source, exposure_ratio=ratio_value,
            input_coverage=input_coverage, missing_inputs=missing,
            invalid_inputs={"calculation": "non-finite result"},
        )

    status = "PARTIAL" if missing else "OK"
    # A partial set containing only observed zeros has no usable monetary amount:
    # unknown interaction types could still contribute value.
    amount_available = status == "OK" or weighted > 0
    return {
        "status": status,
        "message": "仅按已提供的互动字段估算，结果不完整" if missing else None,
        "emv_yuan": round(emv, 2) if amount_available else None,
        "exposure": round(exposure, 1) if amount_available else None,
        "weighted_interaction": round(weighted, 1),
        "cpm": cpm_value,
        "cpm_source": cpm_source,
        "exposure_ratio": ratio_value,
        "input_coverage": input_coverage,
        "missing_inputs": missing,
        "invalid_inputs": {},
        "is_estimate": True,  # 契约红线：EMV 永远为估算口径
        "disclaimer": EMV_DISCLAIMER,
        "basis": (
            "仅已提供的真实互动字段 × 互动-曝光折算 × CPM（部分输入，不代表完整 EMV）"
            if missing else "真实互动(likes/comments/collects/shares) × 互动-曝光折算 × CPM"
        ),
    }


def aggregate_emv(notes: list[dict], cpm: float | None = None,
                  exposure_ratio: float | None = None) -> dict:
    """汇总一批笔记的 EMV（用于周期报告：日报/周报/月报/年报）。

    参数 notes：真实笔记字典列表（含 likes/comments/collects/shares）。
    返回：汇总 EMV + 明细 + 可用率（可用笔记占比，体现数据完整度）。
    """
    items = []
    total = len(notes)
    for n in notes:
        r = calculate_emv(n.get("likes"), n.get("comments"),
                          n.get("collects"), n.get("shares"),
                          cpm=cpm, exposure_ratio=exposure_ratio)
        if (r["status"] == "OK" and r.get("weighted_interaction") == 0
                and n.get("metrics_observed") is not True
                and not str(n.get("detail_fetched_at") or "").strip()):
            # Schema DEFAULT 0 and persisters that materialize absent metrics
            # as 0 make an all-zero row indistinguishable from "never
            # collected". Publish a zero amount only with observation
            # provenance; otherwise the amount is unavailable.
            r = _unavailable_emv(
                "NOT_AVAILABLE", "互动全为 0 且缺少采集观测来源，EMV 金额不可用",
                cpm=r.get("cpm"), cpm_source=r.get("cpm_source", ""),
                exposure_ratio=r.get("exposure_ratio"),
                missing_inputs=["metric_observation_provenance"],
            )
        items.append({
            "note_id": n.get("note_id", ""),
            "author": n.get("author_nickname", ""),
            "title": (n.get("title") or "")[:50],
            "sentiment": n.get("sentiment", "neutral"),
            **r,
        })
    available = sum(item["emv_yuan"] is not None for item in items)
    complete = sum(item["status"] == "OK" for item in items)
    partial = sum(item["status"] == "PARTIAL" for item in items)
    invalid = sum(item["status"] == "INVALID_INPUT" for item in items)
    unavailable = sum(item["status"] == "NOT_AVAILABLE" for item in items)
    cpm_source = CPM_REFERENCE_SOURCE if cpm is None else CUSTOM_CPM_ASSUMPTION_SOURCE
    cpm_value, cpm_error = _nonnegative_finite(
        CPM_REFERENCE_CN if cpm is None else cpm, "cpm", allow_missing=False
    )
    ratio_value, ratio_error = _nonnegative_finite(
        INTERACTION_EXPOSURE_RATIO if exposure_ratio is None else exposure_ratio,
        "exposure_ratio", allow_missing=False,
    )
    invalid_inputs = {
        key: value for key, value in (("cpm", cpm_error), ("exposure_ratio", ratio_error))
        if value
    }
    total_emv = sum(item["emv_yuan"] for item in items if item["emv_yuan"] is not None)
    total_exposure = sum(item["exposure"] for item in items if item["exposure"] is not None)
    if not math.isfinite(total_emv) or not math.isfinite(total_exposure):
        invalid_inputs["calculation"] = "aggregate result is non-finite"
    if invalid or invalid_inputs:
        status = "INVALID_INPUT"
    elif total == 0:
        status = "NOT_AVAILABLE"
    elif complete == total:
        status = "OK"
    elif available or partial:
        status = "PARTIAL"
    else:
        status = "NOT_AVAILABLE"

    if cpm_error or ratio_error:
        cpm_value = None if cpm_error else cpm_value
    if invalid or invalid_inputs:
        total_emv = None
        total_exposure = None
    return {
        "status": status,
        "emv_total_yuan": round(total_emv, 2) if available and not invalid and not invalid_inputs else None,
        "exposure_total": round(total_exposure, 1) if available and not invalid and not invalid_inputs else None,
        "note_count": total,
        "available_count": available,
        "complete_count": complete,
        "partial_count": partial,
        "unavailable_count": unavailable,
        "invalid_count": invalid,
        "coverage": round(available / total, 4) if total else 0.0,
        "complete_coverage": round(complete / total, 4) if total else 0.0,
        "is_estimate": True,
        "disclaimer": EMV_DISCLAIMER,
        "cpm": cpm_value,
        "cpm_source": cpm_source,
        "exposure_ratio": ratio_value,
        "invalid_inputs": invalid_inputs,
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
    normalized = normalize_platform(platform)
    cfg = PLATFORM_EMV_CONFIG.get(normalized, PLATFORM_EMV_CONFIG["default"])
    base_value, base_error = _nonnegative_finite(
        CPM_REFERENCE_CN if base_cpm is None else base_cpm, "cpm", allow_missing=False
    )
    multiplier, multiplier_error = _nonnegative_finite(
        cfg.get("cpm_multiplier"), "cpm_multiplier", allow_missing=False
    )
    ratio, ratio_error = _nonnegative_finite(
        cfg.get("exposure_ratio"), "exposure_ratio", allow_missing=False
    )
    weights: dict[str, float] = {}
    invalid: dict[str, str] = {}
    for field in INTERACTION_FIELDS:
        weight, error = _nonnegative_finite(
            cfg.get(f"weight_{field}"), f"weight_{field}", allow_missing=False
        )
        if error:
            invalid[f"weight_{field}"] = error
        else:
            weights[field] = weight
    for key, error in (("cpm", base_error), ("cpm_multiplier", multiplier_error),
                       ("exposure_ratio", ratio_error)):
        if error:
            invalid[key] = error

    cpm_source = (
        f"{CUSTOM_CPM_ASSUMPTION_SOURCE}；平台系数来源：{cfg['source']}"
        if base_cpm is not None
        else f"{CPM_REFERENCE_SOURCE}；平台系数来源：{cfg['source']}"
    )
    effective_cpm = base_value * multiplier if not invalid else None
    if effective_cpm is not None and not math.isfinite(effective_cpm):
        invalid["cpm"] = "effective cpm must be finite"
        effective_cpm = None
    observed, missing, invalid_interactions = _read_interactions({
        "likes": likes, "comments": comments, "collects": collects, "shares": shares,
    })
    invalid.update(invalid_interactions)
    input_coverage = len(observed) / len(INTERACTION_FIELDS)
    common = {
        "platform": platform,
        "platform_normalized": normalized,
        "platform_name": cfg["name"],
        "cpm": round(effective_cpm, 2) if effective_cpm is not None else None,
        "cpm_base": base_value,
        "cpm_multiplier": multiplier,
        "exposure_ratio": ratio,
        "weights": weights,
        "cpm_source": cpm_source,
        "is_estimate": True,
        "disclaimer": f"{EMV_DISCLAIMER}；平台系数来源见 cpm_source",
        "ic_reference": "IC-021",
        "input_coverage": input_coverage,
        "missing_inputs": missing,
        "invalid_inputs": invalid,
    }
    if invalid:
        return {
            **common,
            "status": "INVALID_INPUT",
            "message": "EMV 输入包含负数、非有限值或无效格式",
            "emv_yuan": None,
            "exposure": None,
            "weighted_interaction": None,
            "basis": "互动数据或 CPM 参数无效；EMV 金额不可用",
        }
    if not observed:
        return {
            **common,
            "status": "NOT_AVAILABLE",
            "message": f"互动数据全缺失，EMV 金额不可用（平台={cfg['name']}）",
            "emv_yuan": None,
            "exposure": None,
            "weighted_interaction": None,
            "basis": "互动数据缺失；EMV 金额不可用",
        }

    weighted = sum(observed.get(field, 0.0) * weights[field] for field in INTERACTION_FIELDS)
    exposure = weighted * ratio
    emv = exposure / 1000.0 * effective_cpm
    if not all(math.isfinite(value) for value in (weighted, exposure, emv)):
        return {
            **common,
            "status": "INVALID_INPUT",
            "message": "EMV 计算结果超出有限数值范围",
            "emv_yuan": None,
            "exposure": None,
            "weighted_interaction": None,
            "invalid_inputs": {"calculation": "non-finite result"},
            "basis": "EMV 计算结果超出有限数值范围；金额不可用",
        }

    partial = bool(missing)
    amount_available = not partial or weighted > 0
    return {
        **common,
        "status": "PARTIAL" if partial else "OK",
        "message": "仅按已提供的互动字段估算，结果不完整" if partial else None,
        "emv_yuan": round(emv, 2) if amount_available else None,
        "exposure": round(exposure, 1) if amount_available else None,
        "weighted_interaction": round(weighted, 1),
        "basis": (
            "仅已提供的真实互动字段 × 平台互动权重 × 曝光折算 × CPM（部分输入）"
            if partial else "真实互动 × 平台互动权重 × 曝光折算 × CPM"
        ),
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
    complete = 0
    partial = 0
    unavailable = 0
    invalid = 0
    total = len(notes)
    base_value, base_error = _nonnegative_finite(
        CPM_REFERENCE_CN if base_cpm is None else base_cpm, "cpm", allow_missing=False
    )

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
            complete += 1
        elif r["status"] == "PARTIAL":
            partial += 1
        elif r["status"] == "INVALID_INPUT":
            invalid += 1
        elif r["status"] == "NOT_AVAILABLE":
            unavailable += 1
        has_amount = r["emv_yuan"] is not None
        if has_amount:
            if r["status"] != "OK":
                available += 1
            grand_total_emv += r["emv_yuan"]
            grand_total_exposure += r["exposure"]

        # Keep every observed platform group, including groups with no usable
        # estimate. Group note_count must describe all notes, not just rows that
        # contributed a monetary amount.
        pkey = r["platform_normalized"]
        if pkey not in platform_totals:
            platform_totals[pkey] = {
                "platform_name": r["platform_name"],
                "emv_yuan": 0.0,
                "exposure": 0.0,
                "note_count": 0,
                "available_count": 0,
                "complete_count": 0,
                "partial_count": 0,
                "unavailable_count": 0,
                "invalid_count": 0,
            }
        group = platform_totals[pkey]
        group["note_count"] += 1
        group["complete_count"] += int(r["status"] == "OK")
        group["partial_count"] += int(r["status"] == "PARTIAL")
        group["unavailable_count"] += int(r["status"] == "NOT_AVAILABLE")
        group["invalid_count"] += int(r["status"] == "INVALID_INPUT")
        if has_amount:
            group["emv_yuan"] += r["emv_yuan"]
            group["exposure"] += r["exposure"]
            group["available_count"] += 1

    # Platform group sums may overflow even if every per-note estimate is finite.
    platform_overflow = False
    for pkey in platform_totals:
        group = platform_totals[pkey]
        group_overflow = (
            not math.isfinite(group["emv_yuan"]) or not math.isfinite(group["exposure"])
        )
        if group_overflow:
            platform_overflow = True
        if group_overflow or group["invalid_count"] or group["available_count"] == 0:
            group["emv_yuan"] = None
            group["exposure"] = None
        else:
            group["emv_yuan"] = round(group["emv_yuan"], 2)
            group["exposure"] = round(group["exposure"], 1)
        group["coverage"] = round(group["available_count"] / group["note_count"], 4)
        group["complete_coverage"] = round(group["complete_count"] / group["note_count"], 4)
        if group_overflow or group["invalid_count"]:
            group["status"] = "INVALID_INPUT"
        elif group["complete_count"] == group["note_count"]:
            group["status"] = "OK"
        elif group["available_count"] or group["partial_count"]:
            group["status"] = "PARTIAL"
        else:
            group["status"] = "NOT_AVAILABLE"

    aggregate_invalid = (
        invalid > 0 or bool(base_error) or platform_overflow
        or not math.isfinite(grand_total_emv)
        or not math.isfinite(grand_total_exposure)
    )
    if aggregate_invalid:
        status = "INVALID_INPUT"
        invalid += int(not math.isfinite(grand_total_emv) or not math.isfinite(grand_total_exposure))
        invalid += int(bool(base_error) and invalid == 0)
    elif total == 0 or (available == 0 and partial == 0):
        status = "NOT_AVAILABLE"
    elif complete == total:
        status = "OK"
    else:
        status = "PARTIAL"

    return {
        "status": status,
        "emv_total_yuan": round(grand_total_emv, 2) if available and not aggregate_invalid else None,
        "exposure_total": round(grand_total_exposure, 1) if available and not aggregate_invalid else None,
        "note_count": total,
        "available_count": available,
        "complete_count": complete,
        "partial_count": partial,
        "unavailable_count": unavailable,
        "invalid_count": invalid,
        "coverage": round(available / total, 4) if total else 0.0,
        "by_platform": platform_totals,
        "platform_count": len(platform_totals),
        "is_estimate": True,
        "disclaimer": f"{EMV_DISCLAIMER}；按平台系数计算（IC-021），自定义 CPM 时按假设处理",
        "cpm_base": base_value,
        "invalid_inputs": {"cpm": base_error} if base_error else {},
        "cpm_source": (
            f"{CUSTOM_CPM_ASSUMPTION_SOURCE}；各平台系数来源见 items.cpm_source"
            if base_cpm is not None else f"{CPM_REFERENCE_SOURCE}；各平台系数来源见 items.cpm_source"
        ),
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
