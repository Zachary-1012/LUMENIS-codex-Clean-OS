# -*- coding: utf-8 -*-
"""全局采集健康状态中心（只读聚合，不发起任何采集、不触网、不改业务口径）。

为「首页健康小点 + 系统内统一 Auth Modal」提供单一数据底座：
- 平台隔离：逐平台独立状态，小红书 300012/登录失效不会让其他平台显示异常；
- 三类分清：A 登录失效(弹码) / B 人机验证(人工) / C IP风控熔断(冷却)，绝不伪装成“0 条”；
- 未启用平台（抖音 SECONDARY、微博/B站等槽位）明确显示 DISABLED，而不是失败或 0 条；
- 动态调度：合并 PlatformSchedulePlanner 的 current_interval/cooldown/next_run/恢复进度，
  让前端能回答“为什么这一次没有采集”。

AI 不参与此处任何状态判定；状态只来自规则状态机、熔断、调度影子与真实采集日志。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .config import PLATFORM_CAPABILITIES
from .scheduling import get_planner
from .scheduling import state_map as sm

# 前端/Modal 用的非规范补充态
IDLE = "IDLE"          # 启用但今天尚无采集记录（待命），不是异常、不是 0 条
DISABLED = "DISABLED"  # 未启用扩展槽位

_PRIORITY_LABEL = {"primary": "主监测平台", "secondary": "第二重点", "event": "事件扩展槽位"}


def _xhs_runtime() -> Dict[str, Any]:
    """读取小红书实时运行态（熔断 + 最近批次 + 会话）。全部延迟 import、异常内聚，绝不抛出。"""
    out: Dict[str, Any] = {"circuit": {}, "last": None, "session_valid": None, "session_msg": ""}
    try:
        import xhs_cookie_bridge as bridge
        try:
            out["circuit"] = bridge.get_circuit_state() or {}
        except Exception:
            out["circuit"] = {}
        try:
            import database as _db
            with _db.get_db() as conn:
                row = conn.execute(
                    "SELECT status,notes_count,COALESCE(error_msg,''),finished_at "
                    "FROM collection_logs ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                out["last"] = {"state": row[0], "notes": row[1], "msg": row[2], "at": row[3]}
        except Exception:
            out["last"] = None
        # 会话有效性只看本地登录态是否齐备，不在这里触网校验，避免健康轮询本身产生请求
        try:
            ok, msg = bridge.verify_account()
            out["session_valid"] = bool(ok)
            out["session_msg"] = str(msg or "")
        except Exception:
            out["session_valid"] = None
    except Exception:
        pass
    return out


def build_platform_health(*, runtime_provider: Optional[Callable[[str], Dict[str, Any]]] = None,
                          planner=None) -> Dict[str, Any]:
    """聚合所有平台健康态。runtime_provider 仅用于单测注入，默认读真实本地运行态。"""
    planner = planner or get_planner()
    try:
        snap = planner.snapshot()
    except Exception:
        snap = {}
    platforms: List[Dict[str, Any]] = []
    counts = {"ok": 0, "idle": 0, "disabled": 0, "incident": 0, "needs_human": 0, "stop": 0}
    worst = None

    for key, cap in PLATFORM_CAPABILITIES.items():
        enabled = bool(cap.get("enabled"))
        item: Dict[str, Any] = {
            "platform": key,
            "name": cap.get("name", key),
            "enabled": enabled,
            "manual_collection_enabled": bool(cap.get("manual_collection_enabled", False)),
            "collection_mode": cap.get("collection_mode", "scheduled" if enabled else "disabled"),
            "product_owner": cap.get("product_owner", "CTH" if key == "xhs" else ""),
            "priority": cap.get("priority", "event"),
            "priority_label": _PRIORITY_LABEL.get(cap.get("priority", "event"), ""),
            "status": DISABLED,
            "triage": DISABLED,
            "needs_human": False,
            "stop_request": False,
            "session_valid": None,
            "risk_status": "",
            "cooldown_until": None,
            "next_run_at": None,
            "current_interval_sec": None,
            "recovery": None,
            "last": None,
            "verification_required": False,
            "message": "未启用扩展槽位" if not enabled else "待命中",
        }

        if not enabled and item["manual_collection_enabled"]:
            # Background scheduling stays fail-closed, while the product can
            # expose an explicit human-triggered read-only collection action.
            item["message"] = "已开放人工触发的只读采集；后台调度仍关闭"

        if not enabled:
            counts["disabled"] += 1
            item["enable_gate"] = cap.get("enable_gate", "")
            platforms.append(item)
            continue

        # 启用平台（当前为 xhs）：合并实时运行态 + 动态调度状态
        rt = runtime_provider(key) if runtime_provider else _xhs_runtime()
        circ = rt.get("circuit", {}) or {}
        last = rt.get("last")
        item["session_valid"] = rt.get("session_valid")
        item["last"] = last

        # 动态调度影子状态（冷却/恢复/下一次/间隔）
        st = snap.get(key, {}) or {}
        item["current_interval_sec"] = st.get("current_interval")
        item["cooldown_until"] = st.get("cooldown_until")
        item["next_run_at"] = st.get("next_run_at")
        item["risk_status"] = st.get("risk_status", "") or ("CIRCUIT_OPEN" if circ.get("open") else "")
        item["recovery"] = {k: st.get(k) for k in
                            ("recovery_stage", "recovery_success_streak", "consecutive_no_new",
                             "consecutive_network_fail") if k in st}
        item["verification_required"] = bool(st.get("paused_for_human", False))

        # 规范态判定：熔断优先，其次最近批次，再无则 IDLE
        if circ.get("open"):
            canon = sm.CS.COOLING_DOWN if circ.get("state") != "auth" else sm.CS.SESSION_EXPIRED
        elif last:
            canon = sm.to_canonical(last.get("state"), items=last.get("notes"))
        elif item["session_valid"] is False:
            canon = sm.CS.SESSION_EXPIRED
        else:
            canon = IDLE

        item["status"] = canon
        if canon == IDLE:
            item["triage"] = IDLE
            counts["idle"] += 1
        else:
            item["triage"] = sm.incident_class(canon)
            item["needs_human"] = sm.needs_human(canon)
            item["stop_request"] = sm.is_stop_request(canon)
            if sm.is_ok(canon):
                counts["ok"] += 1
            else:
                counts["incident"] += 1
                if item["needs_human"]:
                    counts["needs_human"] += 1
                if item["stop_request"]:
                    counts["stop"] += 1
        item["message"] = _message(item, circ, last)
        platforms.append(item)

        # 汇总 worst（需人工 > 停请求 > 风险 > 空闲 > 正常）
        worst = _escalate(worst, canon)

    needs_attention = counts["incident"] > 0
    if needs_attention:
        overall = worst
    elif counts["ok"]:
        overall = "OK"
    elif counts["idle"]:
        overall = IDLE
    else:
        overall = DISABLED
    return {
        "ok": True,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall": overall,
        "needs_attention": needs_attention,
        "needs_human": counts["needs_human"] > 0,
        "counts": counts,
        "platforms": platforms,
    }


def _message(item: Dict[str, Any], circ: Dict[str, Any], last: Optional[Dict[str, Any]]) -> str:
    st = item["status"]
    if st == IDLE:
        return "已启用，今日尚无采集记录（待命，非异常）"
    if sm.is_ok(st):
        if st == sm.CS.NO_NEW_DATA:
            return "接口正常，本批暂无新笔记（不是被拦截的 0 条）"
        return "采集正常"
    if st == sm.CS.SESSION_EXPIRED:
        return "登录态失效，需要重新登录（系统内统一 Auth 入口，不跳转外部登录页）"
    if st == sm.CS.NEED_VERIFY:
        return "触发人机/安全验证，已暂停请求，等待合法人工验证，不绕过"
    if st in (sm.CS.BLOCKED, sm.CS.COOLING_DOWN):
        until = item.get("cooldown_until") or circ.get("resume_at") or ""
        return f"平台风控/熔断冷却中，已停止危险请求{('，恢复于 ' + str(until)) if until else ''}"
    if st == sm.CS.NETWORK_ERROR:
        return "网络异常，按退避策略重试，恢复后小流量试运行"
    if st == sm.CS.RISK_WARNING:
        return "出现轻度风险信号（如部分关键词受限），已自动降低频率"
    if st == sm.CS.COLLECT_ERROR:
        return f"采集出错：{(last or {}).get('msg') or '未知错误'}"
    return str(st)


_RANK = {
    sm.CS.SESSION_EXPIRED: 5, sm.CS.NEED_VERIFY: 5, sm.CS.BLOCKED: 4, sm.CS.COOLING_DOWN: 4,
    sm.CS.NETWORK_ERROR: 3, sm.CS.COLLECT_ERROR: 3, sm.CS.RISK_WARNING: 2,
    IDLE: 1, sm.CS.SUCCESS: 0, sm.CS.NO_NEW_DATA: 0, DISABLED: -1,
}


def _escalate(cur: str, nxt: str) -> str:
    return nxt if _RANK.get(nxt, 0) > _RANK.get(cur, -9) else cur
