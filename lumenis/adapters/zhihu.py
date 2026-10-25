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

from .base import AdapterResult, BaseAdapter, optional_int
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

    def __init__(self, cookie_string: str = "", *, public_read_only: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.public_read_only = public_read_only
        self._cookie_string = cookie_string
        if self.public_read_only:
            self._cookie_string = ''
        elif not self._cookie_string:
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

    def search(self, keyword: str, max_results: int = 20, *, cursor=None) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        if type(max_results) is not int or not 1 <= max_results <= 20:
            return AdapterResult(success=False,error='ZHIHU_PAGE_SIZE_INVALID')
        if cursor is not None and not self._page_cursor_valid(cursor):
            return AdapterResult(success=False,error='ZHIHU_SEARCH_CURSOR_INVALID')
        if self.public_read_only:
            return self._search_api(keyword,max_results,cursor=cursor)
        if cursor is not None:
            from lumenis.system.collector.adapters.config import get_platform_capabilities
            if isinstance(get_platform_capabilities('zhihu').get('readonly_worker'),dict):
                return AdapterResult(success=False,error='ZHIHU_BROWSER_NATIVE_CURSOR_NOT_SUPPORTED')
            return self._search_api(keyword,max_results,cursor=cursor)
        # Use the existing API only when no registered browser worker exists.
        # A registered worker failure, permission denial or challenge is final.
        browser_result = self._search_browser(keyword, max_results)
        if browser_result is not None:
            return browser_result
        return self._search_api(keyword, max_results,cursor=cursor)

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
        likes = None
        if vote_el:
            vote_text = vote_el.inner_text().strip()
            match = re.fullmatch(r'(?:赞同\s*)?([0-9]+)',vote_text)
            likes = optional_int(match.group(1)) if match else None

        # 评论数
        comment_el = card.query_selector(".ContentItem-action button:nth-child(2), .comment")
        comments = None
        if comment_el:
            ctext = comment_el.inner_text().strip()
            match = re.fullmatch(r'([0-9]+)\s*(?:条评论|评论)?',ctext)
            comments = optional_int(match.group(1)) if match else None

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
            collects=None,
            shares=None,
            cover="",
            source_platform="zhihu",
            raw_data={"title": title, "url": url},
        )

    @staticmethod
    def _page_cursor_valid(cursor):
        return (isinstance(cursor,dict) and set(cursor)=={'offset','limit'}
            and isinstance(cursor['offset'],str) and len(cursor['offset']) <= 4096
            and not any(ord(char)<32 for char in cursor['offset'])
            and type(cursor['limit']) is int and 1 <= cursor['limit'] <= 20)

    @classmethod
    def _next_page_cursor(cls, value, path, *, expected_query=None):
        """Keep the observed offset/page size; never fetch a supplied next URL."""
        from urllib.parse import parse_qs, urlsplit
        if not isinstance(value,str) or not value:
            return None
        try:
            parsed = urlsplit(value)
            query = parse_qs(parsed.query,keep_blank_values=True)
            if (parsed.scheme != 'https' or parsed.hostname != 'www.zhihu.com'
                    or parsed.port not in (None,443) or parsed.path != path
                    or parsed.username or parsed.password or parsed.fragment
                    or any(len(values)!=1 for values in query.values())
                    or any(key in query and query[key] != [expected]
                           for key,expected in (expected_query or {}).items())):
                return None
            cursor = {'offset':query['offset'][0], 'limit':int(query.get('limit',['20'])[0])}
            return cursor if cls._page_cursor_valid(cursor) else None
        except (ValueError,KeyError):
            return None

    @staticmethod
    def _content_target(value, content_type='answer'):
        from urllib.parse import urlsplit
        text, kind = str(value or '').strip(), content_type
        qualified = re.fullmatch(r'zhihu:(answer|article|question):([1-9][0-9]{0,24})',text)
        if qualified:
            kind,text = qualified.groups()
        elif text.startswith(('http://','https://')):
            parsed = urlsplit(text)
            if (parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443)
                    or parsed.hostname not in {'zhihu.com','www.zhihu.com','zhuanlan.zhihu.com'}):
                raise ValueError('ZHIHU_SOURCE_TARGET_INVALID')
            path = parsed.path.rstrip('/')
            match = re.fullmatch(r'/(?:question/[1-9][0-9]*/)?answer/([1-9][0-9]*)',path)
            if match:
                text,kind = match.group(1),'answer'
            elif parsed.hostname=='zhuanlan.zhihu.com' and re.fullmatch(r'/p/[1-9][0-9]*',path):
                text,kind = path.rsplit('/',1)[1],'article'
            elif re.fullmatch(r'/question/[1-9][0-9]*',path):
                text,kind = path.rsplit('/',1)[1],'question'
            else:
                raise ValueError('ZHIHU_SOURCE_TARGET_INVALID')
        if re.fullmatch(r'[1-9][0-9]{0,24}',text) is None or kind not in {'answer','article','question'}:
            raise ValueError('ZHIHU_SOURCE_TARGET_INVALID')
        return text,kind

    def _search_api(self, keyword: str, max_results: int, *, cursor=None) -> AdapterResult:
        try:
            params = {
                "t": "general",
                "q": keyword.strip(),
                "limit": min(max_results, 20),
                "correction": 1,
                **(cursor or {}),
            }
            resp = requests.get(
                self.SEARCH_URL,
                headers=self._get_headers(),
                params=params,
                timeout=15,
            )
            if type(resp.status_code) is int and resp.status_code in {401,403,429}:
                return AdapterResult(success=False,error=f'知乎 HTTP {resp.status_code}')
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

            paging = data.get('paging') or {} if isinstance(data,dict) else {}
            next_cursor = self._next_page_cursor(paging.get('next'),'/api/v4/search_v3',
                expected_query={'q':keyword.strip(),'t':'general'})
            return AdapterResult(success=True,notes=notes,raw_count=len(notes),metadata={
                'pagination':{'request_cursor':cursor,'next_cursor':next_cursor,
                    'exhausted':paging.get('is_end') if type(paging.get('is_end')) is bool else None,
                    'page_complete':len(items) <= max_results,
                    'coverage_scope':'PROVIDER_VISIBLE_ZHIHU_SEARCH_PAGE'}})

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
                content = self._clean_html(obj.get('content') if isinstance(obj.get('content'),str) else obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = optional_int(obj.get("voteup_count"))
                comments = optional_int(obj.get("comment_count"))
                publish_date = self._ts_to_iso(obj.get("created_time"))
            elif obj_type == "article":
                aid = obj.get("id", "")
                url = obj.get("url", "") or f"https://zhuanlan.zhihu.com/p/{aid}"
                title = obj.get("title", "") or f"知乎文章 {aid}"
                content = self._clean_html(obj.get('content') if isinstance(obj.get('content'),str) else obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = optional_int(obj.get("voteup_count"))
                comments = optional_int(obj.get("comment_count"))
                publish_date = self._ts_to_iso(obj.get("created"))
            elif obj_type == "question":
                qid = obj.get("id", "")
                url = f"https://www.zhihu.com/question/{qid}" if qid else ""
                title = obj.get("title", "") or f"知乎问题 {qid}"
                content = self._clean_html(obj.get('content') if isinstance(obj.get('content'),str) else obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = None
                comments = optional_int(obj.get('comment_count'))
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
                collects=None,
                shares=None,
                cover="",
                source_platform=self.platform_name,
                raw_data={
                    "engine": "zhihu_search_v3",
                    "object_type": obj_type,
                    "id": obj.get("id"),
                    "updated_time": obj.get("updated_time"),
                    'body_state':'PLATFORM_BODY' if isinstance(obj.get('content'),str) else 'SEARCH_EXCERPT',
                    'source_observation':obj,
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
            content_id,ctype = self._content_target(content_id,ctype)
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
            if type(resp.status_code) is int and resp.status_code in {401,403,429}:
                return AdapterResult(success=False,error=f'知乎 HTTP {resp.status_code}')
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                return AdapterResult(success=False, error=f"知乎详情失败: {data['error'].get('message', str(data['error']))}")
            if str(data.get('id')) != content_id:
                return AdapterResult(success=False,error='ZHIHU_SOURCE_ID_MISMATCH')
            note = self._object_to_note({**data, "type": ctype})
            if note:
                return AdapterResult(success=True, notes=[note], raw_count=1)
            return AdapterResult(success=True, notes=[], raw_count=0)
        except Exception as exc:
            logger.exception("知乎详情采集异常")
            return AdapterResult(success=False, error=f"知乎详情异常: {exc}")

    # ── comments: 原生根评论及回复页；每次调用只读一个已选页 ──
    def comments(self, content_id: str, content_type: str = "answer", max_comments: int = 20, **kwargs) -> AdapterResult:
        try:
            source_id = str(content_id)
            native_id,ctype = self._content_target(content_id,content_type)
            cursor, include = kwargs.get('cursor'), kwargs.get('include_replies',False)
            if type(max_comments) is not int or not 1 <= max_comments <= 20 or type(include) is not bool:
                raise ValueError('ZHIHU_COMMENT_REQUEST_INVALID')
            root_id, pending, root_next, root_end = None, [], None, None
            page = {'offset':'','limit':max_comments}
            if cursor is not None:
                if self._page_cursor_valid(cursor):
                    page = cursor
                elif (isinstance(cursor,dict) and set(cursor)=={
                        'mode','root_id','page','pending_roots','next_root','root_exhausted'}
                        and cursor['mode']=='replies' and include is True
                        and isinstance(cursor['root_id'],str) and re.fullmatch(r'[1-9][0-9]{0,24}',cursor['root_id'])
                        and self._page_cursor_valid(cursor['page'])
                        and isinstance(cursor['pending_roots'],list) and len(cursor['pending_roots']) <= 20
                        and all(isinstance(item,str) and re.fullmatch(r'[1-9][0-9]{0,24}',item)
                                for item in cursor['pending_roots'])
                        and (cursor['next_root'] is None or self._page_cursor_valid(cursor['next_root']))
                        and (cursor['root_exhausted'] is None or type(cursor['root_exhausted']) is bool)):
                    root_id,page,pending = cursor['root_id'],cursor['page'],cursor['pending_roots']
                    root_next,root_end = cursor['next_root'],cursor['root_exhausted']
                else:
                    raise ValueError('ZHIHU_COMMENT_CURSOR_INVALID')
            resource = ctype+'s'
            path = (f'/api/v4/comment_v5/comment/{root_id}/child_comment' if root_id else
                    f'/api/v4/comment_v5/{resource}/{native_id}/root_comment')
            url = 'https://www.zhihu.com'+path
            resp = requests.get(url, headers=self._get_headers(),
                                params={'order_by':'score',**page}, timeout=15)
            if type(resp.status_code) is int and resp.status_code in {401,403,429}:
                return AdapterResult(success=False,error=f'知乎 HTTP {resp.status_code}')
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                return AdapterResult(success=False, error=f"知乎评论失败: {data['error'].get('message', str(data['error']))}")
            if not isinstance(data,dict) or not isinstance(data.get('data'),list):
                raise ValueError('ZHIHU_COMMENT_SOURCE_SHAPE_INVALID')
            items = data['data']
            selected = []
            for item in items:
                selected.append((item,root_id))
                # Already returned replies are observations even with the
                # optional further-replies request disabled.
                selected.extend((child,str(item.get('id'))) for child in item.get('child_comments') or [])
            notes = []
            source_url = (f'https://zhuanlan.zhihu.com/p/{native_id}' if ctype=='article' else
                          f'https://www.zhihu.com/{ctype}/{native_id}')
            for c,parent in selected:
                author = c.get("author") or {}
                author = author.get('member') or author
                notes.append(self._make_note(
                    title="",
                    content=self._clean_html(c.get("content", "")),
                    url=f"{source_url}#cmt{c.get('id')}",
                    author=author.get("name", ""),
                    author_id=str(author.get("id", "")),
                    publish_date=self._ts_to_iso(c.get("created_time")),
                    likes=optional_int(c.get('like_count',c.get('vote_count'))),
                    comments=None,
                    collects=None,
                    shares=None,
                    cover="",
                    source_platform=self.platform_name,
                    raw_data={'engine':'zhihu_comment_v5','cid':c.get('id'),'type':'comment',
                        'parent_content_id':source_id,'parent_comment_id':parent or c.get('root_comment_id'),
                        'reply_to_comment_id':c.get('reply_to_comment_id',c.get('reply_comment_id')),
                        'reply_count':c.get('child_comment_count'),'source_observation':c},
                ))
            paging = data.get('paging') or {}
            end = paging.get('is_end') if type(paging.get('is_end')) is bool else None
            next_page = self._next_page_cursor(paging.get('next'),path,expected_query={'order_by':'score'})
            next_page = next_page if end is not True else None
            totals_known = all(type(item.get('child_comment_count')) is int and item['child_comment_count'] >= 0 for item in items)
            deferred = [str(item['id']) for item in items if type(item.get('child_comment_count')) is int
                        and item['child_comment_count'] > len(item.get('child_comments') or [])]
            replies_complete = not bool(deferred) if totals_known else None
            if root_id:
                if next_page is not None:
                    next_cursor = {**cursor,'page':next_page}
                elif end is True and pending:
                    next_cursor = {**cursor,'root_id':pending[0],'pending_roots':pending[1:],
                                   'page':{'offset':'','limit':max_comments}}
                elif end is True:
                    next_cursor = root_next
                else:
                    next_cursor = None
                replies_complete = end
                exhausted = root_end if end is True and not pending and root_next is None else False if next_cursor else None
            elif include and deferred:
                next_cursor = {'mode':'replies','root_id':deferred[0],'pending_roots':deferred[1:],
                    'page':{'offset':'','limit':max_comments},'next_root':next_page,'root_exhausted':end}
                exhausted = False
            else:
                next_cursor,exhausted = next_page,end
            return AdapterResult(success=True, notes=notes, raw_count=len(notes),metadata={
                'pagination':{'request_cursor':cursor,'next_cursor':next_cursor,'exhausted':exhausted,
                    'page_complete':True,'replies_complete':replies_complete,
                    'reported_root_total':optional_int(paging.get('totals')) if not root_id else None,
                    'reported_reply_total':optional_int(paging.get('totals')) if root_id else None,
                    'coverage_scope':'PROVIDER_VISIBLE_NATIVE_COMMENT_PAGES',
                    'partial_reason':'NATIVE_NEXT_CURSOR_NOT_OBSERVED' if end is False and next_page is None else
                        'REPLY_PAGES_PENDING' if replies_complete is False else None}})
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
                likes=None,
                comments=None,
                collects=None,
                shares=None,
                cover=data.get("avatar_url", ""),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "zhihu_members_api",
                    "uid": data.get("id"),
                    "gender": data.get("gender"),
                    "is_org": data.get("is_org"),
                    'url_token':data.get('url_token'), 'follower_count':data.get('follower_count'),
                    'answer_count':data.get('answer_count'), 'articles_count':data.get('articles_count'),
                    'source_observation':data,
                    "type": "creator",
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        except Exception as exc:
            logger.exception("知乎用户采集异常")
            return AdapterResult(success=False, error=f"知乎用户异常: {exc}")
