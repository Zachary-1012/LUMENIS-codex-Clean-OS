# -*- coding: utf-8 -*-
"""统一控制台路由：/v4/ 与 /v4/console/ 进入单页控制台。未登录跳 V4 登录页。"""
import os
from flask import Blueprint, redirect, render_template
from ..auth import get_current_user, ensure_initialized

console_bp = Blueprint(
    "v4_console", __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
)


@console_bp.before_request
def _ensure():
    ensure_initialized()


@console_bp.route("/")
def v4_root():
    return redirect("/v4/console/")


@console_bp.route("/console/")
def console_home():
    user = get_current_user()
    if not user:
        return redirect("/v4/settings/login")
    return render_template("console.html", current_user=user)
