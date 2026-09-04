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


# ---------- IC-021 EMV（MET-CONTENT-04）----------
@ic_bp.route("/emv", methods=["GET"])
def ic_emv():
    """EMV 估算（估算口径，显式标注，非官方投放成本）。
    GET ?start=&end=&cpm=&limit= 基于真实 notes 互动数据汇总。"""
    import database as db
    import emv as _emv
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    cpm = request.args.get("cpm", type=float)
    limit = min(int(request.args.get("limit", 200)), 500)
    try:
        with db.get_db() as conn:
            if start and end:
                rows = conn.execute(
                    "SELECT note_id, title, author_nickname, likes, comments, collects, shares, sentiment "
                    "FROM notes WHERE publish_date BETWEEN ? AND ? ORDER BY captured_at DESC LIMIT ?",
                    (start, end, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT note_id, title, author_nickname, likes, comments, collects, shares, sentiment "
                    "FROM notes ORDER BY captured_at DESC LIMIT ?", (limit,)).fetchall()
            notes = [dict(r) for r in rows]
        r = _emv.aggregate_emv(notes, cpm=cpm)
        return jsonify({"ok": True, **r})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ---------- IC-039 跨文化本地化守卫 ----------
@ic_bp.route("/localization/check", methods=["POST"])
def localization_check():
    """本地化禁忌/合规检查（中英韩）。契约红线：命中 HOLD/BLOCK 须人工复核。
    POST {"text": "...", "lang": "zh|en|ko|multi", "platform": "..."}"""
    import sys
    if "scripts" not in sys.path:
        sys.path.insert(0, "scripts")
    import localization_guard as lg
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    lang = data.get("lang", "zh")
    platform = data.get("platform", "")
    if not text:
        return jsonify({"ok": False, "error": "text 必填"}), 400
    try:
        if lang == "multi":
            r = lg.check_multi(text, platform=platform)
        else:
            r = lg.check(text, lang=lang, platform=platform)
        return jsonify({"ok": True, **r})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ---------- IC-040 KOS 兴趣图谱信号 ----------
@ic_bp.route("/kos/interest-signal", methods=["GET"])
def kos_interest_signal():
    """KOS 账号兴趣图谱信号（附加维度，代理指标，不改变 kos_score）。"""
    import kos_engine as ke
    author_id = request.args.get("author_id", "")
    brand = request.args.get("brand", "")
    limit = min(int(request.args.get("limit", 30)), 100)
    if not author_id:
        return jsonify({"ok": False, "error": "author_id 必填"}), 400
    try:
        r = ke.interest_signal(author_id, brand=brand, limit=limit)
        return jsonify({"ok": True, **r})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ---------- IC-044 耸动/合成内容风险信号检查 ----------
@ic_bp.route("/synthetic/scan", methods=["POST"])
def synthetic_scan():
    """耸动/合成内容风险信号扫描（与 IC-020 告警联动；代理信号，非平台原生能力）。"""
    import alert_engine as ae
    data = request.get_json(silent=True) or {}
    signals = data.get("signals") or []
    if not isinstance(signals, list):
        return jsonify({"ok": False, "error": "signals 需为列表"}), 400
    try:
        r = ae.synthetic_risk_scan(signals, config=data.get("config"))
        return jsonify({"ok": True, **r})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ---------- IC-048 可视化质量门检查 ----------
@ic_bp.route("/vis/quality-gate", methods=["GET"])
def vis_quality_gate():
    """可视化质量门清单（VISQ；新图上线前验收，不引框架）。"""
    from scripts.visualization_quality_gate import checklist_md, QUALITY_CHECKS
    return jsonify({"ok": True, "checks": QUALITY_CHECKS, "checklist_md": checklist_md()})


# ---------- IC-048 可视化质量门单图检查 ----------
@ic_bp.route("/vis/quality-check", methods=["POST"])
def vis_quality_check():
    """对一张图执行质量门检查（结构化 PASS/FAIL）。"""
    from scripts.visualization_quality_gate import check
    data = request.get_json(silent=True) or {}
    try:
        r = check(
            vis_id=data.get("vis_id", ""),
            question=data.get("question", ""),
            has_zero_baseline=bool(data.get("has_zero_baseline", True)),
            uses_cvd_safe=bool(data.get("uses_cvd_safe", True)),
            multi_channel=bool(data.get("multi_channel", True)),
            role_arch=bool(data.get("role_arch", True)),
            has_empty_state=bool(data.get("has_empty_state", True)),
            canonical_source=data.get("canonical_source", ""),
            data_source_note=data.get("data_source_note", ""),
            mobile_ok=bool(data.get("mobile_ok", True)),
            motion_ok=bool(data.get("motion_ok", True)),
        )
        return jsonify({"ok": True, **r})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
