# -*- coding: utf-8 -*-
"""研究小红书话题页结构，定位browse_count和discussion_count"""
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9222', timeout=15000)
    ctx = browser.contexts[0]
    page = ctx.new_page()

    # 先访问搜索页，搜索"太古汇"，看看话题tab
    print('=== 访问搜索页 ===')
    page.goto('https://www.xiaohongshu.com/search_result?keyword=太古汇', wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(4000)
    print(f'URL: {page.url}')
    print(f'Title: {page.title()}')

    # 查看页面上所有可能包含数字的元素
    print()
    print('=== 查找包含"浏览"/"讨论"/"笔记"/"万"的元素 ===')
    elements = page.evaluate('''() => {
        const results = [];
        document.querySelectorAll('*').forEach(el => {
            const text = (el.innerText || el.textContent || '').trim();
            if (text && text.length < 50 && (text.includes('浏览') || text.includes('讨论') || text.includes('笔记') || text.includes('万') || /\\d+\\.?\\d*万/.test(text))) {
                if (el.children.length === 0 || el.tagName === 'SPAN' || el.tagName === 'DIV') {
                    results.push({tag: el.tagName, class: el.className, text: text.slice(0, 50)});
                }
            }
        });
        return results.slice(0, 30);
    }''')
    for e in elements:
        print(f'  <{e["tag"]} class="{e["class"]}"> {e["text"]}')

    # 尝试点击"话题"tab
    print()
    print('=== 查找话题tab ===')
    tabs = page.evaluate('''() => {
        const tabs = [];
        document.querySelectorAll('[class*="tab"], [class*="Tab"], .search-tabs, .tabs').forEach(el => {
            tabs.push({tag: el.tagName, class: el.className, text: (el.innerText || '').slice(0, 100)});
        });
        return tabs.slice(0, 10);
    }''')
    for t in tabs:
        print(f'  <{t["tag"]} class="{t["class"]}"> {t["text"]}')

    # 尝试直接访问话题页（小红书话题页URL格式可能是 /topic/话题名）
    print()
    print('=== 尝试访问话题聚合页 ===')
    topic_urls = [
        'https://www.xiaohongshu.com/topic/太古汇',
        'https://www.xiaohongshu.com/search_result?keyword=太古汇&type=topic',
        'https://www.xiaohongshu.com/search_result?keyword=%23太古汇',
    ]
    for url in topic_urls:
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            page.wait_for_timeout(3000)
            print(f'  URL: {page.url}')
            print(f'  Title: {page.title()}')
            body = page.evaluate('() => document.body ? document.body.innerText.slice(0, 500) : ""') or ''
            print(f'  Body: {body[:300]}')
            print()
        except Exception as e:
            print(f'  {url} -> 失败: {e}')

    # 复位
    try:
        page.goto('about:blank', timeout=5000)
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass
