"""
品牌营销知识库（V3.0 影子板块 - 为脱离AI做基础）
归属：Z-Brand Core / ZBMP / 品牌智能层
目标：
  1. 全网学习品牌营销、广告宣传、舆情监测管理的领域知识
  2. 结构化存储，支持检索、分类、关联
  3. 为系统脱离外部AI、自主分析品牌传播提供知识基础
  4. 与现有 ai_learning_engine.py（AI操作模式学习）解耦，但可复用底层存储

知识分类：
  - brand_marketing：品牌营销理论与方法
  - advertising：广告宣传策略与案例
  - pr_management：舆情监测与公关管理
  - consumer_behavior：消费者行为与心理
  - market_trend：市场趋势与行业动态
  - case_study：品牌案例分析

存储结构：
  - brand_knowledge 表：知识条目（id/category/title/content/source/tags/created_at）
  - brand_knowledge_tags 表：标签关联
  - JSON文件备份：data/brand_knowledge_base.json

使用方式：
  - 系统分析品牌传播时，自动检索相关知识库
  - AI生成报告时，引用知识库内容作为依据
  - 定期从全网学习新知识，自动入库
"""
from __future__ import annotations

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from lumenis.shared.database import DatabaseRepository, main_db_path
from lumenis.shared.database.registry import resolve_path


DB_PATH = main_db_path()
KNOWLEDGE_JSON = resolve_path('data/brand_knowledge_base.json')

# 知识分类
CATEGORIES = {
    'brand_marketing': '品牌营销',
    'advertising': '广告宣传',
    'pr_management': '舆情管理',
    'consumer_behavior': '消费者行为',
    'market_trend': '市场趋势',
    'case_study': '品牌案例',
    'communication': '传播策略',
    'crisis_management': '危机公关',
}


class BrandKnowledgeBase:
    """品牌营销知识库"""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or main_db_path()
        self._repository = DatabaseRepository(db_path)
        self._ensure_table()

    def _conn(self) -> sqlite3.Connection:
        return self._repository.connect(timeout=15)

    def _ensure_table(self):
        """确保知识库表存在"""
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS brand_knowledge(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    url TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    content_hash TEXT UNIQUE,
                    relevance_score REAL DEFAULT 0.5,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_bk_category ON brand_knowledge(category)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_bk_tags ON brand_knowledge(tags)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_bk_created ON brand_knowledge(created_at)")

    def _hash_content(self, title: str, content: str) -> str:
        """内容哈希，用于去重"""
        return hashlib.md5(f'{title}|{content[:500]}'.encode('utf-8')).hexdigest()

    def add_knowledge(self, category: str, title: str, content: str,
                      source: str = '', url: str = '', tags: List[str] = None,
                      relevance_score: float = 0.5) -> Dict[str, Any]:
        """添加一条知识（自动去重）"""
        if category not in CATEGORIES:
            return {'ok': False, 'error': f'未知分类: {category}，支持: {list(CATEGORIES.keys())}'}

        content_hash = self._hash_content(title, content)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tags_str = ','.join(tags or [])

        try:
            with self._conn() as c:
                # 检查是否已存在
                existing = c.execute('SELECT id FROM brand_knowledge WHERE content_hash = ?', (content_hash,)).fetchone()
                if existing:
                    return {'ok': True, 'id': existing['id'], 'duplicate': True, 'message': '知识已存在，跳过'}

                cur = c.execute("""
                    INSERT INTO brand_knowledge(category, title, content, source, url, tags, content_hash, relevance_score, created_at, updated_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (category, title, content, source, url, tags_str, content_hash, relevance_score, now, now))
                return {'ok': True, 'id': cur.lastrowid, 'duplicate': False}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def search(self, keyword: str = '', category: str = '',
               limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索知识库"""
        query = 'SELECT * FROM brand_knowledge WHERE 1=1'
        params = []

        if keyword:
            query += ' AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)'
            like = f'%{keyword}%'
            params.extend([like, like, like])

        if category and category in CATEGORIES:
            query += ' AND category = ?'
            params.append(category)

        query += ' ORDER BY relevance_score DESC, created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        with self._conn() as c:
            rows = c.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """按分类获取知识"""
        return self.search(category=category, limit=limit)

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计"""
        with self._conn() as c:
            total = c.execute('SELECT COUNT(*) as cnt FROM brand_knowledge').fetchone()['cnt']
            by_category = {}
            for cat in CATEGORIES:
                cnt = c.execute('SELECT COUNT(*) as cnt FROM brand_knowledge WHERE category = ?', (cat,)).fetchone()['cnt']
                if cnt > 0:
                    by_category[CATEGORIES[cat]] = cnt
            return {
                'total': total,
                'by_category': by_category,
                'categories': CATEGORIES,
            }

    def export_to_json(self, filepath: str = KNOWLEDGE_JSON) -> Dict[str, Any]:
        """导出知识库到JSON文件"""
        stats = self.get_stats()
        all_knowledge = self.search(limit=10000)
        data = {
            'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stats': stats,
            'knowledge': all_knowledge,
        }
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {'ok': True, 'filepath': filepath, 'count': len(all_knowledge)}

    def batch_import(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量导入知识"""
        success = 0
        duplicates = 0
        failed = 0
        for item in items:
            result = self.add_knowledge(
                category=item.get('category', ''),
                title=item.get('title', ''),
                content=item.get('content', ''),
                source=item.get('source', ''),
                url=item.get('url', ''),
                tags=item.get('tags', []),
                relevance_score=item.get('relevance_score', 0.5),
            )
            if result.get('ok'):
                if result.get('duplicate'):
                    duplicates += 1
                else:
                    success += 1
            else:
                failed += 1
        return {'success': success, 'duplicates': duplicates, 'failed': failed, 'total': len(items)}


# 全局单例
_kb_instance: Optional[BrandKnowledgeBase] = None

def get_knowledge_base() -> BrandKnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = BrandKnowledgeBase()
    return _kb_instance
