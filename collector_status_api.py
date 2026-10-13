# -*- coding: utf-8 -*-
"""
采集器状态 API（Collector Status API）
======================================
GET /api/collector/status → 返回最近验证记录与当前认证元数据的分层状态。

状态定义（真实，禁止伪造）：
  - cookie_status=NEED_VERIFY 且 status_source=AUTH_METADATA：只表示发现认证元数据，尚未检查平台连通性；不表示平台返回了 challenge。
  - last_verified_status=NEED_VERIFY 且 status_source=VERIFICATION_CACHE：带 last_check 时间的历史平台验证结果（例如平台 challenge）；当前 cookie_status 仍为 UNKNOWN。
  - ACTIVE / VERIFIED / PARTIAL / EXPIRED / BLOCKED 等缓存值：仅作带时间戳的上次验证结果，不表示当前可用。
  - acquisition plan 的 READY/STAGED/BLOCKED 是计划状态，不是本 API 的平台验证结果。
  - INVALID / MISSING：当前认证元数据检查结果。
  - UNKNOWN：身份范围或验证时效未绑定；不能声称当前连通或准备就绪。

返回字段：platform / cookie_status / last_check / records_parsed / error / http_status
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, jsonify

from lumenis.adapters.cookie_vault import check_cookie_status

logger = logging.getLogger(__name__)

collector_status_bp = Blueprint("collector_status", __name__)

# 平台清单（与 registry 对齐，含小红书主链路 + 搜狗微信/搜索等免登平台）
PLATFORMS = [
    "xiaohongshu", "weibo", "bilibili", "zhihu",
    "douyin", "x", "instagram", "jiguang",
    "sogou_wechat", "sogou_search",
    "baidu_search", "bing_search", "google",
    "smzdm", "dianping", "facebook",
]

# 平台显示名
PLATFORM_DISPLAY = {
    "xiaohongshu": "小红书", "weibo": "微博", "bilibili": "B站",
    "zhihu": "知乎", "douyin": "抖音", "x": "X/Twitter",
    "instagram": "Instagram", "jiguang": "极光",
    "sogou_wechat": "搜狗微信", "sogou_search": "搜狗搜索",
    "baidu_search": "百度搜索", "bing_search": "必应搜索",
    "google": "谷歌搜索",
    "smzdm": "什么值得买", "dianping": "大众点评", "facebook": "Facebook",
}

# 状态缓存文件（最近一次真实平台验证结果；不接受 acquisition-plan 状态）
_STATUS_CACHE = Path(__file__).resolve().parent / "data" / "collector_status_cache.json"

# These are platform-verification outcomes, not query-plan or worker lifecycle states.
# NEED_VERIFY is included because an actual verification may encounter a platform
# challenge. Its source/time remain separate from cookie metadata and current readiness.
_HISTORICAL_VERIFICATION_STATUSES = {
    "ACTIVE", "VERIFIED", "PARTIAL", "EXPIRED", "INVALID", "MISSING",
    "BLOCKED", "NEED_VERIFY",
}


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
    """Record a platform-verification outcome, not a query-plan readiness state.

    Args:
        platform: 平台名
        status: platform outcome such as ACTIVE/VERIFIED/PARTIAL/EXPIRED/
            INVALID/MISSING/BLOCKED/NEED_VERIFY. READY/STAGED are plan states
            and are not current platform verification.
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
    """Return current metadata separately from cached historical verification.

    A file-level auth Cookie is not a connectivity check. Cached observations
    retain their original timestamp/status, but remain UNKNOWN as a current
    state until an explicit freshness contract exists. The generic status
    route never reads the protected XHS profile or trusts an unscoped cache row.
    """
    cache = _load_cache()
    results = []
    for p in PLATFORMS:
        if p == "xiaohongshu":
            # No identity/scope binding exists in this generic legacy cache.
            # Never inspect or expose the Product Owner's local XHS identity.
            results.append({
                "platform": p,
                "display": PLATFORM_DISPLAY.get(p, p),
                "cookie_status": "UNKNOWN",
                "last_verified_status": None,
                "last_check": None,
                "records_parsed": None,
                "error": "approved identity scope is not verified by this status source",
                "http_status": None,
                "status_source": "IDENTITY_SCOPE_UNBOUND",
                "freshness": "NOT_CHECKED",
            })
            continue

        cached = cache.get(p)
        if isinstance(cached, dict):
            verified_status = cached.get("cookie_status")
            last_check = cached.get("last_check")
            if verified_status in _HISTORICAL_VERIFICATION_STATUSES \
                    and isinstance(last_check, str) and last_check.strip():
                # Do not expose arbitrary cached exception text: it may contain
                # URLs, identifiers, or credential fragments. The status value
                # itself is the safe reason code; freshness/source/time explain
                # its historical scope.
                cached_error = (
                    "historical platform verification required; current readiness is not established"
                    if verified_status == "NEED_VERIFY"
                    else "stored verification retained; current freshness is not established"
                )
                results.append({
                    "platform": p,
                    "display": PLATFORM_DISPLAY.get(p, p),
                    "cookie_status": "UNKNOWN",
                    "last_verified_status": verified_status,
                    # Compatibility field: for VERIFICATION_CACHE rows this is
                    # the original verification time, never this API read time.
                    "last_check": last_check,
                    "records_parsed": cached.get("records_parsed"),
                    "error": cached_error,
                    "http_status": cached.get("http_status"),
                    "status_source": "VERIFICATION_CACHE",
                    "freshness": "UNKNOWN",
                })
                continue

        # A generic cache entry is not trusted without a known verification
        # state and timestamp. Read only non-XHS Cookie metadata below.
        try:
            metadata = check_cookie_status(p)
        except Exception as exc:
            file_status = "UNKNOWN"
            error = f"auth metadata unavailable: {type(exc).__name__}"
        else:
            file_status = metadata.get("status")
            if file_status == "ACTIVE":
                file_status = "NEED_VERIFY"
                error = "auth-cookie metadata present; connectivity was not checked"
            elif file_status == "NO_AUTH":
                file_status = "INVALID"
                error = "no recognized auth cookie metadata"
            elif file_status == "MISSING":
                error = "cookie metadata missing"
            else:
                file_status = "UNKNOWN"
                error = "cookie metadata state is unknown"
        results.append({
            "platform": p,
            "display": PLATFORM_DISPLAY.get(p, p),
            "cookie_status": file_status,
            "last_verified_status": None,
            "last_check": None,
            "records_parsed": None,
            "error": error,
            "http_status": None,
            "status_source": "AUTH_METADATA",
            "freshness": "NOT_CHECKED",
        })

    last_verified = [r.get("last_verified_status") for r in results]
    last_verified_summary = {
        "active": sum(1 for s in last_verified if s in ("ACTIVE", "VERIFIED")),
        "partial": sum(1 for s in last_verified if s == "PARTIAL"),
        "expired": sum(1 for s in last_verified if s == "EXPIRED"),
        "invalid": sum(1 for s in last_verified if s == "INVALID"),
        "missing": sum(1 for s in last_verified if s == "MISSING"),
        "blocked": sum(1 for s in last_verified if s == "BLOCKED"),
        "need_verify": sum(1 for s in last_verified if s == "NEED_VERIFY"),
    }
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
            "need_verify": sum(1 for r in results if r["cookie_status"] == "NEED_VERIFY"),
            "unknown": sum(1 for r in results if r["cookie_status"] == "UNKNOWN"),
            "last_verified": last_verified_summary,
        },
    }


def get_collector_status_payload() -> dict:
    """Build the shared status payload used by both legacy GET registrations.

    Keep collector process lifecycle and per-platform auth/verification as
    separate named dimensions. The top-level runtime keys preserve the older
    collection_api response; ``data`` preserves the platform status contract.
    """
    import collector_automation

    runtime = collector_automation.get_collector_automation().get_status()
    platform_status = get_all_status()
    platform_status["collector_runtime"] = runtime
    return {
        "ok": True,
        **runtime,
        "success": True,
        "data": platform_status,
        "error": None,
    }


@collector_status_bp.route("/api/collector/status", methods=["GET"])
def collector_status():
    """GET status with one shared runtime + platform-status response contract."""
    try:
        return jsonify(get_collector_status_payload())
    except Exception as e:
        logger.exception("collector_status API 异常")
        return jsonify({"ok": False, "success": False, "data": None, "error": str(e)}), 500
