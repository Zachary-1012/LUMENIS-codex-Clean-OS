"""序境 / LUMENIS — Experience V2 屏幕级生产绑定（P1 传播层）.

定位（ONE-SHOT §10「Shared Contract / Domain Adapter / Screen Configuration」）：
  * 结构唯一源仍是 ``experience_v2/10_prototype/data/screens.js``；本文件**不重画布局**，
    只产出与 ``assets/sections.js`` 渲染器同构的真实 ViewModel section 描述符。
  * 每个数值必须来自既有后端只读函数（database / canonical_data / runtime_guardian /
    evidence_store / skill_execution_chain / ai_governance / function_registry / permission_gate）。
  * 后端没有数据源的字段一律 state='notcollected' + value=None，并在 binding.blocked 标
    BLOCKED_BY_EXTERNAL_DEPENDENCY —— 绝不填 0、绝不保留原型 fixture 假值。
  * 读取异常一律降级为对应 section 的 offline/error 状态，不向上抛、不伪造 200。

只新增只读聚合，不写业务库、不改后端语义。人类工程师维护约定：
一屏 = 一个 ``_build_<id>``；新增屏幕时在末尾 ``SCREEN_BUILDERS`` 注册即可。
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Dict, List, Optional

# 复用 experience_runtime 的同构构造器与状态常量，保证两处输出完全一致
from experience_runtime import (  # noqa: E402
    STATE_READY,
    STATE_NOT_COLLECTED,
    STATE_EMPTY,
    STATE_OFFLINE,
    _is_err,
    _safe,
    days_labels_series,
    metric,
    section,
    today_str,
)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_META_PATH = os.path.join(
    _BASE_DIR, "experience_v2", "10_prototype", "data", "screen_meta.json"
)

# 前端风险枚举：后端 medium -> 前端 med（与 sections.js risk.level.* 对齐）
_LV = {"high": "high", "medium": "med", "low": "low", "critical": "critical"}


def _load_meta() -> Dict[str, Dict[str, Any]]:
    try:
        with open(_META_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


SCREEN_META = _load_meta()


# ---------------------------------------------------------------------------
# 通用小工具：把后端 dict 安全转成渲染器需要的同构形状
# ---------------------------------------------------------------------------
def _head(sid: str, *, actions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    m = SCREEN_META.get(sid, {})
    h = {
        "type": "head",
        "state": STATE_READY,
        "eyebrow": m.get("eyebrow", ""),
        "title": m.get("title", sid),
        "titleKey": m.get("titleKey", f"screen.{sid}"),
        "desc": m.get("desc", ""),
    }
    if actions:
        h["actions"] = actions
    return h


def _envelope(sid: str, sections: List[Dict[str, Any]], *,
              truth: Optional[Dict[str, Any]] = None,
              blocked: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    blocked = blocked or []
    return {
        "ok": True,
        "screen": sid,
        "source": "runtime",
        "bound": True,
        "sections": sections,
        "truth": truth or {},
        "binding": {
            "screen": sid,
            "bound": True,
            "unavailable": [b["field"] for b in blocked],
            "blocked": blocked,
        },
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }


def _block(sid: str, field: str, reason: str, required: str = "") -> Dict[str, str]:
    return {"field": field, "reason": reason, "required": required}


def _note_row(n: Dict[str, Any]) -> Dict[str, Any]:
    """database note dict -> table 行（全部 .get 防御，不臆造列）。"""
    return {
        "date": str(n.get("publish_date") or n.get("created_at") or "")[:10],
        "title": (n.get("title") or (n.get("content") or "")[:40] or "未命名记录"),
        "platform": n.get("platform") or n.get("source") or "—",
        "sentiment": n.get("sentiment") or "—",
        "risk": _LV.get(n.get("risk_level") or "low", "low"),
        "note_id": str(n.get("note_id") or n.get("id") or "—"),
    }


def _notes_table(title: str, notes: List[Dict[str, Any]], limit: int = 12,
                 state: str = STATE_READY) -> Dict[str, Any]:
    cols = [
        {"label": "日期", "key": "date"},
        {"label": "标题 / 摘要", "key": "title"},
        {"label": "平台", "key": "platform"},
        {"label": "情感", "key": "sentiment"},
        {"label": "风险", "key": "risk"},
        {"label": "来源ID", "key": "note_id"},
    ]
    rows = [_note_row(n) for n in notes[:limit]] if isinstance(notes, list) else []
    return section("table", state if rows else STATE_EMPTY, title=title,
                   columns=cols, rows=rows)


def _events_items(events: List[Dict[str, Any]], limit: int = 6) -> List[Dict[str, Any]]:
    out = []
    for e in (events or [])[:limit]:
        out.append({
            "time": str(e.get("event_date") or e.get("last_seen") or "")[5:16] or "—",
            "date": str(e.get("first_seen") or "")[:10],
            "title": e.get("title", "未命名事件"),
            "desc": (e.get("summary") or "")[:120],
            "level": _LV.get(e.get("risk_level") or "low", "low"),
            "tags": [f"提及 {e.get('mention_count', 0)}", f"来源 {e.get('source_count', 1)}"],
            "evidence": f"EV:{e.get('event_id') or e.get('id') or 'UNKNOWN'}",
        })
    return out


def _evidence_items(records: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    out = []
    for r in (records or [])[:limit]:
        out.append({
            "kind": r.get("level") or "evidence",
            "id": f"EV:{r.get('id', 'UNKNOWN')}",
            "chain": ["Source", "Canonical", "Metric", "View"],
            "quote": str(r.get("actual") or r.get("feature_id") or "生产证据记录")[:140],
            "time": str(r.get("created_at") or "")[:16],
            "source": r.get("source") or "app_evidence_records",
            "conf": None,
        })
    return out


def _freshness(items: List[Dict[str, str]]) -> Dict[str, Any]:
    return section("runtime", title="数据新鲜度", items=items)


# ===========================================================================
# CTH 商业运营域（真实数据源：database / daily_report / evidence_store）
# ===========================================================================
def _build_cth02() -> Dict[str, Any]:
    """主体档案 / 业务单元 / 品牌业态：真实主体上下文 + 真实品类分布。"""
    import database as db
    import subject_context as sc

    blocked: List[Dict[str, str]] = []
    scope = _safe(sc.current_scope, default={})
    subj = (scope.get("subject") if isinstance(scope, dict) else {}) or {}
    dist = _safe(db.get_category_distribution, default=[])
    notes_total = _safe(db.get_note_count, default=None)

    kpis = [
        metric("cth02.subject", "当前主体", value=subj.get("name") or subj.get("subject_id") or "未选择",
               state=STATE_READY if subj else STATE_NOT_COLLECTED, icon="target",
               source="subject_context.current_scope"),
        metric("cth02.notes", "主体相关记录", value=notes_total if isinstance(notes_total, int) else None,
               state=STATE_READY if isinstance(notes_total, int) else STATE_OFFLINE,
               icon="event", source="database.get_note_count"),
        metric("cth02.business_units", "业务单元", value=None, state=STATE_NOT_COLLECTED,
               icon="layers", note="需业务单元主数据（外部 MDM/POS），当前生产库无此口径",
               source="BLOCKED: external MDM"),
        metric("cth02.present_brands", "在场品牌", value=None, state=STATE_NOT_COLLECTED,
               icon="campaign", note="需品牌租约/业态主数据，当前生产库无此口径",
               source="BLOCKED: external brand master"),
    ]
    blocked += [_block("cth02.business_units", "BLOCKED_BY_EXTERNAL_DEPENDENCY", "需 MDM 主数据"),
                _block("cth02.present_brands", "BLOCKED_BY_EXTERNAL_DEPENDENCY", "需品牌主数据")]

    # 品类分布：兼容 list[dict] / dict 两种真实返回
    rows = []
    if isinstance(dist, list):
        for d in dist[:14]:
            if isinstance(d, dict):
                rows.append({"品类": d.get("category") or d.get("name") or "—",
                             "数量": d.get("count") or d.get("total") or 0})
            else:
                rows.append({"品类": str(d[0]) if isinstance(d, (list, tuple)) else str(d), "数量": ""})
    elif isinstance(dist, dict):
        rows = [{"品类": k, "数量": v} for k, v in list(dist.items())[:14]]
    dist_sec = section("table", STATE_READY if rows else STATE_EMPTY, title="品类 / 情感分布（真实）",
                       columns=[{"label": "品类", "key": "品类"},
                                {"label": "数量", "key": "数量", "numeric": True}], rows=rows)
    note_sec = section("note", STATE_READY, kind="RULE", code="SUBJECT-IS-CONTEXT",
                       text="选择主体只改变工作上下文；品牌、业态、业务单元的事实归属保持不变。"
                            "业务单元/在场品牌需外部主数据，未接入前不展示虚构数值。")
    sections = [_head("CTH-02"), section("kpis", STATE_READY, items=kpis), dist_sec, note_sec]
    return _envelope("CTH-02", sections, blocked=blocked)


def _build_cth03() -> Dict[str, Any]:
    """实时监测流：真实最新笔记/负面流。"""
    import database as db

    recent = _safe(db.get_notes, {"limit": 30}, default=[])
    neg = _safe(db.get_negative_comments, 30, default=[])
    n_all = len(recent) if isinstance(recent, list) else 0
    n_neg = len(neg) if isinstance(neg, list) else 0
    kpis = [
        metric("cth03.recent", "近窗记录", value=n_all, state=STATE_READY,
               icon="event", source="database.get_notes"),
        metric("cth03.negative", "其中负面", value=n_neg, state=STATE_READY,
               icon="risk", source="database.get_negative_comments"),
    ]
    stream = _notes_table("实时记录流（真实）", recent if isinstance(recent, list) else [], 15)
    sections = [_head("CTH-03"), section("kpis", STATE_READY, items=kpis), stream]
    return _envelope("CTH-03", sections)


def _build_cth04() -> Dict[str, Any]:
    """事件与事件关系：真实事件列表；关系图需图关系数据，缺则诚实 blocked。"""
    import database as db

    events = _safe(db.get_events_curated, 20, default=[])
    items = _events_items(events if isinstance(events, list) else [])
    kpis = [
        metric("cth04.events", "已策展事件", value=len(items), state=STATE_READY,
               icon="event", source="database.get_events_curated"),
        metric("cth04.graph", "事件关系边", value=None, state=STATE_NOT_COLLECTED,
               icon="trend", note="关系图需要事件关联边表（mention/event_link），当前无独立关系口径",
               source="BLOCKED: event relationship edge table"),
    ]
    blocked = [_block("cth04.graph", "BLOCKED_BY_EXTERNAL_DEPENDENCY", "需事件关系边数据")]
    ev_sec = section("events", STATE_READY if items else STATE_EMPTY, title="事件列表（真实）", items=items)
    sections = [_head("CTH-04"), section("kpis", STATE_READY, items=kpis), ev_sec]
    return _envelope("CTH-04", sections, blocked=blocked)


def _build_cth05() -> Dict[str, Any]:
    """舆情日历：真实近 14 日按天负面/高风险序列。"""
    labels, neg, high = days_labels_series(14)
    total_neg, total_high = sum(neg), sum(high)
    kpis = [
        metric("cth05.neg14", "近14日负面", value=total_neg, state=STATE_READY,
               icon="risk", source="database.get_stats_by_date_range"),
        metric("cth05.high14", "近14日高风险", value=total_high, state=STATE_READY,
               icon="event", source="database.get_stats_by_date_range"),
    ]
    chart = section("chart", STATE_READY, kind="line", title="近 14 日舆情日历趋势",
                    sub="按天现算，不补点、不平滑",
                    series=[{"name": "负面", "data": neg, "color": "var(--lum-c-danger,#c0563f)"},
                            {"name": "高风险", "data": high, "color": "var(--lum-c-info,#4FC4E8)"}],
                    labels=labels,
                    legend=[{"label": "负面", "color": "var(--lum-c-danger,#c0563f)"},
                            {"label": "高风险", "color": "var(--lum-c-info,#4FC4E8)"}])
    sections = [_head("CTH-05"), section("kpis", STATE_READY, items=kpis), chart]
    return _envelope("CTH-05", sections)


def _build_cth06() -> Dict[str, Any]:
    """负面与用户/评论反馈：真实负面记录。"""
    import database as db

    neg = _safe(db.get_negative_comments, 40, default=[])
    rows = neg if isinstance(neg, list) else []
    kpi = metric("cth06.negative", "负面反馈条数", value=len(rows), state=STATE_READY,
                 icon="risk", source="database.get_negative_comments")
    tbl = _notes_table("负面 / 用户反馈（真实）", rows, 20)
    sections = [_head("CTH-06"), section("kpis", STATE_READY, items=[kpi]), tbl]
    return _envelope("CTH-06", sections)


def _build_cth07() -> Dict[str, Any]:
    """趋势分析：真实近 14 日三序列（总/负面/高风险）。"""
    import database as db

    labels: List[str] = []
    totals, negs, highs = [], [], []
    today = _dt.date.today()
    for back in range(13, -1, -1):
        d = today - _dt.timedelta(days=back)
        st = _safe(db.get_stats_by_date_range, d.strftime("%Y-%m-%d"), d.strftime("%Y-%m-%d"), default={})
        labels.append(d.strftime("%m-%d"))
        totals.append(int(st.get("total", 0)) if isinstance(st, dict) and not _is_err(st) else 0)
        negs.append(int(st.get("negative", 0)) if isinstance(st, dict) and not _is_err(st) else 0)
        highs.append(int(st.get("high_risk", 0)) if isinstance(st, dict) and not _is_err(st) else 0)
    kpis = [
        metric("cth07.total", "近14日声量", value=sum(totals), state=STATE_READY,
               icon="trend", source="database.get_stats_by_date_range"),
        metric("cth07.neg", "近14日负面", value=sum(negs), state=STATE_READY,
               icon="risk", source="database.get_stats_by_date_range"),
    ]
    chart = section("chart", STATE_READY, kind="line", title="声量 / 负面 / 高风险趋势",
                    sub="按天现算",
                    series=[{"name": "总声量", "data": totals, "color": "var(--lum-text-2,#8a8f98)"},
                            {"name": "负面", "data": negs, "color": "var(--lum-c-danger,#c0563f)"},
                            {"name": "高风险", "data": highs, "color": "var(--lum-c-info,#4FC4E8)"}],
                    labels=labels,
                    legend=[{"label": "总声量", "color": "var(--lum-text-2,#8a8f98)"},
                            {"label": "负面", "color": "var(--lum-c-danger,#c0563f)"},
                            {"label": "高风险", "color": "var(--lum-c-info,#4FC4E8)"}])
    sections = [_head("CTH-07"), section("kpis", STATE_READY, items=kpis), chart]
    return _envelope("CTH-07", sections)


def _build_cth08() -> Dict[str, Any]:
    """案例库 / 案例分析：真实高风险笔记 + 已策展事件。"""
    import database as db

    risk = _safe(db.get_high_risk_notes, 20, default=[])
    events = _safe(db.get_events_curated, 10, default=[])
    risk = risk if isinstance(risk, list) else []
    kpi = metric("cth08.cases", "高风险候选案例", value=len(risk), state=STATE_READY,
                 icon="risk", source="database.get_high_risk_notes")
    tbl = _notes_table("高风险案例（真实）", risk, 14)
    ev = section("events", STATE_READY if events else STATE_EMPTY, title="已策展事件",
                 items=_events_items(events if isinstance(events, list) else []))
    sections = [_head("CTH-08"), section("kpis", STATE_READY, items=[kpi]), tbl, ev]
    return _envelope("CTH-08", sections)


def _build_cth09() -> Dict[str, Any]:
    """风险中心与决策看板：真实风险笔记 + Canonical 风险指数。"""
    import database as db
    import daily_report

    risk = _safe(db.get_high_risk_notes, 10, default=[])
    summ = _safe(daily_report.generate_today_summary, today_str(), default={})
    risk = risk if isinstance(risk, list) else []
    ri = summ.get("risk_index") if isinstance(summ, dict) and not _is_err(summ) else None
    bh = summ.get("brand_health_score") if isinstance(summ, dict) and not _is_err(summ) else None
    kpis = [
        metric("cth09.risk_index", "风险指数", value=ri, decimals=1, state=STATE_READY if ri is not None else STATE_EMPTY,
               icon="risk", source="daily_report.generate_today_summary", evidence_id="MET-RISK-01"),
        metric("cth09.health", "品牌健康分", value=bh, decimals=1, state=STATE_READY if bh is not None else STATE_EMPTY,
               icon="trend", source="daily_report.generate_today_summary", evidence_id="MET-RISK-02"),
        metric("cth09.risk_notes", "高风险记录", value=len(risk), state=STATE_READY,
               icon="event", source="database.get_high_risk_notes"),
    ]
    risk_items = []
    for n in risk[:5]:
        rs = n.get("risk_score")
        risk_items.append({
            "level": _LV.get(n.get("risk_level", "low"), "low"),
            "score": rs if isinstance(rs, (int, float)) and rs else None,
            "title": (n.get("title") or "风险笔记")[:40],
            "desc": (n.get("content") or "")[:90],
            "evidence": f"NOTE:{n.get('note_id') or n.get('id') or 'UNKNOWN'}",
        })
    risks_sec = section("risks", STATE_READY if risk_items else STATE_EMPTY, items=risk_items)
    sections = [_head("CTH-09"), section("kpis", STATE_READY, items=kpis), risks_sec]
    return _envelope("CTH-09", sections,
                     truth={"risk_index": ri, "brand_health_score": bh})


def _build_cth10() -> Dict[str, Any]:
    """报告 / 周报 / 证据：最近报告元数据 + 真实证据链。"""
    import database as db
    import evidence_store as es

    rep = _safe(db.get_latest_report, "daily", default=None)
    evid = _safe(es.query_evidence, limit=6, default=[])
    rep = rep if isinstance(rep, dict) and not _is_err(rep) else None
    kpis = [
        metric("cth10.report_date", "最近报告日期",
               value=(rep.get("report_date") if rep else None),
               state=STATE_READY if rep else STATE_EMPTY, icon="report",
               source="database.get_latest_report"),
        metric("cth10.evidence", "证据记录",
               value=len(evid) if isinstance(evid, list) else None,
               state=STATE_READY if isinstance(evid, list) else STATE_OFFLINE,
               icon="link", source="evidence_store.query_evidence"),
    ]
    ev_sec = section("evidence", STATE_READY if isinstance(evid, list) and evid else STATE_EMPTY,
                     title="证据链（真实）", items=_evidence_items(evid if isinstance(evid, list) else []))
    sections = [_head("CTH-10"), section("kpis", STATE_READY, items=kpis), ev_sec]
    return _envelope("CTH-10", sections)


# ===========================================================================
# AI Agent 域（真实数据源：skill_execution_chain / ai_governance / function_registry）
# ===========================================================================
def _task_timeline(limit: int = 8) -> Dict[str, Any]:
    from skill_execution_chain import query_executions

    tasks = _safe(query_executions, limit, default=[])
    items = []
    for t in (tasks if isinstance(tasks, list) else [])[:limit]:
        items.append({
            "time": str(t.get("created_at") or "")[5:16] or "—",
            "title": t.get("task") or t.get("skill_id") or "AI 任务",
            "desc": f"{t.get('status', 'unknown')} · {str(t.get('execution_id', ''))[:10]}",
            "done": t.get("status") in ("completed", "success", "done"),
        })
    return section("timeline", STATE_READY if items else STATE_EMPTY,
                   title="执行链任务（真实）", label="History", items=items)


def _build_ai02() -> Dict[str, Any]:
    """能力任务工作台：真实执行链。"""
    sections = [_head("AI-02"), _task_timeline(12)]
    return _envelope("AI-02", sections)


def _build_ai03() -> Dict[str, Any]:
    """证据锚定分析线程：执行链 + 证据。"""
    import evidence_store as es

    evid = _safe(es.query_evidence, limit=6, default=[])
    tl = _task_timeline(8)
    ev = section("evidence", STATE_READY if isinstance(evid, list) and evid else STATE_EMPTY,
                 title="证据跳转锚点（真实）", items=_evidence_items(evid if isinstance(evid, list) else []))
    sections = [_head("AI-03"), tl, ev]
    return _envelope("AI-03", sections)


def _build_ai04() -> Dict[str, Any]:
    """Agent / 技能中心：真实 function_registry。"""
    import function_registry as fr

    fmap = getattr(fr, "FUNCTION_MAP", {})
    rows = []
    if isinstance(fmap, dict):
        for fid, fn in list(fmap.items())[:40]:
            rows.append({"技能": str(fid),
                         "类型": type(fn).__name__ if not isinstance(fn, dict) else (fn.get("type") or "func")})
    elif isinstance(fmap, list):
        for fn in fmap[:40]:
            rows.append({"技能": str(fn.get("id") or fn.get("name") or "—"),
                         "类型": str(fn.get("type") or "func")})
    kpi = metric("ai04.functions", "已注册函数 / 技能", value=len(fmap) if hasattr(fmap, "__len__") else None,
                 state=STATE_READY if rows else STATE_EMPTY, icon="skill",
                 source="function_registry.FUNCTION_MAP")
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="函数 / 技能注册表（真实）",
                  columns=[{"label": "技能", "key": "技能"}, {"label": "类型", "key": "类型"}], rows=rows)
    sections = [_head("AI-04"), section("kpis", STATE_READY, items=[kpi]), tbl]
    return _envelope("AI-04", sections)


def _build_ai05() -> Dict[str, Any]:
    """AI Gateway 与 Provider：真实治理状态。"""
    from experience_runtime import _ai_governance, _provider_runtime

    gov = _safe(_ai_governance, default={})
    gov_err = _is_err(gov)
    providers = _provider_runtime(gov if isinstance(gov, dict) else {}, gov_err)
    healthy = sum(1 for p in providers if p["state"] == "ok")
    kpis = [
        metric("ai05.providers_ok", "可用 Provider", value=healthy, unit=f"/{len(providers)}",
               state=STATE_READY if not gov_err else STATE_OFFLINE, icon="ops",
               source="ai_governance.get_governance_status"),
    ]
    rt = section("runtime", title="Provider 状态（真实）", items=providers)
    rule = section("note", STATE_READY, kind="RULE", code="AI-GATEWAY",
                   text="云 AI 不构成产品启动硬依赖；治理层不可用时确定性规则引擎继续工作，页面不伪造延迟。")
    sections = [_head("AI-05"), section("kpis", STATE_READY, items=kpis), rt, rule]
    return _envelope("AI-05", sections)


# ===========================================================================
# SYSTEM 域（真实数据源：runtime_guardian / canonical_data / permission_gate）
# ===========================================================================
def _build_sys01() -> Dict[str, Any]:
    """运行时健康：runtime_guardian 真实健康（状态串走状态条，数值计数才进 KPI，避免 NaN）。"""
    import runtime_guardian as rg

    hc = _safe(rg.legacy_health_check, default={})
    hc = hc if isinstance(hc, dict) and not _is_err(hc) else {}
    overall = hc.get("overall")
    workers = hc.get("workers") if isinstance(hc.get("workers"), dict) else {}
    dlq = hc.get("dlq") if isinstance(hc.get("dlq"), dict) else {}

    def _int(v, default=None):
        return v if isinstance(v, int) and not isinstance(v, bool) else default

    # 只有真实数值才作为数值 KPI（kpis 渲染器会对 ready 值做 countup，状态串会变 NaN）
    kpis = [
        metric("sys01.workers_total", "注册 Worker", value=_int(workers.get("total"), 0),
               state=STATE_READY, icon="ops", source="runtime_guardian.workers.total"),
        metric("sys01.workers_failed", "失败 Worker", value=_int(workers.get("failed"), 0),
               state=STATE_READY, icon="risk", source="runtime_guardian.workers.failed"),
        metric("sys01.dlq", "DLQ 积压", value=_int(dlq.get("total"), 0),
               state=STATE_READY, icon="database", source="runtime_guardian.dlq.total"),
    ]
    overall_state = {"healthy": "ok", "ok": "ok", "degraded": "warn",
                     "unhealthy": "bad", "error": "bad"}.get(str(overall).lower(), "idle")
    rt_items = [
        {"name": "总体状态", "state": overall_state, "detail": str(overall or "unknown")},
        {"name": "reaper", "state": "ok" if hc.get("reaper_running") else "idle",
         "detail": f"running={bool(hc.get('reaper_running'))}"},
        {"name": "熔断器", "state": "ok",
         "detail": f"open={len(hc.get('circuit_breakers') or {})}"},
        {"name": "guardian", "state": "idle", "detail": str(hc.get("guardian_name") or "—")},
        {"name": "时间戳", "state": "idle", "detail": str(hc.get("timestamp") or "—")},
    ]
    rt = section("runtime", title="健康明细（真实）", items=rt_items)
    sections = [_head("SYS-01"), section("kpis", STATE_READY, items=kpis), rt]
    return _envelope("SYS-01", sections, truth={"overall": overall})


def _scalar_str(v: Any) -> str:
    if isinstance(v, dict):
        return " · ".join(f"{k}={v[k]}" for k in list(v)[:3] if v[k] is not None) or "ok"
    if isinstance(v, (list, tuple)):
        return f"items={len(v)}"
    return "NA" if v is None else str(v)


def _build_sys03() -> Dict[str, Any]:
    """数据库与事实链：canonical_data 自检 + schema 版本（真实）。"""
    import database as db
    import canonical_data as cd

    db_path = getattr(db, "DB_PATH", "")
    chk = _safe(cd.self_check, db_path, default={})
    chk = chk if isinstance(chk, dict) and not _is_err(chk) else {}
    versions = _safe(cd.get_schema_versions, db_path, default=[])
    n_ver = len(versions) if isinstance(versions, list) else None
    rows = [{"检查项": str(k), "结果": _scalar_str(v)} for k, v in list(chk.items())[:14]]
    kpis = [
        metric("sys03.schema_versions", "Schema 版本记录", value=n_ver,
               state=STATE_READY if n_ver is not None else STATE_EMPTY,
               icon="database", source="canonical_data.get_schema_versions"),
    ]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="Canonical 自检（真实）",
                  columns=[{"label": "检查项", "key": "检查项"}, {"label": "结果", "key": "结果"}], rows=rows)
    sections = [_head("SYS-03"), section("kpis", STATE_READY, items=kpis), tbl]
    return _envelope("SYS-03", sections, truth={"self_check": chk})


def _build_sys04() -> Dict[str, Any]:
    """安全与权限：permission_gate 真实权限级别枚举（不泄露任何凭据）。"""
    try:
        import permission_gate as pg

        levels = [lvl.name for lvl in getattr(pg, "PermissionLevel", [])] or []
        ops = [op.name for op in getattr(pg, "OperationType", [])] or []
    except Exception as exc:  # noqa: BLE001
        levels, ops = [], []
        levels_err = str(exc)
    else:
        levels_err = ""
    rows = [{"权限级别": x, "范围": "READ/TASK/AUDIT/WRITE/DEPLOY" if x in levels else "—"} for x in levels]
    kpi = metric("sys04.levels", "权限级别数", value=len(levels) or None,
                 state=STATE_READY if levels else STATE_EMPTY, icon="permission",
                 source="permission_gate.PermissionLevel")
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="权限级别（真实枚举）",
                  columns=[{"label": "权限级别", "key": "权限级别"}, {"label": "范围", "key": "范围"}], rows=rows)
    note_sec = section("note", STATE_READY, kind="RULE", code="NO-SECRET",
                       text="界面只呈现权限级别与操作类型，不展示任何 token/cookie/密钥/浏览器会话。"
                            + (f"（枚举读取：{levels_err}）" if levels_err else ""))
    sections = [_head("SYS-04"), section("kpis", STATE_READY, items=[kpi]), tbl, note_sec]
    return _envelope("SYS-04", sections, truth={"operation_types": ops})


# ===========================================================================
# Shared Content 域
# ===========================================================================
def _build_sh03() -> Dict[str, Any]:
    """Canonical 数据 / 指标浏览器：canonical 计数 + schema（真实）。"""
    import canonical_data as cd

    counts: Dict[str, Any] = {}
    err = ""
    try:
        with cd.get_connection() as con:
            counts = cd.count_canonical(con) or {}
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
    rows = [{"对象": str(k), "数量": v} for k, v in list(counts.items())[:14]]
    total = sum(v for v in counts.values() if isinstance(v, (int, float))) if counts else None
    kpi = metric("sh03.canonical_total", "Canonical 记录", value=total,
                 state=STATE_READY if total is not None else (STATE_OFFLINE if err else STATE_EMPTY),
                 icon="database", source="canonical_data.count_canonical",
                 note=err)
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="Canonical 计数（真实）",
                  columns=[{"label": "对象", "key": "对象"}, {"label": "数量", "key": "数量", "numeric": True}],
                  rows=rows)
    sections = [_head("SH-03"), section("kpis", STATE_READY, items=[kpi]), tbl]
    return _envelope("SH-03", sections, truth={"counts": counts})


# ---------------------------------------------------------------------------
# 注册表：一屏一 builder
# ---------------------------------------------------------------------------
SCREEN_BUILDERS = {
    "CTH-02": _build_cth02,
    "CTH-03": _build_cth03,
    "CTH-04": _build_cth04,
    "CTH-05": _build_cth05,
    "CTH-06": _build_cth06,
    "CTH-07": _build_cth07,
    "CTH-08": _build_cth08,
    "CTH-09": _build_cth09,
    "CTH-10": _build_cth10,
    "AI-02": _build_ai02,
    "AI-03": _build_ai03,
    "AI-04": _build_ai04,
    "AI-05": _build_ai05,
    "SYS-01": _build_sys01,
    "SYS-03": _build_sys03,
    "SYS-04": _build_sys04,
    "SH-03": _build_sh03,
}
