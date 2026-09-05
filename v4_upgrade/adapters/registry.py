"""
适配器注册中心
统一管理所有采集适配器，支持动态注册、按平台获取、状态查询
"""
from typing import Dict, List, Optional
from .base import BaseAdapter, AdapterResult


class AdapterRegistry:
    """适配器注册中心（单例）"""
    _instance = None
    _adapters: Dict[str, BaseAdapter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, adapter: BaseAdapter):
        """注册适配器"""
        self._adapters[adapter.platform_name] = adapter

    def get(self, platform: str) -> Optional[BaseAdapter]:
        """按平台名获取适配器"""
        return self._adapters.get(platform)

    def list_platforms(self) -> List[str]:
        """列出所有已注册平台"""
        return list(self._adapters.keys())

    def get_all_status(self) -> List[dict]:
        """获取所有适配器状态"""
        return [a.get_status() for a in self._adapters.values()]

    def search_all(self, keyword: str, max_results: int = 20,
                   platforms: List[str] = None) -> Dict[str, AdapterResult]:
        """
        多平台并行搜索
        platforms: 指定平台，None表示全部
        """
        targets = platforms or self.list_platforms()
        results = {}
        for p in targets:
            adapter = self.get(p)
            if adapter:
                results[p] = adapter.collect(keyword, max_results)
        return results

    def search_all_merged(self, keyword: str, max_results: int = 20,
                          platforms: List[str] = None) -> list:
        """多平台搜索并合并结果（去重），仅返回合并后的笔记"""
        return self.search_all_with_status(keyword, max_results, platforms)[0]

    def search_all_with_status(self, keyword: str, max_results: int = 20,
                               platforms: List[str] = None):
        """多平台搜索，返回 (合并去重笔记, 每平台状态)。
        失败/0条平台绝不静默丢弃，状态如实回传（SUCCESS/EMPTY/FAIL 由调用方判定）。"""
        targets = platforms or self.list_platforms()
        merged, seen_urls, status = [], set(), []
        for p in targets:
            adapter = self.get(p)
            if not adapter:
                status.append({"platform": p, "display": p, "success": False,
                               "count": 0, "error": "适配器未注册", "duration": 0})
                continue
            result = adapter.collect(keyword, max_results)
            status.append({
                "platform": p,
                "display": adapter.platform_display,
                "success": result.success,
                "count": len(result.notes),
                "state": "SUCCESS" if (result.success and result.notes) else
                         ("EMPTY" if result.success else "FAIL"),
                "error": result.error,
                "duration": round(result.duration_seconds, 2),
            })
            if not result.success:
                continue
            for note in result.notes:
                if note.url and note.url in seen_urls:
                    continue
                if note.url:
                    seen_urls.add(note.url)
                merged.append(note)
        return merged, status


# 全局注册中心实例
registry = AdapterRegistry()


def register_default_adapters():
    """注册所有默认适配器（按需导入，避免依赖缺失）"""
    from .douyin import DouyinAdapter
    from .instagram import InstagramAdapter
    from .bilibili import BilibiliAdapter
    from .weibo import WeiboAdapter
    from .zhihu import ZhihuAdapter
    from .facebook import FacebookAdapter
    from .x_platform import XAdapter
    from .baidu_search import BaiduSearchAdapter
    from .bing_search import BingSearchAdapter
    from .sogou_search import SogouSearchAdapter
    from .google import GoogleAdapter
    from .sogou_wechat import SogouWechatAdapter
    from .dianping import DianpingAdapter
    from .doubao_search import DoubaoSearchAdapter
    from .smzdm import SmzdmAdapter

    for cls in [DouyinAdapter, InstagramAdapter, BilibiliAdapter, WeiboAdapter, ZhihuAdapter,
                FacebookAdapter, XAdapter, BaiduSearchAdapter,
                BingSearchAdapter, SogouSearchAdapter, GoogleAdapter, SogouWechatAdapter,
                DianpingAdapter, DoubaoSearchAdapter, SmzdmAdapter]:
        try:
            registry.register(cls())
        except Exception as e:
            print(f"注册适配器 {cls.__name__} 失败: {e}")
