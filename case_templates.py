# -*- coding: utf-8 -*-
"""
case_templates.py — 可复用方案模板注册表（结构化）
来源：docs/learning/CASE-TEMPLATE-REUSE-20260903.md（智谱glm-4.5-air 学习任务①产物）
性质：纯增量学习资产，不修改任何现有业务逻辑；供 案例库/事件中心/风险预警/报告 按场景匹配复用
"""
import re

# ============ 可复用模板注册表 ============
TEMPLATES = [
    {
        "template_id": "brand_health",
        "template_name": "品牌健康诊断",
        "template_type": "intelligence",
        "category": "品牌情报",
        "tags": ["品牌健康", "awareness", "consideration", "intent", "trust", "advocacy"],
        "keywords": ["品牌健康", "品牌认知", "知名度", "品牌形象", "品牌好感", "brand health", "awareness", "consideration", "购买意向"],
        "scenario": "量化评估品牌健康度全貌（认知/考虑/意向/信任/拥护/声量/UGC/社群/文化契合）",
        "steps": ["定义品牌健康维度与权重", "采集各维度信号(声量/UGC/搜索/互动)", "与竞品及行业基准对标", "识别指标分裂(如声量升/销售降)", "输出健康度评分与趋势"],
        "success_factors": ["多维度联合观察而非单一声量", "区分社交媒体声量与真实购买意向", "跨市场/跨品牌可比"],
        "metrics": ["品牌认知度变化率", "品牌健康指数", "相关搜索量增长", "消费者共鸣评分"],
        "module": "案例库/品牌情报",
        "product_scope": "ZBMP"
    },
    {
        "template_id": "crisis_response",
        "template_name": "危机应对框架",
        "template_type": "risk",
        "category": "危机公关",
        "tags": ["危机", "风险", "舆情", "负面", "处置"],
        "keywords": ["危机", "公关", "负面", "投诉", "闭店", "安全", "舆情", "处置", "回应", "声明", "紧急", "风险升级"],
        "scenario": "快速构建危机响应策略（黄金期/证据链/口径/执行/复盘）",
        "steps": ["黄金期响应(0-2h): 成立小组+启动监测+定级", "查明真相/证据链(2-6h): 收集证据+访谈+监控", "统一口径(6-12h): 声明稿+Q&A+渠道", "执行处置(12-72h): 官方/商场/商户三方", "复盘与风险迁移(3-7天): 报告+预案修订+培训"],
        "success_factors": ["黄金期失语是最大失误", "证据链完整度≥95%", "口径一致性100%", "先内部文化再外部传播"],
        "metrics": ["响应速度≤2h", "72h负面声量降≥50%", "品牌恢复时间7-14天", "相关方满意度≥85%"],
        "module": "案例库/风险预警/事件中心",
        "product_scope": "CTH-POMS/ZBMP"
    },
    {
        "template_id": "event_roi",
        "template_name": "事件营销ROI",
        "template_type": "marketing",
        "category": "事件营销",
        "tags": ["事件", "活动", "ROI", "营销", "campaign"],
        "keywords": ["事件营销", "活动", "ROI", "投资回报", "campaign", "快闪", "联名", "发布", "开业", "活动效果"],
        "scenario": "量化事件营销投资回报（目标/触达/互动/UGC/转化/长尾）",
        "steps": ["定义事件目标与KPI", "记录投入(预算/资源)", "采集曝光/互动/UGC数据", "计算转化与长尾动量", "输出ROI报告"],
        "success_factors": ["目标先行", "覆盖前中后全周期", "区分声量与转化"],
        "metrics": ["ROI", "触达量", "互动率", "UGC量", "搜索抬升"],
        "module": "案例库/报告",
        "product_scope": "CTH-POMS/ZBMP"
    },
    {
        "template_id": "social_intel",
        "template_name": "社会智能分析",
        "template_type": "intelligence",
        "category": "市场洞察",
        "tags": ["社会议题", "舆情", "情绪", "需求", "行为"],
        "keywords": ["社会", "议题", "情绪", "需求", "消费者洞察", "话题", "态度", "social listening", "舆情分析"],
        "scenario": "解构社会议题与品牌关联：Mention→Topic→Emotion→Need→Behavior→Intent→Action",
        "steps": ["采集提及与话题", "识别情绪与态度", "挖掘潜在需求", "映射行为与意图", "输出洞察建议"],
        "success_factors": ["不停留在正负面", "需求/行为/意图递进", "与业务决策关联"],
        "metrics": ["话题量", "情绪占比", "需求识别数", "意图转化率"],
        "module": "事件中心/品牌情报",
        "product_scope": "ZBMP"
    },
    {
        "template_id": "ugc_funnel",
        "template_name": "UGC转化漏斗",
        "template_type": "marketing",
        "category": "消费者洞察",
        "tags": ["UGC", "用户生成内容", "转化", "共创"],
        "keywords": ["UGC", "用户内容", "笔记", "评测", "晒单", "共创", "社区", "粉丝", "口碑", "转化"],
        "scenario": "追踪用户生成内容转化路径：Discovery→Consideration→Purchase→Ownership→Review→Advocacy",
        "steps": ["定义UGC类型与阶段", "采集各阶段UGC", "计算阶段转化率", "识别高价值UGC贡献者", "输出优化建议"],
        "success_factors": ["区分内容类型", "识别真实贡献者", "粉丝数≠社区强度"],
        "metrics": ["UGC量", "阶段转化率", "KOC贡献占比", "UGC带动搜索"],
        "module": "案例库/报告",
        "product_scope": "ZBMP"
    },
    {
        "template_id": "market_scan",
        "template_name": "市场机会扫描",
        "template_type": "intelligence",
        "category": "市场洞察",
        "tags": ["市场", "趋势", "机会", "空白"],
        "keywords": ["市场", "趋势", "机会", "空白", "新兴", "竞品动态", "品类", "增长"],
        "scenario": "识别新兴市场趋势与空白（品类/人群/地域/渠道）",
        "steps": ["定义扫描范围", "采集市场信号", "识别趋势与空白", "评估机会与风险", "输出机会清单"],
        "success_factors": ["信号时效性", "多源交叉", "机会可落地"],
        "metrics": ["趋势增长", "空白识别数", "机会可行性评分"],
        "module": "事件中心/品牌情报",
        "product_scope": "ZBMP"
    },
    {
        "template_id": "competitor_bench",
        "template_name": "竞品对标分析",
        "template_type": "intelligence",
        "category": "竞品分析",
        "tags": ["竞品", "对标", "竞争", "benchmark"],
        "keywords": ["竞品", "对标", "竞争", "竞争对手", "benchmark", "同城", "同品类", "价格带"],
        "scenario": "多维度对比品牌竞争态势（Direct/Aspirational/Cultural/Attention）",
        "steps": ["定义对标品牌池", "选择对比维度", "采集双方信号", "计算差距与优势", "输出对标报告"],
        "success_factors": ["区分直接/向往/文化/注意力竞品", "维度覆盖全面", "结论可行动"],
        "metrics": ["声量对比", "份额变化", "竞品动作响应"],
        "module": "案例库/报告",
        "product_scope": "ZBMP"
    },
    {
        "template_id": "culture_fit",
        "template_name": "文化契合度评估",
        "template_type": "intelligence",
        "category": "品牌情报",
        "tags": ["文化", "契合", "价值观", "跨界"],
        "keywords": ["文化", "契合", "价值观", "跨界", "艺术", "生活方式", "品味", "审美", "调性"],
        "scenario": "评估品牌与文化语境的匹配度（价值观/美学/议题关联）",
        "steps": ["定义品牌文化基因", "识别文化语境", "评估契合度", "识别冲突风险", "输出契合评估"],
        "success_factors": ["真实契合而非硬蹭", "识别文化敏感点"],
        "metrics": ["契合度评分", "文化话题相关性", "负面风险指数"],
        "module": "案例库/品牌情报",
        "product_scope": "ZBMP"
    },
    {
        "template_id": "risk_matrix",
        "template_name": "风险预警矩阵",
        "template_type": "risk",
        "category": "风险预警",
        "tags": ["风险", "预警", "矩阵", "等级", "负面"],
        "keywords": ["风险", "预警", "矩阵", "等级", "负面", "高危", "扩散", "升级", "严重", "紧急"],
        "scenario": "预测潜在品牌风险等级（影响×概率×扩散）",
        "steps": ["定义风险维度(影响/概率/扩散)", "采集风险信号", "计算风险矩阵定位", "分级预警", "触发处置或观察"],
        "success_factors": ["维度量化", "分级清晰", "与处置联动"],
        "metrics": ["风险等级", "预警准确率", "响应时效"],
        "module": "风险预警/报告",
        "product_scope": "CTH-POMS"
    },
]

# ============ 危机公关处置 SOP（结构化阶段） ============
CRISIS_SOP = {
    "name": "危机公关处置SOP",
    "description": "商业地产/品牌舆情危机公关处置模板：黄金期响应→证据链→口径→执行→复盘",
    "stages": [
        {"stage": "黄金期响应", "window": "0-2小时", "actions": ["成立危机应对小组(CEO牵头)", "启动舆情监测", "初步评估危机等级(1-5级)", "暂停相关营销", "初步回应"], "metrics": ["小组组建100%", "监测响应≤15分钟", "定级准确率≥90%"]},
        {"stage": "查明真相/证据链", "window": "2-6小时", "actions": ["收集所有证据", "访问目击者/当事人", "调取监控/录音", "分析起因与责任方", "评估影响范围"], "metrics": ["证据完整度≥95%", "证人访谈100%", "事实核查100%"]},
        {"stage": "统一口径/对外声明", "window": "6-12小时", "actions": ["制定统一口径", "准备官方声明稿", "确定发布渠道", "准备Q&A", "内部培训"], "metrics": ["口径一致100%", "声明审核100%", "渠道覆盖100%"]},
        {"stage": "执行处置", "window": "12-72小时", "actions": ["官方:发布声明/发布会/补偿整改", "商场方:运营调整/商户沟通/临时管控", "商户侧:配合行动/经营调整/员工培训"], "metrics": ["声明后24h媒体覆盖≥90%", "整改完成100%", "商户配合≥95%"]},
        {"stage": "复盘与风险迁移", "window": "3-7天", "actions": ["处置效果评估", "撰写危机报告", "修订危机预案", "建立长期监测", "危机培训"], "metrics": ["报告完成100%", "预案修订100%", "培训覆盖100%"]},
    ],
    "kpi": ["危机响应速度≤2h", "72h负面声量下降≥50%", "品牌恢复时间7-14天", "相关方满意度≥85%"],
}

_TYPE_MAP = {
    "品牌营销": ["marketing", "campaign", "活动", "营销", "联名"],
    "危机公关": ["risk", "危机", "负面", "公关", "投诉"],
    "事件营销": ["marketing", "事件", "活动", "开业"],
    "市场洞察": ["intelligence", "市场", "洞察", "趋势", "竞品"],
    "其他": [],
}


def match_templates(keyword="", category="", limit=3):
    """按关键词/场景匹配最合适的模板（轻量本地规则匹配，不调AI、不扣额度）"""
    kw = (keyword or "").strip().lower()
    cat = (category or "").strip()
    scored = []
    for t in TEMPLATES:
        score = 0
        hit_keyword = ""
        if kw:
            for k in t.get("keywords", []):
                if k.lower() in kw or kw in k.lower():
                    score += 3
                    hit_keyword = k
                    break
            # 词元部分命中
            for token in re.split(r"[\s,，、/]+", kw):
                if len(token) >= 2:
                    for k in t.get("keywords", []):
                        if token in k:
                            score += 1
                            break
        if cat:
            if cat in t.get("category", "") or cat in t.get("tags", []):
                score += 2
            for ttype, words in _TYPE_MAP.items():
                if cat in ttype:
                    if any(w in str(t.get("tags", [])) + t.get("category", "") for w in words):
                        score += 1
        if score > 0:
            scored.append({"template": t, "score": score, "hit_keyword": hit_keyword})
    scored.sort(key=lambda x: x["score"], reverse=True)
    out = []
    for s in scored[:limit]:
        t = s["template"]
        out.append({
            "template_id": t["template_id"],
            "template_name": t["template_name"],
            "template_type": t["template_type"],
            "category": t["category"],
            "tags": t["tags"],
            "scenario": t["scenario"],
            "steps": t["steps"],
            "success_factors": t["success_factors"],
            "metrics": t["metrics"],
            "module": t["module"],
            "product_scope": t["product_scope"],
            "match_score": s["score"],
            "hit_keyword": s["hit_keyword"],
        })
    return out


def get_template(template_id):
    for t in TEMPLATES:
        if t["template_id"] == template_id:
            return t
    return None


def get_all_templates():
    return TEMPLATES


def get_crisis_sop():
    return CRISIS_SOP
