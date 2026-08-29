"""
数据清洗脚本
1. 修复 publish_date 相对时间（"编辑于 2025-0x"、"小时前"、"分钟前"等）
2. 标记197条空正文笔记，生成补抓任务清单
3. 可独立运行，不影响系统运行
用法: python -m v4_upgrade.data_cleanup.fix_publish_date
"""
import re
import sqlite3
import time
from datetime import datetime, timedelta
from ..config import DB_PATH


# 相对时间正则
RELATIVE_PATTERNS = [
    (r"(\d+)\s*分钟前", "minutes"),
    (r"(\d+)\s*小时前", "hours"),
    (r"(\d+)\s*天前", "days"),
    (r"(\d+)\s*周前", "weeks"),
    (r"刚刚", "just_now"),
    (r"编辑于\s*(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", "edit_date"),
    (r"编辑于\s*(\d{1,2})[-/月](\d{1,2})", "edit_month_day"),
]


def parse_relative_date(raw: str, collected_at: str = None) -> str:
    """
    解析相对时间为标准 YYYY-MM-DD
    返回标准日期字符串，解析失败返回原字符串
    """
    if not raw:
        return raw
    raw = raw.strip()

    # 已经是标准格式
    if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]

    now = datetime.now()
    if collected_at:
        try:
            now = datetime.strptime(collected_at[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    for pattern, ptype in RELATIVE_PATTERNS:
        m = re.search(pattern, raw)
        if not m:
            continue
        if ptype == "minutes":
            dt = now - timedelta(minutes=int(m.group(1)))
            return dt.strftime("%Y-%m-%d")
        elif ptype == "hours":
            dt = now - timedelta(hours=int(m.group(1)))
            return dt.strftime("%Y-%m-%d")
        elif ptype == "days":
            dt = now - timedelta(days=int(m.group(1)))
            return dt.strftime("%Y-%m-%d")
        elif ptype == "weeks":
            dt = now - timedelta(weeks=int(m.group(1)))
            return dt.strftime("%Y-%m-%d")
        elif ptype == "just_now":
            return now.strftime("%Y-%m-%d")
        elif ptype == "edit_date":
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        elif ptype == "edit_month_day":
            return f"{now.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    return raw


def fix_publish_dates(dry_run: bool = True) -> dict:
    """
    修复所有 publish_date 脏数据
    dry_run=True 只统计不修改
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT id, publish_date, collected_at FROM notes WHERE publish_date IS NOT NULL"
        )
        rows = cur.fetchall()
        dirty = []
        fixed = []
        for row in rows:
            raw = row["publish_date"]
            parsed = parse_relative_date(raw, row["collected_at"])
            if parsed != raw:
                dirty.append({"id": row["id"], "raw": raw, "parsed": parsed})
                if not dry_run:
                    conn.execute(
                        "UPDATE notes SET publish_date=? WHERE id=?",
                        (parsed, row["id"])
                    )
        if not dry_run:
            conn.commit()
        return {
            "total_checked": len(rows),
            "dirty_count": len(dirty),
            "fixed": dirty if dry_run else [d["id"] for d in dirty],
            "dry_run": dry_run,
        }
    finally:
        conn.close()


def find_empty_content_notes() -> dict:
    """查找空正文笔记，生成补抓清单"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("""
            SELECT id, note_id, title, url, xsec_token, source_platform, collected_at
            FROM notes
            WHERE content IS NULL OR content = '' OR content = '正文尚未抓取'
            ORDER BY collected_at DESC
        """)
        notes = [dict(row) for row in cur.fetchall()]
        # 按平台分组
        by_platform = {}
        for n in notes:
            p = n.get("source_platform") or "unknown"
            by_platform[p] = by_platform.get(p, 0) + 1
        return {
            "total": len(notes),
            "by_platform": by_platform,
            "notes": notes,
            "backfill_script_hint": "使用 CDP 进详情页分批补抓，每批10条，遇300012人工过验证",
        }
    finally:
        conn.close()


def generate_backfill_tasks(batch_size: int = 10) -> dict:
    """
    生成补抓任务清单（分批）
    返回批次列表，每批包含note_id和url
    """
    result = find_empty_content_notes()
    notes = result["notes"]
    batches = []
    for i in range(0, len(notes), batch_size):
        batch = notes[i:i + batch_size]
        batches.append({
            "batch_id": i // batch_size + 1,
            "count": len(batch),
            "tasks": [{"note_id": n["note_id"], "url": n["url"], "xsec_token": n.get("xsec_token")} for n in batch],
        })
    return {
        "total_notes": len(notes),
        "batch_size": batch_size,
        "total_batches": len(batches),
        "batches": batches,
    }


if __name__ == "__main__":
    import json
    print("=== publish_date 清洗（dry run）===")
    result = fix_publish_dates(dry_run=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n=== 空正文笔记统计 ===")
    empty = find_empty_content_notes()
    print(f"总数: {empty['total']}")
    print(f"按平台: {empty['by_platform']}")

    print("\n=== 补抓任务批次（前3批）===")
    tasks = generate_backfill_tasks()
    print(f"总批次数: {tasks['total_batches']}")
    for b in tasks["batches"][:3]:
        print(f"  批次{b['batch_id']}: {b['count']}条")
