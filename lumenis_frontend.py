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
