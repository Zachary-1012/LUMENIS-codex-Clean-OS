# -*- coding: utf-8 -*-
"""
知乎（Zhihu）内容采集适配器
----------------------------
定位：服务于 Z-Brand Core 多平台内容采集（ZBMP层，全品牌使用）。
调用知乎搜索 API v4（匿名/带 cookie 均可），薄封装为 v4 BaseAdapter 契约，
接入熔断器/限流/重试/降级体系。

数据主路径：知乎搜索 API
  https://www.zhihu.com/api/v4/search_v3?t=general&q={keyword}&limit={n}
返回 data[].object（type=answer/article/question 等）。

状态映射：
  - 有结果       → SUCCESS
  - 正常空       → EMPTY (success=True, notes=[])
  - API error    → COLLECT_ERROR
  - 异常         → COLLECT_ERROR

时间口径：created_time/updated_time 为 Unix 秒级时间戳，转 ISO 8601；
采集时间由入库层写 captured_at，二者严格分离。

去重：浏览器采集模式按 URL + 标题/作者双键去重，避免同问题多回答重复标题。

只读红线：不点赞、不评论、不关注、不私信、不执行任何账号写操作。
"""
import logging
import re
from datetime import datetime, timezone

import requests

from .base import AdapterResult, BaseAdapter
from .cookie_vault import to_cookie_string

logger = logging.getLogger(__name__)


class ZhihuAdapter(BaseAdapter):
    """知乎搜索适配器（搜索 API v4，只读采集）"""

    platform_name = "zhihu"
    platform_display = "知乎"

    SEARCH_URL = "https://www.zhihu.com/api/v4/search_v3"

    _DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, cookie_string: str = "", **kwargs):
        super().__init__(**kwargs)
        self._cookie_string = cookie_string
        if not self._cookie_string:
            self._cookie_string = self._auto_load_cookie()

    @staticmethod
    def _auto_load_cookie() -> str:
        """经 cookie_vault 加载知乎 cookie 字符串；失败返回空串。"""
        return to_cookie_string("zhihu")

    def _get_headers(self) -> dict:
        headers = {
            "User-Agent": self._DEFAULT_UA,
            "Referer": "https://www.zhihu.com/",
            "Accept": "application/json, text/plain, */*",
        }
        if self._cookie_string:
            headers["Cookie"] = self._cookie_string
        return headers

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        # Use the existing API only when no registered browser worker exists.
        # A registered worker failure, permission denial or challenge is final.
        browser_result = self._search_browser(keyword, max_results)
        if browser_result is not None:
            return browser_result
        return self._search_api(keyword, max_results)

    def _search_browser(self, keyword: str, max_results: int) -> AdapterResult | None:
        """Use only Zhihu's registered background worker; otherwise retain API fallback."""
        hb = None
        page = None
        endpoint = None
        try:
            from urllib.parse import quote

            from lumenis.system.collector.adapters.config import (
                get_platform_capabilities,
            )

            from .cookie_vault import inject_into_context
            from .human_browser import (
                HumanBrowser,
                PageState,
                configured_readonly_worker_url,
            )

            capabilities = get_platform_capabilities("zhihu")
            if not isinstance(capabilities.get("readonly_worker"), dict):
                logger.info("知乎没有注册的受控浏览器，使用既有搜索 API")
                return None
            endpoint = configured_readonly_worker_url("zhihu", mode="BACKGROUND")

            hb = HumanBrowser(cdp_url=endpoint, auto_ensure=False,
                              launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "zhihu")
            page = hb.new_page()
            url = f"https://www.zhihu.com/search?type=content&q={quote(keyword.strip())}"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(4.0, 4.0)

            state = hb.detect_state(page)
            if state in (PageState.BLOCKED, PageState.CAPTCHA,
                         PageState.AUTH_FAILED, PageState.NETWORK_ERROR):
                return AdapterResult(
                    success=False, error=f"知乎页面状态={state}")

            # 解析搜索结果卡片（URL去重 + 标题作者双键去重）
            cards = page.query_selector_all(".SearchResult-Card, .List-item, .Card")
            notes = []
            seen_urls = set()
            seen_title_authors = set()
            for card in cards:
                if len(notes) >= max_results:
                    break
                try:
                    note = self._parse_zhihu_card(card)
                    if not note:
                        continue
                    # URL去重：同一个回答/文章只保留一次
                    if note.url and note.url in seen_urls:
                        continue
                    # 标题+作者去重：同问题同作者的重复回答
                    ta_key = (note.title[:30], note.author)
                    if ta_key in seen_title_authors:
                        continue
                    if note.url:
                        seen_urls.add(note.url)
                    seen_title_authors.add(ta_key)
                    notes.append(note)
                except Exception:
                    continue

            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            # 浏览器无结果也返回成功空（不fallback，避免API签名错误）
            return AdapterResult(success=True, notes=[], raw_count=0)
        except Exception as e:
            logger.warning("知乎注册浏览器采集失败，不绕过该失败转用API: %s", e)
            return AdapterResult(
                success=False, error=f"知乎受控浏览器采集失败: {e}")
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    logger.debug("知乎结果页关闭失败", exc_info=True)
            if hb is not None:
                try:
                    hb.close()
                except Exception:
                    logger.debug("知乎受控浏览器断开失败", exc_info=True)

    def _parse_zhihu_card(self, card) -> "CollectedNote | None":
        """解析单个知乎搜索结果卡片为CollectedNote。"""
        from .base import CollectedNote

        # 标题
        title_el = card.query_selector(".ContentItem-title a, h2 a, .SearchItem-title")
        title = title_el.inner_text().strip() if title_el else ""

        # 链接
        url = ""
        if title_el:
            href = title_el.get_attribute("href") or ""
            if href.startswith("//"):
                url = "https:" + href
            elif href.startswith("/"):
                url = "https://www.zhihu.com" + href
            elif href:
                url = href

        # 摘要
        excerpt_el = card.query_selector(".RichContent-inner, .content, .SearchItem-excerpt")
        content = excerpt_el.inner_text().strip() if excerpt_el else ""

        # 作者
        author_el = card.query_selector(".AuthorInfo-name, .author, .UserLink-link")
        author = author_el.inner_text().strip() if author_el else ""

        # 赞同数
        vote_el = card.query_selector(".VoteButton--up, .like, .ContentItem-action button")
        likes = 0
        if vote_el:
            vote_text = vote_el.inner_text().strip()
            digits = "".join(c for c in vote_text if c.isdigit())
            if digits:
                likes = int(digits)

        # 评论数
        comment_el = card.query_selector(".ContentItem-action button:nth-child(2), .comment")
        comments = 0
        if comment_el:
            ctext = comment_el.inner_text().strip()
            digits = "".join(c for c in ctext if c.isdigit())
            if digits:
                comments = int(digits)

        if not title and not content:
            return None

        return CollectedNote(
            title=title[:200],
            content=content[:500],
            url=url,
            author=author,
            author_id="",
            publish_date="",
            likes=likes,
            comments=comments,
            collects=0,
            shares=0,
            cover="",
            source_platform="zhihu",
            raw_data={"title": title, "url": url},
        )

    def _search_api(self, keyword: str, max_results: int) -> AdapterResult:
        try:
            from urllib.parse import quote
            params = {
                "t": "general",
                "q": keyword.strip(),
                "limit": min(max_results, 20),
                "correction": 1,
            }
            resp = requests.get(
                self.SEARCH_URL,
                headers=self._get_headers(),
                params=params,
                timeout=15,
            )
            data = resp.json()

            # 知乎 API 错误响应
            if isinstance(data, dict) and data.get("error"):
                err = data["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return AdapterResult(success=False, error=f"知乎搜索API错误: {msg}")

            items = data.get("data", []) if isinstance(data, dict) else []
            notes = []
            seen_urls = set()
            for item in items:
                obj = item.get("object", {}) if isinstance(item, dict) else {}
                note = self._object_to_note(obj)
                if note:
                    if note.url and note.url in seen_urls:
                        continue
                    if note.url:
                        seen_urls.add(note.url)
                    notes.append(note)
                if len(notes) >= max_results:
                    break

            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            # 正常无内容
            return AdapterResult(success=True, notes=[], raw_count=0)

        except Exception as exc:
            logger.exception("知乎采集异常")
            return AdapterResult(success=False, error=f"知乎采集异常: {exc}")

    def _object_to_note(self, obj: dict):
        """将知乎搜索结果 object 转为标准化 CollectedNote。"""
        try:
            obj_type = obj.get("type", "")
            if obj_type == "answer":
                question = obj.get("question", {}) or {}
                qid = question.get("id", "")
                aid = obj.get("id", "")
                url = f"https://www.zhihu.com/question/{qid}/answer/{aid}" if qid and aid else ""
                title = question.get("title", "") or f"知乎回答 {aid}"
                content = self._clean_html(obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = int(obj.get("voteup_count", 0) or 0)
                comments = int(obj.get("comment_count", 0) or 0)
                publish_date = self._ts_to_iso(obj.get("created_time"))
            elif obj_type == "article":
                aid = obj.get("id", "")
                url = obj.get("url", "") or f"https://zhuanlan.zhihu.com/p/{aid}"
                title = obj.get("title", "") or f"知乎文章 {aid}"
                content = self._clean_html(obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = int(obj.get("voteup_count", 0) or 0)
                comments = int(obj.get("comment_count", 0) or 0)
                publish_date = self._ts_to_iso(obj.get("created"))
            elif obj_type == "question":
                qid = obj.get("id", "")
                url = f"https://www.zhihu.com/question/{qid}" if qid else ""
                title = obj.get("title", "") or f"知乎问题 {qid}"
                content = self._clean_html(obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = 0
                comments = int(obj.get("answer_count", 0) or 0)
                publish_date = self._ts_to_iso(obj.get("created"))
            else:
                # 其他类型（live/column 等）跳过，不臆造
                return None

            if not title and not content:
                return None

            return self._make_note(
                title=title[:120],
                content=content,
                url=url,
                author=author,
                author_id=author_id,
                publish_date=publish_date,
                likes=likes,
                comments=comments,
                collects=0,
                shares=0,
                cover="",
                source_platform=self.platform_name,
                raw_data={
                    "engine": "zhihu_search_v3",
                    "object_type": obj_type,
                    "id": obj.get("id"),
                    "updated_time": obj.get("updated_time"),
                },
            )
        except Exception as exc:
            logger.warning("知乎 object 解析失败: %s", exc)
            return None

    @staticmethod
    def _clean_html(text: str) -> str:
        """去除 HTML 标签及多余空白。"""
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", str(text))
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _ts_to_iso(ts) -> str:
        """Unix 秒级时间戳 → ISO 8601；无效返回空串（不臆造）。"""
        if not ts:
            return ""
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        except (ValueError, TypeError, OSError):
            return ""

    # ── detail: 内容详情（支持 answer/article/question 三类）──
    def detail(self, content_id: str, content_type: str = "answer", **kwargs) -> AdapterResult:
        if not content_id or not str(content_id).strip():
            return AdapterResult(success=False, error="content_id 为空")
        ctype = (content_type or "answer").strip().lower()
        try:
            if ctype == "answer":
                url = f"https://www.zhihu.com/api/v4/answers/{content_id}"
            elif ctype == "article":
                url = f"https://www.zhihu.com/api/v4/articles/{content_id}"
            elif ctype == "question":
                url = f"https://www.zhihu.com/api/v4/questions/{content_id}"
            else:
                return AdapterResult(success=False, error=f"不支持的知乎内容类型: {ctype}")
            resp = requests.get(url, headers=self._get_headers(),
                                params={"include": "content,voteup_count,comment_count"}, timeout=15)
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                return AdapterResult(success=False, error=f"知乎详情失败: {data['error'].get('message', str(data['error']))}")
            note = self._object_to_note({**data, "type": ctype})
            if note:
                return AdapterResult(success=True, notes=[note], raw_count=1)
            return AdapterResult(success=True, notes=[], raw_count=0)
        except Exception as exc:
            logger.exception("知乎详情采集异常")
            return AdapterResult(success=False, error=f"知乎详情异常: {exc}")

    # ── comments: 内容评论（知乎 root_comments API，只读）──
    def comments(self, content_id: str, content_type: str = "answer", max_comments: int = 20, **kwargs) -> AdapterResult:
        if not content_id or not str(content_id).strip():
            return AdapterResult(success=False, error="content_id 为空")
        ctype = (content_type or "answer").strip().lower()
        try:
            resource = "answers" if ctype == "answer" else ("articles" if ctype == "article" else "questions")
            url = f"https://www.zhihu.com/api/v4/{resource}/{content_id}/root_comments"
            resp = requests.get(url, headers=self._get_headers(),
                                params={"order": "normal", "limit": min(max_comments, 20)}, timeout=15)
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                return AdapterResult(success=False, error=f"知乎评论失败: {data['error'].get('message', str(data['error']))}")
            items = data.get("data", []) if isinstance(data, dict) else []
            notes = []
            for c in items[:max_comments]:
                author = c.get("author") or {}
                notes.append(self._make_note(
                    title="",
                    content=self._clean_html(c.get("content", "")),
                    url=f"https://www.zhihu.com/{resource[:-1]}/{content_id}#cmt{c.get('id')}",
                    author=author.get("name", ""),
                    author_id=str(author.get("id", "")),
                    publish_date=self._ts_to_iso(c.get("created_time")),
                    likes=int(c.get("vote_count", 0) or 0),
                    comments=int(c.get("child_comment_count", 0) or 0),
                    collects=0,
                    shares=0,
                    cover="",
                    source_platform=self.platform_name,
                    raw_data={"engine": "zhihu_comments_api", "cid": c.get("id"), "type": "comment"},
                ))
            return AdapterResult(success=True, notes=notes, raw_count=len(notes))
        except Exception as exc:
            logger.exception("知乎评论采集异常")
            return AdapterResult(success=False, error=f"知乎评论异常: {exc}")

    # ── creator: 知乎用户信息（members API）──
    def creator(self, user_id: str, **kwargs) -> AdapterResult:
        if not user_id or not str(user_id).strip():
            return AdapterResult(success=False, error="user_id 为空")
        try:
            url = f"https://www.zhihu.com/api/v4/members/{user_id}"
            resp = requests.get(url, headers=self._get_headers(),
                                params={"include": "allow_message,is_followed,is_following,is_org,is_blocking,employments,answer_count,follower_count,articles_count,gender,badge[?(type=best_answerer)].topics"},
                                timeout=15)
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                return AdapterResult(success=False, error=f"知乎用户信息失败: {data['error'].get('message', str(data['error']))}")
            note = self._make_note(
                title=data.get("name", ""),
                content=(data.get("headline") or "").strip(),
                url=data.get("url") or f"https://www.zhihu.com/people/{data.get('id', user_id)}",
                author=data.get("name", ""),
                author_id=str(data.get("id", "")),
                publish_date="",
                likes=int(data.get("follower_count", 0) or 0),
                comments=int(data.get("answer_count", 0) or 0),
                collects=int(data.get("articles_count", 0) or 0),
                shares=0,
                cover=data.get("avatar_url", ""),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "zhihu_members_api",
                    "uid": data.get("id"),
                    "gender": data.get("gender"),
                    "is_org": data.get("is_org"),
                    "type": "creator",
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        except Exception as exc:
            logger.exception("知乎用户采集异常")
            return AdapterResult(success=False, error=f"知乎用户异常: {exc}")
