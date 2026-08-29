// v5.7.3 活动专题监测 - 小红书话题采集脚本（中频率，安全采集）
// 功能：提取话题浏览量/讨论量 + 话题下笔记及完整互动数据（点赞/评论/收藏/分享）
// 安全策略：API拦截优先，DOM兜底；滚动间隔≥2.5秒；绝不伪造数据，采不到返回0+错误信息
// 支持两种模式：--cdp（连接已登录浏览器）或 --profile（持久化 profile）
import { chromium } from 'playwright';
import path from 'node:path';
import os from 'node:os';

function arg(name, d = '') {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : d;
}

const topic = arg('--topic', '');
const cdpUrl = arg('--cdp', '');
const profileDir = arg('--profile', path.join(os.homedir(), '.skills-router', 'rednote', 'instances', 'taikoo'));
// 中频率充分采集：默认滚动6次，每次间隔2.5秒（安全第一）
const maxScroll = Math.max(1, Math.min(10, Number(arg('--max-scroll', '6')) || 6));
const SCROLL_DELAY = 2500; // 滚动间隔（毫秒），≥2.5秒保护账号
const PAGE_WAIT = 3500;    // 页面初始加载等待

if (!topic) {
  console.error(JSON.stringify({ ok: false, error: '--topic 必填' }));
  process.exit(1);
}

function clean(s) {
  return String(s || '').replace(/\s+/g, ' ').trim();
}

function parseNum(s) {
  const str = String(s || '').replace(/[,，\s]/g, '');
  const m = str.match(/(\d+(?:\.\d+)?)(万|亿)?/);
  if (!m) return 0;
  let n = Number(m[1]);
  if (m[2] === '万') n *= 1e4;
  if (m[2] === '亿') n *= 1e8;
  return Math.round(n);
}

function normalize(item) {
  const card = item.note_card || {}, user = card.user || {}, interact = card.interact_info || {};
  const noteId = item.id || '';
  const token = item.xsec_token || '';
  const url = token
    ? `https://www.xiaohongshu.com/explore/${noteId}?xsec_token=${encodeURIComponent(token)}`
    : `https://www.xiaohongshu.com/explore/${noteId}`;
  const raw = card.time ?? card.display_time ?? item.time ?? '';
  let publishDate = '';
  const s = String(raw);
  if (/^\d{10}$/.test(s)) publishDate = new Date(Number(s) * 1000).toISOString().slice(0, 10);
  else if (/^\d{13}$/.test(s)) publishDate = new Date(Number(s)).toISOString().slice(0, 10);
  else if (/^\d{4}-\d{2}-\d{2}/.test(s)) publishDate = s.slice(0, 10);
  else if (/^\d{1,2}-\d{1,2}/.test(s)) publishDate = `${new Date().getFullYear()}-${s.slice(0, 5)}`;
  else if (s.includes('昨天')) { const d = new Date(); d.setDate(d.getDate() - 1); publishDate = d.toISOString().slice(0, 10); }
  else if (s.includes('前天')) { const d = new Date(); d.setDate(d.getDate() - 2); publishDate = d.toISOString().slice(0, 10); }
  else if (/(\d+)天前/.test(s)) { const d = new Date(); d.setDate(d.getDate() - Number(s.match(/(\d+)天前/)[1])); publishDate = d.toISOString().slice(0, 10); }
  else if (s.includes('小时前') || s.includes('分钟前') || s.includes('刚刚')) publishDate = new Date().toISOString().slice(0, 10);
  return {
    note_id: noteId,
    title: card.display_title || card.title || '',
    content: '',
    author: user.nickname || user.nick_name || '',
    likes: Number(interact.liked_count || 0),
    comments: Number(interact.comment_count || 0),
    collects: Number(interact.collected_count || 0),
    shares: Number(interact.shared_count || interact.share_count || 0),
    note_url: url,
    publish_datetime: publishDate,
    xsec_token: token,
  };
}

// 从页面提取话题浏览量/讨论量（多种策略，绝不伪造）
async function extractTopicMetrics(page) {
  const result = { browse_count: 0, discussion_count: 0, found: false, method: '' };
  try {
    // 策略1：从页面整体文本匹配（最稳健）
    const bodyText = await page.evaluate(() => document.body ? document.body.innerText : '').catch(() => '');
    // 匹配 "123.4万 浏览" / "5678 讨论" 等格式
    const browseMatch = bodyText.match(/(\d+(?:\.\d+)?)\s*(万|亿)?\s*浏览/);
    const discussMatch = bodyText.match(/(\d+(?:\.\d+)?)\s*(万|亿)?\s*讨论/);
    if (browseMatch) {
      result.browse_count = parseNum(browseMatch[0]);
      result.found = true;
      result.method = 'body-text';
    }
    if (discussMatch) {
      result.discussion_count = parseNum(discussMatch[0]);
      result.found = true;
      result.method = result.method || 'body-text';
    }

    // 策略2：如果正文没找到，尝试从特定元素提取
    if (!result.found) {
      const domMetrics = await page.evaluate(() => {
        const r = { browse: 0, discussion: 0, found: false };
        // 查找包含"浏览"或"讨论"的元素
        const allElements = document.querySelectorAll('span, div, p, em, strong');
        for (const el of allElements) {
          const text = (el.innerText || el.textContent || '').trim();
          if (!text || text.length > 30) continue;
          if (/浏览/.test(text) && r.browse === 0) {
            const m = text.match(/(\d+(?:\.\d+)?)\s*(万|亿)?/);
            if (m) {
              let n = Number(m[1]);
              if (m[2] === '万') n *= 1e4;
              if (m[2] === '亿') n *= 1e8;
              r.browse = Math.round(n);
              r.found = true;
            }
          }
          if (/讨论/.test(text) && r.discussion === 0) {
            const m = text.match(/(\d+(?:\.\d+)?)\s*(万|亿)?/);
            if (m) {
              let n = Number(m[1]);
              if (m[2] === '万') n *= 1e4;
              if (m[2] === '亿') n *= 1e8;
              r.discussion = Math.round(n);
              r.found = true;
            }
          }
          if (r.browse > 0 && r.discussion > 0) break;
        }
        return r;
      }).catch(() => ({ browse: 0, discussion: 0, found: false }));
      if (domMetrics.found) {
        result.browse_count = domMetrics.browse;
        result.discussion_count = domMetrics.discussion;
        result.found = true;
        result.method = 'dom-element';
      }
    }
  } catch (e) {
    result.error = String(e.message || e);
  }
  // 注意：如果没找到，found=false，browse_count/discussion_count保持0，绝不伪造
  return result;
}

async function main() {
  let browser, context;
  try {
    if (cdpUrl) {
      // 模式1：连接已运行的 CDP 浏览器（已登录）
      browser = await chromium.connectOverCDP(cdpUrl);
      const contexts = browser.contexts();
      if (!contexts.length) throw new Error('CDP 连接成功但无 browser context');
      context = contexts[0];
    } else {
      // 模式2：使用持久化 profile 启动 Playwright
      context = await chromium.launchPersistentContext(profileDir, {
        headless: true,
        args: ['--disable-blink-features=AutomationControlled'],
      });
    }

    const page = context.pages()[0] || await context.newPage();
    const notes = new Map();

    // 拦截搜索 API 响应，获取完整笔记数据（含互动数据）
    page.on('response', async (response) => {
      try {
        const req = response.request();
        if (req.method().toLowerCase() !== 'post' || response.status() !== 200) return;
        if (!response.url().includes('/api/sns/web/v1/search/notes')) return;
        const ct = response.headers()['content-type'] || '';
        if (!ct.includes('json')) return;
        const data = await response.json();
        for (const item of data?.data?.items || []) {
          if (item?.model_type === 'note' && item.id) {
            notes.set(item.id, normalize(item));
          }
        }
      } catch {}
    });

    // 访问搜索结果页
    const searchKeyword = topic.replace(/^#/, '');
    const url = `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(searchKeyword)}&source=web_explore_feed`;
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(PAGE_WAIT);

    // 提取话题浏览量/讨论量（滚动前提取，话题卡片在页面顶部）
    const topicMetrics = await extractTopicMetrics(page);

    // 滚动加载更多笔记（中频率：间隔2.5秒，安全第一）
    for (let i = 0; i < maxScroll; i++) {
      await page.evaluate(() => window.scrollBy(0, 1000)).catch(() => {});
      await page.waitForTimeout(SCROLL_DELAY);
    }

    // DOM 兜底：从页面链接提取笔记（API 未拦截到时的补充）
    try {
      const domNotes = await page.evaluate(() =>
        Array.from(document.querySelectorAll('a[href*="/explore/"]'))
          .map(a => ({
            note_id: (a.href.match(/\/explore\/([A-Za-z0-9_-]+)/) || [])[1],
            note_url: a.href,
            title: clean(a.innerText),
          }))
          .filter(x => x.note_id)
      );
      for (const x of domNotes) {
        if (!notes.has(x.note_id)) {
          notes.set(x.note_id, {
            note_id: x.note_id,
            title: x.title,
            content: '',
            author: '',
            likes: 0,
            comments: 0,
            collects: 0,
            shares: 0,
            note_url: x.note_url,
            publish_datetime: '',
            xsec_token: '',
          });
        }
      }
    } catch {}

    // 关闭浏览器（CDP 模式下断开连接，不关闭原浏览器）
    if (cdpUrl) {
      try { await browser.close(); } catch {}
    } else {
      await context.close();
    }

    const result = {
      ok: true,
      topic,
      browse_count: topicMetrics.browse_count || 0,
      discussion_count: topicMetrics.discussion_count || 0,
      topic_metrics_found: topicMetrics.found || false,
      topic_metrics_method: topicMetrics.method || '',
      note_count: notes.size,
      notes: [...notes.values()],
      captured_at: new Date().toISOString(),
      page_url: url,
      scroll_count: maxScroll,
    };
    process.stdout.write(JSON.stringify(result));
  } catch (e) {
    // 采集失败：返回错误信息，绝不伪造数据
    console.error(JSON.stringify({ ok: false, topic, error: String(e.message || e) }));
    process.exit(1);
  }
}

main().catch(e => {
  console.error(JSON.stringify({ ok: false, topic, error: String(e.message || e) }));
  process.exit(1);
});
