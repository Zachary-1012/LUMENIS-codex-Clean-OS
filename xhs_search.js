// Custom robust Xiaohongshu search via Playwright
// Usage: XHS_PROFILE_DIR=<registered-profile> node xhs_search.js --keyword "<topic>" --output ./data/search.json [--max-scroll 5]
import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs';
import { registeredXhsProfile } from './xhs_profile_guard.js';

const userDataDir = registeredXhsProfile();

function parseArgs() {
  const args = process.argv.slice(2);
  const result = { keyword: '', output: '', maxScroll: 4, sort: 'general' };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--keyword' && args[i+1]) result.keyword = args[++i];
    else if (args[i] === '--output' && args[i+1]) result.output = args[++i];
    else if (args[i] === '--max-scroll' && args[i+1]) result.maxScroll = parseInt(args[++i]);
    else if (args[i] === '--sort' && args[i+1]) result.sort = args[++i];
  }
  return result;
}

function normalizeNote(item) {
  const noteCard = item.note_card || {};
  const user = noteCard.user || {};
  const interact = noteCard.interact_info || {};
  const cover = noteCard.cover || {};
  const xsecToken = item.xsec_token || '';
  const noteId = item.id || '';
  const url = xsecToken
    ? `https://www.xiaohongshu.com/explore/${noteId}?xsec_token=${xsecToken}`
    : `https://www.xiaohongshu.com/explore/${noteId}`;
  // 提取发布时间：尝试多个可能的字段
  let publishDate = '';
  const timeStr = noteCard.time || noteCard.display_time || item.time || item.create_time || '';
  if (timeStr) {
    // 时间戳（秒或毫秒）
    if (/^\d{10}$/.test(timeStr)) publishDate = new Date(timeStr * 1000).toISOString().slice(0, 10);
    else if (/^\d{13}$/.test(timeStr)) publishDate = new Date(parseInt(timeStr)).toISOString().slice(0, 10);
    // 已经是 YYYY-MM-DD 格式
    else if (/^\d{4}-\d{2}-\d{2}/.test(timeStr)) publishDate = timeStr.slice(0, 10);
    // MM-DD 格式（补全年份）
    else if (/^\d{1,2}-\d{1,2}/.test(timeStr)) {
      const now = new Date();
      publishDate = `${now.getFullYear()}-${timeStr.slice(0, 5)}`;
    }
    // 相对时间（昨天/前天/N天前）
    else if (timeStr.includes('昨天')) {
      const d = new Date(); d.setDate(d.getDate() - 1);
      publishDate = d.toISOString().slice(0, 10);
    } else if (timeStr.includes('前天')) {
      const d = new Date(); d.setDate(d.getDate() - 2);
      publishDate = d.toISOString().slice(0, 10);
    } else if (/(\d+)天前/.test(timeStr)) {
      const days = parseInt(timeStr.match(/(\d+)天前/)[1]);
      const d = new Date(); d.setDate(d.getDate() - days);
      publishDate = d.toISOString().slice(0, 10);
    } else if (timeStr.includes('小时前') || timeStr.includes('分钟前') || timeStr.includes('刚刚')) {
      publishDate = new Date().toISOString().slice(0, 10);
    }
  }
  // 从note_id前8位十六进制时间戳推断（小红书note_id前8位是秒级时间戳）
  if (!publishDate && noteId && noteId.length >= 8) {
    try {
      const ts = parseInt(noteId.slice(0, 8), 16);
      if (ts > 1000000000 && ts < 2000000000) {
        publishDate = new Date(ts * 1000).toISOString().slice(0, 10);
      }
    } catch(e) {}
  }
  return {
    note_id: noteId,
    title: noteCard.display_title || noteCard.title || '',
    url,
    cover: cover.url_default || cover.url_pre || cover.url || '',
    author_id: user.user_id || '',
    author_nickname: user.nickname || user.nick_name || '',
    author_avatar: user.avatar || '',
    likes: interact.liked_count || 0,
    comments: interact.comment_count || 0,
    collects: interact.collected_count || 0,
    shares: interact.shared_count || 0,
    model_type: item.model_type || '',
    xsec_token: xsecToken,
    type: noteCard.type || '',
    publish_date: publishDate,
    time_raw: timeStr,
  };
}

async function main() {
  const { keyword, output, maxScroll, sort } = parseArgs();
  if (!keyword) {
    console.error('ERROR: --keyword is required');
    process.exit(1);
  }

  console.error(`[search] keyword="${keyword}" maxScroll=${maxScroll}`);
  const encodedKeyword = encodeURIComponent(keyword);
  const searchUrl = `https://www.xiaohongshu.com/search_result?keyword=${encodedKeyword}&source=web_explore_feed`;

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: process.env.XHS_HEADFUL === '1' ? false : true,  // 新版 playwright 只接受布尔；XHS_HEADFUL=1 时有头拟人
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'],
  });

  const page = context.pages()[0] || await context.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  // 反检测：隐藏自动化特征
  await page.addInitScript(() => {
    // 1. 隐藏 navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    // 2. 伪造 chrome 对象
    window.chrome = window.chrome || { runtime: {} };
    // 3. 伪造 permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
    );
    // 4. 伪造 plugins 和 mimeTypes
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5],
    });
    Object.defineProperty(navigator, 'languages', {
      get: () => ['zh-CN', 'zh', 'en'],
    });
  });

  const allNotes = new Map();
  let apiCallCount = 0;

  // Intercept search API responses (broad match for GET/POST)
  page.on('response', async (response) => {
    try {
      const url = response.url();
      if (!url.includes('xiaohongshu.com') && !url.includes('xhscdn.com')) return;
      if (!url.includes('search') && !url.includes('sns/web')) return;
      if (response.status() !== 200) return;
      const ct = response.headers()['content-type'] || '';
      if (!ct.includes('json')) return;

      const data = await response.json();
      const items = data?.data?.items || data?.items || [];
      if (!items.length) return;
      apiCallCount++;
      console.error(`[search] API response #${apiCallCount}: ${items.length} items from ${url.substring(0,80)}`);
      for (const item of items) {
        if (item && (item.model_type === 'note' || item.note_card) && item.id) {
          const normalized = normalizeNote(item);
          if (!allNotes.has(normalized.note_id)) {
            allNotes.set(normalized.note_id, normalized);
          }
        }
      }
    } catch (e) {
      // ignore
    }
  });

  console.error('[search] Navigating to:', searchUrl);
  await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(8000);

  // Check if logged in
  try {
    const loginBtn = await page.locator("#login-btn, .login-btn, [class*='login-btn'], [class*='login-button'], [data-testid*='login']").count();
    if (loginBtn > 0) {
      console.error('[search] WARNING: Not logged in! Results may be limited.');
    }
  } catch(e) {}

  // Check for verification/captcha
  try {
    const captcha = await page.locator("[class*='captcha'], [class*='verify'], [class*='challenge']").count();
    if (captcha > 0) {
      console.error('[search] WARNING: Verification challenge detected!');
    }
  } catch(e) {}

  // Scroll to load more
  for (let i = 0; i < maxScroll; i++) {
    await page.evaluate(() => window.scrollBy(0, 1000));
    await page.waitForTimeout(3000);
    console.error(`[search] Scroll ${i+1}/${maxScroll}, total notes: ${allNotes.size}`);
  }

  // Also try to extract notes from DOM as fallback
  try {
    const domNotes = await page.evaluate(() => {
      const results = [];
      const seen = new Set();
      // 小红书搜索结果页的笔记卡片选择器（多种可能）
      const selectors = [
        'section.note-item', 'div.note-item', 'a.cover',
        '[data-note-id]', 'a[href*="/explore/"]',
        '.feeds-container section', '.search-result-item',
        '.note-item', '.feed-item'
      ];
      for (const sel of selectors) {
        document.querySelectorAll(sel).forEach(el => {
          const link = el.tagName === 'A' ? el : (el.querySelector('a[href*="/explore/"]') || el.querySelector('a'));
          const href = link?.href || el.getAttribute('href') || '';
          const match = href.match(/\/explore\/([a-zA-Z0-9_-]+)/);
          const noteId = match?.[1] || el.getAttribute('data-note-id') || '';
          if (noteId && !seen.has(noteId)) {
            seen.add(noteId);
            const titleEl = el.querySelector('.title, .note-title, [class*="title"]');
            const authorEl = el.querySelector('.author, .nickname, [class*="nickname"], [class*="author"]');
            results.push({
              note_id: noteId,
              url: href || `https://www.xiaohongshu.com/explore/${noteId}`,
              title: titleEl?.textContent?.trim() || '',
              author_nickname: authorEl?.textContent?.trim() || '',
            });
          }
        });
      }
      return results;
    });
    console.error(`[search] DOM extraction found ${domNotes.length} notes`);
    for (const n of domNotes) {
      if (!allNotes.has(n.note_id)) {
        allNotes.set(n.note_id, {
          note_id: n.note_id,
          title: n.title || '',
          url: n.url,
          cover: '',
          author_id: '',
          author_nickname: n.author_nickname || '',
          author_avatar: '',
          likes: 0, comments: 0, collects: 0, shares: 0,
          model_type: 'note', xsec_token: '', type: '',
          publish_date: '',
        });
      }
    }
  } catch (e) {
    console.error('[search] DOM extraction failed:', e.message);
  }

  await context.close();

  const notes = Array.from(allNotes.values());
  const result = {
    keyword,
    fetched_at: new Date().toISOString(),
    total: notes.length,
    api_calls: apiCallCount,
    notes,
  };

  if (output) {
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, JSON.stringify(result, null, 2), 'utf8');
    console.error(`[search] Saved ${notes.length} notes to ${output}`);
  }

  // Output JSON to stdout
  process.stdout.write(JSON.stringify(result));
}

main().catch(err => {
  console.error('[search] FATAL:', err.message);
  process.exit(1);
});
