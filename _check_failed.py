# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'D:\Taikoo-monitor-new\data\monitor.db')
cur = conn.cursor()
cur.execute("SELECT note_id, topic, title, evidence_quality, detail_captured_at FROM topic_campaign_notes WHERE evidence_quality != 'full' OR detail_captured_at IS NULL ORDER BY detail_captured_at ASC LIMIT 10")
rows = cur.fetchall()
print(f'非full笔记: {len(rows)}条')
for r in rows:
    print(f'  {r[0]} | {r[1]} | {str(r[2])[:30]} | {r[3]} | {r[4]}')
conn.close()
