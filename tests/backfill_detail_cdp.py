# -*- coding: utf-8 -*-
"""
backfill_detail_cdp.py —— 通过已过验证的 CDP 浏览器补抓空正文笔记的详情正文
用法：
  python tests/backfill_detail_cdp.py --limit 8        # 补 8 条（分批，防风控）
  python tests/backfill_detail_cdp.py --limit 200 --delay 5
设计：只补 content/body 均空且有 url 的笔记；遇 captcha/登录墙立即停止（不硬刚）；
     已补成功的笔记 content 非空，下次自动跳过（天然断点续跑）。
"""
import os, sys, io, time, argparse, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DBP = os.path.join(ROOT, 'data', 'monitor.db')

ap = argparse.ArgumentParser()
ap.add_argument('--cdp', default='http://127.0.0.1:9222')
ap.add_argument('--limit', type=int, default=5)
ap.add_argument('--delay', type=float, default=4.0)
args = ap.parse_args()

c = sqlite3.connect(DBP); c.row_factory = sqlite3.Row
total_empty = c.execute("SELECT COUNT(*) FROM notes WHERE (content IS NULL OR TRIM(content)='') AND (body IS NULL OR TRIM(body)='')").fetchone()[0]
rows = c.execute("""SELECT note_id,url,xsec_token,title FROM notes
                    WHERE (content IS NULL OR TRIM(content)='') AND (body IS NULL OR TRIM(body)='')
                    ORDER BY id DESC LIMIT ?""", (args.limit,)).fetchall()
print(f'空正文总数={total_empty}，本批补抓={len(rows)}')
if not rows:
    sys.exit(0)

from playwright.sync_api import sync_playwright
DESC_SEL = ['#detail-desc', '.note-text', '.desc', '[class*="desc"]', '#detail-container']
TITLE_SEL = ['#detail-title', '.title']

ok = fail = blocked = 0
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(args.cdp, timeout=20000)
    ctx = b.contexts[0]
    pg = ctx.new_page()
    for i, r in enumerate(rows, 1):
        url = r['url'] or ''
        if not url.startswith('http'):
            url = f'https://www.xiaohongshu.com/search_result/{r["note_id"]}'
            if r['xsec_token']:
                url += '?xsec_token=' + r['xsec_token'] + '&xsec_source='
        try:
            pg.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(2.5)
            if 'captcha' in pg.url or 'website-login' in pg.url:
                print(f'[{i}] 被拦(captcha)，停止本批，稍后再试'); blocked += 1; break
            desc = ''
            for sel in DESC_SEL:
                try:
                    el = pg.query_selector(sel)
                    if el:
                        t = (el.inner_text() or '').strip()
                        if len(t) > len(desc):
                            desc = t
                except Exception:
                    pass
            title = ''
            for sel in TITLE_SEL:
                try:
                    el = pg.query_selector(sel)
                    if el:
                        title = (el.inner_text() or '').strip(); break
                except Exception:
                    pass
            if desc and len(desc) >= 2:
                c.execute("UPDATE notes SET content=?, detail_fetched_at=datetime('now','localtime') WHERE note_id=?",
                          (desc, r['note_id']))
                c.commit(); ok += 1
                print(f'[{i}] OK 正文{len(desc)}字 | {(title or r["title"] or "")[:24]}')
            else:
                fail += 1
                print(f'[{i}] 未取到正文 | {(r["title"] or "")[:24]} | url={url[:60]}')
        except Exception as e:
            fail += 1; print(f'[{i}] 异常 {str(e)[:80]}')
        time.sleep(args.delay)
    pg.close(); b.close()
c.close()
print(f'本批：成功{ok} 失败{fail} 被拦{blocked}')
