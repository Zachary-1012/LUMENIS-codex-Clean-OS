"""
全网话题发现脚本
不依赖微博登录，用普通网页搜索广州太古汇相关话题
不占用小红书采集次数
"""
import os
import sys
import json
import sqlite3
import urllib.request
import urllib.parse
import re
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')

# 搜索关键词
SEARCH_KEYWORDS = [
    '广州太古汇',
    '太古汇 投诉',
    '太古汇 避雷',
    '太古汇 停车',
    '太古汇 活动',
    '太古汇 品牌',
    '太古汇 餐饮',
    '太古汇 服务',
]

# User-Agent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables():
    """确保表存在"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 全网话题表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS web_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            title TEXT,
            url TEXT,
            source TEXT,
            summary TEXT,
            sentiment TEXT DEFAULT 'neutral',
            discovered_at TEXT,
            UNIQUE(url)
        )
    """)
    
    # 品牌业态监测表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brand_industry_monitor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT,
            industry TEXT,
            topic TEXT,
            url TEXT,
            source TEXT,
            sentiment TEXT DEFAULT 'neutral',
            discovered_at TEXT,
            UNIQUE(url)
        )
    """)
    
    conn.commit()
    conn.close()


def search_bing(keyword: str) -> List[Dict[str, Any]]:
    """使用Bing搜索（不需要登录）"""
    results = []
    try:
        query = urllib.parse.quote(keyword)
        url = f'https://www.bing.com/search?q={query}&count=20'
        
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # 提取搜索结果
        # Bing结果通常在 <li class="b_algo"> 中
        pattern = r'<li class="b_algo">.*?<h2><a href="([^"]+)"[^>]*>(.*?)</a></h2>.*?<p>(.*?)</p>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for url, title_html, summary_html in matches[:10]:
            # 清理HTML标签
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            summary = re.sub(r'<[^>]+>', '', summary_html).strip()
            
            if title and url:
                results.append({
                    'title': title[:200],
                    'url': url[:500],
                    'summary': summary[:300],
                    'source': 'bing',
                })
        
    except Exception as e:
        print(f"  Bing搜索失败: {e}")
    
    return results


def save_topics(keyword: str, topics: List[Dict[str, Any]]):
    """保存话题到数据库"""
    conn = get_connection()
    cursor = conn.cursor()
    
    saved = 0
    for topic in topics:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO web_topics 
                (keyword, title, url, source, summary, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                keyword,
                topic['title'],
                topic['url'],
                topic['source'],
                topic.get('summary', ''),
                datetime.now().isoformat()
            ))
            if cursor.rowcount > 0:
                saved += 1
        except Exception as e:
            pass
    
    conn.commit()
    conn.close()
    return saved


def run_discovery():
    """运行全网话题发现"""
    print("=" * 60)
    print("🌐 全网话题发现（不占用小红书次数）")
    print("=" * 60)
    
    ensure_tables()
    
    total_saved = 0
    for keyword in SEARCH_KEYWORDS:
        print(f"\n🔍 搜索: {keyword}")
        topics = search_bing(keyword)
        print(f"  找到 {len(topics)} 条结果")
        
        if topics:
            saved = save_topics(keyword, topics)
            total_saved += saved
            print(f"  新增 {saved} 条话题")
    
    # 统计
    conn = get_connection()
    cursor = conn.execute("SELECT COUNT(*) as c FROM web_topics")
    total = cursor.fetchone()['c']
    cursor = conn.execute("SELECT source, COUNT(*) as c FROM web_topics GROUP BY source")
    sources = {row['source']: row['c'] for row in cursor.fetchall()}
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"✅ 全网话题发现完成！")
    print(f"   本次新增: {total_saved} 条")
    print(f"   话题总数: {total} 条")
    print(f"   来源分布: {sources}")
    print(f"{'=' * 60}")
    
    return total_saved


if __name__ == '__main__':
    run_discovery()
