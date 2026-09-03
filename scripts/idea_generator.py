# -*- coding: utf-8 -*-
"""数据驱动原创创意生成器（对标全球4A：阳狮/Ogilvy/WPP 范式 × ZBC 真实数据）。

不是模板填空，而是把「数据信号 × 知识库底层逻辑 × 圈层符号」组合生成新的 midea&idea：
  - 数据信号：主题词(内容) / 情绪(基调) / 风险(约束) / 圈层(人群符号) / 热点(时效)
  - 创意机制：事件化 / 参与式 / 符号化 / 反差 / 共创 / 文化共识（源自戛纳/Ogilvy 方法论）
  - 输出：每个 idea 含 口号(符号化) + 概念(为什么成立) + 圈层符号 + 触点 + 时效绑定 + 传播设计

用法：
  from scripts.idea_generator import generate_ideas, signals_from_db
  s = signals_from_db("data/monitor.db", "太古汇", circle="Z世代潮人", hotspot="世界杯")
  ideas = generate_ideas("某品牌", "美妆", s)
"""
import json
import os
import sys

# 支持 `python scripts/idea_generator.py` 直接运行（把项目根加入 path）
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
}

# ---- 情绪基调 → 创意风格 ----
EMOTION_STYLES = {
    "positive": "庆祝共鸣·狂欢放大（借势情绪顶点）",
    "neutral": "认知觉醒·场景种草（先种草后转化）",
    "negative": "危机共情·诚实解决（先止血再借势）",
}

# ---- 创意机制（知识库底层逻辑 × 全球4A范式）----
MECHANISMS = {
    "eventify": {"name": "事件化", "desc": "把抽象卖点/概念变成可参与的体验事件（太二运动会/茅台剧本杀）"},
    "participate": {"name": "参与式", "desc": "让用户从旁观者变玩家（Duolingo复活/AIGC贴纸，参与机制即传播）"},
    "symbolize": {"name": "符号化", "desc": "生成一个可记忆可复制的符号/口号/图腾（谐音双关/反差/押韵）"},
    "reverse": {"name": "反差", "desc": "反常识断言制造话题（CeraVe 阴谋论/争议立场）"},
    "cocreate": {"name": "共创式", "desc": "把用户自发行为变成产品/内容（Vaseline Originals UGC→产品飞轮）"},
    "culture": {"name": "文化共识", "desc": "借势已有文化共识/梗自然绑定（玩梗球星/Oreo Cows）"},
}


def signals_from_db(db_path, keyword, circle="都市职场", hotspot=""):
    """从 ZBC 舆情数据提取创意信号（主题词/情绪/风险），叠加圈层与热点时效。"""
    from scripts.brand_insight import diagnose
    r = diagnose(db_path, keyword)
    topics = [t[0] if isinstance(t, (tuple, list)) else str(t) for t in r.get("topics", [])]
    neg = r.get("negative_rate", 0.0)
    sentiment = "negative" if neg > 0.3 else ("positive" if r.get("sentiment", {}).get("positive", 0) > r.get("sentiment", {}).get("negative", 0) else "neutral")
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


def _slogan(brand, topic, mechanism, circle):
    """符号化口号构造：机制 × 主题词 × 圈层语言 → 可记忆口号。"""
    cs = CIRCLE_SYMBOLS.get(circle, CIRCLE_SYMBOLS["都市职场"])
    lang = cs["lang"]
    if mechanism == "symbolize":
        return "「%s%s」——%s，%s的人都在%s" % (brand, topic, topic, circle.split("/")[0], topic)
    if mechanism == "eventify":
        return "「%s%s节」——把%s变成一场%sg众可参与的%s" % (brand, topic, topic, circle.split("/")[0], topic)
    if mechanism == "participate":
        return "「%s%s挑战」——你的%s，%s来定义" % (brand, topic, topic, circle.split("/")[0])
    if mechanism == "reverse":
        return "「谁说%s不能%s」——%s的%s，拒绝%s" % (topic, "好", circle.split("/")[0], topic, "套路")
    if mechanism == "cocreate":
        return "「%s由你造」——%s的%s，来自%s的%s" % (brand, circle.split("/")[0], topic, circle.split("/")[0], topic)
    return "「%s×%s」——%s，%s" % (brand, topic, lang.split("/")[0], topic)


def generate_ideas(brand, category, signals, n=3):
    """生成 n 个原创创意 idea（数据信号 × 机制 × 圈层符号）。"""
    topics = signals.get("topics", []) or ["#趋势词#"]
    sentiment = signals.get("sentiment", "neutral")
    circle = signals.get("circle", "都市职场")
    hotspot = signals.get("hotspot", "")
    style = EMOTION_STYLES.get(sentiment, EMOTION_STYLES["neutral"])
    cs = CIRCLE_SYMBOLS.get(circle, CIRCLE_SYMBOLS["都市职场"])

    # 机制选择：负面→先诚实解决；正面→狂欢/共创；中性→认知/参与
    if sentiment == "negative":
        mech_order = ["reverse", "cocreate", "eventify"]
    elif sentiment == "positive":
        mech_order = ["eventify", "participate", "cocreate"]
    else:
        mech_order = ["symbolize", "participate", "eventify"]

    ideas = []
    used = set()
    for i in range(n):
        m = mech_order[i % len(mech_order)]
        topic = topics[i % len(topics)] if topics else "#趋势词#"
        key = (m, topic)
        if key in used:
            topic = topic + "新解"
        used.add(key)
        slogan = _slogan(brand, topic, m, circle)
        hotspot_bind = ("绑定热点「%s」，踩准文化时机（Cultural Timing）" % hotspot) if hotspot else \
            "择机踩文化时机（趋势/节日/赛事），时效是传播第一变量"
        ideas.append({
            "big_idea": slogan,
            "mechanism": MECHANISMS[m]["name"],
            "concept": "%s——%s" % (MECHANISMS[m]["desc"], slogan),
            "why": "数据信号：主题「%s」+ 情绪基调「%s」→ %s；圈层「%s」用%s沟通。" % (
                topic, sentiment, style, circle, cs["lang"]),
            "circle": circle,
            "circle_symbols": cs["symbols"],
            "timeliness": hotspot_bind,
            "touchpoints": ["内容种草", "圈层互动", "线下体验", "私域沉淀"],
            "virality": "参与机制让用户拉用户（互动即传播）+ 符号可复制（remix/梗/打卡）",
        })
    return {"meta": {"brand": brand, "category": category, "signals": signals}, "ideas": ideas}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="数据驱动原创创意生成器")
    ap.add_argument("--brand", default="示例品牌")
    ap.add_argument("--category", default="通用")
    ap.add_argument("--keyword", default="", help="ZBC 舆情关键词(从 DB 提信号)")
    ap.add_argument("--db", default="data/monitor.db")
    ap.add_argument("--circle", default="都市职场", choices=list(CIRCLE_SYMBOLS.keys()))
    ap.add_argument("--hotspot", default="", help="时效热点(如 世界杯/618/春节)")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    if a.keyword:
        s = signals_from_db(a.db, a.keyword, a.circle, a.hotspot)
    else:
        s = {"topics": [], "sentiment": "neutral", "negative_rate": 0.0,
             "risk_events": 0, "circle": a.circle, "hotspot": a.hotspot, "volume_notes": 0}
    r = generate_ideas(a.brand, a.category, s, a.n)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
