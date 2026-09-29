"""序境 / LUMENIS — App-only Experience ViewModel/API runtime.

本模块是 Flutter App 使用的 JSON transport 与只读 ViewModel 聚合层。
它不托管 Jinja、static、浏览器原型或第二套网页 Experience；所有真实数据、
Evidence、Canonical Data、Permission、Evaluation 与 Learning 仍由既有 canonical
owners 提供。本模块只负责把这些事实以受约束的 API contract 暴露给 App。
"""
from __future__ import annotations

import datetime as _dt
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
_CONTENT_SOURCE_IMPORT_MAX_BYTES = 128 * 1024 * 1024

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


def days_labels_series(days: int = 14) -> Tuple[List[str], List[int], List[int]]:
    """真实近 N 日负面/高风险序列（database.get_stats_by_date_range，按天现算，不造趋势）。"""
    import database as db

    labels: List[str] = []
    neg: List[int] = []
    high: List[int] = []
    today = _dt.date.today()
    for back in range(days - 1, -1, -1):
        d = today - _dt.timedelta(days=back)
        ds = d.strftime("%Y-%m-%d")
        st = _safe(db.get_stats_by_date_range, ds, ds, default={})
        labels.append(d.strftime("%m-%d"))
        neg.append(int(st.get("negative", 0)) if isinstance(st, dict) and not _is_err(st) else 0)
        high.append(int(st.get("high_risk", 0)) if isinstance(st, dict) and not _is_err(st) else 0)
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

    # 当前主体 / 域（subject_context 真实解析）
    try:
        import subject_context as sc

        scope = sc.current_scope()
        identity["subject"] = {
            "subject_id": scope.get("subject", {}).get("subject_id"),
            "brand_key": scope.get("subject", {}).get("brand_key"),
            "product": scope.get("product", {}).get("product_id"),
        }
        dom = request.cookies.get("zbc_domain") or request.headers.get("X-Domain-Id") \
            or request.args.get("domain") or "cth"
        identity["domain"] = dom if dom in ("cth", "zbmp", "system") else "cth"
    except Exception as exc:  # noqa: BLE001
        identity["subject"] = {"error": str(exc)}
        identity["domain"] = "cth"

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
        import subject_context as sc
        from subject_registry import list_subjects

        scope = sc.current_scope()
        return jsonify({
            "ok": True,
            "current": scope.get("subject"),
            "product": scope.get("product"),
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
def _build_cth01() -> Dict[str, Any]:
    import database as db
    from lumenis.shared.reporting import daily as daily_reporting

    blocked: List[Dict[str, str]] = []
    truth: Dict[str, Any] = {}
    # 前端风险枚举：后端 medium -> 前端 med
    _LV = {"high": "high", "medium": "med", "low": "low", "critical": "critical"}

    stats = _safe(db.get_stats, default={})
    stats_err = _is_err(stats)
    canonical = _safe(daily_reporting.generate_today_summary, today_str(), default={})
    canon_err = _is_err(canonical)
    risk_notes = _safe(db.get_high_risk_notes, 6, default=[])
    events = _safe(db.get_events, 6, default=[])
    evid = _safe(_evidence_recent, 2, default=[])

    # ---- KPI：真实可绑 vs 外部缺失（绝不填 0） ----
    neg = stats.get("negative") if isinstance(stats, dict) else None
    open_events = len(events) if isinstance(events, list) and not _is_err(events) else None
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
               icon="risk", source="database.get_stats().negative（主体口径）",
               evidence_id="FUNC-SENTIMENT", fresh="live"),
        metric("cth.open_events", "在办事件",
               value=open_events,
               state=STATE_READY if open_events is not None else STATE_OFFLINE,
               icon="event", source="database.get_events()（主体口径，active 优先）",
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
    labels, neg_series, high_series = days_labels_series(14)
    trend = section("chart", STATE_READY, kind="line", title="近 14 日负面声量 / 高风险",
                    sub="database.get_stats_by_date_range 按天现算",
                    series=[
                        {"name": "负面", "data": neg_series, "color": "var(--lum-c-danger,#c0563f)"},
                        {"name": "高风险", "data": high_series, "color": "var(--lum-c-info,#4FC4E8)"},
                    ], labels=labels,
                    legend=[{"label": "负面", "color": "var(--lum-c-danger,#c0563f)"},
                            {"label": "高风险", "color": "var(--lum-c-info,#4FC4E8)"}])

    # ---- 事件：真实高风险/事件 ----
    ev_items = []
    if isinstance(events, list):
        for e in events[:3]:
            ev_items.append({
                "time": (e.get("event_date") or e.get("last_seen") or "")[5:16] or "—",
                "date": (e.get("first_seen") or "")[:10],
                "title": e.get("title", "未命名事件"),
                "desc": (e.get("summary") or "")[:120],
                "level": _LV.get((e.get("risk_level") or "low"), "low"),
                "tags": [f"提及 {e.get('mention_count', 0)}", f"来源 {e.get('source_count', 1)}"],
                "evidence": f"EV:{e.get('event_id') or e.get('id') or 'UNKNOWN'}",
            })
    events_sec = section("events", STATE_READY if ev_items else STATE_EMPTY,
                         title="重点事件", more=True, items=ev_items)

    # ---- 证据链：Shared Evidence 的真实存储 ----
    ev_rail = []
    for r in (evid if isinstance(evid, list) else [])[:2]:
        ev_rail.append({
            "kind": r.get("level") or "evidence",
            "id": f"EV:{r.get('id', 'UNKNOWN')}",
            "chain": ["Source", "Canonical", "Metric", "View"],
            "quote": str(r.get("actual") or r.get("feature_id") or "生产证据记录")[:140],
            "time": str(r.get("created_at") or "")[:16],
            "source": r.get("source") or "app_evidence_records",
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
        {"name": "舆情数据库", "state": "ok" if not stats_err else "offline",
         "detail": f"共 {stats.get('total') if isinstance(stats, dict) else 'NA'} 条"},
        {"name": "Canonical 指标", "state": "ok" if not canon_err else "offline",
         "detail": ("采集健康：" + _health_text(canonical.get("collection_health"))) if not canon_err else "unavailable"},
        {"name": "证据存储", "state": "ok" if isinstance(evid, list) else "offline",
         "detail": f"近 {len(evid) if isinstance(evid, list) else 'NA'} 条样本"},
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
        metric("ai.provider_health", "Provider 健康", value=healthy if prov_kpi_state == STATE_READY else None,
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
    runtime_sec = section("runtime", title="Provider 状态", items=provider_states)
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
    """真实 Provider 状态；configured 不等于 reachable/model-ready。"""
    items: List[Dict[str, Any]] = []
    try:
        import intelligence
        ai_state = intelligence.ai_status() or {}
    except Exception:
        ai_state = {}
    active_provider = str(ai_state.get("provider") or "")
    zhipu_configured = isinstance(gov, dict) and not gov_err and bool(gov.get("providers") or gov.get("zhipu") or gov.get("enabled"))
    zhipu_ok = bool(ai_state.get("enabled")) and active_provider == "zhipu"
    items.append({"kind": "provider", "name": "智谱 · 可选", "state": "ok" if zhipu_ok else ("idle" if zhipu_configured else "offline"),
                  "detail": "active · verified by gateway" if zhipu_ok else ("configured · not active" if zhipu_configured else "not verified")})
    ollama_ok = bool(ai_state.get("enabled")) and active_provider == "ollama"
    ollama_detail = "active · local model" if ollama_ok else "daemon/model not ready"
    items.append({"kind": "provider", "name": "本地 Ollama", "state": "ok" if ollama_ok else "idle", "detail": ollama_detail})
    return items


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
        if screen_id == "CTH-03":
            binding, error = _cth03_read_scope()
            if error is not None:
                return error
            return jsonify(builder(binding=binding))
        return jsonify(builder())
    except Exception as exc:  # noqa: BLE001
        if screen_id == "CTH-03":
            from flask import current_app
            current_app.logger.warning("CTH03 scoped read unavailable: %s", type(exc).__name__)
            return jsonify({"ok": False, "screen": screen_id, "bound": False,
                            "code": "SCOPED_DATA_UNAVAILABLE",
                            "error": "监测记录暂不可用，请重试"}), 503
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
    body = request.get_json(silent=True) or {}
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
    max_results = body.get("max_results", 20)
    try:
        from lumenis.system.collector.adapters.secondary_collection import collect_search
        result = collect_search(platform, keyword, max_results=max_results, operator=operator)
        http_status = 409 if result.get("status") in {"BUSY", "RATE_LIMITED"} else 200
        return jsonify(result), http_status
    except PermissionError as exc:
        return jsonify({"ok": False, "status": "denied", "code": "HUMAN_OPERATOR_REQUIRED",
                        "reason": str(exc), "read_only": True, "external_write": False}), 403
    except ValueError as exc:
        return jsonify({"ok": False, "status": "invalid_request", "error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"ok": False, "status": "blocked", "error_type": type(exc).__name__}), 503
    except Exception as exc:  # noqa: BLE001 - no adapter details at HTTP boundary
        return jsonify({"ok": False, "status": "error", "error_type": type(exc).__name__}), 503


def _content_project_scope(action: str):
    """Resolve selectors through the canonical registry, then ask Permission."""
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import (
        check_actor_scope_permission, check_local_workspace_scope_permission,
        resolve_local_workspace_principal,
    )
    from subject_registry import get_subject_by_id, normalize_domain
    from shared_artifacts import LocalArtifactError

    try:
        local_principal = resolve_local_workspace_principal(module="content", action=action)
        actor = local_principal if local_principal is not None else get_current_user()
    except Exception as exc:
        raise LocalArtifactError("AUTH_UNAVAILABLE") from exc
    if local_principal is None and (
        not isinstance(actor, dict) or type(actor.get("id")) is not int or actor["id"] <= 0
    ):
        raise LocalArtifactError("AUTH_REQUIRED")
    try:
        selected_domain = normalize_domain(request.headers.get("X-Domain-Id", ""))
    except ValueError as exc:
        raise LocalArtifactError("DOMAIN_REQUIRED") from exc
    if selected_domain not in {"CTH", "BMP"}:
        raise LocalArtifactError("DOMAIN_REQUIRED")
    domain = "cth" if selected_domain == "CTH" else "zbmp"
    product = request.headers.get("X-Product-Id", selected_domain)
    if product not in ({"CTH"} if domain == "cth" else {"BMP", "ZBMP"}):
        raise LocalArtifactError("CONTEXT_SCOPE_MISMATCH")
    mode = request.headers.get("X-Lumenis-Context-Mode", "GLOBAL_ALL")
    selected_subject = request.headers.get("X-Subject-ID", "") or None
    selected_brand = request.headers.get("X-Brand-Focus-ID", "") or None
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
    decision = checker(actor, action=action, module="content", **scope)
    if decision.verification_state != "verified":
        raise LocalArtifactError("CONTENT_SCOPE_UNAVAILABLE")
    if decision.allowed is not True:
        raise LocalArtifactError("CONTENT_SCOPE_DENIED")
    return actor, scope


def _content_project_error_code(exc):
    code = str(exc)
    # Only known code-shaped errors are safe to serialize; never return filesystem paths.
    if not code or len(code) > 100 or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789" for character in code):
        code = "CONTENT_PROJECT_FAILED"
    return code


def _content_project_error(exc):
    code = _content_project_error_code(exc)
    status = 503 if code.endswith("_UNAVAILABLE") else 404 if code.endswith("_NOT_FOUND") else 401 if code == "AUTH_REQUIRED" else 403 if code in {
        "CONTENT_SCOPE_DENIED", "ACTOR_SCOPE_PERMISSION_DENIED", "DOMAIN_REQUIRED", "CONTEXT_SCOPE_MISMATCH",
        "CONTENT_PROJECT_CONTEXT_MISMATCH", "CONTENT_PROJECT_PARENT_SCOPE_MISMATCH",
        "CONTENT_SOURCE_CONTEXT_MISMATCH", "CONTENT_SOURCE_SCOPE_DENIED",
        "CONTENT_SOURCE_ORIGIN_DENIED",
        "CONTENT_SOURCE_APPROVAL_REQUIRED", "CONTENT_EXPORT_PERMISSION_DENIED",
    } else 400
    return jsonify({"ok": False, "code": code, "publish_status": "not_performed"}), status


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
        normalized_paths = [validate_local_asset(value) for value in paths]
        if sum(path.stat().st_size for path in normalized_paths) > 500 * 1024 * 1024:
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
        if not isinstance(payload, dict) or set(payload) not in ({"asset_paths"}, {"asset_refs"}):
            raise LocalArtifactError("INVALID_CONTENT_INPUT")
        actor, scope = _content_project_scope("read")
        with _content_project_assets(payload, actor, scope) as (_, assets, source_refs):
            return jsonify({"ok": True, "assets": [asset.to_dict() for asset in assets],
                            "source_artifact_refs": source_refs, "rights_state": "unknown",
                            "external_fetch": False})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_INSPECTION_UNAVAILABLE"}), 503


def _content_project_execution_context(scope):
    """Adapt the server-authorized content scope to the existing Skill context contract."""
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


@experience_bp.route("/api/experience/content-sources", methods=["POST"])
def import_content_source():
    """Import one bounded local media body into the scoped Artifact owner."""
    from werkzeug.exceptions import RequestEntityTooLarge
    from shared_artifacts import LocalArtifactError, artifact_root, stage_content_source_artifact
    from shared_artifacts import _safe_content_source_filename
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
        declared_length = request.content_length
        if declared_length is not None and declared_length > _CONTENT_SOURCE_IMPORT_MAX_BYTES:
            raise RequestEntityTooLarge()
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
                    chunk = request.stream.read(min(1024 * 1024, _CONTENT_SOURCE_IMPORT_MAX_BYTES - observed + 1))
                    if not chunk:
                        break
                    observed += len(chunk)
                    if observed > _CONTENT_SOURCE_IMPORT_MAX_BYTES:
                        raise RequestEntityTooLarge()
                    body_digest.update(chunk)
                    output.write(chunk)
            if observed <= 0:
                raise LocalArtifactError("CONTENT_SOURCE_EMPTY")
            if declared_length is not None and observed != declared_length:
                raise LocalArtifactError("CONTENT_SOURCE_BODY_LENGTH_MISMATCH")

            body_sha256 = body_digest.hexdigest()
            resource_binding = {"actor_id": actor_id, "scope": scope,
                                "filename": filename, "size_bytes": observed,
                                "body_sha256": body_sha256}
            upload = ContentSourceImport(
                actor_id=actor_id, domain_id="bmp" if scope["domain_id"] == "zbmp" else "cth",
                subject_id=scope["subject_id"], brand_focus_id=scope["brand_focus_id"],
                global_scope=scope["global_scope"], filename=filename,
                size_bytes=observed, body_sha256=body_sha256,
                principal_kind=local_principal.principal_kind if local_principal else None,
                principal_ref=local_principal.principal_ref if local_principal else None,
            )

            def import_asset(ctx):
                return stage_content_source_artifact(
                    upload_path,
                    filename=filename,
                    actor=actor,
                    source_execution_id=ctx.execution_id,
                    expected_sha256=body_sha256,
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
                permission_role="cth_operator" if scope["domain_id"] == "cth" else "zbmp_operator",
                product="CTH" if scope["domain_id"] == "cth" else "ZBMP",
                domain=scope["domain_id"],
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
                            "publish_status": "not_performed"}), 403
        if context.status.value != "completed" or not isinstance(result, dict) or not result.get("artifact"):
            code = _content_project_error_code(context.error or "CONTENT_SOURCE_IMPORT_FAILED")
            return jsonify({"ok": False, "code": code, "execution_id": context.execution_id,
                            "status": context.status.value, "publish_status": "not_performed"}), 503
        return jsonify({
            "ok": True,
            "result": {"artifact": result["artifact"], "asset": result["asset"]},
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
        normalized_scope = {**scope, "domain_id": "bmp" if scope["domain_id"] == "zbmp" else "cth"}
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
    from shared_artifacts import read_content_source_artifact

    try:
        actor, scope = _content_project_scope("read")
        source = read_content_source_artifact(artifact_id, actor=actor, **scope)
        return jsonify({"ok": True, "result": source, "publish_status": "not_performed"})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_SOURCE_UNAVAILABLE",
                        "publish_status": "not_performed"}), 503


@experience_bp.route("/api/experience/content-projects/export", methods=["POST"])
def export_content_project():
    from lumenis.shared.content_creation.video_editing import Timeline
    from shared_artifacts import LocalArtifactError, stage_timeline_artifact
    from lumenis.shared.agents.skills.execution import ActionType, SkillRuntimeInfo, run_execution_chain

    try:
        actor, scope = _content_project_scope("write")
        account_actor = actor if isinstance(actor, dict) else None
        if not _content_source_same_origin():
            raise LocalArtifactError("CONTENT_SOURCE_ORIGIN_DENIED")
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("action_type") != "EXPORT":
            raise LocalArtifactError("CONTENT_EXPORT_REQUIRES_EXPORT")
        payload = body.get("input")
        allowed = {"asset_paths", "asset_refs", "timeline", "output_kind", "demo_acknowledged", "previous_artifact_id"}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise LocalArtifactError("INVALID_CONTENT_INPUT")
        task = str(body.get("task") or "导出可继续编辑的内容工程")[:2000]
        info = SkillRuntimeInfo(skill_id="shared.content_project", name="内容工程导出",
                               description="真实媒体与可回开的编辑版本", product="SHARED", domain="content",
                               version="1.0.0", enabled=True, source="shared_artifacts",
                               cross_domain_allowed=["CTH", "BMP"])
        with _content_project_assets(payload, actor, scope) as (_, assets, source_refs):
            timeline = Timeline.from_dict(payload.get("timeline"), assets=assets)
            normalized = {"timeline": timeline.to_dict(), "scope": scope,
                          "source_artifact_refs": source_refs,
                          "output_kind": payload.get("output_kind", "video"),
                          "demo_acknowledged": payload.get("demo_acknowledged") is True,
                          "previous_artifact_id": payload.get("previous_artifact_id")}

            def render(ctx):
                return stage_timeline_artifact(
                    timeline, actor=actor, **scope, source_execution_id=ctx.execution_id,
                    output_kind=normalized["output_kind"], demo_acknowledged=normalized["demo_acknowledged"],
                    previous_artifact_id=normalized["previous_artifact_id"],
                    source_artifact_refs=source_refs,
                )

            ctx = run_execution_chain(
                skill_id="shared.content_project", task=task, input_payload=normalized,
                action_type=ActionType.EXPORT,
                user_id=account_actor["id"] if account_actor else None,
                user_role=account_actor.get("role", "user") if account_actor else "user",
                product="CTH" if scope["domain_id"] == "cth" else "ZBMP", domain=scope["domain_id"],
                skill_info=info, handler=render, request_context=_content_project_execution_context(scope),
            )
            execution = ctx.execute_result or {}
            result = execution.get("result") if isinstance(execution, dict) else None
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
                        "preview_url": f"/api/experience/content-projects/{artifact_id}/media",
                        "publish_status": "not_performed"})
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_PROJECT_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/content-projects/<artifact_id>/package")
def content_project_package(artifact_id: str):
    from shared_artifacts import _verified_content_project

    try:
        actor, scope = _content_project_scope("read")
        _, _, _, path = _verified_content_project(artifact_id, actor=actor, **scope)
        return send_file(path, mimetype="application/zip", as_attachment=True, download_name=f"{artifact_id}.zip")
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_PROJECT_UNAVAILABLE"}), 503


@experience_bp.route("/api/experience/content-projects/<artifact_id>/media")
def content_project_media(artifact_id: str):
    from io import BytesIO
    from shared_artifacts import authorized_project_media

    try:
        actor, scope = _content_project_scope("read")
        media = authorized_project_media(artifact_id, actor=actor, **scope)
        return send_file(BytesIO(media["data"]), mimetype=media["media_type"],
                         download_name=media["filename"], conditional=True)
    except ValueError as exc:
        return _content_project_error(exc)
    except Exception:
        return jsonify({"ok": False, "code": "CONTENT_PROJECT_UNAVAILABLE"}), 503


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
    normalized_payload["product"] = "LUMENIS"

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
            product_id="LUMENIS",
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
            product="LUMENIS",
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
    raw_domain = str(body.get("domain") or payload.get("domain") or "CTH").strip().upper()
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
            product="LUMENIS",
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


@experience_bp.route("/api/experience/ai/intent", methods=["POST"])
def ai_intent():
    """AI-01 composer 提交：先过标准权限门（P0-WRITEPERM-02），通过后复用既有
    Agent Groups Skill Execution（不重复实现 AI），走 Contract/Artifact 边界。

    四态：granted / pending_approval / denied / permanent_deny。未通过权限门时在进入
    执行链之前返回，保证不写任何证据、不触碰生产写侧，也不回显任何安全内部。
    """
    body = request.get_json(silent=True) or {}
    task = (body.get("task") or body.get("intent") or "").strip()
    if not task:
        return jsonify({"ok": False, "error": "task required"}), 400
    if len(task) > 4000:
        return jsonify({"ok": False, "error": "task too long (max 4000)"}), 400

    # ── 第 1 步：解析动作类型（非法值 fail-closed） ──
    from lumenis.shared.agents.skills.execution import ActionType, run_execution_chain
    raw_action = str(body.get("action_type", "ANALYZE")).upper()
    try:
        action_type = ActionType(raw_action)
    except ValueError:
        return jsonify({"ok": False, "status": "denied",
                        "reason": f"unknown action_type: {raw_action}"}), 400

    # ── 第 2 步：永久拒绝类别（AI 派生层永不发布/推送/删除） ──
    if raw_action in PERMANENT_DENY_ACTIONS:
        return jsonify({
            "ok": False, "status": "permanent_deny",
            "reason": "AI composer 为派生增强层，不允许执行发布/上线/推送/删除类操作。",
        }), 403

    # ── 第 3 步：标准权限门检查 ──
    gate_spec = _action_gate_spec(raw_action)
    if gate_spec is None:
        return jsonify({"ok": False, "status": "denied",
                        "reason": f"action_type {raw_action} 未注册权限映射（fail-closed）"}), 403
    operation_type, risk_level = gate_spec
    decision = get_permission_gate().check(
        operation_type,
        resource=body.get("skill_id") or "zbc.generic_analysis",
        risk_level=risk_level,
        caller=body.get("user_id") or "experience_user",
        domain_id=body.get("domain", "CTH"),
    )
    if not decision.allowed:
        # pending_approval 用 200（流程未失败，等待人工）；denied 用 403。两者都不执行。
        status = "pending_approval" if decision.requires_approval else "denied"
        http_code = 200 if status == "pending_approval" else 403
        return jsonify({
            "ok": False,
            "status": status,
            "reason": decision.reason,
            "permission_required": getattr(decision.permission_required, "value", decision.permission_required),
            "risk_level": risk_level.value,
            "requires_approval": bool(decision.requires_approval),
            "audit_id": decision.audit_id,
        }), http_code

    # ── 第 4 步：仅在 granted 后进入执行链（此前任何分支都不会写证据） ──
    try:
        ctx = run_execution_chain(
            skill_id=body.get("skill_id") or "zbc.generic_analysis",
            task=task,
            input_payload=body.get("input", {}),
            action_type=action_type,
            user_id=body.get("user_id"),
            product=body.get("product", "LUMENIS"),
            domain=body.get("domain", "CTH"),
        )
        return jsonify({
            "ok": True,
            "permission_status": "granted",
            "audit_id": decision.audit_id,
            "execution_id": ctx.execution_id,
            "status": ctx.status.value,
            "evidence_recorded": bool(getattr(ctx, "evidence_record", {}).get("ok", False)),
            "ai_is_derivative": True,
            "note": "AI 输出为派生结果，不覆盖 Evidence/Canonical；前端须展示引用与可追溯状态。",
        })
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


def register_experience_runtime(app):
    """在 app.py 中调用以注册本蓝图（与其他蓝图一致的加法式挂载）。"""
    app.register_blueprint(experience_bp)
    return app
