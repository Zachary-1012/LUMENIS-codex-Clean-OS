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
        'field_status': {
            'content': 'FAILED',
            'media': 'FAILED',
            'comments_detail': 'FAILED',
        },
        'field_errors': {},
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
            result['field_status']['content'] = 'AVAILABLE' if result['content'] else 'EMPTY'
        except Exception as e:
            result['field_errors']['content'] = type(e).__name__
            print(f'    正文提取失败: {type(e).__name__}')

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
            result['field_status']['media'] = 'AVAILABLE' if result['media'] else 'EMPTY'
        except Exception as e:
            result['field_errors']['media'] = type(e).__name__
            print(f'    媒体提取失败: {type(e).__name__}')

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
            result['field_status']['comments_detail'] = (
                'AVAILABLE' if result['comments_detail'] else 'EMPTY'
            )
        except Exception as e:
            result['field_errors']['comments_detail'] = type(e).__name__
            print(f'    评论提取失败: {type(e).__name__}')

    except RuntimeError:
        raise
    except Exception as e:
        result['field_errors']['page'] = type(e).__name__
        print(f'    详情页加载失败: {type(e).__name__}')

    return result


def update_note_detail(conn, note_id, campaign_key, topic, detail):
    """Merge verified non-empty fields without erasing prior detail on failure.

    This owner is an additive backfill: an empty extraction is not evidence that
    a previously captured field should be deleted. The caller retains transaction
    ownership and decides when to commit.
    """
    row = conn.execute(
        """SELECT content, media_json, comments_json, evidence_quality, detail_captured_at
           FROM topic_campaign_notes
           WHERE note_id=? AND campaign_key=? AND topic=?""",
        (note_id, campaign_key, topic),
    ).fetchone()
    if row is None:
        return 0, 'failed'

    columns = ('content', 'media_json', 'comments_json', 'evidence_quality', 'detail_captured_at')
    existing = dict(zip(columns, row))
    statuses = detail.get('field_status')
    updates = {}
    accepted_fields = set()

    def status_for(field):
        if isinstance(statuses, dict):
            return statuses.get(field, 'FAILED')
        # Keep the former helper call shape usable for non-extractor callers;
        # only non-empty values are evidence that can be merged.
        return 'AVAILABLE' if detail.get(field) else 'EMPTY'

    content = detail.get('content')
    if (status_for('content') == 'AVAILABLE'
            and isinstance(content, str) and content.strip()):
        content = content.strip()[:5000]
        accepted_fields.add('content')
        if content != (existing['content'] or ''):
            updates['content'] = content

    field_values = {}
    for field, column in (('media', 'media_json'), ('comments_detail', 'comments_json')):
        value = detail.get(field, [])
        if status_for(field) != 'AVAILABLE' or not isinstance(value, list) or not value:
            continue
        encoded = json.dumps(value, ensure_ascii=False)
        if len(encoded) > 50000:
            detail.setdefault('field_errors', {})[field] = 'StorageLimitExceeded'
            continue
        accepted_fields.add(field)
        field_values[field] = value
        old_encoded = existing[column]
        try:
            same_value = json.loads(old_encoded or '[]') == value
        except (TypeError, ValueError):
            same_value = False
        if not same_value:
            updates[column] = encoded

    if not updates:
        if accepted_fields:
            return 0, 'unchanged'
        if isinstance(statuses, dict) and all(
                statuses.get(field) == 'EMPTY'
                for field in ('content', 'media', 'comments_detail')):
            return 0, 'empty'
        return 0, 'failed'

    merged_content = updates.get('content', existing['content'])
    if 'media' in field_values:
        merged_media = field_values['media']
        media_known = isinstance(merged_media, list)
    else:
        try:
            merged_media = json.loads(existing['media_json'] or '[]')
            media_known = isinstance(merged_media, list)
        except (TypeError, ValueError):
            merged_media, media_known = [], False

    if 'comments_detail' in field_values:
        merged_comments = field_values['comments_detail']
        comments_known = isinstance(merged_comments, list)
    else:
        try:
            merged_comments = json.loads(existing['comments_json'] or '[]')
            comments_known = isinstance(merged_comments, list)
        except (TypeError, ValueError):
            merged_comments, comments_known = [], False

    has_content = isinstance(merged_content, str) and bool(merged_content.strip())
    has_media = bool(merged_media) if media_known else False
    has_comments = bool(merged_comments) if comments_known else False
    if has_content and has_media and has_comments:
        quality = 'full'
    elif has_content or has_media:
        quality = 'partial'
    else:
        quality = 'search_only'
    # If untouched legacy payloads are unreadable, retain their prior quality
    # instead of downgrading it based on an unknown parse result.
    if (not media_known or not comments_known) and existing['evidence_quality'] in ('full', 'partial'):
        quality = existing['evidence_quality']
    if quality != existing['evidence_quality']:
        updates['evidence_quality'] = quality

    captured_at = detail.get('detail_captured_at')
    if isinstance(captured_at, str) and captured_at and captured_at != existing['detail_captured_at']:
        updates['detail_captured_at'] = captured_at

    assignments = ', '.join(f'{column}=?' for column in updates)
    params = (*updates.values(), note_id, campaign_key, topic)
    cur = conn.execute(
        f"UPDATE topic_campaign_notes SET {assignments} "
        "WHERE note_id=? AND campaign_key=? AND topic=?",
        params,
    )
    capture_quality = 'full' if len(accepted_fields) == 3 else 'partial'
    return cur.rowcount, capture_quality


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
    unchanged = 0
    empty = 0
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
                for field, error_type in detail.get('field_errors', {}).items():
                    print(f'    {field} 未核验: {error_type}；原有字段保留')
                if eq == 'full':
                    success += 1
                    print(f'    OK full (content={len(detail["content"])}字, media={len(detail["media"])}, comments={len(detail["comments_detail"])})')
                elif eq == 'partial':
                    partial += 1
                    print(f'    OK partial (content={len(detail["content"])}字, media={len(detail["media"])})')
                elif eq == 'unchanged':
                    unchanged += 1
                    print('    详情已读取，但与已有字段相同；保留原记录')
                elif eq == 'empty':
                    empty += 1
                    print('    本次详情为空；原有字段与质量状态保留')
                else:
                    failed += 1
                    print(f'    未写入新详情 (matched={updated})；原有字段与质量状态保留')
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
    print(f'  full: {success}, partial: {partial}, unchanged: {unchanged}, empty: {empty}, failed: {failed}')
    if stopped_by_captcha:
        print('  因触发验证提前停止，请完成验证后继续。')


if __name__ == '__main__':
    main()
