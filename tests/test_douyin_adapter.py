# -*- coding: utf-8 -*-
"""
抖音适配器真人通道冒烟测试（手动触发，不纳入 CI 自动化）
-------------------------------------------------
前置：9222 采集专用 Edge Profile 已登录抖音，或 data/cookies/douyin.json
存在有效登录态（cookie_vault 自动注入）。
运行：.venv\\Scripts\\python.exe tests\\test_douyin_adapter.py
"""
import sys, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lumenis.adapters.douyin import DouyinAdapter

t0 = time.time()
r = DouyinAdapter().search("广州太古汇", 10)
print(f"success={r.success} raw={r.raw_count} got={len(r.notes)} err={r.error} {time.time()-t0:.1f}s")
for n in r.notes:
    print(f"  ❤{n.likes:>6} 💬{n.comments:>5} ⭐{n.collects:>5} @{n.author[:12]} {n.title[:42]}")
    print(f"      {n.url}  [{n.publish_date}]")
