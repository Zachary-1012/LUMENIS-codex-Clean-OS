"""序境 / LUMENIS — Experience 生产 ViewModel 绑定层.

唯一设计权威：00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md

本模块不拥有页面布局或视觉规则。它负责把真实后端事实映射成前端可消费的
ViewModel/section 数据，并保持 Evidence、状态、权限与缺失语义诚实。

Flutter App 是唯一用户 Experience；本模块只提供 layout-agnostic ViewModel 绑定。
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
import hashlib
import json
import os
import re
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
    _BASE_DIR, "contracts", "experience", "screen_meta.json"
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


def _platform_collection_section(*, consumer: str = "CTH", scoped_material=None) -> Dict[str, Any]:
    """Build the shared platform-intelligence surface for CTH and BMP.

    CTH owns the collector and its Evidence/Canonical writes.  BMP receives
    the same read-only view as a market-intelligence consumer; this helper
    deliberately does not create a second BMP collector or truth table.
    """
    if consumer == "BMP":
        # BMP may consume authorized source observations, never the collector's
        # unscoped web_runs or account health. Reuse the existing Canonical read.
        if not isinstance(scoped_material, dict):
            raise ValueError("BMP_SCOPED_PLATFORM_MATERIAL_REQUIRED")
        records = scoped_material["records"]
        groups = {}
        for record in records:
            platform = record.get("source_platform") or "UNKNOWN"
            group = groups.setdefault(platform, {"platform": platform,
                "platform_id": platform, "observed_source_count": 0,
                "source_references": [], "can_attempt": False,
                "manual_collection_enabled": False, "form_selectable": False})
            group["observed_source_count"] += 1
            group["source_references"].append({"canonical_id": record["canonical_id"],
                "source_id": record.get("source_id"),
                "scope_evidence": record["scope_evidence"]})
        incomplete = bool(scoped_material.get("truncated") or scoped_material.get("rejected_count"))
        return section("platforms", "partial" if incomplete else STATE_READY if records else STATE_EMPTY,
            title="平台来源 · 当前品牌范围只读消费",
            description="仅显示当前授权范围内有签名来源依据的记录；来源计数不是市场洞察或采集成功率。",
            consumer="BMP", collection_owner="CTH", items=list(groups.values()),
            can_trigger=False, endpoint="", source_endpoint="", manual_only=True,
            read_only=True, external_write=False, product_will_not_publish=True,
            source_count=len(records), count_complete=not incomplete,
            rejected_count=scoped_material.get("rejected_count", 0),
            truncated=bool(scoped_material.get("truncated")),
            collection_runtime={"state": "UNKNOWN", "reason": "COLLECTOR_RUN_SCOPE_NOT_VERIFIED"},
            coverage="NOT_VERIFIED", source_freshness="UNKNOWN")
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
        default_keyword="",
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
        # Event identity and Shared Evidence identity are separate namespaces.
        raw_ref = e.get("scope_evidence_ref")
        evidence_ref = str(raw_ref) if type(raw_ref) is int or isinstance(raw_ref, str) else ""
        evidence_ref = f"EV-{evidence_ref}" if evidence_ref.isascii() and evidence_ref.isdigit() and int(evidence_ref) > 0 else None
        out.append({
            "time": str(e.get("event_date") or e.get("last_seen") or "")[5:16] or "—",
            "date": str(e.get("first_seen") or "")[:10],
            "title": e.get("title", "未命名事件"),
            "desc": (e.get("summary") or "")[:120],
            "level": _LV.get(e.get("risk_level") or "low", "low"),
            "tags": [f"提及 {e.get('mention_count', 0)}", f"来源 {e.get('source_count', 1)}"],
            "event_id": e.get("event_id") or e.get("id"),
            "evidence": evidence_ref,
            "evidence_ref": evidence_ref,
            "evidence_state": "REFERENCED" if evidence_ref is not None else "UNKNOWN",
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


def _build_cth03(*, binding: Dict[str, Any]) -> Dict[str, Any]:
    """Read exact Canonical scope; each returned row carries verified lineage."""
    from canonical_data import list_scoped_canonical
    from lumenis.shared.database import get_repository

    with get_repository().connection(read_only=True) as con:
        result = list_scoped_canonical(
            con, product_id="CTH", subject_id=binding["subject_id"], limit=100,
        )
    mode = binding["canonical_scope"]
    view_scope = {
        "mode": mode, "domain_id": "CTH", "product_id": "CTH",
        "global_all_granted": binding["global_all_granted"],
    }
    if mode == "FOCUS":
        view_scope["subject_id"] = binding["subject_id"]
    rows = []
    for record in result["records"]:
        proof = record["scope_evidence"]
        projection = {
            "contract": "lumenis.shared.experience-row-projection", "version": 2,
            "read_allowed": True, "scope": dict(view_scope),
            "canonical_reference": record["canonical_id"],
            "stored_scope": {**proof["stored_scope"], "global": False},
            "evidence": {
                "canonical_reference": f"evidence:canonical:{proof['id']}",
                "evidence_id": str(proof["id"]), "source_id": proof["source_id"],
            },
            "integrity": proof["integrity"],
        }
        rows.append({
            "note_id": record["canonical_id"], "subject_id": record["subject_id"],
            "title": record["title"] or record["content"][:120],
            "date": record["publish_datetime"] or None,
            "captured_at": record["captured_at"] or None,
            "platform": record["source_platform"],
            "source_url": record["canonical_url"] or record["url"] or None,
            # Scope verification does not verify an analysis or risk judgement.
            "sentiment": None, "risk": None,
            "analysis_state": "not_verified", "quality_status": record["quality_status"],
            "scope_mode": mode, "canonical_scope": mode, "read_allowed": True,
            "projection": projection,
        })
    partial = bool(result["truncated"] or result["rejected_count"] or any(
        row["quality_status"] != "ok" or row["date"] is None for row in rows
    ))
    stream_state = STATE_READY if rows else "blocked" if result["rejected_count"] else STATE_NOT_COLLECTED
    kpis = [
        metric("cth03.recent", "近窗记录", value=None, state=STATE_NOT_COLLECTED,
               icon="event", note="来源时间与完整窗口尚未验证", source="canonical_data"),
        metric("cth03.negative", "其中负面", value=None, state=STATE_NOT_COLLECTED,
               icon="risk", note="情感评估尚未验证", source="canonical_data"),
    ]
    platform_sec = _platform_collection_section(consumer="CTH")
    stream = section("table", stream_state, title="已采集记录", rows=rows)
    sections = [_head("CTH-03"), section("kpis", STATE_READY, items=kpis), platform_sec, stream]
    response = _envelope("CTH-03", sections, truth={
        "data_state": "partial" if partial else "available" if rows else stream_state,
        "coverage": "NOT_VERIFIED", "source_freshness": "UNKNOWN",
        **{key: value for key, value in result.items() if key != "records"},
    })
    response["global_binding" if mode == "GLOBAL_ALL" else "focus_binding"] = binding
    return response


def _event_screen_material(binding, domain, event_limit, risk_limit=0):
    """Consume the verified domain read binding; never turn read errors into empty data."""
    import database as db

    if (not isinstance(binding, dict)
            or binding.get("contract") != "lumenis.scope-read-binding.v1"
            or binding.get("scope_verified") is not True
            or binding.get("read_allowed") is not True
            or binding.get("domain_id") != domain
            or binding.get("canonical_scope") not in {"FOCUS", "GLOBAL_ALL"}):
        raise ValueError("EVENT_SCOPE_BINDING_REQUIRED")
    focused = binding["canonical_scope"] == "FOCUS"
    scope = db._normalize_event_scope({
        "domain_id": "cth" if domain == "CTH" else "zbmp",
        "subject_id": binding.get("subject_id") if focused and domain == "CTH" else None,
        "brand_focus_id": binding.get("brand_focus_id") if focused and domain == "BMP" else None,
        "global_scope": not focused,
    }, allow_global=True)
    events = db.get_events_curated(event_limit, scope=scope)
    risk = []
    coverage = {"source_truncated": False, "rejected_sources": 0}
    if risk_limit:
        source_read = db.get_scoped_event_source_rows(
            scope, source_types=("note", "web_mention"), limit=5000)
        candidates = [row for row in source_read["sources"]
                      if row.get("risk_level") in {"high", "critical"}]
        rejected = source_read.get("rejected_count")
        source_complete = source_read.get("truncated") is False and type(rejected) is int and rejected == 0
        risk_truncated = len(candidates) > risk_limit
        risk = candidates[:risk_limit]
        coverage = {"source_truncated": source_read.get("truncated"),
                    "rejected_sources": rejected, "source_read_complete": source_complete,
                    "risk_read_complete": source_complete and not risk_truncated,
                    "risk_truncated": risk_truncated, "risk_observed_count": len(candidates),
                    "risk_returned_count": len(risk)}
    return events, risk, coverage


def _build_cth04(*, binding=None) -> Dict[str, Any]:
    """事件与事件关系：真实事件列表；关系图需图关系数据，缺则诚实 blocked。"""
    events, _risk, coverage = _event_screen_material(binding, "CTH", 20)
    items = _events_items(_curated(events))
    kpis = [
        metric("cth04.events", "已策展事件", value=len(items), state=STATE_READY,
               icon="event", source="database.get_events_curated"),
        metric("cth04.graph", "事件关系边", value=None, state=STATE_NOT_COLLECTED,
               icon="trend", note="关系图需要事件关联边表（mention/event_link），当前无独立关系口径",
               source="BLOCKED: event relationship edge table"),
    ]
    graph_state = "PERMISSION_NOT_AVAILABLE"
    graph_data = None
    try:
        from experience_runtime import _shared_work_actor_scope
        from event_graph import read_scoped_graph
        actor, scope = _shared_work_actor_scope("read")
        graph_data = read_scoped_graph(actor=actor, scope=scope)
        graph_state = "available"
    except (ValueError, PermissionError):
        # Public source observations and actor-owned graph work have separate
        # read rights. A denied private projection must not hide legal sources.
        pass
    kpis[1] = metric("cth04.graph", "当前账户范围关系边", value=len(graph_data["relations"]) if graph_data is not None else None,
        state=STATE_READY if graph_data is not None else STATE_NOT_COLLECTED, icon="trend",
        source="event_graph.read_scoped_graph", note="用户声明与自动推断分别标记；关系不自动证明因果")
    ev_sec = section("events", STATE_READY if items else STATE_EMPTY, title="事件列表（真实）", items=items)
    sections = [_head("CTH-04"), section("kpis", STATE_READY, items=kpis), ev_sec]
    if graph_data is not None:
        rows=[{"source":r["source_event_id"],"target":r["target_event_id"],"relation_type":r["relation_type"],
               "claim_type":r["evidence"]["claim_type"],"causality_verified":False} for r in graph_data["relations"]]
        sections.append(section("table",STATE_READY if rows else STATE_EMPTY,title="已保存关系与推断",columns=[
            {"label":"来源","key":"source"},{"label":"目标","key":"target"},
            {"label":"关系","key":"relation_type"},{"label":"依据类型","key":"claim_type"}],rows=rows))
    return _envelope("CTH-04", sections, truth={"coverage":coverage,"graph_state":graph_state,
        "graph_rejected":graph_data["rejected"] if graph_data else None,"legacy_graph_scope":"UNKNOWN"})


def _cth_temporal_screen(screen_id: str, *, binding, authorize=None) -> Dict[str, Any]:
    """Project the existing domain metric reader; never manufacture aggregate Evidence.

    temporal_metrics is the complete typed derived snapshot. Its source Evidence
    remains in contributions, while snapshot_sha256 pins the computation only.
    Missing publication/classification/coverage stays null, not an invented zero.
    """
    from alert_engine import read_cth_temporal_alerts
    from lumenis.shared.database import get_repository

    end = _dt.date.today()
    start = end - _dt.timedelta(days=13)
    with get_repository().connection(read_only=True) as connection:
        result = read_cth_temporal_alerts(
            connection, start_date=start.isoformat(), end_date=end.isoformat(),
            authorize=authorize if callable(authorize) else lambda: binding,
        )
    fields = (("negative", "负面"), ("high", "高风险")) if screen_id == "CTH-05" else (
        ("total", "声量"), ("negative", "负面"), ("high", "高风险"),
    )
    state = result["state"]
    kpis = [metric(screen_id.lower() + "." + key, "近14日" + label,
                   value=result["totals"][key]["value"],
                   state=result["totals"][key]["state"], icon="trend",
                   source="已核验来源的原生发布时间统计") for key, label in fields]
    chart = section("chart", state, kind="line", title="近14日已收录资料",
                    labels=[day["date"] for day in result["days"]],
                    series=[{"name": label, "metric": key,
                             "data": [day[key]["value"] for day in result["days"]]}
                            for key, label in fields],
                    note="仅统计获准收录资料；空缺不补零，收录样本不代表整体市场。")
    response = _envelope(screen_id, [_head(screen_id), section("kpis", state, items=kpis), chart],
                         truth={"data_state": state, "coverage": result["coverage"],
                                "source_freshness": result["source_freshness"]})
    response["temporal_metrics"] = result
    mode = result["binding"]["canonical_scope"]
    response["global_binding" if mode == "GLOBAL_ALL" else "focus_binding"] = result["binding"]
    response["trend_metadata"] = {
        "numerator": "所选原生发布时间内的已收录资料数量",
        "denominator": "计数，不使用市场总体分母",
        "time_window": start.isoformat() + " / " + end.isoformat(),
        "subject": "GLOBAL/ALL" if mode == "GLOBAL_ALL" else result["binding"]["subject_id"],
        "source": "已获准资料", "freshness": result["source_freshness"],
        "recipe": result["recipe"], "snapshot_sha256": result.get("snapshot_sha256"),
    }
    return response


def _build_cth05(*, binding=None, authorize=None) -> Dict[str, Any]:
    return _cth_temporal_screen("CTH-05", binding=binding, authorize=authorize)


def _cth_source_material(binding, *, sentiment=None, risk_levels=None, offset=0):
    """Read source-backed CTH records using the existing Canonical owner."""
    from canonical_data import list_scoped_canonical
    from lumenis.shared.database import get_repository

    if (not isinstance(binding, dict) or binding.get("contract") != "lumenis.scope-read-binding.v1"
            or binding.get("domain_id") != "CTH" or binding.get("product_id") != "CTH"
            or binding.get("read_allowed") is not True or binding.get("scope_verified") is not True
            or binding.get("canonical_scope") not in {"GLOBAL_ALL", "FOCUS"}):
        raise PermissionError("CTH_SOURCE_BINDING_REQUIRED")
    focused = binding["canonical_scope"] == "FOCUS"
    if focused != bool(binding.get("subject_id")):
        raise PermissionError("CTH_SOURCE_SCOPE_INVALID")
    with get_repository().connection(read_only=True) as connection:
        result = list_scoped_canonical(connection, product_id="CTH",
                                       subject_id=binding.get("subject_id"), limit=100,
                                       source_level=True, sentiment=sentiment,
                                       risk_levels=risk_levels, offset=offset)
    return result


def _cth_view_scope(binding):
    return {"mode": binding["canonical_scope"], "domain_id": "CTH", "product_id": "CTH",
            "subject_id": binding.get("subject_id"), "scope_verified": True,
            "global_all_granted": binding.get("global_all_granted") is True}


def _cth_record_evidence(record, binding):
    proof = record["scope_evidence"]
    integrity = proof["integrity"]
    if integrity.get("verified") is not True or integrity.get("lineage_verified") is not True:
        raise ValueError("CTH_SOURCE_LINEAGE_UNVERIFIED")
    return {"canonical_ref": "evidence:canonical:" + str(proof["id"]),
            "canonical": True, "read_allowed": True, "quote": record.get("title") or "",
            "captured_at": record.get("captured_at"), "scope": _cth_view_scope(binding),
            "stored_scope": proof.get("stored_scope"),
            "integrity": {**integrity, "status": "verified", "version": str(integrity.get("integrity_version"))}}


def _cth_bound_response(screen_id, sections, binding, *, truth=None):
    response = _envelope(screen_id, sections, truth=truth)
    response["binding"].update({**binding, "context_mode": binding["canonical_scope"],
                                "evidence_lineage": "verified"})
    response["global_binding" if binding["canonical_scope"] == "GLOBAL_ALL" else "focus_binding"] = dict(binding)
    return response


def _cth_source_offset(offset):
    if offset is None:
        from flask import has_request_context, request
        raw = request.args.get("offset", "0") if has_request_context() else "0"
        if not raw.isascii() or not raw.isdigit():
            raise ValueError("CTH_SOURCE_OFFSET_INVALID")
        offset = int(raw)
    if type(offset) is not int or offset < 0:
        raise ValueError("CTH_SOURCE_OFFSET_INVALID")
    return offset


def _build_cth06(*, binding=None, offset=None) -> Dict[str, Any]:
    offset = _cth_source_offset(offset)
    result = _cth_source_material(binding, sentiment="negative", offset=offset)
    rows = []
    for record in result["records"]:
        if record.get("sentiment") != "negative":
            continue
        proof = record["scope_evidence"]
        evidence = _cth_record_evidence(record, binding)
        projection = {"contract": "lumenis.shared.experience-row-projection", "version": 2,
                      "read_allowed": True, "scope": _cth_view_scope(binding),
                      "canonical_reference": record["canonical_id"],
                      "stored_scope": proof.get("stored_scope"),
                      "evidence": {"canonical_reference": evidence["canonical_ref"],
                                   "evidence_id": str(proof["id"]), "source_id": proof["source_id"]},
                      "integrity": proof["integrity"]}
        rows.append({"id": record["canonical_id"], "title": record.get("title") or "未命名资料",
                     "date": record.get("publish_datetime"), "platform": record.get("source_platform"),
                     "sentiment": record.get("sentiment"), "risk": record.get("risk_level"),
                     "category": "unclassified", "analysis_state": "stored_labels_not_reverified",
                     "subject_id": record.get("subject_id"), "read_allowed": True,
                     "scope_mode": binding["canonical_scope"], "canonical_scope": binding["canonical_scope"],
                     "projection": projection})
    unknown = result["unknown_sentiment_count"]
    partial = bool(result.get("truncated") or result.get("rejected_count") or unknown)
    state = "partial" if partial else STATE_READY if rows else STATE_EMPTY
    response = _cth_bound_response("CTH-06", [_head("CTH-06"),
        section("table", state, title="已收录负面反馈", rows=rows)], binding,
        truth={"coverage": "UNKNOWN", "unknown_classification_count": unknown,
               "read": {key: value for key, value in result.items() if key != "records"},
               "classification_provenance": "stored_canonical_labels; analysis_correctness_not_verified"})
    return response


def _build_cth07(*, binding=None, authorize=None) -> Dict[str, Any]:
    return _cth_temporal_screen("CTH-07", binding=binding, authorize=authorize)


def _build_cth08(*, binding=None) -> Dict[str, Any]:
    """案例库 / 案例分析：真实高风险笔记 + 已策展事件。"""
    events, risk, coverage = _event_screen_material(binding, "CTH", 10, 20)
    kpi = metric("cth08.cases", "高风险候选案例", value=len(risk), state=STATE_READY,
                 icon="risk", source="database.get_scoped_event_source_rows")
    tbl = _notes_table("高风险案例（真实）", risk, 14)
    ev = section("events", STATE_READY if _curated(events) else STATE_EMPTY, title="已策展事件",
                 items=_events_items(_curated(events)))
    sections = [_head("CTH-08"), section("kpis", STATE_READY, items=[kpi]), tbl, ev]
    return _envelope("CTH-08", sections, truth={"coverage": coverage, "counts_are_returned_observations": True})


def _build_cth09(*, binding=None, offset=None) -> Dict[str, Any]:
    """Scoped risk sources; decisions remain owned by BusinessDecisionWorkflow."""
    offset = _cth_source_offset(offset)
    result = _cth_source_material(binding, risk_levels=["high", "critical"], offset=offset)
    items = []
    for record in result["records"]:
        if record.get("risk_level") not in {"high", "critical"}:
            continue
        score = record.get("risk_score")
        items.append({"id": record["canonical_id"], "title": record.get("title") or "风险资料",
                      "level": record.get("risk_level"),
                      "score": score if type(score) in (int, float) and _finite_metric(score) else None,
                      "summary": "已存风险标签，判断准确性需结合原始资料复核。",
                      "analysis_state": "stored_labels_not_reverified",
                      "evidence": [_cth_record_evidence(record, binding)]})
    unknown = result["unknown_risk_count"]
    state = "partial" if result.get("truncated") or result.get("rejected_count") or unknown else (
        STATE_READY if items else STATE_EMPTY)
    return _cth_bound_response("CTH-09", [_head("CTH-09"), section("risks", state, items=items)], binding,
        truth={"coverage": "UNKNOWN", "unknown_risk_count": unknown,
               "decision_owner": "api_dual_domain.BusinessDecisionWorkflow",
               "read": {key: value for key, value in result.items() if key != "records"}})


def _finite_metric(value):
    import math
    return math.isfinite(value)


def _build_cth10(*, binding=None) -> Dict[str, Any]:
    """Preview the existing source brief in exact scope; never query global Evidence."""
    from lumenis.shared.database import get_repository
    from lumenis.shared.reporting.operational_brief import build_scoped_source_brief

    # Validate before any read, using the same scoped Canonical owner as the source list.
    material = _cth_source_material(binding)
    focused = binding["canonical_scope"] == "FOCUS"
    with get_repository().connection(read_only=True) as connection:
        brief = build_scoped_source_brief(connection, product_id="CTH", global_scope=not focused,
                                          entity_label=binding["subject_id"] if focused else "全部获准主体",
                                          subject_id=binding.get("subject_id"), limit=100)
    records = {row["source_id"]: row for row in material["records"]}
    evidence = [_cth_record_evidence(records[row["source_id"]], binding)
                for row in brief["records"] if row["source_id"] in records]
    if (len(evidence) != len(brief["records"]) or any(
            str(records[row["source_id"]].get("scope_evidence_ref")) != str(row["scope_evidence_ref"])
            for row in brief["records"])):
        raise RuntimeError("CTH_REPORT_SOURCE_SNAPSHOT_CHANGED")
    items = []
    if evidence:
        items.append({"id": "source-brief:" + brief["content_hash"], "title": "资料来源简报",
                      "period": "当前已收录资料", "scope": brief["scope"]["entity_label"],
                      "state": "derived_preview_not_saved", "evidence": evidence,
                      "blocks": [{"id": "source-summary", "title": "来源与覆盖",
                                  "kind": "source_brief", "body": brief["markdown"],
                                  "status": brief["status"]}]})
    response = _cth_bound_response("CTH-10", [_head("CTH-10"),
        section("reports", "partial" if brief["status"] == "PARTIAL" else STATE_READY if items else STATE_EMPTY,
                items=items)], binding, truth={"coverage": brief["coverage"],
                "freshness": brief["freshness"], "persisted": False,
                "source_only": True, "save_owner": "Shared SavedWork / SourceBrief tasks"})
    response["source_brief"] = brief
    return response


# ===========================================================================
# AI Agent 域（真实数据源：Agent Groups Skill Execution / ai_governance / function_registry）
# ===========================================================================
def _task_timeline(limit: int = 8, *, inbox=None) -> Dict[str, Any]:
    """Reuse authorized inbox status projections, never enumerate raw traces."""
    notifications = ((inbox or {}).get("data") or {}).get("notifications", [])
    items = []
    for notice in notifications[:limit]:
        event = notice["event"]
        items.append({
            "time": str(event.get("timestamp") or "")[5:16] or "—",
            "title": event.get("title") or "AI 任务",
            "desc": event.get("message") or "unknown",
            "done": notice.get("terminal") is True,
            "return_ref": notice["return_ref"],
        })
    return section("timeline", STATE_READY if items else STATE_EMPTY,
                   title="执行链任务（真实）", label="History", items=items)


def _build_ai02(*, binding=None) -> Dict[str, Any]:
    """Current authorized task status, retaining the original task owner."""
    inbox = _build_sh06(binding=binding)
    result = _envelope("AI-02", [_head("AI-02"), _task_timeline(12, inbox=inbox)])
    result["scope"] = inbox.get("scope")
    result["truth"] = inbox.get("truth", {"data_state": "scope_unavailable"})
    return result


def _build_ai03() -> Dict[str, Any]:
    """Project the actor's persistent Shared conversations and original turns."""
    from flask import request
    from lumenis.ai_hub import conversations as owner

    if set(request.args) - {"conversation_id"} or any(
            len(request.args.getlist(key)) != 1 for key in request.args):
        raise ValueError("CONVERSATION_SCREEN_QUERY_INVALID")
    actor = owner.current_actor("read")
    listing = owner.list_conversations(actor, limit=30)
    selected_id = request.args.get("conversation_id")
    selected = owner.read_conversation(actor, selected_id) if selected_id else None
    result = _envelope("AI-03", [_head("AI-03"),
        section("conversations", STATE_READY if listing["conversations"] else STATE_EMPTY,
                items=listing["conversations"]),
        section("conversation", STATE_READY if selected else STATE_EMPTY,
                items=selected["turns"] if selected else [])])
    result["data"] = {**listing, "selected_conversation": selected}
    result["truth"] = {"source": "ai_hub.conversations",
                       "scope": "actor-owned-shared-workspace",
                       "task_turns": "derived-reference-with-fresh-owner-authorization",
                       "training_admission": "NOT_GRANTED"}
    return result


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
    raw_overall = hc.get("overall")
    overall = (
        raw_overall
        if isinstance(raw_overall, str)
        and raw_overall.lower() in {"healthy", "ok", "degraded", "unhealthy", "error"}
        else None
    )
    workers = hc.get("workers") if isinstance(hc.get("workers"), dict) else {}
    dlq = hc.get("dlq") if isinstance(hc.get("dlq"), dict) else {}
    raw_breakers = hc.get("circuit_breakers")
    breakers = raw_breakers if isinstance(raw_breakers, dict) else None

    def _int(v, default=None):
        return v if isinstance(v, int) and not isinstance(v, bool) else default

    # Missing counts stay unavailable. Coercing them to zero turns a failed
    # health read into a false healthy-looking KPI.
    worker_total = _int(workers.get("total"))
    worker_failed = _int(workers.get("failed"))
    dlq_total = _int(dlq.get("total"))
    reaper_value = hc.get("reaper_running")

    # RuntimeGuardian's `overall` covers workers and circuit breakers, not the
    # reaper.  A screen titled "system overall" must not promote that narrower
    # status to healthy while the service guardrail is stopped or unobserved.
    if overall in {"healthy", "ok"}:
        if reaper_value is False:
            overall = "degraded"
        elif (
            reaper_value is not True
            or worker_total is None
            or worker_failed is None
            or dlq_total is None
            or breakers is None
        ):
            overall = None

    source = "runtime_guardian.legacy_health_check"
    captured_at = None
    raw_timestamp = hc.get("timestamp")
    if isinstance(raw_timestamp, str) and raw_timestamp and len(raw_timestamp) <= 64:
        try:
            normalized_timestamp = (
                raw_timestamp[:-1] + "+00:00"
                if raw_timestamp.endswith("Z")
                else raw_timestamp
            )
            captured_at = _dt.datetime.fromisoformat(
                normalized_timestamp
            ).isoformat(timespec="seconds")
        except (TypeError, ValueError, OverflowError):
            captured_at = None

    open_breaker_count = None
    registered_breaker_count = None
    if breakers is not None:
        open_breaker_count = sum(
            1
            for breaker in breakers.values()
            if isinstance(breaker, dict) and breaker.get("state") == "open"
        )
        registered_breaker_count = len(breakers)
    observation_ready = captured_at is not None and overall is not None
    trace_id = None
    if observation_ready:
        trace_material = {
            "source": source,
            "captured_at": captured_at,
            "overall": overall.lower(),
            "workers_total": worker_total,
            "workers_failed": worker_failed,
            "dlq_total": dlq_total,
            "reaper_running": reaper_value,
            "open_breakers": open_breaker_count,
            "registered_breakers": registered_breaker_count,
        }
        digest = hashlib.sha256(
            json.dumps(trace_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:24]
        trace_id = f"sys01rt-{digest}"
    runtime_observation = {
        "state": "ready" if observation_ready else "unavailable",
        "source": source,
        "captured_at": captured_at if observation_ready else None,
        "trace_id": trace_id,
        "boundary": "read_only",
    }

    def _count_metric(metric_id, title, value, icon, source):
        return metric(
            metric_id,
            title,
            value=value,
            state=STATE_READY if value is not None else STATE_OFFLINE,
            icon=icon,
            source=source,
        )

    # Status strings stay in the runtime section; countup accepts only numbers.
    kpis = [
        _count_metric(
            "sys01.workers_total", "注册 Worker", worker_total, "ops",
            "runtime_guardian.workers.total",
        ),
        _count_metric(
            "sys01.workers_failed", "失败 Worker", worker_failed, "risk",
            "runtime_guardian.workers.failed",
        ),
        _count_metric(
            "sys01.dlq", "DLQ 积压", dlq_total, "database",
            "runtime_guardian.dlq.total",
        ),
    ]
    overall_state = {"healthy": "ok", "ok": "ok", "degraded": "warn",
                     "unhealthy": "bad", "error": "bad"}.get(
                         str(overall).lower(), "offline"
                     )
    if breakers is None:
        breaker_state = "offline"
        breaker_detail = "状态不可用"
    else:
        breaker_state = "bad" if open_breaker_count else "ok"
        breaker_detail = (
            f"open={open_breaker_count} · registered={registered_breaker_count}"
        )

    rt_items = [
        {"name": "总体状态", "state": overall_state, "detail": str(overall or "unknown")},
        {
            "name": "reaper",
            "state": "ok" if reaper_value is True else (
                "idle" if reaper_value is False else "offline"
            ),
            "detail": f"running={reaper_value if isinstance(reaper_value, bool) else 'unknown'}",
        },
        {"name": "熔断器", "state": breaker_state, "detail": breaker_detail},
        {
            "name": "guardian",
            "state": "ready" if hc.get("guardian_name") else "offline",
            "detail": "已识别" if hc.get("guardian_name") else "状态不可用",
        },
        {
            "name": "时间戳",
            "state": "ready" if captured_at else "offline",
            "detail": captured_at or "状态不可用",
        },
    ]
    rt = section("runtime", title="健康明细（真实）", items=rt_items)
    counts_state = (
        STATE_READY
        if all(value is not None for value in (worker_total, worker_failed, dlq_total))
        else STATE_OFFLINE
    )
    sections = [_head("SYS-01"), section("kpis", counts_state, items=kpis), rt]
    response = _envelope("SYS-01", sections, truth={"overall": overall})
    # This is a correlation label for one SYSTEM runtime read, not canonical business Evidence.
    response["runtime_observation"] = runtime_observation
    return response


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
    """安全与权限：读取 SYSTEM Permission owner 的真实枚举（不泄露凭据）。"""
    try:
        from lumenis.system.security import permission as pg

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
                 source="lumenis.system.security.permission.PermissionLevel")
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
    from lumenis.shared.agents.skills.execution import get_skills_light_status

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
               source="lumenis.shared.agents.skills.execution.get_skills_light_status"),
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


def _build_sh02(*, binding: dict[str, Any]) -> dict[str, Any]:
    from canonical_data import list_scoped_canonical
    from lumenis.shared.database import get_repository

    if (binding.get("contract") != "lumenis.scope-read-binding.v1"
            or binding.get("module") != "evidence"
            or binding.get("scope_verified") is not True
            or binding.get("read_allowed") is not True):
        raise PermissionError("MATERIAL_SCOPE_REQUIRED")
    mode = binding["canonical_scope"]
    scope = {"mode": mode, "global_all_granted": binding["global_all_granted"]}
    if mode == "FOCUS":
        domain = binding["domain_id"]
        scope.update(domain_id=domain, display_name=binding["display_name"])
        key = "subject_id" if domain == "CTH" else "brand_focus_id"
        scope[key] = binding[key]
        domains = [domain]
    elif mode == "GLOBAL_ALL" and binding["global_all_granted"] is True:
        domains = ["CTH", "BMP"]
    else:
        raise PermissionError("MATERIAL_SCOPE_REQUIRED")
    rows, coverage = [], {}
    with get_repository().connection(read_only=True) as con:
        for domain in domains:
            result = list_scoped_canonical(
                con, product_id=domain, limit=100,
                subject_id=binding.get("subject_id") if domain == "CTH" else None,
                brand_focus_id=binding.get("brand_focus_id") if domain == "BMP" else None,
            )
            coverage[domain] = {key: value for key, value in result.items() if key != "records"}
            for record in result["records"]:
                proof = record["scope_evidence"]
                rows.append({
                    "id": record["canonical_id"], "kind": "SOURCE",
                    "summary": (record["title"] or record["content"])[:180],
                    "source": record["source_platform"],
                    "captured_at": record["captured_at"] or None,
                    "published_at": record["publish_datetime"] or None,
                    "freshness": "UNKNOWN", "origin": domain,
                    "lineage": ["SOURCE", "EVIDENCE", "CANONICAL"],
                    "projection": {
                        "contract": "lumenis.shared.experience-row-projection", "version": 2,
                        "read_allowed": True, "scope": dict(scope),
                        "canonical_reference": record["canonical_id"],
                        "stored_scope": {**proof["stored_scope"], "global": False},
                        "evidence": {
                            "canonical_reference": f"evidence:canonical:{proof['id']}",
                            "evidence_id": str(proof["id"]), "source_id": proof["source_id"],
                        },
                        "integrity": proof["integrity"],
                    },
                })
    rows.sort(key=lambda row: (row["captured_at"] or "", row["id"]), reverse=True)
    partial = any(value["truncated"] or value["rejected_count"] for value in coverage.values())
    response = _envelope("SH-02", [_head("SH-02")], truth={
        "data_state": "partial" if partial else "available" if rows else "empty",
        "coverage": coverage,
    })
    response["scope"] = scope
    response["permission"] = {"decision": "ALLOW", "read": True, "module": "evidence"}
    response["data"] = {"evidence": rows, "partial": partial}
    return response


def _build_sh04() -> Dict[str, Any]:
    """报告导出中心：读取 Shared Reporting 真实目录（导出 EFFECT 未接通时不造假下载）。"""
    from lumenis.shared.reporting import engine as re_

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
                 source="lumenis.shared.reporting.engine.list_domain_reports")
    tbl = section("table", STATE_READY if rows else STATE_EMPTY, title="可导出报告目录（真实）",
                  columns=[{"label": "领域", "key": "领域"}, {"label": "类型", "key": "类型"},
                           {"label": "名称", "key": "名称"}, {"label": "受保护", "key": "受保护"}], rows=rows)
    note = section("note", STATE_READY, kind="RULE", code="EXPORT-EFFECT",
                   text="目录为真实只读；点击导出属写操作，需 Shared Reporting 导出端点 + 权限门控，未接通前不提供假下载。")
    sections = [_head("SH-04"), section("kpis", STATE_READY, items=[kpi]), tbl, note]
    return _envelope("SH-04", sections, truth={"domains": list(cat.keys())})


_SH06_REFERENCE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_SH06_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_SH06_FOCUS_KEYS = ("subject_id", "brand_focus_id", "focus_id")


def _sh06_verified_task_chain(rows: Any) -> Optional[Dict[str, Any]]:
    """Verify one TaskEngine Evidence hash chain end to end (SH-06 lineage gate).

    TaskEngine writes current_hash = SHA256(previous|evidence_id|task_id|content|created_at).
    The chain must start at genesis, link every row exactly once and recompute
    each digest; otherwise the task cannot prove Evidence linkage and is dropped.
    """
    if not isinstance(rows, list) or not rows:
        return None
    by_previous: Dict[Optional[str], Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            return None
        previous = row.get("previous_hash") or None
        if previous in by_previous:
            return None
        by_previous[previous] = row
    cursor: Optional[str] = None
    last: Optional[Dict[str, Any]] = None
    for _ in range(len(rows)):
        row = by_previous.get(cursor)
        if row is None:
            return None
        payload = "|".join(str(part) for part in (
            cursor or "genesis", row.get("evidence_id"), row.get("task_id"),
            row.get("content"), row.get("created_at"),
        ))
        digest = row.get("current_hash")
        if type(digest) is not str or not _SH06_DIGEST.match(digest):
            return None
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != digest:
            return None
        cursor, last = digest, row
    evidence_id = last.get("evidence_id") if last else None
    if type(evidence_id) is not str or not _SH06_REFERENCE.match(evidence_id):
        return None
    return {"evidence_id": evidence_id, "digest": cursor, "length": len(rows)}


def _sh06_task_scope(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Read the task's stored row scope; malformed context is unscoped (dropped)."""
    raw = task.get("context_json")
    try:
        context = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
    except (TypeError, ValueError):
        return None
    if not isinstance(context, dict):
        return None
    nested = context.get("scope") if isinstance(context.get("scope"), dict) else {}
    found = {key: (context.get(key) or nested.get(key)) for key in _SH06_FOCUS_KEYS}
    found = {key: value for key, value in found.items() if value not in (None, "")}
    if not found:
        return {"mode": "GLOBAL_ALL"}
    if len(found) != 1 or not all(isinstance(value, str) for value in found.values()):
        return None
    domain = str(context.get("domain_id") or context.get("domain")
                 or nested.get("domain_id") or nested.get("domain") or "").upper()
    domain = "BMP" if domain == "ZBMP" else domain
    if domain not in {"CTH", "BMP"}:
        return None
    key, value = next(iter(found.items()))
    return {"mode": "FOCUS", "domain_id": domain, "key": key, "id": value}


def _sh06_scope_accepts(row_scope: Dict[str, Any], binding: Dict[str, Any]) -> bool:
    if binding["canonical_scope"] == "GLOBAL_ALL":
        return row_scope["mode"] == "GLOBAL_ALL"
    if row_scope["mode"] != "FOCUS" or row_scope["domain_id"] != binding["domain_id"]:
        return False
    expected = binding.get("brand_focus_id") if binding["domain_id"] == "BMP" else binding.get("subject_id")
    return row_scope["id"] == expected


_SH06_PRIORITY = {"L0": "LOW", "L1": "LOW", "L2": "MEDIUM", "L3": "HIGH", "L4": "HIGH"}



def _sh06_skill_notifications(binding: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Project only live actor-owned Skill rows carrying an Owner scope receipt.

    These signed terminal traces have their own evidence contract. They are not
    TaskEngine hash chains and do not authorize reading protected result data.
    Legacy traces without a receipt remain absent from the scoped inbox.
    """
    from lumenis.auth.service import get_current_user
    from lumenis.shared.agents.skills.execution import (
        query_executions, verified_execution_scope,
    )
    from ai_api import _task_row_read_allowed
    from agent_focus.notification import project_persisted_task_notification

    actor = _safe(get_current_user, read_only=True, default=None)
    if not isinstance(actor, dict) or type(actor.get("id")) is not int:
        return []
    rows = _safe(query_executions, limit=50, default=[])
    notifications = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not _task_row_read_allowed(row, kind="SKILL_EXECUTION"):
            continue
        proof = verified_execution_scope(row, actor)
        if not isinstance(proof, dict):
            continue
        if proof.get("global_scope") is True:
            row_scope = {"mode": "GLOBAL_ALL"}
        else:
            domain = str(proof.get("domain_id") or "").upper()
            domain = "BMP" if domain == "ZBMP" else domain
            key = "brand_focus_id" if domain == "BMP" else "subject_id"
            identifier = proof.get(key)
            if domain not in {"CTH", "BMP"} or not isinstance(identifier, str) or not identifier:
                continue
            row_scope = {"mode": "FOCUS", "domain_id": domain, "id": identifier}
        if not _sh06_scope_accepts(row_scope, binding):
            continue
        notification = project_persisted_task_notification(row, task_kind="SKILL_EXECUTION")
        notification["scope_evidence"] = {
            "contract": "skill-execution-scope-v1",
            "evidence_id": proof["evidence_id"], "digest": proof["digest"],
            "stored_scope": row_scope,
        }
        notifications.append(notification)
    return notifications


def _build_sh06(*, binding: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """SH-06 read-only inbox (SH-06.md §1-§5).

    Only an authorized actor-bound GLOBAL_ALL / exact FOCUS binding yields items.
    Each TaskEngine task must carry a matching stored row scope and a fully
    verified Evidence hash chain, emitted as row projection v2; anything else is
    dropped. No approve/assign/snooze/retry/dismiss action is emitted, and no
    global queue, totals or DLQ/raw diagnostics are exposed.
    """
    note = section("note", STATE_READY, kind="RULE", code="SH06-READ-ONLY",
                   text="只读收件箱：卡片只显示状态，不提供审批、指派、稍后提醒或重试。")
    if not binding or binding.get("read_allowed") is not True:
        blocked = section("note", "blocked", kind="SCOPE", code="SH06-SCOPE",
                          text="通知与待办暂不显示：范围或读取授权不可用。")
        return _envelope("SH-06", [_head("SH-06"), blocked, note],
                         truth={"data_state": "scope_unavailable"})

    import ai_task_engine as te

    eng = te.get_task_engine()
    tasks = _safe(eng.list_tasks, limit=50, default=None)
    hc = _safe(eng.health_check, default={})
    hc = hc if isinstance(hc, dict) and not _is_err(hc) else {}
    engine_state = str(hc.get("status") or "").lower()
    operational = ("READY" if engine_state in {"healthy", "ok"} else
                   "DEGRADED" if engine_state == "degraded" else
                   "OFFLINE" if tasks is None else "UNCONFIRMED")
    mode = binding["canonical_scope"]
    view_scope: Dict[str, Any] = {"mode": mode,
                                  "global_all_granted": mode == "GLOBAL_ALL"}
    if mode == "FOCUS":
        view_scope["domain_id"] = binding["domain_id"]
        if binding["domain_id"] == "BMP":
            view_scope["brand_focus_id"] = binding["brand_focus_id"]
        else:
            view_scope["subject_id"] = binding["subject_id"]
    items: List[Dict[str, Any]] = []
    notifications: List[Dict[str, Any]] = []
    dropped = 0
    for task in tasks if isinstance(tasks, list) else []:
        task_id = task.get("task_id") if isinstance(task, dict) else None
        if type(task_id) is not str or not _SH06_REFERENCE.match(task_id):
            dropped += 1
            continue
        # Reuse the task owner's live actor and source-evidence checks. A valid
        # hash chain proves integrity only, never access to another actor's task.
        from ai_api import _task_row_read_allowed
        from agent_focus.notification import project_persisted_task_notification
        record = _safe(eng.get_task, task_id, default=None)
        if not isinstance(record, dict) or not _task_row_read_allowed(record):
            dropped += 1
            continue
        row_scope = _sh06_task_scope(task)
        if row_scope is None or not _sh06_scope_accepts(row_scope, binding):
            dropped += 1
            continue
        chain = _sh06_verified_task_chain(_safe(eng.get_evidence, task_id, default=None))
        if chain is None:
            dropped += 1
            continue
        notifications.append(project_persisted_task_notification(record, task_kind="TASK_ENGINE"))
        status = task.get("status")
        status = status if isinstance(status, str) else getattr(status, "value", None)
        title = task.get("intent") or task.get("user_input") or ""
        items.append({
            "id": task_id,
            "kind": "TASK",
            "title": str(title)[:120],
            "source_label": "任务引擎",
            "priority": _SH06_PRIORITY.get(str(task.get("risk_level") or "").upper()),
            "state": status,
            "projection": {
                "contract": "lumenis.shared.experience-row-projection", "version": 2,
                "read_allowed": True, "origin_verified": True,
                "scope": dict(view_scope),
                "stored_scope": {key: row_scope[key] for key in row_scope if key != "key"},
                "evidence": {
                    "canonical_reference": f"evidence:canonical:task:{chain['evidence_id']}",
                    "evidence_id": chain["evidence_id"], "chain_length": chain["length"],
                },
                "integrity": {
                    "integrity_version": 2, "verified": True, "lineage_verified": True,
                    "algorithm": "sha256", "digest": chain["digest"],
                    "assurance": "content-integrity-only",
                },
            },
        })
    notifications.extend(_sh06_skill_notifications(binding))
    response = _envelope("SH-06", [_head("SH-06"), note], truth={
        "data_state": "available" if items or notifications else "empty",
        "dropped_unverified": dropped,
    })
    response["scope"] = dict(view_scope)
    if mode == "FOCUS":
        response["scope"]["display_name"] = binding.get("display_name")
    response["permission"] = {"decision": "ALLOW", "read": True, "module": binding["module"]}
    response["data"] = {"tasks": items, "notifications": notifications, "alerts": [],
                        "operational_state": operational}
    response["focus_binding" if mode == "FOCUS" else "global_binding"] = binding
    return response


def _bmp_content_project_screen(screen_id, *, binding, podcast=False):
    from experience_runtime import _content_project_scope, _shared_work_actor_scope
    from shared_artifacts import list_content_projects
    from lumenis.shared.reporting.saved_work import search_work
    actor, scope = _content_project_scope("read", read_only_auth=True)
    if scope.get("domain_id") != "zbmp":
        raise ValueError("BMP_CONTENT_SCOPE_REQUIRED")
    projects = list_content_projects(actor=actor, **scope, limit=20)
    rows = projects["projects"]
    if podcast:
        rows = [row for row in rows if row["output_kind"] == "audio"]
    sections = [_head(screen_id), section("table", STATE_READY if rows else STATE_EMPTY,
        title="当前范围音频制作项目" if podcast else "当前范围内容制作项目",
        columns=[{"label":"项目","key":"artifact_id"},{"label":"类型","key":"output_kind"},
                 {"label":"状态","key":"status"}], rows=rows)]
    truth = {"project_list_status": projects["status"], "next_cursor": projects["next_cursor"],
             "returned_projects":len(rows), "legacy_unscoped_content":"NOT_ASSIGNED",
             "audio_is_not_automatically_podcast":True}
    if podcast:
        report_actor, report_scope = _shared_work_actor_scope("read")
        plans = search_work(actor=report_actor, scope=report_scope, kind="podcast_episode", limit=30)
        episodes = [{"artifact_id":row["artifact"]["artifact_id"], "title":row["document"]["title"],
                     "version":row["document"]["version"]} for row in plans["items"]]
        sections.append(section("table", STATE_READY if episodes else STATE_EMPTY, title="已保存播客节目方案",
            columns=[{"label":"标题","key":"title"},{"label":"版本","key":"version"}], rows=episodes))
        truth.update(podcast_plan_has_more=plans["has_more"], podcast_plan_next_cursor=plans["next_cursor"],
                     podcast_plan_verification_complete=plans["verification_complete"])
    result = _envelope(screen_id, sections, truth=truth)
    result["global_binding" if binding["canonical_scope"] == "GLOBAL_ALL" else "focus_binding"] = binding
    return result


def _build_bmp06(*, binding=None) -> Dict[str, Any]:
    return _bmp_content_project_screen("BMP-06", binding=binding)


def _build_bmp08(*, binding=None) -> Dict[str, Any]:
    return _bmp_content_project_screen("BMP-08", binding=binding, podcast=True)


def _event_read_state(material, items):
    """Keep bounded/rejected owner reads visibly partial at the event section."""
    meta = material if isinstance(material, dict) else {}
    complete = meta.get("read_complete") is True
    reasons = []
    if meta.get("truncated") is True:
        reasons.append("READ_LIMIT_OR_SCAN_BUDGET")
    if type(meta.get("rejected_count")) is int and meta["rejected_count"] > 0:
        reasons.append("SOURCE_OR_EVENT_VERIFICATION_REJECTED")
    if not complete and not reasons:
        reasons.append("READ_COMPLETENESS_UNVERIFIED")
    return (STATE_READY if items else STATE_EMPTY) if complete else "partial", {
        "read_complete": complete, "reasons": reasons,
        "observed_returned_count": meta.get("returned_count"), "displayed_count": len(items),
        "display_truncated": (meta["returned_count"] > len(items)) if type(meta.get("returned_count")) is int else None,
        "scanned_count": meta.get("scanned_count"),
        "rejected_count": meta.get("rejected_count"), "truncated": meta.get("truncated")}


def _build_bmp10(*, binding=None) -> Dict[str, Any]:
    """品牌风险与事件：database 真实事件 + 高风险笔记（与 CTH 同源只读，域适配 BMP）。"""
    ev, rn, coverage = _event_screen_material(binding, "BMP", 12, 10)
    event_material = ev
    ev = _curated(ev)
    event_items = _events_items(ev)
    event_state, event_read = _event_read_state(event_material, event_items)
    rn = rn if isinstance(rn, list) else []
    risk_complete = coverage.get("risk_read_complete") is True
    risk_state = (STATE_READY if rn else STATE_EMPTY) if risk_complete else "partial"
    risk_reasons = []
    if coverage.get("source_truncated") is True or coverage.get("risk_truncated") is True:
        risk_reasons.append("SOURCE_OR_RISK_READ_LIMIT")
    if type(coverage.get("rejected_sources")) is int and coverage["rejected_sources"] > 0:
        risk_reasons.append("SOURCE_VERIFICATION_REJECTED")
    if not risk_complete and not risk_reasons:
        risk_reasons.append("READ_COMPLETENESS_UNVERIFIED")
    kpis = [
        metric("bmp10.events", "当前范围已观测策展事件", value=len(ev) if event_read["read_complete"] else None,
               state=event_state, icon="event",
               source="database.get_events_curated"),
        metric("bmp10.high_risk", "高风险记录", value=len(rn) if risk_complete else None, state=risk_state,
               icon="risk", source="database.get_scoped_event_source_rows"),
    ]
    ev_sec = section("events", event_state, items=event_items, read_status=event_read)
    risk_items = [{
        "level": _LV.get(n.get("risk_level", "low"), "low"),
        "score": n.get("risk_score") if type(n.get("risk_score")) in (int, float) and _finite_metric(n["risk_score"]) else None,
        "title": (n.get("title") or "风险记录")[:40],
        "desc": (n.get("content") or "")[:90],
        "evidence": n.get("scope_evidence_ref"),
    } for n in rn[:5] if isinstance(n, dict)]
    risk_sec = section("risks", risk_state, items=risk_items, read_status={
        "read_complete": risk_complete, "reasons": risk_reasons,
        "observed_returned_count": len(rn), "displayed_count": len(risk_items),
        "display_truncated": len(rn) > len(risk_items),
        "rejected_count": coverage.get("rejected_sources"),
        "source_truncated": coverage.get("source_truncated"),
        "risk_truncated": coverage.get("risk_truncated")})
    sections = [_head("BMP-10"), section("kpis", "partial" if not risk_complete or not event_read["read_complete"] else STATE_READY, items=kpis), ev_sec, risk_sec]
    result = _envelope("BMP-10", sections, truth={"coverage": coverage, "event_read": event_read,
        "counts_are_returned_observations": True, "domain_id": "zbmp", "product_id": binding["product_id"],
        "data_state": "PARTIAL" if not risk_complete or not event_read["read_complete"] else "READY" if ev or rn else "EMPTY",
        "analysis_state": "NOT_COMPUTED"})
    result["observation_contract"] = "lumenis.bmp10-observations.v1"
    result["observation_read_binding"] = binding
    result["observation_context"] = {key: binding.get(key) for key in
        ("domain_id", "product_id", "canonical_scope", "subject_id", "brand_focus_id", "actor_id")}
    result["observed_events"] = [{"id": row.get("id"), "title": row.get("title"),
        "date": row.get("event_date"), "status": row.get("status"), "scope_evidence": row.get("scope_evidence")}
        for row in ev]
    result["observed_risks"] = [{"id": row.get("source_id"), "title": row.get("title"),
        "date": row.get("publish_date") or row.get("published_at"), "level": row.get("risk_level"),
        "score": row.get("risk_score"), "scope_evidence": row.get("scope_evidence")}
        for row in rn]
    return result


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
            "evidence": n.get("scope_evidence_ref"),
        })
    return out


def _build_bmp01_focus(binding: Dict[str, Any]) -> Dict[str, Any]:
    """Build authorized global/exact BrandFocus from signed Canonical rows only."""
    from canonical_data import list_scoped_canonical
    from lumenis.shared.database import get_repository
    from subject_registry import get_subject_by_id

    brand_focus_id = binding.get("brand_focus_id")
    subject_id = binding.get("subject_id")
    with get_repository().connection(read_only=True) as con:
        result = list_scoped_canonical(
            con, product_id="ZBMP", brand_focus_id=brand_focus_id, limit=100,
        )

    records = result["records"]
    truncated = bool(result.get("truncated"))
    total = len(records)
    sentiments = [str(row.get("sentiment") or "").lower() for row in records]
    sentiment_known = bool(records) and not truncated and all(
        value in {"positive", "neutral", "negative"} for value in sentiments
    )
    negative = sum(value == "negative" for value in sentiments) if sentiment_known else None
    risks = [str(row.get("risk_level") or "").lower() for row in records]
    risk_known = bool(records) and not truncated and all(
        value in {"none", "low", "medium", "high", "critical"} for value in risks
    )
    high_risk = sum(value in {"high", "critical"} for value in risks) if risk_known else None
    engagement_values = []
    engagement_complete = bool(records) and not truncated
    for row in records:
        fields = [
            row.get("engagement_likes"), row.get("engagement_comments"),
            row.get("engagement_collects"), row.get("engagement_shares"),
        ]
        if all(type(value) in (int, float) and _finite_metric(value) for value in fields):
            engagement_values.append(sum(
                int(value) for value in fields
            ))
        else:
            engagement_complete = False
    total_engagement = sum(engagement_values) if engagement_values else None
    state = STATE_READY if records else STATE_NOT_COLLECTED

    kpis = [
        metric("bmp01.total", "总声量" if not truncated else "已返回记录",
               value=total if records and not truncated else None,
               state=state if not truncated else STATE_NOT_COLLECTED,
               icon="trend", source="canonical_data.exact_brand_focus"),
        metric("bmp01.neg", "负面声量", value=negative,
               state=STATE_READY if negative is not None else STATE_NOT_COLLECTED,
               icon="risk", source="canonical_data.exact_brand_focus"),
        metric("bmp01.high", "高风险", value=high_risk,
               state=STATE_READY if high_risk is not None else STATE_NOT_COLLECTED,
               icon="risk", source="canonical_data.exact_brand_focus"),
        metric("bmp01.eng", "总互动", value=total_engagement if engagement_complete else None,
               state=STATE_READY if total_engagement is not None and engagement_complete else STATE_NOT_COLLECTED,
               icon="trend", source="canonical_data.exact_brand_focus"),
        metric("bmp01.ri", "风险指数", value=None, decimals=1, state=STATE_NOT_COLLECTED,
               icon="risk", source="ZBMP canonical metric not yet available",
               evidence_id="NOT_COLLECTED"),
        metric("bmp01.health", "品牌健康分", value=None, decimals=1,
               state=STATE_NOT_COLLECTED, icon="trend",
               source="ZBMP evaluation output not yet available",
               evidence_id="NOT_COLLECTED"),
    ]
    subject = get_subject_by_id("BMP", subject_id) if subject_id else None
    display_name = {}
    if subject:
        if subject.get("name_zh"):
            display_name["zh-CN"] = subject["name_zh"]
        if subject.get("name_en"):
            display_name["en"] = subject["name_en"]

    blocked = [
        _block("BMP-01", "risk_index", "缺少 ZBMP 专属风险指标真值源", "ZBMP canonical metric"),
        _block("BMP-01", "brand_health_score", "缺少 ZBMP 专属品牌健康真值源", "ZBMP evaluation output"),
        _block("BMP-01", "events", "缺少 ZBMP canonical 事件契约", "ZBMP event source"),
    ]
    response = _envelope(
        "BMP-01",
        [
            _head("BMP-01"),
            section("kpis", state, items=kpis),
            section("events", STATE_NOT_COLLECTED, title="重点事件", items=[],
                    description="ZBMP 事件源尚未形成 canonical 事件契约。"),
            section("risks", STATE_READY if risk_known else STATE_NOT_COLLECTED,
                    items=[{"level": row["risk_level"], "score": row.get("risk_score") if type(row.get("risk_score")) in (int, float) and _finite_metric(row["risk_score"]) else None,
                            "title": row.get("title") or "风险记录", "desc": (row.get("content") or "")[:90],
                            "evidence": "evidence:canonical:" + str(row["scope_evidence"]["id"]),
                            "scope_evidence": row["scope_evidence"]}
                           for row in records if row.get("risk_level") in {"medium", "high", "critical"}]),
        ],
        truth={
            "domain_id": "zbmp", "product_id": "ZBMP",
            "data_state": "READY" if records else "NOT_COLLECTED",
            "canonical_count": total,
            "returned_count": result.get("returned_count", total),
            "candidate_count": result.get("candidate_count"),
            "truncated": truncated,
            "metric_basis": "signed_scope_returned_rows",
            "engagement_complete": engagement_complete,
            "coverage": "NOT_VERIFIED",
            "source_freshness": "UNKNOWN",
            **{key: value for key, value in result.items() if key != "records"},
        },
        blocked=blocked,
    )
    response["focus_context" if binding["canonical_scope"] == "FOCUS" else "global_context"] = {
        "mode": binding["canonical_scope"], "subject_id": subject_id,
        "brand_focus_id": brand_focus_id, "display_name": display_name,
    }
    response["focus_binding" if binding["canonical_scope"] == "FOCUS" else "global_binding"] = binding
    return response


def _build_bmp01(*, binding: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if binding and binding.get("canonical_scope") in {"FOCUS", "GLOBAL_ALL"}:
        return _build_bmp01_focus(binding)
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
    """品牌中心 / 多品牌与竞品：读取当前 Web Discovery owner 的真实零售目录。"""
    import web_discovery as wm

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
               source="web_discovery.get_brand_directory"),
        metric("bmp02.cats", "业态类目数", value=len(cats), state=STATE_READY,
               icon="collection", source="web_discovery.get_brand_directory"),
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


def _build_bmp09(*, binding=None) -> Dict[str, Any]:
    """Read actual SavedWork reports using the report owner's exact actor/scope."""
    from experience_runtime import _bmp_saved_work_actor_scope
    from lumenis.shared.reporting.saved_work import search_work, authorize
    actor, scope = _bmp_saved_work_actor_scope(binding)
    context = authorize(actor, scope, action="read")
    if scope.get("domain_id") != "zbmp":
        raise ValueError("BMP_REPORT_SCOPE_REQUIRED")
    data = search_work(actor=actor, scope=scope, limit=100)
    rows = [{"id": item["artifact"]["artifact_id"], "title": item["document"]["title"],
             "kind": item["document"]["kind"], "version": item["document"]["version"],
             "sha256": item["artifact"]["sha256"], "source_count": len(item["document"]["citations"]),
             "assessment": "NOT_ESTABLISHED_BY_STORAGE"} for item in data["items"]]
    state = STATE_READY if rows else STATE_EMPTY
    response = _envelope("BMP-09", [_head("BMP-09"),
        section("table", state, title="当前范围已保存研究与报告", columns=[
            {"label": "标题", "key": "title"}, {"label": "类型", "key": "kind"},
            {"label": "版本", "key": "version"}, {"label": "引用来源", "key": "source_count"}], rows=rows)],
        truth={"saved_count": len(rows), "has_more": data["has_more"], "next_cursor": data["next_cursor"],
               "unverified_candidates": data["unverified_candidates"], "verification_complete": data["verification_complete"],
               "scope": scope, "evaluation": "artifact-specific; storage is not evaluation"})
    response["global_binding" if binding["canonical_scope"] == "GLOBAL_ALL" else "focus_binding"] = binding
    from lumenis.shared.reporting.source_brief_job import list_source_brief_jobs
    reports = list_source_brief_jobs(actor=actor, scope=scope, limit=30)
    response["sections"].append(section("table", reports["state"].lower(),
        title="来源简报 · 绑定当前报告版本的评估", resource_type="source_brief_job",
        columns=[{"label": "报告", "key": "job_id"}, {"label": "评估状态", "key": "evaluation_state"}],
        rows=reports["items"]))
    response["truth"]["source_brief_reports"] = {key: value for key, value in reports.items() if key != "items"}
    available = reports["state"] != "UNAVAILABLE"
    counts = {status: sum(item["evaluation_counts"][status] for item in reports["items"])
              if available else None for status in ("pass", "warn", "fail", "unknown")}
    distribution = {"counts": counts, "unit": "artifact_bound_check",
        "population": "returned_source_brief_page", "read_complete": reports["read_complete"],
        "has_more": reports["has_more"], "next_cursor": reports.get("next_cursor"),
        "missing_evaluation_count": sum(item["missing_evaluation_count"] for item in reports["items"])
            if available else None,
        "saved_work_evaluation": "NOT_ESTABLISHED", "business_effect": "NOT_ESTABLISHED"}
    response["sections"].insert(1, section("table", reports["state"].lower(),
        title="当前报告版本评价检查分布", resource_type="report_evaluation_distribution",
        columns=[{"label": "状态", "key": "status"}, {"label": "检查数", "key": "count"}],
        rows=[{"status": status, "count": count} for status, count in counts.items()],
        basis=distribution))
    response["truth"]["evaluation_distribution"] = distribution
    # Serialize the original reports owner's authorization result, not a new grant.
    response["report_artifact_contract"] = "lumenis.bmp09-report-artifacts.v1"
    response["report_screen_binding"] = dict(binding)
    response["report_authorization"] = {"module": "reports", "action": "read", "context": dict(context)}
    response["saved_artifacts"] = [{"resource_type": "saved_work", **row} for row in rows]
    response["source_brief_artifacts"] = reports["items"]
    response["truth"]["market_effect_state"] = "NOT_ESTABLISHED"
    current_actor, current_scope = _bmp_saved_work_actor_scope(binding)
    if authorize(current_actor, current_scope, action="read") != context:
        raise PermissionError("BMP_REPORT_PRINCIPAL_CHANGED")
    return response


def _build_sh05() -> Dict[str, Any]:
    """Scoped learning candidates and reproducible measurements, never legacy scan lift."""
    from content_generation import read_pattern_learning_projection
    data = read_pattern_learning_projection()  # Permission/storage failures remain failures.
    rows = [{"标题": item["title"], "状态": item["state"], "评价次数": len(item["evaluations"]),
             "已生效": item["effective"], "模式": item["pattern_id"]} for item in data["items"]]
    kpis = [metric("sh05.count", "当前范围学习模式", value=data["count"], state=STATE_READY, icon="collection",
                   source=data["source"]),
            metric("sh05.effective", "当前有效模式", value=data["effective_count"], state=STATE_READY,
                   source=data["source"])]
    table = section("table", STATE_READY if rows else STATE_EMPTY, title="学习模式与评价",
                    columns=[{"label": key, "key": key} for key in ("标题", "状态", "评价次数", "已生效")], rows=rows)
    note = section("note", STATE_READY, kind="LEARNING-QUALIFICATION",
                   text="可复查保存产物、原始观察和计算方法。工程测量不等于独立业务增益；未满足保留集、真实任务及人工批准时不会晋升。")
    return _envelope("SH-05", [_head("SH-05"), section("kpis", STATE_READY, items=kpis), table, note],
                     truth={"learning_count": data["count"], "effective_count": data["effective_count"],
                            "business_lift_verified": data["business_lift_verified"]})


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


def _build_bmp03(*, binding=None) -> Dict[str, Any]:
    """Scoped market source observations; legacy unbound assets are not assigned."""
    from kos_engine import _read_scoped_canonical_material
    data = _read_scoped_canonical_material(binding)
    records = data["records"]
    rows = [{"id": row["canonical_id"], "title": row.get("title"),
             "platform": row.get("source_platform"), "source_type": row.get("source_type"),
             "scope_evidence": row["scope_evidence"]} for row in records]
    state = STATE_READY if rows else STATE_EMPTY
    result = _envelope("BMP-03", [_head("BMP-03"),
        _platform_collection_section(consumer="BMP", scoped_material=data),
        section("table", state, title="当前范围市场来源资料", columns=[
            {"label":"标题","key":"title"},{"label":"来源平台","key":"platform"},
            {"label":"来源类型","key":"source_type"}], rows=rows)],
        truth={"source_count":len(rows), "truncated":bool(data.get("truncated")),
            "legacy_asset_scope":"UNKNOWN_NOT_ASSIGNED", "classification":"source observations, not automatically verified market facts"})
    result["global_binding" if binding["canonical_scope"] == "GLOBAL_ALL" else "focus_binding"] = binding
    # A source-observation contract is distinct from analyzed market signals.
    # Permission comes from the request owner; source Evidence is not a grant.
    result["source_observation_contract"] = "lumenis.bmp03-source-observations.v1"
    result["source_read_binding"] = binding
    result["source_context"] = {"mode": binding["canonical_scope"], "domain_id": binding["domain_id"],
        "product_id": binding["product_id"], "subject_id": binding.get("subject_id"),
        "brand_focus_id": binding.get("brand_focus_id")}
    result["source_observations"] = rows
    result["truth"].update({"product_id": binding["product_id"], "domain_id": "zbmp",
        "data_state": "PARTIAL" if data.get("truncated") or data.get("rejected_count") else "READY" if rows else "EMPTY",
        "insight_state": "NOT_COMPUTED", "rejected_count": data.get("rejected_count", 0)})
    return result


def _build_bmp04(*, binding=None) -> Dict[str, Any]:
    import brand_propagation
    data = brand_propagation.read_scoped_propagation(binding)
    events = _events_items(_curated(data["events"]))
    event_state, event_read = _event_read_state(data["events"], events)
    state = "partial" if data["data_state"] == "PARTIAL" else STATE_READY if data["source_count"] or events else STATE_EMPTY
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import resolve_local_workspace_principal
    actor = resolve_local_workspace_principal(module="reports", action="read")
    if actor is None:
        actor = get_current_user(read_only=True)
    scope = {"domain_id": "zbmp", "subject_id": None,
             "brand_focus_id": binding.get("brand_focus_id"),
             "global_scope": binding["canonical_scope"] == "GLOBAL_ALL"}
    try:
        classification = brand_propagation.read_scoped_classifications(actor=actor, scope=scope)
    except (ValueError, PermissionError):
        classification = {"rows": [], "rejected": None, "state": "UNAVAILABLE"}
    # Counts describe only the current verified event sample, not the market population.
    event_ids = {item["id"] for item in data["events"].get("featured", [])}
    classified = [row for row in classification["rows"] if row["event"]["id"] in event_ids]
    unknown_count = len(event_ids - {row["event"]["id"] for row in classified})
    complete = data["event_read_complete"] and classification["state"] in {"READY", "EMPTY"} and not classification["rejected"]
    dashboards = []
    for category, title in (("brand_event", "品牌事件看板"), ("product_event", "产品事件看板"), ("industry_event", "行业事件看板")):
        selected = [row for row in classified if row["category"] == category]
        dashboards.append({"category": category, "title": title,
            "observed_events": len(selected), "total_events": len(selected) if complete and not unknown_count else None,
            "state": "ready" if selected and complete and not unknown_count else "empty" if complete and not unknown_count else "partial",
            "claim_type": "human_business_classification", "source_refs": [{"event_id": row["event"]["id"],
                "scope_evidence": row["source_evidence"]} for row in selected],
            "events": _events_items([row["event"] for row in selected])})
    data.update(total_events=data["event_returned_count"] if data["event_read_complete"] else None,
        total_events_semantics="current_verified_curated_sample_not_population", dashboards=dashboards,
        unclassified_event_count=unknown_count, classification_state=classification["state"],
        classification_rejected=classification["rejected"])
    response = _envelope("BMP-04", [_head("BMP-04"),
        section("kpis", state, items=[metric("bmp04.total", "已观测源记录", value=data["source_count"], state=state,
                source="brand_propagation.read_scoped_propagation", icon="trend"),
                metric("bmp04.events", "当前范围策展事件", value=data["event_returned_count"] if data["event_read_complete"] else None, state=state,
                source="database.get_events_curated", icon="event")]),
        section("events", event_state, items=events, read_status=event_read),
        section("table", "partial" if not complete or unknown_count else state, title="品牌 / 产品 / 行业事件看板",
                columns=[{"label": "看板", "key": "title"}, {"label": "已分类观测", "key": "observed_events"},
                         {"label": "范围内完整计数", "key": "total_events"}], rows=dashboards),
        section("table", state, title="源记录平台分布", columns=[{"label": "平台", "key": "platform"},
                {"label": "记录", "key": "count"}], rows=[{"platform": k, "count": v} for k,v in data["platform_counts"].items()])],
        truth={key: value for key, value in data.items() if key not in {"events", "source_observations"}})
    response["global_binding" if binding["canonical_scope"] == "GLOBAL_ALL" else "focus_binding"] = binding
    response["observation_contract"] = "lumenis.bmp04-source-observations.v1"
    response["observation_read_binding"] = binding
    response["observation_context"] = {key: binding.get(key) for key in
        ("domain_id", "product_id", "canonical_scope", "subject_id", "brand_focus_id", "actor_id")}
    response["source_observations"] = data["source_observations"]
    response["truth"].update({"domain_id": "zbmp", "product_id": binding["product_id"],
                              "analysis_state": "NOT_COMPUTED"})
    return response


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


def _build_bmp05(*, binding=None) -> Dict[str, Any]:
    """Scoped observed authors; identity, relationship and score remain unclaimed."""
    import kos_engine
    data = kos_engine.read_scoped_profiles(binding)
    rows = [{"name": row["author_nickname"] or row["author_id"],
             "platform": row["source_platform"], "type": row["identity_label"],
             "tier": row["kos_tier"], "score": row["kos_score"],
             "engagement": row["total_engagement"], "observed_records": row["note_count"],
             "source_refs": row["source_refs"]} for row in data["profiles"]]
    state = STATE_READY if rows else STATE_EMPTY
    response = _envelope("BMP-05", [_head("BMP-05"),
        section("kpis", state, items=[metric("bmp05.total", "已观测传播主体", value=data["total"], state=state,
                source="kos_engine.read_scoped_profiles", icon="creators")]),
        section("table", state, title="当前授权范围的源记录作者", columns=[
            {"label": "主体", "key": "name"}, {"label": "平台", "key": "platform"},
            {"label": "身份", "key": "type"}, {"label": "互动", "key": "engagement", "numeric": True}], rows=rows)],
        truth={key: value for key, value in data.items() if key != "profiles"})
    response["global_binding" if binding["canonical_scope"] == "GLOBAL_ALL" else "focus_binding"] = binding
    return response


def _build_bmp11(*, binding=None) -> Dict[str, Any]:
    import kos_intel
    data = kos_intel.read_scoped_benchmark(binding)
    rows = data["ranking"]
    state = STATE_READY if rows else STATE_EMPTY
    response = _envelope("BMP-11", [_head("BMP-11"),
        section("kpis", state, items=[metric("bmp11.entities", "可比较已观测品牌", value=len(rows), state=state,
                source="kos_intel.read_scoped_benchmark", icon="benchmark")]),
        section("table", state, title="授权品牌范围的源记录样本", columns=[
            {"label": "品牌范围", "key": "entity"}, {"label": "样本记录", "key": "record_count", "numeric": True},
            {"label": "互动", "key": "engagement", "numeric": True}], rows=rows)],
        truth={key: value for key, value in data.items() if key != "ranking"})
    response["global_binding" if binding["canonical_scope"] == "GLOBAL_ALL" else "focus_binding"] = binding
    return response


def _build_sh01() -> Dict[str, Any]:
    """内容创作工作室：呈现已登记能力与真实内容 Evidence，不生成示例内容。"""
    import content_generation

    context = content_generation.authorize_content_root_request(strict=True)
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
    result = _envelope("SH-01", sections, truth=None if failed else {"evidence_total": evidence.get("total", 0)})
    if content_generation.authorize_content_root_request(strict=True) != context:
        raise PermissionError("CONTENT_SCOPE_CHANGED")
    return result


def _browser_surface_markup() -> str:
    """真实 SYS-06 浏览表面。

    这里只声明现有 Browser Surface 控制器所需的 DOM 契约；标签页、导航、
    截图、历史、书签、AI Browser Session 和外部出口都仍由
    Flutter App 通过 Browser Surface API 消费，不复制浏览器后端。
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
        # 真实生产入口：复用 browser_surface 唯一后端与 App API 控制器。
        # 不把旧网页或 prototype example.com 作为 fallback。
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
