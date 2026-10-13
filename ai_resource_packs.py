# -*- coding: utf-8 -*-
"""Historical resource-pack accounting; no executable provider or paid-call route.

Retain original quota/usage metadata for inspection. Product inference uses the
current SYSTEM Gateway and its separate permission and selected-model contract.
"""
import os
import json
import time
import threading
from datetime import datetime, date
from typing import Dict, List, Optional, Any

# ZBC Phase 7: module status markers
MODULE_STATUS = 'DISABLED'
AI_ROLE = 'HISTORICAL_BUDGET_RECORD'  # retained usage history, never a product inference authority
RETIRED_EXECUTION_PROVIDER = 'zhipu'


def _retired_execution_result() -> Dict:
    """Block historical quota routes before quota mutation or Gateway dispatch."""
    return {
        'ok': False,
        'status': 'provider_disabled',
        'provider': RETIRED_EXECUTION_PROVIDER,
        'reason': 'RETIRED_PROVIDER_COMPATIBILITY_ONLY',
        'resource_consumed': False,
    }


# ============ 资源包配置 ============
RESOURCE_PACKS = {
    "glm_4_5_air": {
        "name": "GLM-4.5-Air",
        "type": "tokens",
        "total": 11915296,           # 1191万 tokens
        "daily_limit": 200000,        # 本周测试 20万/天
        "unit": "tokens",
        "description": "主力文本模型，用于摘要/关键词/分析/报告润色",
        "enabled": True,
    },
    "search_std": {
        "name": "Search-STD",
        "type": "calls",
        "total": 100,                 # 100次
        "daily_limit": None,          # 不按天限制，总量控制
        "unit": "次",
        "description": "搜索增强模型(100次)，用在刀刃上：案例库搜索增强、品牌知识库RAG、产品全局架构、层级关系优化、采集器智能检索",
        "enabled": True,
    },
    "per_call": {
        "enabled": True,
        "total": 100,                  # 20次
        "daily_limit": None,
        "unit": "次",
        "description": "高价值模型按次调用(20次)：2次预留用于采集ChatGPT/Codex编程设计功能、交互及学习能力、可进化板块-实时推进开发执行；其余18次按用户需求执行",
        "enabled": True,
        "reserved_for_learning": 5,   # 预留5次用于学习采集(ChatGPT/Codex编程/交互/可进化板块)
    },
    "glm_4_6v": {
        "name": "GLM-4.6V 视觉",
        "type": "tokens",
        "total": 6000000,             # 600万 tokens
        "daily_limit": None,
        "unit": "tokens",
        "description": "视觉多模态模型，效率优先不省用（一次分析到位），但不可滥用（不重复/无价值调用）",
        "enabled": True,
        "require_confirmation": False,  # 2026-09-04 用户取消每次确认；保留"不可滥用"使用纪律
    },
}

# 统计文件
STATS_FILE = os.environ.get(
    "ZBC_AI_RESOURCE_STATS_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ai_resource_packs_stats.json")
)

# 全局暂停状态
_paused = False
_pause_reason = ""
_lock = threading.Lock()


# ============ 统计管理 ============
def _ensure_dir():
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)


def _load_stats() -> Dict:
    _ensure_dir()
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"packs": {}, "pause": {"paused": False, "reason": "", "since": None}}


def _save_stats(stats: Dict):
    _ensure_dir()
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def _today_str() -> str:
    return date.today().isoformat()


def _get_pack_usage(pack_id: str) -> Dict:
    """获取资源包使用情况。"""
    stats = _load_stats()
    today = _today_str()
    pack_stats = stats.get("packs", {}).get(pack_id, {
        "total_used": 0,
        "daily_used": {},
        "last_used_at": None,
        "history": [],
    })
    daily_used = pack_stats.get("daily_used", {}).get(today, 0)
    return {
        "pack_id": pack_id,
        "config": RESOURCE_PACKS.get(pack_id, {}),
        "total_used": pack_stats.get("total_used", 0),
        "daily_used": daily_used,
        "today": today,
        "last_used_at": pack_stats.get("last_used_at"),
        "remaining": RESOURCE_PACKS.get(pack_id, {}).get("total", 0) - pack_stats.get("total_used", 0),
    }


def check_quota(pack_id: str, amount: int = 1) -> Dict:
    """
    检查资源包额度。
    返回: {allowed: bool, reason: str, usage: dict}
    """
    if _paused:
        return {"allowed": False, "reason": f"AI 连接已暂停: {_pause_reason}", "usage": None}

    pack = RESOURCE_PACKS.get(pack_id)
    if not pack:
        return {"allowed": False, "reason": f"未知资源包: {pack_id}", "usage": None}

    if not pack.get("enabled", True):
        return {"allowed": False, "reason": f"资源包已禁用: {pack['name']}", "usage": None}

    usage = _get_pack_usage(pack_id)

    # 检查总量
    if usage["remaining"] < amount:
        return {"allowed": False, "reason": f"资源包总量不足: 剩余{usage['remaining']}{pack['unit']}", "usage": usage}

    # 检查每日限额
    daily_limit = pack.get("daily_limit")
    if daily_limit and usage["daily_used"] + amount > daily_limit:
        return {"allowed": False, "reason": f"今日额度已用: {usage['daily_used']}/{daily_limit}{pack['unit']}", "usage": usage}

    return {"allowed": True, "reason": "ok", "usage": usage}


def record_usage(pack_id: str, amount: int = 1, endpoint: str = "", detail: str = ""):
    """记录资源包使用。"""
    with _lock:
        stats = _load_stats()
        today = _today_str()
        if "packs" not in stats:
            stats["packs"] = {}
        if pack_id not in stats["packs"]:
            stats["packs"][pack_id] = {"total_used": 0, "daily_used": {}, "last_used_at": None, "history": []}

        pack_stats = stats["packs"][pack_id]
        pack_stats["total_used"] += amount
        pack_stats["daily_used"][today] = pack_stats["daily_used"].get(today, 0) + amount
        pack_stats["last_used_at"] = datetime.now().isoformat()
        pack_stats["history"].append({
            "time": datetime.now().isoformat(),
            "amount": amount,
            "endpoint": endpoint,
            "detail": detail[:100] if detail else "",
        })
        # 只保留最近100条历史
        pack_stats["history"] = pack_stats["history"][-100:]
        _save_stats(stats)


# ============ 暂停/恢复 ============
def pause_connection(reason: str = "用户手动暂停"):
    """暂停 AI 连接。"""
    global _paused, _pause_reason
    with _lock:
        _paused = True
        _pause_reason = reason
        stats = _load_stats()
        stats["pause"] = {"paused": True, "reason": reason, "since": datetime.now().isoformat()}
        _save_stats(stats)
    return {"paused": True, "reason": reason}


def resume_connection():
    """Retired accounting cannot resume a model connection or consume quota."""
    return {**_retired_execution_result(), 'paused': True}


def is_paused() -> Dict:
    """检查是否暂停。"""
    return {"paused": _paused, "reason": _pause_reason}


# ============ 按次计费需求执行 ============
def execute_per_call_request(user_request: str, model: str | None = None) -> Dict:
    """Retain the old response contract without model dispatch or quota writes."""
    return _retired_execution_result()


# ============ 状态查询 ============
def get_all_packs_status() -> Dict:
    """获取所有资源包状态。"""
    result = {
        "paused": _paused,
        "pause_reason": _pause_reason,
        "execution": {
            "provider": RETIRED_EXECUTION_PROVIDER,
            "status": "provider_disabled",
            "resource_consumed": False,
        },
        "packs": {},
        "summary": {
            "total_packs": len(RESOURCE_PACKS),
            "enabled_packs": sum(1 for p in RESOURCE_PACKS.values() if p.get("enabled", True)),
        },
    }
    for pack_id in RESOURCE_PACKS:
        result["packs"][pack_id] = _get_pack_usage(pack_id)
    return result


def get_glm_4_5_air_status() -> Dict:
    """获取 glm-4.5-air 状态（用于小 icon 实时显示）。"""
    usage = _get_pack_usage("glm_4_5_air")
    daily_limit = RESOURCE_PACKS["glm_4_5_air"]["daily_limit"]
    daily_percent = (usage["daily_used"] / daily_limit * 100) if daily_limit else 0
    total_percent = (usage["total_used"] / RESOURCE_PACKS["glm_4_5_air"]["total"] * 100)
    return {
        "pack_id": "glm_4_5_air",
        "name": "GLM-4.5-Air",
        "daily_used": usage["daily_used"],
        "daily_limit": daily_limit,
        "daily_percent": round(daily_percent, 1),
        "total_used": usage["total_used"],
        "total_limit": RESOURCE_PACKS["glm_4_5_air"]["total"],
        "total_percent": round(total_percent, 1),
        "remaining": usage["remaining"],
        "paused": _paused,
        "status": "paused" if _paused else ("warning" if daily_percent >= 80 else "ok"),
    }


# 初始化时加载暂停状态
_stats_init = _load_stats()
if _stats_init.get("pause", {}).get("paused", False):
    _paused = True
    _pause_reason = _stats_init["pause"].get("reason", "")
