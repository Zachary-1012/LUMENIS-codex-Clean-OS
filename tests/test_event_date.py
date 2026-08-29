# -*- coding: utf-8 -*-
"""事件发生日期(event_date)口径回归：迁移列、upsert 默认/不覆盖、API 输出与排序。"""
import sys, os, sqlite3, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask
import database as db

db.init_db()
EKEY = '__test_event_date__'

# 1) 新增事件：未显式给 event_date 时默认取 first_seen
eid = db.upsert_event({'event_key': EKEY, 'title': '【单测】发生日期事件', 'first_seen': '2026-05-01',
                       'last_seen': '2026-05-03', 'mention_count': 1, 'risk_level': 'low', 'keywords': ['测试']})
conn = sqlite3.connect(db.DB_PATH); conn.row_factory = sqlite3.Row
r = conn.execute('SELECT event_date,first_seen FROM events WHERE event_key=?', (EKEY,)).fetchone()
print('[新增默认] event_date =', r['event_date'], '(应=first_seen 2026-05-01)')
assert r['event_date'] == '2026-05-01'

# 2) 更新事件：已确定的发生日期不被覆盖
db.upsert_event({'event_key': EKEY, 'title': '【单测】发生日期事件改', 'first_seen': '2026-06-01',
                 'last_seen': '2026-06-02', 'mention_count': 2, 'risk_level': 'medium', 'keywords': ['测试']})
r = conn.execute('SELECT event_date FROM events WHERE event_key=?', (EKEY,)).fetchone()
print('[更新不覆盖] event_date =', r['event_date'], '(应仍为 2026-05-01)')
assert r['event_date'] == '2026-05-01'

# 3) 显式 event_date 的新事件按显式写入
EKEY2 = '__test_event_date_explicit__'
db.upsert_event({'event_key': EKEY2, 'title': '【单测】显式日期', 'first_seen': '2026-07-01',
                 'event_date': '2026-04-20', 'last_seen': '2026-07-02', 'keywords': []})
r = conn.execute('SELECT event_date FROM events WHERE event_key=?', (EKEY2,)).fetchone()
print('[显式优先] event_date =', r['event_date'], '(应=2026-04-20)')
assert r['event_date'] == '2026-04-20'

# 清理
for k in (EKEY, EKEY2):
    conn.execute('DELETE FROM events WHERE event_key=?', (k,))
conn.commit(); conn.close()

# 4) get_events 输出含 event_date，且为规范日期或空（绝不返回“编辑于/小时前”脏相对时间）
es = db.get_events(50)
assert all(('event_date' in x) for x in es), 'get_events 缺 event_date 字段'
bad = [x for x in es if x['event_date'] and not re.match(r'^\d{4}-\d{2}-\d{2}$', x['event_date'])]
print('[get_events] 返回', len(es), '条，非规范发生日期', len(bad), '条（应为0）')
assert not bad
print('ALL_EVENT_DATE_TESTS_DONE')
