# -*- coding: utf-8 -*-
"""抖音RENDER_DATA深度遍历"""
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

# 深度遍历，找含aweme_id或desc的dict
found = []
def walk(obj, path=""):
    if isinstance(obj, dict):
        # 检查是否是aweme对象
        if "desc" in obj and ("statistics" in obj or "aweme_id" in obj or "create_time" in obj):
            found.append((path, obj))
        for k, v in obj.items():
            walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5]):
            walk(v, f"{path}[{i}]")

walk(data)
print(f"找到 {len(found)} 个疑似aweme对象:")
for path, obj in found[:3]:
    print(f"\n  路径: {path}")
    print(f"  desc: {str(obj.get('desc',''))[:80]}")
    stats = obj.get("statistics", {})
    print(f"  digg={stats.get('digg_count')} comment={stats.get('comment_count')} share={stats.get('share_count')} collect={stats.get('collect_count')}")
    print(f"  create_time={obj.get('create_time')}")
    author = obj.get("author", {})
    print(f"  author={author.get('nickname')} sec_uid={author.get('sec_uid','')[:20]}")
    print(f"  duration={obj.get('duration')}")

# 也打印app下的结构
print("\n=== app.initialState 结构 ===")
init = data.get("app", {}).get("initialState", {})
print(f"keys: {list(init.keys())[:15]}")
if "video" in init:
    print(f"video keys: {list(init['video'].keys())[:10]}")
    if "detail" in init["video"]:
        detail = init["video"]["detail"]
        print(f"detail keys: {list(detail.keys())[:5]}")
        for k, v in list(detail.items())[:2]:
            print(f"  detail[{k}] keys: {list(v.keys())[:10] if isinstance(v, dict) else type(v)}")

page.close()
hb.close()
