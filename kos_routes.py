# -*- coding: utf-8 -*-
"""Z-Brand-Core KOS API Blueprint（KOS 传播主体 API）

复用 kos_engine.py 和 kos_report.py，不重复建设。
API 统一前缀 /api/kos/。
"""
from flask import Blueprint, request, jsonify, send_from_directory
import os, sys
from pathlib import Path

kos_bp = Blueprint("kos", __name__, url_prefix="/api/kos")

# 延迟导入，避免循环依赖
def _engine():
    if "kos_engine" not in sys.modules:
        import kos_engine
    return sys.modules["kos_engine"]

def _report():
    if "kos_report" not in sys.modules:
        import kos_report
    return sys.modules["kos_report"]


@kos_bp.route("/overview", methods=["GET"])
def api_overview():
    """KOS 总览统计。"""
    try:
        ke = _engine()
        return jsonify({"ok": True, "data": ke.get_stats()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/list", methods=["GET"])
def api_list():
    """KOS 列表（支持 tier/lifecycle/potential/risk/search/limit/offset/sort_by）。"""
    try:
        ke = _engine()
        tier = request.args.get("tier", "")
        lifecycle = request.args.get("lifecycle", "")
        potential = request.args.get("potential", "0") == "1"
        risk = request.args.get("risk", "0") == "1"
        search = request.args.get("search", "")
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))
        sort_by = request.args.get("sort_by", "kos_score")
        result = ke.list_profiles(tier=tier, lifecycle=lifecycle, potential_only=potential,
                                   risk_only=risk, search=search, limit=limit, offset=offset, sort_by=sort_by)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/detail", methods=["GET"])
def api_detail():
    """KOS 详情（含笔记列表）。"""
    try:
        ke = _engine()
        author_id = request.args.get("author_id", "")
        if not author_id:
            return jsonify({"ok": False, "error": "author_id required"}), 400
        profile = ke.get_profile(author_id)
        if not profile:
            return jsonify({"ok": False, "error": "KOS not found"}), 404
        return jsonify({"ok": True, "data": profile})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/refresh", methods=["POST"])
def api_refresh():
    """从 notes 重新聚合刷新 KOS 数据。"""
    try:
        ke = _engine()
        stats = ke.refresh_profiles()
        return jsonify({"ok": True, "data": stats})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/comments", methods=["GET"])
def api_comments():
    """评论分析（支持 author_id/note_id）。"""
    try:
        ke = _engine()
        author_id = request.args.get("author_id", "")
        note_id = request.args.get("note_id", "")
        limit = min(int(request.args.get("limit", 50)), 200)
        result = ke.analyze_comments(author_id=author_id, note_id=note_id, limit=limit)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/outreach", methods=["POST"])
def api_outreach():
    """生成博主触达邀约文案（DRAFT 状态，不伪造已发送）。"""
    try:
        ke = _engine()
        data = request.get_json(silent=True) or {}
        author_id = data.get("author_id", "")
        brand_name = data.get("brand_name", "广州太古汇")
        campaign_name = data.get("campaign_name", "")
        if not author_id:
            return jsonify({"ok": False, "error": "author_id required"}), 400
        result = ke.generate_outreach(author_id, brand_name=brand_name, campaign_name=campaign_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/ad-candidates", methods=["GET"])
def api_ad_candidates():
    """投流候选评分。"""
    try:
        ke = _engine()
        note_id = request.args.get("note_id", "")
        author_id = request.args.get("author_id", "")
        result = ke.ad_candidate_score(note_id=note_id, author_id=author_id)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/reward", methods=["GET"])
def api_reward():
    """奖励积分计算。"""
    try:
        ke = _engine()
        author_id = request.args.get("author_id", "")
        period = request.args.get("period", "month")
        if not author_id:
            return jsonify({"ok": False, "error": "author_id required"}), 400
        result = ke.reward_calculate(author_id, period=period)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/report/generate", methods=["POST"])
def api_report_generate():
    """生成 KOS 动态 HTML 报告。"""
    try:
        kr = _report()
        data = request.get_json(silent=True) or {}
        brand_name = data.get("brand_name", "广州太古汇")
        result = kr.generate_report(brand_name=brand_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/report/view", methods=["GET"])
def api_report_view():
    """查看最新 KOS 报告（静态 HTML）。"""
    try:
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reports")
        if not os.path.exists(report_dir):
            return jsonify({"ok": False, "error": "No reports found"}), 404
        files = sorted([f for f in os.listdir(report_dir) if f.endswith(".html") and f.startswith("KOS_Report")], reverse=True)
        if not files:
            return jsonify({"ok": False, "error": "No KOS reports found"}), 404
        return send_from_directory(report_dir, files[0])
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def register_kos_api(app):
    """注册 KOS Blueprint 到 Flask app。"""
    app.register_blueprint(kos_bp)
