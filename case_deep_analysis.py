"""案例深度拆解模块（ZBMP / 品牌智能层）。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import DB_PATH


class CaseDeepAnalysis:
    """对案例做结构化深度拆解并持久化；数据库路径由统一数据层管理。"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_table()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS case_deep_analysis(
                id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT UNIQUE NOT NULL, case_title TEXT NOT NULL,
                brand TEXT DEFAULT '', agency TEXT DEFAULT '', industry TEXT DEFAULT '', year INTEGER DEFAULT 0,
                case_type TEXT DEFAULT '', basic_info TEXT DEFAULT '{}', challenge TEXT DEFAULT '', strategy TEXT DEFAULT '{}',
                big_idea TEXT DEFAULT '', execution TEXT DEFAULT '[]', channels TEXT DEFAULT '[]', results TEXT DEFAULT '{}',
                awards TEXT DEFAULT '[]', success_factors TEXT DEFAULT '[]', methodology TEXT DEFAULT '[]',
                system_insights TEXT DEFAULT '[]', quality_score REAL DEFAULT 0, created_at TEXT, updated_at TEXT)""")
            for idx, col in [('idx_cda_brand','brand'),('idx_cda_industry','industry'),('idx_cda_type','case_type'),('idx_cda_quality','quality_score')]:
                c.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON case_deep_analysis({col})")

    def add_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        case_id = case_data.get('case_id', '')
        if not case_id: return {'ok': False, 'error': 'case_id不能为空'}
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S'); quality_score = self._calc_quality_score(case_data)
        values = (case_data.get('case_title',''), case_data.get('brand',''), case_data.get('agency',''), case_data.get('industry',''),
                  case_data.get('year',0), case_data.get('case_type',''), json.dumps(case_data.get('basic_info',{}),ensure_ascii=False),
                  case_data.get('challenge',''), json.dumps(case_data.get('strategy',{}),ensure_ascii=False), case_data.get('big_idea',''),
                  json.dumps(case_data.get('execution',[]),ensure_ascii=False), json.dumps(case_data.get('channels',[]),ensure_ascii=False),
                  json.dumps(case_data.get('results',{}),ensure_ascii=False), json.dumps(case_data.get('awards',[]),ensure_ascii=False),
                  json.dumps(case_data.get('success_factors',[]),ensure_ascii=False), json.dumps(case_data.get('methodology',[]),ensure_ascii=False),
                  json.dumps(case_data.get('system_insights',[]),ensure_ascii=False), quality_score, now, case_id)
        try:
            with self._conn() as c:
                existing = c.execute('SELECT id FROM case_deep_analysis WHERE case_id = ?', (case_id,)).fetchone()
                if existing:
                    c.execute("""UPDATE case_deep_analysis SET case_title=?,brand=?,agency=?,industry=?,year=?,case_type=?,basic_info=?,challenge=?,strategy=?,big_idea=?,execution=?,channels=?,results=?,awards=?,success_factors=?,methodology=?,system_insights=?,quality_score=?,updated_at=? WHERE case_id=?""", values)
                    return {'ok': True, 'case_id': case_id, 'updated': True, 'quality_score': quality_score}
                c.execute("""INSERT INTO case_deep_analysis(case_title,brand,agency,industry,year,case_type,basic_info,challenge,strategy,big_idea,execution,channels,results,awards,success_factors,methodology,system_insights,quality_score,created_at,updated_at,case_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", values[:-1] + (values[-2], values[-2], case_id))
                return {'ok': True, 'case_id': case_id, 'created': True, 'quality_score': quality_score}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def _calc_quality_score(self, case_data: Dict[str, Any]) -> float:
        score = sum(4 for f in ['case_title','brand','agency','industry','year'] if case_data.get(f))
        score += sum(10 for f in ['challenge','big_idea','execution','results','success_factors'] if case_data.get(f))
        score += 15 if case_data.get('methodology') else 0
        score += 15 if case_data.get('system_insights') else 0
        return min(score, 100)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            row = c.execute('SELECT * FROM case_deep_analysis WHERE case_id = ?', (case_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def list_cases(self, case_type: str = '', brand: str = '', industry: str = '', min_quality: float = 0,
                   min_quality_score: float = 0, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        query='SELECT * FROM case_deep_analysis WHERE 1=1'; params=[]
        if case_type: query += ' AND case_type = ?'; params.append(case_type)
        if brand: query += ' AND brand LIKE ?'; params.append(f'%{brand}%')
        if industry: query += ' AND industry LIKE ?'; params.append(f'%{industry}%')
        quality = min_quality_score if min_quality_score > 0 else min_quality
        if quality > 0: query += ' AND quality_score >= ?'; params.append(quality)
        query += ' ORDER BY quality_score DESC, created_at DESC LIMIT ? OFFSET ?'; params.extend([limit,offset])
        with self._conn() as c: return [self._row_to_dict(r) for r in c.execute(query,params).fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        with self._conn() as c:
            total=c.execute('SELECT COUNT(*) FROM case_deep_analysis').fetchone()[0]
            by_type={r['case_type']:r['cnt'] for r in c.execute('SELECT case_type,COUNT(*) cnt FROM case_deep_analysis GROUP BY case_type')}
            by_industry={r['industry']:r['cnt'] for r in c.execute('SELECT industry,COUNT(*) cnt FROM case_deep_analysis GROUP BY industry')}
            avg=c.execute('SELECT AVG(quality_score) FROM case_deep_analysis').fetchone()[0] or 0
            return {'total':total,'by_type':by_type,'by_industry':by_industry,'avg_quality':round(avg,1)}

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data=dict(row)
        for field in ['basic_info','strategy','execution','channels','results','awards','success_factors','methodology','system_insights']:
            if data.get(field):
                try: data[field]=json.loads(data[field])
                except Exception: pass
        return data

    def search_cases(self, keyword: str) -> List[Dict[str, Any]]:
        keyword=keyword.lower(); results=[]
        for case in self.list_cases(limit=1000):
            text=' '.join(str(case.get(f,'')) for f in ['case_title','brand','industry','big_idea','challenge','strategy']).lower()
            if keyword in text: results.append(case)
        return results

    def get_all_methodologies(self) -> List[Dict[str, Any]]:
        return [{'case_id':c.get('case_id'),'case_title':c.get('case_title'),'brand':c.get('brand'),'methodology':m}
                for c in self.list_cases(limit=1000) for m in c.get('methodology',[])]

    def get_all_system_insights(self) -> List[Dict[str, Any]]:
        return [{'case_id':c.get('case_id'),'case_title':c.get('case_title'),'brand':c.get('brand'),'insight':i}
                for c in self.list_cases(limit=1000) for i in c.get('system_insights',[])]

    def export_to_json(self, filepath: str) -> bool:
        try:
            with open(filepath,'w',encoding='utf-8') as f: json.dump({'cases':self.list_cases(limit=1000),'stats':self.get_stats()},f,ensure_ascii=False,indent=2)
            return True
        except Exception: return False


_analysis_instance: Optional[CaseDeepAnalysis] = None

def get_case_analysis() -> CaseDeepAnalysis:
    global _analysis_instance
    if _analysis_instance is None: _analysis_instance=CaseDeepAnalysis()
    return _analysis_instance
