# -*- coding: utf-8 -*-
"""抖音RENDER_DATA完整结构"""
import sys, os, json, re
from urllib.parse import unquote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v4_upgrade.adapters.human_browser import HumanBrowser
from v4_upgrade.adapters.cookie_vault import inject_into_context

AWEME_ID = "7649770505977716454"

hb = HumanBrowser(port=9222, launch_url="about:blank")
hb.connect()
inject_into_context(hb._context, "douyin")

page = hb.new_page()
page.goto(f"https://www.douyin.com/video/{AWEME_ID}", wait_until="domcontentloaded", timeout=30000)
hb.pause(4.0, 4.0)
html = page.content()

m = re.search(r'<script id="RENDER_DATA"[^>]*>(.*?)</script>', html, re.DOTALL)
data = json.loads(unquote(m.group(1)))

def print_structure(obj, prefix="", depth=0, max_depth=4):
    if depth > max_depth:
        print(f"{prefix}... (max depth)")
        return
    if isinstance(obj, dict):
        keys = list(obj.keys())
        print(f"{prefix}dict({len(keys)}): {keys[:12]}")
        for k in keys[:5]:
            v = obj[k]
            if isinstance(v, (dict, list)) and len(str(v)) > 100:
                print_structure(v, f"{prefix}  [{k}]", depth+1, max_depth)
            else:
                print(f"{prefix}  [{k}] = {str(v)[:80]}")
    elif isinstance(obj, list):
        print(f"{prefix}list({len(obj)})")
        if obj and isinstance(obj[0], (dict, list)):
            print_structure(obj[0], f"{prefix}  [0]", depth+1, max_depth)

print("=== RENDER_DATA 顶层 ===")
print_structure(data, "", 0, 3)

# 在整个HTML中搜索aweme_id
print(f"\n=== HTML中搜索 {AWEME_ID} ===")
idx = html.find(AWEME_ID)
if idx >= 0:
    print(f"找到 at pos {idx}")
    print(f"上下文: ...{html[max(0,idx-50):idx+100]}...")
else:
    print("未找到aweme_id")

# 搜索digg_count
idx2 = html.find("digg_count")
if idx2 >= 0:
    print(f"\ndigg_count at pos {idx2}")
    print(f"上下文: ...{html[max(0,idx2-30):idx2+80]}...")

page.close()
hb.close()
