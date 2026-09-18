"""
XHS App Topic Adapter（V3.0 P1 新增）
归属：Z-Brand Core / Data Acquisition Layer / Platform Adapter
目标：补齐话题发现 + 话题浏览量/讨论量（App端专属数据）
约束：
  1. 不修改现有Web采集主链路
  2. Adapter化接入，复用BasePlatformAdapter接口
  3. 数据统一进入Content Center
  4. 复用事件中心
  5. 保留主体过滤规则（subject_rules.py）
  6. 增加source字段区分web/app
  7. Feature Flag控制上线（XHS_APP_TOPIC_ENABLED）

注意：小红书App端话题API需要逆向或App端抓包获取。
当前版本为Adapter框架 + 数据源预留，默认Feature Flag关闭。
后续接入App端API后，只需实现_topic_metrics_from_app()方法。
"""
from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, List, Optional

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus


# Feature Flag: 默认关闭，需在.env或环境变量中设置 XHS_APP_TOPIC_ENABLED=true
FEATURE_FLAG = os.getenv('XHS_APP_TOPIC_ENABLED', 'false').lower() == 'true'

# 数据源标识
SOURCE_APP = 'xhs_app'
SOURCE_WEB = 'xhs_web'


class XHSAppTopicAdapter(BasePlatformAdapter):
    """小红书App端话题适配器

    职责：
    - 话题发现（关键词→相关话题）
    - 话题指标获取（浏览量/讨论量，App端专属）
    - 话题下笔记采集（复用Web端采集逻辑）

    不负责：
    - 主体过滤（由core层subject_rules处理）
    - 事件聚合（由event_center处理）
    - 风险评分（由risk_engine处理）
    """

    platform = "xhs_app_topic"
    enabled = FEATURE_FLAG
    monitor_priority = "topic"

    def __init__(self, *, session_manager: Any = None, proxy_manager: Any = None,
                 cdp_port: int = 9222, app_api_endpoint: Optional[str] = None, **_: Any) -> None:
        super().__init__(session_manager=session_manager, proxy_manager=proxy_manager)
        self.cdp_port = cdp_port
        self.app_api_endpoint = app_api_endpoint or os.getenv('XHS_APP_API_ENDPOINT', '')
        self._last_health_check = 0.0
        self._health_cache: Optional[CollectionResult] = None

    # ── 核心接口实现 ──────────────────────────────────────────

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        """关键词搜索 → 发现相关话题

        返回的items中每个话题包含：
        - topic_name: 话题名
        - topic_id: 话题ID（如有）
        - browse_count: 浏览量（App端，如可获取）
        - discussion_count: 讨论量（App端，如可获取）
        - note_count: 笔记数
        - source: 'xhs_app'
        """
        if not self.enabled:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message="XHS App Topic Adapter Feature Flag未开启（XHS_APP_TOPIC_ENABLED=false）",
            )

        try:
            # 优先从App端API获取话题列表
            topics = self._discover_topics_from_app(keyword)
            if topics:
                return CollectionResult(
                    status=CollectionStatus.SUCCESS,
                    platform=self.platform,
                    items=topics,
                    raw_count=len(topics),
                    new_count=len(topics),
                    message=f"从App端发现{len(topics)}个话题",
                    metadata={'source': SOURCE_APP, 'keyword': keyword},
                )

            # App端API不可用时，返回空结果（不伪造，不回退到Web端）
            return CollectionResult(
                status=CollectionStatus.NO_NEW_DATA,
                platform=self.platform,
                items=[],
                message="App端话题API暂不可用，待接入后获取",
                metadata={'source': SOURCE_APP, 'keyword': keyword, 'note': 'Adapter框架已就绪，App API待接入'},
            )

        except Exception as e:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=f"话题发现失败: {str(e)}",
                metadata={'source': SOURCE_APP, 'keyword': keyword},
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        """获取话题详情（浏览量/讨论量/笔记列表）

        content_id: 话题名或话题ID
        """
        if not self.enabled:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message="Feature Flag未开启",
            )

        try:
            metrics = self._topic_metrics_from_app(content_id)
            if metrics:
                return CollectionResult(
                    status=CollectionStatus.SUCCESS,
                    platform=self.platform,
                    items=[metrics],
                    raw_count=1,
                    new_count=1,
                    message=f"获取话题{content_id}指标成功",
                    metadata={'source': SOURCE_APP, 'topic': content_id},
                )

            return CollectionResult(
                status=CollectionStatus.NO_NEW_DATA,
                platform=self.platform,
                items=[],
                message=f"话题{content_id}的App端指标暂不可用",
                metadata={'source': SOURCE_APP, 'topic': content_id},
            )

        except Exception as e:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=f"话题详情获取失败: {str(e)}",
            )

    def health_check(self, **_: Any) -> CollectionResult:
        """健康检查：App端API可用性 + CDP连接状态"""
        now = time.time()
        if now - self._last_health_check < 30 and self._health_cache:
            return self._health_cache

        checks = {
            'feature_flag': self.enabled,
            'app_api_configured': bool(self.app_api_endpoint),
            'cdp_port': self.cdp_port,
        }

        if not self.enabled:
            status = CollectionStatus.COLLECT_ERROR
            message = "Feature Flag未开启"
        elif not self.app_api_endpoint:
            status = CollectionStatus.NO_NEW_DATA
            message = "App端API未配置（XHS_APP_API_ENDPOINT），Adapter框架就绪待接入"
        else:
            status = CollectionStatus.SUCCESS
            message = "App端API已配置"

        result = CollectionResult(
            status=status,
            platform=self.platform,
            message=message,
            metadata=checks,
        )
        self._health_cache = result
        self._last_health_check = now
        return result

    # ── App端API接入点（待实现） ──────────────────────────────

    def _discover_topics_from_app(self, keyword: str) -> List[Dict[str, Any]]:
        """从App端API发现相关话题

        待实现：需要小红书App端API endpoint和签名算法
        返回格式：
        [
            {
                'topic_name': '#话题名',
                'topic_id': 'xxx',
                'browse_count': 123456,
                'discussion_count': 789,
                'note_count': 1000,
                'source': 'xhs_app',
            },
            ...
        ]
        """
        # 预留接入点：后续填入App端API调用逻辑
        # 注意：不得伪造数据，API不可用时返回空列表
        return []

    def _topic_metrics_from_app(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """从App端API获取话题指标（浏览量/讨论量）

        待实现：需要小红书App端API endpoint和签名算法
        返回格式：
        {
            'topic_name': '#话题名',
            'topic_id': topic_id,
            'browse_count': 123456,
            'discussion_count': 789,
            'note_count': 1000,
            'source': 'xhs_app',
            'captured_at': '2026-08-31T00:00:00Z',
        }
        """
        # 预留接入点：后续填入App端API调用逻辑
        # 注意：不得伪造数据，API不可用时返回None
        return None

    # ── 工具方法 ──────────────────────────────────────────────

    @staticmethod
    def enrich_note_with_source(note: Dict[str, Any], source: str = SOURCE_APP) -> Dict[str, Any]:
        """为笔记数据增加来源字段（区分web/app）

        V3.0要求：增加来源字段区分web/app
        """
        note['source'] = source
        note['data_source'] = source
        return note

    @staticmethod
    def is_enabled() -> bool:
        """检查Feature Flag是否开启"""
        return FEATURE_FLAG


# 自动注册到Adapter Registry
from .registry import register_adapter  # noqa: E402
register_adapter("xhs_app_topic", XHSAppTopicAdapter)
