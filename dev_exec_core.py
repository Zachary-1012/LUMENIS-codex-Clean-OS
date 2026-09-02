# -*- coding: utf-8 -*-
"""
GAP-04 三 run-code 统一收口核心

【施工标准】先旁路、再切换；默认关闭；未完成真实验证不得标记完成。

三个重复执行入口：
1. /api/developer/run    — 已完全禁用（兼容保留，生产永久 403）
2. /api/config/run-code  — 受限命名空间 exec
3. /api/dev/run-code     — 备份后 exec + JS 追加到文件

本模块统一执行核心，端点2/3 调用 execute_dev_code_safe()，
端点1 保持已禁用状态不变。统一安全闸门、统一执行环境、统一返回格式。

不改变现有行为：仅重构，不改变功能。
"""
from __future__ import annotations

import hashlib
import json as _json_mod
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# 代码执行审计日志（本地 JSONL；.gitignore 的 data/* 已整体排除，不进远端，符合安全资料本地保留）
_AUDIT_PATH = Path("data/audit/dev_exec_audit.jsonl")


def _code_fingerprint(code: str) -> dict:
    """代码指纹：只存长度与 SHA256 前 12 位，绝不存全文（避免密钥/敏感逻辑落审计文件）。"""
    text = code or ""
    digest = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:12]
    return {"code_len": len(text), "code_fp": digest}


def audit_dev_execution(decision, outcome, *, code_type="python", code="",
                        reason="", status=0, backup=False, endpoint=""):
    """追加一条代码执行审计记录（学习 memkeeper-warden：每次 allow/deny 都可审计）。

    decision: allow / deny；outcome: blocked / success / error / bad_request。
    旁路设计：任何审计异常都不得影响主执行流程。
    """
    try:
        _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "decision": str(decision),
            "outcome": str(outcome),
            "code_type": str(code_type),
            "reason": str(reason)[:120],
            "http_status": int(status or 0),
            "backup": bool(backup),
            "endpoint": str(endpoint),
        }
        rec.update(_code_fingerprint(code))
        with open(_AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(_json_mod.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 审计为旁路，绝不阻塞/改变执行结果


def _guard_reason(guarded) -> tuple[str, int]:
    """从 guard 返回的 (response, status) 尽力提取拒绝 code 与状态码，失败则给兜底值。"""
    status = 0
    reason = "guard_blocked"
    try:
        if isinstance(guarded, tuple):
            resp, status = guarded[0], int(guarded[1]) if len(guarded) > 1 else 0
            payload = resp.get_json(silent=True) if hasattr(resp, "get_json") else resp
            if isinstance(payload, dict):
                reason = payload.get("code") or payload.get("error") or reason
    except Exception:
        pass
    return reason, status


def execute_dev_code_safe(
    code: str,
    code_type: str = "python",
    *,
    backup: bool = False,
    app: Any = None,
    db: Any = None,
    guard_func: Any = None,
    endpoint: str = "",
) -> tuple[dict, int]:
    """
    统一代码执行核心（GAP-04 收口）。

    Args:
        code: 要执行的代码
        code_type: "python" 或 "javascript"
        backup: 是否备份 app.py（仅 python）
        app: Flask app 实例（注入执行命名空间）
        db: 数据库实例（注入执行命名空间）
        guard_func: 安全闸门函数 _dev_exec_guard（从 app.py 注入，避免循环 import）
        endpoint: 调用端点标识（仅用于审计溯源）

    Returns:
        (response_dict, http_status_code)

    行为与原端点2/3 完全一致：
    - python: 语法检查 → (可选备份) → 受限命名空间 exec → 返回结果
    - javascript: 追加到 static/js/dev_custom.js → 返回成功
    """
    # 1. 安全闸门（从 app.py 注入）
    if guard_func is not None:
        guarded = guard_func(code)
        if guarded is not None:
            reason, gstatus = _guard_reason(guarded)
            audit_dev_execution("deny", "blocked", code_type=code_type, code=code,
                                reason=reason, status=gstatus, endpoint=endpoint)
            return guarded

    code = (code or "").strip()
    if not code:
        audit_dev_execution("deny", "bad_request", code_type=code_type, code=code,
                            reason="empty_code", status=400, endpoint=endpoint)
        return {"ok": False, "error": "代码不能为空"}, 400

    if code_type == "python":
        resp, status = _execute_python(code, backup=backup, app=app, db=db)
    elif code_type == "javascript":
        resp, status = _execute_javascript(code)
    else:
        audit_dev_execution("deny", "bad_request", code_type=code_type, code=code,
                            reason=f"unsupported_type:{code_type}", status=400, endpoint=endpoint)
        return {"ok": False, "error": f"不支持的代码类型: {code_type}"}, 400

    # 执行结果审计（allow 路径：success / error）
    outcome = "success" if (status == 200 and resp.get("ok")) else (
        "error" if status >= 500 else "bad_request")
    audit_dev_execution("allow", outcome, code_type=code_type, code=code,
                        reason=str(resp.get("error", ""))[:80], status=status,
                        backup=backup, endpoint=endpoint)
    return resp, status


def _execute_python(code: str, *, backup: bool, app: Any, db: Any) -> tuple[dict, int]:
    """执行 Python 代码（与原 /api/config/run-code 和 /api/dev/run-code 行为一致）。"""
    # 代码长度限制（与端点2 一致）
    if len(code) > 50000:
        return {"ok": False, "error": "代码过长（超过50000字符）"}, 400

    # 语法检查（与端点3 一致）
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        return {"ok": False, "error": f"语法错误: 第{e.lineno}行 - {e.msg}"}, 400

    # 备份（仅端点3 backup=True）
    backup_file = None
    if backup:
        try:
            backup_dir = Path("data/backups/dev")
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / f"app_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            shutil.copy("app.py", backup_file)
        except Exception as e:
            # 备份失败不阻塞执行（与原端点3 行为一致：备份在 try 外）
            pass

    # 受限命名空间执行
    try:
        import json as _json
        import os as _os
        from datetime import datetime as _dt, timedelta as _td
        from pathlib import Path as _Path

        exec_globals = {
            "__builtins__": __builtins__,
            "app": app, "db": db,
            "json": _json, "os": _os,
            "Path": _Path, "datetime": _dt, "timedelta": _td,
        }
        # 如果有 request/jsonify（端点2 的命名空间），也注入
        try:
            from flask import request as _req, jsonify as _jf
            exec_globals["request"] = _req
            exec_globals["jsonify"] = _jf
        except Exception:
            pass

        exec(code, exec_globals)
        result = exec_globals.get("result", "代码执行成功，无返回值")
        resp = {"ok": True, "message": "代码执行成功", "result": str(result)[:2000]}
        if backup_file:
            resp["backup"] = str(backup_file)
            resp["message"] = "代码执行成功，已部署到运行时"
        return resp, 200
    except Exception as e:
        resp = {"ok": False, "error": f"代码执行失败: {str(e)}"}
        if backup_file:
            resp["backup"] = str(backup_file)
        return resp, 500


def _execute_javascript(code: str) -> tuple[dict, int]:
    """执行 JavaScript 代码（追加到 static/js/dev_custom.js，与原端点3 行为一致）。"""
    try:
        js_file = Path("static/js/dev_custom.js")
        js_file.parent.mkdir(parents=True, exist_ok=True)
        with open(js_file, "a", encoding="utf-8") as f:
            f.write(f"\n// ===== Dev Code {datetime.now().isoformat()} =====\n{code}\n")
        return {"ok": True, "message": "JS代码已添加到static/js/dev_custom.js，刷新页面生效"}, 200
    except Exception as e:
        return {"ok": False, "error": f"JS代码写入失败: {str(e)}"}, 500


# 模块自检
if __name__ == "__main__":
    import json
    print("=== GAP-04 统一执行核心自检 ===")
    # 测试空代码
    r, s = execute_dev_code_safe("", "python")
    print(f"空代码: status={s}, ok={r.get('ok')}")
    # 测试不支持的类型
    r, s = execute_dev_code_safe("1+1", "ruby")
    print(f"不支持类型: status={s}, ok={r.get('ok')}")
    # 测试语法错误
    r, s = execute_dev_code_safe("def foo(", "python")
    print(f"语法错误: status={s}, error={r.get('error','')[:40]}")
    # 测试正常执行（无 guard）
    r, s = execute_dev_code_safe("result = 1+1", "python")
    print(f"正常执行: status={s}, ok={r.get('ok')}, result={r.get('result')}")
    print("自检完成")
