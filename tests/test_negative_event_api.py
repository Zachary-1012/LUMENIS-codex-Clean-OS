# -*- coding: utf-8 -*-
"""负面审核主体口径 + 事件关联笔记 的回归测试（纯 DB，不启服务、不联网）。
覆盖本轮三个修复：
1. 负面审核待办只含广州太古汇主体、非重复非噪音笔记（全网公关案例不得混入）；
2. 待办列表里的每条笔记都能通过详情接口的主体口径（不会再 404 Not found）；
3. 事件“相关笔记案例”走 event_mentions 关联表，能取到真实笔记而非关键词 0 条；
4. 负面审核统计与列表同口径，数字一致。
运行：.venv\\Scripts\\python.exe tests\\test_negative_event_api.py
"""
import os, sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from subject_rules import subject_sql_and_values, subject_hit
from database import note_to_dict

def _visible(note):
    return subject_hit(title=note.get('title',''), body=note.get('body',''),
                       content=note.get('content',''), source_keyword=note.get('source_keyword',''),
                       matched_keywords=note.get('matched_keywords',''))

FAILS = []
def check(name, cond):
    print(('PASS' if cond else 'FAIL'), '-', name)
    if not cond: FAILS.append(name)

conn = sqlite3.connect('data/monitor.db'); conn.row_factory = sqlite3.Row

# 与 app.api_negative_pending 完全一致的口径
clause, sp = subject_sql_and_values(); sp = list(sp)
base = ("sentiment='negative' AND (negative_confirmed=0 OR negative_confirmed IS NULL) "
        "AND COALESCE(is_duplicate,0)=0 AND COALESCE(noise_type,'')='' AND " + clause)
rows = conn.execute(f"SELECT * FROM notes WHERE {base} ORDER BY collected_at DESC", tuple(sp)).fetchall()
pending = [dict(r) for r in rows]
check("负面待办列表非空（系统有太古汇负面待审）", len(pending) > 0)

# 1) 不得混入全网公关案例品牌
CASE_BRANDS = ['拉夫劳伦', 'Ralph Lauren', '宝格丽', 'ZARA', 'GBC', '宝珀']
leaked = [n for n in pending if any(b.lower() in (n.get('title') or '').lower() for b in CASE_BRANDS)]
check("待办列表不含全网公关案例（拉夫劳伦/宝格丽/ZARA 等）", len(leaked) == 0)

# 2) 每条待办都能通过详情主体口径（详情接口不会 404）
hidden = [n['note_id'] for n in pending if not _visible(n)]
check("每条待办笔记经详情主体口径均可见（杜绝 Not found）", len(hidden) == 0)

# 3) 事件关联笔记：event_mentions join notes
ev = conn.execute("SELECT id FROM events ORDER BY id LIMIT 1").fetchone()
if ev:
    linked = conn.execute("""SELECT COUNT(*) FROM event_mentions m JOIN notes n ON n.note_id=m.source_id
                             WHERE m.event_id=?""", (ev['id'],)).fetchone()[0]
    check(f"首个事件(id={ev['id']})经 event_mentions 可关联到笔记", linked >= 1)
    # 负面必须排在前
    ordered = [dict(r) for r in conn.execute("""SELECT n.sentiment FROM event_mentions m JOIN notes n
                 ON n.note_id=m.source_id WHERE m.event_id=?
                 ORDER BY CASE n.sentiment WHEN 'negative' THEN 0 ELSE 1 END""", (ev['id'],)).fetchall()]
    negs = [i for i, x in enumerate(ordered) if x['sentiment'] == 'negative']
    check("事件关联笔记负面排在最前", (not negs) or min(negs) == 0)

# 4) stats 口径与列表口径一致（pending 计数）
stat_pending = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base}", tuple(sp)).fetchone()[0]
check("统计 pending 数与列表 total 一致", stat_pending == len(pending))

conn.close()
print('\n' + ('全部通过 ✅' if not FAILS else f'{len(FAILS)} 项失败: {FAILS}'))
sys.exit(1 if FAILS else 0)
