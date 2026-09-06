# -*- coding: utf-8 -*-
"""幂等迁移：notes 表时间字段规范化回填。

规范字段：publish_datetime（发布时间）+ collected_at（采集时间）
冗余字段：publish_date + captured_at（保留，不删除）

规则（只补空，不覆盖已有值）：
  1. publish_datetime 为空 且 publish_date 非空  → publish_datetime = publish_date
  2. publish_date 为空 且 publish_datetime 非空  → publish_date = publish_datetime
  3. collected_at 为空 且 captured_at 非空     → collected_at = captured_at
  4. captured_at 为空 且 collected_at 非空     → captured_at = collected_at
"""
import os
import sqlite3

DB_PATH = os.environ.get("ZBC_DB_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "monitor.db"
)


def _is_empty(v):
    return v is None or str(v).strip() == ""


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT id, note_id, publish_datetime, publish_date, collected_at, captured_at FROM notes").fetchall()
        print(f"总记录数: {len(rows)}")
        stats = {"pub_dt_filled": 0, "pub_date_filled": 0, "coll_at_filled": 0, "capt_at_filled": 0, "skipped": 0}

        for r in rows:
            rid = r["id"]
            pub_dt = r["publish_datetime"]
            pub_date = r["publish_date"]
            coll_at = r["collected_at"]
            capt_at = r["captured_at"]
            changes = []

            # 1. publish_datetime 空 ← publish_date
            if _is_empty(pub_dt) and not _is_empty(pub_date):
                conn.execute("UPDATE notes SET publish_datetime=? WHERE id=?", (pub_date, rid))
                changes.append(f"publish_datetime←{pub_date}")
                stats["pub_dt_filled"] += 1

            # 2. publish_date 空 ← publish_datetime
            elif _is_empty(pub_date) and not _is_empty(pub_dt):
                conn.execute("UPDATE notes SET publish_date=? WHERE id=?", (pub_dt, rid))
                changes.append(f"publish_date←{pub_dt}")
                stats["pub_date_filled"] += 1

            # 3. collected_at 空 ← captured_at
            if _is_empty(coll_at) and not _is_empty(capt_at):
                conn.execute("UPDATE notes SET collected_at=? WHERE id=?", (capt_at, rid))
                changes.append(f"collected_at←{capt_at}")
                stats["coll_at_filled"] += 1

            # 4. captured_at 空 ← collected_at
            elif _is_empty(capt_at) and not _is_empty(coll_at):
                conn.execute("UPDATE notes SET captured_at=? WHERE id=?", (coll_at, rid))
                changes.append(f"captured_at←{coll_at}")
                stats["capt_at_filled"] += 1

            if changes:
                print(f"  id={rid} note_id={r['note_id']}: {', '.join(changes)}")
            else:
                stats["skipped"] += 1

        conn.commit()

        # 验证
        print("\n--- 迁移后验证 ---")
        rows2 = conn.execute("SELECT id, note_id, publish_datetime, publish_date, collected_at, captured_at FROM notes").fetchall()
        pub_dt_nonempty = sum(1 for r in rows2 if not _is_empty(r["publish_datetime"]))
        coll_at_nonempty = sum(1 for r in rows2 if not _is_empty(r["collected_at"]))
        pub_date_nonempty = sum(1 for r in rows2 if not _is_empty(r["publish_date"]))
        capt_at_nonempty = sum(1 for r in rows2 if not _is_empty(r["captured_at"]))
        print(f"publish_datetime 非空: {pub_dt_nonempty}/{len(rows2)}")
        print(f"publish_date 非空:     {pub_date_nonempty}/{len(rows2)}")
        print(f"collected_at 非空:     {coll_at_nonempty}/{len(rows2)}")
        print(f"captured_at 非空:      {capt_at_nonempty}/{len(rows2)}")
        print(f"\n回填统计: {stats}")

        for r in rows2:
            print(f"  id={r['id']} pub_dt={r['publish_datetime']!r} pub_date={r['publish_date']!r} coll_at={r['collected_at']!r} capt_at={r['captured_at']!r}")

    finally:
        conn.close()


if __name__ == "__main__":
    run()
