"""T1-1b) 空正文 253 条审计脚本（只读，不写 DB）
输出：platform分布、publish_datetime区间、URL前缀、是否有 note_id/xhs_note_id、9222 CDP 健康
"""
import os, sys, sqlite3, json, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.environ.get('ZBC_DB_PATH') or os.path.join(ROOT, 'data', 'monitor.db')
print('[DB]', DB)
conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
cur = conn.cursor()
cur.execute("SELECT name FROM pragma_table_info('notes') ORDER BY cid")
cols = [r[0] for r in cur.fetchall()]
print('[notes columns]', ', '.join(cols))

EMPTY_WHERE = "(body IS NULL OR TRIM(body)='')"
cur.execute(f"SELECT COUNT(*) FROM notes WHERE {EMPTY_WHERE}")
EMPTY_TOTAL = cur.fetchone()[0]
print(f'\n[空正文总数] = {EMPTY_TOTAL}')

# platform 分布：真实列是 source_platform (上面列清单可见)
print('\n-- 空正文按 source_platform --')
for row in cur.execute(f"""
SELECT COALESCE(source_platform,'NULL') AS p, COUNT(*) c
FROM notes
WHERE {EMPTY_WHERE}
GROUP BY COALESCE(source_platform,'NULL') ORDER BY c DESC
"""): print(f'  {row[0]!s:<12} {row[1]}')

# publish_datetime 区间
print('\n-- 空正文最早/最晚 publish_datetime --')
cur.execute(f"""
SELECT MIN(publish_datetime), MAX(publish_datetime), COUNT(*)
FROM notes WHERE {EMPTY_WHERE}
""")
r = cur.fetchone()
print(f'  MIN={r[0]}  MAX={r[1]}  N={r[2]}')

# URL 前缀 / ID 样例 (真实列名 url 而非 note_url)
print('\n-- 空正文 TOP 10 url host prefix + id --')
for row in cur.execute(f"""
SELECT source_platform, note_id, url, publish_datetime, id as db_id
FROM notes WHERE {EMPTY_WHERE}
ORDER BY id LIMIT 10
"""):
    url = (row[2] or '')[:80]
    print(f'  dbid={row[4]:<5} plat={row[0]!s:<10} id={str(row[1])[:24]:<26} pub={row[3]} url={url}')

# URL host 聚合（从 url 提取 host）
def host(url):
    try:
        from urllib.parse import urlparse
        return urlparse(url or '').netloc or 'EMPTY'
    except Exception:
        return 'ERR'
print('\n-- 空正文 url host TOP 12 --')
rows = cur.execute(f"SELECT url, COUNT(*) FROM notes WHERE {EMPTY_WHERE} GROUP BY url").fetchall()
from collections import Counter
cc = Counter()
total_empty_url = 0
for url, _ in rows:
    h = host(url)
    cc[h] += 1
    if not url: total_empty_url += 1
for h, c in cc.most_common(12):
    print(f'  host={h!s:<28}  distinct_urls={c}')
print(f'  (note_url 为空或 NULL 条数 = {total_empty_url})')

# CDP 9222 健康
print('\n-- Edge CDP 9222 健康检查 --')
try:
    with urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=5) as r:
        data = json.loads(r.read().decode('utf-8', errors='ignore'))
    print(f'  OK: {data.get("Browser")}  protocol={data.get("Protocol-Version")}')
    with urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=5) as r:
        tabs = json.loads(r.read().decode('utf-8', errors='ignore'))
    print(f'  Open tabs: {len(tabs)}')
    for t in tabs[:5]: print('   -', (t.get('title') or '')[:60], '|', (t.get('url') or '')[:70])
except Exception as e:
    print(f'  WARN 9222 不可用: {e}')

conn.close()
