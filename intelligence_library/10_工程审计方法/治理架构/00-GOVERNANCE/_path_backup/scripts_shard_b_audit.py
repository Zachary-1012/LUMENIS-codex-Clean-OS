"""Shard B audit script: DB tables, provider chain, OSAI module graph."""
import sqlite3, os, sys, importlib, inspect

ROOT = r"D:\Taikoo-monitor-new"
sys.path.insert(0, ROOT)

# 1. DB audit
db = os.path.join(ROOT, "data", "monitor.db")
print("=== DB AUDIT ===")
if os.path.exists(db):
    conn = sqlite3.connect(db)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print(f"Total tables: {len(tables)}")
    evidence_tables = []
    for t in tables:
        try:
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except:
            cnt = -1
        if any(k in t.lower() for k in ("evidence", "trace", "eval", "checkpoint", "skill", "agent", "audit", "log")):
            evidence_tables.append((t, cnt))
            print(f"  [EVIDENCE/TRACE] {t}: {cnt} rows")
    print(f"\nEvidence/trace related tables: {len(evidence_tables)}")
    conn.close()
else:
    print("DB not found")

# 2. Provider chain
print("\n=== PROVIDER CHAIN ===")
try:
    from ai_channel import provider_chain
    chain = provider_chain()
    print(f"provider_chain() = {chain}")
except Exception as e:
    print(f"provider_chain error: {e}")

try:
    from provider_registry import PROVIDER_REGISTRY, registry_summary
    print(f"Registry summary: {registry_summary()}")
    for name, info in PROVIDER_REGISTRY.items():
        print(f"  {name}: status={info['status']}, role={info['role']}")
except Exception as e:
    print(f"registry error: {e}")

# 3. AI_PROVIDER env
print(f"\nAI_PROVIDER env = {os.environ.get('AI_PROVIDER', 'not set')}")
print(f"ALLOW_CLOUD_AI = {os.environ.get('ALLOW_CLOUD_AI', 'not set')}")

# Check which keys are non-empty
for key in ["ZHIPU_API_KEY", "ARK_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"]:
    val = os.environ.get(key, "")
    print(f"  {key}: {'SET' if val else 'EMPTY'} (len={len(val)})")
