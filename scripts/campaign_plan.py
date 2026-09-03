# -*- coding: utf-8 -*-
"""可比稿营销方案引擎（营销知识库框架落地）。

输入品牌/品类/目标/预算/人群 → 输出 10 段完整提案骨架：
Brief理解 → 洞察 → 策略 → Big Idea → 创意落地 → 整合触点 → 媒介 → KPI →
节奏 → 风险。按品类映射打法库（餐饮/快消/美妆/汽车/文旅/城市/B2B/科技/金融/通用）。

生成的是一份**逻辑完整的方案骨架与创意方向**：创意概念给出 2 个方向（一条稳妥可执行 + 一条
更有胆量的 Big Idea），供你在真实 Brief 上进一步细化。CLI：
  python scripts/campaign_plan.py --brand 品牌 --category 餐饮 --goal 新品上市 --budget 500万
"""
import argparse
import json
import textwrap

# 品类打法库（决策特性 / 核心打法 / 关键触点 / 创意方向 / 风险点）
CATEGORY_PLAYBOOKS = {
    "餐饮": {
        "decision": "低客单高频冲动",
        "play": "上新情绪化 + 体验事件化 + KOC 矩阵",
        "touchpoints": ["门店体验改造", "上新主题事件", "直播内容IP", "本地达人", "会员私域"],
        "creative": [
            "把产品卖点做成一场「运动会/剧本杀」式体验事件（抽象概念体验化）",
            "用谐音/双关做沟通切口，绑定当下集体情绪（产品属性×情绪双关）",
        ],
        "risk": "排队/出品一致性差会反噬；上新节奏过快透支期待",
    },
    "快消": {
        "decision": "低客单高频，货架+线上双战场",
        "play": "派样拉新 + AIGC 参与式玩法 + 情绪价值日常化",
        "touchpoints": ["派样试用", "AIGC贴纸/合拍", "KOC矩阵", "会员复购", "联名"],
        "creative": [
            "把用户行为变成产品/内容（UGC→产品飞轮）",
            "用可参与的轻互动让用户拉用户（滚雪球破圈）",
        ],
        "risk": "同质化快；派样成本控制；话题衰减周期短",
    },
    "美妆": {
        "decision": "中客单颜值社交",
        "play": "环境即内容 + 可分享细节 + 试用派样",
        "touchpoints": ["快闪体验", "成分可视化", "达人测评", "派样盒", "私域"],
        "creative": [
            "选址即表达：把快闪放在「本身就是宣言」的环境",
            "设计可分享的细节而非仅可拍照的背景（出片率）",
        ],
        "risk": "强监管（功效宣称）；成分焦虑反向舆情",
    },
    "汽车": {
        "decision": "高客单长决策",
        "play": "场景体验 + 地标事件 + 文旅联动",
        "touchpoints": ["上市发布会地标化", "试驾体验", "文旅跨界", "车主社群", "口碑"],
        "creative": [
            "把发布会搬进城市地标/文旅场景（产品×城市叙事）",
            "车主真实故事/长途实测做长内容（决策信任）",
        ],
        "risk": "高客单决策链长；口碑负面影响大；上市即交付口碑",
    },
    "文旅": {
        "decision": "目的地心智",
        "play": "票根串联 + IP×平台 + 流动名片",
        "touchpoints": ["票根延伸链路", "IP联名", "跨省巡游", "主题彩蛋", "OTA"],
        "creative": [
            "设计「一张票的延伸链路」：一张票串起交通/住宿/商圈/周边",
            "把城市地标变成流动名片（车队/彩蛋车/主题车）",
        ],
        "risk": "旺季承载与安全；季节性波动；过度商业化伤原生体验",
    },
    "城市": {
        "decision": "区域品牌与招商心智",
        "play": "重大赛事IP + 全域消费激活 + 政企协同",
        "touchpoints": ["赛事/节庆IP", "一票通城", "商圈联动", "媒体矩阵", "招商"],
        "creative": [
            "用一张票/一个赛事做城市级消费引擎（票根经济）",
            "把城市文化提炼成可巡游的「流动名片」",
        ],
        "risk": "政府多利益方协同；人流安全；效果归因难",
    },
    "B2B": {
        "decision": "高客单多决策人",
        "play": "内容基建 + 思想领导力 + 分层内容",
        "touchpoints": ["白皮书", "案例", "行业知识树", "高管曝光", "客户同行发声"],
        "creative": [
            "先建权威再销售：教育型内容做转化引擎",
            "反向营销：让客户/同行讲（peer-to-peer 思想领导力）",
        ],
        "risk": "决策链长周期长；内容投入见效慢；技术导向自嗨",
    },
    "科技": {
        "decision": "中高客单，技术信任+新品节奏",
        "play": "新品发布会事件化 + 场景化演示 + 开发者/用户共创",
        "touchpoints": ["发布会", "场景化Demo", "KOL评测", "社区共创", "渠道"],
        "creative": [
            "让产品自己当主角（用产品拍产品，零后期真实感）",
            "把抽象技术能力变成可参与的体验事件",
        ],
        "risk": "参数内卷；发布即被拆解；技术承诺落空反噬",
    },
    "金融": {
        "decision": "高信任品类，强监管",
        "play": "信任建设 + 场景嵌入 + 教育内容",
        "touchpoints": ["场景化服务", "教育内容", "客户故事", "合规内容", "App"],
        "creative": [
            "把服务嵌入真实生活场景（用渠道解决问题）",
            "用真实客户故事/同行对话建立信任而非自夸",
        ],
        "risk": "强监管红线；收益承诺合规；金融舆情放大",
    },
    "通用": {
        "decision": "视品类而定",
        "play": "洞察先行 + 情绪锚点 + 分阶段整合",
        "touchpoints": ["线上内容", "线下体验", "达人", "私域", "直播"],
        "creative": [
            "找到大众心里已有的文化共识，与品牌自然绑定",
            "让用户从旁观者变成参与者",
        ],
        "risk": "需结合具体品类再评估",
    },
}

PLAN_SECTIONS = [
    ("brief", "Brief 理解与重构"),
    ("insight", "市场与消费者洞察"),
    ("strategy", "核心策略"),
    ("big_idea", "Big Idea / 创意概念"),
    ("creative_landing", "创意落地"),
    ("integration", "整合传播规划"),
    ("media", "媒介与资源"),
    ("kpi", "效果衡量"),
    ("timeline", "执行节奏"),
    ("risk", "风险与合规"),
]


def _human_intro(brand, category, goal, budget, audience):
    return {
        "brief": "客户需求：为「%s」在「%s」品类下实现「%s」。隐藏机会：%s" % (
            brand, category, goal,
            "从「做一场活动」升级为「沉淀一个可持续的品牌资产/机制」（比稿赢在定义问题）"),
        "insight": "先回答 3C：消费者在真实讨论什么（可用 ZBC 舆情主题聚类佐证）、竞争者在占什么心智空位、"
                     "自身有什么可借力的资产（渠道/IP/用户/文化）。目标人群：%s。" % audience,
        "strategy": "定位一句话 + 沟通主题（一句话讲给老板听，讲不清=没想透）。",
        "big_idea": "一句话创意概念 + 情绪锚点 + 为什么成立（对应知识库底层逻辑：洞察先行、情绪共谋、资源内置）。",
        "creative_landing": "主视觉概念 + 2 个关键触点示范（画面感描述，比稿关键）。",
        "integration": "分阶段：蓄水（造期待）→ 引爆（集中资源）→ 持效（沉淀资产），触点组合见品类打法。",
        "media": "预算「%s」分配逻辑：内容生产 X%% / 媒介投放 X%% / 体验与物料 X%% / 数据与工具 X%%（不报死数字也给分配逻辑）。"
                  % (budget or "未定"),
        "kpi": "KPI 分层：声量（曝光/话题量）、互动（UGC 参与）、转化（新客/连带）、资产（私域沉淀），每项给测量方式。",
        "timeline": "里程碑：筹备期（X周）→ 预热蓄水（X周）→ 首发引爆（X周）→ 持效运营（持续），标注关键节点。",
        "risk": "舆情风险预案 + 平台规则 + 合规边界（可用 ZBC 风险引擎支撑，负面率/高敏话题监控）。",
    }


def generate_plan(brand, category="通用", goal="品牌声量提升", budget="", audience="目标人群"):
    pb = CATEGORY_PLAYBOOKS.get(category, CATEGORY_PLAYBOOKS["通用"])
    intros = _human_intro(brand, category, goal, budget, audience)
    plan = {
        "meta": {"brand": brand, "category": category, "goal": goal,
                 "budget": budget, "audience": audience,
                 "decision_profile": pb["decision"]},
        "sections": {},
        "category_playbook": pb["play"],
        "touchpoints": pb["touchpoints"],
        "creative_directions": pb["creative"],
        "risk": pb["risk"],
    }
    for key, label in PLAN_SECTIONS:
        plan["sections"][label] = intros.get(key)
    return plan


def render_text(plan):
    lines = []
    m = plan["meta"]
    lines.append("=" * 60)
    lines.append("可比稿方案骨架：%s（%s）" % (m["brand"], m["category"]))
    lines.append("目标：%s | 预算：%s | 人群：%s" % (m["goal"], m["budget"] or "待定", m["audience"]))
    lines.append("决策特性：%s | 品类打法：%s" % (m["decision_profile"], plan["category_playbook"]))
    lines.append("=" * 60)
    for label, text in plan["sections"].items():
        lines.append("\n【%s】\n%s" % (label, textwrap.fill(text or "-", 68)))
    lines.append("\n创意方向（2 选 1 深化）：")
    for i, c in enumerate(plan["creative_directions"], 1):
        lines.append("  %d. %s" % (i, c))
    lines.append("\n关键触点：%s" % " / ".join(plan["touchpoints"]))
    lines.append("风险提示：%s" % plan["risk"])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="可比稿营销方案引擎")
    ap.add_argument("--brand", default="示例品牌", help="品牌名")
    ap.add_argument("--category", default="通用",
                    choices=list(CATEGORY_PLAYBOOKS.keys()), help="品类")
    ap.add_argument("--goal", default="品牌声量提升", help="营销目标")
    ap.add_argument("--budget", default="", help="预算")
    ap.add_argument("--audience", default="目标人群", help="人群")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    a = ap.parse_args()
    plan = generate_plan(a.brand, a.category, a.goal, a.budget, a.audience)
    if a.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(render_text(plan))


if __name__ == "__main__":
    main()
