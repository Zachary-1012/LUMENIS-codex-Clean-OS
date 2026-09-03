# -*- coding: utf-8 -*-
"""方案需求拆解分析引擎（对标国际公司/品牌公司方法论 × ZBC 分层架构）。

输入：方案需求文本 或 文件(txt/md/json/csv) → 输出：
  1. 要素提取：品牌/品类/预算/圈层/调性/渠道/目标/创意线索
  2. 对标拆解：该品类全球标杆打法 + Gap 分析（缺什么、怎么补）
  3. 创意建议：调 idea_generator 生成原创创意方向
  4. 方案模板脉络：借鉴 ZBC 产品架构分层（数据层/能力层/接口层/展示层/质量层/证据层）

用法：
  from scripts.pitch_parser import analyze_pitch, analyze_pitch_file
  r = analyze_pitch_file("需求.docx" 或 "需求.md" 或 "需求.csv")
  r = analyze_pitch("我们想做... 品牌X 预算100万 目标人群是年轻女性")
"""
import os
import re
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.idea_generator import generate_ideas, CIRCLE_SYMBOLS

# ---- 品类识别（全品类）----
CATEGORIES = {
    "美妆个护": ["美妆", "护肤", "彩妆", "香水", "个护", "洗护", "口腔", "牙膏"],
    "餐饮": ["餐饮", "火锅", "茶饮", "咖啡", "快餐", "烘焙", "甜品", "酒馆", "餐厅"],
    "汽车": ["汽车", "新能源", "4s", "车展", "电动车", "SUV", "出行"],
    "文旅": ["文旅", "景区", "旅游", "度假", "酒店", "民宿", "展览", "博物馆", "乐园"],
    "科技数码": ["科技", "数码", "手机", "电脑", "app", "软件", "智能", "ai", "电子"],
    "金融": ["金融", "银行", "保险", "理财", "基金", "证券", "支付"],
    "服装鞋包": ["服装", "服饰", "鞋", "箱包", "皮具", "高定", "配饰", "珠宝", "腕表"],
    "家居": ["家居", "家具", "家纺", "家电", "厨具", "香薰"],
    "母婴": ["母婴", "奶粉", "尿不湿", "童装", "亲子", "辅食"],
    "运动": ["运动", "健身", "户外", "露营", "瑜伽", "跑鞋"],
    "酒水": ["酒", "白酒", "啤酒", "洋酒", "葡萄酒"],
    "商业地产": ["商场", "mall", "购物中心", "商业地产", "商圈", "街区"],
    "医疗健康": ["医疗", "健康", "保健", "体检", "中医", "营养"],
    "教育培训": ["教育", "培训", "课程", "留学", "考试", "职场培训"],
    "B2B企服": ["企业服务", "saas", "to b", "工业", "供应链", "软件服务"],
    "烟草酒水礼品": ["礼品", "伴手礼", "茶业", "茶叶"],
}

# ---- 圈层识别关键词 → 映射 CIRCLE_SYMBOLS ----
CIRCLE_KEYWORDS = {
    "Z世代潮人": ["年轻", "00后", "z世代", "潮人", "学生", "亚文化", "二次元", "追星"],
    "都市职场": ["职场", "白领", "上班族", "都市", "通勤", "打工人", "精致"],
    "母婴家庭": ["宝妈", "妈妈", "母婴", "亲子", "家庭", "育儿", "新手爸妈"],
    "户外运动": ["户外", "运动", "健身", "露营", "骑行", "跑者", "驴友"],
    "银发健康": ["银发", "老人", "中老年", "长辈", "养生", "退休"],
    "粉丝经济": ["粉丝", "追星", "应援", "饭圈", "代言人", "idol"],
    "高奢小众": ["高净值", "高奢", "贵妇", "藏家", "顶奢", "私域", "小众"],
}

# ---- 调性识别 ----
TONALITY_KEYWORDS = {
    "luxury": ["高奢", "顶奢", "重奢", "贵妇", "稀缺", "限量", "工艺", "传世", "高定", "私享", "顶级"],
    "premium": ["高端", "中高端", "质感", "精致", "格调", "品味", "生活方式"],
    "mass": ["大众", "破圈", "全民", "狂欢", "走量", "流量", "网红", "爆款"],
}

# ---- 渠道识别 ----
CHANNEL_KEYWORDS = ["小红书", "抖音", "微博", "微信", "公众号", "视频号", "快手", "B站", "b站",
                    "知乎", "线下", "门店", "直播", "私域", "社群", "电商", "淘宝", "天猫", "京东", "海外"]

# ---- 目标识别 ----
GOAL_KEYWORDS = {
    "销量转化": ["销量", "转化", "卖货", "成交", "复购", "GMV", "带货"],
    "品牌建设": ["品牌", "形象", "认知", "心智", "溢价", "资产"],
    "声量传播": ["声量", "曝光", "热度", "破圈", "话题", "热搜", "传播"],
    "新品上市": ["新品", "上市", "发布", "首发", "上新"],
    "展览活动": ["展览", "活动", "快闪", "event", "event", "发布会", "开业"],
    "客户获取": ["拉新", "获客", "涨粉", "引流", "到店"],
    "舆情风险": ["舆情", "公关", "危机", "负面", "口碑", "恢复"],
}

# ---- 品类全球标杆打法库（对标国际公司/品牌公司 + 2026 最新案例）----
BENCHMARKS = {
    "美妆个护": ("Aesop / 欧莱雅 / eos / Dove", "Aesop 以实验室棕瓶+文学艺术构筑小众审美定义者；eos 用持续成功塑造女性剃须话语权；Vaseline 把用户 hack 变成产品线(UGC→产品飞轮)；Dove 2026『Unfiltered Feed』把账号交给22位微创作者30天=约束本身即故事(3.4亿曝光+28%购买意向)。"),
    "餐饮": ("太二 / McDonald's / Lay's / Wendy's", "造节(太二运动会)+符号化(麦当劳金拱门)+幽默梗(Lay's 玩球星纸条)；Wendy's 2026 CTV 实时比分广告(API驱动90s更新一次,游戏夜订单+9%)——实时创意在直播环境即竞争力。"),
    "汽车": ("Tesla / Porsche / Hyundai", "Tesla 事件化(发布即热搜)；保时捷克制与赛道故事；Hyundai 2026 用虚拟人 Kenza Layli(跨文化多语言)做新品发布,ROI 20x。"),
    "文旅": ("阿那亚 / Disney / 环球影城", "阿那亚用社群与精神地标打造生活方式共同体；Disney 用世界观(world-building)让游客进入叙事。体验+世界观是核心。"),
    "科技数码": ("Apple / Claude(Anthropic) / Nike×Lisa", "Apple 2026『Designed by Humans』全AI时代反着只做印刷长文(稀缺媒介即定向)；Claude by Mother 用两个简单问题(『能快速六块腹肌吗』『怎么和妈妈沟通』)讲AI的角色——Film GP;Nike 用文化碰撞破圈。"),
    "金融": ("AXA / BCP(SOS POS) / 招商银行", "AXA 把家暴条款植入保险=产品即创意；BCP 2026『SOS POS』把POS终端变紧急保护点(用投诉+位置数据)→Creative Data GP,触达3400万人；招行用私域+温度叙事。"),
    "服装鞋包": ("Hermès / Goyard / Brunello Cucinelli / adidas", "Hermès 计算型稀缺；Goyard 全球仅30店不线上不标价；Brunello 信任小圈层；adidas 2026『Original Forever』(Johannes Leonardo)用音乐+文化记忆拿双 GP。"),
    "家居": ("IKEA / 观夏 / Aesop", "IKEA 超级碗二屏互动+2026 Hope/Mornings/Picky 电影级短片；观夏以东方叙事+节气仪式感做香氛；家居=生活方式提案。"),
    "母婴": ("balabala / 帮宝适 / Slurrp Farm", "情感成长刻度+科学背书；Slurrp Farm(印度婴食)用 lo-fi 厨房视频(真实父母做饭)替代棚拍,IG互动3x——不完美=真实信号。"),
    "运动": ("Nike / lululemon / On昂跑", "Nike 2026『Unwitnessed』关停付费社媒6周转超本地OOH(零运动员,城市环境音QR解锁歌单,情绪+14点)——品牌出乎意料即earned media；lululemon 社群；On 精英共鸣。"),
    "酒水": ("茅台 / 可口可乐JUMP / Heineken", "茅台高端宴请符号化；可乐怀旧版权跨代共鸣；Heineken 2026『Could Have Been a Heineken』(错失即话题)Social&Creator GP。"),
    "商业地产": ("太古里 / SKP / 阿那亚", "太古里街区感+首店经济；SKP 高奢矩阵+私域；阿那亚社群运营。体验+圈层运营是核心。"),
    "医疗健康": ("汤臣倍健 / 东阿阿胶", "科学背书+场景化(节日送礼)+信任资产。"),
    "教育培训": ("得到 / Duolingo", "Duolingo 用玩梗与病毒机制做参与式学习；得到用知识IP社群。"),
    "B2B企服": ("Salesforce / HubSpot / Spotify", "内容即产品+客户成功故事；Spotify 2026『Listening Proof』向CMO自嘲式广告自己的广告平台(『是的,这广告正跑在Spotify上』)→Cannes Media Lion——平台自我营销即创意。"),
    "烟草酒水礼品": ("小罐茶 / 观夏", "礼品=仪式感+身份符号；小罐茶标准化+大师背书；观夏节气东方叙事。"),
}

# ---- 方案模板脉络（借鉴 ZBC 产品架构分层）----
# ZBC: 数据层 → 能力层 → 接口层(Contract) → 展示层 → 质量层 → 证据层
PITCH_TOC = [
    {"sec": "01 背景与市场", "layer": "数据层", "desc": "市场/消费者/竞品/自身真实数据（决策信息优先，不堆文字）"},
    {"sec": "02 洞察与策略", "layer": "能力层", "desc": "核心洞察→策略主张→定位（数据信号升维成一句话策略）"},
    {"sec": "03 创意构想", "layer": "能力层", "desc": "Big Idea + 机制（事件化/参与式/符号化/共创/反差/文化共识）"},
    {"sec": "04 传播与触点", "layer": "接口层", "desc": "渠道组合（小红书/抖音/线下/私域）× 每触点的 Contract 与内容"},
    {"sec": "05 执行落地", "layer": "展示层", "desc": "节奏排期/物料清单/团队分工/预算拆解"},
    {"sec": "06 效果与度量", "layer": "展示层", "desc": "KPI/ROI/数据看板（曝光/互动/转化/复购/心智指标）"},
    {"sec": "07 风险与合规", "layer": "质量层", "desc": "舆情/平台规则/法律/合规 Gate + 应急预案"},
    {"sec": "08 证据与附录", "layer": "证据层", "desc": "数据来源/竞品参考/引用（一切结论可追溯）"},
]


def detect_category(text):
    for cat, kws in CATEGORIES.items():
        for k in kws:
            if k.lower() in text.lower():
                return cat
    return "通用"


def detect_circle(text):
    best, score = None, 0
    for c, kws in CIRCLE_KEYWORDS.items():
        s = sum(1 for k in kws if k in text)
        if s > score:
            best, score = c, s
    return best or "都市职场"


def detect_tonality(text):
    for t, kws in TONALITY_KEYWORDS.items():
        if any(k in text for k in kws):
            return t
    return "premium"


def detect_channels(text):
    return [c for c in CHANNEL_KEYWORDS if c in text]


def detect_goals(text):
    return [g for g, kws in GOAL_KEYWORDS.items() if any(k in text for k in kws)]


def detect_budget(text):
    m = re.findall(r"(预算[^\d]{0,4}|投入[^\d]{0,4})?\s*(\d+(?:\.\d+)?)\s*(万|亿|w|k|百万)?", text)
    for prefix, num, unit in m:
        if num:
            return {"value": float(num), "unit": unit or "万"}
    return None


def detect_brand(text, hint=""):
    if hint:
        return hint
    m = re.search(r"品牌[是为叫]?\s*[「『\"]?([\u4e00-\u9fa5A-Za-z0-9]{2,12})", text)
    if m:
        return m.group(1)
    return "待定品牌"


def extract_creative_leads(text):
    """抓取方案里的创意线索/约束（一句话原则，供创意引擎参考）。"""
    leads = []
    for pat in [r"(?:创意方向|核心方向|创意)[是为]?[：:，,]?\s*([^。；\n]{4,40})",
                r"(?:核心主张|品牌概念)[是为]?[：:，,]?\s*([^。；\n]{4,40})",
                r"(?:主打|核心卖点|诉求)[是为]?[：:，,]?\s*([^。；\n]{4,40})"]:
        m = re.search(pat, text)
        if m:
            leads.append(m.group(1).strip())
    return leads[:3]


def build_benchmark(category, tonality, circle):
    name, how = BENCHMARKS.get(category, ("行业头部", "以真实数据/真实用户/真实结果为第一原则"))
    return {"category": category, "benchmark": name, "playbook": how,
            "gap_questions": [
                "你的核心数据证据是否支撑洞察？（数据层）",
                "有没有一个可复制/可记忆的符号？（符号化）",
                "用户参与机制在哪？互动即传播？（参与式）",
                "是否绑定当下的文化时机/热点？（时效）",
                "调性「%s」与圈层「%s」的沟通语言是否一致？" % (tonality, circle),
            ]}


def analyze_pitch(text, brand_hint="", n_ideas=3, hotspot=""):
    """主入口：方案需求文本 → 拆解分析。"""
    category = detect_category(text)
    circle = detect_circle(text)
    tonality = detect_tonality(text)
    signals = {"topics": extract_creative_leads(text), "sentiment": "neutral",
               "negative_rate": 0.0, "risk_events": 0, "circle": circle,
               "hotspot": hotspot, "volume_notes": 0}
    ideas = generate_ideas(detect_brand(text, brand_hint), category, signals, n_ideas, tonality)
    return {
        "extracted": {
            "brand": detect_brand(text, brand_hint),
            "category": category,
            "budget": detect_budget(text),
            "circle": circle,
            "tonality": tonality,
            "channels": detect_channels(text),
            "goals": detect_goals(text),
            "creative_leads": extract_creative_leads(text),
        },
        "benchmark": build_benchmark(category, tonality, circle),
        "ideas": ideas,
        "pitch_toc": PITCH_TOC,
    }


def analyze_pitch_file(path, brand_hint="", n_ideas=3, hotspot=""):
    """从文件导入方案需求：支持 txt/md/json/csv。"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        data = json.load(open(path, encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False)
    elif ext == ".csv":
        import csv
        rows = []
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.reader(f):
                rows.append(" ".join(c for c in r if c))
        text = "\n".join(rows)
    else:  # txt / md / 其他文本
        text = open(path, encoding="utf-8", errors="ignore").read()
    r = analyze_pitch(text, brand_hint, n_ideas, hotspot)
    r["source_file"] = path
    return r


def main():
    import argparse
    ap = argparse.ArgumentParser(description="方案需求拆解分析引擎")
    ap.add_argument("input", nargs="?", default="", help="方案需求文本或文件路径(txt/md/json/csv)")
    ap.add_argument("--brand", default="", help="品牌名(兜底)")
    ap.add_argument("--hotspot", default="", help="时效热点")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    if a.input and os.path.isfile(a.input):
        r = analyze_pitch_file(a.input, a.brand, a.n, a.hotspot)
    else:
        r = analyze_pitch(a.input, a.brand, a.n, a.hotspot)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
