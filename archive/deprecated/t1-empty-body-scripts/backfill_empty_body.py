# -*- coding: utf-8 -*-
"""
T1-1: notes.body 空正文 253 条 CDP 旁路补抓（独立脚本 · 不改 app.py/collector.py）
严格遵循：
  - 仅 UPDATE notes.body / summary / detail_fetched_at / data_quality_status
  - 绝不触碰 publish_datetime / captured_at
  - 每条间隔 --cooldown 秒，遇到验证/CAPTCHA 立即停止并写熔断文件
  - --dry-run 只列出清单不进浏览器
  - --limit N 控制补抓条数
  - 结果 JSON 落盘 scripts/_zachary_t1_1_result.json 便于审计
"""
import os, sys, json, time, sqlite3, argparse, random
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.environ.get('ZBC_DB_PATH') or os.path.join(BASE, 'data', 'monitor.db')
CDP  = os.getenv('XHS_CDP_URL', 'http://127.0.0.1:9222')
CIRCUIT_FILE = os.path.join(BASE, 'data', 'private', 'topic_campaign_circuit.json')
RESULT_FILE  = os.path.join(BASE, 'scripts', '_zachary_t1_1_result.json')

EMPTY_SQL = "body IS NULL OR TRIM(body)=''"

def query_empty(conn, limit):
    sql = f"""SELECT id, note_id, url, xsec_token, title, publish_datetime, captured_at, source_platform
             FROM notes WHERE {EMPTY_SQL} ORDER BY id ASC"""
    if limit and limit > 0: sql += f" LIMIT {int(limit)}"
    return [dict(r) for r in conn.execute(sql).fetchall()]

def write_circuit(msg):
    os.makedirs(os.path.dirname(CIRCUIT_FILE), exist_ok=True)
    with open(CIRCUIT_FILE,'w',encoding='utf-8') as f:
        json.dump({'status':'PAUSED','reason':f'T1-1 BACKFILL: {msg}','ts':datetime.now().isoformat(timespec='seconds')}, f, ensure_ascii=False, indent=2)

def extract_body_title(page, note_url):
    """返回 {'body','summary','risk_flag','captcha_trigger'}"""
    page.goto(note_url, wait_until='domcontentloaded', timeout=25000)
    page.wait_for_timeout(2500)  # SPA 渲染
    cur = page.url or ''
    if any(k in cur for k in ('captcha','website-login','/login','verify')):
        try: txt = page.evaluate("() => (document.body?document.body.innerText.slice(0,400):'')")
        except: txt=''
        if any(k in txt for k in ('验证','扫码','滑块','人机','CAPTCHA','安全验证')):
            return {'body':'','summary':'','captcha_trigger': True}
    data = page.evaluate("""() => {
        const bodySel = [
            '#detail-desc', '.note-content', '.content .desc', '[class*="desc"]',
            'div.note-scroller .content', 'meta[property="og:description"]'
        ];
        let body = '';
        for (const s of bodySel) {
            const el = document.querySelector(s);
            if (el) { body = (s.startsWith('meta') ? el.getAttribute('content') : (el.innerText||el.textContent||'')) || ''; }
            if (body && body.length>=12) break;
        }
        const h1 = document.querySelector('h1')?.innerText || '';
        const noteTitle = document.querySelector('.note-title, [class*="title"], .title, meta[property="og:title"]')?.innerText || '';
        const title = h1 || noteTitle || '';
        return {body: body.slice(0,5000), title: title.slice(0,300)};
    }""") or {'body':'','title':''}
    return {'body': (data.get('body') or '').strip(),
            'summary': (data.get('title') or '').strip(),
            'captcha_trigger': False}

def run_backfill(rows, cooldown, headless=False):
    from playwright.sync_api import sync_playwright
    res = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.connect_over_cdp(CDP, timeout=15000)
            ctx = browser.contexts[0]
        except Exception as e:
            print('连接 CDP 9222 失败：', e)
            raise SystemExit(2)
        page = ctx.new_page()
        stopped = False
        for i, r in enumerate(rows):
            nid = r['note_id']; dbid = r['id']
            url = r.get('url') or ''
            if not url:
                xsec = r.get('xsec_token') or ''
                url = f"https://www.xiaohongshu.com/explore/{nid}" + (f"?xsec_token={xsec}" if xsec else '')
            print(f'[{i+1}/{len(rows)}] id={dbid:<5} nid={str(nid):<26} pub={r.get("publish_datetime")}')
            print(f'      url= {url[:120]}')
            item = {'db_id': dbid, 'note_id': nid, 'url': url,
                    'before_body_empty': True, 'status':'PENDING', 'error':'', 'body_len':0, 'title_len':0}
            try:
                got = extract_body_title(page, url)
            except Exception as e:
                item['status']='ERROR_LOAD'; item['error']=f'{type(e).__name__}: {e}'[:200]
                res.append(item); print(f'      ✘ load error: {item["error"]}')
                time.sleep(cooldown); continue
            if got.get('captcha_trigger'):
                item['status']='CAPTCHA'; item['error']='验证码/登录验证页'
                res.append(item); stopped=True
                write_circuit('body backfill captcha'); print('      ⛔ CAPTCHA！写入熔断并停止后续补抓。'); break
            body = got['body']; summary = got['summary']
            if not body:
                item['status']='STILL_EMPTY'; item['error']='DOM仍无正文（可能笔记已删/权限/反爬）'
                res.append(item); print('      ⚠ 仍无正文，跳过写入')
                time.sleep(cooldown); continue
            item['body_len']=len(body); item['title_len']=len(summary)
            # 写回：只改 body / summary / detail_fetched_at / data_quality_status
            # 强约束：publish_datetime/captured_at 出现在 SET 里 = 硬错误
            sql = """UPDATE notes SET body=?, summary=COALESCE(NULLIF(?, ''), summary),
                            detail_fetched_at=COALESCE(detail_fetched_at, ?),
                            data_quality_status = CASE WHEN data_quality_status IS NULL OR data_quality_status='' THEN 'backfilled' ELSE data_quality_status END
                     WHERE id=? AND (""" + EMPTY_SQL + ")"
            params = (body, summary, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), dbid)
            cur = conn.cursor()
            cur.execute(sql, params)
            updated = cur.rowcount
            conn.commit()
            if updated == 1:
                item['status']='UPDATED'
                print(f'      ✅ UPDATE OK  body={len(body)}字  title={len(summary)}字')
            else:
                # 竞态：另一进程已补上
                item['status']='ALREADY_FILLED'
                print(f'      ℹ 竞态：已被其他进程补全，未重复写入')
            res.append(item)
            # 每条后冷 2~cooldown+随机抖动
            time.sleep(1.5 + random.uniform(0.5, float(cooldown)))
        try: page.close()
        except: pass
        try: browser.disconnect()
        except: pass
    return res, stopped


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='T1-1 notes 空正文 CDP 旁路补抓 (独立脚本)')
    ap.add_argument('--limit', type=int, default=0, help='补抓条数上限，0=全部')
    ap.add_argument('--dry-run', action='store_true', help='只列清单不抓')
    ap.add_argument('--cooldown', type=float, default=3.0, help='每条最小冷却秒数（实际1.5+随机抖动）')
    args = ap.parse_args()

    print('=== T1-1 空正文补抓 BACKFILL ===')
    print(f'DB = {DB}')
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    before = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {EMPTY_SQL}").fetchone()[0]
    print(f'[BEFORE] 空正文条数 = {before}')

    rows = query_empty(conn, args.limit)
    print(f'[TARGET] 本次 = {len(rows)} 条  (limit={args.limit or "all"})')
    if args.dry_run:
        print(f'-- DRY-RUN 清单 (前 {min(len(rows),50)} 条)')
        for r in rows[:50]:
            print(f"  id={r['id']:<5}  nid={str(r['note_id']):<26}  plat={r['source_platform']!s:<8}  pub={r['publish_datetime']}  url={(r['url'] or '')[:110]}")
        conn.close(); sys.exit(0)

    if not rows: print('无需补抓'); conn.close(); sys.exit(0)
    t0 = time.time()
    results, stopped = run_backfill(rows, args.cooldown)
    elapsed = time.time() - t0
    after = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {EMPTY_SQL}").fetchone()[0]
    print()
    print(f'[AFTER] 空正文条数 = {after}   减少 = {before-after}')
    counts = {}
    for r in results: counts[r['status']] = counts.get(r['status'],0)+1
    print('[STATUS 汇总]', '  '.join(f'{k}={v}' for k,v in counts.items()))
    print(f'[耗时] {elapsed:.0f}s  平均={elapsed/max(1,len(results)):.1f}s/条')
    if stopped: print('[熔断] 因 CAPTCHA/验证页提前停止，结果已写入熔断文件，请在系统内完成验证再继续。')
    payload = {'ts': datetime.now().isoformat(timespec='seconds'),
               'before_empty': before, 'after_empty': after, 'reduced': before-after,
               'counts': counts, 'elapsed_s': round(elapsed,1),
               'items': results, 'stopped_by_captcha': stopped}
    with open(RESULT_FILE,'w',encoding='utf-8') as f: json.dump(payload,f,ensure_ascii=False,indent=2)
    print(f'[JSON 证据] {RESULT_FILE}')
    conn.close()
