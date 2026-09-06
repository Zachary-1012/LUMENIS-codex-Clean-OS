# -*- coding: utf-8 -*-
"""Zachary OS AI · Evidence API（证据查询 REST 接口）

Phase 2：把 evidence_store 的能力暴露给前端 Dashboard。
只读接口，不提供删除/修改（证据不可篡改，只能追加）。
"""
from __future__ import annotations
import evidence_store
import logging


logger = logging.getLogger(__name__)

def register_evidence_api(app):
    """在 Flask app 上注册 Evidence 查询蓝图。"""
    from flask import Blueprint, jsonify, request

    bp = Blueprint("evidence_api", __name__)

    @bp.route("/api/evidence/stats", methods=["GET"])
    def evidence_stats():
        """证据统计：总数 + 按 result/level/account/source 分组 + 最近 10 条。"""
        try:
            return jsonify({"ok": True, "stats": evidence_store.get_stats()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.route("/api/evidence/list", methods=["GET"])
    def evidence_list():
        """证据列表（支持 source/feature_id/level/result/account/env 筛选 + 分页）。"""
        try:
            rows = evidence_store.query_evidence(
                source=request.args.get("source", ""),
                feature_id=request.args.get("feature_id", ""),
                level=request.args.get("level", ""),
                result=request.args.get("result", ""),
                account=request.args.get("account", ""),
                env=request.args.get("env", ""),
                limit=min(int(request.args.get("limit", "50")), 200),
                offset=int(request.args.get("offset", "0")),
            )
            return jsonify({"ok": True, "count": len(rows), "records": rows})
        except ValueError as e:
            return jsonify({"ok": False, "error": f"参数错误: {e}"}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.route("/api/evidence/<int:record_id>", methods=["GET"])
    def evidence_detail(record_id):
        """单条证据详情。"""
        try:
            rows = evidence_store.query_evidence(limit=1000)
            record = next((r for r in rows if r["id"] == record_id), None)
            if not record:
                return jsonify({"ok": False, "error": "证据不存在"}), 404
            return jsonify({"ok": True, "record": record})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.route("/api/evidence/timeline", methods=["GET"])
    def evidence_timeline():
        """时间线视图：按 feature_id 分组的最近证据（健康/采集分开）。"""
        try:
            account = request.args.get("account", "")
            limit = min(int(request.args.get("limit", "30")), 100)
            health = evidence_store.query_evidence(
                feature_id="RESIDENT_HEALTH", account=account, limit=limit)
            collection = evidence_store.query_evidence(
                feature_id="XHS_COLLECT", account=account, limit=limit)
            return jsonify({
                "ok": True,
                "health": health,
                "collection": collection,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    app.register_blueprint(bp)
    return bp
