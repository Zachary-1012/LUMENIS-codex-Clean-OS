"""独立普通浏览器搜索发现层：不调用 RedNote 采集器，不消耗其检索次数。

多源搜索（对标 Safari/Chrome 地址栏 + 通用搜索）：
    - Bing HTML（既有，保持向后兼容）
    - 百度 HTML
    - DuckDuckGo HTML
统一结果结构；单引擎失败自动跳过，不影响其它引擎；纯标准库，无第三方依赖。
"""
import os
import re
import json
import html as _html
import urllib.parse
import urllib.request
import hashlib

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

# 支持的引擎（顺序即默认优先级）；对外统一 Canonical engine 名
ENGINES = ("bing", "baidu", "duckduckgo")
DEFAULT_ENGINES = ("bing", "baidu", "duckduckgo")


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    # 尝试 utf-8，失败回退 gb18030（百度偶发）
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def _clean(x):
    """去标签 + 反转义实体 + 压缩空白。"""
    txt = re.sub(r"<[^>]+>", " ", x or "")
    txt = _html.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


def _make_item(query, engine, url, title, content):
    if not url or not title:
        return None
    url = _html.unescape(url.strip())
    canon = url.split("#")[0]
    return {
        "source_id": hashlib.sha1(canon.split("?")[0].encode("utf-8", "ignore")).hexdigest(),
        "source_platform": "web",
        "source_type": "browser_search",
        "source_adapter": f"{engine}_html",
        "engine": engine,
        "query": query,
        "title": _clean(title)[:300],
        "content": _clean(content)[:1000],
        "url": url,
        "canonical_url": canon,
        "domain": urllib.parse.urlparse(url).netloc,
    }


# ─────────────────────────── 各引擎解析（独立容错）───────────────────────────

def _search_bing(query, limit):
    out = []
    htmltxt = _get("https://www.bing.com/search?q=" + urllib.parse.quote(query)
                   + "&count=" + str(min(limit, 50)))
    for m in re.finditer(r'<li class="b_algo"[\s\S]*?</li>', htmltxt, re.I):
        block = m.group(0)
        hm = re.search(r"<h2[^>]*>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", block, re.I | re.S)
        sm = re.search(r"<p[^>]*>(.*?)</p>", block, re.I | re.S)
        if not hm:
            continue
        item = _make_item(query, "bing", hm.group(1), hm.group(2), sm.group(1) if sm else "")
        if item:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _search_baidu(query, limit):
    out = []
    htmltxt = _get("https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
                   + "&rn=" + str(min(limit, 50)))
    # 百度结果块 class 多变，按 result 容器 + h3>a 宽松匹配
    for m in re.finditer(r"<h3[^>]*>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>[\s\S]*?</h3>",
                         htmltxt, re.I | re.S):
        url, title = m.group(1), m.group(2)
        # 摘要：向后取最近的内容容器（best-effort）
        tail = htmltxt[m.end():m.end() + 1200]
        sm = re.search(r'<span[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</span>', tail, re.I | re.S)
        item = _make_item(query, "baidu", url, title, sm.group(1) if sm else "")
        if item:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _decode_ddg_redirect(href):
    """DuckDuckGo 结果链接为 /l/?uddg=<encoded>，解出真实 URL；非跳转链接原样返回。"""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    qs = urllib.parse.parse_qs(parsed.query)
    if "uddg" in qs and qs["uddg"]:
        return urllib.parse.unquote(qs["uddg"][0])
    return href


def _search_duckduckgo(query, limit):
    out = []
    htmltxt = _get("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query))
    # 按 result__body/result 块切分，块内分别取标题链接与摘要，避免强依赖单一闭合结构
    blocks = re.split(r'<div[^>]*class="[^"]*result\b', htmltxt, flags=re.I)
    for block in blocks[1:]:
        hm = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                       block, re.I | re.S)
        if not hm:
            continue
        url = _decode_ddg_redirect(hm.group(1))
        sm = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.I | re.S)
        item = _make_item(query, "duckduckgo", url, hm.group(2), sm.group(1) if sm else "")
        if item:
            out.append(item)
        if len(out) >= limit:
            break
    return out


_ENGINE_FN = {
    "bing": _search_bing,
    "baidu": _search_baidu,
    "duckduckgo": _search_duckduckgo,
}


def search(query, limit=30, engines=None):
    """多源搜索。engines 为 None/单引擎字符串/引擎列表；默认全部引擎。

    向后兼容：search(query, limit) 仍可用，返回统一结构列表（新增 engine 字段）。
    任一引擎异常只记录错误、不中断其它引擎。
    """
    if engines is None:
        engines = DEFAULT_ENGINES
    if isinstance(engines, str):
        engines = [engines]
    engines = [e.lower() for e in engines if e and e.lower() in _ENGINE_FN]
    if not engines:
        return []
    per_engine = max(3, (limit // max(1, len(engines))) + 3)
    out, errors = [], {}
    for engine in engines:
        try:
            out.extend(_ENGINE_FN[engine](query, per_engine))
        except Exception as e:
            errors[engine] = str(e)[:200]
    # 同 URL 去重（保留先出现的引擎结果）
    seen, dedup = set(), []
    for item in out:
        key = item["canonical_url"].split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
        if len(dedup) >= limit:
            break
    if errors:
        for it in dedup:
            it.setdefault("engine_errors", errors)
    return dedup[:limit]


def discover(queries, limit=80, engines=None):
    """批量多源发现，跨 query/引擎按 canonical URL 去重。保持既有签名向后兼容。"""
    if isinstance(queries, str):
        queries = [queries]
    all_items = []
    n = max(1, len(queries))
    for q in queries:
        all_items.extend(search(q, limit=max(5, min(30, limit // n + 4)), engines=engines))
    seen, out = set(), []
    for x in all_items:
        if x["source_id"] in seen:
            continue
        seen.add(x["source_id"])
        out.append(x)
        if len(out) >= limit:
            break
    return out
