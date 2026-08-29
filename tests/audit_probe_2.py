# -*- coding: utf-8 -*-
"""只读审计探查 2：数据库全量结构/行数/关键字段/索引。"""
import os, glob, sqlite3
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(ROOT,'docs','audit_evidence'); os.makedirs(OUT,exist_ok=True)
buf=[]; p=buf.append
DBS=glob.glob(os.path.join(ROOT,'data','*.db'))+glob.glob(os.path.join(ROOT,'*.db'))
p('# 取证2 数据库')
p('db 文件: '+', '.join(os.path.relpath(d,ROOT) for d in DBS))
# 选主库（taikoo_*.db 优先，最大）
def size(d): return os.path.getsize(d)
main=sorted(DBS,key=size,reverse=True)[0]
p('选定主库: '+os.path.relpath(main,ROOT)+f'  {os.path.getsize(main)//1024} KB')
con=sqlite3.connect(main); cur=con.cursor()
tabs=[r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
p(f'\n## 表数量 {len(tabs)}')
for t in tabs:
    try: n=cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    except Exception as e: n=f'ERR {e}'
    cols=[(r[1],r[2]) for r in cur.execute(f'PRAGMA table_info("{t}")')]
    colstr=', '.join(f'{c[0]}:{c[1]}' for c in cols)
    p(f'\n### {t}  rows={n}  cols={len(cols)}')
    p('   '+colstr[:400])
# 索引与唯一约束
p('\n## 索引/唯一 (sqlite_master type=index)')
for r in cur.execute("SELECT name,tbl_name,sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY tbl_name"):
    p(f'  {r[0]} on {r[1]} :: {(r[2] or "")[:90]}')
con.close()
open(os.path.join(OUT,'02_db.txt'),'w',encoding='utf-8').write('\n'.join(buf))
print('tables=',len(tabs),'written 02_db.txt')
