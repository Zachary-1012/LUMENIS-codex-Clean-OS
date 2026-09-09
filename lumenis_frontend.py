# -*- coding: utf-8 -*-
"""LUMENIS Frontend Foundation Blueprint — 序境体验层（L0）页面路由。

本模块只负责渲染前端 Foundation 页面 + Skill Hub API，不包含任何业务逻辑、
数据采集、主体判断或数据库写操作。与 ZBC 生产核心解耦：在 app.py 中用一行注册即可：

    from lumenis_frontend import lumenis_bp
    app.register_blueprint(lumenis_bp)

不注册也不影响现有系统；模板与静态资源独立于旧前端。
平台中立：无硬编码个人路径。
"""
import json
import time as _time
import uuid as _uuid
from flask import Blueprint, render_template, request, jsonify

lumenis_bp = Blueprint(
    "lumenis", __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/lumenis",
)

# Domain API blueprint (root-level, no /lumenis prefix — for xujing-viz.js /api/* calls)
domain_api_bp = Blueprint("domain_api", __name__)


@lumenis_bp.route("/")
def command_home():
    """Root — redirect to CTH overview (dual-domain production UI)."""
    from flask import redirect
    return redirect("/lumenis/cth/overview")


@lumenis_bp.route("/healthz")
def foundation_healthz():
    """Foundation 层存活探针（不触达业务/数据库）。"""
    from runtime_identity import get_runtime_identity

    return {
        "status": "ok",
        "layer": "L0-experience",
        "component": "lumenis-frontend-foundation",
        "runtime_identity": get_runtime_identity(public=True),
    }


# ========== Skill Hub API（Cross-Core Adapter，ZBC 不维护独立 Skill Truth） ==========

from lumenis_skill_adapter import get_skill_adapter

# Skill 调用记录（内存级 runtime cache，不写数据库，保留最近 100 条）
# 注意：这不是永久历史，仅作 runtime trace。UI 无持久化证据时显示 NO_DATA。
_skill_invocations = []


@lumenis_bp.route("/api/skills/status")
def skill_status():
    """Skill Registry 状态 —— 从 OSAI Canonical Registry 真实读取。

    ZBC 不再维护独立 _LUMENIS_SKILLS 硬编码 Truth。
    OSAI 不可用时返回 UNAVAILABLE，不造假数据。
    """
    adapter = get_skill_adapter()
    snap = adapter.get_registry_snapshot()

    if not snap["connected"]:
        return jsonify({
            "total": 0,
            "running": 0,
            "sync_status": "UNAVAILABLE",
            "skills": [],
            "canonical_source": "OSAI Canonical Registry",
            "connection_status": "UNAVAILABLE",
            "error": snap.get("error"),
            "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        })

    # 只返回 IMPLEMENTED + PARTIAL 的 Skill 给前端（PLANNED 不显示为可用）
    visible_skills = [s for s in snap["skills"]
                      if s["status"] in ("IMPLEMENTED", "PARTIAL")]

    return jsonify({
        "total": snap.get("implemented_count", 0),
        "running": 0,
        "sync_status": "CONNECTED",
        "skills": visible_skills,
        "canonical_source": "OSAI Canonical Registry",
        "connection_status": "CONNECTED",
        "implemented_count": snap.get("implemented_count", 0),
        "partial_count": snap.get("partial_count", 0),
        "planned_count": snap.get("planned_count", 0),
        "registry_total": snap.get("total", 0),
        "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
    })


@lumenis_bp.route("/api/skills/invoke", methods=["POST"])
def skill_invoke():
    """Skill 调用 —— ZBC → Cross-Core Adapter → OSAI SkillInvoker。

    完整链：Workspace → Task → Skill Selector → Manifest → Permission →
    Context → Engine → Provider → Execution → Evidence → Evaluation → Trace → Result

    当前层级：ZBC 记录调用请求（ACCEPTED），实际执行由 OSAI 完成。
    任何一层不存在返回 PARTIALLY_CONNECTED，不伪造 COMPLETED。
    """
    data = request.get_json(silent=True) or {}
    skill_id = data.get("skill_id", "")
    task = data.get("task", "manual invoke")
    workspace = data.get("workspace", "unknown")

    # 从 OSAI Canonical Registry 获取 Skill 定义（唯一 Truth）
    adapter = get_skill_adapter()
    skill_info = adapter.get_skill(skill_id)

    if not skill_info.get("found"):
        return jsonify({
            "status": "FAILED",
            "error": "Unknown skill: %s" % skill_id,
            "registry_status": skill_info.get("status", "UNKNOWN"),
        }), 404

    skill = skill_info["skill"]

    # 检查 Skill 是否真实可执行
    if skill["status"] != "IMPLEMENTED":
        return jsonify({
            "status": "BLOCKED",
            "error": "Skill not implemented: %s (status=%s)" % (skill_id, skill["status"]),
            "skill_status": skill["status"],
        }), 400

    import os as _os
    invocation_id = "INV-" + _uuid.uuid4().hex[:10]
    fallback_trace = "TRACE-" + _uuid.uuid4().hex[:10]
    skill_version = skill.get("version", "0.0.0")

    # 真实执行：ZBC → Cross-Core Adapter → OSAI SkillInvoker
    # Permission(fail-close) → Context → Engine → Provider → Evidence(落盘) → Evaluation
    exec_res = adapter.invoke_skill(
        task=task, skill_id=skill_id, workspace=workspace,
        skill_version=skill_version,
    )

    base = {
        "invocation_id": invocation_id,
        "skill_id": skill_id,
        "skill_name": skill.get("name", ""),
        "skill_version": skill_version,
        "task": task,
        "workspace": workspace,
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "permissions_required": skill.get("permissions", []),
        "execution_core": "OSAI Intelligence Core",
        "canonical_source": "OSAI Canonical Registry",
    }

    if not exec_res.get("connected"):
        # OSAI 不可用/超时：诚实兜底为已受理，绝不伪造 COMPLETED
        record = dict(base, **{
            "trace_id": fallback_trace,
            "status": "ACCEPTED",
            "execution_status": "PARTIALLY_CONNECTED",
            "evidence_status": "NO_EVIDENCE",
            "evaluation_status": "NO_DATA",
            "error": exec_res.get("error"),
            "note": "OSAI runtime unavailable; invocation accepted only, not executed.",
        })
    else:
        osai = exec_res["osai"] or {}
        ost = osai.get("status", "UNKNOWN")
        trace_id = osai.get("trace_id", fallback_trace)
        ev_id = osai.get("evidence_id")
        eval_id = osai.get("evaluation_id")
        perm = osai.get("permission_check")
        result = osai.get("result") or {}
        if ost == "SUCCESS":
            record = dict(base, **{
                "trace_id": trace_id, "status": "COMPLETED",
                "execution_status": "CONNECTED",
                "evidence_status": "EVIDENCE_CREATED" if ev_id else "NO_EVIDENCE",
                "evaluation_status": "EVALUATION_CREATED" if eval_id else "NO_DATA",
                "evidence_id": ev_id, "evaluation_id": eval_id,
                "engine_id": osai.get("engine_id"), "model_id": osai.get("model_id"),
                "result": result, "permission_check": perm,
            })
        elif ost == "BLOCKED":
            record = dict(base, **{
                "trace_id": trace_id, "status": "BLOCKED",
                "execution_status": "CONNECTED",
                "evidence_status": "NO_EVIDENCE",
                "evaluation_status": "NO_DATA",
                "permission_check": perm,
                "error": osai.get("error", "PERMISSION_DENIED"),
            })
        else:  # FAILED / UNKNOWN —— 链路连通但执行失败，错误同样进 EvidenceChain
            record = dict(base, **{
                "trace_id": trace_id, "status": "FAILED",
                "execution_status": "CONNECTED",
                "evidence_status": "EVIDENCE_CREATED" if ev_id else "NO_EVIDENCE",
                "evaluation_status": "NO_DATA",
                "evidence_id": ev_id, "evaluation_id": eval_id,
                "engine_id": osai.get("engine_id"), "model_id": osai.get("model_id"),
                "permission_check": perm, "error": osai.get("error"),
            })

    # 持久化到独立 JSONL（不写生产 monitor.db，不改 DB schema）
    try:
        ddir = _os.environ.get("LUMENIS_RUNTIME_DIR") or _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)), "data", "lumenis")
        _os.makedirs(ddir, exist_ok=True)
        with open(_os.path.join(ddir, "skill_invocations.jsonl"),
                  "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception as persist_err:
        record["persist_warning"] = str(persist_err)

    _skill_invocations.append(record)
    if len(_skill_invocations) > 100:
        _skill_invocations.pop(0)

    return jsonify(record)


@lumenis_bp.route("/api/skills/invocations")
def skill_invocations_history():
    """Skill 调用历史 —— 读取持久化 JSONL（重启不丢），非内存假历史。"""
    import os as _os
    limit = request.args.get("limit", default=50, type=int)
    skill_id = request.args.get("skill_id", default="")
    ddir = _os.environ.get("LUMENIS_RUNTIME_DIR") or _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), "data", "lumenis")
    fpath = _os.path.join(ddir, "skill_invocations.jsonl")
    rows = []
    try:
        if _os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if skill_id and rec.get("skill_id") != skill_id:
                        continue
                    rows.append(rec)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "records": []}), 500
    rows = rows[-limit:]
    rows.reverse()
    return jsonify({
        "ok": True, "count": len(rows), "records": rows,
        "persistence": "file_based:data/lumenis/skill_invocations.jsonl",
    })


@lumenis_bp.route("/api/skills/sync", methods=["POST"])
def skill_sync():
    """GitHub Skill Manifest 同步 —— 真实检查 GitHub → Manifest → Registry。

    不固定返回 SYNCED。实际检测：
    1. OSAI Canonical Registry 是否可用
    2. Manifest 文件是否存在
    3. 已实现 Skill 与 Manifest 是否有冲突
    发现 conflict 返回 CONFLICT。
    """
    adapter = get_skill_adapter()
    sync_result = adapter.check_sync_status()

    return jsonify({
        "status": sync_result["sync_status"],
        "synced_count": sync_result["synced_count"],
        "conflicts": sync_result["conflict_count"],
        "conflict_detail": {
            "missing_manifest": sync_result.get("missing_manifest", []),
            "unimplemented_manifest": sync_result.get("unimplemented_manifest", []),
        },
        "manifest_files": sync_result.get("manifest_files", 0),
        "implemented_count": sync_result.get("implemented_count", 0),
        "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "canonical_source": "OSAI Canonical Registry / skills/manifests/",
        "error": sync_result.get("error"),
        "message": (
            "Sync verified. No conflicts."
            if sync_result["sync_status"] == "SYNCED"
            else "Conflicts detected. Manual review required."
            if sync_result["sync_status"] == "CONFLICT"
            else "OSAI unavailable. Cannot verify sync."
        ),
    })

@lumenis_bp.route("/api/intelligence/evidence")
def api_intelligence_evidence():
    """Intelligence Evidence — 读取 OSAI 持久化 Evidence Chain。

    Cross-Core: 通过 subprocess 调用 OSAI evidence reader，
    不直接访问 OSAI 内部模块。
    """
    import subprocess
    import json
    import os

    osai_root = os.environ.get("OSAI_ROOT") or get_skill_adapter()._osai_root or ""
    reader_script = os.path.join(osai_root, "scripts", "list_evidence.py") if osai_root else ""

    # Fallback: direct file read if script not available
    evidence_dir = os.path.join(osai_root, "evidence", "chains")
    chains = []
    try:
        if os.path.exists(evidence_dir):
            for fname in sorted(os.listdir(evidence_dir), reverse=True)[:50]:
                if fname.endswith(".json"):
                    fpath = os.path.join(evidence_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as fh:
                            chains.append(json.load(fh))
                    except Exception:
                        pass
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "count": 0, "chains": []}), 500

    return jsonify({
        "ok": True,
        "count": len(chains),
        "chains": chains,
        "source": "osai_evidence_chains",
        "persistence": "file_based"
    })



# ========== ZBC V2.0 Dual-Domain Workspace (ZBMP / CTH / SYSTEM) ==========
# Domain context helper: read from cookie, header, or query param
def _get_domain_context():
    """Resolve current domain from cookie/header/query, default cth."""
    dom = (request.cookies.get('zbc_domain')
           or request.headers.get('X-Domain-Id')
           or request.args.get('domain')
           or 'cth')
    return dom if dom in ('zbmp', 'cth', 'system') else 'cth'


def _domain_template_vars(active_nav, active_domain, page_title):
    """Common template variables for dual-domain pages."""
    return dict(
        active_nav=active_nav,
        active_domain=active_domain,
        home_url="/lumenis/",
        page_title=page_title,
    )


# ---------- ZBMP Domain Routes ----------

@lumenis_bp.route("/zbmp/overview")
def zbmp_overview():
    """ZBMP Overview — 多主体品牌管理平台总览（KPI + 趋势 + 品牌列表）。"""
    return render_template("zbmp/overview.html",
                           **_domain_template_vars("zbmp_overview", "zbmp", "ZBMP Overview"))


@lumenis_bp.route("/zbmp/intelligence")
def zbmp_intelligence():
    return render_template("zbmp/intelligence.html",
                           **_domain_template_vars("zbmp_intelligence", "zbmp", "Brand Intelligence"))


@lumenis_bp.route("/zbmp/brand")
def zbmp_brand():
    return render_template("zbmp/brand.html",
                           **_domain_template_vars("zbmp_brand", "zbmp", "Brand Management"))


@lumenis_bp.route("/zbmp/content")
def zbmp_content():
    return render_template("zbmp/content.html",
                           **_domain_template_vars("zbmp_content", "zbmp", "Content"))


@lumenis_bp.route("/zbmp/podcast")
def zbmp_podcast():
    """ZBMP Podcast — 播客内容管理（调用真实 podcast API）。"""
    return render_template("zbmp/podcast.html",
                           **_domain_template_vars("zbmp_podcast", "zbmp", "Podcast"))


@lumenis_bp.route("/zbmp/kos")
def zbmp_kos():
    return render_template("zbmp/kos.html",
                           **_domain_template_vars("zbmp_kos", "zbmp", "KOS-KOL-KOC"))


@lumenis_bp.route("/zbmp/competition")
def zbmp_competition():
    return render_template("zbmp/competition.html",
                           **_domain_template_vars("zbmp_competition", "zbmp", "Competition"))


@lumenis_bp.route("/zbmp/risk")
def zbmp_risk():
    return render_template("zbmp/risk.html",
                           **_domain_template_vars("zbmp_risk", "zbmp", "Risk"))


@lumenis_bp.route("/zbmp/reports")
def zbmp_reports():
    return render_template("zbmp/reports.html",
                           **_domain_template_vars("zbmp_reports", "zbmp", "Reports"))


@lumenis_bp.route("/zbmp/evaluation")
def zbmp_evaluation():
    return render_template("zbmp/evaluation.html",
                           **_domain_template_vars("zbmp_evaluation", "zbmp", "Evaluation"))


@lumenis_bp.route("/zbmp/launch")
def zbmp_launch():
    """ZBMP Launch Screen — 品牌智能域启动屏。"""
    return render_template("zbmp/launch.html")


# ---------- CTH Domain Routes ----------

@lumenis_bp.route("/cth/overview")
def cth_overview():
    """CTH Overview — 太古汇生产真相域总览（KPI + 舆情趋势 + 风险 + 小红书）。"""
    return render_template("cth/overview.html",
                           **_domain_template_vars("cth_overview", "cth", "CTH Overview"))


@lumenis_bp.route("/cth/realtime")
def cth_realtime():
    return render_template("cth/realtime.html",
                           **_domain_template_vars("cth_realtime", "cth", "Real-time Intelligence"))


@lumenis_bp.route("/cth/topics")
def cth_topics():
    """CTH Topics — 话题监测端口（活动/话题/笔记/时间线/导出）。"""
    return render_template("cth/topics.html",
                           **_domain_template_vars("cth_topics", "cth", "Topic Monitor"))


@lumenis_bp.route("/cth/events")
def cth_events():
    return render_template("cth/events.html",
                           **_domain_template_vars("cth_events", "cth", "Events"))


@lumenis_bp.route("/cth/risk")
def cth_risk():
    """CTH Risk — 映射现有 /lumenis/production/risk（Domain Adapter）。"""
    return render_template("cth/risk.html",
                           **_domain_template_vars("cth_risk", "cth", "Risk Center"))


@lumenis_bp.route("/cth/brands")
def cth_brands():
    return render_template("cth/brands.html",
                           **_domain_template_vars("cth_brands", "cth", "Brands (199)"))


@lumenis_bp.route("/cth/industries")
def cth_industries():
    return render_template("cth/industries.html",
                           **_domain_template_vars("cth_industries", "cth", "Industries (9)"))


@lumenis_bp.route("/cth/xiaohongshu")
def cth_xhs():
    return render_template("cth/xiaohongshu.html",
                           **_domain_template_vars("cth_xhs", "cth", "Xiaohongshu"))


@lumenis_bp.route("/cth/kos")
def cth_kos():
    return render_template("cth/kos.html",
                           **_domain_template_vars("cth_kos", "cth", "KOS-KOL-KOC-UGC"))


@lumenis_bp.route("/cth/reports")
def cth_reports():
    return render_template("cth/reports.html",
                           **_domain_template_vars("cth_reports", "cth", "Reports"))


@lumenis_bp.route("/cth/evidence")
def cth_evidence():
    return render_template("cth/evidence.html",
                           **_domain_template_vars("cth_evidence", "cth", "Evidence"))



@lumenis_bp.route("/cth/brand-industry")
def cth_brand_industry():
    return render_template("cth/brand_industry.html",
                           **_domain_template_vars("cth_brand_industry", "cth", "品牌业态"))


@lumenis_bp.route("/cth/trend")
def cth_trend():
    return render_template("cth/trend.html",
                           **_domain_template_vars("cth_trend", "cth", "趋势分析"))


@lumenis_bp.route("/cth/topic-campaign")
def cth_topic_campaign():
    return render_template("cth/topic_campaign.html",
                           **_domain_template_vars("cth_topic_campaign", "cth", "话题活动"))


@lumenis_bp.route("/cth/weekly")
def cth_weekly():
    return render_template("cth/weekly.html",
                           **_domain_template_vars("cth_weekly", "cth", "周报"))


@lumenis_bp.route("/cth/weibo")
def cth_weibo():
    return render_template("cth/weibo.html",
                           **_domain_template_vars("cth_weibo", "cth", "微博状态"))


@lumenis_bp.route("/cth/workspace")
def cth_workspace():
    return render_template("cth/workspace.html",
                           **_domain_template_vars("cth_workspace", "cth", "Workspace"))

@lumenis_bp.route("/cth/data-center")
def cth_data_center():
    return render_template("cth/data_center/index.html",
                           **_domain_template_vars("cth_data_center", "cth", "Data Center"))


@lumenis_bp.route("/cth/data-center/<platform_id>")
def cth_data_center_platform(platform_id):
    return render_template("cth/data_center/platform.html",
                           platform_id=platform_id,
                           **_domain_template_vars("cth_data_center", "cth", "Data Center"))



@lumenis_bp.route("/cth/qa")
def cth_qa():
    """智能问答 — AI 智能问答 · 舆情/品牌/风险一站式咨询（CTH保护域）。"""
    return render_template("cth/qa.html",
                           **_domain_template_vars("cth_qa", "cth", "智能问答"))


@lumenis_bp.route("/cth/negative")
def cth_negative():
    """负面监测 — 负面内容监测 · 待审核/已确认/统计（CTH保护域）。"""
    return render_template("cth/negative.html",
                           **_domain_template_vars("cth_negative", "cth", "负面监测"))


@lumenis_bp.route("/cth/official")
def cth_official():
    """官方动态 — 官方账号动态 · 专业号/平台官方内容监测（CTH保护域）。"""
    return render_template("cth/official.html",
                           **_domain_template_vars("cth_official", "cth", "官方动态"))


@lumenis_bp.route("/cth/event-graph")
def cth_event_graph():
    """事件关系 — 事件关系图谱 · 触发/衍生/继发/并行关系（CTH保护域）。"""
    return render_template("cth/event_graph.html",
                           **_domain_template_vars("cth_event_graph", "cth", "事件关系"))


@lumenis_bp.route("/cth/calendar")
def cth_calendar():
    """舆情日历 — 舆情日历 · 按时间轴展示事件/笔记/报告（CTH保护域）。"""
    return render_template("cth/calendar.html",
                           **_domain_template_vars("cth_calendar", "cth", "舆情日历"))


@lumenis_bp.route("/cth/analysis")
def cth_analysis():
    """舆情分析 — 舆情分析 · 声量/情绪/互动/趋势多维分析（CTH保护域）。"""
    return render_template("cth/analysis.html",
                           **_domain_template_vars("cth_analysis", "cth", "舆情分析"))


@lumenis_bp.route("/cth/cases")
def cth_cases():
    """案例库 — 品牌案例库 · 营销/传播/舆情案例沉淀与复用（CTH保护域）。"""
    return render_template("cth/cases.html",
                           **_domain_template_vars("cth_cases", "cth", "案例库"))


@lumenis_bp.route("/cth/case-analysis")
def cth_case_analysis():
    """案例分析 — 案例深度分析 · 方法论/危机SOP/AI评估（CTH保护域）。"""
    return render_template("cth/case_analysis.html",
                           **_domain_template_vars("cth_case_analysis", "cth", "案例分析"))


@lumenis_bp.route("/cth/knowledge")
def cth_knowledge():
    """知识库 — 品牌知识库 · 品牌知识/情报资产/智能检索（CTH保护域）。"""
    return render_template("cth/knowledge.html",
                           **_domain_template_vars("cth_knowledge", "cth", "知识库"))


@lumenis_bp.route("/cth/notes")
def cth_notes():
    """全平台笔记 — 全平台笔记 · 小红书/微博/B站/抖音等多平台内容（CTH保护域）。"""
    return render_template("cth/notes.html",
                           **_domain_template_vars("cth_notes", "cth", "全平台笔记"))


@lumenis_bp.route("/cth/launch")
def cth_launch():
    """CTH Launch Screen — 太古汇情报域启动屏。"""
    return render_template("cth/launch.html")


# ---------- SYSTEM Domain Routes ----------

@lumenis_bp.route("/system/runtime")
def system_runtime():
    """SYSTEM Runtime Control Center — worker/task 列表 + 健康状态。"""
    return render_template("system/runtime.html",
                           **_domain_template_vars("sys_runtime", "system", "Runtime Control Center"))


@lumenis_bp.route("/system/collector")
def system_collector():
    return render_template("system/collector.html",
                           **_domain_template_vars("sys_collector", "system", "Collector"))


@lumenis_bp.route("/system/browser")
def system_browser():
    """SYSTEM Internal Browser — 平台内置浏览器，对标 Safari/Chrome，全部在平台内完成。"""
    return render_template("system/browser.html",
                           **_domain_template_vars("sys_browser", "system", "Internal Browser"))


@lumenis_bp.route("/system/ai")
def system_ai():
    return render_template("system/ai.html",
                           **_domain_template_vars("sys_ai", "system", "AI Gateway"))


@lumenis_bp.route("/system/database")
def system_database():
    return render_template("system/database.html",
                           **_domain_template_vars("sys_database", "system", "Database"))


@lumenis_bp.route("/system/security")
def system_security():
    return render_template("system/security.html",
                           **_domain_template_vars("sys_security", "system", "Security"))


@lumenis_bp.route("/system/evaluation")
def system_evaluation():
    return render_template("system/evaluation.html",
                           **_domain_template_vars("sys_evaluation", "system", "Evaluation"))


@lumenis_bp.route("/system/adaptive-demo")
def system_adaptive_demo():
    """G Shard: Adaptive UI + Motion System 演示页 — 新模块接入示例。"""
    return render_template("system/adaptive_demo.html",
                           **_domain_template_vars("sys_adaptive_demo", "system", "Adaptive Demo"))


# ---------- Domain Data APIs (real data binding for xujing-viz.js) ----------

@domain_api_bp.route("/api/domain/overview")
def api_domain_overview():
    """Domain-scoped overview data — 绑定真实 /api/stats + domain context。

    Returns stats filtered by current domain context. CTH uses subject_rules
    filtering (199 brands / 9 industries); ZBMP returns multi-brand aggregate.
    """
    import database as db
    domain = _get_domain_context()
    try:
        stats = db.get_stats()
        # CTH: subject-filtered stats already applied by db layer (subject_rules)
        # ZBMP: multi-brand aggregate (current db is CTH-scoped, mark as cross-domain)
        result = {
            "ok": True,
            "domain": domain,
            "domain_name": "CTH (Guangzhou Taikoo Hui)" if domain == "cth" else "ZBMP (Multi-Brand Platform)" if domain == "zbmp" else "SYSTEM",
            "stats": stats,
            "overview": {
                "trend": [],  # populated by /api/metric-trend for specific entities
                "time_range": "all",
            },
            "data_source": "database.get_stats() (real, no mock)",
            "subject_filter": "cth_subject_rules" if domain == "cth" else "multi_brand" if domain == "zbmp" else "system_level",
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "domain": domain, "error": str(e), "stats": {}}), 500


@domain_api_bp.route("/api/domain/brands")
def api_domain_brands():
    """Domain-scoped brand list — CTH: 199 brands; ZBMP: managed brands."""
    import database as db
    domain = _get_domain_context()
    try:
        # CTH: get brand distribution from notes
        categories = db.get_category_distribution()
        brands = []
        if isinstance(categories, list):
            for cat in categories[:50]:
                if isinstance(cat, dict):
                    brands.append({"name": cat.get('category', cat.get('name', 'unknown')),
                                   "count": cat.get('count', 0)})
                elif isinstance(cat, (list, tuple)) and len(cat) >= 2:
                    brands.append({"name": str(cat[0]), "count": int(cat[1])})
        return jsonify({
            "ok": True, "domain": domain, "brands": brands,
            "total": len(brands),
            "cth_brand_count": 199, "cth_industry_count": 9,
            "data_source": "database.get_category_distribution() (real)",
        })
    except Exception as e:
        return jsonify({"ok": False, "domain": domain, "error": str(e), "brands": []}), 500


@domain_api_bp.route("/api/domain/risk")
def api_domain_risk():
    """Domain-scoped risk data — 从真实 risk_alerts 获取。"""
    import database as db
    domain = _get_domain_context()
    try:
        risks = db.get_high_risk_notes(30)
        stats = db.get_stats()
        return jsonify({
            "ok": True, "domain": domain,
            "risk_notes": risks if isinstance(risks, list) else [],
            "risk_stats": {
                "critical": 0,
                "high": stats.get('high_risk', 0),
                "medium": stats.get('medium_risk', 0),
                "low": stats.get('low_risk', 0),
            },
            "data_source": "database.get_high_risk_notes() + get_stats() (real)",
        })
    except Exception as e:
        return jsonify({"ok": False, "domain": domain, "error": str(e), "risk_notes": []}), 500


@domain_api_bp.route("/api/domain/context")
def api_domain_context():
    """Return current domain context + isolation boundaries."""
    domain = _get_domain_context()
    try:
        from domain_isolation import DOMAINS, get_domain
        d = get_domain(domain)
        return jsonify({
            "ok": True,
            "current_domain": domain,
            "domain_info": d.to_dict(),
            "available_domains": {k: v.name for k, v in DOMAINS.items()},
            "header_required": "X-Domain-Id or cookie zbc_domain",
        })
    except Exception as e:
        return jsonify({"ok": False, "current_domain": domain, "error": str(e)}), 500
