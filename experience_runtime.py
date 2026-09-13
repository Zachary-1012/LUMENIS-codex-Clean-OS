"""序境 / LUMENIS — Experience V2 生产运行时挂载层 (Experience Runtime Mount).

职责（严格最小、加法式）：
  1. 把零构建前端蓝图 ``experience_v2/10_prototype`` 通过现有 Flask 生产进程挂载到
     ``/experience/``（不新建 React/Vue，不重写旧 Jinja 前端，旧 ``/lumenis/*`` 保持原样）。
  2. 提供与原型 section 描述符**同构**的真实 ViewModel JSON：
       GET  /api/experience/screen/<screen_id>
       GET  /api/experience/runtime/identity
       GET  /api/experience/subjects
       POST /api/experience/ai/intent
     前端 assets/runtime.js 拿到同构 sections 后就地水合（hydrate），并把 data-source 切到 runtime。

生产事实红线（ONE-SHOT §7）：
  * 只复用既有后端能力（database / daily_report / evidence_store / skill_execution_chain /
    ai_governance / runtime_guardian / subject_context），不并行实现第二套真值。
  * 后端不存在数据源的指标（如到店客流 / 会员销售，需 POS 外部源）一律 state='notcollected'、
    value=None，并在 binding.blocked 里标 BLOCKED_BY_EXTERNAL_DEPENDENCY —— 绝不填 0、不造假。
  * 任何读取异常都降级为对应 section 的 error/offline 状态，不伪造 200 成功数据。
  * identity 不返回绝对路径、密钥、cookie、token、浏览器会话等安全内部。

本模块是只读聚合层 + 静态托管层：不写业务库、不迁移、不改权限语义。
"""

from __future__ import annotations

import datetime as _dt
import io as _io
import os
import threading
import traceback as _tb
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request, send_from_directory

# ---------------------------------------------------------------------------
# 路径与蓝图
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROTO_DIR = os.path.join(_BASE_DIR, "experience_v2", "10_prototype")

experience_bp = Blueprint("experience_runtime", __name__, static_folder=None)

# 已完成真实后端绑定的屏幕（其余屏幕由前端保持原型，服务端明确返回 bound=False）
BOUND_SCREENS = ("CTH-01", "AI-01")

# 13 态中，section 描述符使用的状态别名（与 assets/sections.js stateKind 对齐）
STATE_READY = "ready"
STATE_NOT_COLLECTED = "notcollected"   # 后端无该数据源（需外部依赖）
STATE_EMPTY = "empty"                  # 数据源存在但当前无记录
STATE_OFFLINE = "offline"              # 依赖运行时不可用
STATE_ERROR = "error"

# ---------------------------------------------------------------------------
# P0-WRITEPERM-02：AI composer 写权限边界（标准 permission_gate.PermissionGate）
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
    """skill ActionType -> (permission_gate.OperationType, RiskLevel)。

    未注册动作返回 None，由调用方 fail-closed 拒绝。只读/分析低风险自动放行；
    导出为中风险（VERIFY 权限）；写/提交为高风险，需要对应权限等级 + 人工审批。
    """
    from permission_gate import OperationType, RiskLevel
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
        from permission_gate import PermissionGate
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


# ===========================================================================
# 静态托管：把零构建原型作为生产前端提供（注入运行时配置，不改动磁盘上的原型文件）
# ===========================================================================
_RUNTIME_BOOT = (
    '<script>window.LUM_RUNTIME_API="/api/experience";'
    'window.LUM_RUNTIME={served:true,mode:"production"};</script>'
    '<script src="./assets/runtime.js" defer></script>'
)


@experience_bp.route("/experience/")
@experience_bp.route("/experience/index.html")
def experience_shell():
    """生产外壳：返回原型 index.html，并在 </body> 前注入运行时配置与 runtime.js。

    磁盘上的 index.html 保持离线原型不变；仅在响应文本里注入，离线直接打开仍是 prototype。
    """
    index_path = os.path.join(PROTO_DIR, "index.html")
    try:
        with _io.open(index_path, "r", encoding="utf-8") as fh:
            html = fh.read()
    except OSError as exc:
        return f"experience prototype missing: {exc}", 500
    if "assets/runtime.js" not in html:
        html = html.replace("</body>", f"{_RUNTIME_BOOT}\n</body>")
    # 生产外壳下隐藏原型 QA 工具条与 prototype 标记（由 runtime.js 统一改为 runtime 来源）
    return html


@experience_bp.route("/experience/<path:filename>")
def experience_asset(filename: str):
    """托管原型 assets/data（send_from_directory 自带路径穿越保护）。"""
    return send_from_directory(PROTO_DIR, filename)


# ===========================================================================
# 运行时身份 / 主体（只读，不泄露安全内部）
# ===========================================================================
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
    """当前主体与可用域。主体列表的呈现层仍由前端 fixtures 提供，这里给真实当前主体。"""
    try:
        import subject_context as sc

        scope = sc.current_scope()
        return jsonify({
            "ok": True,
            "current": scope.get("subject"),
            "product": scope.get("product"),
            "domains": [
                {"id": "CTH", "name": "商业运营"},
                {"id": "BMP", "name": "品牌市场"},
            ],
        })
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


# ===========================================================================
# CTH-01 商业运营总览 —— 真实绑定
# ===========================================================================
def _build_cth01() -> Dict[str, Any]:
    import database as db
    import daily_report

    blocked: List[Dict[str, str]] = []
    truth: Dict[str, Any] = {}
    # 前端风险枚举：后端 medium -> 前端 med
    _LV = {"high": "high", "medium": "med", "low": "low", "critical": "critical"}

    stats = _safe(db.get_stats, default={})
    stats_err = _is_err(stats)
    canonical = _safe(daily_report.generate_today_summary, today_str(), default={})
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
        "lineage": "daily_report.generate_today_summary / FUNC-RISK-01/02",
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

    # ---- 证据链：真实 evidence_store ----
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
    import evidence_store as es

    return es.query_evidence(limit=limit)


def _build_ai01() -> Dict[str, Any]:
    import evidence_store as es

    blocked: List[Dict[str, str]] = []
    truth: Dict[str, Any] = {}

    ev_stats = _safe(es.get_stats, default={})
    ev_err = _is_err(ev_stats)
    tasks = _safe(_ai_recent_tasks, 4, default=[])
    gov = _safe(_ai_governance, default={})
    gov_err = _is_err(gov)

    anchored = ev_stats.get("total") if isinstance(ev_stats, dict) else None
    # AI 结论可追溯率：需要执行链里“已完成且带证据”的真实样本才能计算；样本缺失时诚实 notcollected。
    raw_tasks = tasks if isinstance(tasks, list) else []
    done = [t for t in raw_tasks if t.get("status") in ("completed", "success", "done")]
    if raw_tasks and done:
        trace_val = round(100.0 * len(done) / len(raw_tasks), 1)
        trace_state, trace_note = STATE_READY, ""
    else:
        trace_val, trace_state, trace_note = None, STATE_NOT_COLLECTED, "需 AI 执行链累计已完成样本后计算，当前不臆造比率"
    if trace_state != STATE_READY:
        blocked.append({"field": "ai.traceability", "reason": "INSUFFICIENT_RUNTIME_SAMPLE",
                        "required": trace_note})

    # Provider 健康：治理状态可用则给真实数量，否则 offline（不编 4/4）
    provider_states = _provider_runtime(gov, gov_err)
    healthy = sum(1 for p in provider_states if p["state"] == "ok")
    prov_kpi_state = STATE_READY if not gov_err else STATE_OFFLINE

    # 待人工复核：证据 by_result 中 pending/review 计数（真实键存在才给值）
    by_result = ev_stats.get("by_result", {}) if isinstance(ev_stats, dict) else {}
    review = None
    for k in ("pending", "review", "needs_review", "shadow"):
        if k in by_result:
            review = (review or 0) + int(by_result[k] or 0)
    review_state = STATE_READY if review is not None else STATE_NOT_COLLECTED
    if review_state != STATE_READY:
        blocked.append({"field": "ai.review_queue", "reason": "NO_REVIEW_QUEUE_TABLE",
                        "required": "需要人工复核队列表/结果枚举"})

    kpis = [
        metric("ai.anchored_evidence", "今日已锚定证据",
               value=None if ev_err or anchored is None else anchored,
               state=STATE_READY if not ev_err and anchored is not None else STATE_OFFLINE,
               icon="link", source="evidence_store.get_stats().total", fresh="live"),
        metric("ai.traceability", "AI 结论可追溯率", value=trace_val, unit="%",
               decimals=1, state=trace_state, icon="evaluation", note=trace_note,
               source="skill_execution_chain（样本不足）"),
        metric("ai.provider_health", "Provider 健康", value=healthy if prov_kpi_state == STATE_READY else None,
               unit=f"/{len(provider_states)}", state=prov_kpi_state, icon="ops",
               source="ai_governance.get_governance_status", fresh="m5"),
        metric("ai.review_queue", "待人工复核", value=review, state=review_state,
               icon="risk", source="evidence_store.by_result(pending/review/shadow)"),
    ]
    truth["evidence_stats"] = None if ev_err else {
        "total": ev_stats.get("total"),
        "by_result": ev_stats.get("by_result"),
        "by_level": ev_stats.get("by_level"),
    }

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

    # 最近任务（真实执行链）
    tl_items = []
    for t in raw_tasks[:4]:
        tl_items.append({
            "time": str(t.get("created_at") or "")[5:16] or "—",
            "title": t.get("task") or t.get("skill_id") or "AI 任务",
            "desc": f"{t.get('status', 'unknown')} · {t.get('execution_id', '')[:10]}",
            "done": t.get("status") in ("completed", "success", "done"),
        })
    timeline_sec = section("timeline", STATE_READY if tl_items else STATE_EMPTY,
                           title="最近任务", label="History", items=tl_items)
    runtime_sec = section("runtime", title="Provider 状态", items=provider_states)
    rule_note = section("note", STATE_READY, kind="RULE", code="AI-NOT-TRUTH",
                        text="AI 输出为派生结果，携带 Provider/Model/Prompt/Confidence/Evidence 引用与人工修正状态，"
                             "不覆盖原始 Evidence 或 Canonical Data。")

    head = {
        "type": "head", "state": STATE_READY, "eyebrow": "AI Agent",
        "title": "AI 意图入口", "titleKey": "screen.AI-01",
        "desc": "从一句任务出发，识别意图、检索证据、生成可追溯结论；AI 是增强层，不拥有生产事实。",
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
            '<span class="lum-chip lum-press"><span data-i18n="ai.task_morph">能力任务</span></span></div>'
            '<textarea class="lum-textarea" data-ai-composer style="min-height:84px;background:transparent;'
            'border:0;font-size:16px;padding:0" data-i18n-ph="ai.composer_placeholder" '
            'data-i18n-aria="ai.composer_placeholder" placeholder="" aria-label="composer"></textarea>'
            '<div class="lum-row-between" style="margin-top:10px"><div class="lum-row" style="gap:8px">'
            '<button type="button" class="lum-chip lum-press" data-ai-ref>引用证据</button>'
            '<button type="button" class="lum-chip lum-press" data-ai-subject>指定主体</button>'
            '<button type="button" class="lum-chip lum-press" data-ai-window>时间范围</button></div>'
            '<button type="button" class="lum-btn lum-btn-primary" data-ai-send>'
            '<span data-i18n="ai.send">发送</span> →</button></div>'
            '<div data-ai-thread class="lum-stack-4" style="margin-top:14px"></div></div></div>'
        ),
    }

    sections = [
        head, composer,
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
    from skill_execution_chain import query_executions

    return query_executions(limit=limit)


def _ai_governance() -> Dict[str, Any]:
    import ai_governance

    return ai_governance.get_governance_status() or {}


def _provider_runtime(gov: Dict[str, Any], gov_err: bool) -> List[Dict[str, Any]]:
    """真实 Provider 状态：治理层可用则反映配置/可用性；本地确定性引擎恒为 ok；不伪造延迟。"""
    items: List[Dict[str, Any]] = []
    zhipu_ok = isinstance(gov, dict) and not gov_err
    items.append({"name": "智谱 glm-5.3", "state": "ok" if zhipu_ok else "offline",
                  "detail": "governance configured" if zhipu_ok else "governance unavailable"})
    items.append({"name": "本地 Ollama", "state": "idle", "detail": "local · 未在请求内探测"})
    items.append({"name": "规则引擎", "state": "ok", "detail": "deterministic"})
    items.append({"name": "备用通道", "state": "idle", "detail": "standby"})
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
        return jsonify({"ok": True, "screen": screen_id, "source": "prototype", "bound": False,
                        "sections": None,
                        "classification": "BLOCKED_BY_EXTERNAL_DEPENDENCY",
                        "note": _unbound_reason(screen_id)}), 200
    try:
        return jsonify(builder())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "screen": screen_id, "bound": True, "error": str(exc),
                        "trace": _tb.format_exc(limit=2)}), 500


@experience_bp.route("/api/experience/ai/intent", methods=["POST"])
def ai_intent():
    """AI-01 composer 提交：先过标准权限门（P0-WRITEPERM-02），通过后复用既有
    skill_execution_chain（不重复实现 AI），走 Contract/Artifact 边界。

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
    from skill_execution_chain import ActionType, run_execution_chain
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
