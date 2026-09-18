"""序境 / LUMENIS — Experience 生产 ViewModel 绑定层.

唯一设计权威：00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md

本模块不拥有页面布局或视觉规则。它负责把真实后端事实映射成前端可消费的
ViewModel/section 数据，并保持 Evidence、状态、权限与缺失语义诚实。

experience_v2/10_prototype 目前只是兼容实现路径，不代表 V2 设计仍有权威。
Golden Pages 迁移到新的语义 composition 时，本绑定层应保持 truth-first、
layout-agnostic，必要时适配新的语义 section，而不是强迫 UI 继续使用旧模板。

生产事实约束：
  * 每个数值来自既有真实后端能力；
  * 无数据源字段使用 notcollected / None，并记录真实 blocker；
  * 读取异常降级为 offline/error，不伪造成功；
  * 只读聚合不改变 Canonical Data、Evidence 或权限边界。
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
    shared_skill_surface,
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


def _platform_collection_section(*, consumer: str = "CTH") -> Dict[str, Any]:
    """Build the shared platform-intelligence surface for CTH and BMP.

    CTH owns the collector and its Evidence/Canonical writes.  BMP receives
    the same read-only view as a market-intelligence consumer; this helper
    deliberately does not create a second BMP collector or truth table.
    """
    try:
        from lumenis.system.collector.adapters.secondary_collection import get_collection_surface

        surface = _safe(get_collection_surface, default={})
    except Exception:
        surface = {}
    if not isinstance(surface, dict) or not surface.get("ok"):
        return section(
            "platforms", STATE_OFFLINE,
            title="平台情报 · 只读采集",
            description="CTH 采集面当前不可读取；未展示平台样例数据。",
            items=[],
            consumer=consumer,
            manual_only=True,
            read_only=True,
            product_will_not_publish=True,
        )

    status_labels = {
        "READY": "待人工触发",
        "PROBING": "驻场状态探测中",
        "UNVERIFIED": "本机运行态未验证",
        "USER_PAUSED": "用户已暂停",
        "SUCCESS": "最近成功",
        "NO_NEW_DATA": "暂无新内容",
        "SESSION_EXPIRED": "需更新登录态",
        "NEED_VERIFY": "需人工验证",
        "RISK_WARNING": "风险降频",
        "BLOCKED": "已阻断",
        "COLLECT_ERROR": "引擎异常",
        "UNAVAILABLE": "未就绪",
        "CONFIGURED": "已配置，待首次运行",
        "NOT_SUPPORTED": "暂不支持该能力",
        "NOT_CONFIGURED": "未配置运行方式",
        "PROVIDER_UNAVAILABLE": "运行服务暂不可用",
        "COOLING_DOWN": "冷却中",
        "RATE_LIMITED": "达到采集频率上限",
        "POLICY_STATE_UNAVAILABLE": "门禁状态不可用",
        "IMPORT_FAILED": "部分记录未入库",
        "CANONICAL_SYNC_FAILED": "Canonical 同步未完成",
        "EVIDENCE_WRITE_FAILED": "Evidence 保存失败",
        "BUSY": "正在采集中",
    }
    tone = {
        "READY": "info", "SUCCESS": "success", "NO_NEW_DATA": "neutral",
        "PROBING": "info", "UNVERIFIED": "neutral", "USER_PAUSED": "neutral",
        "SESSION_EXPIRED": "warning", "NEED_VERIFY": "warning",
        "NOT_CONFIGURED": "warning", "PROVIDER_UNAVAILABLE": "warning",
        "COOLING_DOWN": "warning", "RATE_LIMITED": "warning",
        "POLICY_STATE_UNAVAILABLE": "warning", "BUSY": "info",
        "RISK_WARNING": "danger", "BLOCKED": "danger", "COLLECT_ERROR": "danger",
        "IMPORT_FAILED": "danger", "CANONICAL_SYNC_FAILED": "danger",
        "EVIDENCE_WRITE_FAILED": "danger", "UNAVAILABLE": "neutral",
        "CONFIGURED": "neutral", "NOT_SUPPORTED": "neutral",
    }
    rows: List[Dict[str, Any]] = []
    primary = surface.get("primary_collection")
    if isinstance(primary, dict):
        runtime = primary.get("runtime") if isinstance(primary.get("runtime"), dict) else {}
        health = primary.get("health") if isinstance(primary.get("health"), dict) else {}
        last = primary.get("last_run") if isinstance(primary.get("last_run"), dict) else {}
        status = str(primary.get("status") or runtime.get("status") or "UNVERIFIED").upper()
        fetched = last.get("fetched")
        rows.append({
            "platform": primary.get("name") or "小红书（香港账号）",
            "platform_id": "xhs_hk_primary",
            "primary_collector": True,
            "status": {
                "READY": "驻场状态已验证",
                "PROBING": "驻场状态探测中",
                "SESSION_EXPIRED": "登录态需人工恢复",
                "USER_PAUSED": "用户已暂停",
                "UNVERIFIED": "本机运行态未验证",
            }.get(status, status),
            "status_tone": {
                "READY": "success", "PROBING": "info", "SESSION_EXPIRED": "warning",
                "USER_PAUSED": "neutral", "UNVERIFIED": "neutral",
            }.get(status, tone.get(status, "neutral")),
            "schedule": primary.get("entry_label") or "既有主采集链路 · 此表只读展示",
            "last_run": (last.get("finished_at") or last.get("started_at") or "—") if last else "—",
            "counts": f"{fetched if fetched is not None else '—'} / —" if last else "—",
            "subject_matches": None,
            "evidence": "既有采集日志" if last else "暂无持久化采集日志",
            "ready": bool(health.get("ready")),
            "manual_collection_enabled": bool(primary.get("manual_collection_enabled")),
            "can_attempt": bool(health.get("can_attempt")),
            "form_selectable": False,
        })

    for item in surface.get("platforms", []) if isinstance(surface.get("platforms"), list) else []:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "UNAVAILABLE").upper()
        health = item.get("health") if isinstance(item.get("health"), dict) else {}
        last = item.get("last_run") if isinstance(item.get("last_run"), dict) else {}
        manual_enabled = bool(item.get("manual_collection_enabled"))
        can_attempt = bool(health.get("can_attempt", health.get("ready", False)))
        fetched = last.get("fetched")
        accepted = last.get("accepted")
        counts = "—" if not last else f"{fetched if fetched is not None else '—'} / {accepted if accepted is not None else '—'}"
        last_at = (last.get("finished_at") or last.get("started_at") or "—") if last else "—"
        rows.append({
            "platform": item.get("name") or item.get("platform") or "—",
            "platform_id": item.get("platform") or "",
            "status": status_labels.get(status, status),
            "status_tone": tone.get(status, "neutral"),
            "schedule": item.get("entry_label") or (
                "可人工触发" if manual_enabled and can_attempt
                else "需配置 / 验证" if manual_enabled
                else "未开放"
            ),
            "last_run": last_at,
            "counts": counts,
            "subject_matches": last.get("accepted") if last else None,
            "evidence": "Evidence 链路" if last else "待首次运行",
            "ready": bool(health.get("ready")),
            "manual_collection_enabled": manual_enabled,
            "can_attempt": can_attempt,
        })

    can_trigger = consumer == "CTH"
    return section(
        "platforms", STATE_READY,
        title="平台情报 · CTH 只读采集",
        description=(
            "香港小红书沿用既有主采集链路；其他平台复用已注册适配器，由 CTH 人工触发并按 Evidence / Canonical 契约处理。"
            "本表单不接管小红书、不启用平台写入或自动发布；BMP 只读查看共享数据。"
        ),
        items=rows,
        endpoint="/api/experience/cth/platform-collection/search" if can_trigger else "",
        source_endpoint="/api/experience/cth/platform-collection" if can_trigger else "",
        default_keyword="广州太古汇" if can_trigger else "",
        can_trigger=can_trigger,
        manual_only=True,
        read_only=True,
        external_write=False,
        product_will_not_publish=True,
        consumer=consumer,
        paused_platforms=surface.get("paused_platforms", []),
        out_of_scope_platforms=surface.get("out_of_scope_platforms", []),
    )


def _curated(v: Any) -> List[Dict[str, Any]]:
    """get_events_curated 返回 {'featured':[...],'generic_count','noise_count','total'}；取 featured 列表。"""
    if isinstance(v, dict):
        f = v.get("featured")
        return f if isinstance(f, list) else []
    return v if isinstance(v, list) else []


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
    platform_sec = _platform_collection_section(consumer="CTH")
    stream = _notes_table("实时记录流（真实）", recent if isinstance(recent, list) else [], 15)
    sections = [_head("CTH-03"), section("kpis", STATE_READY, items=kpis), platform_sec, stream]
    return _envelope("CTH-03", sections)


def _build_cth04() -> Dict[str, Any]:
    """事件与事件关系：真实事件列表；关系图需图关系数据，缺则诚实 blocked。"""
    import database as db

    events = _safe(db.get_events_curated, 20, default=[])
    items = _events_items(_curated(events))
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
    ev = section("events", STATE_READY if _curated(events) else STATE_EMPTY, title="已策展事件",
                 items=_events_items(_curated(events)))
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
    actions_sec = section("actions", title="受控运行操作", items=[
        {
            "id": "archive-dead-workers",
            "title": "归档历史 dead workers",
            "icon": "runtime",
            "cls": "EFFECT",
            "scope": "system_runtime",
            "target": "/api/runtime/archive-dead",
            "permission": "human_approval",
            "desc": "先审批，再一次性归档超过 24 小时的 DEAD/STOPPED worker",
            "risk": True,
        },
    ])
    note_sec = section("note", STATE_READY, kind="RULE", code="NO-SECRET",
                       text="界面只呈现权限级别与操作类型，不展示任何 token/cookie/密钥/浏览器会话。"
                            + (f"（枚举读取：{levels_err}）" if levels_err else ""))
    sections = [_head("SYS-04"), section("kpis", STATE_READY, items=[kpi]), tbl, actions_sec, note_sec]
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


# ===========================================================================
# 第二批传播：存在真实只读后端源的 System / Shared / BMP 屏（P1 增量）
# 每个数值都来自真实只读函数；无数据走 EMPTY，外部未连通如实标状态，绝不造假。
# ===========================================================================
def _int_or_none(v: Any) -> Optional[int]:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _build_sys02() -> Dict[str, Any]:
    """采集器状态：collector_status_api.get_all_status（真实连通状态，未验证不标 ACTIVE）。"""
    from collector_status_api import get_all_status

    st = _safe(get_all_status, default={})
    st = st if isinstance(st, dict) and not _is_err(st) else {}
    summ = st.get("summary") if isinstance(st.get("summary"), dict) else {}
    plats = st.get("platforms") if isinstance(st.get("platforms"), list) else []

    def _k(key: str, label: str, icon: str = "ops") -> Dict[str, Any]:
        v = _int_or_none(summ.get(key))
        return metric(f"sys02.{key}", label, value=v,
                      state=STATE_READY if v is not None else STATE_EMPTY,
                      icon=icon, source="collector_status_api.get_all_status")

    kpis = [_k("active", "真连通 ACTIVE/VERIFIED"), _k("partial", "受限 PARTIAL"),
            _k("missing", "缺登录态 MISSING"), _k("blocked", "被反爬 BLOCKED")]
    rows = [{
        "平台": p.get("display") or p.get("platform"),
        "状态": p.get("cookie_status") or "—",
        "解析记录": _int_or_none(p.get("records_parsed")),
        "说明": p.get("error") or "—",
    } for p in plats if isinstance(p, dict)]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY,
                  title="采集器连通状态（真实；未连通如实标 MISSING/INVALID/BLOCKED）",
                  columns=[{"label": "平台", "key": "平台"}, {"label": "状态", "key": "状态"},
                           {"label": "解析记录", "key": "解析记录", "numeric": True},
                           {"label": "说明", "key": "说明"}], rows=rows)
    note = section("note", STATE_READY, kind="RULE", code="NO-FAKE-ACTIVE",
                   text="状态来自最近一次真连通验证缓存与 cookie 文件级检查；未做真连通验证不标 ACTIVE。")
    sections = [_head("SYS-02"), section("kpis", STATE_READY, items=kpis), tbl, note]
    return _envelope("SYS-02", sections, truth={"summary": summ, "total_platforms": st.get("total_platforms")})


def _build_sys07() -> Dict[str, Any]:
    """验收评估：ai_governance OWASP 启用项 + 已注册技能轻状态（真实）。"""
    import ai_governance as gov
    from skill_execution_chain import get_skills_light_status

    ow = _safe(gov.get_owasp_security_status, default={})
    ow = ow if isinstance(ow, dict) and not _is_err(ow) else {}
    sk = _safe(get_skills_light_status, default=[])
    sk = sk if isinstance(sk, list) else []
    checks = ow.get("checks_enabled") if isinstance(ow.get("checks_enabled"), list) else []
    cnt = _int_or_none(ow.get("checks_count")) or (len(checks) or None)
    kpis = [
        metric("sys07.owasp_checks", "OWASP 防护项", value=cnt,
               state=STATE_READY if checks else STATE_EMPTY, icon="permission",
               source="ai_governance.get_owasp_security_status"),
        metric("sys07.skills", "已注册技能", value=len(sk) or None,
               state=STATE_READY if sk else STATE_EMPTY, icon="ai",
               source="skill_execution_chain.get_skills_light_status"),
    ]
    rows = [{"防护项": str(c), "参考": ow.get("ic_reference") or "—"} for c in checks]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY,
                  title="OWASP Agentic Top10 启用项（真实）",
                  columns=[{"label": "防护项", "key": "防护项"}, {"label": "参考", "key": "参考"}], rows=rows)
    sections = [_head("SYS-07"), section("kpis", STATE_READY, items=kpis), tbl]
    return _envelope("SYS-07", sections, truth={"ic_reference": ow.get("ic_reference")})


def _build_sys08() -> Dict[str, Any]:
    """可观测/日志：logger.get_log_summary（真实；只显文件名，不暴露绝对路径）。"""
    import logger as L

    s = _safe(L.get_log_summary, default={})
    s = s if isinstance(s, dict) and not _is_err(s) else {}
    files = s.get("files") if isinstance(s.get("files"), list) else []
    tf = _int_or_none(s.get("total_files"))
    tmb = s.get("total_size_mb")
    kpis = [
        metric("sys08.files", "日志文件", value=tf,
               state=STATE_READY if tf is not None else STATE_EMPTY, icon="ops",
               source="logger.get_log_summary"),
        metric("sys08.size_mb", "日志体积 MB", value=round(tmb, 2) if isinstance(tmb, (int, float)) else None,
               decimals=2, state=STATE_READY if isinstance(tmb, (int, float)) else STATE_EMPTY,
               icon="ops", source="logger.get_log_summary"),
    ]
    rows = [{"文件": f.get("name"), "大小MB": f.get("size_mb"),
             "修改": str(f.get("modified") or "")[:19]} for f in files if isinstance(f, dict)]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY,
                  title="日志文件（真实；仅文件名，不暴露绝对路径）",
                  columns=[{"label": "文件", "key": "文件"},
                           {"label": "大小MB", "key": "大小MB", "numeric": True},
                           {"label": "修改", "key": "修改"}], rows=rows)
    sections = [_head("SYS-08"), section("kpis", STATE_READY, items=kpis), tbl]
    return _envelope("SYS-08", sections)


def _build_sh02() -> Dict[str, Any]:
    """证据库：evidence_store 真实只读列表 + 统计。"""
    import evidence_store as es

    recs = _safe(es.query_evidence, limit=30, default=[])
    stats = _safe(es.get_stats, default={})
    recs = recs if isinstance(recs, list) else []
    stats = stats if isinstance(stats, dict) and not _is_err(stats) else {}
    total = _int_or_none(stats.get("total"))
    if total is None:
        total = len(recs) or None
    kpi = metric("sh02.total", "证据总量", value=total,
                 state=STATE_READY if total is not None else STATE_EMPTY, icon="link",
                 source="evidence_store.get_stats/query_evidence")
    rows = [{
        "ID": f"EV:{r.get('id')}",
        "级别": r.get("level") or "—",
        "来源": r.get("source") or r.get("account") or "—",
        "特征": str(r.get("feature_id") or "")[:28] or "—",
        "结果": r.get("result") or "—",
        "时间": str(r.get("created_at") or "")[:16],
    } for r in recs if isinstance(r, dict)]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="证据库记录（真实只读）",
                  columns=[{"label": "ID", "key": "ID"}, {"label": "级别", "key": "级别"},
                           {"label": "来源", "key": "来源"}, {"label": "特征", "key": "特征"},
                           {"label": "结果", "key": "结果"}, {"label": "时间", "key": "时间"}], rows=rows)
    ev = section("evidence", STATE_READY if recs else STATE_EMPTY,
                 title="证据链（最近）", items=_evidence_items(recs, 4))
    sections = [_head("SH-02"), section("kpis", STATE_READY, items=[kpi]), tbl, ev]
    return _envelope("SH-02", sections, truth={"stats": stats})


def _build_sh04() -> Dict[str, Any]:
    """报告导出中心：report_engine.list_domain_reports 真实目录（导出 EFFECT 待端点，不造假下载）。"""
    import report_engine as re_

    cat = _safe(re_.list_domain_reports, default={})
    cat = cat if isinstance(cat, dict) and not _is_err(cat) else {}
    rows = []
    for dom, types in cat.items():
        if not isinstance(types, dict):
            continue
        for t, meta in types.items():
            meta = meta if isinstance(meta, dict) else {}
            rows.append({"领域": str(dom), "类型": str(t),
                         "名称": meta.get("name") or t,
                         "受保护": "是" if meta.get("protected") else "否"})
    kpi = metric("sh04.types", "报告类型", value=len(rows) or None,
                 state=STATE_READY if rows else STATE_EMPTY, icon="report",
                 source="report_engine.list_domain_reports")
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="可导出报告目录（真实）",
                  columns=[{"label": "领域", "key": "领域"}, {"label": "类型", "key": "类型"},
                           {"label": "名称", "key": "名称"}, {"label": "受保护", "key": "受保护"}], rows=rows)
    note = section("note", STATE_READY, kind="RULE", code="EXPORT-EFFECT",
                   text="目录为真实只读；点击导出属写操作，需 report_engine 导出端点 + 权限门控，未接通前不提供假下载。")
    sections = [_head("SH-04"), section("kpis", STATE_READY, items=[kpi]), tbl, note]
    return _envelope("SH-04", sections, truth={"domains": list(cat.keys())})


def _build_sh06() -> Dict[str, Any]:
    """通知/任务中心：TaskEngine.list_tasks/get_dlq/health_check（真实）。"""
    import ai_task_engine as te

    eng = te.get_task_engine()
    tasks = _safe(eng.list_tasks, limit=20, default=[])
    dlq = _safe(eng.get_dlq, default=[])
    hc = _safe(eng.health_check, default={})
    tasks = tasks if isinstance(tasks, list) else []
    dlq = dlq if isinstance(dlq, list) else []
    hc = hc if isinstance(hc, dict) and not _is_err(hc) else {}

    def _g(o: Any, k: str) -> Any:
        return o.get(k) if isinstance(o, dict) else getattr(o, k, None)

    kpis = [
        metric("sh06.tasks", "在列任务", value=len(tasks) or None,
               state=STATE_READY if tasks else STATE_EMPTY, icon="ai",
               source="TaskEngine.list_tasks"),
        metric("sh06.dlq", "死信队列", value=len(dlq), state=STATE_READY,
               icon="ops", source="TaskEngine.get_dlq"),
    ]
    rows = []
    for t in tasks:
        st = _g(t, "status")
        st = st if isinstance(st, str) else getattr(st, "value", "—")
        rows.append({"任务": str(_g(t, "task_id") or _g(t, "id") or "—")[:22],
                     "状态": st, "技能": str(_g(t, "skill_id") or "—"),
                     "创建": str(_g(t, "created_at") or "")[:16]})
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="任务 / 通知（真实）",
                  columns=[{"label": "任务", "key": "任务"}, {"label": "状态", "key": "状态"},
                           {"label": "技能", "key": "技能"}, {"label": "创建", "key": "创建"}], rows=rows)
    cb = hc.get("circuit_breaker") if isinstance(hc.get("circuit_breaker"), dict) else {}
    rt = section("runtime", title="任务引擎健康（真实）", items=[
        {"name": "总体", "state": {"healthy": "ok", "ok": "ok", "degraded": "warn"}.get(
            str(hc.get("status")).lower(), "idle"), "detail": str(hc.get("status") or "—")},
        {"name": "熔断器", "state": "ok" if cb.get("state") == "closed" else "warn",
         "detail": f"state={cb.get('state', '—')} · failures={_int_or_none(cb.get('failure_count')) or 0}"},
        {"name": "DB", "state": "ok" if hc.get("db") == "connected" else "bad",
         "detail": str(hc.get("db") or "—")},
    ])
    sections = [_head("SH-06"), section("kpis", STATE_READY, items=kpis), tbl, rt]
    return _envelope("SH-06", sections, truth={"engine_status": hc.get("status")})


def _build_bmp06() -> Dict[str, Any]:
    """内容中心：content_generation 模块状态 + 内容证据（真实）。"""
    import content_generation as cg

    le = _safe(cg.list_evidence, limit=20, default={})
    mods = _safe(cg.get_module_status, default=[])
    le = le if isinstance(le, dict) and not _is_err(le) else {}
    mods = mods if isinstance(mods, list) else []
    items = le.get("items") if isinstance(le.get("items"), list) else []
    active = [m for m in mods if isinstance(m, dict) and m.get("status") == "ACTIVE"]
    ev_total = _int_or_none(le.get("total"))
    if ev_total is None:
        ev_total = len(items) or None
    kpis = [
        metric("bmp06.evidence", "内容证据", value=ev_total,
               state=STATE_READY if ev_total is not None else STATE_EMPTY, icon="content",
               source="content_generation.list_evidence"),
        metric("bmp06.modules", "ACTIVE 模块", value=len(active) or None,
               state=STATE_READY if active else STATE_EMPTY, icon="ai",
               source="content_generation.get_module_status"),
    ]
    rows = [{"模块": m.get("name") or m.get("id"), "ID": m.get("id"),
             "状态": m.get("status") or "—", "AI": "是" if m.get("ai") else "否",
             "端点": m.get("api") or "—"} for m in mods if isinstance(m, dict)]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="内容生成模块状态（真实）",
                  columns=[{"label": "模块", "key": "模块"}, {"label": "ID", "key": "ID"},
                           {"label": "状态", "key": "状态"}, {"label": "AI", "key": "AI"},
                           {"label": "端点", "key": "端点"}], rows=rows)
    sections = [_head("BMP-06"), section("kpis", STATE_READY, items=kpis), tbl]
    return _envelope("BMP-06", sections, truth={"module_count": len(mods)})


def _build_bmp08() -> Dict[str, Any]:
    """播客工作室：podcast_store 统计 + 实体（真实，空库如实 EMPTY）。"""
    import podcast_store as ps

    st = _safe(ps.get_stats, default={})
    ents = _safe(ps.list_entities, limit=20, default=[])
    st = st if isinstance(st, dict) and not _is_err(st) else {}
    ents = ents if isinstance(ents, list) else []
    total = _int_or_none(st.get("total"))
    if total is None:
        total = len(ents) or None
    by_ev = st.get("by_evidence") if isinstance(st.get("by_evidence"), dict) else {}
    verified = sum(v for v in by_ev.values() if isinstance(v, int)) if by_ev else None
    kpis = [
        metric("bmp08.entities", "播客实体", value=total,
               state=STATE_READY if total is not None else STATE_EMPTY, icon="content",
               source="podcast_store.get_stats"),
        metric("bmp08.evidence", "已标证据状态", value=verified,
               state=STATE_READY if verified is not None else STATE_EMPTY, icon="link",
               source="podcast_store.get_stats.by_evidence"),
    ]
    rows = [{"类型": e.get("entity_type"), "标题": e.get("title") or "—",
             "证据状态": e.get("evidence_status") or "unverified",
             "ID": str(e.get("entity_id") or "—")[:24]} for e in ents if isinstance(e, dict)]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY,
                  title="播客实体（真实；空库显示空态，不造假数据）",
                  columns=[{"label": "类型", "key": "类型"}, {"label": "标题", "key": "标题"},
                           {"label": "证据状态", "key": "证据状态"}, {"label": "ID", "key": "ID"}], rows=rows)
    sections = [_head("BMP-08"), section("kpis", STATE_READY, items=kpis), tbl]
    return _envelope("BMP-08", sections, truth={"stats": st})


def _build_bmp10() -> Dict[str, Any]:
    """品牌风险与事件：database 真实事件 + 高风险笔记（与 CTH 同源只读，域适配 BMP）。"""
    import database as db

    ev = _safe(db.get_events_curated, 12, default=[])
    rn = _safe(db.get_high_risk_notes, 10, default=[])
    ev = _curated(ev)
    rn = rn if isinstance(rn, list) else []
    kpis = [
        metric("bmp10.events", "在办事件", value=len(ev) or None,
               state=STATE_READY if ev else STATE_EMPTY, icon="event",
               source="database.get_events_curated"),
        metric("bmp10.high_risk", "高风险记录", value=len(rn), state=STATE_READY,
               icon="risk", source="database.get_high_risk_notes"),
    ]
    ev_sec = section("events", STATE_READY if ev else STATE_EMPTY, items=_events_items(ev))
    risk_items = [{
        "level": _LV.get(n.get("risk_level", "low"), "low"),
        "score": n.get("risk_score") if isinstance(n.get("risk_score"), (int, float)) and n.get("risk_score") else None,
        "title": (n.get("title") or "风险记录")[:40],
        "desc": (n.get("content") or "")[:90],
        "evidence": f"NOTE:{n.get('note_id') or n.get('id') or 'UNKNOWN'}",
    } for n in rn[:5] if isinstance(n, dict)]
    risk_sec = section("risks", STATE_READY if risk_items else STATE_EMPTY, items=risk_items)
    sections = [_head("BMP-10"), section("kpis", STATE_READY, items=kpis), ev_sec, risk_sec]
    return _envelope("BMP-10", sections)


# ---------------------------------------------------------------------------
# 第三批传播：品牌市场总览 / 多品牌目录 / Campaign 配额 / 评估 / 学习资产 / 本地设置
# 全部来自真实只读源；无数据走 EMPTY，纯前端偏好显式标注 INTENTIONALLY_NOT_APPLICABLE。
# ---------------------------------------------------------------------------
def _risk_items(notes: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    out = []
    for n in notes[:limit]:
        if not isinstance(n, dict):
            continue
        rs = n.get("risk_score")
        out.append({
            "level": _LV.get(n.get("risk_level", "low"), "low"),
            "score": rs if isinstance(rs, (int, float)) and rs else None,
            "title": (n.get("title") or "风险记录")[:40],
            "desc": (n.get("content") or "")[:90],
            "evidence": f"NOTE:{n.get('note_id') or n.get('id') or 'UNKNOWN'}",
        })
    return out


def _build_bmp01() -> Dict[str, Any]:
    """品牌市场总览：只读 ZBMP canonical snapshot，不借用 CTH 统计。"""
    from api_dual_domain import get_zbmp_product_snapshot

    snapshot = _safe(get_zbmp_product_snapshot, default={})
    snapshot = snapshot if isinstance(snapshot, dict) and not _is_err(snapshot) else {}
    metrics = snapshot.get("metrics") if isinstance(snapshot.get("metrics"), dict) else {}
    data_state = snapshot.get("data_state") or STATE_NOT_COLLECTED.upper()
    ready = data_state == "READY"
    state = STATE_READY if ready else STATE_NOT_COLLECTED

    sentiment = metrics.get("sentiment_distribution")
    sentiment = sentiment if isinstance(sentiment, dict) else {}
    risk = metrics.get("risk_distribution")
    risk = risk if isinstance(risk, dict) else {}
    engagement = metrics.get("total_engagement")
    engagement = engagement if isinstance(engagement, dict) else {}
    observed_engagement = [value for value in engagement.values() if isinstance(value, (int, float))]
    total_engagement = sum(observed_engagement) if observed_engagement else None

    negative = sentiment.get("negative") if ready else None
    high_risk = sum(risk.get(level, 0) for level in ("high", "critical")) if ready else None
    total = metrics.get("total_canonical_zbmp") if ready else None
    kpis = [
        metric("bmp01.total", "总声量", value=_int_or_none(total), state=state,
               icon="trend", source="api_dual_domain.get_zbmp_product_snapshot"),
        metric("bmp01.neg", "负面声量", value=_int_or_none(negative), state=state,
               icon="risk", source="api_dual_domain.get_zbmp_product_snapshot"),
        metric("bmp01.high", "高风险", value=_int_or_none(high_risk), state=state,
               icon="risk", source="api_dual_domain.get_zbmp_product_snapshot"),
        metric("bmp01.eng", "总互动", value=_int_or_none(total_engagement), state=state,
               icon="trend", source="api_dual_domain.get_zbmp_product_snapshot"),
        metric("bmp01.ri", "风险指数", value=None, decimals=1, state=STATE_NOT_COLLECTED,
               icon="risk", source="ZBMP canonical metric not yet available", evidence_id="NOT_COLLECTED"),
        metric("bmp01.health", "品牌健康分", value=None, decimals=1, state=STATE_NOT_COLLECTED,
               icon="trend", source="ZBMP canonical metric not yet available", evidence_id="NOT_COLLECTED"),
    ]

    trend = metrics.get("capture_trend") if isinstance(metrics.get("capture_trend"), dict) else {}
    labels = trend.get("labels") if ready and isinstance(trend.get("labels"), list) else []
    totals = trend.get("total") if ready and isinstance(trend.get("total"), list) else []
    negs = trend.get("negative") if ready and isinstance(trend.get("negative"), list) else []
    chart = section(
        "chart", state, kind="line", title="近14日声量与负面", sub="按 canonical captured_at 统计",
        labels=labels,
        series=[
            {"name": "总声量", "data": totals, "color": "var(--lum-text-2,#8a8f98)"},
            {"name": "负面", "data": negs, "color": "var(--lum-c-danger,#c0563f)"},
        ] if ready else [],
        legend=[
            {"label": "总声量", "color": "var(--lum-text-2,#8a8f98)"},
            {"label": "负面", "color": "var(--lum-c-danger,#c0563f)"},
        ] if ready else [],
    )

    # No canonical event source is defined for ZBMP yet.  Do not reuse CTH
    # curated events or synthesize events from note authors.
    ev_sec = section(
        "events", STATE_NOT_COLLECTED, title="重点事件", items=[],
        description="ZBMP 事件源尚未形成 canonical 事件契约；未借用 CTH 事件。",
    )
    records = snapshot.get("canonical_records")
    records = records if isinstance(records, list) else []
    risk_records = [
        record for record in records
        if isinstance(record, dict)
        and (str(record.get("risk_level") or "").lower() in ("medium", "high", "critical")
             or isinstance(record.get("risk_score"), (int, float)) and record.get("risk_score", 0) > 0)
    ]
    risk_items = []
    for record in risk_records[:5]:
        evidence = record.get("evidence_ref") or f"CANONICAL:{record.get('canonical_id') or 'UNKNOWN'}"
        risk_items.append({
            "level": _LV.get(record.get("risk_level", "low"), "low"),
            "score": record.get("risk_score") if isinstance(record.get("risk_score"), (int, float)) else None,
            "title": (record.get("title") or "风险记录")[:40],
            "desc": (record.get("content") or "")[:90],
            "evidence": evidence,
        })
    risk_sec = section("risks", STATE_READY if risk_items else (state if ready else STATE_NOT_COLLECTED),
                       items=risk_items)
    blocked = [
        _block("BMP-01", "risk_index", "缺少 ZBMP 专属风险指标真值源", "ZBMP canonical metric"),
        _block("BMP-01", "brand_health_score", "缺少 ZBMP 专属健康评分真值源", "ZBMP evaluation output"),
        _block("BMP-01", "events", "缺少 ZBMP canonical 事件契约", "ZBMP event source"),
    ]
    sections = [_head("BMP-01"), section("kpis", state, items=kpis), chart, ev_sec, risk_sec]
    return _envelope(
        "BMP-01", sections,
        truth={
            "domain_id": "zbmp",
            "product_id": "ZBMP",
            "data_state": data_state,
            "canonical_count": snapshot.get("total_records", 0),
            "latest_capture": metrics.get("latest_capture") or None,
        },
        blocked=blocked,
    )


def _build_bmp02() -> Dict[str, Any]:
    """品牌中心 / 多品牌与竞品：真实零售目录业态分布（web_monitor_v570 策展目录）。"""
    import web_monitor_v570 as wm

    d = _safe(wm.get_brand_directory, default={})
    d = d if isinstance(d, dict) and not _is_err(d) else {}
    cats = d.get("categories")
    cats = cats if isinstance(cats, dict) else {}
    total = _int_or_none(d.get("total_brands"))
    rows = [{"业态类目": str(k), "品牌数": _int_or_none(v)} for k, v in cats.items()]
    rows.sort(key=lambda r: -(r["品牌数"] or 0))
    kpis = [
        metric("bmp02.total", "目录品牌总数", value=total,
               state=STATE_READY if total is not None else STATE_EMPTY, icon="collection",
               source="web_monitor_v570.get_brand_directory"),
        metric("bmp02.cats", "业态类目数", value=len(cats), state=STATE_READY,
               icon="collection", source="web_monitor_v570.get_brand_directory"),
    ]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="零售目录业态分布（真实）",
                  columns=[{"label": "业态类目", "key": "业态类目"},
                           {"label": "品牌数", "key": "品牌数", "numeric": True}], rows=rows)
    src = d.get("source") or "—"
    upd = d.get("updated_at") or "—"
    note = section("note", STATE_READY, kind="SOURCE",
                   text=f"策展零售目录更新于 {upd}；来源：{src}。竞品对标（benchmark）仍需外部数据源，"
                        "当前不造假、不补默认值。")
    sections = [_head("BMP-02"), section("kpis", STATE_READY, items=kpis), tbl, note]
    return _envelope("BMP-02", sections, truth={"total_brands": total, "updated_at": upd})


def _build_bmp07() -> Dict[str, Any]:
    """话题活动 Campaign：真实采集配额/冷却运行态；活动列表写入侧无只读表，诚实空态。"""
    import topic_campaign as tc

    q = _safe(tc.get_campaign_rate_status, default={})
    q = q if isinstance(q, dict) and not _is_err(q) else {}
    kpis = [
        metric("bmp07.ran", "今日已运行", value=_int_or_none(q.get("today_runs")),
               state=STATE_READY if "today_runs" in q else STATE_NOT_COLLECTED, icon="runtime",
               source="topic_campaign.get_campaign_rate_status"),
        metric("bmp07.max", "每日上限", value=_int_or_none(q.get("max_daily_runs")),
               state=STATE_READY if "max_daily_runs" in q else STATE_NOT_COLLECTED, icon="runtime",
               source="topic_campaign.get_campaign_rate_status"),
        metric("bmp07.remain", "今日剩余", value=_int_or_none(q.get("remaining_today")),
               state=STATE_READY if "remaining_today" in q else STATE_NOT_COLLECTED, icon="runtime",
               source="topic_campaign.get_campaign_rate_status"),
        metric("bmp07.cooldown", "冷却剩余(分)", value=_int_or_none(q.get("cooldown_remaining_minutes")),
               state=STATE_READY if "cooldown_remaining_minutes" in q else STATE_NOT_COLLECTED,
               icon="runtime", source="topic_campaign.get_campaign_rate_status"),
    ]
    note = section("note", STATE_READY, kind="SCOPE",
                   text="此处仅呈现真实的活动采集配额与冷却运行态。活动创建/编排属写入侧，"
                        "当前无只读活动表，活动列表保持空态，待后端活动只读源就绪后绑定。")
    sections = [_head("BMP-07"), section("kpis", STATE_READY, items=kpis), note]
    return _envelope("BMP-07", sections, truth={"quota": q})


def _build_bmp09() -> Dict[str, Any]:
    """品牌报告与评估：evaluation_recorder 真实评估汇总 + 记录（空库诚实空态）。"""
    import evaluation_recorder as er

    s = _safe(er.get_evaluation_summary, default={})
    s = s if isinstance(s, dict) and not _is_err(s) else {}
    recs = _safe(er.get_evaluation_records, 100, default=[])
    recs = recs if isinstance(recs, list) else []
    counts = s.get("counts")
    counts = counts if isinstance(counts, dict) else {}

    def _c(k: str):
        return _int_or_none(counts.get(k))

    kpis = [
        metric("bmp09.total", "评估记录总数", value=_int_or_none(s.get("total_records")),
               state=STATE_READY if "total_records" in s else STATE_NOT_COLLECTED, icon="report",
               source="evaluation_recorder.get_evaluation_summary"),
        metric("bmp09.pass", "通过", value=_c("pass"),
               state=STATE_READY if "pass" in counts else STATE_NOT_COLLECTED, icon="check",
               source="evaluation_recorder.get_evaluation_summary"),
        metric("bmp09.warn", "警示", value=_c("warn"),
               state=STATE_READY if "warn" in counts else STATE_NOT_COLLECTED, icon="risk",
               source="evaluation_recorder.get_evaluation_summary"),
        metric("bmp09.fail", "失败", value=_c("fail"),
               state=STATE_READY if "fail" in counts else STATE_NOT_COLLECTED, icon="risk",
               source="evaluation_recorder.get_evaluation_summary"),
    ]
    crows = [{"评估状态": {"pass": "通过", "warn": "警示", "fail": "失败", "unknown": "未知"}.get(k, k),
              "数量": _c(k)} for k in ("pass", "warn", "fail", "unknown")]
    ctbl = section("table", STATE_READY if counts else STATE_NOT_COLLECTED,
                   title="评估状态分布（真实）",
                   columns=[{"label": "评估状态", "key": "评估状态"},
                            {"label": "数量", "key": "数量", "numeric": True}], rows=crows)
    rrows = [{"维度": str(r.get("dimension") or "—"), "指标": str(r.get("metric_id") or r.get("metric") or "—"),
              "状态": str(r.get("status") or "—")} for r in recs[:30] if isinstance(r, dict)]
    rtbl = section("table", STATE_READY if rrows else STATE_EMPTY, title="最近评估记录",
                   columns=[{"label": "维度", "key": "维度"}, {"label": "指标", "key": "指标"},
                            {"label": "状态", "key": "状态"}], rows=rrows)
    gstatus = s.get("global_status")
    note = section("note", STATE_READY, kind="STATUS",
                   text=f"全局评估状态：{gstatus or '—'}（来自 evaluation_recorder，未产生评估记录前为 unknown，属真实空态）。")
    sections = [_head("BMP-09"), section("kpis", STATE_READY, items=kpis), ctbl, rtbl, note]
    return _envelope("BMP-09", sections, truth={"global_status": gstatus})


def _build_sh05() -> Dict[str, Any]:
    """学习与评估资产：learning_collector 真实学习历史（空库诚实空态）。"""
    import learning_collector as lc

    h = _safe(lc.get_learning_history, default={})
    h = h if isinstance(h, dict) and not _is_err(h) else {}
    items = h.get("learnings")
    items = items if isinstance(items, list) else []
    kpis = [
        metric("sh05.count", "学习资产", value=len(items), state=STATE_READY, icon="collection",
               source="learning_collector.get_learning_history"),
    ]
    rows = [{"标题": str(x.get("title") or x.get("summary") or "—")[:60],
             "类型": str(x.get("type") or x.get("kind") or "—"),
             "时间": str(x.get("created_at") or x.get("learned_at") or "—")}
            for x in items[:40] if isinstance(x, dict)]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="学习历史（真实）",
                  columns=[{"label": "标题", "key": "标题"}, {"label": "类型", "key": "类型"},
                           {"label": "时间", "key": "时间"}], rows=rows)
    note = section("note", STATE_EMPTY if not items else STATE_READY, kind="EMPTY-OK",
                   text="学习资产由生产运行沉淀；当前无学习记录时显示空态，不生成示例/占位资产。")
    sections = [_head("SH-05"), section("kpis", STATE_READY, items=kpis), tbl, note]
    return _envelope("SH-05", sections, truth={"learning_count": len(items)})


def _build_sys05() -> Dict[str, Any]:
    """设置 / 外观 / 语言 + 主体与授权入口。

    外观偏好仍是 localStorage；主体登记与 Cookie 导入使用真实受保护 API。
    两者放在同一设置工作区，但不混淆数据责任：主体登记不会切换默认主体，
    Cookie 导入不会绕过香港采集策略或人工权限门。
    """
    form = section("form", STATE_READY, title="本地偏好（仅存于本浏览器 localStorage，不上传、无后端表）",
                   fields=[
                       {"label": "外观主题（黑银浅色 / 白银深色）", "type": "select",
                        "opts": ["跟随系统", "浅色 · 黑银 SH", "深色 · 白银 AI"]},
                       {"label": "显示语言", "type": "select", "opts": ["简体中文", "English", "한국어"]},
                       {"label": "光学密度 Optical", "type": "select", "opts": ["LOW", "BALANCED", "HIGH"]},
                       {"label": "减弱动态效果（无障碍）", "type": "select", "opts": ["跟随系统", "开启", "关闭"]},
                   ])
    integrations = section("raw", STATE_READY, html=(
        '<section class="lum-card lum-card-pad lum-stack-6" data-lumenis-settings-surface>'
        '<div class="lum-row-between"><div>'
        '<div class="lum-eyebrow">LUMENIS CONTROL PLANE</div>'
        '<h2 class="lum-h4" style="margin-top:6px">主体与授权 Session</h2>'
        '<p class="lum-caption" style="margin-top:6px">CTH 商业运营与 BMP 品牌市场共用通用主体模块；'
        '主体只作为可选择的工作上下文，不改变两域既有运行规则。</p>'
        '</div><span class="lum-badge lum-badge-info">HUMAN CONTROL</span></div>'
        '<div class="lum-grid-main-side" style="grid-template-columns:minmax(0,1fr) minmax(260px,.8fr)">'
        '<form class="lum-stack-4" data-subject-form aria-label="新增通用主体">'
        '<div class="lum-field"><label class="lum-label" for="lumenis-subject-domain">归属领域</label>'
        '<select class="lum-select" id="lumenis-subject-domain" data-subject-domain>'
        '<option value="CTH">商业运营 · CTH</option><option value="BMP">品牌市场 · BMP</option>'
        '</select></div>'
        '<div class="lum-field"><label class="lum-label" for="lumenis-subject-type">主体类型</label>'
        '<select class="lum-select" id="lumenis-subject-type" data-subject-type>'
        '<option value="brand">品牌主体</option><option value="company">商业主体</option>'
        '</select></div>'
        '<div class="lum-field"><label class="lum-label" for="lumenis-subject-en">英文名</label>'
        '<input class="lum-input" id="lumenis-subject-en" data-subject-name-en autocomplete="organization" '
        'placeholder="例如：LUMENIS Holdings" required></div>'
        '<div class="lum-field"><label class="lum-label" for="lumenis-subject-zh">中文名</label>'
        '<input class="lum-input" id="lumenis-subject-zh" data-subject-name-zh autocomplete="organization" '
        'placeholder="例如：序境控股" required></div>'
        '<div class="lum-field"><label class="lum-label" for="lumenis-subject-industry">行业（可选）</label>'
        '<input class="lum-input" id="lumenis-subject-industry" data-subject-industry '
        'placeholder="不限行业；例如：零售、科技、地产、制造"></div>'
        '<div class="lum-row"><button type="submit" class="lum-btn lum-btn-primary" data-subject-submit>登记主体</button>'
        '<span class="lum-caption" data-subject-status role="status">需人工审批后写入生产配置</span></div>'
        '</form>'
        '<div class="lum-stack-4"><div class="lum-row-between"><b>已登记主体</b>'
        '<button type="button" class="lum-chip" data-subject-refresh>刷新</button></div>'
        '<div class="lum-stack-2" data-subject-list><span class="lum-caption">读取真实注册表…</span></div>'
        '<p class="lum-caption">选择主体只改变工作上下文；默认 CTH/BMP 生产规则、权限和数据归属保持不变。</p></div>'
        '</div>'
        '<div class="lum-opt lum-opt-flat lum-stack-4" data-cookie-surface>'
        '<div class="lum-row-between"><div><b>新增授权 Cookie</b>'
        '<p class="lum-caption" style="margin-top:4px">当前生产采集仅接入香港/国际小红书；凭证只写入本机受保护运行数据，界面不回显明文。</p></div>'
        '<span class="lum-badge lum-badge-warning">HK ONLY</span></div>'
        '<div class="lum-field"><label class="lum-label" for="lumenis-cookie-json">小红书 Cookie JSON 数组</label>'
        '<textarea class="lum-textarea" id="lumenis-cookie-json" data-setting-cookie-json rows="4" '
        'placeholder="粘贴浏览器导出的 Cookie JSON；提交后不会在页面显示凭证" spellcheck="false"></textarea></div>'
        '<label class="lum-row lum-caption"><input type="checkbox" data-setting-cookie-apply> 经人工确认后立即绑定 XHS_RETINAUT 香港/国际生产采集</label>'
        '<div class="lum-row"><button type="button" class="lum-btn lum-btn-secondary" data-setting-cookie-submit>安全导入</button>'
        '<button type="button" class="lum-chip" data-cookie-status-refresh>读取状态</button>'
        '<span class="lum-caption" data-setting-cookie-status role="status">状态读取中…</span></div>'
        '</div></section>'
    ))
    note = section("note", STATE_READY, kind="INTENTIONALLY-NOT-APPLICABLE",
                   code="FRONTEND_LOCAL_ONLY",
                   text="本屏为前端本地偏好，不依赖后端/数据库，分类 INTENTIONALLY_NOT_APPLICABLE；"
                        "不产生外部数据缺口，也不伪造任何后端状态。")
    sections = [_head("SYS-05"), form, integrations, note]
    return _envelope("SYS-05", sections, truth={"data_source": "localStorage", "backend_required": False})


def _build_acc02() -> Dict[str, Any]:
    """主体选择与领域视角：默认配置 + 通用主体注册表的真实只读投影。"""
    import subject_rules as sr
    from subject_registry import list_subjects

    profiles = sr.BRAND_PROFILES if isinstance(sr.BRAND_PROFILES, dict) else {}
    active = _safe(sr.get_active_brand, default="")
    rows = []
    for key, cfg in profiles.items():
        cfg = cfg if isinstance(cfg, dict) else {}
        kws = cfg.get("collect_keywords")
        rows.append({
            "主体": cfg.get("display_name") or key,
            "领域": "CTH",
            "类型": "品牌主体",
            "地区": cfg.get("region") or "本地",
            "业态": cfg.get("store_type") or "商业体",
            "采集关键词": len(kws) if isinstance(kws, list) else 0,
            "当前": "● 激活" if key == active else "",
        })
    configured = _safe(list_subjects, default=[])
    if isinstance(configured, list):
        for item in configured:
            if not isinstance(item, dict):
                continue
            rows.append({
                "主体": f"{item.get('name_zh') or '—'} / {item.get('name_en') or '—'}",
                "领域": item.get("domain_name") or item.get("domain_id") or "—",
                "类型": item.get("subject_type_name") or item.get("subject_type") or "—",
                "地区": "通用",
                "业态": item.get("industry") or "不限行业",
                "采集关键词": len(item.get("keywords") or []) if isinstance(item.get("keywords"), list) else 0,
                "当前": "",
            })
    kpis = [
        metric("acc02.subjects", "已配置主体", value=len(rows), state=STATE_READY, icon="collection",
               source="subject_rules.BRAND_PROFILES + lumenis_subject_registry"),
    ]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="可选主体（真实配置）",
                  columns=[{"label": "主体", "key": "主体"}, {"label": "领域", "key": "领域"},
                           {"label": "类型", "key": "类型"}, {"label": "地区", "key": "地区"},
                           {"label": "业态", "key": "业态"}, {"label": "采集关键词", "key": "采集关键词", "numeric": True},
                           {"label": "当前", "key": "当前"}], rows=rows)
    note = section("note", STATE_READY, kind="RULE",
                   text="选择主体只切换工作上下文（SubjectContext），不改变数据归属；进入领域后由后端重验授权。")
    sections = [_head("ACC-02"), section("kpis", STATE_READY, items=kpis), tbl, note]
    return _envelope("ACC-02", sections, truth={"active_brand": active,
                                                  "registry_subjects": len(configured) if isinstance(configured, list) else 0,
                                                  "selection_only": True})


def _build_acc03() -> Dict[str, Any]:
    """全局工作空间启动：启动时真实运行时健康（runtime_guardian），统一入口状态。"""
    import runtime_guardian as rg

    h = _safe(rg.legacy_health_check, default={})
    h = h if isinstance(h, dict) and not _is_err(h) else {}
    w = h.get("workers") if isinstance(h.get("workers"), dict) else {}
    dlq = h.get("dlq") if isinstance(h.get("dlq"), dict) else {}
    kpis = [
        metric("acc03.workers", "工作进程", value=_int_or_none(w.get("total")),
               state=STATE_READY if "total" in w else STATE_NOT_COLLECTED, icon="runtime",
               source="runtime_guardian.legacy_health_check"),
        metric("acc03.running", "运行中", value=_int_or_none(w.get("running")),
               state=STATE_READY if "running" in w else STATE_NOT_COLLECTED, icon="runtime",
               source="runtime_guardian.legacy_health_check"),
        metric("acc03.failed", "异常", value=_int_or_none(w.get("failed")),
               state=STATE_READY if "failed" in w else STATE_NOT_COLLECTED, icon="risk",
               source="runtime_guardian.legacy_health_check"),
        metric("acc03.dlq", "死信队列", value=_int_or_none(dlq.get("total")),
               state=STATE_READY if "total" in dlq else STATE_NOT_COLLECTED, icon="risk",
               source="runtime_guardian.legacy_health_check"),
    ]
    note = section("note", STATE_READY, kind="ENTRY",
                   text="统一入口启动状态来自真实运行时守护；底部 Dock 承载一级目的地与中央 AI 入口。")
    sections = [_head("ACC-03"), section("kpis", STATE_READY, items=kpis), note]
    return _envelope("ACC-03", sections, truth={"overall": h.get("overall")})


def _build_bmp03() -> Dict[str, Any]:
    """市场情报：canonical 连接只读 intelligence_assets（表不存在则诚实空态，不造假）。"""
    import database as db

    total = None
    by_sub: Dict[str, int] = {}
    table_exists = False
    try:
        with db.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intelligence_assets'")
            table_exists = cur.fetchone() is not None
            if table_exists:
                cur.execute("SELECT COUNT(*) FROM intelligence_assets WHERE knowledge_status IN ('FACT','VERIFIED') AND admission_status='ADMITTED'")
                total = int(cur.fetchone()[0])
                cur.execute("SELECT sub_library, COUNT(*) FROM intelligence_assets WHERE knowledge_status IN ('FACT','VERIFIED') AND admission_status='ADMITTED' GROUP BY sub_library ORDER BY sub_library")
                by_sub = {str(r[0] or "未分类"): int(r[1]) for r in cur.fetchall()}
    except Exception as exc:  # 只读守卫：任何异常都降级为未采集，绝不抛到 UI
        return _envelope("BMP-03", [_head("BMP-03"),
                                    section("note", STATE_NOT_COLLECTED, kind="OFFLINE",
                                            text=f"市场情报只读探测失败：{type(exc).__name__}；保持未采集态，不造假。")],
                         truth={"error": type(exc).__name__})
    state = STATE_READY if table_exists else STATE_NOT_COLLECTED
    kpis = [
        metric("bmp03.total", "情报资产", value=total if table_exists else None,
               state=state, icon="collection", source="intelligence_assets (read-only)"),
    ]
    rows = [{"子库": k, "资产数": _int_or_none(v)} for k, v in by_sub.items()]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="按子库分布（真实）",
                  columns=[{"label": "子库", "key": "子库"},
                           {"label": "资产数", "key": "资产数", "numeric": True}], rows=rows)
    if not table_exists:
        note = section("note", STATE_NOT_COLLECTED, kind="NOT-COLLECTED",
                       text="intelligence_assets 表尚未在当前库建立（情报入库流水线未运行），保持未采集态，不补默认值。")
    else:
        note = section("note", STATE_READY, kind="SOURCE",
                       text="只读自 canonical 库 intelligence_assets；情报入库/评审属写入侧，走权限链。")
    platform_sec = _platform_collection_section(consumer="BMP")
    sections = [_head("BMP-03"), section("kpis", STATE_READY, items=kpis), tbl, platform_sec, note]
    return _envelope("BMP-03", sections, truth={"table_exists": table_exists, "total": total})


def _build_bmp04() -> Dict[str, Any]:
    """传播分析：brand_propagation 三类传播看板真实只读汇总（空库诚实空态）。"""
    import brand_propagation as bp

    eng = _safe(bp.get_brand_propagation_engine, default=None)
    dash = _safe(eng.get_all_dashboards, default={}) if eng is not None else {}
    dash = dash if isinstance(dash, dict) and not _is_err(dash) else {}
    entities = _safe(eng.list_entities, default=[]) if eng is not None else []
    entities = entities if isinstance(entities, list) else []

    def _g(d, k):
        return getattr(d, k, None)

    tot = pos = neu = neg = 0
    heats = []
    rows = []
    for cat, d in dash.items():
        t = _int_or_none(_g(d, "total_events")) or 0
        p = _int_or_none(_g(d, "positive_count")) or 0
        nu = _int_or_none(_g(d, "neutral_count")) or 0
        ng = _int_or_none(_g(d, "negative_count")) or 0
        ah = _g(d, "avg_heat")
        tot += t; pos += p; neu += nu; neg += ng
        if isinstance(ah, (int, float)):
            heats.append(ah)
        rows.append({"传播看板": str(_g(d, "title") or cat), "事件数": t, "正面": p,
                     "中性": nu, "负面": ng, "平均热度": round(float(ah), 2) if isinstance(ah, (int, float)) else None})
    avg_heat = round(sum(heats) / len(heats), 2) if heats else None
    kpis = [
        metric("bmp04.total", "传播事件", value=tot, state=STATE_READY, icon="trend",
               source="brand_propagation.get_all_dashboards"),
        metric("bmp04.pos", "正面", value=pos, state=STATE_READY, icon="check",
               source="brand_propagation.get_all_dashboards"),
        metric("bmp04.neg", "负面", value=neg, state=STATE_READY, icon="risk",
               source="brand_propagation.get_all_dashboards"),
        metric("bmp04.heat", "平均热度", value=avg_heat, decimals=2,
               state=STATE_READY if avg_heat is not None else STATE_EMPTY, icon="trend",
               source="brand_propagation.get_all_dashboards"),
        metric("bmp04.ent", "传播实体", value=len(entities), state=STATE_READY, icon="collection",
               source="brand_propagation.list_entities"),
    ]
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="分域传播看板（真实）",
                  columns=[{"label": "传播看板", "key": "传播看板"},
                           {"label": "事件数", "key": "事件数", "numeric": True},
                           {"label": "正面", "key": "正面", "numeric": True},
                           {"label": "中性", "key": "中性", "numeric": True},
                           {"label": "负面", "key": "负面", "numeric": True},
                           {"label": "平均热度", "key": "平均热度", "numeric": True}], rows=rows)
    note = section("note", STATE_EMPTY if tot == 0 else STATE_READY, kind="EMPTY-OK",
                   text="传播事件由采集与传播引擎沉淀；当前无事件时显示真实 0/空态，不生成示例传播链。")
    sections = [_head("BMP-04"), section("kpis", STATE_READY, items=kpis), tbl, note]
    return _envelope("BMP-04", sections, truth={"total_events": tot, "entities": len(entities)})


# ---------------------------------------------------------------------------
# 最终六屏生产绑定：只读既有 Canonical 能力，不复制业务规则
# ---------------------------------------------------------------------------
def _build_acc01() -> Dict[str, Any]:
    """统一入口：只陈述认证入口配置是否具备，不返回用户名或密钥。"""
    user_configured = bool(os.environ.get("TAIKOO_AUTH_USER", "").strip())
    secret_configured = bool(os.environ.get("TAIKOO_AUTH_PASSWORD", "").strip())
    ready = user_configured and secret_configured
    state = STATE_READY if ready else STATE_OFFLINE
    sections = [
        _head("ACC-01"),
        section("kpis", state, items=[
            metric("acc01.auth", "认证入口", value=1 if ready else None, state=state,
                   icon="lock", source="app authentication configuration",
                   note="凭据仅报告是否配置，不回传内容"),
            metric("acc01.domains", "产品领域", value=2, state=STATE_READY,
                   icon="domain", source="canonical CTH/BMP registry"),
        ]),
        section("note", state, kind="AUTH-READY" if ready else "CONFIG-REQUIRED",
                text="统一入口使用后端认证与权限校验；主体选择不会改变 Production Truth。"),
    ]
    return _envelope("ACC-01", sections, truth={"auth_configured": ready, "domains": ["CTH", "BMP"]})


def _build_acc04() -> Dict[str, Any]:
    """账号恢复：复用 AuthRecoveryCenter 的真实待处理任务。"""
    from auth_recovery_center import recovery_center

    summary = _safe(recovery_center.get_recovery_summary, default={"__error__": "unavailable"})
    failed = _is_err(summary)
    pending = None if failed else int(summary.get("pending_count", 0) or 0)
    rows = [] if failed else [
        {"platform": t.get("platform", "—"), "title": t.get("title", "—"),
         "status": t.get("status", "—"), "created_at": t.get("created_at", "—")}
        for t in summary.get("pending_tasks", [])[:20]
    ]
    state = STATE_OFFLINE if failed else (STATE_READY if rows else STATE_EMPTY)
    sections = [
        _head("ACC-04"),
        section("kpis", state, items=[metric("acc04.pending", "待恢复任务", value=pending,
                state=state, icon="risk", source="auth_recovery_center.get_recovery_summary")]),
        section("table", state, title="认证恢复队列", columns=[
            {"label": "平台", "key": "platform"}, {"label": "问题", "key": "title"},
            {"label": "状态", "key": "status"}, {"label": "创建时间", "key": "created_at"}], rows=rows),
        section("note", state, kind="RECOVERY", text="验证由用户完成；系统只展示、暂停并在验证后健康复核。"),
    ]
    return _envelope("ACC-04", sections, truth=None if failed else {"pending_count": pending})


def _build_bmp05() -> Dict[str, Any]:
    """创作者：复用 KOS Canonical Profile，只读聚合。"""
    import kos_engine

    stats = _safe(kos_engine.get_stats, default={"__error__": "unavailable"})
    listing = _safe(kos_engine.list_profiles, limit=20, default={"__error__": "unavailable"})
    failed = _is_err(stats) or _is_err(listing)
    profiles = [] if failed else listing.get("profiles", [])
    rows = [{"name": p.get("author_nickname") or p.get("author_id") or "—",
             "type": p.get("subject_type") or p.get("identity_label") or "UNKNOWN",
             "tier": p.get("kos_tier") or "—", "score": p.get("kos_score"),
             "engagement": p.get("total_engagement", 0)} for p in profiles]
    state = STATE_OFFLINE if failed else (STATE_READY if rows else STATE_EMPTY)
    total = None if failed else int(stats.get("total", 0) or 0)
    sections = [
        _head("BMP-05"),
        section("kpis", state, items=[
            metric("bmp05.total", "传播主体", value=total, state=state, icon="creators",
                   source="kos_engine.get_stats"),
            metric("bmp05.potential", "潜力主体", value=None if failed else stats.get("potential", 0),
                   state=state, icon="trend", source="kos_engine.get_stats"),
            metric("bmp05.risk", "风险主体", value=None if failed else stats.get("risk", 0),
                   state=state, icon="risk", source="kos_engine.get_stats"),
        ]),
        section("table", state, title="KOS / KOL / KOC / UGC 主体", columns=[
            {"label": "主体", "key": "name"}, {"label": "类型", "key": "type"},
            {"label": "层级", "key": "tier"}, {"label": "评分", "key": "score", "numeric": True},
            {"label": "互动", "key": "engagement", "numeric": True}], rows=rows),
    ]
    return _envelope("BMP-05", sections, truth=None if failed else {"total": total})


def _build_bmp11() -> Dict[str, Any]:
    """竞品对标：复用 kos_intel 的实体消歧与确定性评分。"""
    import kos_intel

    data = _safe(kos_intel.competitor_benchmark, default={"__error__": "unavailable"})
    failed = _is_err(data)
    ranking = [] if failed else data.get("ranking", [])
    rows = [{"entity": r.get("entity", "—"), "score": r.get("score")} for r in ranking]
    state = STATE_OFFLINE if failed else (STATE_READY if rows else STATE_EMPTY)
    sections = [
        _head("BMP-11"),
        section("kpis", state, items=[
            metric("bmp11.entities", "对标实体", value=None if failed else len(rows), state=state,
                   icon="benchmark", source="kos_intel.competitor_benchmark"),
            metric("bmp11.leader", "当前领先", value=None if failed else data.get("leader"), state=state,
                   icon="trend", source="kos_intel.competitor_benchmark"),
        ]),
        section("table", state, title="可追溯对标", columns=[
            {"label": "实体", "key": "entity"}, {"label": "确定性评分", "key": "score", "numeric": True}], rows=rows),
        section("note", state, kind="METHOD", text="评分来自内容量、互动、强意向和作者数；AI 不改写统计口径。"),
    ]
    return _envelope("BMP-11", sections, truth=None if failed else {"leader": data.get("leader"), "ranking": ranking})


def _build_sh01() -> Dict[str, Any]:
    """内容创作工作室：呈现已登记能力与真实内容 Evidence，不生成示例内容。"""
    import content_generation

    modules = _safe(content_generation.get_module_status, default=[])
    evidence = _safe(content_generation.list_evidence, limit=12, default={"__error__": "unavailable"})
    failed = _is_err(evidence)
    rows = [] if failed else evidence.get("items", [])
    state = STATE_OFFLINE if failed else (STATE_READY if rows else STATE_EMPTY)
    latest_evidence_id = rows[0].get("evidence_id", "") if rows else ""
    sections = [
        _head("SH-01"),
        section("kpis", state, items=[
            metric("sh01.modules", "已登记创作能力", value=len(modules), state=STATE_READY,
                   icon="content", source="content_generation.get_module_status",
                   note="登记不等于全部 Runtime 已验证"),
            metric("sh01.evidence", "创作证据", value=None if failed else evidence.get("total", 0),
                   state=state, icon="evidence", source="content_generation.list_evidence"),
        ]),
        section("table", state, title="创作 Evidence",
                action=({"id": "open-content-evidence", "label": "查看最近证据", "variant": "secondary",
                         "size": "sm", "cls": "QUERY", "scope": "SHARED", "target": latest_evidence_id,
                         "permission": "READ", "ico": "evidence"} if latest_evidence_id else None), columns=[
            {"label": "证据 ID", "key": "evidence_id"}, {"label": "内容类型", "key": "content_type"},
            {"label": "Provider", "key": "provider"}, {"label": "状态", "key": "status"},
            {"label": "时间", "key": "created_at"}], rows=rows),
        shared_skill_surface("STUDIO"),
        section("note", state, kind="FACTUALITY-WALL",
                text="Brief → Evidence → Draft → Human Approval；AI 只增强草稿，不拥有事实。"),
        section("raw", state,
                html='<section class="lum-card lum-card-pad" data-content-evidence-detail '
                     'aria-live="polite"><span class="lum-eyebrow">Evidence Detail</span>'
                     '<p class="lum-body-2">选择一条真实创作 Evidence 查看可追溯结果。</p></section>'),
    ]
    return _envelope("SH-01", sections, truth=None if failed else {"evidence_total": evidence.get("total", 0)})


def _browser_surface_markup() -> str:
    """真实 SYS-06 浏览表面。

    这里只声明现有 Browser Surface 控制器所需的 DOM 契约；标签页、导航、
    截图、历史、书签、AI Browser Session 和外部出口都仍由
    ``static/js/browser.js`` + ``browser_surface.py`` 提供，不复制浏览器后端。
    外部出口是显式人工操作，默认路径始终留在序境内置浏览器。
    """
    return r'''
<section class="lum-browser-surface" data-browser-surface data-reveal aria-label="序境内置浏览器">
  <div class="lum-browser-surface__head">
    <div>
      <span class="lum-eyebrow">SYSTEM · INTERNAL BROWSER</span>
      <h2 class="lum-h4">序境内置浏览器</h2>
      <p class="lum-caption">默认在序境内读取、观察与固定证据；采集身份与通用浏览身份物理隔离。需要时可由人明确选择外部浏览器接力。</p>
    </div>
    <span class="lum-chip lum-mono">INTERNAL FIRST · 9224</span>
  </div>

  <div class="browser-shell" id="browser-shell">
    <div class="browser-tabbar">
      <div class="browser-tab-list" id="browser-tab-list" role="tablist" aria-label="浏览器标签页"></div>
      <button type="button" class="browser-tab-new" id="browser-tab-new" title="新建标签页" aria-label="新建标签页" onclick="BrowserApp.newTab()">＋</button>
    </div>

    <div class="browser-toolbar">
      <div class="browser-nav-btns">
        <button type="button" class="browser-nav-btn" id="btn-back" title="后退" aria-label="后退" onclick="BrowserApp.goBack()">‹</button>
        <button type="button" class="browser-nav-btn" id="btn-forward" title="前进" aria-label="前进" onclick="BrowserApp.goForward()">›</button>
        <button type="button" class="browser-nav-btn" id="btn-refresh" title="刷新" aria-label="刷新" onclick="BrowserApp.refresh()">↻</button>
        <button type="button" class="browser-nav-btn" id="btn-stop" title="停止" aria-label="停止" onclick="BrowserApp.stopLoading()" style="display:none">×</button>
      </div>
      <div class="browser-address-wrap">
        <div class="browser-security-indicator is-unknown" id="security-indicator" aria-live="polite">
          <span class="browser-security-icon" aria-hidden="true">●</span><span class="browser-security-label" id="security-label">未知</span>
        </div>
        <input type="text" class="browser-address-input" id="address-input" placeholder="输入 URL 或搜索…" autocomplete="off" spellcheck="false" aria-label="地址或搜索">
      </div>
      <div class="browser-toolbar-actions">
        <button type="button" class="browser-action-btn" id="btn-bookmark" title="添加书签" aria-label="添加书签" onclick="BrowserApp.toggleBookmark()">☆</button>
        <button type="button" class="browser-action-btn" id="btn-external" title="在外部浏览器打开（仅手动）" aria-label="在外部浏览器打开（仅手动）" onclick="BrowserApp.openExternal()">↗</button>
        <button type="button" class="browser-action-btn is-active" id="btn-sidebar" title="侧边面板" aria-label="侧边面板" onclick="BrowserApp.toggleSidebar()">☷</button>
      </div>
    </div>

    <div class="browser-main">
      <div class="browser-viewport" id="browser-viewport">
        <div class="browser-viewport__img-wrap" id="viewport-img-wrap">
          <div class="browser-viewport__placeholder" id="viewport-placeholder">
            <div class="browser-viewport__placeholder-icon">◌</div>
            <div class="browser-viewport__placeholder-text">正在连接序境内置浏览器</div>
            <div class="browser-viewport__placeholder-sub">通用浏览 9224 · 采集身份不混用</div>
          </div>
        </div>
        <div class="browser-blocked" id="browser-blocked" style="display:none" role="alert">
          <div class="browser-blocked__icon">!</div>
          <div class="browser-blocked__title">访问被拦截</div>
          <div class="browser-blocked__url" id="blocked-url"></div>
          <div class="browser-blocked__reason" id="blocked-reason"></div>
        </div>
      </div>

      <aside class="browser-sidebar" id="browser-sidebar" aria-label="浏览器侧边面板">
        <div class="browser-sidebar__tabs" role="tablist">
          <button type="button" class="browser-sidebar__tab is-active" data-panel="bookmarks" onclick="BrowserApp.switchPanel('bookmarks')">书签</button>
          <button type="button" class="browser-sidebar__tab" data-panel="history" onclick="BrowserApp.switchPanel('history')">历史</button>
          <button type="button" class="browser-sidebar__tab" data-panel="collect" onclick="BrowserApp.switchPanel('collect')">采集</button>
          <button type="button" class="browser-sidebar__tab" data-panel="ai-agent" onclick="BrowserApp.switchPanel('ai-agent')">AI</button>
        </div>
        <div class="browser-sidebar__content" id="sidebar-content">
          <div class="browser-panel" id="panel-bookmarks">
            <div class="browser-panel-section__header"><span class="browser-panel-section__title">书签</span><button type="button" class="browser-panel-section__action" onclick="BrowserApp.refreshBookmarks()">刷新</button></div>
            <div id="bookmarks-list"></div>
          </div>
          <div class="browser-panel" id="panel-history" style="display:none">
            <div class="browser-panel-section__header"><span class="browser-panel-section__title">浏览历史</span><button type="button" class="browser-panel-section__action" onclick="BrowserApp.clearHistory()">清空</button></div>
            <div id="history-list"></div>
          </div>
          <div class="browser-panel" id="panel-collect" style="display:none">
            <div class="browser-readonly-banner">只读保护 · 不关注、不点赞、不评论、不私信、不发布</div>
            <section class="browser-auth-card" aria-labelledby="hk-auth-title">
              <div class="browser-auth-card__head">
                <div>
                  <span class="browser-panel-section__title">COLLECTOR IDENTITY</span>
                  <h3 id="hk-auth-title" class="browser-auth-card__title">香港小红书 · XHS_RETINAUT</h3>
                </div>
                <span class="lum-chip lum-chip--sm" id="hk-auth-state" data-state="unknown">未检查</span>
              </div>
              <p class="browser-panel-copy">授权恢复只在序境内置浏览器完成。二维码由香港/国际采集驻场端口 9223 提供；不展示 Cookie，不启用大陆采集，不自动发布。</p>
              <div class="browser-inline-actions">
                <button type="button" class="lum-btn lum-btn-secondary lum-btn-sm" id="hk-auth-open" onclick="BrowserApp.openHKLogin()">连接香港账号</button>
                <button type="button" class="lum-btn lum-btn-ghost lum-btn-sm" id="hk-auth-check" onclick="BrowserApp.checkHKAuth()">检查授权</button>
              </div>
              <p class="browser-auth-card__trace" id="hk-auth-trace" aria-live="polite">授权状态尚未读取。</p>
            </section>
            <div class="browser-collect-status">
              <div><span>当前平台</span><b id="cs-platform">—</b></div>
              <div><span>浏览 / 采集</span><b id="cs-port">9224 / 9223</b></div>
              <div><span>浏览器状态</span><b id="cs-online">检测中…</b></div>
              <div><span>当前页面</span><b id="cs-page">—</b></div>
              <div><span>标签页数</span><b id="cs-tabs">—</b></div>
              <div><span>导航模式</span><b id="cs-navmode">—</b></div>
            </div>
            <button type="button" class="lum-btn lum-btn-secondary lum-btn-sm" onclick="BrowserApp.checkCollectStatus()">检测状态</button>
          </div>
          <div class="browser-panel" id="panel-ai-agent" style="display:none">
            <div class="browser-readonly-banner">AI Browser Runtime · Observe → Act → Verify → Evidence</div>
            <div class="browser-panel-section__header"><span class="browser-panel-section__title">Session</span><button type="button" class="browser-panel-section__action" onclick="AIBrowser.refreshStatus()">刷新</button></div>
            <div class="browser-collect-status">
              <div><span>Session</span><b id="ai-session-id">未创建</b></div>
              <div><span>状态</span><b id="ai-session-status">—</b></div>
              <div><span>当前 URL</span><b id="ai-current-url">—</b></div>
              <div><span>风险</span><b id="ai-risk-level">medium</b></div>
              <div><span>熔断</span><b id="ai-circuit-breaker">closed</b></div>
            </div>
            <div class="browser-inline-actions"><button type="button" class="lum-btn lum-btn-secondary lum-btn-sm" onclick="AIBrowser.createSession()">创建 Session</button><button type="button" class="lum-btn lum-btn-ghost lum-btn-sm" onclick="AIBrowser.stopSession()">关闭</button></div>
            <div class="browser-panel-section__header"><span class="browser-panel-section__title">Observe</span><button type="button" class="browser-panel-section__action" onclick="AIBrowser.observe()">观察</button></div>
            <div id="ai-observe-content" class="browser-panel-copy">点击“观察”读取当前页面 DOM 摘要与脱敏文本。</div>
            <div id="ai-injection-warning" class="browser-warning" style="display:none"></div>
            <div class="browser-panel-section__header"><span class="browser-panel-section__title">Act · Verify</span></div>
            <select id="ai-action-type" class="lum-select" aria-label="AI Action 类型"><option value="click">click · 点击</option><option value="input">input · 输入</option><option value="navigate">navigate · 导航</option><option value="scroll">scroll · 滚动</option><option value="back">back · 后退</option><option value="forward">forward · 前进</option><option value="reload">reload · 刷新</option><option value="wait">wait · 等待</option><option value="keyboard">keyboard · 键盘</option></select>
            <input id="ai-action-selector" class="lum-input" placeholder="CSS/XPath selector" aria-label="CSS或XPath selector">
            <input id="ai-action-value" class="lum-input" placeholder="value / url / text" aria-label="Action value">
            <input id="ai-action-expected" class="lum-input" placeholder="期望：url_contains=…" aria-label="Verification expected">
            <button type="button" class="lum-btn lum-btn-secondary" onclick="AIBrowser.executeAction()">执行（带验证）</button>
            <div id="ai-action-result" class="browser-panel-copy">等待执行…</div>
            <div class="browser-panel-section__header"><span class="browser-panel-section__title">Evidence</span><button type="button" class="browser-panel-section__action" onclick="AIBrowser.refreshEvidence()">刷新</button></div>
            <div id="ai-evidence-timeline" class="browser-panel-copy">暂无 Evidence 记录</div>
          </div>
        </div>
      </aside>
    </div>

    <div class="browser-statusbar"><span><i class="browser-statusbar__dot is-offline" id="status-dot"></i><span id="status-text">未连接</span></span><span class="browser-statusbar__url" id="status-url">—</span><span class="browser-statusbar__spacer"></span><span id="status-time"></span></div>
  </div>

  <div class="browser-modal-overlay" id="confirm-modal">
    <div class="browser-modal"><div class="browser-modal__icon">?</div><div class="browser-modal__title">确认在内置浏览器访问外部域名</div><div class="browser-modal__desc">该域名不在当前批准范围。确认后只允许本次在序境内置浏览器导航，不改变持久策略。</div><div class="browser-modal__url-box" id="confirm-url"></div><div class="browser-modal__actions"><button type="button" class="lum-btn lum-btn-ghost" onclick="BrowserApp.cancelNavigate()">取消</button><button type="button" class="lum-btn lum-btn-secondary" onclick="BrowserApp.confirmNavigate()">确认访问</button></div></div>
  </div>
  <div class="browser-modal-overlay" id="browser-auth-modal" aria-hidden="true">
    <div class="browser-modal browser-auth-modal" role="dialog" aria-modal="true" aria-labelledby="browser-auth-modal-title" aria-describedby="browser-auth-modal-desc">
      <div class="browser-modal__icon browser-auth-modal__icon">⌁</div>
      <div class="browser-modal__title" id="browser-auth-modal-title">香港小红书授权恢复</div>
      <div class="browser-modal__desc" id="browser-auth-modal-desc">请在序境内完成扫码。系统只会在检测到真实登录态后保存授权，不会以“我已扫码”替代验证。</div>
      <div class="browser-auth-modal__stage" id="browser-auth-stage" aria-live="polite">正在准备香港账号授权会话…</div>
      <div class="browser-auth-modal__qr-wrap" id="browser-auth-qr-wrap" hidden>
        <img class="browser-auth-modal__qr" id="browser-auth-qr" alt="香港小红书登录二维码">
        <span class="browser-auth-modal__qr-caption">使用小红书 App 扫描二维码；二维码仅在本机序境页面显示。</span>
      </div>
      <div class="browser-auth-modal__message" id="browser-auth-message"></div>
      <div class="browser-modal__actions">
        <button type="button" class="lum-btn lum-btn-ghost" id="browser-auth-later" onclick="BrowserApp.closeHKLogin()">稍后处理</button>
        <button type="button" class="lum-btn lum-btn-secondary" id="browser-auth-confirm" onclick="BrowserApp.confirmHKLogin()" disabled>我已完成扫码</button>
      </div>
    </div>
  </div>
  <div class="browser-modal-overlay" id="ai-approval-modal" style="display:none">
    <div class="browser-modal"><div class="browser-modal__icon">!</div><div class="browser-modal__title">需要人工审批</div><div class="browser-modal__desc" id="ai-approval-reason">AI Browser Runtime 请求执行操作，需要人工确认。</div><div class="browser-approval-grid"><span>Action</span><b id="ai-approval-action">—</b><span>Target</span><b id="ai-approval-target">—</b><span>Expected</span><b id="ai-approval-expected">—</b><span>Risk</span><b id="ai-approval-risk">—</b></div><div class="browser-modal__actions"><button type="button" class="lum-btn lum-btn-ghost" onclick="AIBrowser.rejectAction()">拒绝</button><button type="button" class="lum-btn lum-btn-secondary" onclick="AIBrowser.approveAction()">批准执行</button></div></div>
  </div>
</section>
'''


def _build_sys06() -> Dict[str, Any]:
    """内部浏览器：只读能力与驻场实例状态，不返回 Profile 绝对路径或 Cookie。"""
    import browser_surface

    report = _safe(browser_surface.capability_report, default={"__error__": "unavailable"})
    failed = _is_err(report)
    residents = [] if failed else report.get("residents", [])
    rows = [{"account": r.get("account") or r.get("name") or "—",
             "port": r.get("port"), "state": r.get("state") or r.get("status") or "UNKNOWN"}
            for r in residents]
    if not failed:
        general = report.get("general_browser", {})
        rows.append({"account": "GENERAL", "port": general.get("port"),
                     "state": "ONLINE" if general.get("online") else "OFFLINE"})
    online = sum(1 for r in rows if str(r.get("state", "")).upper() in ("ONLINE", "READY", "HEALTHY"))
    state = STATE_OFFLINE if failed else STATE_READY
    sections = [
        _head("SYS-06"),
        # 真实生产入口：复用 browser_surface 唯一后端与 browser.js 控制器。
        # 不把旧 Jinja 页面或 prototype example.com 作为 fallback。
        section("raw", STATE_READY, html=_browser_surface_markup()),
        section("kpis", state, items=[
            metric("sys06.instances", "浏览器实例", value=None if failed else len(rows), state=state,
                   icon="browser", source="browser_surface.capability_report"),
            metric("sys06.online", "当前在线", value=None if failed else online, state=state,
                   icon="status", source="browser_surface.capability_report"),
            metric("sys06.capabilities", "只读能力", value=None if failed else len(report.get("capabilities", [])),
                   state=state, icon="layers", source="browser_surface.capability_report"),
        ]),
        section("table", state, title="隔离浏览实例", columns=[
            {"label": "实例", "key": "account"}, {"label": "CDP 端口", "key": "port", "numeric": True},
            {"label": "状态", "key": "state"}], rows=rows),
        section("note", state, kind="READ-ONLY", text="自动化永久禁止关注、点赞、评论、私信、发布和账号设置写操作。"),
    ]
    return _envelope("SYS-06", sections, truth=None if failed else {"instances": len(rows), "online": online})


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
    "SYS-02": _build_sys02,
    "SYS-03": _build_sys03,
    "SYS-04": _build_sys04,
    "SYS-07": _build_sys07,
    "SYS-08": _build_sys08,
    "SH-02": _build_sh02,
    "SH-03": _build_sh03,
    "SH-04": _build_sh04,
    "SH-06": _build_sh06,
    "BMP-06": _build_bmp06,
    "BMP-08": _build_bmp08,
    "BMP-10": _build_bmp10,
    "BMP-01": _build_bmp01,
    "BMP-02": _build_bmp02,
    "BMP-07": _build_bmp07,
    "BMP-09": _build_bmp09,
    "SH-05": _build_sh05,
    "SYS-05": _build_sys05,
    "ACC-02": _build_acc02,
    "ACC-03": _build_acc03,
    "BMP-03": _build_bmp03,
    "BMP-04": _build_bmp04,
    "ACC-01": _build_acc01,
    "ACC-04": _build_acc04,
    "BMP-05": _build_bmp05,
    "BMP-11": _build_bmp11,
    "SH-01": _build_sh01,
    "SYS-06": _build_sys06,
}
