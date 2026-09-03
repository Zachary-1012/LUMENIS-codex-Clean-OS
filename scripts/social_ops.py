# -*- coding: utf-8 -*-
"""多平台社媒运营传播策略生成器（小红书/抖音/IG/Facebook/X/公众号）。

借鉴太古汇年度运营 learnings：KFS模型、5栏目体系、人群分层、
达人矩阵 KOL:KOC:素人=1:3:6、聚光投流、搜索品专、UGC共创、
爆款公式（热门事件×高级感视觉×品牌巧植入×福利驱动）。
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 平台运营方法论库 ----
PLATFORMS = {
    "小红书": {
        "name": "小红书",
        "ecosystem": "从生活指南向兴趣生态深化，内容=氛围感种草+兴趣价值传递",
        "content_columns": ["Show Time(制造爆点/场内活动)", "Bonus Time(激发行动/福利促销)",
                            "Trending Time(承接流量/线上精品店)", "Crush Time(承接流量/线下种草)",
                            "Treasure Time(沉淀粉丝/品牌底色)"],
        "viral_formula": "爆款公式=热门事件(IP/明星)×高级感视觉×品牌巧植入×福利驱动",
        "publish_rhythm": "发布节点前3-4天预热；封面简洁色调统一；视频15-60s竖屏3:4",
        "invest": "KFS模型：KOL/KOC/素人=1:3:6(KOC性价比最高) + 聚光投流(24h互动>20再放大) + 搜索品专(品牌词/长尾词/竞品拦截词)",
        "crowd_layers": "核心转化(本地高净值/白领)+潜力拉新(Z世代/周边潮流)+氛围造势(垂直兴趣)",
        "ugc": "低门槛活动激发UGC：打卡/话题/福利互动，UGC即传播",
        "metrics": "阅读/互动/爆文率/CPE(互动成本)/CPR(阅读成本)/粉丝增长/UGC数",
    },
    "抖音": {
        "name": "抖音",
        "ecosystem": "兴趣电商+爆款流量池，前3秒决定完播，完播率是分发第一权重",
        "content_columns": ["热点跟拍(借势热梗)", "达人共创(挑战赛/合拍)", "直播切片", "场景种草",
                            "品牌号IP短剧(连续内容沉淀)"],
        "viral_formula": "爆款=3秒钩子(冲突/悬念/反常识)×快节奏转场×参与机制(挑战/合拍)×评论区运营",
        "publish_rhythm": "15-30s竖屏9:16；黄金时段(午休/晚8-10)；一周3-5更保持账号活跃",
        "invest": "信息流投放+达人共创(星图)；爆款内容二次加热；DOU+小预算测款",
        "crowd_layers": "兴趣标签圈选(时尚/美食/运动)+地域+人群包(行为/DMP二次触达)",
        "ugc": "挑战赛/话题参与让用户拍同款，达人随机舞蹈/打卡激发自发UGC",
        "metrics": "完播率/互动率/转粉率/转化(GMV)/直播间在线/CPM",
    },
    "Instagram": {
        "name": "Instagram",
        "ecosystem": "视觉优先的年轻文化平台，Reels短视频+Stories日常+Feed美学阵地",
        "content_columns": ["Reels(15-30s创意短视频,算法主推)", "Stories(日常/倒计时/互动贴纸)",
                            "Feed(美学图阵,品牌视觉资产)", "IGTV(长内容)", "Threads(轻对话)"],
        "viral_formula": "高审美视觉×Reels原生节奏×Hashtag(精准+圈层)×Stories互动(投票/问答/倒计时)",
        "publish_rhythm": "Reels每周3-5条；Stories每日；高峰段(当地晚8-10)；统一视觉滤镜建立记忆点",
        "invest": "Meta广告(Reels广告+Story ads)；KOL/KOC共创(UGC即素材)；Lookalike人群放大",
        "crowd_layers": "地域+兴趣+行为数据定向；Creator audience 相似人群",
        "ugc": "品牌Hashtag挑战+用户晒单@品牌；共创UGC授权再投放",
        "metrics": "Reach/Engagement/Reels plays/Profile visits/Follows/CTR",
    },
    "Facebook": {
        "name": "Facebook",
        "ecosystem": "社群+广告的成熟平台，粉丝群组/社群运营价值高，中高龄+下沉市场覆盖",
        "content_columns": ["社群运营(Facebook Group,私域沉淀)", "品牌页内容(资讯/故事/活动)",
                            "直播(带货/发布会)", "广告(精准投放成熟)"],
        "viral_formula": "社群共鸣内容×真实故事(用户证言)×本地化运营×广告精准放大",
        "publish_rhythm": "品牌页每周3-5条；群组日常互动；直播活动节点",
        "invest": "Meta广告全漏斗(认知→考虑→转化)；Lookalike+Retargeting；购物目录广告",
        "crowd_layers": "兴趣+行为+自定义受众(邮件/网站访客)再营销",
        "ugc": "群组内用户晒单/问答；UGC授权为广告素材(真实感)",
        "metrics": "Reach/Engagement/Group活跃/Lead/ROAS",
    },
    "X": {
        "name": "X(Twitter)",
        "ecosystem": "实时话题+舆论场，文化时刻/热搜是传播引擎，适合事件营销与实时互动",
        "content_columns": ["实时热梗(借势文化时刻)", "Threads(观点长文)", "投票互动", "话题运营",
                            "品牌账号人格化(玩梗/回应)"],
        "viral_formula": "实时文化时机×犀利观点/玩梗×参与机制(投票/引用回复)×话题标签破圈",
        "publish_rhythm": "高频实时更新；紧跟热点黄金期(数小时内)；人格化口吻",
        "invest": "Promoted Trends(话题)+Promoted Posts；事件节点大预算引爆",
        "crowd_layers": "关键词+话题+兴趣定向；事件营销借势",
        "ugc": "话题共创+用户引用互动；让用户造梗传播",
        "metrics": "Impressions/Engagements/Reactions/Reposts/Trend reach",
    },
    "公众号": {
        "name": "微信公众号",
        "ecosystem": "私域内容阵地+服务号交易能力，深度内容/品牌资产/会员沉淀的官方主场",
        "content_columns": ["深度长文(品牌叙事/行业洞察)", "栏目化运营(固定栏目养成阅读习惯)",
                            "服务号推送(交易/会员)", "视频号联动", "留言互动"],
        "viral_formula": "深度价值×选题精准(圈层痛点)×标题党克制(不标题党但信息前置)×转发激励(社交货币)",
        "publish_rhythm": "订阅号每周1-2篇深度；固定栏目固定时间(如每周三晚8点)；服务号每月4次权益",
        "invest": "朋友圈广告(精准地域/人群)+搜一搜SEO(关键词占位)+视频号直播引流",
        "crowd_layers": "私域会员分层(高净值/潜力/长尾)；朋友圈LBS+兴趣定向",
        "ugc": "留言互动+征文/故事征集；会员社群共创",
        "metrics": "阅读/在看/分享/涨粉/会员转化/私域活跃",
    },
    "TikTok": {
        "name": "TikTok(海外抖音)",
        "ecosystem": "全球短视频+兴趣电商，算法主推完播/互动/分享，原生真实感内容占优",
        "content_columns": ["Trending声效/挑战(借平台热梗)", "AI-Enhanced UGC(脚本/剪辑AI化但保持真实感)",
                            "创作者共创(达人挑战/合拍)", "TikTok Shop(可购物直播/短视频)", "品牌号持续人设"],
        "viral_formula": "前3秒organic感(无logo splash)×原生声效/挑战×参与机制(duet/stitch/挑战赛)×评论区运营——AI-UGC成本可-60%",
        "publish_rhythm": "每周3-5条竖屏9:16；跟随平台趋势声效黄金期(数小时内)；lo-fi真实感优先",
        "invest": "Spark Ads(原生创作者内容加热)+Smart Performance(智能投放)+TikTok Shop直播",
        "crowd_layers": "兴趣标签+行为数据+Creator相似人群；海外多市场本地化",
        "ugc": "挑战赛/声效共创让全球用户拍同款；UGC授权再投放",
        "metrics": "完播率/互动/转粉/直播GMV/CPA/CPM",
    },
    "YouTube": {
        "name": "YouTube",
        "ecosystem": "长内容+搜索+订阅，品牌叙事/教程/纪录片的主场，搜索SEO价值高",
        "content_columns": ["长视频(品牌纪录片/深度叙事)", "Shorts(竖屏引流切片)", "品牌频道(内容资产沉淀)",
                            "直播(发布会/互动)", "搜索占位(品类关键词)"],
        "viral_formula": "深度价值×订阅养成×Shorts切片导流长视频×搜索SEO占位——创始人/专家口述观看完成率+42%",
        "publish_rhythm": "长视频每周1-2条+Shorts每日；固定栏目时间；片头3秒钩子",
        "invest": "TrueView(可跳过广告)+Shorts Feed广告+品牌频道内容资产(长尾SEO)",
        "crowd_layers": "兴趣+搜索意图+订阅人群；相似受众Lookalike",
        "ugc": "评论区互动+用户投稿(故事征集)；创作者联盟(creator partnership)",
        "metrics": "观看时长/订阅增长/Shorts完播/搜索排名/CTR/ROAS",
    },
    "Threads": {
        "name": "Threads(海外微博)",
        "ecosystem": "X的轻量替代，文字社交+实时对话，品牌人格化/观点表达/即时互动的场",
        "content_columns": ["品牌人格化口吻(玩梗/观点)", "实时话题(热点即时反应)", "Thread(观点串联长文)",
                            "投票互动", "创始人/团队日常"],
        "viral_formula": "真实人格×犀利观点/玩梗×高发布频次×回应互动——文字即内容,人格即记忆点",
        "publish_rhythm": "高发布频次(每日多条)；紧跟平台趋势话题；口语化不官方",
        "invest": "付费推广尚轻(以自然流量为主)；与X/IG联动矩阵",
        "crowd_layers": "话题+兴趣定向(平台较新,投放池小)",
        "ugc": "话题共创+用户引用互动；鼓励用户造梗",
        "metrics": "Impressions/Engagements/Replies/Reposts/Profile visits",
    },
}


def generate_social_ops(brand, platform, circle="都市职场", tonality="premium", hotspot=""):
    """生成单平台运营传播策略。"""
    p = PLATFORMS.get(platform)
    if not p:
        raise ValueError("平台不支持: %s" % platform)
    tone = {"mass": "大众", "premium": "中高端", "luxury": "高奢"}.get(tonality, "中高端")
    lux = tonality == "luxury"
    return {
        "meta": {"brand": brand, "platform": p["name"], "circle": circle,
                 "tonality": tone, "hotspot_bind": "绑定热点「%s」" % hotspot if hotspot else ("克制不追热点" if lux else "择机踩文化时机")},
        "ecosystem": p["ecosystem"],
        "content_columns": p["content_columns"],
        "viral_formula": p["viral_formula"] + ("（高奢调性：克制叙事，不参与流量狂欢）" if lux else ""),
        "publish_rhythm": p["publish_rhythm"] + ("；高奢调性建议：私享首发+邀请制" if lux else ""),
        "invest": p["invest"],
        "crowd_layers": p["crowd_layers"],
        "ugc": p["ugc"],
        "metrics": p["metrics"],
        "tone_advice": {"mass": "玩梗破圈、参与机制、狂欢放大", "premium": "质感叙事、场景种草、圈层认同",
                        "luxury": "克制稀缺、工艺故事、私域仪式"}.get(tonality, ""),
    }


def generate_social_matrix(brand, platforms=None, circle="都市职场", tonality="premium", hotspot=""):
    """生成多平台运营传播矩阵（默认全平台）。"""
    if platforms is None:
        platforms = list(PLATFORMS.keys())
    return {p: generate_social_ops(brand, p, circle, tonality, hotspot) for p in platforms if p in PLATFORMS}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="多平台社媒运营传播策略生成器")
    ap.add_argument("--brand", default="示例品牌")
    ap.add_argument("--platform", default="", help="单平台(小红书/抖音/Instagram/Facebook/X/公众号)；空=全矩阵")
    ap.add_argument("--circle", default="都市职场")
    ap.add_argument("--tonality", default="premium", choices=["mass", "premium", "luxury"])
    ap.add_argument("--hotspot", default="")
    a = ap.parse_args()
    if a.platform:
        r = generate_social_ops(a.brand, a.platform, a.circle, a.tonality, a.hotspot)
    else:
        r = generate_social_matrix(a.brand, None, a.circle, a.tonality, a.hotspot)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
