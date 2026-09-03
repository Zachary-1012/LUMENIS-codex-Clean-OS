# -*- coding: utf-8 -*-
"""小红书聚光（Juguang）API 对接点（Phase B 预留）。

用户在平台侧开通「企业蓝V + 聚光广告账户」后，把凭证填入环境变量即可激活自动归因，
自动回填 cost_metrics / channel_roi 的 Boosting 预算、消耗与私信线索（CTR-XHS-LEADS-P1-01 Phase B）。

凭证规则（安全硬约束）：
- 一律从环境变量读取（JUGUANG_*），绝不入库、绝不写入 Git、绝不写入任何配置文件。
- 未配置时所有查询返回 pending，不影响现有手动回填（KM-02 / /api/kos/manual）链路。
"""
import os
from typing import Optional

JUGUANG_ENV_KEYS = (
    "JUGUANG_CLIENT_ID",
    "JUGUANG_CLIENT_SECRET",
    "JUGUANG_ACCESS_TOKEN",
    "JUGUANG_ADVERTISER_ID",
)


def is_configured() -> bool:
    """聚光凭证是否已配置（client_id + access_token 为最小必需）。"""
    return bool(os.environ.get("JUGUANG_CLIENT_ID") and os.environ.get("JUGUANG_ACCESS_TOKEN"))


def get_config() -> dict:
    """返回当前聚光配置项（值一律不回显明文，仅返回是否已设置）。"""
    return {k: ("<set>" if os.environ.get(k) else "") for k in JUGUANG_ENV_KEYS}


def verify_config() -> dict:
    """校验聚光配置，返回缺失项。"""
    missing = [k for k in JUGUANG_ENV_KEYS if not os.environ.get(k)]
    return {
        "ok": not missing,
        "configured": not missing,
        "missing": missing,
        "note": "设置 JUGUANG_CLIENT_ID / JUGUANG_CLIENT_SECRET / JUGUANG_ACCESS_TOKEN / JUGUANG_ADVERTISER_ID 环境变量后激活",
    }


def query_boosting_metrics(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """聚光投放消耗/预算/转化数据（Boosting 归因）。

    Phase B TODO：调用聚光开放平台接口拉取「消耗、预算、点击、进线」，
    回填 kos_metrics.cost_metrics / channel_roi（替换手动回填层）。
    """
    if not is_configured():
        return {"status": "pending", "configured": False,
                "note": "聚光凭证未配置，请设置 JUGUANG_* 环境变量后激活自动归因", "data": None}
    return {"status": "not_implemented", "configured": True,
            "note": "Phase B：接入聚光开放平台接口（消耗/预算/点击/进线）", "data": None}


def query_leads(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """聚光私信线索/进线数据（Boosting 私信线索归因）。

    Phase B TODO：拉取私信线索，回填 inquiry / wecom_add（CTR-XHS-LEADS-P1-01 Phase B）。
    """
    if not is_configured():
        return {"status": "pending", "configured": False,
                "note": "聚光凭证未配置，请设置 JUGUANG_* 环境变量后激活私信线索归因", "data": None}
    return {"status": "not_implemented", "configured": True,
            "note": "Phase B：接入聚光私信线索 API", "data": None}
