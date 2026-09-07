# -*- coding: utf-8 -*-
"""
Adaptive UI Routes — 自适应 UI Flask 蓝图
=========================================
提供自适应面板的 HTTP API：
  GET  /api/agent/adaptive-panel/<run_id>           : 返回面板 JSON
  GET  /api/agent/adaptive-panel/<run_id>/refresh   : 强制刷新

路由内做异常处理，失败返回 {error: ..., panels: []}，不抛 500。

设计原则：
  - 只读：不修改任何现有生产数据
  - 异常降级：任何内部错误都返回结构化错误，不中断服务
  - 可追溯：每次请求记录 run_id 和生成时间
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from .panel import get_adaptive_panel

logger = logging.getLogger(__name__)

adaptive_ui_bp = Blueprint(
    "adaptive_ui",
    __name__,
    url_prefix="/api/agent",
)


def _error_response(run_id: str, error_msg: str, status_code: int = 200):
    """构造错误响应（不抛 500，返回结构化错误）。"""
    logger.warning("adaptive_ui error for run_id=%s: %s", run_id, error_msg)
    return jsonify({
        "run_id": run_id,
        "error": error_msg,
        "panels": [],
        "count": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }), status_code


@adaptive_ui_bp.route("/adaptive-panel/<run_id>", methods=["GET"])
def get_panel(run_id: str):
    """获取指定 Agent Run 的自适应面板。

    支持通过 query 参数传递 run_state（JSON 字符串），或从请求体获取。
    若未提供 run_state，则返回缓存或基于空状态生成。

    Args:
        run_id: Agent Run 唯一标识

    Returns:
        JSON: {run_id, generated_at, panels, count, cached}
    """
    try:
        run_state: Dict[str, Any] = {}

        # 1. 从 query 参数获取 state（JSON 字符串）
        state_param = request.args.get("state")
        if state_param:
            import json
            try:
                run_state = json.loads(state_param)
            except (json.JSONDecodeError, ValueError) as e:
                return _error_response(run_id, f"invalid state parameter: {e}")

        # 2. 从 JSON body 获取
        if not run_state and request.is_json:
            body = request.get_json(silent=True)
            if isinstance(body, dict):
                run_state = body.get("run_state", body)

        result = get_adaptive_panel(run_id, run_state if run_state else None)
        return jsonify(result)

    except Exception as e:
        return _error_response(run_id, f"unexpected error: {str(e)[:200]}")


@adaptive_ui_bp.route("/adaptive-panel/<run_id>/refresh", methods=["GET"])
def refresh_panel(run_id: str):
    """强制刷新指定 Agent Run 的自适应面板（清除缓存后重新生成）。

    Args:
        run_id: Agent Run 唯一标识

    Returns:
        JSON: {run_id, generated_at, panels, count, cached: false}
    """
    try:
        from .panel import _get_generator
        generator = _get_generator()
        generator.invalidate_cache(run_id)

        run_state: Dict[str, Any] = {}

        state_param = request.args.get("state")
        if state_param:
            import json
            try:
                run_state = json.loads(state_param)
            except (json.JSONDecodeError, ValueError) as e:
                return _error_response(run_id, f"invalid state parameter: {e}")

        if not run_state and request.is_json:
            body = request.get_json(silent=True)
            if isinstance(body, dict):
                run_state = body.get("run_state", body)

        result = get_adaptive_panel(run_id, run_state if run_state else None)
        result["refreshed"] = True
        return jsonify(result)

    except Exception as e:
        return _error_response(run_id, f"refresh failed: {str(e)[:200]}")


@adaptive_ui_bp.route("/adaptive-panel/types", methods=["GET"])
def list_panel_types():
    """列出支持的面板类型（供前端动态渲染参考）。"""
    try:
        from .panel import PanelType
        return jsonify({
            "panel_types": [
                {"key": pt.name, "value": pt.value}
                for pt in PanelType
            ],
            "component_types": ["metric", "list", "chart", "button", "text", "table"],
        })
    except Exception as e:
        return _error_response("types", f"unexpected error: {str(e)[:200]}")
