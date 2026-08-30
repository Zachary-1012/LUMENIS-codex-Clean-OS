# -*- coding: utf-8 -*-
"""小红书 CDP 真人采集通道（独立进程，Python Playwright）。

为什么不用 node rednote_collector.cjs：node 版 Playwright connectOverCDP 对 Edge152 会 ws 已连但握手 30s 超时；
Python 版 connect_over_cdp 已实测可稳定连接 9222 持久 Edge（登录态长期复用）。
collector 通过 venv python 子进程调用本脚本以隔离崩溃；stdout 末尾打印 ---RESULT_JSON--- 结果。

铁律：只识别不绕过——300012/IP风险/安全限制 => ip_blocked；验证码/安全验证 => verification_required；
不破解、不伪装；发布时间拿不到就留空（publish != captured）；只关闭本脚本新开的标签，绝不关闭 CDP 浏览器。
"""
import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timedelta

CDP_URL = 'http://127.0.0.1:9222'

_IP_WORDS = ['300012', 'IP存在风险', 'ip存在风险', '安全限制', '访问受限', '当前访问出现异常', '网络有点忙', '操作频繁', '访问过于频繁']
_VERIFY_WORDS = ['验证码', '安全验证', '人机验证', '请完成验证', '请通过验证', '滑块', '拖动下方', 'captcha', '安全检测']


def log(msg):
    print(f'[xhs-cdp] {msg}', file=sys.stderr, flush=True)


def human_sleep(a=1.2, b=2.6):
    time.sleep(random.uniform(a, b))


def parse_count(s):
    if s is None:
        return 0
    s = str(s).strip().lower().replace(',', '').replace(' ', '')
    if not s:
        return 0
    m = re.search(r'(-?\d+(?:\.\d+)?)\s*(万|w|千|k|亿|m|b)?', s)
    if not m:
        return 0
    num = float(m.group(1))
    unit = m.group(2) or ''
    mul = {'万': 1e4, 'w': 1e4, '千': 1e3, 'k': 1e3, '亿': 1e8, 'm': 1e6, 'b': 1e9}.get(unit, 1)
    return int(num * mul)


def normalize_publish_time(raw):
    """小红书发布时间：明确日期优先；相对时间换算；拿不到返回空字符串，绝不臆造。"""
    if not raw:
        return ''
    raw = raw.strip().replace('编辑于', '').strip()
    m = re.search(r'(20\d{2})[-./](\d{1,2})[-./](\d{1,2})', raw)
    if m:
        return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    m = re.search(r'(\d{1,2})[-./](\d{1,2})', raw)
    if m:
        return f'{datetime.now().year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}'
    now = datetime.now()
    if '今天' in raw:
        return now.strftime('%Y-%m-%d')
    if '昨天' in raw:
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')
    m = re.search(r'(\d+)\s*天前', raw)
    if m:
        return (now - timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')
    m = re.search(r'(\d+)\s*(分钟|小时)前', raw)
    if m:
        return now.strftime('%Y-%m-%d')
    return ''


_LIST_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('section.note-item').forEach(item => {
    const coverLink = item.querySelector('a.cover') || item.querySelector('a[href*="/search_result/"]');
    const href = coverLink ? coverLink.getAttribute('href') : '';
    const idm = href.match(/\/search_result\/([^/?]+)/);
    const tkm = href.match(/xsec_token=([^&]+)/);
    const q = s => { const e = item.querySelector(s); return e ? (e.innerText||'').trim() : ''; };
    const img = item.querySelector('a.cover img');
    out.push({
      note_id: idm ? idm[1] : '',
      xsec_token: tkm ? decodeURIComponent(tkm[1]) : '',
      title: q('a.title span') || q('.title'),
      author: q('a.author .name') || q('.author .name'),
      time_raw: q('a.author .time') || q('.time'),
      likes_raw: q('span.like-wrapper .count') || q('.count'),
      cover: img ? img.getAttribute('src') : '',
      url: 'https://www.xiaohongshu.com' + (href.startsWith('/') ? href : '/' + href)
    });
  });
  return out.filter(x => x.note_id);
}
"""

_DETAIL_JS = r"""
() => {
  const q = sels => { for (const s of sels) { const e = document.querySelector(s); if (e && (e.innerText||'').trim()) return (e.innerText||'').trim(); } return ''; };
  const counts = Array.from(document.querySelectorAll('.count')).map(c => (c.innerText||'').trim()).filter(Boolean);
  const comments = Array.from(document.querySelectorAll('.comment-item')).map(c => {
    const u = c.querySelector('.name,.author a'), x = c.querySelector('.content,.comment-content'),
          t = c.querySelector('.time,.date'), l = c.querySelector('.like .count,.count');
    return { user: u?(u.innerText||'').trim():'', content: x?(x.innerText||'').trim():'',
             time: t?(t.innerText||'').trim():'', likes_raw: l?(l.innerText||'').trim():'' };
  });
  return {
    title: q(['#detail-title','.note-content .title','h1']),
    desc: q(['#detail-desc','.note-content .desc','.note-text','.desc']),
    author: q(['.author-container .name','.author .name','.username']),
    time_raw: q(['.author-container .time','.publish-time','.date','.time']),
    all_counts: counts, comment_list: comments, comment_count: comments.length
  };
}
"""


def classify_page(text):
    for w in _VERIFY_WORDS:
        if w in text:
            return 'verify', w
    for w in _IP_WORDS:
        if w in text:
            return 'ip', w
    return None, ''


def collect(keyword, max_scroll=3, max_details=10, cdp_url=CDP_URL):
    from playwright.sync_api import sync_playwright
    result = {'ok': False, 'keyword': keyword, 'notes': [], 'summary': {}}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url, timeout=30000)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        try:
            from urllib.parse import quote
            url = f'https://www.xiaohongshu.com/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51'
            log(f'导航搜索: {keyword}')
            # 用 commit 等响应头即可（实测 0.9s）；真正就绪由后续 wait_for_selector(卡片) 判定，
            # 不等 domcontentloaded（错误URL/慢资源会让它偶发永不触发）。
            page.goto(url, wait_until='commit', timeout=30000)
            human_sleep(3.0, 4.5)

            text = page.evaluate("() => document.body ? document.body.innerText : ''") or ''
            kind, hit = classify_page(text)
            if kind == 'ip':
                result['summary'] = {'ip_blocked': True, 'matched': hit}
                result['error'] = 'IP_RISK_OR_300012'
                return result
            if kind == 'verify':
                result['summary'] = {'verification_required': True, 'matched': hit}
                result['error'] = 'NEED_VERIFY'
                return result

            try:
                page.wait_for_selector('section.note-item', timeout=18000)
            except Exception:
                body_len = len(text.replace('\n', '').replace(' ', ''))
                if body_len < 20 or page.url.startswith('about:blank'):
                    result['error'] = 'LOAD_FAILED'
                    result['summary'] = {'load_failed': True, 'url': page.url[:80]}
                    return result

            # 拟人变速滚动触发懒加载
            for i in range(int(max_scroll)):
                page.mouse.wheel(0, random.randint(500, 950))
                human_sleep(1.4, 2.6)
            human_sleep(0.8, 1.4)

            cards = page.evaluate(_LIST_JS)
            log(f'列表发现 {len(cards)} 张卡片')
            result['summary']['discovered'] = len(cards)
            if not cards:
                # 二次风控判定（滚动后才弹验证的情况）
                t2 = page.evaluate("() => document.body ? document.body.innerText : ''") or ''
                kind, hit = classify_page(t2)
                if kind == 'ip':
                    result['summary'] = {'ip_blocked': True, 'matched': hit}; result['error'] = 'IP_RISK_OR_300012'; return result
                if kind == 'verify':
                    result['summary'] = {'verification_required': True, 'matched': hit}; result['error'] = 'NEED_VERIFY'; return result
                result['error'] = 'EMPTY_LIST'
                return result

            actual = min(int(max_details), len(cards))
            ok_detail = 0
            for i in range(actual):
                c = cards[i]
                try:
                    page.goto(c['url'], wait_until='domcontentloaded', timeout=30000)
                    try:
                        page.wait_for_selector('#detail-desc, #detail-title, .note-content .desc', timeout=10000)
                    except Exception:
                        pass
                    human_sleep(2.2, 3.4)
                    d = page.evaluate(_DETAIL_JS)
                    nums = [int(x) for x in d.get('all_counts', []) if re.fullmatch(r'\d+', str(x))]
                    likes = nums[-3] if len(nums) >= 3 else (nums[-1] if nums else parse_count(c.get('likes_raw')))
                    collects = nums[-2] if len(nums) >= 2 else 0
                    comments = nums[-1] if len(nums) >= 1 else 0
                    pub = normalize_publish_time(d.get('time_raw')) or normalize_publish_time(c.get('time_raw'))
                    rec = {
                        'note_id': c['note_id'], 'xsec_token': c.get('xsec_token', ''),
                        'title': d.get('title') or c.get('title', ''),
                        'detail_title': d.get('title') or c.get('title', ''),
                        'desc': d.get('desc', ''),
                        'author': d.get('author') or c.get('author', ''),
                        'detail_author': d.get('author') or c.get('author', ''),
                        'detail_publish_time': pub, 'publish_time': pub,
                        'likes': likes, 'collects': collects, 'comments': comments,
                        'comment_list': d.get('comment_list', []), 'comment_count': d.get('comment_count', 0),
                        'cover': c.get('cover', ''), 'url': c['url'],
                        'detail_fetched': True, 'captured_at': datetime.now().isoformat(),
                        'collector_version': 'xhs-cdp-py-1.0',
                    }
                    result['notes'].append(rec); ok_detail += 1
                    log(f'详情 {i+1}/{actual}: {rec["title"][:24]} 赞{likes} 藏{collects} 评{comments} {pub}')
                    human_sleep(1.0, 2.0)
                except Exception as e:
                    log(f'详情失败 {i+1}: {e}')
                    result['notes'].append({**c, 'detail_fetched': False, 'error': str(e)[:160],
                                            'desc': '', 'likes': parse_count(c.get('likes_raw')),
                                            'collects': 0, 'comments': 0, 'detail_publish_time': normalize_publish_time(c.get('time_raw'))})
            result['summary'].update({'detail_success': ok_detail, 'detail_total': actual})
            result['ok'] = len(result['notes']) > 0
            if not result['ok']:
                result['error'] = result.get('error') or 'NO_DETAIL'
            return result
        finally:
            try:
                page.close()
            except Exception:
                pass
            # CDP 模式绝不 browser.close()，保留持久 Edge 登录态


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keyword', required=True)
    ap.add_argument('--output', default='')
    ap.add_argument('--max-scroll', type=int, default=3)
    ap.add_argument('--max-details', type=int, default=10)
    ap.add_argument('--cdp-url', default=CDP_URL)
    args = ap.parse_args()
    t0 = time.time()
    try:
        res = collect(args.keyword, args.max_scroll, args.max_details, args.cdp_url)
    except Exception as e:
        res = {'ok': False, 'keyword': args.keyword, 'notes': [], 'error': f'CDP_EXCEPTION: {e}', 'summary': {}}
    res['elapsed'] = round(time.time() - t0, 1)
    if args.output:
        try:
            import os
            os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log(f'写输出失败: {e}')
    print('\n---RESULT_JSON---')
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if res.get('ok') else 1)


if __name__ == '__main__':
    main()
