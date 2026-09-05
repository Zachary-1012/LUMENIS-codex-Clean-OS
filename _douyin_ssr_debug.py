# -*- coding: utf-8 -*-
"""抖音detail SSR数据提取调试"""
import sys, os, time, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v4_upgrade.adapters.human_browser import HumanBrowser
from v4_upgrade.adapters.cookie_vault import inject_into_context

AWEME_ID = "7649770505977716454"

hb = HumanBrowser(port=9222, launch_url="about:blank")
hb.connect()
inject_into_context(hb._context, "douyin")

page = hb.new_page()
print(f"打开详情页: https://www.douyin.com/video/{AWEME_ID}")
page.goto(f"https://www.douyin.com/video/{AWEME_ID}", wait_until="domcontentloaded", timeout=30000)
hb.pause(5.0, 5.0)

# 检查页面标题
print(f"标题: {page.title()[:80]}")

# 检查SSR数据
html = page.content()
print(f"HTML长度: {len(html)}")

# 查找RENDER_DATA
m = re.search(r'<script id="RENDER_DATA"[^>]*>(.*?)</script>', html, re.DOTALL)
if m:
    print(f"找到 RENDER_DATA, 长度={len(m.group(1))}")
    try:
        from urllib.parse import unquote
        decoded = unquote(m.group(1))
        data = json.loads(decoded)
        print(f"RENDER_DATA keys: {list(data.keys())[:10]}")
        # 查找aweme_detail
        def find_aweme(obj, path=""):
            if isinstance(obj, dict):
                if "aweme_detail" in obj:
                    print(f"  找到 aweme_detail at {path}")
                    ad = obj["aweme_detail"]
                    if isinstance(ad, dict):
                        print(f"    desc={str(ad.get('desc',''))[:60]}")
                        print(f"    digg_count={ad.get('statistics',{}).get('digg_count')}")
                        print(f"    comment_count={ad.get('statistics',{}).get('comment_count')}")
                for k, v in obj.items():
                    find_aweme(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj[:3]):
                    find_aweme(v, f"{path}[{i}]")
        find_aweme(data)
    except Exception as e:
        print(f"解析RENDER_DATA失败: {e}")
else:
    print("未找到 RENDER_DATA")

# 查找_ROUTER_DATA
m2 = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\});', html, re.DOTALL)
if m2:
    print(f"找到 _ROUTER_DATA, 长度={len(m2.group(1))}")
else:
    print("未找到 _ROUTER_DATA")

# 查找所有script中的aweme
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\n页面共有 {len(scripts)} 个script标签")
for i, s in enumerate(scripts):
    if "aweme" in s.lower() and len(s) > 100:
        print(f"  script[{i}] 含aweme, 长度={len(s)}")
        break

page.close()
hb.close()
print("\n完成")
