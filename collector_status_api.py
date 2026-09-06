# -*- coding: utf-8 -*-
"""
采集器状态 API（Collector Status API）
======================================
GET /api/collector/status → 返回各平台真实连通状态。

状态定义（真实，禁止伪造）：
  - ACTIVE   : cookie 有效且最近一次搜索/解析成功
  - VERIFIED : 同 ACTIVE，用于明确"真连通验证通过"
  - PARTIAL  : cookie 有效但部分功能受限（如风控/搜索空/详情失败）
  - EXPIRED  : cookie 过期/登录态失效
  - INVALID  : cookie 文件存在但无关键认证 cookie
  - MISSING  : cookie 文件不存在
  - BLOCKED  : 平台反爬/网络不通/外部限制导致无法连通

返回字段：platform / cookie_status / last_check / records_parsed / error / http_status
"""
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, jsonify

from v4_upgrade.adapters.cookie_vault import check_cookie_status, load_cookies

logger = logging.getLogger(__name__)

collector_status_bp = Blueprint("collector_status", __name__)

# 平台清单（与 registry 对齐，含小红书主链路 + 搜狗微信/搜索等免登平台）
PLATFORMS = [
    "xiaohongshu", "weibo", "bilibili", "zhihu",
    "douyin", "x", "instagram", "jiguang",
    "sogou_wechat", "sogou_search",
    "baidu_search", "bing_search", "google", "doubao_search",
    "smzdm", "dianping", "facebook",
]

# 平台显示名
PLATFORM_DISPLAY = {
    "xiaohongshu": "小红书", "weibo": "微博", "bilibili": "B站",
    "zhihu": "知乎", "douyin": "抖音", "x": "X/Twitter",
    "instagram": "Instagram", "jiguang": "极光",
    "sogou_wechat": "搜狗微信", "sogou_search": "搜狗搜索",
    "baidu_search": "百度搜索", "bing_search": "必应搜索",
    "google": "谷歌搜索", "doubao_search": "豆包搜索",
    "smzdm": "什么值得买", "dianping": "大众点评", "facebook": "Facebook",
}

# 状态缓存文件（最近一次真实验证结果）
_STATUS_CACHE = Path(__file__).resolve().parent / "data" / "collector_status_cache.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_cache() -> dict:
    """加载最近一次验证缓存；不存在返回空 dict。"""
    try:
        if _STATUS_CACHE.exists():
            return json.loads(_STATUS_CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    """保存验证缓存。"""
    try:
        _STATUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _STATUS_CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("保存 collector_status 缓存失败: %s", e)


def update_platform_status(platform: str, status: str, records_parsed: int = 0,
                           error: str = "", http_status: int = None):
    """更新单个平台验证状态（由验证脚本/采集器调用）。

    Args:
        platform: 平台名
        status: ACTIVE/VERIFIED/PARTIAL/EXPIRED/INVALID/MISSING/BLOCKED
        records_parsed: 解析到的记录数
        error: 错误信息（如有）
        http_status: HTTP 状态码（如有）
    """
    cache = _load_cache()
    cache[platform] = {
        "platform": platform,
        "display": PLATFORM_DISPLAY.get(platform, platform),
        "cookie_status": status,
        "last_check": _now_iso(),
        "records_parsed": records_parsed,
        "error": error or "",
        "http_status": http_status,
    }
    _save_cache(cache)


def get_all_status() -> dict:
    """获取所有平台状态（合并 cookie 文件级状态 + 最近一次验证缓存）。

    优先级：验证缓存（真连通结果） > cookie 文件级状态（ACTIVE/MISSING/NO_AUTH）。
    """
    cache = _load_cache()
    results = []
    for p in PLATFORMS:
        if p in cache:
            # 有真实验证缓存，直接使用
            results.append(cache[p])
        else:
            # 无验证缓存，返回 cookie 文件级状态（未做真连通验证）
            cs = check_cookie_status(p)
            file_status = cs["status"]  # ACTIVE / MISSING / NO_AUTH
            results.append({
                "platform": p,
                "display": PLATFORM_DISPLAY.get(p, p),
                "cookie_status": file_status if file_status != "NO_AUTH" else "INVALID",
                "last_check": _now_iso(),
                "records_parsed": 0,
                "error": "未执行真连通验证" if file_status == "ACTIVE" else
                         ("cookie 文件不存在" if file_status == "MISSING" else "无关键认证 cookie"),
                "http_status": None,
            })
    return {
        "timestamp": _now_iso(),
        "total_platforms": len(PLATFORMS),
        "platforms": results,
        "summary": {
            "active": sum(1 for r in results if r["cookie_status"] in ("ACTIVE", "VERIFIED")),
            "partial": sum(1 for r in results if r["cookie_status"] == "PARTIAL"),
            "expired": sum(1 for r in results if r["cookie_status"] == "EXPIRED"),
            "invalid": sum(1 for r in results if r["cookie_status"] == "INVALID"),
            "missing": sum(1 for r in results if r["cookie_status"] == "MISSING"),
            "blocked": sum(1 for r in results if r["cookie_status"] == "BLOCKED"),
        },
    }


@collector_status_bp.route("/api/collector/status", methods=["GET"])
def collector_status():
    """GET /api/collector/status → 各平台连通状态（统一信封 success/data/error）。"""
    try:
        data = get_all_status()
        return jsonify({"success": True, "data": data, "error": None})
    except Exception as e:
        logger.exception("collector_status API 异常")
        return jsonify({"success": False, "data": None, "error": str(e)}), 500
