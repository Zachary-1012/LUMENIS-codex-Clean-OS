# -*- coding: utf-8 -*-
"""
Agent Proactive Routes — Flask 蓝图
====================================
提供主动式协助的 HTTP API：
  - GET  /api/agent/proactive/signals            : 获取当前信号列表
  - POST /api/agent/proactive/approve/<action_id> : 批准建议动作

设计原则：
  - 只读信号查询，不自动执行任何操作
  - 审批接口仅修改内存中 SuggestedAction 状态，不直接触发执行
  - 不绕过 Permission / Action Firewall
  - 所有响应可序列化、可追踪
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

try:
    from flask import Blueprint, jsonify, request
except ImportError:  # pragma: no cover - Flask 缺失时降级
    Blueprint = None  # type: ignore

from .detector import SignalDetector, Signal, detect_signals
from .suggestion import (
    SuggestionGenerator, SuggestedAction, ApprovalFlow,
    ApprovalStatus,
)


# 内存存储（生产环境可替换为 DB 持久化）
_signals_store: List[Signal] = []
_actions_store: Dict[str, SuggestedAction] = {}
_store_lock = threading.Lock()

_detector = SignalDetector()
_generator = SuggestionGenerator()


def _build_blueprint() -> Optional["Blueprint"]:
    """构建 Flask 蓝图。Flask 不可用时返回 None。"""
    if Blueprint is None:
        return None

    bp = Blueprint("agent_proactive", __name__, url_prefix="/api/agent/proactive")

    @bp.route("/signals", methods=["GET"])
    def list_signals():
        """获取当前信号列表。

        支持查询参数：
          - severity: 按严重度过滤（info/warning/critical）
          - type: 按信号类型过滤
          - limit: 返回数量上限（默认 50）
        """
        global _signals_store

        # 可选：从 query context 实时检测
        context_param = request.args.get("context")
        if context_param:
            try:
                import json
                ctx = json.loads(context_param)
                fresh = _detector.detect_signals(ctx)
                with _store_lock:
                    _signals_store = fresh
            except Exception:
                pass

        with _store_lock:
            signals = list(_signals_store)

        severity_filter = request.args.get("severity", "").lower()
        type_filter = request.args.get("type", "").lower()
        limit = request.args.get("limit", default=50, type=int)

        if severity_filter:
            signals = [s for s in signals if s.severity == severity_filter]
        if type_filter:
            signals = [s for s in signals if s.signal_type == type_filter]

        signals = signals[:limit]

        return jsonify({
            "ok": True,
            "count": len(signals),
            "signals": [s.to_dict() for s in signals],
        })

    @bp.route("/detect", methods=["POST"])
    def detect():
        """主动触发一次信号检测。

        Request Body: JSON 格式的 context 字典
        Response: 检测到的信号列表 + 生成的建议
        """
        global _signals_store, _actions_store

        context = request.get_json(silent=True) or {}
        signals = _detector.detect_signals(context)
        actions = _generator.generate_batch(signals)

        with _store_lock:
            _signals_store = signals
            for act in actions:
                _actions_store[act.action_id] = act

        return jsonify({
            "ok": True,
            "signal_count": len(signals),
            "action_count": len(actions),
            "signals": [s.to_dict() for s in signals],
            "actions": [a.to_dict() for a in actions],
        })

    @bp.route("/approve/<action_id>", methods=["POST"])
    def approve_action(action_id: str):
        """批准建议动作。

        Request Body (可选):
          - approver: 审批人标识
          - note: 审批备注

        注意：本接口仅修改审批状态，不直接执行动作。
        执行需由调用方在获取 APPROVED 状态后，经 Permission Gate 触发。
        """
        global _actions_store

        with _store_lock:
            action = _actions_store.get(action_id)

        if action is None:
            return jsonify({"ok": False, "error": f"action not found: {action_id}"}), 404

        body = request.get_json(silent=True) or {}
        approver = str(body.get("approver", ""))
        note = str(body.get("note", ""))

        try:
            flow = ApprovalFlow(action)
            flow.approve(approver=approver, note=note)
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 409

        with _store_lock:
            _actions_store[action_id] = action

        return jsonify({
            "ok": True,
            "action_id": action_id,
            "status": action.approval_status,
            "approved_by": action.approved_by,
            "approved_at": action.approved_at,
        })

    @bp.route("/reject/<action_id>", methods=["POST"])
    def reject_action(action_id: str):
        """拒绝建议动作。"""
        global _actions_store

        with _store_lock:
            action = _actions_store.get(action_id)

        if action is None:
            return jsonify({"ok": False, "error": f"action not found: {action_id}"}), 404

        body = request.get_json(silent=True) or {}
        reason = str(body.get("reason", ""))
        rejecter = str(body.get("rejecter", ""))

        try:
            flow = ApprovalFlow(action)
            flow.reject(reason=reason, rejecter=rejecter)
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 409

        with _store_lock:
            _actions_store[action_id] = action

        return jsonify({
            "ok": True,
            "action_id": action_id,
            "status": action.approval_status,
            "rejected_reason": action.rejected_reason,
        })

    @bp.route("/actions", methods=["GET"])
    def list_actions():
        """获取建议动作列表。"""
        global _actions_store

        with _store_lock:
            actions = list(_actions_store.values())

        status_filter = request.args.get("status", "").lower()
        if status_filter:
            actions = [a for a in actions if a.approval_status == status_filter]

        return jsonify({
            "ok": True,
            "count": len(actions),
            "actions": [a.to_dict() for a in actions],
        })

    return bp


# 模块级蓝图实例（供 app.register_blueprint 使用）
proactive_bp = _build_blueprint()


def register_proactive_routes(app) -> bool:
    """将主动式协助蓝图注册到 Flask 应用。

    Args:
        app: Flask 应用实例

    Returns:
        True 注册成功，False 失败（Flask 不可用或蓝图构建失败）
    """
    if proactive_bp is None:
        return False
    try:
        app.register_blueprint(proactive_bp)
        return True
    except Exception:
        return False


def get_stored_signals() -> List[Signal]:
    """获取当前内存中存储的信号（供测试与内部调用）。"""
    with _store_lock:
        return list(_signals_store)


def get_stored_action(action_id: str) -> Optional[SuggestedAction]:
    """获取指定建议动作（供测试与内部调用）。"""
    with _store_lock:
        return _actions_store.get(action_id)


def clear_store() -> None:
    """清空内存存储（仅测试用）。"""
    global _signals_store, _actions_store
    with _store_lock:
        _signals_store = []
        _actions_store = {}
