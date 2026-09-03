# -*- coding: utf-8 -*-
"""视频创意分析脚本模板生成器（TVC/概念片/小红书视频/抖音视频）。

对标太古汇视频脚本规范（每镜头：场景/景别/时长/画面内容/画面参考/服装动作）
+ 阳狮六阶段SOP（洞察→策略→概念→方案→执行→复盘）+ 各平台原生规格。

用法：
  from scripts.video_script import generate_video_script
  s = generate_video_script("岚序", "美妆个护", "高奢小众", "luxury", "tvc",
                            product_point="东方节气香氛", hotspot="中秋")
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.idea_generator import CIRCLE_SYMBOLS, TONALITIES

# ---- 视频类型规格与节奏 ----
VIDEO_TYPES = {
    "tvc": {
        "name": "TVC / 电视广告",
        "ratio": "16:9 横屏", "duration": "30-60s", "purpose": "品牌主张 / 记忆符号",
        "structure": [("钩子", "3-5s", "用冲突/悬念/惊艳画面抓住注意力"),
                      ("展开", "15-20s", "产品/场景/故事展开，建立品牌价值"),
                      ("升华", "5-10s", "品牌口号 + 标志性符号 + logo收尾")],
    },
    "concept": {
        "name": "品牌概念片",
        "ratio": "16:9 / 9:16", "duration": "60-120s", "purpose": "世界观 / 情绪共鸣",
        "structure": [("世界观引入", "15-20s", "建立品牌世界/情绪基调"),
                      ("情绪展开", "30-60s", "故事/人物/冲突，情感浓度递增"),
                      ("品牌宣言", "10-15s", "一句话宣言 + 品牌符号升华")],
    },
    "xhs": {
        "name": "小红书视频",
        "ratio": "3:4 / 4:5 竖屏", "duration": "15-60s", "purpose": "种草 / 探店 / 教程",
        "structure": [("封面钩子", "3-5s", "封面即利益点，前置核心信息"),
                      ("内容种草", "10-30s", "真实体验/场景/细节，氛围感"),
                      ("行动号召", "3-5s", "关注/收藏/评论区互动引导")],
    },
    "douyin": {
        "name": "抖音视频",
        "ratio": "9:16 竖屏", "duration": "15-30s", "purpose": "爆款节奏 / 破圈",
        "structure": [("3秒爆点", "3s", "前3秒必须抓住注意力（冲突/悬念/反常识）"),
                      ("内容快进", "8-20s", "快节奏信息/转场/多机位，保持完播"),
                      ("反转/CTA", "3-5s", "反转或行动号召，引导互动")],
    },
    "tiktok": {
        "name": "TikTok(海外抖音)",
        "ratio": "9:16 竖屏", "duration": "15-45s", "purpose": "全球破圈 / 原生声效挑战",
        "structure": [("有机开头", "1-3s", "前3秒必须像organic内容(无logo无片头)，贴合原生信息流"),
                      ("声效/挑战钩子", "5-15s", "借平台Trending声效/挑战/duet参与机制放大"),
                      ("完播CTA", "3-8s", "引导评论/合拍/挑战赛参与，制造UGC")],
    },
}

# ---- 品类场景库（每镜头画面描述的素材）----
CATEGORY_SCENES = {
    "美妆个护": ["梳妆台特写", "指尖划过瓶身", "妆容渐变特写", "香氛弥漫慢镜", "使用前后对比"],
    "餐饮": ["热气升腾特写", "大快朵颐慢镜", "食客笑脸", "食材细节", "门店氛围"],
    "汽车": ["流线车身光影", "仪表盘启动", "城市穿行", "赛道疾驰", "内饰质感"],
    "文旅": ["航拍地标", "行走街巷", "展览馆光影", "人文互动", "夜色灯火"],
    "科技数码": ["产品悬浮转场", "界面交互特写", "参数可视化", "生活场景应用", "极简棚拍"],
    "金融": ["城市天际线", "办公场景", "信任握手", "数据流动", "家庭守护"],
    "服装鞋包": ["面料细节", "穿搭变装", "街拍动态", "秀场光影", "工艺针脚"],
    "家居": ["晨光洒入", "生活场景", "质感细节", "空间氛围", "家人互动"],
    "母婴": ["亲子互动", "成长瞬间", "温软触感", "家庭日常", "安心笑容"],
    "运动": ["奔跑动态", "汗水特写", "突破瞬间", "自然户外", "训练专注"],
    "酒水": ["液体流动慢镜", "举杯时刻", "宴席氛围", "酒窖光影", "品鉴特写"],
    "商业地产": ["商场中庭", "品牌橱窗", "人流涌动", "艺术装置", "夜景观光"],
    "通用": ["产品特写", "生活场景", "人物情绪", "空间氛围", "光影细节"],
}

# ---- TVC/视频专业制作方法论（来源：heeds/Granite River/Viva/搜狐制作全流程，2026-09 研究）----
PRODUCTION_WORKFLOW = [
    ("1.Brief 简报", "明确商业目标/目标人群/核心信息/预算/投放渠道/成功指标(KPI)，一页纸说清「对谁说、说什么、要他做什么」"),
    ("2.Concept 概念", "出3-5个创意方向(含脚本雏形/视觉参考/调性参考)供选，每个方向一句话Big Idea+情绪基调"),
    ("3.Script 脚本", "文学脚本：30s≈75-90字配音(每秒都有任务)、60s≈150-180字；先情感连接再理性利益(lead with feeling, justify with logic)；标VO/对白/画面/字幕"),
    ("4.Storyboard 分镜", "20-40帧逐镜画：机位/景别/运动/演员动作/道具/字幕/时长；分镜是最便宜的纠错阶段(visual problems solved cheaply)"),
    ("5.Pre-production 前期", "选角/勘景/美术道具/服装/拍摄日程/通告单/设备清单；前期越充分拍摄当天越省(拍摄是最烧钱阶段,日成本数万至数十万)"),
    ("6.Shoot 拍摄", "走场彩排→逐镜拍摄→多拍保条(B-roll/空镜/特写)；现场监看画面与焦点/收音"),
    ("7.Post 后期", "粗剪→精剪→调色(DI)→配乐/音效/混音→字幕/特效→多版本(15s/30s/60s,横竖屏适配各平台)"),
    ("8.Delivery 交付投放", "母版+各平台规格版；节点前3-4天预热；投放后看完播/互动/转化回流优化下一支"),
]
# 分镜镜头语言速查
SHOT_LANGUAGE = {
    "景别": "大远景(环境/孤独感)·远景(人与环境)·全景(动作)·中景(对话/关系)·近景(情绪)·特写(细节/质感)·大特写(强烈情绪)",
    "运镜": "推(聚焦/逼近真相)·拉(抽离/孤独)·摇(展示环境)·移(陪伴/流动)·跟(沉浸)·升降(权力/格局)·手持(真实/紧张)·固定(克制/高级)",
    "节奏": "3秒一变(短视频)·情绪递进·留白(高奢用静与慢)·音乐卡点转场·首尾呼应",
    "光线": "柔光(亲和/美妆)·硬光(力量/运动)·逆光(轮廓/高级)·自然光(真实lo-fi)·黄金时刻(温暖/文旅)",
}


# ---- 平台标题/封面文案模板（统一3占位：品牌/卖点/圈层）----
TITLE_TEMPLATES = {
    "xhs": ["「%s」%s，%s的人都在看", "发现%s｜%s的正确打开方式", "谁懂啊，%s竟然可以%s"],
    "douyin": ["%s挑战，%s直接破防，%s都顶不住", "3秒带你认识%s的%s", "别再问了，%s就是%s，%s"],
    "tiktok": ["POV: %s meets %s #%s", "Is %s the new %s? #%s", "%s × %s — creators are going wild #%s"],
    "tvc": ["%s：%s——%s", "%s，%s｜%s"],
    "concept": ["%s｜%s，%s", "%s：%s（%s）"],
}


def _scene(brand, category, circle, product_point, scenes):
    """生成一个镜头描述（品类场景 × 圈层符号 × 品牌/卖点）。"""
    cs = CIRCLE_SYMBOLS.get(circle, CIRCLE_SYMBOLS["都市职场"])
    scene = scenes[0] if scenes else "产品特写"
    return "%s（%s）· 融入%s" % (scene, product_point or brand, cs["symbols"][0])


def _emotion_hook(brand, topic, circle, tonality):
    """视频情感钩子：复用情感共鸣句库（韩剧×文学手法），一句话直击人心。"""
    from scripts.idea_generator import emotion_hook
    import random
    return emotion_hook(brand, topic=topic or brand, circle=circle, tonality=tonality,
                        rng=random.Random())


def generate_video_script(brand, category="通用", circle="都市职场", tonality="premium",
                          video_type="tvc", product_point="", hotspot="", n_shots=None):
    """生成视频创意分析脚本。返回结构化脚本（可 JSON 输出）。"""
    vtype = VIDEO_TYPES.get(video_type, VIDEO_TYPES["tvc"])
    scenes = CATEGORY_SCENES.get(category, CATEGORY_SCENES["通用"])
    tone = TONALITIES.get(tonality, TONALITIES["premium"])["name"]
    cs = CIRCLE_SYMBOLS.get(circle, CIRCLE_SYMBOLS["都市职场"])
    # 镜头数：TVC 4-6 / 概念 6-8 / xhs 5-7 / douyin 4-6
    default_n = {"tvc": 5, "concept": 7, "xhs": 6, "douyin": 5, "tiktok": 6}[video_type]
    n = n_shots or default_n

    shots = []
    struct = vtype["structure"]
    # 按结构分配镜头
    seg = max(1, n // len(struct))
    si = 0
    for i in range(n):
        s_meta = struct[min(si, len(struct) - 1)]
        part, dur, purpose = s_meta
        if (i + 1) % seg == 0 and si < len(struct) - 1:
            si += 1
            s_meta = struct[si]
            part, dur, purpose = s_meta
        tone_hint = "克制·静谧" if tonality == "luxury" else ("快节奏·高能" if video_type in ("douyin", "tiktok") else "氛围感·质感")
        shots.append({
            "shot": i + 1,
            "part": part,
            "purpose": purpose,
            "scene": _scene(brand, category, circle, product_point, [scenes[i % len(scenes)]]),
            "shot_size": ("特写" if i % 2 == 0 else "中景/全景"),
            "duration": dur if i == 0 or i == n - 1 else "3-5s",
            "content": "镜头%d：%s · 调性%s · 服务%s人群" % (i + 1, purpose, tone_hint, circle),
            "audio": "背景音乐/BGM" if i < n - 1 else "音乐收尾+品牌音效",
            "subtitle": "%s，%s" % (brand, product_point or part),
            "ref": "参考：%s" % cs["examples"],
        })

    titles = TITLE_TEMPLATES.get(video_type, TITLE_TEMPLATES["xhs"])
    title = titles[0] % (brand, product_point or "上新", circle.split("/")[0])
    title_candidates = []
    for tpl in titles[:3]:
        try:
            title_candidates.append(tpl % (brand, product_point or "上新", circle.split("/")[0]))
        except TypeError:
            title_candidates.append(tpl % (brand, product_point or "上新"))
    hotspot_bind = "绑定热点「%s」" % hotspot if hotspot else ("克制不追热点" if tonality == "luxury" else "择机踩文化时机")

    return {
        "meta": {
            "brand": brand, "category": category, "circle": circle, "tonality": tone,
            "video_type": vtype["name"], "ratio": vtype["ratio"], "duration": vtype["duration"],
            "purpose": vtype["purpose"], "product_point": product_point, "hotspot_bind": hotspot_bind,
        },
        "big_idea": "%s：%s" % (brand, product_point or "品牌主张"),
        "emotion_hook": _emotion_hook(brand, product_point, circle, tonality),
        "structure": struct,
        "title_candidates": title_candidates,
        "shots": shots,
        "publish_advice": _publish_advice(video_type, tonality),
        "production_workflow": PRODUCTION_WORKFLOW,
        "shot_language": SHOT_LANGUAGE,
    }


def _publish_advice(video_type, tonality):
    base = {
        "tvc": "投放：电视+视频号+朋友圈广告；重点在黄金时段/节点前3-4天预热",
        "concept": "投放：发布会/首映+社媒矩阵首发；内容长尾运营，搜索占位",
        "xhs": "投放：KFS模型（达人种草+聚光投流+搜索品专）；封面前置利益点",
        "douyin": "投放：信息流+达人共创；前3秒完播率是核心指标，24h内互动超20+再放大",
        "tiktok": "投放：Spark Ads(原生创作者内容加热)+Smart Performance；借Trending声效/挑战，AI-UGC低成本多版本测钩子",
    }.get(video_type, "")
    if tonality == "luxury":
        base += "；高奢调性：首发圈层私享+邀请制，不铺量"
    return base


def main():
    import argparse
    ap = argparse.ArgumentParser(description="视频创意分析脚本模板生成器")
    ap.add_argument("--brand", default="示例品牌")
    ap.add_argument("--category", default="通用")
    ap.add_argument("--circle", default="都市职场", choices=list(CIRCLE_SYMBOLS.keys()))
    ap.add_argument("--tonality", default="premium", choices=list(TONALITIES.keys()))
    ap.add_argument("--type", default="tvc", choices=list(VIDEO_TYPES.keys()))
    ap.add_argument("--point", default="", help="产品卖点/概念")
    ap.add_argument("--hotspot", default="")
    ap.add_argument("--shots", type=int, default=0)
    a = ap.parse_args()
    r = generate_video_script(a.brand, a.category, a.circle, a.tonality, a.type,
                              a.point, a.hotspot, a.shots or None)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
