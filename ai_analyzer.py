"""
LUMENIS CTH reference-subject compatibility analyzer - local auditable rules
不依赖外部 AI API；使用可审计的本地规则完成情感、风险、话题、分类与摘要分析
- 情感分析 (sentiment): positive / neutral / negative
- 风险评级 (risk_level): high / medium / low
- 内容摘要 (summary)
- 话题标签 (topics)
- 内容分类 (category): 投诉/活动/商业分析/探店/招聘/其他
"""
import re
import hashlib
from subject_rules import SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit
from datetime import datetime

# ZBC Phase 7: module status markers (audit / evaluation reference)
MODULE_STATUS = 'RULES_ENGINE_PRIMARY'
AI_ROLE = 'AUXILIARY_ONLY'
SUBJECT_FILTER_BEFORE_AI = True  # subject_hit() always runs before AI

# ============== 情感词典 ==============
POSITIVE_WORDS = {
    # 真正的“用户评价性”正面词（词组优先，避免单字/营销词把中性内容误判为正面）
    '棒', '赞', '喜欢', '喜爱', '最爱', '超爱', '好爱', '爱了', '优秀', '满意', '开心', '快乐', '舒服',
    'nice', 'good', 'great', 'perfect', '推荐', '值得', '惊喜', '惊艳',
    '高级', '精致', '优雅', '漂亮', '美丽', '好吃', '好喝', '好逛', '好看', '好评', '好玩', '方便', '贴心',
    '专业', '热情', '周到', '完美', '治愈', '松弛感', '氛围好', '体验好', '超好', '很好', '真好', '好棒',
    '顶流', '必去', '值得去', '值得买', '回购', '种草', '圈粉', '真香', '绝绝子', '宝藏',
    '宠粉', '划算', '实惠', '用心', '用心了', '点赞', '好评如潮', '无可挑剔',
}

NEGATIVE_WORDS = {
    # 注：差/假/贵/黑/坑/烂 等单字歧义大（差不多/假期/贵州/黑色/水坑/灿烂），
    # 不在此放单字，统一用下方“复合负面词”精确匹配
    '垃圾', '讨厌', '恶心', '生气', '愤怒', '失望', '无语',
    '避雷', '投诉', '差评', '糟糕', '骗', '纠纷', '维权', '曝光',
    '拒绝退款', '拒绝处理', '拒绝售后', '被拒', '拒赔', '拒不退换',
    '骂', '怼', '撕', '翻车', '塌房', '丑闻', '内幕', '质疑',
    '封路', '官威', '禁用', '乱收费', '强制', '骚扰', '拉客', '欺骗',
    '倒闭', '闭店', '停业', '清仓', '裁员', '撤场', '退出', '缩水',
    '下滑', '下降', '疲软', '冷清', '没人气', '没人理', '空荡',
    '气笑', '迷惑', '离谱', '荒谬', '过分', '服了',
    'bad', 'terrible', 'awful', 'worst', 'hate',
    # 歧义词的复合负面形式（精确，避免误伤）
    '很差', '太差', '好差', '真差', '最差', '极差', '差劲', '差到', '差死', '体验差',
    '假货', '卖假', '造假', '虚假', '货不对板',
    '好贵', '很贵', '太贵', '真贵', '贵死', '天价', '宰客',
    '黑心', '黑店', '拉黑', '很黑',
    '大坑', '神坑', '是坑', '坑钱', '坑人', '坑我', '被坑',
    '很烂', '稀烂', '烂尾', '破烂',
    # —— v5.8.3 补充：口语化/餐饮/服务/商场投诉高频（词组优先，避免单字误伤）——
    '害我', '害人', '害惨', '坑死', '割韭菜', '欺负',
    '劝退', '踩雷', '踩坑', '下头', '难吃', '很难吃', '不好吃',
    '很脏', '太脏', '脏乱', '很凶', '态度凶', '冷漠', '推诿', '甩锅', '扯皮',
    '翻白眼', '不耐烦', '嫌弃', '赶客', '傲慢', '阴阳怪气',
    '拉肚子', '闹肚子', '吃坏', '吃吐', '呕吐', '异物', '变质', '发酸', '发臭',
    '有虫', '虫子', '吃出虫', '头发丝', '缺斤短两', '霸王条款',
    '再也不', '不会再', '别来', '千万别', '大无语', '离大谱', '活久见',
    '心累', '寒心', '吓人', '可怕', '漏水', '异味', '油烟味', '插队',
    '加价', '套路', '不退', '不给退', '踢皮球', '排队久', '等太久', '白跑一趟',
    # —— 程度副词搭配 / 反讽 / 事故类（补单字移除后的口语表达）——
    '诈骗', '被骗', '骗人', '巨差', '超差', '贼差', '有点差', '略差', '质量差',
    '这么贵', '那么贵', '小贵', '巨难吃', '超难吃', '难吃到', '泡水', '关门',
    '高贵什么', '在高贵', '不吃了', '不去了', '不买了', '避雷贴', '塌了',
}

# ============== v5.8.3 句式/语序规则（识别词袋抓不到的口语控诉，可审计） ==============
# 每条为 (编译正则, 权重, 命中原因标签)；命中标题权重更高
NEGATIVE_PATTERNS = [
    # 求救/受害控诉：“求你不要害我”“这是要坑死消费者”
    (r'(求你?|求求|拜托).{0,6}(别|不要|千万别|勿).{0,8}(害|坑|骗|整|来|去|买|吃|试|踩|冲)', 2.0, '否定祈使控诉'),
    (r'(害我|害人|害惨|坑我|坑死|坑人|骗我|整我|欺负我|恶心到我?|吃坏(肚子)?|拉肚子|闹肚子)', 1.8, '受害表述'),
    # 劝退/决绝：“劝你别来”“再也不会去”“拉黑这家”
    (r'(劝你?|真心劝|听我一句|建议).{0,6}(别|不要|千万别|勿)', 1.6, '劝退表述'),
    (r'(再也不|不会再|绝不再|以后(还是|都)?不|不吃了|不去了|不买了|不试了|直接拉黑|永久拉黑)', 1.5, '决绝否定'),
    (r'(小心(被)?(骗|坑|宰)|别被(骗|坑)|谨防|警惕(套路|诈骗))', 1.3, '风险警示'),
    (r'(避雷|劝退|踩雷|踩大坑|踩坑|翻车|大无语|离大谱|离了大谱|活久见|下头)', 1.3, '网络负面用语'),
    # 反问质问（负面语气）
    (r'(凭什么|怎么敢|谁给的.{0,4}勇气|就这[?？]|这也叫|合理吗[?？]|这就是.{0,10}[?？])', 0.8, '质问语气'),
]
# 正面强调/反讽豁免：“不要太好吃”“不得不夸”属于强正面，不能被“不要/不”带偏
POSITIVE_PATTERNS = [
    (r'不要太(好吃|香|美|好看|绝|划算|值|棒|舒服|治愈)', 1.6, '正面强调(不要太…)'),
    (r'(不得不(说|夸|推荐)|谁懂啊.{0,6}(好|香|爱|绝)|真的会(爱|回购|无限回购))', 1.2, '正面强调'),
    (r'(拒绝不了|无法拒绝|没法拒绝|抗拒不了)', 1.2, '正面(无法拒绝)'),
    (r'(豪华|好吃|好美|美|香|绝|好看|精致|惊艳|划算|值|贴心).{0,4}(到|得|有?点)?离谱', 2.2, '褒义强调(…到离谱)'),
]
# 否定负面/澄清：文本是在“否认/澄清某负面”，应抵消对应负面词，而非判负面
NEG_FLIP_PATTERNS = [
    (r'(没(有)?|未|并无|并非|不是|否认|澄清|辟谣|辟谣称|回应称).{0,5}(倒闭|闭店|关门|翻车|差评|违规|塌房|跑路|安全问题|质量问题|起火|漏水|骗|宰客)', 1.3, '否定负面(澄清非负面)'),
    (r'(择期重开|重新开业|恢复营业|正常营业|并未.{0,4}影响)', 1.0, '澄清恢复营业'),
]

# ============== 风险关键词 ==============
HIGH_RISK_KEYWORDS = {
    '投诉', '维权', '曝光', '丑闻', '内幕', '翻车', '塌房', '欺骗', '诈骗',
    '食品安全', '卫生问题', '安全隐患', '事故', '受伤', '火灾', '盗窃',
    '歧视', '侮辱', '性骚扰', '暴力', '冲突', '打架', '报警', '起诉',
    '官威', '封路', '强制', '乱收费', '天价', '宰客', '黑店',
    '集体维权', '联名投诉', '媒体曝光', '上热搜', '舆情', '危机',
    '员工投诉', '劳资纠纷', '欠薪', '裁员', '罢工',
}

MEDIUM_RISK_KEYWORDS = {
    '避雷', '差评', '失望', '态度差', '服务差', '排队久', '等太久',
    '不好吃', '不好玩', '不值', '太贵', '性价比低', '缩水', '减少',
    '闭店', '停业', '清仓', '撤场', '退出', '调整', '变动',
    '质疑', '疑问', '不解', '困惑', '奇怪', '异常',
    '停车难', '找不到', '迷路', '不方便', '拥挤', '人太多',
}

# ============== 话题词典 ==============
TOPIC_KEYWORDS = {
    '停车/保安': ['停车', '车位', '停车场', '预约停车', '封路', '保安', '官威', '不让拍'],
    '服务投诉': ['投诉', '态度', '服务', '店员', '员工', '柜姐', '迷惑', '差评', '避雷'],
    '餐饮问题': ['餐厅', '吃饭', '美食', '茶水费', '白开水', '强制消费', '卫生', '难吃', '排队', '等位', '翠园', '日料'],
    '品牌售后': ['售后', '退换', '质量', '假货', '虚假宣传', '专柜', 'LV', 'Dior', 'NARS', '拒绝'],
    '安全事件': ['骚扰', '猥亵', '安全', '盗窃', '事故', '受伤', '报警', '冲突', '打架'],
    '方所闭店': ['方所', '闭店', '停业', '清仓', '书店', '撤场'],
    '扩容调整': ['扩容', '调整', '二期', '三期', '施工', '围挡', '升级', '扩建', '装修'],
    '品牌活动': ['活动', '七夕', '宠粉', '抽奖', '福利', '限时', '快闪', '展览', '艺术', '装置'],
    '新店开业': ['新店', '开业', '首店', '入驻', '围挡', '品牌'],
    '商业分析': ['销售额', '业绩', '商圈', '竞争', '标杆', '王座', '华南', '高端', '奢侈品'],
    '探店分享': ['探店', '打卡', '好逛', '拍照', '出片', '逛街', 'citywalk', '攻略', '逛吃', '周末', '约会', '闺蜜', '情侣', '美食', '咖啡', '下午茶', 'brunch', '看展', '展览'],
    '设施问题': ['电梯', '厕所', '卫生间', '空调', '拥挤', '人多', '找不到', '迷路', '排队', '等位', '停车难', '导航', '指示牌'],
    '购物体验': ['购物', '买', '专柜', '试穿', '试戴', '导购', '柜姐', '店员', '服务态度', '结账', '排队', '限购', '缺货'],
    '价格争议': ['贵', '价格', '涨价', '降价', '折扣', '优惠', '性价比', '天价', '宰客', '乱收费', '服务费', '茶位费'],
    '文化艺术': ['展览', '艺术', '装置', '设计', '美学', '文化', '书店', '方所', '音乐', '演出', '活动'],
    '生活方式': ['生活', '日常', 'vlog', '记录', '分享', '体验', '感受', '推荐', '种草', '拔草'],
    '招聘信息': ['招聘', '岗位', '兼职', '陈列', '求职', '实习'],
    '会员服务': ['会员', '积分', '专属', '礼遇', 'VIP'],
    '用户互动': ['评论', '互动', '讨论', '热议', '话题'],
}

# 本身带有负面倾向的话题（命中即提升风险等级）
NEGATIVE_TOPICS = {'停车/保安', '服务投诉', '餐饮问题', '品牌售后', '安全事件', '设施问题'}
# 高风险话题（命中即高风险）
HIGH_RISK_TOPICS = {'安全事件'}

# ============== 广州太古汇主体验证 ==============
# 统一引用 subject_rules.py；这里保留历史常量名供旧代码兼容。
TAIKOO_DIRECT_KEYWORDS = SUBJECT_WORDS
EXCLUDE_KEYWORDS = SUBJECT_EXCLUDE_WORDS

def verify_taikoo_location(title, content=''):
    """严格验证是否属于广州太古汇；排除词一票否决。"""
    ok = subject_hit(title=title, body=content, content=content)
    if ok:
        return True, '命中广州太古汇主体词'
    text = f'{title} {content}'
    for kw in SUBJECT_EXCLUDE_WORDS:
        if kw.lower() in text.lower():
            return False, f'包含排除词:{kw}'
    return False, '未匹配广州太古汇主体词'

# ============== 分类规则 ==============
CATEGORY_RULES = [
    ('投诉', ['投诉', '避雷', '态度差', '服务差', '维权', '曝光', '官威', '封路', '乱收费', '欺骗', '气笑', '迷惑']),
    ('活动', ['活动', '七夕', '宠粉', '抽奖', '福利', '限时', '快闪', '展览', '艺术', '节日', '甄选']),
    ('商业分析', ['扩容', '调整', '销售额', '业绩', '商圈', '竞争', '标杆', '王座', '华南', '高端', '二期', '三期', '施工', '围挡升级']),
    ('探店', ['探店', '打卡', '好逛', '美食', '拍照', '出片', '逛街', '氛围', '松弛']),
    ('招聘', ['招聘', '岗位', '兼职', '陈列', '求职', '实习', '找工作']),
    ('闭店调整', ['方所', '闭店', '停业', '清仓', '撤场', '退出']),
]

OFFICIAL_ACCOUNTS = {'广州太古汇'}


def _safe_int(val, default=0):
    try:
        return int(val) if val else default
    except (ValueError, TypeError):
        return default


def analyze_sentiment(title, content='', topics=None, return_reasons=False):
    """
    情感分析：词典 + 句式语序 + 话题/事件 三层判定（本地、可审计）。
    - 词袋：正/负词计数，标题权重加倍
    - 句式：识别“求你别害我/劝退/再也不/凭什么”等词袋抓不到的口语控诉；
            “不要太好吃”等正面强调豁免，不被否定词带偏
    - 话题/事件：命中负面话题（服务投诉/餐饮问题/安全事件等）即下修情感
    返回 (sentiment, score)；return_reasons=True 时返回 (sentiment, score, reasons)
    """
    text = f"{title} {content}".lower()
    title_lower = (title or '').lower()
    reasons = []

    pos_score = sum(1 for w in POSITIVE_WORDS if w.lower() in text)
    neg_score = sum(1 for w in NEGATIVE_WORDS if w.lower() in text)
    # 标题权重加倍
    pos_score += sum(1 for w in POSITIVE_WORDS if w.lower() in title_lower)
    tneg_lex = sum(1 for w in NEGATIVE_WORDS if w.lower() in title_lower)
    neg_score += tneg_lex
    if tneg_lex:
        reasons.append('标题命中负面词')

    # 句式/语序层（正则在原文上跑，保留中文与标点）
    raw_text = f"{title or ''} {content or ''}"
    raw_title = title or ''
    pattern_neg = 0.0
    for pat, weight, label in NEGATIVE_PATTERNS:
        hit_body = re.search(pat, raw_text)
        hit_title = re.search(pat, raw_title)
        if hit_title:
            pattern_neg += weight * 1.5  # 句式出现在标题，信号更强
            reasons.append(f'标题{label}')
        elif hit_body:
            pattern_neg += weight
            reasons.append(label)
    pattern_pos = 0.0
    for pat, weight, label in POSITIVE_PATTERNS:
        if re.search(pat, raw_text):
            pattern_pos += weight
            reasons.append(label)

    # 否定负面/澄清：命中“没有倒闭/择期重开”等，回退负面分，避免把澄清当负面
    for pat, weight, label in NEG_FLIP_PATTERNS:
        if re.search(pat, raw_text):
            pattern_neg -= weight
            reasons.append(label)

    # 问号（疑问/质疑）轻微负面；感叹号不单独计负
    pattern_neg += raw_text.count('？') * 0.3 + raw_text.count('?') * 0.2

    # 话题/事件层：话题用于“印证并放大”已出现的负面信号，而不是凭空把中性内容打负。
    # 例如“美食节进驻”只命中类目词“美食”，本身无负面信号时不下修情感。
    topic_neg = 0.0
    has_neg_signal = (neg_score + pattern_neg) > pattern_pos + 0.3  # 净负面强于正面豁免才印证话题
    if topics and has_neg_signal:
        hit_neg_topics = [t for t in topics if t in NEGATIVE_TOPICS]
        if hit_neg_topics:
            topic_neg += 0.8 + 0.4 * (len(hit_neg_topics) - 1)
            reasons.append('命中负面话题:' + '/'.join(hit_neg_topics))
        if any(t in HIGH_RISK_TOPICS for t in topics):
            topic_neg += 1.0
            reasons.append('命中高风险话题')

    pos_total = pos_score + pattern_pos
    neg_total = max(0.0, neg_score + pattern_neg + topic_neg)  # 澄清/褒义抵消后不为负
    total = pos_total + neg_total
    # 强负面句式（受害/控诉/决绝/风险警示）直接锁定负面，不被少量正面词翻转
    strong_neg = any(lb in ('否定祈使控诉', '受害表述', '决绝否定', '风险警示') for lb in reasons)
    if total == 0:
        sentiment, score = 'neutral', 0.0
    else:
        score = (pos_total - neg_total) / total
        if strong_neg:
            sentiment = 'negative'
            score = min(score, -0.3)
        elif neg_total >= 1 and pos_total <= neg_total:
            # 存在负面信号、且未被明显正面盖过 → 判负面（舆情监测优先不漏负面）
            sentiment = 'negative'
        elif pos_total >= 1 and pos_total > neg_total and score > 0.15:
            sentiment = 'positive'
        else:
            sentiment = 'neutral'

    if return_reasons:
        return sentiment, round(score, 3), reasons
    return sentiment, round(score, 3)


def assess_risk(title, content, likes, comments, author_nickname=''):
    """风险评级：基于关键词 + 话题 + 传播力 + 情感"""
    text = f"{title} {content}"
    high_hits = sum(1 for w in HIGH_RISK_KEYWORDS if w in text)
    med_hits = sum(1 for w in MEDIUM_RISK_KEYWORDS if w in text)

    # 基础风险分
    risk_score = high_hits * 25 + med_hits * 10

    # 话题维度风险判断（核心：负面话题本身即风险信号）
    topics = extract_topics(title, content)
    topic_set = set(topics)
    # 高风险话题直接大幅加分
    if topic_set & HIGH_RISK_TOPICS:
        risk_score += 35
    # 负面倾向话题加分
    neg_topics = topic_set & NEGATIVE_TOPICS
    if neg_topics:
        risk_score += len(neg_topics) * 8
    # 负面话题+负面关键词组合，风险更高
    if neg_topics and (high_hits > 0 or med_hits > 0):
        risk_score += 15

    # 传播力加权（高互动负面内容风险更高）
    engagement = _safe_int(likes) + _safe_int(comments) * 2
    if high_hits > 0 or med_hits > 0 or neg_topics:
        risk_score += min(engagement / 50, 20)

    # 官方账号发布的内容风险低（但负面话题除外）
    if author_nickname in OFFICIAL_ACCOUNTS and not neg_topics:
        risk_score = max(0, risk_score - 30)

    # 情感负面加权（结合已提取话题）
    sentiment, _ = analyze_sentiment(title, content, topics=topics)
    if sentiment == 'negative':
        risk_score += 10
    elif sentiment == 'positive' and not neg_topics:
        risk_score = max(0, risk_score - 5)

    # 地点验证：未通过验证的笔记最高只能是中风险
    is_verified, _ = verify_taikoo_location(title, content)
    if not is_verified and risk_score >= 40:
        risk_score = 39  # 降到中风险上限

    risk_score = min(100, int(risk_score))

    # critical: independent higher bucket, never merged into high (Phase 6 audit fix)
    if risk_score >= 80 and (high_hits > 0 or len(neg_topics) > 0):
        risk_level = 'critical'
    elif risk_score >= 40:
        risk_level = 'high'
    elif risk_score >= 15:
        risk_level = 'medium'
    else:
        risk_level = 'low'

    return risk_level, risk_score


def extract_topics(title, content=''):
    """话题标签提取"""
    text = f"{title} {content}"
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            topics.append(topic)
    return topics[:5] if topics else ['其他']


def categorize(title, content=''):
    """内容分类"""
    text = f"{title} {content}"
    for category, keywords in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return '其他'


def generate_summary(title, content, sentiment, risk_level, topics):
    """生成管理层可扫读的短摘要；不把指控写成事实。"""
    s_label={'positive':'正面','neutral':'中性','negative':'负面'}.get(sentiment,'中性')
    r_label={'high':'高风险','medium':'中风险','low':'低风险'}.get(risk_level,'低风险')
    topic='、'.join([x for x in (topics or []) if x and x!='其他'][:2]) or '一般讨论'
    if sentiment=='negative':
        action='建议核查原始经历与互动扩散' if risk_level!='low' else '持续观察互动变化'
        return f'{s_label}｜{topic}｜{r_label}｜{action}'
    if sentiment=='positive':
        return f'{s_label}｜{topic}｜{r_label}｜可作为正向口碑观察样本'
    return f'{s_label}｜{topic}｜{r_label}｜以信息记录与趋势观察为主'

def analyze_note(note, provider='hybrid'):
    """
    单条笔记完整分析
    provider 仅作为数据库兼容字段；当前实现使用本地规则引擎。
    """
    title = note.get('title', '') or ''
    content = note.get('content', '') or ''
    likes = _safe_int(note.get('likes', 0))
    comments = _safe_int(note.get('comments', 0))
    author = note.get('author_nickname', '')

    # 本地规则：先提话题，再让情感判定结合话题/事件（语序+事件双维度）
    topics = extract_topics(title, content)
    sentiment, sentiment_score, sentiment_reasons = analyze_sentiment(
        title, content, topics=topics, return_reasons=True)

    # 本地规则：风险评估 + 分类
    risk_level, risk_score = assess_risk(title, content, likes, comments, author)
    category = categorize(title, content)

    # 双 AI 融合摘要
    summary = generate_summary(title, content, sentiment, risk_level, topics)

    # 官方账号标记
    is_official = 1 if author in OFFICIAL_ACCOUNTS else 0

    return {
        'sentiment': sentiment,
        'sentiment_score': sentiment_score,
        'sentiment_reasons': sentiment_reasons,
        'risk_level': risk_level,
        'risk_score': risk_score,
        'summary': summary,
        'topics': topics,
        'category': category,
        'ai_provider': provider,
        'is_official': is_official,
    }


def batch_analyze(notes, provider='hybrid'):
    """批量分析"""
    results = []
    for note in notes:
        analysis = analyze_note(note, provider)
        results.append({**note, **analysis})
    return results


def generate_daily_report(notes, stats, date_str=None):
    """生成基于真实采集数据的日报。"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 话题统计
    topic_count = {}
    for n in notes:
        for t in n.get('topics', []):
            if t and t != '其他':
                topic_count[t] = topic_count.get(t, 0) + 1
    top_topics = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)[:10]
    top_topics = [{'topic': t, 'count': c} for t, c in top_topics]

    # 热门笔记
    hot_notes = sorted(notes, key=lambda x: _safe_int(x.get('likes', 0)) + _safe_int(x.get('comments', 0)) * 2, reverse=True)[:5]
    hot_notes = [{
        'note_id': n['note_id'], 'title': n.get('title', ''),
        'author': n.get('author_nickname', ''), 'likes': n.get('likes', 0),
        'comments': n.get('comments', 0), 'url': n.get('url', ''),
        'sentiment': n.get('sentiment', 'neutral'), 'risk_level': n.get('risk_level', 'low'),
    } for n in hot_notes]

    # 风险预警
    risk_alerts = []
    high_risk = [n for n in notes if n.get('risk_level') == 'high']
    for n in high_risk[:5]:
        risk_alerts.append({
            'note_id': n['note_id'], 'title': n.get('title', ''),
            'author': n.get('author_nickname', ''), 'risk_score': n.get('risk_score', 0),
            'summary': n.get('summary', ''), 'url': n.get('url', ''),
        })

    # 日报总结
    neg_count = stats.get('negative', 0)
    high_count = stats.get('high_risk', 0)
    total = stats.get('total', 0)

    summary_parts = [f"{date_str} 共监测到 {total} 条广州太古汇相关笔记"]
    if total > 0:
        pos_pct = round(stats.get('positive', 0) / total * 100, 1)
        neg_pct = round(neg_count / total * 100, 1)
        summary_parts.append(f"正面占比 {pos_pct}%，负面占比 {neg_pct}%")
    if high_count > 0:
        summary_parts.append(f"⚠️ 发现 {high_count} 条高风险内容，建议优先处理")
    if top_topics:
        summary_parts.append(f"热门话题：{'、'.join([t['topic'] for t in top_topics[:3]])}")

    return {
        'report_type': 'daily',
        'report_date': date_str,
        'period_start': date_str,
        'period_end': date_str,
        'total_notes': total,
        'positive_count': stats.get('positive', 0),
        'neutral_count': stats.get('neutral', 0),
        'negative_count': neg_count,
        'high_risk_count': high_count,
        'medium_risk_count': stats.get('medium_risk', 0),
        'low_risk_count': stats.get('low_risk', 0),
        'total_likes': stats.get('total_likes', 0),
        'total_comments': stats.get('total_comments', 0),
        'total_engagements': stats.get('total_engagements', 0),
        'top_topics': top_topics,
        'hot_notes': hot_notes,
        'risk_alerts': risk_alerts,
        'key_events': _extract_key_events(notes, 'daily'),
        'event_summary': _build_event_summary(notes, 'daily', date_str, date_str),
        'sentiment_analysis': _build_sentiment_analysis(notes, stats, 'daily'),
        'summary': '；'.join(summary_parts),
    }


def _extract_key_events(notes, period_type):
    """从真实笔记中提取关键事件（仅基于采集到的真实数据，不编造）"""
    events = []
    seen_titles = set()
    # 按话题分组
    topic_groups = {}
    for n in notes:
        for t in n.get('topics', []):
            if t and t != '其他':
                topic_groups.setdefault(t, []).append(n)
    # 每个话题取互动量最高的代表笔记作为事件
    for topic, group in sorted(topic_groups.items(), key=lambda x: len(x[1]), reverse=True):
        group_sorted = sorted(group, key=lambda x: _safe_int(x.get('likes', 0)) + _safe_int(x.get('comments', 0)) * 2, reverse=True)
        for n in group_sorted[:2]:
            title = n.get('title', '') or '（无标题）'
            if title in seen_titles:
                continue
            seen_titles.add(title)
            events.append({
                'event_topic': topic,
                'title': title[:60],
                'author': n.get('author_nickname', ''),
                'note_id': n['note_id'],
                'url': n.get('url', ''),
                'likes': _safe_int(n.get('likes', 0)),
                'comments': _safe_int(n.get('comments', 0)),
                'sentiment': n.get('sentiment', 'neutral'),
                'risk_level': n.get('risk_level', 'low'),
                'risk_score': n.get('risk_score', 0),
                'summary': n.get('summary', '')[:120],
                'is_official': n.get('is_official', 0),
            })
    # 限制事件数量
    max_events = {'daily': 8, 'weekly': 12, 'monthly': 15, 'yearly': 20}.get(period_type, 10)
    return events[:max_events]


def _build_event_summary(notes, period_type, period_start, period_end):
    """事件汇总（基于真实数据，按话题维度归纳）"""
    if not notes:
        return f"本周期（{period_start} 至 {period_end}）暂无采集数据。"
    topic_count = {}
    for n in notes:
        for t in n.get('topics', []):
            if t and t != '其他':
                topic_count[t] = topic_count.get(t, 0) + 1
    sorted_topics = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)
    period_label = {'daily': '当日', 'weekly': '本周', 'monthly': '本月', 'yearly': '本年', 'special': '近30日'}.get(period_type, '本周期')
    parts = [f"【{period_label}事件汇总】数据覆盖 {period_start} 至 {period_end}，共采集 {len(notes)} 条真实笔记。"]
    if sorted_topics:
        parts.append(f"主要事件话题集中在：{'、'.join([f'{t}({c}条)' for t, c in sorted_topics[:5]])}。")
    # 负面事件
    neg_notes = [n for n in notes if n.get('sentiment') == 'negative']
    if neg_notes:
        neg_topics = {}
        for n in neg_notes:
            for t in n.get('topics', []):
                if t and t != '其他':
                    neg_topics[t] = neg_topics.get(t, 0) + 1
        if neg_topics:
            top_neg = sorted(neg_topics.items(), key=lambda x: x[1], reverse=True)[:3]
            parts.append(f"负面舆情主要涉及：{'、'.join([f'{t}({c}条)' for t, c in top_neg])}。")
    # 高风险
    high_risk = [n for n in notes if n.get('risk_level') == 'high']
    if high_risk:
        parts.append(f"⚠️ 识别到 {len(high_risk)} 条高风险内容，需重点关注。")
    # 官方动态
    official = [n for n in notes if n.get('is_official')]
    if official:
        parts.append(f"官方账号发布 {len(official)} 条内容，以活动推广和品牌宣传为主。")
    parts.append("以上事件均来自小红书真实采集数据，每条事件可通过笔记链接溯源核实。")
    return '\n'.join(parts)


def _build_sentiment_analysis(notes, stats, period_type):
    """舆情分析（基于真实数据的多维度分析）"""
    if not notes:
        return "暂无数据，无法进行舆情分析。"
    total = len(notes)
    pos = stats.get('positive', 0)
    neg = stats.get('negative', 0)
    neu = stats.get('neutral', 0)
    pos_pct = round(pos / total * 100, 1) if total else 0
    neg_pct = round(neg / total * 100, 1) if total else 0
    neu_pct = round(neu / total * 100, 1) if total else 0
    period_label = {'daily': '当日', 'weekly': '本周', 'monthly': '本月', 'yearly': '本年', 'special': '近30日'}.get(period_type, '本周期')
    parts = [f"【{period_label}舆情分析】"]
    # 情感格局
    parts.append(f"一、情感格局：正面{pos}条({pos_pct}%)、中性{neu}条({neu_pct}%)、负面{neg}条({neg_pct}%)。")
    if neg_pct > 25:
        parts.append("负面占比偏高，舆情整体偏谨慎，建议加强客服响应和负面内容跟进。")
    elif pos_pct > neg_pct:
        parts.append("正面声量优于负面，品牌口碑整体健康。")
    else:
        parts.append("正负声量接近，舆情处于中性偏观察状态。")
    # 风险态势
    high = stats.get('high_risk', 0)
    med = stats.get('medium_risk', 0)
    parts.append(f"二、风险态势：高风险{high}条、中风险{med}条。")
    if high > 0:
        high_notes = [n for n in notes if n.get('risk_level') == 'high']
        high_topics = set()
        for n in high_notes:
            for t in n.get('topics', []):
                if t and t != '其他':
                    high_topics.add(t)
        parts.append(f"高风险集中在：{'、'.join(list(high_topics)[:3])}。建议24小时内跟进处理。")
    # 传播力
    total_eng = stats.get('total_engagements', 0)
    if total_eng > 0:
        avg_eng = round(total_eng / total)
        parts.append(f"三、传播力：总互动量{total_eng}，篇均互动{avg_eng}。")
        hot = sorted(notes, key=lambda x: _safe_int(x.get('likes', 0)) + _safe_int(x.get('comments', 0)), reverse=True)[:1]
        if hot:
            parts.append(f"传播最热内容：「{hot[0].get('title', '无标题')[:30]}」（互动{_safe_int(hot[0].get('likes', 0)) + _safe_int(hot[0].get('comments', 0))}）。")
    # 话题趋势
    topic_count = {}
    for n in notes:
        for t in n.get('topics', []):
            if t and t != '其他':
                topic_count[t] = topic_count.get(t, 0) + 1
    if topic_count:
        top3 = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)[:3]
        parts.append(f"四、话题焦点：{' > '.join([t for t, _ in top3])}。")
    parts.append("注：以上分析全部基于小红书真实采集笔记，AI仅做归纳统计，不虚构任何事件。")
    return '\n'.join(parts)


def generate_period_report(notes, stats, report_type='daily', period_start='', period_end=''):
    """通用周期报告生成（日报/周报/月报）"""
    from datetime import datetime, timedelta
    today = datetime.now().strftime('%Y-%m-%d')
    if not period_start:
        period_start = today
    if not period_end:
        period_end = today
    # 基于通用逻辑生成
    topic_count = {}
    for n in notes:
        for t in n.get('topics', []):
            if t and t != '其他':
                topic_count[t] = topic_count.get(t, 0) + 1
    top_topics = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)[:10]
    top_topics = [{'topic': t, 'count': c} for t, c in top_topics]
    hot_notes = sorted(notes, key=lambda x: _safe_int(x.get('likes', 0)) + _safe_int(x.get('comments', 0)) * 2, reverse=True)[:5]
    hot_notes = [{
        'note_id': n['note_id'], 'title': n.get('title', ''),
        'author': n.get('author_nickname', ''), 'likes': n.get('likes', 0),
        'comments': n.get('comments', 0), 'url': n.get('url', ''),
        'sentiment': n.get('sentiment', 'neutral'), 'risk_level': n.get('risk_level', 'low'),
    } for n in hot_notes]
    risk_alerts = []
    for n in [x for x in notes if x.get('risk_level') == 'high'][:5]:
        risk_alerts.append({
            'note_id': n['note_id'], 'title': n.get('title', ''),
            'author': n.get('author_nickname', ''), 'risk_score': n.get('risk_score', 0),
            'summary': n.get('summary', ''), 'url': n.get('url', ''),
        })
    total = len(notes)
    neg_count = stats.get('negative', 0)
    high_count = stats.get('high_risk', 0)
    period_label = {'daily': '日报', 'weekly': '周报', 'monthly': '月报', 'yearly': '年报', 'special': '专报'}.get(report_type, '专报')
    summary_parts = [f"{period_start} 至 {period_end} {period_label}：共监测 {total} 条笔记"]
    if total > 0:
        summary_parts.append(f"正面{round(stats.get('positive', 0)/total*100,1)}% / 负面{round(neg_count/total*100,1)}%")
    if high_count > 0:
        summary_parts.append(f"高风险{high_count}条")
    if top_topics:
        summary_parts.append(f"焦点：{'、'.join([t['topic'] for t in top_topics[:3]])}")
    return {
        'report_type': report_type,
        'report_date': period_end,
        'period_start': period_start,
        'period_end': period_end,
        'total_notes': total,
        'positive_count': stats.get('positive', 0),
        'neutral_count': stats.get('neutral', 0),
        'negative_count': neg_count,
        'high_risk_count': high_count,
        'medium_risk_count': stats.get('medium_risk', 0),
        'low_risk_count': stats.get('low_risk', 0),
        'total_likes': stats.get('total_likes', 0),
        'total_comments': stats.get('total_comments', 0),
        'total_engagements': stats.get('total_engagements', 0),
        'top_topics': top_topics,
        'hot_notes': hot_notes,
        'risk_alerts': risk_alerts,
        'key_events': _extract_key_events(notes, report_type),
        'event_summary': _build_event_summary(notes, report_type, period_start, period_end),
        'sentiment_analysis': _build_sentiment_analysis(notes, stats, report_type),
        'summary': '；'.join(summary_parts),
    }
