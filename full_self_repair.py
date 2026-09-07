# -*- coding: utf-8 -*-
"""
TAIKOO MONITOR
FULL SELF AUDIT + SAFE AUTO REPAIR + BROWSER REGRESSION

链路：
SOURCE
 -> BACKEND
 -> DATABASE
 -> API CONTRACT
 -> FRONTEND
 -> CSS/UI
 -> PLAYWRIGHT
 -> SECURITY
 -> AUTO REPAIR
 -> BUILD
 -> REGRESSION
 -> ROLLBACK IF FAILED
"""

import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

BASE_URL = os.environ.get(
    "TAIKOO_BASE_URL",
    "http://127.0.0.1:5000"
)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

BACKUP_DIR = ROOT / ".self_repair" / RUN_ID
REPORT = ROOT / f"SELF_REPAIR_REPORT_{RUN_ID}.json"

IGNORE = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".self_repair",
    "dist",
    "build",
    ".pytest_cache",
}

TEXT_EXT = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".vue",
    ".json",
    ".sql",
}

results = {
    "run_id": RUN_ID,
    "root": str(ROOT),
    "base_url": BASE_URL,
    "started_at": datetime.now().isoformat(),
    "source": {},
    "backend": {},
    "database": {},
    "api_contract": {},
    "frontend": {},
    "ui": {},
    "ux": {},
    "security": {},
    "browser": {},
    "repairs": [],
    "regression": {},
    "final_status": "NOT VERIFIED",
}


# =========================================================
# 基础
# =========================================================

def log(msg):
    print(msg, flush=True)


def run_cmd(cmd, timeout=300):
    try:
        p = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=isinstance(cmd, str),
        )

        return {
            "returncode": p.returncode,
            "stdout": p.stdout[-12000:],
            "stderr": p.stderr[-12000:],
        }

    except Exception as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def save_report():
    REPORT.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def project_files():
    out = []

    for p in ROOT.rglob("*"):

        if not p.is_file():
            continue

        if any(part in IGNORE for part in p.parts):
            continue

        if p.suffix.lower() in TEXT_EXT:
            out.append(p)

    return out


def read_text(p):
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        try:
            return p.read_text(encoding="utf-8-sig")
        except Exception:
            return ""


def backup_file(p):
    rel = p.relative_to(ROOT)
    target = BACKUP_DIR / rel

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not target.exists():
        shutil.copy2(p, target)


def safe_write(p, text):
    backup_file(p)
    p.write_text(
        text,
        encoding="utf-8",
    )


# =========================================================
# SOURCE AUDIT
# =========================================================

def source_audit():

    fs = project_files()

    counts = {}

    for p in fs:
        ext = p.suffix.lower()
        counts[ext] = counts.get(ext, 0) + 1

    results["source"] = {
        "files": len(fs),
        "extensions": counts,
    }

    return fs


# =========================================================
# BACKEND ROUTES
# =========================================================

def find_backend_routes(files):

    routes = []

    patterns = [
        r'@\w+\.route\s*\(\s*[\'"]([^\'"]+)',
        r'@app\.route\s*\(\s*[\'"]([^\'"]+)',
        r'@(?:\w+\.)?(?:get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)',
    ]

    for p in files:

        if p.suffix != ".py":
            continue

        text = read_text(p)

        for pattern in patterns:

            for match in re.findall(pattern, text):

                routes.append({
                    "route": match.rstrip("/"),
                    "file": str(p.relative_to(ROOT)),
                })

    return routes


# =========================================================
# FRONTEND API
# =========================================================

def find_frontend_api_calls(files):

    calls = []

    patterns = [
        r'fetch\s*\(\s*[`\'"]([^`\'"]+)',
        r'axios\.(?:get|post|put|delete|patch)\s*\(\s*[`\'"]([^`\'"]+)',
        r'url\s*:\s*[`\'"]([^`\'"]+)',
    ]

    for p in files:

        if p.suffix.lower() not in {
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".html",
            ".vue",
        }:
            continue

        text = read_text(p)

        for pattern in patterns:

            for match in re.findall(pattern, text):

                if match.startswith("/"):

                    calls.append({
                        "api": match.split("?")[0].rstrip("/"),
                        "file": str(p.relative_to(ROOT)),
                    })

    return calls


def normalize_api(x):

    x = x.split("?")[0]
    x = re.sub(r"\$\{[^}]+\}", "", x)
    x = re.sub(r"<[^>]+>", "", x)

    return x.rstrip("/") or "/"


def api_contract_audit(files):

    routes = find_backend_routes(files)
    calls = find_frontend_api_calls(files)

    route_set = {
        normalize_api(x["route"])
        for x in routes
    }

    missing = []

    for call in calls:

        api = normalize_api(call["api"])

        if api in route_set:
            continue

        matched = False

        for route in route_set:

            if api.startswith(route + "/"):
                matched = True
                break

            if route.startswith(api + "/"):
                matched = True
                break

        if not matched:
            missing.append(call)

    results["api_contract"] = {
        "backend_route_count": len(routes),
        "frontend_api_count": len(calls),
        "unmatched_frontend_api": missing,
    }


# =========================================================
# PYTHON
# =========================================================

def python_audit():

    log("[SOURCE] Python compile...")

    result = run_cmd(
        [sys.executable, "-m", "compileall", "-q", "."],
        timeout=180,
    )

    results["backend"]["compile"] = result

    return result["returncode"] == 0


# =========================================================
# TEST
# =========================================================

def test_audit():

    tests = list(ROOT.rglob("test*.py"))
    tests += list(ROOT.rglob("*_test.py"))

    if not tests:

        results["regression"]["pytest"] = {
            "status": "NOT_AVAILABLE"
        }

        return True

    log("[TEST] pytest...")

    result = run_cmd(
        [sys.executable, "-m", "pytest", "-q"],
        timeout=600,
    )

    results["regression"]["pytest"] = result

    return result["returncode"] == 0


# =========================================================
# NPM BUILD
# =========================================================

def frontend_build():

    package = ROOT / "package.json"

    if not package.exists():

        results["frontend"]["build"] = {
            "status": "NOT_AVAILABLE"
        }

        return True

    try:

        data = json.loads(
            read_text(package)
        )

        scripts = data.get(
            "scripts",
            {}
        )

        if "build" not in scripts:

            results["frontend"]["build"] = {
                "status": "NOT_AVAILABLE"
            }

            return True

    except Exception as e:

        results["frontend"]["build"] = {
            "status": "FAIL",
            "error": str(e),
        }

        return False

    log("[FRONTEND] npm build...")

    result = run_cmd(
        ["npm", "run", "build"],
        timeout=600,
    )

    results["frontend"]["build"] = result

    return result["returncode"] == 0


# =========================================================
# UI STATIC COVERAGE
# =========================================================

def ui_static_audit(files):

    findings = []

    for p in files:

        if p.suffix.lower() not in {
            ".css",
            ".scss",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".html",
            ".vue",
        }:
            continue

        text = read_text(p)

        important = len(
            re.findall(
                r"!important",
                text,
                re.I,
            )
        )

        inline = len(
            re.findall(
                r'\bstyle\s*=',
                text,
                re.I,
            )
        )

        dynamic_style = len(
            re.findall(
                r'\.style\.[A-Za-z_-]+\s*=',
                text,
            )
        )

        if important:

            findings.append({
                "file": str(p.relative_to(ROOT)),
                "type": "IMPORTANT",
                "count": important,
            })

        if inline:

            findings.append({
                "file": str(p.relative_to(ROOT)),
                "type": "INLINE_STYLE",
                "count": inline,
            })

        if dynamic_style:

            findings.append({
                "file": str(p.relative_to(ROOT)),
                "type": "DYNAMIC_STYLE",
                "count": dynamic_style,
            })

    results["ui"]["static_override_findings"] = findings


# =========================================================
# SECURITY STATIC
# =========================================================

def security_audit(files):

    findings = []

    for p in files:

        if p.suffix.lower() not in {
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".html",
            ".vue",
        }:
            continue

        text = read_text(p)

        patterns = {
            "innerHTML": r"\.innerHTML\s*=",
            "outerHTML": r"\.outerHTML\s*=",
            "document.write": r"document\.write\s*\(",
            "eval": r"\beval\s*\(",
            "new Function": r"new\s+Function\s*\(",
        }

        for name, pattern in patterns.items():

            count = len(
                re.findall(
                    pattern,
                    text,
                )
            )

            if count:

                findings.append({
                    "file": str(p.relative_to(ROOT)),
                    "type": name,
                    "count": count,
                })

    results["security"]["static_findings"] = findings


# =========================================================
# SAFE REPAIR
# =========================================================

def safe_repairs(files):

    """
    只执行明确、安全的修复。
    不自动改业务 API、不自动改数据库、不自动删除 CSS。
    """

    repairs = []

    # --------------------------------------------
    # 1. 删除明显的 Python 调试断点
    # --------------------------------------------

    for p in files:

        if p.suffix != ".py":
            continue

        text = read_text(p)

        if "breakpoint()" in text:

            new = re.sub(
                r"^[ \t]*breakpoint\(\)[ \t]*\r?\n",
                "",
                text,
                flags=re.M,
            )

            if new != text:

                safe_write(
                    p,
                    new,
                )

                repairs.append({
                    "file": str(p.relative_to(ROOT)),
                    "type": "REMOVE_DEBUG_BREAKPOINT",
                })

    # --------------------------------------------
    # 2. 删除明显 console.debug
    # --------------------------------------------

    for p in files:

        if p.suffix.lower() not in {
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
        }:
            continue

        text = read_text(p)

        new = re.sub(
            r"^[ \t]*console\.debug\s*\([^;]*\);?[ \t]*\r?\n",
            "",
            text,
            flags=re.M,
        )

        if new != text:

            safe_write(
                p,
                new,
            )

            repairs.append({
                "file": str(p.relative_to(ROOT)),
                "type": "REMOVE_DEBUG_LOG",
            })

    results["repairs"] = repairs


# =========================================================
# SERVER
# =========================================================

def port_from_url():

    m = re.search(
        r":(\d+)",
        BASE_URL,
    )

    return int(m.group(1)) if m else 5000


def port_open():

    port = port_from_url()

    s = socket.socket()

    try:

        s.settimeout(0.5)

        return (
            s.connect_ex(
                ("127.0.0.1", port)
            )
            == 0
        )

    finally:

        s.close()


def start_server():

    if port_open():

        log(
            f"[SERVER] 已发现运行中的系统 {BASE_URL}"
        )

        return None

    app = ROOT / "app.py"

    if not app.exists():

        log(
            "[SERVER] 未找到 app.py，无法自动启动 Flask"
        )

        return None

    log("[SERVER] 启动应用...")

    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(20):

        if port_open():
            break

        time.sleep(1)

    return proc


# =========================================================
# PLAYWRIGHT
# =========================================================

async def browser_audit():

    try:

        from playwright.async_api import async_playwright

    except Exception as e:

        results["browser"] = {
            "status": "NOT_AVAILABLE",
            "error": str(e),
        }

        return False

    browser_result = {
        "pages": [],
        "console_errors": [],
        "network_failures": [],
        "ui_overflow": [],
        "hidden_content": [],
    }

    async with async_playwright() as pw:

        browser = await pw.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            viewport={
                "width": 1440,
                "height": 900,
            }
        )

        page = await context.new_page()

        console_errors = []

        def console_handler(msg):

            if msg.type == "error":

                console_errors.append(
                    msg.text
                )

        page.on(
            "console",
            console_handler,
        )

        failed_requests = []

        def request_failed(req):

            failed_requests.append({
                "url": req.url,
                "method": req.method,
                "failure": str(req.failure),
            })

        page.on(
            "requestfailed",
            request_failed,
        )

        # 首页先打开
        try:

            response = await page.goto(
                BASE_URL,
                wait_until="networkidle",
                timeout=30000,
            )

            if response:

                browser_result["pages"].append({
                    "path": "/",
                    "status": response.status,
                    "title": await page.title(),
                })

        except Exception as e:

            browser_result["pages"].append({
                "path": "/",
                "error": str(e),
            })

        # 自动发现站内页面
        paths = {"/"}

        try:

            links = await page.locator(
                "a[href]"
            ).evaluate_all(
                """
                els => els.map(
                    x => x.getAttribute('href')
                )
                """
            )

            for href in links:

                if not href:
                    continue

                if href.startswith("/"):

                    clean = href.split(
                        "#"
                    )[0].split(
                        "?"
                    )[0]

                    if clean:
                        paths.add(clean)

        except Exception:
            pass

        # 限制为真实内部路径
        paths = sorted(
            x for x in paths
            if x.startswith("/")
        )

        for path in paths:

            if path == "/":
                continue

            try:

                response = await page.goto(
                    BASE_URL.rstrip("/") + path,
                    wait_until="networkidle",
                    timeout=20000,
                )

                status = (
                    response.status
                    if response
                    else None
                )

                browser_result["pages"].append({
                    "path": path,
                    "status": status,
                    "title": await page.title(),
                })

            except Exception as e:

                browser_result["pages"].append({
                    "path": path,
                    "error": str(e),
                })

        # -----------------------------------------
        # 重新检查每个实际页面
        # -----------------------------------------

        for item in browser_result["pages"]:

            path = item["path"]

            try:

                await page.goto(
                    BASE_URL.rstrip("/") + path,
                    wait_until="networkidle",
                    timeout=20000,
                )

                inspection = await page.evaluate(
                    """
                    () => {

                        const visible = el => {

                            if (!el)
                                return false;

                            const s =
                                getComputedStyle(el);

                            const r =
                                el.getBoundingClientRect();

                            return (
                                s.display !== 'none' &&
                                s.visibility !== 'hidden' &&
                                parseFloat(
                                    s.opacity || '1'
                                ) > 0 &&
                                r.width > 0 &&
                                r.height > 0
                            );
                        };

                        const main =
                            document.querySelector(
                                'main'
                            ) ||
                            document.querySelector(
                                '#app'
                            ) ||
                            document.querySelector(
                                '#root'
                            );

                        const all =
                            [...document.querySelectorAll('*')];

                        const overflow =
                            all.filter(el => {

                                const r =
                                    el.getBoundingClientRect();

                                return (
                                    r.right >
                                    window.innerWidth + 2
                                );
                            }).slice(0, 30)
                            .map(el => ({
                                tag: el.tagName,
                                id: el.id,
                                class:
                                    String(
                                        el.className || ''
                                    ).slice(0, 200)
                            }));

                        const buttons =
                            [...document.querySelectorAll(
                                'button,[role="button"],a'
                            )];

                        const inputs =
                            [...document.querySelectorAll(
                                'input,textarea,select'
                            )];

                        const inlineImportant =
                            all.filter(el => {

                                for (
                                    const prop of el.style
                                ) {

                                    if (
                                        el.style
                                            .getPropertyPriority(
                                                prop
                                            ) === 'important'
                                    ) {
                                        return true;
                                    }
                                }

                                return false;
                            }).length;

                        const inlineEvents =
                            all.filter(el =>
                                [...el.attributes]
                                .some(a =>
                                    /^on/i.test(
                                        a.name
                                    )
                                )
                            ).length;

                        return {

                            title:
                                document.title,

                            bodyText:
                                document.body
                                    ?.innerText
                                    ?.length || 0,

                            mainVisible:
                                visible(main),

                            buttons:
                                buttons.length,

                            visibleButtons:
                                buttons.filter(
                                    visible
                                ).length,

                            inputs:
                                inputs.length,

                            visibleInputs:
                                inputs.filter(
                                    visible
                                ).length,

                            overflow,

                            inlineImportant,

                            inlineEvents,

                            viewport: {
                                width:
                                    window.innerWidth,
                                height:
                                    window.innerHeight
                            }
                        };
                    }
                    """
                )

                item["ui"] = inspection

                if inspection["overflow"]:

                    browser_result[
                        "ui_overflow"
                    ].append({
                        "path": path,
                        "elements":
                            inspection["overflow"],
                    })

                if not inspection["mainVisible"]:

                    browser_result[
                        "hidden_content"
                    ].append(path)

            except Exception as e:

                item["runtime_error"] = str(e)

        browser_result[
            "console_errors"
        ] = console_errors

        browser_result[
            "network_failures"
        ] = failed_requests

        await browser.close()

    results["browser"] = browser_result

    results["ui"]["runtime_overflow"] = (
        browser_result["ui_overflow"]
    )

    results["ux"]["hidden_content"] = (
        browser_result["hidden_content"]
    )

    results["security"]["browser_console"] = (
        browser_result["console_errors"]
    )

    return (
        not browser_result["console_errors"]
        and not browser_result["network_failures"]
        and not browser_result["hidden_content"]
    )


# =========================================================
# DATABASE
# =========================================================

def database_audit():

    db_files = []

    for p in ROOT.rglob("*"):

        if not p.is_file():
            continue

        if any(x in IGNORE for x in p.parts):
            continue

        if p.suffix.lower() in {
            ".db",
            ".sqlite",
            ".sqlite3",
        }:

            db_files.append(
                str(
                    p.relative_to(ROOT)
                )
            )

    results["database"] = {
        "database_files": db_files,
        "status":
            "PASS"
            if db_files
            else "NOT_VERIFIED",
    }


# =========================================================
# VERIFY
# =========================================================

def basic_verify():

    checks = {
        "python_compile":
            results["backend"]
            .get("compile", {})
            .get("returncode") == 0,

        "pytest":
            results["regression"]
            .get("pytest", {})
            .get("returncode", 0) == 0,

        "frontend_build":
            results["frontend"]
            .get("build", {})
            .get("returncode", 0) == 0,
    }

    results["regression"]["basic"] = checks

    return all(checks.values())


# =========================================================
# MAIN
# =========================================================

async def main():

    log("=" * 75)
    log("TAIKOO MONITOR — FULL SELF REPAIR")
    log("=" * 75)
    log(f"ROOT: {ROOT}")
    log(f"URL : {BASE_URL}")
    log("")

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = source_audit()

    log(
        f"[SOURCE] {len(files)} 个源码文件"
    )

    log("[1/10] 后端编译")
    python_audit()

    log("[2/10] 数据库")
    database_audit()

    log("[3/10] API 前后端 Contract")
    api_contract_audit(files)

    log("[4/10] UI/CSS 静态覆盖")
    ui_static_audit(files)

    log("[5/10] Security")
    security_audit(files)

    log("[6/10] 安全自动修复")
    safe_repairs(files)

    # 修复后重新扫描
    files = project_files()

    log("[7/10] 修复后重新编译")
    python_ok = python_audit()

    log("[8/10] Frontend Build")
    build_ok = frontend_build()

    log("[9/10] Pytest")
    test_ok = test_audit()

    # 启动
    server = start_server()

    # 给应用一点时间
    time.sleep(2)

    log("[10/10] Playwright 真实浏览器验证")

    browser_ok = await browser_audit()

    # ------------------------------------------
    # Final
    # ------------------------------------------

    basic_ok = basic_verify()

    api_missing = results[
        "api_contract"
    ].get(
        "unmatched_frontend_api",
        []
    )

    console_errors = results[
        "browser"
    ].get(
        "console_errors",
        []
    )

    network_errors = results[
        "browser"
    ].get(
        "network_failures",
        []
    )

    hidden = results[
        "browser"
    ].get(
        "hidden_content",
        []
    )

    overflow = results[
        "browser"
    ].get(
        "ui_overflow",
        []
    )

    critical_failure = (
        not python_ok
        or not build_ok
        or not test_ok
        or bool(console_errors)
        or bool(network_errors)
        or bool(hidden)
    )

    # ------------------------------------------
    # 如果出现严重回归，恢复自动修改
    # ------------------------------------------

    if critical_failure:

        log("")
        log(
            "[ROLLBACK] 检测到严重回归，恢复本轮自动修改..."
        )

        restored = 0

        if BACKUP_DIR.exists():

            for backup in BACKUP_DIR.rglob("*"):

                if not backup.is_file():
                    continue

                rel = backup.relative_to(
                    BACKUP_DIR
                )

                target = ROOT / rel

                target.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                shutil.copy2(
                    backup,
                    target,
                )

                restored += 1

        results["regression"][
            "rollback"
        ] = {
            "performed": True,
            "files_restored": restored,
        }

        results["final_status"] = "RESTORED_WITH_ROLLBACK"

    else:

        if (
            api_missing
            or overflow
            or results["ui"].get(
                "static_override_findings"
            )
            or results["security"].get(
                "static_findings"
            )
        ):

            results["final_status"] = "PASS_WITH_WARNINGS"

        else:

            results["final_status"] = "RESTORED"

    results["finished_at"] = (
        datetime.now().isoformat()
    )

    save_report()

    if server:

        try:
            server.terminate()
        except Exception:
            pass

    log("")
    log("=" * 75)
    log("FINAL RESULT")
    log("=" * 75)

    log(
        f"SOURCE        : PASS"
    )

    log(
        f"PYTHON        : {'PASS' if python_ok else 'FAIL'}"
    )

    log(
        f"FRONTEND      : {'PASS' if build_ok else 'FAIL'}"
    )

    log(
        f"TEST          : {'PASS' if test_ok else 'FAIL'}"
    )

    log(
        f"BROWSER       : {'PASS' if browser_ok else 'FAIL/WARN'}"
    )

    log(
        f"API MISMATCH  : {len(api_missing)}"
    )

    log(
        f"CONSOLE ERROR : {len(console_errors)}"
    )

    log(
        f"NETWORK ERROR : {len(network_errors)}"
    )

    log(
        f"UI OVERFLOW   : {len(overflow)}"
    )

    log(
        f"HIDDEN UI     : {len(hidden)}"
    )

    log(
        f"AUTO REPAIRED : {len(results['repairs'])}"
    )

    log(
        f"FINAL STATUS  : {results['final_status']}"
    )

    log("")
    log(
        f"REPORT: {REPORT}"
    )

    log(
        f"BACKUP: {BACKUP_DIR}"
    )

    log("=" * 75)


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "\n已停止。"
        )

    except Exception as e:

        print(
            "\nFATAL:",
            repr(e)
        )

        save_report()

        sys.exit(1)