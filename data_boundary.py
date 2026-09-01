# -*- coding: utf-8 -*-
"""
Z-Brand 数据边界（Data Boundary）
================================
工单：ZB-DATA-BOUNDARY-001（P0，《ZBIP_四产品_统一安全架构运行预检工单》Z-Brand 行）

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

# ------------------------------------------------------------------
# 1. 数据分区定义（相对根目录的归属；仅用于边界说明与判定，不移动任何文件）
# ------------------------------------------------------------------
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

# 源码 / 样式 / 脚本 / 文档：即使文件名含 cookie/token（如 xhs_cookie_bridge.py、tokens.css），
# 也属于“处理凭证的代码”而非凭证本身，路径层放行，改由 runtime_preflight 的内容层扫描把关。
_SOURCE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".css", ".scss", ".less",
    ".html", ".htm", ".md", ".bat", ".cmd", ".ps1", ".sh", ".yml", ".yaml",
    ".toml", ".ini", ".cfg", ".conf", ".vue", ".jsx",
}
# 凭证 / 业务数据“载体文件”扩展名：只要被跟踪即判越界
_CRED_DATA_EXTS = {
    ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".db-journal",
    ".pem", ".key", ".p12", ".pfx", ".keystore", ".jks", ".crt", ".cer",
}
# 数据/文本类载体：仅当路径同时带有凭证语义时才判越界（避免误伤普通业务 json）
_DATA_TEXT_EXTS = {".json", ".txt", ".dat", ".bin", ".log", ".csv"}
_CRED_WORD = re.compile(r"cookie|token|secret|credential|session|passwd|password|profile|login[_-]?state", re.I)
# 即使命中规则也允许入库的白名单（模板/示例/文档/测试夹具）
_CRED_PATH_WHITELIST = [
    r"\.env\.example$",
    r"(^|/)tests?/",                # 测试目录内的夹具
    r"(^|/)docs/",                  # 文档中的示例
    r"example|sample|fixture|dummy|fake",
    r"design[_-]?token|tokens?\.css|tokens?\.js",  # 设计 Token（CSS 变量），与凭证无关
]


def _is_credential_path(rel_path: str) -> bool:
    """判断一个相对路径是否属于凭证/数据“载体”（不应入库）。

    分层原则：处理凭证的【源码】(xhs_cookie_bridge.py / cookie_vault.py) 允许入库，
    由内容层扫描确认其不含明文；路径层只拦截真正的凭证/数据【载体文件】。白名单优先放行。
    """
    p = rel_path.replace("\\", "/").lower()
    for wl in _CRED_PATH_WHITELIST:
        if re.search(wl, p):
            return False
    base = os.path.basename(p)
    _, ext = os.path.splitext(base)
    # 1) .env 本体及其环境变体（.env.local / .env.prod）
    if base == ".env" or re.match(r"\.env\.[\w-]+$", base):
        return True
    # 2) 数据库 / 密钥库 / 证书载体
    if ext in _CRED_DATA_EXTS:
        return True
    # 3) 源码 / 样式 / 脚本：路径层放行（交给内容层 SEC-SCAN）
    if ext in _SOURCE_EXTS:
        return False
    # 4) 文本/数据载体且带凭证语义（如 cookies.json、session.dat、xxx_profile/ 下文件）
    if ext in _DATA_TEXT_EXTS and _CRED_WORD.search(p):
        return True
    # 5) 浏览器持久化登录 Profile 目录内的任意文件
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

    返回: {"status": "pass"|"fail"|"skip", "tracked_total": int, "leaks": [...相对路径...], "detail": str}
    绝不读取这些文件内容，也不返回任何密钥值。
    """
    tracked = git_tracked_files(root)
    if tracked is None:
        return {"status": "skip", "tracked_total": 0, "leaks": [],
                "detail": "当前不是可用 Git 工作树（git ls-files 不可用），凭证入库检查跳过"}
    leaks = sorted({p for p in tracked if _is_credential_path(p)})
    if leaks:
        return {"status": "fail", "tracked_total": len(tracked), "leaks": leaks,
                "detail": f"发现 {len(leaks)} 个凭证/数据类文件进入 Git 跟踪面，必须移出跟踪"}
    return {"status": "pass", "tracked_total": len(tracked), "leaks": [],
            "detail": f"Git 跟踪面 {len(tracked)} 个文件，未发现 Cookie/Token/.env/私钥/数据库被跟踪"}


def current_db_zone():
    """识别当前业务数据库落在哪个分区、是否处于隔离状态（不返回库内任何数据）。"""
    info = {"configured": False, "isolated": False, "zone": "UNKNOWN", "inside_project": False, "detail": ""}
    try:
        import database as _db  # 复用统一入口，避免另造路径口径
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
    except Exception as e:  # 数据库模块不可用时只告警，不伪造
        info["detail"] = f"数据库分区识别失败: {type(e).__name__}"
    return info


# ------------------------------------------------------------------
# 2. 日志 / Evidence 脱敏
# ------------------------------------------------------------------
# 顺序敏感：先处理“键=值 / 键: 值”，再处理 Authorization 头与私钥块
_SAN_RULES = [
    # Authorization: Bearer xxxx / Basic xxxx
    (re.compile(r"(authorization\s*[:=]\s*)(bearer|basic|token)?\s*[A-Za-z0-9._\-/+=]{6,}", re.I),
     r"\1\2 [REDACTED]"),
    # Cookie: a=b; c=d 整串
    (re.compile(r"(cookie\s*[:=]\s*)[^;\n\r]{0,4096}", re.I), r"\1[REDACTED]"),
    # 各种 key/token/secret/password = "值"（前缀统一消费键名两侧与值前引号，尾部再吃掉闭合引号）
    (re.compile(r"([\"']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?secret|xsec[_-]?token|token|secret|password|passwd|pwd|private[_-]?key)[\"']?\s*[:=]\s*[\"']?)[^\s\"',;}&]{3,}[\"']?", re.I),
     r"\1[REDACTED]"),
    # PEM 私钥块
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "[REDACTED PRIVATE KEY]"),
]


def sanitize_text(text):
    """把任意待写入日志/Evidence/Attestation 的文本中的凭证打码。非字符串原样返回。"""
    if not isinstance(text, str):
        return text
    out = text
    for rule, repl in _SAN_RULES:
        out = rule.sub(repl, out)
    return out


def sanitize_mapping(obj):
    """递归脱敏 dict/list 内的字符串值（用于 Attestation 落盘前最后一道闸）。"""
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
    status = tracked["status"]
    return {
        "check_id": "ZB-DATA-BOUNDARY-001",
        "status": status,                       # pass / fail / skip
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
