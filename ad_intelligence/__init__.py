"""
广告投流与深度学习智能模块
==========================
定位：序境/LUMENIS 商业应用级广告投流智能模块。

能力：
- 全平台广告数据采集与分析（只读）
- 投流策略生成与优化（AI 辅助）
- 可替换的 CTR/特征工程增强层（当前 baseline 为确定性、可解释、只读）
- 投流操作执行（带 Permission Gate，默认关闭）

红线：
- 投流操作默认关闭，需 Permission Gate + 人工确认
- 资金操作最高保护，必须人工二次确认
- 只读优先，写操作需显式授权
- 所有操作可追溯
- baseline model 不是 Production Truth，不自动执行投流
"""
from .base import AdPlatform, AdCampaign, AdMetric, AdCreative
from .permission_gate import AdPermissionGate, AdPermissionLevel
from .platform_registry import (
    PlatformCommercialProfile, PLATFORM_COMMERCIAL_REGISTRY,
    get_platform_profile, check_platform_readiness,
    Region, Currency, ApiAccessLevel, AccountStatus,
)
from .models import CTRPrediction, CTRPredictor, AdFeatureEngineer, AdFeatureSet

__all__ = [
    "AdPlatform",
    "AdCampaign",
    "AdMetric",
    "AdCreative",
    "AdPermissionGate",
    "AdPermissionLevel",
    "PlatformCommercialProfile",
    "PLATFORM_COMMERCIAL_REGISTRY",
    "get_platform_profile",
    "check_platform_readiness",
    "Region",
    "Currency",
    "ApiAccessLevel",
    "AccountStatus",
    "CTRPrediction",
    "CTRPredictor",
    "AdFeatureEngineer",
    "AdFeatureSet",
]
