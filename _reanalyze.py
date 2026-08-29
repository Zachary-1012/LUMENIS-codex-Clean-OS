# -*- coding: utf-8 -*-
import sys, io, os, sqlite3, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import ai_analyzer as A

c = sqlite3.connect('data/monitor.db')
c.row_factory = sqlite3.Row
rows = c.execute("SELECT * FROM notes").fetchall()
print('总笔记:', len(rows))
# topics 存储格式样例
sample = c.execute("SELECT topics FROM notes WHERE topics IS NOT NULL AND topics<>'' LIMIT 1").fetchone()
print('topics原格式样例:', repr(sample[0]) if sample else None)

before = {}
after = {}
changed = 0
target_fixed = []
for r in rows:
    d = dict(r)
    before[d.get('sentiment')] = before.get(d.get('sentiment'), 0) + 1
    res = A.analyze_note(d)
    topics_str = json.dumps(res['topics'], ensure_ascii=False)
    reason_str = '；'.join(res.get('sentiment_reasons', [])) or '无明显正负倾向，规则引擎判定中性'
    c.execute("""UPDATE notes SET sentiment=?,sentiment_score=?,risk_level=?,risk_score=?,
                 summary=?,topics=?,category=?,ai_reason=?,ai_analyzed_at=datetime('now','localtime')
                 WHERE id=?""",
              (res['sentiment'], res['sentiment_score'], res['risk_level'], res['risk_score'],
               res['summary'], topics_str, res['category'], reason_str, d['id']))
    after[res['sentiment']] = after.get(res['sentiment'], 0) + 1
    if res['sentiment'] != d.get('sentiment') or res['risk_level'] != d.get('risk_level'):
        changed += 1
    if '美奈小馆' in (d.get('title') or ''):
        target_fixed.append((d['title'], d.get('sentiment'), res['sentiment'], d.get('risk_level'), res['risk_level'], res['risk_score'], reason_str))
c.commit()
print('\n情感分布 回刷前:', before)
print('情感分布 回刷后:', after)
print('风险分布 回刷后:', dict(c.execute("SELECT risk_level,COUNT(*) FROM notes GROUP BY risk_level").fetchall()))
print('发生变化条数:', changed)
print('\n=== 用户指出案例 ===')
for t in target_fixed: print(t)
c.close()
