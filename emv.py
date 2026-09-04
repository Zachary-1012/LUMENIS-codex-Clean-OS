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
