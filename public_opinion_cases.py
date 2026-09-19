"""
全网舆情案例数据库 - 广州太古汇舆情监测系统 v5.8.0

功能：
1. 广州太古汇舆情事件案例库
2. 其他商业地产舆情事件案例库
3. 品牌业态舆情事件案例库
4. 案例分类、风险等级、应对策略
5. 接入系统数据库，用于学习和参考
"""
import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from lumenis.shared.database import DatabaseRepository, main_db_path

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = main_db_path()

# ========== 广州太古汇舆情事件案例库 ==========
TAIKOO_HUI_CASES = [
    {
        'case_id': 'TKH-2025-001',
        'title': '翠园餐厅收取11元白开水费事件',
        'summary': '2025年6月30日，两名顾客在广州太古汇翠园餐厅点了一壶58元陈皮水后，账单还收取11元白开水费及10%服务费，总消费563.9元。消费者质疑重复收费，事件登上热搜。',
        'date': '2025-06-30',
        'platform': '微博/小红书/新闻媒体',
        'category': '餐饮服务',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': '白开水费,翠园,太古汇,重复收费,强制消费',
        'impact': '登上微博热搜，引发广泛讨论，影响太古汇餐饮服务形象',
        'response': '餐厅负责人称所有收费"明码标价"，市场监管局表示明码标价可以收',
        'lessons': '餐饮收费需清晰透明，避免消费者误解；高风险事件需快速响应',
        'source_url': 'https://new.qq.com/rain/a/20250703A07E8B00',
    },
    {
        'case_id': 'TKH-2024-001',
        'title': '女厕隔间玻璃透明事件',
        'summary': '2024年10月9日，网友发帖称在广州太古汇如厕时发现厕所玻璃可透视，被保洁员催促赶紧离开。10月11日记者走访看到部分隔间玻璃是磨砂的，还有隔间暂停开放。',
        'date': '2024-10-09',
        'platform': '微博/小红书/新闻媒体',
        'category': '设施安全',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': '透明玻璃,女厕,隐私,太古汇,保洁',
        'impact': '引发隐私安全担忧，影响商场形象',
        'response': '商场工作人员称仅极个别洗手间存在问题，已在进行改造',
        'lessons': '设施安全需定期检查，隐私问题需高度重视；问题发现后需快速整改',
        'source_url': 'https://m.gmw.cn/toutiao/2024-10/11/content_1303868418.htm',
    },
    {
        'case_id': 'TKH-2025-002',
        'title': '始祖鸟商品质量问题并虚假宣传',
        'summary': '2025年8月24日消费者在广州太古汇始祖鸟门店购入Gamma SL Pant长裤，穿着不到5次两侧裤脚内衬大面积起球，纤维面破损。官方售后回复是使用过程中不可避免的摩擦。',
        'date': '2025-08-24',
        'platform': '黑猫投诉',
        'category': '品牌质量',
        'risk_level': 'medium',
        'sentiment': 'negative',
        'keywords': '始祖鸟,质量问题,起球,虚假宣传,太古汇',
        'impact': '高端品牌质量问题引发消费者不满',
        'response': '官方售后称是使用过程中不可避免的摩擦',
        'lessons': '高端品牌质量管控需加强，售后服务态度影响品牌形象',
        'source_url': 'https://ln.tousu.sina.cn/complaint/view/17391287567/',
    },
    {
        'case_id': 'TKH-2023-001',
        'title': 'LV实体店服务态度恶劣事件',
        'summary': '2023年7月，网友在广州太古汇LV实体店花费9700元购买男士鞋子，因未及时试穿要求调换码数，店内员工和店长服务态度恶劣，拒绝处理并让保安驱逐顾客，还用广州本地话沟通疑似歧视外地人。',
        'date': '2023-07-25',
        'platform': '抖音/微博',
        'category': '服务态度',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': 'LV,服务态度,调换码数,保安驱逐,歧视外地人,太古汇',
        'impact': '奢侈品服务态度问题引发广泛关注，影响品牌和商场形象',
        'response': '未公开回应',
        'lessons': '奢侈品服务培训需加强，退换货政策需清晰，歧视问题零容忍',
        'source_url': 'https://www.iesdouyin.com/share/video/7259566988488396066',
    },
    {
        'case_id': 'TKH-2026-001',
        'title': '半藏寿司餐厅顾客被性骚扰事件',
        'summary': '2026年3月，网友发文称在广州太古汇Sushi Hanzo Pro鮨·半藏寿司餐厅用餐时遭到一名男子当众性骚扰，事件引发广泛热议。品牌发布致歉声明称已协助报警并配合调查。',
        'date': '2026-03-17',
        'platform': '微博/新闻媒体',
        'category': '安全事件',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': '半藏寿司,性骚扰,太古汇,安全,报警',
        'impact': '商场安全问题引发关注，影响消费者安全感',
        'response': '品牌发布致歉声明，已协助报警并配合调查',
        'lessons': '商场安全保障需加强，突发事件需快速响应并配合警方',
        'source_url': 'http://m.toutiao.com/group/7618155655752466996/',
    },
    {
        'case_id': 'TKH-2025-003',
        'title': '华为售后拆机导致漏液事件',
        'summary': '消费者2024年4月购入华为Pura X折叠屏手机，6月发现内屏转轴处胶条脱落，送至广州天河路太古汇6楼华为官方授权售后网点维修，门店告知需拆机处理，拆机后导致漏液，不备份收回手机并拒不免费维修。',
        'date': '2025-07-03',
        'platform': '消费保',
        'category': '售后服务',
        'risk_level': 'medium',
        'sentiment': 'negative',
        'keywords': '华为,售后,拆机,漏液,太古汇,维修',
        'impact': '品牌售后服务问题引发消费者投诉',
        'response': '未公开回应',
        'lessons': '售后服务流程需规范，拆机风险需提前告知，数据备份需重视',
        'source_url': 'https://www.xfb315.com/tousu/99092013',
    },
    {
        'case_id': 'TKH-2025-004',
        'title': '童程童美广州所有门店暂停营业事件',
        'summary': '2025年1月14日，知名少儿编程机构童程童美"爆雷"，广州所有门店都已贴出放假通知暂停营业，多位家长反映跑路消息属实，涉及大量预付费课程费用。',
        'date': '2025-01-14',
        'platform': '新闻媒体/微博',
        'category': '商户经营',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': '童程童美,爆雷,暂停营业,预付费,太古汇',
        'impact': '商户爆雷引发消费者维权，影响商场信誉',
        'response': '未公开回应',
        'lessons': '商户资质审核需加强，预付费风险需提前预警，商户退出机制需完善',
        'source_url': 'https://m.163.com/dy/article/JLSH0CNO05569FE4.html',
    },
    {
        'case_id': 'TKH-2026-002',
        'title': '客服服务态度投诉',
        'summary': '小红书用户反映太古汇客服体验"简直跌破眼镜"，"整个对话感觉不像在解决问题，更像在证明是我的错"，客服态度冷冰冰。也有用户吐槽停车系统难用，服务人员不专业，交费整整花了十分钟才搞好。',
        'date': '2026-07-14',
        'platform': '小红书',
        'category': '服务态度',
        'risk_level': 'medium',
        'sentiment': 'negative',
        'keywords': '客服,服务态度,冷冰冰,停车系统,太古汇',
        'impact': '服务态度问题影响商场形象和消费者体验',
        'response': '未公开回应',
        'lessons': '客服培训需加强，解决问题导向而非推卸责任；停车系统需优化',
        'source_url': 'https://m.focus.cn/wuzhou/zixun/a188cfb46f594ed4.html',
    },
    {
        'case_id': 'TKH-2026-003',
        'title': '香奈儿店服务差劲投诉',
        'summary': '猫途鹰用户评价太古汇香奈儿专卖店购物体验极其糟糕，销售人员态度粗鲁、冷漠，让消费者感觉被评判，仿佛已经认定买不起任何东西，态度显得不耐烦且漠不关心，完全没有服务意识或热情。',
        'date': '2026-04-15',
        'platform': '猫途鹰Tripadvisor',
        'category': '服务态度',
        'risk_level': 'medium',
        'sentiment': 'negative',
        'keywords': '香奈儿,服务态度,粗鲁,冷漠,太古汇',
        'impact': '奢侈品服务态度问题影响品牌和商场形象',
        'response': '未公开回应',
        'lessons': '奢侈品服务培训需加强，不能以貌取人，服务意识需提升',
        'source_url': 'https://api-global.tripadvisor.cn/Attraction_Review-g298555-d3247950-Reviews-Taikoo_Hui-Guangzhou_Guangdong.html',
    },
]

# ========== 其他商业地产舆情事件案例库 ==========
OTHER_MALL_CASES = [
    {
        'case_id': 'OTHER-2026-001',
        'title': '西安万象城多只小鸟撞玻璃墙身亡事件',
        'summary': '2026年2月8日，西安万象城商场因玻璃幕墙导致多只小鸟撞击死亡事件引发社会关注。市民反映在商场外发现多只死亡小鸟，疑似撞击玻璃幕墙所致。',
        'date': '2026-02-08',
        'platform': '新闻媒体/微博',
        'mall_name': '西安万象城',
        'category': '环保安全',
        'risk_level': 'medium',
        'sentiment': 'negative',
        'keywords': '西安万象城,小鸟,撞玻璃,环保,玻璃幕墙',
        'impact': '环保问题引发关注，影响商场形象',
        'response': '未公开回应',
        'lessons': '玻璃幕墙需加装防撞标识，环保意识需加强',
        'source_url': 'https://m.eefung.com/yanjiu/20260211103212192',
    },
    {
        'case_id': 'OTHER-2026-002',
        'title': '温州滨江万象城跨年夜扎针事件谣言',
        'summary': '2026年1月1日，部分网络社交平台传播所谓"跨年夜温州滨江万象城发生扎针事件"的信息。商场发布严正声明，经彻底调阅12月31日全场监控记录及多方核实，当晚未发生任何与此谣言相符的事件，信息纯属捏造。',
        'date': '2026-01-01',
        'platform': '微博/新闻媒体',
        'mall_name': '温州滨江万象城',
        'category': '谣言事件',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': '温州万象城,扎针,谣言,跨年夜,辟谣',
        'impact': '谣言引发公众恐慌，影响商场形象和客流',
        'response': '商场发布严正声明辟谣，配合公安机关调查',
        'lessons': '谣言需快速辟谣，监控留存需完善，舆情监测需实时',
        'source_url': 'https://xinwen.bjd.com.cn/content/s69561419e4b0cd719e9b7f08.html',
    },
    {
        'case_id': 'OTHER-2026-003',
        'title': '太原万象城地面污渍致衣物受损事件',
        'summary': '2026年5月4日，消费者在太原万象城内正常行走时，因地面有洒落的奶茶长时间未清理且无警示标识，不慎踩踏导致个人衣物严重受损，LESS品牌半身裙（购入价1525元）受损。客诉部门擅自洗护加重损坏，拒绝全额赔偿。',
        'date': '2026-05-04',
        'platform': '黑猫投诉',
        'mall_name': '太原万象城',
        'category': '设施安全',
        'risk_level': 'medium',
        'sentiment': 'negative',
        'keywords': '太原万象城,地面污渍,衣物受损,客诉,赔偿',
        'impact': '商场设施维护问题引发消费者投诉和赔偿纠纷',
        'response': '客诉部门擅自洗护加重损坏，拒绝全额赔偿',
        'lessons': '地面清洁需及时，警示标识需设置，客诉处理需专业规范',
        'source_url': 'https://tousu.sina.cn/complaint/view/17397730548/',
    },
    {
        'case_id': 'OTHER-2026-004',
        'title': '南宁万象城玻璃挤爆伤5人事件',
        'summary': '2026年5月31日，南宁万象城张凌赫活动现场发生玻璃挤爆事件，造成5人受伤。现场人群拥挤导致玻璃碎裂，引发安全事故和广泛关注。',
        'date': '2026-05-31',
        'platform': '抖音/微博/新闻媒体',
        'mall_name': '南宁万象城',
        'category': '安全事件',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': '南宁万象城,玻璃挤爆,受伤,张凌赫,活动安全',
        'impact': '活动安全事故引发关注，影响商场形象和消费者安全感',
        'response': '未公开回应',
        'lessons': '大型活动安保需加强，人流管控需预案，安全设施需定期检查',
        'source_url': 'https://www.iesdouyin.com/share/video/7646385752313498934',
    },
    {
        'case_id': 'OTHER-2026-005',
        'title': '济南恒隆1个月连关3家店事件',
        'summary': '2026年8月，济南恒隆广场1个月内连关3家店，包括古洋食坊Old Melodie（山东首店）、安金烤肉等品牌。门店非正常闭店引发消费者对储值卡安全的担忧。',
        'date': '2026-08-22',
        'platform': '今日头条/新闻媒体',
        'mall_name': '济南恒隆广场',
        'category': '商户经营',
        'risk_level': 'medium',
        'sentiment': 'negative',
        'keywords': '济南恒隆,闭店,首店,储值卡,商户退出',
        'impact': '商户集中闭店影响商场形象和消费者信心',
        'response': '未公开回应',
        'lessons': '商户经营状况需监测，预付费风险需预警，商户退出需有序管理',
        'source_url': 'http://m.toutiao.com/group/7676834163965641255/',
    },
    {
        'case_id': 'OTHER-2025-001',
        'title': '成都远洋太古里积分难兑事件',
        'summary': '消费者2025年在成都太古里消费50多万，平时购物后销售提醒弄商场积分，但积分难兑心仪购物卡，引发消费者投诉。',
        'date': '2025-12-30',
        'platform': '黑猫投诉',
        'mall_name': '成都远洋太古里',
        'category': '会员服务',
        'risk_level': 'low',
        'sentiment': 'negative',
        'keywords': '成都太古里,积分,兑换,购物卡,会员',
        'impact': '会员积分兑换问题影响消费者体验和会员忠诚度',
        'response': '未公开回应',
        'lessons': '积分规则需清晰透明，兑换流程需简化，会员服务需优化',
        'source_url': 'https://tousu.sina.cn/company/view/?couid=3513260533',
    },
    {
        'case_id': 'OTHER-2026-006',
        'title': '南通万象城8年老店非正常闭店事件',
        'summary': '2026年8月，南通万象城虹料理非正常闭店，相关平台显示已停业。公告显示8月31日房租到期，却早早张贴"设备调试中"通知。爆料网友认为万象城没有尽到监管责任，涉及预付费消费者权益。',
        'date': '2026-08-05',
        'platform': '网易/新闻媒体',
        'mall_name': '南通万象城',
        'category': '商户经营',
        'risk_level': 'medium',
        'sentiment': 'negative',
        'keywords': '南通万象城,闭店,虹料理,预付费,监管责任',
        'impact': '商户非正常闭店引发消费者维权，质疑商场监管责任',
        'response': '未公开回应',
        'lessons': '商户经营状况需监测，闭店信息需透明，预付费风险需预警',
        'source_url': 'https://www.163.com/dy/article/L3IEUHSQ0556ARTX.html',
    },
]

# ========== 品牌业态舆情事件案例库 ==========
BRAND_CASES = [
    {
        'case_id': 'BRAND-2026-001',
        'title': 'LV GUCCI撤店潮事件',
        'summary': '2026年，高端商场出现LV GUCCI等奢侈品牌撤店潮，高端商场失宠。北京三里屯太古里一年内迎来6家奢侈品新店，但其他二三线城市高端商场面临品牌撤店和招商困难。',
        'date': '2026-08-19',
        'platform': '36氪/新闻媒体',
        'brand_name': 'LV/GUCCI等奢侈品',
        'category': '品牌经营',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': 'LV,GUCCI,撤店,高端商场,奢侈品',
        'impact': '奢侈品牌撤店影响高端商场定位和招商',
        'response': '未公开回应',
        'lessons': '品牌经营状况需监测，高端商场需多元化发展，招商策略需调整',
        'source_url': 'https://eu.36kr.com/zh/p/3945848730320256',
    },
    {
        'case_id': 'BRAND-2026-002',
        'title': '重奢降温潮事件',
        'summary': '2026年，一线顶流商场集体遇冷，高端商业地产迎来大洗牌。多个头部新项目集体降温，老牌顶奢商场也迎来变数，奢侈品牌纷纷放缓入驻节奏、推迟落地计划。',
        'date': '2026-05-21',
        'platform': '今日头条/新闻媒体',
        'brand_name': '奢侈品行业',
        'category': '行业趋势',
        'risk_level': 'high',
        'sentiment': 'negative',
        'keywords': '重奢,降温,高端商场,商业地产,洗牌',
        'impact': '奢侈品行业降温影响高端商场经营和招商',
        'response': '未公开回应',
        'lessons': '行业趋势需关注，商场定位需灵活调整，业态需多元化',
        'source_url': 'http://m.toutiao.com/group/7641978227733168680/',
    },
]



# ========== P1-D: 外部标杆舆情案例库（C-01~C-15） ==========
# 来源：audit/公关话术模版-舆情信息.docx + 公开可查事实
# 每个案例含五要素：事件→传播→回应→效果→对太古汇启示
# severity: 🔴高风险 / 🟡中风险 / 🟢低风险
# evidence_level: high(多源交叉验证) / medium(单源+公开报道) / low(网传待核)

EXTERNAL_BENCHMARK_CASES = [
    {
        "case_id": "C-01",
        "title": "深圳K11\"穷逛买不起\"服务歧视事件",
        "category": "服务态度",
        "scenario": "service_discrimination",
        "severity": "🔴",
        "risk_level": "high",
        "source": "docx_extract+public_record",
        "evidence_level": "high",
        "date": "2026-06",
        "brand": "深圳K11 ECOAST",
        "event": {
            "time": "2026年6月",
            "location": "深圳K11 ECOAST",
            "brand": "K11",
            "description": "顾客因想坐店内造型椅被请走，店员嘲讽\"穷逛、买不起\"、\"商场只服务高端用户\"，冲突视频被拍下疯传。"
        },
        "spread": {
            "platform": "小红书/抖音/微博",
            "volume": "全网热搜级传播",
            "key_nodes": "店内冲突视频→小红书/抖音扩散→本地号跟进→全网热搜→商场+品牌双重压力"
        },
        "response": {
            "time": "事件发酵后次日",
            "content": "K11 ECOAST官方致歉，强调\"每一位消费者都应获得平等尊重的体验，不存在消费高低之分\"；品牌方开除涉事员工，承诺服务培训。",
            "channel": "官方微博/小红书声明"
        },
        "effect": {
            "sentiment_trend": "商场态度获认可，品牌方动作果断，负面约2周回落",
            "recovery_period": "约2周",
            "business_impact": "\"高端商场歧视\"标签短期残留，品牌形象受损"
        },
        "taikoo_insight": "①高端定位≠歧视普通顾客，服务平等是底线；②商场+品牌联合发声，商场不缺位也不替品牌背全锅；③涉事员工处理要快，但避免\"只开除不整改\"被批作秀。"
    },
    {
        "case_id": "C-02",
        "title": "合肥万象城香奈儿柜姐打人肢体冲突事件",
        "category": "服务态度",
        "scenario": "service_physical_conflict",
        "severity": "🔴",
        "risk_level": "high",
        "source": "docx_extract+public_record",
        "evidence_level": "high",
        "date": "2025-07",
        "brand": "合肥万象城/香奈儿",
        "event": {
            "time": "2025年7月",
            "location": "合肥万象城香奈儿专柜",
            "brand": "香奈儿",
            "description": "母亲带孩子逛香奈儿，因拍摄商品与柜姐冲突，演变为三对一肢体冲突，拉卷帘门继续殴打，女儿在旁哭泣。"
        },
        "spread": {
            "platform": "抖音/微博/新闻媒体",
            "volume": "全网愤怒级传播",
            "key_nodes": "现场视频→全网愤怒→\"奢侈品柜姐优越感\"话题→媒体深度报道→品牌形象长期受损"
        },
        "response": {
            "time": "事件发酵后（偏晚）",
            "content": "品牌+商场致歉，涉事柜员停职；但回应偏晚且偏官方，未能平息\"奢侈品维权难\"的深层情绪。",
            "channel": "品牌官方声明+商场声明"
        },
        "effect": {
            "sentiment_trend": "事件成为\"奢侈品服务傲慢\"标志性案例",
            "recovery_period": "≥1-3月",
            "business_impact": "品牌及商场形象恢复周期长，奢侈品维权难话题持续发酵"
        },
        "taikoo_insight": "①奢侈品专柜是舆情高风险区，需建立商场侧现场干预机制（不能等品牌方）；②涉及肢体冲突/未成年人在场，情绪敏感度翻倍，必须最高优先级；③回应不能只说\"个人行为\"，要体现商场管理责任。"
    },
    {
        "case_id": "C-03",
        "title": "郑州正弘城FILA\"嫌贵\"备注隐性歧视事件",
        "category": "服务态度",
        "scenario": "service_implicit_discrimination",
        "severity": "🟡",
        "risk_level": "medium",
        "source": "public_record",
        "evidence_level": "medium",
        "date": "2025-11",
        "brand": "郑州正弘城/FILA",
        "event": {
            "time": "2025年11月",
            "location": "郑州正弘城FILA门店",
            "brand": "FILA",
            "description": "顾客发现购物小票或系统备注中被标注\"嫌贵\"等带有评判性的标签，感觉被店员隐性歧视和标签化。"
        },
        "spread": {
            "platform": "小红书/微博",
            "volume": "中等传播",
            "key_nodes": "顾客发帖曝光→评论区共鸣→\"被店员标签化\"话题→品牌回应"
        },
        "response": {
            "time": "曝光后",
            "content": "品牌方致歉，称备注为内部沟通用语不当，已对涉事员工进行培训，承诺优化内部沟通规范。",
            "channel": "品牌客服/官方回应"
        },
        "effect": {
            "sentiment_trend": "负面可控，约1周内回落",
            "recovery_period": "约1周",
            "business_impact": "品牌服务形象短期受损，内部管理规范受质疑"
        },
        "taikoo_insight": "①内部系统备注/标签是隐性歧视高发区，需规范员工内部用语；②顾客对\"被评判\"高度敏感，即使无恶意也会引发不满；③商场应要求商户建立内部沟通用语审核机制。"
    },
    {
        "case_id": "C-04",
        "title": "南昌万象城阿迪达斯言语嘲讽事件",
        "category": "服务态度",
        "scenario": "service_verbal_mockery",
        "severity": "🟡",
        "risk_level": "medium",
        "source": "public_record",
        "evidence_level": "medium",
        "date": "2025-10",
        "brand": "南昌万象城/阿迪达斯",
        "event": {
            "time": "2025年10月",
            "location": "南昌万象城阿迪达斯门店",
            "brand": "阿迪达斯",
            "description": "顾客在店内选购时，店员说出\"等一千块过年\"等带有嘲讽意味的言语，暗示顾客买不起，引发顾客不满。"
        },
        "spread": {
            "platform": "小红书/抖音",
            "volume": "中等传播",
            "key_nodes": "顾客发帖→评论区共鸣→\"店员嘲讽顾客\"话题→品牌回应"
        },
        "response": {
            "time": "曝光后",
            "content": "品牌方致歉，涉事员工停职培训，承诺加强服务意识教育。",
            "channel": "品牌官方回应"
        },
        "effect": {
            "sentiment_trend": "负面约1-2周回落",
            "recovery_period": "约1-2周",
            "business_impact": "品牌服务形象短期受损"
        },
        "taikoo_insight": "①言语嘲讽是服务歧视的常见形式，即使未升级为肢体冲突也极易传播；②运动品牌客群年轻化，对\"被嘲讽\"容忍度极低；③商场应将言语服务纳入商户考核。"
    },
    {
        "case_id": "C-05",
        "title": "三亚大悦城\"红包雨\"拥挤摔倒活动安全事件",
        "category": "活动安全",
        "scenario": "event_safety_crowd",
        "severity": "🔴",
        "risk_level": "high",
        "source": "docx_extract+public_record",
        "evidence_level": "high",
        "date": "2025-10",
        "brand": "三亚大悦城",
        "event": {
            "time": "2025年10月国庆期间",
            "location": "三亚大悦城",
            "brand": "大悦城",
            "description": "国庆期间举办\"天降红包雨\"活动，参与人数远超预期，局部拥挤，顾客被推倒受伤。"
        },
        "spread": {
            "platform": "抖音/微博/新闻媒体",
            "volume": "高传播",
            "key_nodes": "现场视频→安全质疑→\"商场活动无预案\"话题→媒体报道→国庆节点放大效应"
        },
        "response": {
            "time": "次日晚",
            "content": "发布情况通报，承认\"预判不足\"，致歉并说明受伤顾客跟进，承诺整改人流管控。",
            "channel": "官方情况通报"
        },
        "effect": {
            "sentiment_trend": "回应及时且态度诚恳，短期负面可控",
            "recovery_period": "约2周",
            "business_impact": "活动品牌和商场运营能力受质疑"
        },
        "taikoo_insight": "①大型活动（尤其节假日）必须做人流预判和应急预案，太古汇IP活动（如弗里达展）热度高更需警惕；②现场秩序问题是太古汇高频风险（已有弗里达展排队负面），需在活动策划阶段就嵌入舆情预案；③\"预判不足\"比\"意外\"更能获得理解，坦诚比辩解有效。"
    },
    {
        "case_id": "C-06",
        "title": "巴奴火锅北京悠唐店排队至凌晨活动运营事件",
        "category": "活动运营",
        "scenario": "event_operation_queue",
        "severity": "🟡",
        "risk_level": "medium",
        "source": "public_record",
        "evidence_level": "medium",
        "date": "2026-05",
        "brand": "巴奴火锅/北京悠唐",
        "event": {
            "time": "2026年5月",
            "location": "北京悠唐购物中心巴奴火锅",
            "brand": "巴奴火锅",
            "description": "巴奴火锅新店开业或促销活动引发大量顾客排队，排队时间长达数小时甚至至凌晨，顾客体验下降，部分顾客抱怨排队管理混乱。"
        },
        "spread": {
            "platform": "小红书/微博",
            "volume": "中等传播",
            "key_nodes": "顾客发帖抱怨排队→\"网红店排队\"话题→讨论商场客流管理"
        },
        "response": {
            "time": "发酵后",
            "content": "品牌方致歉，增加排队管理措施，优化叫号系统，承诺改善顾客排队体验。",
            "channel": "品牌官方回应"
        },
        "effect": {
            "sentiment_trend": "负面可控，约1周回落",
            "recovery_period": "约1周",
            "business_impact": "品牌热度与负面并存，商场客流管理受关注"
        },
        "taikoo_insight": "①网红店排队是双刃剑，热度高但体验差易引发负面；②商场应协助商户做好排队区规划和客流疏导；③长时间排队需设置预期管理（如明确告知等待时间）。"
    },
    {
        "case_id": "C-07",
        "title": "杭州金匠寿司老鼠传送带食品安全事件",
        "category": "食品安全",
        "scenario": "food_safety_hygiene",
        "severity": "🔴",
        "risk_level": "high",
        "source": "docx_extract+public_record",
        "evidence_level": "high",
        "date": "2026-03",
        "brand": "杭州金匠寿司",
        "event": {
            "time": "2026年3月",
            "location": "杭州金匠寿司门店",
            "brand": "金匠寿司",
            "description": "顾客拍到老鼠在回转寿司传送带上奔跑，旁置待食用寿司，视频引发全网\"太恶心\"情绪爆发。"
        },
        "spread": {
            "platform": "抖音/微博/小红书/新闻媒体",
            "volume": "全网爆发级传播",
            "key_nodes": "视频→\"太恶心\"情绪爆发→食品安全话题→媒体跟进→全门店信任危机"
        },
        "response": {
            "time": "当晚+次日升级",
            "content": "①当晚致歉，废弃当日食材+全额退款+暂停营业消杀；②次日升级补偿：全额退款+十倍现金补偿（不满一千按一千）+全门店系统升级。",
            "channel": "官方声明（分两步）"
        },
        "effect": {
            "sentiment_trend": "超预期补偿和果断停业获认可，从\"恶心\"转向\"有担当\"",
            "recovery_period": "约2-3周",
            "business_impact": "短期停业损失，但品牌信任度因超预期补偿反而提升"
        },
        "taikoo_insight": "①场内餐饮商户食品安全是商场连带风险，需建立商户应急联动机制；②补偿超预期是止损利器——\"十倍补偿\"比\"道歉\"更有说服力；③分两步回应（先止损再升级补偿）比一次性说完更有节奏。"
    },
    {
        "case_id": "C-08",
        "title": "苏州复悦城洗手间海报表述不当内容争议事件",
        "category": "内容物料",
        "scenario": "content_material_controversy",
        "severity": "🟡",
        "risk_level": "medium",
        "source": "docx_extract+public_record",
        "evidence_level": "high",
        "date": "2026-01",
        "brand": "苏州复悦城",
        "event": {
            "time": "2026年1月",
            "location": "苏州复悦城男洗手间",
            "brand": "复悦城",
            "description": "男洗手间内张贴海报表述不当，被指冒犯女性，引发性别议题发酵，中国妇女报等媒体关注。"
        },
        "spread": {
            "platform": "微博/小红书/新闻媒体",
            "volume": "中等偏高传播",
            "key_nodes": "网友拍照发帖→性别议题发酵→中国妇女报等媒体关注→商场审核能力质疑"
        },
        "response": {
            "time": "当天撤除+当晚正式说明",
            "content": "①初期\"高度重视并正在处理\"；②当晚正式情况说明，承认表述不当致歉，当天已撤除海报，对设计审核张贴全流程复盘彻查。",
            "channel": "官方情况说明"
        },
        "effect": {
            "sentiment_trend": "撤除快+致歉诚恳+复盘全流程，负面约1周回落",
            "recovery_period": "约1周",
            "business_impact": "商场内容审核能力受质疑，但快速回应控制了扩散"
        },
        "taikoo_insight": "①商场所有视觉物料（含洗手间、导视、活动海报）必须经过内容审核，不能只看设计美感；②性别/地域/职业等敏感议题在小红书极易发酵，审核清单需纳入；③\"当天撤除+全流程复盘\"是标准动作。"
    },
    {
        "case_id": "C-09",
        "title": "南京鼓楼吾悦\"您踏马来了\"谐音梗内容事件",
        "category": "内容物料",
        "scenario": "content_pun_humor",
        "severity": "🟢",
        "risk_level": "low",
        "source": "public_record",
        "evidence_level": "medium",
        "date": "2026-01",
        "brand": "南京鼓楼吾悦广场",
        "event": {
            "time": "2026年1月",
            "location": "南京鼓楼吾悦广场",
            "brand": "吾悦广场",
            "description": "商场使用\"您踏马来了\"作为宣传标语（谐音\"您他妈来了\"），被部分消费者认为不雅，但也有人认为是创意幽默，引发讨论。"
        },
        "spread": {
            "platform": "小红书/微博",
            "volume": "低传播",
            "key_nodes": "网友发帖讨论→\"谐音梗边界\"话题→小范围讨论"
        },
        "response": {
            "time": "讨论后",
            "content": "商场未正式回应，标语后续自然替换或保留，事件未升级。",
            "channel": "无正式回应"
        },
        "effect": {
            "sentiment_trend": "讨论为主，未形成负面危机",
            "recovery_period": "数天",
            "business_impact": "几乎无负面影响，反而获得一定话题度"
        },
        "taikoo_insight": "①谐音梗/创意文案需把握雅俗边界，高端商场尤其需谨慎；②低风险事件可不急于回应，让话题自然消退；③但需建立内容审核预判机制，避免创意翻车。"
    },
    {
        "case_id": "C-10",
        "title": "哈尔滨魁牛火锅凑重扣押金价格规则事件",
        "category": "价格规则",
        "scenario": "price_rule_deposit",
        "severity": "🟡",
        "risk_level": "medium",
        "source": "public_record",
        "evidence_level": "medium",
        "date": "2026-04",
        "brand": "哈尔滨魁牛火锅",
        "event": {
            "time": "2026年4月",
            "location": "哈尔滨魁牛火锅门店",
            "brand": "魁牛火锅",
            "description": "顾客反映火锅店采用\"凑重\"方式计费（将食材凑到固定重量收费），并扣除押金，规则不透明引发顾客质疑被\"变相多收费\"。"
        },
        "spread": {
            "platform": "小红书/抖音/黑猫投诉",
            "volume": "中等传播",
            "key_nodes": "顾客发帖/投诉→\"火锅店收费套路\"话题→讨论价格透明度"
        },
        "response": {
            "time": "发酵后",
            "content": "品牌方致歉，重新核查收费规则，退还不合理费用，优化规则公示方式。",
            "channel": "品牌官方回应/客服处理"
        },
        "effect": {
            "sentiment_trend": "负面约1-2周回落",
            "recovery_period": "约1-2周",
            "business_impact": "品牌价格诚信受质疑，短期客流可能受影响"
        },
        "taikoo_insight": "①价格规则必须透明公示，\"凑重\"\"押金\"等非常规计费方式需明确告知；②顾客对\"被套路\"零容忍，价格争议极易引发投诉；③商场应要求商户在显眼位置公示计费规则。"
    },
    {
        "case_id": "C-11",
        "title": "狗不理王府井报警威胁差评博主反面硬刚事件",
        "category": "反面教材",
        "scenario": "negative_confrontation_police",
        "severity": "🔴",
        "risk_level": "high",
        "source": "docx_extract+public_record",
        "evidence_level": "high",
        "date": "2020-09",
        "brand": "狗不理王府井店",
        "event": {
            "time": "2020年9月",
            "location": "北京狗不理王府井店",
            "brand": "狗不理",
            "description": "博主发布探店差评视频，狗不理王府井店发布声明称\"虚假视频\"\"侵犯名誉权\"并报警，完全站在消费者对立面。"
        },
        "spread": {
            "platform": "B站/微博/新闻媒体",
            "volume": "全网史诗级传播",
            "key_nodes": "差评视频→店家报警声明→\"差评就报警\"话题→全网嘲讽→店铺最终停业"
        },
        "response": {
            "time": "差评发布后",
            "content": "报警威胁+声明指责，完全站在消费者对立面，拒绝接受任何批评。",
            "channel": "店铺声明+报警"
        },
        "effect": {
            "sentiment_trend": "史诗级翻车，从一条差评变成品牌危机",
            "recovery_period": "不可逆（店铺停业）",
            "business_impact": "店铺不久后停业，狗不理品牌形象严重受损"
        },
        "taikoo_insight": "①绝对禁止用报警/律师函威胁普通消费者差评，这是自杀式操作；②负面评价是正常商业反馈，应对而非对抗；③场内商户如出现此类行为，商场需及时介入制止，避免连带。"
    },
    {
        "case_id": "C-12",
        "title": "麦当劳员工吐口水多次改口反面甩锅事件",
        "category": "反面教材",
        "scenario": "negative_shifting_blame",
        "severity": "🔴",
        "risk_level": "high",
        "source": "public_record",
        "evidence_level": "medium",
        "date": "2026-07",
        "brand": "麦当劳",
        "event": {
            "time": "2026年7月",
            "location": "麦当劳某门店",
            "brand": "麦当劳",
            "description": "顾客拍到麦当劳员工在食物中吐口水，视频曝光后品牌方多次改口，先称\"个人行为\"，后称\"正在调查\"，回应前后矛盾，甩锅意图明显。"
        },
        "spread": {
            "platform": "抖音/微博/新闻媒体",
            "volume": "高传播",
            "key_nodes": "视频曝光→品牌首次回应→被发现改口→二次回应→\"麦当劳甩锅\"话题→信任危机"
        },
        "response": {
            "time": "曝光后（多次改口）",
            "content": "多次改口，先称个人行为，后称正在调查，未能给出一致、诚恳的回应，甩锅意图明显。",
            "channel": "品牌官方回应（多次）"
        },
        "effect": {
            "sentiment_trend": "多次改口加剧负面，信任危机持续",
            "recovery_period": "≥1月",
            "business_impact": "品牌食品安全形象严重受损，多次改口被全网嘲讽"
        },
        "taikoo_insight": "①食品安全事件回应必须一致、诚恳，多次改口等于自杀；②不能甩锅\"个人行为\"，品牌需承担管理责任；③回应前需内部统一口径，避免前后矛盾。"
    },
    {
        "case_id": "C-13",
        "title": "西贝预制菜争议贾国龙扬言起诉创始人硬刚事件",
        "category": "反面教材",
        "scenario": "negative_founder_confrontation",
        "severity": "🔴",
        "risk_level": "high",
        "source": "docx_extract+public_record",
        "evidence_level": "high",
        "date": "2025-09",
        "brand": "西贝莜面村",
        "event": {
            "time": "2025年9月",
            "location": "全网",
            "brand": "西贝",
            "description": "罗永浩吐槽西贝预制菜\"太贵太恶心\"，创始人贾国龙放话\"起诉\"，后续被曝后厨用两年期冷冻西兰花，证据反转。"
        },
        "spread": {
            "platform": "微博/抖音/新闻媒体",
            "volume": "全网围观级传播",
            "key_nodes": "大V吐槽→创始人硬刚起诉→全民围观→证据反转→西贝致歉整改"
        },
        "response": {
            "time": "先硬刚后被迫致歉",
            "content": "创始人先硬刚起诉→后续证据不利→被迫致歉整改，日营业额下滑超30%。",
            "channel": "创始人个人言论+品牌官方致歉"
        },
        "effect": {
            "sentiment_trend": "硬刚导致事件持续一周以上，从产品争议变成人品争议",
            "recovery_period": "≥1月",
            "business_impact": "日营业额下滑超30%，品牌形象严重受损"
        },
        "taikoo_insight": "①创始人/高管个人言论是企业舆情风险点，商场管理层对外发言需谨慎；②面对大V/媒体质疑，\"先听再说\"比\"先怼再道歉\"成本低100倍；③硬刚会逼出更多证据（网友扒料），让事件失控。"
    },
    {
        "case_id": "C-14",
        "title": "海底捞\"魔童尿海\"标杆超预期补偿事件",
        "category": "标杆应对",
        "scenario": "benchmark_extra_compensation",
        "severity": "🔴",
        "risk_level": "high",
        "source": "docx_extract+public_record",
        "evidence_level": "high",
        "date": "2025-02",
        "brand": "海底捞",
        "event": {
            "time": "2025年2月",
            "location": "海底捞某门店",
            "brand": "海底捞",
            "description": "顾客在火锅中发现疑似异物（被网友戏称为\"魔童尿海\"），视频传播，引发食品安全危机。"
        },
        "spread": {
            "platform": "抖音/微博/小红书/新闻媒体",
            "volume": "全网关注级传播",
            "key_nodes": "视频发酵→\"火锅加料\"话题→全网关注→品牌信任危机"
        },
        "response": {
            "time": "第一时间+48h内+持续",
            "content": "①第一时间向公安报案（寻求权威介入）；②门店卫生整改（更换餐具彻底消毒）；③48h内完成调查，CEO张勇主动道歉\"主要责任在董事会\"；④全国1300多家门店地毯式排查，退还类似事件款项，公布补偿方案。",
            "channel": "公安介入+CEO公开道歉+全国排查+补偿方案"
        },
        "effect": {
            "sentiment_trend": "高管担责+权威介入+全面排查+补偿落地，从危机中重建信任",
            "recovery_period": "约2-3周",
            "business_impact": "成为行业标杆，品牌信任度因危机应对反而提升"
        },
        "taikoo_insight": "①重大事件需要高层（甚至集团层面）出面担责，比基层道歉有力；②寻求权威第三方介入（公安/监管/检测机构）能缓冲舆论；③\"全国排查\"式动作传递系统性整改信号，比单店处理更有说服力；④CEO说\"责任在董事会\"比\"员工个人行为\"高级100倍。"
    },
    {
        "case_id": "C-15",
        "title": "顺德渔村避雨驱赶标杆快速止损事件",
        "category": "标杆应对",
        "scenario": "benchmark_quick_damage_control",
        "severity": "🟡",
        "risk_level": "medium",
        "source": "public_record",
        "evidence_level": "medium",
        "date": "2026-06",
        "brand": "顺德渔村",
        "event": {
            "time": "2026年6月",
            "location": "顺德渔村门店",
            "brand": "顺德渔村",
            "description": "暴雨天顾客在餐厅门口避雨被员工驱赶，视频曝光引发\"不近人情\"批评，品牌初期回应不当加剧负面。"
        },
        "spread": {
            "platform": "抖音/微博/小红书",
            "volume": "中等传播",
            "key_nodes": "视频曝光→\"避雨被驱赶\"话题→批评品牌不近人情→品牌快速致歉止损"
        },
        "response": {
            "time": "快速致歉（初期不当后立即纠正）",
            "content": "品牌快速致歉，承认服务意识不足，对涉事员工进行培训，承诺为避雨市民提供便利（如门口设置遮雨区、提供饮用水）。",
            "channel": "品牌官方致歉+实际行动"
        },
        "effect": {
            "sentiment_trend": "快速止损，负面约1周回落",
            "recovery_period": "约1周",
            "business_impact": "品牌形象短期受损，但快速回应和实际行动控制了扩散"
        },
        "taikoo_insight": "①服务细节（如避雨、借厕所）是品牌温度的体现，驱赶行为极易引发共情式负面；②初期回应不当后需立即纠正，越拖越被动；③用实际行动（设置遮雨区、提供便利）比单纯道歉更有说服力。"
    },
]

# ========== P1-D: 6场景公关回复话术公式 ==========
PR_RESPONSE_TEMPLATES = [
    {
        "scenario": "service_attitude",
        "scenario_name": "服务态度/歧视",
        "formula_steps": [
            "共情致歉：对顾客遭遇表示真诚歉意，不回避问题",
            "强调平等尊重：明确表态\"每位顾客都应获得平等尊重的体验\"",
            "涉事人员处理：公布对涉事员工的处理结果（停职/培训/解聘）",
            "全员培训承诺：承诺全员服务意识培训，建立长效机制"
        ],
        "taboos": [
            "不说\"个人行为与商场无关\"",
            "不辩解\"顾客也有问题\"",
            "不拖延回应"
        ],
        "example_response": "我们对这位顾客的遭遇深表歉意。每一位走进商场的顾客都应获得平等、尊重的服务体验，这是我们不可动摇的底线。目前涉事员工已停职接受调查，我们将根据调查结果严肃处理。同时，我们已启动全员服务意识专项培训，确保此类事件不再发生。感谢顾客的监督，我们将以此为鉴，持续提升服务品质。"
    },
    {
        "scenario": "event_safety",
        "scenario_name": "活动安全/秩序",
        "formula_steps": [
            "致歉：对活动中发生的安全问题表示诚挚歉意",
            "承认预判不足：坦诚承认人流预判和应急预案不足",
            "受伤顾客跟进：说明受伤顾客的医疗跟进和赔偿安排",
            "人流管控整改方案：公布具体的人流管控和安全整改措施"
        ],
        "taboos": [
            "不甩锅\"顾客自己不遵守秩序\"",
            "不隐瞒受伤情况",
            "不辩解\"这是意外\""
        ],
        "example_response": "我们对活动现场发生的拥挤事件及受伤顾客深表歉意。经核查，我们对活动参与人数预判不足，现场人流管控措施不到位，这是我们的责任。目前受伤顾客已得到妥善救治，我们将承担全部医疗费用并持续跟进。我们已立即启动整改：增加现场安保人员、设置人流缓冲区、完善应急预案，确保后续活动安全有序。再次向受伤顾客及所有受影响的顾客致歉。"
    },
    {
        "scenario": "food_safety",
        "scenario_name": "食品安全/卫生",
        "formula_steps": [
            "致歉：对食品安全问题表示最诚挚的歉意",
            "立即停业下架：涉事门店立即暂停营业，问题产品全部下架",
            "全额退款：为受影响顾客办理全额退款",
            "超预期补偿：提供超预期补偿（如十倍赔偿、代金券等）",
            "全门店排查：启动全门店食品安全系统排查和升级"
        ],
        "taboos": [
            "不先说\"外部入侵\"撇清责任",
            "不只道歉不补偿",
            "不拖延停业整改"
        ],
        "example_response": "我们对发生的食品安全问题深感痛心和歉意。涉事门店已立即暂停营业，问题食材全部废弃销毁。我们将为所有受影响顾客办理全额退款，并提供十倍现金补偿（不足一千元按一千元计）。同时，我们已启动全门店食品安全系统排查，升级卫生管理标准，邀请第三方检测机构定期检测。食品安全是我们的生命线，我们将以最严格的标准要求自己，绝不辜负顾客的信任。"
    },
    {
        "scenario": "content_material",
        "scenario_name": "内容/物料争议",
        "formula_steps": [
            "当天撤除：争议物料当天全部撤除",
            "承认审核疏漏：坦诚承认内容审核流程存在疏漏",
            "致歉：对受到冒犯的公众表示诚挚歉意",
            "全流程复盘：对设计、审核、张贴全流程进行复盘彻查",
            "完善审核机制：公布完善后的内容审核机制和敏感词清单"
        ],
        "taboos": [
            "不辩解\"只是创意/谐音梗\"",
            "不拖延撤除",
            "不指责公众\"过度解读\""
        ],
        "example_response": "我们对商场内张贴的不当海报内容深表歉意。该海报已于今天全部撤除。经核查，此事件暴露了我们在内容审核流程中的疏漏，我们对此承担全部责任。我们已对设计、审核、张贴全流程进行复盘彻查，将完善内容审核机制，增加性别、地域、职业等敏感议题的审核清单，确保所有对外物料经过严格审核。感谢公众的监督和批评。"
    },
    {
        "scenario": "price_rule",
        "scenario_name": "价格/规则争议",
        "formula_steps": [
            "致歉：对价格/规则不透明给顾客带来的困扰表示歉意",
            "重新核查：立即对收费规则进行重新核查",
            "退还不合理费用：为多收费用的顾客办理退还",
            "优化规则公示：优化价格规则的公示方式，确保透明清晰"
        ],
        "taboos": [
            "不嘲讽顾客\"穷/计较\"",
            "不拿\"最终解释权\"压人",
            "不辩解\"规则一直如此\""
        ],
        "example_response": "我们对收费规则不清晰给顾客带来的困扰深表歉意。我们已立即对相关收费规则进行重新核查，对存在不合理收费的顾客，将主动联系并退还多收费用。同时，我们将优化价格规则的公示方式，在显眼位置清晰标注所有收费项目和计费方式，确保顾客明明白白消费。感谢顾客的监督，我们将持续提升服务透明度。"
    },
    {
        "scenario": "misinformation",
        "scenario_name": "不实信息/抹黑",
        "formula_steps": [
            "感谢关注：感谢公众对品牌的关注和监督",
            "客观陈述事实：客观陈述事实真相，附凭证（监控、检测报告等）",
            "欢迎私信核实：欢迎质疑者私信沟通，提供核实渠道",
            "持续改进：承诺持续改进产品和服务，接受公众监督"
        ],
        "taboos": [
            "不报警威胁",
            "不扣帽子\"黑子/水军\"",
            "不删评",
            "不使用攻击性语言"
        ],
        "example_response": "感谢大家对我们的关注和监督。针对网络上流传的相关信息，我们在此做客观说明：[陈述事实，附监控截图/检测报告/时间线等凭证]。我们欢迎对此事有疑问的朋友私信联系我们，我们将提供完整的证据材料供核实。我们始终欢迎合理的批评和建议，将持续改进产品和服务品质。如经核实存在我方问题，我们将承担全部责任并立即整改。"
    },
]

# ========== P1-D: 案例库查询辅助函数 ==========

def get_external_cases(category=None, scenario=None, severity=None, limit=100):
    """按分类/场景/严重度查询外部标杆案例。"""
    results = EXTERNAL_BENCHMARK_CASES
    if category:
        results = [c for c in results if c.get("category") == category]
    if scenario:
        results = [c for c in results if c.get("scenario") == scenario]
    if severity:
        results = [c for c in results if c.get("severity") == severity]
    return results[:limit]


def get_external_case(case_id):
    """按 case_id 查询单个外部标杆案例详情。"""
    for c in EXTERNAL_BENCHMARK_CASES:
        if c.get("case_id") == case_id:
            return c
    return None


def get_pr_response_template(scenario=None):
    """查询公关回复话术模板。"""
    if scenario:
        for t in PR_RESPONSE_TEMPLATES:
            if t.get("scenario") == scenario:
                return t
        return None
    return PR_RESPONSE_TEMPLATES


def match_cases_by_scenario(event_scenario, event_text="", limit=3):
    """专报生成时按场景匹配同类案例，返回2-3个案例编号和处置方式。"""
    # 场景映射：risk_engine风险类型 → 案例库scenario
    scenario_map = {
        "service_discrimination": ["service_discrimination", "service_implicit_discrimination", "service_verbal_mockery", "service_physical_conflict"],
        "service_attitude": ["service_discrimination", "service_implicit_discrimination", "service_verbal_mockery"],
        "event_safety": ["event_safety_crowd", "event_operation_queue"],
        "food_safety": ["food_safety_hygiene"],
        "content_material": ["content_material_controversy", "content_pun_humor"],
        "price_rule": ["price_rule_deposit"],
        "misinformation": ["misinformation"],
        "negative_confrontation": ["negative_confrontation_police", "negative_shifting_blame", "negative_founder_confrontation"],
        "benchmark": ["benchmark_extra_compensation", "benchmark_quick_damage_control"],
    }
    target_scenarios = scenario_map.get(event_scenario, [event_scenario])
    matched = []
    for c in EXTERNAL_BENCHMARK_CASES:
        if c.get("scenario") in target_scenarios:
            matched.append({
                "case_id": c["case_id"],
                "title": c["title"],
                "severity": c["severity"],
                "response_summary": c.get("response", {}).get("content", "")[:100],
                "taikoo_insight": c.get("taikoo_insight", "")[:150],
            })
    # 如果匹配不足，补充标杆案例
    if len(matched) < 2:
        for c in EXTERNAL_BENCHMARK_CASES:
            if c.get("category") == "标杆应对" and c["case_id"] not in [m["case_id"] for m in matched]:
                matched.append({
                    "case_id": c["case_id"],
                    "title": c["title"],
                    "severity": c["severity"],
                    "response_summary": c.get("response", {}).get("content", "")[:100],
                    "taikoo_insight": c.get("taikoo_insight", "")[:150],
                })
            if len(matched) >= limit:
                break
    return matched[:limit]

class PublicOpinionCaseDB:
    """全网舆情案例数据库"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        try:
            conn = DatabaseRepository(self.db_path).connect()
            cursor = conn.cursor()
            
            # 创建舆情案例表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS public_opinion_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT UNIQUE,
                    title TEXT,
                    summary TEXT,
                    date TEXT,
                    platform TEXT,
                    mall_name TEXT,
                    brand_name TEXT,
                    category TEXT,
                    risk_level TEXT,
                    sentiment TEXT,
                    keywords TEXT,
                    impact TEXT,
                    response TEXT,
                    lessons TEXT,
                    source_url TEXT,
                    case_type TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"初始化数据库失败: {e}")
    
    def insert_case(self, case, case_type='taikoo_hui'):
        """插入单个案例"""
        try:
            conn = DatabaseRepository(self.db_path).connect()
            cursor = conn.cursor()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT OR REPLACE INTO public_opinion_cases 
                (case_id, title, summary, date, platform, mall_name, brand_name, 
                 category, risk_level, sentiment, keywords, impact, response, 
                 lessons, source_url, case_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                case.get('case_id'),
                case.get('title'),
                case.get('summary'),
                case.get('date'),
                case.get('platform'),
                case.get('mall_name', ''),
                case.get('brand_name', ''),
                case.get('category'),
                case.get('risk_level'),
                case.get('sentiment'),
                case.get('keywords'),
                case.get('impact'),
                case.get('response'),
                case.get('lessons'),
                case.get('source_url'),
                case_type,
                now,
                now
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"插入案例失败: {e}")
            return False
    
    def import_all_cases(self):
        """导入所有案例（含P1-D外部标杆案例）"""
        count = 0
        
        # 导入广州太古汇案例
        for case in TAIKOO_HUI_CASES:
            if self.insert_case(case, 'taikoo_hui'):
                count += 1
        
        # 导入其他商业地产案例
        for case in OTHER_MALL_CASES:
            if self.insert_case(case, 'other_mall'):
                count += 1
        
        # 导入品牌业态案例
        for case in BRAND_CASES:
            if self.insert_case(case, 'brand'):
                count += 1

        # P1-D: 导入外部标杆案例（C-01~C-15）
        for case in EXTERNAL_BENCHMARK_CASES:
            # 转换为insert_case兼容格式
            compatible = {
                'case_id': case.get('case_id'),
                'title': case.get('title'),
                'summary': case.get('event', {}).get('description', ''),
                'date': case.get('date', ''),
                'platform': case.get('spread', {}).get('platform', ''),
                'category': case.get('category', ''),
                'risk_level': case.get('risk_level', 'medium'),
                'sentiment': 'negative',
                'keywords': case.get('title', ''),
                'impact': case.get('effect', {}).get('business_impact', ''),
                'response': case.get('response', {}).get('content', ''),
                'lessons': case.get('taikoo_insight', ''),
                'source_url': '',
            }
            if self.insert_case(compatible, 'external_benchmark'):
                count += 1
        
        return count
    
    def get_cases(self, case_type=None, risk_level=None, category=None, limit=100):
        """获取案例列表"""
        try:
            conn = DatabaseRepository(self.db_path).connect()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM public_opinion_cases WHERE 1=1"
            params = []
            
            if case_type:
                query += " AND case_type = ?"
                params.append(case_type)
            if risk_level:
                query += " AND risk_level = ?"
                params.append(risk_level)
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " ORDER BY date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            cases = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return cases
        except Exception as e:
            print(f"获取案例失败: {e}")
            return []
    
    def get_stats(self):
        """获取案例统计"""
        try:
            conn = DatabaseRepository(self.db_path).connect()
            cursor = conn.cursor()
            
            stats = {}
            
            # 总数
            cursor.execute("SELECT COUNT(*) FROM public_opinion_cases")
            stats['total'] = cursor.fetchone()[0]
            
            # 按类型统计
            cursor.execute("SELECT case_type, COUNT(*) FROM public_opinion_cases GROUP BY case_type")
            stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 按风险等级统计
            cursor.execute("SELECT risk_level, COUNT(*) FROM public_opinion_cases GROUP BY risk_level")
            stats['by_risk'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 按类别统计
            cursor.execute("SELECT category, COUNT(*) FROM public_opinion_cases GROUP BY category")
            stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            return stats
        except Exception as e:
            print(f"获取统计失败: {e}")
            return {}


# 全局单例
_case_db = None

def get_case_db():
    """获取案例数据库单例"""
    global _case_db
    if _case_db is None:
        _case_db = PublicOpinionCaseDB()
    return _case_db


# 测试
if __name__ == '__main__':
    print("=" * 60)
    print("全网舆情案例数据库 - 广州太古汇舆情监测系统 v5.8.0")
    print("=" * 60)
    print()
    
    db = get_case_db()
    
    # 导入所有案例
    print("导入案例...")
    count = db.import_all_cases()
    print(f"✅ 成功导入 {count} 个案例")
    print()
    
    # 获取统计
    print("案例统计:")
    stats = db.get_stats()
    print(f"  总数: {stats.get('total', 0)}")
    print(f"  按类型: {stats.get('by_type', {})}")
    print(f"  按风险等级: {stats.get('by_risk', {})}")
    print(f"  按类别: {stats.get('by_category', {})}")
    print()
    
    # 获取广州太古汇案例
    print("广州太古汇案例（前5个）:")
    cases = db.get_cases(case_type='taikoo_hui', limit=5)
    for i, case in enumerate(cases, 1):
        print(f"  {i}. [{case.get('risk_level')}] {case.get('title')} ({case.get('date')})")
