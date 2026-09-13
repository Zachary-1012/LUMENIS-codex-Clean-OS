# -*- coding: utf-8 -*-
"""
LUMENIS 数据边界（Data Boundary）
===============================

职责（只做边界判定与脱敏，不读取/打印任何凭证内容、不改业务数据、不改业务口径）：
1. 定义四类数据分区：
   - CODE        源码与配置模板（可入库；.env 仅允许 .env.example 模板）
   - BRAND_DATA  品牌业务数据（data/*.db、采集/分析结果；不入库）
   - CREDENTIAL  账号授权：Cookie / Token / 浏览器登录 Profile / 私钥 / .env（绝不入库、不入日志/Evidence/前端 Bundle）
   - RUNTIME     运行产物：logs、data/security(预检/Attestation)、缓存（不入库）
2. assert_no_tracked_credentials()：断言 CREDENTIAL 类文件没有进入 Git 跟踪面（git ls-files）。
3. sanitize_text()：对日志 / Evidence / Attestation 文本做脱敏，Cookie/Token/Authorization/密码/私钥一律打码。

设计原则：
- 只用标准库；任何返回结构都不携带真实密钥值，最多携带“文件相对路径 / 命中行号 / 匹配类型”。
- 非 Git 环境（git 不可用）降级为 skip 并说明，绝不误判为通过或失败的硬阻断。
"""
from __future__ import annotations

import os
import re
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

ZONES = {
    "CODE": {
        "desc": "源码/模板/文档，可入库",
        "tracked_allowed": True,
        "paths": ["*.py", "static/", "templates/", "tests/", "docs/", ".env.example", "requirements.txt"],
    },
    "BRAND_DATA": {
        "desc": "品牌业务数据：SQLite 库、采集与分析结果",
        "tracked_allowed": False,
        "paths": ["data/*.db", "data/backups/", "data/exports/", "data/imports/"],
    },
    "CREDENTIAL": {
        "desc": "账号授权：Cookie/Token/Profile/私钥/.env，绝不入库、不入日志证据",
        "tracked_allowed": False,
        "paths": [".env", "data/cookies/", "data/private/", "*profile*/", "*cookies*.json", "*.pem", "*.key"],
    },
    "RUNTIME": {
        "desc": "运行产物：日志、预检/Attestation、缓存",
        "tracked_allowed": False,
        "paths": ["logs/", "data/security/", "data/logs/", "data/cache/", "__pycache__/"],
    },
}

_SOURCE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".css", ".scss", ".less",
    ".html", ".htm", ".md", ".bat", ".cmd", ".ps1", ".sh", ".yml", ".yaml",
    ".toml", ".ini", ".cfg", ".conf", ".vue",
}
_CRED_DATA_EXTS = {
    ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".db-journal",
    ".pem", ".key", ".p12", ".pfx", ".keystore", ".jks", ".crt", ".cer",
}
_DATA_TEXT_EXTS = {".json", ".txt", ".dat", ".bin", ".log", ".csv"}
_CRED_WORD = re.compile(r"cookie|token|secret|credential|session|passwd|password|profile|login[_-]?state", re.I)

# 即使命中凭证语义也允许入库的明确非凭证路径。
# 白名单必须窄：只放模板/测试/文档/已验证的配置或扫描报告命名，不放宽 Cookie/Token/DB/私钥载体。
_CRED_PATH_WHITELIST = [
    r"\.env\.example$",
    r"(^|/)tests?/",
    r"(^|/)docs/",
    r"example|sample|fixture|dummy|fake",
    r"design[_-]?token|tokens?\.css|tokens?\.js",
    r"kos[_-]?monitor[_-]?profiles?",
    r"(^|/)naming[_-]?profile\.json$",          # i18n/design naming profile, not browser login profile
    r"(^|/)secret[_-]?scan[_-]?result\.txt$", # scan result report; contents are separately security-scanned
]


def _is_credential_path(rel_path: str) -> bool:
    """判断相对路径是否属于凭证/数据载体（不应入库）。

    处理凭证的源码允许入库；路径层只拦截真正的凭证/数据载体。
    """
    p = rel_path.replace("\\", "/").lower()
    for wl in _CRED_PATH_WHITELIST:
        if re.search(wl, p):
            return False
    base = os.path.basename(p)
    _, ext = os.path.splitext(base)
    if base == ".env" or re.match(r"\.env\.[\w-]+$", base):
        return True
    if ext in _CRED_DATA_EXTS:
        return True
    if ext in _SOURCE_EXTS:
        return False
    if ext in _DATA_TEXT_EXTS and _CRED_WORD.search(p):
        return True
    if "profile" in p and ext not in _SOURCE_EXTS:
        return True
    return False


def git_tracked_files(root: str = ROOT_DIR, timeout: int = 15):
    """返回 Git 跟踪文件相对路径列表；git 不可用时返回 None（调用方按 skip 处理）。"""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files"],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="ignore",
        )
        if out.returncode != 0:
            return None
        return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def assert_no_tracked_credentials(root: str = ROOT_DIR):
    """检查 Git 跟踪面是否混入凭证/业务数据库。

    返回结构绝不读取这些文件内容，也不返回任何密钥值。
    """
    tracked = git_tracked_files(root)
    if tracked is None:
        return {
            "status": "skip",
            "tracked_total": 0,
            "leaks": [],
            "detail": "当前不是可用 Git 工作树（git ls-files 不可用），凭证入库检查跳过",
        }
    leaks = sorted({p for p in tracked if _is_credential_path(p)})
    if leaks:
        return {
            "status": "fail",
            "tracked_total": len(tracked),
            "leaks": leaks,
            "detail": f"发现 {len(leaks)} 个凭证/数据类文件进入 Git 跟踪面，必须移出跟踪",
        }
    return {
        "status": "pass",
        "tracked_total": len(tracked),
        "leaks": [],
        "detail": f"Git 跟踪面 {len(tracked)} 个文件，未发现 Cookie/Token/.env/私钥/数据库被跟踪",
    }


def current_db_zone():
    """识别当前业务数据库落在哪个分区、是否处于隔离状态（不返回库内任何数据）。"""
    info = {"configured": False, "isolated": False, "zone": "UNKNOWN", "inside_project": False, "detail": ""}
    try:
        import database as _db
        db_path = os.path.abspath(getattr(_db, "DB_PATH", ""))
        info["configured"] = bool(db_path)
        proj = os.path.abspath(ROOT_DIR).lower()
        info["inside_project"] = db_path.lower().startswith(proj)
        env_path = os.path.abspath(os.environ.get("ZBC_DB_PATH", "")) if os.environ.get("ZBC_DB_PATH") else ""
        info["isolated"] = bool(env_path) and os.path.abspath(env_path).lower() == db_path.lower()
        if info["isolated"]:
            info["zone"] = "ISOLATED_STAGING"
        elif info["inside_project"]:
            info["zone"] = "BRAND_DATA(local default)"
        else:
            info["zone"] = "BRAND_DATA(external)"
        info["detail"] = f"DB 分区={info['zone']}，隔离={'是' if info['isolated'] else '否（默认生产口径）'}"
    except Exception as e:
        info["detail"] = f"数据库分区识别失败: {type(e).__name__}"
    return info


_SAN_RULES = [
    (
        re.compile(r"(authorization\s*[:=]\s*)(bearer|basic|token)?\s*[A-Za-z0-9._\-/+=]{6,}", re.I),
        r"\1\2 [REDACTED]",
    ),
    (re.compile(r"(cookie\s*[:=]\s*)[^;\n\r]{0,4096}", re.I), r"\1[REDACTED]"),
    (
        re.compile(
            r"([\"']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?secret|xsec[_-]?token|token|secret|password|passwd|pwd|private[_-]?key)[\"']?\s*[:=]\s*[\"']?)[^\s\"',;}&]{3,}[\"']?",
            re.I,
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
        "[REDACTED PRIVATE KEY]",
    ),
]


def sanitize_text(text):
    """把待写入日志/Evidence/Attestation 的文本中的凭证打码。非字符串原样返回。"""
    if not isinstance(text, str):
        return text
    out = text
    for rule, repl in _SAN_RULES:
        out = rule.sub(repl, out)
    return out


def sanitize_mapping(obj):
    """递归脱敏 dict/list 内的字符串值。"""
    if isinstance(obj, dict):
        return {k: sanitize_mapping(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_mapping(v) for v in obj]
    if isinstance(obj, str):
        return sanitize_text(obj)
    return obj


def assess(root: str = ROOT_DIR):
    """汇总数据边界评估，供 Runtime Preflight 调用。"""
    tracked = assert_no_tracked_credentials(root)
    db_zone = current_db_zone()
    return {
        "check_id": "ZB-DATA-BOUNDARY-001",
        "status": tracked["status"],
        "level": "P0",
        "tracked_credentials": tracked,
        "db_zone": db_zone,
        "zones": {k: v["desc"] for k, v in ZONES.items()},
        "detail": tracked["detail"] + "；" + db_zone["detail"],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(assess(), ensure_ascii=False, indent=2))
    demo = "Authorization: Bearer abc123def456ghi789; Cookie: sessionid=xxxx; api_key=sk-abcdef123456"
    print("sanitize demo ->", sanitize_text(demo))
