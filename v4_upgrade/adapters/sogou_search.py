# -*- coding: utf-8 -*-
"""
搜狗全网搜索采集适配器
-------------------------------------------------
定位：轻量、免登录、直连可用的“全网公开网页 / 新闻”补充信源。
  · 新闻频道 news.sogou.com/news：媒体报道，带来源与发布时间，舆情主用；
  · 网页频道 www.sogou.com/web：全网公开页面，作为补充；
  · 支持 site: 语法（调用方在 keyword 内写入即可），可定向覆盖搜狐等
    纯 requests 抓不动的站点（例如 "keyword site:sohu.com"）。

工程约定（对齐系统六态，不制造“0 条假成功”）：
  · 正常返回但确无结果 -> success=True, notes=[]（由注册中心判 EMPTY）；
  · 命中搜狗反爬验证页 / 网络异常 -> success=False（判 FAIL/BLOCKED 语义），
    绝不用空列表冒充采集成功；
  · 搜索结果链接为搜狗 /link?url= 中转，本模块负责并发还原真实 URL，
    还原失败时保留中转链并在 raw_data 标记，不丢弃该条。

发布时间与采集时间严格分离：这里解析出的是文章“发布时间”(publish_date)，
采集时间由入库层统一写 captured_at，本模块不臆造。
"""
import re
import html
import time
import random
import datetime
import urllib.parse
import concurrent.futures
from .base import BaseAdapter, AdapterResult


# 命中即视为搜狗反爬/人机校验，需按 BLOCKED 处理而非“无结果”
_BLOCK_PATTERNS = [
    "antispider", "anti.min.css", "verify.css", "imgcode",
    "请输入验证码", "访问过于频繁", "用户您好", "网络不给力",
    "验证码", "unusual traffic", "请您输入验证码",
]
# 发布时间：2026年6月7日 / 2025-03-2 / 2025/03/02
_DATE_CN = re.compile(r"(20\d{2})\s*[年/\-\.]\s*(\d{1,2})\s*[月/\-\.]\s*(\d{1,2})")
# 用于从来源文本里整体抹掉日期（含年/月/日/号汉字与分隔符）
_DATE_FULL = re.compile(r"20\d{2}\s*[年/\-\.]\s*\d{1,2}\s*[月/\-\.]\s*\d{1,2}\s*[日号]?")
# 相对时间：刚刚 / N分钟前 / N小时前 / 昨天 / 前天 / N天前
_REL_NOW = re.compile(r"刚刚|刚|\d+\s*分钟前")
_REL_HOUR = re.compile(r"(\d+)\s*小时前")
_REL_DAY = re.compile(r"(\d+)\s*天前")
# URL 路径里的年份（用于与标注日期交叉校验）
_URL_YEAR = re.compile(r"/(20\d{2})[/\-_.]")
# JS / meta 跳转里的真实地址
_JS_LOCATION = re.compile(
    r"(?:location\.replace|location\.href|URL=|url=)\s*[\"']?(https?://[^\"'\)\s>]+)",
    re.IGNORECASE)


class SogouSearchAdapter(BaseAdapter):
    """搜狗搜索（新闻 + 网页）适配器"""

    platform_name = "sogou_search"
    platform_display = "搜狗搜索"

    # 频道定义：(内部名, URL模板, Referer)
    _CHANNELS = (
        ("news", "https://news.sogou.com/news?mode=1&query={q}", "https://news.sogou.com/"),
        ("web", "https://www.sogou.com/web?query={q}", "https://www.sogou.com/"),
    )

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """搜索入口：默认合并“新闻 + 网页”两个频道，按真实 URL 去重。"""
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            import requests
        except ImportError:
            return AdapterResult(success=False, error="缺少 requests 依赖")

        session = requests.Session()
        collected, blocked = [], []
        for ci, (channel, tmpl, referer) in enumerate(self._CHANNELS):
            if ci > 0:
                time.sleep(random.uniform(1.6, 3.0))  # 频道间拟人停顿，避免连撞风控
            page, err = self._fetch_channel(session, tmpl.format(q=urllib.parse.quote(keyword)), referer)
            if err:
                blocked.append(f"{channel}:{err}")
                continue
            collected.extend(self._parse_channel(page, channel))

        # 两个频道都被拦 -> 明确失败，不返回空成功
        if not collected and blocked:
            return AdapterResult(success=False, error="；".join(blocked))

        # 还原 /link 中转真实地址（并发，温和限流）
        self._resolve_links(session, collected, workers=6)

        # 按真实 URL 去重（新闻优先保留），再截断
        deduped, seen = [], set()
        for note in collected:
            key = note.url or note.title
            if key in seen:
                continue
            seen.add(key)
            deduped.append(note)
        return AdapterResult(
            success=True,
            notes=deduped[:max_results],
            raw_count=len(deduped),
        )

    # ---------- 解析 ----------
    def _headers(self, referer: str) -> dict:
        """构造贴近真实 Edge 的请求头。"""
        return {
            "User-Agent": self.config["user_agent"] + " (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Referer": referer,
        }

    def _fetch_channel(self, session, url: str, referer: str):
        """抓取单个频道结果页；命中风控时退避后最多重试一次。

        返回 (html, error)：成功 error 为 None；被拦/网络异常返回 (None, 原因)。
        不做多次硬撞，符合“被拦即退避、不硬刚风控”的原则。
        """
        for attempt in range(2):
            try:
                resp = session.get(url, headers=self._headers(referer),
                                   timeout=self.config["request_timeout"])
                resp.encoding = "utf-8"
                text = resp.text
            except Exception as e:
                return None, f"网络异常 {e}"
            if not self._is_blocked(text):
                return text, None
            if attempt == 0:
                time.sleep(random.uniform(4.0, 6.0))  # 首次被拦，冷却后仅再试一次
                continue
            return None, "命中搜狗反爬验证页(已退避重试仍受限)"
        return None, "命中搜狗反爬验证页"

    @staticmethod
    def _is_blocked(text: str) -> bool:
        """识别搜狗反爬/人机校验页（命中即按 BLOCKED 处理，不当作 0 条）。"""
        if not text or len(text) < 800:
            return True  # 异常空壳页同样视为被拦，避免“假成功 0 条”
        low = text.lower()
        return any(p.lower() in low for p in _BLOCK_PATTERNS)

    def _parse_channel(self, page_html: str, channel: str) -> list:
        """解析单个频道结果页为标准化笔记列表。"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []
        soup = BeautifulSoup(page_html, "html.parser")
        notes = []
        for item in soup.select("div.vrwrap"):
            anchor = self._title_anchor(item)
            if anchor is None:
                continue  # 跳过“相关搜索/广告”等无标题块
            title = html.unescape(anchor.get_text(" ", strip=True))
            href = anchor.get("href", "").strip()
            if not title or not href:
                continue
            if href.startswith("/"):
                href = "https://www.sogou.com" + href
            snippet = self._pick_text(item, [".star-wiki", ".space-txt", ".text-layout", ".fz-mid"])
            source, pub, date_source, conflict = self._source_and_date(item, channel, href)
            notes.append(self._make_note(
                title=re.sub(r"\s+", " ", title),
                content=re.sub(r"\s+", " ", snippet or ""),
                url=href,
                author=source or "搜狗搜索",
                publish_date=pub,
                raw_data={
                    "channel": channel,
                    "link_redirect": href.startswith("https://www.sogou.com/link"),
                    "date_source": date_source,       # 日期取自哪里（可追溯）
                    "date_conflict": conflict,         # URL 路径年份与标注日期严重不符
                },
            ))
        return notes

    @staticmethod
    def _title_anchor(item):
        """取得条目标题链接（h3 优先，回退 .vrTitle）。"""
        h3 = item.find("h3")
        if h3 and h3.find("a"):
            return h3.find("a")
        return item.select_one(".vrTitle a")

    @staticmethod
    def _pick_text(item, selectors):
        """按候选选择器取首个非空纯文本摘要。"""
        for sel in selectors:
            el = item.select_one(sel)
            if el:
                txt = el.get_text(" ", strip=True)
                if txt:
                    return html.unescape(txt)
        return ""

    def _source_and_date(self, item, channel: str, href: str):
        """提取 (来源, 发布日期, 日期来源层级, URL年份是否冲突)。

        日期可信度分级（宁缺毋滥，绝不从正文摘要抓年份）：
          · 新闻频道：以 .news-from 来源行为准（.fz-mid 仅在“短且像来源行”时
            采用，长 .fz-mid 是摘要）；支持绝对日期与“N小时前/昨天”相对时间归一；
          · 网页频道：时间只取 .cite-date；.fz-mid 是面包屑/地址/摘要，不作来源；
            来源名改由 URL 域名主名给出；
          · 摘要（star-wiki/text-layout）里出现的“2011年”等是正文内容，永不作发布日期。
        """
        if channel == "news":
            line = ""
            nf = item.select_one(".news-from")
            if nf:
                line = nf.get_text(" ", strip=True)
            if not line:  # 仅当 fz-mid 很短时才把它当来源行，否则是摘要
                fm = item.select_one(".fz-mid")
                cand = fm.get_text(" ", strip=True) if fm else ""
                if cand and len(cand) <= 20:
                    line = cand
            pub, date_source = self._extract_date(line)
            source = self._clean_source(line)
        else:
            cd = item.select_one(".cite-date")
            t = cd.get_text(" ", strip=True) if cd else ""
            pub, date_source = self._extract_date(t)
            source = ""  # 网页频道来源行不可靠，统一走域名

        if not source:
            source = self._domain_source(href) or ("搜狗新闻" if channel == "news" else "搜狗网页")
        conflict = self._url_date_conflict(href, pub)
        return source, pub, (date_source or ""), conflict

    # ---------- 日期 / 来源 清洗工具 ----------
    def _extract_date(self, text: str):
        """从来源行/时间行提取发布日期：绝对日期优先，其次相对时间归一。返回(date,层级)。"""
        if not text:
            return "", ""
        m = _DATE_CN.search(text)
        if m:
            y, mo, d = (int(x) for x in m.groups())
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}", "absolute"
        today = datetime.datetime.now()
        if _REL_NOW.search(text):
            return today.strftime("%Y-%m-%d"), "relative"
        mh = _REL_HOUR.search(text)
        if mh or "小时前" in text:
            n = int(mh.group(1)) if mh else 1
            return (today - datetime.timedelta(hours=n)).strftime("%Y-%m-%d"), "relative"
        if "昨天" in text:
            return (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d"), "relative"
        if "前天" in text:
            return (today - datetime.timedelta(days=2)).strftime("%Y-%m-%d"), "relative"
        md = _REL_DAY.search(text)
        if md:
            return (today - datetime.timedelta(days=int(md.group(1)))).strftime("%Y-%m-%d"), "relative"
        return "", ""

    @staticmethod
    def _clean_source(line: str) -> str:
        """从来源行抹掉绝对/相对日期与重复片段，得到干净媒体名。"""
        if not line:
            return ""
        s = _DATE_FULL.sub("", line)
        s = re.sub(r"\d+\s*(分钟|小时|天)?前|刚刚?|昨天|前天|[年月日]", " ", s)
        seen, toks = set(), []
        for tok in re.split(r"[\s·|\-]+", s):
            tok = tok.strip(" :：·|-")
            if tok and tok not in seen and not tok.isdigit():
                seen.add(tok)
                toks.append(tok)
        s = "".join(toks) if all(len(t) <= 4 for t in toks) else " ".join(toks)
        if len(s) > 16 or re.search(r"地址|：|:|，|。|综上", s):
            return ""
        return s.strip()

    @staticmethod
    def _domain_source(href: str) -> str:
        """从 URL 取注册主名（去 www/m/new 等前缀与后缀），作来源兜底。"""
        try:
            host = urllib.parse.urlparse(href).netloc.lower()
        except Exception:
            return ""
        if not host:
            return ""
        parts = host.split(".")
        drop_pre = {"www", "m", "new", "news", "mobile", "wap", "apimobile"}
        while parts and parts[0] in drop_pre:
            parts.pop(0)
        return parts[0] if parts else ""

    @staticmethod
    def _url_date_conflict(href: str, pub: str) -> bool:
        """URL 路径年份与发布日期年份相差超过 1 年时标记冲突（只标注，不篡改）。"""
        if not pub:
            return False
        mu = _URL_YEAR.search(href or "")
        if not mu:
            return False
        try:
            return abs(int(mu.group(1)) - int(pub[:4])) > 1
        except ValueError:
            return False


    # ---------- 中链还原 ----------
    def _resolve_links(self, session, notes, workers: int = 6):
        """并发把搜狗 /link 中转地址还原为真实 URL；失败保留原中转链。"""
        pending = {i: n.url for i, n in enumerate(notes)
                   if n.url.startswith("https://www.sogou.com/link")}
        if not pending:
            return
        headers = self._headers("https://www.sogou.com/")

        def resolve(url):
            try:
                r = session.get(url, headers=headers, timeout=8, allow_redirects=True)
                m = _JS_LOCATION.search(r.text[:4000])
                if m:
                    return html.unescape(m.group(1))
                if r.url and "sogou.com/link" not in r.url:
                    return r.url  # 极少数走 HTTP 302
            except Exception:
                return None
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(resolve, u): i for i, u in pending.items()}
            for fut in concurrent.futures.as_completed(futures):
                i = futures[fut]
                real = fut.result()
                if real:
                    notes[i].url = real
                    notes[i].raw_data["link_redirect"] = False
                    if notes[i].author in ("搜狗搜索", "搜狗新闻", "搜狗网页", "sogou"):
                        real_src = self._domain_source(real)
                        if real_src and real_src != "sogou":
                            notes[i].author = real_src
                # 还原失败：保留原中转链，raw_data 标记保持 True
