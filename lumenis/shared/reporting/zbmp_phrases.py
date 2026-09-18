"""
BMP / 序境·品牌市场 通用品牌话术库
================================
适用于 LUMENIS Brand & Market (BMP) 多品牌场景；文件名 zbmp 保留为内部技术兼容 ID
不绑定特定品牌，可配置品牌参数后生成
"""

# ============ 通用品牌配置模板 ============

BRAND_CONFIG_TEMPLATE = {
    "brand_name": "",
    "industry": "",  # retail/food/beauty/tech/fashion/automotive
    "positioning": "",
    "tone": "专业、客观、数据驱动",
    "core_metrics": ["曝光量", "互动量", "正面占比", "风险指数", "品牌健康度"],
    "competitors": [],
    "key_platforms": ["小红书", "微博", "抖音", "知乎", "全网"],
}

# ============ 通用报告话术 ============

ZBMP_REPORT_PHRASES = {
    "executive_summary": {
        "positive": "{brand}本周期品牌声量正面占优，整体口碑健康，{metric}环比{direction}{value}。",
        "negative": "{brand}本周期负面舆情上升，主要集中在{issue_type}，建议关注{action}。",
        "neutral": "{brand}本周期舆情平稳，声量波动在正常范围。",
        "crisis": "{brand}本周期出现{risk_level}风险事件，需立即启动{response}。",
    },
    "risk_alert": {
        "critical": "【紧急】{brand}检测到{risk_level}风险：{event}，风险指数{score}，建议{time}内响应。",
        "high": "【高风险】{brand}：{event}，扩散趋势{trend}，建议{time}内关注。",
        "medium": "【中风险】{brand}：{event}，持续观察中。",
        "low": "【低风险】{brand}：{event}，常规监测。",
    },
    "competitor_benchmark": "{brand}声量占比{share}%，对比{competitor}（{comp_share}%），{advantage}。",
    "trend_analysis": "{metric}呈{trend}趋势，{reason}，预计{forecast}。",
    "action_recommendation": "{priority}：{action}，预期效果{expected_impact}。",
}

# ============ 行业特定关注点 ============

INDUSTRY_FOCUS = {
    "retail": {  # 零售/购物中心
        "key_metrics": ["客流", "销售额", "租户动态", "活动效果", "会员增长"],
        "risk_types": ["服务体验", "停车交通", "设施环境", "价格促销", "安全"],
        "positive_signals": ["打卡分享", "品牌推荐", "活动好评", "会员权益"],
    },
    "food": {  # 餐饮
        "key_metrics": ["口味评价", "服务速度", "排队时长", "卫生", "性价比"],
        "risk_types": ["食品安全", "服务态度", "等位时间", "价格", "出品不稳定"],
        "positive_signals": ["美食推荐", "探店分享", "复购意愿", "菜品好评"],
    },
    "beauty": {  # 美妆
        "key_metrics": ["产品评价", "成分讨论", "使用效果", "包装设计", "价格"],
        "risk_types": ["过敏反应", "虚假宣传", "价格争议", "假货", "客服"],
        "positive_signals": ["妆容分享", "好物推荐", "成分党好评", "试色"],
    },
    "tech": {  # 科技
        "key_metrics": ["产品体验", "性能评价", "售后服务", "价格", "创新"],
        "risk_types": ["质量问题", "系统bug", "售后延迟", "隐私安全", "价格"],
        "positive_signals": ["测评推荐", "使用技巧", "功能好评", "对比优势"],
    },
    "fashion": {  # 时尚
        "key_metrics": ["设计评价", "材质工艺", "穿搭分享", "品牌调性", "价格"],
        "risk_types": ["质量问题", "抄袭争议", "价格", "尺码", "客服"],
        "positive_signals": ["穿搭分享", "品牌联名", "设计好评", "明星同款"],
    },
    "automotive": {  # 汽车
        "key_metrics": ["驾驶体验", "续航/油耗", "智能座舱", "售后服务", "价格"],
        "risk_types": ["质量召回", "续航虚标", "车机bug", "售后", "安全事故"],
        "positive_signals": ["提车分享", "试驾评测", "改装案例", "车主口碑"],
    },
}

# ============ 多品牌对比模板 ============

MULTI_BRAND_COMPARISON = {
    "share_of_voice": "声量占比：{brand1} {s1}% / {brand2} {s2}% / {brand3} {s3}%",
    "sentiment_compare": "正面占比：{brand1} {p1}% / {brand2} {p2}% / {brand3} {p3}%",
    "risk_compare": "风险指数：{brand1} {r1} / {brand2} {r2} / {brand3} {r3}",
    "engagement_compare": "互动量：{brand1} {e1} / {brand2} {e2} / {brand3} {e3}",
    "conclusion": "{leader}在{metric}领先，{follower}需在{improvement}方面提升。",
}

# ============ 报告周期侧重点 ============

PERIOD_FOCUS = {
    "daily": {
        "focus": "当日舆情动态、风险预警、即时行动建议",
        "sections": ["今日摘要", "风险事件", "关键洞察", "行动建议", "数据完整性"],
        "length": "精简（1-2页）",
    },
    "weekly": {
        "focus": "周度趋势、事件发展、传播分析、竞品对比",
        "sections": ["执行摘要", "舆情趋势", "重点事件", "传播分析", "竞品动态", "行动建议"],
        "length": "中等（3-5页）",
    },
    "monthly": {
        "focus": "月度综合分析、品牌健康度、活动效果、深度洞察",
        "sections": ["执行摘要", "品牌健康度", "舆情全景", "重点事件复盘", "传播主体分析", "竞品分析", "市场趋势", "战略建议"],
        "length": "详细（8-12页）",
    },
    "yearly": {
        "focus": "年度总结、年度趋势、品牌资产变化、来年规划建议",
        "sections": ["年度回顾", "品牌资产变化", "年度大事件", "传播趋势", "竞品年度对比", "用户画像变化", "来年战略建议"],
        "length": "全面（15-20页）",
    },
    "event": {
        "focus": "单一事件深度分析、发展脉络、影响评估、应对建议",
        "sections": ["事件概述", "发展时间线", "传播分析", "情感变化", "影响评估", "应对建议", "后续监测"],
        "length": "专项（5-8页）",
    },
}

# ============ 通用话术生成函数 ============

def generate_zbmp_phrase(phrase_type: str, mood: str, **kwargs) -> str:
    """生成通用品牌话术"""
    templates = ZBMP_REPORT_PHRASES.get(phrase_type, {})
    template = templates.get(mood, "")
    if not template:
        return ""
    return template.format(**kwargs)

def get_industry_focus(industry: str) -> dict:
    """获取行业特定关注点"""
    return INDUSTRY_FOCUS.get(industry, INDUSTRY_FOCUS["retail"])

def get_period_focus(period: str) -> dict:
    """获取报告周期侧重点"""
    return PERIOD_FOCUS.get(period, PERIOD_FOCUS["daily"])