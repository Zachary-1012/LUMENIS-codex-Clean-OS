# -*- coding: utf-8 -*-
"""
品牌业态统计重算模块
------------------------------------------------------------------
作用：brand_industry_monitor 表内的 note_count/positive_count/negative_count/
total_engagement/risk_level 是预聚合字段，历史上曾出现整库笔记被错误归到单个
品牌（如某品牌 note_count=667≈全库）的污染。本模块用与「单品牌详情」接口
(/api/brand-industry/brands/<name>) 完全一致的实时 LIKE 口径，批量重算全部品牌，
保证列表/业态卡片/品牌详情三处数字一致、可信。

可独立运行：  python brand_stats_recompute.py
也可被 app.py 调用：from brand_stats_recompute import recompute_brand_stats
"""
import os
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, 'data', 'monitor.db')

# 笔记中用于匹配品牌名的文本列（与单品牌详情接口保持一致）
_MATCH_COLS = ('title', 'content', 'summary', 'body')
# 互动量列
_ENGAGE_COLS = ('likes', 'comments', 'collects', 'shares')


def _to_int(v):
    """安全转整数，空值/非数字一律按 0 处理"""
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _brand_keys(cn, en):
    """品牌匹配关键词：中文名必用；英文名长度>=3 才用，避免单字母误匹配（与详情接口一致）"""
    keys = [k.strip() for k in [cn] if k and k.strip()]
    en = (en or '').strip()
    if len(en) >= 3:
        keys.append(en)
    return keys


def recompute_brand_stats(db_path=DB_PATH, verbose=True):
    """按实时 LIKE 口径重算全部品牌的预聚合统计。
    返回 {updated, nonzero, negative_brands, positive_brands, samples}"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    brands = [dict(r) for r in conn.execute(
        "SELECT id, brand_name, brand_name_cn FROM brand_industry_monitor").fetchall()]

    updated = 0
    nonzero = 0
    neg_brand_ids = set()
    pos_brand_ids = set()
    samples = []

    for b in brands:
        keys = _brand_keys(b.get('brand_name_cn', ''), b.get('brand_name', ''))
        if not keys:
            # 无可用中文名、英文名过短：统计清零，避免残留污染
            conn.execute("UPDATE brand_industry_monitor SET note_count=0, positive_count=0, "
                         "negative_count=0, total_engagement=0, risk_level='none', last_updated=datetime('now','localtime') "
                         "WHERE id=?", (b['id'],))
            updated += 1
            continue

        where = " OR ".join(["(" + " OR ".join([f"{col} LIKE ?" for col in _MATCH_COLS]) + ")"
                             for _ in keys])
        params = []
        for k in keys:
            params += [f"%{k}%"] * len(_MATCH_COLS)
        rows = conn.execute(
            f"SELECT sentiment, risk_level, likes, comments, collects, shares FROM notes WHERE {where}",
            params).fetchall()

        total = len(rows)
        pos = sum(1 for r in rows if r['sentiment'] == 'positive')
        neg = sum(1 for r in rows if r['sentiment'] == 'negative')
        engagement = sum(sum(_to_int(r[c]) for c in _ENGAGE_COLS) for r in rows)

        # 风险等级取该品牌匹配笔记中的最高级
        risk = 'none'
        rlevels = [r['risk_level'] for r in rows]
        if neg and any(x == 'high' for x in rlevels):
            risk = 'high'
        elif neg:
            risk = 'medium'
        elif total:
            risk = 'low'

        conn.execute(
            "UPDATE brand_industry_monitor SET note_count=?, positive_count=?, negative_count=?, "
            "total_engagement=?, risk_level=?, last_updated=datetime('now','localtime') WHERE id=?",
            (total, pos, neg, engagement, risk, b['id']))
        updated += 1
        if total:
            nonzero += 1
        if neg:
            neg_brand_ids.add(b['id'])
        if pos:
            pos_brand_ids.add(b['id'])
        if total and len(samples) < 12:
            samples.append((b.get('brand_name_cn') or b.get('brand_name'), total, pos, neg))

    conn.commit()
    conn.close()

    result = {'updated': updated, 'nonzero': nonzero,
              'negative_brands': len(neg_brand_ids), 'positive_brands': len(pos_brand_ids),
              'samples': samples}
    if verbose:
        print(f"[BrandStats] 重算完成：共 {updated} 个品牌，有笔记 {nonzero} 个，"
              f"负面品牌 {len(neg_brand_ids)}，正面品牌 {len(pos_brand_ids)}")
        for name, total, pos, neg in samples:
            print(f"   - {name}: 总{total} 正{pos} 负{neg}")
    return result


if __name__ == '__main__':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    recompute_brand_stats()
