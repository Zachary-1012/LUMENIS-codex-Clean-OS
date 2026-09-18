# -*- coding: utf-8 -*-
"""
GAP-10 report_center 旁路路由挂载
【施工标准】先旁路、再切换；默认关闭；未完成真实验证不得标记完成。

在 app.py 中新增报告中心旁路路由，使用 lumenis.report_center 的 ReportGenerator/ReportExporter。
Feature Gate: ZBC_REPORT_CENTER=1 才启用，默认关闭。
不改变现有报告功能（/api/report/* 等），仅新增旁路入口。
"""
import os
from flask import Blueprint, jsonify, request

report_center_bp = Blueprint('report_center', __name__, url_prefix='/api/report-center')

FEATURE_GATE_ENV = "ZBC_REPORT_CENTER"


def is_enabled() -> bool:
    return os.environ.get(FEATURE_GATE_ENV, "").strip() == "1"


@report_center_bp.route('/status', methods=['GET'])
def status():
    """报告中心状态（旁路，Feature Gate 控制）。"""
    enabled = is_enabled()
    resp = {
        "ok": True,
        "enabled": enabled,
        "feature_gate": FEATURE_GATE_ENV,
        "module": "lumenis.report_center",
        "capabilities": ["ReportGenerator", "ReportExporter", "standard_taxonomy"],
        "brand_modes": ["cth", "zbmp"],
        "periods": ["daily", "weekly", "monthly", "yearly", "custom"],
    }
    if not enabled:
        resp["note"] = f"Feature Gate 关闭，设置 {FEATURE_GATE_ENV}=1 启用"
        return jsonify(resp), 200
    try:
        from lumenis.report_center import ReportGenerator, ReportExporter
        resp["import_ok"] = True
        resp["report_generator"] = ReportGenerator.__name__
        resp["report_exporter"] = ReportExporter.__name__
    except Exception as e:
        resp["import_ok"] = False
        resp["import_error"] = str(e)[:200]
    return jsonify(resp), 200


@report_center_bp.route('/generate', methods=['POST'])
def generate():
    """生成标准化报告（旁路，Feature Gate 控制）。"""
    if not is_enabled():
        return jsonify({"ok": False, "error": f"Feature Gate 关闭，设置 {FEATURE_GATE_ENV}=1 启用",
                        "code": "REPORT_CENTER_DISABLED"}), 403
    data = request.get_json(silent=True) or {}
    brand_mode = data.get("brand_mode", "cth")
    period = data.get("period", "daily")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if brand_mode not in ("cth", "zbmp"):
        return jsonify({"ok": False, "error": f"不支持的 brand_mode: {brand_mode}"}), 400
    if period not in ("daily", "weekly", "monthly", "yearly", "custom"):
        return jsonify({"ok": False, "error": f"不支持的 period: {period}"}), 400

    try:
        from lumenis.report_center import ReportGenerator
        gen = ReportGenerator(brand_mode=brand_mode)
        report = gen.generate(period=period, start_date=start_date, end_date=end_date)
        return jsonify({
            "ok": True,
            "brand_mode": brand_mode,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "report_keys": list(report.keys()) if isinstance(report, dict) else ["non-dict"],
            "report": report if isinstance(report, dict) else str(report)[:2000],
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": f"报告生成失败: {str(e)[:300]}"}), 500


@report_center_bp.route('/export', methods=['POST'])
def export():
    """导出 Word/PDF 报告（旁路，Feature Gate 控制）。"""
    if not is_enabled():
        return jsonify({"ok": False, "error": f"Feature Gate 关闭，设置 {FEATURE_GATE_ENV}=1 启用",
                        "code": "REPORT_CENTER_DISABLED"}), 403
    data = request.get_json(silent=True) or {}
    brand_mode = data.get("brand_mode", "cth")
    period = data.get("period", "daily")

    if brand_mode not in ("cth", "zbmp"):
        return jsonify({"ok": False, "error": f"不支持的 brand_mode: {brand_mode}"}), 400

    try:
        from lumenis.report_center import ReportExporter
        exporter = ReportExporter()
        result = exporter.generate_and_export(brand_mode=brand_mode, period=period)
        return jsonify({
            "ok": True,
            "brand_mode": brand_mode,
            "period": period,
            "word_path": result.get("word_path"),
            "pdf_path": result.get("pdf_path"),
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": f"导出失败: {str(e)[:300]}"}), 500
