# -*- coding: utf-8 -*-
"""验证 insert_note 标题兜底：空标题+正文→取首句；空标题空正文+作者→作者的笔记。测试后立即删除，不留垃圾。"""
import io, os, sys, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import database
db = database.DB_PATH
fails = []
def cleanup(*ids):
    with database.get_db() as conn:
        conn.execute("DELETE FROM notes WHERE note_id IN (%s)" % ','.join('?'*len(ids)), ids)

cleanup('__fb_t1__', '__fb_t2__')
try:
    database.insert_note({'note_id':'__fb_t1__','title':'','content':'测试标题首句\n第二行正文','author_nickname':'作者甲'})
    database.insert_note({'note_id':'__fb_t2__','title':'   ','content':'','author_nickname':'作者乙'})
    c = sqlite3.connect(db)
    t1 = c.execute("SELECT title FROM notes WHERE note_id='__fb_t1__'").fetchone()[0]
    t2 = c.execute("SELECT title FROM notes WHERE note_id='__fb_t2__'").fetchone()[0]
    c.close()
    print('正文首句兜底 ->', repr(t1))
    print('作者昵称兜底 ->', repr(t2))
    if t1 != '测试标题首句': fails.append(('正文首句', t1))
    if t2 != '作者乙的笔记': fails.append(('作者兜底', t2))
finally:
    cleanup('__fb_t1__', '__fb_t2__')
    c = sqlite3.connect(f'file:{os.path.abspath(db)}?mode=ro', uri=True)
    left = c.execute("SELECT COUNT(*) FROM notes WHERE note_id IN ('__fb_t1__','__fb_t2__')").fetchone()[0]
    c.close()
    print('测试残留(应0) =', left)
    if left: fails.append(('清理残留', left))
print('标题兜底入库验证:', '通过' if not fails else f'失败 {fails}')
sys.exit(1 if fails else 0)
