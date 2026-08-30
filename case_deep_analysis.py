"""
案例深度拆解模块（V3.0 影子板块 - 案例学习库）
归属：Z-Brand Core / ZBMP / 品牌智能层
目标：
  1. 对品牌营销、整合传播、危机公关、商业地产案例进行11维结构化深度拆解
  2. 将案例从"故事"转化为"可复用的方法论"
  3. 建立案例-系统功能映射，指导产品迭代
  4. 为AI策略生成提供高质量案例参考

11维拆解框架：
  1. 案例基本信息（品牌、代理、时间、行业、背景）
  2. 核心问题/挑战
  3. 策略目标
  4. 核心创意 Big Idea
  5. 执行细节（分阶段）
  6. 传播渠道整合
  7. 数据成果
  8. 获奖情况
  9. 成功要素分析（带权重）
  10. 可复用方法论
  11. 对Z-Brand系统的启示
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


DB_PATH = r'D:\Taikoo-monitor-new\data\monitor.db'


class CaseDeepAnalysis:
    """案例深度拆解"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_table()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        """确保案例深度拆解表存在"""
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS case_deep_analysis(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT UNIQUE NOT NULL,
                    case_title TEXT NOT NULL,
                    brand TEXT DEFAULT '',
                    agency TEXT DEFAULT '',
                    industry TEXT DEFAULT '',
                    year INTEGER DEFAULT 0,
                    case_type TEXT DEFAULT '',
                    basic_info TEXT DEFAULT '{}',
                    challenge TEXT DEFAULT '',
                    strategy TEXT DEFAULT '{}',
                    big_idea TEXT DEFAULT '',
                    execution TEXT DEFAULT '[]',
                    channels TEXT DEFAULT '[]',
                    results TEXT DEFAULT '{}',
                    awards TEXT DEFAULT '[]',
                    success_factors TEXT DEFAULT '[]',
                    methodology TEXT DEFAULT '[]',
                    system_insights TEXT DEFAULT '[]',
                    quality_score REAL DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_cda_brand ON case_deep_analysis(brand)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_cda_industry ON case_deep_analysis(industry)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_cda_type ON case_deep_analysis(case_type)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_cda_quality ON case_deep_analysis(quality_score)")

    def add_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加一个深度拆解案例"""
        case_id = case_data.get('case_id', '')
        if not case_id:
            return {'ok': False, 'error': 'case_id不能为空'}

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 计算质量分（基于拆解完整度）
        quality_score = self._calc_quality_score(case_data)

        try:
            with self._conn() as c:
                existing = c.execute('SELECT id FROM case_deep_analysis WHERE case_id = ?', (case_id,)).fetchone()
                if existing:
                    # 更新
                    c.execute("""
                        UPDATE case_deep_analysis SET
                            case_title=?, brand=?, agency=?, industry=?, year=?, case_type=?,
                            basic_info=?, challenge=?, strategy=?, big_idea=?, execution=?,
                            channels=?, results=?, awards=?, success_factors=?, methodology=?,
                            system_insights=?, quality_score=?, updated_at=?
                        WHERE case_id=?
                    """, (
                        case_data.get('case_title', ''),
                        case_data.get('brand', ''),
                        case_data.get('agency', ''),
                        case_data.get('industry', ''),
                        case_data.get('year', 0),
                        case_data.get('case_type', ''),
                        json.dumps(case_data.get('basic_info', {}), ensure_ascii=False),
                        case_data.get('challenge', ''),
                        json.dumps(case_data.get('strategy', {}), ensure_ascii=False),
                        case_data.get('big_idea', ''),
                        json.dumps(case_data.get('execution', []), ensure_ascii=False),
                        json.dumps(case_data.get('channels', []), ensure_ascii=False),
                        json.dumps(case_data.get('results', {}), ensure_ascii=False),
                        json.dumps(case_data.get('awards', []), ensure_ascii=False),
                        json.dumps(case_data.get('success_factors', []), ensure_ascii=False),
                        json.dumps(case_data.get('methodology', []), ensure_ascii=False),
                        json.dumps(case_data.get('system_insights', []), ensure_ascii=False),
                        quality_score,
                        now,
                        case_id,
                    ))
                    return {'ok': True, 'case_id': case_id, 'updated': True, 'quality_score': quality_score}
                else:
                    # 新增
                    c.execute("""
                        INSERT INTO case_deep_analysis(
                            case_id, case_title, brand, agency, industry, year, case_type,
                            basic_info, challenge, strategy, big_idea, execution, channels,
                            results, awards, success_factors, methodology, system_insights,
                            quality_score, created_at, updated_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        case_id,
                        case_data.get('case_title', ''),
                        case_data.get('brand', ''),
                        case_data.get('agency', ''),
                        case_data.get('industry', ''),
                        case_data.get('year', 0),
                        case_data.get('case_type', ''),
                        json.dumps(case_data.get('basic_info', {}), ensure_ascii=False),
                        case_data.get('challenge', ''),
                        json.dumps(case_data.get('strategy', {}), ensure_ascii=False),
                        case_data.get('big_idea', ''),
                        json.dumps(case_data.get('execution', []), ensure_ascii=False),
                        json.dumps(case_data.get('channels', []), ensure_ascii=False),
                        json.dumps(case_data.get('results', {}), ensure_ascii=False),
                        json.dumps(case_data.get('awards', []), ensure_ascii=False),
                        json.dumps(case_data.get('success_factors', []), ensure_ascii=False),
                        json.dumps(case_data.get('methodology', []), ensure_ascii=False),
                        json.dumps(case_data.get('system_insights', []), ensure_ascii=False),
                        quality_score,
                        now,
                        now,
                    ))
                    return {'ok': True, 'case_id': case_id, 'created': True, 'quality_score': quality_score}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def _calc_quality_score(self, case_data: Dict[str, Any]) -> float:
        """计算案例拆解质量分（0-100）"""
        score = 0
        # 基本信息完整度（20分）
        basic_fields = ['case_title', 'brand', 'agency', 'industry', 'year']
        score += sum(4 for f in basic_fields if case_data.get(f))
        # 核心内容完整度（50分）
        core_fields = ['challenge', 'big_idea', 'execution', 'results', 'success_factors']
        score += sum(10 for f in core_fields if case_data.get(f))
        # 方法论和启示（30分）
        if case_data.get('methodology'):
            score += 15
        if case_data.get('system_insights'):
            score += 15
        return min(score, 100)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """获取单个案例详情"""
        with self._conn() as c:
            row = c.execute('SELECT * FROM case_deep_analysis WHERE case_id = ?', (case_id,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def list_cases(self, case_type: str = '', brand: str = '', industry: str = '',
                    min_quality: float = 0, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取案例列表（支持筛选）"""
        query = 'SELECT * FROM case_deep_analysis WHERE 1=1'
        params = []
        if case_type:
            query += ' AND case_type = ?'
            params.append(case_type)
        if brand:
            query += ' AND brand LIKE ?'
            params.append(f'%{brand}%')
        if industry:
            query += ' AND industry LIKE ?'
            params.append(f'%{industry}%')
        if min_quality > 0:
            query += ' AND quality_score >= ?'
            params.append(min_quality)
        query += ' ORDER BY quality_score DESC, created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        with self._conn() as c:
            rows = c.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_stats(self) -> Dict[str, Any]:
        """获取案例库统计"""
        with self._conn() as c:
            total = c.execute('SELECT COUNT(*) FROM case_deep_analysis').fetchone()[0]
            by_type = {}
            for row in c.execute('SELECT case_type, COUNT(*) as cnt FROM case_deep_analysis GROUP BY case_type'):
                by_type[row['case_type']] = row['cnt']
            by_industry = {}
            for row in c.execute('SELECT industry, COUNT(*) as cnt FROM case_deep_analysis GROUP BY industry'):
                by_industry[row['industry']] = row['cnt']
            avg_quality = c.execute('SELECT AVG(quality_score) FROM case_deep_analysis').fetchone()[0] or 0
            return {
                'total': total,
                'by_type': by_type,
                'by_industry': by_industry,
                'avg_quality': round(avg_quality, 1),
            }

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典（解析JSON字段）"""
        data = dict(row)
        json_fields = ['basic_info', 'strategy', 'execution', 'channels', 'results',
                       'awards', 'success_factors', 'methodology', 'system_insights']
        for field in json_fields:
            if data.get(field):
                try:
                    data[field] = json.loads(data[field])
                except Exception:
                    pass
        return data

    def export_to_json(self, filepath: str) -> bool:
        """导出全部案例为JSON"""
        try:
            cases = self.list_cases(limit=1000)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({'cases': cases, 'stats': self.get_stats()}, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False


# 全局单例
_analysis_instance: Optional[CaseDeepAnalysis] = None

def get_case_analysis() -> CaseDeepAnalysis:
    global _analysis_instance
    if _analysis_instance is None:
        _analysis_instance = CaseDeepAnalysis()
    return _analysis_instance
