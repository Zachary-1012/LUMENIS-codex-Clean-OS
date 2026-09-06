# -*- coding: utf-8 -*-
"""
广告平台商业属性注册表
======================
记录每个广告平台的真实世界商业属性：
- 地区与市场覆盖
- 准入门槛与开户状态
- 资金与结算（币种、支付方式）
- API 权限等级
- 合规要求
- 代理商体系

这些是开发硬约束，不是可选配置。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class Region(str, Enum):
    """地区枚举。"""
    MAINLAND_CHINA = "mainland_china"
    HONG_KONG = "hong_kong"
    TAIWAN = "taiwan"
    NORTH_AMERICA = "north_america"
    EUROPE = "europe"
    SOUTHEAST_ASIA = "southeast_asia"
    JAPAN_KOREA = "japan_korea"
    GLOBAL = "global"


class Currency(str, Enum):
    """币种枚举。"""
    CNY = "CNY"
    USD = "USD"
    EUR = "EUR"
    HKD = "HKD"
    JPY = "JPY"


class ApiAccessLevel(str, Enum):
    """API 权限等级。"""
    NONE = "none"              # 无 API 权限，只能浏览器采集
    READ_ONLY = "read_only"    # 只读 API（数据查询）
    LIMITED_WRITE = "limited_write"  # 有限写操作（部分接口）
    FULL = "full"              # 完整 API 权限


class AccountStatus(str, Enum):
    """广告账户状态。"""
    NOT_OPENED = "not_opened"      # 未开户
    UNDER_REVIEW = "under_review"  # 审核中
    ACTIVE = "active"              # 正常投放
    SUSPENDED = "suspended"        # 被暂停
    BANNED = "banned"              # 被封禁
    ARREARS = "arrears"            # 欠费


@dataclass
class PlatformCommercialProfile:
    """平台商业属性画像（真实世界约束）。"""
    platform: str                          # 平台标识
    display_name: str                      # 显示名称
    ad_system: str                         # 广告系统名称
    primary_regions: List[Region]          # 主要市场地区
    accessible_from_china: bool            # 中国大陆是否可直接访问
    requires_proxy: bool                   # 是否需要代理
    currency: Currency                     # 默认结算币种
    payment_methods: List[str]             # 支持的支付方式
    min_deposit: float                     # 最低充值金额（0 表示无）
    min_daily_budget: float                # 最低日预算
    api_access_level: ApiAccessLevel       # API 权限等级
    api_application_required: bool         # API 是否需要申请
    api_quota_limited: bool                # API 是否有配额限制
    account_status: AccountStatus          # 当前账户状态
    requires_business_license: bool        # 是否需要企业营业执照
    restricted_industries: List[str]       # 受限行业
    compliance_regulations: List[str]      # 适用合规法规
    supports_agency: bool                  # 是否支持代理商体系
    typical_rebate_rate: float             # 典型代理商返点率（0-1）
    targeting_granularity: str             # 定向粒度描述
    data_granularity: str                  # 数据粒度（小时/天）
    notes: str = ""                        # 备注


# ============================================================
# 平台商业属性注册表（基于真实世界商业现实）
# ============================================================

PLATFORM_COMMERCIAL_REGISTRY: Dict[str, PlatformCommercialProfile] = {

    # ---------- 中国大陆平台 ----------

    "xhs": PlatformCommercialProfile(
        platform="xhs",
        display_name="小红书",
        ad_system="聚光（DEPRECATED 2026-09-06 用户指令弃用）",
        primary_regions=[Region.MAINLAND_CHINA],
        accessible_from_china=True,
        requires_proxy=False,
        currency=Currency.CNY,
        payment_methods=["对公转账", "支付宝"],
        min_deposit=5000,
        min_daily_budget=50,
        api_access_level=ApiAccessLevel.READ_ONLY,
        api_application_required=True,
        api_quota_limited=True,
        account_status=AccountStatus.NOT_OPENED,
        requires_business_license=True,
        restricted_industries=["医疗", "金融", "教育", "保健品"],
        compliance_regulations=["广告法", "个人信息保护法", "数据安全法"],
        supports_agency=True,
        typical_rebate_rate=0.05,
        targeting_granularity="省/市/商圈/兴趣/人群包",
        data_granularity="天级（API有限开放）",
        notes="聚光API需特批，配额严格；种草内容审核较严",
    ),

    "douyin": PlatformCommercialProfile(
        platform="douyin",
        display_name="抖音",
        ad_system="巨量引擎",
        primary_regions=[Region.MAINLAND_CHINA],
        accessible_from_china=True,
        requires_proxy=False,
        currency=Currency.CNY,
        payment_methods=["对公转账", "支付宝"],
        min_deposit=10000,
        min_daily_budget=100,
        api_access_level=ApiAccessLevel.LIMITED_WRITE,
        api_application_required=True,
        api_quota_limited=True,
        account_status=AccountStatus.NOT_OPENED,
        requires_business_license=True,
        restricted_industries=["医疗", "金融", "教育", "保健品", "烟草"],
        compliance_regulations=["广告法", "个人信息保护法", "数据安全法"],
        supports_agency=True,
        typical_rebate_rate=0.08,
        targeting_granularity="省/市/商圈/兴趣/人群包/DMP",
        data_granularity="小时级（Marketing API）",
        notes="巨量引擎Marketing API需企业资质审核；代理商体系成熟，返点3%-15%",
    ),

    "bilibili": PlatformCommercialProfile(
        platform="bilibili",
        display_name="B站",
        ad_system="花火",
        primary_regions=[Region.MAINLAND_CHINA],
        accessible_from_china=True,
        requires_proxy=False,
        currency=Currency.CNY,
        payment_methods=["对公转账"],
        min_deposit=5000,
        min_daily_budget=50,
        api_access_level=ApiAccessLevel.NONE,
        api_application_required=True,
        api_quota_limited=True,
        account_status=AccountStatus.NOT_OPENED,
        requires_business_license=True,
        restricted_industries=["部分行业限制"],
        compliance_regulations=["广告法", "个人信息保护法"],
        supports_agency=True,
        typical_rebate_rate=0.03,
        targeting_granularity="省/市/兴趣/UP主粉丝画像",
        data_granularity="天级（API有限开放，邀请制）",
        notes="花火平台以UP主商单为主，信息流广告API有限开放；邀请制",
    ),

    "weibo": PlatformCommercialProfile(
        platform="weibo",
        display_name="微博",
        ad_system="粉丝通",
        primary_regions=[Region.MAINLAND_CHINA],
        accessible_from_china=True,
        requires_proxy=False,
        currency=Currency.CNY,
        payment_methods=["对公转账", "支付宝"],
        min_deposit=5000,
        min_daily_budget=50,
        api_access_level=ApiAccessLevel.READ_ONLY,
        api_application_required=True,
        api_quota_limited=True,
        account_status=AccountStatus.NOT_OPENED,
        requires_business_license=True,
        restricted_industries=["医疗", "金融"],
        compliance_regulations=["广告法", "个人信息保护法"],
        supports_agency=True,
        typical_rebate_rate=0.05,
        targeting_granularity="省/市/兴趣/人群/话题",
        data_granularity="小时级",
        notes="粉丝通API需申请；热搜和话题广告溢价高",
    ),

    "zhihu": PlatformCommercialProfile(
        platform="zhihu",
        display_name="知乎",
        ad_system="知+",
        primary_regions=[Region.MAINLAND_CHINA],
        accessible_from_china=True,
        requires_proxy=False,
        currency=Currency.CNY,
        payment_methods=["对公转账"],
        min_deposit=5000,
        min_daily_budget=50,
        api_access_level=ApiAccessLevel.NONE,
        api_application_required=True,
        api_quota_limited=True,
        account_status=AccountStatus.NOT_OPENED,
        requires_business_license=True,
        restricted_industries=["医疗", "金融"],
        compliance_regulations=["广告法", "个人信息保护法"],
        supports_agency=True,
        typical_rebate_rate=0.03,
        targeting_granularity="省/市/兴趣/话题/关键词",
        data_granularity="天级",
        notes="知+以内容加热为主，API有限开放；内容审核严格",
    ),

    # ---------- 海外平台 ----------

    "facebook": PlatformCommercialProfile(
        platform="facebook",
        display_name="Facebook",
        ad_system="Meta Ads",
        primary_regions=[Region.NORTH_AMERICA, Region.EUROPE, Region.SOUTHEAST_ASIA, Region.GLOBAL],
        accessible_from_china=False,
        requires_proxy=True,
        currency=Currency.USD,
        payment_methods=["信用卡", "PayPal", "对公转账"],
        min_deposit=0,
        min_daily_budget=1,
        api_access_level=ApiAccessLevel.FULL,
        api_application_required=True,
        api_quota_limited=True,
        account_status=AccountStatus.NOT_OPENED,
        requires_business_license=True,
        restricted_industries=["成人内容", "烟草", "武器", "加密货币（受限）", "政治广告（需特批）"],
        compliance_regulations=["GDPR", "CCPA", "Meta广告政策"],
        supports_agency=True,
        typical_rebate_rate=0.0,
        targeting_granularity="国家/州/市/DMA/兴趣/自定义受众/相似受众",
        data_granularity="小时级（Marketing API）",
        notes="Meta Ads Manager需企业BM+公共主页；政治广告需身份验证；中国大陆需代理",
    ),

    "instagram": PlatformCommercialProfile(
        platform="instagram",
        display_name="Instagram",
        ad_system="Meta Ads",
        primary_regions=[Region.NORTH_AMERICA, Region.EUROPE, Region.SOUTHEAST_ASIA, Region.GLOBAL],
        accessible_from_china=False,
        requires_proxy=True,
        currency=Currency.USD,
        payment_methods=["信用卡", "PayPal"],
        min_deposit=0,
        min_daily_budget=1,
        api_access_level=ApiAccessLevel.FULL,
        api_application_required=True,
        api_quota_limited=True,
        account_status=AccountStatus.NOT_OPENED,
        requires_business_license=True,
        restricted_industries=["成人内容", "烟草", "武器"],
        compliance_regulations=["GDPR", "CCPA", "Meta广告政策"],
        supports_agency=True,
        typical_rebate_rate=0.0,
        targeting_granularity="同 Facebook（Meta统一广告后台）",
        data_granularity="小时级",
        notes="Instagram广告通过Meta Ads Manager投放，与Facebook共享广告账户；视觉素材要求高",
    ),

    "x": PlatformCommercialProfile(
        platform="x",
        display_name="X (Twitter)",
        ad_system="X Ads",
        primary_regions=[Region.NORTH_AMERICA, Region.EUROPE, Region.JAPAN_KOREA, Region.GLOBAL],
        accessible_from_china=False,
        requires_proxy=True,
        currency=Currency.USD,
        payment_methods=["信用卡"],
        min_deposit=0,
        min_daily_budget=1,
        api_access_level=ApiAccessLevel.FULL,
        api_application_required=True,
        api_quota_limited=True,
        account_status=AccountStatus.NOT_OPENED,
        requires_business_license=False,
        restricted_industries=["政治广告（需特批）", "成人内容", "加密货币（受限）"],
        compliance_regulations=["GDPR", "CCPA", "X广告政策"],
        supports_agency=True,
        typical_rebate_rate=0.0,
        targeting_granularity="国家/州/市/兴趣/关键词/受众",
        data_granularity="小时级（Ads API）",
        notes="X Ads API需开发者审核；API配额严格；中国大陆需代理；企业账户可开发票",
    ),
}


def get_platform_profile(platform: str) -> Optional[PlatformCommercialProfile]:
    """获取平台商业属性画像。"""
    return PLATFORM_COMMERCIAL_REGISTRY.get(platform.strip().lower())


def list_platforms_by_region(region: Region) -> List[str]:
    """按地区列出支持的平台。"""
    return [
        p.platform for p in PLATFORM_COMMERCIAL_REGISTRY.values()
        if region in p.primary_regions
    ]


def list_platforms_by_access(accessible_from_china: bool) -> List[str]:
    """按中国大陆可访问性列出平台。"""
    return [
        p.platform for p in PLATFORM_COMMERCIAL_REGISTRY.values()
        if p.accessible_from_china == accessible_from_china
    ]


def get_cross_platform_roi_normalization(platforms: List[str],
                                         base_currency: Currency = Currency.CNY) -> Dict[str, float]:
    """获取跨平台 ROI 归一化汇率（占位，实际需接入实时汇率）。

    开发约束：跨平台 ROAS 比较必须先统一币种。
    """
    # 固定汇率占位（实际应从汇率API获取，记录时间戳）
    exchange_rates = {
        Currency.CNY: 1.0,
        Currency.USD: 7.25,   # 1 USD = 7.25 CNY（占位）
        Currency.EUR: 7.85,
        Currency.HKD: 0.93,
        Currency.JPY: 0.048,
    }
    result = {}
    for plat in platforms:
        profile = get_platform_profile(plat)
        if profile:
            rate = exchange_rates.get(profile.currency, 1.0)
            if base_currency == Currency.USD:
                rate = 1.0 / rate if rate != 0 else 1.0
            result[plat] = rate
    return result


def check_platform_readiness(platform: str) -> Dict[str, any]:
    """检查平台投流就绪状态（基于商业现实约束）。"""
    profile = get_platform_profile(platform)
    if not profile:
        return {"ready": False, "reason": "平台不在注册表中", "profile": None}

    blockers = []
    warnings = []

    # 账户状态检查
    if profile.account_status != AccountStatus.ACTIVE:
        blockers.append(f"账户状态: {profile.account_status.value}")

    # 代理检查
    if profile.requires_proxy:
        import os
        has_proxy = bool(os.environ.get("OPENAI_PROXY") or os.environ.get("HTTPS_PROXY"))
        if not has_proxy:
            blockers.append("需要代理但未检测到代理配置")

    # API 权限检查
    if profile.api_access_level == ApiAccessLevel.NONE:
        warnings.append("无API权限，只能浏览器只读采集")
    elif profile.api_access_level == ApiAccessLevel.READ_ONLY:
        warnings.append("API仅只读，写操作不可用")

    # 最低充值检查
    if profile.min_deposit > 0:
        warnings.append(f"最低充值: {profile.min_deposit} {profile.currency.value}")

    return {
        "ready": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
        "profile": profile,
    }
