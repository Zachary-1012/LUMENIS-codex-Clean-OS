# -*- coding: utf-8 -*-
"""LUMENIS Frontend Foundation Blueprint — 序境体验层（L0）页面路由。

本模块只负责渲染前端 Foundation 页面，不包含任何业务逻辑、数据采集、
主体判断或数据库写操作。与 ZBC 生产核心解耦：在 app.py 中用一行注册即可：

    from lumenis_frontend import lumenis_bp
    app.register_blueprint(lumenis_bp)

不注册也不影响现有系统；模板与静态资源独立于旧前端。
平台中立：无硬编码个人路径。
"""
from flask import Blueprint, render_template

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
