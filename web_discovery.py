"""LUMENIS public web discovery.

Canonical public-source discovery for brand/industry monitoring and the
reprocessing pipeline. This module is version-neutral and owns the public RSS
normalization used by both API and background analysis paths.
"""
import os
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse


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
    if isinstance(queries, str):
        queries = [queries]
    if queries is None or not isinstance(queries, (list, tuple)):
        return []
    query_list = [str(q).strip() for q in queries if isinstance(q, str) and q.strip()]
    if not query_list:
        return []
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


def _known_publication_datetime(item):
    """Return a UTC instant only when the source provides a timezone-aware date."""
    if not isinstance(item, dict):
        return None
    state = str(item.get('publication_time_state') or '').strip().upper()
    if state and state != 'KNOWN':
        return None
    for value in (item.get('published_at'), item.get('source_published_at')):
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str) and value.strip():
            raw = value.strip()
            try:
                parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(raw)
                except (TypeError, ValueError, OverflowError):
                    continue
        else:
            continue
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            continue
        try:
            return parsed.astimezone(timezone.utc)
        except (OverflowError, ValueError):
            continue
    return None


def _sort_publication_chronologically(items):
    """Sort known publication instants newest-first and keep unknowns stable-last."""
    known = []
    unknown = []
    for item in items:
        published = _known_publication_datetime(item)
        if published is None:
            unknown.append(item)
        else:
            known.append((published, item))
    known.sort(key=lambda entry: entry[0], reverse=True)
    return [entry[1] for entry in known] + unknown


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
    
    if isinstance(brands, str):
        brands = [brands]
    if not isinstance(brands, (list, tuple)) or not brands:
        return []
    
    # 默认分类
    if not categories:
        categories = list(BRAND_CATEGORIES.keys())
    
    # 生成查询组合
    for brand in brands:
        if not isinstance(brand, str) or not brand.strip():
            continue
        brand = brand.strip()
        queries.append(brand)
        for cat in categories:
            queries.append(f"{brand} {cat}")
            # 添加负面关键词组合
            neg_words = ['投诉', '差评', '避雷', '问题', '失望']
            for neg in neg_words[:2]:
                queries.append(f"{brand} {cat} {neg}")
    
    # 去重
    queries = list(dict.fromkeys(queries))
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
    
    # Lexical sorting is wrong when ISO and RFC dates carry different offsets.
    items = _sort_publication_chronologically(items)
    
    return items, total

def fetch_google_news_rss(query, max_results=5):
    """Fetch and normalize the existing public RSS source with explicit failure state.

    The fixed provider host and quoted query prevent this helper from becoming a
    configurable-URL fetcher. Existing callers keep using the list-returning
    wrapper below; the Collector adapter consumes the structured result.
    """
    import xml.etree.ElementTree as ET

    collected_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    outcome = {
        'ok': False,
        'items': [],
        'provider': 'google_news_rss',
        'source': 'news.google.com/rss/search',
        'collected_at': collected_at,
        'error_type': '',
    }
    try:
        from email.utils import parsedate_to_datetime
        from lumenis.system.collector.adapters import public_source

        query = str(query or '').strip()
        if not query or len(query) > 120:
            outcome['error_type'] = 'INVALID_QUERY'
            return outcome
        limit = max(1, min(int(max_results), 20))
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        response = public_source.fetch_public_url(
            url,
            timeout=10,
            max_bytes=public_source.MAX_RESPONSE_BYTES,
            allowed_host_suffixes=('google.com',),
        )
        outcome['http_status'] = response.status_code
        outcome.update(public_source.public_source_provenance(response, url))
        if response.content_type not in {
            'application/rss+xml', 'application/xml', 'text/xml',
        }:
            outcome['error_type'] = 'RSS_RESPONSE_TYPE_UNSUPPORTED'
            return outcome

        root = ET.fromstring(response.content)
        channel = root.find('channel')
        if channel is None:
            outcome['error_type'] = 'RSS_CHANNEL_MISSING'
            return outcome

        items = []
        for item in channel.findall('item')[:limit]:
            pub_date = item.findtext('pubDate', '')
            published_at = ''
            publication_time_state = 'UNKNOWN'
            if pub_date:
                try:
                    parsed_time = parsedate_to_datetime(pub_date)
                    if parsed_time.tzinfo is not None and parsed_time.utcoffset() is not None:
                        # Keep the queryable value in one sortable timezone;
                        # preserve the source's literal separately below.
                        published_at = parsed_time.astimezone(timezone.utc).isoformat()
                        publication_time_state = 'KNOWN'
                except Exception:
                    pass
            source_element = item.find('source')
            items.append({
                'title': item.findtext('title', ''),
                'url': item.findtext('link', ''),
                'source': source_element.text if source_element is not None else '',
                'source_url': (source_element.get('url', '')
                               if source_element is not None else ''),
                'published_at': published_at,
                'source_published_at': pub_date,
                'publication_time_state': publication_time_state,
                'query': query,
                'platform': 'google_news',
            })
        outcome['ok'] = True
        outcome['items'] = items
        return outcome
    except ET.ParseError:
        outcome['error_type'] = 'RSS_PARSE_ERROR'
        return outcome
    except Exception as exc:
        status_code = getattr(exc, 'status_code', None)
        if (getattr(exc, 'failure_type', None) == 'HTTP_STATUS'
                and isinstance(status_code, int) and not isinstance(status_code, bool)):
            outcome['http_status'] = status_code
            outcome['error_type'] = f'HTTP_{status_code}'
        else:
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
    dir_path = os.path.join(os.path.dirname(__file__), 'data', 'brand_directory.json')
    try:
        with open(dir_path, 'r', encoding='utf-8') as f:
            directory = json.load(f)
    except FileNotFoundError:
        return {
            'brands': [], 'categories': {}, 'total_brands': None,
            'updated_at': None, 'source': None, 'status': 'NOT_AVAILABLE',
            'reason': 'DIRECTORY_FILE_MISSING',
        }
    except (OSError, ValueError):
        return {
            'brands': [], 'categories': {}, 'total_brands': None,
            'updated_at': None, 'source': None, 'status': 'ERROR',
            'reason': 'DIRECTORY_FILE_UNREADABLE',
        }
    if not isinstance(directory, dict) or not isinstance(directory.get('brands'), list):
        return {
            'brands': [], 'categories': {}, 'total_brands': None,
            'updated_at': None, 'source': None, 'status': 'ERROR',
            'reason': 'DIRECTORY_SCHEMA_INVALID',
        }
    return {**directory, 'status': 'AVAILABLE'}

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

def search_trending_topics(days=7, queries=None):
    """
    搜索热门话题（全网，不占用小红书次数）
    """
    topics = []
    if isinstance(queries, str):
        queries = [queries]
    if not isinstance(queries, (list, tuple)) or not queries:
        return topics
    
    for query in queries:
        try:
            results = _search_google_news_rss(query, max_results=3)
            topics.extend(results)
        except Exception:
            pass
    
    return topics[:10]
