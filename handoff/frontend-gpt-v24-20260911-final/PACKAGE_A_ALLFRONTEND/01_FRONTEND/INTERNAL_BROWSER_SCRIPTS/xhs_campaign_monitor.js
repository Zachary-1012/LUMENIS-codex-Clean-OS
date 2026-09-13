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

// 连接前用纯 HTTP CDP 接口把活动页复位为 about:blank（不走 WebSocket，不受挂起影响）。
// 根因：connectOverCDP 会 attach 现有 page；若停在小红书等"重页面"（持续 XHR / 长连接 / 复杂 JS），
// attach 阶段的 CDP 初始化会挂起直到 30s 超时。复位为 about:blank 后可秒连。专用采集 profile，关闭其采集页安全（登录态在 profile 内不依赖页面）。
async function resetCdpTargets(cdpUrl) {
  try {
    const base = cdpUrl.replace(/\/$/, '');
    const get = async (u, opt) => { try { return await (await fetch(u, opt)).text(); } catch { return ''; } };
    let list = [];
    try { list = JSON.parse(await get(base + '/json/list')); } catch { return; }
    const heavy = list.filter(t => t.type === 'page' && t.url && !t.url.includes('about:blank'));
    if (!heavy.length) return; // 已是干净态，无需复位
    await get(base + '/json/new?about:blank', { method: 'PUT' });           // 新版 Chromium 需 PUT
    await get(base + '/json/new?about:blank');                              // 旧版 GET 兜底
    await new Promise(r => setTimeout(r, 500));
    let list2 = [];
    try { list2 = JSON.parse(await get(base + '/json/list')); } catch { list2 = list; }
    for (const t of list2) {
      if (t.type === 'page' && t.url && !t.url.includes('about:blank')) {
        await get(base + '/json/close/' + t.id);
      }
    }
    await new Promise(r => setTimeout(r, 400));
  } catch { /* 复位失败不阻断，交给 connectOverCDP 自身超时/上层硬超时 */ }
}

/**
 * 风控/安全验证页识别（P0 红线：绝不能把验证码/安全验证/IP风控当成“0条笔记 ok=true”）
 * 返回 {hit,status,reason}；status: NEED_VERIFY（需人工扫码/滑块）| IP_RISK（频率/IP 限制）
 */
async function detectRisk(page) {
  try {
    const u = page.url() || '';
    const body = await page.evaluate(() => document.body ? (document.body.innerText || '').slice(0, 1000) : '').catch(() => '');
    if (/website-login\/captcha|\/website-login\/|verifyType=|\/login\?/.test(u))
      return { hit: true, status: 'NEED_VERIFY', reason: '跳转登录/扫码安全验证页（verifyType），需在已登录浏览器人工扫码', pageUrl: u };
    if (/扫码验证|扫码验证身份|安全验证|拖动滑块|完成验证|人机验证|请使用.*APP.*扫码/.test(body))
      return { hit: true, status: 'NEED_VERIFY', reason: '页面出现安全/扫码/滑块验证，需人工完成验证', pageUrl: u };
    if (/访问过于频繁|操作过于频繁|操作频繁|稍后再试|系统繁忙|账号异常|限制访问|IP风险|300012/.test(body))
      return { hit: true, status: 'IP_RISK', reason: '频率/IP 风控提示，需熔断冷却', pageUrl: u };
    return { hit: false };
  } catch { return { hit: false }; }
}

// 输出结构化风控结果并以独立退出码退出：3=NEED_VERIFY，4=IP_RISK（区别于 1 普通错误、2 硬超时）
function emitRisk(topic, status, reason, pageUrl) {
  const out = {
    ok: false, topic, risk_status: status, status, error: reason,
    need_manual_verify: status === 'NEED_VERIFY',
    captured_at: new Date().toISOString(), page_url: pageUrl || '',
  };
  try { process.stdout.write(JSON.stringify(out)); } catch {}
  process.exit(status === 'NEED_VERIFY' ? 3 : 4);
}

async function main() {
  let browser, context;
  // 硬超时兜底：任何环节（CDP 握手 / goto / service worker / close）意外挂起时强制退出，
  // 绝不伪造数据；避免父进程 subprocess.run 永久等待导致快照不落地
  const hardTimer = setTimeout(() => {
    try { process.stdout.write(JSON.stringify({ ok: false, topic, error: '采集硬超时(150s)保护退出，未伪造数据' })); } catch {}
    process.exit(2);
  }, 150000);
  try {
    if (cdpUrl) {
      // 模式1：连接已运行的 CDP 浏览器（已登录）；先 HTTP 复位重页面，避免 attach 挂起
      await resetCdpTargets(cdpUrl);
      browser = await chromium.connectOverCDP(cdpUrl, { timeout: 20000 });
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

    // CDP 模式：关闭可能处于僵死/重状态的既有页，新建干净工作页（残留页 attach/evaluate 可能挂起）
    if (cdpUrl) {
      for (const oldPage of context.pages()) { try { await oldPage.close(); } catch {} }
    }
    const page = context.pages()[0] || await context.newPage();
    const notes = new Map();
    // 命中风控/验证：复位工作页 -> 断开 -> 输出结构化状态后退出（不继续任何请求）
    const abortRisk = async (info) => {
      try { if (cdpUrl) await page.goto('about:blank', { timeout: 4000 }); } catch {}
      try { await Promise.race([cdpUrl ? browser.close() : context.close(), new Promise(r => setTimeout(r, 4000))]); } catch {}
      clearTimeout(hardTimer);
      emitRisk(topic, info.status, info.reason, info.pageUrl || page.url());
    };

    // 拦截搜索 API 响应，获取完整笔记数据（含互动数据）
    page.on('response', async (response) => {
      try {
        const req = response.request();
        if (req.method().toLowerCase() !== 'post' || response.status() !== 200) return;
        // 兼容 v1(edith.xiaohongshu.com) 与 v2(so.xiaohongshu.com) 两版笔记搜索接口，不写死版本号
        if (!/\/api\/sns\/web\/v\d+\/search\/notes/.test(response.url())) return;
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

    // 进站预热：小红书对 search_result 冷导航（无站内 referer / 会话上下文）会挂起文档响应，
    // 真人也是先打开站点再站内搜索。先访问 explore 建立会话，再进搜索页，避免 goto 超时（已实测：冷跳搜索页 30s 超时，预热后 1.1s）
    await page.goto('https://www.xiaohongshu.com/explore', { waitUntil: 'domcontentloaded', timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1200);
    // 进站即触发验证：直接熔断，不进搜索页（避免加重风控）
    let __pre = await detectRisk(page);
    if (__pre.hit) { await abortRisk(__pre); return; }
    // 访问搜索结果页
    const searchKeyword = topic.replace(/^#/, '');
    const url = `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(searchKeyword)}&source=web_explore_feed`;
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(PAGE_WAIT);
    // 搜索后检测：被重定向到验证/风控页则立即停止，绝不当作 0 条
    let __post = await detectRisk(page);
    if (__post.hit) { await abortRisk(__post); return; }

    // 提取话题浏览量/讨论量（滚动前提取，话题卡片在页面顶部）
    const topicMetrics = await extractTopicMetrics(page);

    // 滚动加载更多笔记（中频率：间隔2.5秒，安全第一）
    let scrollRisk = null;
    for (let i = 0; i < maxScroll; i++) {
      await page.evaluate(() => window.scrollBy(0, 1000)).catch(() => {});
      await page.waitForTimeout(SCROLL_DELAY);
      const __sr = await detectRisk(page);
      if (__sr.hit) { scrollRisk = __sr; break; } // 滚动中触发验证/风控：立即停止，不再继续请求
    }
    if (scrollRisk) { await abortRisk(scrollRisk); return; }

    // DOM 兜底：API 未拦截到时从渲染卡片提取（浏览器上下文必须自包含，不能引用 node 侧 clean）
    try {
      const domNotes = await page.evaluate(() => {
        const txt = el => (el && el.innerText ? el.innerText : '').replace(/\s+/g, ' ').trim();
        const pickId = h => {
          const m = h.match(/\/explore\/([A-Za-z0-9_-]+)/) || h.match(/\/search_result\/([A-Za-z0-9_-]+)/);
          return m ? m[1] : '';
        };
        const out = [];
        document.querySelectorAll('section.note-item').forEach(sec => {
          const a = sec.querySelector('a[href*="/explore"],a[href*="/search_result"]');
          const id = a ? pickId(a.href) : '';
          if (!id) return;
          out.push({
            note_id: id, note_url: a.href,
            title: txt(sec.querySelector('.title, .note-title, a')),
            author: txt(sec.querySelector('.author .name, .name, .author-wrapper .name')),
            likeTxt: txt(sec.querySelector('.like-wrapper .count, .like-count, .count')),
          });
        });
        document.querySelectorAll('a[href*="/explore/"]').forEach(a => {
          const id = pickId(a.href);
          if (id) out.push({ note_id: id, note_url: a.href, title: txt(a), author: '', likeTxt: '' });
        });
        return out;
      });
      const parseLike = t => {
        if (!t) return 0; const m = t.match(/([\d.]+)\s*(万|亿)?/); if (!m) return 0;
        let n = Number(m[1]); if (m[2] === '万') n *= 1e4; if (m[2] === '亿') n *= 1e8; return Math.round(n);
      };
      for (const x of domNotes) {
        if (!notes.has(x.note_id)) {
          notes.set(x.note_id, {
            note_id: x.note_id, title: clean(x.title), content: '', author: clean(x.author || ''),
            likes: parseLike(x.likeTxt), comments: 0, collects: 0, shares: 0,
            note_url: x.note_url, publish_datetime: '', xsec_token: '',
          });
        }
      }
    } catch {}

    if (cdpUrl) { try { await page.goto('about:blank', { timeout: 5000 }); } catch {} }
    // 关闭连接（CDP 模式下断开、不关闭原浏览器）；加 5s 超时保护，
    // 避免 service worker / 残留 CDP ws 让 close 挂住
    await Promise.race([
      cdpUrl ? browser.close() : context.close(),
      new Promise(r => setTimeout(r, 5000)),
    ]).catch(() => {});

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
    clearTimeout(hardTimer);
    process.stdout.write(JSON.stringify(result));
    // 关键：connectOverCDP 的 ws / service worker 可能让事件循环挂住，结果已输出必须显式退出，
    // 否则父进程 subprocess.run 一直等待、快照无法落地
    process.exit(0);
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
