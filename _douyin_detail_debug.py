# -*- coding: utf-8 -*-
"""抖音detail单独调试"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v4_upgrade.adapters.human_browser import HumanBrowser
from v4_upgrade.adapters.cookie_vault import inject_into_context

AWEME_ID = "7649770505977716454"  # 从之前search结果中取

hb = HumanBrowser(port=9222, launch_url="about:blank")
hb.connect()
inject_into_context(hb._context, "douyin")

page = hb.new_page()
captured = []

def on_response(resp):
    try:
        if resp.request.resource_type in ("xhr", "fetch") and "douyin" in resp.url:
            url = resp.url
            if any(k in url for k in ["aweme", "detail", "item", "comment", "user"]):
                captured.append({"url": url[:120], "status": resp.status})
    except: pass

page.on("response", on_response)

print(f"打开详情页: https://www.douyin.com/video/{AWEME_ID}")
page.goto(f"https://www.douyin.com/video/{AWEME_ID}", wait_until="domcontentloaded", timeout=30000)
print("等待8秒加载XHR...")
hb.pause(8.0, 8.0)

print(f"\n拦截到 {len(captured)} 个相关接口:")
for c in captured:
    print(f"  [{c['status']}] {c['url']}")

# 找detail接口
detail_urls = [c["url"] for c in captured if "detail" in c["url"].lower() or "aweme" in c["url"].lower()]
print(f"\n疑似detail接口: {len(detail_urls)}")
for u in detail_urls[:3]:
    print(f"  {u}")

page.close()
hb.close()
print("\n完成")
