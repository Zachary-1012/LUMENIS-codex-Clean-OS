# -*- coding: utf-8 -*-
"""
Shared Reporting canonical capability routes

使用 lumenis.shared.reporting 的 ReportGenerator / ReportExporter。
Feature Gate: LUMENIS_REPORTING=1 控制该组 API 的暴露，不改变 Shared Reporting 的 canonical ownership。
报告 Production Truth、artifact 与既有 /api/report/* 契约统一归 Shared Reporting。
"""
import os
from flask import Blueprint, jsonify, request

reporting_bp = Blueprint('reporting', __name__, url_prefix='/api/reporting')

FEATURE_GATE_ENV = "LUMENIS_REPORTING"


def is_enabled() -> bool:
    return os.environ.get(FEATURE_GATE_ENV, "").strip() == "1"


@reporting_bp.route('/status', methods=['GET'])
def status():
    """Shared Reporting canonical capability 状态（Feature Gate 仅控制 API 暴露）。"""
    enabled = is_enabled()
    resp = {
        "ok": True,
        "enabled": enabled,
        "feature_gate": FEATURE_GATE_ENV,
        "module": "lumenis.shared.reporting",
        "capabilities": ["ReportGenerator", "ReportExporter", "standard_taxonomy"],
        "brand_modes": ["cth", "zbmp"],
        "periods": ["daily", "weekly", "monthly", "yearly", "custom"],
    }
    if not enabled:
        resp["note"] = f"Feature Gate 关闭，设置 {FEATURE_GATE_ENV}=1 启用"
        return jsonify(resp), 200
    try:
        from lumenis.shared.reporting import ReportGenerator, ReportExporter
        resp["import_ok"] = True
        resp["report_generator"] = ReportGenerator.__name__
        resp["report_exporter"] = ReportExporter.__name__
    except Exception as e:
        resp["import_ok"] = False
        resp["import_error"] = str(e)[:200]
    return jsonify(resp), 200


@reporting_bp.route('/generate', methods=['POST'])
def generate():
    """生成标准化报告（Shared Reporting canonical capability）。"""
    if not is_enabled():
        return jsonify({"ok": False, "error": f"Feature Gate 关闭，设置 {FEATURE_GATE_ENV}=1 启用",
                        "code": "REPORTING_DISABLED"}), 403
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
        from lumenis.shared.reporting import ReportGenerator
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


@reporting_bp.route('/export', methods=['POST'])
def export():
    """导出 Word/PDF 报告（Shared Reporting canonical capability）。"""
    if not is_enabled():
        return jsonify({"ok": False, "error": f"Feature Gate 关闭，设置 {FEATURE_GATE_ENV}=1 启用",
                        "code": "REPORTING_DISABLED"}), 403
    data = request.get_json(silent=True) or {}
    brand_mode = data.get("brand_mode", "cth")
    period = data.get("period", "daily")

    if brand_mode not in ("cth", "zbmp"):
        return jsonify({"ok": False, "error": f"不支持的 brand_mode: {brand_mode}"}), 400

    try:
        from lumenis.shared.reporting import ReportExporter
        exporter = ReportExporter()
        result = exporter.generate_and_export(brand_mode=brand_mode, period=period)
        missing_formats = [format for format in ("word", "pdf") if not result.get(format + "_path")]
        if missing_formats:
            return jsonify({
                "ok": False, "code": "REPORT_EXPORT_INCOMPLETE", "error": "所需报告格式未能导出",
                "unavailable_formats": missing_formats, "brand_mode": brand_mode, "period": period,
                "word_path": result.get("word_path"), "pdf_path": result.get("pdf_path"),
            }), 503
        return jsonify({
            "ok": True,
            "brand_mode": brand_mode,
            "period": period,
            "word_path": result.get("word_path"),
            "pdf_path": result.get("pdf_path"),
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": f"导出失败: {str(e)[:300]}"}), 500
