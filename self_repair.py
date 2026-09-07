import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
BACKUP = ROOT / ".self_repair_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT = ROOT / "SELF_REPAIR_REPORT.json"

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules",
    "__pycache__", ".self_repair_backup",
    "dist", "build"
}

TEXT_EXT = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".html", ".htm", ".css", ".scss",
    ".json", ".vue"
}

def files():
    result = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(x in IGNORE_DIRS for x in p.parts):
            continue
        if p.suffix.lower() in TEXT_EXT:
            result.append(p)
    return result

def read(p):
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="utf-8-sig")
        except Exception:
            return ""

def backup_file(p):
    rel = p.relative_to(ROOT)
    dst = BACKUP / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dst)

def save(p, text):
    backup_file(p)
    p.write_text(text, encoding="utf-8")

def scan():
    fs = files()
    py = [p for p in fs if p.suffix == ".py"]
    js = [p for p in fs if p.suffix in {".js", ".jsx", ".ts", ".tsx"}]
    html = [p for p in fs if p.suffix in {".html", ".htm", ".vue"}]
    css = [p for p in fs if p.suffix in {".css", ".scss"}]

    return fs, py, js, html, css

def backend_routes(py):
    routes = set()
    patterns = [
        r'@\w+\.route\(["\']([^"\']+)',
        r'@\w+\.(?:get|post|put|delete|patch)\(["\']([^"\']+)',
        r'@app\.route\(["\']([^"\']+)'
    ]

    for p in py:
        text = read(p)
        for pattern in patterns:
            routes.update(re.findall(pattern, text))

    return routes

def frontend_apis(js, html):
    calls = set()

    for p in js + html:
        text = read(p)

        for m in re.findall(
            r'(?:fetch|axios\.(?:get|post|put|delete|patch))\s*\(\s*[`"\']([^`"\']+)',
            text
        ):
            calls.add(m.split("?")[0])

    return calls

def check_api_consistency(py, js, html):
    routes = backend_routes(py)
    calls = frontend_apis(js, html)

    normalized_routes = {
        r.rstrip("/") for r in routes
    }

    missing = []

    for call in calls:
        if not call.startswith("/"):
            continue

        # 去掉动态参数和 query
        c = call.split("?")[0]
        c = re.sub(r"\$\{[^}]+\}", "", c)
        c = re.sub(r"<[^>]+>", "", c)

        matched = False

        for route in normalized_routes:
            r = route.rstrip("/")
            r = re.sub(r"<[^>]+>", "", r)

            if c == r or c.startswith(r + "/") or r.startswith(c + "/"):
                matched = True
                break

        if not matched:
            missing.append(call)

    return {
        "backend_routes": sorted(routes),
        "frontend_api_calls": sorted(calls),
        "frontend_calls_without_obvious_backend_match": sorted(set(missing))
    }

def css_override_scan(css):
    findings = []

    for p in css:
        text = read(p)

        important = len(re.findall(r'!important', text))
        inline_like = len(re.findall(r'style\s*=', text, re.I))

        if important:
            findings.append({
                "file": str(p.relative_to(ROOT)),
                "type": "important",
                "count": important
            })

        if inline_like:
            findings.append({
                "file": str(p.relative_to(ROOT)),
                "type": "inline-style",
                "count": inline_like
            })

    return findings

def dangerous_frontend_patterns(js, html):
    findings = []

    for p in js + html:
        text = read(p)

        patterns = {
            "innerHTML": r'\.innerHTML\s*=',
            "outerHTML": r'\.outerHTML\s*=',
            "document.write": r'document\.write\s*\(',
            "eval": r'\beval\s*\(',
            "new Function": r'new\s+Function\s*\('
        }

        for name, pattern in patterns.items():
            count = len(re.findall(pattern, text))
            if count:
                findings.append({
                    "file": str(p.relative_to(ROOT)),
                    "type": name,
                    "count": count
                })

    return findings

def safe_escape_patch(js, html):
    """
    只对明显存在的 innerHTML 直接赋值进行保护性修复。
    不自动修改复杂模板，避免破坏业务。
    """

    repaired = []

    for p in js + html:
        text = read(p)

        if ".innerHTML =" not in text:
            continue

        # 如果项目已经有 escape/sanitize，则不动
        if re.search(r'\b(?:escapeHTML|sanitizeHTML|safeHTML|DOMPurify)\b', text):
            continue

        # 不自动重写复杂 innerHTML。
        # 仅记录，避免因为错误替换导致 UI 损坏。
        repaired.append({
            "file": str(p.relative_to(ROOT)),
            "action": "NOT_AUTO_MODIFIED",
            "reason": "发现 innerHTML，需要人工/项目级安全渲染策略确认"
        })

    return repaired

def python_compile():
    try:
        r = subprocess.run(
            ["python", "-m", "compileall", "-q", str(ROOT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout[-4000:],
            "stderr": r.stderr[-4000:]
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def npm_build():
    package = ROOT / "package.json"

    if not package.exists():
        return {
            "status": "NOT_AVAILABLE",
            "reason": "package.json 不存在"
        }

    try:
        data = json.loads(read(package))
        scripts = data.get("scripts", {})

        if "build" not in scripts:
            return {
                "status": "NOT_AVAILABLE",
                "reason": "package.json 没有 build script"
            }

        r = subprocess.run(
            ["npm", "run", "build"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )

        return {
            "status": "PASS" if r.returncode == 0 else "FAIL",
            "stdout": r.stdout[-6000:],
            "stderr": r.stderr[-6000:]
        }

    except Exception as e:
        return {
            "status": "FAIL",
            "error": str(e)
        }

def pytest():
    if not any(ROOT.rglob("test*.py")) and not any(ROOT.rglob("*_test.py")):
        return {
            "status": "NOT_AVAILABLE"
        }

    try:
        r = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600
        )

        return {
            "status": "PASS" if r.returncode == 0 else "FAIL",
            "stdout": r.stdout[-6000:],
            "stderr": r.stderr[-6000:]
        }

    except Exception as e:
        return {
            "status": "FAIL",
            "error": str(e)
        }

def main():
    print("=" * 70)
    print("TAIKOO MONITOR — FULL SELF AUDIT / SAFE RECOVERY")
    print("=" * 70)

    BACKUP.mkdir(parents=True, exist_ok=True)

    fs, py, js, html, css = scan()

    print(f"[SCAN] files={len(fs)} python={len(py)} js={len(js)} html={len(html)} css={len(css)}")

    result = {
        "timestamp": datetime.now().isoformat(),
        "root": str(ROOT),
        "backup": str(BACKUP),
        "scan": {
            "files": len(fs),
            "python": len(py),
            "javascript": len(js),
            "html": len(html),
            "css": len(css)
        }
    }

    print("[1/7] API 前后端一致性检查...")
    result["api_consistency"] = check_api_consistency(py, js, html)

    print("[2/7] CSS/UI 覆盖检查...")
    result["ui_override"] = css_override_scan(css)

    print("[3/7] 前端危险渲染检查...")
    result["frontend_security"] = dangerous_frontend_patterns(js, html)

    print("[4/7] 安全自动恢复检查...")
    result["safe_recovery"] = safe_escape_patch(js, html)

    print("[5/7] Python 编译检查...")
    result["python_compile"] = python_compile()

    print("[6/7] Pytest 回归...")
    result["pytest"] = pytest()

    print("[7/7] Frontend Build...")
    result["npm_build"] = npm_build()

    # 最终状态
    api_missing = result["api_consistency"][
        "frontend_calls_without_obvious_backend_match"
    ]

    result["final_status"] = {
        "api_consistency": "WARN" if api_missing else "PASS",
        "ui_override": "WARN" if result["ui_override"] else "PASS",
        "frontend_security": "WARN" if result["frontend_security"] else "PASS",
        "python": "PASS" if result["python_compile"].get("ok") else "FAIL",
        "pytest": result["pytest"].get("status", "UNKNOWN"),
        "build": result["npm_build"].get("status", "UNKNOWN")
    }

    REPORT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print()
    print("=" * 70)
    print("SELF AUDIT COMPLETE")
    print("=" * 70)
    print("报告：", REPORT)
    print("备份：", BACKUP)
    print()
    print("最终状态：")
    for k, v in result["final_status"].items():
        print(f"  {k}: {v}")

    print()
    print("注意：")
    print("发现的问题中，只有明确安全的问题才允许自动修复。")
    print("API/UI 结构性问题不会盲目改写，避免自动修复破坏现有功能。")

if __name__ == "__main__":
    main()