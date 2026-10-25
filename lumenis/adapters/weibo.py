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

    def search(self, keyword: str, max_results: int = 20, *, cursor=None) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        if type(max_results) is not int or not 1 <= max_results <= 20:
            return AdapterResult(success=False,error='WEIBO_PAGE_SIZE_INVALID')
        if cursor is not None and (not isinstance(cursor,dict) or set(cursor) not in ({'page'},{'since_id'})
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
            params = {"containerid": containerid,'page_type':'searchall',
                      **(cursor if cursor is not None else {'page':1})}

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
            notes = []
            for card in cards:
                mblog = card.get("mblog")
                if not mblog:
                    continue
                note = self._mblog_to_note(mblog)
                if note:
                    notes.append(note)
                if len(notes) >= max_results:
                    break

            info = (data.get('data') or {}).get('cardlistInfo') or {}
            next_id = info.get('since_id')
            known = type(next_id) is int and next_id >= 0 or isinstance(next_id,str) and next_id.isascii() and next_id.isdigit()
            next_cursor = {'since_id':str(next_id)} if known and str(next_id) != '0' else None
            if next_cursor == cursor:
                next_cursor = None
            return AdapterResult(success=True,notes=notes,raw_count=len(notes),metadata={
                'pagination':{'request_cursor':cursor,'next_cursor':next_cursor,
                    'exhausted':str(next_id)=='0' if known else True if info.get('total') == 0 else None,
                    'reported_total':optional_int(info.get('total')), 'page_complete':len(notes) >= len([
                        card for card in cards if isinstance(card,dict) and card.get('mblog')]),
                    'coverage_scope':'PROVIDER_VISIBLE_WEIBO_SEARCH_PAGE'}})

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
                cover="",
                source_platform=self.platform_name,
                raw_data={
                    "engine": "weibo_mobile_search_api",
                    "mid": mid,
                    "id": mblog.get("id"),
                    "is_long_text": mblog.get("isLongText", False),
                    "source": mblog.get("source", ""),
                    "region_name": mblog.get("region_name", ""),
                    'body_state':'NATIVE_LONG_TEXT' if long_body else
                        'TRUNCATED_PLATFORM_TEXT' if mblog.get('isLongText') is True else 'PLATFORM_TEXT',
                    'page_info':mblog.get('page_info'), 'pics':mblog.get('pics'),
                    'source_observation':mblog,
                },
            )
        except Exception as exc:
            logger.warning("微博 mblog 解析失败: %s", exc)
            return None

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
        if (type(max_comments) is not int or not 1 <= max_comments <= 20
                or cursor is not None and (not isinstance(cursor,dict) or set(cursor)!={'max_id','max_id_type'}
                    or not isinstance(cursor['max_id'],str) or re.fullmatch(r'[0-9]{1,30}',cursor['max_id']) is None
                    or type(cursor['max_id_type']) is not int or not 0 <= cursor['max_id_type'] <= 3)):
            return AdapterResult(success=False,error='WEIBO_COMMENT_CURSOR_INVALID')
        try:
            if not self._cookie_ok():
                return AdapterResult(success=False, error="微博 cookie 缺失或无关键认证 cookie，请更新 data/weibo_cookies.json")
            cookie_string = to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")
            resp = requests.get(
                "https://m.weibo.cn/comments/hotflow",
                params={"id":str(mid).strip(),'mid':str(mid).strip(),'max_id_type':0,
                        **(cursor or {})},
                headers=self._get_headers(cookie_string),
                timeout=15,
            )
            data = resp.json()
            if data.get("ok") != 1:
                return AdapterResult(success=False, error=f"微博评论失败: {data.get('msg', str(data))}")
            payload = data.get('data') or {}
            normal = payload.get('data') or []
            selected = []
            for root in normal[:max_comments]:
                selected.append((root,None))
                selected.extend((child,root.get('id')) for child in root.get('comments') or [])
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
                    raw_data={'engine':'weibo_hotflow_read_api','cid':c.get('id'),'type':'comment',
                        'parent_content_id':str(mid).strip(),'parent_comment_id':parent or c.get('rootid'),
                        'reply_to_comment_id':c.get('reply_id') or (c.get('reply_comment') or {}).get('id'),
                        'reply_count':c.get('total_number'),'source_observation':c},
                ))
            next_id, next_type = payload.get('max_id'),payload.get('max_id_type')
            known = (type(next_id) is int and next_id >= 0 or isinstance(next_id,str)
                     and next_id.isascii() and next_id.isdigit())
            complete = len(normal) <= max_comments
            next_cursor = {'max_id':str(next_id),'max_id_type':next_type} if (
                known and str(next_id) != '0' and type(next_type) is int and 0 <= next_type <= 3 and complete) else None
            reply_totals_known = all(type(item.get('total_number')) is int and item['total_number']>=0 for item in normal[:max_comments])
            replies_complete = all(item['total_number'] <= len(item.get('comments') or [])
                                   for item in normal[:max_comments]) if reply_totals_known else None
            return AdapterResult(success=True,notes=notes,raw_count=len(notes),metadata={
                'pagination':{'request_cursor':cursor,'next_cursor':next_cursor,
                    'exhausted':str(next_id)=='0' if known and complete else None,
                    'page_complete':complete, 'replies_complete':replies_complete,
                    'coverage_scope':'PROVIDER_VISIBLE_HOTFLOW_ROOT_PAGE_WITH_RETURNED_REPLIES',
                    'partial_reason':'REQUESTED_ROOT_LIMIT_REACHED' if not complete else
                        'NATIVE_REPLY_PAGES_NOT_OBSERVED' if replies_complete is False else
                        'NATIVE_NEXT_CURSOR_NOT_OBSERVED' if not known else None}})
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
        if cursor is not None and (not isinstance(cursor,dict) or set(cursor)!={'container_id','since_id'}
                or not isinstance(cursor['container_id'],str) or re.fullmatch(r'[A-Za-z0-9_-]{1,128}',cursor['container_id']) is None
                or not isinstance(cursor['since_id'],str) or re.fullmatch(r'[0-9]{1,30}',cursor['since_id']) is None):
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
            posts = [card['mblog'] for card in payload.get('cards') or [] if isinstance(card,dict) and isinstance(card.get('mblog'),dict)]
            if any(str((post.get('user') or {}).get('id')) != uid for post in posts):
                return AdapterResult(success=False,error='WEIBO_AUTHOR_POST_OWNER_MISMATCH')
            notes = [note for post in posts[:max_results] if (note:=self._mblog_to_note(post)) is not None]
            next_id = (payload.get('cardlistInfo') or {}).get('since_id')
            known = type(next_id) is int and next_id>=0 or isinstance(next_id,str) and next_id.isascii() and next_id.isdigit()
            complete = len(posts)<=max_results
            next_cursor = {'container_id':container,'since_id':str(next_id)} if known and str(next_id)!='0' and complete else None
            return AdapterResult(success=True,notes=notes,raw_count=len(notes),metadata={
                'author_id':uid,'pagination':{'request_cursor':cursor,'next_cursor':next_cursor,
                    'exhausted':str(next_id)=='0' if known and complete else None,
                    'page_complete':complete,'coverage_scope':'PROVIDER_VISIBLE_AUTHOR_TIMELINE',
                    'partial_reason':'REQUESTED_ROOT_LIMIT_REACHED' if not complete else
                        'NATIVE_NEXT_CURSOR_NOT_OBSERVED' if not known else None}})
        except Exception as exc:
            return AdapterResult(success=False,error=f'微博作者历史异常: {type(exc).__name__}')

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
