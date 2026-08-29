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

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'monitor.db')

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

class PublicOpinionCaseDB:
    """全网舆情案例数据库"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
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
            conn = sqlite3.connect(self.db_path)
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
        """导入所有案例"""
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
        
        return count
    
    def get_cases(self, case_type=None, risk_level=None, category=None, limit=100):
        """获取案例列表"""
        try:
            conn = sqlite3.connect(self.db_path)
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
            conn = sqlite3.connect(self.db_path)
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
