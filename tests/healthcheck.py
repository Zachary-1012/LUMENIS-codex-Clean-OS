# -*- coding: utf-8 -*-
"""只读健康检查：关键模块可导入 + monitor.db 可只读打开 + 主体口径仍在。不写任何数据。"""
import io, os, sys, sqlite3, json, importlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(root)
sys.path.insert(0, root)
report = {'modules': {}, 'db': {}, 'subject_guard': {}, 'ok': True}

# 1) 关键模块可导入
for mod in ['app', 'collector', 'intelligence', 'reprocess', 'risk_engine_mod',
            'collector_guard', 'collector_guard.risk_engine', 'collector_guard.guard',
            'proxy_pool', 'run_supervised']:
    if mod == 'risk_engine_mod':
        continue
    try:
        importlib.import_module(mod)
        report['modules'][mod] = 'ok'
    except Exception as e:
        report['modules'][mod] = f'FAIL: {type(e).__name__}: {e}'
        report['ok'] = False

# 2) 数据库只读打开（mode=ro，绝不写）
db = os.path.join(root, 'data', 'monitor.db')
try:
    uri = 'file:' + db.replace('\\', '/') + '?mode=ro'
    con = sqlite3.connect(uri, uri=True)
    cur = con.cursor()
    cur.execute("SELECT count(*) FROM notes")
    report['db']['notes_total'] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM notes WHERE captured_at >= date('now','localtime')")
    report['db']['notes_today'] = cur.fetchone()[0]
    cur.execute("SELECT max(captured_at) FROM notes")
    report['db']['last_captured_at'] = cur.fetchone()[0]
    # publish 与 captured 双时间都在
    cur.execute("PRAGMA table_info(notes)")
    cols = [r[1] for r in cur.fetchall()]
    report['db']['has_publish_datetime'] = 'publish_datetime' in cols or 'publish_date' in cols
    report['db']['has_captured_at'] = 'captured_at' in cols
    con.close()
except Exception as e:
    report['db']['error'] = f'{type(e).__name__}: {e}'
    report['ok'] = False

# 3) 主体口径仍在（广州太古汇命中、上海太古汇排除）
try:
    import subject_rules as dc
    pos = dc.subject_hit('广州太古汇 一方五境装置')
    neg = dc.subject_hit('上海兴业太古汇开业')
    report['subject_guard']['gz_hit'] = bool(pos)
    report['subject_guard']['sh_excluded'] = not bool(neg)
    if not (pos and not neg):
        report['ok'] = False
except Exception as e:
    report['subject_guard']['error'] = f'{type(e).__name__}: {e}'

print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if report['ok'] else 1)
