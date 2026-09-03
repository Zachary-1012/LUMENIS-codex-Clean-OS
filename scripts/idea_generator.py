# -*- coding: utf-8 -*-
"""数据驱动原创创意生成器 V2（反模板化：多维组合引擎）。

对标全球 4A（阳狮/Ogilvy/WPP/戛纳范式）× ZBC 真实数据。
V2 核心升级（针对 V1 模板填空缺陷）：
  1. 反模板化：同一机制不再固定一句式，而是「机制 × 张力句式库 × 角度 × 语义角色」多维组合，
     同一主题可产出观点、行动、故事、反转、共创、文化暗语等多种张力表达，禁止重复循环。
  2. 语义角色：中文主题词先做语义角色推断（空间/活动/美食/服务/权益/节点/IP/情绪），
     用对应意象槽位，而非把词生硬塞进句式。
  3. 预算感知：新增 budget(low/mid/high) 维度，同一品牌同一主题不同预算产出不同落地档位
     （轻内容玩法 / 单点事件+达人 / 全链路战役），适配每次报价/预算调整。
  4. 角度(Angle)：消费者视角/品牌自省/圈层暗语/场景时间/反叛/共创——同一主题不同切入人设。
  5. 多样性控制：批次内句式不重复、槽位语义去重、机制轮转 + 随机张力选型。

Contract 不变：仍输出 meta/ideas，每个 idea 保留 mechanism/big_idea/concept/why/circle/
circle_symbols/tonality/timeliness/touchpoints/virality/provenance；新增 angle/execution。
芥子→须弥 provenance 机制（evidence_level/confidence 封顶/负样本待检）保持不变。

用法：
  from scripts.idea_generator import generate_ideas, signals_from_db
  s = signals_from_db("data/monitor.db", "太古汇", circle="都市高净值", hotspot="15周年")
  ideas = generate_ideas("某品牌", "商业地产", s, n=6, tonality="premium", budget="mid")
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 圈层符号语言（人群 → 沟通语言/符号体系）----
CIRCLE_SYMBOLS = {
    "Z世代潮人": {"lang": "玩梗/反差/亚文化/圈层暗语", "symbols": ["暗语", "梗图", "共创", "remix"],
                  "examples": "王老吉x哈兰德《Haaland Song》魔性共创"},
    "都市职场": {"lang": "反内卷/情绪出口/效率/精致", "symbols": ["解压", "摸鱼经济学", "通勤场景", "搭子"],
                "examples": "Coca-Cola AFK 文化：放下手机回到餐桌"},
    "母婴家庭": {"lang": "安全感/成长/温情", "symbols": ["成长刻度", "亲子时刻", "安心", "第一次"],
                "examples": "balabala《中国小朋友》"},
    "户外运动": {"lang": "自由/突破/自然", "symbols": ["征服", "山野", "赛道", "能量"],
                "examples": "Nike x Lisa《Rip The Script》文化碰撞"},
    "银发健康": {"lang": "陪伴/安心/养生", "symbols": ["老友", "体面", "慢生活", "邻里"],
                "examples": "小方同学卯发：卯时新生"},
    "粉丝经济": {"lang": "应援/共创/身份认同", "symbols": ["应援色", "舞台", "pick", "打call"],
                "examples": "Uva Uva Bombón：Bad Bunny 唱名即解锁"},
    "高奢小众": {"lang": "克制/稀缺/工艺/安静奢华", "symbols": ["限量", "稀缺", "手作", "仪式感", "私密"],
                 "examples": "Hermès 计算型稀缺 / Goyard 不广告不代言 / Ffern 四季限量"},
    "都市高净值": {"lang": "质感/稀缺/圈子认同/体面", "symbols": ["限量", "圈层", "体面", "品味", "私享"],
                  "examples": "太古汇/连卡佛 高净值生活方式场域"},
    "年轻潮流": {"lang": "酷/新鲜/反差/打卡", "symbols": ["新店", "打卡", "氛围感", "宝藏", "反差"],
                "examples": "新店首发/氛围感打卡/宝藏挖掘"},
    "疗愈系": {"lang": "悦己/情绪出口/慢疗愈", "symbols": ["治愈", "情绪出口", "慢下来", "自我关怀", "松弛感"],
               "examples": "Aesop 感官疗愈门店 / 颂钵声疗体验"},
    "露营旷野": {"lang": "自由/回归自然/临时社群", "symbols": ["营地", "篝火", "野趣", "逃离", "星空"],
                 "examples": "Snow Peak 露营节 / 城市青年一夜出逃"},
    "夜生活": {"lang": "松弛/微醺/社交暗语", "symbols": ["微醺", "bistro", "夜猫子", "局", "氛围感酒馆"],
               "examples": "夜经济街区 / 精酿厂牌社群"},
}

# 调性（影响创意气质与机制）：大众狂欢 vs 中端种草 vs 高奢克制
TONALITIES = {
    "mass": {"name": "大众", "style": "狂欢放大、参与机制、玩梗破圈"},
    "premium": {"name": "中高端", "style": "场景种草、质感叙事、圈层认同"},
    "luxury": {"name": "高奢", "style": "克制叙事、稀缺仪式、工艺故事、不参与流量狂欢"},
}

# ---- 情绪基调 → 创意风格 ----
EMOTION_STYLES = {
    "positive": "庆祝共鸣·狂欢放大（借势情绪顶点）",
    "neutral": "认知觉醒·场景种草（先种草后转化）",
    "negative": "危机共情·诚实解决（先止血再借势）",
}

# ---- 创意机制（知识库底层逻辑 × 全球4A范式）----
MECHANISMS = {
    "eventify": {"name": "事件化", "desc": "把抽象卖点/概念变成可参与的体验事件"},
    "participate": {"name": "参与式", "desc": "让用户从旁观者变玩家，参与机制即传播"},
    "symbolize": {"name": "符号化", "desc": "生成一个可记忆可复制的符号/口号/图腾"},
    "reverse": {"name": "反差", "desc": "反常识断言制造话题"},
    "cocreate": {"name": "共创式", "desc": "把用户自发行为变成产品/内容飞轮"},
    "culture": {"name": "文化共识", "desc": "借势已有文化共识/圈层暗语自然绑定"},
    "resonate": {"name": "情感共鸣", "desc": "韩剧×文学式表达：以小写大/时间具象/朴素真话/边界/悖论，直击人心非信息传递"},
}

MECH_TO_L1 = {
    "eventify": "事件化体验公式（造事-造势-造市）",
    "participate": "参与式传播公式（用户即媒介）",
    "symbolize": "符号化记忆公式（可复制图腾）",
    "reverse": "反差断言公式（反常识破圈）",
    "cocreate": "UGC 共创飞轮公式",
    "culture": "文化共识借势公式",
    "resonate": "情感共鸣公式（以小写大·具象抒情·悖论并置）",
}

# ---- 角度：同一主题的不同切入人设（防止"主题换了，创意没换"）----
ANGLES = {
    "consumer": "消费者视角（替目标人群说出心声）",
    "introspect": "品牌自省（敢于自我调侃/反推销）",
    "coded": "圈层暗语（懂的人才懂，制造专属感）",
    "scene": "场景时间（把主题放进某个真实时刻/地点）",
    "rebel": "反叛视角（挑战刻板印象/既定答案）",
    "cocreate": "共创视角（把定义权交给用户）",
}

# ---- 主题词语义角色推断（中文2-gram→语义类，供意象槽位选择）----
_TOPIC_ROLE_RULES = [
    (("方所", "书店", "展览", "美术馆", "空间", "商场", "天台", "中庭", "店"), "space", "空间/场域"),
    (("面包", "美食", "餐厅", "咖啡", "甜品", "茶", "火锅", "探店", "吃喝", "米其林"), "food", "美食/体验"),
    (("停车", "排队", "退换", "投诉", "服务", "预约", "积分", "会员", "售后", "权益"), "service", "服务/权益"),
    (("周年", "节日", "圣诞", "新年", "周年庆", "开箱", "首发", "预售", "快闪"), "event", "节点/活动"),
    (("米奇", "联名", "IP", "限量", "上新", "新款", "限定"), "ip", "IP/联名/限定"),
    (("拍照", "打卡", "氛围", "美", "出片", "颜值"), "aesthetic", "颜值/出片"),
    (("美妆", "护肤", "香水", "面膜", "彩妆", "口红", "洗护", "面霜", "精华"), "beauty", "美妆/悦己"),
    (("母婴", "亲子", "宝宝", "育儿", "童装", "玩具", "纸尿裤"), "family", "母婴/家庭"),
    (("户外", "露营", "徒步", "山野", "骑行", "跑步", "越野", "运动"), "sport", "户外/运动"),
    (("酒", "威士忌", "精酿", "鸡尾酒", "红酒", "咖啡豆", "烘焙"), "wine", "酒饮/社交"),
]
_TOPIC_ROLE_DEFAULT = ("general", "通用")
_TOPIC_ROLE_IMAGES = {
    "space": {"mass": "打卡地标", "premium": "值得专程的场域", "luxury": "安静的收藏级空间"},
    "food": {"mass": "好吃到想炫耀", "premium": "值得专程的味道", "luxury": "值得慢品的手作味道"},
    "service": {"mass": "不踩坑攻略", "premium": "体面省心的体验", "luxury": "不动声色的周到"},
    "event": {"mass": "限时狂欢", "premium": "一年一次的事", "luxury": "一年只做一次的事"},
    "ip": {"mass": "限定联名", "premium": "限量上新", "luxury": "限量即稀缺"},
    "aesthetic": {"mass": "出片圣地", "premium": "氛围感拉满", "luxury": "克制的审美仪式"},
    "beauty": {"mass": "变美打卡", "premium": "悦己的仪式感", "luxury": "不动声色的精致"},
    "family": {"mass": "亲子欢乐场", "premium": "有温度的共同成长", "luxury": "珍藏的成长时刻"},
    "sport": {"mass": "燃起来", "premium": "自在山野的松弛", "luxury": "克制而有力的远行"},
    "wine": {"mass": "一起喝一杯", "premium": "值得慢品的味道", "luxury": "陈年后的分享"},
    "general": {"mass": "宝藏新发现", "premium": "质感新体验", "luxury": "难得的质感"},
}


def _topic_role(topic):
    """把中文主题词映射到语义角色（空间/美食/服务/节点/IP/颜值/通用），供意象槽位。"""
    for keys, role, _name in _TOPIC_ROLE_RULES:
        if any(k in topic for k in keys):
            return role
    return _TOPIC_ROLE_DEFAULT[0]


# ---- 张力句式库（反模板核心）：每个句式一条"有张力的表达"，非填空壳 ----
# 槽位：{brand} 品牌  {topic} 主题  {c0} 圈层名  {img} 主题意象  {sym} 圈层符号  {hot} 热点
_HOOK = {
    # 主张型（立场/态度，适合 symbolize/culture）
    "assert": [
        "「{c0}的{topic}，从来不止一种答案」——{brand}，把{topic}还给生活",
        "「真正的{topic}，{brand}很少说」——留给懂的人自己发现",
        "「{topic}，是{brand}最低调的骄傲」——不声张，但不缺席",
        "「别问{brand}的{topic}贵不贵，问它值不值得」——{img}，本来就不赶时间",
        "「{img}，是{brand}给{topic}的体面」——{c0}都懂",
    ],
    # 行动型（号召/动词转换，适合 participate/eventify）
    "imperative": [
        "「来{brand}，把{topic}过成今天最重要的事」——{img}，从此刻开始",
        "「在{brand}，{topic}从『看』变成『玩』」——{c0}的新玩法",
        "「把{topic}留到周末，来{brand}认真浪费一次」——浪费时间，也值得",
        "「别只收藏，来{brand}把{topic}『用』一次」——{img}，眼见为实",
        "「{hot}来了，{topic}也该换一种过法」——来{brand}，{img}",
    ],
    # 故事型（场景/悬念开场，适合 eventify）
    "story": [
        "「有人为了{brand}的{topic}，跑了半个城」——{img}，值得专程",
        "「第一次来{brand}的人，都先问{topic}在哪」——后来都成了常客",
        "「在{brand}，有人为{topic}来了七次」——{img}，每一次都不同",
        "「{c0}的私藏清单里，{brand}的{topic}排第一」——{img}，才舍得分享",
        "「那天路过{brand}，发现{topic}变了」——{img}，是时候重新认识",
    ],
    # 反转型（反常识断言，适合 reverse）
    "reversal": [
        "「{brand}劝你别只看{topic}」——{img}，好戏在后面",
        "「没人规定{topic}要很贵」——{brand}的{topic}，主打一个值",
        "「{brand}的{topic}，不排队」——稀有，但不必争抢",
        "「别一上来就{topic}，先逛逛再说」——{brand}，值得慢慢来",
        "「都说{topic}是{img}，{brand}偏要说不止于此」——{c0}，亲自来验",
    ],
    # 共创型（把定义权交给用户，适合 cocreate/participate）
    "cocreate": [
        "「{topic}怎么玩，{c0}说了算」——{brand}搭台，你来唱戏",
        "「你的{topic}，{brand}来搭台」——{img}，由你定义",
        "「把{topic}交给懂它的人」——{brand}，只做最懂{img}的那一档",
        "「{c0}共创的{topic}，正在{brand}发生」——你也可以参与定义",
        "「{#话题#}，{brand}帮你把{topic}玩成限量版」——{img}，由你收藏",
    ],
    # 文化共识型（圈层暗语/趋势 + 名句重构 remix，适合 culture）
    "culture": [
        "「{c0}都懂的{topic}，{brand}替你准备好了」——{img}，心照不宣",
        "「{topic}正在成为{c0}的新暗号」——{brand}，站在暗号中心",
        "「{sym}这件事，{c0}只在{brand}聊」——{topic}，圈内人才懂",
        "「{hot}里，{c0}都在追{brand}的{topic}」——{img}，先到先得",
        "「{c0}的{topic}审美，被{brand}接住了」——{img}，刚刚好",
        # 名句重构 remix（arXiv 2602.06049 范式：名言结构+词汇替换，新颖×熟悉）
        "「吾日三省吾身：{topic}、{topic}、还是{topic}」——{brand}，{c0}的{img}",
        "「山不在高，有仙则名」——{brand}的{topic}，不在多，在{img}",
        "「人生得意须尽欢」——{topic}，就该在{brand}过成{img}",
        "「来都来了」——{topic}当然要过成{img}，{brand}都替{c0}想好了",
    ],
}

# 高奢专属：克制叙事句库（不玩梗、不狂欢）
_HOOK_LUX = {
    "assert": [
        "「{brand}的{topic}，安静到值得专程」——{img}，不喧哗自有声",
        "「{topic}这件事，{brand}只做给少数人看」——{img}，稀缺即诚意",
        "「{topic}，是{brand}写给{c0}的一封安静的信」——{img}，慢慢读",
    ],
    "imperative": [
        "「来{brand}，赴一场{topic}之约」——{img}，一年一次",
        "「{topic}，留给愿意专程的人」——{brand}，不邀不请",
    ],
    "story": [
        "「有人为{brand}的{topic}，等了整整一年」——{img}，值得",
        "「{c0}的{topic}，只在{brand}对少数人开放」——{img}，私享",
    ],
    "reversal": [
        "「{brand}不谈{topic}有多好，只做{topic}该有的样子」——{img}",
        "「我们不把{topic}讲大声」——{brand}，{img}自有分寸",
    ],
    "cocreate": [
        "「{topic}，由藏家与匠人共同定义」——{brand}，{img}的默契",
        "「{brand}的{topic}，只邀请懂它的人」——{img}，心领神会",
    ],
    "culture": [
        "「{c0}的{topic}暗语，{brand}听得懂」——{img}，心照不宣",
        "「{topic}，是{brand}与{c0}之间的默契」——{img}，不解释",
        # 高奢名句重构 remix（大隐隐于市 / 陋室铭）
        "「大隐隐于市」——{brand}的{topic}，{img}，只给懂的人",
        "「无丝竹之乱耳，无案牍之劳形」——{brand}的{topic}，是{c0}的{img}",
    ],
}

# ---- 情感共鸣句库（韩剧×全球文学表达手法：直击人心，非信息传递）----
# 手法来源（研究沉淀）：
#   ① 以小写大：日常细节承载大情感（如「因为你是我妈妈，所以我喜欢你，这不是应该的吗」）
#   ② 时间/天气具象化：用天气季节写抽象感受（如《鬼怪》「无论天气好/坏/适宜，每一天都很美好」）
#   ③ 朴素真话：平民视角戳破伪装的反常识真话（如《我的出走日记》）
#   ④ 越界即张力：边界与危险感制造情感张力（如《爱的迫降》「越过这条线，你真的会变得危险」）
#   ⑤ 不说破的深情：用行为/限定词替代直白告白（Tatler: lines that sound better than 'I love you'）
#   ⑥ 条件句预言/希望：自然意象+条件句（如雪莱「如果冬天来了，春天还会远吗」）
#   ⑦ 悖论并置：让相反真理共存（如托尔斯泰「幸福的家庭都是相似的，不幸的各有各的不幸」）
#   ⑧ 刺破本质的陈述：表面共识、实则反讽（如《傲慢与偏见》开篇）
# 海外策略层（2026 海外社媒算法研究）：signals["overseas"]=True 时替换 touchpoints/virality
_OVERSEAS_TOUCH = ["TikTok Spark Ads 原生分发", "IG Reels/Stories 双链路", "KOC 金字塔共创",
                   "独立站/小店站内闭环", "搜索关键词内容卡位"]
_OVERSEAS_VIRAL = ("海外算法：收藏/分享权重>点赞——内容可收藏化（教程/攻略/避坑）激发长尾；"
                   "First-Party 原创素材权重加成；前3秒直击痛点避免标题党；"
                   "真人出镜/原生UGC建立信任；把卖点埋进用户主动搜索词")
_HOOK_EMO = {
    "emo_heart": [  # 以小写大
        "{c0}说「不就是{topic}吗」——{brand}说，正因为是{topic}，才值得{img}",
        "因为{topic}是日常，所以{brand}值得，这不是应该的吗——{c0}，都懂",
        "「把{topic}过好，是{c0}给自己的生活交代」——{brand}，只做{img}这一件小事",
    ],
    "emo_time": [  # 时间/天气具象化
        "天气好的日子、天气坏的日子、天气刚刚好的日子——与{topic}有关的每一天，{brand}都在，{img}",
        "{topic}的日子有晴天也有雨天，但来{brand}的这一天，都值得好好过——{c0}，{img}",
        "四季会换，{topic}会变——{brand}的{img}，一年只等一次",
    ],
    "emo_truth": [  # 朴素真话 / 戳破伪装
        "{c0}不说的实话：{topic}，其实是你给自己的交代——{brand}，替你把{img}准备好",
        "别再假装不需要{topic}了——{c0}都会在某个瞬间，想被{brand}的{img}接住",
        "生活已经够忙了，{topic}就该简单点——{brand}，把{img}留给你",
    ],
    "emo_edge": [  # 越界即张力
        "跨过这条线，你就真的离{topic}近了——{brand}的{img}，在等你",
        "别靠{topic}太近——{brand}的{img}，会上瘾",
        "「就试这一次」——{c0}每次这么想，都走不出{brand}的{topic}",
    ],
    "emo_unspoken": [  # 不说破的深情
        "不必说{topic}有多好——{brand}替你记住值得来的那天，{img}",
        "我们不谈{topic}，只把{img}准备好，等你来{brand}",
        "{c0}最懂：有些{topic}，不用说出口，{brand}已经做了",
    ],
    "emo_omen": [  # 条件句预言 / 希望
        "如果今天不够好，就来{brand}——{topic}之后，总有{img}",
        "等{topic}的那天，{brand}把{img}也一起等来了——{c0}，别错过",
        "只要你还愿意来，{brand}的{topic}就永远是{img}——风雨无阻",
    ],
    "emo_paradox": [  # 悖论并置
        "好的{topic}都是相似的，值得专程的{img}却各有各的不同——{brand}，{c0}都懂",
        "我们用{img}把{topic}变简单，却让{c0}的日子复杂了一点——{brand}，故意的",
        "越热闹的{topic}越像{img}，越安静的{brand}越值得——{c0}，慢慢品",
    ],
    "emo_query": [  # 反问推理（莎士比亚 "What's in a name?"：把犹豫变成提问，答案自现）
        "{topic}是什么？{brand}说，是{img}——{c0}心里，其实早有答案",
        "谁规定{topic}必须是这样？——{brand}，{img}，不信这一套",
        "如果没有{brand}，{c0}的{topic}会少点什么？——{img}，答案在来的路上",
    ],
    "emo_repeat": [  # 首语重复/无连词排比（anaphora/asyndeton：重复即强调，排比即气势）
        "不赶路，不将就，不解释——{brand}的{topic}，{img}",
        "今天不追{topic}，今天不敷衍，今天只做{img}——{brand}，{c0}都懂",
        "好的{topic}，慢一点；好的{img}，等一会；好的{brand}，不急",
    ],
    "emo_mirror": [  # 交错配列（chiasmus："Fair is foul, and foul is fair" 两轴对仗，制造闭环）
        "{topic}是{c0}的日常，{c0}的日常里有{img}——{brand}，把这两件事做成一件",
        "你在找{topic}，{topic}也在找你——{brand}，{img}，双向奔赴",
        "{c0}离不开{topic}，{topic}离不开{img}，{img}离不开{brand}——一圈，刚好",
    ],
    "emo_slant": [  # 留白/斜着说（俳句×狄金森：不点破，用画面+停顿，把余味留给读者）
        "雨停的时候，{topic}刚好。{brand}，{img}——剩下的话，不说了",
        "{topic}的事，说一半，留一半——{brand}的{img}，另一半你自己来",
        "暮色四合，{topic}还没有走。{brand}的{img}，也在等——等一个不赶时间的人",
    ],
    "emo_season": [  # 季语/物候（俳句 kigo：季节意象触发集体记忆，一年一季的限定感）
        "桂花开的月份，{topic}正好——{brand}的{img}，一年一季",
        "第一场雨落下来的时候，{topic}就换了样子——{brand}，{img}，应季而至",
        "这个季节的{topic}，是{brand}留给{c0}的{img}——过了，就要再等一年",
    ],
    "emo_surreal": [  # 魔幻现实（日常中的超现实：马尔克斯式，让平凡长出魔法）
        "如果{topic}会说话，它会说：{img}——{brand}，{c0}的魔法日常",
        "在{brand}，{topic}会迷路，会等一整个黄昏，然后把自己变成{img}——{c0}都见过",
        "据说{topic}每年来{brand}一次，来时带着{img}——{c0}，别问真假，来了就知道",
    ],
    "emo_understate": [  # 轻描淡写（understatement：把大事说小，反衬更大张力）
        "{topic}嘛，{brand}只是把它做得刚刚好——{img}，不值一提",
        "没什么特别的，{brand}的{topic}就是{img}——{c0}都这么说",
        "{topic}不难，{brand}只是替{c0}多走了几步——{img}，而已",
    ],
    # —— 品类情感手法（2026 智谱 web_search 研究落地：美妆疗愈/母婴/户外/酒类）——
    # 原则：克制比浓烈更治愈，拒绝宏大词，用微小细节写真实情绪
    "emo_sensory": [  # 感官通感（触觉/嗅觉/听觉具象承载情绪）
        "{topic}的质感，像{img}落在指腹——{brand}，替{c0}记得那种触感",
        "闻见{topic}的气息，就像回到某个下午——{brand}的{img}，是记忆的开关",
        "{topic}的声音很轻，轻得像{img}——{brand}，{c0}听了就知道",
    ],
    "emo_self": [  # 悦己和解（不是想变成谁，只是更真实一点）
        "不是想躲开{topic}，只是想对自己真实一点——{brand}，{img}，为自己",
        "{c0}不必把{topic}过成标准答案——{brand}，{img}，做自己就好",
        "把{topic}留一点给{img}——{brand}相信，{c0}值得被好好对待",
    ],
    "emo_nature": [  # 自然对白（自然元素×身体感知，自由留白）
        "{topic}的风一吹，{c0}就松开了——{brand}的{img}，在远处等你",
        "走到{topic}那里，山会替你回答——{brand}，{img}，不必赶路",
        "{topic}在路尽头，{brand}把{img}铺到脚下——{c0}，出发就是答案",
    ],
    "emo_grow": [  # 共同生长（不刻意、日常仪式、一起慢慢来）
        "{topic}不是赶出来的，是{brand}和{c0}一起慢慢长成的——{img}，不急",
        "每天一点点，{topic}就和{img}一起长大了——{brand}，陪着{c0}",
        "{brand}相信：{topic}最好的样子，是{c0}一起{img}的样子",
    ],
}

# 高奢版情感共鸣：安静克制，不煽情
_HOOK_EMO_LUX = {
    "emo_heart": [
        "「{topic}最好的样子，是留给愿意慢下来的人」——{brand}，{img}不催",
    ],
    "emo_time": [
        "一年里总有几天，值得为{topic}专程——{brand}，{img}只在对的时刻",
    ],
    "emo_truth": [
        "{c0}都明白：真正的{topic}，不必说给所有人听——{brand}，{img}自有分量",
    ],
    "emo_edge": [
        "「别惊动它」——{brand}的{topic}，{img}，只可静观",
    ],
    "emo_unspoken": [
        "不必开口，{brand}的{topic}自会说话——{img}，安静自有分量",
    ],
    "emo_omen": [
        "若你愿意等，{brand}的{topic}会以{img}的方式到来——{c0}，不失约",
    ],
    "emo_paradox": [
        "我们少说一点{topic}，多留一点{img}——{brand}，与{c0}心照不宣",
    ],
    "emo_query": [
        "{topic}是什么，{brand}不急着回答——{img}，慢慢品，答案自会来",
    ],
    "emo_repeat": [
        "不声张，不示弱，不追赶——{brand}的{topic}，{img}，自有章法",
    ],
    "emo_mirror": [
        "你在找{topic}，{topic}也在等你——{brand}，{img}，隔着一整个城市的安静",
    ],
    "emo_slant": [
        "灯亮起来的时候，{topic}刚好。{brand}，{img}——余下的，各自体会",
    ],
    "emo_season": [
        "这个季节的{topic}，一年只有一次——{brand}，{img}，如约而至",
    ],
    "emo_surreal": [
        "在{brand}，{topic}会放慢脚步，把自己藏进{img}——{c0}，心照不宣",
    ],
    "emo_understate": [
        "{topic}，{brand}只是做得安静些——{img}，不必多言",
    ],
    # —— LUX 专属：2026 全球高奢/低调小众"去噪"叙事（智谱 web_search 研究 2026-09-03 落地）——
    # 法则：名词优于形容词 / 过程重于结果 / 传承与时间 / 留白不煽动 / 仪式与私密 / 懂的门槛
    "emo_material": [
        "{brand}的{topic}，不说奢华，只说能穿过戒指的绒——{img}，足矣",
        "六微米的{topic}，替{c0}说尽了一切——{brand}，{img}，安静如初",
        "{topic}，用一百道工序换一句话：{brand}的{img}，不解释",
    ],
    "emo_heirloom": [
        "有些{topic}，值得交给下一个人——{brand}，{img}，与时间同行",
        "父辈走过的晨路，{topic}还在——{brand}，{img}，替你记得",
        "{brand}的{topic}，不是一次相遇，是{img}里的一辈子",
    ],
    "emo_silence": [
        "{topic}，{brand}只说一句，剩下的是{img}——{c0}，懂的人自懂",
        "不声张的{topic}，最接近{img}——{brand}，静默成金",
        "{brand}不喊{topic}，{img}替它说——{c0}，听完就够了",
    ],
    "emo_ritual": [
        "为{topic}留一个傍晚——{brand}，{img}，只此一刻，只为你",
        "{topic}的时刻，{brand}备好{img}——{c0}，慢一点，像某种仪式",
        "把{topic}过成仪式——{brand}的{img}，专为值得的人",
    ],
    # —— 品类情感手法·高奢版（克制更甚：感官/悦己/自然/共生）——
    "emo_sensory": [
        "{topic}的触感，只有{brand}知道怎么形容——{img}，留在指尖",
        "让{topic}的气味替你开口——{brand}，{img}，不言而喻",
    ],
    "emo_self": [
        "{topic}，不必为谁而美——{brand}，{img}，只对{c0}自己",
        "不追赶{topic}，{brand}只在意{c0}是否自在——{img}，足矣",
    ],
    "emo_nature": [
        "{topic}在山的那一头——{brand}，{img}，安静地等{c0}",
        "{c0}走向{topic}，{brand}的{img}一路相随，不多话",
    ],
    "emo_grow": [
        "{topic}与{brand}，都经得起时间——{img}，与{c0}一起慢慢来",
        "{brand}的{topic}，是一点一点长出来的——{img}，如你",
    ],
}

_EMO_LUX_EXTRA = ["emo_material", "emo_heirloom", "emo_silence", "emo_ritual"]

# 语义角色 → 情感手法适配约束（手法×主题词适配）
# 功能性/低语境主题词（如 停车/排队/投诉 → service）收敛到写实手法，避免"越界张力/魔幻现实"
# 等需要浪漫语境的手法与之组合出戏；高语境角色放开手法面。
_EMO_ROLE_COMPAT = {
    "space":  ["emo_time", "emo_unspoken", "emo_omen", "emo_paradox", "emo_slant", "emo_surreal", "emo_season",
               "emo_sensory", "emo_nature"],
    "food":   ["emo_heart", "emo_truth", "emo_time", "emo_unspoken", "emo_season", "emo_slant", "emo_understate",
               "emo_sensory", "emo_self", "emo_grow"],
    "service":["emo_truth", "emo_heart", "emo_time", "emo_repeat", "emo_understate", "emo_season"],
    "event":  ["emo_omen", "emo_heart", "emo_edge", "emo_unspoken", "emo_query", "emo_repeat", "emo_understate",
               "emo_grow", "emo_self"],
    "ip":     ["emo_edge", "emo_unspoken", "emo_omen", "emo_mirror", "emo_query", "emo_surreal", "emo_repeat",
               "emo_nature", "emo_sensory"],
    "aesthetic": ["emo_unspoken", "emo_paradox", "emo_omen", "emo_slant", "emo_season", "emo_surreal", "emo_mirror",
                  "emo_sensory", "emo_self", "emo_nature"],
    "general": ["emo_truth", "emo_omen", "emo_paradox", "emo_query", "emo_repeat", "emo_heart",
                "emo_time", "emo_slant", "emo_season", "emo_surreal", "emo_understate", "emo_mirror",
                "emo_sensory", "emo_self", "emo_nature", "emo_grow"],
    "beauty":  ["emo_sensory", "emo_self", "emo_time", "emo_season", "emo_unspoken", "emo_mirror"],
    "family":  ["emo_grow", "emo_heart", "emo_time", "emo_season", "emo_understate", "emo_self"],
    "sport":   ["emo_nature", "emo_self", "emo_edge", "emo_repeat", "emo_truth", "emo_time"],
    "wine":    ["emo_sensory", "emo_grow", "emo_ritual", "emo_season", "emo_slant", "emo_truth"],
}

# 机制 → 张力句式类型（可多选）
MECH_TO_HOOK = {
    "eventify": ["story", "imperative", "assert"],
    "participate": ["imperative", "cocreate"],
    "symbolize": ["assert", "culture"],
    "reverse": ["reversal", "assert"],
    "cocreate": ["cocreate", "imperative"],
    "culture": ["culture", "assert"],
    "resonate": ["emo_heart", "emo_time", "emo_truth", "emo_edge", "emo_unspoken", "emo_omen",
                 "emo_paradox", "emo_query", "emo_repeat", "emo_mirror", "emo_slant",
                 "emo_season", "emo_surreal", "emo_understate",
                 "emo_sensory", "emo_self", "emo_nature", "emo_grow"],
}

# ---- 预算感知（同一创意不同预算的落地档位）----
BUDGETS = {
    "low": {
        "name": "轻量（低预算）",
        "scale": "话题/内容玩法 + UGC 机制 + 轻量达人合作（无大物料）",
        "investment": "以内容与话题为主，边际成本低，适合快速验证与常态化运营",
        "tactics": ["纯内容话题引爆（挑战/清单/攻略）", "UGC 机制+官方转发放大", "KOC 轻量置换合作", "搜索词占位与评论区运营"],
        "why": "预算有限时，靠「参与机制 + 真实 UGC」撬动，而不是物料砸量",
    },
    "mid": {
        "name": "单点战役（中预算）",
        "scale": "单点事件/快闪 + 中量物料 + 达人矩阵 + 搜索承接",
        "investment": "一次可被记忆的单点事件，配合内容与达人矩阵放大",
        "tactics": ["单点事件/快闪制造话题峰值", "KOL+KOC 矩阵集中发布", "核心物料（短片/装置/海报）", "搜索/信息流承接与转化"],
        "why": "预算中等时，把弹药集中在「一个可传播的事件」上，避免摊薄",
    },
    "high": {
        "name": "全链路战役（高预算）",
        "scale": "全链路整合：大事件 + 全物料 + 达人矩阵 + 媒体/线下 + 私域闭环",
        "investment": "品牌级战役投入，覆盖声量-互动-到店-私域全链路",
        "tactics": ["旗舰事件/大装置/概念片", "全平台达人+媒体矩阵", "线下体验+线上 UGC 双场联动", "会员/私域沉淀与复购链路"],
        "why": "预算充足时，打透「事件→传播→到店→沉淀」完整闭环，形成长期资产",
    },
}


def _provenance(topic, sentiment, mech, tonality, circle, signals, angle):
    """上下文指纹（不变，新增 angle 维度）：芥子→须弥→再生产，证据分级如实标注。"""
    n_notes = int(signals.get("volume_notes", 0) or 0)
    has_db = bool(signals.get("keyword")) and n_notes > 0
    evidence_level = "repeated" if n_notes >= 10 else ("single_case" if n_notes > 0 else "assumption")
    confidence = round(min(0.4 + min(n_notes, 50) / 100.0, 0.9), 2) if has_db else 0.35
    return {
        "seed_signal": ("ZBC 真实信号：主题「%s」、情绪=%s、样本笔记=%d、风险事件=%d"
                        % (topic, sentiment, n_notes, int(signals.get("risk_events", 0) or 0)))
                       if has_db else "结构化假设：未接入 ZBC 真实样本（keyword/DB 缺失），信号为占位，需真实数据回填",
        "parent_L1_formula": MECH_TO_L1.get(mech, "未归类公式"),
        "parent_L2_tone": TONALITIES.get(tonality, TONALITIES["premium"])["name"],
        "parent_circle": circle,
        "angle": ANGLES.get(angle, "未标注角度"),
        "causal_type": "相关性（平台/人群偏好，算法或人群变化需复核，非因果机制）",
        "evidence_level": evidence_level,
        "confidence": confidence,
        "counter_example_check": "pending（负样本库为 P2 能力，晋升 L1 前须补 3 个反例，当前未校验）",
        "trace": "芥子(真实信号) → 须弥(机制/角度抽象) → idea(多维再生产) → FEEDBACK 回流",
    }


def signals_from_db(db_path, keyword, circle="都市职场", hotspot=""):
    """从 ZBC 舆情数据提取创意信号（主题词/情绪/风险），叠加圈层与热点时效。"""
    from scripts.brand_insight import diagnose
    r = diagnose(db_path, keyword)
    topics = [t[0] if isinstance(t, (tuple, list)) else str(t) for t in r.get("topics", [])]
    neg = r.get("negative_rate", 0.0)
    pos = r.get("sentiment", {}).get("positive", 0)
    negc = r.get("sentiment", {}).get("negative", 0)
    sentiment = "negative" if neg > 0.3 else ("positive" if pos > negc else "neutral")
    return {
        "keyword": keyword,
        "topics": topics,
        "sentiment": sentiment,
        "negative_rate": neg,
        "risk_events": len(r.get("risk_events", [])),
        "circle": circle,
        "hotspot": hotspot,
        "volume_notes": r.get("volume", {}).get("notes", 0),
    }


def _render(tpl, brand, topic, c0, img, sym, hot):
    """填充句式槽位；{...}未知槽位用品牌名兜底，防止 KeyError 导致空口号。"""
    def _sub(s):
        return (s.replace("{brand}", brand).replace("{topic}", topic).replace("{c0}", c0)
                 .replace("{img}", img).replace("{sym}", sym).replace("{hot}", hot or "今天")
                 .replace("{#话题#}", "#%s#" % topic))
    return _sub(tpl)


def _pick_hook(lib, mech, tonality, rng, used_keys, role=None):
    """从机制可用句式中选一条未用过的张力句式；用完则重置（保证批次内不重复优先）。

    role: 主题词语义角色（space/food/service/...）。resonate 时按 _EMO_ROLE_COMPAT 过滤
    候选手法——功能性/低语境主题词（service）收敛到写实手法，避免高语境手法出戏。

    注意：必须对 list 副本 shuffle——若就地 shuffle 模块级共享 list（MECH_TO_HOOK/_HOOK），
    会跨调用残留顺序，破坏 seed 可复现性。
    """
    pool = (_HOOK_EMO_LUX if tonality == "luxury" else _HOOK_EMO) if mech == "resonate" \
        else (_HOOK_LUX if tonality == "luxury" else _HOOK)
    candidates = list(MECH_TO_HOOK.get(mech, ["assert"]))
    # 手法×主题词适配：resonate 时按语义角色收敛可用手法（高语境手法不匹配功能性词）
    if mech == "resonate":
        # LUX 专属手法仅在高奢调性启用
        if tonality == "luxury":
            candidates = candidates + _EMO_LUX_EXTRA
        if role:
            allowed = set(_EMO_ROLE_COMPAT.get(role, _EMO_ROLE_COMPAT["general"]))
            if allowed:
                candidates = [c for c in candidates
                              if c in allowed or (tonality == "luxury" and c in _EMO_LUX_EXTRA
                                                  and role != "service")]
    if not candidates:
        candidates = list(MECH_TO_HOOK.get(mech, ["assert"]))
    rng.shuffle(candidates)
    for hk in candidates:
        patterns = list(pool.get(hk) or pool.get("assert") or [])
        if not patterns:
            # 兜底：任取第一组模板，保证永远有输出（不依赖 assert 键存在）
            patterns = list(next(iter(pool.values())))
        rng.shuffle(patterns)
        for tpl in patterns:
            key = hk + "|" + tpl
            if key not in used_keys:
                return tpl, hk, key
    # 全部用过：重置该机制桶，随机再取（保证永远有输出，不重复优先已满足）
    hk = candidates[0]
    pool_clean = list(pool.get(hk) or pool.get("assert") or list(next(iter(pool.values()))))
    tpl = rng.choice(pool_clean)
    return tpl, hk, hk + "|" + tpl


def generate_ideas(brand, category, signals, n=3, tonality="premium", budget="mid", seed=None):
    """生成 n 个原创创意 idea（机制 × 角度 × 张力句式 × 语义角色 × 预算感知）。

    budget: low(轻量) / mid(单点战役) / high(全链路战役)，随预算输出不同落地档位。
    seed: 可复现性；不传则每次随机（保证"新 idea"）。
    """
    rng = random.Random(seed)
    # 无主题词时不得输出占位符（#趋势词# 属模板残留）；以「日常」为兜底主题——
    # 真实中文词、全品类语义成立（商场=日常逛、餐饮=一日三餐），并与 general 意象「质感新体验」契合
    topics = [t for t in (signals.get("topics", []) or []) if t] or ["日常"]
    sentiment = signals.get("sentiment", "neutral")
    circle = signals.get("circle", "都市职场")
    hotspot = signals.get("hotspot", "")
    # 芥子→须弥：未显式指定热点时，自动绑定当下营销节点（时效自动增强）。
    # 仅非 luxury 调性启用——高奢克制叙事原则：不参与流量狂欢、不追热点。
    if not hotspot and tonality != "luxury":
        try:
            import datetime as _dt
            from scripts.marketing_calendar import suggest_hotspot
            _mc = suggest_hotspot(_dt.date.today().strftime("%Y-%m-%d"), category)
            if _mc and _mc.get("nodes"):
                hotspot = _mc["nodes"][0]["name"]
        except Exception:
            pass
    style = EMOTION_STYLES.get(sentiment, EMOTION_STYLES["neutral"])
    cs = CIRCLE_SYMBOLS.get(circle, CIRCLE_SYMBOLS["都市职场"])
    tone = TONALITIES.get(tonality, TONALITIES["premium"])["name"]
    c0 = circle.split("/")[0]
    sym = rng.choice(cs["symbols"])
    bd = BUDGETS.get(budget, BUDGETS["mid"])

    if tonality == "luxury":
        mech_order = ["symbolize", "reverse", "culture", "eventify", "resonate"]
    elif sentiment == "negative":
        mech_order = ["reverse", "cocreate", "eventify", "resonate"]
    elif sentiment == "positive":
        mech_order = ["eventify", "participate", "cocreate", "resonate"]
    else:
        mech_order = ["symbolize", "participate", "eventify", "resonate"]

    angles_order = ["consumer", "introspect", "coded", "scene", "rebel", "cocreate"]
    rng.shuffle(angles_order)

    ideas = []
    used_keys = set()
    used_slogans = set()
    topic_slots = {}
    for i in range(n):
        m = mech_order[i % len(mech_order)]
        topic = topics[i % len(topics)]
        role = _topic_role(topic)
        img = _TOPIC_ROLE_IMAGES[role][tonality]
        # 角度轮转（每个 idea 用不同切入人设，防止"主题换了创意没换"）
        angle = angles_order[i % len(angles_order)]
        # 同一主题多次出现时，用不同意象槽位避免同义重复
        slot_key = topic + "|" + m
        if slot_key in topic_slots:
            img = img + "·" + sym
        topic_slots[slot_key] = True

        tpl, hk, key = _pick_hook(_HOOK, m, tonality, rng, used_keys, role)
        used_keys.add(key)
        slogan = _render(tpl, brand, topic, c0, img, sym, hotspot)
        # 兜底：若与本批次已出 slogan 重复，重取一条不同句式的
        guard = 0
        while slogan in used_slogans and guard < 6:
            tpl, hk, key = _pick_hook(_HOOK, m, tonality, rng, used_keys, role)
            used_keys.add(key)
            slogan = _render(tpl, brand, topic, c0, img, sym, hotspot)
            guard += 1
        used_slogans.add(slogan)

        hotspot_bind = ("绑定热点「%s」，踩准文化时机（Cultural Timing）" % hotspot) if hotspot else \
            ("克制不追热点（高奢调性：稀缺与工艺即传播）" if tonality == "luxury"
             else "择机踩文化时机（趋势/节日/赛事），时效是传播第一变量")
        mech_name = MECHANISMS[m]["name"]
        hook_names = {"assert": "主张式", "imperative": "行动式", "story": "故事式",
                      "reversal": "反转式", "cocreate": "共创式", "culture": "暗语式",
                      "emo_heart": "以小写大", "emo_time": "时间具象", "emo_truth": "朴素真话",
                      "emo_edge": "越界张力", "emo_unspoken": "不说破的深情",
                      "emo_omen": "条件预言", "emo_paradox": "悖论并置",
                      "emo_query": "反问推理", "emo_repeat": "首语重复", "emo_mirror": "交错配列",
                      "emo_slant": "留白斜说", "emo_season": "季语物候", "emo_surreal": "魔幻现实",
                      "emo_understate": "轻描淡写", "emo_material": "材质细语",
                      "emo_heirloom": "传承物语", "emo_silence": "沉默留白", "emo_ritual": "仪式时刻",
                      "emo_sensory": "感官通感", "emo_self": "悦己和解", "emo_nature": "自然对白",
                      "emo_grow": "共同生长"}
        ideas.append({
            "big_idea": slogan,
            "mechanism": mech_name,
            "angle": ANGLES[angle],
            "tension_type": hook_names.get(hk, hk),
            "concept": "%s：%s（%s，角度=消费者/品牌/圈层等）" % (mech_name, slogan, hook_names.get(hk, hk)),
            "why": "数据信号：主题「%s」(语义角色:%s) + 情绪「%s」→ %s；调性「%s」；圈层「%s」以%s沟通；"
                   "张力来源=%s。" % (topic, role, sentiment, style, tone, circle, cs["lang"], hook_names.get(hk, hk)),
            "circle": circle,
            "circle_symbols": cs["symbols"],
            "tonality": tone,
            "budget": bd,
            "timeliness": hotspot_bind,
            "touchpoints": (_OVERSEAS_TOUCH if signals.get("overseas") else
                            ["内容种草", "圈层互动", "线下体验", "私域沉淀"]),
            "virality": (_OVERSEAS_VIRAL if signals.get("overseas") else
                         "参与机制让用户拉用户（互动即传播）+ 张力句式可记忆可复制（打卡/接话/二创）"),
            "provenance": _provenance(topic, sentiment, m, tonality, circle, signals, angle),
        })
    return {"meta": {"brand": brand, "category": category, "signals": signals,
                     "tonality": tone, "budget": budget,
                     "bound_hotspot": hotspot if hotspot else "（未绑定节点）",
                     "framework": "Seed-Sumeru×Taiji V2：芥子(真实信号)→须弥(机制×角度×句式)→Contract→再生产；"
                                  "形可变道不可移；反模板化=多维组合而非固定句式"},
            "ideas": ideas}


def emotion_hook(brand, topic=None, circle="都市职场", tonality="premium", img=None, rng=None):
    """渲染一条情感共鸣钩子（供视频脚本/社媒矩阵复用，跨产物统一表达力）。

    情感手法句库随机取一条，槽位用品牌/主题/圈层/意象填充。rng 可传固定 seed 保证可复现。
    """
    r = rng or random.Random()
    lib = _HOOK_EMO_LUX if tonality == "luxury" else _HOOK_EMO
    groups = list(lib.values())
    tpl = r.choice(r.choice(groups))
    t = topic or brand or "日常"
    role = _topic_role(t)
    if img is None:
        img = _TOPIC_ROLE_IMAGES[role][tonality]
    c0 = circle.split("/")[0]
    sym = r.choice(CIRCLE_SYMBOLS.get(circle, CIRCLE_SYMBOLS["都市职场"])["symbols"])
    return _render(tpl, brand, t, c0, img, sym, "")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="数据驱动原创创意生成器 V2（反模板化）")
    ap.add_argument("--brand", default="示例品牌")
    ap.add_argument("--category", default="通用")
    ap.add_argument("--keyword", default="", help="ZBC 舆情关键词(从 DB 提信号)")
    ap.add_argument("--db", default="data/monitor.db")
    ap.add_argument("--circle", default="都市职场", choices=list(CIRCLE_SYMBOLS.keys()))
    ap.add_argument("--tonality", default="premium", choices=list(TONALITIES.keys()))
    ap.add_argument("--hotspot", default="", help="时效热点(如 15周年/618/春节)")
    ap.add_argument("--budget", default="mid", choices=list(BUDGETS.keys()))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    if a.keyword:
        s = signals_from_db(a.db, a.keyword, a.circle, a.hotspot)
    else:
        s = {"topics": [], "sentiment": "neutral", "negative_rate": 0.0,
             "risk_events": 0, "circle": a.circle, "hotspot": a.hotspot, "volume_notes": 0}
    r = generate_ideas(a.brand, a.category, s, a.n, a.tonality, a.budget, a.seed)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
