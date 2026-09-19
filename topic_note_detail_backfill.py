# -*- coding: utf-8 -*-
"""
V2.0 P0-5：Topic Note Detail 补抓脚本

对 evidence_quality='search_only' 的笔记，进入小红书详情页获取：
  - 正文 content
  - 媒体列表 media
  - 评论列表 comments_detail
  - 更新 evidence_quality 为 full/partial

使用方式：
  python topic_note_detail_backfill.py [--limit N] [--note-id ID] [--campaign-key KEY]

原则：
  - 连接 9222 已登录 CDP 浏览器，不启动新浏览器
  - 低频串行，每条间隔 3-8 秒，遇到验证立即停止
  - 绝不破解验证码、绕过风控
  - 主体判断仍由 subject_rules.py 负责（_save_notes 已集成）
"""
import os, sys, json, time, sqlite3, argparse, random
from lumenis.shared.database import get_repository, main_db_path
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = main_db_path()
CDP_URL = os.getenv('XHS_CDP_URL', 'http://127.0.0.1:9222')

# 熔断文件（与 topic_campaign.py 一致）
CIRCUIT_FILE = os.path.join(BASE_DIR, 'data', 'private', 'topic_campaign_circuit.json')


def check_circuit():
    """检查熔断状态，熔断中直接退出。"""
    if not os.path.exists(CIRCUIT_FILE):
        return None
    try:
        with open(CIRCUIT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def extract_note_detail(page, note_url):
    """从笔记详情页提取正文、媒体、评论。

    返回 dict: {content, media, comments_detail, detail_captured_at}
    提取失败返回部分数据，绝不伪造。
    """
    result = {
        'content': '',
        'media': [],
        'comments_detail': [],
        'detail_captured_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    try:
        page.goto(note_url, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_timeout(3000)

        # 检查是否跳验证页
        cur_url = page.url or ''
        if any(k in cur_url for k in ('captcha', 'website-login', '/login')):
            body = ''
            try:
                body = page.evaluate("() => document.body ? document.body.innerText.slice(0,300) : ''") or ''
            except Exception:
                pass
            if any(k in body for k in ('扫码', '验证', '滑块', '人机')):
                raise RuntimeError('DETAIL_CAPTCHA: 详情页跳转验证页')

        # 提取正文（小红书笔记正文通常在 #detail-desc 或 .note-content 或 meta）
        try:
            content = page.evaluate("""() => {
                const sel = ['#detail-desc', '.note-content', '.content', 'meta[property="og:description"]'];
                for (const s of sel) {
                    const el = document.querySelector(s);
                    if (el) {
                        if (s.startsWith('meta')) return el.getAttribute('content') || '';
                        return el.innerText || el.textContent || '';
                    }
                }
                return '';
            }""") or ''
            result['content'] = content.strip()[:5000]
        except Exception as e:
            print(f'    正文提取失败: {e}')

        # 提取媒体图片
        try:
            media = page.evaluate("""() => {
                const imgs = [];
                document.querySelectorAll('.note-slider-img, .swiper-slide img, .content img, img').forEach(img => {
                    const src = img.src || img.getAttribute('data-src') || '';
                    if (src && src.startsWith('http') && !src.includes('sns-web') && imgs.length < 20) {
                        imgs.push({url: src, alt: img.alt || ''});
                    }
                });
                return imgs;
            }""") or []
            result['media'] = media
        except Exception as e:
            print(f'    媒体提取失败: {e}')

        # 提取评论（滚动加载前几条）
        try:
            comments = page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('.comment-item, .list-container .comment, [class*="comment"] .item').forEach(item => {
                    if (list.length >= 30) return;
                    const author = item.querySelector('.author, .user-name, .nickname')?.innerText || '';
                    const text = item.querySelector('.content, .comment-content, .text')?.innerText || '';
                    const likes = item.querySelector('.like-count, .like, .count')?.innerText || '0';
                    if (text) list.push({author, content: text.slice(0,500), likes: likes});
                });
                return list;
            }""") or []
            result['comments_detail'] = comments
        except Exception as e:
            print(f'    评论提取失败: {e}')

    except RuntimeError:
        raise
    except Exception as e:
        print(f'    详情页加载失败: {e}')

    return result


def update_note_detail(conn, note_id, campaign_key, topic, detail):
    """更新笔记详情到数据库。"""
    has_content = bool(detail.get('content'))
    has_media = bool(detail.get('media'))
    has_comments = bool(detail.get('comments_detail'))
    if has_content and has_media and has_comments:
        eq = 'full'
    elif has_content or has_media:
        eq = 'partial'
    else:
        eq = 'search_only'

    media_json = json.dumps(detail.get('media', []), ensure_ascii=False)[:50000]
    comments_json = json.dumps(detail.get('comments_detail', []), ensure_ascii=False)[:50000]

    cur = conn.execute(
        """UPDATE topic_campaign_notes
           SET content=?, media_json=?, comments_json=?, evidence_quality=?, detail_captured_at=?
           WHERE note_id=? AND campaign_key=? AND topic=?""",
        (detail.get('content', ''), media_json, comments_json, eq,
         detail.get('detail_captured_at', ''), note_id, campaign_key, topic)
    )
    return cur.rowcount, eq


def main():
    parser = argparse.ArgumentParser(description='Topic Note Detail 补抓')
    parser.add_argument('--limit', type=int, default=0, help='最多补抓条数（0=全部）')
    parser.add_argument('--note-id', type=str, default='', help='只补抓指定 note_id')
    parser.add_argument('--campaign-key', type=str, default='taikoo_15th', help='campaign_key')
    parser.add_argument('--dry-run', action='store_true', help='只列出待补抓，不实际抓取')
    args = parser.parse_args()

    # 熔断检查
    cb = check_circuit()
    if cb:
        print(f'[熔断中] status={cb.get("status")}, reason={cb.get("reason")}')
        print('请先在系统内完成扫码验证并解除熔断，再运行补抓。')
        sys.exit(1)

    conn = get_repository().connect()
    conn.row_factory = sqlite3.Row

    # 查询待补抓笔记
    if args.note_id:
        rows = conn.execute(
            'SELECT * FROM topic_campaign_notes WHERE note_id=? AND campaign_key=?',
            (args.note_id, args.campaign_key)
        ).fetchall()
    else:
        q = """SELECT * FROM topic_campaign_notes
               WHERE campaign_key=? AND (evidence_quality='search_only' OR evidence_quality IS NULL OR content='' OR content IS NULL)
               ORDER BY last_seen_at DESC"""
        rows = conn.execute(q, (args.campaign_key,)).fetchall()

    if args.limit > 0:
        rows = rows[:args.limit]

    print(f'待补抓: {len(rows)} 条')
    if args.dry_run:
        for r in rows[:20]:
            print(f'  {r["note_id"]} | {r["title"][:40]} | {r["note_url"][:50]}')
        conn.close()
        return

    if not rows:
        print('没有需要补抓的笔记。')
        conn.close()
        return

    # 连接 CDP 浏览器
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('错误: 未安装 playwright，请先运行 pip install playwright')
        conn.close()
        sys.exit(1)

    success = 0
    partial = 0
    failed = 0
    stopped_by_captcha = False

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.connect_over_cdp(CDP_URL, timeout=15000)
            ctx = browser.contexts[0]
        except Exception as e:
            print(f'连接 CDP 失败: {e}')
            print(f'请确认 9222 浏览器已启动: {CDP_URL}')
            conn.close()
            sys.exit(1)

        page = ctx.new_page()
        for i, r in enumerate(rows):
            nid = r['note_id']
            url = r['note_url'] or f'https://www.xiaohongshu.com/explore/{nid}'
            title = (r['title'] or '')[:40]
            print(f'[{i+1}/{len(rows)}] {nid} | {title}')

            try:
                detail = extract_note_detail(page, url)
                updated, eq = update_note_detail(conn, nid, r['campaign_key'], r['topic'], detail)
                conn.commit()
                if eq == 'full':
                    success += 1
                    print(f'    OK full (content={len(detail["content"])}字, media={len(detail["media"])}, comments={len(detail["comments_detail"])})')
                elif eq == 'partial':
                    partial += 1
                    print(f'    OK partial (content={len(detail["content"])}字, media={len(detail["media"])})')
                else:
                    failed += 1
                    print(f'    未获取到详情')
            except RuntimeError as e:
                if 'DETAIL_CAPTCHA' in str(e):
                    print(f'    [触发验证] 停止补抓，已处理 {i} 条')
                    stopped_by_captcha = True
                    break
                failed += 1
            except Exception as e:
                failed += 1
                print(f'    异常: {e}')

            # 拟人间隔 3-8 秒
            if i < len(rows) - 1:
                wait = random.uniform(3, 8)
                time.sleep(wait)

        try:
            page.goto('about:blank', timeout=5000)
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass

    conn.close()
    print(f'\n===== 补抓完成 =====')
    print(f'  full: {success}, partial: {partial}, failed: {failed}')
    if stopped_by_captcha:
        print('  因触发验证提前停止，请完成验证后继续。')


if __name__ == '__main__':
    main()
