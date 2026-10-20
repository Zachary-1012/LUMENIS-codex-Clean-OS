# -*- coding: utf-8 -*-
"""
广州太古汇舆情系统：网络自适应检测模块

功能：
1. 自动检测IP风控（错误码300012）、验证码、captcha
2. 检测到风控时自动降低频率、提示切换网络
3. 记录网络健康状态到日志
4. 不把"抓不到数据"误判为"今天没有舆情"
5. 提供网络状态API供前端展示
"""
from __future__ import annotations
import json, os, time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE = Path(__file__).resolve().parent
HEALTH_LOG = BASE / "data" / "network_health.json"
CACHE_DIR = BASE / "data" / "cache"

# 风控关键词检测
RISK_KEYWORDS = [
    "300012", "verification_required", "captcha", "验证码",
    "安全验证", "challenge", "风控", "异常", "登录失效",
    "session expired", "too many requests", "429", "403"
]

# 网络状态枚举
class NetworkStatus:
    NORMAL = "normal"           # 正常
    DEGRADED = "degraded"       # 降级（部分功能受限）
    BLOCKED = "blocked"         # 被风控拦截
    OFFLINE = "offline"         # 完全离线

def _ensure_dirs():
    """确保目录存在"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _load_health() -> Dict:
    """加载网络健康记录"""
    _ensure_dirs()
    if HEALTH_LOG.exists():
        try:
            return json.loads(HEALTH_LOG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "current_status": NetworkStatus.NORMAL,
        "last_check": None,
        "last_successful_collection": None,
        "consecutive_failures": 0,
        "risk_events": [],
        "adaptive_settings": {
            "current_scroll_limit": 6,
            "current_delay_seconds": 2,
            "auto_reduced": False
        }
    }

def _save_health(data: Dict):
    """保存网络健康记录"""
    _ensure_dirs()
    HEALTH_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def detect_risk(response_text: str = "", error_msg: str = "", status_code: int = 0) -> Dict:
    """
    检测响应中是否包含风控信号
    
    返回：
    {
        "is_risk": bool,
        "risk_type": str,
        "matched_keyword": str,
        "severity": "low"|"medium"|"high"
    }
    """
    combined = f"{response_text} {error_msg}".lower()
    
    for keyword in RISK_KEYWORDS:
        if keyword.lower() in combined:
            severity = "high" if keyword in ["300012", "verification_required", "captcha", "403"] else "medium"
            return {
                "is_risk": True,
                "risk_type": keyword,
                "matched_keyword": keyword,
                "severity": severity
            }
    
    if status_code in [403, 429]:
        return {
            "is_risk": True,
            "risk_type": f"http_{status_code}",
            "matched_keyword": str(status_code),
            "severity": "high"
        }
    
    return {"is_risk": False, "risk_type": None, "matched_keyword": None, "severity": "low"}

def report_collection_result(success: bool, risk_info: Optional[Dict] = None, notes_count: int = 0,
                             state: Optional[str] = None):
    """
    报告一次采集结果，更新网络健康状态
    
    Args:
        success: 是否成功采集到数据
        risk_info: detect_risk()返回的风控信息
        notes_count: 采集到的笔记数量
        state: 采集六态；SUCCESS/EMPTY 表示获得有效响应，即使没有新增笔记
    """
    health = _load_health()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    now_ts = time.time()
    
    health["last_check"] = now
    
    result_state = state.strip().upper() if isinstance(state, str) else None
    blocked_states = {"BLOCKED", "CAPTCHA", "AUTH_FAILED"}
    is_risk = isinstance(risk_info, dict) and risk_info.get("is_risk") is True
    if result_state in blocked_states and not is_risk:
        risk_info = {"is_risk": True, "risk_type": result_state}
        is_risk = True

    if is_risk:
        # 风险信息独立于数据计数和聚合状态；一次任务只会经调用方汇总后记录一次。
        health["consecutive_failures"] += 1
        health["current_status"] = NetworkStatus.BLOCKED
        risk_type = risk_info.get("risk_type") or risk_info.get("type") or result_state or "unknown"
        event = {
            "time": now,
            "type": risk_type,
            "severity": risk_info.get("severity"),
            "consecutive": health["consecutive_failures"]
        }
        health["risk_events"].append(event)
        health["risk_events"] = health["risk_events"][-20:]
        health["adaptive_settings"]["current_scroll_limit"] = max(1, health["adaptive_settings"]["current_scroll_limit"] - 2)
        health["adaptive_settings"]["current_delay_seconds"] = min(30, health["adaptive_settings"]["current_delay_seconds"] + 3)
        health["adaptive_settings"]["auto_reduced"] = True
    elif result_state in {"SUCCESS", "EMPTY"} or (
            result_state is None and success and notes_count > 0):
        # 成功采集
        health["last_successful_collection"] = now
        health["consecutive_failures"] = 0
        health["current_status"] = NetworkStatus.NORMAL
        # 恢复自适应设置
        if health["adaptive_settings"]["auto_reduced"]:
            health["adaptive_settings"]["current_scroll_limit"] = 6
            health["adaptive_settings"]["current_delay_seconds"] = 2
            health["adaptive_settings"]["auto_reduced"] = False
    else:
        # 网络错误、部分失败及未知状态都按失败处理；没有显式六态不能冒充成功。
        health["consecutive_failures"] += 1
        if health["consecutive_failures"] >= 3:
            health["current_status"] = NetworkStatus.OFFLINE
        else:
            health["current_status"] = NetworkStatus.DEGRADED
    
    _save_health(health)
    return health

def get_network_status() -> Dict:
    """获取当前网络状态（供API调用）"""
    health = _load_health()
    return {
        "status": health["current_status"],
        "status_text": {
            NetworkStatus.NORMAL: "正常",
            NetworkStatus.DEGRADED: "降级运行",
            NetworkStatus.BLOCKED: "风控拦截",
            NetworkStatus.OFFLINE: "网络离线"
        }.get(health["current_status"], "未知"),
        "last_check": health["last_check"],
        "last_successful_collection": health["last_successful_collection"],
        "consecutive_failures": health["consecutive_failures"],
        "recent_risk_events": health["risk_events"][-5:],
        "adaptive_settings": health["adaptive_settings"],
        "recommendation": _get_recommendation(health)
    }

def _get_recommendation(health: Dict) -> str:
    """根据网络状态给出建议"""
    status = health["current_status"]
    if status == NetworkStatus.NORMAL:
        return "网络正常，可正常采集"
    elif status == NetworkStatus.DEGRADED:
        return "网络不稳定，已自动降低采集频率，建议检查网络连接"
    elif status == NetworkStatus.BLOCKED:
        consecutive = health["consecutive_failures"]
        if consecutive >= 3:
            return "检测到IP风控，建议：1) 切换5G热点 2) 等待15-30分钟 3) 检查账号登录状态"
        return "检测到风控信号，已自动降低频率，建议切换网络或稍后重试"
    elif status == NetworkStatus.OFFLINE:
        return "网络连接失败，系统将使用本地缓存数据，建议检查网络连接"
    return "未知状态"

def get_adaptive_settings() -> Dict:
    """获取当前自适应设置（供采集器调用）"""
    health = _load_health()
    return health["adaptive_settings"]

def should_use_cache() -> bool:
    """判断是否应该使用缓存数据（前端降级展示）"""
    health = _load_health()
    # 连续失败3次以上，或状态为blocked/offline时使用缓存
    return health["consecutive_failures"] >= 3 or health["current_status"] in [NetworkStatus.BLOCKED, NetworkStatus.OFFLINE]

def reset_network_status():
    """重置网络状态（用户手动切换网络后调用）"""
    health = _load_health()
    health["current_status"] = NetworkStatus.NORMAL
    health["consecutive_failures"] = 0
    health["adaptive_settings"] = {
        "current_scroll_limit": 6,
        "current_delay_seconds": 2,
        "auto_reduced": False
    }
    _save_health(health)
    return get_network_status()
