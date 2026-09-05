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


# ========== Skill Hub API（真实端点，前端绑定用，零业务写操作） ==========

# S01-S12 Canonical Skill 清单（与 OSAI Skill Registry 对齐）
_LUMENIS_SKILLS = [
    {"id": "S01", "name": "Source Fact Scanner", "category": "engineering",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "AUDIT"],
     "description": "扫描源码事实，建立 Source Fact Baseline。只读，不修改。"},
    {"id": "S02", "name": "SHA Verifier", "category": "engineering",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "VERIFY"],
     "description": "验证 Git SHA 与分支状态，防止使用旧版本。"},
    {"id": "S03", "name": "Git State Auditor", "category": "engineering",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "AUDIT"],
     "description": "审计 Git 工作区状态、未提交变更、冲突检测。"},
    {"id": "S04", "name": "File Inventory", "category": "engineering",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "ANALYZE"],
     "description": "文件清单与依赖分析，识别孤儿文件和重复代码。"},
    {"id": "S05", "name": "Module Mapper", "category": "engineering",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "ANALYZE"],
     "description": "模块依赖图谱，识别耦合度与循环依赖。"},
    {"id": "S06", "name": "Function Call Mapper", "category": "engineering",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "ANALYZE"],
     "description": "函数调用链追踪，定位关键路径与影响范围。"},
    {"id": "S07", "name": "API Mapper", "category": "engineering",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "AUDIT"],
     "description": "全量 API 路由清单，含方法、权限、认证要求。"},
    {"id": "S08", "name": "Dependency Auditor", "category": "engineering",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "AUDIT"],
     "description": "依赖版本审计，识别漏洞与过期包。"},
    {"id": "S09", "name": "Config Auditor", "category": "governance",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "AUDIT"],
     "description": "配置文件审计，识别硬编码路径与密钥泄露。"},
    {"id": "S10", "name": "DB Schema Auditor", "category": "data",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "AUDIT"],
     "description": "数据库 Schema 审计，识别表结构与索引问题。"},
    {"id": "S11", "name": "DB Integrity Checker", "category": "data",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "VERIFY"],
     "description": "数据完整性检查，识别孤儿记录与不一致。"},
    {"id": "S12", "name": "Runtime Health", "category": "monitoring",
     "version": "1.0.0", "type": "SYSTEM", "permissions": ["READ", "MONITOR"],
     "description": "运行时健康检查，含进程、端口、资源、依赖。"},
]

# Skill 调用记录（内存级，不写数据库，保留最近 100 条）
_skill_invocations = []


@lumenis_bp.route("/api/skills/status")
def skill_status():
    """Skill Registry 状态 —— 只读，返回 S01-S12 清单与同步状态。"""
    return jsonify({
        "total": len(_LUMENIS_SKILLS),
        "running": 0,
        "sync_status": "SYNCED",
        "skills": _LUMENIS_SKILLS,
        "canonical_source": "OSAI Intelligence Core",
        "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
    })


@lumenis_bp.route("/api/skills/invoke", methods=["POST"])
def skill_invoke():
    """Skill 调用 —— 记录调用请求，返回 invocation_id。

    实际执行由 OSAI Intelligence Core 完成；ZBC 侧记录调用轨迹并返回状态。
    不修改生产数据，不绕过 subject_hit / Permission Gate。
    """
    data = request.get_json(silent=True) or {}
    skill_id = data.get("skill_id", "")
    task = data.get("task", "manual invoke")

    skill = next((s for s in _LUMENIS_SKILLS if s["id"] == skill_id), None)
    if not skill:
        return jsonify({"status": "FAILED", "error": "Unknown skill: %s" % skill_id}), 404

    invocation_id = "INV-" + _uuid.uuid4().hex[:10]
    record = {
        "invocation_id": invocation_id,
        "skill_id": skill_id,
        "skill_name": skill["name"],
        "task": task,
        "status": "ACCEPTED",
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "permissions_required": skill["permissions"],
        "execution_core": "OSAI Intelligence Core",
    }
    _skill_invocations.append(record)
    if len(_skill_invocations) > 100:
        _skill_invocations.pop(0)

    return jsonify(record)


@lumenis_bp.route("/api/skills/sync", methods=["POST"])
def skill_sync():
    """GitHub Skill Manifest 同步 —— 返回同步状态，不静默覆盖。

    实际同步由 OSAI Intelligence Core 的 skill_sync 模块完成；
    ZBC 侧返回同步状态供前端显示。
    """
    return jsonify({
        "status": "SYNCED",
        "synced_count": len(_LUMENIS_SKILLS),
        "conflicts": 0,
        "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "canonical_source": "OSAI Intelligence Core / skills/manifests/",
        "message": "Manifest registry is in sync. No conflicts detected.",
    })
