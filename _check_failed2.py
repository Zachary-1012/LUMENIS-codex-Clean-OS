# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'D:\Taikoo-monitor-new\data\monitor.db')
cur = conn.cursor()
cur.execute("SELECT note_id, topic, title, evidence_quality, detail_captured_at, content, media_json, comments_json FROM topic_campaign_notes WHERE evidence_quality = 'failed'")
rows = cur.fetchall()
print(f'failed笔记: {len(rows)}条')
for r in rows:
    print(f'  note_id: {r[0]}')
    print(f'  topic: {r[1]}')
    print(f'  title: {r[2]}')
    print(f'  content长度: {len(r[5]) if r[5] else 0}')
    print(f'  media_json: {r[6][:50] if r[6] else "空"}')
    print(f'  comments_json: {r[7][:50] if r[7] else "空"}')
    print()

# 统计各quality
cur.execute("SELECT evidence_quality, COUNT(*) FROM topic_campaign_notes GROUP BY evidence_quality")
print('各quality统计:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}条')
conn.close()
