# v5.3.2: add to existing app.py (inside the authenticated API section)
from flask import send_file, jsonify, request
from report_export.report_engine import export_report

@app.get("/api/reports/export")
def api_reports_export():
    kind=request.args.get("type","daily")
    fmt=request.args.get("format","xlsx").lower()
    if fmt not in ("docx","csv","xlsx"): return jsonify({"ok":False,"error":"format 必须为 docx/csv/xlsx"}),400
    result=export_report(kind,request.args.get("start"),request.args.get("end"),(fmt,))
    return send_file(result["files"][fmt],as_attachment=True)

@app.get("/api/reports/export-all")
def api_reports_export_all():
    result=export_report(request.args.get("type","daily"),request.args.get("start"),request.args.get("end"),("docx","csv","xlsx"))
    return jsonify({"ok":True,"files":result["files"],"payload":result["payload"]})
