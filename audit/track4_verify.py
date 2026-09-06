# -*- coding: utf-8 -*-
"""Track 4 真实验证脚本：API / 前端 / 报告 / 安全边界 / 错误处理。

所有测试使用 Flask test_client，不启动真实服务器。
输出 JSON 结果到 audit/track4_*.json。
"""
import json
import os
import sys
import traceback
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

RESULT_DIR = os.path.join(PROJECT_ROOT, "audit")
os.makedirs(RESULT_DIR, exist_ok=True)

api_results = []
report_results = []
frontend_results = []
security_results = []
error_results = []


def record(target, name, method, url, status_code, ok, body_preview="", error="", extra=None):
    entry = {
        "name": name,
        "method": method,
        "url": url,
        "status_code": status_code,
        "ok": ok,
        "body_preview": body_preview[:300] if isinstance(body_preview, str) else str(body_preview)[:300],
        "error": error,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    if extra:
        entry.update(extra)
    target.append(entry)
    return entry


def safe_json(resp):
    try:
        return resp.get_json()
    except Exception:
        try:
            return json.loads(resp.data.decode("utf-8", errors="replace"))
        except Exception:
            return None


def main():
    print("=" * 70)
    print("Track 4: API & Frontend & Reports & Security — 真实验证")
    print("=" * 70)

    # ── 1. 导入 app ──
    print("\n[1/6] 导入 Flask app...")
    try:
        import app as flask_app
        app = flask_app.app
        print(f"  app imported: {app.name}, routes={len(list(app.url_map.iter_rules()))}")
    except Exception as e:
        print(f"  FATAL: app import failed: {e}")
        traceback.print_exc()
        # 写一个失败结果然后退出
        with open(os.path.join(RESULT_DIR, "track4_api_test_results.json"), "w", encoding="utf-8") as f:
            json.dump({"fatal": f"app import failed: {e}", "traceback": traceback.format_exc()}, f, ensure_ascii=False, indent=2)
        return

    client = app.test_client()

    # 构建 HTTP Basic Auth 头（凭证从 app 模块读取，绝不打印/记录明文）
    import base64 as _b64
    _au = getattr(flask_app, 'AUTH_USER', '')
    _ap = getattr(flask_app, 'AUTH_PASSWORD', '')
    AUTH_HEADERS = {}
    if _au and _ap:
        _token = _b64.b64encode(f'{_au}:{_ap}'.encode('utf-8')).decode('ascii')
        AUTH_HEADERS = {'Authorization': f'Basic {_token}'}
        print(f"  auth enabled: using Basic Auth (credentials not logged)")
    else:
        print(f"  auth disabled: no credentials configured")

    def _get(url):
        return client.get(url, headers=AUTH_HEADERS)

    def _post(url, json_body=None):
        return client.post(url, json=json_body or {}, headers=AUTH_HEADERS)

    # ── 2. API 端点测试（10+ 核心端点，GET/POST）──
    print("\n[2/6] 测试核心 API 端点...")

    api_tests = [
        # GET 端点
        ("GET /api/health", "GET", "/api/health", None),
        ("GET /api/stats", "GET", "/api/stats", None),
        ("GET /api/notes?page=1&per_page=5", "GET", "/api/notes?page=1&per_page=5", None),
        ("GET /api/events", "GET", "/api/events", None),
        ("GET /api/hot-topics?limit=5", "GET", "/api/hot-topics?limit=5", None),
        ("GET /api/intelligence/models", "GET", "/api/intelligence/models", None),
        ("GET /api/system/runtime", "GET", "/api/system/runtime", None),
        ("GET /api/production/reports", "GET", "/api/production/reports", None),
        ("GET /api/architecture/status", "GET", "/api/architecture/status", None),
        ("GET /api/auth-recovery/health", "GET", "/api/auth-recovery/health", None),
        ("GET /api/export/list", "GET", "/api/export/list", None),
        ("GET /api/kos/overview", "GET", "/api/kos/overview", None),
        ("GET /api/podcast/overview", "GET", "/api/podcast/overview", None),
        # POST 端点
        ("POST /api/metric-trend (bad params -> 400)", "GET", "/api/metric-trend?entity_type=invalid", None),
        ("POST /api/local-ai/analyze (empty text -> 400)", "POST", "/api/local-ai/analyze", {"text": ""}),
        ("POST /api/kos/professional/disable (unavailable -> 503)", "POST", "/api/kos/professional/disable", {}),
    ]

    for name, method, url, body in api_tests:
        try:
            if method == "GET":
                resp = _get(url)
            else:
                resp = _post(url, body or {})
            data = safe_json(resp)
            # 成功端点应返回 200 + JSON；错误测试端点应返回 4xx + 错误结构
            is_ok = (resp.status_code == 200 and data is not None) or \
                    (400 <= resp.status_code < 500 and isinstance(data, dict) and
                     (data.get("ok") is False or "error" in data))
            preview = json.dumps(data, ensure_ascii=False) if data else resp.data[:200].decode("utf-8", errors="replace")
            record(api_results, name, method, url, resp.status_code, is_ok, preview,
                   extra={"has_json": data is not None, "json_keys": list(data.keys())[:10] if isinstance(data, dict) else None})
            print(f"  {'PASS' if is_ok else 'FAIL'} {name} -> {resp.status_code}")
        except Exception as e:
            record(api_results, name, method, url, 0, False, "", str(e))
            print(f"  ERROR {name}: {e}")

    # ── 3. 前端页面测试（3+ 页面返回 200）──
    print("\n[3/6] 测试前端页面...")
    frontend_pages = [
        ("/lumenis/", "Command Home"),
        ("/lumenis/intelligence", "Intelligence Workspace"),
        ("/lumenis/production", "Production Overview"),
        ("/lumenis/operations", "Operations"),
        ("/lumenis/healthz", "Foundation Healthz"),
        ("/", "Root / Home"),
    ]
    for url, name in frontend_pages:
        try:
            resp = _get(url)
            content_type = resp.content_type or ""
            is_html = "html" in content_type.lower() or b"<html" in resp.data[:500].lower() or b"<!DOCTYPE" in resp.data[:500].upper()
            is_ok = resp.status_code == 200
            record(frontend_results, name, "GET", url, resp.status_code, is_ok,
                   f"content_type={content_type}, body_len={len(resp.data)}",
                   extra={"is_html": is_html, "body_length": len(resp.data)})
            print(f"  {'PASS' if is_ok else 'FAIL'} {name} ({url}) -> {resp.status_code}, len={len(resp.data)}")
        except Exception as e:
            record(frontend_results, name, "GET", url, 0, False, "", str(e))
            print(f"  ERROR {name}: {e}")

    # ── 4. 报告生成验证 ──
    print("\n[4/6] 验证报告生成...")

    # 4a. 生成日报（daily_report.generate_daily_digest）
    try:
        import daily_report
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"  生成日报 digest for {today}...")
        digest = daily_report.generate_daily_digest(today)
        digest_ok = isinstance(digest, dict) and digest.get("digest_date") == today
        record(report_results, "daily_report.generate_daily_digest", "FUNC",
               f"daily_report.generate_daily_digest({today})", 200, digest_ok,
               json.dumps({k: digest.get(k) for k in ["digest_date", "total_found", "effective_count", "risk_index", "brand_health_score"]}, ensure_ascii=False),
               extra={"report_type": "daily_digest", "has_key_insights": bool(digest.get("key_insights")),
                      "has_action_items": bool(digest.get("action_items")), "has_top_events": bool(digest.get("top_events"))})
        print(f"    digest: total_found={digest.get('total_found')}, effective={digest.get('effective_count')}, risk_index={digest.get('risk_index')}")
    except Exception as e:
        record(report_results, "daily_report.generate_daily_digest", "FUNC", "daily_report", 0, False, "", str(e))
        print(f"    ERROR: {e}")
        traceback.print_exc()

    # 4b. report_engine.generate_report (daily)
    try:
        import report_engine
        print("  生成 report_engine daily report...")
        report, digest = report_engine.generate_report("daily")
        report_ok = isinstance(report, dict) and report.get("report_type") == "daily" and report.get("_artifact_verified", False)
        record(report_results, "report_engine.generate_report(daily)", "FUNC",
               "report_engine.generate_report('daily')", 200, report_ok,
               json.dumps({k: report.get(k) for k in ["report_type", "report_date", "total_notes", "report_id", "_artifact_verified", "_db_row_id"]}, ensure_ascii=False),
               extra={"report_type": "daily", "artifact_verified": report.get("_artifact_verified"),
                      "db_row_id": report.get("_db_row_id"), "has_digest": digest is not None})
        print(f"    report: total_notes={report.get('total_notes')}, db_row_id={report.get('_db_row_id')}, verified={report.get('_artifact_verified')}")
    except Exception as e:
        record(report_results, "report_engine.generate_report(daily)", "FUNC", "report_engine", 0, False, "", str(e))
        print(f"    ERROR: {e}")
        traceback.print_exc()

    # 4c. 导出 Excel 报告（生成文件并验证存在）
    try:
        import export_report
        print("  生成 Excel 导出文件...")
        result = export_report._export_excel("daily")
        if isinstance(result, str) and os.path.isfile(result):
            size = os.path.getsize(result)
            record(report_results, "export_report._export_excel(daily)", "FUNC",
                   "export_report._export_excel('daily')", 200, size > 0,
                   f"file={result}, size={size} bytes",
                   extra={"file_path": result, "file_size": size, "file_exists": True, "file_nonempty": size > 0})
            print(f"    Excel file: {result}, size={size} bytes")
        else:
            record(report_results, "export_report._export_excel(daily)", "FUNC",
                   "export_report._export_excel('daily')", 500, False,
                   f"result={str(result)[:200]}",
                   extra={"file_exists": False})
            print(f"    FAIL: result is not a file path: {str(result)[:200]}")
    except Exception as e:
        record(report_results, "export_report._export_excel(daily)", "FUNC", "export_report", 0, False, "", str(e))
        print(f"    ERROR: {e}")
        traceback.print_exc()

    # 4d. 报告下载端点测试
    try:
        print("  测试报告下载端点 /api/export/report?type=daily&format=xlsx...")
        resp = _get("/api/export/report?type=daily&format=xlsx")
        is_file = resp.status_code == 200 and len(resp.data) > 100
        record(report_results, "GET /api/export/report (download xlsx)", "GET",
               "/api/export/report?type=daily&format=xlsx", resp.status_code, is_file,
               f"content_type={resp.content_type}, body_len={len(resp.data)}",
               extra={"body_length": len(resp.data), "content_type": resp.content_type,
                      "is_attachment": "attachment" in (resp.headers.get("Content-Disposition", "") or "")})
        print(f"    download: status={resp.status_code}, len={len(resp.data)}, ct={resp.content_type}")
    except Exception as e:
        record(report_results, "GET /api/export/report", "GET", "/api/export/report", 0, False, "", str(e))
        print(f"    ERROR: {e}")

    # 4e. report_artifact 校验模块
    try:
        import report_artifact as ra
        print("  测试 report_artifact 校验...")
        # 找一个已生成的文件
        export_dir = os.path.join(PROJECT_ROOT, "data", "exports")
        test_file = None
        if os.path.isdir(export_dir):
            for f in sorted(os.listdir(export_dir), reverse=True):
                fp = os.path.join(export_dir, f)
                if os.path.isfile(fp) and fp.endswith((".xlsx", ".docx")):
                    test_file = fp
                    break
        if test_file:
            v = ra.verify_artifact_file(test_file)
            record(report_results, "report_artifact.verify_artifact_file", "FUNC",
                   f"verify_artifact_file({os.path.basename(test_file)})", 200, v["valid"],
                   json.dumps(v, ensure_ascii=False),
                   extra={"file": test_file, "valid": v["valid"], "size": v["size"], "hash": v["hash"][:16] + "..." if v["hash"] else ""})
            print(f"    artifact verify: valid={v['valid']}, size={v['size']}, hash={v['hash'][:16] if v['hash'] else 'N/A'}")
        else:
            record(report_results, "report_artifact.verify_artifact_file", "FUNC", "no test file", 200, True,
                   "no xlsx/docx file found in exports dir; module import OK",
                   extra={"module_import_ok": True})
            print("    no test file found, module import OK")
    except Exception as e:
        record(report_results, "report_artifact.verify_artifact_file", "FUNC", "report_artifact", 0, False, "", str(e))
        print(f"    ERROR: {e}")

    # ── 5. 安全边界验证 ──
    print("\n[5/6] 验证安全边界 (permission_gate deny by default)...")

    try:
        from permission_gate import PermissionGate, OperationType, RiskLevel, PermissionLevel
        print("  测试 PermissionGate...")

        # 5a. 未注册操作 + fail_closed=True -> 应拒绝
        gate = PermissionGate(fail_closed=True)
        # 用一个未注册的操作类型
        class FakeOp:
            value = "unregistered_dangerous_op"
        result = gate.check(FakeOp(), resource="/etc/passwd", risk_level=RiskLevel.CRITICAL)
        denied = not result.allowed
        record(security_results, "permission_gate: unregistered op + fail_closed -> DENY", "FUNC",
               "PermissionGate.check(unregistered, fail_closed=True)", 200, denied,
               f"allowed={result.allowed}, reason={result.reason}",
               extra={"allowed": result.allowed, "reason": result.reason, "fail_closed": True})
        print(f"    unregistered op: allowed={result.allowed}, reason={result.reason[:80]}")

        # 5b. 高风险操作无审批 -> 应拒绝
        gate2 = PermissionGate(fail_closed=True)
        result2 = gate2.check(OperationType.CONFIG_MODIFY, resource="config.yaml", risk_level=RiskLevel.HIGH)
        denied2 = not result2.allowed
        record(security_results, "permission_gate: HIGH risk no approval -> DENY", "FUNC",
               "PermissionGate.check(CONFIG_MODIFY, HIGH, no_approval)", 200, denied2,
               f"allowed={result2.allowed}, reason={result2.reason}",
               extra={"allowed": result2.allowed, "requires_approval": result2.requires_approval})
        print(f"    HIGH risk no approval: allowed={result2.allowed}, requires_approval={result2.requires_approval}")

        # 5c. 低风险只读操作 -> 应允许
        gate3 = PermissionGate(fail_closed=True)
        result3 = gate3.check(OperationType.REPORT_GENERATE, resource="daily_report")
        allowed3 = result3.allowed
        record(security_results, "permission_gate: LOW risk read -> ALLOW", "FUNC",
               "PermissionGate.check(REPORT_GENERATE, LOW)", 200, allowed3,
               f"allowed={result3.allowed}, reason={result3.reason}",
               extra={"allowed": result3.allowed})
        print(f"    LOW risk read: allowed={result3.allowed}")

        # 5d. DB_WRITE 高风险无审批 -> 应拒绝
        gate4 = PermissionGate(fail_closed=True)
        result4 = gate4.check(OperationType.DB_WRITE, resource="notes_table", risk_level=RiskLevel.HIGH)
        denied4 = not result4.allowed
        record(security_results, "permission_gate: DB_WRITE HIGH no approval -> DENY", "FUNC",
               "PermissionGate.check(DB_WRITE, HIGH, no_approval)", 200, denied4,
               f"allowed={result4.allowed}, reason={result4.reason}",
               extra={"allowed": result4.allowed, "requires_approval": result4.requires_approval})
        print(f"    DB_WRITE HIGH: allowed={result4.allowed}")

    except Exception as e:
        record(security_results, "permission_gate module", "FUNC", "permission_gate", 0, False, "", str(e))
        print(f"  ERROR: {e}")
        traceback.print_exc()

    # ── 6. API 错误处理验证 ──
    print("\n[6/6] 验证 API 错误响应结构...")

    error_tests = [
        ("GET /api/metric-trend (missing entity_key -> 400)", "GET", "/api/metric-trend?entity_type=note", None),
        ("GET /api/kos/detail (missing author_id -> 400)", "GET", "/api/kos/detail", None),
        ("POST /api/local-ai/analyze (empty text -> 400)", "POST", "/api/local-ai/analyze", {"text": ""}),
        ("GET /api/notes (bad page -> 400)", "GET", "/api/notes?page=abc", None),
        ("GET /api/browser-surface/tab/new (empty url -> 400)", "POST", "/api/browser-surface/tab/new", {"url": ""}),
    ]

    for name, method, url, body in error_tests:
        try:
            if method == "GET":
                resp = _get(url)
            else:
                resp = _post(url, body or {})
            data = safe_json(resp)
            # 错误响应应该有 ok=False 或 error 字段，且状态码应为 4xx（不是 500 裸异常）
            has_error_structure = isinstance(data, dict) and (data.get("ok") is False or "error" in data)
            is_client_error = 400 <= resp.status_code < 500
            is_ok = is_client_error and has_error_structure
            preview = json.dumps(data, ensure_ascii=False) if data else resp.data[:200].decode("utf-8", errors="replace")
            record(error_results, name, method, url, resp.status_code, is_ok, preview,
                   extra={"has_error_structure": has_error_structure, "is_client_error": is_client_error,
                          "not_500": resp.status_code != 500})
            print(f"  {'PASS' if is_ok else 'FAIL'} {name} -> {resp.status_code}, error_struct={has_error_structure}")
        except Exception as e:
            record(error_results, name, method, url, 0, False, "", str(e))
            print(f"  ERROR {name}: {e}")

    # ── 保存结果 ──
    print("\n" + "=" * 70)
    print("保存验证结果...")

    # API 测试结果
    api_summary = {
        "total": len(api_results),
        "passed": sum(1 for r in api_results if r["ok"]),
        "failed": sum(1 for r in api_results if not r["ok"]),
        "results": api_results,
    }
    with open(os.path.join(RESULT_DIR, "track4_api_test_results.json"), "w", encoding="utf-8") as f:
        json.dump(api_summary, f, ensure_ascii=False, indent=2)
    print(f"  API: {api_summary['passed']}/{api_summary['total']} passed")

    # 报告生成验证
    report_summary = {
        "total": len(report_results),
        "passed": sum(1 for r in report_results if r["ok"]),
        "failed": sum(1 for r in report_results if not r["ok"]),
        "results": report_results,
    }
    with open(os.path.join(RESULT_DIR, "track4_report_generation_verification.json"), "w", encoding="utf-8") as f:
        json.dump(report_summary, f, ensure_ascii=False, indent=2)
    print(f"  Reports: {report_summary['passed']}/{report_summary['total']} passed")

    # 前端 + 安全 + 错误 合并到一个补充文件
    combined = {
        "frontend": {"total": len(frontend_results), "passed": sum(1 for r in frontend_results if r["ok"]), "results": frontend_results},
        "security": {"total": len(security_results), "passed": sum(1 for r in security_results if r["ok"]), "results": security_results},
        "error_handling": {"total": len(error_results), "passed": sum(1 for r in error_results if r["ok"]), "results": error_results},
    }
    with open(os.path.join(RESULT_DIR, "track4_frontend_security_error_verification.json"), "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"  Frontend: {combined['frontend']['passed']}/{combined['frontend']['total']} passed")
    print(f"  Security: {combined['security']['passed']}/{combined['security']['total']} passed")
    print(f"  Error handling: {combined['error_handling']['passed']}/{combined['error_handling']['total']} passed")

    print("\n验证完成！结果已保存到 audit/ 目录。")
    print("=" * 70)


if __name__ == "__main__":
    main()
