# -*- coding: utf-8 -*-
"""
统一 Cookie 登录态保险库（Cookie Vault）
=================================================
定位：为抖音 / Instagram / 微博 / B站等需要登录态的采集源，提供
"粘贴文本 → 标准 Cookie → 注入 CDP 浏览器上下文"的可复用桥接，与
持久 Profile 登录互为补充（Profile 优先、Cookie 注入兜底/换号）。

安全约定（硬性）：
  · Cookie 是敏感凭证，只落地到本地 data/cookies/<platform>.json 或
    data/<platform>_cookies.json，绝不硬编码进源码、不进 git；
  · 只做登录态桥接，不做任何账号风控绕过；
  · 过期 / 会话型 Cookie 如实标注，不伪造有效期。
  · 所有适配器统一经本模块加载 cookie，不得自行拼路径读文件。

支持两种来源：
  1. 标准 JSON（EditThisCookie / Cookie-Editor 导出的 [{name,value,domain,...}]）；
  2. 浏览器 Cookie 面板复制出的"粘连文本"——多条首尾相连、字段间无分隔，
     用 "字面域名锚点 + 各平台已知 Cookie 名 + 真实子域白名单" 可靠切分。
"""
import re
import json
import time
import logging
import calendar
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE = Path(__file__).resolve().parents[2]


def _resolve_runtime_data_dir(root: str | None = None, environ=None) -> Path:
    """Resolve the credential/data root used by the running instance.

    Production credentials live beside the canonical runtime database, outside
    the source checkout.  ``ZBC_DATA_DIR`` is authoritative; otherwise the
    parent of ``ZBC_DB_PATH`` is used.  The repository ``data`` directory is
    retained only as the development/test fallback.
    """
    env = os.environ if environ is None else environ
    base = Path(root or _BASE).resolve()
    configured = str(env.get("ZBC_DATA_DIR") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    db_path = str(env.get("ZBC_DB_PATH") or "").strip()
    if db_path:
        if db_path.startswith("sqlite:///"):
            db_path = db_path[len("sqlite:///"):]
        elif db_path.startswith("file:"):
            db_path = db_path[len("file:"):].split("?", 1)[0]
        parent = Path(db_path).expanduser().resolve().parent
        if str(parent):
            return parent
    return (base / "data").resolve()


DATA_DIR = _resolve_runtime_data_dir()
COOKIE_DIR = DATA_DIR / "cookies"

# 各平台主域名锚点
PLATFORM_DOMAINS = {
    "douyin": ["douyin.com", "bytedance.com"],
    "xiaohongshu": ["xiaohongshu.com", "xhscdn.com"],
    "instagram": ["instagram.com", "cdninstagram.com"],
    "weibo": ["weibo.com", "weibo.cn", "sina.com.cn"],
    "bilibili": ["bilibili.com"],
    "zhihu": ["zhihu.com"],
    "x": ["x.com", "twitter.com"],
    "jiguang": ["jgdt.com", "jiguang.cn"],
    "google": ["google.com"],
    "chatgpt": ["chatgpt.com", "openai.com"],
}

# 平台 → 候选 cookie 文件路径（按优先级查找，第一个存在即使用）
PLATFORM_COOKIE_PATHS = {
    "douyin":      [COOKIE_DIR / "douyin.json"],
    "xiaohongshu": [DATA_DIR / "xhs_cookies.json", COOKIE_DIR / "xiaohongshu.json"],
    "xhs":         [DATA_DIR / "xhs_cookies.json", COOKIE_DIR / "xiaohongshu.json"],
    "instagram":   [COOKIE_DIR / "instagram.json"],
    "weibo":       [DATA_DIR / "weibo_cookies.json", COOKIE_DIR / "weibo.json"],
    "bilibili":    [DATA_DIR / "bilibili_cookies.json", COOKIE_DIR / "bilibili.json"],
    "zhihu":       [DATA_DIR / "zhihu_cookies.json", COOKIE_DIR / "zhihu.json"],
    "x":           [COOKIE_DIR / "x.json"],
    "jiguang":     [COOKIE_DIR / "jiguang.json"],
}


def _current_data_dir() -> Path:
    """Read the current process path contract without exposing credentials."""
    return _resolve_runtime_data_dir()


def _current_cookie_paths(platform: str) -> list[Path] | None:
    """Build platform paths from the current runtime root.

    The exported ``PLATFORM_COOKIE_PATHS`` remains a compatibility snapshot for
    callers/tests.  Runtime reads use this function so a supervised process
    that loads environment configuration after module import still follows the
    canonical protected data directory.
    """
    data_dir = _current_data_dir()
    cookie_dir = data_dir / "cookies"
    paths = {
        "douyin": [cookie_dir / "douyin.json"],
        "xiaohongshu": [data_dir / "xhs_cookies.json", cookie_dir / "xiaohongshu.json"],
        "xhs": [data_dir / "xhs_cookies.json", cookie_dir / "xiaohongshu.json"],
        "instagram": [cookie_dir / "instagram.json"],
        "weibo": [data_dir / "weibo_cookies.json", cookie_dir / "weibo.json"],
        "bilibili": [data_dir / "bilibili_cookies.json", cookie_dir / "bilibili.json"],
        "zhihu": [data_dir / "zhihu_cookies.json", cookie_dir / "zhihu.json"],
        "x": [cookie_dir / "x.json"],
        "jiguang": [cookie_dir / "jiguang.json"],
    }
    return paths.get(platform)

# 各平台判定登录态有效的关键 cookie 名（有任一即视为 cookie 已注入）
PLATFORM_AUTH_COOKIES = {
    "douyin":      ["sessionid", "sessionid_ss", "sid_tt", "uid_tt"],
    "xiaohongshu": ["web_session", "a1", "webId", "gid"],
    "xhs":         ["web_session", "a1", "webId", "gid"],
    "instagram":   ["sessionid", "ds_user_id", "csrftoken"],
    "weibo":       ["SUB", "SCF", "WBPSESS", "PC_TOKEN"],
    "bilibili":    ["SESSDATA", "bili_jct", "DedeUserID"],
    "zhihu":       ["z_c0", "d_c0", "_zap"],
    "x":           ["auth_token", "ct0", "guest_id"],
    "jiguang":     ["customer-sso-sid", "ares.beaker.session.id"],
}

# 真实子域白名单：只有这些前缀才视为域名子域，避免把 value 尾段误当子域吞掉
SUBDOMAIN_WHITELIST = {
    "www", "m", "sso", "passport", "mssdk", "s", "lf", "apimobile",
    "i", "help", "open", "cdn", "static",
}
# 已知 Cookie 名（用于在粘连文本里定位 name/value 分界；未知名不瞎切，直接跳过）
KNOWN_NAMES = {
    "douyin": [
        "sessionid_ss", "sessionid", "sid_guard", "sid_tt", "ssid_ucp_v1",
        "sid_ucp_v1", "uid_tt_ss", "uid_tt", "ttwid", "tt_scid", "ttcid",
        "sso_auth_status", "sso_uid_tt", "strategyABtestKey", "stream_player_status_params",
        "stream_recommend_feed_params", "sdk_source_info", "SEARCH_RESULT_LIST_TYPE",
        "SelfTabRedDotControl", "session_tlb_tag", "publish_badge_show_info",
        "totalRecommendGuideTagCount", "volume_info", "UIFID_TEMP", "UIFID",
        "is_ttwebid", "odin_tt", "passport_csrf_token", "msToken",
        "bd_ticket_guard_client_data", "store-region", "theme-tip-show", "n_mh",
        "bd_ticket_guard_client_web_domain",
    ],
    "instagram": [
        "sessionid", "ds_user_id", "csrftoken", "ig_did", "mid", "rur", "datr",
        "ig_nrcb", "shbid", "shbts", "dpr", "wd",
    ],
}

_SAMESITE_MAP = {"medium": "Lax", "lax": "Lax", "strict": "Strict",
                 "none": "None", "": "Lax"}


# ============================================================
# 解析：标准 JSON / 粘连文本
# ============================================================
def _iso_to_epoch(value) -> float:
    """ISO8601 / Unix 秒 → Unix 秒；Session/无法解析返回 -1（会话 Cookie）。"""
    if value is None:
        return -1
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s.lower() == "session":
        return -1
    if s.isdigit():
        return float(s)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return calendar.timegm(dt.utctimetuple())
    except Exception:
        return -1


def parse_pasted(text: str, platform: str):
    """把浏览器 Cookie 面板的粘连文本解析为标准 Cookie 列表。

    步骤：字面定位每个"域名/"锚点 → 锚点前一段用"已知 Cookie 名"定位
    name 起点、其后到域名为 value → 锚点后一段解析过期时间 / ✓ / SameSite。
    无法可靠识别的条目跳过（宁缺毋滥，不产出错误 Cookie）。
    """
    domains = PLATFORM_DOMAINS.get(platform)
    names = sorted(KNOWN_NAMES.get(platform, []), key=len, reverse=True)
    if not domains or not names:
        logger.warning("平台 %s 缺少域名/已知名表，无法解析粘连文本", platform)
        return []

    dom_alt = "|".join(d.replace(".", r"\.") for d in domains)
    main_anchor = re.compile(r"(" + dom_alt + r")/", re.IGNORECASE)
    matches = list(main_anchor.finditer(text))
    cookies = []
    for i, m in enumerate(matches):
        main_start = m.start(1)
        seg, t = "", main_start
        if main_start - 1 >= 0 and text[main_start - 1] == ".":
            k = main_start - 1
            t = k
            while t - 1 >= 0 and re.match(r"[A-Za-z0-9\-]", text[t - 1]):
                t -= 1
            seg = text[t:k]
        segl = seg.lower()
        sub_t, sub_name = None, ""
        if segl in SUBDOMAIN_WHITELIST:
            sub_t, sub_name = t, seg
        else:
            for w in SUBDOMAIN_WHITELIST:
                if segl.endswith(w) and len(segl) > len(w):
                    sub_t = t + (len(seg) - len(w))
                    sub_name = seg[len(seg) - len(w):]
                    break
        if sub_t is not None:
            dom_start = sub_t
            dom_full = f"{sub_name}.{m.group(1)}"
        else:
            dom_start = main_start
            dom_full = m.group(1)
        prev_end = matches[i - 1].end() if i > 0 else 0
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        head = text[prev_end:dom_start]
        tail = text[m.end():next_start]

        hit = None
        for n in names:
            p = head.find(n)
            if p >= 0 and (hit is None or p < hit[0]):
                hit = (p, n)
        if not hit:
            continue
        pos, name = hit
        value = head[pos + len(name):].strip(".")
        if not value:
            continue

        exp_m = re.search(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z|Session", tail)
        expires = exp_m.group(0) if exp_m else "Session"
        checks = tail.count("✓")
        ss_m = re.search(r"(Medium|Lax|Strict|None)\s*$", tail)
        same_site = _SAMESITE_MAP.get((ss_m.group(1) if ss_m else "").lower(), "Lax")

        cookies.append({
            "name": name,
            "value": value,
            "domain": ("." + dom_full) if not dom_full.startswith(".") else dom_full,
            "path": "/",
            "expires": expires,
            "httpOnly": checks >= 1,
            "secure": "✓✓" in tail or checks >= 2,
            "sameSite": same_site,
        })
    return cookies


# ============================================================
# 存储 / 读取（统一入口：所有平台经 PLATFORM_COOKIE_PATHS 查找）
# ============================================================
def _resolve_path(platform: str) -> Path | None:
    """按优先级查找平台 cookie 文件，返回第一个存在的路径；都不存在返回 None。"""
    paths = _current_cookie_paths(platform)
    if not paths:
        # 未配置平台，回退到 data/cookies/<platform>.json
        p = _current_data_dir() / "cookies" / f"{platform}.json"
        return p if p.exists() else None
    for p in paths:
        if p.exists():
            return p
    return None


def _path(platform):
    """默认写入路径（data/cookies/<platform>.json）。"""
    cookie_dir = _current_data_dir() / "cookies"
    cookie_dir.mkdir(parents=True, exist_ok=True)
    return cookie_dir / f"{platform}.json"


def save_cookies(platform: str, cookies: list):
    """标准 cookie 列表落盘（本地、受保护目录），返回写入数量。"""
    p = _path(platform)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    logger.info("Cookie 已保存 %s（%d 条）", p, len(cookies))
    return len(cookies)


def load_cookies(platform: str):
    """读取标准 cookie（按 PLATFORM_COOKIE_PATHS 多路径查找）；不存在返回空列表。

    支持两种文件结构：
      - 标准列表 [{name, value, domain, ...}]
      - 包装 dict {"cookies": [...]} 或 {"<name>": "<value>", ...}
    """
    p = _resolve_path(platform)
    if not p:
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "cookies" in data and isinstance(data["cookies"], list):
                return data["cookies"]
            # dict 形式 {name: value} → 转标准列表
            return [{"name": k, "value": str(v), "domain": "", "path": "/"}
                    for k, v in data.items() if k != "cookies"]
        return []
    except Exception as e:
        logger.warning("读取 Cookie 失败 %s: %s", p, e)
        return []


def import_pasted(platform: str, text: str):
    """解析粘连文本并落盘的便捷方法，返回 (数量, 列表)。"""
    cookies = parse_pasted(text, platform)
    if cookies:
        save_cookies(platform, cookies)
    return len(cookies), cookies


# ============================================================
# 辅助：cookie 字符串 / requests dict / 状态检查
# ============================================================
def to_cookie_string(platform: str) -> str:
    """加载平台 cookie 并转为 "name1=value1; name2=value2" 字符串（用于 HTTP Header）。

    不打印 cookie 内容，只返回字符串；无 cookie 返回空串。
    """
    cookies = load_cookies(platform)
    if not cookies:
        return ""
    parts = []
    for c in cookies:
        name = c.get("name", "")
        value = c.get("value", "")
        if name and value:
            parts.append(f"{name}={value}")
    return "; ".join(parts)


def to_requests_cookies(platform: str) -> dict:
    """加载平台 cookie 并转为 {name: value} dict（用于 requests cookies= 参数）。"""
    cookies = load_cookies(platform)
    if not cookies:
        return {}
    return {c["name"]: str(c.get("value", "")) for c in cookies if c.get("name")}


def check_cookie_status(platform: str) -> dict:
    """检查平台 cookie 文件状态（不打印 cookie 值，只返回元信息）。

    返回:
      {
        "platform": str,
        "cookie_file": str | None,       # 找到的 cookie 文件路径
        "cookie_count": int,              # cookie 条数
        "has_auth_cookie": bool,          # 是否包含关键认证 cookie
        "auth_cookies_found": list[str],  # 找到的关键认证 cookie 名
        "status": "ACTIVE" | "MISSING" | "NO_AUTH",  # 文件级状态（非连通状态）
      }
    """
    p = _resolve_path(platform)
    if not p:
        return {
            "platform": platform,
            "cookie_file": None,
            "cookie_count": 0,
            "has_auth_cookie": False,
            "auth_cookies_found": [],
            "status": "MISSING",
        }
    cookies = load_cookies(platform)
    auth_keys = PLATFORM_AUTH_COOKIES.get(platform, [])
    found = [c["name"] for c in cookies if c.get("name") in auth_keys]
    return {
        "platform": platform,
        "cookie_file": str(p),
        "cookie_count": len(cookies),
        "has_auth_cookie": bool(found),
        "auth_cookies_found": found,
        "status": "ACTIVE" if found else "NO_AUTH",
    }


# ============================================================
# 注入 CDP / Playwright 浏览器上下文
# ============================================================
def to_playwright_cookies(cookies: list):
    """标准 cookie 转 Playwright add_cookies 所需结构。"""
    out = []
    for c in cookies:
        item = {
            "name": c["name"],
            "value": str(c["value"]),
            "domain": c.get("domain") or "",
            "path": c.get("path", "/"),
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", False)),
        }
        item["sameSite"] = _SAMESITE_MAP.get(str(c.get("sameSite") or "Lax").lower(), "Lax")
        exp = _iso_to_epoch(c.get("expires"))
        if exp and exp > time.time() - 86400 * 365:
            item["expires"] = exp
        out.append(item)
    return out


def inject_into_context(context, platform: str, url: str = None):
    """把某平台已保存的 Cookie 注入 Playwright 浏览器上下文，返回注入条数。

    在导航到目标站点之前调用；domain 型 cookie 由上下文按域自动携带。
    批量失败则退化为 url 方式逐条注入；整体不抛异常，返回 0 由调用方走 AUTH。
    """
    cookies = load_cookies(platform)
    if not cookies:
        return 0
    pw_cookies = to_playwright_cookies(cookies)
    try:
        context.add_cookies(pw_cookies)
        logger.info("已向上下文注入 %s Cookie %d 条", platform, len(pw_cookies))
        return len(pw_cookies)
    except Exception as e:
        logger.warning("批量注入 Cookie 失败(%s)，改逐条注入", e)
        fallback = url or f"https://www.{PLATFORM_DOMAINS.get(platform, [platform])[0]}"
        ok = 0
        for c in pw_cookies:
            try:
                c2 = {k: v for k, v in c.items() if k != "domain"}
                c2["url"] = fallback
                context.add_cookies([c2])
                ok += 1
            except Exception:
                continue
        return ok
