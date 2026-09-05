"""品牌营销知识库（ZBMP / 品牌智能层）。"""
from __future__ import annotations

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import DB_PATH

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_JSON = os.path.abspath(os.environ.get(
    'ZBC_BRAND_KNOWLEDGE_JSON',
    os.path.join(_BASE_DIR, 'data', 'brand_knowledge_base.json'),
))

CATEGORIES = {
    'brand_marketing': '品牌营销', 'advertising': '广告宣传', 'pr_management': '舆情管理',
    'consumer_behavior': '消费者行为', 'market_trend': '市场趋势', 'case_study': '品牌案例',
    'communication': '传播策略', 'crisis_management': '危机公关',
}


class BrandKnowledgeBase:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_table()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS brand_knowledge(
                id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, title TEXT NOT NULL,
                content TEXT NOT NULL, source TEXT DEFAULT '', url TEXT DEFAULT '', tags TEXT DEFAULT '',
                content_hash TEXT UNIQUE, relevance_score REAL DEFAULT 0.5, created_at TEXT, updated_at TEXT)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_bk_category ON brand_knowledge(category)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_bk_tags ON brand_knowledge(tags)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_bk_created ON brand_knowledge(created_at)")

    def _hash_content(self, title: str, content: str) -> str:
        return hashlib.md5(f'{title}|{content[:500]}'.encode('utf-8')).hexdigest()

    def add_knowledge(self, category: str, title: str, content: str,
                      source: str = '', url: str = '', tags: List[str] = None,
                      relevance_score: float = 0.5) -> Dict[str, Any]:
        if category not in CATEGORIES:
            return {'ok': False, 'error': f'未知分类: {category}，支持: {list(CATEGORIES.keys())}'}
        content_hash = self._hash_content(title, content)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self._conn() as c:
                existing = c.execute('SELECT id FROM brand_knowledge WHERE content_hash = ?', (content_hash,)).fetchone()
                if existing:
                    return {'ok': True, 'id': existing['id'], 'duplicate': True, 'message': '知识已存在，跳过'}
                cur = c.execute("""INSERT INTO brand_knowledge
                    (category,title,content,source,url,tags,content_hash,relevance_score,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (category,title,content,source,url,','.join(tags or []),content_hash,relevance_score,now,now))
                return {'ok': True, 'id': cur.lastrowid, 'duplicate': False}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def search(self, keyword: str = '', category: str = '', limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        query = 'SELECT * FROM brand_knowledge WHERE 1=1'; params = []
        if keyword:
            query += ' AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)'; like = f'%{keyword}%'; params.extend([like]*3)
        if category and category in CATEGORIES:
            query += ' AND category = ?'; params.append(category)
        query += ' ORDER BY relevance_score DESC, created_at DESC LIMIT ? OFFSET ?'; params.extend([limit, offset])
        with self._conn() as c:
            return [dict(row) for row in c.execute(query, params).fetchall()]

    def get_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.search(category=category, limit=limit)

    def get_stats(self) -> Dict[str, Any]:
        with self._conn() as c:
            total = c.execute('SELECT COUNT(*) FROM brand_knowledge').fetchone()[0]
            by_category = {}
            for cat in CATEGORIES:
                cnt = c.execute('SELECT COUNT(*) FROM brand_knowledge WHERE category = ?', (cat,)).fetchone()[0]
                if cnt > 0: by_category[CATEGORIES[cat]] = cnt
            return {'total': total, 'by_category': by_category, 'categories': CATEGORIES}

    def export_to_json(self, filepath: str = KNOWLEDGE_JSON) -> Dict[str, Any]:
        all_knowledge = self.search(limit=10000)
        data = {'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'stats': self.get_stats(), 'knowledge': all_knowledge}
        parent = os.path.dirname(os.path.abspath(filepath))
        if parent: os.makedirs(parent, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        return {'ok': True, 'filepath': filepath, 'count': len(all_knowledge)}

    def batch_import(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        success = duplicates = failed = 0
        for item in items:
            result = self.add_knowledge(category=item.get('category',''), title=item.get('title',''), content=item.get('content',''),
                                        source=item.get('source',''), url=item.get('url',''), tags=item.get('tags',[]),
                                        relevance_score=item.get('relevance_score',0.5))
            if result.get('ok'): duplicates += bool(result.get('duplicate')); success += not result.get('duplicate')
            else: failed += 1
        return {'success': success, 'duplicates': duplicates, 'failed': failed, 'total': len(items)}


_kb_instance: Optional[BrandKnowledgeBase] = None

def get_knowledge_base() -> BrandKnowledgeBase:
    global _kb_instance
    if _kb_instance is None: _kb_instance = BrandKnowledgeBase()
    return _kb_instance
