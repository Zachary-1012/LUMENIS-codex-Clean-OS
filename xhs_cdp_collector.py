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
import hmac
import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urlsplit

CDP_URL = os.getenv('XHS_CDP_URL', '').strip()
COLLECTION_HOST = os.environ.get('XHS_COLLECTION_HOST', 'www.rednote.com').strip().lower()
COLLECTION_ORIGIN = f'https://{COLLECTION_HOST}'


def _assert_collection_host():
    """只允许香港/国际 RedNote 主机，避免 Cookie/CDP 与大陆站点错配。"""
    if COLLECTION_HOST != 'www.rednote.com':
        raise RuntimeError('当前生产采集仅允许香港/国际 RedNote 主机 www.rednote.com')

class CollectionIdentityError(RuntimeError):
    """Safe failure stage, without identity, Cookie or endpoint values."""
    def __init__(self, code, stage):
        super().__init__(code)
        self.stage = stage


def _assert_collection_identity(context, *, expected_user_id=None):
    """Verify the existing RedNote UI identifies the approved HK account."""
    expected = (expected_user_id if expected_user_id is not None else
                os.environ.get('XHS_EXPECTED_COLLECTION_USER_ID', '')).strip()
    if not expected:
        raise CollectionIdentityError('COLLECTOR_IDENTITY_NOT_CONFIGURED','APPROVED_IDENTITY_NOT_CONFIGURED')
    try:
        cookies = context.cookies([COLLECTION_ORIGIN])
    except Exception as exc:
        raise CollectionIdentityError('COLLECTOR_IDENTITY_UNAVAILABLE','REGISTERED_CONTEXT_COOKIE_READ_FAILED') from exc
    cookie_names = {
        str(cookie.get('name') or '').lower()
        for cookie in cookies if str(cookie.get('value') or '').strip()
    }
    if 'web_session' not in cookie_names:
        raise CollectionIdentityError('COLLECTOR_IDENTITY_NOT_VERIFIED','WEB_SESSION_NOT_PRESENT')
    user_ids = {
        str(cookie.get('value') or '').strip()
        for cookie in cookies
        if cookie.get('name') == 'x-user-id-pro' and cookie.get('value')
    }
    if len(user_ids) > 1 or (user_ids and not hmac.compare_digest(next(iter(user_ids)), expected)):
        raise CollectionIdentityError('COLLECTOR_IDENTITY_MISMATCH','COOKIE_USER_ID_MISMATCH')
    holder_countries = {
        str(cookie.get('value') or '').strip().upper()
        for cookie in cookies
        if str(cookie.get('name') or '').lower() == 'x-rednote-holderctry' and cookie.get('value')
    }
    if holder_countries and holder_countries != {'HK'}:
        raise CollectionIdentityError('COLLECTOR_IDENTITY_MISMATCH','HOLDER_COUNTRY_MISMATCH')

    try:
        pages = getattr(context, 'pages', None) or []
        if not pages:
            raise CollectionIdentityError('COLLECTOR_IDENTITY_NOT_VERIFIED','NO_EXISTING_APPROVED_ORIGIN_PAGE')
        rednote_pages = []
        for page in pages:
            page_url = urlsplit(str(page.url or ''))
            if page_url.scheme == 'https' and page_url.hostname == 'www.rednote.com':
                rednote_pages.append(page)
        if not rednote_pages:
            raise CollectionIdentityError('COLLECTOR_IDENTITY_NOT_VERIFIED','NO_EXISTING_APPROVED_ORIGIN_PAGE')
        candidates = []
        for page in rednote_pages:
            candidates.extend(page.locator('a.link-wrapper, a.bottom-channel').evaluate_all(
                """els => els.map(el => ({
                    classes: Array.from(el.classList),
                    text: (el.innerText || el.textContent || '').trim(),
                    href: el.getAttribute('href') || ''
                }))"""
            ))
    except RuntimeError:
        raise
    except Exception as exc:
        raise CollectionIdentityError('COLLECTOR_IDENTITY_NOT_VERIFIED','SELF_NAVIGATION_READ_FAILED') from exc

    self_ids = set()
    for item in candidates or []:
        classes = set(item.get('classes') or [])
        text = re.sub(r'\s+', '', str(item.get('text') or ''))
        href = str(item.get('href') or '').strip()
        if text != '我' or not classes.intersection({'link-wrapper', 'bottom-channel'}):
            continue
        parsed = urlsplit(href)
        if parsed.scheme and (parsed.scheme != 'https' or parsed.hostname != 'www.rednote.com'):
            raise CollectionIdentityError('COLLECTOR_IDENTITY_MISMATCH','SELF_NAVIGATION_ORIGIN_MISMATCH')
        if parsed.netloc and parsed.netloc != 'www.rednote.com':
            raise CollectionIdentityError('COLLECTOR_IDENTITY_MISMATCH','SELF_NAVIGATION_ORIGIN_MISMATCH')
        match = re.fullmatch(r'/user/profile/([0-9a-fA-F]{24})/?', parsed.path)
        if not match:
            raise CollectionIdentityError('COLLECTOR_IDENTITY_MISMATCH','SELF_NAVIGATION_TARGET_INVALID')
        self_ids.add(match.group(1).lower())
    if not self_ids:
        raise CollectionIdentityError('COLLECTOR_IDENTITY_NOT_VERIFIED','SELF_NAVIGATION_NOT_OBSERVED')
    if len(self_ids) != 1 or not hmac.compare_digest(next(iter(self_ids)), expected.lower()):
        raise CollectionIdentityError('COLLECTOR_IDENTITY_MISMATCH','SELF_NAVIGATION_USER_ID_MISMATCH')


def _existing_collection_context(browser):
    """Use only a pre-existing approved browser context; never create one."""
    contexts = getattr(browser, 'contexts', None) or []
    if not contexts:
        raise RuntimeError('COLLECTOR_IDENTITY_CONTEXT_UNAVAILABLE')
    return contexts[0]


def _connect_verified_collection_context(playwright, cdp_url):
    """Connect read-only, then verify approved identity before creating any page."""
    browser = playwright.chromium.connect_over_cdp(cdp_url, timeout=30000)
    context = _existing_collection_context(browser)
    _assert_collection_identity(context)
    return browser, context

_IP_WORDS = ['300012', 'IP存在风险', 'ip存在风险', '安全限制', '访问受限', '当前访问出现异常', '网络有点忙', '操作频繁', '访问过于频繁']
_VERIFY_WORDS = ['验证码', '安全验证', '人机验证', '请完成验证', '请通过验证', '滑块', '拖动下方', 'captcha', '安全检测']
_LOGIN_LIMIT_WORDS = ('电脑设备登录超限',)


def log(msg):
    print(f'[xhs-cdp] {msg}', file=sys.stderr, flush=True)


# ============================================================
# 真人节奏原语（自包含，不依赖 lumenis，便于独立子进程调用）
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
    """Submit only after the controlled search field reads back the exact query."""
    box = _find_first(page, _SEARCH_INPUT_SEL, timeout_ms=6000)
    if box is None:
        raise RuntimeError('SEARCH_INPUT_NOT_FOUND')
    box.fill(keyword, timeout=6000)
    if box.input_value(timeout=6000) != keyword:
        raise RuntimeError('SEARCH_INPUT_VALUE_MISMATCH')
    box.press('Enter', timeout=6000)
    log('搜索框精确词条已读回并提交')


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


def human_read_content(page, depth=0.5, *, one_scroll=False):
    """滚动阅读正文：分 2~4 次小幅向下滚动，每次高斯停留（模拟阅读）。"""
    try:
        if one_scroll:
            page.mouse.wheel(0, 150)
            return
        base = max(1, round(1 + 3*depth))
        rounds = random.randint(base, min(5, base+1)) if base > 1 else 1
        for _ in range(rounds):
            page.mouse.wheel(0, random.randint(120, 360))
            gauss_sleep(0.5 + 0.75*depth, 0.3, 0.4)
    except Exception:
        pass


def human_read_comments(page, depth=0.5, *, loaded_only=False):
    """滚动阅读评论区：先定位评论区，再分 2~5 次小幅滚动，随机停留阅读。"""
    try:
        cnt = page.locator(_COMMENT_ITEM_SEL).count()
        if cnt == 0:
            return 0
        if loaded_only:
            return cnt
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


def human_consume_detail(page, profile, depth, detail_media_mode='legacy'):
    """按行为画像编排一次详情阅读，返回过程证据；全程只被动浏览，不产生任何互动。"""
    if not isinstance(detail_media_mode, str) or detail_media_mode not in {'legacy', 'cover_only'}:
        raise ValueError('INVALID_DETAIL_MEDIA_MODE')
    t0 = time.time(); video_watched=False; img_swiped=0; comment_seen=0
    try:
        if profile == 'skip':
            # 秒退：仅短暂扫视封面/标题即离开，不滑图、不读评论
            gauss_sleep(1.0, 0.5, 0.7)
            time.sleep(random.uniform(0.4, 1.4))
        else:
            if detail_media_mode == 'legacy':
                video_watched = human_watch_video(page, depth)
                if not video_watched:
                    img_swiped = human_swipe_gallery(page, depth)
            human_read_content(page, depth, one_scroll=detail_media_mode == 'cover_only')
            comment_seen = human_read_comments(page, depth, loaded_only=detail_media_mode == 'cover_only')
    except Exception as e:
        log(f'真人阅读阶段异常(不影响采集): {e}')
    return {'profile': profile, 'depth': depth, 'video_watched': video_watched,
            'images_swiped': img_swiped, 'comments_seen': comment_seen,
            'dwell_sec': round(time.time()-t0, 1), 'detail_media_mode': detail_media_mode}


def parse_count(s):
    if s is None or isinstance(s, bool):
        return None
    s = str(s).strip().lower().replace(',', '').replace(' ', '')
    if not s:
        return None
    m = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(万|w|千|k|亿|m|b)?', s)
    if not m:
        return None
    from decimal import Decimal
    num = Decimal(m.group(1))
    unit = m.group(2) or ''
    mul = {'万': 10000, 'w': 10000, '千': 1000, 'k': 1000, '亿': 100000000,
           'm': 1000000, 'b': 1000000000}.get(unit, 1)
    count = num * mul
    return int(count) if count == count.to_integral_value() else None


def _detail_metrics(detail, card):
    """Only labeled note metrics may fill note counts; comment likes cannot."""
    engage = detail.get('engage') or {}
    likes = parse_count(engage.get('like_raw'))
    if likes is None:
        likes = parse_count(card.get('likes_raw'))
    return {'likes': likes, 'collects': parse_count(engage.get('collect_raw')),
            'comments': parse_count(engage.get('comment_raw')),
            'shares': parse_count(engage.get('share_raw'))}


def _require_detail_observation(detail):
    if detail.get('detail_present') is not True:
        raise RuntimeError('DETAIL_CONTENT_UNAVAILABLE')


class RawCheckpointError(RuntimeError):
    pass


def _identity_fingerprint():
    import hashlib
    expected = os.environ.get('XHS_EXPECTED_COLLECTION_USER_ID', '').strip()
    return hashlib.sha256(expected.encode('utf-8')).hexdigest() if expected else ''


def _load_resume_checkpoint(path, keyword, acquisition_fingerprint=None):
    if not path:
        return None
    with open(path, encoding='utf-8') as source:
        previous = json.load(source)
    if not isinstance(previous, dict):
        raise RuntimeError('RESUME_INPUT_MISMATCH')
    checkpoint = previous.get('checkpoint') or {}
    if (previous.get('keyword') != keyword or checkpoint.get('source_host') != COLLECTION_HOST
            or previous.get('acquisition_fingerprint') != acquisition_fingerprint
            or checkpoint.get('acquisition_fingerprint') != acquisition_fingerprint
            or not _identity_fingerprint()
            or checkpoint.get('verified_identity_fingerprint') != _identity_fingerprint()
            or previous.get('identity_verified') is not True):
        raise RuntimeError('RESUME_INPUT_MISMATCH')
    return previous


def _completed_detail_ids(previous):
    if previous is None:
        return set()
    completed = {note['note_id'] for note in previous.get('notes', [])
                 if isinstance(note, dict) and note.get('detail_fetched') is True
                 and isinstance(note.get('note_id'), str) and note['note_id']}
    completed.update(value for value in previous.get('summary', {}).get('resumed_note_ids', [])
                     if isinstance(value, str) and value)
    return completed


def _resume_note_ids(path, keyword):
    return _completed_detail_ids(_load_resume_checkpoint(path, keyword))


def _validate_native_card(card):
    from urllib.parse import urlsplit
    if not isinstance(card, dict) or not re.fullmatch(r'[0-9a-fA-F]{24}', str(card.get('note_id') or '')):
        raise RuntimeError('NATIVE_PENDING_SOURCE_INVALID')
    try:
        url = urlsplit(str(card.get('url') or ''))
        match = re.fullmatch(r'/(?:explore|search_result|discovery/item)/([0-9a-fA-F]{24})/?', url.path)
        valid = (url.scheme == 'https' and url.hostname == COLLECTION_HOST
                 and url.port in (None, 443) and not url.username and not url.password
                 and match and match.group(1).lower() == card['note_id'].lower())
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError('NATIVE_PENDING_SOURCE_INVALID')
    return card


def _resume_pending_cards(previous, completed):
    if previous is None:
        return []
    pending = {}
    for card in previous.get('discovered_cards', []) + previous.get('notes', []):
        if isinstance(card, dict) and card.get('note_id') not in completed:
            _validate_native_card(card)
            pending.setdefault(card['note_id'], dict(card))
    recorded = (previous.get('summary') or {}).get('pending_note_ids', [])
    if any(note_id not in pending and note_id not in completed for note_id in recorded):
        raise RuntimeError('RESUME_PENDING_SOURCE_MISSING')
    return list(pending.values())


def _merge_native_cards(resume_cards, current_cards):
    merged = {}
    for card in (resume_cards or []) + current_cards:
        _validate_native_card(card)
        merged.setdefault(card['note_id'], dict(card))
    return list(merged.values())


def _require_detail_identity(detail, expected_note_id):
    from urllib.parse import urlsplit
    try:
        url = urlsplit(str(detail.get('source_page_url') or ''))
        valid = (url.scheme == 'https' and url.hostname == COLLECTION_HOST
                 and url.port in (None, 443) and not url.username and not url.password)
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError('DETAIL_SOURCE_UNVERIFIED')
    observed = detail.get('source_note_ids')
    if not isinstance(observed, list) or not observed:
        raise RuntimeError('DETAIL_IDENTITY_UNVERIFIED')
    if any(not isinstance(value, str) or value.lower() != expected_note_id.lower() for value in observed):
        raise RuntimeError('DETAIL_IDENTITY_MISMATCH')


def _update_detail_progress(result):
    completed = {note.get('note_id') for note in result['notes'] if note.get('detail_fetched') is True}
    completed.update(result['summary'].get('resumed_note_ids', []))
    pending = [card['note_id'] for card in result.get('discovered_cards', [])
               if card.get('note_id') and card['note_id'] not in completed]
    pending = list(dict.fromkeys(pending))
    result['summary'].update({'pending_note_ids': pending,
                              'pagination_exhausted': False,
                              'continuation_required': bool(pending)})


def _write_checkpoint(output, result, run_id, *, complete=False, checkpoint_override=None):
    """Atomically replace the existing Raw artifact after each observation."""
    if not output:
        return
    import tempfile
    folder = os.path.dirname(os.path.abspath(output))
    os.makedirs(folder, exist_ok=True)
    snapshot = dict(result)
    if checkpoint_override is None:
        snapshot['partial'] = not complete
        snapshot['checkpoint'] = {'run_id': run_id, 'source_host': COLLECTION_HOST,
                                  'complete': complete,
                                  'verified_identity_fingerprint': _identity_fingerprint() if result.get('identity_verified') else '',
                                  'written_at': datetime.now().astimezone().isoformat()}
        if result.get('acquisition_fingerprint'):
            snapshot['checkpoint']['acquisition_fingerprint'] = result['acquisition_fingerprint']
    else:
        snapshot['checkpoint'] = dict(checkpoint_override)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=folder,
                                         prefix='.xhs-raw-', suffix='.tmp', delete=False) as target:
            temporary = target.name
            json.dump(snapshot, target, ensure_ascii=False, indent=2)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, output)
    except OSError as exc:
        raise RawCheckpointError('RAW_CHECKPOINT_WRITE_FAILED') from exc
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return snapshot['checkpoint']


def _budget_reached(result, deadline, budget_kind='worker_chunk'):
    if deadline is None or time.monotonic() < deadline:
        return False
    result['partial'] = True
    summary = result.setdefault('summary', {})
    if budget_kind == 'worker_chunk':
        summary['worker_chunk_budget_reached'] = True
        _update_detail_progress(result)
        summary['continuation_required'] = True
        has_verified_detail = result.get('identity_verified') is True and any(
            isinstance(note, dict) and note.get('detail_fetched') is True
            for note in result.get('notes', []))
        if has_verified_detail and not result.get('error'):
            result['ok'] = True
        else:
            result['ok'] = False
            result['error'] = result.get('error') or 'CDP_CHUNK_BUDGET_NO_VERIFIED_DETAIL'
    else:
        result['ok'] = False
        result['error'] = result.get('error') or 'CDP_TIME_BUDGET_PARTIAL'
        summary['time_budget_reached'] = True
    return True


def _terminal_detail_failure_code(exc):
    """Stop this acquisition chunk after identity or transport failures."""
    message = str(exc).strip()
    identity_codes = {
        'DETAIL_IDENTITY_UNVERIFIED',
        'DETAIL_IDENTITY_MISMATCH',
        'DETAIL_SOURCE_UNVERIFIED',
    }
    if message in identity_codes:
        return message
    name = type(exc).__name__.lower()
    lowered = message.lower()
    if name in {'targetclosederror', 'browserclosederror', 'connectionerror'}:
        return 'COLLECTOR_PROVIDER_FAILURE'
    if any(marker in lowered for marker in (
            'net::err_', 'connection refused', 'connection reset', 'socket hang up',
            'target closed', 'browser has been closed', 'page crashed', 'protocol error')):
        return 'COLLECTOR_PROVIDER_FAILURE'
    if name in {'timeouterror', 'playwrighttimeout'}:
        return 'COLLECTOR_PROVIDER_FAILURE'
    return ''


def normalize_publish_time(raw):
    """小红书发布时间：明确日期优先；相对时间换算；拿不到返回空字符串，绝不臆造。"""
    if not raw:
        return ''
    raw = str(raw).strip()
    if '编辑于' in raw:
        return ''  # An edit time does not establish publication.
    stamp = re.search(r'20\d{2}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?', raw)
    if stamp:
        try:
            datetime.fromisoformat(stamp.group(0))
            return stamp.group(0)
        except ValueError:
            return ''
    m = re.search(r'(20\d{2})[-./](\d{1,2})[-./](\d{1,2})', raw)
    if m:
        try:
            return datetime(*(int(m.group(i)) for i in (1, 2, 3))).strftime('%Y-%m-%d')
        except ValueError:
            return ''
    m = re.search(r'(\d{1,2})[-./](\d{1,2})', raw)
    if m:
        return ''  # The publication year was not observed.
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


def _source_publication_time(detail, card):
    """A visible edit/unclassified date is not independent publication evidence."""
    observations = []
    for origin, source in (('detail', detail), ('card', card)):
        raw = source.get('time_raw') or ''
        kind = source.get('time_kind') or 'unclassified'
        if re.search(r'编辑|更新|edited|updated', str(raw), re.I):
            kind = 'edit'
        locator = source.get('time_locator')
        observations.append({'origin': origin, 'raw': raw, 'kind': kind, 'locator': locator})
    for observation in observations:
        if observation['kind'] == 'publication' and observation['locator']:
            value = normalize_publish_time(observation['raw'])
            if value:
                return value, observations, observation['origin']
    return '', observations, 'unknown'


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
    let observedTime = {time_raw:'', time_kind:'unknown', time_locator:null};
    for (const selector of ['[itemprop="datePublished"]','.publish-time','a.author .time','.time']) {
      const e = item.querySelector(selector);
      const raw = e ? (e.getAttribute('content') || e.getAttribute('datetime') || e.innerText || '').trim() : '';
      if (!raw) continue;
      observedTime = {time_raw:raw,
        time_kind:/编辑|更新|edited|updated/i.test(raw)?'edit':(['[itemprop="datePublished"]','.publish-time'].includes(selector)?'publication':'unclassified'),
        time_locator:{container_selector:'section.note-item',note_id:idm?idm[1]:'',selector}};
      break;
    }
    out.push({
      note_id: idm ? idm[1] : '',
      xsec_token: tkm ? decodeURIComponent(tkm[1]) : '',
      title: q('a.title span') || q('.title'),
      author: q('a.author .name') || q('.author .name'),
      ...observedTime,
      likes_raw: q('span.like-wrapper .count') || q('.count'),
      cover: img ? img.getAttribute('src') : '',
      url: href && href.startsWith('http') ? href : new URL(href.startsWith('/') ? href : '/' + href, window.location.origin).href
    });
  });
  return out.filter(x => x.note_id);
}
"""

_DETAIL_JS = r"""
() => {
  const q = sels => { for (const s of sels) { const e = document.querySelector(s); if (e && (e.innerText||'').trim()) return (e.innerText||'').trim(); } return ''; };
  const counts = Array.from(document.querySelectorAll('.count')).map(c => (c.innerText||'').trim()).filter(Boolean);
  const wc = sels => { for (const s of sels) { for (const e of document.querySelectorAll(s)) {
    if (e.closest('section.note-item,.comment-item,.parent-comment,.comments-container,.comment-container')) continue;
    const v=(e.innerText||'').trim(); if(v) return v;
  }} return ''; };
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
    const rawId=c.getAttribute('data-comment-id')||c.id||'';
    const native=rawId.match(/^(?:comment[-_])?([0-9a-fA-F]{24})$/);
    const rawParent=c.getAttribute('data-parent-comment-id')||'';
    return { user: u?(u.innerText||'').trim():'', content: x?(x.innerText||'').trim():'',
             platform_comment_id:native?native[1]:null,
             parent_comment_id:/^[0-9a-fA-F]{24}$/.test(rawParent)?rawParent:null,
             time: t?(t.innerText||'').trim():'', likes_raw: l?(l.innerText||'').trim():'' };
  });
  const hasVideo = !!document.querySelector('video,.video-container,[class*="video-player"]');
  const images = Array.from(document.querySelectorAll('.swiper-slide img, .note-slider-img, .media-container img'));
  const imageList = Array.from(new Set(images.map(e => e.currentSrc || e.getAttribute('src') || '').filter(Boolean)));
  const videoList = Array.from(document.querySelectorAll('video')).map(v => ({
    url: v.currentSrc || v.getAttribute('src') || '', poster: v.getAttribute('poster') || '',
    sources: Array.from(v.querySelectorAll('source')).map(s => s.getAttribute('src') || '').filter(Boolean)
  }));
  const authorLink = document.querySelector('.author-container a[href*="/user/profile/"],.author a[href*="/user/profile/"]');
  const authorUrl = authorLink ? authorLink.href : '';
  const authorMatch = authorUrl.match(/\/user\/profile\/([0-9a-fA-F]{24})(?:[/?#]|$)/);
  const tags = Array.from(new Set(Array.from(document.querySelectorAll('#detail-desc a.tag,.note-content a.tag,a[href*="/search_result?keyword=%23"]')).map(e => (e.innerText||'').trim()).filter(Boolean)));
  let observedTime = {time_raw:'', time_kind:'unknown', time_locator:null};
  for (const selector of ['[itemprop="datePublished"]','.publish-time','.author-container .time','.date','.time']) {
    for (const e of document.querySelectorAll(selector)) {
      if(e.closest('section.note-item,.comment-item,.parent-comment,.comments-container,.comment-container')) continue;
      const raw = (e.getAttribute('content') || e.getAttribute('datetime') || e.innerText || '').trim();
      if (!raw) continue;
      observedTime = {time_raw:raw,
        time_kind:/编辑|更新|edited|updated/i.test(raw)?'edit':(['[itemprop="datePublished"]','.publish-time'].includes(selector)?'publication':'unclassified'),
        time_locator:{page_url:window.location.origin+window.location.pathname,selector}};
      break;
    }
    if(observedTime.time_raw) break;
  }
  const nativeNoteId = value => {
    try {
      const u = new URL(value, window.location.origin);
      const m = u.pathname.match(/^\/(?:discovery\/item|explore|search_result)\/([0-9a-fA-F]{24})\/?$/);
      return u.protocol === 'https:' && u.hostname === 'www.rednote.com' && m ? m[1].toLowerCase() : '';
    } catch (_) { return ''; }
  };
  const canonical = document.querySelector('link[rel="canonical"]');
  const sourceNoteIds = Array.from(new Set([
    nativeNoteId(window.location.href),
    canonical ? nativeNoteId(canonical.getAttribute('href') || '') : '',
    ...Array.from(document.querySelectorAll('.note-detail[data-note-id],#noteContainer[data-note-id]')).map(e => e.getAttribute('data-note-id') || '')
  ].filter(x => /^[0-9a-fA-F]{24}$/.test(x)).map(x => x.toLowerCase())));
  return {
    source_note_ids: sourceNoteIds,
    source_page_url: window.location.origin + window.location.pathname,
    detail_present: !!document.querySelector('#detail-title,#detail-desc,.note-content .desc,.note-detail'),
    title: q(['#detail-title','.note-content .title','h1']),
    desc: q(['#detail-desc','.note-content .desc','.note-text','.desc']),
    author: q(['.author-container .name','.author .name','.username']),
    ...observedTime,
    all_counts: counts, engage: engage, comment_list: comments, comment_count: comments.length,
    is_video: hasVideo, image_count: images.length, image_list: imageList, video_list: videoList,
    author_url: authorUrl, author_id: authorMatch ? authorMatch[1] : '', tag_list: tags
  };
}
"""


def classify_page(text):
    normalized = str(text or '')
    for w in _IP_WORDS:
        if w in normalized:
            return 'ip', w
    if any(word in normalized for word in _LOGIN_LIMIT_WORDS) or (
            '请重新登录' in normalized and
            any(word in normalized for word in ('扫码登录', '手机号登录', '获取验证码'))):
        return 'session_expired', 'SESSION_EXPIRED'
    for w in _VERIFY_WORDS:
        if w in normalized:
            return 'verify', w
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
    if kind == 'session_expired':
        result.setdefault('summary', {}).update({'session_expired': True, 'matched': hit})
        result['error'] = 'SESSION_EXPIRED'
        return True
    if kind == 'ip':
        result.setdefault('summary', {}).update({'ip_blocked': True, 'matched': hit})
        result['error'] = 'IP_RISK_OR_300012'
        return True
    if kind == 'verify':
        result.setdefault('summary', {}).update({'verification_required': True, 'matched': hit})
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

_SEARCH_STATE_JS = r"""(keyword) => {
  const body = document.body ? (document.body.innerText || '') : '';
  const query = new URL(location.href).searchParams.get('keyword');
  const input = document.querySelector('#search-input,.search-input input,input[type=search]');
  const selectors = ['section.note-item','a.cover','.feeds-container'];
  const counts = Object.fromEntries(selectors.map(s => [s,document.querySelectorAll(s).length]));
  const links = Array.from(document.querySelectorAll('section.note-item a')).map(a => a.getAttribute('href') || '');
  const noteLinkCount = links.filter(x => /(?:search_result|explore)\/([^/?]+)/.test(x)).length;
  const bodyLines = body.split(/\r?\n/).map(x => x.trim());
  return {
    host_matches: location.hostname === 'www.rednote.com' && location.protocol === 'https:',
    route_is_search: location.pathname.startsWith('/search_result'),
    query_matches: query === keyword || (!!input && input.value === keyword && query === encodeURIComponent(keyword)),
    query_encoding: query === keyword ? 'literal' : (!!input && input.value === keyword && query === encodeURIComponent(keyword) ? 'percent_encoded_once' : 'unverified'),
    input_matches: !!input && input.value === keyword,
    document_ready_state: document.readyState,
    selector_counts: counts,
    note_link_count: noteLinkCount,
    body_character_count: body.length,
    native_empty_indicators: counts['section.note-item'] === 0 && noteLinkCount === 0
      ? ['暂无搜索结果','没有找到相关内容','无搜索结果','No results found'].filter(x => bodyLines.includes(x)) : [],
    loading_element_count: document.querySelectorAll('[aria-busy=true],.loading,.load-more').length
  };
}"""


def _snapshot_search_state(page, keyword, result, phase, progress=None, *, error_type=None):
    """Capture bounded DOM facts only; never URL queries, HTML, cookies or headers."""
    observation = {'phase': phase, 'observed_at': datetime.now().astimezone().isoformat()}
    try:
        raw = page.evaluate(_SEARCH_STATE_JS, keyword)
        if not isinstance(raw, dict):
            raise TypeError('SEARCH_STATE_INVALID')
        for key in ('host_matches', 'route_is_search', 'query_matches', 'input_matches'):
            observation[key] = raw.get(key) is True
        encoding = raw.get('query_encoding')
        observation['query_encoding'] = encoding if encoding in {'literal', 'percent_encoded_once'} else 'unverified'
        state = raw.get('document_ready_state')
        observation['document_ready_state'] = state if state in {'loading','interactive','complete'} else 'unknown'
        counts = raw.get('selector_counts') or {}
        observation['selector_counts'] = {}
        for selector in ('section.note-item','a.cover','.feeds-container'):
            count = counts.get(selector)
            observation['selector_counts'][selector] = count if type(count) is int and count >= 0 else None
        for key in ('note_link_count', 'body_character_count', 'loading_element_count'):
            count = raw.get(key)
            observation[key] = count if type(count) is int and count >= 0 else None
        indicators = raw.get('native_empty_indicators') or []
        observation['native_empty_indicators'] = [value for value in indicators if value in {
            '暂无搜索结果','没有找到相关内容','无搜索结果','No results found'}]
    except Exception as exc:
        observation['diagnostic_error_type'] = type(exc).__name__
    if error_type:
        observation['wait_error_type'] = error_type
    diagnostics = result.setdefault('search_diagnostics', {'version': 'xhs-search-state-v1', 'observations': []})
    diagnostics['observations'].append(observation)
    diagnostics['observations'] = diagnostics['observations'][-12:]
    if progress:
        progress(result)
    return observation


def _search_failure_code(observation):
    """An empty observation is an acquisition state, never a business metric zero."""
    if observation.get('diagnostic_error_type'):
        return 'SEARCH_STATE_UNAVAILABLE'
    if observation.get('host_matches') is not True:
        return 'SOURCE_HOST_MISMATCH'
    if not observation.get('route_is_search') or not observation.get('query_matches'):
        return 'SEARCH_TRANSITION_UNVERIFIED'
    if (observation.get('native_empty_indicators')
            and observation.get('selector_counts', {}).get('section.note-item') == 0
            and observation.get('note_link_count') == 0):
        return 'SOURCE_NO_RESULTS'
    if (observation.get('body_character_count') or 0) < 20:
        return 'LOAD_FAILED'
    if (observation.get('selector_counts', {}).get('section.note-item') or 0) > 0 and observation.get('note_link_count') == 0:
        return 'LIST_PARSE_UNAVAILABLE'
    if (observation.get('loading_element_count') or 0) > 0:
        return 'SEARCH_LOADING_TIMEOUT'
    return 'EMPTY_LIST_UNCLASSIFIED'


def _await_search_ready(page, keyword, result, progress=None, deadline=None, budget_kind='worker_chunk'):
    """Wait for this exact query and a visible native card, within one time budget."""
    from urllib.parse import parse_qs, quote
    started = time.monotonic()
    end = min(started + 18, deadline) if deadline is not None else started + 18
    observation = _snapshot_search_state(page, keyword, result, 'search_submitted', progress)
    if observation.get('host_matches') is not True:
        result['error'] = _search_failure_code(observation)
        return False
    def matches(url):
        parsed = urlsplit(str(url))
        return (parsed.scheme == 'https' and parsed.hostname == COLLECTION_HOST
                and parsed.path.startswith('/search_result')
                and parse_qs(parsed.query).get('keyword') in ([keyword], [quote(keyword, safe="~()*!.'")]))
    try:
        if _budget_reached(result, deadline, budget_kind):
            return False
        page.wait_for_url(matches, wait_until='domcontentloaded', timeout=max(1, int((end-time.monotonic())*1000)))
        page.locator('section.note-item').first.wait_for(state='visible', timeout=max(1, int((end-time.monotonic())*1000)))
    except Exception as exc:
        observation = _snapshot_search_state(page, keyword, result, 'search_wait_failed', progress, error_type=type(exc).__name__)
        if _risk_check(page, result):
            return False
        if _budget_reached(result, deadline, budget_kind):
            return False
        result['error'] = _search_failure_code(observation)
        return False
    observation = _snapshot_search_state(page, keyword, result, 'search_ready', progress)
    if not (observation.get('host_matches') and observation.get('route_is_search') and observation.get('query_matches')):
        result['error'] = _search_failure_code(observation)
        return False
    return True


def _capture_verified_detail(page, target, *, detail_media_mode, human_view,
                             video_watched=False, comment_seen=None, detail=None):
    """One identity-checked detail parser for search and exact-URL reads."""
    _validate_native_card(target)
    detail = page.evaluate(_DETAIL_JS) if detail is None else detail
    _require_detail_observation(detail)
    _require_detail_identity(detail, target['note_id'])
    metrics = _detail_metrics(detail, target)
    published, time_observations, publication_source = _source_publication_time(detail, target)
    record = {
        'note_id': target['note_id'], 'xsec_token': target.get('xsec_token', ''),
        'title': detail.get('title') or target.get('title', ''),
        'detail_title': detail.get('title') or target.get('title', ''),
        'desc': detail.get('desc', ''),
        'author': detail.get('author') or target.get('author', ''),
        'detail_author': detail.get('author') or target.get('author', ''),
        'detail_publish_time': published, 'publish_time': published,
        'time_raw': detail.get('time_raw') or target.get('time_raw', ''),
        'time_source_observations': time_observations,
        'publication_time_source': publication_source,
        'native_metrics_raw': {'engage': detail.get('engage') or {},
                               'card_likes_raw': target.get('likes_raw')},
        'author_id': detail.get('author_id', ''), 'author_url': detail.get('author_url', ''),
        'image_list': detail.get('image_list', []), 'video_list': detail.get('video_list', []),
        'tag_list': detail.get('tag_list', []), **metrics,
        'comment_list': detail.get('comment_list', []),
        'comment_count': detail.get('comment_count', comment_seen),
        'is_video': bool(detail.get('is_video') or detail.get('video_list') or video_watched),
        'detail_media_mode': detail_media_mode, 'image_count': detail.get('image_count'),
        'cover': target.get('cover', ''),
        'url': page.url if human_view['opened_by'] == 'click' else target['url'],
        'human_view': human_view,
        'detail_fetched': True, 'collected_at': datetime.now().astimezone().isoformat(),
        'source_note_ids': detail.get('source_note_ids'),
        'source_page_url': detail.get('source_page_url'),
        'detail_identity_verified': True, 'collector_version': 'xhs-cdp-py-human-2.3',
    }
    record['subject_hit'] = _compute_subject_hit(record['title'], record['desc'])
    return record


def collect_detail(keyword, detail_url, *, cdp_url=CDP_URL, progress=None,
                   deadline=None, resume_ids=None, budget_kind='worker_chunk',
                   detail_media_mode='legacy'):
    """Read one requested RedNote note through the registered search worker.

    No search, alternate endpoint, profile creation, or personal-session fallback
    is allowed. A failed chunk retains the exact pending note for normal recovery.
    """
    if detail_media_mode not in {'legacy', 'cover_only'}:
        raise ValueError('INVALID_DETAIL_MEDIA_MODE')
    _assert_collection_host()
    parsed = urlsplit(detail_url)
    match = re.fullmatch(r'/(?:explore|search_result|discovery/item)/([0-9a-fA-F]{24})/?', parsed.path)
    if not match:
        raise ValueError('DETAIL_SOURCE_UNVERIFIED')
    target = _validate_native_card({'note_id': match.group(1).lower(), 'url': detail_url})
    _validate_native_card({'note_id': target['note_id'], 'url': keyword})
    result = {'ok': False, 'keyword': keyword, 'mode': 'detail',
              'detail_media_mode': detail_media_mode, 'notes': [],
              'discovered_cards': [target],
              'summary': {'resumed_note_ids': sorted(resume_ids or ())}}
    _update_detail_progress(result)
    if target['note_id'] in (resume_ids or ()):
        result['ok'] = True
        return result
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser, context = _connect_verified_collection_context(playwright, cdp_url)
        result['identity_verified'] = True
        page = context.new_page()
        try:
            if progress:
                progress(result)
            if _budget_reached(result, deadline, budget_kind):
                return result
            robust_goto(page, detail_url)
            if _risk_check(page, result) or _budget_reached(result, deadline, budget_kind):
                return result
            page.wait_for_selector(_DETAIL_READY_SEL, timeout=10000)
            # Verify the selected note before consuming any media/comments.
            observed = page.evaluate(_DETAIL_JS)
            _require_detail_observation(observed)
            _require_detail_identity(observed, target['note_id'])
            profile, depth = human_reading_profile()
            consumed = human_consume_detail(page, profile, depth, detail_media_mode)
            if _risk_check(page, result) or _budget_reached(result, deadline, budget_kind):
                return result
            result['notes'].append(_capture_verified_detail(page, target,
                detail_media_mode=detail_media_mode,
                video_watched=consumed['video_watched'], comment_seen=consumed['comments_seen'],
                human_view={'opened_by': 'goto', 'profile': profile, 'depth': depth,
                            'dwell_sec': consumed['dwell_sec'],
                            'video_watched': consumed['video_watched'],
                            'images_swiped': consumed['images_swiped'],
                            'comments_seen': consumed['comments_seen']}))
            _update_detail_progress(result)
            result['summary'].update(detail_success=1, detail_total=1, interactions_made=0,
                                      acquisition_capability='detail')
            result['ok'] = True
            if progress:
                progress(result)
            return result
        finally:
            try:
                page.close()
            except Exception:
                pass
            # The approved existing browser/context is deliberately retained.

def collect_human(keyword, max_scroll=3, max_details=10, cdp_url=CDP_URL, progress=None, deadline=None,
                  resume_ids=None, resume_cards=None, budget_kind='worker_chunk',
                  detail_media_mode='legacy'):
    if not isinstance(detail_media_mode, str) or detail_media_mode not in {'legacy', 'cover_only'}:
        raise ValueError('INVALID_DETAIL_MEDIA_MODE')
    _assert_collection_host()
    from playwright.sync_api import sync_playwright
    result = {'ok': False, 'keyword': keyword, 'mode': 'human', 'detail_media_mode': detail_media_mode,
              'notes': [], 'summary': {}, 'human_trace': []}
    result['summary']['resumed_note_ids'] = sorted(resume_ids or ())
    trace = result['human_trace']
    with sync_playwright() as p:
        browser, ctx = _connect_verified_collection_context(p, cdp_url)
        result['identity_verified'] = True
        page = ctx.new_page()
        try:
            if _budget_reached(result, deadline, budget_kind):
                return result
            from urllib.parse import quote
            # 先稳落探索页（无 keyword 的 search_result 冷导航易挂起；explore 实测稳定），
            # 再由真人键盘输入关键词触发结果页，更像真人且更稳
            landing = f'{COLLECTION_ORIGIN}/explore'
            log('真人模式：打开探索页')
            robust_goto(page, landing)
            _snapshot_search_state(page, keyword, result, 'landing', progress)
            if _risk_check(page, result):
                return result
            if _budget_reached(result, deadline, budget_kind):
                return result
            human_sleep(2.4, 3.8)
            if _risk_check(page, result):
                return result
            if _budget_reached(result, deadline, budget_kind):
                return result
            # 1) 真实键盘输入关键词
            try:
                human_search_keyword(page, keyword)
            except Exception as e:
                # 兜底：键盘输入失败时退回 URL 直达（仍继续真人浏览，不中断采集）
                log(f'键盘输入失败，回退URL直达: {e}')
                robust_goto(page, f'{COLLECTION_ORIGIN}/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51')
            if not _await_search_ready(page, keyword, result, progress, deadline, budget_kind):
                return result
            human_sleep(1.2, 2.2)

            # Browse only the confirmed exact-query list.
            for i in range(int(max_scroll)):
                if _budget_reached(result, deadline, budget_kind):
                    return result
                scroll_human(page, total_px=random.randint(700, 1100), rounds=random.randint(2, 4))
                gauss_sleep(1.4, 0.5, 0.8)
                if _risk_check(page, result):
                    return result
            human_sleep(0.8, 1.6)

            observation = _snapshot_search_state(page, keyword, result, 'before_list_parse', progress)
            if not (observation.get('host_matches') and observation.get('route_is_search') and observation.get('query_matches')):
                result['error'] = _search_failure_code(observation)
                return result
            cards = page.evaluate(_LIST_JS)
            log(f'信息流发现 {len(cards)} 张卡片')
            result['summary']['discovered'] = len(cards)
            cards = _merge_native_cards(resume_cards, cards) if resume_cards else cards
            result['discovered_cards'] = cards
            if progress:
                _update_detail_progress(result)
                progress(result)
            if not cards:
                if _risk_check(page, result):
                    return result
                result['error'] = _search_failure_code(_snapshot_search_state(page, keyword, result, 'empty_list', progress))
                return result

            pending_cards = [card for card in cards if card['note_id'] not in (resume_ids or ())]
            actual = len(pending_cards) if int(max_details) == 0 else min(int(max_details), len(pending_cards))
            ok_detail = 0
            seen_ids = set(resume_ids or ())
            for i in range(actual):
                if _budget_reached(result, deadline, budget_kind):
                    return result
                # 每 4 篇长休息一次（真人刷累了停顿）
                if i > 0 and i % 4 == 0:
                    long_break = random.uniform(15, 32)
                    log(f'模拟真人长休息 {long_break:.0f}s')
                    time.sleep(long_break)
                    if _risk_check(page, result):
                        return result
                    if _budget_reached(result, deadline, budget_kind):
                        return result

                # Keep the pending identity queue stable across live-list refreshes.
                observation = _snapshot_search_state(page, keyword, result, 'before_detail_select', progress)
                if not (observation.get('host_matches') and observation.get('route_is_search') and observation.get('query_matches')):
                    if _risk_check(page, result):
                        return result
                    result['error'] = _search_failure_code(observation)
                    return result
                target = pending_cards[i]
                fresh = page.evaluate(_LIST_JS) or []
                matching = next((card for card in fresh if card.get('note_id') == target['note_id']), None)
                if matching is not None:
                    target = _validate_native_card(matching)
                seen_ids.add(target['note_id'])
                opened_by_click = False
                try:
                    # 3) 贝塞尔鼠标移动 + 真实点击笔记封面打开详情（绝不点互动按钮）
                    card_loc = page.locator(f'section.note-item:has(a[href*="{target["note_id"]}"])').first
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
                    if _risk_check(page, result):
                        return result
                    if _budget_reached(result, deadline, budget_kind):
                        return result
                    human_sleep(1.6, 2.8)
                    if _risk_check(page, result):
                        return result
                    if _budget_reached(result, deadline, budget_kind):
                        return result

                    # 4) 真人阅读：按行为画像(秒退/浅读/正常/深读)差异化停留，每次时长不一
                    profile, depth = human_reading_profile()
                    consume = human_consume_detail(page, profile, depth, detail_media_mode)
                    if _risk_check(page, result):
                        return result
                    if _budget_reached(result, deadline, budget_kind):
                        return result
                    video_watched = consume['video_watched']; img_swiped = consume['images_swiped']
                    comment_seen = consume['comments_seen']

                    d = page.evaluate(_DETAIL_JS)
                    rec = _capture_verified_detail(page, target, detail=d,
                        detail_media_mode=detail_media_mode,
                        video_watched=video_watched, comment_seen=comment_seen,
                        human_view={'opened_by': 'click' if opened_by_click else 'goto',
                                    'profile': profile, 'depth': depth,
                                    'dwell_sec': consume['dwell_sec'],
                                    'video_watched': video_watched, 'images_swiped': img_swiped,
                                    'comments_seen': comment_seen})
                    likes, collects, comments, shares = (rec[k] for k in ('likes', 'collects', 'comments', 'shares'))
                    pub = rec['publish_time']
                    result['notes'].append(rec)
                    ok_detail += 1
                    if progress:
                        _update_detail_progress(result)
                        progress(result)
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
                            page.goto(f'{COLLECTION_ORIGIN}/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51',
                                      wait_until='commit', timeout=20000)
                    human_sleep(2.4, 4.2)  # 返回信息流后的真人停顿
                    try:
                        page.wait_for_selector('section.note-item', timeout=8000)
                    except Exception:
                        pass
                except Exception as e:
                    if isinstance(e, RawCheckpointError):
                        raise
                    if _risk_check(page, result):
                        _update_detail_progress(result)
                        if progress:
                            progress(result)
                        return result
                    terminal_code = _terminal_detail_failure_code(e)
                    if terminal_code:
                        result['ok'] = False
                        result['error'] = terminal_code
                        result['partial'] = True
                        _update_detail_progress(result)
                        if progress:
                            progress(result)
                        return result
                    log(f'详情失败 {i+1}: {e}')
                    result['notes'].append({**target, 'detail_fetched': False, 'error': str(e)[:160],
                                            'detail_media_mode': detail_media_mode,
                                            'desc': '', 'likes': parse_count(target.get('likes_raw')),
                                            'collects': None, 'comments': None, 'shares': None,
                                            'time_raw': target.get('time_raw', ''),
                                            'collected_at': datetime.now().astimezone().isoformat(),
                                            'detail_publish_time': '',
                                            'time_source_observations': _source_publication_time({}, target)[1],
                                            'publication_time_source': 'unknown',
                                            'unassigned_detail_observation': d if 'd' in locals() and str(e) in {'DETAIL_IDENTITY_UNVERIFIED', 'DETAIL_IDENTITY_MISMATCH', 'DETAIL_SOURCE_UNVERIFIED'} else None})
                    if progress:
                        _update_detail_progress(result)
                        progress(result)
                    # 异常后尝试回到结果流，避免卡在详情页
                    try:
                        page.goto(f'{COLLECTION_ORIGIN}/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51',
                                  wait_until='commit', timeout=20000)
                        human_sleep(2.0, 3.2)
                    except Exception:
                        pass
            result['summary'].update({'detail_success': ok_detail, 'detail_total': actual,
                                      'human': True, 'interactions_made': 0})
            _update_detail_progress(result)
            result['partial'] = bool(result['summary']['pending_note_ids'])
            result['summary']['batch_limited'] = len(pending_cards) > actual
            result['ok'] = ok_detail > 0
            if not result['ok']:
                result['error'] = result.get('error') or 'NO_DETAIL'
            return result
        finally:
            try:
                page.close()
            except Exception:
                pass
            if progress:
                progress(result)
            # CDP 模式绝不 browser.close()，保留持久 Edge 登录态


# ============================================================
# 旧直连流程（--human=0 回退用，保留稳定基线）
# ============================================================
def collect_direct(keyword, max_scroll=3, max_details=10, cdp_url=CDP_URL, progress=None, deadline=None,
                   resume_ids=None, resume_cards=None, budget_kind='worker_chunk'):
    _assert_collection_host()
    from playwright.sync_api import sync_playwright
    result = {'ok': False, 'keyword': keyword, 'mode': 'direct', 'notes': [], 'summary': {}}
    result['summary']['resumed_note_ids'] = sorted(resume_ids or ())
    with sync_playwright() as p:
        browser, ctx = _connect_verified_collection_context(p, cdp_url)
        result['identity_verified'] = True
        page = ctx.new_page()
        try:
            if _budget_reached(result, deadline, budget_kind):
                return result
            from urllib.parse import quote
            url = f'{COLLECTION_ORIGIN}/search_result/?keyword={quote(keyword)}&source=web_explore_feed&type=51'
            log(f'导航搜索: {keyword}')
            page.goto(url, wait_until='commit', timeout=30000)
            _snapshot_search_state(page, keyword, result, 'landing', progress)
            if _risk_check(page, result):
                return result
            if _budget_reached(result, deadline, budget_kind):
                return result
            human_sleep(3.0, 4.5)

            text = page.evaluate("() => document.body ? document.body.innerText : ''") or ''
            kind, hit = classify_page(text)
            if kind == 'session_expired':
                result.setdefault('summary', {}).update({'session_expired': True, 'matched': hit})
                result['error'] = 'SESSION_EXPIRED'
                return result
            if kind == 'ip':
                result.setdefault('summary', {}).update({'ip_blocked': True, 'matched': hit})
                result['error'] = 'IP_RISK_OR_300012'
                return result
            if kind == 'verify':
                result.setdefault('summary', {}).update({'verification_required': True, 'matched': hit})
                result['error'] = 'NEED_VERIFY'
                return result

            if not _await_search_ready(page, keyword, result, progress, deadline, budget_kind):
                return result
            for i in range(int(max_scroll)):
                if _budget_reached(result, deadline, budget_kind):
                    return result
                page.mouse.wheel(0, random.randint(500, 950))
                human_sleep(1.4, 2.6)
                if _risk_check(page, result):
                    return result
                if _budget_reached(result, deadline, budget_kind):
                    return result
            human_sleep(0.8, 1.4)

            observation = _snapshot_search_state(page, keyword, result, 'before_list_parse', progress)
            if not (observation.get('host_matches') and observation.get('route_is_search') and observation.get('query_matches')):
                result['error'] = _search_failure_code(observation)
                return result
            cards = page.evaluate(_LIST_JS)
            log(f'列表发现 {len(cards)} 张卡片')
            result['summary']['discovered'] = len(cards)
            cards = _merge_native_cards(resume_cards, cards) if resume_cards else cards
            result['discovered_cards'] = cards
            if progress:
                _update_detail_progress(result)
                progress(result)
            if not cards:
                t2 = page.evaluate("() => document.body ? document.body.innerText : ''") or ''
                kind, hit = classify_page(t2)
                if kind == 'session_expired':
                    result.setdefault('summary', {}).update({'session_expired': True, 'matched': hit})
                    result['error'] = 'SESSION_EXPIRED'; return result
                if kind == 'ip':
                    result.setdefault('summary', {}).update({'ip_blocked': True, 'matched': hit}); result['error'] = 'IP_RISK_OR_300012'; return result
                if kind == 'verify':
                    result.setdefault('summary', {}).update({'verification_required': True, 'matched': hit}); result['error'] = 'NEED_VERIFY'; return result
                result['error'] = _search_failure_code(_snapshot_search_state(page, keyword, result, 'empty_list', progress))
                return result

            cards = [card for card in cards if card['note_id'] not in (resume_ids or ())]
            actual = len(cards) if int(max_details) == 0 else min(int(max_details), len(cards))
            ok_detail = 0
            for i in range(actual):
                if _budget_reached(result, deadline, budget_kind):
                    return result
                c = cards[i]
                try:
                    page.goto(c['url'], wait_until='domcontentloaded', timeout=30000)
                    try:
                        page.wait_for_selector('#detail-desc, #detail-title, .note-content .desc', timeout=10000)
                    except Exception:
                        pass
                    if _risk_check(page, result):
                        return result
                    if _budget_reached(result, deadline, budget_kind):
                        return result
                    human_sleep(2.2, 3.4)
                    if _risk_check(page, result):
                        return result
                    if _budget_reached(result, deadline, budget_kind):
                        return result
                    d = page.evaluate(_DETAIL_JS)
                    _require_detail_observation(d)
                    _require_detail_identity(d, c['note_id'])
                    metrics = _detail_metrics(d, c)
                    likes, collects, comments, shares = (metrics[k] for k in ('likes', 'collects', 'comments', 'shares'))
                    pub, time_observations, publication_source = _source_publication_time(d, c)
                    rec = {
                        'note_id': c['note_id'], 'xsec_token': c.get('xsec_token', ''),
                        'title': d.get('title') or c.get('title', ''),
                        'detail_title': d.get('title') or c.get('title', ''),
                        'desc': d.get('desc', ''),
                        'author': d.get('author') or c.get('author', ''),
                        'detail_author': d.get('author') or c.get('author', ''),
                        'detail_publish_time': pub, 'publish_time': pub,
                        'time_raw': d.get('time_raw') or c.get('time_raw', ''),
                        'time_source_observations': time_observations,
                        'publication_time_source': publication_source,
                        'native_metrics_raw': {'engage': d.get('engage') or {}, 'card_likes_raw': c.get('likes_raw')},
                        'author_id': d.get('author_id', ''), 'author_url': d.get('author_url', ''),
                        'image_list': d.get('image_list', []), 'video_list': d.get('video_list', []),
                        'tag_list': d.get('tag_list', []), 'is_video': d.get('is_video'),
                        'image_count': d.get('image_count'),
                        'likes': likes, 'collects': collects, 'comments': comments, 'shares': shares,
                        'comment_list': d.get('comment_list', []), 'comment_count': d.get('comment_count', 0),
                        'cover': c.get('cover', ''), 'url': c['url'],
                        'detail_fetched': True, 'collected_at': datetime.now().astimezone().isoformat(),
                        'source_note_ids': d.get('source_note_ids'), 'source_page_url': d.get('source_page_url'),
                        'detail_identity_verified': True,
                        'collector_version': 'xhs-cdp-py-direct-1.2',
                    }
                    rec['subject_hit'] = _compute_subject_hit(rec.get('title'), rec.get('desc'))
                    result['notes'].append(rec); ok_detail += 1
                    if progress:
                        _update_detail_progress(result)
                        progress(result)
                    log(f'详情 {i+1}/{actual}: {rec["title"][:24]} 赞{likes} 藏{collects} 评{comments} {pub}')
                    human_sleep(1.0, 2.0)
                except Exception as e:
                    if isinstance(e, RawCheckpointError):
                        raise
                    if _risk_check(page, result):
                        _update_detail_progress(result)
                        if progress:
                            progress(result)
                        return result
                    terminal_code = _terminal_detail_failure_code(e)
                    if terminal_code:
                        result['ok'] = False
                        result['error'] = terminal_code
                        result['partial'] = True
                        _update_detail_progress(result)
                        if progress:
                            progress(result)
                        return result
                    log(f'详情失败 {i+1}: {e}')
                    result['notes'].append({**c, 'detail_fetched': False, 'error': str(e)[:160],
                                            'desc': '', 'likes': parse_count(c.get('likes_raw')),
                                            'collects': None, 'comments': None, 'shares': None,
                                            'time_raw': c.get('time_raw', ''),
                                            'collected_at': datetime.now().astimezone().isoformat(),
                                            'detail_publish_time': '',
                                            'time_source_observations': _source_publication_time({}, c)[1],
                                            'publication_time_source': 'unknown',
                                            'unassigned_detail_observation': d if 'd' in locals() and str(e) in {'DETAIL_IDENTITY_UNVERIFIED', 'DETAIL_IDENTITY_MISMATCH', 'DETAIL_SOURCE_UNVERIFIED'} else None})
                    if progress:
                        _update_detail_progress(result)
                        progress(result)
            result['summary'].update({'detail_success': ok_detail, 'detail_total': actual})
            _update_detail_progress(result)
            result['partial'] = bool(result['summary']['pending_note_ids'])
            result['summary']['batch_limited'] = len(cards) > actual
            result['ok'] = ok_detail > 0
            if not result['ok']:
                result['error'] = result.get('error') or 'NO_DETAIL'
            return result
        finally:
            try:
                page.close()
            except Exception:
                pass
            if progress:
                progress(result)


def collect(keyword, max_scroll=3, max_details=10, cdp_url=CDP_URL, human=1, progress=None, deadline=None,
            resume_ids=None, resume_cards=None, budget_kind='worker_chunk', detail_media_mode='legacy',
            detail_url=None):
    """统一入口：human=1 真人浏览链路（默认），human=0 旧直连。"""
    if not isinstance(detail_media_mode, str) or detail_media_mode not in {'legacy', 'cover_only'}:
        return {'ok': False, 'keyword': keyword, 'notes': [], 'summary': {},
                'error': 'INVALID_DETAIL_MEDIA_MODE'}
    if detail_media_mode == 'cover_only' and int(human) == 0:
        return {'ok': False, 'keyword': keyword, 'notes': [], 'summary': {},
                'detail_media_mode': detail_media_mode, 'error': 'COVER_ONLY_REQUIRES_HUMAN_MODE'}
    if not cdp_url:
        return {'ok': False, 'keyword': keyword, 'notes': [], 'summary': {},
                'error': 'COLLECTOR_ENDPOINT_NOT_CONFIGURED'}
    if detail_url is not None:
        return collect_detail(keyword, detail_url, cdp_url=cdp_url, progress=progress,
                              deadline=deadline, resume_ids=resume_ids, budget_kind=budget_kind,
                              detail_media_mode=detail_media_mode)
    if int(human) == 0:
        return collect_direct(keyword, max_scroll, max_details, cdp_url, progress, deadline,
                              resume_ids, resume_cards, budget_kind)
    return collect_human(keyword, max_scroll, max_details, cdp_url, progress, deadline,
                         resume_ids, resume_cards, budget_kind, detail_media_mode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keyword', required=True)
    ap.add_argument('--output', default='')
    ap.add_argument('--max-scroll', type=int, default=3)
    ap.add_argument('--max-details', type=int, default=10)
    ap.add_argument('--cdp-url', default=CDP_URL)
    ap.add_argument('--human', type=int, default=1, help='1=真人浏览链路(默认) 0=旧直连')
    ap.add_argument('--run-id', default='')
    ap.add_argument('--time-budget', type=float, default=None,
                    help='Optional positive caller task budget; omitted means no global task deadline')
    ap.add_argument('--worker-chunk-seconds', type=float, default=300,
                    help='Finite per-invocation worker chunk cap (maximum 300 seconds)')
    ap.add_argument('--acquisition-fingerprint', default='',
                    help='Optional exact purpose/query binding supplied by the SYSTEM caller')
    ap.add_argument('--detail-media-mode', choices=('legacy', 'cover_only'), default='legacy',
                    help='Detail read mode; cover_only skips media watch/swipe waits while preserving native clues')
    ap.add_argument('--resume-from', default='')
    ap.add_argument('--detail-url', default=None,
                    help='Exact permitted RedNote note URL; reuse the same identity-verified worker')
    args = ap.parse_args()
    if args.time_budget is not None and (not math.isfinite(args.time_budget) or args.time_budget <= 0):
        ap.error('--time-budget must be a finite positive number when supplied')
    if (not math.isfinite(args.worker_chunk_seconds)
            or args.worker_chunk_seconds <= 0 or args.worker_chunk_seconds > 300):
        ap.error('--worker-chunk-seconds must be finite, positive, and no more than 300')
    if args.detail_media_mode == 'cover_only' and args.human == 0:
        ap.error('--detail-media-mode cover_only requires --human 1')
    acquisition_fingerprint = args.acquisition_fingerprint or None
    if (acquisition_fingerprint is not None
            and re.fullmatch(r'[0-9a-f]{64}', acquisition_fingerprint) is None):
        ap.error('--acquisition-fingerprint must be a lowercase SHA-256 hex string')
    if args.resume_from and args.output and os.path.normcase(os.path.abspath(args.resume_from)) == os.path.normcase(os.path.abspath(args.output)):
        ap.error('--resume-from and --output must name distinct Raw artifacts')
    t0 = time.time()
    if not args.run_id:
        from uuid import uuid4
        args.run_id = uuid4().hex
    effective_budget = args.worker_chunk_seconds
    budget_kind = 'worker_chunk'
    if args.time_budget is not None and args.time_budget <= effective_budget:
        effective_budget = args.time_budget
        budget_kind = 'time_budget'
    deadline = time.monotonic() + effective_budget

    def progress(value):
        value.setdefault('detail_media_mode', args.detail_media_mode)
        if acquisition_fingerprint is not None:
            value['acquisition_fingerprint'] = acquisition_fingerprint
        else:
            value.pop('acquisition_fingerprint', None)
        return _write_checkpoint(args.output, value, args.run_id)

    initial = {'ok': False, 'keyword': args.keyword, 'detail_media_mode': args.detail_media_mode,
               'notes': [], 'summary': {'phase': 'starting'},
               'search_diagnostics': {'version': 'xhs-search-state-v1', 'observations': []}}
    if acquisition_fingerprint is not None:
        initial['acquisition_fingerprint'] = acquisition_fingerprint
    terminal_replay = False
    previous = None
    try:
        previous = _load_resume_checkpoint(args.resume_from, args.keyword, acquisition_fingerprint)
        if previous is not None and (previous.get('checkpoint') or {}).get('complete') is True:
            res = previous
            terminal_replay = True
        else:
            if previous is not None:
                previous_mode = previous.get('detail_media_mode', 'legacy')
                if previous_mode != args.detail_media_mode:
                    raise RuntimeError('RESUME_MEDIA_MODE_MISMATCH')
            progress(initial)
            resume_ids = _completed_detail_ids(previous)
            resume_options = {'resume_cards': _resume_pending_cards(previous, resume_ids)} if previous is not None else {}
            if args.detail_url is not None:
                resume_options['detail_url'] = args.detail_url
            res = collect(args.keyword, args.max_scroll, args.max_details, args.cdp_url, args.human,
                          progress, deadline, resume_ids, budget_kind=budget_kind,
                          detail_media_mode=args.detail_media_mode, **resume_options)
    except Exception as e:
        res = initial
        if args.output:
            try:
                with open(args.output, encoding='utf-8') as source:
                    saved = json.load(source)
                if (saved.get('checkpoint', {}).get('run_id') == args.run_id
                        and saved.get('keyword') == args.keyword):
                    res = saved
            except (OSError, ValueError, TypeError, AttributeError):
                pass
        code = str(e) if re.fullmatch(r'[A-Z][A-Z0-9_]{0,100}', str(e)) else type(e).__name__
        res.update({'ok': False, 'partial': True, 'error': f'CDP_EXCEPTION: {code}'})
        if isinstance(e,CollectionIdentityError):
            res['identity_failure_stage'] = e.stage
    if not terminal_replay:
        res.setdefault('detail_media_mode', args.detail_media_mode)
        res['elapsed'] = round(time.time() - t0, 1)
        res['partial'] = bool(res.get('error') or res.get('partial'))
        if acquisition_fingerprint is not None:
            res['acquisition_fingerprint'] = acquisition_fingerprint
        else:
            res.pop('acquisition_fingerprint', None)
        summary = res.setdefault('summary', {})
        pending = summary.get('pending_note_ids', [])
        if not isinstance(pending, list):
            pending = []
        summary['pagination_exhausted'] = False
        summary['continuation_required'] = bool(
            pending or summary.get('worker_chunk_budget_reached') or res.get('partial'))
    if args.output:
        if terminal_replay:
            _write_checkpoint(args.output, res, args.run_id,
                              complete=True, checkpoint_override=res['checkpoint'])
        else:
            res['checkpoint'] = _write_checkpoint(args.output, res, args.run_id, complete=not res['partial'])
    print('\n---RESULT_JSON---')
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if res.get('ok') else 1)


if __name__ == '__main__':
    main()
