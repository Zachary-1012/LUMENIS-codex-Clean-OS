# -*- coding: utf-8 -*-
"""
Instagram 适配器真人通道冒烟测试（手动触发，不纳入 CI 自动化）
-------------------------------------------------
前置：本地代理可用（GOOGLE_PROXY / OPENAI_PROXY），且 data/cookies/instagram.json
存在有效登录态（cookie_vault 自动注入到 9223 代理 Profile）。
运行：.venv\\Scripts\\python.exe tests\\test_instagram_adapter.py
"""
import sys, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 独立脚本手动加载 .env（app 运行时由框架自动加载）
envp = os.path.join(ROOT, ".env")
if os.path.exists(envp):
    for line in open(envp, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from v4_upgrade.adapters.registry import registry, register_default_adapters
register_default_adapters()

ad = registry.get("instagram")
t0 = time.time()
res = ad.search("lululemon", 12)
print(f"success={res.success} raw={res.raw_count} got={len(res.notes)} err={res.error} {time.time()-t0:.1f}s")
for n in res.notes:
    print(f"  ❤{n.likes:>9} @{n.author:22} {n.title[:50]}")
    print("     ", n.url)
