"""
XHSClient - 小红书HTTP请求层（独立）
只负责API请求，不负责登录管理和主体过滤
包含评论分页获取
"""
import os
import json
import asyncio
import hashlib
import re
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from urllib.parse import quote


class XHSClient:
    """小红书API客户端"""
    
    BASE_URL = "https://edith.xiaohongshu.com"
    WEB_URL = "https://www.xiaohongshu.com"
    
    def __init__(self, cookie: str = "", user_agent: str = ""):
        self.cookie = cookie
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self._session = None
        self._request_count = 0
        self._last_request_time = 0
    
    def _get_headers(self) -> Dict:
        """获取请求头"""
        return {
            "Cookie": self.cookie,
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": self.WEB_URL,
            "Referer": f"{self.WEB_URL}/",
            "Content-Type": "application/json;charset=UTF-8",
        }
    
    async def _rate_limit(self):
        """请求频率限制，防止封号"""
        now = datetime.now().timestamp()
        elapsed = now - self._last_request_time
        # 动态间隔：根据请求次数调整
        if self._request_count < 3:
            min_interval = 2.0  # 新账号前3次极轻量
        elif self._request_count < 10:
            min_interval = 3.0
        else:
            min_interval = 4.0
        
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        
        self._last_request_time = datetime.now().timestamp()
        self._request_count += 1
    
    async def request(self, method: str, url: str, 
                      params: Optional[Dict] = None,
                      data: Optional[Dict] = None) -> Optional[Dict]:
        """统一请求入口。

        该 V2 适配器依赖平台私有接口/签名契约，研究边界已将其排除在
        生产采集主链之外；保留代码用于历史解析与回放，但默认禁止真实请求。
        """
        raise RuntimeError('XHS 私有接口适配器已标记为非生产路径，禁止发起真实请求')
        await self._rate_limit()
        
        try:
            import aiohttp
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            async with self._session.request(
                method, url,
                headers=self._get_headers(),
                params=params,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"[XHSClient] 请求失败: {resp.status} {url}")
                    return None
        except ImportError:
            # 没有aiohttp，用requests同步
            import requests
            try:
                resp = requests.request(
                    method, url,
                    headers=self._get_headers(),
                    params=params,
                    json=data,
                    timeout=30
                )
                if resp.status_code == 200:
                    return resp.json()
                else:
                    print(f"[XHSClient] 请求失败: {resp.status}")
                    return None
            except Exception as e:
                print(f"[XHSClient] 请求异常: {e}")
                return None
        except Exception as e:
            print(f"[XHSClient] 请求异常: {e}")
            return None
    
    async def search_notes(self, keyword: str, page: int = 1,
                            page_size: int = 20, sort: str = "general") -> Optional[Dict]:
        """搜索笔记"""
        url = f"{self.BASE_URL}/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "note_type": 0,
        }
        return await self.request("POST", url, data=data)
    
    async def get_note(self, note_id: str, xsec_token: str = "") -> Optional[Dict]:
        """获取笔记详情"""
        url = f"{self.BASE_URL}/api/sns/web/v1/feed"
        data = {
            "source_note_id": note_id,
            "xsec_token": xsec_token,
            "image_formats": ["jpg", "webp"],
        }
        return await self.request("POST", url, data=data)
    
    async def get_comments(self, note_id: str, xsec_token: str = "",
                            cursor: str = "", page_size: int = 20) -> Tuple[List, bool, str]:
        """
        获取评论（单页）
        返回: (comments_list, has_more, next_cursor)
        """
        url = f"{self.BASE_URL}/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "xsec_token": xsec_token,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif",
        }
        
        result = await self.request("GET", url, params=params)
        
        if not result or result.get("code") != 0:
            return [], False, ""
        
        data = result.get("data", {})
        comments = data.get("comments", [])
        has_more = data.get("has_more", False)
        next_cursor = data.get("cursor", "")
        
        return comments, has_more, next_cursor
    
    async def get_all_comments(self, note_id: str, xsec_token: str = "",
                                max_pages: int = 3) -> List:
        """
        获取全部评论（分页获取）
        max_pages: 最大获取页数，防止过度采集被封号
        """
        all_comments = []
        cursor = ""
        
        for page in range(max_pages):
            try:
                comments, has_more, next_cursor = await self.get_comments(
                    note_id, xsec_token, cursor
                )
                all_comments.extend(comments)
                
                if not has_more or not next_cursor:
                    break
                cursor = next_cursor
                
            except Exception as e:
                print(f"[XHSClient] 获取评论第{page+1}页失败: {e}")
                break
        
        return all_comments
    
    async def get_sub_comments(self, note_id: str, comment_id: str,
                                 xsec_token: str = "", cursor: str = "",
                                 page_size: int = 20) -> Tuple[List, bool, str]:
        """获取子评论（单页）"""
        url = f"{self.BASE_URL}/api/sns/web/v2/comment/sub/page"
        params = {
            "note_id": note_id,
            "comment_id": comment_id,
            "xsec_token": xsec_token,
            "cursor": cursor,
            "image_formats": "jpg,webp,avif",
        }
        
        result = await self.request("GET", url, params=params)
        
        if not result or result.get("code") != 0:
            return [], False, ""
        
        data = result.get("data", {})
        comments = data.get("comments", [])
        has_more = data.get("has_more", False)
        next_cursor = data.get("cursor", "")
        
        return comments, has_more, next_cursor
    
    def update_cookie(self, cookie: str):
        """更新Cookie"""
        self.cookie = cookie
    
    async def close(self):
        """关闭会话"""
        if self._session:
            await self._session.close()
            self._session = None
