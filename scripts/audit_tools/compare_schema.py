import sqlite3, json

SRC = r"D:\Taikoo-staging-ui\staging\monitor.staging.db"
DST = r"D:\Taikoo-monitor-new\data\monitor.db"

def schema(p):
    con = sqlite3.connect(p)
    tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
    out = {}
    for t in tabs:
        cols = [(r[1], r[2]) for r in con.execute(f'PRAGMA table_info("{t}")')]
        try:
            n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
        except Exception:
            n = -1
        out[t] = {"cols": [c[0] for c in cols], "n": n}
    con.close()
    return out

src = schema(SRC); dst = schema(DST)
print(f"源(历史staging)表数={len(src)}  目标(当前主库)表数={len(dst)}")
print("\n===== 源库各表: 行数 | 目标是否有同名表 | 仅源字段(目标缺) =====")
for t in sorted(src):
    s = src[t]
    if s["n"] == 0:
        continue  # 只列有数据的源表
    if t in dst:
        only_src = [c for c in s["cols"] if c not in dst[t]["cols"]]
        only_dst = [c for c in dst[t]["cols"] if c not in s["cols"]]
        status = f"目标有(目标{dst[t]['n']}行)"
        extra = f" 源多字段={only_src}" if only_src else ""
        extra += f" 目标多字段={only_dst}" if only_dst else ""
    else:
        status = "★目标无此表(需映射/新建映射)"
        extra = f" 字段={s['cols']}"
    print(f"[{s['n']:>5}] {t}  -> {status}{extra}")

print("\n===== 目标有、源没有的表(当前新增结构) =====")
for t in sorted(dst):
    if t not in src:
        print(f"  + {t} ({dst[t]['n']}行)")

print("\n===== 源有数据但目标空/缺失的关键采集表汇总 =====")
for t in ["notes","note_comments","events","event_graph_events","swire_notes","swire_events","web_mentions","topic_campaign_notes","canonical_data","zbc_canonical_data"]:
    sn = src.get(t,{}).get("n","-"); dn = dst.get(t,{}).get("n","无表")
    print(f"  {t}: 源={sn}  目标={dn}")
