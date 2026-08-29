import sqlite3
import urllib.request
import base64
import json

print("=== 数据库空表检查 ===")
conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()
tables = ['web_topics', 'web_events', 'weekly_events', 'notification_logs', 'notes', 'events']
for t in tables:
    try:
        count = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} 条")
    except Exception as e:
        print(f"  {t}: 错误 - {e}")
conn.close()

print("\n=== 关键API测试 ===")
auth = base64.b64encode(b'Zachary:ID082610').decode()
headers = {'Authorization': f'Basic {auth}'}

apis = [
    '/api/architecture/status',
    '/api/settings/config',
    '/api/export/preview?period=daily',
    '/api/pr/cases',
    '/api/local-ai/status',
    '/api/collector/status',
]

for api in apis:
    try:
        req = urllib.request.Request(f'http://127.0.0.1:8200{api}', headers=headers)
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read())
        print(f"  ✅ {api} (ok={data.get('ok')})")
    except Exception as e:
        print(f"  ❌ {api} - {str(e)[:50]}")

print("\n=== 检查完成 ===")
