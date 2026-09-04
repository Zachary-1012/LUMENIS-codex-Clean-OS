# -*- coding: utf-8 -*-
"""序境-Core · IC-020/028/047 已就绪契约 HTTP API（增量、只读+受控状态流转）。"""
from flask import Blueprint, jsonify, request

ic_bp = Blueprint("ic_contracts", __name__, url_prefix="/api/ic")


# ---------- IC-020 舆情告警 ----------
@ic_bp.route("/alert/config", methods=["GET", "POST"])
def alert_config():
    import alert_engine as ae
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            cfg = ae.set_config(data, source=request.headers.get("X-Operator", "MANUAL"))
            return jsonify({"ok": True, "config": cfg})
        cfg = ae.get_config()
        return jsonify({"ok": True, "config": cfg})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@ic_bp.route("/alert/records", methods=["GET"])
def alert_records():
    import alert_engine as ae
    state = request.args.get("state", "")
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        return jsonify({"ok": True, "records": ae.list_records(state, limit)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@ic_bp.route("/alert/<int:alert_id>/state", methods=["POST"])
def alert_transition(alert_id):
    """HCG 状态机流转：DETECTED→NOTIFIED→ESCALATED→RESOLVED（合法转移才允许）。"""
    import alert_engine as ae
    data = request.get_json(silent=True) or {}
    new_state = data.get("state", "")
    operator = data.get("operator", "api")
    note = data.get("note", "")
    try:
        rec = ae.transition_state(alert_id, new_state, operator=operator, note=note)
        return jsonify({"ok": True, "record": rec})
    except (ValueError, LookupError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@ic_bp.route("/alert/evaluate", methods=["POST"])
def alert_evaluate():
    """评估输入（须由调用方提供 canonical 指标，防重复计算）。"""
    import alert_engine as ae
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", [])
    try:
        ae.init_alert_tables()
        r = ae.evaluate_alerts(
            notes,
            risk_index=data.get("risk_index"),
            brand_health=data.get("brand_health"),
            event_high_count=data.get("event_high_count"),
            mention_baseline=data.get("mention_baseline"),
        )
        return jsonify({"ok": True, **r})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ---------- IC-047 免税 KOS 场景 ----------
@ic_bp.route("/kos-scenario", methods=["GET"])
def kos_scenario():
    """免税/品牌场景 KOS 运营推荐（只读聚合，复用 kos_engine）。"""
    import kos_scenarios as ks
    brand = request.args.get("brand", "海南中免")
    limit = min(int(request.args.get("limit", 20)), 100)
    try:
        r = ks.recommend(brand, limit=limit)
        return jsonify({"ok": True, **r})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ---------- IC-028 营销日历增强 ----------
@ic_bp.route("/marketing/calendar", methods=["GET"])
def marketing_calendar():
    """营销节点（含 IC-028 priority/lead_days/burst 字段）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mc_api", "scripts/marketing_calendar.py")
    mc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mc)
    month = request.args.get("month", type=int)
    try:
        if month:
            nodes = mc.nodes_for_month(month)
            return jsonify({"ok": True, "month": month, "nodes": nodes})
        return jsonify({"ok": True, "summary": mc.yearly_summary()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


def register_ic_api(app):
    app.register_blueprint(ic_bp)
    print("[ic_routes] IC API registered: /api/ic/*")
