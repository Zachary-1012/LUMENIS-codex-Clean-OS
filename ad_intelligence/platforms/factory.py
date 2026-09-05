# -*- coding: utf-8 -*-
"""
广告平台采集器工厂
==================
统一创建和管理各平台广告数据采集器。
按真实商业属性自动选择采集路径（API / 浏览器只读 / 不可用）。
"""
from __future__ import annotations
from typing import Dict, Optional, Any
from .ocean_engine import OceanEngineCollector, OceanEngineConfig
from .jiguang import JiguangCollector, JiguangConfig
from .meta_ads import MetaAdsCollector, MetaAdsConfig
from .x_ads import XAdsCollector, XAdsConfig
from ..platform_registry import get_platform_profile, check_platform_readiness


class AdCollectorFactory:
    """广告平台采集器工厂。"""

    _collectors: Dict[str, Any] = {}

    @classmethod
    def get_collector(cls, platform: str) -> Optional[Any]:
        """获取平台采集器实例（单例）。"""
        platform = platform.strip().lower()
        if platform in cls._collectors:
            return cls._collectors[platform]

        collector = None
        if platform in ("douyin", "ocean_engine"):
            collector = OceanEngineCollector(cls._load_ocean_config())
        elif platform in ("xhs", "jiguang", "xiaohongshu"):
            collector = JiguangCollector(cls._load_jiguang_config())
        elif platform in ("facebook", "instagram", "meta", "meta_ads"):
            collector = MetaAdsCollector(cls._load_meta_config())
        elif platform in ("x", "twitter", "x_ads"):
            collector = XAdsCollector(cls._load_x_config())

        if collector:
            cls._collectors[platform] = collector
        return collector

    @classmethod
    def health_check_all(cls) -> Dict[str, Any]:
        """所有平台健康检查。"""
        results = {}
        for platform in ["douyin", "xhs", "facebook", "x"]:
            collector = cls.get_collector(platform)
            if collector:
                results[platform] = collector.health_check()
            else:
                results[platform] = {"status": "not_implemented"}
        return results

    @classmethod
    def _load_ocean_config(cls) -> OceanEngineConfig:
        import os
        return OceanEngineConfig(
            access_token=os.environ.get("OCEAN_ENGINE_ACCESS_TOKEN", ""),
            advertiser_id=os.environ.get("OCEAN_ENGINE_ADVERTISER_ID", ""),
            agency_rebate_rate=float(os.environ.get("OCEAN_ENGINE_REBATE_RATE", "0")),
        )

    @classmethod
    def _load_jiguang_config(cls) -> JiguangConfig:
        import os
        return JiguangConfig(
            access_token=os.environ.get("JIGUANG_ACCESS_TOKEN", ""),
            advertiser_id=os.environ.get("JIGUANG_ADVERTISER_ID", ""),
            agency_rebate_rate=float(os.environ.get("JIGUANG_REBATE_RATE", "0")),
        )

    @classmethod
    def _load_meta_config(cls) -> MetaAdsConfig:
        import os
        return MetaAdsConfig(
            access_token=os.environ.get("META_ADS_ACCESS_TOKEN", ""),
            ad_account_id=os.environ.get("META_ADS_ACCOUNT_ID", ""),
            app_id=os.environ.get("META_APP_ID", ""),
            app_secret=os.environ.get("META_APP_SECRET", ""),
            proxy_url=os.environ.get("OPENAI_PROXY", ""),
        )

    @classmethod
    def _load_x_config(cls) -> XAdsConfig:
        import os
        return XAdsConfig(
            consumer_key=os.environ.get("X_ADS_CONSUMER_KEY", ""),
            consumer_secret=os.environ.get("X_ADS_CONSUMER_SECRET", ""),
            access_token=os.environ.get("X_ADS_ACCESS_TOKEN", ""),
            access_token_secret=os.environ.get("X_ADS_ACCESS_TOKEN_SECRET", ""),
            account_id=os.environ.get("X_ADS_ACCOUNT_ID", ""),
            proxy_url=os.environ.get("OPENAI_PROXY", ""),
        )
