# -*- coding: utf-8 -*-
"""LUMENIS Frontend Foundation Blueprint — 序境体验层（L0）页面路由。

本模块只负责渲染前端 Foundation 页面 + Skill Hub API，不包含任何业务逻辑、
数据采集、主体判断或数据库写操作。与 ZBC 生产核心解耦：在 app.py 中用一行注册即可：

    from lumenis_frontend import lumenis_bp
    app.register_blueprint(lumenis_bp)

不注册也不影响现有系统；模板与静态资源独立于旧前端。
平台中立：无硬编码个人路径。
"""
import time as _time
import uuid as _uuid
from flask import Blueprint, render_template, request, jsonify

lumenis_bp = Blueprint(
    "lumenis", __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/lumenis",
)


@lumenis_bp.route("/")
def command_home():
    """Command Home —— 全局入口（非 Dashboard），六区结构。"""
    return render_template("home/command_home.html", active_nav="home",
                           home_url="/lumenis/")


@lumenis_bp.route("/healthz")
def foundation_healthz():
    """Foundation 层存活探针（不触达业务/数据库）。"""
    return {"status": "ok", "layer": "L0-experience", "component": "lumenis-frontend-foundation"}


# ========== P0 页面（真实只读 API 绑定，零业务写操作） ==========

@lumenis_bp.route("/intelligence")
def intelligence_workspace():
    """Intelligence Workspace — AI 工作区（Input→Context→Retrieval→Reasoning→Evidence→Action）。"""
    return render_template("intelligence/workspace.html", active_nav="ai",
                           home_url="/lumenis/")


@lumenis_bp.route("/production")
def production_overview():
    """Production Overview — 生产总览（核心指标 + 采集健康 + 主体口径）。"""
    return render_template("production/overview.html", active_nav="production",
                           home_url="/lumenis/")


@lumenis_bp.route("/production/public-opinion")
def public_opinion():
    """Public Opinion — 舆情总览（情感分布 + 风险笔记 + 话题）。"""
    return render_template("production/public_opinion.html", active_nav="opinion",
                           home_url="/lumenis/")


@lumenis_bp.route("/production/risk")
def risk():
    """Risk — 风险预警中心（高/中风险笔记全量 + 风险等级分布）。"""
    return render_template("production/risk.html", active_nav="risk",
                           home_url="/lumenis/")


@lumenis_bp.route("/operations")
def operations():
    """Operations — 系统运维（健康四灯 + 采集状态 + AI 通道 + 运行时）。"""
    return render_template("operations/index.html", active_nav="operations",
                           home_url="/lumenis/")


# ========== PHASE 3 页面（Intelligence 子域 + Research） ==========

@lumenis_bp.route("/intelligence/skills")
def skill_hub():
    """Skill Hub — 能力中心（S01-S12 已落地，S13-S72 规划中）。"""
    return render_template("intelligence/skill_hub.html", active_nav="skills",
                           home_url="/lumenis/")


@lumenis_bp.route("/intelligence/agents")
def agent_center():
    """Agent Center — 代理中心（Orchestrator/Research/Engineering/Evaluation）。"""
    return render_template("intelligence/agent_center.html", active_nav="agents",
                           home_url="/lumenis/")


@lumenis_bp.route("/intelligence/evaluation")
def evaluation_center():
    """Evaluation Center — 评估中心（Correctness/Completeness/Regression/Safety）。"""
    return render_template("intelligence/evaluation.html", active_nav="evaluation",
                           home_url="/lumenis/")


@lumenis_bp.route("/research")
def research_workspace():
    """Research Workspace — 研究工作区（Research→Finding→Evidence→Decision→Proposal）。"""
    return render_template("research/workspace.html", active_nav="research",
                           home_url="/lumenis/")


# ========== P1 全产品页面（LUMENIS Full Product Visual Foundation） ==========

@lumenis_bp.route("/intelligence/models")
def models():
    """Models / AI Gateway — 模型与引擎管理（Provider-agnostic）。"""
    return render_template("intelligence/models.html", active_nav="models",
                           home_url="/lumenis/")


@lumenis_bp.route("/intelligence/evidence")
def evidence():
    """Evidence Center — 证据中心（Evidence Chain + Trace）。"""
    return render_template("intelligence/evidence.html", active_nav="evidence",
                           home_url="/lumenis/")


@lumenis_bp.route("/production/monitoring")
def monitoring():
    """Monitoring — 生产监控（Collector + Runtime + Risk）。"""
    return render_template("production/monitoring.html", active_nav="monitoring",
                           home_url="/lumenis/")


@lumenis_bp.route("/production/cases")
def cases():
    """Case Library — 案例库（统一 Case Intelligence 入口）。"""
    return render_template("production/cases.html", active_nav="cases",
                           home_url="/lumenis/")


@lumenis_bp.route("/production/reports")
def reports():
    """Reports — 报告中心（日报/周报/月报/综合报告）。"""
    return render_template("production/reports.html", active_nav="reports",
                           home_url="/lumenis/")


@lumenis_bp.route("/research/findings")
def findings():
    """Research Findings — 研究发现（Finding Pipeline）。"""
    return render_template("research/findings.html", active_nav="findings",
                           home_url="/lumenis/")


@lumenis_bp.route("/operations/runtime")
def runtime():
    """Runtime — 运行时（Local Runtime + Health Check）。"""
    return render_template("operations/runtime.html", active_nav="runtime",
                           home_url="/lumenis/")


@lumenis_bp.route("/operations/permissions")
def permissions():
    """Permissions & Audit — 权限与审计（Permission Gate + Identity + Delegation）。"""
    return render_template("operations/permissions.html", active_nav="permissions",
                           home_url="/lumenis/")


@lumenis_bp.route("/operations/repository")
def repository():
    """Repository Registry — 仓库注册（ZBC + OSAI 双核状态）。"""
    return render_template("operations/repository.html", active_nav="repository",
                           home_url="/lumenis/")


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

    invocation_id = "INV-" + _uuid.uuid4().hex[:10]
    trace_id = "TRACE-" + _uuid.uuid4().hex[:10]

    record = {
        "invocation_id": invocation_id,
        "trace_id": trace_id,
        "skill_id": skill_id,
        "skill_name": skill.get("name", ""),
        "skill_version": skill.get("version", "0.0.0"),
        "task": task,
        "workspace": workspace,
        "status": "ACCEPTED",
        "execution_status": "PARTIALLY_CONNECTED",
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "permissions_required": skill.get("permissions", []),
        "execution_core": "OSAI Intelligence Core",
        "canonical_source": "OSAI Canonical Registry",
        "evidence_status": "NO_EVIDENCE",
        "evaluation_status": "NO_DATA",
        "note": "Invocation accepted by ZBC adapter. Full execution chain (Engine→Provider→Evidence→Evaluation) requires OSAI runtime integration.",
    }
    _skill_invocations.append(record)
    if len(_skill_invocations) > 100:
        _skill_invocations.pop(0)

    return jsonify(record)


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
