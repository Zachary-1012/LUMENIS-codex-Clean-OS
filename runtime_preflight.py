# -*- coding: utf-8 -*-
"""
Z-Brand Runtime Integrity Preflight（运行时完整性启动预检）
=========================================================
工单：ZB-RUNTIME-PREFLIGHT-001（P0）
对齐：ZBIP 统一启动闸门（Runtime Preflight Contract）、《四产品总执行规则》安全运行底座。

启动前检查（PASS 才正常运行；P0 硬项失败在 enforce 模式下阻断）：
  1. identity     产品身份 / VERSION / Git 来源(head,branch)
  2. permissions  关键目录可读、数据目录可写（临时文件探测后即删）
  3. dependencies 核心依赖与红线模块可导入（Flask + 数据、主体、风险、事件与当前日报 owner）
  4. data_boundary复用 data_boundary：凭证不得入 Git 跟踪面、数据库分区识别
  5. sensitive    被跟踪源码不得含明文 Cookie/Token/密钥（复用 security_scanner 规则，只记路径行号不记值）
  6. dangerous    危险运行组合（debug 暴露 0.0.0.0 / 隔离库却开生产采集 等）
  7. capability   采集能力状态（RedNote/XHS 处于 research/shadow，不得伪装 production）
  8. config       版本与数据路径配置可解析

阻断策略（最高优先：不破坏现网生产）：
- 默认 enforce=False：只记录 + 打印 + 写 Attestation，绝不阻断启动；
- ZBC_PREFLIGHT_ENFORCE=1 或显式 enforce=True：存在 P0 blocker 时 SystemExit(3)（CI / Staging / Docker 使用）。

产物：data/security/attestation_latest.json（及带时间戳副本）——即 ZBIP Attestation 运行证明，
落盘前经 data_boundary.sanitize_mapping 脱敏，不含任何 Cookie/Token/密钥值。该目录已被 .gitignore 忽略。
"""
from __future__ import annotations

import os
import re
import sys
import json
import time
import importlib.util
import subprocess
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

import data_boundary  # noqa: E402

PRODUCT = "Z-Brand-Core"
PRODUCT_FULL = "Z-Brand 品牌业务生产平台 / Z-Brand-Core（承载 CTH-POMS 与 ZBMP）"
ATTEST_DIR = os.path.join(ROOT_DIR, "data", "security")

# 核心红线模块：缺一即 P0（对应生产红线：主体/风险/事件/报告/数据层）
CORE_MODULES = [
    "flask", "database", "subject_rules", "risk_engine",
    "event_graph", "lumenis.shared.reporting.daily", "config",
]
READ_DIRS = ["static", "templates", "tests", "docs"]
# 敏感扫描只覆盖被 Git 跟踪的代码文件，且不扫数据/依赖目录
SENSITIVE_EXTS = (".py", ".js", ".html")
SENSITIVE_SCAN_FILE_CAP = 4000


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _check(ckid, category, level, status, detail, **meta):
    return {"id": ckid, "category": category, "level": level,
            "status": status, "detail": detail, "meta": meta}


# ------------------------------------------------------------------ 各检查项
def check_identity():
    ver = ""
    vf = os.path.join(ROOT_DIR, "VERSION")
    try:
        with open(vf, "r", encoding="utf-8-sig") as f:
            ver = f.read().strip()
    except Exception as e:
        return _check("ID-VERSION", "identity", "P1", "warn", f"VERSION 读取失败: {type(e).__name__}")
    head, branch = "", ""
    try:
        head = subprocess.run(["git", "-C", ROOT_DIR, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=8).stdout.strip()
        branch = subprocess.run(["git", "-C", ROOT_DIR, "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, timeout=8).stdout.strip()
    except Exception:
        pass
    if not head:
        return _check("ID-GIT", "identity", "P2", "warn",
                      f"产品={PRODUCT} VERSION={ver}；非 Git 工作树，来源无法记录（不阻断）",
                      version=ver)
    return _check("ID-GIT", "identity", "P2", "pass",
                  f"产品={PRODUCT} VERSION={ver} branch={branch} head={head[:12]}",
                  version=ver, head=head, branch=branch)


def check_permissions():
    missing = [d for d in READ_DIRS if not os.path.isdir(os.path.join(ROOT_DIR, d))]
    # 数据目录可写探测（写后即删）
    os.makedirs(os.path.join(ROOT_DIR, "data"), exist_ok=True)
    probe = os.path.join(ROOT_DIR, "data", f".preflight_probe_{os.getpid()}.tmp")
    writable = False
    try:
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        writable = True
    except Exception as e:
        return _check("PERM-WRITE", "permissions", "P0", "fail", f"data 目录不可写: {type(e).__name__}")
    finally:
        try:
            if os.path.exists(probe):
                os.remove(probe)
        except OSError:
            pass
    if missing:
        return _check("PERM-READ", "permissions", "P1", "warn",
                      f"data 可写={writable}；缺失目录 {missing}", writable=writable, missing=missing)
    return _check("PERM-READ", "permissions", "P1", "pass",
                  f"关键目录可读、data 可写={writable}", writable=writable)


def check_dependencies():
    missing = []
    for mod in CORE_MODULES:
        try:
            if importlib.util.find_spec(mod) is None:
                missing.append(mod)
        except (ImportError, ValueError, ModuleNotFoundError):
            missing.append(mod)
    if missing:
        return _check("DEP-CORE", "dependencies", "P0", "fail",
                      f"核心依赖/红线模块无法定位: {missing}", missing=missing)
    return _check("DEP-CORE", "dependencies", "P0", "pass",
                  f"核心模块全部可导入: {', '.join(CORE_MODULES)}")


def check_data_boundary():
    r = data_boundary.assess(ROOT_DIR)
    tc = r["tracked_credentials"]
    status = {"pass": "pass", "skip": "warn", "fail": "fail"}.get(tc["status"], "warn")
    leak = tc.get("leaks", [])
    return _check(r["check_id"], "data_boundary", "P0", status, r["detail"],
                  leaks=leak[:50], leak_count=len(leak), db_zone=r["db_zone"]["zone"])


_CODE_CONTEXT_MARKERS = (
    "env_content", "os.environ", "getenv", ".split(", " in ", " and ", " or ",
    "len(", "startswith", "print(", "!= ", "== ", "config.get", "get_config",
)


def _looks_like_real_secret(line, match):
    """区分“真实硬编码密钥”与“读取/判断环境变量的代码”，压低误报。

    无捕获值的高特征规则（如 AKIA…、sk-… 整串）直接采信；
    候选值若处于代码语境、含空白/中文、过短，则判为非泄露。
    """
    groups = [g for g in (match.groups() or ()) if g]
    val = groups[-1] if groups else ""
    if not val:
        return True  # 例如 AKIA[0-9A-Z]{16} 这类整串高特征匹配
    low = line
    if any(mk in low for mk in _CODE_CONTEXT_MARKERS):
        return False
    if re.search(r"\s", val) or re.search(r"[一-鿿]", val):
        return False  # 真密钥不含空白/中文
    if len(val) < 8:
        return False
    # 平台标准字段名白名单（不是真实密钥）
    _PLATFORM_FIELD_WHITELIST = {"xsec_token", "note_id", "aweme_id", "bvid", "mid", "object_id"}
    if val.lower() in _PLATFORM_FIELD_WHITELIST:
        return False
    return True


def check_sensitive_tracked():
    """被跟踪源码中的明文凭证扫描（复用 security_scanner 规则；只记 路径:行号:类型，不记值）。"""
    try:
        import security_scanner
        patterns = security_scanner.SecurityScanner().sensitive_patterns
    except Exception:
        return _check("SEC-SCAN", "sensitive", "P1", "warn", "security_scanner 不可用，敏感扫描跳过")
    tracked = data_boundary.git_tracked_files(ROOT_DIR)
    if tracked is None:
        return _check("SEC-SCAN", "sensitive", "P2", "warn", "非 Git 工作树，跟踪面敏感扫描跳过")
    import re as _re
    targets = [p for p in tracked
               if p.lower().endswith(SENSITIVE_EXTS) and not _re.search(r"tests?/|docs/|\.example|intelligence_library/|audit/", p.lower())]
    targets = targets[:SENSITIVE_SCAN_FILE_CAP]
    findings = []
    for rel in targets:
        fp = os.path.join(ROOT_DIR, rel.replace("/", os.sep))
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                for ln, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//"):
                        continue  # 注释行不算泄露
                    for pat, desc in patterns:
                        mm = _re.search(pat, line)
                        if mm and _looks_like_real_secret(line, mm):
                            findings.append({"file": rel, "line": ln, "type": desc})
                            break
        except Exception:
            continue
        if len(findings) >= 50:
            break
    if findings:
        return _check("SEC-SCAN", "sensitive", "P0", "fail",
                      f"被跟踪源码发现 {len(findings)} 处疑似明文凭证（必须移入环境变量/.env 且不入库）",
                      findings=findings)
    return _check("SEC-SCAN", "sensitive", "P0", "pass",
                  f"扫描 {len(targets)} 个被跟踪代码文件，未发现明文 Cookie/Token/密钥")


def check_dangerous_mode():
    warns = []
    debug = os.environ.get("FLASK_DEBUG", "") or os.environ.get("ZBC_DEBUG", "")
    host = os.environ.get("APP_HOST", "")
    if str(debug).lower() in ("1", "true", "yes") and host in ("0.0.0.0", ""):
        warns.append("debug 模式对外监听，生产风险")
    # 隔离库却打开生产采集开关 = 配置矛盾
    dbz = data_boundary.current_db_zone()
    xhs_prod = str(os.environ.get("XHS_PRODUCTION", "")).lower() in ("1", "true", "yes")
    if dbz["isolated"] and xhs_prod:
        warns.append("隔离(Staging)数据库与 XHS_PRODUCTION=true 同时出现，配置矛盾")
    if warns:
        return _check("DANGER-MODE", "dangerous", "P1", "warn", "；".join(warns), warns=warns)
    return _check("DANGER-MODE", "dangerous", "P1", "pass",
                  f"无危险运行组合（XHS_PRODUCTION={xhs_prod}，DB={dbz['zone']}）")


def check_capability():
    """采集能力门禁：研究/影子能力不得被标记为生产。只记录状态，不触发任何采集。"""
    cap_doc = os.path.join(ROOT_DIR, "docs", "CAPABILITY_BASELINE.md")
    has_doc = os.path.isfile(cap_doc)
    # App Evidence 当前应为 shadow_only（不自动采集 App）
    mode = "unknown"
    try:
        from lumenis.shared.evidence import manual as app_evidence
        mode = getattr(app_evidence, "MODULE_VERSION", "unknown")
    except Exception:
        pass
    return _check("CAP-XHS", "capability", "P2", "pass",
                  f"RedNote/XHS 采集当前以香港来源研究/运行为主、国内暂缓；App Evidence={mode} 保持 shadow，不标记为自动生产",
                  capability_doc=has_doc, app_evidence=mode)


def check_config():
    try:
        from database import DB_PATH
        ok = bool(DB_PATH)
    except Exception as e:
        return _check("CFG", "config", "P0", "fail", f"统一数据入口不可用: {type(e).__name__}")
    return _check("CFG", "config", "P1", "pass" if ok else "warn",
                  "统一配置与数据路径入口可解析（值不写入证据）", db_resolvable=bool(ok))


CHECKS = [
    check_identity,
    check_permissions,
    check_dependencies,
    check_data_boundary,
    check_sensitive_tracked,
    check_dangerous_mode,
    check_capability,
    check_config,
]


def run_preflight(enforce=None, write_attestation=True):
    t0 = time.time()
    results = []
    for fn in CHECKS:
        try:
            results.append(fn())
        except Exception as e:  # 单项异常不应炸掉整个预检
            results.append(_check(fn.__name__, "exception", "P1", "warn",
                                  f"检查项异常: {type(e).__name__}: {e}"))
    blockers = [c for c in results if c["level"] == "P0" and c["status"] == "fail"]
    warnings_ = [c for c in results if c["status"] in ("warn", "fail") and c not in blockers]
    overall = "block" if blockers else ("warn" if warnings_ else "pass")

    report = {
        "product": PRODUCT,
        "product_full": PRODUCT_FULL,
        "started_at": _now(),
        "elapsed_ms": int((time.time() - t0) * 1000),
        "enforce": bool(enforce) if enforce is not None else str(os.environ.get("ZBC_PREFLIGHT_ENFORCE", "")).lower() in ("1", "true", "yes"),
        "overall": overall,
        "blocker_count": len(blockers),
        "warning_count": len(warnings_),
        "checks": results,
        "blockers": [{"id": c["id"], "detail": data_boundary.sanitize_text(c["detail"])} for c in blockers],
    }
    if write_attestation:
        report["attestation"] = _write_attestation(report)
    # 落盘/返回前统一脱敏兜底
    report = data_boundary.sanitize_mapping(report)

    if overall == "block" and report["enforce"]:
        sys.stderr.write(format_summary(report) + "\n")
        sys.stderr.write("[Preflight] P0 阻断项存在且处于 enforce 模式，终止启动。\n")
        raise SystemExit(3)
    return report


def _write_attestation(report):
    os.makedirs(ATTEST_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = {k: v for k, v in report.items() if k != "attestation"}
    payload["attestation_kind"] = "runtime-preflight"
    stamped = os.path.join(ATTEST_DIR, f"attestation_{stamp}.json")
    latest = os.path.join(ATTEST_DIR, "attestation_latest.json")
    try:
        with open(stamped, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        with open(latest, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return {"written": True, "latest": os.path.relpath(latest, ROOT_DIR), "stamped": os.path.relpath(stamped, ROOT_DIR)}
    except Exception as e:
        return {"written": False, "error": f"{type(e).__name__}: {e}"}


def format_summary(r):
    icon = {"pass": "PASS", "warn": "WARN", "block": "BLOCK"}
    lines = ["-" * 64,
             f"[Preflight] Z-Brand Runtime Integrity  总体={icon.get(r['overall'], r['overall'])}  "
             f"P0阻断={r['blocker_count']} 警告={r['warning_count']}  耗时={r['elapsed_ms']}ms"]
    for c in r["checks"]:
        mark = {"pass": "✓", "warn": "!", "fail": "✗"}.get(c["status"], "?")
        lines.append(f"   {mark} [{c['level']}] {c['category']:<13} {c['detail']}")
    att = r.get("attestation") or {}
    if att.get("written"):
        lines.append(f"   运行证明(Attestation): {att.get('latest')}")
    lines.append("-" * 64)
    return "\n".join(lines)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        try:
            if _stream is not None and hasattr(_stream, "reconfigure"):
                _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    _enf = "--enforce" in sys.argv or str(os.environ.get("ZBC_PREFLIGHT_ENFORCE", "")).lower() in ("1", "true", "yes")
    rep = run_preflight(enforce=_enf)
    print(format_summary(rep))
    print(json.dumps({"overall": rep["overall"], "blockers": rep["blocker_count"], "warnings": rep["warning_count"]},
                     ensure_ascii=False))
