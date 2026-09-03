# -*- coding: utf-8 -*-
"""全年营销节点日历 + 品类适配（芥子=具体节点信号，须弥=可复用适配逻辑）。

数据：2026 中国营销节点（节气/传统节日/电商大促/国际节点），来自智谱 web_search 研究
（research-inbox/marketing-calendar-2026-20260903.md）。公历节点固定；农历/移动节日逐年微调。

用途：
  1. 给创意引擎/方案引擎提供 hotspot 建议：输入月份+品类 → 命中节点 + 情感主题；
  2. 报告/运营排期参考：输入日期 → 当天/当月节点；
  3. 自循环延伸：OSAI 可基于此继续扩充行业节点（母婴/美妆/酒类等垂直节点）。

用法：
  from scripts.marketing_calendar import suggest_hotspot, nodes_for_month, node_on
  suggest_hotspot("2026-09-25", "商业地产")   # 中秋 → 情感主题/适合品类
  nodes_for_month(6)                          # 6月全部节点
"""
import datetime

# 节点类型
K_SOLAR = "节气"      # 24 节气
K_FEST = "节日"       # 传统节日/法定节日
K_EMC = "电商大促"    # 618/双11 等
K_INTL = "国际节点"   # 地球日/读书日等
K_MARK = "营销节点"   # 开学季/跨年等

# 月 → 节点列表：name/date(mm-dd)/kind/theme(情感主题)/cats(适合品类关键词)
_NODES = {
    1: [
        {"name": "元旦", "date": "01-01", "kind": K_FEST, "theme": "辞旧迎新、愿望、新生",
         "cats": ["年货", "食品", "酒水", "服饰", "数码", "家居"]},
        {"name": "小寒", "date": "01-05", "kind": K_SOLAR, "theme": "冬日温暖、慢生活",
         "cats": ["保暖", "养生", "热饮"]},
        {"name": "腊八", "date": "01-07", "kind": K_FEST, "theme": "暖粥、团圆、年味",
         "cats": ["食品", "杂粮", "传统"]},
        {"name": "大寒", "date": "01-20", "kind": K_SOLAR, "theme": "岁末总结、蓄力",
         "cats": ["养生", "滋补", "家居"]},
        {"name": "年货节", "date": "01-20", "kind": K_EMC, "theme": "备年货、送礼、祈福",
         "cats": ["年货", "礼盒", "食品", "美妆", "3C"]},
    ],
    2: [
        {"name": "立春", "date": "02-04", "kind": K_SOLAR, "theme": "春意、生机、焕新",
         "cats": ["春装", "美妆", "户外"]},
        {"name": "情人节", "date": "02-14", "kind": K_FEST, "theme": "爱意、浪漫、专属",
         "cats": ["鲜花", "珠宝", "巧克力", "餐饮", "美妆"]},
        {"name": "除夕", "date": "02-16", "kind": K_FEST, "theme": "阖家团圆、守岁",
         "cats": ["年夜饭", "年货", "酒水"]},
        {"name": "春节", "date": "02-17", "kind": K_FEST, "theme": "团圆、喜庆、新开始",
         "cats": ["礼盒", "服饰", "黄金", "食品", "酒水"]},
        {"name": "雨水", "date": "02-18", "kind": K_SOLAR, "theme": "润泽、生发",
         "cats": ["护肤", "茶饮"]},
    ],
    3: [
        {"name": "惊蛰", "date": "03-05", "kind": K_SOLAR, "theme": "苏醒、活力",
         "cats": ["户外", "运动", "春游"]},
        {"name": "妇女节", "date": "03-08", "kind": K_FEST, "theme": "悦己、女性力量、宠爱",
         "cats": ["美妆", "鲜花", "珠宝", "服饰", "健康"]},
        {"name": "植树节", "date": "03-12", "kind": K_INTL, "theme": "绿色、环保、希望",
         "cats": ["环保", "公益", "亲子"]},
        {"name": "消费者权益日", "date": "03-15", "kind": K_INTL, "theme": "透明、信任、诚信",
         "cats": ["零售", "电商", "服务"]},
        {"name": "春分", "date": "03-20", "kind": K_SOLAR, "theme": "平衡、踏青、焕新",
         "cats": ["春装", "茶具", "户外"]},
        {"name": "元宵节", "date": "03-03", "kind": K_FEST, "theme": "团圆、灯火、浪漫",
         "cats": ["汤圆", "灯会", "餐饮"]},
    ],
    4: [
        {"name": "愚人节", "date": "04-01", "kind": K_INTL, "theme": "趣味、反差、玩梗",
         "cats": ["食品", "饮品", "零售"]},
        {"name": "清明", "date": "04-05", "kind": K_FEST, "theme": "缅怀、春游、传统",
         "cats": ["青团", "春游", "茶"]},
        {"name": "谷雨", "date": "04-20", "kind": K_SOLAR, "theme": "生长、滋养",
         "cats": ["茶", "护肤", "滋补"]},
        {"name": "世界地球日", "date": "04-22", "kind": K_INTL, "theme": "低碳、可持续、守护",
         "cats": ["环保", "公益", "可持续品牌"]},
        {"name": "世界读书日", "date": "04-23", "kind": K_INTL, "theme": "阅读、思考、成长",
         "cats": ["图书", "文创", "文具"]},
    ],
    5: [
        {"name": "劳动节", "date": "05-01", "kind": K_FEST, "theme": "致敬、松弛、小长假",
         "cats": ["旅游", "出行", "美食", "家居"]},
        {"name": "青年节", "date": "05-04", "kind": K_FEST, "theme": "热血、理想、青春",
         "cats": ["潮牌", "数码", "运动"]},
        {"name": "立夏", "date": "05-05", "kind": K_SOLAR, "theme": "热情、生长",
         "cats": ["夏装", "冷饮", "防晒"]},
        {"name": "母亲节", "date": "05-10", "kind": K_FEST, "theme": "感恩、陪伴、温柔",
         "cats": ["鲜花", "珠宝", "美妆", "康养", "家居"]},
        {"name": "小满", "date": "05-21", "kind": K_SOLAR, "theme": "小满足、恰到好处",
         "cats": ["生活方式", "家居", "茶饮"]},
    ],
    6: [
        {"name": "儿童节", "date": "06-01", "kind": K_FEST, "theme": "童真、快乐、陪伴",
         "cats": ["玩具", "童装", "亲子", "乐园"]},
        {"name": "芒种", "date": "06-05", "kind": K_SOLAR, "theme": "耕耘、播种",
         "cats": ["农业", "食品", "劳作"]},
        {"name": "端午节", "date": "06-19", "kind": K_FEST, "theme": "传统、安康、家味",
         "cats": ["粽子", "酒水", "礼盒", "香囊"]},
        {"name": "618 大促", "date": "06-18", "kind": K_EMC, "theme": "狂欢、实惠、囤货",
         "cats": ["数码", "美妆", "家居", "服饰", "全品类"]},
        {"name": "父亲节", "date": "06-21", "kind": K_FEST, "theme": "感恩、担当、深沉",
         "cats": ["男士理容", "运动", "数码", "酒水"]},
        {"name": "夏至", "date": "06-21", "kind": K_SOLAR, "theme": "热烈、消暑",
         "cats": ["避暑", "冷饮", "防晒"]},
    ],
    7: [
        {"name": "小暑", "date": "07-07", "kind": K_SOLAR, "theme": "热浪、清凉",
         "cats": ["防晒", "冷饮", "空调"]},
        {"name": "大暑", "date": "07-22", "kind": K_SOLAR, "theme": "盛夏、释放、夜经济",
         "cats": ["夜宵", "泳具", "旅游"]},
        {"name": "暑期档", "date": "07-01", "kind": K_MARK, "theme": "暑假、释放、亲子",
         "cats": ["亲子", "旅游", "文娱", "数码"]},
    ],
    8: [
        {"name": "立秋", "date": "08-07", "kind": K_SOLAR, "theme": "初秋、收获前奏",
         "cats": ["秋装", "茶饮", "滋补"]},
        {"name": "七夕", "date": "08-19", "kind": K_FEST, "theme": "中式浪漫、专属、心意",
         "cats": ["鲜花", "珠宝", "美妆", "礼盒"]},
        {"name": "处暑", "date": "08-23", "kind": K_SOLAR, "theme": "秋意、收敛",
         "cats": ["滋补", "秋装"]},
        {"name": "开学季", "date": "08-25", "kind": K_MARK, "theme": "成长、新起点、仪式",
         "cats": ["文具", "数码", "服饰", "箱包"]},
    ],
    9: [
        {"name": "白露", "date": "09-07", "kind": K_SOLAR, "theme": "清透、秋凉",
         "cats": ["秋装", "茶"]},
        {"name": "教师节", "date": "09-10", "kind": K_FEST, "theme": "尊师、感恩",
         "cats": ["礼盒", "鲜花", "图书"]},
        {"name": "秋分", "date": "09-23", "kind": K_SOLAR, "theme": "丰收、平衡",
         "cats": ["时令", "大闸蟹", "茶"]},
        {"name": "中秋节", "date": "09-25", "kind": K_FEST, "theme": "团圆、相思、月光",
         "cats": ["月饼", "礼盒", "茶酒", "珠宝"]},
        {"name": "丰收节", "date": "09-23", "kind": K_MARK, "theme": "丰收、土地、馈赠",
         "cats": ["食品", "农产品", "乡村"]},
    ],
    10: [
        {"name": "国庆节", "date": "10-01", "kind": K_FEST, "theme": "家国、长假、盛典",
         "cats": ["旅游", "出行", "婚庆", "餐饮"]},
        {"name": "寒露", "date": "10-08", "kind": K_SOLAR, "theme": "深秋、滋补",
         "cats": ["滋补", "养生", "秋装"]},
        {"name": "重阳节", "date": "10-20", "kind": K_FEST, "theme": "敬老、登高、安康",
         "cats": ["银发", "健康", "滋补"]},
        {"name": "霜降", "date": "10-23", "kind": K_SOLAR, "theme": "收官、沉淀",
         "cats": ["滋补", "冬装预热"]},
        {"name": "万圣节前夜", "date": "10-31", "kind": K_INTL, "theme": "变装、狂欢、反差",
         "cats": ["糖果", "派对", "服饰"]},
    ],
    11: [
        {"name": "立冬", "date": "11-07", "kind": K_SOLAR, "theme": "冬始、温暖",
         "cats": ["保暖", "热饮", "滋补"]},
        {"name": "双11", "date": "11-11", "kind": K_EMC, "theme": "狂欢、实惠、囤货",
         "cats": ["美妆", "服饰", "数码", "家居", "全品类"]},
        {"name": "小雪", "date": "11-22", "kind": K_SOLAR, "theme": "微寒、收纳",
         "cats": ["冬装", "家居"]},
        {"name": "感恩节", "date": "11-26", "kind": K_INTL, "theme": "感恩、回馈",
         "cats": ["礼盒", "食品", "家宴"]},
        {"name": "黑色星期五", "date": "11-27", "kind": K_EMC, "theme": "海淘、折扣、狂欢",
         "cats": ["数码", "美妆", "服饰"]},
    ],
    12: [
        {"name": "大雪", "date": "12-07", "kind": K_SOLAR, "theme": "凛冬、围炉",
         "cats": ["火锅", "保暖", "围炉"]},
        {"name": "双12", "date": "12-12", "kind": K_EMC, "theme": "年终回馈、囤货",
         "cats": ["全品类", "年货预热"]},
        {"name": "冬至", "date": "12-21", "kind": K_SOLAR, "theme": "至暗后新生、团圆",
         "cats": ["饺子", "汤圆", "滋补"]},
        {"name": "平安夜", "date": "12-24", "kind": K_INTL, "theme": "惊喜、温情、礼物",
         "cats": ["礼盒", "苹果", "派对"]},
        {"name": "圣诞节", "date": "12-25", "kind": K_FEST, "theme": "浪漫、许愿、仪式",
         "cats": ["礼盒", "美妆", "珠宝", "餐饮"]},
        {"name": "跨年", "date": "12-31", "kind": K_MARK, "theme": "岁末总结、新年期待、告白",
         "cats": ["派对", "烟花", "跨年活动", "酒水"]},
    ],
}

# 品类 → 泛化关键词（用于命中 cats，做触类旁通）
_CAT_ALIAS = {
    "商业地产": ["零售", "餐饮", "旅游", "亲子", "文娱", "派对", "跨年活动", "灯会"],
    "美妆": ["美妆", "护肤", "香水", "礼盒"],
    "食品": ["食品", "茶", "酒水", "时令", "汤圆", "粽子", "月饼", "饺子", "糖果"],
    "酒饮": ["酒水", "洋酒", "围炉", "热饮"],
    "服饰": ["服饰", "冬装", "秋装", "春装", "夏装", "童装", "箱包"],
    "珠宝": ["珠宝", "黄金"],
    "母婴": ["亲子", "童装", "玩具"],
    "数码": ["数码", "3C"],
    "家居": ["家居", "家电"],
    "汽车": ["出行", "汽车"],
    "旅游": ["旅游", "出行", "度假"],
}

# 垂直行业专属节点（2026 研究：母婴/美妆/酒饮/文旅/教育/宠物/咖啡茶饮）
# 结构：行业 → [{name, month(可空=全年), theme, cats}]
_V_NODES = {
    "母婴": [
        {"name": "爱婴节", "month": 5, "theme": "更轻松的妈妈、高质量带娃", "cats": ["育儿", "亲子"]},
        {"name": "童装节", "month": 6, "theme": "快乐童年、成长刻度", "cats": ["童装", "亲子"]},
        {"name": "亲子嘉年华", "month": 10, "theme": "陪伴、做回自己、亲情", "cats": ["亲子", "乐园", "文娱"]},
    ],
    "美妆": [
        {"name": "美妆节", "month": 3, "theme": "悦己、女性力量、焕新", "cats": ["美妆", "护肤"]},
        {"name": "香水节", "month": 11, "theme": "浪漫、听见声音、情感优先", "cats": ["香水", "礼盒"]},
    ],
    "酒饮": [
        {"name": "精酿节", "month": 9, "theme": "微醺、情绪消费、松弛", "cats": ["精酿", "酒水"]},
        {"name": "威士忌节", "month": 11, "theme": "仪式感、文化感、浓情", "cats": ["威士忌", "洋酒"]},
        {"name": "品酒季", "month": 12, "theme": "家、团圆、微醺慢聊", "cats": ["红酒", "酒水"]},
    ],
    "文旅": [
        {"name": "旅游节", "month": 5, "theme": "悦己、美好生活在当下", "cats": ["旅游", "文旅"]},
        {"name": "非遗文化季", "month": 6, "theme": "文化感、寻迹、深耕", "cats": ["非遗", "文化体验"]},
    ],
    "教育": [
        {"name": "开学季", "month": 9, "theme": "新起点、成长、焕新", "cats": ["教育", "文具", "数码"]},
        {"name": "考试季", "month": 6, "theme": "加油助力、青春、规划", "cats": ["教育", "学习"]},
    ],
    "宠物": [
        {"name": "国际宠物日", "month": 4, "theme": "陪伴、治愈、家庭成员", "cats": ["宠物"]},
        {"name": "宠物节", "month": 8, "theme": "社交货币、分享、关爱", "cats": ["宠物"]},
    ],
    "咖啡茶饮": [
        {"name": "世界咖啡日", "month": 10, "theme": "松弛感、第三空间、社交", "cats": ["咖啡", "咖啡豆"]},
        {"name": "茶文化节", "month": 5, "theme": "新中式、生活仪式、探索", "cats": ["茶叶", "茶饮"]},
    ],
}


def industry_nodes(industry="", month=None):
    """垂直行业节点：industry 关键词 → 节点列表（可按月过滤）。
    未指定行业时返回全部行业节点。
    """
    hits = []
    for ind, nodes in _V_NODES.items():
        if industry and ind not in industry and industry not in ind:
            # 允许用品类别名匹配（如"美妆"命中"美妆"）
            continue
        for n in nodes:
            if month is None or n.get("month") == month:
                hits.append(dict(n, industry=ind))
    return hits


# 垂直行业 → 情感主题 → 调性映射（并入 _THEME_TO_TONALITY 判断）
_V_THEME_TONALITY = {
    "陪伴": "premium", "治愈": "premium", "松弛": "premium", "微醺": "premium",
    "悦己": "premium", "仪式": "luxury", "文化": "premium", "成长": "premium",
    "狂欢": "mass", "松弛感": "premium",
}


def cross_industry_season(industry, date_str=""):
    """垂直行业 × 当月节气 交叉建议（触类旁通：行业节点与通用节点叠加）。
    返回 {"industry", "industry_nodes":[...], "month":m, "season_nodes":[...], "advice":[...]}
    """
    import datetime as _dt
    try:
        if len(date_str) == 5:
            m = int(date_str[:2])
        else:
            m = int((date_str or _dt.date.today().strftime("%Y-%m-%d"))[5:7])
    except Exception:
        m = _dt.date.today().month
    inds = industry_nodes(industry, m) or industry_nodes(industry)
    # 当月节气（通用节点中 kind==节气）
    season = [n for n in nodes_for_month(m) if n["kind"] == K_SOLAR]
    advice = []
    for n in inds[:2]:
        for s in season[:1]:
            advice.append("%s遇%s：%s × %s" % (n["name"], s["name"], n["theme"], s["theme"]))
    return {"industry": industry, "month": m, "industry_nodes": inds,
            "season_nodes": season, "advice": advice}

# 情感主题 → 调性偏好（须弥层：节点主题映射创意气质）
_THEME_TO_TONALITY = {
    "狂欢": "mass", "实惠": "mass", "玩梗": "mass", "变装": "mass", "热闹": "mass",
    "浪漫": "premium", "质感": "premium", "焕新": "premium", "成长": "premium",
    "温柔": "premium", "爱意": "premium", "悦己": "premium", "中秋": "premium",
    "克制": "luxury", "仪式": "luxury", "稀缺": "luxury", "工艺": "luxury", "安静": "luxury",
}


def _norm(cat):
    return _CAT_ALIAS.get(cat, [])


def nodes_for_month(month):
    """返回某月（1-12）全部节点。"""
    return list(_NODES.get(int(month), []))


def node_on(date_str):
    """给定 'YYYY-MM-DD' 或 'MM-DD'，返回当天命中节点（无则 []）。"""
    try:
        if len(date_str) == 5:
            d = date_str
        else:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%m-%d")
        hits = []
        for nodes in _NODES.values():
            for n in nodes:
                if n["date"] == d:
                    hits.append(n)
        return hits
    except Exception:
        return []


def suggest_hotspot(date_str, category=""):
    """核心能力：给定日期+品类 → 命中节点 + 情感主题 + 建议调性（芥子→须弥）。
    返回 {"date", "nodes":[{name,date,kind,theme}], "themes":[...], "tonality_advice":...}
    """
    try:
        if len(date_str) == 5:
            m = int(date_str[:2])
            d = date_str
        else:
            m = int(date_str[5:7])
            d = date_str[5:]  # 'MM-DD'
    except Exception:
        m = datetime.date.today().month
        d = ""
    nodes = nodes_for_month(m)
    alias = _norm(category)
    matched, themes = [], []
    for n in nodes:
        if d and n["date"] == d:
            matched.append(n)
        elif alias and any(a in n["cats"] for a in alias):
            matched.append(n)
        if n["name"] in ("中秋节", "春节", "跨年", "双11", "618 大促"):
            themes.append(n["theme"])
    if not matched:
        matched = nodes[:2]
    themes += [n["theme"] for n in matched[:3]]
    themes = list(dict.fromkeys(themes))[:4]
    to = [_THEME_TO_TONALITY[t] for t in themes if t in _THEME_TO_TONALITY]
    advice = "建议调性：%s" % (to[0] if to else "premium")
    return {"date": date_str, "month": m, "nodes": matched, "themes": themes,
            "tonality_advice": advice}


def yearly_summary():
    """全年营销节点概览（芥子→须弥聚合）：节点总数/每月分布/垂直行业数。"""
    total = sum(len(v) for v in _NODES.values())
    monthly = {m: len(v) for m, v in _NODES.items()}
    return {"total_nodes": total, "monthly": monthly, "industries": len(_V_NODES)}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="营销节点日历与品类适配")
    ap.add_argument("date", nargs="?", default="", help="日期 YYYY-MM-DD 或 MM-DD（默认今天）")
    ap.add_argument("--category", default="", help="品类，如 商业地产/美妆/母婴")
    ap.add_argument("--month", type=int, default=0, help="只看某月节点")
    ap.add_argument("--industry", default="", help="垂直行业节点，如 母婴/美妆/酒饮/文旅/教育/宠物/咖啡茶饮")
    ap.add_argument("--cross", default="", help="行业×节气交叉，如 --cross 母婴")
    a = ap.parse_args()
    if a.cross:
        c = cross_industry_season(a.cross, a.date or "")
        print("[%s %d月] 行业节点: %s" % (c["industry"], c["month"],
                                       "、".join(n["name"] for n in c["industry_nodes"])))
        print("当月节气: %s" % "、".join(n["name"] for n in c["season_nodes"]))
        for t in c["advice"]:
            print("  交叉建议:", t)
        return
    if a.industry:
        for n in industry_nodes(a.industry, a.month or None):
            print("[%s] %s（%s月）｜%s" % (n["industry"], n["name"], n.get("month", "全年"), n["theme"]))
        return
    if a.month:
        for n in nodes_for_month(a.month):
            print("[%s %s] %s｜%s" % (n["date"], n["kind"], n["name"], n["theme"]))
        return
    ds = a.date or datetime.date.today().strftime("%Y-%m-%d")
    r = suggest_hotspot(ds, a.category)
    print("日期: %s  品类: %s" % (r["date"], a.category or "全部"))
    print("节点:")
    for n in r["nodes"]:
        print("  - %s（%s %s）｜%s" % (n["name"], n["kind"], n["date"], n["theme"]))
    print("情感主题: %s" % " / ".join(r["themes"]))
    print(r["tonality_advice"])


if __name__ == "__main__":
    main()
