import sqlite3
import json
import os

print("=" * 60)
print("数据库表检查")
print("=" * 60)
conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f"共{len(tables)}张表:")
empty_tables = []
for t in tables:
    count = c.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    status = "✅" if count > 0 else "⚠️ 空表"
    print(f"  {status} {t[0]}: {count}条")
    if count == 0:
        empty_tables.append(t[0])
conn.close()

print("\n" + "=" * 60)
print("空表汇总")
print("=" * 60)
if empty_tables:
    for t in empty_tables:
        print(f"  ⚠️ {t}")
else:
    print("  ✅ 没有空表")

print("\n" + "=" * 60)
print("collector_v2 缺失文件检查")
print("=" * 60)
required_files = ['standardizer.py', 'smart_scheduler.py']
for f in required_files:
    found = False
    for root, dirs, files in os.walk('collector_v2'):
        if f in files:
            found = True
            print(f"  ✅ {f} 存在于 {root}")
            break
    if not found:
        print(f"  ❌ {f} 缺失")

print("\n" + "=" * 60)
print("日志系统检查")
print("=" * 60)
log_dirs = ['logs', 'data']
for d in log_dirs:
    if os.path.exists(d):
        log_files = [f for f in os.listdir(d) if f.endswith('.log')]
        print(f"  {d}/: {len(log_files)}个日志文件")
        for f in log_files[:5]:
            size = os.path.getsize(os.path.join(d, f))
            print(f"    {f}: {size}字节")

print("\n" + "=" * 60)
print("关键配置检查")
print("=" * 60)
with open('.env', 'r', encoding='utf-8', errors='replace') as f:
    env_content = f.read()
    
checks = {
    'SMTP_HOST': 'SMTP_HOST=' in env_content and 'SMTP_HOST=\n' not in env_content and 'SMTP_HOST=\r' not in env_content,
    'SMTP_USER': 'SMTP_USER=' in env_content and 'SMTP_USER=\n' not in env_content,
    'OLLAMA_MODEL': 'OLLAMA_MODEL=' in env_content and 'OLLAMA_MODEL=\n' not in env_content,
    'DASHSCOPE_API_KEY': 'DASHSCOPE_API_KEY=' in env_content and len(env_content.split('DASHSCOPE_API_KEY=')[1].split('\n')[0]) > 5,
    'OPENAI_API_KEY': 'OPENAI_API_KEY=' in env_content and len(env_content.split('OPENAI_API_KEY=')[1].split('\n')[0]) > 5,
}
for key, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {key}: {'已配置' if ok else '未配置/为空'}")

print("\n检查完成！")
