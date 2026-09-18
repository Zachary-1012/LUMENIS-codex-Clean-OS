# -*- coding: utf-8 -*-
"""
全网采集中心页面路由
页面仅负责渲染；采集/健康/任务数据全部走主蓝图 /v4/adapters/* 接口。
未登录跳转 V4 登录页，不返回白屏。
"""
import os
from flask import Blueprint, redirect, jsonify
from ..auth import get_current_user, ensure_initialized

collect_bp = Blueprint(
    "v4_collect", __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    url_prefix="/collect",
)


@collect_bp.before_request
def _ensure():
    ensure_initialized()


@collect_bp.route("/")
def collect_center():
    user = get_current_user()
    if not user:
        return redirect("/v4/settings/login")
    return jsonify({"ok": True, "ui_reset": True, "page": "collect", "user": user.get("username") if user else None})
