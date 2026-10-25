"""序境 / LUMENIS — shared Flutter Experience ViewModel/API runtime.

本模块是 Flutter App 使用的 JSON transport 与只读 ViewModel 聚合层。
它不托管 Jinja、static、浏览器原型或第二套网页 Experience；所有真实数据、
Evidence、Canonical Data、Permission、Evaluation 与 Learning 仍由既有 canonical
owners 提供。本模块只负责把这些事实以受约束的 API contract 暴露给 App。
"""
from __future__ import annotations

import datetime as _dt
from contextlib import contextmanager
import hashlib
import tempfile
from urllib.parse import urlsplit
import os
import json
import re
import threading
import traceback as _tb
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request, send_file

# ---------------------------------------------------------------------------
# 路径与蓝图
# ---------------------------------------------------------------------------
experience_bp = Blueprint("experience_runtime", __name__)

# 已完成真实后端绑定的屏幕（其余屏幕由前端保持原型，服务端明确返回 bound=False）
BOUND_SCREENS = ("CTH-01", "AI-01")

# 13 态中，section 描述符使用的状态别名（与 assets/sections.js stateKind 对齐）
STATE_READY = "ready"
STATE_NOT_COLLECTED = "notcollected"   # 后端无该数据源（需外部依赖）
STATE_EMPTY = "empty"                  # 数据源存在但当前无记录
STATE_OFFLINE = "offline"              # 依赖运行时不可用
STATE_ERROR = "error"

# ---------------------------------------------------------------------------
# P0-WRITEPERM-02：AI composer 写权限边界（标准 lumenis.system.security.PermissionGate）
#
# 执行任何 skill 前先过统一权限门，deny-by-default，四态：
#   granted          -> 权限通过，进入执行链
#   pending_approval -> 权限等级够但高风险缺人工审批令牌（不执行、不写证据，HTTP 200 等审批）
#   denied           -> 权限不足/未注册/跨域（不执行、不写证据，HTTP 403）
#   permanent_deny   -> AI composer 边界永不放行的操作类别（发布/上线/删除，HTTP 403）
# denied / pending 路径在到达 run_execution_chain 之前就返回，因此不会产生任何证据写入。
# ---------------------------------------------------------------------------
#: AI composer（派生增强层）永久拒绝的动作：不允许直接发布/上线/推送/删除。
PERMANENT_DENY_ACTIONS = frozenset({"PUSH"})


def _action_gate_spec(action_value: str):
    """skill ActionType -> (lumenis.system.security.OperationType, RiskLevel)。

    未注册动作返回 None，由调用方 fail-closed 拒绝。只读/分析低风险自动放行；
    导出为中风险（VERIFY 权限）；写/提交为高风险，需要对应权限等级 + 人工审批。
    """
    from lumenis.system.security import OperationType, RiskLevel
    mapping = {
        "READ": (OperationType.AI_CALL, RiskLevel.LOW),
        "ANALYZE": (OperationType.AI_CALL, RiskLevel.LOW),
        "SUGGEST": (OperationType.AI_CALL, RiskLevel.LOW),
        "EXPORT": (OperationType.DATA_EXPORT, RiskLevel.MEDIUM),
        "WRITE": (OperationType.DB_WRITE, RiskLevel.HIGH),
        "COMMIT": (OperationType.CONFIG_MODIFY, RiskLevel.HIGH),
    }
    return mapping.get(action_value)


_perm_gate_singleton = None


def get_permission_gate():
    """AI composer 边界复用的标准权限门单例（deny-by-default，caller 固定为本模块）。"""
    global _perm_gate_singleton
    if _perm_gate_singleton is None:
        from lumenis.system.security import PermissionGate
        _perm_gate_singleton = PermissionGate(caller="experience_runtime.ai_intent")
    return _perm_gate_singleton


# ---------------------------------------------------------------------------
# 安全读取工具：任何后端调用都不允许抛出到路由外，失败转诚实状态
# ---------------------------------------------------------------------------
def _safe(fn, *args, default=None, **kwargs):
    """运行一个只读后端读取，异常时返回 default，绝不向上抛（不造假、只降级）。"""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - 聚合层需要把任意依赖故障转成状态
        return default if default is not None else {"__error__": str(exc)}


def _is_err(v: Any) -> bool:
    return isinstance(v, dict) and "__error__" in v


def today_str() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d")


def days_labels_series(days: int = 14) -> Tuple[List[str], List[Any], List[Any]]:
    """真实近 N 日负面/高风险序列；缺数保持 None，真实 0 保持 0。"""
    import database as db

    labels: List[str] = []
    neg: List[Any] = []
    high: List[Any] = []
    today = _dt.date.today()
    for back in range(days - 1, -1, -1):
        d = today - _dt.timedelta(days=back)
        ds = d.strftime("%Y-%m-%d")
        st = _safe(db.get_stats_by_date_range, ds, ds, default=None)
        labels.append(d.strftime("%m-%d"))
        if isinstance(st, dict) and not _is_err(st):
            neg.append(int(st["negative"]) if st.get("negative") is not None else None)
            high.append(int(st["high_risk"]) if st.get("high_risk") is not None else None)
        else:
            neg.append(None)
            high.append(None)
    return labels, neg, high


def metric(mid: str, label: str, *, value: Any = None, unit: str = "",
           state: str = STATE_READY, icon: str = "trend", decimals: int = 0,
           delta: Any = None, delta_unit: str = "%", spark: Optional[List[float]] = None,
           source: str = "", fresh: str = "live", note: str = "",
           evidence_id: str = "") -> Dict[str, Any]:
    """构造与 sections.js kpis 渲染器同构的单个指标。

    value=None + state!=ready 时前端渲染诚实占位（—），不显示伪造数值。
    """
    return {
        "id": mid,
        "label": label,
        "value": value,
        "unit": unit,
        "decimals": decimals,
        "icon": icon,
        "delta": delta,
        "deltaUnit": delta_unit,
        "spark": spark,
        "source": source,
        "fresh": fresh if state == STATE_READY else "na",
        "state": state,
        "stateNote": note,
        "evidenceId": evidence_id,
    }


def section(stype: str, state: str = STATE_READY, **kw) -> Dict[str, Any]:
    d = {"type": stype, "state": state}
    d.update(kw)
    return d


def shared_skill_surface(surface: str = "AI") -> Dict[str, Any]:
    """One shared tool surface consumed by AI-01 and SH-01.

    The catalog itself is fetched at runtime so the UI can show real binding
    state.  This section only establishes the product placement; it does not
    embed fixture outputs or claim that an optional tool is ready.
    """
    title = "Shared Content & Creation" if surface == "STUDIO" else "把能力带入任务"
    desc = (
        "六个研究/创作工具共享同一套 Content Studio 执行链；选择工具只生成受控的本地草案，"
        "不离开序境、不直接发布。"
        if surface == "STUDIO"
        else "从当前主体/品牌上下文调用共享能力；每次运行都会标记输入范围、权限、Evidence 与状态。"
    )
    html = (
        '<section class="lum-shared-skill-field" data-shared-skill-surface="'
        + surface
        + '" data-reveal>'
        '<div class="lum-shared-skill-field__head">'
        '<div><span class="lum-eyebrow">Shared Capability · Content Studio</span>'
        '<h2 class="lum-h4" style="margin-top:6px">'
        + title
        + '</h2><p class="lum-caption" style="margin-top:5px">'
        + desc
        + '</p></div>'
        '<span class="lum-chip lum-mono">CTH ↔ BMP · local-first</span></div>'
        '<div data-shared-skill-palette class="lum-shared-skill-palette" aria-live="polite">'
        '<span class="lum-caption">正在读取本地能力注册表…</span></div>'
        '<p class="lum-caption lum-shared-skill-field__boundary">'
        'AI 只做增强；原始 Evidence、Canonical Data、权限与人工审批仍由序境持有。'
        '</p></section>'
    )
    return section("raw", STATE_READY, html=html)


# ===========================================================================
# 运行时身份 / 主体（只读，不泄露安全内部）
# ===========================================================================
@experience_bp.route("/api/runtime/identity")
@experience_bp.route("/api/experience/runtime/identity")
def runtime_identity():
    """P0-RT-01：前端运行时身份。返回应用/数据库身份、域、运行时健康，全部真实、无密钥。"""
    import database as db

    identity: Dict[str, Any] = {
        "ok": True,
        "app": "LUMENIS Experience Runtime",
        "api": "experience_runtime.v1",
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    # 数据库身份：只给文件名与是否存在/大小，不暴露绝对路径
    try:
        db_exists = os.path.exists(db.DB_PATH)
        identity["database"] = {
            "resolved": bool(os.environ.get("ZBC_DB_PATH")),
            "name": os.path.basename(db.DB_PATH),
            "exists": db_exists,
            "isolated_by_env": "ZBC_DB_PATH" if os.environ.get("ZBC_DB_PATH") else "default",
        }
    except Exception as exc:  # noqa: BLE001
        identity["database"] = {"exists": False, "error": str(exc)}

    # Runtime identity owns process/database health only. Workspace focus is
    # selected through /api/settings/context. Never project the legacy
    # Guangzhou reference Subject (or any other Subject) as the product default.
    identity["context"] = {
        "mode": "GLOBAL_ALL",
        "domain_id": None,
        "subject_id": None,
        "brand_focus_id": None,
        "resource_type": "GLOBAL",
        "selection_authority": "/api/settings/context",
    }
    identity["subject"] = None
    identity["domain"] = None

    # 运行时守护者健康（真实，失败诚实降级）
    try:
        import runtime_guardian as rg

        hc = _safe(rg.legacy_health_check, default={})
        identity["runtime_guardian"] = {
            "overall": hc.get("overall") if isinstance(hc, dict) else "unknown",
            "workers": hc.get("workers") if isinstance(hc, dict) else None,
        }
    except Exception as exc:  # noqa: BLE001
        identity["runtime_guardian"] = {"overall": "unavailable", "error": str(exc)}
    return jsonify(identity)


@experience_bp.route("/api/experience/subjects")
def runtime_subjects():
    """当前主体、可用域与通用主体注册表（真实运行数据）。

    注册表只提供可选工作上下文，不切换当前生产主体，也不改变 CTH/BMP
    原有规则；没有登记数据时返回空数组，不用 fixture 冒充生产主体。
    """
    try:
        from subject_registry import list_subjects

        return jsonify({
            "ok": True,
            "current": None,
            "product": None,
            "context": {"mode": "GLOBAL_ALL", "domain_id": None,
                        "subject_id": None, "brand_focus_id": None,
                        "resource_type": "GLOBAL"},
            "domains": [
                {"id": "CTH", "name": "商业运营"},
                {"id": "BMP", "name": "品牌市场"},
            ],
            "subjects": list_subjects(),
            "selection_only": True,
        })
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


# ===========================================================================
# CTH-01 商业运营总览 —— 真实绑定
# ===========================================================================
def _build_cth01(*, binding: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    import database as db
    from lumenis.shared.reporting import daily as daily_reporting
    from canonical_metrics import sentiment_count, risk_count

    if (not isinstance(binding, dict)
            or binding.get("contract") != "lumenis.scope-read-binding.v1"
            or binding.get("scope_verified") is not True
            or binding.get("read_allowed") is not True):
        raise ValueError("CTH_SCOPE_BINDING_REQUIRED")
    mode = binding.get("canonical_scope")
    if mode not in {"GLOBAL_ALL", "FOCUS"}:
        raise ValueError("CTH_SCOPE_BINDING_INVALID")
    scope = db._normalize_event_scope({
        "domain_id": "cth", "product_id": "CTH",
        "subject_id": binding.get("subject_id") if mode == "FOCUS" else None,
        "brand_focus_id": None, "global_scope": mode == "GLOBAL_ALL",
    }, allow_global=True)

    blocked: List[Dict[str, str]] = []
    truth: Dict[str, Any] = {}
    # 前端风险枚举：后端 medium -> 前端 med
    _LV = {"high": "high", "medium": "med", "low": "low", "critical": "critical"}

    source_read = _safe(db.get_scoped_event_source_rows, scope, source_types=("note",),
                        limit=5000, default=None)
    stats_err = _is_err(source_read) or not isinstance(source_read, dict)
    scoped_notes = [] if stats_err else source_read.get("sources", [])
    source_complete = (not stats_err and not source_read.get("truncated")
                       and not source_read.get("rejected_count"))
    if source_complete:
        sentiment = sentiment_count(scoped_notes)
        risks = risk_count(scoped_notes)
        stats = {
            "total": len(scoped_notes),
            "positive": sentiment["positive"] if sentiment["known"] == sentiment["total"] else None,
            "neutral": sentiment["neutral"] if sentiment["known"] == sentiment["total"] else None,
            "negative": sentiment["negative"] if sentiment["known"] == sentiment["total"] else None,
            "high_risk": risks["high"] if not risks["missing"] and not risks["other"] else None,
            "medium_risk": risks["medium"] if not risks["missing"] and not risks["other"] else None,
            "low_risk": risks["low"] if not risks["missing"] and not risks["other"] else None,
        }
    else:
        stats = {key: None for key in ("total", "positive", "neutral", "negative",
                                       "high_risk", "medium_risk", "low_risk")}
    canonical = _safe(daily_reporting.generate_today_summary, today_str(), scope=scope, default={})
    canon_err = _is_err(canonical)
    events_read = _safe(db.get_scoped_events, 6, scope=scope, include_sources=True, default=None)
    events_err = _is_err(events_read) or not isinstance(events_read, dict)
    events = [] if events_err else events_read.get("events", [])
    active_events_read = _safe(
        db.get_scoped_events, 500, scope=scope, status="active", default=None,
    )
    active_events_err = _is_err(active_events_read) or not isinstance(active_events_read, dict)
    risk_notes = sorted(
        (note for note in scoped_notes if str(note.get("risk_level") or "").lower() in {"high", "critical"}),
        key=lambda note: (note.get("risk_score") is not None, note.get("risk_score") or 0),
        reverse=True,
    )

    # ---- KPI：真实可绑 vs 外部缺失（绝不填 0） ----
    neg = stats.get("negative") if isinstance(stats, dict) else None
    open_events = (
        len(active_events_read.get("events", []))
        if (not active_events_err and not active_events_read.get("truncated")
            and not active_events_read.get("rejected_count")) else None
    )
    kpis = [
        metric("cth.footfall", "今日到店客流", value=None, state=STATE_NOT_COLLECTED,
               icon="trend",
               note="需 POS/客流外部数据源，当前生产库无此口径",
               source="BLOCKED: external POS required"),
        metric("cth.member_sales", "会员销售占比", value=None, unit="%", state=STATE_NOT_COLLECTED,
               icon="trend",
               note="需销售/会员外部数据源，当前生产库无此口径",
               source="BLOCKED: external sales required"),
        metric("cth.negative_voice", "在线负面声量",
               value=None if stats_err or neg is None else neg,
               state=STATE_READY if not stats_err and neg is not None else STATE_OFFLINE,
               icon="risk", source="已核验来源记录的主体范围汇总",
               evidence_id="FUNC-SENTIMENT", fresh="live"),
        metric("cth.open_events", "在办事件",
               value=open_events,
                state=STATE_READY if open_events is not None else STATE_OFFLINE,
                icon="event", source=("已核验来源 Evidence 的在办事件完整计数"
                                      if open_events is not None else
                                      "在办事件总数不完整或不可用，当前仅展示预览"),
               evidence_id="EVENT-GRAPH", fresh="live"),
    ]
    for m in kpis:
        if m["state"] == STATE_NOT_COLLECTED:
            blocked.append({"field": m["id"], "reason": "BLOCKED_BY_EXTERNAL_DEPENDENCY",
                            "required": m["stateNote"]})
    truth["stats"] = None if stats_err else {k: stats.get(k) for k in
                  ("total", "positive", "neutral", "negative", "high_risk", "medium_risk", "low_risk")}
    truth["canonical"] = None if canon_err else {
        "risk_index": canonical.get("risk_index"),
        "brand_health_score": canonical.get("brand_health_score"),
        "risk_count": canonical.get("risk_count"),
        "events_count": canonical.get("events_count"),
        "collection_health": canonical.get("collection_health"),
        "lineage": "lumenis.shared.reporting.daily.generate_today_summary / FUNC-RISK-01/02",
    }

    # ---- 主区：真实 14 日负面/高风险趋势（替换无数据源的客流销售趋势） ----
    end_day = _dt.date.today()
    start_day = end_day - _dt.timedelta(days=13)
    trend_read = _safe(db.get_scoped_event_source_rows, scope, source_types=("note",),
                       date_start=start_day.isoformat(), date_end=end_day.isoformat(),
                       limit=5000, default=None)
    trend_rows = [] if _is_err(trend_read) or not isinstance(trend_read, dict) else trend_read.get("sources", [])
    trend_complete = (isinstance(trend_read, dict) and not trend_read.get("truncated")
                      and not trend_read.get("rejected_count"))
    labels, neg_series, high_series = [], [], []
    for back in range(13, -1, -1):
        day = end_day - _dt.timedelta(days=back)
        day_text = day.isoformat()
        labels.append(day.strftime("%m-%d"))
        day_rows = [row for row in trend_rows
                    if str(row.get("publish_date") or row.get("publish_datetime") or "")[:10] == day_text]
        if not trend_complete:
            neg_series.append(None)
            high_series.append(None)
            continue
        if not day_rows:
            # Zero means no records in this completely read, authorized sample;
            # it does not claim that the platform had no business activity.
            neg_series.append(0)
            high_series.append(0)
            continue
        day_sentiment = sentiment_count(day_rows)
        day_risk = risk_count(day_rows)
        neg_series.append(day_sentiment["negative"] if day_sentiment["known"] == day_sentiment["total"] else None)
        high_series.append(day_risk["high"] if not day_risk["missing"] and not day_risk["other"] else None)
    trend = section("chart", STATE_READY if isinstance(trend_read, dict) and not _is_err(trend_read) else STATE_OFFLINE,
                    kind="line", title="近 14 日负面声量 / 高风险",
                    sub="仅统计当前授权主体的已核验样本；完整读取且无样本为0，覆盖不完整或分类未知显示未知（—）",
                    series=[
                        {"name": "负面", "data": neg_series, "color": "var(--lum-c-danger,#c0563f)"},
                        {"name": "高风险", "data": high_series, "color": "var(--lum-c-info,#4FC4E8)"},
                    ], labels=labels,
                    legend=[{"label": "负面", "color": "var(--lum-c-danger,#c0563f)"},
                            {"label": "高风险", "color": "var(--lum-c-info,#4FC4E8)"}])

    # ---- 事件：真实高风险/事件 ----
    ev_items = []
    if not events_err:
        for e in events[:3]:
            ev_items.append({
                "time": (e.get("event_date") or e.get("last_seen") or "")[5:16] or "—",
                "date": (e.get("first_seen") or "")[:10],
                "title": e.get("title", "未命名事件"),
                "desc": (e.get("summary") or "")[:120],
                "level": _LV.get((e.get("risk_level") or "low"), "low"),
                "tags": [f"提及 {e.get('mention_count', 0)}", f"来源平台 {e.get('source_count', 1)}"],
                "evidence": f"EV:{e.get('event_id') or e.get('id') or 'UNKNOWN'}",
            })
    events_sec = section("events", STATE_READY if ev_items else STATE_EMPTY,
                         title="重点事件", more=True, items=ev_items)

    # ---- 证据链：只呈现已通过 scoped event/source 核验的引用 ----
    ev_rail = []
    for event in events[:2] if not events_err else []:
        for source in event.get("sources", [])[:1]:
            ev_rail.append({
                "kind": "source",
                "id": f"SRC:{source.get('source_id') or 'UNKNOWN'}",
                "chain": ["Source", "Evidence", "Canonical", "Event"],
                "quote": str(event.get("title") or "已核验来源")[:140],
                "time": str(source.get("published_at") or source.get("publish_date") or "")[:16],
                "source": str(source.get("source_platform") or source.get("source_type") or "source"),
                "conf": None,
            })
    evidence_sec = section("evidence", STATE_READY if ev_rail else STATE_EMPTY,
                           title="证据链", items=ev_rail)

    # ---- 侧栏：Canonical 事实型洞察（非 AI 结论，确定性，标注 lineage） ----
    if not canon_err and (canonical.get("risk_index") is not None):
        ri = canonical.get("risk_index"); bh = canonical.get("brand_health_score")
        insight_sec = section("insight", STATE_READY, kind="Canonical",
                              text=f"当前风险指数 {ri}，品牌健康分 {bh}；"
                                   f"在办风险 {canonical.get('risk_count')} 条。该结论为确定性指标聚合，非 AI 生成。",
                              why="数据来自 UDIP 统一指标管线，页面不重算指标。",
                              evidence=["MET-RISK-01", "MET-RISK-02"],
                              actions=[{"label": "生成运营简报", "variant": "secondary", "size": "sm",
                                        "id": "draft-brief", "cls": "DRAFT", "scope": "subject:current",
                                        "target": "report", "permission": "report:write", "ico": "report"}])
    else:
        insight_sec = section("insight", STATE_OFFLINE, kind="Canonical", text="",
                              stateActions=[])

    # ---- 风险卡：真实（score 仅在真实计算值存在时展示） ----
    risk_items = []
    if isinstance(risk_notes, list):
        for n in risk_notes[:2]:
            rs = n.get("risk_score")
            risk_items.append({
                "level": _LV.get(n.get("risk_level", "low"), "low"),
                "score": rs if isinstance(rs, (int, float)) and rs else None,
                "title": (n.get("title") or "风险笔记")[:40],
                "desc": (n.get("content") or "")[:90],
                "evidence": f"NOTE:{n.get('note_id') or n.get('id') or 'UNKNOWN'}",
            })
    risks_sec = section("risks", STATE_READY if risk_items else STATE_EMPTY, items=risk_items)

    actions_sec = section("actions", title="建议行动", items=[
        {"id": "open-event", "cls": "NAVIGATION", "scope": "subject:current", "target": "CTH-04",
         "permission": "read", "icon": "event", "title": "打开重点事件", "desc": "进入事件时间线与影响面"},
        {"id": "draft-action", "cls": "DRAFT", "scope": "subject:current", "target": "ops_plan",
         "permission": "plan:write", "icon": "zap", "title": "起草引导排班调整", "desc": "进入草稿，经权限后执行"},
        {"id": "notify-team", "cls": "EFFECT", "scope": "team:ops", "target": "im",
         "permission": "notify:write", "risk": True, "icon": "bell", "title": "通知运营班组",
         "desc": "高风险确认后触达，需二次确认"},
    ])

    # ---- 运行时新鲜度（真实，detail 必须是标量字符串，禁止把 dict 直接丢给前端渲染成 [object Object]） ----
    def _scalar(v):
        if isinstance(v, dict):
            parts = [f"{k}={v[k]}" for k in list(v)[:3] if v[k] is not None]
            return " · ".join(parts) or "ok"
        if isinstance(v, (list, tuple)):
            return f"items={len(v)}"
        return "NA" if v is None else str(v)
    def _health_text(h):
        if isinstance(h, dict):
            st = h.get("state") or h.get("status")
            msg = h.get("detail") or h.get("message")
            parts = []
            if st is not None:
                parts.append(f"状态 {st}")
            if msg:
                parts.append(str(msg))
            return "；".join(parts) if parts else "无状态"
        return _scalar(h)
    runtime_items = [
        {"name": "主体范围数据", "state": "ok" if not stats_err else "offline",
         "detail": (f"来源 {stats.get('total')} 条" if stats.get('total') is not None
                    else "来源覆盖未知或不完整")},
        {"name": "Canonical 指标", "state": "ok" if not canon_err else "offline",
         "detail": ("采集健康：" + _health_text(canonical.get("collection_health"))) if not canon_err else "unavailable"},
        {"name": "来源核验", "state": "ok" if not events_err else "offline",
         "detail": "事件关联来源与主体范围已核验" if not events_err else "来源核验不可用"},
    ]
    runtime_sec = section("runtime", title="数据新鲜度", items=runtime_items)

    head = {
        "type": "head", "state": STATE_READY, "eyebrow": "CTH · 商业运营",
        "title": "商业运营总览", "titleKey": "screen.CTH-01",
        "desc": "围绕选定主体，从事实、关系、证据到风险与行动；页面不重算指标，所有数值可追溯。",
        "actions": [
            {"label": "生成运营简报", "variant": "primary", "id": "draft-brief", "cls": "DRAFT",
             "scope": "subject:current", "target": "report", "permission": "report:write", "ico": "report"},
            {"label": "时间范围", "variant": "secondary", "id": "head-range", "cls": "QUERY",
             "scope": "subject:current", "target": "time_window", "permission": "read", "ico": "calendar"},
            {"label": "导出", "variant": "ghost", "id": "export-overview", "cls": "QUERY",
             "scope": "subject:current", "target": "export", "permission": "report:read", "ico": "download"},
        ],
    }

    sections = [
        head,
        section("kpis", STATE_READY, items=kpis),
        {"type": "split", "state": STATE_READY,
         "main": [trend, events_sec, evidence_sec],
         "side": [insight_sec, risks_sec, actions_sec, runtime_sec]},
    ]
    return {
        "ok": True, "screen": "CTH-01", "source": "runtime", "bound": True,
        "sections": sections, "truth": truth,
        "binding": {"screen": "CTH-01", "bound": True,
                    "unavailable": [b["field"] for b in blocked], "blocked": blocked},
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }


# ===========================================================================
# AI-01 AI 意图入口 —— 真实绑定
# ===========================================================================
def _evidence_recent(limit: int = 2) -> List[Dict[str, Any]]:
    from lumenis.shared.evidence import store as es

    return es.query_evidence(limit=limit)


def _build_ai01() -> Dict[str, Any]:
    blocked: List[Dict[str, str]] = [
        {
            "field": "ai.anchored_evidence",
            "reason": "UNSCOPED_EVIDENCE_STORE",
            "required": "A trusted actor and authorized CTH Subject or BMP BrandFocus scope.",
        },
        {
            "field": "ai.traceability",
            "reason": "UNSCOPED_EXECUTION_STORE",
            "required": "An actor-scoped execution query linked to authorized product context.",
        },
        {
            "field": "ai.review_queue",
            "reason": "UNSCOPED_EVIDENCE_STORE",
            "required": "A trusted actor and authorized product-scoped review queue.",
        },
    ]
    truth: Dict[str, Any] = {}

    # The current Evidence and execution owners expose whole-store reads. Do not
    # query or serialize them through this screen until trusted product scope is
    # available; client-side filtering is not an authorization boundary.
    gov = _safe(_ai_governance, default={})
    gov_err = _is_err(gov)

    # Provider health includes only actual model providers. Deterministic rules
    # and standby plumbing are not providers and must not inflate the KPI.
    provider_states = _provider_runtime(gov, gov_err)
    healthy = sum(1 for p in provider_states if p["state"] == "ok")
    prov_kpi_state = STATE_READY if not gov_err else STATE_OFFLINE

    kpis = [
        metric("ai.anchored_evidence", "已授权范围内的锚定证据",
               value=None, state=STATE_NOT_COLLECTED, icon="link",
               note="Evidence 查询尚未绑定可信 Subject / BrandFocus 权限范围。",
               source="lumenis.shared.evidence.store.get_stats（全库，暂不读取）"),
        metric("ai.traceability", "AI 结论可追溯率", value=None, unit="%",
               decimals=1, state=STATE_NOT_COLLECTED, icon="evaluation",
               note="执行历史查询尚未绑定 actor 与授权产品范围。",
               source="Agent Groups Skill Execution（全局，暂不读取）"),
        metric("ai.provider_health", "AI Gateway 状态", value=healthy if prov_kpi_state == STATE_READY else None,
               unit=f"/{len(provider_states)}", state=prov_kpi_state, icon="ops",
               source="ai_governance.get_governance_status", fresh="m5"),
        metric("ai.review_queue", "待人工复核", value=None, state=STATE_NOT_COLLECTED,
               icon="risk", note="人工复核队列尚未绑定可信 actor 与产品范围。",
               source="lumenis.shared.evidence.store（全库，暂不读取）"),
    ]

    # 能力入口卡（静态入口，点击由 runtime.js 填入 composer 意图，不产生假数据）
    def _card_action(aid, intent):
        return {"id": aid, "label": "开始", "variant": "secondary", "size": "sm",
                "cls": "QUERY", "scope": "subject:current", "target": "composer",
                "permission": "read", "ico": "arrow-right", "intent": intent}

    cards = section("cards", STATE_READY, cols=4, items=[
        {"title": "生成商业运营简报", "desc": "汇总主体下指标/事件/风险并标注证据链", "ico": "report",
         "badge": {"text": "商业运营", "cls": "brand"}, "action": _card_action("intent-brief", "生成当前主体商业运营简报")},
        {"title": "追踪一个新事件", "desc": "按事件与案例建立时间线与影响面", "ico": "event",
         "action": _card_action("intent-event", "追踪一个新事件并建立时间线")},
        {"title": "对比竞品传播表现", "desc": "多品牌同口径对比，输出差异与证据", "ico": "target",
         "action": _card_action("intent-compare", "对比竞品传播表现")},
        {"title": "起草内容并走审批", "desc": "生成草稿进入 DRAFT，经权限后才执行", "ico": "content",
         "action": _card_action("intent-draft", "起草内容并进入审批流程")},
    ])

    # The shared execution owner currently returns global history. Keep the
    # section structurally present while withholding its rows at the server.
    timeline_sec = section("timeline", STATE_NOT_COLLECTED,
                           title="最近任务", label="History", items=[])
    runtime_sec = section("runtime", title="AI Gateway 状态", items=provider_states)
    rule_note = section("note", STATE_READY, kind="RULE", code="AI-NOT-TRUTH",
                        text="AI 输出为派生结果，携带 Provider/Model/Prompt/Confidence/Evidence 引用与人工修正状态，"
                             "不覆盖原始 Evidence 或 Canonical Data。")

    head = {
        "type": "head", "state": STATE_READY, "eyebrow": "LUMENIS AI · INTENT WORKSPACE",
        # The AI-first product entry is a canonical product name, not the
        # retired prototype label stored under screen.AI-01 in fixture data.
        "title": "LUMENIS AI", "titleKey": None,
        "desc": "从一句任务出发，读取当前业务上下文与本地证据，形成可追溯的判断或受控任务；AI 是增强层，不拥有生产事实。",
        "actions": [
            {"label": "查看 AI Gateway", "variant": "secondary", "id": "go-AI-05", "cls": "NAVIGATION",
             "scope": "global", "target": "AI-05", "permission": "read", "ico": "ops"},
            {"label": "技能中心", "variant": "ghost", "id": "go-AI-04", "cls": "NAVIGATION",
             "scope": "global", "target": "AI-04", "permission": "read", "ico": "skill"},
        ],
    }
    composer = {
        "type": "raw", "state": STATE_READY,
        "html": (
            '<div class="lum-opt lum-opt-composer" data-opt="composer" data-strength="idle" data-reveal>'
            '<canvas class="lum-opt__gl"></canvas><div class="lum-opt__fallback"></div>'
            '<div style="padding:20px">'
            '<div class="lum-row" style="gap:8px;margin-bottom:10px">'
            '<span class="lum-chip lum-press"><span data-i18n="ai.task_morph">能力任务</span></span>'
            '<span class="lum-caption">对话与执行分开：先理解，再决定是否进入任务链。</span></div>'
            '<textarea class="lum-textarea" data-ai-composer style="min-height:84px;background:transparent;'
            'border:0;font-size:16px;padding:0" data-i18n-ph="ai.composer_placeholder" '
            'data-i18n-aria="ai.composer_placeholder" placeholder="" aria-label="composer"></textarea>'
            '<div class="lum-row-between" style="margin-top:10px"><div class="lum-row" style="gap:8px">'
            '<button type="button" class="lum-chip lum-press" data-ai-ref>引用证据</button>'
            '<button type="button" class="lum-chip lum-press" data-ai-subject>指定主体</button>'
            '<button type="button" class="lum-chip lum-press" data-ai-window>时间范围</button></div>'
            '<div class="lum-row" style="gap:8px;justify-content:flex-end">'
            '<button type="button" class="lum-btn lum-btn-secondary" data-ai-execute>进入任务 →</button>'
            '<button type="button" class="lum-btn lum-btn-primary" data-ai-send>'
            '<span data-i18n="ai.send">发送</span> →</button></div></div>'
            '<div data-ai-thread class="lum-stack-4" style="margin-top:14px"></div></div></div>'
        ),
    }

    sections = [
        head, composer, shared_skill_surface("AI"),
        section("kpis", STATE_READY, items=kpis),
        cards,
        {"type": "split", "state": STATE_READY, "main": [timeline_sec],
         "side": [runtime_sec, rule_note]},
    ]
    return {
        "ok": True, "screen": "AI-01", "source": "runtime", "bound": True,
        "sections": sections, "truth": truth,
        "binding": {"screen": "AI-01", "bound": True,
                    "unavailable": [b["field"] for b in blocked], "blocked": blocked},
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }


def _ai_recent_tasks(limit: int) -> List[Dict[str, Any]]:
    from lumenis.shared.agents.skills.execution import query_executions

    return query_executions(limit=limit)


def _ai_governance() -> Dict[str, Any]:
    import ai_governance

    return ai_governance.get_governance_status() or {}


def _provider_runtime(gov: Dict[str, Any], gov_err: bool) -> List[Dict[str, Any]]:
    """Expose only the current SYSTEM Gateway route, without provider discovery."""
    try:
        from lumenis.system.ai_gateway import core

        ai_state = core.ai_status() or {}
    except Exception:
        ai_state = {}
    route_available = not gov_err and ai_state.get("enabled") is True
    detail = "Owned Gateway route is available." if route_available else (
        str(ai_state.get("detail") or "Gateway route is not verified.")
        if not gov_err else "Gateway status is unavailable."
    )
    return [{"kind": "provider", "name": "Owned AI Gateway",
             "state": "ok" if route_available else "offline", "detail": detail}]


# ===========================================================================
# 屏幕 ViewModel 统一入口
# ===========================================================================
_BUILDERS = {"CTH-01": _build_cth01, "AI-01": _build_ai01}

# P1 传播：其余真实数据屏 builder 集中在 experience_screens.py（一屏一函数）。
# 注意 experience_screens 顶部反向 import 本模块的同构构造器，构成导入环：若在模块体
# 顶部直接 import，会在对方“部分初始化”时拿不到 SCREEN_BUILDERS，异常被静默吞掉，导致
# 36 个传播屏全部退回 prototype（P0-E2E-03 实测发现）。改为首次请求时懒加载——此刻两个
# 模块必然都已完成初始化，无论谁先 import 都能正确合并（P0-E2E-03 修复）。
_PROPAGATED_BUILDERS: Dict[str, Any] = {}
_PROPAGATION_LOADED = False
_PROPAGATION_IMPORT_ERROR = ""
_PROPAGATION_LOCK = threading.RLock()


def _all_builders() -> Dict[str, Any]:
    """返回样板屏 + 传播屏的全部 builder（首次调用时懒加载 experience_screens，破循环导入）。"""
    global _PROPAGATION_LOADED, _PROPAGATED_BUILDERS, _PROPAGATION_IMPORT_ERROR
    with _PROPAGATION_LOCK:
        if not _PROPAGATION_LOADED:
            try:
                from experience_screens import SCREEN_BUILDERS as _propagated
                _BUILDERS.update(_propagated)
                _PROPAGATED_BUILDERS = dict(_propagated)
                _PROPAGATION_IMPORT_ERROR = ""
                _PROPAGATION_LOADED = True
            except Exception as _prop_exc:  # Retry on the next request after an import failure.
                _PROPAGATION_IMPORT_ERROR = str(_prop_exc)
    return _BUILDERS

# 未绑定屏幕（无生产数据源）的诚实说明，来自 06_CONTRACTS/unknown-bindings.json
def _unbound_reason(screen_id: str) -> str:
    return "screen has no production data source yet (BLOCKED_BY_EXTERNAL_DEPENDENCY); prototype structure only"


@experience_bp.route("/api/experience/screen/<screen_id>")
def screen_viewmodel(screen_id: str):
    """返回与原型同构的真实 section 描述符。未绑定屏幕明确 bound=False（前端保留原型，不假装）。"""
    builder = _all_builders().get(screen_id)
    if builder is None:
        return jsonify({"ok": True, "screen": screen_id, "source": "runtime", "bound": False,
                        "sections": None,
                        "classification": "BLOCKED_BY_EXTERNAL_DEPENDENCY",
                        "note": _unbound_reason(screen_id)}), 200
    try:
        if screen_id in {"CTH-05", "CTH-07"}:
            binding, error = _cth03_read_scope()
            if error is not None:
                return error

            def authorize_temporal_read():
                current, denial = _cth03_read_scope()
                if denial is not None:
                    raise PermissionError("CTH_TEMPORAL_SCOPE_REVOKED")
                return current

            return jsonify(builder(binding=binding, authorize=authorize_temporal_read))
        if screen_id in {"CTH-01", "CTH-03", "CTH-04", "CTH-06", "CTH-08", "CTH-09", "CTH-10"}:
            binding, error = _cth03_read_scope()
            if error is not None:
                return error
            result = builder(binding=binding)
            current, denial = _cth03_read_scope()
            if denial is not None or current != binding:
                raise PermissionError("CTH_SCREEN_SCOPE_CHANGED")
            return jsonify(result)
        if screen_id in {"BMP-01", "BMP-03", "BMP-04", "BMP-05", "BMP-06", "BMP-08", "BMP-09", "BMP-10", "BMP-11"}:
            read_scope = _bmp03_read_scope if screen_id in {"BMP-03", "BMP-04", "BMP-10"} else _bmp01_read_scope
            binding, error = read_scope()
            if error is not None:
                return error
            result = builder(binding=binding)
            current, denial = read_scope()
            if denial is not None or current != binding:
                raise PermissionError("BMP_SCREEN_SCOPE_CHANGED")
            return jsonify(result)
        if screen_id == "SH-02":
            binding, denial = _sh06_read_scope(module="evidence")
            if binding is None:
                status = 401 if denial == "AUTH_REQUIRED" else 400 if denial.startswith("INVALID_CONTEXT") else 503 if denial == "AUTHORIZATION_UNAVAILABLE" else 403
                return jsonify({"ok": False, "screen": screen_id, "bound": False,
                                "code": denial}), status
            result = builder(binding=binding)
            current, denial = _sh06_read_scope(module="evidence")
            if denial is not None or current != binding:
                raise PermissionError("MATERIAL_SCOPE_CHANGED")
            response = jsonify(result)
            response.headers["Cache-Control"] = "no-store"
            return response
        if screen_id in {"SH-06", "AI-02"}:
            # Scope/permission failure renders the honest "not shown" state, never items.
            binding, _error = _sh06_read_scope() if screen_id == "SH-06" else _sh06_read_scope(module="skills")
            return jsonify(builder(binding=binding))
        return jsonify(builder())
    except Exception as exc:  # noqa: BLE001
        if screen_id == "BMP-09":
            code = _content_project_error_code(exc)
            denied = isinstance(exc, PermissionError) or code in {"AUTH_REQUIRED", "WORK_PERMISSION_DENIED"}
            status = 403 if denied else 400 if isinstance(exc, ValueError) else 503
            return jsonify({"ok": False, "screen": screen_id, "bound": False,
                            "code": "BMP_REPORT_SCOPE_DENIED" if denied else "BMP_REPORT_UNAVAILABLE"}), status
        if screen_id == "SH-01":
            code = _content_project_error_code(exc)
            status = 403 if isinstance(exc, PermissionError) or code.startswith(("AUTH_", "SHARED_WORKSPACE_", "CONTENT_SCOPE_")) else 400 if isinstance(exc, ValueError) else 503
            return jsonify({"ok": False, "screen": screen_id, "bound": False,
                            "code": "CONTENT_SCOPE_DENIED" if status == 403 else "CONTENT_DATA_UNAVAILABLE"}), status
        if screen_id == "SH-02":
            from flask import current_app
            current_app.logger.warning("Material library unavailable: %s", type(exc).__name__)
            denied = isinstance(exc, PermissionError)
            return jsonify({"ok": False, "screen": screen_id, "bound": False,
                            "code": "MATERIAL_SCOPE_DENIED" if denied else "MATERIAL_DATA_UNAVAILABLE"}), 403 if denied else 503
        if screen_id == "SH-05":
            from flask import current_app
            current_app.logger.exception("SH-05 scoped learning projection unavailable")
            code = str(exc)
            integrity_failure = any(part in code for part in ("INTEGRITY", "SIGNED_RECEIPT", "RECEIPT_UNVERIFIED", "CHAIN_INVALID"))
            scope_failure = code.startswith(("AUTH_", "SHARED_WORKSPACE_", "CONTENT_SCOPE_"))
            status = 503 if integrity_failure else 403 if isinstance(exc, PermissionError) or scope_failure else 400 if isinstance(exc, ValueError) else 503
            return jsonify({"ok": False, "screen": screen_id, "bound": False,
                            "code": "LEARNING_SCOPE_DENIED" if status == 403 else "LEARNING_DATA_UNAVAILABLE"}), status
        if screen_id == "AI-03":
            status = 403 if isinstance(exc, PermissionError) else 400 if isinstance(exc, ValueError) else 503
            code = "CONVERSATION_ACCESS_DENIED" if status == 403 else "CONVERSATION_QUERY_INVALID" if status == 400 else "CONVERSATION_UNAVAILABLE"
            return jsonify({"ok": False, "screen": screen_id, "bound": False, "code": code}), status
        if screen_id in {"CTH-01", "CTH-03", "CTH-04", "CTH-05", "CTH-06", "CTH-07", "CTH-08", "CTH-09", "CTH-10", "BMP-01", "BMP-03", "BMP-04", "BMP-05", "BMP-06", "BMP-08", "BMP-09", "BMP-10", "BMP-11", "SH-06"}:
            from flask import current_app
            current_app.logger.warning("%s scoped read unavailable: %s", screen_id, type(exc).__name__)
            return jsonify({"ok": False, "screen": screen_id, "bound": False,
                            "code": "SCOPED_DATA_UNAVAILABLE",
                            "error": "当前范围数据暂不可用，请重试"}), 503
        return jsonify({"ok": False, "screen": screen_id, "bound": True, "error": str(exc),
                        "trace": _tb.format_exc(limit=2)}), 500


def _cth03_read_scope():
    """Authorize the requested viewing scope independently of row provenance."""
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import (
        check_actor_scope_permission, local_workspace_read_allowed,
    )
    from lumenis_app_api import _context_error, _context_selection_from_scope

    mode = request.headers.get("X-Lumenis-Context-Mode", "GLOBAL_ALL")
    domain = request.headers.get("X-Domain-Id")
    subject = request.headers.get("X-Subject-ID")
    if mode == "GLOBAL_ALL":
        if domain or subject:
            return None, _context_error("INVALID_CONTEXT", "全局范围不能携带聚焦主体", 400)
    elif mode == "FOCUS" and domain == "CTH" and subject:
        _selection, error = _context_selection_from_scope(domain, subject)
        if error is not None:
            return None, error
    else:
        return None, _context_error("INVALID_CONTEXT", "需要有效的商业主体范围", 400)

    module = "commercial_realtime_stream"
    local_read = local_workspace_read_allowed(module)
    if not local_read:
        actor = get_current_user()
        if not isinstance(actor, dict) or type(actor.get("id")) is not int:
            return None, _context_error("AUTH_REQUIRED", "当前请求没有读取授权", 401)
        decision = check_actor_scope_permission(
            actor, domain_id="CTH", action="read", module=module,
            subject_id=subject, global_scope=mode == "GLOBAL_ALL",
        )
        if decision.verification_state != "verified":
            return None, _context_error("AUTHORIZATION_UNAVAILABLE", "读取授权暂不可用", 503)
        if not decision.allowed:
            return None, _context_error("SUBJECT_SCOPE_DENIED", "当前范围不可读取", 403)
    return {
        "contract": "lumenis.scope-read-binding.v1",
        "module": module,
        "policy": "local-workspace-read-v1" if local_read else "actor-exact-scope-v1",
        "domain_id": "CTH", "product_id": "CTH", "canonical_scope": mode,
        "subject_id": subject, "applied": True, "read_allowed": True,
        "scope_verified": True,
        "actor_scope": "anonymous_read" if local_read else "authenticated",
        "global_all_granted": mode == "GLOBAL_ALL" and not local_read,
    }, None


def _sh06_read_scope(*, module="operational_inbox"):
    """Authorize the SH-06 inbox range for the signed-in actor (SH-06.md §2).

    GLOBAL_ALL needs a verified global read grant in both CTH and BMP; FOCUS needs
    the exact registered Subject/BrandFocus grant. Anonymous reads are never
    granted for the operational inbox.
    """
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import check_actor_scope_permission
    from lumenis_app_api import _context_selection_from_scope

    mode = request.headers.get("X-Lumenis-Context-Mode", "GLOBAL_ALL")
    domain = (request.headers.get("X-Domain-Id") or "").upper() or None
    subject = request.headers.get("X-Subject-ID")
    actor = get_current_user(read_only=True)
    principal = None
    if not isinstance(actor, dict) or type(actor.get("id")) is not int:
        if module in {"skills", "evidence"}:
            from lumenis.system.security.permission import resolve_local_workspace_principal
            principal = resolve_local_workspace_principal(module=module, action="read")
        if principal is None:
            return None, "AUTH_REQUIRED"
    brand_focus = None
    display_name = None
    if mode == "GLOBAL_ALL":
        if domain or subject:
            return None, "INVALID_CONTEXT"
        checks = [("CTH", {}), ("BMP", {})]
    elif mode == "FOCUS" and domain in {"CTH", "BMP"} and subject:
        selection, error = _context_selection_from_scope(domain, subject)
        if error is not None or selection is None:
            return None, "INVALID_CONTEXT"
        try:
            from subject_registry import get_subject_by_id
            record = get_subject_by_id(domain, subject) or {}
        except Exception:  # noqa: BLE001
            record = {}
        display_name = record.get("display_name") or record.get("name")
        if domain == "BMP":
            brand_focus = selection.brand_focus_id
            if not brand_focus:
                return None, "INVALID_CONTEXT_SCOPE"
            checks = [("BMP", {"brand_focus_id": brand_focus})]
        else:
            checks = [("CTH", {"subject_id": subject})]
    else:
        return None, "INVALID_CONTEXT"
    for check_domain, ids in checks:
        if principal is not None:
            from lumenis.system.security.permission import check_local_workspace_scope_permission
            scope_check = check_local_workspace_scope_permission
            identity = principal
        else:
            scope_check = check_actor_scope_permission
            identity = actor
        decision = scope_check(
            identity, domain_id=check_domain, action="read", module=module,
            global_scope=mode == "GLOBAL_ALL", **ids,
        )
        if decision.verification_state != "verified":
            return None, "AUTHORIZATION_UNAVAILABLE"
        if not decision.allowed:
            return None, "SCOPE_DENIED"
    return {
        "contract": "lumenis.scope-read-binding.v1",
        "module": module, "policy": "actor-exact-scope-v1",
        "domain_id": domain if mode == "FOCUS" else None,
        "canonical_scope": mode,
        "subject_id": subject if mode == "FOCUS" and domain == "CTH" else None,
        "brand_focus_id": brand_focus, "display_name": display_name,
        "applied": True, "read_allowed": True, "scope_verified": True,
        "actor_scope": "sealed_local" if principal is not None else "authenticated", "global_all_granted": mode == "GLOBAL_ALL",
        "actor_id": actor["id"] if principal is None else None,
    }, None


def _bmp03_read_scope():
    """Bind the existing scope admission to the current server-side identity."""
    from lumenis.auth.service import get_current_user
    before = get_current_user(read_only=True)
    binding, error = _bmp01_read_scope()
    if error is not None:
        return binding, error
    actor = get_current_user(read_only=True)
    actor_id = actor.get("id") if isinstance(actor, dict) else None
    before_id = before.get("id") if isinstance(before, dict) else None
    if before_id != actor_id:
        raise PermissionError("BMP_SOURCE_PRINCIPAL_CHANGED")
    return {**binding, "actor_id": actor_id if type(actor_id) is int else None}, None


def _bmp01_read_scope():
    """Authorize GLOBAL or exact BMP BrandFocus view before Canonical projection."""
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import (
        check_actor_scope_permission,
        local_workspace_read_allowed,
    )
    from lumenis_app_api import _context_error, _context_selection_from_scope

    mode = request.headers.get("X-Lumenis-Context-Mode", "GLOBAL_ALL")
    domain = request.headers.get("X-Domain-Id")
    subject = request.headers.get("X-Subject-ID")
    brand_focus = None
    supplied_brand = request.headers.get("X-Brand-Focus-ID")
    if mode == "GLOBAL_ALL":
        if subject or supplied_brand or (domain and domain != "BMP"):
            return None, _context_error(
                "INVALID_CONTEXT", "全局品牌范围不能携带其他主体", 400
            )
    elif mode == "FOCUS" and domain == "BMP" and (subject or supplied_brand):
        if supplied_brand and (
            supplied_brand != supplied_brand.strip() or not supplied_brand
        ):
            return None, _context_error(
                "INVALID_CONTEXT_SCOPE", "品牌范围标识无效", 400
            )
        if not subject:
            from subject_registry import list_subjects

            matches = [
                entry
                for entry in list_subjects("BMP")
                if entry.get("brand_focus_id") == supplied_brand
                and entry.get("subject_type") == "brand"
                and entry.get("status") in {"active", "configured"}
            ]
            if len(matches) != 1:
                return None, _context_error(
                    "INVALID_CONTEXT_SCOPE", "品牌范围未唯一登记", 400
                )
            subject = matches[0]["subject_id"]
        selection, error = _context_selection_from_scope(domain, subject)
        if error is not None:
            return None, error
        brand_focus = selection.brand_focus_id
        if not brand_focus or (supplied_brand and brand_focus != supplied_brand):
            return None, _context_error(
                "INVALID_CONTEXT_SCOPE", "品牌关注范围不完整", 400
            )
    else:
        return None, _context_error("INVALID_CONTEXT", "需要有效的品牌关注范围", 400)

    module = "brand_market_overview"
    local_read = local_workspace_read_allowed(module)
    if not local_read:
        actor = get_current_user()
        if not isinstance(actor, dict) or type(actor.get("id")) is not int:
            return None, _context_error("AUTH_REQUIRED", "当前请求没有读取授权", 401)
        decision = check_actor_scope_permission(
            actor,
            domain_id="BMP",
            action="read",
            module=module,
            subject_id=None,
            brand_focus_id=brand_focus,
            global_scope=mode == "GLOBAL_ALL",
        )
        if decision.verification_state != "verified":
            return None, _context_error(
                "AUTHORIZATION_UNAVAILABLE", "读取授权暂不可用", 503
            )
        if not decision.allowed:
            return None, _context_error(
                "SUBJECT_SCOPE_DENIED", "当前品牌范围不可读取", 403
            )

    binding = {
        "contract": "lumenis.scope-read-binding.v1",
        "module": module,
        "policy": "local-workspace-read-v1" if local_read else "actor-exact-scope-v1",
        "domain_id": "BMP",
        "product_id": "ZBMP",
        "canonical_scope": mode,
        "subject_id": subject,
        "brand_focus_id": brand_focus,
        "applied": True,
        "read_allowed": True,
        "scope_verified": True,
        "actor_scope": "anonymous_read" if local_read else "authenticated",
        "global_all_granted": mode == "GLOBAL_ALL" and not local_read,
    }
    if local_read:
        # Describes this module's actual transport admission, never a principal
        # or an account GLOBAL grant. The route rechecks admission after reading.
        binding["read_transport"] = {
            "contract": "lumenis.local-read-transport.v1",
            "module": module, "action": "read", "verified": True,
        }
    return binding, None


@experience_bp.route("/api/experience/shared-skills")
def shared_skills_catalog():
    """Read-only catalog for the single Shared Content & Creation surface."""
    try:
        from lumenis_shared_skills import list_shared_skills
        return jsonify({
            "ok": True,
            "product": "LUMENIS",
            "capability": "Shared Content & Creation",
            "consumers": ["CTH", "BMP"],
            "skills": list_shared_skills(),
        })
    except Exception as exc:  # pragma: no cover - defensive runtime boundary
        return jsonify({"ok": False, "error": "shared skill catalog unavailable", "error_type": type(exc).__name__}), 503


@experience_bp.route("/api/experience/cth/platform-collection")
def cth_platform_collection_surface():
    """Return the single CTH-owned, human-triggered secondary collection surface.

    This endpoint is a local health/readiness read.  It does not start a
    browser, call a platform, or expose credential paths.  BMP consumes the
    same surface through its screen ViewModel rather than owning another
    collector.
    """
    try:
        from lumenis.system.collector.adapters.secondary_collection import get_collection_surface
        return jsonify(get_collection_surface())
    except Exception as exc:  # pragma: no cover - defensive runtime boundary
        return jsonify({
            "ok": False,
            "product": "LUMENIS",
            "domain": "CTH",
            "error": "platform collection surface unavailable",
            "error_type": type(exc).__name__,
        }), 503


@experience_bp.route("/api/experience/cth/platform-collection/search", methods=["POST"])
def cth_platform_collection_search():
    """Run one explicit, read-only platform search after human confirmation.

    The endpoint is intentionally separate from scheduler controls and from
    AI task execution.  It can import Evidence/Canonical records, but it has
    no external write or publish path.
    """
    body = request.get_json(silent=True)
    allowed_fields = {"operator", "confirm_read_only", "platform", "keyword", "max_results", "capability", "content_id",
                      "business_requests", "max_queries", "continuation", "checkpoint", "request_id",
                      "source_id", "include_replies", "action", "confirmed_resource", "task_id", "author_id"}
    if not isinstance(body, dict) or set(body) - allowed_fields:
        return jsonify({"ok": False, "status": "invalid_request", "code": "INVALID_COLLECTION_REQUEST",
                        "read_only": True, "external_write": False}), 400
    operator = str(body.get("operator") or "").strip().lower()
    if operator not in {"human", "human_ui"}:
        return jsonify({
            "ok": False,
            "status": "denied",
            "code": "HUMAN_OPERATOR_REQUIRED",
            "reason": "平台采集只能由人工从序境内触发。",
            "read_only": True,
            "external_write": False,
        }), 403
    if body.get("confirm_read_only") is not True:
        return jsonify({
            "ok": False,
            "status": "input_required",
            "code": "READ_ONLY_CONFIRMATION_REQUIRED",
            "reason": "必须确认本次只读采集，不执行外部写入或发布。",
        }), 400
    platform = body.get("platform")
    keyword = body.get("keyword")
    capability = body.get("capability", "search")
    if capability not in {"search", "detail", "comments", "author", "author_posts"}:
        return jsonify({"ok": False, "code": "INVALID_COLLECTION_CAPABILITY"}), 400
    max_results = body.get("max_results", 20)
    action = body.get("action", "run")
    if action not in {"prepare", "confirm", "run", "start", "status", "step", "cancel", "resume","recover"}:
        return jsonify({"ok": False, "code": "INVALID_COLLECTION_ACTION"}), 400
    if action != "confirm" and "confirmed_resource" in body:
        return jsonify({"ok": False, "code": "INVALID_COLLECTION_CONFIRMATION"}), 400
    try:
        from shared_artifacts import LocalArtifactError
        from lumenis.system.collector.adapters.secondary_collection import (
            collect_comments, collect_detail, collect_search,
            collect_author, collect_author_posts,
            prepare_collection_request, confirm_collection_request, operate_collection_request,
        )
        try:
            actor, scope = _content_project_scope("write", module="collector")
        except LocalArtifactError as exc:
            return _content_project_error(exc)
        if action in {"status", "step", "cancel", "resume","recover"}:
            if set(body) - {"operator", "confirm_read_only", "action", "task_id"}:
                raise ValueError("An existing collection task uses its saved source request")
            result = operate_collection_request(action, actor=actor, scope=scope, task_id=body.get("task_id"))
        elif action == "start":
            if set(body) & {"business_requests", "max_queries", "continuation", "checkpoint", "task_id"}:
                raise ValueError("Start one exact approved source request")
            if capability == "detail" and "max_results" in body:
                raise ValueError("Detail accepts one content_id")
            result = operate_collection_request(action, actor=actor, scope=scope, request_id=body.get("request_id"),
                capability=capability, platform=platform, keyword=keyword, content_id=body.get("content_id"),
                source_id=body.get("source_id"), max_results=max_results, include_replies=body.get("include_replies", False),
                author_id=body.get('author_id'))
        elif action in {"prepare", "confirm"}:
            if set(body) & {"business_requests", "max_queries", "continuation", "checkpoint", "request_id", "task_id"}:
                raise ValueError("Confirm one explicit source request before acquisition")
            if capability == "detail" and "max_results" in body:
                raise ValueError("Detail accepts one content_id")
            source_request = {"capability": capability, "platform": platform, "keyword": keyword,
                              "content_id": body.get("content_id"), "source_id": body.get("source_id"),
                              "max_results": max_results, "include_replies": body.get("include_replies", False),
                              "author_id":body.get('author_id')}
            result = (prepare_collection_request(actor=actor, scope=scope, **source_request)
                      if action == "prepare" else confirm_collection_request(
                          actor=actor, scope=scope, confirmed_resource=body.get("confirmed_resource"),
                          confirmed=body.get("confirm_read_only"), **source_request))
        elif capability in {'author','author_posts'}:
            if set(body) & {'business_requests','keyword','content_id','source_id','max_queries','checkpoint',
                            'continuation','include_replies','task_id','request_id'}:
                raise ValueError('Author operations require one explicit profile or saved task')
            result = (collect_author(platform,body.get('author_id'),actor=actor,scope=scope) if capability=='author'
                      else collect_author_posts(platform,body.get('author_id'),actor=actor,scope=scope,max_results=max_results))
        elif capability == "comments":
            if set(body) & {"business_requests", "platform", "keyword", "content_id", "max_queries", "checkpoint", "task_id", "author_id"}:
                raise ValueError("Comments require an admitted source, not a new platform query")
            result = collect_comments(body.get("source_id"), actor=actor, scope=scope,
                request_id=body.get("request_id"), max_results=max_results,
                include_replies=body.get("include_replies", False), continuation=body.get("continuation"))
        elif "business_requests" in body:
            from lumenis.system.collector.adapters.secondary_collection import collect_business_queries
            if set(body) & {"platform", "keyword", "content_id", "source_id", "include_replies", "task_id", "author_id"} or capability != "search":
                raise ValueError("Choose one explicit source query or a task-selected business batch")
            max_queries = body.get("max_queries", 32)
            if type(max_queries) is not int or not 1 <= max_queries <= 64:
                raise ValueError("max_queries must be an integer from 1 to 64")
            domain = "bmp" if scope["domain_id"] in {"bmp", "zbmp"} else "cth"
            result = collect_business_queries(body["business_requests"], actor=actor,
                scopes={domain: scope}, operator=operator, max_results=max_results,
                max_queries=max_queries, continuation=body.get("continuation"),
                checkpoint=body.get("checkpoint"), request_id=body.get("request_id"))
        else:
            if set(body) & {"max_queries", "continuation", "checkpoint", "request_id", "source_id", "include_replies", "task_id", "author_id"}:
                raise ValueError("Business continuation fields require business_requests")
            if capability == "detail":
                if "keyword" in body or "max_results" in body:
                    raise ValueError("Detail accepts a content_id, not search fields")
                result = collect_detail(platform, body.get("content_id"), operator=operator,
                                        actor=actor, scope=scope)
            else:
                if "content_id" in body:
                    raise ValueError("A content_id requires detail capability")
                result = collect_search(platform, keyword, max_results=max_results, operator=operator,
                                        actor=actor, scope=scope)
        state = result.get("status")
        http_status = (401 if state == "AUTH_REQUIRED" else
                       403 if state in {"SCOPE_UNAUTHORIZED", "APPROVAL_REQUIRED"} else
                       503 if state == "PERMISSION_UNAVAILABLE" else
                       409 if state in {"BUSY", "RATE_LIMITED"} else 200)
        return jsonify(result), http_status
    except PermissionError as exc:
        code = str(exc) if str(exc).startswith(("COMMENT_", "COLLECTION_", "AUTHOR_")) else "HUMAN_OPERATOR_REQUIRED"
        return jsonify({"ok": False, "status": "denied", "code": code,
                        "read_only": True, "external_write": False}), 403
    except LookupError as exc:
        code = "COLLECTION_TASK_NOT_FOUND" if str(exc) == "COLLECTION_TASK_NOT_FOUND" else "COMMENT_PARENT_NOT_FOUND"
        return jsonify({"ok": False, "code": code}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "status": "invalid_request", "error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"ok": False, "status": "blocked", "error_type": type(exc).__name__}), 503
    except Exception as exc:  # noqa: BLE001 - no adapter details at HTTP boundary
        return jsonify({"ok": False, "status": "error", "error_type": type(exc).__name__}), 503


@experience_bp.get('/api/experience/cth/platform-collection/results')
def cth_platform_collection_results():
    from shared_artifacts import LocalArtifactError
    from lumenis.system.collector.adapters.secondary_collection import read_collected_items
    if set(request.args) != {'evidence_ref'} or len(request.args.getlist('evidence_ref')) != 1:
        return jsonify({'ok':False, 'code':'COLLECTION_RESULT_REFERENCE_REQUIRED'}), 400
    try:
        actor, scope = _content_project_scope('read', module='collector', read_only_auth=True)
        return jsonify(read_collected_items(request.args['evidence_ref'], actor=actor, scope=scope))
    except LocalArtifactError as exc:
        return _content_project_error(exc)
    except PermissionError as exc:
        return jsonify({'ok':False, 'code':str(exc)}), 403
    except ValueError as exc:
        return jsonify({'ok':False, 'code':str(exc)}), 400
    except Exception:
        return jsonify({'ok':False, 'code':'COLLECTION_RESULT_READ_UNAVAILABLE'}), 503


@experience_bp.route("/api/experience/cth/platform-collection/comments")
def cth_platform_collection_comments():
    from shared_artifacts import LocalArtifactError
    from lumenis.system.collector.adapters.secondary_collection import read_collected_comments

    if set(request.args) - {"source_id", "limit", "before", "page_ref"} or any(
        len(request.args.getlist(key)) != 1 for key in request.args
    ):
        return jsonify({"ok": False, "code": "COMMENT_REQUEST_INVALID"}), 400
    try:
        actor, scope = _content_project_scope("read", module="collector", read_only_auth=True)
        result = read_collected_comments(request.args.get("source_id"), actor=actor, scope=scope,
            limit=int(request.args.get("limit", "20")), before=request.args.get("before"),
            page_ref=request.args.get("page_ref"))
        return jsonify(result)
    except LocalArtifactError as exc:
        return _content_project_error(exc)
    except PermissionError as exc:
        code = str(exc) if str(exc).startswith("COMMENT_") else "COMMENT_SOURCE_NOT_AUTHORIZED"
        return jsonify({"ok": False, "code": code}), 403
    except LookupError:
        return jsonify({"ok": False, "code": "COMMENT_PARENT_NOT_FOUND"}), 404
    except (TypeError, ValueError):
        return jsonify({"ok": False, "code": "COMMENT_REQUEST_INVALID"}), 400
    except Exception:
        return jsonify({"ok": False, "code": "COMMENT_READ_UNAVAILABLE"}), 503


def _content_project_scope(action: str, *, module="content", include_decision=False, read_only_auth=False, selectors=None):
    """Resolve selectors through the canonical registry, then ask Permission."""
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import (
        check_actor_scope_permission, check_local_workspace_scope_permission,
        resolve_local_workspace_principal,
    )
    from subject_registry import get_subject_by_id, normalize_domain
    from shared_artifacts import LocalArtifactError

    selectors = request.headers if selectors is None else selectors

    try:
        local_principal = resolve_local_workspace_principal(module=module, action=action)
        actor = local_principal if local_principal is not None else (
            get_current_user(read_only=True) if read_only_auth else get_current_user()
        )
    except Exception as exc:
        raise LocalArtifactError("AUTH_UNAVAILABLE") from exc
    if local_principal is None and (
        not isinstance(actor, dict) or type(actor.get("id")) is not int or actor["id"] <= 0
    ):
        raise LocalArtifactError("AUTH_REQUIRED")
    if selectors.get(_SHARED_WORKSPACE_SCOPE_HEADER) is not None:
        if module != "content" or not _shared_content_project_route_allowed():
            raise LocalArtifactError("SHARED_WORKSPACE_SCOPE_NOT_SUPPORTED")
        try:
            from lumenis.system.security.permission import (
                authorize_shared_workspace,
                validate_shared_workspace_scope,
            )

            shared_scope = validate_shared_workspace_scope(_parse_shared_workspace_scope_header(selectors))
            authorize_shared_workspace(actor, shared_scope, module="content", action=action)
        except PermissionError as exc:
            raise LocalArtifactError(str(exc)) from exc
        except ValueError as exc:
            raise LocalArtifactError(str(exc)) from exc
        if include_decision:
            raise LocalArtifactError("SHARED_WORKSPACE_SCOPE_NOT_SUPPORTED")
        return actor, {"shared_workspace_scope": shared_scope}
    try:
        selected_domain = normalize_domain(selectors.get("X-Domain-Id", ""))
    except ValueError as exc:
        raise LocalArtifactError("DOMAIN_REQUIRED") from exc
    if selected_domain not in {"CTH", "BMP"}:
        raise LocalArtifactError("DOMAIN_REQUIRED")
    domain = "cth" if selected_domain == "CTH" else "zbmp"
    product = selectors.get("X-Product-Id", selected_domain)
    if product not in ({"CTH"} if domain == "cth" else {"BMP", "ZBMP"}):
        raise LocalArtifactError("CONTEXT_SCOPE_MISMATCH")
    mode = selectors.get("X-Lumenis-Context-Mode", "GLOBAL_ALL")
    selected_subject = selectors.get("X-Subject-ID", "") or None
    selected_brand = selectors.get("X-Brand-Focus-ID", "") or None
    if any(value is not None and value != value.strip() for value in (selected_subject, selected_brand)):
        raise LocalArtifactError("CONTEXT_SCOPE_MISMATCH")
    subject, brand = None, None
    if mode == "GLOBAL_ALL":
        if selected_subject or selected_brand:
            raise LocalArtifactError("CONTEXT_SCOPE_MISMATCH")
    elif mode == "FOCUS":
        if selected_subject:
            try:
                entry = get_subject_by_id(selected_domain, selected_subject)
            except Exception as exc:
                raise LocalArtifactError("CONTENT_SCOPE_UNAVAILABLE") from exc
            if not isinstance(entry, dict):
                raise LocalArtifactError("CONTENT_SCOPE_NOT_FOUND")
            if domain == "cth":
                if entry.get("subject_type") != "company" or selected_brand:
                    raise LocalArtifactError("CONTEXT_SCOPE_MISMATCH")
                subject = selected_subject
            else:
                brand = entry.get("brand_focus_id")
                if entry.get("subject_type") != "brand" or not brand or (selected_brand and selected_brand != brand):
                    raise LocalArtifactError("CONTEXT_SCOPE_MISMATCH")
        elif domain == "zbmp" and selected_brand:
            # Direct BrandFocus selection is still verified against the registry by Permission.
            brand = selected_brand
        else:
            raise LocalArtifactError("CONTEXT_SCOPE_MISMATCH")
    else:
        raise LocalArtifactError("CONTEXT_SCOPE_MISMATCH")
    scope = {"domain_id": domain, "subject_id": subject, "brand_focus_id": brand,
             "global_scope": mode == "GLOBAL_ALL"}
    checker = (
        check_local_workspace_scope_permission if local_principal is not None
        else check_actor_scope_permission
    )
    decision = checker(actor, action=action, module=module, **scope)
    if decision.verification_state != "verified":
        raise LocalArtifactError("CONTENT_SCOPE_UNAVAILABLE")
    if decision.allowed is not True:
        raise LocalArtifactError("CONTENT_SCOPE_DENIED")
    return (actor, scope, decision) if include_decision else (actor, scope)


@experience_bp.route("/api/experience/owned-training/review-resources", methods=["POST"])
def prepare_owned_training_review_resource():
    """Prepare a review fingerprint from a real request; never submit a review."""
    from lumenis.shared.database import get_repository
    from lumenis.shared.learning import training_cases, training_review
    from lumenis.shared.reporting.source_brief_job import _scope_material
    from lumenis.system.security import permission

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("OWNED_TRAINING_PREVIEW_INPUT_INVALID")
            result[key] = value
        return result

    try:
        raw = request.stream.read(65537)
        if len(raw) > 65536 or not request.is_json:
            raise ValueError("OWNED_TRAINING_PREVIEW_INPUT_INVALID")
        body = json.loads(raw, object_pairs_hook=unique_object)
        if type(body) is not dict or set(body) != {
            "submission_id", "source_evidence_refs", "prompt_messages", "proposed_target",
            "context", "proposed_rights_declaration",
        }:
            raise ValueError("OWNED_TRAINING_PREVIEW_INPUT_INVALID")
        actor, selected, scoped = _content_project_scope(
            "write", module="owned_training", include_decision=True, read_only_auth=True,
        )
        scope = _scope_material(
            product_id="CTH" if selected["domain_id"] == "cth" else "ZBMP",
            subject_id=selected["subject_id"], brand_focus_id=selected["brand_focus_id"],
            global_scope=selected["global_scope"], entity_label="GLOBAL / ALL" if selected["global_scope"] else (
                selected["subject_id"] or selected["brand_focus_id"]
            ),
        )
        gate = permission.get_permission_gate()
        decision = gate.check(
            permission.OperationType.OWNED_TRAINING_REVIEW_PREVIEW,
            resource=request.path, caller=scoped.caller, domain_id=scoped.domain_id,
        )
        if not decision.allowed or not decision.audit_id:
            raise PermissionError("OWNED_TRAINING_PREVIEW_DENIED")
        identity_args = {"principal": actor} if type(actor) is permission.LocalWorkspacePrincipal else {
            "authenticated_actor": actor,
        }
        args = dict(
            **identity_args, expected_scope=scope,
            source_evidence_refs=body["source_evidence_refs"], submission_id=body["submission_id"],
            prompt_messages=body["prompt_messages"], reviewer_approved_target=body["proposed_target"],
            context=body["context"], rights_declaration=body["proposed_rights_declaration"],
        )
        resource = training_review.training_review_approval_resource(**args)
        # Read the same signed rows again so the response cannot certify an
        # input whose immutable source changed between fingerprint and output.
        material = training_review._request_material(**args)
        with get_repository().connection(read_only=True, wal=False) as connection:
            source_hashes = training_review._source_hashes(connection, material)
        if resource != training_review._resource(material, source_hashes):
            raise PermissionError("OWNED_TRAINING_PREVIEW_SOURCE_CHANGED")
        return jsonify({
            "ok": True, "state": "REVIEW_RESOURCE_PREPARED", "resource": resource,
            "submission_id": body["submission_id"], "input_sha256": hashlib.sha256(
                training_cases._json(body).encode("utf-8")
            ).hexdigest(), "source_evidence": source_hashes,
            "scope_permission_audit_id": scoped.audit_id, "preview_permission_audit_id": decision.audit_id,
            "human_rights_decision": "PENDING", "human_target_decision": "PENDING",
            "approval_issued": False, "training_eligible": False, "training_started": False,
        })
    except Exception as exc:
        return _content_project_error(exc)


def _owned_training_review_api_body(required):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("OWNED_TRAINING_REVIEW_INPUT_INVALID")
            result[key] = value
        return result
    raw = request.stream.read(65537)
    if len(raw) > 65536 or not request.is_json:
        raise ValueError("OWNED_TRAINING_REVIEW_INPUT_INVALID")
    body = json.loads(raw, object_pairs_hook=unique)
    if type(body) is not dict or set(body) != required:
        raise ValueError("OWNED_TRAINING_REVIEW_INPUT_INVALID")
    return body


def _owned_training_review_api_scope(action):
    from lumenis.shared.reporting.source_brief_job import _scope_material
    from lumenis.system.security import permission as p
    actor, selected, decision = _content_project_scope(
        action, module="owned_training", include_decision=True, read_only_auth=True,
    )
    scope = _scope_material(
        product_id="CTH" if selected["domain_id"] == "cth" else "ZBMP",
        subject_id=selected["subject_id"], brand_focus_id=selected["brand_focus_id"],
        global_scope=selected["global_scope"],
        entity_label="GLOBAL / ALL" if selected["global_scope"] else (
            selected["subject_id"] or selected["brand_focus_id"]),
    )
    identity_args = {"principal": actor} if type(actor) is p.LocalWorkspacePrincipal else {"actor_id": actor["id"]}
    return actor, scope, decision, p.owned_training_identity(**identity_args)


@experience_bp.route("/api/experience/owned-training/review-submissions", methods=["POST"])
def submit_owned_training_review():
    """Apply an explicit human target/rights decision through canonical owners."""
    from lumenis.shared.learning import training_review
    from lumenis.system.security import permission as p
    token = None
    gate = p.get_permission_gate()
    try:
        body = _owned_training_review_api_body({"material", "confirmed_resource", "confirm"})
        material = body["material"]
        if (body["confirm"] is not True or type(material) is not dict or set(material) != {
            "submission_id", "source_evidence_refs", "prompt_messages", "proposed_target",
            "context", "proposed_rights_declaration",
        }):
            raise PermissionError("OWNED_TRAINING_REVIEW_EXPLICIT_CONFIRMATION_REQUIRED")
        actor, scope, scoped, identity = _owned_training_review_api_scope("write")
        if (type(gate) is not p.PermissionGate or p.is_testing_bypass_enabled()
                or not gate.has_permission(p.PermissionLevel.HUMAN_APPROVAL)
                or not gate.has_permission(p.PermissionLevel.COMMIT)):
            raise PermissionError("OWNED_TRAINING_REVIEW_MANUAL_AUTHORITY_REQUIRED")
        args = dict(
            **({"principal": actor} if type(actor) is p.LocalWorkspacePrincipal else {"authenticated_actor": actor}),
            expected_scope=scope, source_evidence_refs=material["source_evidence_refs"],
            submission_id=material["submission_id"], prompt_messages=material["prompt_messages"],
            reviewer_approved_target=material["proposed_target"], context=material["context"],
            rights_declaration=material["proposed_rights_declaration"],
        )
        resource = training_review.training_review_approval_resource(**args)
        if type(body["confirmed_resource"]) is not str or body["confirmed_resource"] != resource:
            raise PermissionError("OWNED_TRAINING_REVIEW_CONFIRMED_RESOURCE_CHANGED")
        _, current_scope, _, current_identity = _owned_training_review_api_scope("write")
        if (current_scope, current_identity) != (scope, identity):
            raise PermissionError("OWNED_TRAINING_REVIEW_IDENTITY_CHANGED")
        # This grants only the exact reviewed target/rights resource. It cannot
        # authorize a model/recipe/dataset execution resource or a phase task.
        token = gate.grant_approval(p.OperationType.MODEL_TRAIN.value, resource=resource,
                                   duration_minutes=5, granted_by=identity["caller"])
        result = training_review.submit_training_review(gate=gate, **args)
        _, current_scope, _, current_identity = _owned_training_review_api_scope("write")
        if (current_scope, current_identity) != (scope, identity):
            raise PermissionError("OWNED_TRAINING_REVIEW_IDENTITY_CHANGED")
        return jsonify({"ok": True, **result, "confirmed_resource": resource,
                        "scope_permission_audit_id": scoped.audit_id,
                        "training_started": False, "execution_approval_issued": False})
    except Exception as exc:
        return _source_brief_job_error(exc)
    finally:
        if token is not None:
            gate.revoke_approval(token)


@experience_bp.route("/api/experience/owned-training/review-exports", methods=["POST"])
def export_owned_training_reviews():
    """Export current signed review records; never train or accept client records."""
    from lumenis.shared.learning import training_cases
    from lumenis.system.security import permission as p
    try:
        body = _owned_training_review_api_body({"review_evidence_refs"})
        actor, scope, _, identity = _owned_training_review_api_scope("read")
        gate = p.get_permission_gate()
        if type(gate) is not p.PermissionGate or p.is_testing_bypass_enabled():
            raise PermissionError("OWNED_TRAINING_EXPORT_CANONICAL_PERMISSION_REQUIRED")
        resource = "owned_training_case_export:v1:" + hashlib.sha256(training_cases._json({
            "identity": identity, "scope": scope, "review_evidence_refs": body["review_evidence_refs"],
        }).encode()).hexdigest()
        def authorize():
            _, current_scope, scoped, current_identity = _owned_training_review_api_scope("read")
            if (current_scope, current_identity) != (scope, identity):
                raise PermissionError("OWNED_TRAINING_EXPORT_IDENTITY_MISMATCH")
            domain = "bmp" if scope["domain_id"] == "zbmp" else "cth"
            decision = gate.check(p.OperationType.DATA_EXPORT, resource=resource,
                                  caller=identity["caller"], domain_id=domain,
                                  risk_level=p.RiskLevel.MEDIUM)
            if (not decision.allowed or not decision.audit_id
                    or decision.permission_required != p.PermissionLevel.VERIFY):
                raise PermissionError("OWNED_TRAINING_EXPORT_READ_DENIED")
            return {"actor_id": identity["caller"], "scope": scope,
                    "permission_audit_ref": scoped.audit_id, "operation_audit_ref": decision.audit_id}
        records = training_cases.export_reviewed_training_records(
            body["review_evidence_refs"], actor_id=identity["caller"], expected_scope=scope,
            authorize=authorize, principal=actor if type(actor) is p.LocalWorkspacePrincipal else None,
            gate=gate,
        )
        authorize()
        return jsonify({"ok": True, "state": "TRAINING_RECORDS_EXPORTED", "records": records,
                        "scope": scope, "actor_ref": identity["caller"], "resource": resource,
                        "training_started": False, "execution_approval_issued": False})
    except Exception as exc:
        return _source_brief_job_error(exc)


def _owned_training_phase_material(body):
    """Bind the private phase owner to fresh server identity and exact training inputs."""
    from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest
    from lumenis.system.security import permission as p

    data = body.get("training_request")
    fields = {"model_id", "model_revision", "train_sha256", "heldout_sha256", "scopes",
              "recipe", "manifest_sha256", "domain_id"}
    if type(data) is not dict or set(data) != fields or type(data.get("scopes")) is not list:
        raise ValueError("OWNED_TRAINING_PHASE_INPUT_INVALID")
    typed = TrainingApprovalRequest(**{**data, "scopes": tuple(data["scopes"])})
    actor, selected, scoped = _content_project_scope(
        "write", module="owned_training", include_decision=True, read_only_auth=True,
    )
    domain = "cth" if selected["domain_id"] == "cth" else "bmp"
    context = {"scope_descriptors": body.get("scope_descriptors")}
    identity_args = ({"principal": actor} if type(actor) is p.LocalWorkspacePrincipal
                     else {"actor_id": actor["id"]})
    identity = p.owned_training_identity(**identity_args)
    fingerprints = p.owned_training_phase_fingerprints(
        typed, domain_id=domain, context=context, **identity_args,
    )
    binding = {
        "resource": p.owned_training_approval_resource(
            typed, domain_id=domain, context=context, **identity_args,
        ),
        "identity": {name: identity[name] for name in
                     ("actor_id", "caller", "principal_kind", "principal_ref")},
        "scope_descriptors": context["scope_descriptors"],
    }
    gate = p.get_permission_gate()
    if type(gate) is not p.PermissionGate or not gate.fail_closed or p.is_testing_bypass_enabled():
        raise PermissionError("OWNED_TRAINING_PHASE_PERMISSION_UNAVAILABLE")
    verifier = p.make_owned_training_approval_verifier(
        gate, domain_id=domain, context=context, **identity_args,
    )

    def fresh_approval():
        if identity.get("actor_id") is not None:
            from lumenis.auth.service import get_current_user
            current = get_current_user(read_only=True)
            if type(current) is not dict or current.get("id") != identity["actor_id"]:
                raise PermissionError("OWNED_TRAINING_PHASE_IDENTITY_CHANGED")
        if not verifier(typed):
            raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
        approval = gate.check(
            p.OperationType.MODEL_TRAIN, resource=binding["resource"], caller=identity["caller"],
            domain_id=domain, exact_approval_required=True,
        )
        if not approval.allowed or not approval.requires_approval or not approval.approval_token:
            raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
        return approval

    return typed, context, identity_args, domain, binding, fingerprints, gate, fresh_approval


@experience_bp.route("/api/experience/owned-training/execution-approvals", methods=["POST"])
def confirm_owned_training_execution_approval():
    """Confirm one explicit training resource through the real Permission owner.

    A preview creates no grant. A confirmed request carries the operator's
    training intent; it neither starts a trainer nor replaces source admission.
    Approval tokens and signing material remain in the Core.
    """
    from lumenis.system.security import permission as p
    token = None
    try:
        body = _owned_training_review_api_body({
            "training_request", "scope_descriptors", "confirmed_resource", "confirm",
        })
        if type(body["confirm"]) is not bool:
            raise ValueError("OWNED_TRAINING_EXECUTION_CONFIRMATION_INVALID")
        typed, context, args, domain, binding, fingerprints, gate, fresh = _owned_training_phase_material(body)
        if (not gate.has_permission(p.PermissionLevel.HUMAN_APPROVAL)
                or not gate.has_permission(p.PermissionLevel.COMMIT)):
            raise PermissionError("OWNED_TRAINING_EXECUTION_MANUAL_AUTHORITY_REQUIRED")
        if body["confirm"] is False:
            if body["confirmed_resource"] is not None:
                raise ValueError("OWNED_TRAINING_EXECUTION_PREVIEW_INVALID")
            return jsonify({"ok": True, "state": "EXECUTION_RESOURCE_PREPARED",
                            "resource": binding["resource"], "fingerprints": fingerprints,
                            "identity": binding["identity"], "scope_descriptors": context["scope_descriptors"],
                            "approval_issued": False, "training_started": False})
        if (type(body["confirmed_resource"]) is not str
                or body["confirmed_resource"] != binding["resource"]):
            raise PermissionError("OWNED_TRAINING_EXECUTION_RESOURCE_CHANGED")
        _, _, _, current_domain, current_binding, current_fingerprints, current_gate, _ = _owned_training_phase_material(body)
        if (current_binding != binding or current_fingerprints != fingerprints
                or current_domain != domain or current_gate is not gate):
            raise PermissionError("OWNED_TRAINING_EXECUTION_IDENTITY_CHANGED")
        token = gate.grant_approval(p.OperationType.MODEL_TRAIN.value, resource=binding["resource"],
                                   duration_minutes=15, granted_by=binding["identity"]["caller"])
        approval = fresh()
        reference = gate.owned_training_approval_reference(
            training_request=typed, context=context, domain_id=domain, approval=approval, **args,
        )
        _, _, _, final_domain, final_binding, final_fingerprints, final_gate, _ = _owned_training_phase_material(body)
        if (final_binding != binding or final_fingerprints != fingerprints
                or final_domain != domain or final_gate is not gate):
            raise PermissionError("OWNED_TRAINING_EXECUTION_IDENTITY_CHANGED")
        return jsonify({"ok": True, "state": "EXACT_EXECUTION_INTENT_GRANTED",
                        "resource": binding["resource"], "fingerprints": fingerprints,
                        "identity": binding["identity"], "approval_reference": reference,
                        "permission_audit_id": approval.audit_id, "duration_minutes": 15,
                        "approval_issued": True, "training_started": False})
    except Exception as exc:
        if token is not None:
            gate.revoke_approval(token)
        if str(exc) == "AUTH_REQUIRED":
            return jsonify({"ok": False, "code": "AUTH_REQUIRED", "training_started": False}), 401
        return _owned_training_phase_error(exc)


def _owned_training_phase_body(*, challenge=False, phase=False):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("OWNED_TRAINING_PHASE_INPUT_INVALID")
            result[key] = value
        return result

    def no_constant(_):
        raise ValueError("OWNED_TRAINING_PHASE_INPUT_INVALID")

    raw = request.stream.read(65537)
    if len(raw) > 65536 or not request.is_json:
        raise ValueError("OWNED_TRAINING_PHASE_INPUT_INVALID")
    body = json.loads(raw, object_pairs_hook=unique_object, parse_constant=no_constant)
    fields = ({"training_request", "scope_descriptors"}
              | ({"challenge"} if challenge else set())
              | ({"phase"} if phase else set()))
    if type(body) is not dict or set(body) != fields:
        raise ValueError("OWNED_TRAINING_PHASE_INPUT_INVALID")
    return body


def _owned_training_phase_reference(typed, context, args, domain, gate, fresh):
    approval = fresh()
    reference = gate.owned_training_approval_reference(
        training_request=typed, context=context, domain_id=domain, approval=approval, **args,
    )
    return approval, reference


@contextmanager
def _owned_training_phase_transaction():
    """Bound the entire staged transaction to the existing Task metadata owner."""
    import sqlite3
    from lumenis.shared.database import get_repository

    with get_repository().connection(timeout=30) as conn:
        conn.execute("BEGIN IMMEDIATE")
        capture = {"denied": False, "allow_commit": False}
        writes = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
        task_savepoints = {
            "sealed_training_phase_prepare", "sealed_training_phase_consume",
            "sealed_training_phase_interrupt",
        }
        schema_effects = {getattr(sqlite3, name) for name in (
            "SQLITE_ATTACH", "SQLITE_DETACH", "SQLITE_ALTER_TABLE", "SQLITE_REINDEX",
            "SQLITE_ANALYZE", "SQLITE_CREATE_INDEX", "SQLITE_CREATE_TABLE",
            "SQLITE_CREATE_TEMP_INDEX", "SQLITE_CREATE_TEMP_TABLE", "SQLITE_CREATE_TEMP_TRIGGER",
            "SQLITE_CREATE_TEMP_VIEW", "SQLITE_CREATE_TRIGGER", "SQLITE_CREATE_VIEW",
            "SQLITE_DROP_INDEX", "SQLITE_DROP_TABLE", "SQLITE_DROP_TEMP_INDEX",
            "SQLITE_DROP_TEMP_TABLE", "SQLITE_DROP_TEMP_TRIGGER", "SQLITE_DROP_TEMP_VIEW",
            "SQLITE_DROP_TRIGGER", "SQLITE_DROP_VIEW", "SQLITE_CREATE_VTABLE", "SQLITE_DROP_VTABLE",
        )}

        def authorize(action, first, second, database, _trigger):
            denied = (
                (action in writes and (database != "main" or first not in {"ai_task", "ai_task_step"}))
                or action in schema_effects
                or (action == sqlite3.SQLITE_TRANSACTION and first == "COMMIT" and not capture["allow_commit"])
                or (action == sqlite3.SQLITE_SAVEPOINT and (
                    first not in {"BEGIN", "ROLLBACK", "RELEASE"} or second not in task_savepoints
                ))
                or (action == sqlite3.SQLITE_PRAGMA and second is not None
                    and first.lower() not in {"table_info", "table_xinfo", "index_info", "index_list", "foreign_key_list"})
                or (action == sqlite3.SQLITE_FUNCTION and str(second).lower() == "load_extension")
            )
            if denied:
                capture["denied"] = True
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        def commit_metadata():
            if capture["denied"]:
                raise PermissionError("OWNED_TRAINING_PHASE_TRANSACTION_EFFECT_DENIED")
            capture["allow_commit"] = True
            try:
                conn.commit()
            finally:
                capture["allow_commit"] = False

        conn.set_authorizer(authorize)
        try:
            yield conn, commit_metadata
            if capture["denied"]:
                raise PermissionError("OWNED_TRAINING_PHASE_TRANSACTION_EFFECT_DENIED")
        except Exception:
            conn.rollback()
            if capture["denied"]:
                raise PermissionError("OWNED_TRAINING_PHASE_TRANSACTION_EFFECT_DENIED") from None
            raise
        finally:
            conn.set_authorizer(None)


def _commit_owned_training_phase(conn, typed, context, args, domain, gate, fresh, reference,
                                 *, task_id, mutation, state, commit):
    from lumenis.system.security.effect_fence import (
        EffectFence, TrainingPhaseMetadataFenceDecision, get_effect_fence,
    )

    approval, current = _owned_training_phase_reference(typed, context, args, domain, gate, fresh)
    if current != reference:
        raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REPLACED")
    fence = get_effect_fence()
    if type(fence) is not EffectFence:
        raise PermissionError("OWNED_TRAINING_PHASE_FENCE_UNAVAILABLE")
    decision = fence.authorize_training_phase_metadata(
        connection=conn, task_id=task_id, mutation=mutation, training_request=typed,
        context=context, domain_id=domain, gate=gate, approval=approval,
        approval_reference=reference, expected_state=state,
        capture_mode="owned_training_task_metadata", **args,
    )
    if (type(decision) is not TrainingPhaseMetadataFenceDecision or decision.allowed is not True
            or decision.effect_mode != "owned_training_task_metadata"
            or decision.model_execution_allowed is not False or decision.task_id != task_id
            or decision.mutation != mutation or decision.resource != reference["resource"]
            or decision.approval_token_sha256 != reference["approval_token_sha256"]
            or not decision.state_sha256 or not decision.permission_audit_id or not decision.fence_audit_id):
        raise PermissionError(getattr(decision, "code", "OWNED_TRAINING_PHASE_FENCE_UNAVAILABLE"))
    with gate.owned_training_phase_commit_lease(
        training_request=typed, context=context, domain_id=domain, approval=approval,
        connection=conn, expected_approval_reference=reference, **args,
    ):
        commit()


def _owned_training_historical_receipt_response(record, *, state="HISTORICAL_PHASE_RECEIPT"):
    # Historical bytes are recoverable evidence, never renewed phase authority.
    return {"ok": True, "state": state, "receipt": record["receipt"],
            "challenge": record["challenge"], "task": record["state"],
            "pinned_public_key": record["pinned_public_key"], "historical": True,
            "authorization_usable": False, "model_execution_claimed": False}


@experience_bp.route("/api/experience/owned-training/phase-tasks", methods=["POST"])
def prepare_owned_training_phase_task():
    """Prepare a durable phase task only under an existing exact MODEL_TRAIN approval."""
    from ai_task_engine import get_task_engine
    from lumenis.shared.database import get_repository
    from lumenis.system.security import training_receipts as receipts

    try:
        body = _owned_training_phase_body()
        typed, context, args, domain, binding, fingerprints, gate, fresh = _owned_training_phase_material(body)
        fresh()
        public_key = receipts.get_training_receipt_public_key()
        engine = get_task_engine()
        with _owned_training_phase_transaction() as (conn, commit):
            try:
                _, reference = _owned_training_phase_reference(typed, context, args, domain, gate, fresh)
                state = engine.create_training_receipt_task(
                    binding=binding, fingerprints=fingerprints, connection=conn,
                    approval_reference=reference, pinned_public_key=public_key,
                )
                if state.get("admission_version") != 2:
                    raise PermissionError("OWNED_TRAINING_PHASE_SEALED_ADMISSION_REQUIRED")
                _commit_owned_training_phase(conn, typed, context, args, domain, gate, fresh, reference,
                                             task_id=state["task_id"], mutation="create", state=state, commit=commit)
            except Exception:
                conn.rollback()
                raise
        public_state = {key: value for key, value in state.items() if key != "task_id"}
        return jsonify({"ok": True, "state": "PHASE_TASK_PREPARED", "task_id": state["task_id"],
                        "public_challenge_context": public_state, "pinned_public_key": public_key,
                        "training_started": False, "approval_issued": False})
    except Exception as exc:
        return _owned_training_phase_error(exc)


_OWNED_TRAINING_PARENT_LOCK = threading.RLock()
# Retained OS handles only. Canonical Task, checkpoint and result state stays
# with TaskEngine/Shared Artifact; this map never grants authority.
_OWNED_TRAINING_PARENT_FENCES = {}


def _owned_training_parent_profile(body, domain):
    from pathlib import Path
    from lumenis.system.ai_gateway.owned_training import TrainingBlocked
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins

    root = Path(__file__).resolve().parent
    path = Path(os.environ.get("LUMENIS_TRAINING_PARENT_SPEC_PATH",
                               str(root / "config/ai-owned-training-runtime.json")))
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise TrainingBlocked("TRAINING_PARENT_SPEC_NOT_CONFIGURED")
    document = json.loads(path.read_bytes())
    profiles = document.get("profiles")
    if type(profiles) is not list:
        raise TrainingBlocked("TRAINING_PARENT_SPEC_INVALID")
    matches = [profile for profile in profiles if type(profile) is dict
               and profile.get("domain_id") == domain and profile.get("request_body") == body]
    if (len(matches) != 1 or document.get("worker_source_pins") != training_worker_source_pins(root)):
        raise TrainingBlocked("TRAINING_PARENT_INPUT_VERSION_CHANGED")
    profile = matches[0]
    if (Path(profile["controller_source_root"]) != root
            or profile["local_invocation"]["manifest_path"] != str(root / "config/ai-owned-foundation.json")
            or profile["local_invocation"].get("resume_request") is not None
            or profile["local_invocation"].get("stop_after_checkpoint_step") != 2):
        raise TrainingBlocked("TRAINING_PARENT_SPEC_INVALID")
    return root, document, profile


def _owned_training_parent_endpoint(pins, configuration_reference=None):
    from pathlib import Path
    from lumenis.system.ai_gateway.owned_training import TrainingBlocked
    from lumenis.system.ai_gateway.owned_training_ssh import SSHTrainingEndpoint

    # Safe startup intentionally does not import arbitrary .env fields. This
    # SYSTEM private configuration has an explicit local application default.
    local_root = os.environ.get("LOCALAPPDATA")
    if not local_root and os.name == "nt":
        import ctypes
        folder = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x001C, None, 0, folder) != 0:
            raise TrainingBlocked("TRAINING_SSH_ENDPOINT_NOT_CONFIGURED")
        local_root = folder.value
    default = (str(Path(local_root) / "LUMENIS/runtime/owned-training-ssh-endpoint.json")
               if local_root else None)
    configured = configuration_reference or os.environ.get("LUMENIS_TRAINING_SSH_ENDPOINT_PATH") or default
    if not configured:
        raise TrainingBlocked("TRAINING_SSH_ENDPOINT_NOT_CONFIGURED")
    path = Path(configured)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise TrainingBlocked("TRAINING_SSH_ENDPOINT_NOT_CONFIGURED")
    value = json.loads(path.read_bytes())
    fields = {"ssh_executable", "host", "port", "user", "identity_file", "known_hosts",
              "remote_python", "source_root", "source_pins"}
    if type(value) is not dict or set(value) != fields or value["source_pins"] != pins:
        raise TrainingBlocked("TRAINING_SSH_ENDPOINT_INVALID")
    # Private identity and known-host files remain in the real Core process.
    for name in ("ssh_executable", "identity_file", "known_hosts"):
        value[name] = Path(value[name])
    return SSHTrainingEndpoint(**value)


@experience_bp.route("/api/experience/owned-training/execution-configuration", methods=["POST"])
def read_owned_training_execution_configuration():
    """Observe this serving process's effective binding without disclosing it."""
    try:
        body = _owned_training_phase_body()
        _, _, _, domain, _, _, _, fresh = _owned_training_phase_material(body)
        fresh()
        _, specification, _ = _owned_training_parent_profile(body, domain)
        _owned_training_parent_endpoint(specification["worker_source_pins"],
            specification.get("private_endpoint_configuration_reference"))
        fresh()
        return jsonify({"ok": True, "state": "PARENT_CONFIGURATION_BOUND", "serving_pid": os.getpid(),
                        "configuration_revision": "owned-parent-private-config-3",
                        "endpoint_present": True, "exact_source_pins": True,
                        "training_started": False})
    except Exception as exc:
        response, status = _owned_training_phase_error(exc)
        value = response.get_json()
        from pathlib import Path
        selected_spec = Path(os.environ.get("LUMENIS_TRAINING_PARENT_SPEC_PATH",
            str(Path(__file__).resolve().parent / "config/ai-owned-training-runtime.json")))
        observed_spec = json.loads(selected_spec.read_bytes()) if selected_spec.is_file() else {}
        profile_reference = observed_spec.get("private_endpoint_configuration_reference")
        environment_reference = os.environ.get("LUMENIS_TRAINING_SSH_ENDPOINT_PATH")
        selected_reference = profile_reference or environment_reference
        selected_path = Path(selected_reference) if selected_reference else None
        def _private_file_probe(candidate):
            import hashlib
            result = {"reference_present": bool(candidate), "reference_is_absolute": False,
                      "reference_is_file": False, "reference_is_symlink": False,
                      "reference_sha256": hashlib.sha256(str(candidate or "").encode()).hexdigest()}
            if not candidate:
                return result
            probe = Path(candidate)
            result["reference_is_absolute"] = probe.is_absolute()
            try:
                result["reference_is_symlink"] = probe.is_symlink()
                result["reference_is_file"] = probe.is_file()
                result["reference_stat_mode"] = probe.stat().st_mode
                result["reference_bytes_sha256"] = hashlib.sha256(probe.read_bytes()).hexdigest()
            except Exception as probe_error:
                result.update(reference_error_class=type(probe_error).__name__,
                              reference_error_errno=getattr(probe_error, "errno", None),
                              reference_error_winerror=getattr(probe_error, "winerror", None))
            return result
        root_path = Path(__file__).resolve().parent
        expected_root = Path(r"D:\LUMENIS_REBUILD\序\序境")
        value.update(serving_pid=os.getpid(), configuration_revision="owned-parent-private-config-4",
                     environment_reference_present=bool(os.environ.get("LUMENIS_TRAINING_SSH_ENDPOINT_PATH")),
                     native_appdata_environment_present=bool(os.environ.get("LOCALAPPDATA")),
                     running_source_root_sha256=__import__("hashlib").sha256(str(root_path).encode()).hexdigest(),
                     running_source_root_matches_expected=root_path == expected_root,
                     selected_spec_bytes_sha256=__import__("hashlib").sha256(selected_spec.read_bytes()).hexdigest() if selected_spec.is_file() else None,
                     selected_spec_is_canonical=selected_spec == root_path / "config/ai-owned-training-runtime.json",
                     selected_profile_reference_present=bool(profile_reference),
                     selected_endpoint_is_absolute=selected_path.is_absolute() if selected_path else False,
                     selected_endpoint_is_file=selected_path.is_file() if selected_path else False,
                     selected_endpoint_is_symlink=selected_path.is_symlink() if selected_path else False,
                     selected_endpoint_probe=_private_file_probe(selected_reference))
        return jsonify(value), status


@experience_bp.route("/api/experience/owned-training/execution-preflight", methods=["POST"])
def preflight_owned_training_execution():
    """Verify the exact remote source binding without launching training or a model."""
    try:
        from lumenis.system.ai_gateway.owned_training_ssh import AuthenticatedSSHTrainingTransport

        body = _owned_training_phase_body()
        _, _, _, domain, _, _, _, fresh = _owned_training_phase_material(body)
        fresh()
        _, specification, _ = _owned_training_parent_profile(body, domain)
        endpoint = _owned_training_parent_endpoint(
            specification["worker_source_pins"],
            specification.get("private_endpoint_configuration_reference"),
        )
        observation = AuthenticatedSSHTrainingTransport(endpoint).preflight_source()
        if observation != {
            "state": "REMOTE_TRAINING_PREFLIGHT_SOURCE_PINS_VERIFIED",
            "source_pins_verified": True,
        }:
            raise RuntimeError("REMOTE_TRAINING_PREFLIGHT_INVALID")
        fresh()
        return jsonify({
            "ok": True,
            "state": "REMOTE_TRAINING_PREFLIGHT_BOUND",
            "configuration_revision": "owned-parent-remote-preflight-1",
            "endpoint_present": True,
            "exact_source_pins": True,
            "remote_source_pins_verified": True,
            "training_started": False,
            "model_loaded": False,
            "optimizer_steps": 0,
        })
    except Exception as exc:
        return _owned_training_phase_error(exc)


def _owned_training_parent_checkpoint(client):
    from lumenis.shared.database import get_repository

    client._fresh()
    with get_repository().connection(timeout=30) as connection:
        connection.execute("BEGIN")
        try:
            checkpoint = client._engine.training_checkpoint_latest_receipt(
                client.task_id, **client._args(connection))
            client._fresh()
            return checkpoint
        finally:
            connection.rollback()


@experience_bp.route("/api/experience/owned-training/phase-tasks/<task_id>/execute", methods=["POST"])
def execute_owned_training_phase_task(task_id):
    """Run the existing owned trainer, committed checkpoint and physical reload.

    The initiating real HTTP context owns the private parent for the complete
    call. No synthetic CLI principal, Core listener, queue or signer is created.
    A lost response leaves the canonical checkpoint receipt available.
    """
    import copy
    import uuid
    from pathlib import Path, PurePosixPath
    import requests
    import shared_artifacts
    from ai_task_engine import get_task_engine
    from lumenis.shared.database import get_repository
    from lumenis.system.security import training_receipts
    from lumenis.system.ai_gateway.owned_training import TrainingBlocked
    from lumenis.system.ai_gateway.owned_training_runtime import (
        OwnedTrainingCheckpointClient, OwnedTrainingPhaseHTTPTransport, TrainingProcessFence,
    )
    from lumenis.system.ai_gateway.owned_training_ssh import AuthenticatedSSHTrainingTransport

    worker = None
    session = None
    registered = False
    try:
        body = _owned_training_phase_body()
        typed, context, args, domain, binding, _, gate, fresh = _owned_training_phase_material(body)
        _, reference = _owned_training_phase_reference(typed, context, args, domain, gate, fresh)
        pin = training_receipts.get_training_receipt_public_key()
        engine = get_task_engine()
        with get_repository().connection(timeout=30) as connection:
            connection.execute("BEGIN")
            try:
                engine.require_training_receipt_admission(task_id, binding, reference, pin, connection)
                fresh()
            finally:
                connection.rollback()
        root, specification, profile = _owned_training_parent_profile(body, domain)
        endpoint = _owned_training_parent_endpoint(specification["worker_source_pins"],
            specification.get("private_endpoint_configuration_reference"))
        if not re.fullmatch(r"trainrelay_[0-9a-f-]{36}", task_id):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        with _OWNED_TRAINING_PARENT_LOCK:
            if task_id in _OWNED_TRAINING_PARENT_FENCES:
                raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
            _OWNED_TRAINING_PARENT_FENCES[task_id] = {"binding": binding, "worker": None}
            registered = True
        fresh()
        staging = shared_artifacts.artifact_root() / "training-checkpoints" / task_id
        staging.mkdir(mode=0o700, parents=True, exist_ok=True)
        worker = TrainingProcessFence(staging / "worker.lock")
        with _OWNED_TRAINING_PARENT_LOCK:
            _OWNED_TRAINING_PARENT_FENCES[task_id]["worker"] = worker
        transport = AuthenticatedSSHTrainingTransport(endpoint)
        start = {"python_executable": Path(profile["controller_python"]), "cwd": root,
                 "log_path": staging / "worker.stderr", "source_pins": specification["worker_source_pins"],
                 "remote_transport": transport}
        worker.start_managed_training(**start)
        client = OwnedTrainingCheckpointClient(typed, context, task_id=task_id, worker=worker,
            manifest_path=profile["local_invocation"]["manifest_path"], staging_root=staging,
            max_bytes=profile["max_checkpoint_bytes"],
            remote_storage_root=PurePosixPath(profile["intended_remote_storage_root"]), **args)
        client.initialize()
        session = requests.Session()
        session.trust_env = False
        session.verify = True
        for name in ("Authorization", "Cookie", "Origin", "Referer", "Sec-Fetch-Site",
                     "X-Domain-Id", "X-Product-Id", "X-Subject-ID", "X-Brand-Focus-ID",
                     "X-Lumenis-Context-Mode", "X-Lumenis-Action"):
            if name in request.headers:
                session.headers[name] = request.headers[name]
        phase_transport = OwnedTrainingPhaseHTTPTransport(core_origin="http://127.0.0.1:8201",
            session=session, pinned_public_key=pin)
        invocation = copy.deepcopy(profile["local_invocation"])
        call = {"client": client, "phase_transport": phase_transport,
                "timeout_seconds": profile["timeout_seconds"],
                "remote_input_paths": profile["intended_remote_input_paths"]}
        first_result = worker.invoke_owned_training(invocation=invocation, **call)
        checkpoint = _owned_training_parent_checkpoint(client)
        if checkpoint is None or checkpoint["completed_step"] != 2:
            raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
        fresh()
        worker.start_managed_training(replace=True, **start)
        # These references originate from the actual committed owner receipt;
        # no path or dictionary supplied by the caller proves checkpoint bytes.
        invocation["resume_request"] = {
            "operation_id": str(uuid.uuid4()), "checkpoint_ref": checkpoint["artifact_ref"],
            "expected_checkpoint_sha256": checkpoint["artifact_sha256"], "replay_through_step": 2,
        }
        invocation["stop_after_checkpoint_step"] = None
        resumed_result = worker.invoke_owned_training(invocation=invocation, **call)
        parent_ref = checkpoint["artifact_ref"]
        checkpoint = _owned_training_parent_checkpoint(client)
        if (checkpoint is None or checkpoint["completed_step"] <= 2
                or checkpoint["artifact_ref"] == parent_ref or checkpoint["parent_ref"] != parent_ref):
            raise TrainingBlocked("CHECKPOINT_TRAINING_CONTINUATION_NOT_OBSERVED")
        fresh()
        return jsonify({"ok": True, "state": "OWNED_TRAINING_CALL_RETURNED", "task_id": task_id,
                        "first_result": first_result, "resumed_result": resumed_result,
                        "checkpoint": checkpoint, "runtime_promotion": "NOT_PERFORMED"})
    except Exception as exc:
        return _owned_training_phase_error(exc)
    finally:
        # Stop/reap is owned by the fence and is required even after revocation.
        # A failed stop must remain an actual error, never a successful return.
        stopped = worker is None
        try:
            if worker is not None:
                worker.close()
                stopped = True
        finally:
            if session is not None:
                session.close()
            if registered and stopped:
                with _OWNED_TRAINING_PARENT_LOCK:
                    _OWNED_TRAINING_PARENT_FENCES.pop(task_id, None)


@experience_bp.route(
    "/api/experience/owned-training/phase-tasks/<task_id>/challenges", methods=["POST"],
)
def prepare_owned_training_phase_challenge(task_id):
    """Persist the one legal server-authored challenge; perform no model work."""
    from ai_task_engine import get_task_engine
    from lumenis.shared.database import get_repository
    from lumenis.system.security import training_receipts as receipts

    try:
        body = _owned_training_phase_body(phase=True)
        typed, context, args, domain, binding, _, gate, fresh = _owned_training_phase_material(body)
        fresh()
        public_key = receipts.get_training_receipt_public_key()
        engine = get_task_engine()
        with _owned_training_phase_transaction() as (conn, commit):
            try:
                _, reference = _owned_training_phase_reference(typed, context, args, domain, gate, fresh)
                engine.require_training_receipt_admission(task_id, binding, reference, public_key, conn)
                challenge = engine.prepare_training_phase_challenge(
                    task_id, binding, reference, public_key, body["phase"], conn,
                )
                state = engine.get_training_receipt_task(task_id, expected_binding=binding, connection=conn)
                _commit_owned_training_phase(conn, typed, context, args, domain, gate, fresh, reference,
                                             task_id=task_id, mutation="challenge", state=state, commit=commit)
            except Exception:
                conn.rollback()
                raise
        return jsonify({"ok": True, "state": "PHASE_CHALLENGE_PREPARED", "challenge": challenge,
                        "pinned_public_key": public_key, "model_execution_claimed": False})
    except Exception as exc:
        return _owned_training_phase_error(exc)


@experience_bp.route(
    "/api/experience/owned-training/phase-tasks/<task_id>/challenge-decisions", methods=["POST"],
)
def issue_owned_training_phase_decision(task_id):
    """Sign and durably consume one current challenge; never execute a model here."""
    from ai_task_engine import get_task_engine
    from lumenis.shared.database import get_repository
    from lumenis.system.security import training_receipts as receipts

    try:
        body = _owned_training_phase_body(challenge=True)
        typed, context, args, domain, binding, fingerprints, gate, fresh = _owned_training_phase_material(body)
        supplied = body["challenge"]
        challenge = receipts.validate_training_phase_challenge(
            supplied, now=supplied.get("issued_at") if type(supplied) is dict else None,
        )
        if any(challenge[name] != value for name, value in fingerprints.items()):
            raise PermissionError("OWNED_TRAINING_PHASE_BINDING_MISMATCH")
        fresh()
        public_key = receipts.get_training_receipt_public_key()
        engine = get_task_engine()
        with _owned_training_phase_transaction() as (conn, commit):
            try:
                _, reference = _owned_training_phase_reference(typed, context, args, domain, gate, fresh)
                engine.require_training_receipt_admission(task_id, binding, reference, public_key, conn)
                prior = engine.get_training_phase_receipt(task_id, binding, reference, challenge["nonce"], conn)
                if prior is not None:
                    if prior["challenge"] != challenge:
                        raise PermissionError("OWNED_TRAINING_PHASE_BINDING_MISMATCH")
                    _, current = _owned_training_phase_reference(typed, context, args, domain, gate, fresh)
                    if current != reference:
                        raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REPLACED")
                    conn.rollback()
                    return jsonify(_owned_training_historical_receipt_response(prior, state="PHASE_RECEIPT_ALREADY_COMMITTED"))
                challenge = engine.require_pending_training_phase_challenge(
                    task_id, binding, reference, public_key, challenge, conn,
                )
                signed = receipts.sign_training_phase_decision(challenge, "allow")
                receipts.verify_training_phase_decision(
                    signed, expected_challenge=challenge, pinned_public_key=public_key,
                )
                encoded = json.dumps(signed, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")
                state = engine.consume_training_phase_challenge(
                    task_id, expected_binding=binding, challenge=challenge,
                    receipt_sha256=hashlib.sha256(encoded).hexdigest(), decision="allow", connection=conn,
                    receipt=signed, expected_approval_reference=reference,
                )
                _commit_owned_training_phase(conn, typed, context, args, domain, gate, fresh, reference,
                                             task_id=task_id, mutation="receipt", state=state, commit=commit)
            except Exception:
                conn.rollback()
                raise
        return jsonify({"ok": True, "state": "PHASE_RECEIPT_COMMITTED", "receipt": signed,
                        "next_sequence": state["next_sequence"], "model_execution_claimed": False})
    except Exception as exc:
        return _owned_training_phase_error(exc)


@experience_bp.route(
    "/api/experience/owned-training/phase-tasks/<task_id>/receipts/<nonce>", methods=["GET"],
)
def read_owned_training_phase_receipt(task_id, nonce):
    """Read exact historical bytes under the still-live same grant and scope."""
    from ai_task_engine import get_task_engine
    from lumenis.auth.service import get_current_user
    from lumenis.shared.database import get_repository
    from lumenis.system.security import permission as p

    try:
        actor = get_current_user(read_only=True)
        if type(actor) is dict and type(actor.get("id")) is int and actor["id"] > 0:
            args = {"actor_id": actor["id"]}
        else:
            principal = p.resolve_local_workspace_principal(module="owned_training", action="write")
            if principal is None:
                raise PermissionError("OWNED_TRAINING_PHASE_AUTH_REQUIRED")
            args = {"principal": principal}
        identity = p.owned_training_identity(**args)
        expected = {name: identity[name] for name in ("actor_id", "caller", "principal_kind", "principal_ref")}
        gate = p.get_permission_gate()
        if type(gate) is not p.PermissionGate or not gate.fail_closed or p.is_testing_bypass_enabled():
            raise PermissionError("OWNED_TRAINING_PHASE_PERMISSION_UNAVAILABLE")
        engine = get_task_engine()
        with get_repository().connection(timeout=30) as conn:
            conn.execute("BEGIN")
            try:
                material = engine.get_training_receipt_history_material(task_id, expected_identity=expected, connection=conn)
                reference = gate.owned_training_history_approval_reference(material["binding"], **args)
                if reference != material["approval_reference"]:
                    raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REPLACED")
                record = engine.get_training_phase_receipt(task_id, material["binding"], reference, nonce, conn)
                if gate.owned_training_history_approval_reference(material["binding"], **args) != reference:
                    raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REPLACED")
            finally:
                conn.rollback()
        if record is None:
            return jsonify({"ok": True, "state": "PHASE_RECEIPT_NOT_COMMITTED", "receipt": None,
                            "historical": True, "authorization_usable": False, "model_execution_claimed": False}), 202
        return jsonify(_owned_training_historical_receipt_response(record))
    except Exception as exc:
        return _owned_training_phase_error(exc)


def _change_owned_training_phase_task_state(task_id, *, resume):
    from ai_task_engine import get_task_engine
    from lumenis.shared.database import get_repository
    from lumenis.system.security import training_receipts as receipts

    body = _owned_training_phase_body()
    typed, context, args, domain, binding, _, gate, fresh = _owned_training_phase_material(body)
    fresh()
    stopped = None
    if not resume:
        with _OWNED_TRAINING_PARENT_LOCK:
            retained = _OWNED_TRAINING_PARENT_FENCES.get(task_id)
            if retained is not None and retained["binding"] != binding:
                raise PermissionError("OWNED_TRAINING_PHASE_IDENTITY_CHANGED")
            worker = None if retained is None else retained["worker"]
        if worker is not None:
            stopped = worker.stop_and_reap()
            fresh()
    public_key = receipts.get_training_receipt_public_key()
    engine = get_task_engine()
    with _owned_training_phase_transaction() as (conn, commit):
        try:
            _, reference = _owned_training_phase_reference(typed, context, args, domain, gate, fresh)
            engine.require_training_receipt_admission(task_id, binding, reference, public_key, conn)
            change = engine.resume_training_receipt_task if resume else engine.interrupt_training_receipt_task
            state = change(task_id, expected_binding=binding, connection=conn)
            _commit_owned_training_phase(conn, typed, context, args, domain, gate, fresh, reference,
                                         task_id=task_id, mutation="resume" if resume else "interrupt", state=state, commit=commit)
        except Exception:
            conn.rollback()
            raise
    return jsonify({"ok": True, "state": "PHASE_TASK_RESUMED" if resume else "PHASE_TASK_INTERRUPTED",
                    "task": state, "model_execution_claimed": False,
                    "trainer_process_stopped": stopped is not None,
                    "trainer_stop_receipt": stopped})


@experience_bp.route("/api/experience/owned-training/phase-tasks/<task_id>/interrupt", methods=["POST"])
def interrupt_owned_training_phase_task(task_id):
    try:
        return _change_owned_training_phase_task_state(task_id, resume=False)
    except Exception as exc:
        return _owned_training_phase_error(exc)


@experience_bp.route("/api/experience/owned-training/phase-tasks/<task_id>/resume", methods=["POST"])
def resume_owned_training_phase_task(task_id):
    try:
        return _change_owned_training_phase_task_state(task_id, resume=True)
    except Exception as exc:
        return _owned_training_phase_error(exc)


def _owned_training_phase_error(exc):
    import sqlite3
    from lumenis.system.security.training_receipts import TrainingReceiptConfigurationError

    if isinstance(exc, TrainingReceiptConfigurationError):
        return jsonify({"ok": False, "code": "OWNED_TRAINING_PHASE_SIGNING_UNAVAILABLE"}), 503
    code = _content_project_error_code(exc)
    status = (403 if isinstance(exc, PermissionError) else
              409 if isinstance(exc, (KeyError, RuntimeError, sqlite3.IntegrityError)) else 400)
    return jsonify({"ok": False, "code": code, "training_started": False}), status


def _content_project_error_code(exc):
    code = str(exc)
    # Only known code-shaped errors are safe to serialize; never return filesystem paths.
    if not code or len(code) > 100 or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789" for character in code):
        code = "CONTENT_PROJECT_FAILED"
    return code


def _content_project_error(exc):
    code = _content_project_error_code(exc)
    status = 507 if code == "CONTENT_MEDIA_STORAGE_REQUIRED" else 503 if code.endswith("_UNAVAILABLE") or code == "CONTENT_MEDIA_RESOURCE_BUSY" else 404 if code.endswith("_NOT_FOUND") else 401 if code == "AUTH_REQUIRED" else 403 if code in {
        "CONTENT_SCOPE_DENIED", "ACTOR_SCOPE_PERMISSION_DENIED", "DOMAIN_REQUIRED", "CONTEXT_SCOPE_MISMATCH",
        "CONTENT_PROJECT_CONTEXT_MISMATCH", "CONTENT_PROJECT_PARENT_SCOPE_MISMATCH",
        "CONTENT_SOURCE_CONTEXT_MISMATCH", "CONTENT_SOURCE_SCOPE_DENIED",
        "CONTENT_SOURCE_USE_PERMISSION_REQUIRED",
        "CONTENT_SOURCE_ORIGIN_DENIED",
        "CONTENT_SOURCE_APPROVAL_REQUIRED", "CONTENT_EXPORT_PERMISSION_DENIED",
        "OWNED_TRAINING_PREVIEW_DENIED",
    } else 400
    return jsonify({"ok": False, "code": code, "publish_status": "not_performed"}), status


def _source_brief_context(action, *, include_actor=False, module="reports"):
    """Bind reporting to the same server principal, registry and scope as work."""
    from lumenis.shared.database import get_repository
    from subject_registry import TABLE_NAME

    if _SHARED_WORKSPACE_SCOPE_HEADER in request.headers:
        if module != "reports" or not _shared_research_route_allowed():
            raise ValueError("SHARED_WORKSPACE_SCOPE_NOT_SUPPORTED")
        from lumenis.auth.service import get_current_user
        from lumenis.system.security import permission
        scope = _parse_shared_workspace_scope_header()
        actor = permission.resolve_local_workspace_principal(module="reports", action=action)
        if actor is None:
            actor = get_current_user(read_only=True)
        if actor is None:
            raise PermissionError("AUTH_REQUIRED")
        identity, audit_id = permission.authorize_shared_workspace(
            actor, scope, module="reports", action=action, _return_audit=True)
        actor_ref = identity.get("principal_ref") or f"actor:{identity.get('actor_id')}"
        result = actor_ref, audit_id, scope
        return (*result, actor) if include_actor else result

    actor, scope, decision = _content_project_scope(
        action, module=module, include_decision=True,
    )
    label = "全球商业" if scope["domain_id"] == "cth" else "全球品牌"
    if not scope["global_scope"]:
        field = "subject_id" if scope["domain_id"] == "cth" else "brand_focus_id"
        con = get_repository().connect(read_only=True, wal=False)
        try:
            row = con.execute(
                f"SELECT name_zh,name_en FROM {TABLE_NAME} WHERE {field}=? AND domain_id=?",
                (scope[field], "CTH" if field == "subject_id" else "BMP"),
            ).fetchone()
        finally:
            con.close()
        if row is None or not (row[0] or row[1]):
            raise ValueError("CONTENT_SCOPE_NOT_FOUND")
        label = row[0] or row[1]
    actor_ref = decision.principal_ref or f"actor:{decision.actor_id}"
    result = actor_ref, decision.audit_id, {
        "product_id": "CTH" if scope["domain_id"] == "cth" else "ZBMP",
        "global_scope": scope["global_scope"], "entity_label": label,
        "subject_id": scope["subject_id"], "brand_focus_id": scope["brand_focus_id"],
    }
    return (*result, actor) if include_actor else result


def _with_committed_readback_state(result, exc):
    """Add a non-success persistence hint without changing denial semantics."""
    from lumenis.shared.reporting.saved_work import committed_readback_state
    state = committed_readback_state(exc)
    if state is not None:
        response = result[0] if isinstance(result, tuple) else result
        body = response.get_json(silent=True)
        if isinstance(body, dict):
            body["persistence_state"] = state
            response.set_data(json.dumps(body))
            response.headers["Cache-Control"] = "no-store"
    return result


def _source_brief_job_error(exc):
    code = _content_project_error_code(exc)
    if isinstance(exc, PermissionError) or code == "WORK_PERMISSION_DENIED":
        status = 403
    elif isinstance(exc, LookupError):
        status = 404
    elif isinstance(exc, RuntimeError):
        status = 409 if "CONFLICT" in code or "STOPPING" in code else 503
    else:
        return _with_committed_readback_state(_content_project_error(exc), exc)
    return _with_committed_readback_state((jsonify({"ok": False, "code": code, "publish_status": "not_performed"}), status), exc)


_SHARED_WORKSPACE_SCOPE_HEADER = "X-Lumenis-Workspace-Scope"
_SHARED_WORKSPACE_LEGACY_SCOPE_HEADERS = frozenset({
    "x-domain-id", "x-product-id", "x-lumenis-context-mode",
    "x-subject-id", "x-brand-focus-id",
    "x-actor-id", "x-user-id", "x-lumenis-actor-id", "x-lumenis-user-id",
    "x-principal-id", "x-principal-ref", "x-project-id", "x-workspace-id",
    "x-lumenis-project-id", "x-lumenis-workspace-id",
})
_SHARED_WORKSPACE_CLIENT_IDENTITY_ARGS = frozenset({
    "actor_id", "user_id", "principal_kind", "principal_ref",
    "workspace_id", "project_id", "domain_id", "product_id",
    "context_mode", "subject_id", "brand_focus_id", "global_scope",
})


def _shared_research_route_allowed():
    if request.endpoint == 'experience_runtime.research_hypothesis_review':
        return request.url_rule is not None and (request.url_rule.rule,request.method) in {
            ('/api/experience/reports/source-brief/jobs/<job_id>/hypotheses','GET'),
            ('/api/experience/reports/source-brief/jobs/<job_id>/hypotheses/review','POST')}
    if request.endpoint == 'experience_runtime.research_reference_library':
        return request.url_rule is not None and (request.url_rule.rule, request.method) in {
            ('/api/experience/reports/source-brief/reference-library', 'GET'),
            ('/api/experience/reports/source-brief/reference-library', 'POST'),
            ('/api/experience/reports/source-brief/reference-library/<int:evidence_id>', 'GET')}
    if request.endpoint == 'experience_runtime.research_learning':
        return request.url_rule is not None and (request.url_rule.rule, request.method) in {
            ('/api/experience/reports/source-brief/learning/<kind>', 'GET'),
            ('/api/experience/reports/source-brief/learning/<kind>', 'POST'),
            ('/api/experience/reports/source-brief/learning/<kind>/<object_id>', 'GET'),
            ('/api/experience/reports/source-brief/learning/<kind>/<object_id>/<operation>', 'POST')}
    if request.blueprint != "experience_runtime" or request.url_rule is None:
        return False
    routes = {
        "generate_source_brief_job": ("/api/experience/reports/source-brief/generate", {"POST"}),
        "reopen_source_brief_job": ("/api/experience/reports/source-brief/jobs/<job_id>", {"GET"}),
        "submit_source_brief_review": ("/api/experience/reports/source-brief/jobs/<job_id>/reviews", {"POST"}),
        "start_source_brief_task": ("/api/experience/reports/source-brief/start", {"POST"}),
        "source_brief_task_status": ("/api/experience/reports/source-brief/tasks/<task_id>", {"GET"}),
        "resume_source_brief_task": ("/api/experience/reports/source-brief/tasks/<task_id>/resume", {"POST"}),
        "list_source_brief_tasks": ("/api/experience/reports/source-brief/tasks", {'GET'}),
        "edit_source_brief_task": ("/api/experience/reports/source-brief/tasks/<task_id>", {'PATCH'}),
        "change_source_brief_task_state": ("/api/experience/reports/source-brief/tasks/<task_id>/<operation>", {'POST'}),
        "research_reference_catalog": ("/api/experience/reports/source-brief/references", {'GET'}),
        "research_taxonomy": ("/api/experience/reports/source-brief/taxonomy", {'GET'}),
        "save_source_brief_result": ("/api/experience/reports/source-brief/jobs/<job_id>/save", {'POST'}),
        'research_reference_work': ('/api/experience/reports/source-brief/reference-work', {'POST', 'GET'}),
        'research_reference_version': ('/api/experience/reports/source-brief/reference-work/<artifact_id>', {'POST', 'GET'}),
        'research_match_rules': ('/api/experience/reports/source-brief/references/match-rules', {'POST'}),
        "list_research_reports": ("/api/experience/reports/source-brief/jobs", {'GET'}),
    }
    expected = routes.get(request.endpoint.split(".")[-1])
    return expected is not None and request.url_rule.rule == expected[0] and request.method in expected[1]


def _shared_saved_work_route_allowed():
    if _artifact_experiment_route_matches():
        return True
    routes = {
        "experience_runtime.work_dependency_workflow": (
            "/api/experience/work-dependencies", "POST", r"/api/experience/work-dependencies"),
        "experience_runtime.save_shared_work": (
            "/api/experience/saved-work", "POST", r"/api/experience/saved-work"),
        "experience_runtime.import_shared_document": (
            "/api/experience/materials/documents", "POST", r"/api/experience/materials/documents"),
        "experience_runtime.download_work_attachment": (
            "/api/experience/saved-work/<artifact_id>/attachments/<name>", "GET",
            r"/api/experience/saved-work/ART-[0-9a-f]{16}/attachments/[A-Za-z0-9_.-]{1,100}"),
        "experience_runtime.revise_shared_work": (
            "/api/experience/saved-work/<artifact_id>/revise", "POST",
            r"/api/experience/saved-work/ART-[0-9a-f]{16}/revise"),
        "experience_runtime.read_office_document": (
            "/api/experience/saved-work/<artifact_id>/office", "GET",
            r"/api/experience/saved-work/ART-[0-9a-f]{16}/office"),
        "experience_runtime.edit_office_document": (
            "/api/experience/saved-work/<artifact_id>/office/edit", "POST",
            r"/api/experience/saved-work/ART-[0-9a-f]{16}/office/edit"),
        "experience_runtime.search_shared_work": (
            "/api/experience/saved-work", "GET", r"/api/experience/saved-work"),
        "experience_runtime.read_shared_work": (
            "/api/experience/saved-work/<artifact_id>", "GET",
            r"/api/experience/saved-work/ART-[0-9a-f]{16}"),
        "experience_runtime.export_shared_work": (
            "/api/experience/saved-work/<artifact_id>/export", "GET",
            r"/api/experience/saved-work/ART-[0-9a-f]{16}/export"),
    }
    expected = routes.get(request.endpoint)
    return (expected is not None and request.url_rule is not None
            and request.url_rule.rule == expected[0] and request.method == expected[1]
            and re.fullmatch(expected[2], request.path) is not None)


def _shared_content_project_route_allowed():
    """Limit Shared scope headers to existing Content owner routes."""
    if request.blueprint == "content_generation" and request.url_rule is not None:
        from content_generation import CONTENT_ENDPOINTS
        contract = CONTENT_ENDPOINTS.get(request.endpoint.split(".")[-1])
        return bool(contract and request.url_rule.rule == contract[0] and request.method in contract[1])
    routes = {
        "experience_runtime.screen_viewmodel": (
            "/api/experience/screen/<screen_id>", "GET", r"/api/experience/screen/SH-(?:01|05)"),
        "experience_runtime.content_evidence_detail": (
            "/api/experience/content/evidence/<evidence_id>", "GET",
            r"/api/experience/content/evidence/CGE-[A-Za-z0-9_-]{1,96}"),
        "experience_runtime.inspect_content_project_media": (
            "/api/experience/shared-skills/shared.content_project/inspect", "POST",
            r"/api/experience/shared-skills/shared\.content_project/inspect"),
        "experience_runtime.import_content_source": (
            "/api/experience/content-sources", "POST", r"/api/experience/content-sources"),
        "experience_runtime.confirm_content_source_import_request": (
            "/api/experience/content-source-confirmations/<confirmation_id>", "POST",
            r"/api/experience/content-source-confirmations/[A-Za-z0-9_-]{32,128}"),
        "experience_runtime.content_source_detail": (
            "/api/experience/content-sources/<artifact_id>", ("GET", "HEAD"),
            r"/api/experience/content-sources/ART-(?:[0-9a-f]{16}|[0-9a-f]{32})"),
        "experience_runtime.export_content_project": (
            "/api/experience/content-projects/export", "POST",
            r"/api/experience/content-projects/export"),
        "experience_runtime.preview_content_speech": (
            "/api/experience/content-sources/tts/preview", "POST",
            r"/api/experience/content-sources/tts/preview"),
        "experience_runtime.content_speech_capabilities": (
            "/api/experience/content-sources/tts/capabilities", "GET",
            r"/api/experience/content-sources/tts/capabilities"),
        "experience_runtime.preview_podcast_topics": (
            "/api/experience/podcast/topics/preview", "POST",
            r"/api/experience/podcast/topics/preview"),
        "experience_runtime.preview_podcast_editorial": (
            "/api/experience/podcast/editorial/preview", "POST",
            r"/api/experience/podcast/editorial/preview"),
        "experience_runtime.prepare_content_edl": (
            "/api/experience/content-projects/<artifact_id>/edl/prepare", "POST",
            r"/api/experience/content-projects/ART-[0-9a-f]{16}/edl/prepare"),
        "experience_runtime.apply_content_edl": (
            "/api/experience/content-projects/<artifact_id>/edl/apply", "POST",
            r"/api/experience/content-projects/ART-[0-9a-f]{16}/edl/apply"),
        "experience_runtime.content_project_list": (
            "/api/experience/content-projects", "GET", r"/api/experience/content-projects"),
        "experience_runtime.content_project_detail": (
            "/api/experience/content-projects/<artifact_id>", "GET",
            r"/api/experience/content-projects/ART-[0-9a-f]{16}"),
        "experience_runtime.content_project_package": (
            "/api/experience/content-projects/<artifact_id>/package", ("GET", "HEAD"),
            r"/api/experience/content-projects/ART-[0-9a-f]{16}/package"),
        "experience_runtime.content_project_media": (
            "/api/experience/content-projects/<artifact_id>/media", ("GET", "HEAD"),
            r"/api/experience/content-projects/ART-[0-9a-f]{16}/media"),
    }
    expected = routes.get(request.endpoint)
    return (expected is not None and request.url_rule is not None
            and request.url_rule.rule == expected[0]
            and request.method in (expected[1] if isinstance(expected[1], tuple) else (expected[1],))
            and re.fullmatch(expected[2], request.path) is not None)


def _parse_shared_workspace_scope_header(headers=None):
    """Parse the exact actor-free Shared workspace wire scope."""
    headers = request.headers if headers is None else headers
    values = headers.getlist(_SHARED_WORKSPACE_SCOPE_HEADER)
    if (len(values) != 1 or not isinstance(values[0], str)
            or len(values[0].encode("utf-8")) > 256):
        raise ValueError("SHARED_WORKSPACE_SCOPE_INVALID")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("SHARED_WORKSPACE_SCOPE_INVALID")
            result[key] = value
        return result

    try:
        scope = json.loads(
            values[0], object_pairs_hook=unique_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("SHARED_WORKSPACE_SCOPE_INVALID")),
        )
        from lumenis.system.security.permission import validate_shared_workspace_scope

        scope = validate_shared_workspace_scope(scope)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("SHARED_WORKSPACE_SCOPE_INVALID") from exc
    header_names = {name.casefold() for name in headers.keys()}  # noqa: SIM118 - Werkzeug Headers iterates pairs.
    if header_names.intersection(_SHARED_WORKSPACE_LEGACY_SCOPE_HEADERS):
        raise ValueError("SHARED_WORKSPACE_SCOPE_MIXED_CONTEXT")
    if _SHARED_WORKSPACE_CLIENT_IDENTITY_ARGS.intersection(request.args):
        raise ValueError("SHARED_WORKSPACE_SCOPE_MIXED_CONTEXT")
    return scope


def _shared_work_actor_scope(action):
    if _SHARED_WORKSPACE_SCOPE_HEADER in request.headers:
        if not _shared_saved_work_route_allowed():
            raise ValueError("SHARED_WORKSPACE_SCOPE_NOT_SUPPORTED")
        from lumenis.auth.service import get_current_user
        from lumenis.shared.reporting.saved_work import authorize_saved_work
        from lumenis.system.security.permission import resolve_local_workspace_principal

        scope = _parse_shared_workspace_scope_header()
        actor = resolve_local_workspace_principal(module="reports", action=action)
        if actor is None:
            actor = get_current_user(read_only=True)
        if actor is None:
            raise PermissionError("AUTH_REQUIRED")
        authorize_saved_work(actor, scope, action=action)
        return actor, scope

    from lumenis.shared.reporting.saved_work import authorize
    _actor_ref, _audit, material, actor = _source_brief_context(action, include_actor=True)
    scope = {"domain_id": "cth" if material["product_id"] == "CTH" else "zbmp",
             "subject_id": material["subject_id"], "brand_focus_id": material["brand_focus_id"],
             "global_scope": material["global_scope"]}
    authorize(actor, scope, action=action)
    return actor, scope


def _bmp_saved_work_actor_scope(binding):
    """Exact BMP-09 read delegation; screen permission never grants report access."""
    if not (request.method == "GET" and request.endpoint == "experience_runtime.screen_viewmodel"
            and request.url_rule is not None
            and request.url_rule.rule == "/api/experience/screen/<screen_id>"
            and (request.view_args or {}).get("screen_id") == "BMP-09"):
        raise PermissionError("BMP_REPORT_ROUTE_UNAUTHORIZED")
    if _SHARED_WORKSPACE_SCOPE_HEADER in request.headers:
        raise ValueError("BMP_REPORT_SCOPE_REQUIRED")
    current, denial = _bmp01_read_scope()
    if denial is not None or current != binding:
        raise PermissionError("BMP_REPORT_SCOPE_CHANGED")
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import resolve_local_workspace_principal
    from lumenis.shared.reporting.saved_work import authorize
    actor = resolve_local_workspace_principal(module="reports", action="read")
    if actor is None:
        actor = get_current_user(read_only=True)
    if actor is None:
        raise PermissionError("AUTH_REQUIRED")
    scope = {"domain_id": "zbmp", "subject_id": None,
             "brand_focus_id": binding["brand_focus_id"],
             "global_scope": binding["canonical_scope"] == "GLOBAL_ALL"}
    authorize(actor, scope, action="read")
    return actor, scope


def _shared_work_response(call):
    from flask import current_app
    try:
        result = call()
        if not isinstance(result, dict):
            return result
        response = jsonify({"ok": True, "result": result, "publish_status": "not_performed"})
        response.headers["Cache-Control"] = "no-store"
        return response
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        import re
        code = str(exc)
        if re.fullmatch(r"[A-Z_0-9]{1,100}", code) is None:
            code = "SHARED_WORK_UNAVAILABLE"
        if code == "AUTH_REQUIRED":
            status = 401
        elif isinstance(exc, PermissionError) or any(term in code for term in ("PERMISSION", "RIGHTS", "NOT_AUTHORIZED", "SCOPE_DENIED")):
            status = 403
        elif isinstance(exc, LookupError) or code in {"WORK_NOT_FOUND", "WORK_EVIDENCE_MISSING"}:
            status = 404
        elif isinstance(exc, RuntimeError) or "UNAVAILABLE" in code:
            status = 503
        elif any(term in code for term in ("CONFLICT", "CHANGED", "INTEGRITY_FAILED")):
            status = 409
        else:
            status = 400
        response = jsonify({"ok": False, "code": code, "publish_status": "not_performed"})
        response.headers["Cache-Control"] = "no-store"
        return _with_committed_readback_state((response, status), exc)
    except Exception as exc:
        current_app.logger.warning("shared work owner unavailable: %s", type(exc).__name__)
        return _with_committed_readback_state((jsonify({"ok": False, "code": "SHARED_WORK_UNAVAILABLE"}), 503), exc)


def _shared_work_local_access_allowed():
    from lumenis.system.security.permission import resolve_local_workspace_principal
    endpoints = {"experience_runtime.import_shared_document": "POST",
                 "experience_runtime.read_shared_document": "GET",
                 "experience_runtime.download_shared_document": "GET",
                 "experience_runtime.download_work_attachment": "GET",
                 "experience_runtime.quote_shared_document": "GET",
                 "experience_runtime.save_shared_work": "POST",
                 "experience_runtime.search_shared_work": "GET",
                 "experience_runtime.read_shared_work": "GET",
                 "experience_runtime.export_shared_work": "GET",
                 "experience_runtime.read_reporting_preferences": "GET",
                 "experience_runtime.save_reporting_preferences": "POST",
                 "experience_runtime.read_reporting_notifications": "GET",
                 "experience_runtime.revise_shared_work": "POST"}
    endpoints.update({"experience_runtime.read_office_document": "GET",
                      "experience_runtime.edit_office_document": "POST"})
    if endpoints.get(request.endpoint) != request.method:
        return False
    action = "read" if request.method == "GET" or request.endpoint == "experience_runtime.quote_shared_document" else "write"
    if resolve_local_workspace_principal(module="reports", action=action) is None:
        return False
    try:
        _shared_work_actor_scope(action)
        return True
    except (ValueError, LookupError, PermissionError, RuntimeError):
        return False


@experience_bp.post("/api/experience/materials/documents")
def import_shared_document():
    def execute():
        import hashlib
        import json
        import tempfile
        import unicodedata
        from pathlib import Path
        from lumenis.importer.documents import import_document
        from lumenis.shared.reporting.saved_work import _json, _safe_payload

        if not _content_source_same_origin():
            raise PermissionError("DOCUMENT_UPLOAD_ORIGIN_DENIED")
        actor, scope = _shared_work_actor_scope("write")
        private_shared = scope.get("scope_kind") == "shared_workspace"
        valid_form = (
            (
                set(request.form).issubset({"request_id", "keywords"})
                and all(len(request.form.getlist(key)) == 1 for key in request.form)
            )
            if private_shared
            else (
                "provenance" in request.form
                and set(request.form).issubset(
                    {"provenance", "mode", "confirmed_resource", "confirm"}
                )
                and all(len(request.form.getlist(key)) == 1 for key in request.form)
            )
        )
        if (
            set(request.files) != {"file"}
            or len(request.files.getlist("file")) != 1
            or not valid_form
            or (request.content_length or 0) > 8 * 1024 * 1024 + 65536
        ):
            raise ValueError("DOCUMENT_UPLOAD_INVALID")
        file = request.files["file"]
        name = file.filename
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 185
            or name != name.strip()
            or any(
                char in '<>:"/\\|?*' or unicodedata.category(char).startswith("C")
                for char in name
            )
            or name.endswith((".", " "))
            or Path(name).stem.split(".", 1)[0].upper()
            in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                *{f"COM{i}" for i in range(1, 10)},
                *{f"LPT{i}" for i in range(1, 10)},
            }
        ):
            raise ValueError("DOCUMENT_UPLOAD_NAME_INVALID")
        raw = file.stream.read(8 * 1024 * 1024 + 1)
        if not 0 < len(raw) <= 8 * 1024 * 1024:
            raise ValueError("DOCUMENT_SIZE_INVALID")
        if private_shared:
            import uuid
            from lumenis.importer.documents import save_private_document

            with tempfile.TemporaryDirectory(
                prefix="lumenis-private-upload-"
            ) as temporary:
                path = Path(temporary) / name
                path.write_bytes(raw)
                return save_private_document(
                    str(path),
                    actor=actor,
                    scope=scope,
                    request_id=request.form.get("request_id")
                    or "upload-" + uuid.uuid4().hex,
                    context_keywords=[
                        term.strip()
                        for term in request.form.get("keywords", "").split(",")
                        if term.strip()
                    ],
                )
        if len(request.form["provenance"].encode()) > 65536:
            raise ValueError("DOCUMENT_PROVENANCE_REQUIRED")

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("DOCUMENT_PROVENANCE_REQUIRED")
                result[key] = value
            return result

        try:
            provenance = json.loads(
                request.form["provenance"],
                object_pairs_hook=pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError("DOCUMENT_PROVENANCE_REQUIRED")
                ),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("DOCUMENT_PROVENANCE_REQUIRED") from exc
        if not isinstance(provenance, dict) or "source_origin" in provenance:
            raise ValueError("DOCUMENT_PROVENANCE_REQUIRED")
        _safe_payload(json.loads(_json(provenance)))
        if provenance.get("source_url") is None:
            provenance["source_origin"] = {
                "kind": "approved-file",
                "ref": "file-upload-" + hashlib.sha256(raw).hexdigest(),
            }
        with tempfile.TemporaryDirectory(
            prefix="lumenis-document-upload-"
        ) as temporary:
            path = Path(temporary) / name
            path.write_bytes(raw)
            from lumenis.importer.documents import document_import_resource
            from lumenis.shared.reporting.saved_work import authorize
            from lumenis.system.security.permission import (
                get_permission_gate,
                PermissionLevel,
            )

            mode = request.form.get("mode", "import")
            if mode not in {"prepare", "import", "revoke"}:
                raise ValueError("DOCUMENT_UPLOAD_MODE_INVALID")
            resource = document_import_resource(
                str(path), actor=actor, scope=scope, provenance=provenance
            )
            if mode == "prepare":
                return {
                    "state": "PREPARED",
                    "resource": resource,
                    "source_sha256": hashlib.sha256(raw).hexdigest(),
                    "effect": "CANONICAL_SOURCE_IMPORT",
                    "scope": scope,
                }
            gate = get_permission_gate()
            token = gate.get_valid_approval_token("data_import", resource, exact=True)
            explicit_confirmation = (
                "confirmed_resource" in request.form or "confirm" in request.form
            )
            if mode == "revoke" or explicit_confirmation:
                if (
                    request.form.get("confirm") != "true"
                    or request.form.get("confirmed_resource") != resource
                ):
                    raise PermissionError("DOCUMENT_EXACT_CONFIRMATION_REQUIRED")
                if not gate.has_permission(
                    PermissionLevel.HUMAN_APPROVAL
                ) or not gate.has_permission(PermissionLevel.COMMIT):
                    raise PermissionError("DOCUMENT_MANUAL_AUTHORITY_REQUIRED")
                context = authorize(actor, scope, action="write")
                if mode == "revoke":
                    return {
                        "revoked": bool(token and gate.revoke_approval(token)),
                        "resource": resource,
                    }
                if token is None:
                    token = gate.grant_approval(
                        "data_import",
                        resource=resource,
                        duration_minutes=5,
                        granted_by=context.get("principal_ref")
                        or "actor:" + str(context["actor_id"]),
                    )
            try:
                return import_document(
                    str(path), actor=actor, scope=scope, provenance=provenance
                )
            except Exception:
                if explicit_confirmation and token:
                    gate.revoke_approval(token)
                raise

    return _shared_work_response(execute)


def _document_row_page_request(source_ref, actor, scope):
    from lumenis.importer.documents import read_document_source_rows
    if (set(request.args) != {"offset", "limit", "source_version", "source_sha256"}
            or any(len(request.args.getlist(k)) != 1 for k in request.args)
            or any(not request.args[k].isascii() or not request.args[k].isdecimal()
                   or len(request.args[k]) > 6 for k in ("offset", "limit"))):
        raise ValueError("DOCUMENT_ROW_PAGE_INVALID")
    return read_document_source_rows(source_ref, actor=actor, scope=scope,
        offset=int(request.args["offset"]), limit=int(request.args["limit"]),
        source_version=request.args["source_version"], source_sha256=request.args["source_sha256"])


@experience_bp.get("/api/experience/materials/documents/<int:evidence_id>")
def read_shared_document(evidence_id):
    def execute():
        from lumenis.importer.documents import reopen_imported_source
        actor, scope = _shared_work_actor_scope("read")
        if request.args:
            return _document_row_page_request(evidence_id, actor, scope)
        result = reopen_imported_source(evidence_id, actor=actor, scope=scope)
        return {**{key: value for key, value in result.items() if key != "content"},
                "source_file_url": f"/api/experience/materials/documents/{evidence_id}/file"}
    return _shared_work_response(execute)


@experience_bp.get("/api/experience/materials/documents/<int:evidence_id>/file")
def download_shared_document(evidence_id):
    def execute():
        import io
        from flask import send_file
        from lumenis.importer.documents import reopen_imported_source
        if request.args:
            raise ValueError("DOCUMENT_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("read")
        result = reopen_imported_source(evidence_id, actor=actor, scope=scope)
        response = send_file(io.BytesIO(result["content"]), as_attachment=True,
                             download_name=result["filename"], max_age=0)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Source-Artifact-ID"] = result["artifact_ref"]
        response.headers["X-Content-SHA256"] = result["sha256"]
        return response
    return _shared_work_response(execute)


@experience_bp.get("/api/experience/materials/documents/<int:evidence_id>/quote")
def quote_shared_document(evidence_id):
    def execute():
        from lumenis.importer.documents import locate_quote
        if set(request.args) != {"start", "end"} or any(len(request.args.getlist(k)) != 1 for k in request.args):
            raise ValueError("DOCUMENT_QUOTE_INVALID")
        if any(not request.args[k].isascii() or not request.args[k].isdecimal() for k in request.args):
            raise ValueError("DOCUMENT_QUOTE_RANGE_INVALID")
        body = {key: int(request.args[key]) for key in ("start", "end")}
        actor, scope = _shared_work_actor_scope("read")
        return locate_quote(evidence_id, actor=actor, scope=scope, **body)
    return _shared_work_response(execute)


@experience_bp.post("/api/experience/saved-work")
def save_shared_work():
    def execute():
        from lumenis.shared.reporting.saved_work import save_work
        from lumenis_app_api import _internal_pitch_body
        body = _internal_pitch_body()
        if "verify_fact_wall_claims" in body:
            if set(body) != {"verify_fact_wall_claims"}:
                raise ValueError("WORK_FACT_WALL_REQUEST_INVALID")
            from lumenis.shared.evidence.api import verify_fact_wall_claims
            actor, scope = _shared_work_actor_scope("read")
            return verify_fact_wall_claims(actor=actor, scope=scope, claims=body["verify_fact_wall_claims"])
        if "adopt_source_brief_job_id" in body:
            required = {"adopt_source_brief_job_id", "request_id", "mode"}
            optional = {"title"}
            approval_fields = {"confirm", "confirmed_resource"}
            if (not required.issubset(body) or set(body) - required - optional - approval_fields
                    or bool(set(body) & approval_fields) != approval_fields.issubset(body)):
                raise ValueError("WORK_ADOPTION_REQUEST_INVALID")
            if request.args:
                raise ValueError("WORK_ADOPTION_REQUEST_INVALID")
            if not _content_source_same_origin():
                raise PermissionError("SOURCE_BRIEF_ADOPTION_ORIGIN_DENIED")
            from lumenis.shared.reporting.source_brief_job import adopt_domain_report
            actor, scope = _shared_work_actor_scope("write")
            job_id = body["adopt_source_brief_job_id"]
            request_id = body["request_id"]
            mode = body["mode"]
            title = body.get("title")
            if "title" in body and not isinstance(title, str):
                raise ValueError("WORK_INPUT_INVALID")
            if not isinstance(mode, str) or mode not in {"prepare", "save", "apply", "revoke"}:
                raise ValueError("SOURCE_BRIEF_ADOPTION_MODE_INVALID")
            prepared = adopt_domain_report(job_id=job_id, request_id=request_id,
                mode="prepare", actor=actor, target_scope=scope, title=title)
            if mode == "prepare":
                if approval_fields.intersection(body):
                    raise ValueError("WORK_ADOPTION_REQUEST_INVALID")
                return prepared
            if approval_fields.issubset(body):
                if (body["confirm"] is not True
                        or body["confirmed_resource"] != prepared.get("resource")):
                    raise PermissionError("SOURCE_BRIEF_ADOPTION_EXACT_CONFIRMATION_REQUIRED")
                from lumenis.shared.reporting.saved_work import authorize_saved_work
                from lumenis.system.security.permission import (
                    OperationType,
                    PermissionLevel,
                    get_permission_gate,
                )
                gate = get_permission_gate()
                if (not gate.has_permission(PermissionLevel.HUMAN_APPROVAL)
                        or not gate.has_permission(PermissionLevel.COMMIT)):
                    raise PermissionError("SOURCE_BRIEF_ADOPTION_MANUAL_AUTHORITY_REQUIRED")
                context = authorize_saved_work(actor, scope, action="write")
                resource = prepared["resource"]
                token = gate.get_valid_approval_token(OperationType.DATA_EXPORT.value, resource, exact=True)
                if mode == "revoke":
                    return {"revoked": bool(token and gate.revoke_approval(token)), "resource": resource}
                if token is None:
                    caller = context.get("principal_ref") or "actor:" + str(context["actor_id"])
                    token = gate.grant_approval(OperationType.DATA_EXPORT.value, resource=resource,
                        duration_minutes=5, granted_by=caller)
                try:
                    return adopt_domain_report(job_id=job_id, request_id=request_id,
                        mode="save", actor=actor, target_scope=scope, title=title)
                except Exception:
                    gate.revoke_approval(token)
                    raise
            if mode == "revoke":
                raise PermissionError("SOURCE_BRIEF_ADOPTION_EXACT_CONFIRMATION_REQUIRED")
            if mode == "apply":
                raise PermissionError("SOURCE_BRIEF_ADOPTION_EXACT_CONFIRMATION_REQUIRED")
            return adopt_domain_report(job_id=job_id, request_id=request_id,
                mode="save", actor=actor, target_scope=scope, title=title)
        required = {"title", "markdown", "kind", "payload", "citations", "request_id"}
        allowed = required | {"work_id", "previous_artifact_id", "expected_draft_digest", "contract"}
        if not required.issubset(body) or set(body) - allowed:
            raise ValueError("WORK_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("write")
        return save_work(actor=actor, scope=scope, **body)
    return _shared_work_response(execute)


@experience_bp.post("/api/experience/saved-work/<artifact_id>/revise")
def revise_shared_work(artifact_id):
    def execute():
        from lumenis.shared.reporting.saved_work import revise_work
        from lumenis_app_api import _internal_pitch_body
        body = _internal_pitch_body()
        required = {"request_id", "expected_sha256", "reason", "edits"}
        if not required.issubset(body) or set(body) - required - {"citations", "source_adoptions"}:
            raise ValueError("WORK_REVISION_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("write")
        from lumenis.shared.reporting import saved_work, work_dependencies
        parent = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope)
        if work_dependencies.KEY in parent["document"]["payload"]:
            # The dedicated owner verifies its signed parent receipt. Invalid
            # copied metadata must never fall back to a generic successful save.
            return work_dependencies.revise_owned_work(artifact_id, actor=actor, scope=scope, **body)
        return revise_work(artifact_id, actor=actor, scope=scope, **body)
    return _shared_work_response(execute)


@experience_bp.get("/api/experience/saved-work/<artifact_id>/office")
def read_office_document(artifact_id):
    def execute():
        from lumenis.importer.documents import read_office_document as read
        if (set(request.args) - {"offset", "limit"}
                or any(len(request.args.getlist(key)) != 1 for key in request.args)):
            raise ValueError("OFFICE_PAGE_INVALID")
        values = [request.args.get("offset", "0"), request.args.get("limit", "100")]
        if any(not value.isascii() or not value.isdecimal() for value in values):
            raise ValueError("OFFICE_PAGE_INVALID")
        actor, scope = _shared_work_actor_scope("read")
        return read(artifact_id, actor=actor, scope=scope, offset=int(values[0]), limit=int(values[1]))
    return _shared_work_response(execute)


@experience_bp.post("/api/experience/saved-work/<artifact_id>/office/edit")
def edit_office_document(artifact_id):
    def execute():
        from lumenis.importer.documents import edit_office_document as edit
        from lumenis_app_api import _internal_pitch_body
        if not _content_source_same_origin():
            raise PermissionError("OFFICE_ORIGIN_DENIED")
        body = _internal_pitch_body()
        required = {"request_id", "expected_sha256", "expected_package_sha256", "reason", "commands"}
        if (not required.issubset(body)
                or set(body) - required - {"acknowledge_signature_invalidation"}):
            raise ValueError("OFFICE_EDIT_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("write")
        return edit(artifact_id, actor=actor, scope=scope, **body)
    return _shared_work_response(execute)


@experience_bp.get("/api/experience/saved-work")
def search_shared_work():
    def execute():
        from lumenis.shared.reporting.saved_work import search_work
        if set(request.args) - {"query", "limit", "cursor", "kind", "evidence_id", "latest_only"} or any(len(request.args.getlist(k)) != 1 for k in request.args):
            raise ValueError("WORK_SEARCH_INVALID")
        limit = request.args.get("limit", "30")
        if not limit.isascii() or not limit.isdecimal():
            raise ValueError("WORK_SEARCH_INVALID")
        evidence_id = request.args.get("evidence_id")
        if evidence_id is not None and (not evidence_id.isascii() or not evidence_id.isdecimal()):
            raise ValueError("WORK_SEARCH_INVALID")
        latest = request.args.get("latest_only", "false")
        if latest not in {"true", "false"}:
            raise ValueError("WORK_SEARCH_INVALID")
        actor, scope = _shared_work_actor_scope("read")
        return search_work(actor=actor, scope=scope, query=request.args.get("query", ""), limit=int(limit),
                           cursor=request.args.get("cursor"), kind=request.args.get("kind"),
                           evidence_id=int(evidence_id) if evidence_id is not None else None, latest_only=latest == "true")
    return _shared_work_response(execute)


@experience_bp.get("/api/experience/saved-work/<artifact_id>")
def read_shared_work(artifact_id):
    def execute():
        from lumenis.shared.reporting.saved_work import reopen_work, prepare_work_selection, compare_work_versions
        if set(request.args) & {"offset", "limit", "source_version", "source_sha256"}:
            actor, scope = _shared_work_actor_scope("read")
            return _document_row_page_request(artifact_id, actor, scope)
        if (set(request.args) - {"selection_start", "selection_end", "compare_to"}
                or any(len(request.args.getlist(k)) != 1 for k in request.args)):
            raise ValueError("WORK_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("read")
        if "compare_to" in request.args:
            if set(request.args) != {"compare_to"} or not request.args["compare_to"]:
                raise ValueError("WORK_REQUEST_INVALID")
            return compare_work_versions(artifact_id, request.args["compare_to"], actor=actor, scope=scope)
        if request.args:
            if set(request.args) != {"selection_start", "selection_end"} or any(
                    not value.isascii() or not value.isdecimal() for value in request.args.values()):
                raise ValueError("WORK_SELECTION_RANGE_INVALID")
            return prepare_work_selection(artifact_id, actor=actor, scope=scope,
                start=int(request.args["selection_start"]), end=int(request.args["selection_end"]))
        return reopen_work(artifact_id, actor=actor, scope=scope)
    return _shared_work_response(execute)


@experience_bp.get("/api/experience/saved-work/<artifact_id>/export")
def export_shared_work(artifact_id):
    def execute():
        import io
        from flask import send_file
        from lumenis.shared.reporting.saved_work import export_work
        if ("format" not in request.args or set(request.args) - {"format", "purpose"}
                or any(len(request.args.getlist(key)) != 1 for key in request.args)):
            raise ValueError("WORK_EXPORT_FORMAT_INVALID")
        actor, scope = _shared_work_actor_scope("read")
        result = export_work(artifact_id, actor=actor, scope=scope, format=request.args["format"],
                             purpose=request.args.get("purpose", "audit_snapshot"))
        response = send_file(io.BytesIO(result["content"]), mimetype=result["media_type"],
                             download_name=result["filename"], as_attachment=True, max_age=0)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Source-Artifact-ID"] = artifact_id
        response.headers["X-Content-SHA256"] = result["sha256"]
        return response
    return _shared_work_response(execute)


@experience_bp.get("/api/experience/saved-work/preferences")
def read_reporting_preferences():
    def execute():
        from lumenis.shared.reporting.delivery_preferences import read_preferences
        if request.args:
            raise ValueError("DELIVERY_PREFERENCES_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("read")
        return read_preferences(actor=actor, scope=scope)
    return _shared_work_response(execute)


@experience_bp.post("/api/experience/saved-work/preferences")
def save_reporting_preferences():
    def execute():
        from lumenis.shared.reporting.delivery_preferences import save_preferences
        from lumenis_app_api import _internal_pitch_body
        body = _internal_pitch_body()
        required = {"preferences", "request_id"}
        if not required.issubset(body) or set(body) - required - {"previous_artifact_id", "expected_draft_digest"}:
            raise ValueError("DELIVERY_PREFERENCES_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("write")
        return save_preferences(actor=actor, scope=scope, **body)
    return _shared_work_response(execute)


@experience_bp.get("/api/experience/saved-work/notifications")
def read_reporting_notifications():
    def execute():
        from lumenis.shared.reporting.delivery_preferences import notification_feed
        if set(request.args) - {"limit", "cursor"} or any(len(request.args.getlist(k)) != 1 for k in request.args):
            raise ValueError("DELIVERY_NOTIFICATIONS_REQUEST_INVALID")
        limit = request.args.get("limit", "30")
        if not limit.isascii() or not limit.isdecimal():
            raise ValueError("DELIVERY_NOTIFICATIONS_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("read")
        return notification_feed(actor=actor, scope=scope, limit=int(limit), cursor=request.args.get("cursor"))
    return _shared_work_response(execute)


def _source_brief_material_ids(body, *, question, limit):
    from canonical_data import validate_source_ids
    if "source_ids" not in body:
        return None
    if body["source_ids"] is None or "resume_job_id" in body or "retry_media_job_id" in body:
        raise ValueError("SOURCE_BRIEF_MATERIAL_INPUT_INVALID")
    return validate_source_ids(body["source_ids"], limit=min(limit, 8) if question is not None else limit)


@experience_bp.route("/api/experience/reports/source-brief/generate", methods=["POST"])
def generate_source_brief_job():
    import uuid
    from lumenis.shared.database import get_repository
    from lumenis.shared.reporting.source_brief_job import (
        create_source_brief_job, get_source_brief_job, _scope_material,
    )
    from lumenis.system.security import get_permission_gate, OperationType

    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) - {"limit", "resume_job_id", "image_source_ref", "retry_media_job_id", "business_question", "source_ids", "research", "reference"}:
            raise ValueError("SOURCE_BRIEF_INPUT_INVALID")
        question = body.get("business_question")
        if "business_question" in body and (
            not isinstance(question, str) or not 4 <= len(question.strip()) <= 1500
            or "resume_job_id" in body or "retry_media_job_id" in body
        ):
            raise ValueError("SOURCE_BRIEF_BUSINESS_QUESTION_INVALID")
        limit = body.get("limit", 30)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("SOURCE_BRIEF_LIMIT_INVALID")
        source_ids = _source_brief_material_ids(body, question=question, limit=limit)
        image_ref = body.get("image_source_ref")
        research, reference = body.get("research"), body.get("reference")
        if "image_source_ref" in body and (
            not isinstance(image_ref, str) or not re.fullmatch(r"ART-[0-9a-f]{16}", image_ref)
            or "resume_job_id" in body
        ):
            raise ValueError("SOURCE_BRIEF_IMAGE_INPUT_INVALID")
        if "retry_media_job_id" in body and ("resume_job_id" in body or "image_source_ref" in body):
            raise ValueError("SOURCE_BRIEF_RETRY_INPUT_INVALID")
        actor_ref, audit_ref, scope, actor = _source_brief_context("write", include_actor=True)
        if scope.get("scope_kind") == "shared_workspace":
            domain_id = None
            _report_task_authorize(actor_ref, scope)
        else:
            from domain_isolation import resolve_domain_identity
            domain_id, _product_id = resolve_domain_identity(product_id=scope.get("product_id"))
            if not domain_id:
                raise ValueError("DOMAIN_REQUIRED")
            allowed = get_permission_gate().check(
                OperationType.REPORT_GENERATE, resource=request.path, caller=actor_ref,
                domain_id=domain_id,
            )
            if not allowed.allowed:
                raise PermissionError("SOURCE_BRIEF_GENERATE_DENIED")
        retry_of = body.get("retry_media_job_id")
        if "retry_media_job_id" in body:
            previous = get_source_brief_job(
                retry_of, actor_id=actor_ref, expected_scope=_scope_material(**scope), actor=actor,
            )
            image_ref = previous.get("requested_image_source_ref")
            question = previous.get("business_question")
            source_ids = previous.get("requested_source_ids")
            if (previous["multimodal"].get("state") not in {"unavailable", "error"}
                    or not isinstance(image_ref, str) or not re.fullmatch(r"ART-[0-9a-f]{16}", image_ref)):
                raise ValueError("SOURCE_BRIEF_MEDIA_NOT_RETRYABLE")
        job_id = body.get("resume_job_id")
        if job_id is not None:
            # A client can retry an existing server-issued job, never choose a new ID.
            get_source_brief_job(
                job_id, actor_id=actor_ref, expected_scope=_scope_material(**scope), actor=actor,
            )
        else:
            job_id = "brief-" + uuid.uuid4().hex

        def before_persist():
            current_ref, _, current_scope = _source_brief_context("write")
            if current_ref != actor_ref:
                raise PermissionError("SOURCE_BRIEF_ACTOR_MISMATCH")
            if _scope_material(**current_scope) != _scope_material(**scope):
                raise PermissionError("SOURCE_BRIEF_SCOPE_MISMATCH")
            if scope.get("scope_kind") == "shared_workspace":
                _report_task_authorize(actor_ref, scope)
            else:
                allowed = get_permission_gate().check(
                    OperationType.REPORT_GENERATE, resource=request.path, caller=current_ref,
                    domain_id=domain_id,
                )
                if not allowed.allowed:
                    raise PermissionError("SOURCE_BRIEF_GENERATE_DENIED")

        con = get_repository().connect(read_only=True, wal=False)
        try:
            result = create_source_brief_job(
                con, **scope, actor_id=actor_ref, permission_audit_ref=audit_ref,
                trace_id="source-brief:" + job_id, job_id=job_id, limit=limit,
                image_source_ref=image_ref, image_actor=actor,
                retry_of_job_id=retry_of,
                business_question=question,
                source_ids=source_ids, research=body.get("research"), reference=body.get("reference"),
                before_persist=before_persist,
            )
        finally:
            con.close()
        response = jsonify({"ok": True, "result": result, "publish_status": "not_performed"})
        response.headers["Cache-Control"] = "no-store"
        before_persist()
        return response
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "SOURCE_BRIEF_JOB_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/reports/source-brief/jobs/<job_id>", methods=["GET"])
def reopen_source_brief_job(job_id):
    from lumenis.shared.reporting.source_brief_job import get_source_brief_job, _scope_material

    try:
        actor_ref, _audit_ref, scope, actor = _source_brief_context("read", include_actor=True)
        result = get_source_brief_job(
            job_id, actor_id=actor_ref, expected_scope=_scope_material(**scope), actor=actor,
        )
        response = jsonify({"ok": True, "result": result, "publish_status": "not_performed"})
        response.headers["Cache-Control"] = "no-store"
        current_ref, _, current_scope, _ = _source_brief_context("read", include_actor=True)
        if current_ref != actor_ref:
            raise PermissionError("SOURCE_BRIEF_ACTOR_MISMATCH")
        if _scope_material(**current_scope) != _scope_material(**scope):
            raise PermissionError("SOURCE_BRIEF_SCOPE_MISMATCH")
        return response
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "SOURCE_BRIEF_JOB_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/reports/source-brief/jobs/<job_id>/reviews", methods=["POST"])
def submit_source_brief_review(job_id):
    from lumenis.shared.reporting.operator_review import write_operator_review
    from lumenis.shared.reporting.source_brief_job import _scope_material
    from lumenis.system.security import get_permission_gate, OperationType

    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"submission_id", "decision", "notes"}:
            raise ValueError("SOURCE_BRIEF_REVIEW_INPUT_INVALID")
        actor_ref, _, scope = _source_brief_context("write")
        expected = _scope_material(**scope)
        if scope.get("scope_kind") == "shared_workspace":
            from lumenis.shared.reporting.source_brief_job import write_shared_report_review
            _, _, _, actor = _source_brief_context("write", include_actor=True)
            review = write_shared_report_review(job_id, actor=actor, actor_id=actor_ref, **body)
            return jsonify({"ok": True, "review": review, "publish_status": "not_performed"})

        def authorize():
            current_ref, audit_ref, current_scope = _source_brief_context("write")
            if current_ref != actor_ref or current_scope != scope:
                raise PermissionError("SOURCE_BRIEF_REVIEW_SCOPE_DENIED")
            domain = expected["domain_id"]
            resource = domain + ":" + (scope["subject_id"] or scope["brand_focus_id"] or "GLOBAL_ALL")
            allowed = get_permission_gate().check(
                OperationType.REPORT_REVIEW, resource=resource, caller=actor_ref, domain_id=domain,
            )
            if (not allowed.allowed or not allowed.audit_id or allowed.resource != resource
                    or allowed.caller != actor_ref or allowed.domain_id != domain):
                raise PermissionError("SOURCE_BRIEF_REVIEW_DENIED")
            return {"actor_id": actor_ref, "scope": expected, "permission_audit_ref": audit_ref,
                    "operation_audit_ref": allowed.audit_id}

        review = write_operator_review(job_id, actor_id=actor_ref, expected_scope=expected,
                                       authorize=authorize, **body)
        return jsonify({"ok": True, "review": review, "publish_status": "not_performed"})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "SOURCE_BRIEF_REVIEW_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/cth/cases", methods=["POST"])
def create_cth_work_case():
    from cth_cases import create_cth_case
    from lumenis.shared.reporting.source_brief_job import _scope_material
    from lumenis.system.security import get_permission_gate, OperationType

    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {
            "submission_id", "title", "question", "source_job_id", "source_ids",
        }:
            raise ValueError("CTH_CASE_INPUT_INVALID")
        actor_ref, _, scope = _source_brief_context("write", module="cases")
        expected = _scope_material(**scope)

        def authorize():
            current_ref, audit_ref, current_scope = _source_brief_context("write", module="cases")
            if current_ref != actor_ref or current_scope != scope:
                raise PermissionError("CTH_CASE_CONTEXT_CHANGED")
            resource = "cth:" + (scope["subject_id"] or "GLOBAL_ALL")
            allowed = get_permission_gate().check(
                OperationType.CTH_CASE_CREATE, resource=resource, caller=actor_ref, domain_id="cth",
            )
            if (not allowed.allowed or not allowed.audit_id or allowed.resource != resource
                    or allowed.caller != actor_ref or allowed.domain_id != "cth"):
                raise PermissionError("CTH_CASE_CREATE_DENIED")
            return {"permission_audit_ref": audit_ref, "operation_audit_ref": allowed.audit_id}

        result = create_cth_case(actor_ref=actor_ref, expected_scope=expected, authorize=authorize, **body)
        return jsonify({"ok": True, "result": result, "publish_status": "not_performed"})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CTH_CASE_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/cth/cases", methods=["GET"])
def read_cth_case_list():
    """Find source-verified Cases in the current principal's exact CTH Focus."""
    from cth_cases import list_cth_cases
    from lumenis.shared.reporting.source_brief_job import _scope_material

    try:
        actor_ref, _audit_ref, scope = _source_brief_context("read", module="cases")
        if set(request.args) - {"limit", "before"} or any(len(request.args.getlist(key)) != 1 for key in request.args):
            raise ValueError("CTH_CASE_LIST_INPUT_INVALID")
        raw_limit = request.args.get("limit", "25")
        if not re.fullmatch(r"[1-9][0-9]{0,2}", raw_limit):
            raise ValueError("CTH_CASE_LIST_INPUT_INVALID")
        result = list_cth_cases(actor_ref=actor_ref, expected_scope=_scope_material(**scope),
                                limit=int(raw_limit), before=request.args.get("before"))
        return jsonify({"ok": True, "result": result, "publish_status": "not_performed"})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CTH_CASE_UNAVAILABLE", "publish_status": "not_performed"}), 503


@experience_bp.route("/api/experience/cth/cases/<case_id>", methods=["GET"])
def reopen_cth_work_case(case_id):
    from cth_cases import get_cth_case
    from lumenis.shared.reporting.source_brief_job import _scope_material

    try:
        if not re.fullmatch(r"CASE-[0-9a-f]{32}", case_id):
            raise ValueError("CTH_CASE_ID_INVALID")
        actor_ref, _, scope = _source_brief_context("read", module="cases")
        result = get_cth_case(case_id, actor_ref=actor_ref, expected_scope=_scope_material(**scope))
        return jsonify({"ok": True, "result": result, "publish_status": "not_performed"})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CTH_CASE_UNAVAILABLE"}), 503


def _report_task_authorize(actor_ref, scope):
    """Revalidate the actual request on admission, execution and artifact commit."""
    from lumenis.system.security import get_permission_gate, OperationType

    current_ref, audit_ref, current_scope, actor = _source_brief_context("write", include_actor=True)
    if current_ref != actor_ref or current_scope != scope:
        raise PermissionError("SOURCE_BRIEF_TASK_SCOPE_DENIED")
    if scope == {"scope_kind": "shared_workspace", "version": 1}:
        return actor, audit_ref
    domain = "cth" if scope["product_id"] == "CTH" else "zbmp"
    resource = domain + ":" + (scope["subject_id"] or scope["brand_focus_id"] or "GLOBAL_ALL")
    allowed = get_permission_gate().check(
        OperationType.REPORT_GENERATE, resource=resource, caller=actor_ref, domain_id=domain,
    )
    if (not allowed.allowed or not allowed.audit_id or allowed.resource != resource
            or allowed.caller != actor_ref or allowed.domain_id != domain):
        raise PermissionError("SOURCE_BRIEF_GENERATE_DENIED")
    return actor, audit_ref


@experience_bp.route("/api/experience/reports/source-brief/start", methods=["POST"])
def start_source_brief_task():
    from flask import copy_current_request_context
    from lumenis.shared.reporting import source_brief_tasks as tasks

    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) - {"limit", "image_source_ref", "business_question", "source_ids", "revision", "research", "defer", "request_id", "reference"}:
            raise ValueError("SOURCE_BRIEF_INPUT_INVALID")
        if "revision" in body and set(body) != {"revision"}:
            raise ValueError("REPORT_REVISION_INHERITS_PARENT_INPUT")
        limit = body.get("limit", 30)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("SOURCE_BRIEF_LIMIT_INVALID")
        question = body.get("business_question")
        if "business_question" in body and (not isinstance(question, str) or not 4 <= len(question.strip()) <= 1500):
            raise ValueError("SOURCE_BRIEF_BUSINESS_QUESTION_INVALID")
        source_ids = _source_brief_material_ids(body, question=question, limit=limit)
        image_ref = body.get("image_source_ref")
        research, reference = body.get("research"), body.get("reference")
        if "image_source_ref" in body and (not isinstance(image_ref, str) or not re.fullmatch(r"ART-[0-9a-f]{16}", image_ref)):
            raise ValueError("SOURCE_BRIEF_IMAGE_INPUT_INVALID")
        actor_ref, audit_ref, scope = _source_brief_context("write")
        authorize = lambda: _report_task_authorize(actor_ref, scope)
        authorize()
        if "revision" in body:
            from lumenis.shared.reporting.operator_review import resolve_report_revision
            from lumenis.shared.reporting.source_brief_job import _scope_material
            if scope.get("scope_kind") == "shared_workspace":
                from lumenis.shared.reporting.source_brief_job import resolve_shared_report_revision
                actor, _ = authorize()
                inherited = resolve_shared_report_revision(body["revision"], actor=actor, actor_id=actor_ref)
            else:
                inherited = resolve_report_revision(body["revision"], actor_id=actor_ref,
                                                     expected_scope=_scope_material(**scope))
            if scope.get("scope_kind") != "shared_workspace":
                from lumenis.shared.reporting.source_brief_job import get_source_brief_job
                parent = get_source_brief_job(body["revision"]["parent_job_id"], actor_id=actor_ref,
                    expected_scope=_scope_material(**scope), actor=authorize()[0])
                inherited = {**inherited, "research": parent.get("research"), "reference": parent.get("reference")}
            question, source_ids = inherited["business_question"], inherited["source_ids"]
            image_ref, limit = inherited["image_source_ref"], len(source_ids)
            research, reference = inherited.get("research"), inherited.get("reference")
        if source_ids is not None and scope.get("scope_kind") != "shared_workspace":
            from lumenis.shared.database import get_repository
            from lumenis.shared.reporting.operational_brief import build_scoped_source_brief
            with get_repository().connection(read_only=True, wal=False) as con:
                build_scoped_source_brief(con, **scope, source_ids=source_ids, limit=limit)
        if type(body.get("defer", False)) is not bool:
            raise ValueError("SOURCE_BRIEF_INPUT_INVALID")
        from lumenis.shared.reporting.source_brief_job import _read_research_reference, _scope_material
        _read_research_reference(reference, actor=authorize()[0], scope=_scope_material(**scope))
        task = tasks.create_task(actor_ref=actor_ref, scope=scope, permission_audit_ref=audit_ref,
                                 limit=limit, image_source_ref=image_ref, business_question=question,
                                 source_ids=source_ids, revision=body.get("revision"), research=research, reference=reference, request_id=body.get("request_id"))
        if type(body.get("defer", False)) is not bool:
            raise ValueError("SOURCE_BRIEF_INPUT_INVALID")
        if not body.get("defer", False):
            tasks.dispatch(task, authorize=authorize, request_wrapper=copy_current_request_context)
        # The worker may already have finished; 202 is admission, not job success.
        result = tasks.status(tasks.scoped_task(task["task_id"], actor_ref=actor_ref, scope=scope), actor=authorize()[0])
        return jsonify({"ok": True, "task": result, "publish_status": "not_performed"}), 202
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "SOURCE_BRIEF_TASK_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/reports/source-brief/tasks/<task_id>", methods=["GET"])
def source_brief_task_status(task_id):
    from lumenis.shared.reporting import source_brief_tasks as tasks

    try:
        actor_ref, _audit, scope, actor = _source_brief_context("read", include_actor=True)
        task = tasks.scoped_task(task_id, actor_ref=actor_ref, scope=scope)
        return jsonify({"ok": True, "task": tasks.status(task, actor=actor), "publish_status": "not_performed"})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "SOURCE_BRIEF_TASK_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/reports/source-brief/tasks/<task_id>/resume", methods=["POST"])
def resume_source_brief_task(task_id):
    from flask import copy_current_request_context
    from lumenis.shared.reporting import source_brief_tasks as tasks

    try:
        if request.get_json(silent=True) != {}:
            raise ValueError("SOURCE_BRIEF_INPUT_INVALID")
        actor_ref, _audit, scope = _source_brief_context("write")
        task = tasks.scoped_task(task_id, actor_ref=actor_ref, scope=scope)
        tasks.dispatch(task, authorize=lambda: _report_task_authorize(actor_ref, scope),
                       request_wrapper=copy_current_request_context)
        return jsonify({"ok": True, "task": tasks.status(tasks.scoped_task(
            task_id, actor_ref=actor_ref, scope=scope), actor=_report_task_authorize(actor_ref, scope)[0]), "publish_status": "not_performed"}), 202
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "SOURCE_BRIEF_TASK_UNAVAILABLE"}), 503


def _content_project_assets(payload, actor, scope):
    """Yield freshly fingerprinted local assets or authorized imported source refs."""
    from contextlib import contextmanager

    @contextmanager
    def _open():
        from lumenis.shared.content_creation.video_editing import fingerprint_local_media
        from shared_artifacts import LocalArtifactError, resolve_content_source_assets, validate_local_asset

        has_paths = "asset_paths" in payload
        has_refs = "asset_refs" in payload
        if has_paths == has_refs:
            raise LocalArtifactError("CONTENT_ASSET_INPUT_REQUIRED")
        if has_refs:
            refs = payload.get("asset_refs")
            with resolve_content_source_assets(refs, actor=actor, **scope) as resolved:
                yield [str(item["path"]) for item in resolved], [item["asset"] for item in resolved], list(refs)
            return

        paths = payload.get("asset_paths")
        if not isinstance(paths, list) or not 1 <= len(paths) <= 64:
            raise LocalArtifactError("LOCAL_ASSETS_REQUIRED")
        normalized_paths = [validate_local_asset(value, resource_budget=True) for value in paths]
        from shared_artifacts import content_media_resource_budget
        if sum(path.stat().st_size for path in normalized_paths) > content_media_resource_budget()["storage_capacity_bytes"]:
            raise LocalArtifactError("CONTENT_SOURCE_TOTAL_TOO_LARGE")
        assets = [fingerprint_local_media(str(path)) for path in normalized_paths]
        asset_ids = [asset.asset_id for asset in assets]
        if len(set(asset_ids)) != len(asset_ids):
            raise LocalArtifactError("CONTENT_SOURCE_ASSET_DUPLICATE")
        yield [str(path) for path in normalized_paths], assets, []

    return _open()


@experience_bp.route("/api/experience/shared-skills/shared.content_project/inspect", methods=["POST"])
def inspect_content_project_media():
    from shared_artifacts import LocalArtifactError

    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("action_type") != "READ":
            raise LocalArtifactError("CONTENT_INSPECT_REQUIRES_READ")
        payload = body.get("input")
        if not isinstance(payload, dict) or (set(payload) - {"asset_paths", "asset_refs", "waveform", "silence_proposal", "timeline", "stream_metadata", "broll", "toolchain", "transcription", "transcript_edit", "edit_batch", "audio_comparison", "source_preview"} or (("asset_paths" in payload) == ("asset_refs" in payload))):
            raise LocalArtifactError("INVALID_CONTENT_INPUT")
        actor, scope = _content_project_scope("read")
        with _content_project_assets(payload, actor, scope) as (_, assets, source_refs):
            def check_read():
                current_actor, current_scope = _content_project_scope("read")
                if current_actor != actor or current_scope != scope:
                    raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
            source_preview = None
            if "source_preview" in payload:
                from shared_artifacts import prepare_content_source_preview
                options = payload['source_preview']
                if (not source_refs or type(options) is not dict or not {'asset_id','kind'} <= set(options)
                        or set(options) - {'asset_id','kind','audio_stream_index'}):
                    raise LocalArtifactError('CONTENT_SOURCE_PREVIEW_INVALID')
                index = next((index for index, asset in enumerate(assets) if asset.asset_id == options['asset_id']), None)
                if index is None:
                    raise LocalArtifactError('CONTENT_SOURCE_PREVIEW_INVALID')
                source_preview = prepare_content_source_preview(source_refs[index], actor=actor, **scope,
                    expected_sha256=assets[index].sha256, source_asset=assets[index], kind=options['kind'],
                    audio_stream_index=options.get('audio_stream_index'), check_continue=check_read)
            if "audio_comparison" in payload:
                from lumenis.shared.content_creation.rendering import (
                    preview_audio_processing,
                )
                from lumenis.shared.content_creation.video_editing import Timeline
                options = payload["audio_comparison"]
                if (set(payload) - {"asset_paths", "asset_refs", "timeline", "audio_comparison"}
                        or "timeline" not in payload or not isinstance(options, dict)
                        or set(options) != {"start_sec", "end_sec", "render_options"}):
                    raise LocalArtifactError("AUDIO_COMPARISON_INPUT_INVALID")
                original = Timeline.from_dict(payload["timeline"], assets=assets)
                comparison = preview_audio_processing(original, **options, check_continue=check_read)
                check_read()
                with _content_project_assets(payload, actor, scope) as (_, fresh_assets, _):
                    if [asset.to_dict() for asset in fresh_assets] != [asset.to_dict() for asset in assets]:
                        raise LocalArtifactError("CONTENT_SOURCE_CHANGED_DURING_AUDIO_PREVIEW")
                response = jsonify({"ok": True, "audio_comparison": comparison,
                                    "assets": [asset.to_dict() for asset in assets],
                                    "source_artifact_refs": source_refs, "rights_state": "unknown",
                                    "external_fetch": False})
                response.headers["Cache-Control"] = "no-store"
                return response
            edit_batch = None
            if "edit_batch" in payload:
                from lumenis.shared.content_creation.video_editing import Timeline
                options = payload["edit_batch"]
                if (not isinstance(options, dict) or set(options) != {"commands", "expected_version"}
                        or "timeline" not in payload):
                    raise LocalArtifactError("EDIT_BATCH_INPUT_INVALID")
                original = Timeline.from_dict(payload["timeline"], assets=assets)
                updated = original.apply_edit_batch(options["commands"], expected_version=options["expected_version"])
                check_read()
                with _content_project_assets(payload, actor, scope) as (_, fresh_assets, _):
                    if [asset.to_dict() for asset in fresh_assets] != [asset.to_dict() for asset in assets]:
                        raise LocalArtifactError("CONTENT_SOURCE_CHANGED_DURING_BATCH_PREVIEW")
                edit_batch = {"state": "preview", "base_version": original.version,
                              "base_digest": original._view_digest(), "timeline": updated.to_dict(),
                              "timeline_digest": updated._view_digest(), "persisted": False,
                              "export_performed": False, "approval_required": True,
                              "undo_scope": "session_per_operation_not_persisted"}
            transcript_edit = None
            if "transcript_edit" in payload:
                from lumenis.shared.content_creation.transcript_editing import project_word_deletion_candidate
                options=payload["transcript_edit"]
                if (not isinstance(options,dict) or "project_id" not in options
                        or set(options)-{"project_id","word_ids","filler_terms","expected_transcript_sha256","clip_ids","synchronize","transcript_asset_id"}
                        or (("word_ids" in options) == ("filler_terms" in options))
                        or "filler_terms" in options and "expected_transcript_sha256" not in options
                        or not isinstance(options["project_id"],str)):
                    raise LocalArtifactError("WORD_EDIT_OPTIONS_INVALID")
                transcript_edit=project_word_deletion_candidate(actor=actor,scope=scope,source_artifact_refs=source_refs,**options)
                check_read()
            transcription = None
            if "transcription" in payload:
                from lumenis.shared.content_creation.speech_transcription import build_transcription_files
                options=payload["transcription"]
                if len(assets)!=1 or not isinstance(options,dict) or set(options)-{"audio_stream_index","language_hint"}:
                    raise LocalArtifactError("CONTENT_TRANSCRIPTION_OPTIONS_INVALID")
                transcription=build_transcription_files(assets[0],check_cancel=check_read,**options)["report"]
                check_read()
            toolchain = None
            if "toolchain" in payload:
                if payload["toolchain"] is not True:raise LocalArtifactError("MEDIA_TOOLCHAIN_OPTIONS_INVALID")
                from lumenis.shared.content_creation.toolchain_capabilities import inspect_media_toolchain
                toolchain=inspect_media_toolchain()
                # Runtime paths are retained in local diagnostics only, not HTTP responses.
                for key in ("ffmpeg","ffprobe","caption_font","libreoffice","espeak_ng"):toolchain[key].pop("path",None)
                check_read()
            broll = None
            if "broll" in payload:
                from lumenis.shared.content_creation.broll_suggestions import suggest_broll,prepare_broll_insertion
                options=payload["broll"]
                if not isinstance(options,dict) or not {"transcript","descriptions"}<=set(options) or set(options)-{"transcript","descriptions","limit","insert"}:
                    raise LocalArtifactError("BROLL_OPTIONS_INVALID")
                broll=suggest_broll(assets,check_cancel=check_read,**{key:value for key,value in options.items() if key!="insert"})
                if "insert" in options:
                    from lumenis.shared.content_creation.video_editing import Timeline
                    if "timeline" not in payload or not isinstance(options["insert"],dict) or set(options["insert"])!={"selected_asset_id","at_sec","source_in","source_out"}:
                        raise LocalArtifactError("BROLL_INSERT_INPUT_INVALID")
                    if options["insert"]["selected_asset_id"] not in {item["asset_id"] for item in broll["candidates"]}:
                        raise LocalArtifactError("BROLL_SELECTION_NOT_IN_CANDIDATES")
                    broll["insertion_preview"]=prepare_broll_insertion(Timeline.from_dict(payload["timeline"],assets=assets),**options["insert"])
                check_read()
            waveforms = []
            stream_metadata = []
            if "stream_metadata" in payload:
                from lumenis.shared.content_creation.stream_probe import probe_source_streams
                options=payload["stream_metadata"]
                if not isinstance(options,dict) or set(options)-{"analyze_timing"} or len(assets)>4:
                    raise LocalArtifactError("SOURCE_PROBE_OPTIONS_INVALID")
                stream_metadata=[probe_source_streams(asset,check_cancel=check_read,**options) for asset in assets]
                check_read()
            silence_proposals = []
            silence_edl = None
            if "timeline" in payload and "silence_proposal" not in payload and "broll" not in payload and "edit_batch" not in payload:
                raise LocalArtifactError("SILENCE_EDL_REQUIRES_MEASUREMENT")
            if "silence_proposal" in payload:
                from lumenis.shared.content_creation.rendering import propose_silence_edits
                options = payload["silence_proposal"]
                if not isinstance(options, dict) or set(options) - {"min_silence_sec", "threshold_db", "margin_sec", "audio_stream_index"} or len(assets) > 4:
                    raise LocalArtifactError("SILENCE_DETECTION_OPTIONS_INVALID")
                silence_proposals = [propose_silence_edits(asset, **options, check_continue=check_read) for asset in assets]
                if "timeline" in payload:
                    if len(assets)!=1:raise LocalArtifactError("SILENCE_EDL_REQUIRES_SINGLE_ASSET")
                    from lumenis.shared.content_creation.video_editing import Timeline
                    from lumenis.shared.content_creation.editorial_candidates import silence_edl_candidate
                    silence_edl=silence_edl_candidate(Timeline.from_dict(payload["timeline"],assets=assets),silence_proposals[0])
                check_read()
            if "waveform" in payload:
                from lumenis.shared.content_creation.rendering import extract_waveform
                options = payload["waveform"]
                if not isinstance(options, dict) or set(options) - {"start_sec", "end_sec", "bins", "audio_stream_index"} or len(assets) > 4:
                    raise LocalArtifactError("WAVEFORM_INPUT_INVALID")
                waveforms = [extract_waveform(asset, **options, check_continue=check_read) for asset in assets]
                check_read()
            return jsonify({"ok": True, **({"source_preview": source_preview} if source_preview is not None else {}), **({"edit_batch": edit_batch} if edit_batch is not None else {}), **({"transcript_edit":transcript_edit} if transcript_edit is not None else {}), **({"transcription":transcription} if transcription is not None else {}), **({"toolchain":toolchain} if toolchain is not None else {}), **({"broll":broll} if broll is not None else {}), **({"stream_metadata":stream_metadata} if "stream_metadata" in payload else {}), **({"silence_edl":silence_edl} if silence_edl is not None else {}), **({"silence_proposals": silence_proposals} if "silence_proposal" in payload else {}), **({"waveforms": waveforms} if "waveform" in payload else {}), "assets": [asset.to_dict() for asset in assets],
                            "source_artifact_refs": source_refs, "rights_state": "unknown",
                            "external_fetch": False})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_INSPECTION_UNAVAILABLE"}), 503


def _content_project_execution_context(scope):
    """Adapt the server-authorized content scope to the existing Skill context contract."""
    if "shared_workspace_scope" in scope:
        return {"shared_workspace_scope": dict(scope["shared_workspace_scope"])}
    domain = "bmp" if scope["domain_id"] == "zbmp" else "cth"
    return {
        "domain_context": {"domain_id": domain},
        "lumenis_focus_context": {
            "domain_id": domain, "state": "available",
            "mode": "GLOBAL_ALL" if scope["global_scope"] else "FOCUS",
            "subject_type": "company" if domain == "cth" else "brand",
            "subject_id": scope["subject_id"], "brand_focus_id": scope["brand_focus_id"],
        },
    }


def _content_source_same_origin():
    """Reject cross-origin browser uploads while allowing native clients without Origin."""
    fetch_site = request.headers.get("Sec-Fetch-Site", "").strip().lower()
    if fetch_site in {"cross-site", "cross-origin"}:
        return False
    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    candidate = origin if origin is not None else referer
    if candidate is None:
        return True
    if candidate.strip().lower() == "null":
        return False
    try:
        parsed = urlsplit(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        return parsed.scheme.lower() == request.scheme.lower() and parsed.netloc.lower() == request.host.lower()
    except (TypeError, ValueError):
        return False


@experience_bp.get("/api/experience/content-sources/tts/capabilities")
def content_speech_capabilities():
    from lumenis.shared.content_creation.offline_speech import speech_capabilities
    from shared_artifacts import LocalArtifactError
    try:
        actor, scope = _content_project_scope("read")
        result = speech_capabilities()
        if (actor, scope) != _content_project_scope("read"):
            raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
        response = jsonify({"ok": True, **result})
        response.headers["Cache-Control"] = "no-store"
        return response
    except ValueError as exc:
        return _content_project_error(exc)


@experience_bp.post("/api/experience/content-sources/tts/preview")
def preview_content_speech():
    """Generate an explicitly synthetic local WAV; importing remains a separate confirmation."""
    from flask import Response
    from shared_artifacts import LocalArtifactError
    from lumenis.shared.content_creation.offline_speech import synthesize_offline_speech
    try:
        actor,scope=_content_project_scope("read")
        if not _content_source_same_origin():raise LocalArtifactError("CONTENT_SOURCE_ORIGIN_DENIED")
        body=request.get_json(silent=True)
        if (not isinstance(body,dict) or "text" not in body
                or set(body)-{"text","language","voice","engine","response_format"}
                or body.get("response_format", "wav") not in {"wav", "json"}):
            raise LocalArtifactError("CONTENT_TTS_INPUT_INVALID")
        def check():
            current_actor,current_scope=_content_project_scope("read")
            if current_actor!=actor or current_scope!=scope:raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
        engine=body.get("engine","flite")
        parameters={key:value for key,value in body.items() if key not in {"engine","response_format"}}
        if engine=="flite":result=synthesize_offline_speech(**parameters,check_cancel=check)
        elif engine=="espeak_ng":
            from lumenis.shared.content_creation.offline_formant_speech import synthesize_formant_speech
            if "language" not in parameters:raise LocalArtifactError("TTS_LANGUAGE_REQUIRED")
            result=synthesize_formant_speech(**parameters,check_cancel=check)
        else:raise LocalArtifactError("TTS_ENGINE_UNAVAILABLE")
        check();data=result["files"]["speech.wav"];report=result["report"]
        if body.get("response_format") == "json":
            import base64

            from lumenis.shared.content_creation.offline_speech import (
                read_speech_source,
                speech_source_wav,
            )
            data = speech_source_wav(data, report)
            check()
            response = jsonify({"ok": True, "audio_base64": base64.b64encode(data).decode("ascii"),
                                "source": read_speech_source(data), "size_bytes": len(data),
                                "sha256": hashlib.sha256(data).hexdigest(),
                                "persisted": False, "requires_explicit_adoption": True})
            response.headers["Cache-Control"] = "no-store"
            return response
        response=Response(data,mimetype="audio/wav")
        response.headers["Content-Disposition"]='attachment; filename="synthetic-speech.wav"'
        response.headers["Cache-Control"]="no-store"
        response.headers["X-Lumenis-Synthetic"]="true"
        response.headers["X-Lumenis-TTS-Engine"]=report["engine"]
        response.headers["X-Lumenis-TTS-Language"]=report["language"]
        response.headers["X-Lumenis-TTS-Voice"]=report["voice"]
        response.headers["X-Lumenis-Generated-At"]=_dt.datetime.now(_dt.timezone.utc).isoformat()
        response.headers["X-Lumenis-Source-SHA256"]=hashlib.sha256(data).hexdigest()
        response.headers["X-Lumenis-Text-SHA256"]=hashlib.sha256(body["text"].encode("utf-8")).hexdigest()
        return response
    except ValueError as exc:return _content_project_error(exc)
    except Exception:return jsonify({"ok":False,"code":"CONTENT_TTS_UNAVAILABLE"}),503


@experience_bp.post("/api/experience/podcast/topics/preview")
def preview_podcast_topics():
    """Manual topic planning; current source reads stay with SavedWork owner."""
    from shared_artifacts import LocalArtifactError
    from podcast.intelligence.topic_planning import build_topic_preview
    from lumenis.shared.reporting.saved_work import read_committed_work
    try:
        actor,scope=_content_project_scope("read")
        if not _content_source_same_origin():raise LocalArtifactError("CONTENT_SOURCE_ORIGIN_DENIED")
        body=request.get_json(silent=True)
        if not isinstance(body,dict) or set(body)!={"as_of","cards"} or not isinstance(body["cards"],list) or len(body["cards"])>100:
            raise LocalArtifactError("PODCAST_TOPIC_INPUT_INVALID")
        refs=set()
        for card in body["cards"]:
            if not isinstance(card,dict):raise LocalArtifactError("PODCAST_TOPIC_CARD_INVALID")
            values=card.get("source_artifact_ids",[])
            if not isinstance(values,list) or len(values)>20 or any(not isinstance(v,str) or not re.fullmatch(r"ART-[0-9a-f]{16}",v) for v in values):
                raise LocalArtifactError("PODCAST_TOPIC_SOURCE_BINDING_REQUIRED")
            refs.update(values)
        if len(refs)>20:raise LocalArtifactError("PODCAST_TOPIC_SOURCE_LIMIT")
        bindings={};citations=[]
        for aid in sorted(refs):
            source=read_committed_work(aid,actor=actor,scope=scope)
            bindings[aid]={"artifact_id":aid,"version":source["document"]["version"],"sha256":source["artifact"]["sha256"],
                           "draft_digest":source["document"]["draft_digest"],"observed_at":_dt.datetime.now(_dt.timezone.utc).isoformat()}
            for citation in source["document"]["citations"]:
                if citation not in citations:citations.append(citation)
        result=build_topic_preview(**body,source_bindings=bindings,citations=citations)
        current_actor,current_scope=_content_project_scope("read")
        if current_actor!=actor or current_scope!=scope:raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
        for aid,binding in bindings.items():
            if read_committed_work(aid,actor=actor,scope=scope)["artifact"]["sha256"]!=binding["sha256"]:
                raise LocalArtifactError("PODCAST_TOPIC_SOURCE_CHANGED")
        return jsonify({"ok":True,**result})
    except LocalArtifactError as exc:return _content_project_error(exc)
    except (ValueError,PermissionError,LookupError,RuntimeError) as exc:return _source_brief_job_error(exc)
    except Exception:return jsonify({"ok":False,"code":"PODCAST_TOPIC_PREVIEW_UNAVAILABLE"}),503


@experience_bp.post("/api/experience/podcast/editorial/preview")
def preview_podcast_editorial():
    """No automatic guest choice, fact promotion, external transmission or persistence."""
    from shared_artifacts import LocalArtifactError
    from podcast.intelligence.editorial_planning import build_editorial_preview
    try:
        actor,scope=_content_project_scope("read")
        if not _content_source_same_origin():raise LocalArtifactError("CONTENT_SOURCE_ORIGIN_DENIED")
        body=request.get_json(silent=True)
        if (not isinstance(body,dict) or not {"topic","guests"}<=set(body)
                or set(body)-{"topic","guests","selected_guest_id","gates","include_sop"}):
            raise LocalArtifactError("PODCAST_EDITORIAL_INPUT_INVALID")
        result=build_editorial_preview(**body)
        current_actor,current_scope=_content_project_scope("read")
        if current_actor!=actor or current_scope!=scope:raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
        review={"principal_ref":f"actor:{actor['id']}" if isinstance(actor,dict) else actor.principal_ref,
                "scope":scope,"observed_at":_dt.datetime.now(_dt.timezone.utc).isoformat(),
                "gate_origin":"explicit_user_supplied_decisions_not_independent_fact_verification"}
        if "saved_work_draft" in result:
            result["saved_work_draft"]["payload"]["manual_review_context"]=review
            result["saved_work_payload_hash"]=hashlib.sha256(json.dumps(result["saved_work_draft"]["payload"],ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
        return jsonify({"ok":True,**result,"review_context":review,"external_fetch":False,"published":False})
    except ValueError as exc:return _content_project_error(exc)
    except Exception:return jsonify({"ok":False,"code":"PODCAST_EDITORIAL_UNAVAILABLE"}),503


@experience_bp.route("/api/experience/content-sources", methods=["POST"])
def import_content_source():
    """Import one bounded local media body into the scoped Artifact owner."""
    from werkzeug.exceptions import RequestEntityTooLarge
    from shared_artifacts import (LocalArtifactError, artifact_root, stage_content_source_artifact,
                                  content_media_resource_budget)
    from shared_artifacts import _safe_content_source_filename, parse_media_license_header, validate_media_license, _media_license_digest
    from lumenis.shared.agents.skills.execution import ActionType, SkillRuntimeInfo, run_execution_chain
    from lumenis.system.security.permission import ContentSourceImport

    try:
        if request.headers.get("X-Lumenis-Action", "").strip().upper() != "WRITE":
            raise LocalArtifactError("CONTENT_SOURCE_IMPORT_REQUIRES_WRITE")
        actor, scope = _content_project_scope("write")
        local_principal = actor if not isinstance(actor, dict) else None
        account_actor = actor if local_principal is None else None
        actor_id = account_actor["id"] if account_actor is not None else None
        if not _content_source_same_origin():
            raise LocalArtifactError("CONTENT_SOURCE_ORIGIN_DENIED")
        if request.mimetype != "application/octet-stream":
            raise LocalArtifactError("CONTENT_SOURCE_CONTENT_TYPE_INVALID")
        filenames = request.args.getlist("filename")
        if len(filenames) != 1:
            raise LocalArtifactError("CONTENT_SOURCE_FILENAME_INVALID")
        filename = _safe_content_source_filename(filenames[0])
        media_license = parse_media_license_header(request.headers.get("X-Lumenis-Media-License"))
        declared_length = request.content_length
        budget = content_media_resource_budget()
        # Keep enough space for the incoming temporary body and immutable original.
        upload_budget = max(0, (budget["available_bytes"] - 65536) // 2)
        if declared_length is not None and declared_length > upload_budget:
            raise LocalArtifactError("CONTENT_MEDIA_STORAGE_REQUIRED")
        # Flask 3.1 supplies a per-request setter. Keep the application's other
        # request limits intact while admitting this authenticated streaming body.
        try:
            request.max_content_length = upload_budget
        except AttributeError:
            if declared_length is None or declared_length > (request.max_content_length or upload_budget):
                raise LocalArtifactError('CONTENT_SOURCE_STREAM_RUNTIME_UNAVAILABLE')
        # Independently bound observed bytes; the supported Flask >=2 range
        # does not always expose a writable per-request max_content_length.

        runtime_info = SkillRuntimeInfo(
            skill_id="shared.content_project",
            name="导入内容素材",
            description="将用户明确选择的单个本地媒体文件存入受限共享 Artifact",
            product="SHARED",
            domain="content",
            version="1.0.0",
            enabled=True,
            source="shared_artifacts",
            cross_domain_allowed=["CTH", "BMP"],
        )
        artifact_root().mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="content-source-upload-", dir=str(artifact_root())) as work_dir:
            upload_path = os.path.join(work_dir, filename)
            observed = 0
            body_digest = hashlib.sha256()
            with open(upload_path, "xb") as output:
                while True:
                    chunk = request.stream.read(min(budget["chunk_bytes"], upload_budget - observed + 1))
                    if not chunk:
                        break
                    observed += len(chunk)
                    if observed > upload_budget:
                        raise LocalArtifactError("CONTENT_MEDIA_STORAGE_REQUIRED")
                    if (actor, scope) != _content_project_scope("write"):
                        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
                    if len(chunk) > content_media_resource_budget()["available_bytes"]:
                        raise LocalArtifactError("CONTENT_MEDIA_STORAGE_REQUIRED")
                    body_digest.update(chunk)
                    output.write(chunk)
            if observed <= 0:
                raise LocalArtifactError("CONTENT_SOURCE_EMPTY")
            if declared_length is not None and observed != declared_length:
                raise LocalArtifactError("CONTENT_SOURCE_BODY_LENGTH_MISMATCH")

            body_sha256 = body_digest.hexdigest()
            media_license = validate_media_license(media_license, asset_sha256=body_sha256)
            license_digest = _media_license_digest(media_license)
            resource_binding = {"actor_id": actor_id, "scope": scope,
                                "filename": filename, "size_bytes": observed,
                                "body_sha256": body_sha256,
                                **({"license_metadata_sha256": license_digest} if license_digest else {})}
            shared_workspace_scope = scope.get("shared_workspace_scope")
            upload = ContentSourceImport(
                actor_id=actor_id,
                domain_id=(None if shared_workspace_scope is not None else
                           "bmp" if scope["domain_id"] == "zbmp" else "cth"),
                subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
                global_scope=scope.get("global_scope", False), filename=filename,
                size_bytes=observed, body_sha256=body_sha256,
                principal_kind=local_principal.principal_kind if local_principal else None,
                principal_ref=local_principal.principal_ref if local_principal else None,
                scope_kind=shared_workspace_scope.get("scope_kind") if shared_workspace_scope else None,
                scope_version=shared_workspace_scope.get("version") if shared_workspace_scope else None,
                license_metadata_sha256=license_digest,
            )

            def import_asset(ctx):
                return stage_content_source_artifact(
                    upload_path,
                    filename=filename,
                    actor=actor,
                    source_execution_id=ctx.execution_id,
                    expected_sha256=body_sha256,
                    media_license=media_license,
                    **scope,
                )

            context = run_execution_chain(
                skill_id="shared.content_project",
                task=f"导入媒体素材 {filename}",
                input_payload={**resource_binding, "effect_mode": "staging"},
                content_source_import=upload,
                request_context=_content_project_execution_context(scope),
                action_type=ActionType.WRITE,
                user_id=actor_id,
                user_role=account_actor.get("role", "user") if account_actor else "user",
                workspace_principal=local_principal,
                permission_role=(None if "shared_workspace_scope" in scope else
                                 "cth_operator" if scope["domain_id"] == "cth" else "zbmp_operator"),
                product=("SHARED" if "shared_workspace_scope" in scope else
                         "CTH" if scope["domain_id"] == "cth" else "ZBMP"),
                domain=None if "shared_workspace_scope" in scope else scope["domain_id"],
                skill_info=runtime_info,
                handler=import_asset,
            )
        execution = context.execute_result or {}
        result = execution.get("result") if isinstance(execution, dict) else None
        permission = context.permission_result or {}
        if permission.get("allowed") is False:
            from lumenis.system.security.permission import prepare_content_source_import_confirmation

            confirmation = prepare_content_source_import_confirmation(
                account_actor, upload, principal=local_principal,
            )
            if confirmation.get("allowed") is not True:
                return jsonify({"ok": False, "code": confirmation.get("code"),
                                "publish_status": "not_performed"}), 403
            return jsonify({"ok": False,
                            "code": "CONTENT_SOURCE_APPROVAL_REQUIRED",
                            "execution_id": context.execution_id, "status": context.status.value,
                            "requires_approval": True, "confirmation": confirmation,
                            **({"media_license": media_license} if media_license is not None else {}),
                            "publish_status": "not_performed"}), 403
        if context.status.value != "completed" or not isinstance(result, dict) or not result.get("artifact"):
            code = _content_project_error_code(context.error or "CONTENT_SOURCE_IMPORT_FAILED")
            return jsonify({"ok": False, "code": code, "execution_id": context.execution_id,
                            "status": context.status.value, "publish_status": "not_performed"}), 503
        return jsonify({
            "ok": True,
            "result": {"artifact": result["artifact"], "asset": result["asset"],
                       **({key: result[key] for key in ("rights_state", "media_license", "media_license_sha256", "license_verification_state")}
                          if "media_license" in result else {})},
            "execution_id": context.execution_id,
            "evidence_recorded": bool((getattr(context, "evidence_record", None) or {}).get("ok")),
            "publish_status": "not_performed",
        }), 201
    except RequestEntityTooLarge:
        return jsonify({"ok": False, "code": "CONTENT_SOURCE_TOO_LARGE", "publish_status": "not_performed"}), 413
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_SOURCE_IMPORT_UNAVAILABLE",
                        "publish_status": "not_performed"}), 503


@experience_bp.route("/api/experience/content-source-confirmations/<confirmation_id>", methods=["POST"])
def confirm_content_source_import_request(confirmation_id: str):
    """Confirm or cancel one server-prepared, actor-bound local import request."""
    from lumenis.system.security.permission import (
        confirm_content_source_import, cancel_content_source_import_confirmation,
    )
    from shared_artifacts import LocalArtifactError

    try:
        actor, scope = _content_project_scope("write")
        local_principal = actor if not isinstance(actor, dict) else None
        account_actor = actor if local_principal is None else None
        if not _content_source_same_origin():
            raise LocalArtifactError("CONTENT_SOURCE_ORIGIN_DENIED")
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"confirmed"} or type(body["confirmed"]) is not bool:
            raise LocalArtifactError("CONTENT_SOURCE_CONFIRMATION_REQUIRED")
        normalized_scope = ({"shared_workspace_scope": scope["shared_workspace_scope"]}
                            if "shared_workspace_scope" in scope else
                            {**scope, "domain_id": "bmp" if scope["domain_id"] == "zbmp" else "cth"})
        if not body["confirmed"]:
            cancelled = cancel_content_source_import_confirmation(
                account_actor, confirmation_id, current_scope=normalized_scope,
                principal=local_principal,
            )
            return jsonify({"ok": bool(cancelled), "status": "cancelled" if cancelled else "not_found",
                            "publish_status": "not_performed"}), (200 if cancelled else 404)
        decision = confirm_content_source_import(
            account_actor, confirmation_id, confirmed=True,
            principal=local_principal, **normalized_scope,
        )
        if not decision.allowed:
            status = 503 if decision.verification_state == "unavailable" else 403
            return jsonify({"ok": False, "code": "CONTENT_SOURCE_CONFIRMATION_DENIED",
                            "publish_status": "not_performed"}), status
        # The private token remains inside Permission. Retrying different bytes
        # cannot use this confirmation, and no file has been imported yet.
        return jsonify({"ok": True, "status": "ready_for_retry", "confirmation_id": confirmation_id,
                        "purpose": "local_content_draft", "publish_status": "not_performed"})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_SOURCE_CONFIRMATION_UNAVAILABLE",
                        "publish_status": "not_performed"}), 503


@experience_bp.route("/api/experience/content-sources/<artifact_id>")
def content_source_detail(artifact_id: str):
    from pathlib import Path

    from shared_artifacts import open_content_source_media, read_content_source_artifact

    try:
        selectors = _content_media_selectors()
        actor, scope = _content_project_scope("read", selectors=selectors)
        formats = request.args.getlist("format")
        if formats:
            if (formats != ["media"] or set(request.args) - {"format", "sha256", "context", "preview_key"}
                    or len(request.args.getlist("sha256")) != 1):
                raise ValueError("CONTENT_SOURCE_FORMAT_INVALID")
            if not _content_source_same_origin():
                raise ValueError("CONTENT_SOURCE_ORIGIN_DENIED")
            media = open_content_source_media(
                artifact_id, expected_sha256=request.args["sha256"], preview_key=request.args.get('preview_key'), actor=actor, **scope)
            from flask import Response, stream_with_context

            etag = f'"{media.sha256}"'
            headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                       "Accept-Ranges": "bytes", "ETag": etag,
                       "Cross-Origin-Resource-Policy": "same-origin",
                       "Content-Disposition": f'inline; filename="{artifact_id}{Path(media.filename).suffix}"'}
            start, stop, status = 0, media.size_bytes, 200
            if request.method != "HEAD" and request.headers.get("Range") and request.headers.get("If-Range", etag) == etag:
                ranges = request.range
                selected = ranges.range_for_length(media.size_bytes) if ranges is not None and ranges.units == "bytes" else None
                if selected is None:
                    headers["Content-Range"] = f"bytes */{media.size_bytes}"
                    return Response(status=416, headers=headers)
                start, stop = selected
                status = 206
                headers["Content-Range"] = f"bytes {start}-{stop - 1}/{media.size_bytes}"

            def authorize_stream():
                if (actor, scope) != _content_project_scope("read", selectors=selectors):
                    raise ValueError("CONTENT_SOURCE_CONTEXT_MISMATCH")

            response = Response(
                () if request.method == "HEAD" else stream_with_context(media.iter_bytes(start, stop, authorize=authorize_stream)),
                status=status, headers=headers, mimetype=media.media_type, direct_passthrough=True,
            )
            response.content_length = stop - start
            return response
        if "context" in request.args:
            raise ValueError("CONTENT_SOURCE_FORMAT_INVALID")
        source = read_content_source_artifact(artifact_id, actor=actor, **scope)
        return jsonify({"ok": True, "result": source, "publish_status": "not_performed"})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_SOURCE_UNAVAILABLE",
                        "publish_status": "not_performed"}), 503


def _content_media_selectors(*, expected_format="media"):
    from werkzeug.datastructures import Headers

    if "context" not in request.args:
        return request.headers
    values = request.args.getlist("context")
    if len(values) != 1 or len(values[0].encode("utf-8")) > 2048 or request.args.getlist("format") != [expected_format]:
        raise ValueError("CONTENT_SOURCE_FORMAT_INVALID")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("CONTENT_SOURCE_FORMAT_INVALID")
            result[key] = value
        return result

    try:
        context = json.loads(values[0], object_pairs_hook=unique)
    except (ValueError, TypeError) as exc:
        raise ValueError("CONTENT_SOURCE_FORMAT_INVALID") from exc
    allowed = {_SHARED_WORKSPACE_SCOPE_HEADER, "X-Domain-Id", "X-Product-Id",
               "X-Lumenis-Context-Mode", "X-Subject-ID", "X-Brand-Focus-ID"}
    if (not isinstance(context, dict) or not context or set(context) - allowed
            or any(not isinstance(value, str) or "\r" in value or "\n" in value for value in context.values())):
        raise ValueError("CONTENT_SOURCE_FORMAT_INVALID")
    selectors = Headers(context)
    for key in allowed:
        if key in request.headers and request.headers[key] != selectors.get(key):
            raise ValueError("CONTENT_SOURCE_FORMAT_INVALID")
    if {name.casefold() for name in request.headers.keys()}.intersection(  # noqa: SIM118
        _SHARED_WORKSPACE_LEGACY_SCOPE_HEADERS - {name.casefold() for name in allowed}
    ):
        raise ValueError("CONTENT_SOURCE_FORMAT_INVALID")
    return selectors


@experience_bp.route("/api/experience/content-projects/export", methods=["POST"])
def export_content_project():
    from lumenis.shared.content_creation.video_editing import Timeline
    from shared_artifacts import LocalArtifactError, stage_timeline_artifact
    from lumenis.shared.agents.skills.execution import ActionType, SkillRuntimeInfo, run_execution_chain

    try:
        actor, scope = _content_project_scope("write")
        local_principal = (
            actor if "shared_workspace_scope" in scope and not isinstance(actor, dict) else None
        )
        account_actor = actor if isinstance(actor, dict) else None
        if not _content_source_same_origin():
            raise LocalArtifactError("CONTENT_SOURCE_ORIGIN_DENIED")
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("action_type") != "EXPORT":
            raise LocalArtifactError("CONTENT_EXPORT_REQUIRES_EXPORT")
        payload = body.get("input")
        allowed = {"asset_paths", "asset_refs", "timeline", "output_kind", "demo_acknowledged", "previous_artifact_id", "render_options", "delivery_options", "title", "render_media"}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise LocalArtifactError("INVALID_CONTENT_INPUT")
        task = str(body.get("task") or "导出可继续编辑的内容工程")[:2000]
        info = SkillRuntimeInfo(skill_id="shared.content_project", name="内容工程导出",
                               description="真实媒体与可回开的编辑版本", product="SHARED", domain="content",
                               version="1.0.0", enabled=True, source="shared_artifacts",
                               cross_domain_allowed=["CTH", "BMP"])
        with _content_project_assets(payload, actor, scope) as (_, assets, source_refs):
            timeline = Timeline.from_dict(payload.get("timeline"), assets=assets)
            from lumenis.shared.content_creation.rendering import validate_render_options
            render_options = validate_render_options(payload.get("render_options"))
            from shared_artifacts import _validate_content_delivery_options
            delivery_options = _validate_content_delivery_options(payload.get("delivery_options"))
            normalized = {"render_options": render_options, "delivery_options": delivery_options,"timeline": timeline.to_dict(), "scope": scope,
                          "source_artifact_refs": source_refs,
                          "output_kind": payload.get("output_kind", "video"),
                          "previous_artifact_id": payload.get("previous_artifact_id"),
                          "title": payload.get("title"), "render_media": payload.get("render_media", True)}
            from shared_artifacts import content_project_export_resource

            normalized["target"] = content_project_export_resource(
                timeline, actor=actor, source_artifact_refs=source_refs,
                output_kind=normalized["output_kind"],
                title=normalized["title"], render_media=normalized["render_media"],
                previous_artifact_id=normalized["previous_artifact_id"], render_options=render_options, delivery_options=delivery_options, **scope,
            )

            def render(ctx):
                try:
                    staged = stage_timeline_artifact(
                        timeline, actor=actor, **scope, source_execution_id=ctx.execution_id,
                        output_kind=normalized["output_kind"],
                        title=normalized["title"], render_media=normalized["render_media"],
                        previous_artifact_id=normalized["previous_artifact_id"],
                        source_artifact_refs=source_refs, render_options=render_options, delivery_options=delivery_options,
                    )
                except LocalArtifactError as exc:
                    if str(exc) != "CONTENT_PROJECT_PARENT_REVISION_REQUIRED":
                        raise
                    return {"success": False, "error": str(exc)}
                from shared_artifacts import _verified_content_project
                verified_project,verified_render,verified_record,_=_verified_content_project(staged["artifact"]["artifact_id"],actor=actor,**scope)
                reopened={"project":verified_project,"render":verified_render}
                if (verified_record["sha256"]!=staged["artifact"]["sha256"]
                        or reopened["render"] != staged["render"]
                        or reopened["project"] != staged["project"]):
                    raise LocalArtifactError("CONTENT_PROJECT_INTEGRITY_FAILED")
                return {"success":True,"result":{"artifact":staged["artifact"],
                    "render_receipt":{key:reopened["render"][key] for key in ("state","media_sha256","size_bytes","timeline_version") if key in reopened["render"]}},
                    "diagnostics":staged}

            ctx = run_execution_chain(
                skill_id="shared.content_project", task=task, input_payload=normalized,
                action_type=ActionType.EXPORT,
                user_id=account_actor["id"] if account_actor else None,
                user_role=account_actor.get("role", "user") if account_actor else "user",
                product=("SHARED" if "shared_workspace_scope" in scope else
                         "CTH" if scope["domain_id"] == "cth" else "ZBMP"),
                domain=None if "shared_workspace_scope" in scope else scope["domain_id"],
                skill_info=info, handler=render, request_context=_content_project_execution_context(scope),
                workspace_principal=local_principal,
            )
            execution = ctx.execute_result or {}
            result = execution.get("result") if isinstance(execution, dict) else None
            if isinstance(result,dict) and result.get("success") is True and isinstance(result.get("diagnostics"),dict):
                result=result["diagnostics"]
            if ctx.status.value != "completed" or not isinstance(result, dict) or not result.get("artifact"):
                code = _content_project_error_code(ctx.error or "CONTENT_EXPORT_FAILED")
                status_code = 400 if code == "CONTENT_PROJECT_PARENT_REVISION_REQUIRED" else 503
                return jsonify({"ok": False, "code": code, "execution_id": ctx.execution_id,
                                "status": ctx.status.value, "publish_status": "not_performed"}), status_code
            return jsonify({"ok": True, "result": result, "execution_id": ctx.execution_id,
                            "evidence_recorded": bool((getattr(ctx, "evidence_record", None) or {}).get("ok")),
                            "publish_status": "not_performed"})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_EXPORT_UNAVAILABLE"}), 503


def _content_edl_request(artifact_id, *, apply):
    from shared_artifacts import LocalArtifactError, prepare_content_edl_application, apply_content_edl_application
    try:
        actor, scope = _content_project_scope("write")
        if not _content_source_same_origin():
            raise LocalArtifactError("CONTENT_SOURCE_ORIGIN_DENIED")
        body = request.get_json(silent=True)
        keys = {"edl", "request_id", "expected_resource", "confirmed"} if apply else {"edl", "request_id"}
        if not isinstance(body, dict) or set(body) != keys:
            raise LocalArtifactError("CONTENT_EDL_INPUT_INVALID")
        service = apply_content_edl_application if apply else prepare_content_edl_application
        result = service(artifact_id, body["edl"], actor=actor, scope=scope,
                         **{key: value for key, value in body.items() if key != "edl"})
        return jsonify({"ok": True, **result, "publish_status": "not_performed"})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_EDL_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/content-projects/<artifact_id>/edl/prepare", methods=["POST"])
def prepare_content_edl(artifact_id):
    return _content_edl_request(artifact_id, apply=False)


@experience_bp.route("/api/experience/content-projects/<artifact_id>/edl/apply", methods=["POST"])
def apply_content_edl(artifact_id):
    return _content_edl_request(artifact_id, apply=True)


@experience_bp.route("/api/experience/content-projects")
def content_project_list():
    """Discover saved projects through the same scope boundary as reopening."""
    from shared_artifacts import list_content_projects, LocalArtifactError

    try:
        actor, scope = _content_project_scope("read")
        limit = request.args.get("limit", "20")
        if not limit.isascii() or not limit.isdecimal() or not 1 <= int(limit) <= 20:
            raise LocalArtifactError("CONTENT_PROJECT_LIMIT_INVALID")
        result = list_content_projects(
            actor=actor, **scope, limit=int(limit), cursor=request.args.get("cursor"),
        )
        return jsonify({"ok": True, **result, "publish_status": "not_performed"})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_PROJECT_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/content-projects/<artifact_id>")
def content_project_detail(artifact_id: str):
    from shared_artifacts import read_content_project

    try:
        actor, scope = _content_project_scope("read")
        project = read_content_project(artifact_id, actor=actor, **scope)
        return jsonify({"ok": True, "project": project,
                        "package_url": f"/api/experience/content-projects/{artifact_id}/package",
                        "preview_url": (f"/api/experience/content-projects/{artifact_id}/media"
                                        if project["render"]["state"] == "rendered_verified" else None),
                        "publish_status": "not_performed"})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_PROJECT_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/content-projects/<artifact_id>/package")
def content_project_package(artifact_id: str):
    from shared_artifacts import _verified_content_project, ContentProjectMedia, _source_file_identity

    try:
        if set(request.args) - {'format','context','sha256'}:
            raise ValueError('CONTENT_PROJECT_FORMAT_INVALID')
        if not _content_source_same_origin():
            raise ValueError('CONTENT_SOURCE_ORIGIN_DENIED')
        selectors = _content_media_selectors(expected_format='package')
        actor, scope = _content_project_scope("read", selectors=selectors)
        project, _, record, path = _verified_content_project(artifact_id, actor=actor, **scope)
        if 'sha256' in request.args and request.args.getlist('sha256') != [record['sha256']]:
            raise ValueError('CONTENT_PROJECT_VERSION_MISMATCH')
        media = ContentProjectMedia(f'{artifact_id}.zip', 'application/zip', record['sha256'], record['size_bytes'],
            path, 0, _source_file_identity(path), artifact_id, actor, scope, record['sha256'],
            tuple(project.get('source_artifact_refs', [])))
        return _content_project_stream_response(media, actor=actor, scope=scope, selectors=selectors, as_attachment=True)
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_PROJECT_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/content-projects/<artifact_id>/media")
def content_project_media(artifact_id: str):
    from shared_artifacts import open_content_project_media

    try:
        if set(request.args) - {"format", "context", "sha256"}:
            raise ValueError("CONTENT_PROJECT_FORMAT_INVALID")
        if not _content_source_same_origin():
            raise ValueError('CONTENT_SOURCE_ORIGIN_DENIED')
        selectors = _content_media_selectors()
        actor, scope = _content_project_scope("read", selectors=selectors)
        media = open_content_project_media(artifact_id, actor=actor, **scope)
        if "sha256" in request.args and request.args.getlist("sha256") != [media.sha256]:
            raise ValueError("CONTENT_PROJECT_VERSION_MISMATCH")
        return _content_project_stream_response(media, actor=actor, scope=scope, selectors=selectors)
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_PROJECT_UNAVAILABLE"}), 503


def _content_project_stream_response(media, *, actor, scope, selectors, as_attachment=False):
    from flask import Response, stream_with_context
    etag = f'"{media.sha256}"'
    disposition = 'attachment' if as_attachment else 'inline'
    headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
               "Accept-Ranges": "bytes", "ETag": etag,
               "Cross-Origin-Resource-Policy": "same-origin",
               "Content-Disposition": f'{disposition}; filename="{media.filename}"'}
    start, stop, status = 0, media.size_bytes, 200
    if request.method != 'HEAD' and request.headers.get('Range') and request.headers.get('If-Range', etag) == etag:
        ranges = request.range
        selected = ranges.range_for_length(media.size_bytes) if ranges is not None and ranges.units == 'bytes' else None
        if selected is None:
            headers['Content-Range'] = f'bytes */{media.size_bytes}'
            return Response(status=416, headers=headers)
        start, stop = selected
        status = 206
        headers['Content-Range'] = f'bytes {start}-{stop - 1}/{media.size_bytes}'

    def authorize_stream():
        if (actor, scope) != _content_project_scope('read', selectors=selectors):
            raise ValueError('CONTENT_PROJECT_CONTEXT_MISMATCH')

    response = Response(() if request.method == 'HEAD' else stream_with_context(
        media.iter_bytes(start, stop, authorize=authorize_stream)), status=status,
        headers=headers, mimetype=media.media_type, direct_passthrough=True)
    response.content_length = stop - start
    return response


@experience_bp.route("/api/experience/shared-skills/shared.video_shotcraft/render", methods=["POST"])
def render_shared_video_artifact():
    """Render explicitly supplied local assets into a staged video artifact.

    This is an EXPORT action, not a platform action.  The global permission
    resolver maps it to DATA_EXPORT; the execution chain still records the
    action, Evidence and Evaluation.  No remote URL or browser media request
    is accepted here.
    """
    from lumenis_shared_skills import validate_input
    from shared_artifacts import LocalArtifactError, render_local_video_artifact, validate_local_asset

    body = request.get_json(silent=True) or {}
    action_value = str(body.get("action_type") or "").upper()
    if action_value != "EXPORT":
        return jsonify({
            "ok": False,
            "status": "denied",
            "code": "VIDEO_RENDER_REQUIRES_EXPORT",
            "reason": "视频渲染是受控的 staged EXPORT，不能伪装成普通分析请求。",
        }), 403
    payload = body.get("input") if isinstance(body.get("input"), dict) else {}
    invalid = validate_input(payload)
    if invalid:
        return jsonify({"ok": False, "status": "denied", **invalid}), 403
    if any(str(key).lower() in {"url", "media_url", "media_urls", "remote_url", "download_url"}
           for key in payload.keys()):
        return jsonify({
            "ok": False,
            "status": "denied",
            "code": "LOCAL_ASSETS_ONLY",
            "reason": "视频渲染只接受明确提交的本地素材，不接受远程媒体地址。",
        }), 400
    asset_paths = payload.get("asset_paths")
    if not isinstance(asset_paths, list) or not asset_paths:
        return jsonify({
            "ok": False,
            "status": "input_required",
            "code": "LOCAL_ASSETS_REQUIRED",
            "reason": "必须明确提供 asset_paths；系统不会自行下载或猜测平台媒体。",
        }), 400
    try:
        # Validate before entering the execution chain so invalid/remote input
        # is a client error, never a misleading runtime failure.
        [validate_local_asset(value) for value in asset_paths]
    except LocalArtifactError as exc:
        return jsonify({
            "ok": False,
            "status": "rejected",
            "code": str(exc),
            "reason": "本地素材未通过受限渲染边界，未产生制品。",
            "external_fetch": False,
        }), 400
    raw_domain = str(body.get("domain") or payload.get("domain") or "CTH").strip().upper()
    domain_id = {"CTH": "cth", "BMP": "zbmp", "ZBMP": "zbmp"}.get(raw_domain)
    if not domain_id:
        return jsonify({
            "ok": False,
            "status": "denied",
            "code": "DOMAIN_NOT_ALLOWED",
            "reason": "视频共享能力只接受 CTH/BMP 产品领域。",
        }), 400
    from domain_isolation import resolve_domain_identity

    domain_id, product_id = resolve_domain_identity(domain_id=domain_id)
    evidence_id = str(payload.get("evidence_id") or "").strip()
    note_id = str(payload.get("note_id") or "").strip()
    if evidence_id or note_id:
        if not evidence_id or not note_id or payload.get("source", "browser_rendered") != "browser_rendered":
            return jsonify({
                "ok": False,
                "status": "denied",
                "code": "BROWSER_RENDERED_EVIDENCE_REQUIRED",
                "reason": "关联视频 Evidence 时必须同时提供 note_id，并声明 browser_rendered。",
            }), 400

    task = str(body.get("task") or payload.get("brief") or "视频本地素材成片草稿").strip()[:4000]
    normalized_payload = dict(payload)
    normalized_payload["domain"] = domain_id
    normalized_payload["product"] = product_id

    from lumenis.shared.agents.skills.execution import ActionType, SkillRuntimeInfo, run_execution_chain

    runtime_info = SkillRuntimeInfo(
        skill_id="shared.video_shotcraft",
        name="专业级片头与转场",
        description="共享视频成片草稿能力",
        product="SHARED",
        domain="content",
        version="1.0.0",
        enabled=True,
        source="lumenis_shared_skills",
        cross_domain_allowed=["CTH", "BMP"],
    )

    def _render(_ctx):
        return render_local_video_artifact(
            normalized_payload["asset_paths"],
            brief=task,
            product_id=product_id,
            domain_id=domain_id,
            source_execution_id=_ctx.execution_id,
            evidence_id=evidence_id,
            note_id=note_id,
        )

    try:
        ctx = run_execution_chain(
            skill_id="shared.video_shotcraft",
            task=task,
            input_payload=normalized_payload,
            action_type=ActionType.EXPORT,
            user_role="user",
            product=product_id,
            domain=domain_id,
            skill_info=runtime_info,
            handler=_render,
        )
        execute_result = ctx.execute_result or {}
        result = execute_result.get("result") if isinstance(execute_result, dict) else None
        result = result if isinstance(result, dict) else {}
        ok = ctx.status.value == "completed" and bool(result.get("artifact"))
        return jsonify({
            "ok": ok,
            "status": result.get("status") if ok else ctx.status.value,
            "execution_status": ctx.status.value,
            "skill_id": "shared.video_shotcraft",
            "execution_id": ctx.execution_id,
            "artifact": result.get("artifact"),
            "render": result if ok else None,
            "error": None if ok else (ctx.error or execute_result.get("error")),
            "error_type": None if ok else type(ctx.error).__name__ if ctx.error else execute_result.get("code"),
            "permission": ctx.permission_result,
            "firewall": ctx.firewall_result,
            "effect_fence": ctx.effect_fence_result,
            "evidence": ctx.evidence,
            "evidence_recorded": bool(getattr(ctx, "evidence_record", {}).get("ok", False)),
            "evaluation": ctx.evaluation,
            "external_fetch": False,
            "approval_required": True,
            "publish_status": "not_performed",
        }), (200 if ok else 503)
    except LocalArtifactError as exc:
        return jsonify({
            "ok": False,
            "status": "rejected",
            "code": str(exc),
            "reason": "本地素材未通过受限渲染边界，未产生制品。",
            "external_fetch": False,
        }), 400
    except Exception as exc:  # noqa: BLE001 - API boundary must not expose paths
        return jsonify({
            "ok": False,
            "status": "error",
            "error_type": type(exc).__name__,
            "external_fetch": False,
        }), 503


@experience_bp.route("/api/experience/artifacts/<artifact_id>")
def shared_artifact_detail(artifact_id: str):
    """Return staged artifact metadata without exposing its filesystem path."""
    from shared_artifacts import get_artifact

    artifact = get_artifact(artifact_id)
    if not artifact:
        return jsonify({"ok": False, "error": "artifact not found"}), 404
    return jsonify({
        "ok": True,
        "source": "runtime",
        "artifact": artifact,
        "approval_required": True,
        "publish_status": "not_performed",
        "preview_url": f"/api/experience/artifacts/{artifact_id}/file",
    })


@experience_bp.route("/api/experience/artifacts/<artifact_id>/file")
def shared_artifact_file(artifact_id: str):
    """Stream a staged local artifact after root-confinement validation."""
    from shared_artifacts import artifact_file_path, get_artifact

    artifact = get_artifact(artifact_id)
    path = artifact_file_path(artifact_id)
    if not artifact or path is None:
        return jsonify({"ok": False, "error": "artifact not found"}), 404
    return send_file(
        path,
        mimetype=artifact.get("media_type") or "application/octet-stream",
        as_attachment=False,
        download_name=artifact.get("filename") or "artifact",
        conditional=True,
    )


@experience_bp.route("/api/experience/ai/publish-requests", methods=["POST"])
def create_publish_approval_request():
    """Create a traceable human-approval task without publishing externally."""
    from shared_artifacts import get_artifact

    body = request.get_json(silent=True) or {}
    artifact_id = str(body.get("artifact_id") or "").strip()
    artifact = get_artifact(artifact_id)
    if not artifact:
        return jsonify({"ok": False, "code": "ARTIFACT_NOT_FOUND", "error": "artifact not found"}), 404
    if artifact.get("status") != "staged" or not artifact.get("approval_required"):
        return jsonify({
            "ok": False,
            "code": "ARTIFACT_NOT_APPROVABLE",
            "error": "only staged approval-required artifacts may enter the publish queue",
        }), 409
    requested_platform = str(body.get("platform") or "rednote_hk").strip().lower()
    if requested_platform in {"xhs", "rednote", "xhs_hk", "rednote_hk"}:
        platform = "rednote_hk"
        account_policy = "XHS_RETINAUT"
    else:
        return jsonify({
            "ok": False,
            "code": "PLATFORM_NOT_ENABLED",
            "error": "当前只开放已验证的香港/国际 RedNote 审批目标；大陆账号及其他平台保持暂停。",
        }), 409
    raw_domain = str(body.get("domain") or artifact.get("domain_id") or "").strip().lower()
    if raw_domain not in {"cth", "zbmp"} or raw_domain != str(artifact.get("domain_id") or "").lower():
        return jsonify({
            "ok": False,
            "code": "DOMAIN_MISMATCH",
            "error": "发布审批的产品领域必须与制品绑定领域一致。",
        }), 409
    requested_by = str(body.get("requested_by") or "product_user").strip()[:64]
    note = str(body.get("note") or "").strip()[:500]
    try:
        from ai_task_engine import get_task_engine, init_task_engine_db

        init_task_engine_db()
        engine = get_task_engine()
        created = engine.create_task(
            "申请发布内容到香港/国际 RedNote（仅创建人工审批请求，不执行外部操作）",
            context={
                "artifact_id": artifact_id,
                "domain": raw_domain,
                "platform": platform,
                "account_policy": account_policy,
                "publish_mode": "human_approval_required",
                "external_action": "not_executed",
                "request_note": note,
            },
            created_by=requested_by,
        )
        task = engine.parse_task(created["task_id"])
        return jsonify({
            "ok": True,
            "status": "awaiting_approval" if task.get("status") == "awaiting_approval" else task.get("status"),
            "approval_required": True,
            "external_action": "not_executed",
            "platform": platform,
            "account_policy": account_policy,
            "artifact": artifact,
            "task": task,
            "next_step": "human_manual_publish",
            "human_controls_publish": True,
            "product_will_not_publish": True,
        }), 200
    except Exception as exc:  # noqa: BLE001 - do not expose DB details
        return jsonify({"ok": False, "status": "error", "error_type": type(exc).__name__}), 503


@experience_bp.route("/api/experience/ai/publish-requests/<task_id>")
def publish_approval_request_detail(task_id: str):
    """Read one publish approval task and keep external action explicit."""
    try:
        from ai_task_engine import get_task_engine

        task = get_task_engine().get_task(task_id)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "status": "error", "error_type": type(exc).__name__}), 503
    if not task:
        return jsonify({"ok": False, "error": "publish request not found"}), 404
    context = task.get("context") if isinstance(task.get("context"), dict) else {}
    return jsonify({
        "ok": True,
        "task": task,
        "approval_required": True,
        "external_action": "not_executed",
        "next_step": "human_manual_publish",
        "human_controls_publish": True,
        "product_will_not_publish": True,
        "artifact_id": context.get("artifact_id"),
        "platform": context.get("platform"),
        "account_policy": context.get("account_policy"),
    })


@experience_bp.route("/api/experience/shared-skills/<skill_id>/run", methods=["POST"])
def run_shared_skill_route(skill_id: str):
    """Execute a shared skill through the standard permission/evidence chain.

    This surface intentionally accepts only read/analysis/suggestion actions.
    Export, write, publish, commit and push remain outside the AI/Shared
    surface and must use their own permissioned human-approved paths.
    """
    from lumenis_shared_skills import get_shared_skill, run_shared_skill, validate_input

    spec = get_shared_skill(skill_id)
    if not spec:
        return jsonify({"ok": False, "status": "not_found", "error": "shared skill not found"}), 404
    body = request.get_json(silent=True) or {}
    action_value = str(body.get("action_type") or "ANALYZE").upper()
    if action_value not in {"READ", "ANALYZE", "SUGGEST"}:
        return jsonify({
            "ok": False, "status": "denied", "code": "SHARED_ACTION_NOT_ALLOWED",
            "reason": "Shared Content & Creation 只允许 READ/ANALYZE/SUGGEST；写入、发布和推送必须走人工审批链。",
        }), 403
    task = str(body.get("task") or "").strip()[:4000]
    payload = body.get("input") if isinstance(body.get("input"), dict) else {}
    invalid = validate_input(payload)
    if invalid:
        return jsonify({"ok": False, "status": "denied", **invalid}), 403
    # The product lens travels as context; the shared skill never becomes a
    # fourth product line and never changes ownership of CTH/BMP facts.  The
    # browser uses product-facing labels (CTH/BMP), while the existing
    # execution firewall contract uses canonical scopes (cth/zbmp).  Normalize
    # at this boundary instead of weakening the firewall or leaking a second
    # domain vocabulary into the execution chain.
    requested_domain = body.get("domain") if "domain" in body else payload.get("domain")
    if requested_domain is None:
        try:
            from ai_domain_context import get_current_domain
            raw_domain = get_current_domain().upper()
        except (ImportError, TypeError, ValueError):
            return jsonify({
                "ok": False, "status": "denied", "code": "DOMAIN_REQUIRED",
                "reason": "共享能力需要当前服务端请求绑定的产品域。",
            }), 400
    elif type(requested_domain) is not str or not requested_domain or requested_domain != requested_domain.strip():
        return jsonify({
            "ok": False, "status": "denied", "code": "DOMAIN_NOT_ALLOWED",
            "reason": "共享能力需要规范的 CTH/BMP 产品域。",
        }), 400
    else:
        raw_domain = requested_domain.upper()
    if ("domain" in body and "domain" in payload
            and type(payload["domain"]) is str
            and payload["domain"].upper() != raw_domain):
        return jsonify({
            "ok": False, "status": "denied", "code": "CONTEXT_SCOPE_MISMATCH",
            "reason": "请求域与资料域不一致。",
        }), 400
    domain_id = {"CTH": "cth", "BMP": "zbmp", "ZBMP": "zbmp", "SYSTEM": "system"}.get(raw_domain)
    if not domain_id:
        return jsonify({
            "ok": False,
            "status": "denied",
            "code": "DOMAIN_NOT_ALLOWED",
            "reason": "共享能力只接受 CTH/BMP 产品领域（内部映射为 cth/zbmp）。",
        }), 400
    payload = dict(payload)
    payload["domain"] = domain_id
    payload["product"] = "LUMENIS"

    from lumenis.shared.agents.skills.execution import ActionType, SkillRuntimeInfo, run_execution_chain
    from domain_isolation import resolve_domain_identity

    domain_id, product_id = resolve_domain_identity(domain_id=domain_id)

    try:
        action_type = ActionType(action_value)
        runtime_info = SkillRuntimeInfo(
            skill_id=skill_id,
            name=spec["name"],
            description=spec["description"],
            product="SHARED",
            domain="content",
            version=spec["metadata"]["version"],
            enabled=True,
            source="lumenis_shared_skills",
            cross_domain_allowed=["CTH", "BMP"],
        )
        ctx = run_execution_chain(
            skill_id=skill_id,
            task=task,
            input_payload=payload,
            action_type=action_type,
            user_role="user",
            product=product_id,
            domain=domain_id,
            skill_info=runtime_info,
            handler=lambda execution_ctx: run_shared_skill(
                skill_id, task=execution_ctx.task, input_payload=execution_ctx.input_payload
            ),
        )
        execute_result = ctx.execute_result or {}
        return jsonify({
            "ok": ctx.status.value == "completed",
            "status": ctx.status.value,
            "skill_id": skill_id,
            "execution_id": ctx.execution_id,
            "result": execute_result.get("result"),
            "error": ctx.error or execute_result.get("error"),
            "permission": ctx.permission_result,
            "firewall": ctx.firewall_result,
            "effect_fence": ctx.effect_fence_result,
            "evidence": ctx.evidence,
            "evidence_recorded": bool(getattr(ctx, "evidence_record", {}).get("ok", False)),
            "evaluation": ctx.evaluation,
            "ai_is_derivative": True,
            "external_fetch": False,
        }), 200
    except ValueError as exc:
        return jsonify({"ok": False, "status": "denied", "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001 - API boundary must remain honest
        return jsonify({"ok": False, "status": "error", "error_type": type(exc).__name__}), 500


@experience_bp.route("/api/experience/content/evidence/<evidence_id>")
def content_evidence_detail(evidence_id: str):
    """返回 SH-01 可展示的创作证据字段；输入 Prompt/研究上下文永不下发。"""
    if not re.fullmatch(r"CGE-[A-Za-z0-9_-]{1,96}", evidence_id):
        return jsonify({"ok": False, "error": "invalid evidence id"}), 400
    import content_generation
    try:
        expected_context = content_generation.authorize_content_root_request(strict=True)
    except ValueError as exc:
        if str(exc) == "AUTH_REQUIRED":
            return jsonify({"ok": False, "code": "AUTH_REQUIRED"}), 401
        return jsonify({"ok": False, "error": "invalid content scope"}), 400
    except PermissionError:
        return jsonify({"ok": False, "error": "content access denied"}), 403
    except RuntimeError:
        return jsonify({"ok": False, "error": "content authorization unavailable"}), 503
    record = _safe(content_generation.get_evidence, evidence_id, default={"__error__": "unavailable"})
    if _is_err(record):
        return jsonify({"ok": False, "error": "evidence runtime unavailable"}), 503
    if not record:
        return jsonify({"ok": False, "error": "evidence not found"}), 404
    try:
        output = json.loads(record.get("output_json") or "{}")
    except (TypeError, ValueError):
        output = {"status": "stored output is not structured JSON"}
    evaluations = [{key: item.get(key) for key in (
        "relevance", "creativity", "brand_fit", "platform_fit", "overall",
        "eval_method", "human_rating", "created_at",
    )} for item in record.get("evaluations", [])]
    # Re-read through the owner: signed receipt, actor/root and live source rights
    # must still match. A changed record requires a fresh request, not stale output.
    try:
        if content_generation.authorize_content_root_request(strict=True) != expected_context:
            raise PermissionError("CONTENT_CONTEXT_CHANGED")
        current_record = content_generation.get_evidence(evidence_id)
        if current_record != record or not current_record:
            raise PermissionError("CONTENT_EVIDENCE_CHANGED_OR_REVOKED")
        if content_generation.authorize_content_root_request(strict=True) != expected_context:
            raise PermissionError("CONTENT_CONTEXT_CHANGED")
    except (ValueError, PermissionError):
        return jsonify({"ok": False, "error": "content access changed"}), 403
    except Exception:
        return jsonify({"ok": False, "error": "evidence runtime unavailable"}), 503
    return jsonify({"ok": True, "source": "runtime", "ai_is_derivative": True, "evidence": {
        "evidence_id": record.get("evidence_id"),
        "content_type": record.get("content_type"),
        "provider": record.get("provider"),
        "model": record.get("model"),
        "status": record.get("status"),
        "confidence": record.get("confidence"),
        "iteration": record.get("iteration"),
        "created_at": record.get("created_at"),
        "output": output,
        "evaluations": evaluations,
    }})


def _verified_execution_evidence(ctx) -> bool:
    """AI-01 receipt check: Evidence counts as recorded only after read-back.

    The execution chain's own ``{"ok": True}`` flag is not trusted by itself. The
    Evidence owner must return the record it wrote for this exact execution:
    skill_execution source, source/task/trace bound to ``execution_id``, an intact
    content hash, and a payload naming the same execution. Anything else is
    reported as not recorded (AI-01.md section 1/2: no fake output or trace).
    """
    record = getattr(ctx, "evidence_record", None)
    execution_id = getattr(ctx, "execution_id", None)
    if not isinstance(record, dict) or record.get("ok") is not True:
        return False
    evidence_id = record.get("evidence_id")
    if type(evidence_id) is not str or not evidence_id:
        return False
    if type(execution_id) is not str or not execution_id:
        return False
    try:
        from lumenis.shared.evidence import EvidenceStore
        from lumenis.shared.evidence.chain import compute_content_hash

        evidence = EvidenceStore().get_evidence(evidence_id)
        if evidence is None or evidence.evidence_id != evidence_id:
            return False
        if evidence.source_type != "skill_execution":
            return False
        if (evidence.source_id, evidence.task_id, evidence.trace_id) != (
                execution_id, execution_id, execution_id):
            return False
        if compute_content_hash(evidence.raw_content) != evidence.content_hash:
            return False
        payload = json.loads(evidence.raw_content)
        return isinstance(payload, dict) and payload.get("execution_id") == execution_id
    except Exception:  # noqa: BLE001 - an unreadable receipt is not a recorded one
        return False


_AI_INTENT_BODY_FIELDS = frozenset({"task", "action_type"})


def _ai_intent_trusted_domain():
    """Resolve the AI-01 execution identity from server-side scope only.

    Uses the existing canonical resolver (_content_project_scope: local workspace
    principal or signed-in actor, registry-checked FOCUS, Permission decision).
    Explicit domain GLOBAL_ALL and registered FOCUS are both supported.
    Unresolved context returns None; the caller never invents a domain.
    """
    from domain_isolation import resolve_domain_identity

    try:
        _actor, scope, decision = _content_project_scope(
            "read", module="content", include_decision=True)
    except Exception:  # noqa: BLE001 - no trusted scope means not executable
        return None
    if not isinstance(scope, dict) or type(scope.get("global_scope")) is not bool:
        return None
    try:
        domain, product = resolve_domain_identity(scope.get("domain_id"), None)
    except ValueError:
        return None
    if domain not in {"cth", "zbmp"} or product not in {"CTH", "ZBMP"}:
        return None
    actor_ref = getattr(decision, "principal_ref", None) or (
        f"actor:{getattr(decision, 'actor_id', None)}")
    return domain, product, actor_ref


@experience_bp.route("/api/experience/ai/intent", methods=["POST"])
def ai_intent():
    """AI-01 composer 提交：先过标准权限门（P0-WRITEPERM-02），通过后复用既有
    Agent Groups Skill Execution（不重复实现 AI），走 Contract/Artifact 边界。

    四态：granted / pending_approval / denied / permanent_deny。未通过权限门时在进入
    执行链之前返回，保证不写任何证据、不触碰生产写侧，也不回显任何安全内部。
    """
    if not _content_source_same_origin():
        return (
            jsonify(
                {"ok": False, "status": "denied", "code": "AI_INTENT_ORIGIN_DENIED"}
            ),
            403,
        )
    body = request.get_json(silent=True)
    # AI-01.md:56-57 / BACKEND-GAP-029: only task and action_type are accepted;
    # identity, domain, product, skill and input never come from the body.
    if not isinstance(body, dict) or set(body) - _AI_INTENT_BODY_FIELDS:
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "denied",
                    "reason": "only task and action_type are accepted",
                }
            ),
            400,
        )
    task = body.get("task") if isinstance(body.get("task"), str) else ""
    task = task.strip()
    if not task:
        return jsonify({"ok": False, "error": "task required"}), 400
    if len(task) > 4000:
        return jsonify({"ok": False, "error": "task too long (max 4000)"}), 400

    # ── 第 1 步：解析动作类型（非法值 fail-closed） ──
    from lumenis.shared.agents.skills.execution import ActionType

    raw_action = str(body.get("action_type", "ANALYZE")).upper()
    try:
        action_type = ActionType(raw_action)
    except ValueError:
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "denied",
                    "reason": f"unknown action_type: {raw_action}",
                }
            ),
            400,
        )

    # ── 第 2 步：永久拒绝类别（AI 派生层永不发布/推送/删除） ──
    if raw_action in PERMANENT_DENY_ACTIONS:
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "permanent_deny",
                    "reason": "AI composer 为派生增强层，不允许执行发布/上线/推送/删除类操作。",
                }
            ),
            403,
        )

    # ── 第 3 步：标准权限门检查 ──
    gate_spec = _action_gate_spec(raw_action)
    if gate_spec is None:
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "denied",
                    "reason": f"action_type {raw_action} 未注册权限映射（fail-closed）",
                }
            ),
            403,
        )
    operation_type, risk_level = gate_spec
    trusted = _ai_intent_trusted_domain()
    decision = get_permission_gate().check(
        operation_type,
        resource="agent_runtime.intent",
        risk_level=risk_level,
        caller=trusted[2] if trusted else "experience_user",
        domain_id=trusted[0].upper() if trusted else "CTH",
    )
    if not decision.allowed:
        # pending_approval 用 200（流程未失败，等待人工）；denied 用 403。两者都不执行。
        status = "pending_approval" if decision.requires_approval else "denied"
        http_code = 200 if status == "pending_approval" else 403
        return (
            jsonify(
                {
                    "ok": False,
                    "status": status,
                    "reason": decision.reason,
                    "permission_required": getattr(
                        decision.permission_required,
                        "value",
                        decision.permission_required,
                    ),
                    "risk_level": risk_level.value,
                    "requires_approval": bool(decision.requires_approval),
                    "audit_id": decision.audit_id,
                }
            ),
            http_code,
        )

    # ── 第 4 步：仅在 granted 后进入执行链（此前任何分支都不会写证据） ──
    if trusted is None:
        # No server-resolved domain/scope: no durable task may be created.
        return jsonify(
            {
                "ok": False,
                "permission_status": "granted",
                "status": "not_executable",
                "code": "AI_INTENT_AUTHORIZED_SCOPE_REQUIRED",
                "audit_id": decision.audit_id,
                "evidence_recorded": False,
                "ai_is_derivative": True,
            }
        )
    intent_domain, _intent_product, actor_ref = trusted
    try:
        actor, selected_scope = _content_project_scope(
            "read", module="content", read_only_auth=True
        )
        from lumenis.system.security.permission import LocalWorkspacePrincipal

        if type(actor) is LocalWorkspacePrincipal:
            expected_actor_ref = actor.principal_ref
        elif isinstance(actor, dict) and type(actor.get("id")) is int:
            expected_actor_ref = "actor:" + str(actor["id"])
        else:
            raise PermissionError("AI_INTENT_ACTOR_REQUIRED")
        if (
            actor_ref != expected_actor_ref
            or selected_scope.get("domain_id") != intent_domain
        ):
            raise PermissionError("AI_INTENT_CONTEXT_CHANGED")
        from ai_task_engine import get_task_engine
        from agent_runtime.task_binding import create_agent_task, start_agent_task

        scope = {
            key: selected_scope.get(key)
            for key in ("global_scope", "subject_id", "brand_focus_id")
        }
        engine = get_task_engine()
        record = create_agent_task(
            engine, actor=actor, goal=task, domain_id=intent_domain, scope=scope
        )
        start_agent_task(record["task_id"])
        return (
            jsonify(
                {
                    "ok": True,
                    "permission_status": "granted",
                    "audit_id": decision.audit_id,
                    "task_id": record["task_id"],
                    "execution_id": record["task_id"],
                    "execution_kind": "AGENT_TASK",
                    "status": record["status"],
                    "return_ref": "/api/ai/tasks/" + record["task_id"],
                    "evidence_recorded": False,
                    "ai_is_derivative": True,
                    "note": "Task accepted; planning and tool outcomes are read from the durable task owner.",
                }
            ),
            202,
        )
    except PermissionError as exc:
        return jsonify({"ok": False, "status": "denied", "code": str(exc)}), 403
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "status": "denied", "code": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "code": "AI_INTENT_TASK_OWNER_UNAVAILABLE"}), 503


def register_experience_runtime(app):
    """在 app.py 中调用以注册本蓝图（与其他蓝图一致的加法式挂载）。"""
    app.register_blueprint(experience_bp)
    return app


@experience_bp.get("/api/experience/saved-work/<artifact_id>/attachments/<name>")
def download_work_attachment(artifact_id, name):
    def execute():
        import io
        from flask import send_file
        from lumenis.shared.reporting.saved_work import download_attachment
        if request.args:
            raise ValueError("WORK_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("read")
        result = download_attachment(artifact_id, name=name, actor=actor, scope=scope)
        response = send_file(io.BytesIO(result["content"]), mimetype="application/octet-stream",
                             as_attachment=True, download_name=result["filename"], max_age=0)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Content-SHA256"] = result["sha256"]
        return response
    return _shared_work_response(execute)


@experience_bp.route("/api/experience/entity-profiles", methods=["GET", "POST"])
def entity_profile_workflow():
    """Exact registered entity research, using the existing document admission."""
    from lumenis.importer import entity_profiles
    from lumenis.system.security.permission import get_permission_gate, PermissionLevel

    try:
        actor, scope = _shared_work_actor_scope(
            "read" if request.method == "GET" else "write"
        )
        if request.method == "GET":
            result = entity_profiles.read_profiles(actor=actor, scope=scope)
            query = request.args.get("query", "").casefold()
            if query:
                result["matching_assertions"] = [
                    a
                    for row in result["versions"]
                    for a in row["manifest"]["assertions"]
                    if query in (a["field"] + " " + str(a["value"])).casefold()
                ]
            return jsonify({"ok": True, "result": result})
        if not _content_source_same_origin():
            raise PermissionError("ENTITY_PROFILE_ORIGIN_DENIED")
        body = request.get_json(silent=True)
        if (
            not isinstance(body, dict)
            or set(body) - {"manifest", "mode", "confirmed_resource", "confirm"}
            or body.get("mode", "prepare") not in {"prepare", "import", "revoke"}
        ):
            raise ValueError("ENTITY_PROFILE_REQUEST_INVALID")
        prepared = entity_profiles.prepare_profile(
            body.get("manifest"), actor=actor, scope=scope
        )
        if body.get("mode", "prepare") == "prepare":
            return jsonify(
                {
                    "ok": True,
                    "state": "PREPARED",
                    "resource": prepared["resource"],
                    "manifest_sha256": prepared["sha256"],
                    "operation_type": "data_import",
                    "approval_issued": False,
                    "rights": "private research compilation only; publisher rights remain UNKNOWN",
                }
            )
        if (
            body.get("confirm") is not True
            or body.get("confirmed_resource") != prepared["resource"]
        ):
            raise PermissionError("ENTITY_PROFILE_EXACT_CONFIRMATION_REQUIRED")
        gate = get_permission_gate()
        if not gate.has_permission(
            PermissionLevel.HUMAN_APPROVAL
        ) or not gate.has_permission(PermissionLevel.COMMIT):
            raise PermissionError("ENTITY_PROFILE_MANUAL_AUTHORITY_REQUIRED")
        resource = prepared["resource"]
        token = gate.get_valid_approval_token("data_import", resource, exact=True)
        if body["mode"] == "revoke":
            return jsonify(
                {"ok": True, "revoked": bool(token and gate.revoke_approval(token))}
            )
        if token is None:
            context = entity_profiles._context(actor, scope, "write")
            token = gate.grant_approval(
                "data_import",
                resource=resource,
                duration_minutes=5,
                granted_by=context.get("principal_ref")
                or "actor:" + str(context["actor_id"]),
            )
        try:
            result = entity_profiles.import_profile(
                body["manifest"], actor=actor, scope=scope
            )
        except Exception:
            gate.revoke_approval(token)
            raise
        return jsonify(
            {"ok": True, "result": result, "external_effect": "not_performed"}
        )
    except PermissionError as exc:
        return jsonify({"ok": False, "code": str(exc)}), 403
    except (ValueError, TypeError, LookupError) as exc:
        return jsonify({"ok": False, "code": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "code": "ENTITY_PROFILE_UNAVAILABLE"}), 503


def _entity_profile_route_matches():
    return (
        request.endpoint == "experience_runtime.entity_profile_workflow"
        and request.url_rule is not None
        and request.url_rule.rule == "/api/experience/entity-profiles"
        and request.method in {"GET", "POST"}
    )


def _entity_profile_local_access_allowed():
    from lumenis.system.security.permission import LocalWorkspacePrincipal

    if not _entity_profile_route_matches():
        return False
    try:
        actor, _scope = _shared_work_actor_scope(
            "read" if request.method == "GET" else "write"
        )
        return type(actor) is LocalWorkspacePrincipal
    except (PermissionError, ValueError):
        return False


@experience_bp.route("/api/experience/reports/statistics", methods=["GET", "POST"])
def analyze_statistics_material():
    """Deterministic statistics over a currently authorized imported source."""

    def execute():
        from lumenis.shared.reporting.business_brief import analyze_statistics_source
        from lumenis_app_api import _internal_pitch_body

        if request.method == "GET":
            if request.args:
                raise ValueError("STATISTICS_REQUEST_INVALID")
            _shared_work_actor_scope("read")
            from lumenis.shared.reporting.business_brief import statistics_capabilities

            return statistics_capabilities()
        body = _internal_pitch_body()
        if (
            not isinstance(body, dict)
            or "evidence_id" not in body
            or set(body) - {"evidence_id", "options", "business_purpose"}
        ):
            raise ValueError("STATISTICS_REQUEST_INVALID")
        if not _content_source_same_origin():
            raise PermissionError("STATISTICS_ORIGIN_DENIED")
        actor, scope = _shared_work_actor_scope("read")
        return analyze_statistics_source(
            body["evidence_id"],
            actor=actor,
            scope=scope,
            options=body.get("options"),
            business_purpose=body.get("business_purpose"),
        )

    return _shared_work_response(execute)


def _statistics_route_matches():
    return (
        request.method in {"GET", "POST"}
        and request.endpoint == "experience_runtime.analyze_statistics_material"
        and request.url_rule is not None
        and request.url_rule.rule == "/api/experience/reports/statistics"
    )


def _statistics_local_access_allowed():
    from lumenis.system.security.permission import LocalWorkspacePrincipal

    if not _statistics_route_matches():
        return False
    try:
        actor, _scope = _shared_work_actor_scope("read")
        return type(actor) is LocalWorkspacePrincipal
    except (ValueError, PermissionError):
        return False


@experience_bp.post("/api/experience/reports/financial/analyze")
def analyze_financial_material():
    return _financial_material_response(save=False)


@experience_bp.post("/api/experience/reports/financial/save")
def save_financial_material():
    return _financial_material_response(save=True)


def _financial_material_response(*, save):
    """Existing imported Evidence to scoped analysis and original SavedWork."""

    def execute():
        from lumenis.importer.financial import (
            analyze_financial_source,
            save_financial_analysis,
        )
        from lumenis_app_api import _internal_pitch_body

        body = _internal_pitch_body()
        allowed = {"evidence_id", "format", "annotations", "filing_id", "filed", "form", "identity_review_artifact_id", "fs_div"}
        if save:
            allowed |= {"request_id", "work_id", "previous_artifact_id"}
        if (
            not isinstance(body, dict)
            or "evidence_id" not in body
            or set(body) - allowed
            or (save and "request_id" not in body)
        ):
            raise ValueError("FINANCIAL_REQUEST_INVALID")
        if not _content_source_same_origin():
            raise PermissionError("FINANCIAL_ORIGIN_DENIED")
        actor, scope = _shared_work_actor_scope("write" if save else "read")
        operation = save_financial_analysis if save else analyze_financial_source
        return operation(actor=actor, scope=scope, **body)

    return _shared_work_response(execute)


def _financial_route_matches():
    routes = {
        "experience_runtime.save_financial_identity_association": "/api/experience/reports/financial/identity-review",
        "experience_runtime.analyze_financial_material": "/api/experience/reports/financial/analyze",
        "experience_runtime.save_financial_material": "/api/experience/reports/financial/save",
        "experience_runtime.save_financial_collection_target": "/api/experience/reports/financial/target",
        "experience_runtime.collect_financial_material": "/api/experience/reports/financial/collect",
        "experience_runtime.import_financial_material_capture": "/api/experience/reports/financial/capture",
    }
    return (
        request.method == "POST"
        and request.endpoint in routes
        and request.url_rule is not None
        and request.url_rule.rule == routes[request.endpoint]
    )


@experience_bp.post("/api/experience/reports/financial/target")
def save_financial_collection_target():
    def execute():
        from lumenis.importer.financial import save_financial_target
        from lumenis_app_api import _internal_pitch_body

        body = _internal_pitch_body()
        fields = {
            "identity_evidence_id",
            "request_id",
            "format",
            "taxonomy",
            "concept",
            "work_id",
            "previous_artifact_id",
        }
        if (
            not isinstance(body, dict)
            or not {"identity_evidence_id", "request_id"}.issubset(body)
            or set(body) - fields
        ):
            raise ValueError("FINANCIAL_TARGET_REQUEST_INVALID")
        if not _content_source_same_origin():
            raise PermissionError("FINANCIAL_ORIGIN_DENIED")
        actor, scope = _shared_work_actor_scope("write")
        return save_financial_target(actor=actor, scope=scope, **body)

    return _shared_work_response(execute)


@experience_bp.post("/api/experience/reports/financial/collect")
def collect_financial_material():
    return _financial_source_confirmation(capture=False)


@experience_bp.post("/api/experience/reports/financial/capture")
def import_financial_material_capture():
    return _financial_source_confirmation(capture=True)


def _financial_source_confirmation(*, capture):
    """Human confirmation binds one original target or captured byte sequence."""

    def execute():
        from lumenis.importer import financial
        from lumenis.shared.reporting.saved_work import authorize
        from lumenis.system.security.permission import (
            get_permission_gate,
            PermissionLevel,
            OperationType,
        )
        from lumenis_app_api import _internal_pitch_body

        body = _internal_pitch_body()
        identifier = "capture_artifact_id" if capture else "target_artifact_id"
        fields = {identifier, "mode", "confirm", "confirmed_resource"}
        if not capture:
            fields.add("request_id")
        if not isinstance(body, dict) or identifier not in body or set(body) - fields:
            raise ValueError("FINANCIAL_CONFIRMATION_REQUEST_INVALID")
        mode = body.get("mode", "prepare")
        if mode not in {"prepare", "apply", "revoke"}:
            raise ValueError("FINANCIAL_CONFIRMATION_MODE_INVALID")
        if not _content_source_same_origin():
            raise PermissionError("FINANCIAL_ORIGIN_DENIED")
        actor, scope = _shared_work_actor_scope("write")
        prepare = (
            financial.prepare_financial_capture
            if capture
            else financial.prepare_financial_collection
        )
        prepared = prepare(body[identifier], actor=actor, scope=scope)
        if mode == "prepare":
            return prepared
        if (
            body.get("confirm") is not True
            or body.get("confirmed_resource") != prepared["resource"]
        ):
            raise PermissionError("FINANCIAL_EXACT_CONFIRMATION_REQUIRED")
        gate = get_permission_gate()
        if not gate.has_permission(
            PermissionLevel.HUMAN_APPROVAL
        ) or not gate.has_permission(PermissionLevel.COMMIT):
            raise PermissionError("FINANCIAL_MANUAL_AUTHORITY_REQUIRED")
        operation = (
            OperationType.DATA_IMPORT if capture else OperationType.COLLECTOR_START
        )
        context = authorize(actor, scope, action="write")
        token = gate.get_valid_approval_token(
            operation.value, prepared["resource"], exact=True
        )
        if mode == "revoke":
            return {
                "revoked": bool(token and gate.revoke_approval(token)),
                "resource": prepared["resource"],
            }
        if not capture and not isinstance(body.get("request_id"), str):
            raise ValueError("FINANCIAL_REQUEST_ID_REQUIRED")
        if token is None:
            token = gate.grant_approval(
                operation.value,
                resource=prepared["resource"],
                duration_minutes=5,
                granted_by=context.get("principal_ref")
                or "actor:" + str(context["actor_id"]),
            )
        try:
            if capture:
                return financial.import_financial_capture(
                    body[identifier], actor=actor, scope=scope
                )
            return financial.collect_financial_target(
                body[identifier],
                actor=actor,
                scope=scope,
                request_id=body["request_id"],
            )
        except Exception:
            gate.revoke_approval(token)
            raise

    return _shared_work_response(execute)


@experience_bp.post("/api/experience/reports/financial/identity-review")
def save_financial_identity_association():
    def execute():
        from lumenis.importer.financial import save_financial_identity_review
        from lumenis_app_api import _internal_pitch_body
        body = _internal_pitch_body()
        required = {"identity_evidence_id", "entity", "name_span", "identifier_span", "reviewed", "review_note", "request_id"}
        if not isinstance(body, dict) or not required.issubset(body) or set(body) - required - {"work_id", "previous_artifact_id"}:
            raise ValueError("FINANCIAL_IDENTITY_REVIEW_REQUEST_INVALID")
        if not _content_source_same_origin():
            raise PermissionError("FINANCIAL_ORIGIN_DENIED")
        actor, scope = _shared_work_actor_scope("write")
        return save_financial_identity_review(actor=actor, scope=scope, **body)
    return _shared_work_response(execute)


@experience_bp.post("/api/experience/reports/entity-candidates")
def entity_candidate_review_workflow():
    """Source-backed review in SavedWork; actual registration uses Registry."""
    def execute():
        from lumenis.shared.reporting import entity_candidate_review as owner
        if not _content_source_same_origin():
            raise PermissionError("ENTITY_REVIEW_ORIGIN_DENIED")
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ValueError("ENTITY_REVIEW_REQUEST_INVALID")
        mode = body.get("mode", "read")
        common = {"mode", "artifact_id"}
        fields = {"candidate_id", "decision", "rationale", "request_id", "proposed_identity", "proposed_side",
                  "work_id", "previous_artifact_id"} if mode == "review" else set()
        if set(body) - common - fields or mode not in {"read", "review", "registration"}:
            raise ValueError("ENTITY_REVIEW_REQUEST_INVALID")
        actor, scope = _shared_work_actor_scope("write" if mode == "review" else "read")
        if mode == "read":
            return owner.read_candidates(body.get("artifact_id"), actor=actor, scope=scope)
        if mode == "registration":
            return owner.registration_proposal(body.get("artifact_id"), actor=actor, scope=scope)
        required = {"candidate_id", "decision", "rationale", "request_id"}
        if not required <= set(body):
            raise ValueError("ENTITY_REVIEW_REQUEST_INVALID")
        return owner.save_review(body.get("artifact_id"), actor=actor, scope=scope,
                                 **{key: body[key] for key in fields if key in body})
    return _shared_work_response(execute)


def _entity_candidate_review_route_matches():
    return (request.endpoint == "experience_runtime.entity_candidate_review_workflow"
            and request.method == "POST" and request.url_rule is not None
            and request.url_rule.rule == "/api/experience/reports/entity-candidates")


@experience_bp.route('/api/experience/reports/staffing-options', methods=['GET', 'POST'])
def staffing_options_workflow():
    """Map one explicit business scenario into the original mathematical Task."""
    from lumenis.shared.evaluation.openai_math_papers.business_scenarios import (
        staffing_capability, staffing_task_input,
    )
    def execute():
        if request.method == 'GET':
            if request.args:
                raise ValueError('STAFFING_QUERY_INVALID')
            _shared_work_actor_scope('read')
            return staffing_capability()
        if not _content_source_same_origin():
            raise PermissionError('STAFFING_ORIGIN_DENIED')
        from ai_api import api_ai_tasks_create
        # This existing Owner resolves identity, current SourceBrief scope/hash,
        # freezes the declaration and performs original Task idempotency checks.
        return api_ai_tasks_create(staffing_task_input(request.get_json(silent=True)))
    return _shared_work_response(execute)


def _staffing_route_matches():
    return (request.endpoint == 'experience_runtime.staffing_options_workflow'
            and request.method in {'GET', 'POST'} and request.url_rule is not None
            and request.url_rule.rule == '/api/experience/reports/staffing-options')


@experience_bp.post("/api/experience/reports/macro/analyze")
def analyze_macro_material():
    return _macro_material_response(save=False)


@experience_bp.post("/api/experience/reports/macro/save")
def save_macro_material():
    return _macro_material_response(save=True)


def _macro_material_response(*, save):
    def execute():
        from lumenis.importer.macro import analyze_macro_sources, save_macro_analysis
        from lumenis_app_api import _internal_pitch_body
        body = _internal_pitch_body()
        allowed = {"evidence_ids", "selection"}
        if save:
            allowed |= {"request_id", "work_id", "previous_artifact_id"}
        if (not isinstance(body, dict) or "evidence_ids" not in body
                or set(body) - allowed or (save and "request_id" not in body)):
            raise ValueError("MACRO_REQUEST_INVALID")
        if not _content_source_same_origin():
            raise PermissionError("MACRO_ORIGIN_DENIED")
        actor, scope = _shared_work_actor_scope("write" if save else "read")
        operation = save_macro_analysis if save else analyze_macro_sources
        return operation(actor=actor, scope=scope, **body)
    return _shared_work_response(execute)


def _macro_route_matches():
    routes = {
        "experience_runtime.analyze_macro_material": "/api/experience/reports/macro/analyze",
        "experience_runtime.save_macro_material": "/api/experience/reports/macro/save",
        "experience_runtime.save_macro_collection_target": "/api/experience/reports/macro/target",
        "experience_runtime.collect_macro_material": "/api/experience/reports/macro/collect",
        "experience_runtime.import_macro_material_capture": "/api/experience/reports/macro/capture",
    }
    return (request.method == "POST" and request.endpoint in routes
            and request.url_rule is not None and request.url_rule.rule == routes[request.endpoint])


def _macro_local_access_allowed():
    from lumenis.system.security.permission import LocalWorkspacePrincipal
    if not _macro_route_matches():
        return False
    try:
        actor, _scope = _shared_work_actor_scope("read" if request.endpoint.endswith("analyze_macro_material") else "write")
        return type(actor) is LocalWorkspacePrincipal
    except (ValueError, PermissionError):
        return False


@experience_bp.post("/api/experience/reports/macro/target")
def save_macro_collection_target():
    def execute():
        from lumenis.importer.macro import save_macro_target
        from lumenis_app_api import _internal_pitch_body
        body=_internal_pitch_body()
        if (not isinstance(body,dict) or not {'source_evidence_id','request_id'}.issubset(body)
                or set(body)-{'source_evidence_id','request_id','work_id','previous_artifact_id'}):
            raise ValueError('MACRO_TARGET_REQUEST_INVALID')
        if not _content_source_same_origin():
            raise PermissionError('MACRO_ORIGIN_DENIED')
        actor,scope=_shared_work_actor_scope('write')
        return save_macro_target(actor=actor,scope=scope,**body)
    return _shared_work_response(execute)


@experience_bp.post("/api/experience/reports/macro/collect")
def collect_macro_material():
    return _macro_source_confirmation(capture=False)


@experience_bp.post("/api/experience/reports/macro/capture")
def import_macro_material_capture():
    return _macro_source_confirmation(capture=True)


def _macro_source_confirmation(*,capture):
    def execute():
        from lumenis.importer import macro
        from lumenis.shared.reporting.saved_work import authorize
        from lumenis.system.security.permission import get_permission_gate,PermissionLevel,OperationType
        from lumenis_app_api import _internal_pitch_body
        body=_internal_pitch_body();identifier='capture_artifact_id' if capture else 'target_artifact_id'
        fields={identifier,'mode','confirm','confirmed_resource'} | (set() if capture else {'request_id'})
        if not isinstance(body,dict) or identifier not in body or set(body)-fields:
            raise ValueError('MACRO_CONFIRMATION_REQUEST_INVALID')
        mode=body.get('mode','prepare')
        if mode not in {'prepare','apply','revoke'}:
            raise ValueError('MACRO_CONFIRMATION_MODE_INVALID')
        if not _content_source_same_origin():
            raise PermissionError('MACRO_ORIGIN_DENIED')
        actor,scope=_shared_work_actor_scope('write')
        prepare=macro.prepare_macro_capture if capture else macro.prepare_macro_collection
        prepared=prepare(body[identifier],actor=actor,scope=scope)
        if mode=='prepare':return prepared
        if body.get('confirm') is not True or body.get('confirmed_resource')!=prepared['resource']:
            raise PermissionError('MACRO_EXACT_CONFIRMATION_REQUIRED')
        gate=get_permission_gate()
        if not gate.has_permission(PermissionLevel.HUMAN_APPROVAL) or not gate.has_permission(PermissionLevel.COMMIT):
            raise PermissionError('MACRO_MANUAL_AUTHORITY_REQUIRED')
        operation=OperationType.DATA_IMPORT if capture else OperationType.COLLECTOR_START
        context=authorize(actor,scope,action='write')
        token=gate.get_valid_approval_token(operation.value,prepared['resource'],exact=True)
        if mode=='revoke':return {'revoked':bool(token and gate.revoke_approval(token)),'resource':prepared['resource']}
        if not capture and not isinstance(body.get('request_id'),str):
            raise ValueError('MACRO_REQUEST_ID_REQUIRED')
        if token is None:
            token=gate.grant_approval(operation.value,resource=prepared['resource'],duration_minutes=5,
                granted_by=context.get('principal_ref') or 'actor:'+str(context['actor_id']))
        try:
            if capture:return macro.import_macro_capture(body[identifier],actor=actor,scope=scope)
            return macro.collect_macro_target(body[identifier],actor=actor,scope=scope,request_id=body['request_id'])
        except Exception:
            gate.revoke_approval(token)
            raise
    return _shared_work_response(execute)


@experience_bp.post('/api/experience/work-dependencies')
def work_dependency_workflow():
    """Explicit dependency binding and adoption; no automatic rewriting."""
    def execute():
        from lumenis.shared.reporting import work_dependencies as owner
        if not _content_source_same_origin():
            raise PermissionError('DEPENDENCY_ORIGIN_DENIED')
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ValueError('DEPENDENCY_REQUEST_INVALID')
        mode = body.get('mode', 'impact')
        fields = {
            'impact': set(),
            'bind': {'dependency_id', 'location', 'source', 'expected_text', 'request_id', 'reason'},
            'accept': {'dependency_id', 'source', 'replacement_text', 'expected_preview_hash', 'request_id', 'reason'},
        }
        if not isinstance(mode, str) or mode not in fields:
            raise ValueError('DEPENDENCY_REQUEST_INVALID')
        optional = {'replace_bindings'} if mode == 'bind' else set()
        if set(body) - {'mode', 'artifact_id'} - fields[mode] - optional or not fields[mode] <= set(body):
            raise ValueError('DEPENDENCY_REQUEST_INVALID')
        actor, scope = _shared_work_actor_scope('read' if mode == 'impact' else 'write')
        function = {'impact': owner.preview_impact, 'bind': owner.bind_dependency, 'accept': owner.accept_update}[mode]
        arguments = {key: body[key] for key in fields[mode] | optional if key in body}
        return function(body.get('artifact_id'), actor=actor, scope=scope, **arguments)
    return _shared_work_response(execute)


def _work_dependency_route_matches():
    return (request.endpoint == 'experience_runtime.work_dependency_workflow'
            and request.method == 'POST' and request.url_rule is not None
            and request.url_rule.rule == '/api/experience/work-dependencies')


@experience_bp.route('/api/experience/reports/artifact-experiments', methods=['GET', 'POST'])
def artifact_experiment_workflow():
    """Source-observed variant statistics; this endpoint does not allocate exposure."""
    def execute():
        from lumenis.shared.reporting import artifact_experiments as owner
        if request.method == 'GET':
            if request.args:
                raise ValueError('ARTIFACT_EXPERIMENT_REQUEST_INVALID')
            _shared_work_actor_scope('read')
            return owner.capabilities()
        if not _content_source_same_origin():
            raise PermissionError('ARTIFACT_EXPERIMENT_ORIGIN_DENIED')
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ValueError('ARTIFACT_EXPERIMENT_REQUEST_INVALID')
        mode = body.get('mode', 'analyze')
        if not isinstance(mode, str) or mode not in {'analyze', 'save', 'read'}:
            raise ValueError('ARTIFACT_EXPERIMENT_REQUEST_INVALID')
        if mode == 'read':
            required, optional = {'artifact_id'}, set()
        else:
            evidence_input = 'evidence_id' in body
            observation_input = bool({'observation_artifact_id', 'observation_sha256'} & set(body))
            if evidence_input == observation_input:
                raise ValueError('ARTIFACT_EXPERIMENT_ONE_INPUT_REQUIRED')
            required = {'evidence_id'} if evidence_input else {'observation_artifact_id', 'observation_sha256'}
            optional = {'work_id', 'previous_artifact_id'} if mode == 'save' else set()
            if mode == 'save':
                required.add('request_id')
        if not required <= set(body) or set(body) - required - optional - {'mode'}:
            raise ValueError('ARTIFACT_EXPERIMENT_REQUEST_INVALID')
        actor, scope = _shared_work_actor_scope('write' if mode == 'save' else 'read')
        function = {'analyze': owner.analyze, 'save': owner.save, 'read': owner.read}[mode]
        return function(actor=actor, scope=scope, **{key: value for key, value in body.items() if key != 'mode'})
    return _shared_work_response(execute)


def _artifact_experiment_route_matches():
    return (request.endpoint == 'experience_runtime.artifact_experiment_workflow'
            and request.method in {'GET', 'POST'} and request.url_rule is not None
            and request.url_rule.rule == '/api/experience/reports/artifact-experiments')


@experience_bp.get("/api/experience/reports/source-brief/tasks")
def list_source_brief_tasks():
    from lumenis.shared.reporting import source_brief_tasks as tasks
    try:
        actor_ref, _, scope, actor = _source_brief_context("read", include_actor=True)
        result = tasks.engine().list_report_tasks(actor_ref=actor_ref, scope=scope,
            limit=int(request.args.get("limit", 30)), cursor=request.args.get("cursor"),
            dimension=request.args.get("dimension"), state=request.args.get("state"))
        result["items"] = [{**tasks.status(task, actor=actor), "snapshot_state":task["status"]} for task in result["items"]]
        _source_brief_context("read")
        return jsonify({"ok": True, "result": result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.patch("/api/experience/reports/source-brief/tasks/<task_id>")
def edit_source_brief_task(task_id):
    return _mutate_source_brief_task(task_id, "edit")


@experience_bp.post("/api/experience/reports/source-brief/tasks/<task_id>/<operation>")
def change_source_brief_task_state(task_id, operation):
    if operation not in {"cancel", "restore"}:
        return jsonify({"ok": False, "code": "SOURCE_BRIEF_TASK_OPERATION_INVALID"}), 404
    return _mutate_source_brief_task(task_id, operation)


def _mutate_source_brief_task(task_id, operation):
    from lumenis.shared.reporting import source_brief_tasks as tasks
    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != ({"expected_revision", "changes"} if operation == "edit" else {"expected_revision"}):
            raise ValueError("SOURCE_BRIEF_INPUT_INVALID")
        actor_ref, _, scope, actor = _source_brief_context("write", include_actor=True)
        with tasks._lock:
            current = tasks.scoped_task(task_id, actor_ref=actor_ref, scope=scope)
            if operation in {"edit", "restore"}:
                active = tasks._workers.get(task_id)
                if ((active is not None and active.is_alive())
                        or (current.get("parameters") and tasks._worker_alive(current))):
                    raise RuntimeError("SOURCE_BRIEF_TASK_WORKER_STOPPING")
            result = tasks.engine().mutate_report_task(task_id, actor_ref=actor_ref, scope=scope,
                expected_revision=body["expected_revision"], operation=operation, changes=body.get("changes"))
        return jsonify({"ok": True, "task": tasks.status(result, actor=actor)})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.get("/api/experience/reports/source-brief/taxonomy")
def research_taxonomy():
    from agent_research.taxonomy import get_research_taxonomy
    try:
        _source_brief_context("read")
        return jsonify({"ok": True, "result": get_research_taxonomy(request.args.get("language", "en"))})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.get("/api/experience/reports/source-brief/references")
def research_reference_catalog():
    from agent_research.reference_assets import query_reference_assets
    try:
        _source_brief_context("read")
        result = query_reference_assets(kind=request.args.get("kind"), query=request.args.get("query", ""),
            region=request.args.get("region"), page=int(request.args.get("page", 1)),
            page_size=int(request.args.get("limit", 20)))
        return jsonify({"ok": True, "result": result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.post("/api/experience/reports/source-brief/jobs/<job_id>/save")
def save_source_brief_result(job_id):
    from lumenis.shared.reporting.source_brief_job import get_source_brief_job, _scope_material, _media_scope
    from lumenis.shared.reporting.saved_work import save_work
    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"request_id", "title"}:
            raise ValueError("SOURCE_BRIEF_INPUT_INVALID")
        actor_ref, _, scope, actor = _source_brief_context("write", include_actor=True)
        report = get_source_brief_job(job_id, actor_id=actor_ref, expected_scope=_scope_material(**scope), actor=actor)
        target = scope if scope.get("scope_kind") else _media_scope(_scope_material(**scope))
        payload = {"source_brief_reference": {"job_id": job_id, "actor_id": actor_ref,
            "scope": _scope_material(**scope), "artifact_hash": report["artifact_outcome"]["artifact_hash"]},
            "hypothesis_review_reference": report.get("hypothesis_review"),
            "research_result": report.get("research_analysis") or report.get("business_analysis")}
        from agent_research.source_bound import decision_brief_markdown
        appendix = decision_brief_markdown(payload['research_result'])
        markdown = report['source_brief']['markdown'] + ('\n\n' + appendix if appendix else '')
        result = save_work(title=body["title"], markdown=markdown, kind="research",
            payload=payload, citations=[], request_id=body["request_id"], actor=actor, scope=target)
        return jsonify({"ok": True, "result": result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.get("/api/experience/reports/source-brief/jobs")
def list_research_reports():
    from lumenis.shared.reporting.source_brief_job import list_source_brief_jobs, _scope_material, _media_scope
    try:
        actor_ref, _, scope, actor = _source_brief_context("read", include_actor=True)
        target = scope if scope.get("scope_kind") else _media_scope(_scope_material(**scope))
        result = list_source_brief_jobs(actor=actor, scope=target, limit=int(request.args.get("limit", 30)),
                                        cursor=request.args.get("cursor"))
        return jsonify({"ok": True, "result": result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.route('/api/experience/reports/source-brief/reference-work', methods=['GET', 'POST'])
def research_reference_work():
    from agent_research import reference_work as owner
    from lumenis.shared.reporting.source_brief_job import _scope_material, _media_scope
    try:
        _, _, scope, actor = _source_brief_context('read' if request.method == 'GET' else 'write', include_actor=True)
        scope = scope if scope.get('scope_kind') else _media_scope(_scope_material(**scope))
        if request.method == 'GET':
            result = owner.list_reference_work(actor=actor, scope=scope, query=request.args.get('query', ''),
                limit=int(request.args.get('limit', 30)), cursor=request.args.get('cursor'))
        else:
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or not {'asset_id','request_id'} <= set(body) or set(body)-{'asset_id','request_id','edits'}:
                raise ValueError('REFERENCE_INPUT_INVALID')
            result = owner.adopt_reference_asset(actor=actor, scope=scope, **body)
        return jsonify({'ok': True, 'result': result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.route('/api/experience/reports/source-brief/reference-work/<artifact_id>', methods=['GET', 'POST'])
def research_reference_version(artifact_id):
    from agent_research import reference_work as owner
    from lumenis.shared.reporting.source_brief_job import _scope_material, _media_scope
    try:
        _, _, scope, actor = _source_brief_context('read' if request.method == 'GET' else 'write', include_actor=True)
        scope = scope if scope.get('scope_kind') else _media_scope(_scope_material(**scope))
        if request.method == 'GET':
            result = owner.read_reference_work(artifact_id, actor=actor, scope=scope,
                expected_sha256=request.args.get('sha256'))
        else:
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or not {'request_id','expected_sha256','operation'} <= set(body) or set(body)-{'request_id','expected_sha256','operation','edits'}:
                raise ValueError('REFERENCE_INPUT_INVALID')
            result = owner.revise_reference_work(artifact_id, actor=actor, scope=scope, **body)
        return jsonify({'ok': True, 'result': result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.post('/api/experience/reports/source-brief/references/match-rules')
def research_match_rules():
    from agent_research.reference_assets import match_rule_references
    try:
        _source_brief_context('read')
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or 'content' not in body or set(body)-{'content','regions','industry','business','platform','as_of'}:
            raise ValueError('REFERENCE_INPUT_INVALID')
        return jsonify({'ok': True, 'result': match_rule_references(**body)})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.route('/api/experience/reports/source-brief/learning/<kind>', methods=['GET','POST'])
@experience_bp.get('/api/experience/reports/source-brief/learning/<kind>/<object_id>')
@experience_bp.post('/api/experience/reports/source-brief/learning/<kind>/<object_id>/<operation>')
def research_learning(kind, object_id=None, operation=None):
    from lumenis.shared.learning import contribution as owner
    from lumenis.shared.reporting.source_brief_job import _scope_material
    try:
        if kind not in {'candidates','outbox'}:
            raise LookupError('LEARNING_ROUTE_NOT_FOUND')
        actor_ref, _, scope, actor = _source_brief_context('read' if request.method == 'GET' else 'write', include_actor=True)
        scope = _scope_material(**scope)
        args = dict(actor=actor, actor_id=actor_ref, expected_scope=scope)
        def authorize():
            fresh_ref, audit, fresh_scope = _source_brief_context('write')
            if fresh_ref != actor_ref or _scope_material(**fresh_scope) != scope:
                raise PermissionError('LEARNING_AUTHORIZATION_CHANGED')
            return {'actor_id': actor_ref, 'scope': scope, 'permission_audit_ref': str(audit),
                    'operation_audit_ref': str(audit)}
        if request.method == 'GET':
            if object_id:
                result = (owner.get_candidate if kind == 'candidates' else owner.get_outbox)(object_id, **args)
            else:
                result = (owner.list_candidates if kind == 'candidates' else owner.list_outbox)(**args,
                    limit=int(request.args.get('limit',30)), offset=int(request.args.get('offset',0)))
        else:
            body = request.get_json(silent=True)
            if not isinstance(body, dict):
                raise ValueError('LEARNING_INPUT_INVALID')
            args['authorize'] = authorize
            if not object_id and kind == 'candidates':
                allowed = {'job_id','review_id','submission_id'}
                business = {'work_id','expected_business_revision','job_id','submission_id'}
                if set(body) not in (allowed, business):
                    raise ValueError('LEARNING_INPUT_INVALID')
                result = (owner.create_candidate if set(body)==allowed else owner.create_business_candidate)(**args, **body)
            elif object_id and operation == 'enqueue' and kind == 'candidates':
                if set(body) != {'expected_revision','submission_id','receiver'}:
                    raise ValueError('LEARNING_INPUT_INVALID')
                result = owner.enqueue_candidate(object_id, **args, **body)
            elif object_id and kind == 'candidates' and operation in {'review','validate','adopt','withdraw','restore','reject'}:
                if set(body) != {'expected_revision','submission_id','notes'}:
                    raise ValueError('LEARNING_INPUT_INVALID')
                result = owner.transition_candidate(object_id, action=operation, **args, **body)
            elif object_id and kind == 'outbox' and operation in {'stage','fail','requeue','receive_local'}:
                if set(body) != {'expected_revision','submission_id'}:
                    raise ValueError('LEARNING_INPUT_INVALID')
                result = (owner.receive_local_contribution(object_id, **args, **body) if operation == 'receive_local'
                          else owner.transition_outbox(object_id, action=operation, **args, **body))
            else:
                raise LookupError('LEARNING_ROUTE_NOT_FOUND')
        return jsonify({'ok': True, 'result': result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.post('/api/experience/reports/source-brief/adopt-source')
def adopt_research_source():
    from lumenis.importer.documents import adopt_shared_research_source
    from lumenis.shared.reporting.source_brief_job import _scope_material, _media_scope
    try:
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {'job_id','source_id','provenance','mode'}:
            raise ValueError('RESEARCH_ADOPTION_INPUT_INVALID')
        _, _, scope, actor = _source_brief_context('write', include_actor=True)
        if scope.get('scope_kind'):
            raise ValueError('RESEARCH_ADOPTION_TARGET_DOMAIN_REQUIRED')
        result = adopt_shared_research_source(actor=actor, target_scope=_media_scope(_scope_material(**scope)), **body)
        return jsonify({'ok': True, 'result': result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.route('/api/experience/reports/source-brief/reference-library', methods=['GET','POST'])
@experience_bp.get('/api/experience/reports/source-brief/reference-library/<int:evidence_id>')
def research_reference_library(evidence_id=None):
    import intelligence_library_api as owner
    from lumenis.shared.reporting.source_brief_job import _scope_material, _media_scope
    try:
        _, _, scope, actor = _source_brief_context('read' if request.method == 'GET' else 'write', include_actor=True)
        scope = scope if scope.get('scope_kind') else _media_scope(_scope_material(**scope))
        if evidence_id is not None:
            result = owner.read_reference_library_source(evidence_id, actor=actor, scope=scope)
        elif request.method == 'GET':
            result = owner.discover_reference_library_sources(actor=actor, scope=scope, query=request.args.get('query',''),
                limit=int(request.args.get('limit',30)), cursor=request.args.get('cursor'))
        else:
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or not {'asset_id','request_id'} <= set(body) or set(body)-{'asset_id','request_id','edits'}:
                raise ValueError('REFERENCE_INPUT_INVALID')
            result = owner.adopt_reference_library_asset(actor=actor, scope=scope, **body)
        return jsonify({'ok': True, 'result': result})
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.get('/api/experience/reports/source-brief/jobs/<job_id>/hypotheses')
@experience_bp.post('/api/experience/reports/source-brief/jobs/<job_id>/hypotheses/review')
def research_hypothesis_review(job_id):
    from lumenis.shared.reporting.source_brief_job import get_hypothesis_review, write_hypothesis_review, _scope_material
    try:
        actor_id, _, scope, actor = _source_brief_context('read' if request.method == 'GET' else 'write', include_actor=True)
        scope = _scope_material(**scope)
        args = {'actor':actor,'actor_id':actor_id,'expected_scope':scope}
        if request.method == 'GET':
            result = get_hypothesis_review(job_id, **args)
        else:
            body = request.get_json(silent=True)
            if not isinstance(body,dict) or set(body) != {'hypothesis_id','disposition','rationale','evidence_refs','request_id','expected_revision'}:
                raise ValueError('HYPOTHESIS_REVIEW_INPUT_INVALID')
            result = write_hypothesis_review(job_id, **args, **body)
        return jsonify({'ok':True,'result':result})
    except (ValueError,LookupError,PermissionError,RuntimeError) as exc:
        return _source_brief_job_error(exc)


@experience_bp.route('/api/experience/propagation/classify', methods=['POST'])
def propagation_classify():
    from brand_propagation import classification_http
    return classification_http()
