# -*- coding: utf-8 -*-
"""广告平台数据采集模块。"""
from .ocean_engine import OceanEngineCollector, OceanEngineConfig
from .jiguang import JiguangCollector, JiguangConfig
from .meta_ads import MetaAdsCollector, MetaAdsConfig
from .x_ads import XAdsCollector, XAdsConfig
from .factory import AdCollectorFactory

__all__ = [
    "OceanEngineCollector",
    "OceanEngineConfig",
    "JiguangCollector",
    "JiguangConfig",
    "MetaAdsCollector",
    "MetaAdsConfig",
    "XAdsCollector",
    "XAdsConfig",
    "AdCollectorFactory",
]
