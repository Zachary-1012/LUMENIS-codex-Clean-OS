"""
XHSCollector - 小红书采集器 V2
继承PlatformCollector基类
只负责采集，不做主体过滤（由系统层pipeline处理）
"""
import os
import re
import asyncio
from typing import List, Optional, Dict
from datetime import datetime

from ..base import PlatformCollector, RawNote, RawComment
from .client import XHSClient


class XHSCollector(PlatformCollector):
    """小红书采集器"""
    
    def __init__(self, cookie: str = "", config: Optional[Dict] = None):
        super().__init__(config)
        self.client = XHSClient(cookie=cookie)
        self.platform = "xiaohongshu"
        # 新账号保护：前3次极轻量
        self._collect_count = 0
        self._max_scroll_light = 2  # 极轻量模式滚动次数
    
    async def search(self, keyword: str, page: int = 1, 
                     max_scroll: int = 3) -> List[RawNote]:
        """
        搜索笔记
        新账号前3次强制极轻量模式
        """
        # 新账号保护
        if self._collect_count < 3:
            max_scroll = min(max_scroll, self._max_scroll_light)
            print(f"[XHSCollector] 新账号保护模式（第{self._collect_count+1}次），max_scroll={max_scroll}")
        
        all_notes = []
        
        for scroll_page in range(1, max_scroll + 1):
            try:
                result = await self.client.search_notes(
                    keyword=keyword,
                    page=scroll_page,
                    page_size=20
                )
                
                if not result or result.get("code") != 0:
                    print(f"[XHSCollector] 搜索第{scroll_page}页失败")
                    break
                
                data = result.get("data", {})
                items = data.get("items", [])
                
                for item in items:
                    note = self._parse_search_item(item, keyword)
                    if note:
                        all_notes.append(note)
                
                # 检查是否还有更多
                has_more = data.get("has_more", False)
                if not has_more:
                    break
                    
            except Exception as e:
                print(f"[XHSCollector] 搜索第{scroll_page}页异常: {e}")
                break
        
        self._collect_count += 1
        print(f"[XHSCollector] 关键词'{keyword}'采集到{len(all_notes)}条笔记")
        return all_notes
    
    def _parse_search_item(self, item: Dict, keyword: str) -> Optional[RawNote]:
        """解析搜索结果项"""
        try:
            note_data = item.get("note_card", item)
            note_id = note_data.get("note_id", "")
            if not note_id:
                return None
            
            title = note_data.get("display_title", note_data.get("title", ""))
            user = note_data.get("user", {})
            interact_info = note_data.get("interact_info", {})
            
            # 发布时间
            time_info = note_data.get("time", "")
            publish_date = ""
            if time_info:
                try:
                    # 时间戳转换
                    ts = int(time_info) / 1000
                    publish_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    publish_date = str(time_info)
            
            xsec_token = note_data.get("xsec_token", "")
            url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"
            
            return RawNote(
                note_id=note_id,
                title=title,
                content="",  # 搜索结果没有正文，需要get_detail获取
                author_id=user.get("user_id", ""),
                author_nickname=user.get("nickname", ""),
                likes=int(interact_info.get("liked_count", "0") or 0),
                comments=int(interact_info.get("comment_count", "0") or 0),
                collects=int(interact_info.get("collected_count", "0") or 0),
                shares=int(interact_info.get("share_count", "0") or 0),
                publish_date=publish_date,
                url=url,
                xsec_token=xsec_token,
                source_platform=self.platform,
                raw_data=note_data
            )
        except Exception as e:
            print(f"[XHSCollector] 解析搜索项失败: {e}")
            return None
    
    async def get_detail(self, note_id: str, xsec_token: str = "") -> Optional[RawNote]:
        """获取笔记详情（正文等）"""
        try:
            result = await self.client.get_note(note_id, xsec_token)
            
            if not result or result.get("code") != 0:
                return None
            
            data = result.get("data", {})
            items = data.get("items", [])
            
            if not items:
                return None
            
            note_data = items[0].get("note_card", items[0])
            
            # 解析正文
            desc = note_data.get("desc", "")
            title = note_data.get("title", note_data.get("display_title", ""))
            
            return RawNote(
                note_id=note_id,
                title=title,
                content=desc,
                author_id=note_data.get("user", {}).get("user_id", ""),
                author_nickname=note_data.get("user", {}).get("nickname", ""),
                likes=int(note_data.get("interact_info", {}).get("liked_count", 0) or 0),
                comments=int(note_data.get("interact_info", {}).get("comment_count", 0) or 0),
                collects=int(note_data.get("interact_info", {}).get("collected_count", 0) or 0),
                xsec_token=xsec_token,
                source_platform=self.platform,
                raw_data=note_data
            )
            
        except Exception as e:
            print(f"[XHSCollector] 获取笔记详情失败: {e}")
            return None
    
    async def get_comments(self, note_id: str, xsec_token: str = "",
                            cursor: str = "") -> tuple:
        """获取评论（单页）"""
        comments_data, has_more, next_cursor = await self.client.get_comments(
            note_id, xsec_token, cursor
        )
        
        raw_comments = []
        for c in comments_data:
            raw_comment = self._parse_comment(c, note_id)
            if raw_comment:
                raw_comments.append(raw_comment)
        
        return raw_comments, has_more, next_cursor
    
    def _parse_comment(self, comment_data: Dict, note_id: str) -> Optional[RawComment]:
        """解析评论数据"""
        try:
            comment_id = comment_data.get("id", comment_data.get("comment_id", ""))
            if not comment_id:
                return None
            
            user_info = comment_data.get("user_info", {})
            create_time = comment_data.get("create_time", "")
            publish_time = ""
            if create_time:
                try:
                    ts = int(create_time) / 1000
                    publish_time = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    publish_time = str(create_time)
            
            # 解析子评论
            sub_comments = []
            sub_comment_list = comment_data.get("sub_comments", [])
            for sc in sub_comment_list:
                sub_raw = self._parse_comment(sc, note_id)
                if sub_raw:
                    sub_raw.parent_comment_id = comment_id
                    sub_comments.append(sub_raw)
            
            return RawComment(
                comment_id=comment_id,
                note_id=note_id,
                content=comment_data.get("content", ""),
                author_id=user_info.get("user_id", ""),
                author_nickname=user_info.get("nickname", ""),
                likes=int(comment_data.get("like_count", 0) or 0),
                publish_time=publish_time,
                sub_comments=sub_comments,
                raw_data=comment_data
            )
        except Exception as e:
            print(f"[XHSCollector] 解析评论失败: {e}")
            return None
    
    async def check_login(self) -> bool:
        """检查登录状态"""
        try:
            # 通过搜索接口判断是否登录
            result = await self.client.search_notes("test", page=1, page_size=1)
            if result and result.get("code") == 0:
                self._is_logged_in = True
                return True
            self._is_logged_in = False
            return False
        except:
            self._is_logged_in = False
            return False
    
    def update_cookie(self, cookie: str):
        """更新Cookie"""
        self.client.update_cookie(cookie)
    
    async def close(self):
        """关闭采集器"""
        await self.client.close()
