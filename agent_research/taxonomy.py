"""Research taxonomy. Labels never grant rights or establish facts."""
from copy import deepcopy
RESEARCH_DIMENSIONS = [{'key': 'global_market', 'zh': '全球市场', 'en': 'Global Market', 'ko': '글로벌 시장'}, {'key': 'region_country', 'zh': '国家/地区', 'en': 'Region / Country', 'ko': '국가/지역'}, {'key': 'industry', 'zh': '行业', 'en': 'Industry', 'ko': '산업'}, {'key': 'business', 'zh': '商业', 'en': 'Business', 'ko': '비즈니스'}, {'key': 'policy_regulation', 'zh': '政策法规', 'en': 'Policy & Regulation', 'ko': '정책·규제'}, {'key': 'technology', 'zh': '技术', 'en': 'Technology', 'ko': '기술'}, {'key': 'competition', 'zh': '竞争格局', 'en': 'Competition', 'ko': '경쟁 구도'}, {'key': 'trend', 'zh': '趋势', 'en': 'Trends', 'ko': '트렌드'}, {'key': 'growth_opportunity', 'zh': '增长机会', 'en': 'Growth Opportunity', 'ko': '성장 기회'}]
REGIONS = [{'key': 'global', 'zh': '全球', 'en': 'Global', 'ko': '글로벌'}, {'key': 'north_america', 'zh': '北美', 'en': 'North America', 'ko': '북미'}, {'key': 'europe', 'zh': '欧洲', 'en': 'Europe', 'ko': '유럽'}, {'key': 'asia_pacific', 'zh': '亚太', 'en': 'Asia Pacific', 'ko': '아시아 태평양'}, {'key': 'china', 'zh': '中国', 'en': 'China', 'ko': '중국'}, {'key': 'latin_america', 'zh': '拉美', 'en': 'Latin America', 'ko': '라틴 아메리카'}, {'key': 'middle_east_africa', 'zh': '中东非洲', 'en': 'Middle East & Africa', 'ko': '중동·아프리카'}]
EVIDENCE_LEVELS = [{'key': 'FACT', 'zh': '事实', 'en': 'Fact', 'ko': '사실', 'meaning_en': 'Directly observed or sourced datum', 'meaning_zh': '直接观察或有来源的数据'}, {'key': 'EVIDENCE', 'zh': '证据', 'en': 'Evidence', 'ko': '증거', 'meaning_en': 'Verified material supporting a claim', 'meaning_zh': '经核验、支撑论断的材料'}, {'key': 'INFERENCE', 'zh': '推断', 'en': 'Inference', 'ko': '추론', 'meaning_en': 'Reasoned conclusion from evidence, defeasible', 'meaning_zh': '基于证据的推理结论，可被推翻'}, {'key': 'HYPOTHESIS', 'zh': '假设', 'en': 'Hypothesis', 'ko': '가설', 'meaning_en': 'Testable proposition not yet confirmed', 'meaning_zh': '待验证的可检验命题'}, {'key': 'DECISION', 'zh': '决策', 'en': 'Decision', 'ko': '의사결정', 'meaning_en': 'A chosen commitment grounded in the above', 'meaning_zh': '基于前述做出的承诺性选择'}]

# Preserve source labels without adopting its sourced-datum => FACT semantics.
for _level in EVIDENCE_LEVELS:
    _level['source_meaning_en'] = _level.pop('meaning_en', '')
    _level['source_meaning_zh'] = _level.pop('meaning_zh', '')
    _level['classification_only'] = True

def _valid(key, items):
    return isinstance(key, str) and key in {item['key'] for item in items}

def is_valid_dimension(key):
    return _valid(key, RESEARCH_DIMENSIONS)

def is_valid_region(key):
    return _valid(key, REGIONS)

def is_valid_level(key):
    return _valid(key, EVIDENCE_LEVELS)

def normalize_dimension(key):
    if not is_valid_dimension(key):
        raise ValueError('UNKNOWN_RESEARCH_DIMENSION')
    return key

def get_research_taxonomy(lang='en'):
    if lang not in ('en', 'zh', 'ko'):
        raise ValueError('UNKNOWN_RESEARCH_LANGUAGE')
    return {name: [dict(deepcopy(row), label=row[lang]) for row in rows]
            for name, rows in [('dimensions', RESEARCH_DIMENSIONS), ('regions', REGIONS),
                               ('claim_labels', EVIDENCE_LEVELS)]}

def taxonomy_payload(lang='en'):
    return get_research_taxonomy(lang)
