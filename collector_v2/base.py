"""
PlatformCollector 基类
所有平台采集器必须继承此类，实现统一接口
主体过滤不放进爬虫，由系统层判断
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawNote:
    """原始笔记数据（采集器输出，未经过主体过滤）"""
    note_id: str
    title: str = ""
    content: str = ""
    author_id: str = ""
    author_nickname: str = ""
    likes: int = 0
    comments: int = 0
    collects: int = 0
    shares: int = 0
    publish_date: str = ""
    url: str = ""
    xsec_token: str = ""
    source_platform: str = ""
    raw_data: Dict = field(default_factory=dict)
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RawComment:
    """原始评论数据"""
    comment_id: str
    note_id: str
    content: str = ""
    author_id: str = ""
    author_nickname: str = ""
    likes: int = 0
    publish_time: str = ""
    parent_comment_id: str = ""
    sub_comments: List['RawComment'] = field(default_factory=list)
    raw_data: Dict = field(default_factory=dict)


class PlatformCollector(ABC):
    """平台采集器基类"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._is_logged_in = False
        self._session = None
    
    @abstractmethod
    async def search(self, keyword: str, page: int = 1, max_scroll: int = 3) -> List[RawNote]:
        """搜索笔记"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_detail(self, note_id: str, xsec_token: str = "") -> Optional[RawNote]:
        """获取笔记详情（正文等）"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_comments(self, note_id: str, xsec_token: str = "", 
                           cursor: str = "") -> tuple:
        """
        获取评论（单页）
        返回: (comments_list, has_more, next_cursor)
        """
        raise NotImplementedError
    
    async def get_all_comments(self, note_id: str, xsec_token: str = "",
                                max_pages: int = 3) -> List[RawComment]:
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
                # 分页间隔，降低封号风险
                import asyncio
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"[Collector] 获取评论第{page+1}页失败: {e}")
                break
        return all_comments
    
    @abstractmethod
    async def check_login(self) -> bool:
        """检查登录状态"""
        raise NotImplementedError
    
    @abstractmethod
    async def close(self):
        """关闭采集器，释放资源"""
        pass
    
    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in
