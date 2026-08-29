"""
Web Monitor v5.7.0
全网品牌业态监测，不占用小红书采集次数
"""
import os
import json
import requests
from datetime import datetime, timedelta
from urllib.parse import quote

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

def _search_google_news_rss(query, max_results=5):
    """
    使用Google News RSS搜索（无需API Key，不占用小红书次数）
    """
    items = []
    try:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            # 简单解析RSS XML
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            channel = root.find('channel')
            if channel is not None:
                for i, item in enumerate(channel.findall('item')[:max_results]):
                    title = item.findtext('title', '')
                    link = item.findtext('link', '')
                    pub_date = item.findtext('pubDate', '')
                    source = item.findtext('source', '')
                    
                    # 转换日期格式
                    published_at = ''
                    if pub_date:
                        try:
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(pub_date)
                            published_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            published_at = pub_date
                    
                    items.append({
                        'title': title,
                        'url': link,
                        'source': source,
                        'published_at': published_at,
                        'query': query,
                        'platform': 'google_news'
                    })
    except Exception:
        pass
    
    return items

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
