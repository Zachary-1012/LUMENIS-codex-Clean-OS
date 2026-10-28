# -*- coding: utf-8 -*-
"""
Bilibili（B站）视频内容采集适配器
----------------------------------
定位：服务于 Z-Brand Core 多平台内容采集。
基于 bilibili_login_manager.search_videos（cookie + requests API），
薄封装为 v4 BaseAdapter 契约，自动接入熔断器/限流/重试/降级体系。

数据主路径：B站搜索 API
  https://api.bilibili.com/x/web-interface/search/type
返回视频列表（aid/bvid/title/author/play/pubdate/duration/description）。

状态映射：
  - ok=True 且有结果  → SUCCESS
  - ok=True 但空      → EMPTY (success=True, notes=[])
  - code=-101         → cookie 失效（SESSION_EXPIRED 语义）
  - code=-352/-509    → 风控/频控（RISK_WARNING 语义）
  - 其他错误          → COLLECT_ERROR

时间口径：pubdate 为 Unix 秒级时间戳，转 ISO 8601；
采集时间由入库层写 captured_at，二者严格分离。

只读红线：不发评论、不点赞、不关注、不执行任何账号写操作；
遇到风控/验证码如实返回，不破解、不绕过、不对抗。
"""
import logging
from datetime import datetime, timezone

from .base import BaseAdapter, AdapterResult, optional_int
from .cookie_vault import to_requests_cookies, check_cookie_status

logger = logging.getLogger(__name__)


class _ReadResponseFailure(RuntimeError):
    def __init__(self, metadata):
        self.metadata = metadata
        super().__init__(metadata['failure_class'])


class BilibiliAdapter(BaseAdapter):
    """B站视频搜索适配器（API + cookie，薄封装 bilibili_login_manager）"""

    platform_name = "bilibili"
    platform_display = "B站"

    # B站 API 错误码 → 人类可读说明（仅记录，不做绕过）
    _ERROR_HINTS = {
        -101: "账号未登录或 cookie 失效",
        -352: "风控校验失败，需人工验证",
        -404: "无搜索结果",
        -509: "请求过于频繁，已触发频控",
        6000: "搜索词包含敏感内容",
    }

    def __init__(self, manager=None, public_read_only=False, **kwargs):
        super().__init__(**kwargs)
        self._manager = manager  # 向后兼容：旧测试传入 manager，现统一走 cookie_vault
        self.public_read_only = public_read_only is True

    @staticmethod
    def _cookie_ok() -> bool:
        s = check_cookie_status("bilibili")
        return s["status"] == "ACTIVE"

    @staticmethod
    def _response_data(response):
        """Classify the actual response, without parsing error strings as status."""
        from collections.abc import Mapping
        from email.utils import parsedate_to_datetime
        import math
        status = response.status_code if type(response.status_code) is int else None
        headers = response.headers if isinstance(response.headers,Mapping) else {}
        retry = headers.get('Retry-After')
        retry_seconds = None
        if isinstance(retry,str):
            try:
                retry_seconds = int(retry) if retry.isascii() and retry.isdigit() else max(
                    0,math.ceil((parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds()))
            except (ValueError,TypeError,OverflowError):
                pass
        observed = {'http_status':status,'retry_after_seconds':retry_seconds,'provider_code':None}
        if status in {401,403,404,412,429,503}:
            observed['failure_class'] = {401:'AUTH_REQUIRED',403:'ACCESS_BLOCKED',404:'CONTENT_UNAVAILABLE',
                412:'ACCESS_BLOCKED',429:'RATE_LIMITED',503:'PROVIDER_UNAVAILABLE'}[status]
            raise _ReadResponseFailure(observed)
        try:
            data = response.json()
        except (ValueError,TypeError):
            raise _ReadResponseFailure({**observed,'failure_class':'SOURCE_PARSE_ERROR'}) from None
        if not isinstance(data,dict) or type(data.get('code')) is not int:
            raise _ReadResponseFailure({**observed,'failure_class':'SOURCE_PROTOCOL_ERROR'})
        code = data['code']
        if code != 0:
            raise _ReadResponseFailure({**observed,'provider_code':code,'failure_class':{
                -101:'AUTH_REQUIRED',-352:'VERIFICATION_REQUIRED',-509:'RATE_LIMITED',
                412:'ACCESS_BLOCKED',-412:'ACCESS_BLOCKED',-404:'CONTENT_UNAVAILABLE'}.get(code,'PROVIDER_REJECTED')})
        return data

    @staticmethod
    def _response_failure(exc):
        metadata = (dict(exc.metadata) if isinstance(exc,_ReadResponseFailure) else
                    {'failure_class':'CONNECTIVITY_FAILURE','error_type':type(exc).__name__})
        labels = {'AUTH_REQUIRED':'B站登录态待验证','VERIFICATION_REQUIRED':'B站需要人工验证',
            'RATE_LIMITED':'B站频控，等待服务端允许重试','ACCESS_BLOCKED':'B站拒绝本次访问',
            'CONTENT_UNAVAILABLE':'B站该内容不可用','SOURCE_PARSE_ERROR':'B站响应无法解析',
            'SOURCE_PROTOCOL_ERROR':'B站响应协议待核','PROVIDER_REJECTED':'B站接口拒绝本次请求'}
        return AdapterResult(success=False,error=labels.get(metadata['failure_class'],'B站采集异常: '+type(exc).__name__),
                             metadata=metadata)

    def search(self, keyword: str, max_results: int = 20, *, cursor=None, **kwargs) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        page_number = 1
        if cursor is not None:
            if (not isinstance(cursor, dict) or set(cursor) != {'page'}
                    or type(cursor['page']) is not int or not 1 <= cursor['page'] <= 100000):
                return AdapterResult(success=False, error='BILIBILI_SEARCH_CURSOR_INVALID')
            page_number = cursor['page']
        if type(max_results) is not int or not 1 <= max_results <= 20:
            return AdapterResult(success=False, error='BILIBILI_SEARCH_PAGE_SIZE_INVALID')
        # 向后兼容：测试传入 mock manager 时走 manager 路径
        if self._manager is not None:
            if cursor is not None:
                return AdapterResult(success=False, error='MANAGER_NATIVE_PAGINATION_NOT_IMPLEMENTED')
            try:
                login_status = self._manager.check_login_status()
                if not login_status.get("logged_in", False):
                    return AdapterResult(success=False, error="登录态失效：B站 cookie 未配置或已过期")
                raw = self._manager.search_videos(keyword, max_results=max_results)
            except Exception as _e:
                return AdapterResult(success=False, error=f"manager搜索异常: {_e}")
            if not isinstance(raw, dict):
                return AdapterResult(success=False, error=f"manager返回异常: {raw!r}")
            if not raw.get("ok", False):
                code = raw.get("code")
                error = raw.get("error", "搜索失败")
                if code == -101:
                    return AdapterResult(success=False, error=f"B站 cookie 失效: {error}")
                if code in (-352, -509):
                    return AdapterResult(success=False, error=f"B站风控/频控: {error}")
                return AdapterResult(success=False, error=f"B站搜索失败: {error} (code={code})")
            videos = raw.get("videos", []) or []
            notes = []
            for v in videos[:max_results]:
                notes.append(self._make_note(
                    title=self._clean_title(v.get("title")),
                    content=(v.get("description") or "").strip(),
                    url=v.get("url", ""),
                    author=v.get("author", ""),
                    author_id="",
                    publish_date=self._ts_to_iso(v.get("pubdate")),
                    likes=None,
                    comments=None,  # Search review fields lack verified comment semantics.
                    collects=optional_int(v.get("favorites")),
                    shares=None,
                    source_platform="bilibili",
                    raw_data=v,
                ))
            return AdapterResult(success=True, notes=notes, raw_count=len(videos))
        try:
            import requests as _req
            # 登录态前置检查（经 cookie_vault）
            if not self.public_read_only and not self._cookie_ok():
                return AdapterResult(
                    success=False,
                    error="B站 cookie 缺失或无关键认证 cookie，请更新 data/bilibili_cookies.json",
                )
            cookies = {} if self.public_read_only else to_requests_cookies("bilibili")
            resp = _req.get(
                "https://api.bilibili.com/x/web-interface/search/type",
                params={"search_type": "video", "keyword": keyword.strip(),
                        "page": page_number, "page_size": max_results},
                cookies=cookies,
                headers=self._api_headers(),
                timeout=15,
            )
            data = self._response_data(resp)
            if data.get("code") != 0:
                raw = {"ok": False, "error": data.get("message", "搜索失败"), "code": data.get("code")}
            else:
                result = data.get("data", {})
                videos = []
                for ri in result.get("result", []):
                    videos.append({
                        "id": ri.get("aid"), "bvid": ri.get("bvid"),
                        "mid": ri.get("mid"), "pic": ri.get("pic"),
                        "title": ri.get("title", ""), "author": ri.get("author"),
                        "play": ri.get("play"), "video_review": ri.get("video_review"),
                        "favorites": ri.get("favorites"), "pubdate": ri.get("pubdate"),
                        "duration": ri.get("duration"), "description": ri.get("description", ""),
                        "url": f"https://www.bilibili.com/video/{ri.get('bvid', '')}",
                    })
                raw = {"ok": True, "videos": videos, "total": result.get("numResults"),
                       "page": result.get('page'), "num_pages": result.get('numPages')}
            if not isinstance(raw, dict):
                return AdapterResult(success=False, error=f"B站搜索返回异常: {raw!r}")

            if not raw.get("ok", False):
                code = raw.get("code")
                error = raw.get("error", "搜索失败")
                hint = self._ERROR_HINTS.get(code, "")
                # 风控/未登录如实返回，不硬刚、不绕过
                if code == -101:
                    return AdapterResult(
                        success=False,
                        error=f"B站 cookie 失效: {hint or error}",
                    )
                if code in (-352, -509):
                    return AdapterResult(
                        success=False,
                        error=f"B站风控/频控: {hint or error}",
                    )
                return AdapterResult(
                    success=False,
                    error=f"B站搜索失败: {error} (code={code})",
                )

            videos = raw.get("videos", []) or []
            notes = []
            for v in videos[:max_results]:
                notes.append(self._make_note(
                    title=self._clean_title(v.get("title")),
                    content=(v.get("description") or "").strip(),
                    url=v.get("url", ""),
                    author=v.get("author", ""),
                    author_id=str(v['mid']) if v.get('mid') is not None else "",
                    publish_date=self._ts_to_iso(v.get("pubdate")),
                    likes=None,    # 搜索API不返回点赞数
                    comments=None,  # Search review fields lack verified comment semantics.
                    collects=optional_int(v.get("favorites")),
                    shares=None,
                    cover=v.get('pic') or "",
                    source_platform=self.platform_name,
                    raw_data={
                        "engine": "bilibili_search_api",
                        "aid": v.get("id"),
                        "bvid": v.get("bvid"),
                        "play": v.get("play"),
                        "video_review": v.get("video_review"),
                        "review": v.get("review"),
                        "duration": v.get("duration"),
                        "pubdate_ts": v.get("pubdate"),
                        "media_type": v.get("type", "video"),
                        "mid": v.get('mid'), "pic": v.get('pic'),
                    },
                ))

            pages = raw.get('num_pages')
            observed = type(pages) is int and pages >= 0 and raw.get('page') == page_number
            exhausted = page_number >= pages if observed else None
            return AdapterResult(success=True, notes=notes, raw_count=len(notes), metadata={
                'access_class': 'Z0' if self.public_read_only else 'Z1',
                'pagination': {'request_cursor': cursor, 'next_cursor': {'page': page_number + 1}
                    if observed and not exhausted else None, 'exhausted': exhausted,
                    'reported_total': raw.get('total') if type(raw.get('total')) is int else None,
                    'page_complete': True, 'coverage_scope': 'PROVIDER_VISIBLE_VIDEO_SEARCH_PAGE'}})

        except Exception as exc:
            logger.error('B站采集未完成 error_type=%s',type(exc).__name__)
            return self._response_failure(exc)

    @staticmethod
    def _clean_title(raw):
        """去除 B站搜索结果标题中的 <em class='keyword'> 高亮标签及多余空白。"""
        if not raw:
            return ""
        import re
        text = re.sub(r"</?em[^>]*>", "", str(raw))
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _ts_to_iso(ts):
        """Unix 秒级时间戳 → ISO 8601；无效返回空串（不臆造时间）。"""
        if not ts:
            return ""
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        except (ValueError, TypeError, OSError):
            return ""

    # ── detail: 视频详情（B站 view API，补全搜索API缺失的点赞/评论/UP主mid）──
    def detail(self, bvid: str, **kwargs) -> AdapterResult:
        if not bvid or not str(bvid).strip():
            return AdapterResult(success=False, error="bvid 为空")
        try:
            import requests as _req
            bvid = self._bvid(bvid)
            if not self.public_read_only and not self._cookie_ok():
                return AdapterResult(success=False, error="B站 cookie 缺失或无关键认证 cookie，请更新 data/bilibili_cookies.json")
            cookies = self._load_cookies()
            if not cookies and not self.public_read_only:
                return AdapterResult(success=False, error="B站 cookie 不存在，无法获取详情")
            resp = _req.get(
                "https://api.bilibili.com/x/web-interface/view",
                params={"bvid": str(bvid).strip()},
                cookies=cookies,
                headers=self._api_headers(),
                timeout=15,
            )
            data = self._response_data(resp)
            if data.get("code") != 0:
                code = data.get("code")
                msg = data.get("message", "详情获取失败")
                if code == -101:
                    return AdapterResult(success=False, error=f"B站 cookie 失效: {msg}")
                if code in (-352, -509, 412):
                    return AdapterResult(success=False, error=f"B站风控/频控: {msg}")
                return AdapterResult(success=False, error=f"B站详情失败: {msg} (code={code})")
            v = data.get("data", {}) or {}
            stat = v.get("stat", {}) or {}
            owner = v.get("owner", {}) or {}
            note = self._make_note(
                title=v.get("title", ""),
                content=(v.get("desc") or "").strip(),
                url=f"https://www.bilibili.com/video/{v.get('bvid', bvid)}",
                author=owner.get("name", ""),
                author_id=str(owner.get("mid", "")),
                publish_date=self._ts_to_iso(v.get("pubdate")),
                likes=optional_int(stat.get("like")),
                comments=optional_int(stat.get("reply")),
                collects=optional_int(stat.get("favorite")),
                shares=optional_int(stat.get("share")),
                cover=v.get("pic", ""),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "bilibili_view_api",
                    "aid": v.get("aid"),
                    "bvid": v.get("bvid"),
                    "mid": owner.get("mid"),
                    "pubdate": v.get("pubdate"),
                    "like": stat.get("like"),
                    "reply": stat.get("reply"),
                    "favorite": stat.get("favorite"),
                    "share": stat.get("share"),
                    "view": stat.get("view"),
                    "danmaku": stat.get("danmaku"),
                    "coin": stat.get("coin"),
                    "duration": v.get("duration"),
                    "tname": v.get("tname"),
                    "pubdate_ts": v.get("pubdate"),
                    'source_observation':v,'body_state':'PLATFORM_VIDEO_DESCRIPTION',
                    'media_hints':[{'kind':'cover','url':v.get('pic'),
                        'native_locator':'$.data.pic','original_bytes_state':'NOT_ACQUIRED'},
                        *[{'kind':'video','url':None,'native_segment_id':str(segment['cid']),
                           'page_number':segment.get('page'),'title':segment.get('part'),
                           'duration_seconds':segment.get('duration'),
                           'native_locator':f'$.data.pages[{index}]',
                           'url_state':'NATIVE_SEGMENT_OBSERVED_PLAYBACK_URL_NOT_ACQUIRED',
                           'original_bytes_state':'NOT_ACQUIRED'}
                          for index,segment in enumerate(v.get('pages') or [])
                          if isinstance(segment,dict) and type(segment.get('cid')) in (str,int)]],
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        except Exception as exc:
            logger.error('B站详情未完成 error_type=%s',type(exc).__name__)
            return self._response_failure(exc)

    # ── comments: 视频评论（B站 reply API，只读）──
    def comments(self, bvid: str, max_comments: int = 20, **kwargs) -> AdapterResult:
        if not bvid or not str(bvid).strip():
            return AdapterResult(success=False, error="bvid 为空")
        cursor = kwargs.get('cursor')
        include_replies = kwargs.get('include_replies', False)
        if type(include_replies) is not bool:
            return AdapterResult(success=False, error='BILIBILI_REPLY_SELECTION_INVALID')
        reply_root, pending_roots, next_root_page = None, [], None
        page_number = 1
        if cursor is not None:
            if not isinstance(cursor, dict):
                return AdapterResult(success=False, error='BILIBILI_COMMENT_CURSOR_INVALID')
            if set(cursor) == {'mode','root_id','page','pending_roots','next_root_page','root_exhausted'}:
                import re
                if (include_replies is not True or cursor['mode'] != 'replies'
                        or not isinstance(cursor['root_id'], str) or re.fullmatch(r'[1-9]\d{0,24}', cursor['root_id']) is None
                        or not isinstance(cursor['pending_roots'], list) or len(cursor['pending_roots']) > 20
                        or cursor['root_exhausted'] is not None and type(cursor['root_exhausted']) is not bool
                        or any(not isinstance(value,str) or re.fullmatch(r'[1-9]\d{0,24}',value) is None
                               for value in cursor['pending_roots'])
                        or cursor['next_root_page'] is not None and (
                            type(cursor['next_root_page']) is not int or cursor['next_root_page'] < 1)):
                    return AdapterResult(success=False, error='BILIBILI_COMMENT_CURSOR_INVALID')
                reply_root, pending_roots, next_root_page = cursor['root_id'], cursor['pending_roots'], cursor['next_root_page']
            elif set(cursor) != {'page'}:
                return AdapterResult(success=False, error='BILIBILI_COMMENT_CURSOR_INVALID')
            if type(cursor['page']) is not int or not 1 <= cursor['page'] <= 100000:
                return AdapterResult(success=False, error='BILIBILI_COMMENT_CURSOR_INVALID')
            page_number = cursor['page']
        if type(max_comments) is not int or not 1 <= max_comments <= 20:
            return AdapterResult(success=False, error='BILIBILI_COMMENT_PAGE_SIZE_INVALID')
        try:
            import requests as _req
            bvid = self._bvid(bvid)
            if not self.public_read_only and not self._cookie_ok():
                return AdapterResult(success=False, error="B站 cookie 缺失或无关键认证 cookie，请更新 data/bilibili_cookies.json")
            cookies = self._load_cookies()
            if not cookies and not self.public_read_only:
                return AdapterResult(success=False, error="B站 cookie 不存在，无法获取评论")
            # 先取详情拿 aid（评论API需要oid=aid）
            aid = kwargs.get("aid")
            if not aid:
                det = self.detail(bvid)
                if det.success and det.notes:
                    aid = det.notes[0].raw_data.get("aid")
            if not aid:
                return AdapterResult(success=False, error="无法获取 aid，评论需 aid 参数")
            resp = _req.get(
                "https://api.bilibili.com/x/v2/reply/reply" if reply_root else "https://api.bilibili.com/x/v2/reply",
                params={"type": 1, "oid": aid, "pn": page_number, "ps": max_comments,
                        **({'root':reply_root} if reply_root else {'sort':1})},
                cookies=cookies,
                headers=self._api_headers(),
                timeout=15,
            )
            data = self._response_data(resp)
            if data.get("code") != 0:
                return AdapterResult(success=False, error=f"B站评论失败: {data.get('message')} (code={data.get('code')})")
            source_data = data.get('data') or {}
            replies = source_data.get('replies') or []
            if reply_root and source_data.get('root') and str(source_data['root'].get('rpid')) != reply_root:
                return AdapterResult(success=False, error='BILIBILI_REPLY_PARENT_MISMATCH')
            notes = []
            selected = []
            for root in replies:
                selected.append((root, reply_root))
                selected.extend((reply, root.get('rpid')) for reply in root.get('replies') or [])
            for r, root_id in selected:
                member = r.get("member", {}) or {}
                content = r.get("content", {}) or {}
                notes.append(self._make_note(
                    title="",
                    content=(content.get("message") or "").strip(),
                    url=f"https://www.bilibili.com/video/{bvid}#reply{r.get('rpid')}",
                    author=member.get("uname", ""),
                    author_id=str(member.get("mid", "")),
                    publish_date=self._ts_to_iso(r.get("ctime")),
                    likes=optional_int(r.get("like")),
                    comments=None,
                    collects=None,
                    shares=None,
                    cover="",
                    source_platform=self.platform_name,
                    raw_data={"engine": "bilibili_reply_api", "rpid": r.get("rpid"), "type": "comment",
                              'parent_content_id': bvid,
                              'parent_comment_id': root_id or r.get('root') or None,
                              'reply_to_comment_id': r.get('parent') or None,
                              'reply_count': r.get('rcount'), 'source_observation': r},
                ))
            page = source_data.get('page') or {}
            observed = (isinstance(page, dict) and type(page.get('num')) is int
                and page['num'] == page_number and type(page.get('size')) is int and page['size'] > 0
                and type(page.get('count')) is int and page['count'] >= 0)
            exhausted = page['num'] * page['size'] >= page['count'] if observed else None
            next_cursor = {'page': page_number + 1} if observed and not exhausted else None
            omitted_replies = any(type(root.get('rcount')) is int
                and root['rcount'] > len(root.get('replies') or []) for root in replies)
            replies_known = all(type(root.get('rcount')) is int and root['rcount'] >= 0 for root in replies)
            if reply_root:
                if exhausted is False:
                    next_cursor = {**cursor, 'page':page_number + 1}
                elif exhausted is True and pending_roots:
                    next_cursor = {**cursor, 'root_id':pending_roots[0], 'page':1,
                                   'pending_roots':pending_roots[1:]}
                elif exhausted is True and next_root_page:
                    next_cursor = {'page':next_root_page}
                else:
                    next_cursor = None
                replies_known, omitted_replies = exhausted is not None, exhausted is not True
                exhausted = (None if exhausted is None else False if not exhausted or pending_roots or next_root_page
                             else cursor['root_exhausted'])
            elif include_replies and omitted_replies:
                roots = [str(root['rpid']) for root in replies if root.get('rpid') is not None
                    and type(root.get('rcount')) is int and root['rcount'] > len(root.get('replies') or [])]
                if roots:
                    next_cursor = {'mode':'replies', 'root_id':roots[0], 'page':1,
                                   'pending_roots':roots[1:], 'next_root_page':
                                       next_cursor['page'] if next_cursor else None,
                                   'root_exhausted':exhausted}
                    exhausted = False
            return AdapterResult(success=True, notes=notes, raw_count=len(notes), metadata={
                'pagination': {'request_cursor': cursor, 'next_cursor': next_cursor,
                    'exhausted': exhausted, 'page_complete': True,
                    'coverage_scope': 'PROVIDER_DECLARED_VISIBLE_ROOT_COMMENTS_WITH_LOADED_REPLIES',
                    'reported_root_total': page.get('count') if observed and not reply_root else None,
                    'reported_reply_total': page.get('count') if observed and reply_root else None,
                    'replies_complete': False if omitted_replies else True if replies_known else None,
                    'partial_reason': ('NESTED_REPLY_PAGES_NOT_OBSERVED' if omitted_replies else
                                       'NATIVE_PAGE_TOTAL_NOT_OBSERVED' if not observed else None)}})
        except Exception as exc:
            logger.error('B站评论未完成 error_type=%s',type(exc).__name__)
            return self._response_failure(exc)

    # ── creator: UP主信息（B站 space API）──
    def creator(self, mid: str, **kwargs) -> AdapterResult:
        if not mid or not str(mid).strip():
            return AdapterResult(success=False, error="mid 为空")
        try:
            import requests as _req
            mid = self._mid(mid)
            cookies = self._load_cookies()
            if not cookies and not self.public_read_only:
                return AdapterResult(success=False, error="B站 cookie 不存在，无法获取UP主信息")
            resp = _req.get(
                "https://api.bilibili.com/x/web-interface/card" if self.public_read_only
                    else "https://api.bilibili.com/x/space/acc/info",
                params={"mid": str(mid).strip()},
                cookies=cookies,
                headers=self._api_headers(),
                timeout=15,
            )
            data = self._response_data(resp)
            if data.get("code") != 0:
                return AdapterResult(success=False, error=f"B站UP主信息失败: {data.get('message')} (code={data.get('code')})")
            payload = data.get("data", {}) or {}
            u = payload.get('card') or {} if self.public_read_only else payload
            if str(u.get('mid')) != mid:
                return AdapterResult(success=False, error='BILIBILI_AUTHOR_ID_MISMATCH')
            note = self._make_note(
                title=u.get("name", ""),
                content=(u.get("sign") or "").strip(),
                url=f"https://space.bilibili.com/{u.get('mid', mid)}",
                author=u.get("name", ""),
                author_id=str(u.get("mid", "")),
                publish_date="",
                likes=None,
                comments=None,
                collects=None,
                shares=None,
                cover=u.get("face", ""),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "bilibili_space_api",
                    "mid": u.get("mid"),
                    "level": u.get("level"),
                    "sex": u.get("sex"),
                    "silence": u.get("silence"),
                    "vip_type": (u.get("vip") or {}).get("type"),
                    "type": "creator",
                    'display_name':u.get('name'), 'bio':u.get('sign'), 'avatar_url':u.get('face'),
                    'profile_url':f'https://space.bilibili.com/{mid}',
                    'follower_count':optional_int(u.get('fans')),
                    'following_count':None, 'content_count':optional_int(payload.get('archive_count')),
                    'source_observation':payload,
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        except Exception as exc:
            logger.error('B站作者未完成 error_type=%s',type(exc).__name__)
            return self._response_failure(exc)

    def author_posts(self, author_id, *, max_results=20, cursor=None, **kwargs):
        """One native UP-space video page; no challenge/signature fallback."""
        try:
            import requests
            mid = self._mid(author_id)
            if type(max_results) is not int or not 1 <= max_results <= 20:
                raise ValueError('BILIBILI_AUTHOR_PAGE_SIZE_INVALID')
            page = 1
            if cursor is not None:
                if (not isinstance(cursor,dict) or set(cursor) != {'page'}
                        or type(cursor['page']) is not int or not 1 <= cursor['page'] <= 100000):
                    raise ValueError('BILIBILI_AUTHOR_CURSOR_INVALID')
                page = cursor['page']
            cookies = self._load_cookies()
            if not self.public_read_only and not cookies:
                return AdapterResult(success=False, error='B站登录态未配置')
            response = requests.get('https://api.bilibili.com/x/space/arc/search',
                params={'mid':mid,'pn':page,'ps':max_results,'order':'pubdate'},
                cookies=cookies, headers=self._api_headers(), timeout=15)
            data = self._response_data(response)
            if data.get('code') != 0:
                return AdapterResult(success=False, error=f"B站作者历史失败: {data.get('message')} (code={data.get('code')})")
            payload = data.get('data') or {}
            videos = (payload.get('list') or {}).get('vlist') or []
            notes = []
            for video in videos:
                bvid = self._bvid(video.get('bvid'))
                native_mid = str(video['mid']) if video.get('mid') is not None else None
                if native_mid is not None and native_mid != mid:
                    raise ValueError('BILIBILI_AUTHOR_POST_OWNER_MISMATCH')
                notes.append(self._make_note(title=self._clean_title(video.get('title')),
                    content=video.get('description') or '', url=f'https://www.bilibili.com/video/{bvid}',
                    author=video.get('author') or '', author_id=native_mid or '',
                    publish_date=self._ts_to_iso(video.get('created')), likes=None, comments=None,
                    collects=None, shares=None, cover=video.get('pic') or '', source_platform=self.platform_name,
                    raw_data={**video,'bvid':bvid,'pubdate':video.get('created'),
                              'engine':'bilibili_author_video_page','requested_author_id':mid}))
            declared = payload.get('page') or {}
            known = (declared.get('pn') == page and type(declared.get('ps')) is int and declared['ps'] > 0
                     and type(declared.get('count')) is int and declared['count'] >= 0)
            exhausted = page * declared['ps'] >= declared['count'] if known else None
            return AdapterResult(success=True, notes=notes, raw_count=len(notes), metadata={
                'author_id':mid, 'pagination':{'request_cursor':cursor, 'next_cursor':{'page':page+1}
                    if exhausted is False else None, 'exhausted':exhausted, 'page_complete':True,
                    'reported_total':declared.get('count') if known else None,
                    'coverage_scope':'PROVIDER_VISIBLE_UP_SPACE_VIDEO_HISTORY'}})
        except Exception as exc:
            return self._response_failure(exc)

    def _load_cookies(self):
        """经 cookie_vault 读取 B站 cookie dict；失败返回 None。"""
        if self.public_read_only:
            return {}
        c = to_requests_cookies("bilibili")
        return c if c else None

    @staticmethod
    def _bvid(value):
        import re
        from urllib.parse import urlsplit
        text = str(value or '').strip()
        if text.startswith(('http://', 'https://')):
            parts = urlsplit(text)
            if (parts.scheme != 'https' or parts.hostname not in {'www.bilibili.com', 'bilibili.com'}
                    or parts.username or parts.password):
                raise ValueError('BILIBILI_SOURCE_ID_INVALID')
            text = parts.path.strip('/').removeprefix('video/')
        if re.fullmatch(r'BV[A-Za-z0-9]{10}', text) is None:
            raise ValueError('BILIBILI_SOURCE_ID_INVALID')
        return text

    @staticmethod
    def _mid(value):
        import re
        from urllib.parse import urlsplit
        text = str(value or '').strip()
        if text.startswith('https://'):
            parts = urlsplit(text)
            if parts.hostname != 'space.bilibili.com' or parts.username or parts.password:
                raise ValueError('BILIBILI_AUTHOR_ID_INVALID')
            text = parts.path.strip('/')
        if re.fullmatch(r'[1-9]\d{0,19}',text) is None:
            raise ValueError('BILIBILI_AUTHOR_ID_INVALID')
        return text

    @staticmethod
    def _api_headers():
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
        }
