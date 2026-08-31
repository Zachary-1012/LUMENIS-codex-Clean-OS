"""
CTH 太古汇专属话术库
====================
基于广州太古汇小红书运营SOP、复盘报告、活动规划提取的标准话术
用于报告生成、笔记分析、活动建议的太古汇调性输出

品牌调性：温暖、精致、有仪式感，像「懂生活的朋友在推荐」
设计偏好：简洁有设计感，参考成都太古里、颐缇港INDIGO、MIXTURE
"""

# ============ 品牌基础信息 ============

BRAND_INFO = {
    "full_name": "广州太古汇",
    "english_name": "Guangzhou Taikoo Hui",
    "positioning": "高端购物中心",
    "tone": "温暖、精致、有仪式感，像懂生活的朋友在推荐",
    "core_value": "微小而具体的需求",
    "design_reference": ["成都太古里", "颐缇港INDIGO", "MIXTURE", "无锡恒隆广场", "深圳湾万象城"],
    "target_audience": "高端消费人群、品质生活追求者、时尚爱好者",
    "location": "广州天河商圈",
}

# ============ 标题话术模板（三角度） ============

TITLE_TEMPLATES = {
    "search_type": {  # 检索型：地域+品类+痛点
        "formula": "{brand}{品类}地图｜{节点}{具体建议}",
        "examples": [
            "太古汇花艺地图｜七夕这样选花送到心里",
            "太古汇咖啡地图｜这5家藏在商场里的精品咖啡馆",
            "太古汇送礼指南｜毕业季这样选不踩雷",
        ],
    },
    "emotion_type": {  # 情绪型：情绪+场景+品牌调性
        "formula": "{情绪}之外，{节点}还有这些更{形容词}",
        "examples": [
            "玫瑰之外，七夕还有这些更会表达爱",
            "人潮之外，太古汇里藏着这些安静角落",
            "常规之外，这场展览给了夏天新的答案",
        ],
    },
    "concept_type": {  # 概念型：冲突+设问+解决方案
        "formula": "{冲突设问}？这{物品}里有{答案}",
        "examples": [
            "带哪只包去度假？这只草编包里有夏天的答案",
            "送什么才不踩雷？这份清单里有她想要的答案",
            "周末去哪？太古汇这层楼有一整天的答案",
        ],
    },
}

# ============ 笔记目的固定公式 ============

NOTE_PURPOSE_FORMULA = "借势{节点/热点}，深挖到{长搜索词}，打造以{主题}的笔记，以{具体切入点}，输出{主题}内容，通过{核心体验}赋能商场客流/销售"

# ============ 正文五段式结构 ============

BODY_STRUCTURE = {
    "paragraph_1": "场景引入：用一个具体的生活场景或情绪切入，让读者产生共鸣",
    "paragraph_2": "核心推荐：介绍本次推荐的主体（品牌/活动/产品），突出独特价值",
    "paragraph_3": "体验细节：描述具体的体验感受，用感官词汇（视觉/嗅觉/触觉）营造画面感",
    "paragraph_4": "实用信息：给出具体的实用信息（位置/时间/价格/预约方式）",
    "paragraph_5": "情感收尾：用温暖的句子收尾，呼应开头，留下回味空间",
}

# ============ 报告话术模板 ============

REPORT_PHRASES = {
    # 执行摘要
    "executive_summary": {
        "positive_dominant": "本周期品牌声量以正面为主，整体口碑健康，{活动/节点}带动传播量环比增长{增长比例}。",
        "negative_rising": "本周期负面舆情占比上升，主要集中在{负面类型}，需重点关注扩散趋势。",
        "stable": "本周期舆情整体平稳，正负声量接近，处于中性观察状态。",
        "data_incomplete": "本周期采集受到平台安全限制，数据不完整，不对舆情趋势作结论性判断。",
    },
    # 风险预警
    "risk_alert": {
        "critical": "紧急风险：{事件标题}，风险指数{分数}，建议{响应时间}内核查事实并准备官方回应。",
        "high": "高风险：{事件标题}，有扩散趋势，建议{响应时间}内关注并收集更多反馈。",
        "medium": "中风险：{事件标题}，持续观察中，必要时主动沟通改善。",
        "low": "低风险：{事件标题}，常规监测即可。",
    },
    # 行动建议
    "action_recommendation": {
        "urgent": "紧急（24小时内）：{具体动作}，负责方向：{团队}",
        "high": "高优先级（本周内）：{具体动作}，负责方向：{团队}",
        "medium": "中优先级（本月内）：{具体动作}，负责方向：{团队}",
        "routine": "常规：{具体动作}，持续执行。",
    },
    # 传播分析
    "propagation": {
        "high_engagement": "传播热度较高，互动活跃，主要在{平台}传播，{传播主体}贡献了主要声量。",
        "medium_engagement": "有一定传播量，互动中等，尚未形成大规模讨论。",
        "low_engagement": "传播量有限，目前以用户自发分享为主。",
        "multi_platform": "多平台交叉出现，需关注跨平台扩散风险。",
    },
    # 品牌健康度
    "brand_health": {
        "excellent": "品牌健康度优秀（{分数}分），正面声量占优，用户口碑良好。",
        "good": "品牌健康度良好（{分数}分），整体健康，个别负面需关注。",
        "average": "品牌健康度一般（{分数}分），正负声量接近，需提升正面传播。",
        "attention": "品牌健康度需关注（{分数}分），负面占比较高，建议主动干预。",
    },
}

# ============ 太古汇专属活动节点 ============

ACTIVITY_NODES = {
    "anniversary": {"name": "周年庆", "month": "9月", "tone": "盛大、感恩、仪式感"},
    "valentines": {"name": "七夕/情人节", "month": "2月/8月", "tone": "浪漫、精致、表达爱"},
    "graduation": {"name": "毕业季", "month": "6月", "tone": "青春、祝福、新开始"},
    "qixi_flower": {"name": "七夕花语篇", "month": "8月", "tone": "花艺、浪漫、选礼指南"},
    "abeibei": {"name": "阿贝贝治愈好物篇", "month": "8月", "tone": "治愈、生活好物、温暖"},
    "sanchushan": {"name": "三出山开业", "month": "7月", "tone": "新品牌、特色、探店"},
    "members_day": {"name": "会员日", "month": "每月", "tone": "专属、权益、感恩回馈"},
    "art_exhibition": {"name": "艺术展览", "month": "不定期", "tone": "艺术、文化、沉浸式体验"},
    "night_economy": {"name": "夜间经济", "month": "暑期", "tone": "夜生活、微醺、社交"},
}

# ============ 太古汇栏目构成 ============

COLUMN_STRUCTURE = {
    "original": {"count": 3, "description": "原创笔记，品牌自主策划"},
    "tenant_reuse": {"count": 2, "description": "商户二创笔记，联动场内品牌"},
    "influencer_co": {"count": 1, "description": "达人共创笔记，KOC/KOL合作"},
    "video_requirement": "每月至少1条视频笔记",
}

# ============ 竞品监控 ============

COMPETITORS = {
    "tianhuan": {"name": "天环广场", "positioning": "潮流年轻", "watch_focus": "活动、选题"},
    "tianhui": {"name": "天汇广场", "positioning": "高端", "watch_focus": "品牌、活动"},
    "k11": {"name": "广州K11", "positioning": "艺术商业", "watch_focus": "艺术展览、营销"},
    "taikoo_li_chengdu": {"name": "成都太古里", "positioning": "标杆参考", "watch_focus": "设计、内容"},
}

# ============ 报告专属开头/结尾 ============

REPORT_HEADER = "广州太古汇 舆情监测{周期}报告"
REPORT_FOOTER = "本报告由 CTH-POMS 广州太古汇舆情监控系统自动生成，数据来源可追溯。\n品牌调性：温暖、精致、有仪式感 | 监测范围：小红书/微博/全网"

# ============ 话术生成函数 ============

def generate_title(angle: str, brand: str = "太古汇", **kwargs) -> str:
    """生成太古汇风格标题"""
    templates = TITLE_TEMPLATES.get(angle, TITLE_TEMPLATES["search_type"])
    return templates["formula"].format(brand=brand, **kwargs)

def generate_note_purpose(node: str, keyword: str, theme: str, angle: str, experience: str) -> str:
    """生成笔记目的（固定公式）"""
    return NOTE_PURPOSE_FORMULA.format(
        **{"节点/热点": node, "长搜索词": keyword, "主题": theme, "具体切入点": angle, "核心体验": experience}
    )

def get_risk_phrase(level: str, title: str, score: float) -> str:
    """获取风险预警话术"""
    from .standard_taxonomy import RiskLevel
    level_enum = RiskLevel(level) if isinstance(level, str) else level
    template = REPORT_PHRASES["risk_alert"][level_enum.value]
    return template.format(事件标题=title[:30], 分数=score, 响应时间=level_enum.response_time)

def get_executive_phrase(mood: str, **kwargs) -> str:
    """获取执行摘要话术"""
    return REPORT_PHRASES["executive_summary"].get(mood, "").format(**kwargs)
