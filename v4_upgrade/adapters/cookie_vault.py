# -*- coding: utf-8 -*-
"""
统一 Cookie 登录态保险库（Cookie Vault）
=================================================
定位：为抖音 / Instagram / 微博 / B站等需要登录态的采集源，提供
“粘贴文本 → 标准 Cookie → 注入 CDP 浏览器上下文”的可复用桥接，与
持久 Profile 登录互为补充（Profile 优先、Cookie 注入兜底/换号）。

安全约定（硬性）：
  · Cookie 是敏感凭证，只落地到本地 data/cookies/<platform>.json，
    绝不硬编码进源码、不进 git（.gitignore 应排除 data/cookies/）；
  · 只做登录态桥接，不做任何账号风控绕过；
  · 过期 / 会话型 Cookie 如实标注，不伪造有效期。

支持两种来源：
  1. 标准 JSON（EditThisCookie / Cookie-Editor 导出的 [{name,value,domain,...}]）；
  2. 浏览器 Cookie 面板复制出的“粘连文本”——多条首尾相连、字段间无分隔，
     用 “字面域名锚点 + 各平台已知 Cookie 名 + 真实子域白名单” 可靠切分。
"""
import re
import json
import time
import logging
import calendar
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE = Path(__file__).resolve().parents[2]
COOKIE_DIR = _BASE / "data" / "cookies"

# 各平台主域名锚点
PLATFORM_DOMAINS = {
    "douyin": ["douyin.com", "bytedance.com"],
    "xiaohongshu": ["xiaohongshu.com", "xhscdn.com"],
    "instagram": ["instagram.com", "cdninstagram.com"],
    "weibo": ["weibo.com", "weibo.cn", "sina.com.cn"],
    "bilibili": ["bilibili.com"],
    "google": ["google.com"],
    "chatgpt": ["chatgpt.com", "openai.com"],
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

    步骤：字面定位每个“域名/”锚点 → 锚点前一段用“已知 Cookie 名”定位
    name 起点、其后到域名为 value → 锚点后一段解析过期时间 / ✓ / SameSite。
    无法可靠识别的条目跳过（宁缺毋滥，不产出错误 Cookie）。
    """
    domains = PLATFORM_DOMAINS.get(platform)
    names = sorted(KNOWN_NAMES.get(platform, []), key=len, reverse=True)
    if not domains or not names:
        logger.warning("平台 %s 缺少域名/已知名表，无法解析粘连文本", platform)
        return []

    dom_alt = "|".join(d.replace(".", r"\.") for d in domains)
    # 先字面定位主域名/，再向左回看“紧邻的单个点段”判断是否为白名单真实子域，
    # 避免贪婪正则把 value 尾部字母吞进子域。
    main_anchor = re.compile(r"(" + dom_alt + r")/", re.IGNORECASE)
    matches = list(main_anchor.finditer(text))
    cookies = []
    for i, m in enumerate(matches):
        main_start = m.start(1)
        seg, t = "", main_start
        if main_start - 1 >= 0 and text[main_start - 1] == ".":
            k = main_start - 1  # 指向主域前的点
            t = k
            while t - 1 >= 0 and re.match(r"[A-Za-z0-9\-]", text[t - 1]):
                t -= 1
            seg = text[t:k]
        # 整段是白名单子域，或 value 紧贴白名单子域（如 9831mssdk）——以后缀识别
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

        # 在 head 中取“最先出现的已知名”作为本条 name（上一条 tail 不含已知名）
        hit = None
        for n in names:
            p = head.find(n)
            if p >= 0 and (hit is None or p < hit[0]):
                hit = (p, n)
        if not hit:
            continue
        pos, name = hit
        value = head[pos + len(name):].strip(".")  # 去掉主域前残留分隔点
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
# 存储 / 读取
# ============================================================
def _path(platform):
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    return COOKIE_DIR / f"{platform}.json"


def save_cookies(platform: str, cookies: list):
    """标准 cookie 列表落盘（本地、受保护目录），返回写入数量。"""
    p = _path(platform)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    logger.info("Cookie 已保存 %s（%d 条）", p, len(cookies))
    return len(cookies)


def load_cookies(platform: str):
    """读取标准 cookie；不存在返回空列表。"""
    p = _path(platform)
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
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
        if exp and exp > time.time() - 86400 * 365:  # 有效时间才带 expires
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
