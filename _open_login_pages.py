# -*- coding: utf-8 -*-
"""连接9222浏览器，打开各平台登录页"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright

PAGES = [
    ("微博", "https://m.weibo.cn/"),
    ("知乎", "https://www.zhihu.com/signin"),
    ("Instagram", "https://www.instagram.com/accounts/login/"),
    ("抖音", "https://www.douyin.com/"),
]

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0] if browser.contexts else browser.new_context()

    for name, url in PAGES:
        try:
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            print(f"  已打开 {name}: {page.title()[:50]}")
        except Exception as e:
            print(f"  打开 {name} 失败: {e}")

    print("\n===== 请在浏览器中登录以上4个平台 =====")
    print("登录完成后告诉我，我自动采集 cookie")
    browser.close()
