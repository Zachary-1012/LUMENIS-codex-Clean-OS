"""
标准化舆情分类体系
==================
统一事件类型、风险等级、情感标签、传播主体、报告周期的标准化定义
所有报告模块共用此分类，确保口径一致
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict


# ============ 事件类型（标准化） ============

class EventType(Enum):
    """舆情事件类型"""
    PRODUCT_QUALITY = "product_quality"        # 产品/服务质量
    CUSTOMER_SERVICE = "customer_service"      # 客户服务体验
    PRICING_PROMOTION = "pricing_promotion"    # 价格/促销活动
    BRAND_IMAGE = "brand_image"                # 品牌形象/声誉
    SAFETY_SECURITY = "safety_security"        # 安全/安保
    FACILITY_ENVIRONMENT = "facility_environment"  # 设施/环境
    PARKING_TRAFFIC = "parking_traffic"        # 停车/交通
    MARKETING_ACTIVITY = "marketing_activity"  # 营销活动
    MEMBERSHIP = "membership"                  # 会员/CRM
    TENANT_BRAND = "tenant_brand"              # 租户/品牌
    PUBLIC_OPINION = "public_opinion"          # 公众舆论
    OTHER = "other"                            # 其他

    @property
    def label(self):
        return {
            "product_quality": "产品服务质量",
            "customer_service": "客户服务体验",
            "pricing_promotion": "价格促销活动",
            "brand_image": "品牌形象声誉",
            "safety_security": "安全安保",
            "facility_environment": "设施环境",
            "parking_traffic": "停车交通",
            "marketing_activity": "营销活动",
            "membership": "会员CRM",
            "tenant_brand": "租户品牌",
            "public_opinion": "公众舆论",
            "other": "其他",
        }[self.value]


# ============ 风险等级（标准化） ============

class RiskLevel(Enum):
    """风险等级（4级）"""
    CRITICAL = "critical"    # 紧急：需24小时内响应，可能引发大规模负面
    HIGH = "high"            # 高风险：需48小时内关注，有扩散趋势
    MEDIUM = "medium"        # 中风险：持续观察，必要时介入
    LOW = "low"              # 低风险：常规监测，无需主动介入

    @property
    def label(self):
        return {"critical": "紧急", "high": "高风险", "medium": "中风险", "low": "低风险"}[self.value]

    @property
    def score_range(self):
        return {"critical": (80, 100), "high": (60, 79), "medium": (30, 59), "low": (0, 29)}[self.value]

    @property
    def response_time(self):
        return {"critical": "24小时内", "high": "48小时内", "medium": "本周内", "low": "持续观察"}[self.value]


# ============ 情感标签（标准化） ============

class Sentiment(Enum):
    """情感标签"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"  # 正负交织

    @property
    def label(self):
        return {"positive": "正面", "neutral": "中性", "negative": "负面", "mixed": "正负交织"}[self.value]


# ============ 传播主体（标准化） ============

class SubjectType(Enum):
    """传播主体类型"""
    OFFICIAL = "official"          # 官方账号
    KOL = "kol"                    # 大V/意见领袖（粉丝>10万）
    KOC = "koc"                    # 关键意见消费者（粉丝1万-10万）
    NORMAL_USER = "normal_user"    # 普通用户
    MEDIA = "media"                # 媒体
    COMPETITOR = "competitor"      # 竞品
    BOT = "bot"                    # 机器人/营销号

    @property
    def label(self):
        return {
            "official": "官方", "kol": "KOL", "koc": "KOC",
            "normal_user": "普通用户", "media": "媒体",
            "competitor": "竞品", "bot": "营销号",
        }[self.value]


# ============ 报告周期（标准化） ============

class ReportPeriod(Enum):
    """报告周期"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    EVENT = "event"  # 事件专项报告

    @property
    def label(self):
        return {"daily": "日报", "weekly": "周报", "monthly": "月报", "yearly": "年报", "event": "专项报告"}[self.value]

    @property
    def default_days(self):
        return {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365, "event": 7}[self.value]


# ============ 事实状态（标准化） ============

class FactStatus(Enum):
    """事实核实状态"""
    CONFIRMED = "confirmed"              # 已确认（多来源交叉验证）
    PARTIALLY_CONFIRMED = "partially_confirmed"  # 部分确认
    UNCONFIRMED = "unconfirmed"          # 未确认（单一来源）
    REFUTED = "refuted"                  # 已辟谣

    @property
    def label(self):
        return {"confirmed": "已确认", "partially_confirmed": "部分确认", "unconfirmed": "未确认", "refuted": "已辟谣"}[self.value]


# ============ 标准化数据结构 ============

@dataclass
class StandardizedEvent:
    """标准化事件"""
    event_id: str
    title: str
    event_type: EventType
    risk_level: RiskLevel
    risk_score: float
    sentiment: Sentiment
    fact_status: FactStatus
    mention_count: int
    source_count: int
    first_seen: str
    last_seen: str
    key_voices: List[Dict]
    summary: str
    recommended_action: str
    propagation_analysis: str


@dataclass
class StandardizedNote:
    """标准化笔记"""
    note_id: str
    platform: str
    title: str
    content: str
    author: str
    author_type: SubjectType
    sentiment: Sentiment
    risk_level: RiskLevel
    publish_at: str
    likes: int
    comments: int
    shares: int
    url: str
    event_id: str = ""
    fact_status: FactStatus = FactStatus.UNCONFIRMED


# ============ 分类工具函数 ============

def classify_risk_level(score: float) -> RiskLevel:
    """根据风险分数0-100分类"""
    if score >= 80:
        return RiskLevel.CRITICAL
    elif score >= 60:
        return RiskLevel.HIGH
    elif score >= 30:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def classify_sentiment(positive: int, negative: int, neutral: int = 0) -> Sentiment:
    """根据情感分布分类"""
    total = positive + negative + neutral
    if total == 0:
        return Sentiment.NEUTRAL
    pos_ratio = positive / total
    neg_ratio = negative / total
    if pos_ratio > 0.6:
        return Sentiment.POSITIVE
    elif neg_ratio > 0.6:
        return Sentiment.NEGATIVE
    elif abs(pos_ratio - neg_ratio) < 0.15:
        return Sentiment.MIXED
    return Sentiment.NEUTRAL


def classify_subject(followers: int, is_verified: bool = False, verified_type: str = "") -> SubjectType:
    """根据粉丝量和认证分类传播主体"""
    if is_verified and verified_type in ("enterprise", "official"):
        return SubjectType.OFFICIAL
    elif followers >= 100000:
        return SubjectType.KOL
    elif followers >= 10000:
        return SubjectType.KOC
    elif followers < 1000 and not is_verified:
        return SubjectType.NORMAL_USER
    return SubjectType.NORMAL_USER


def get_event_type_keywords() -> Dict[EventType, List[str]]:
    """获取各事件类型的关键词匹配表"""
    return {
        EventType.PRODUCT_QUALITY: ["质量", "假货", "瑕疵", "品质", "劣质", "变质", "过期", "山寨"],
        EventType.CUSTOMER_SERVICE: ["服务", "态度", "客服", "店员", "不理", "冷漠", "投诉", "差评"],
        EventType.PRICING_PROMOTION: ["价格", "贵", "优惠", "折扣", "促销", "涨价", "性价比", "坑"],
        EventType.BRAND_IMAGE: ["品牌", "形象", "高端", "档次", "调性", "定位", "口碑"],
        EventType.SAFETY_SECURITY: ["安全", "保安", "盗窃", "危险", "事故", "受伤", "隐患"],
        EventType.FACILITY_ENVIRONMENT: ["设施", "环境", "卫生", "脏", "破旧", "维修", "空调", "电梯"],
        EventType.PARKING_TRAFFIC: ["停车", "车位", "堵车", "交通", "排队", "拥挤", "入场"],
        EventType.MARKETING_ACTIVITY: ["活动", "展览", "快闪", "联名", "促销", "周年", "节日"],
        EventType.MEMBERSHIP: ["会员", "积分", "VIP", "权益", "等级", "兑换", "CRM"],
        EventType.TENANT_BRAND: ["品牌", "店铺", "商户", "专柜", "门店", "开业", "撤店"],
    }
