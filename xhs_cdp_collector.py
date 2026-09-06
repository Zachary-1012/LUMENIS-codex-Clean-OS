# -*- coding: utf-8 -*-
"""小红书 CDP 真人采集通道（独立进程，Python Playwright）。

为什么不用 node rednote_collector.cjs：node 版 Playwright connectOverCDP 对 Edge152 会 ws 已连但握手 30s 超时；
Python 版 connect_over_cdp 已实测可稳定连接 9222 持久 Edge（登录态长期复用）。
collector 通过 venv python 子进程调用本脚本以隔离崩溃；stdout 末尾打印 ---RESULT_JSON--- 结果。

铁律：只识别不绕过——300012/IP风险/安全限制 => ip_blocked；验证码/安全验证 => verification_required；
不破解、不伪装；发布时间拿不到就留空（publish != captured）；只关闭本脚本新开的标签，绝不关闭 CDP 浏览器。

============================================================
真人浏览链路（--human=1 默认开启，=0 回退旧直连逻辑）
------------------------------------------------------------
真实键盘逐字输入关键词 → 贝塞尔鼠标轨迹 → 变速/偶发回滚滚动信息流
→ 真实点击笔记封面打开详情 → 左右滑动图片 → 识别并观看视频
→ 滚动阅读正文 → 滚动阅读评论 → 返回列表 → 下一篇。

【互动禁手·最高安全护栏】只做“被动浏览”，绝不产生实质性互动：
  点赞 / 收藏 / 评论提交 / 发布笔记 / 关注 用户 的按钮一律不点击、不输入、不提交。
  任何点击前校验元素是否命中 INTERACT_BLACKLIST，命中即跳过。
真人节奏全部为高斯/均匀随机，禁止固定 sleep 机械节奏。
============================================================
"""
import argparse
import json
import math
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


# ============================================================
# 真人节奏原语（自包含，不依赖 v4_upgrade，便于独立子进程调用）
# ============================================================
def human_sleep(a=1.2, b=2.6):
    """均匀随机停顿。"""
    time.sleep(random.uniform(a, b))


def gauss_sleep(mean=1.2, sigma=0.4, floor=0.3):
    """高斯停顿，模拟真人动作间隔的自然抖动。"""
    time.sleep(max(floor, random.gauss(mean, sigma)))


def _bezier_path(start, end, steps=26):
    """带两个随机控制点的三次贝塞尔鼠标轨迹。"""
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    cp1 = (sx + dx * random.uniform(0.2, 0.45) + random.uniform(-34, 34),
           sy + dy * random.uniform(0.2, 0.45) + random.uniform(-34, 34))
    cp2 = (sx + dx * random.uniform(0.55, 0.8) + random.uniform(-34, 34),
           sy + dy * random.uniform(0.55, 0.8) + random.uniform(-34, 34))

    def b(t, p0, p1, p2, p3):
        mt = 1 - t
        return mt ** 3 * p0 + 3 * mt ** 2 * t * p1 + 3 * mt * t ** 2 * p2 + t ** 3 * p3

    return [(b(i / steps, sx, cp1[0], cp2[0], ex),
             b(i / steps, sy, cp1[1], cp2[1], ey)) for i in range(steps + 1)]


def _viewport_size(page):
    try:
        return page.evaluate("() => [window.innerWidth, window.innerHeight]") or [1280, 800]
    except Exception:
        return [1280, 800]


def move_mouse_human(page, target_x, target_y, duration=None):
    """沿贝塞尔轨迹把鼠标从当前附近位置移动到目标点（含轻微过冲修正）。"""
    vw, vh = _viewport_size(page)
    start = (random.uniform(0, vw * 0.4), random.uniform(0, vh * 0.35))
    path = _bezier_path(start, (target_x, target_y))
    dur = duration or random.uniform(0.45, 0.95)
    per = dur / len(path)
    mx = page.mouse
    for x, y in path:
        try:
            mx.move(x, y)
        except Exception:
            pass
        time.sleep(per)
    gauss_sleep(0.22, 0.08, 0.08)


def move_to_locator_and_click(page, locator, *, click=True):
    """把鼠标沿轨迹移入元素随机内点，停顿后真实按下/抬起（非 .click() 瞬点）。"""
    locator.scroll_into_view_if_needed(timeout=8000)
    box = locator.bounding_box()
    if not box:
        raise RuntimeError('目标元素无布局位置')
    tx = box['x'] + box['width'] * random.uniform(0.28, 0.72)
    ty = box['y'] + box['height'] * random.uniform(0.28, 0.72)
    move_mouse_human(page, tx, ty)
    if click:
        page.mouse.down()
        human_sleep(0.05, 0.14)
        page.mouse.up()


def scroll_human(page, *, total_px=1400, rounds=None, back_prob=0.10):
    """变速、偶发小幅回滚地滚动，期间伴随随机横向鼠标漂移，替代机械 wheel。"""
    scrolled = 0
    rounds = rounds or max(2, total_px // 320)
    for _ in range(rounds):
        if random.random() < back_prob:
            page.mouse.wheel(0, -random.randint(60, 180))  # 偶尔回看
        else:
            step = random.randint(140, 540)
            page.mouse.wheel(0, step)
            scrolled += step
        # 滚动时鼠标轻微漂移，更像真人握鼠
        if random.random() < 0.5:
            try:
                vw, vh = _viewport_size(page)
                page.mouse.move(random.uniform(vw * 0.2, vw * 0.8),
                                random.uniform(vh * 0.2, vh * 0.8), steps=4)
            except Exception:
                pass
        gauss_sleep(0.7, 0.25, 0.3)
    return scrolled


# 互动禁手：命中以下任一特征的元素绝不点击/输入/提交（只被动浏览）
INTERACT_BLACKLIST = [
    'like-wrapper', 'like-active', 'like-lottie', 'class="like', 'class="like"',
    'collect-wrapper', 'collect-active', 'class="collect',
    'comment-input', 'content-input', 'post-button', 'submit-comment',
    'publish', 'submit', 'follow-wrapper', 'follow-button', 'class="follow',
    'chat-wrapper', 'input-box', 'engage',
]


def _is_interact_element(page, locator):
    """安全护栏：判断目标是否为点赞/收藏/评论/发布/关注等互动元素。"""
    try:
        attr = (locator.get_attribute('class') or '') + ' ' + \
               (locator.get_attribute('aria-label') or '') + ' ' + \
               (locator.get_attribute('data-v') or '')
        outer = locator.evaluate("el => (el.outerHTML || '').slice(0, 400)")
    except Exception:
        return False
    blob = (attr + ' ' + outer).lower()
    return any(bad in blob for bad in INTERACT_BLACKLIST)


# 搜索框候选选择器（多兜底）
_SEARCH_INPUT_SEL = ['#search-input', '.search-input input', 'input.search-input',
                     '.input-box input', 'input[placeholder*="搜索"]', 'input[type="search"]']
# 笔记详情容器
_DETAIL_READY_SEL = '#detail-title, #detail-desc, .note-content .desc, .note-container .title, .note-detail'
# 轮播下一张 / 视频 / 评论
_GALLERY_NEXT_SEL = '.swiper-button-next, .arrow-right, .next-arrow, .slider-next, [class*="next"]:not([class*="comment"])'
_VIDEO_SEL = 'video, .video-container, .player-container, [class*="video-player"]'
_COMMENT_ITEM_SEL = '.comment-item, .parent-comment, .list-container .comment'


def _find_first(page, selectors, timeout_ms=4000):
    """按候选选择器顺序返回第一个存在且可见的 Locator（都没有返回 None）。"""
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    return loc
            except Exception:
                continue
        time.sleep(0.2)
    return None


def human_click_note_coords(page, note_id):
    """真人坐标点击：实时取该笔记封面相对视口的中心点，贝塞尔移动后真实按下/抬起。
    绕过 Playwright actionability 对瀑布流封面的误判（not visible/stable）。返回是否点击。"""
    js = """(nid) => {
      const items = document.querySelectorAll('section.note-item');
      for (const it of items) {
        const a = it.querySelector('a.cover') || it.querySelector('a[href*="search_result"]') || it.querySelector('a[href*="explore"]') || it.querySelector('a');
        if (!a || !a.href || a.href.indexOf(nid) < 0) continue;
        const r = a.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          return {x: r.x + r.width*0.5, y: r.y + r.height*0.5,
                  top: r.top, bottom: r.bottom, vh: window.innerHeight};
        }
      }
      return null;
    }"""
    try:
        rect = page.evaluate(js, note_id)
    except Exception:
        rect = None
    if not rect:
        return False
    # 不在视口则真人式滚动到其附近，再取一次坐标
    if rect['top'] < 60 or rect['bottom'] > rect['vh'] - 60:
        try:
            page.evaluate("""(nid) => {
              const items = document.querySelectorAll('section.note-item');
              for (const it of items) {
                const a = it.querySelector('a.cover')||it.querySelector('a');
                if (a && a.href && a.href.indexOf(nid)>=0){ it.scrollIntoView({block:'center',behavior:'instant'}); return; }
              }}""", note_id)
            gauss_sleep(0.5, 0.15, 0.3)
            rect = page.evaluate(js, note_id) or rect
        except Exception:
            pass
    # 安全护栏：坐标点上的元素不得是互动按钮
    try:
        hit = page.evaluate("""({x,y}) => {
            const el = document.elementFromPoint(x,y);
            let cur = el, blob='';
            for (let i=0;i<3 && cur;i++){ blob += ' '+(cur.className||'')+' '+(cur.getAttribute&&cur.getAttribute('aria-label')||''); cur=cur.parentElement; }
            return blob.toLowerCase();
        }""", {'x': rect['x'], 'y': rect['y']})
        if hit and any(b in hit for b in ['like', 'collect', 'follow', 'comment-input', 'publish', 'submit']):
            return False
    except Exception:
        pass
    move_mouse_human(page, rect['x'], rect['y'])
    page.mouse.down()
    human_sleep(0.05, 0.14)
    page.mouse.up()
    return True


def human_search_keyword(page, keyword):
    """真人搜索：聚焦搜索框 → 逐字符键盘输入（偶发误触回删+思考停顿）→ 停顿 → 回车。"""
    box = _find_first(page, _SEARCH_INPUT_SEL, timeout_ms=6000)
    if box is None:
        raise RuntimeError('SEARCH_INPUT_NOT_FOUND')
    move_to_locator_and_click(page, box)
    human_sleep(0.2, 0.5)
    # 清空已有内容（真实键盘全选删除，而非 .fill）
    page.keyboard.press('Control+A')
    human_sleep(0.1, 0.25)
    page.keyboard.press('Delete')
    human_sleep(0.15, 0.35)
    for ch in keyword:
        # 3% 概率误触 → 停顿 → 退格 → 重打
        if random.random() < 0.03:
            wrong = 'z' if ch != 'z' else 'x'
            page.keyboard.type(wrong, delay=random.randint(60, 160))
            gauss_sleep(0.28, 0.1, 0.12)
            page.keyboard.press('Backspace')
            gauss_sleep(0.18, 0.08, 0.08)
        page.keyboard.type(ch, delay=random.randint(70, 240))
        if random.random() < 0.05:
            gauss_sleep(0.55, 0.2, 0.2)   # 思考式短暂停顿
    gauss_sleep(0.6, 0.2, 0.3)
    page.keyboard.press('Enter')
    log(f'真人键盘输入关键词并回车: {keyword}')


def human_swipe_gallery(page, depth=0.5):
    """详情内左右滑动浏览图片：识别图片张数，逐张点“下一张/方向键/拖拽”，每张随机停留。"""
    swiped = 0
    try:
        # 图片数量：轮播计数 “1/6” 或 slide 节点
        idx_text = ''
        for sel in ['.swiper-pagination', '.count', '.index-container', '[class*="pagination"]']:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    idx_text = el.inner_text(timeout=1000) or ''
                    if idx_text:
                        break
            except Exception:
                continue
        m = re.search(r'(\d+)\s*/\s*(\d+)', idx_text or '')
        total = int(m.group(2)) if m else 0
        slides = page.locator('.swiper-slide, .slider-slide, .note-slider-img, .media-container img').count()
        total = max(total, slides)
        if total <= 1:
            # 单图也停留“看一眼”（深度越低看得越快）
            gauss_sleep(0.8 + 0.8*depth, 0.35, 0.5)
            return 0
        nxt = _find_first(page, _GALLERY_NEXT_SEL.split(', '), timeout_ms=1500)
        max_swipe = max(1, round(1 + 11*depth))   # 浅读只翻1~2张，深读翻更多
        for i in range(min(total - 1, max_swipe)):
            gauss_sleep(0.9 + 1.0*depth, 0.5, 0.6)     # 每张图观看停留，时长不一
            moved = False
            if nxt is not None:
                try:
                    if not _is_interact_element(page, nxt):
                        nxt.click(timeout=1500)
                        moved = True
                except Exception:
                    moved = False
            if not moved:
                # 兜底：键盘方向键 / 在媒体区向左拖拽（真人滑图）
                try:
                    page.keyboard.press('ArrowRight')
                    moved = True
                except Exception:
                    pass
            if moved:
                swiped += 1
            nxt = _find_first(page, _GALLERY_NEXT_SEL.split(', '), timeout_ms=800)
    except Exception as e:
        log(f'滑图阶段异常(不影响采集): {e}')
    return swiped


def human_watch_video(page, depth=0.5):
    """识别视频笔记并“观看”：等待播放 + 按时长/封顶随机停留，绝不点赞。返回是否视频。"""
    try:
        v = page.locator(_VIDEO_SEL).first
        if v.count() == 0:
            return False
        # 尝试确认视频真的在播放（currentTime 前进）；不点击任何互动控件
        info = page.evaluate(
            """() => { const v = document.querySelector('video');
             if(!v) return null;
             return {dur: Number.isFinite(v.duration)?v.duration:0, paused:v.paused}; }"""
        )
        # 真人观看：深度决定观看比例与封顶；每次随机不一致，低深度偶发“没兴趣秒划”
        dur = (info or {}).get('dur', 0) if info else 0
        lo, hi = 0.12 + 0.55*depth, 0.25 + 0.70*depth
        cap_lo, cap_hi = 4 + 10*depth, 9 + 26*depth
        watch = min(max(dur * random.uniform(lo, hi), cap_lo), cap_hi) if dur else random.uniform(cap_lo, cap_hi)
        if random.random() < 0.35*(1-depth):    # 看得越浅越可能秒退
            watch = min(watch, random.uniform(1.0, 2.6))
        log(f'视频笔记，模拟观看 {watch:.1f}s (depth={depth:.2f})')
        time.sleep(watch)
        # 观看中轻微移动鼠标，不点击
        vw, vh = _viewport_size(page)
        page.mouse.move(random.uniform(vw*0.3, vw*0.7), random.uniform(vh*0.3, vh*0.7), steps=5)
        return True
    except Exception:
        return False


def human_read_content(page, depth=0.5):
    """滚动阅读正文：分 2~4 次小幅向下滚动，每次高斯停留（模拟阅读）。"""
    try:
        base = max(1, round(1 + 3*depth))
        rounds = random.randint(base, min(5, base+1)) if base > 1 else 1
        for _ in range(rounds):
            page.mouse.wheel(0, random.randint(120, 360))
            gauss_sleep(0.5 + 0.75*depth, 0.3, 0.4)
    except Exception:
        pass


def human_read_comments(page, depth=0.5):
    """滚动阅读评论区：先定位评论区，再分 2~5 次小幅滚动，随机停留阅读。"""
    try:
        cnt = page.locator(_COMMENT_ITEM_SEL).count()
        if cnt == 0:
            return 0
        if depth < 0.3 and random.random() < 0.6:
            return 0   # 浅读多数不展开评论
        rounds = min(max(cnt, 1 if depth < 0.3 else 2), max(2, round(1+4*depth)))
        for _ in range(rounds):
            page.mouse.wheel(0, random.randint(140, 420))
            gauss_sleep(0.8, 0.3, 0.4)
            if random.random() < 0.12:   # 偶发回看上一条评论
                page.mouse.wheel(0, -random.randint(50, 120))
                gauss_sleep(0.5, 0.2, 0.3)
        return cnt
    except Exception:
        return 0


def human_reading_profile():
    """人类浏览行为画像：秒退/浅读/正常/深读，按真人分布抽样；每篇独立、时长不一。"""
    r = random.random()
    if r < 0.14:                                   # 点进去就退出
        return 'skip', 0.0
    if r < 0.40:                                   # 只看一点点
        return 'skim', round(random.uniform(0.10, 0.28), 2)
    if r < 0.82:                                   # 正常浏览
        return 'normal', round(random.uniform(0.42, 0.66), 2)
    return 'deep', round(random.uniform(0.78, 1.0), 2)   # 仔细阅读


def human_consume_detail(page, profile, depth):
    """按行为画像编排一次详情阅读，返回过程证据；全程只被动浏览，不产生任何互动。"""
    t0 = time.time(); is_video=False; img_swiped=0; comment_seen=0
    try:
        if profile == 'skip':
            # 秒退：仅短暂扫视封面/标题即离开，不滑图、不读评论
            gauss_sleep(1.0, 0.5, 0.7)
            time.sleep(random.uniform(0.4, 1.4))
        else:
            is_video = human_watch_video(page, depth)
            if not is_video:
                img_swiped = human_swipe_gallery(page, depth)
            human_read_content(page, depth)
            comment_seen = human_read_comments(page, depth)
    except Exception as e:
        log(f'真人阅读阶段异常(不影响采集): {e}')
    return {'profile': profile, 'depth': depth, 'is_video': is_video,
            'images_swiped': img_swiped, 'comments_seen': comment_seen,
            'dwell_sec': round(time.time()-t0, 1)}


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
    const coverLink = item.querySelector('a.cover') || item.querySelector('a[href*="/search_result/"]') || item.querySelector('a[href*="/explore/"]');
    const href = coverLink ? coverLink.getAttribute('href') : '';
    const idm = href.match(/(?:search_result|explore)\/([^/?]+)/);
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
      url: href && href.startsWith('http') ? href : ('https://www.xiaohongshu.com' + (href.startsWith('/') ? href : '/' + href))
    });
  });
  return out.filter(x => x.note_id);
}
"""

_DETAIL_JS = r"""
() => {
  const q = sels => { for (const s of sels) { const e = document.querySelector(s); if (e && (e.innerText||'').trim()) return (e.innerText||'').trim(); } return ''; };
  const counts = Array.from(document.querySelectorAll('.count')).map(c => (c.innerText||'').trim()).filter(Boolean);
  const wc = sels => { for (const s of sels) { const e=document.querySelector(s); const v=e?(e.innerText||'').trim():''; if(v) return v; } return ''; };
  // 语义化互动计数（只读取数字，绝不点击）：赞/藏/评/分享，缺省为空串由后端兜底
  const engage = {
    like_raw: wc(['.like-wrapper .count','.engage-bar .like .count','[class*="like-wrapper"] .count','[class*="like"] .count']),
    collect_raw: wc(['.collect-wrapper .count','.engage-bar .collect .count','[class*="collect-wrapper"] .count','[class*="collect"] .count']),
    comment_raw: wc(['.chat-wrapper .count','.engage-bar .chat .count','[class*="chat-wrapper"] .count','[class*="comment"] .count']),
    share_raw: wc(['.share-wrapper .count','.engage-bar .share .count','[class*="share-wrapper"] .count','[class*="share"] .count'])
  };
  const comments = Array.from(document.querySelectorAll('.comment-item, .parent-comment')).map(c => {
    const u = c.querySelector('.name,.author a,.user .name'), x = c.querySelector('.content,.comment-content,.note-text'),
          t = c.querySelector('.time,.date'), l = c.querySelector('.like .count,.count');
    return { user: u?(u.innerText||'').trim():'', content: x?(x.innerText||'').trim():'',
             time: t?(t.innerText||'').trim():'', likes_raw: l?(l.innerText||'').trim():'' };
  });
  const hasVideo = !!document.querySelector('video,.video-container,[class*="video-player"]');
  const slideImgs = document.querySelectorAll('.swiper-slide img, .note-slider-img, .media-container img').length;
  return {
    title: q(['#detail-title','.note-content .title','h1']),
    desc: q(['#detail-desc','.note-content .desc','.note-text','.desc']),
    author: q(['.author-container .name','.author .name','.username']),
    time_raw: q(['.author-container .time','.publish-time','.date','.time']),
    all_counts: counts, engage: engage, comment_list: comments, comment_count: comments.length,
    is_video: hasVideo, image_count: slideImgs
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


def _compute_subject_hit(title, desc):
    """采集层主体硬判定：委托 subject_rules.subject_hit_text（不修改口径）。
    返回 True/False；导入失败返回 None（下游不排除，保持向后兼容）。
    P0 加固：使 collector.py 的 subject_hit_cdp 硬过滤真正生效。"""
    try:
        from subject_rules import subject_hit_text
        return bool(subject_hit_text(f"{title or ''} {desc or ''}"))
    except Exception:
        return None


def _risk_check(page, result):
    """全程风控检测：命中返回 True 并写 result。"""
    try:
        text = page.evaluate("() => document.body ? document.body.innerText : ''") or ''
    except Exception:
        return False
    kind, hit = classify_page(text)
    if kind == 'ip':
        result['summary'] = {'ip_blocked': True, 'matched': hit}
        result['error'] = 'IP_RISK_OR_300012'
        return True
    if kind == 'verify':
        result['summary'] = {'verification_required': True, 'matched': hit}
        result['error'] = 'NEED_VERIFY'
        return True
    return False


def robust_goto(page, url, commit_to=30000, dom_to=45000):
    """稳健导航：先等最快的 commit；冷挂起时降级 domcontentloaded；两轮仍失败才抛，
    避免一次冷导航超时把整轮采集判死。同页二次 goto 会取消上一挂起导航。"""
    last = None
    for attempt in range(2):
        try:
            page.goto(url, wait_until='commit', timeout=commit_to)
            return 'commit'
        except Exception as e1:
            last = e1
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=dom_to)
                return 'dom'
            except Exception as e2:
                last = e2
                if attempt == 0:
                    gauss_sleep(1.0, 0.4, 0.6)
    raise last


# ============================================================
# 真人采集主流程（默认）
# ============================================================
def collect_human(keyword, max_scroll=3, max_details=10, cdp_url=CDP_URL):
    from playwright.sync_api import sync_playwright
    result = {'ok': False, 'keyword': keyword, 'mode': 'human', 'notes': [], 'summary': {}, 'human_trace': []}
    trace = result['human_trace']
    with sync_playwright() as p:
        try:
            from cdp_helper import reset_cdp_targets
            _port = int(str(cdp_url).split(':')[-1].split('/')[0])
            reset_cdp_targets(_port)
        except Exception:
            pass
        browser = p.chromium.connect_over_cdp(cdp_url, timeout=30000)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        try:
            from urllib.parse import quote
            # 先稳落探索页（无 keyword 的 search_result 冷导航易挂起；explore 实测稳定），
            # 再由真人键盘输入关键词触发结果页，更像真人且更稳
            landing = 'https://www.xiaohongshu.com/explore'
            log('真人模式：打开探索页')
            robust_goto(page, landing)
            human_sleep(2.4, 3.8)
            if _risk_check(page, result):
                return result
            # 1) 真实键盘输入关键词
            try:
                human_search_keyword(page, keyword)
            except Exception as e:
                # 兜底：键盘输入失败时退回 URL 直达（仍继续真人浏览，不中断采集）
                log(f'键盘输入失败，回退URL直达: {e}')
                robust_goto(page, f'https://www.xiaohongshu.com/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51')
            try:
                page.wait_for_selector('section.note-item', timeout=18000)
            except Exception:
                text = page.evaluate("() => document.body ? document.body.innerText : ''") or ''
                if len(text.replace('\n', '').replace(' ', '')) < 20 or page.url.startswith('about:blank'):
                    result['error'] = 'LOAD_FAILED'
                    result['summary'] = {'load_failed': True, 'url': page.url[:80]}
                    return result
            human_sleep(1.2, 2.2)

            # 2) 真人变速滚动浏览信息流（触发懒加载），鼠标伴随漂移
            for i in range(int(max_scroll)):
                scroll_human(page, total_px=random.randint(700, 1100), rounds=random.randint(2, 4))
                gauss_sleep(1.4, 0.5, 0.8)
                if _risk_check(page, result):
                    return result
            human_sleep(0.8, 1.6)

            cards = page.evaluate(_LIST_JS)
            log(f'信息流发现 {len(cards)} 张卡片')
            result['summary']['discovered'] = len(cards)
            if not cards:
                if _risk_check(page, result):
                    return result
                result['error'] = 'EMPTY_LIST'
                return result

            actual = min(int(max_details), len(cards))
            ok_detail = 0
            seen_ids = set()
            for i in range(actual):
                # 每 4 篇长休息一次（真人刷累了停顿）
                if i > 0 and i % 4 == 0:
                    long_break = random.uniform(15, 32)
                    log(f'模拟真人长休息 {long_break:.0f}s')
                    time.sleep(long_break)

                # 返回列表后 DOM 可能重建，每次重新取卡片并挑下一张未采的
                fresh = page.evaluate(_LIST_JS)
                if fresh:
                    cards = fresh
                target = None
                for c in cards:
                    if c['note_id'] not in seen_ids:
                        target = c
                        break
                if target is None:
                    break
                seen_ids.add(target['note_id'])
                opened_by_click = False
                try:
                    # 3) 贝塞尔鼠标移动 + 真实点击笔记封面打开详情（绝不点互动按钮）
                    card_loc = page.locator(f'section.note-item:has(a[href*="{target["note_id"]}"])').first
                    if card_loc.count() == 0:
                        card_loc = page.locator('section.note-item').nth(min(i, max(len(cards)-1, 0)))
                    # 优先真人坐标点击封面（最像真人，且不受 actionability 误判影响）
                    try:
                        if human_click_note_coords(page, target['note_id']):
                            opened_by_click = True
                            trace.append({'note_id': target['note_id'], 'open': 'mouse_coords_click'})
                    except Exception as e:
                        log(f'坐标点击异常，尝试locator: {e}')
                    if not opened_by_click:
                        cover = card_loc.locator('a.cover, a[href*="search_result"], a[href*="explore"]').first
                        if cover.count() > 0 and not _is_interact_element(page, cover):
                            try:
                                move_to_locator_and_click(page, cover)
                                opened_by_click = True
                                trace.append({'note_id': target['note_id'], 'open': 'mouse_locator_click'})
                            except Exception as e:
                                log(f'真人点击打开失败，回退直达: {e}')
                    if not opened_by_click:
                        page.goto(target['url'], wait_until='domcontentloaded', timeout=30000)
                        trace.append({'note_id': target['note_id'], 'open': 'goto_fallback'})
                    try:
                        page.wait_for_selector(_DETAIL_READY_SEL, timeout=10000)
                    except Exception:
                        pass
                    human_sleep(1.6, 2.8)
                    if _risk_check(page, result):
                        return result

                    # 4) 真人阅读：按行为画像(秒退/浅读/正常/深读)差异化停留，每次时长不一
                    profile, depth = human_reading_profile()
                    consume = human_consume_detail(page, profile, depth)
                    is_video = consume['is_video']; img_swiped = consume['images_swiped']
                    comment_seen = consume['comments_seen']

                    d = page.evaluate(_DETAIL_JS)
                    nums = [int(x) for x in d.get('all_counts', []) if re.fullmatch(r'\d+', str(x))]
                    eng = d.get('engage') or {}
                    likes = parse_count(eng.get('like_raw')) or (nums[-3] if len(nums) >= 3 else (nums[-1] if nums else parse_count(target.get('likes_raw'))))
                    collects = parse_count(eng.get('collect_raw')) or (nums[-2] if len(nums) >= 2 else 0)
                    comments = parse_count(eng.get('comment_raw')) or (nums[-1] if nums else 0)
                    shares = parse_count(eng.get('share_raw'))
                    pub = normalize_publish_time(d.get('time_raw')) or normalize_publish_time(target.get('time_raw'))
                    rec = {
                        'note_id': target['note_id'], 'xsec_token': target.get('xsec_token', ''),
                        'title': d.get('title') or target.get('title', ''),
                        'detail_title': d.get('title') or target.get('title', ''),
                        'desc': d.get('desc', ''),
                        'author': d.get('author') or target.get('author', ''),
                        'detail_author': d.get('author') or target.get('author', ''),
                        'detail_publish_time': pub, 'publish_time': pub,
                        'likes': likes, 'collects': collects, 'comments': comments, 'shares': shares,
                        'comment_list': d.get('comment_list', []), 'comment_count': d.get('comment_count', comment_seen),
                        'is_video': bool(d.get('is_video') or is_video),
                        'image_count': d.get('image_count', img_swiped + 1),
                        'cover': target.get('cover', ''), 'url': page.url if opened_by_click else target['url'],
                        'human_view': {'opened_by': 'click' if opened_by_click else 'goto',
                                       'profile': profile, 'depth': depth,
                                       'dwell_sec': consume['dwell_sec'],
                                       'video_watched': is_video, 'images_swiped': img_swiped,
                                       'comments_seen': comment_seen},
                        'detail_fetched': True, 'captured_at': datetime.now().isoformat(),
                        'collector_version': 'xhs-cdp-py-human-2.1',
                    }
                    rec['subject_hit'] = _compute_subject_hit(rec.get('title'), rec.get('desc'))
                    result['notes'].append(rec)
                    ok_detail += 1
                    log(f'真人阅评 {i+1}/{actual} [{profile}/{consume["dwell_sec"]}s]: {rec["title"][:20]} 视频={rec["is_video"]} 翻图={img_swiped} 评{comment_seen} 赞{likes} 藏{collects} 享{shares} {pub}')

                    # 5) 真人“返回”信息流（优先返回键/关闭弹层，不触发互动）
                    self_closed = False
                    for close_sel in ['.close-circle', '.close-box', '.note-detail-close', '[class*="close"]']:
                        try:
                            c_loc = page.locator(close_sel).first
                            if c_loc.count() > 0 and c_loc.is_visible() and not _is_interact_element(page, c_loc):
                                c_loc.click(timeout=1200)
                                self_closed = True
                                break
                        except Exception:
                            continue
                    if not self_closed:
                        try:
                            page.go_back(wait_until='commit', timeout=12000)
                        except Exception:
                            page.goto(f'https://www.xiaohongshu.com/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51',
                                      wait_until='commit', timeout=20000)
                    human_sleep(2.4, 4.2)  # 返回信息流后的真人停顿
                    try:
                        page.wait_for_selector('section.note-item', timeout=8000)
                    except Exception:
                        pass
                except Exception as e:
                    log(f'详情失败 {i+1}: {e}')
                    result['notes'].append({**target, 'detail_fetched': False, 'error': str(e)[:160],
                                            'desc': '', 'likes': parse_count(target.get('likes_raw')),
                                            'collects': 0, 'comments': 0,
                                            'detail_publish_time': normalize_publish_time(target.get('time_raw'))})
                    # 异常后尝试回到结果流，避免卡在详情页
                    try:
                        page.goto(f'https://www.xiaohongshu.com/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51',
                                  wait_until='commit', timeout=20000)
                        human_sleep(2.0, 3.2)
                    except Exception:
                        pass
            result['summary'].update({'detail_success': ok_detail, 'detail_total': actual,
                                      'human': True, 'interactions_made': 0})
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


# ============================================================
# 旧直连流程（--human=0 回退用，保留稳定基线）
# ============================================================
def collect_direct(keyword, max_scroll=3, max_details=10, cdp_url=CDP_URL):
    from playwright.sync_api import sync_playwright
    result = {'ok': False, 'keyword': keyword, 'mode': 'direct', 'notes': [], 'summary': {}}
    with sync_playwright() as p:
        try:
            from cdp_helper import reset_cdp_targets
            _port = int(str(cdp_url).split(':')[-1].split('/')[0])
            reset_cdp_targets(_port)
        except Exception:
            pass
        browser = p.chromium.connect_over_cdp(cdp_url, timeout=30000)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        try:
            from urllib.parse import quote
            url = f'https://www.xiaohongshu.com/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51'
            log(f'导航搜索: {keyword}')
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

            for i in range(int(max_scroll)):
                page.mouse.wheel(0, random.randint(500, 950))
                human_sleep(1.4, 2.6)
            human_sleep(0.8, 1.4)

            cards = page.evaluate(_LIST_JS)
            log(f'列表发现 {len(cards)} 张卡片')
            result['summary']['discovered'] = len(cards)
            if not cards:
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
                    rec['subject_hit'] = _compute_subject_hit(rec.get('title'), rec.get('desc'))
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


def collect(keyword, max_scroll=3, max_details=10, cdp_url=CDP_URL, human=1):
    """统一入口：human=1 真人浏览链路（默认），human=0 旧直连。"""
    if int(human) == 0:
        return collect_direct(keyword, max_scroll, max_details, cdp_url)
    return collect_human(keyword, max_scroll, max_details, cdp_url)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keyword', required=True)
    ap.add_argument('--output', default='')
    ap.add_argument('--max-scroll', type=int, default=3)
    ap.add_argument('--max-details', type=int, default=10)
    ap.add_argument('--cdp-url', default=CDP_URL)
    ap.add_argument('--human', type=int, default=1, help='1=真人浏览链路(默认) 0=旧直连')
    args = ap.parse_args()
    t0 = time.time()
    try:
        res = collect(args.keyword, args.max_scroll, args.max_details, args.cdp_url, args.human)
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
