"""
公关案例整合模块 v1.0
功能：
1. 全网舆情案例库（15个典型案例）
2. 6个场景话术模板
3. ACT法则（Acknowledge-Confirm-Take action）
4. 5个专报触发条件
5. 笔记详情页"案例对标"和"话术推荐"
6. API接口
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, request

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

pr_case_bp = Blueprint('pr_case', __name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db')


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================
# 1. 全网舆情案例库（15个典型案例）
# ============================================

PR_CASES = [
    {
        'id': 1,
        'title': '海底捞后厨卫生事件',
        'brand': '海底捞',
        'industry': '餐饮',
        'type': '食品安全',
        'severity': 'high',
        'summary': '2017年媒体曝光海底捞北京两家门店后厨老鼠横行、火锅漏勺掏下水道等卫生问题',
        'response': '3小时内发布致歉信，承认问题，承诺整改，不推诿，不辩解',
        'effect': '舆情迅速平息，品牌形象未受重大影响，被称为"教科书级危机公关"',
        'lesson': '快速响应、真诚道歉、承担责任、立即整改',
        'keywords': ['卫生', '老鼠', '后厨', '食品安全', '道歉']
    },
    {
        'id': 2,
        'title': '星巴克咖啡致癌谣言',
        'brand': '星巴克',
        'industry': '餐饮',
        'type': '谣言',
        'severity': 'medium',
        'summary': '2018年自媒体发文称星巴克咖啡含致癌物质丙烯酰胺，引发广泛传播',
        'response': '发布科学说明，引用权威机构数据，解释丙烯酰胺在烘焙食品中普遍存在且含量在安全范围内',
        'effect': '谣言被澄清，品牌形象未受损',
        'lesson': '用科学数据说话，引用权威机构，不情绪化回应',
        'keywords': ['致癌', '谣言', '丙烯酰胺', '咖啡', '科学']
    },
    {
        'id': 3,
        'title': '杜嘉班纳辱华事件',
        'brand': 'D&G',
        'industry': '奢侈品',
        'type': '品牌价值观',
        'severity': 'critical',
        'summary': '2018年D&G发布涉嫌辱华的广告视频，设计师在社交媒体发表不当言论，引发中国消费者强烈抵制',
        'response': '初期辩解称账号被盗，后被迫道歉，但已无法挽回局面',
        'effect': '中国市场全面下架，明星解约，大秀取消，品牌形象严重受损',
        'lesson': '尊重当地文化，价值观问题不能回避，初期回应态度决定后续走向',
        'keywords': ['辱华', '广告', '设计师', '抵制', '价值观']
    },
    {
        'id': 4,
        'title': '顺丰快递员被打事件',
        'brand': '顺丰',
        'industry': '物流',
        'type': '员工权益',
        'severity': 'medium',
        'summary': '2016年顺丰快递员被车主掌掴，视频在网上传播，引发公众对快递员权益的关注',
        'response': '顺丰总裁王卫公开表态"如果这事不追究到底，我不再配做顺丰总裁"，公司力挺员工',
        'effect': '品牌形象大幅提升，员工归属感增强，公众好感度上升',
        'lesson': '保护员工就是保护品牌，高层表态要有力量，立场要坚定',
        'keywords': ['快递员', '被打', '员工', '总裁', '力挺']
    },
    {
        'id': 5,
        'title': '携程亲子园虐童事件',
        'brand': '携程',
        'industry': '互联网',
        'type': '社会责任',
        'severity': 'critical',
        'summary': '2017年携程自营亲子园被曝老师虐童，喂孩子芥末、消毒水，引发社会震怒',
        'response': 'CEO公开道歉，承诺追责，亲子园关停，但回应被指不够及时和真诚',
        'effect': '品牌形象严重受损，CEO引咎辞职，企业社会责任受到质疑',
        'lesson': '涉及儿童的事件敏感度极高，必须第一时间回应，态度要极其诚恳',
        'keywords': ['虐童', '亲子园', '芥末', '儿童', '社会责任']
    },
    {
        'id': 6,
        'title': '华为孟晚舟事件',
        'brand': '华为',
        'industry': '科技',
        'type': '国际政治',
        'severity': 'critical',
        'summary': '2018年华为CFO孟晚舟在加拿大被拘捕，引发中美科技博弈',
        'response': '华为官方声明尊重法律，同时强调公司合规经营，任正非公开访谈展现格局',
        'effect': '华为品牌形象反而提升，民族品牌认同感增强',
        'lesson': '面对复杂国际事件，保持理性和格局，不情绪化，相信法律',
        'keywords': ['孟晚舟', '拘捕', '加拿大', '合规', '国际']
    },
    {
        'id': 7,
        'title': '瑞幸咖啡财务造假',
        'brand': '瑞幸',
        'industry': '餐饮',
        'type': '诚信危机',
        'severity': 'critical',
        'summary': '2020年瑞幸咖啡自曝财务造假22亿元，股价暴跌，面临退市',
        'response': '成立独立委员会调查，CEO被免职，积极配合监管，努力维持运营',
        'effect': '股价暴跌90%，从纳斯达克退市，但通过后续运营逐步恢复',
        'lesson': '诚信是企业生命线，造假代价巨大，造假后要彻底整改重建信任',
        'keywords': ['财务造假', '股价', '退市', '诚信', '调查']
    },
    {
        'id': 8,
        'title': '胖东来超市服务标杆',
        'brand': '胖东来',
        'industry': '零售',
        'type': '正面案例',
        'severity': 'low',
        'summary': '胖东来以极致服务著称，员工待遇好，顾客满意度高，被称为"超市界的海底捞"',
        'response': '持续优化服务，员工幸福感高，口碑传播',
        'effect': '品牌美誉度极高，成为行业标杆，顾客忠诚度极高',
        'lesson': '好的服务就是最好的公关，员工幸福才能让顾客幸福',
        'keywords': ['服务', '员工', '口碑', '标杆', '幸福']
    },
    {
        'id': 9,
        'title': '特斯拉刹车失灵维权',
        'brand': '特斯拉',
        'industry': '汽车',
        'type': '产品质量',
        'severity': 'high',
        'summary': '2021年上海车展特斯拉车主站车顶维权，称刹车失灵，引发广泛关注',
        'response': '初期回应强硬，称"决不妥协"，后迫于压力道歉并成立调查小组',
        'effect': '品牌形象受损，销量受影响，被指缺乏同理心',
        'lesson': '消费者维权事件要先共情再调查，态度强硬会激化矛盾',
        'keywords': ['刹车', '维权', '车展', '车顶', '产品质量']
    },
    {
        'id': 10,
        'title': '鸿星尔克河南暴雨捐款',
        'brand': '鸿星尔克',
        'industry': '运动品牌',
        'type': '正面案例',
        'severity': 'low',
        'summary': '2021年河南暴雨，鸿星尔克默默捐款5000万，被网友发现后引发"野性消费"',
        'response': '老板亲自直播感谢，呼吁理性消费，员工加班发货',
        'effect': '品牌一夜爆红，销量暴增，国货认同感大幅提升',
        'lesson': '真诚行善自有回报，品牌价值观是最好的营销',
        'keywords': ['捐款', '河南', '暴雨', '野性消费', '国货']
    },
    {
        'id': 11,
        'title': '李佳琦直播间花西子事件',
        'brand': '花西子/李佳琦',
        'industry': '美妆',
        'type': '公众人物',
        'severity': 'high',
        'summary': '2023年李佳琦直播间评论花西子眉笔价格，说"哪里贵了，有时候找找自己原因，这么多年工资涨没涨"，引发网友不满',
        'response': '当晚直播道歉，次日发布书面道歉信，暂停直播一段时间',
        'effect': '掉粉百万，花西子品牌形象受损，被指脱离群众',
        'lesson': '公众人物要谨言慎行，共情消费者，不要居高临下',
        'keywords': ['李佳琦', '花西子', '眉笔', '工资', '道歉']
    },
    {
        'id': 12,
        'title': '宝马MINI冰淇淋事件',
        'brand': '宝马MINI',
        'industry': '汽车',
        'type': '歧视',
        'severity': 'high',
        'summary': '2023年上海车展宝马MINI展台发放冰淇淋，区别对待中国人和外国人，引发热议',
        'response': '发布道歉声明，称是管理疏忽，承诺培训员工',
        'effect': '品牌形象受损，被指歧视中国人，车展热度被负面舆情覆盖',
        'lesson': '涉及歧视的事件敏感度极高，要真诚道歉，不要找借口',
        'keywords': ['冰淇淋', '车展', '歧视', '区别对待', '道歉']
    },
    {
        'id': 13,
        'title': '新东方转型直播带货',
        'brand': '新东方',
        'industry': '教育',
        'type': '转型',
        'severity': 'medium',
        'summary': '2021年教培行业政策调整，新东方转型直播带货，董宇辉双语直播走红',
        'response': '俞敏洪带领团队转型，不抱怨政策，积极探索新方向',
        'effect': '成功转型，东方甄选成为直播电商新势力，品牌形象提升',
        'lesson': '面对行业变革，积极转型，发挥自身优势，不抱怨不放弃',
        'keywords': ['转型', '直播', '董宇辉', '双语', '教培']
    },
    {
        'id': 14,
        'title': '椰树集团直播风格争议',
        'brand': '椰树',
        'industry': '饮料',
        'type': '营销争议',
        'severity': 'medium',
        'summary': '椰树集团直播风格延续一贯"土味"和"擦边"风格，引发争议，多次被平台封禁',
        'response': '坚持自身风格，不随大流，认为这是品牌特色',
        'effect': '争议带来流量，品牌辨识度高，但也面临监管风险',
        'lesson': '品牌特色要把握尺度，争议营销有风险，要注意合规',
        'keywords': ['直播', '土味', '擦边', '风格', '争议']
    },
    {
        'id': 15,
        'title': '蜂花洗发水捡箱子',
        'brand': '蜂花',
        'industry': '美妆',
        'type': '正面案例',
        'severity': 'low',
        'summary': '2021年蜂花被传"倒闭"，网友发现其包装简陋，用纸箱发货，引发"心疼"，销量暴增',
        'response': '官方幽默回应，感谢网友支持，承诺提升包装但保持性价比',
        'effect': '品牌翻红，销量大增，国货认同感提升',
        'lesson': '真诚和性价比是最好的品牌资产，网友的"心疼"也是一种情感连接',
        'keywords': ['蜂花', '倒闭', '纸箱', '国货', '性价比']
    }
]


# ============================================
# 2. 6个场景话术模板
# ============================================

PR_TEMPLATES = {
    'product_quality': {
        'name': '产品质量问题',
        'scenario': '产品出现质量问题，消费者投诉或媒体曝光',
        'template': '''【致歉声明】

尊敬的消费者：

我们非常重视您反馈的关于{product}的质量问题，对此给您带来的不便，我们深表歉意。

我们已第一时间成立专项调查小组，对相关批次产品进行全面检测，并将在{timeframe}内公布调查结果。

如您购买的产品存在类似问题，请联系我们的客服热线{hotline}，我们将为您提供{solution}。

感谢您的监督与反馈，我们将持续改进产品质量，为消费者提供更优质的产品和服务。

{brand}
{date}''',
        'key_points': ['快速响应', '真诚道歉', '成立调查组', '给出时间表', '提供解决方案', '感谢监督']
    },
    'service_attitude': {
        'name': '服务态度问题',
        'scenario': '员工服务态度不好，消费者投诉或视频曝光',
        'template': '''【关于{incident}的说明】

尊敬的顾客：

我们关注到网络上关于{incident}的视频/反馈，对此给当事人带来的不好体验，我们深表歉意。

经核实，涉事员工确实存在服务态度问题，我们已对其进行{punishment}，并将在全公司开展服务培训。

我们始终将顾客体验放在首位，如您在消费过程中遇到任何问题，请随时联系我们。

感谢您的监督，我们将以此为鉴，持续提升服务水平。

{brand}
{date}''',
        'key_points': ['承认问题', '不护短', '处理涉事员工', '全员培训', '感谢监督']
    },
    'safety_incident': {
        'name': '安全事故',
        'scenario': '发生安全事故，人员受伤或财产损失',
        'template': '''【关于{incident}的情况通报】

尊敬的公众：

{time}，我司{location}发生{incident}，我们对此深表痛心和歉意。

目前，伤者已送往医院救治，我们将全力配合治疗，并承担相应责任。事故原因正在调查中，我们将及时公布进展。

我们已成立应急处理小组，全面排查安全隐患，防止类似事件再次发生。

如有相关线索或疑问，请联系{contact}。

{brand}
{date}''',
        'key_points': ['第一时间通报', '表达痛心', '救治伤者', '承担责任', '调查原因', '排查隐患', '及时更新']
    },
    'rumor_clarification': {
        'name': '谣言澄清',
        'scenario': '出现关于品牌的不实信息或谣言',
        'template': '''【关于{rumor_topic}的严正声明】

近日，网络上出现关于{rumor_topic}的不实信息，对此我们严正声明：

上述内容均为不实信息，严重误导了公众，损害了我司品牌声誉。

事实真相是：{fact}。

我们已对相关不实信息进行取证，并保留追究法律责任的权利。

请广大消费者不信谣、不传谣，以我司官方信息为准。如有疑问，请联系{contact}。

{brand}
{date}''',
        'key_points': ['态度坚决', '澄清事实', '提供证据', '保留追责权利', '引导公众']
    },
    'price_controversy': {
        'name': '价格争议',
        'scenario': '产品定价引发争议，被指太贵或价格歧视',
        'template': '''【关于{product}定价的说明】

尊敬的消费者：

我们关注到关于{product}定价的讨论，感谢大家的关注和反馈。

{product}的定价是基于{pricing_basis}综合考虑的，我们承诺价格公开透明，不存在{controversy_point}。

如您对价格有任何疑问，欢迎联系我们的客服，我们将为您详细解答。

我们始终致力于为消费者提供物有所值的产品和服务，感谢您的理解与支持。

{brand}
{date}''',
        'key_points': ['感谢关注', '解释定价依据', '承诺透明', '提供咨询渠道', '表达诚意']
    },
    'employee_issue': {
        'name': '员工问题',
        'scenario': '员工不当言论或行为引发舆情',
        'template': '''【关于{employee_issue}的声明】

尊敬的公众：

我们关注到{employee}的相关言论/行为，对此造成的不良影响，我们深表歉意。

经核实，该言论/行为仅代表其个人观点，不代表公司立场。我司已对其进行{punishment}。

我司始终坚持{value}，将加强员工价值观教育，杜绝类似事件再次发生。

感谢社会各界的监督，我们将以此为鉴，不断完善管理。

{brand}
{date}''',
        'key_points': ['切割个人行为', '不代表公司', '处理员工', '强调价值观', '加强管理']
    }
}


# ============================================
# 3. ACT法则
# ============================================

ACT_PRINCIPLE = {
    'name': 'ACT法则',
    'full_name': 'Acknowledge - Confirm - Take action',
    'description': '危机公关三步法则：承认问题 - 确认事实 - 采取行动',
    'steps': [
        {
            'step': 'A - Acknowledge（承认）',
            'description': '第一时间承认问题存在，不回避、不推诿、不辩解',
            'key_actions': [
                '快速响应（黄金4小时内）',
                '表达歉意和关注',
                '承认问题存在',
                '不找借口、不甩锅'
            ],
            'example': '我们非常重视您反馈的问题，对此给您带来的不便深表歉意。'
        },
        {
            'step': 'C - Confirm（确认）',
            'description': '确认事实真相，给出调查进展和时间表',
            'key_actions': [
                '成立专项调查小组',
                '公布调查进展',
                '给出明确时间表',
                '透明公开信息'
            ],
            'example': '我们已成立专项调查组，将在48小时内公布调查结果。'
        },
        {
            'step': 'T - Take action（行动）',
            'description': '采取切实行动解决问题，整改并防止再次发生',
            'key_actions': [
                '提供具体解决方案',
                '赔偿/补偿受影响者',
                '整改流程和制度',
                '建立长效机制',
                '公布整改结果'
            ],
            'example': '我们将为受影响的消费者提供全额退款，并全面升级质量管控体系。'
        }
    ],
    'golden_rules': [
        '黄金4小时：危机发生后4小时内是回应最佳时机',
        '态度决定一切：真诚的态度比完美的解释更重要',
        '不要说谎：一个谎言需要一百个谎言来圆',
        '不要沉默：沉默会被解读为默认',
        '不要对抗：与消费者对抗只会激化矛盾',
        '持续更新：不要只发一次声明，要持续公布进展'
    ]
}


# ============================================
# 4. 5个专报触发条件
# ============================================

SPECIAL_REPORT_TRIGGERS = [
    {
        'id': 1,
        'name': '负面舆情突增',
        'condition': '单日负面笔记数量超过过去7天平均值的200%',
        'threshold': '负面数 > 7日均值 × 2',
        'severity': 'high',
        'action': '立即生成舆情专报，推送至管理层',
        'example': '过去7天日均负面5条，今日突增至15条以上'
    },
    {
        'id': 2,
        'name': '高影响力账号负面',
        'condition': '粉丝量超过10万的账号发布负面内容',
        'threshold': '粉丝数 > 100,000 且 情绪=负面',
        'severity': 'high',
        'action': '立即生成专报，评估传播风险，制定应对方案',
        'example': '百万粉丝博主发布太古汇负面体验视频'
    },
    {
        'id': 3,
        'name': '特定品牌/业态集中负面',
        'condition': '单一品牌或业态24小时内出现3条以上负面',
        'threshold': '同品牌/业态负面数 >= 3 / 24h',
        'severity': 'medium',
        'action': '生成品牌/业态专项舆情报告，通知相关负责人',
        'example': '某餐饮品牌一天内出现5条服务投诉'
    },
    {
        'id': 4,
        'name': '安全/健康相关负面',
        'condition': '涉及食品安全、人身安全、健康风险的负面内容',
        'threshold': '关键词匹配：安全/健康/食品/受伤/中毒等',
        'severity': 'critical',
        'action': '立即生成最高级别专报，启动应急预案',
        'example': '顾客在商场内摔倒受伤，或餐饮店食品卫生问题'
    },
    {
        'id': 5,
        'name': '媒体/自媒体集中报道',
        'condition': '24小时内有3家以上媒体或自媒体报道相关负面',
        'threshold': '不同媒体报道数 >= 3 / 24h',
        'severity': 'high',
        'action': '生成媒体舆情专报，评估舆论走向，准备媒体回应',
        'example': '多家本地自媒体同时报道太古汇停车收费问题'
    }
]


# ============================================
# 5. 案例匹配算法
# ============================================

def match_cases(note_title, note_content='', note_keywords=None):
    """匹配相关公关案例"""
    note_text = (note_title + ' ' + note_content).lower()
    matched = []

    for case in PR_CASES:
        score = 0
        # 关键词匹配
        for kw in case.get('keywords', []):
            if kw.lower() in note_text:
                score += 10
        # 行业匹配
        if case.get('industry') and case['industry'].lower() in note_text:
            score += 5
        # 类型匹配
        if case.get('type') and case['type'].lower() in note_text:
            score += 5

        if score > 0:
            matched.append({
                'case': case,
                'match_score': score,
                'match_reason': f'匹配关键词: {", ".join([kw for kw in case.get("keywords", []) if kw.lower() in note_text])}'
            })

    # 按匹配度排序
    matched.sort(key=lambda x: x['match_score'], reverse=True)
    return matched[:5]  # 返回最相关的5个


def recommend_template(note_title, note_content=''):
    """推荐公关话术模板"""
    note_text = (note_title + ' ' + note_content).lower()

    # 简单的场景匹配
    scenario_keywords = {
        'product_quality': ['质量', '假货', '变质', '过期', '缺陷', '不合格', '卫生', '老鼠', '蟑螂'],
        'service_attitude': ['服务', '态度', '员工', '骂', '吼', '投诉', '歧视', '冷眼'],
        'safety_incident': ['安全', '事故', '受伤', '摔倒', '火灾', '电梯', '伤人', '危险'],
        'rumor_clarification': ['谣言', '不实', '传闻', '网传', '假的', '造谣'],
        'price_controversy': ['价格', '贵', '涨价', '收费', '坑', '宰客', '性价比'],
        'employee_issue': ['员工', '言论', '不当', '辱华', '歧视', '价值观']
    }

    scores = {}
    for scenario, keywords in scenario_keywords.items():
        score = sum(1 for kw in keywords if kw in note_text)
        if score > 0:
            scores[scenario] = score

    if not scores:
        return None

    best_scenario = max(scores, key=scores.get)
    template = PR_TEMPLATES.get(best_scenario)
    if template:
        return {
            'scenario': best_scenario,
            'template_name': template['name'],
            'template': template['template'],
            'key_points': template['key_points'],
            'match_score': scores[best_scenario]
        }
    return None


# ============================================
# 6. API接口
# ============================================

# 注意：/api/pr/cases 已在 app.py 中实现，此处不再重复注册

@pr_case_bp.route('/api/pr/cases/<int:case_id>')
def get_pr_case_detail(case_id):
    """获取单个案例详情"""
    try:
        case = next((c for c in PR_CASES if c['id'] == case_id), None)
        if not case:
            return jsonify({'ok': False, 'error': '案例不存在'}), 404
        return jsonify({'ok': True, 'case': case})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# 注意：/api/pr/templates 已在 app.py 中实现，此处不再重复注册

@pr_case_bp.route('/api/pr/act-principle')
def get_act_principle():
    """获取ACT法则"""
    try:
        return jsonify({'ok': True, 'act_principle': ACT_PRINCIPLE})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@pr_case_bp.route('/api/pr/triggers')
def get_special_report_triggers():
    """获取专报触发条件"""
    try:
        return jsonify({'ok': True, 'triggers': SPECIAL_REPORT_TRIGGERS})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# 注意：/api/pr/match 已在 app.py 中实现，此处不再重复注册

print("[PRCase] 公关案例整合模块已加载", flush=True)
