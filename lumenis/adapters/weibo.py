# -*- coding: utf-8 -*-
"""
微博（Weibo）内容采集适配器
----------------------------
定位：服务于 Z-Brand Core 多平台内容采集。
基于 weibo_login_manager 的 cookie + requests 调用微博移动端搜索 API，
薄封装为 v4 BaseAdapter 契约，接入熔断器/限流/重试/降级体系。

数据主路径：微博移动端搜索 API
  https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{keyword}
返回 cards[].mblog（微博正文/作者/点赞/评论/转发/发布时间）。

状态映射：
  - ok=1 且有 mblog → SUCCESS
  - ok=1 但空      → EMPTY (success=True, notes=[])
  - 登录失效/cookie 无效 → SESSION_EXPIRED 语义
  - 风控/验证码     → RISK_WARNING 语义（如实返回，不硬刚）
  - 其他错误        → COLLECT_ERROR

时间口径：created_at 为 "%a %b %d %H:%M:%S %z %Y"，转 ISO 8601；
采集时间由入库层写 captured_at，二者严格分离。

只读红线：不发微博、不评论、不点赞、不关注、不私信、不执行任何账号写操作；
遇到风控/验证码如实返回，不破解、不绕过、不对抗。
"""
import re
import logging
from datetime import datetime

import requests

from .base import BaseAdapter, AdapterResult, optional_int
from .cookie_vault import to_cookie_string, check_cookie_status
from .human_browser import NativePageWindowError, native_page_window, validate_native_page_window_cursor

logger = logging.getLogger(__name__)


class WeiboAdapter(BaseAdapter):
    """微博搜索适配器（移动端 API + cookie，只读采集）"""

    platform_name = "weibo"
    platform_display = "微博"

    SEARCH_URL = "https://m.weibo.cn/api/container/getIndex"
    # type=1 综合搜索；type=60 实时；type=61 关注；type=62 视频
    CONTAINER_TEMPLATE = "100103type={type}&q={keyword}"

    _MOBILE_UA = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    )

    def __init__(self, manager=None, **kwargs):
        super().__init__(**kwargs)
        self._manager = manager  # 向后兼容：旧测试传入 manager，现统一走 cookie_vault

    @staticmethod
    def _cookie_ok() -> bool:
        """经 cookie_vault 检查微博 cookie 是否存在且含关键认证 cookie。"""
        s = check_cookie_status("weibo")
        return s["status"] == "ACTIVE"

    def _get_headers(self, cookie_string: str) -> dict:
        return {
            "User-Agent": self._MOBILE_UA,
            "Referer": "https://m.weibo.cn/",
            "Accept": "application/json, text/plain, */*",
            "Cookie": cookie_string,
            "X-Requested-With": "XMLHttpRequest",
        }

    @staticmethod
    def _native_posts(cards):
        """Read native mblogs inside cards/card_group, never sidebar user cards."""
        stack = list(reversed(cards)) if isinstance(cards, list) else []
        posts = []
        while stack:
            card = stack.pop()
            if not isinstance(card, dict):
                continue
            if isinstance(card.get('mblog'), dict):
                posts.append(card['mblog'])
            if isinstance(card.get('card_group'), list):
                stack.extend(reversed(card['card_group']))
        return posts

    def search(self, keyword: str, max_results: int = 20, *, cursor=None) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        if type(max_results) is not int or not 1 <= max_results <= 20:
            return AdapterResult(success=False,error='WEIBO_PAGE_SIZE_INVALID')
        try:
            validate_native_page_window_cursor(cursor)
        except NativePageWindowError:
            return AdapterResult(success=False,error='WEIBO_NATIVE_CURSOR_WINDOW_INVALID')
        if cursor is not None and (not isinstance(cursor,dict) or set(cursor)-{'item_offset','page_sha256'} not in ({'page'},{'since_id'})
                or 'page' in cursor and (type(cursor['page']) is not int or not 1 <= cursor['page'] <= 100000)
                or 'since_id' in cursor and (not isinstance(cursor['since_id'],str)
                    or re.fullmatch(r'[0-9]{1,30}',cursor['since_id']) is None)):
            return AdapterResult(success=False,error='WEIBO_SEARCH_CURSOR_INVALID')
        try:
            # 注入 manager 时优先采信其登录态：明确未登录则前置短路，不发任何请求
            # （账号保活/不暴力采集；也使全 mock 单测不触网）
            if self._manager is not None:
                try:
                    _login_state = self._manager.check_login_status()
                except Exception:
                    _login_state = None
                if isinstance(_login_state, dict) and _login_state.get('logged_in') is False:
                    return AdapterResult(success=False, error='微博登录失效：当前账号未登录，请先登录或更新 cookie')
            # 注入 manager（测试或宿主 Auth Center）时由其提供 cookie；否则走统一 vault。
            manager_cookie = ""
            if self._manager is not None:
                try:
                    manager_cookie = self._manager.get_cookie_string() or ""
                except Exception:
                    manager_cookie = ""
            if self._manager is None and not self._cookie_ok():
                return AdapterResult(
                    success=False,
                    error="微博 cookie 缺失或无关键认证 cookie，请更新 data/weibo_cookies.json",
                )

            cookie_string = manager_cookie or to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")

            containerid = self.CONTAINER_TEMPLATE.format(
                type=1, keyword=keyword.strip()
            )
            native_request = ({key: value for key, value in cursor.items() if key not in {'item_offset','page_sha256'}}
                              if cursor is not None else {'page':1})
            params = {"containerid": containerid,'page_type':'searchall', **native_request}

            resp = requests.get(
                self.SEARCH_URL,
                headers=self._get_headers(cookie_string),
                params=params,
                timeout=15,
            )
            data = resp.json()

            # 微博 API ok=1 表示成功
            if data.get("ok") != 1:
                msg = data.get("msg", "") or str(data)
                # 登录失效/风控如实返回（ok=-100 为未登录跳转SSO）
                if data.get("ok") == -100 or "登录" in msg or "login" in msg.lower() or "passport" in msg.lower():
                    return AdapterResult(success=False, error=f"微博登录失效: {msg}")
                if "验证" in msg or "captcha" in msg.lower() or "风险" in msg:
                    return AdapterResult(success=False, error=f"微博风控/验证: {msg}")
                return AdapterResult(success=False, error=f"微博搜索失败: {msg}")

            cards = (data.get("data") or {}).get("cards") or []
            posts = self._native_posts(cards)
            window = native_page_window(posts, limit=max_results, cursor=cursor,
                identities=[str(post.get('mid') or post.get('id')) for post in posts])
            notes = []
            for mblog in window['rows']:
                note = self._mblog_to_note(mblog)
                if note:
                    notes.append(note)

            info = (data.get('data') or {}).get('cardlistInfo') or {}
            next_id = info.get('since_id')
            known = type(next_id) is int and next_id >= 0 or isinstance(next_id,str) and next_id.isascii() and next_id.isdigit()
            next_cursor = {'since_id':str(next_id)} if known and str(next_id) != '0' else None
            if next_cursor == native_request:
                next_cursor = None
            if not window['page_complete']:
                next_cursor = {**native_request, **window['next_window']}
            return AdapterResult(success=True,notes=notes,raw_count=len(notes),metadata={
                'pagination':{'request_cursor':cursor,'next_cursor':next_cursor,
                    'exhausted':False if not window['page_complete'] else str(next_id)=='0' if known else True if info.get('total') == 0 else None,
                    'reported_total':optional_int(info.get('total')), 'page_complete':window['page_complete'],
                    **{key: window[key] for key in ('window_start','window_end','observed_native_rows','page_sha256','page_identity_basis')},
                    'coverage_scope':'PROVIDER_VISIBLE_WEIBO_SEARCH_PAGE'}})

        except NativePageWindowError as exc:
            return self._window_failure(exc,cursor)
        except Exception as exc:
            logger.exception("微博采集异常")
            return AdapterResult(success=False, error=f"微博采集异常: {exc}")

    def _mblog_to_note(self, mblog: dict):
        """将微博 mblog 转为标准化 CollectedNote。"""
        try:
            long_body = (mblog.get('longText') or {}).get('longTextContent')
            text_html = long_body or mblog.get("text", "") or ""
            content = self._clean_html(text_html)
            user = mblog.get("user") or {}
            mid = str(mblog.get("mid") or mblog.get("id") or "")
            if not mid and not content:
                return None
            url = f"https://m.weibo.cn/status/{mid}" if mid else ""
            media = self._media_observations(mblog)
            return self._make_note(
                title=content[:80] or f"微博 {mid}",
                content=content,
                url=url,
                author=user.get("screen_name", ""),
                author_id=str(user.get("id", "")),
                publish_date=self._parse_weibo_date(mblog.get("created_at")),
                likes=optional_int(mblog.get("attitudes_count")),
                comments=optional_int(mblog.get("comments_count")),
                collects=None,  # 微博搜索API不返回收藏数
                shares=optional_int(mblog.get("reposts_count")),
                cover=next((item['url'] for item in media if item['kind']=='image' and item.get('url')),''),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "weibo_mobile_search_api",
                    "mid": mid,
                    "id": mblog.get("id"),
                    "is_long_text": mblog.get("isLongText") if type(mblog.get('isLongText')) is bool else None,
                    "source": mblog.get("source", ""),
                    "region_name": mblog.get("region_name", ""),
                    'body_state':'NATIVE_LONG_TEXT' if long_body else
                        'TRUNCATED_PLATFORM_TEXT' if mblog.get('isLongText') is True else
                        'PLATFORM_TEXT' if mblog.get('isLongText') is False else 'COMPLETENESS_NOT_OBSERVED',
                    'page_info':mblog.get('page_info'), 'pics':mblog.get('pics'),
                    'source_observation':mblog,
                    'media_hints':media, 'media_observation_state':'OBSERVED' if media else 'NOT_REPORTED',
                    'topic_list':mblog.get('topic_struct'),
                },
            )
        except Exception as exc:
            logger.warning("微博 mblog 解析失败: %s", exc)
            return None

    @staticmethod
    def _media_observations(post):
        """Preserve native media locators; this does not download media bytes."""
        from urllib.parse import urlsplit
        values = []
        def add(url,kind,native_id=None,locator=None):
            if isinstance(url,str) and url.startswith('//'):
                url='https:'+url
            try:
                parts=urlsplit(url) if isinstance(url,str) else None
                usable=(parts is not None and parts.scheme=='https' and parts.hostname
                        and not parts.username and not parts.password)
            except ValueError:
                usable=False
            item={'kind':kind,'url':url if usable else None,
                  'platform_media_id':str(native_id) if type(native_id) in (str,int) else None,
                  'native_locator':locator,'original_bytes_state':'NOT_ACQUIRED'}
            if item not in values:
                values.append(item)
        for index,picture in enumerate(post.get('pics') or []):
            if not isinstance(picture,dict):
                continue
            observed = picture.get('largest') or picture.get('large') or picture
            add(observed.get('url') if isinstance(observed,dict) else None,'image',
                picture.get('pid'),f'$.pics[{index}]')
            if picture.get('videoSrc'):
                add(picture['videoSrc'],'video',picture.get('pid'),f'$.pics[{index}].videoSrc')
        page = post.get('page_info') or {}
        native = page.get('media_info') or {}
        if isinstance(native,dict):
            for key in ('stream_url','stream_url_hd','h5_url','mp4_sd_url','mp4_hd_url'):
                if key in native:
                    add(native[key],'video',page.get('object_id'),f'$.page_info.media_info.{key}')
        return values

    @staticmethod
    def _post_target(value):
        from urllib.parse import urlsplit
        text=str(value or '').strip()
        if text.startswith(('http://','https://')):
            parts=urlsplit(text)
            if (parts.scheme!='https' or parts.hostname not in {'m.weibo.cn','weibo.com','www.weibo.com'}
                    or parts.username or parts.password or parts.port not in (None,443)):
                raise ValueError('WEIBO_SOURCE_TARGET_INVALID')
            segments=parts.path.strip('/').split('/')
            if len(segments)!=2 or (parts.hostname=='m.weibo.cn' and segments[0] not in {'status','detail'}):
                raise ValueError('WEIBO_SOURCE_TARGET_INVALID')
            text=segments[-1]
        if re.fullmatch(r'[A-Za-z0-9]{1,32}',text) is None:
            raise ValueError('WEIBO_SOURCE_TARGET_INVALID')
        return text

    @staticmethod
    def _clean_html(text: str) -> str:
        """去除微博正文中的 HTML 标签及多余空白。"""
        if not text:
            return ""
        # 去掉 <a> 标签但保留链接文本（话题/ @用户 等）
        text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text, flags=re.DOTALL)
        # 去掉其余 HTML 标签
        text = re.sub(r"<[^>]+>", "", text)
        # HTML 实体
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_weibo_date(raw: str) -> str:
        """微博 created_at → ISO 8601；无法解析返回空串（不臆造）。"""
        if not raw:
            return ""
        # 格式如 "Tue Sep 03 12:00:00 +0800 2024"
        for fmt in ("%a %b %d %H:%M:%S %z %Y", "%a %b %d %H:%M:%S %Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).isoformat()
            except (ValueError, TypeError):
                continue
        # 微博有时返回 "刚刚" / "x分钟前" / "x小时前" / "昨天 HH:MM"
        return ""

    # ── detail: 单条微博详情（statuses/show API）──
    def detail(self, mid: str, **kwargs) -> AdapterResult:
        if not mid or not str(mid).strip():
            return AdapterResult(success=False, error="mid 为空")
        try:
            mid=self._post_target(mid)
            if not self._cookie_ok():
                return AdapterResult(success=False, error="微博 cookie 缺失或无关键认证 cookie，请更新 data/weibo_cookies.json")
            cookie_string = to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")
            resp = requests.get(
                "https://m.weibo.cn/statuses/show",
                params={"id": str(mid).strip()},
                headers=self._get_headers(cookie_string),
                timeout=15,
            )
            data = resp.json()
            if data.get("ok") != 1:
                msg = data.get("msg", "") or str(data)
                if "登录" in msg or "login" in msg.lower():
                    return AdapterResult(success=False, error=f"微博登录失效: {msg}")
                return AdapterResult(success=False, error=f"微博详情失败: {msg}")
            mblog = data.get("data") or {}
            if mid not in {str(mblog.get(key) or '') for key in ('id','idstr','mid','bid')}:
                return AdapterResult(success=False,error='WEIBO_SOURCE_ID_MISMATCH')
            note = self._mblog_to_note(mblog)
            if note:
                return AdapterResult(success=True, notes=[note], raw_count=1)
            return AdapterResult(success=True, notes=[], raw_count=0)
        except Exception as exc:
            logger.exception("微博详情采集异常")
            return AdapterResult(success=False, error=f"微博详情异常: {exc}")

    # ── comments: 微博评论（comments/show API，只读）──
    def comments(self, mid: str, max_comments: int = 20, **kwargs) -> AdapterResult:
        if not mid or not str(mid).strip():
            return AdapterResult(success=False, error="mid 为空")
        cursor = kwargs.get('cursor')
        include_replies = kwargs.get('include_replies',False)
        reply_root, pending_roots, next_root, root_exhausted = None, [], None, None
        window_keys = {'item_offset','page_sha256'}
        def native_page(value):
            return (isinstance(value,dict) and set(value)-window_keys=={'max_id','max_id_type'}
                and isinstance(value['max_id'],str) and re.fullmatch(r'[0-9]{1,30}',value['max_id']) is not None
                and type(value['max_id_type']) is int and 0 <= value['max_id_type'] <= 3)
        if (type(max_comments) is not int or not 1 <= max_comments <= 20 or type(include_replies) is not bool):
            return AdapterResult(success=False,error='WEIBO_COMMENT_CURSOR_INVALID')
        try:
            validate_native_page_window_cursor(cursor)
            if isinstance(cursor,dict) and cursor.get('mode') == 'replies':
                validate_native_page_window_cursor(cursor.get('next_root'))
        except NativePageWindowError:
            return AdapterResult(success=False,error='WEIBO_NATIVE_CURSOR_WINDOW_INVALID')
        request_page = {key:value for key,value in cursor.items() if key not in window_keys} if isinstance(cursor,dict) else None
        if cursor is not None and not native_page(cursor):
            if (not isinstance(cursor,dict) or set(cursor)-window_keys!={'mode','root_id','page','pending_roots','next_root','root_exhausted'}
                    or cursor['mode']!='replies' or include_replies is not True
                    or not isinstance(cursor['root_id'],str) or re.fullmatch(r'[1-9][0-9]{0,29}',cursor['root_id']) is None
                    or not native_page(cursor['page']) or set(cursor['page']) != {'max_id','max_id_type'} or not isinstance(cursor['pending_roots'],list)
                    or len(cursor['pending_roots'])>20 or any(not isinstance(value,str)
                        or re.fullmatch(r'[1-9][0-9]{0,29}',value) is None for value in cursor['pending_roots'])
                    or cursor['next_root'] is not None and not native_page(cursor['next_root'])
                    or cursor['root_exhausted'] is not None and type(cursor['root_exhausted']) is not bool):
                return AdapterResult(success=False,error='WEIBO_COMMENT_CURSOR_INVALID')
            reply_root,request_page = cursor['root_id'],cursor['page']
            pending_roots,next_root,root_exhausted = cursor['pending_roots'],cursor['next_root'],cursor['root_exhausted']
        try:
            mid=self._post_target(mid)
            if not self._cookie_ok():
                return AdapterResult(success=False, error="微博 cookie 缺失或无关键认证 cookie，请更新 data/weibo_cookies.json")
            cookie_string = to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")
            resp = requests.get(
                'https://m.weibo.cn/comments/hotFlowChild' if reply_root else 'https://m.weibo.cn/comments/hotflow',
                params={**({'cid':reply_root} if reply_root else {'id':str(mid).strip(),'mid':str(mid).strip()}),
                        'max_id_type':0,**(request_page or {})},
                headers=self._get_headers(cookie_string),
                timeout=15,
            )
            data = resp.json()
            if data.get('ok') not in ({None,1} if reply_root else {1}):
                return AdapterResult(success=False, error=f"微博评论失败: {data.get('msg', str(data))}")
            payload = data if reply_root else data.get('data') or {}
            normal = payload.get('data')
            if not isinstance(normal,list):
                return AdapterResult(success=False,error='WEIBO_NATIVE_COMMENT_PAGE_NOT_OBSERVED')
            roots = payload.get('rootComment') or []
            if reply_root and any(str(value.get('id') or value.get('idstr')) != reply_root for value in roots):
                return AdapterResult(success=False,error='WEIBO_NATIVE_REPLY_PARENT_MISMATCH')
            window = native_page_window(normal,limit=max_comments,cursor=cursor,
                identities=[str(value.get('id') or value.get('idstr')) if isinstance(value,dict) else None for value in normal])
            selected = []
            for root in window['rows']:
                selected.append((root,reply_root))
                selected.extend((child,root.get('id') or root.get('idstr'))
                                for child in (root.get('comments') or []) if isinstance(child,dict))
            notes = []
            for c,parent in selected:
                user = c.get("user") or {}
                notes.append(self._make_note(
                    title="",
                    content=self._clean_html(c.get("text", "")),
                    url=f"https://m.weibo.cn/status/{mid}#cmt{c.get('id')}",
                    author=user.get("screen_name", ""),
                    author_id=str(user.get("id", "")),
                    publish_date=self._parse_weibo_date(c.get("created_at")),
                    likes=optional_int(c.get("like_count")),
                    comments=None,
                    collects=None,
                    shares=None,
                    cover="",
                    source_platform=self.platform_name,
                    raw_data={'engine':'weibo_hotflow_read_api','cid':c.get('id') or c.get('idstr'),'type':'comment',
                        'parent_content_id':str(mid).strip(),'parent_comment_id':parent or c.get('rootid'),
                        'reply_to_comment_id':c.get('reply_id') or (c.get('reply_comment') or {}).get('id'),
                        'reply_count':c.get('total_number'),'source_observation':c,
                        'media_hints':self._media_observations(c)},
                ))
            next_id, next_type = payload.get('max_id'),payload.get('max_id_type')
            known = (type(next_id) is int and next_id >= 0 or isinstance(next_id,str)
                     and next_id.isascii() and next_id.isdigit())
            complete = window['page_complete']
            next_cursor = {'max_id':str(next_id),'max_id_type':next_type} if (
                known and str(next_id) != '0' and type(next_type) is int and 0 <= next_type <= 3 and complete) else None
            if next_cursor == request_page:
                next_cursor = None
            base_cursor = {key:value for key,value in (cursor or {}).items() if key not in window_keys}
            if not complete:
                next_cursor = {**(base_cursor if reply_root else request_page or {'max_id':'0','max_id_type':0}), **window['next_window']}
            reply_totals_known = all(type(item.get('total_number')) is int and item['total_number']>=0 for item in window['rows'])
            replies_complete = all(item['total_number'] <= len(item.get('comments') or [])
                                   for item in window['rows']) if reply_totals_known else None
            page_exhausted = False if not complete else str(next_id)=='0' if known else None
            deferred = [str(item.get('id') or item.get('idstr')) for item in window['rows']
                if type(item.get('total_number')) is int and item['total_number']>len(item.get('comments') or [])
                and re.fullmatch(r'[1-9][0-9]{0,29}',str(item.get('id') or item.get('idstr')))]
            if reply_root:
                if next_cursor is not None and complete:
                    next_cursor = {**base_cursor,'page':next_cursor}
                elif page_exhausted is True and pending_roots:
                    next_cursor = {**base_cursor,'root_id':pending_roots[0],'pending_roots':pending_roots[1:],
                                   'page':{'max_id':'0','max_id_type':0}}
                elif page_exhausted is True:
                    next_cursor = next_root
                replies_complete = page_exhausted
                exhausted = (root_exhausted if page_exhausted is True and not pending_roots and next_root is None
                             else False if next_cursor else None)
            elif include_replies and deferred:
                next_cursor = {'mode':'replies','root_id':deferred[0],'page':{'max_id':'0','max_id_type':0},
                    'pending_roots':deferred[1:],'next_root':next_cursor,'root_exhausted':page_exhausted}
                exhausted = False
            else:
                exhausted = page_exhausted
            return AdapterResult(success=True,notes=notes,raw_count=len(notes),metadata={
                'pagination':{'request_cursor':cursor,'next_cursor':next_cursor,
                    'exhausted':exhausted,
                    'page_complete':complete, 'replies_complete':replies_complete,
                    **{key: window[key] for key in ('window_start','window_end','observed_native_rows','page_sha256','page_identity_basis')},
                    'reported_root_total':optional_int(payload.get('total_number')) if not reply_root else None,
                    'reported_reply_total':optional_int(payload.get('total_number')) if reply_root else None,
                    'coverage_scope':'PROVIDER_VISIBLE_HOTFLOW_COMMENT_AND_REPLY_PAGES',
                    'partial_reason':'REQUESTED_ROOT_LIMIT_REACHED' if not complete else
                        'NATIVE_REPLY_PAGES_NOT_OBSERVED' if replies_complete is False else
                        'NATIVE_NEXT_CURSOR_NOT_OBSERVED' if not known else None}})
        except NativePageWindowError as exc:
            return self._window_failure(exc,cursor)
        except Exception as exc:
            logger.exception("微博评论采集异常")
            return AdapterResult(success=False, error=f"微博评论异常: {exc}")

    # ── creator: 微博用户信息（container/getIndex INFO tab）──
    def author_posts(self, author_id, *, max_results=20, cursor=None, **kwargs):
        """One native author timeline page using the observed timeline container."""
        uid = str(author_id or '').strip()
        if re.fullmatch(r'[1-9][0-9]{0,24}',uid) is None:
            return AdapterResult(success=False,error='WEIBO_AUTHOR_ID_INVALID')
        if type(max_results) is not int or not 1 <= max_results <= 20:
            return AdapterResult(success=False,error='WEIBO_AUTHOR_PAGE_SIZE_INVALID')
        try:
            validate_native_page_window_cursor(cursor)
        except NativePageWindowError:
            return AdapterResult(success=False,error='WEIBO_NATIVE_CURSOR_WINDOW_INVALID')
        if cursor is not None and (not isinstance(cursor,dict) or set(cursor)-{'item_offset','page_sha256'}!={'container_id','since_id'}
                or not isinstance(cursor['container_id'],str) or re.fullmatch(r'[A-Za-z0-9_-]{1,128}',cursor['container_id']) is None
                or not (cursor['since_id'] is None and 'item_offset' in cursor
                    or isinstance(cursor['since_id'],str) and re.fullmatch(r'[0-9]{1,30}',cursor['since_id']) is not None)):
            return AdapterResult(success=False,error='WEIBO_AUTHOR_CURSOR_INVALID')
        try:
            if not self._cookie_ok():
                return AdapterResult(success=False,error='微博 cookie 缺失或无关键认证 cookie')
            cookie = to_cookie_string('weibo')
            if not cookie:
                return AdapterResult(success=False,error='微博 cookie 为空')
            if cursor is None:
                response = requests.get(self.SEARCH_URL,params={'type':'uid','value':uid},
                    headers=self._get_headers(cookie),timeout=15)
                data = response.json()
                if data.get('ok') != 1:
                    return AdapterResult(success=False,error='微博作者目录失败: '+str(data.get('msg') or 'PROVIDER_UNAVAILABLE'))
                payload = data.get('data') or {}
                user = payload.get('userInfo') or {}
                if str(user.get('id')) != uid:
                    return AdapterResult(success=False,error='WEIBO_AUTHOR_ID_MISMATCH')
                containers = [tab.get('containerid') for tab in (payload.get('tabsInfo') or {}).get('tabs') or []
                              if tab.get('tab_type') == 'weibo']
                if len(containers)!=1 or not isinstance(containers[0],str) or re.fullmatch(r'[A-Za-z0-9_-]{1,128}',containers[0]) is None:
                    return AdapterResult(success=False,error='WEIBO_NATIVE_AUTHOR_CONTAINER_NOT_OBSERVED')
                container, since = containers[0],None
            else:
                container,since = cursor['container_id'],cursor['since_id']
            response = requests.get(self.SEARCH_URL,params={'type':'uid','value':uid,'containerid':container,
                **({'since_id':since} if since is not None else {})},headers=self._get_headers(cookie),timeout=15)
            data = response.json()
            if data.get('ok') != 1:
                return AdapterResult(success=False,error='微博作者历史失败: '+str(data.get('msg') or 'PROVIDER_UNAVAILABLE'))
            payload = data.get('data') or {}
            posts = self._native_posts(payload.get('cards') or [])
            if any(str((post.get('user') or {}).get('id')) != uid for post in posts):
                return AdapterResult(success=False,error='WEIBO_AUTHOR_POST_OWNER_MISMATCH')
            window = native_page_window(posts,limit=max_results,cursor=cursor,
                identities=[str(post.get('mid') or post.get('id')) for post in posts])
            notes = [note for post in window['rows'] if (note:=self._mblog_to_note(post)) is not None]
            next_id = (payload.get('cardlistInfo') or {}).get('since_id')
            known = type(next_id) is int and next_id>=0 or isinstance(next_id,str) and next_id.isascii() and next_id.isdigit()
            complete = window['page_complete']
            next_cursor = {'container_id':container,'since_id':str(next_id)} if known and str(next_id)!='0' and complete else None
            if next_cursor is not None and str(next_id) == since:
                next_cursor = None
            if not complete:
                next_cursor = {'container_id':container,'since_id':since, **window['next_window']}
            return AdapterResult(success=True,notes=notes,raw_count=len(notes),metadata={
                'author_id':uid,'pagination':{'request_cursor':cursor,'next_cursor':next_cursor,
                    'exhausted':False if not complete else str(next_id)=='0' if known else None,
                    'page_complete':complete,'coverage_scope':'PROVIDER_VISIBLE_AUTHOR_TIMELINE',
                    **{key: window[key] for key in ('window_start','window_end','observed_native_rows','page_sha256','page_identity_basis')},
                    'partial_reason':'REQUESTED_ROOT_LIMIT_REACHED' if not complete else
                        'NATIVE_NEXT_CURSOR_NOT_OBSERVED' if not known else None}})
        except NativePageWindowError as exc:
            return self._window_failure(exc,cursor)
        except Exception as exc:
            return AdapterResult(success=False,error=f'微博作者历史异常: {type(exc).__name__}')

    @staticmethod
    def _window_failure(exc,cursor):
        return AdapterResult(success=False,raw_count=None,error='WEIBO_'+str(exc),metadata={
            'failure_class':str(exc),'pagination':{'request_cursor':cursor,'next_cursor':None,
                'exhausted':None,'page_complete':False,'resume_requires_fresh_page':True}})

    def creator(self, uid: str, **kwargs) -> AdapterResult:
        if not uid or not str(uid).strip():
            return AdapterResult(success=False, error="uid 为空")
        try:
            cookie_string = to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")
            containerid = f"230283{uid}_-_INFO"
            resp = requests.get(
                self.SEARCH_URL,
                params={"containerid": containerid},
                headers=self._get_headers(cookie_string),
                timeout=15,
            )
            data = resp.json()
            if data.get("ok") != 1:
                return AdapterResult(success=False, error=f"微博用户信息失败: {data.get('msg', str(data))}")
            cards = (data.get("data") or {}).get("cards") or []
            user_info = {}
            for card in cards:
                if card.get("card_type") == 11 and card.get("card_group"):
                    for item in card["card_group"]:
                        if item.get("card_type") == 10:
                            user_info = item.get("user") or {}
                            break
                if card.get("card_type") == 10:
                    user_info = card.get("user") or {}
                    break
            if not user_info:
                return AdapterResult(success=True, notes=[], raw_count=0)
            note = self._make_note(
                title=user_info.get("screen_name", ""),
                content=(user_info.get("description") or "").strip(),
                url=f"https://m.weibo.cn/u/{user_info.get('id', uid)}",
                author=user_info.get("screen_name", ""),
                author_id=str(user_info.get("id", "")),
                publish_date="",
                likes=None,
                comments=None,
                collects=None,
                shares=None,
                cover=user_info.get("avatar_hd", ""),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "weibo_user_info_api",
                    "uid": user_info.get("id"),
                    "followers": user_info.get("followers_count"),
                    "follow_count": user_info.get("follow_count"),
                    'content_count':user_info.get('statuses_count'),
                    "verified": user_info.get("verified"),
                    "verified_reason": user_info.get("verified_reason"),
                    "type": "creator",
                    'source_observation':user_info,
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        except Exception as exc:
            logger.exception("微博用户采集异常")
            return AdapterResult(success=False, error=f"微博用户异常: {exc}")
