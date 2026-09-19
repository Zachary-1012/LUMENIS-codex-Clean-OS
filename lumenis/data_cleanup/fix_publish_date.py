"""
数据清洗脚本
1. 修复 publish_date 相对时间（"编辑于 2025-08-22"、"编辑于 06-02"、"昨天 23:39"、"5小时前"等）为标准 YYYY-MM-DD
2. 标记空正文笔记，生成补抓任务清单
3. 可独立运行，不影响系统运行

口径约束：只规范 publish_date（发布时间），绝不改动 captured_at/collected_at（采集时间），二者不混淆。
基准时间优先 captured_at（新规范列），回退 collected_at（旧列），再回退当前时间。
用法:
  python -m lumenis.data_cleanup.fix_publish_date        # dry run 只预览
  python -m lumenis.data_cleanup.fix_publish_date --apply # 真正写库
"""
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from lumenis.shared.database import get_repository


# 相对时间正则（顺序敏感：先匹配更具体的）
RELATIVE_PATTERNS = [
    (r"前天", "day_before_yesterday"),
    (r"昨天|昨日", "yesterday"),
    (r"今天|今日|刚刚", "today"),
    (r"(\d+)\s*分钟前", "minutes"),
    (r"(\d+)\s*小时前", "hours"),
    (r"(\d+)\s*天前", "days"),
    (r"(\d+)\s*周前", "weeks"),
    (r"编辑于\s*(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", "edit_date"),
    (r"编辑于\s*(\d{1,2})[-/月](\d{1,2})", "edit_month_day"),
]

_STD = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _base_dt(captured_at=None, collected_at=None) -> datetime:
    """归一化基准时间：captured_at 优先，回退 collected_at，再回退 now。"""
    for val in (captured_at, collected_at):
        if not val:
            continue
        s = val.strip().replace("T", " ")[:19]
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    return datetime.now()


def parse_relative_date(raw: str, captured_at: str = None, collected_at: str = None) -> str:
    """把相对/残缺发布时间解析为标准 YYYY-MM-DD；无法解析时原样返回（不臆造）。"""
    if not raw:
        return raw
    raw = raw.strip()
    if _STD.match(raw):
        return raw[:10]

    now = _base_dt(captured_at, collected_at)

    for pattern, ptype in RELATIVE_PATTERNS:
        m = re.search(pattern, raw)
        if not m:
            continue
        if ptype == "day_before_yesterday":
            return (now - timedelta(days=2)).strftime("%Y-%m-%d")
        if ptype == "yesterday":
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")
        if ptype == "today":
            return now.strftime("%Y-%m-%d")
        if ptype == "minutes":
            return (now - timedelta(minutes=int(m.group(1)))).strftime("%Y-%m-%d")
        if ptype == "hours":
            return (now - timedelta(hours=int(m.group(1)))).strftime("%Y-%m-%d")
        if ptype == "days":
            return (now - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
        if ptype == "weeks":
            return (now - timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")
        if ptype == "edit_date":
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        if ptype == "edit_month_day":
            # 只有月日，用基准年份；若该月日晚于基准日期（跨年情形，如基准1月、显示12-25），则取上一年
            month, day = int(m.group(1)), int(m.group(2))
            year = now.year
            try:
                cand = datetime(year, month, day)
                if cand.date() > now.date():
                    cand = datetime(year - 1, month, day)
                return cand.strftime("%Y-%m-%d")
            except ValueError:
                return raw  # 非法月日不臆造
    return raw


def fix_publish_dates(dry_run: bool = True) -> dict:
    """修复发布时间脏数据，publish_date 与 publish_datetime 双列保持一致。

    - publish_date 为相对/残缺时间时解析为标准 YYYY-MM-DD；
    - publish_datetime 若残留“编辑于/昨天/小时前”等脏原文，用同一标准日期同步，避免双列不一致；
    - 只规范发布时间，绝不改 captured_at/collected_at（采集时间）。dry_run=True 只预览。
    """
    conn = get_repository().connect()
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT id, publish_date, publish_datetime, captured_at, collected_at FROM notes "
            "WHERE (publish_date IS NOT NULL AND TRIM(publish_date) <> '') "
            "OR (publish_datetime IS NOT NULL AND TRIM(publish_datetime) <> '')"
        )
        rows = cur.fetchall()
        fixed = []
        for row in rows:
            sets = {}
            pdate = (row["publish_date"] or "").strip()
            pdt = (row["publish_datetime"] or "").strip()
            # 标准发布日期：优先已干净的 publish_date，否则解析相对时间（基准 captured→collected→now）
            if pdate and _STD.match(pdate):
                std = pdate[:10]
            else:
                parsed = parse_relative_date(pdate, row["captured_at"], row["collected_at"])
                std = parsed[:10] if parsed and _STD.match(parsed) else None
                if std and pdate and not _STD.match(pdate):
                    sets["publish_date"] = std
            # datetime 列脏、但能得到标准日期时同步（多数行两列同为日期粒度，保持一致）
            if std and pdt and not _STD.match(pdt):
                sets["publish_datetime"] = std
            if sets:
                fixed.append({"id": row["id"], "sets": sets, "raw_date": pdate, "raw_dt": pdt})
                if not dry_run:
                    cols = ", ".join(f"{k}=?" for k in sets)
                    conn.execute(f"UPDATE notes SET {cols} WHERE id=?",
                                 list(sets.values()) + [row["id"]])
        if not dry_run:
            conn.commit()
        return {
            "total_checked": len(rows),
            "fixed_count": len(fixed),
            "fixed": fixed if dry_run else [f["id"] for f in fixed],
            "dry_run": dry_run,
        }
    finally:
        conn.close()


def backfill_captured_from_collected(dry_run: bool = True) -> dict:
    """老数据新规范列 captured_at 为空串/NULL、而旧采集列 collected_at 有值时回填。

    语义：collected_at 本就是历史采集时刻，回填到 captured_at 仅为补齐“采集时间”列，
    绝不触碰任何发布时间列，不混淆 publish 与 captured。
    """
    conn = get_repository().connect()
    try:
        where = ("(captured_at IS NULL OR TRIM(captured_at)='') "
                 "AND collected_at IS NOT NULL AND TRIM(collected_at)<>''")
        n = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {where}").fetchone()[0]
        if not dry_run and n:
            conn.execute(f"UPDATE notes SET captured_at=collected_at WHERE {where}")
            conn.commit()
        return {"backfill_count": n, "dry_run": dry_run}
    finally:
        conn.close()


def find_empty_content_notes() -> dict:
    """查找空正文笔记，生成补抓清单（不写库）。"""
    conn = get_repository().connect()
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("""
            SELECT id, note_id, title, url, xsec_token, source_platform, captured_at, collected_at
            FROM notes
            WHERE content IS NULL OR content = '' OR content = '正文尚未抓取'
            ORDER BY captured_at DESC
        """)
        notes = [dict(row) for row in cur.fetchall()]
        by_platform = {}
        for n in notes:
            p = n.get("source_platform") or "unknown"
            by_platform[p] = by_platform.get(p, 0) + 1
        return {"total": len(notes), "by_platform": by_platform, "notes": notes,
                "backfill_script_hint": "使用 CDP 进详情页分批补抓，每批10条，遇300012人工过验证"}
    finally:
        conn.close()


def generate_backfill_tasks(batch_size: int = 10) -> dict:
    result = find_empty_content_notes()
    notes = result["notes"]
    batches = []
    for i in range(0, len(notes), batch_size):
        batch = notes[i:i + batch_size]
        batches.append({"batch_id": i // batch_size + 1, "count": len(batch),
                        "tasks": [{"note_id": n["note_id"], "url": n["url"],
                                   "xsec_token": n.get("xsec_token")} for n in batch]})
    return {"total_notes": len(notes), "batch_size": batch_size,
            "total_batches": len(batches), "batches": batches}


if __name__ == "__main__":
    import json
    mode_apply = "--apply" in sys.argv
    print("=== 发布时间清洗 publish_date/publish_datetime（%s）===" % ("APPLY 写库" if mode_apply else "dry run 预览"))
    result = fix_publish_dates(dry_run=not mode_apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n=== 采集时间回填 captured_at<-collected_at（%s）===" % ("APPLY 写库" if mode_apply else "dry run 预览"))
    print(json.dumps(backfill_captured_from_collected(dry_run=not mode_apply), ensure_ascii=False, indent=2))
    print("\n=== 空正文笔记统计 ===")
    empty = find_empty_content_notes()
    print(f"总数: {empty['total']}  按平台: {empty['by_platform']}")
