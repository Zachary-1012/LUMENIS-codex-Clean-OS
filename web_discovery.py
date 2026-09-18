"""LUMENIS public web discovery.

Canonical public-source discovery for brand/industry monitoring and the
reprocessing pipeline. This module is version-neutral and owns the public RSS
normalization used by both API and background analysis paths.
"""
import os
import json
import requests
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse


DEFAULT_DISCOVERY_QUERIES = [
    '广州太古汇',
    '广州太古汇 投诉',
    '广州太古汇 避雷',
    '广州太古汇 安全',
    '广州太古汇 活动',
    '广州太古汇 品牌',
    '广州太古汇 餐饮',
    '广州太古汇 服务',
]

FEEDBACK_SIGNALS = (
    '投诉', '差评', '避雷', '问题', '失望', '安全', '事故', '消防',
    '服务', '停车', '售后', '骚扰',
)


def _as_web_mention(item):
    """Normalize one public RSS item to the canonical web_mentions contract."""
    url = str(item.get('url') or '').strip()
    title = str(item.get('title') or '').strip()
    source_name = str(item.get('source') or '').strip()
    return {
        'source_id': url or title,
        'source_platform': 'web',
        'source_type': 'public_rss',
        'title': title,
        'content': source_name,
        'url': url,
        'domain': urlparse(url).netloc.lower() if url else '',
        'published_at': item.get('published_at') or '',
        'source_adapter': 'google_news_rss',
        'query': item.get('query') or '',
        'canonical_url': url,
    }


def discover(limit=20, queries=None):
    """Discover public mentions through the canonical no-key RSS source.

    Returns only real normalized results. Failures are isolated per query and
    never converted into fabricated mentions.
    """
    try:
        wanted = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        wanted = 20
    query_list = [str(q).strip() for q in (queries or DEFAULT_DISCOVERY_QUERIES) if str(q).strip()]
    seen = set()
    items = []
    per_query = max(3, min(20, (wanted + max(len(query_list), 1) - 1) // max(len(query_list), 1)))
    for query in query_list:
        outcome = fetch_google_news_rss(query, max_results=per_query)
        if not outcome.get('ok'):
            continue
        for raw in outcome.get('items', []):
            item = _as_web_mention(raw)
            key = item.get('canonical_url') or item.get('source_id')
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(item)
            if len(items) >= wanted:
                return items
    return items


def feedback_keywords(items=None):
    """Extract deterministic feedback signals from collected public mentions."""
    found = []
    seen = set()
    for item in items or []:
        text = ' '.join(str(item.get(k) or '') for k in ('title', 'content', 'query'))
        for signal in FEEDBACK_SIGNALS:
            if signal in text and signal not in seen:
                seen.add(signal)
                found.append(signal)
    return found


# 品牌业态分类
BRAND_CATEGORIES = {
    '零售品牌': ['奢侈品', '服饰', '美妆', '珠宝', '手表', '电子', '家居', '运动'],
    '餐饮': ['中餐', '西餐', '日料', '韩餐', '咖啡', '甜品', '奶茶', '快餐'],
    '商场服务': ['停车', '会员', '积分', '客服', '导览', '寄存'],
    '活动展览': ['展览', '快闪', '促销', '节日', '周年庆', '明星活动'],
    '环境设施': ['卫生', '空调', '母婴室', '电梯', '洗手间', '休息区'],
    '安全突发': ['安全', '事故', '突发', '紧急', '疏散']
}

def brand_queries(brands=None, categories=None):
    """
    生成品牌查询关键词列表
    brands: 品牌名称列表
    categories: 业态分类列表
    """
    queries = []
    
    # 默认品牌（广州太古汇核心品牌）
    if not brands:
        brands = ['广州太古汇', '太古汇', 'Taikoo Hui']
    
    # 默认分类
    if not categories:
        categories = list(BRAND_CATEGORIES.keys())
    
    # 生成查询组合
    for brand in brands:
        queries.append(brand)
        for cat in categories:
            queries.append(f"{brand} {cat}")
            # 添加负面关键词组合
            neg_words = ['投诉', '差评', '避雷', '问题', '失望']
            for neg in neg_words[:2]:
                queries.append(f"{brand} {cat} {neg}")
    
    # 去重
    queries = list(set(queries))
    return queries[:50]  # 限制最多50个查询

def discover_brand_industry(brands=None, categories=None, batch=20, offset=0):
    """
    发现品牌业态信息（全网搜索，不占用小红书次数）
    返回: (items, total)
    """
    queries = brand_queries(brands, categories)
    
    # 分页
    paginated_queries = queries[offset:offset + batch]
    
    items = []
    total = len(queries)
    
    for query in paginated_queries:
        try:
            # 使用Google News RSS（无需API Key）
            results = _search_google_news_rss(query)
            items.extend(results)
        except Exception as e:
            # 搜索失败，跳过
            pass
    
    # 按时间排序
    items.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    
    return items, total

def fetch_google_news_rss(query, max_results=5):
    """Fetch and normalize the existing public RSS source with explicit failure state.

    The fixed provider host and quoted query prevent this helper from becoming a
    configurable-URL fetcher. Existing callers keep using the list-returning
    wrapper below; the Collector adapter consumes the structured result.
    """
    import xml.etree.ElementTree as ET

    collected_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    outcome = {
        'ok': False,
        'items': [],
        'provider': 'google_news_rss',
        'source': 'news.google.com/rss/search',
        'collected_at': collected_at,
        'error_type': '',
    }
    try:
        query = str(query or '').strip()
        if not query or len(query) > 120:
            outcome['error_type'] = 'INVALID_QUERY'
            return outcome
        limit = max(1, min(int(max_results), 20))
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        headers = {
            'User-Agent': 'LUMENIS-Collector/1.0 (+public RSS reader)'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            outcome['error_type'] = f'HTTP_{response.status_code}'
            return outcome

        root = ET.fromstring(response.content)
        channel = root.find('channel')
        if channel is None:
            outcome['error_type'] = 'RSS_CHANNEL_MISSING'
            return outcome

        from email.utils import parsedate_to_datetime
        items = []
        for item in channel.findall('item')[:limit]:
            pub_date = item.findtext('pubDate', '')
            published_at = ''
            if pub_date:
                try:
                    published_at = parsedate_to_datetime(pub_date).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    published_at = pub_date
            items.append({
                'title': item.findtext('title', ''),
                'url': item.findtext('link', ''),
                'source': item.findtext('source', ''),
                'published_at': published_at,
                'query': query,
                'platform': 'google_news',
            })
        outcome['ok'] = True
        outcome['items'] = items
        return outcome
    except requests.RequestException as exc:
        outcome['error_type'] = type(exc).__name__
        return outcome
    except ET.ParseError:
        outcome['error_type'] = 'RSS_PARSE_ERROR'
        return outcome
    except Exception as exc:
        outcome['error_type'] = type(exc).__name__
        return outcome


def _search_google_news_rss(query, max_results=5):
    """Backward-compatible list API for the existing web-monitor callers."""
    outcome = fetch_google_news_rss(query, max_results=max_results)
    return outcome['items'] if outcome.get('ok') else []

def get_brand_directory():
    """
    获取品牌目录（从brand_directory.json）
    """
    try:
        dir_path = os.path.join(os.path.dirname(__file__), 'data', 'brand_directory.json')
        if os.path.exists(dir_path):
            with open(dir_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    
    # 默认品牌目录
    return {
        'brands': [
            {'name': '广州太古汇', 'category': '商场', 'floor': '全馆'},
        ],
        'categories': list(BRAND_CATEGORIES.keys()),
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }

def get_industry_stats():
    """
    获取业态统计信息
    """
    stats = {}
    for cat in BRAND_CATEGORIES.keys():
        stats[cat] = {
            'mentions': 0,
            'negative': 0,
            'positive': 0,
            'neutral': 0
        }
    
    # 从数据库获取统计（如果可用）
    try:
        import database
        # 这里可以添加数据库查询逻辑
        pass
    except Exception:
        pass
    
    return stats

def search_trending_topics(days=7):
    """
    搜索热门话题（全网，不占用小红书次数）
    """
    topics = []
    queries = ['广州太古汇 热门', '广州商场 热点', '广州 舆情 热门']
    
    for query in queries:
        try:
            results = _search_google_news_rss(query, max_results=3)
            topics.extend(results)
        except Exception:
            pass
    
    return topics[:10]
