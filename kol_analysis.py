# -*- coding: utf-8 -*-
"""KOL / KOC / UGC 分层分析（P1-C）。

链路：Account -> Note -> Interaction -> Event -> Evidence
  notes 表按 author 聚合 → 互动总量 / 笔记数 → 分层（KOL/KOC/UGC）→ 趋势事件 → 证据可追溯。

分层依据（小红书语境；followers 未持久化时不伪造，用已存互动+笔记数）：
  KOL  关键意见领袖：累计互动 >= KOL_MIN_INTERACTIONS 且笔记 >= KOL_MIN_NOTES
  KOC  关键意见消费者：互动 >= KOC_MIN_INTERACTIONS 且笔记 >= KOC_MIN_NOTES
  UGC  普通用户：其余

互动 = likes + comments + collects + shares（notes 表已存字段）。
纯函数 + 可注入连接，便于测试；不持有状态。
"""
KOL_MIN_INTERACTIONS = 10000
KOL_MIN_NOTES = 3
KOC_MIN_INTERACTIONS = 1000
KOC_MIN_NOTES = 1

LAYER_KOL = "KOL"
LAYER_KOC = "KOC"
LAYER_UGC = "UGC"


def classify_author(total_interactions: int, note_count: int):
    """按累计互动与笔记数给作者分层。返回 LAYER_KOL / LAYER_KOC / LAYER_UGC。"""
    total_interactions = int(total_interactions or 0)
    note_count = int(note_count or 0)
    if total_interactions >= KOL_MIN_INTERACTIONS and note_count >= KOL_MIN_NOTES:
        return LAYER_KOL
    if total_interactions >= KOC_MIN_INTERACTIONS and note_count >= KOC_MIN_NOTES:
        return LAYER_KOC
    return LAYER_UGC


def analyze_authors(rows):
    """rows: [(author_id, nickname, note_count, total_interactions), ...]
    返回每作者带分层 + 汇总。纯函数，不查库。"""
    result = []
    for author_id, nickname, note_count, total_interactions in rows:
        result.append({
            "author_id": author_id,
            "nickname": nickname or "",
            "note_count": int(note_count or 0),
            "total_interactions": int(total_interactions or 0),
            "layer": classify_author(total_interactions, note_count),
        })
    summary = {"KOL": 0, "KOC": 0, "UGC": 0}
    for r in result:
        summary[r["layer"]] += 1
    return {"authors": result, "summary": summary}


def top_authors(limit: int = 20, conn=None):
    """从 notes 表按作者聚合互动/笔记数，返回 top 分层作者（含分层）。"""
    own = conn is None
    if own:
        conn = database_get_db()
    try:
        cur = conn.execute(
            "SELECT author_id, author_nickname, COUNT(*) AS n, "
            "SUM(likes+comments+collects+shares) AS inter "
            "FROM notes WHERE author_id<>'' GROUP BY author_id "
            "ORDER BY inter DESC, n DESC LIMIT ?", (int(limit),))
        rows = [(r[0], r[1], r[2], r[3] or 0) for r in cur.fetchall()]
    finally:
        if own:
            try:
                conn.close()
            except Exception:
                pass
    return analyze_authors(rows)


def chain():
    """返回 Account→Note→Interaction→Event→Evidence 链路说明（结构化，供文档/前端）。"""
    return {
        "account": "author_id/author_nickname（notes 表）",
        "note": "作者发布笔记（note_id/title/publish_date）",
        "interaction": "likes+comments+collects+shares（互动总量）",
        "event": "按时间聚合的舆情/风险事件（与 events 表联动）",
        "evidence": "原始 notes 行可追溯（note_id/url 留存）",
    }


def database_get_db():
    import database
    return database.get_db()
