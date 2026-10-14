/**
 * rednote_collector.js — rednote 真实数据采集引擎
 * 
 * SYSTEM Owner registered local read-only browser worker only.
 * 采集链路：搜索 → 笔记列表 → 详情页 → 正文/互动/评论 → 数据质量 → 主体过滤
 * 
 * 用法：
 *   node rednote_collector.js --keyword "广州太古汇" --output data/result.json --max-details 10 --max-scroll 3
 * 
 * 环境变量：
 *   XHS_CDP_URL - SYSTEM Owner-resolved dynamic local worker endpoint (required)
 *   XHS_COLLECTION_HOST — 固定为 www.rednote.com
 * 
 * 注意：CDP 模式下不要调用 browser.close()，否则会关闭整个 Edge 浏览器。
 */

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('node:child_process');

// ========== 工具函数 ==========

function parseArgs() {
  const args = process.argv.slice(2);
  const result = { keyword: '广州太古汇', output: null, maxDetails: 10, maxScroll: 3, maxCommentPages: 3 };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--keyword' && args[i+1]) result.keyword = args[++i];
    else if (args[i] === '--output' && args[i+1]) result.output = args[++i];
    else if (args[i] === '--max-details' && args[i+1]) result.maxDetails = parseInt(args[++i]);
    else if (args[i] === '--max-scroll' && args[i+1]) result.maxScroll = parseInt(args[++i]);
    else if (args[i] === '--max-comment-pages' && args[i+1]) result.maxCommentPages = parseInt(args[++i]);
  }
  return result;
}

function parseCount(value) {
  if (value == null) return null;
  if (typeof value === 'number') {
    return Number.isSafeInteger(value) && value >= 0 ? value : null;
  }

  const raw = String(value).trim();
  if (!raw) return null;
  if (raw.includes(',') && !/^\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*万?\+?$/.test(raw)) {
    return null;
  }

  const normalized = raw.replace(/,/g, '');
  const match = normalized.match(/^(\d+(?:\.\d+)?)\s*(万)?\+?$/);
  if (!match) return null;

  const amount = Number(match[1]);
  const count = match[2] ? Math.round(amount * 10000) : amount;
  return Number.isSafeInteger(count) && count >= 0 ? count : null;
}

function parseExplicitDisplayDate(raw) {
  if (typeof raw !== 'string') return '';
  const match = raw.trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return '';

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > daysInMonth[month - 1]) return '';

  return `${match[1]}-${match[2]}-${match[3]}`;
}

function isYearlessDisplayDate(raw) {
  const match = raw.match(/^(\d{2})-(\d{2})$/);
  if (!match) return false;
  const month = Number(match[1]);
  const day = Number(match[2]);
  const daysInMonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return month >= 1 && month <= 12 && day >= 1 && day <= daysInMonth[month - 1];
}

function normalizePublishTime(raw) {
  if (typeof raw !== 'string') return '';
  const display = raw.trim();
  if (!display || /编辑/.test(display)) return '';
  return parseExplicitDisplayDate(display);
}

function sourceTimeFields(raw) {
  const sourceDisplayTime = typeof raw === 'string' ? raw : raw == null ? '' : String(raw);
  const display = sourceDisplayTime.trim();
  let sourcePublishedAt = '';
  let sourceUpdatedAt = '';
  let sourceTimeKind = 'UNKNOWN';

  const editMatch = display.match(/^编辑(?:于)?\s*(.*)$/);
  if (editMatch) {
    sourceUpdatedAt = parseExplicitDisplayDate(editMatch[1]);
    sourceTimeKind = 'UPDATE_DISPLAY';
  } else {
    sourcePublishedAt = parseExplicitDisplayDate(display);
    if (sourcePublishedAt) {
      sourceTimeKind = 'ABSOLUTE_DATE';
    } else if (isYearlessDisplayDate(display)) {
      sourceTimeKind = 'YEAR_UNKNOWN';
    } else if (/(?:\d+\s*(?:秒|分钟|小时|天|周|个月|年)前|刚刚|今天|昨天|前天)/.test(display)) {
      sourceTimeKind = 'RELATIVE_DISPLAY';
    }
  }

  return {
    source_display_time: sourceDisplayTime,
    source_published_at: sourcePublishedAt,
    source_updated_at: sourceUpdatedAt,
    source_time_kind: sourceTimeKind,
    source_publication_precision: sourcePublishedAt ? 'DATE' : 'UNKNOWN'
  };
}

function normalizeSearchNote(note) {
  return {
    ...note,
    ...sourceTimeFields(note.publish_time_raw),
    publish_time: normalizePublishTime(note.publish_time_raw),
    likes: parseCount(note.likes_raw),
    collects: null,
    shares: null
  };
}

// ========== 主采集逻辑 ==========

function detailCommentFields(detailFetched, detail) {
  // The broad `.count` selector has no semantic label and can include comment likes.
  // Keep the post-wide comments metric unknown until a dedicated source is available.
  const knownCount = value => Number.isSafeInteger(value) && value >= 0 ? value : null;
  const observedCommentCount = detailFetched === true
    ? knownCount(detail && detail.comment_count)
    : null;
  const loadedCommentCount = detailFetched === true
    ? knownCount(detail && detail.loaded_comment_count)
    : null;
  return {
    comments: null,
    comment_count: observedCommentCount,
    comments_collected: loadedCommentCount ?? observedCommentCount
  };
}

function detailEngagementFields(searchLikes) {
  // The detail page currently exposes only unscoped `.count` nodes. Preserve a
  // measured search like count (including zero) and leave detail collections unknown.
  const knownCount = value => Number.isSafeInteger(value) && value >= 0 ? value : null;
  return { likes: knownCount(searchLikes), collects: null };
}

function resolveRegisteredWorkerFromSystemOwner({
  execFile = execFileSync,
  pythonExecutable = process.env.LUMENIS_SERVICE_PYTHON,
} = {}) {
  const servicePython = String(pythonExecutable || '').trim();
  if (!servicePython || !path.isAbsolute(servicePython)) return null;
  const script = [
    'import json, sys',
    'sys.path.insert(0, __import__("os").getcwd())',
    'import cdp_helper',
    "state = cdp_helper.resolve_registered_xhs_worker(account='XHS_RETINAUT', headless=True)",
    "print(json.dumps({key: state.get(key) for key in ('available','code','account','profile','browser','port','endpoint','pid','headless','loopback_only')}, separators=(',', ':')))"
  ].join('; ');
  try {
    const output = execFile(servicePython, ['-c', script], {
      cwd: __dirname, encoding: 'utf8', windowsHide: true, timeout: 5000,
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
    const line = output.split(/\r?\n/).filter(Boolean).at(-1);
    return line ? JSON.parse(line) : null;
  } catch {
    return null;
  }
}

function sameRegisteredPath(actual, expected) {
  try {
    const actualPath = fs.realpathSync.native(actual);
    const expectedPath = fs.realpathSync.native(expected);
    return process.platform === 'win32'
      ? actualPath.toLocaleLowerCase('en-US') === expectedPath.toLocaleLowerCase('en-US')
      : actualPath === expectedPath;
  } catch {
    return false;
  }
}

async function verifyPreconnectedWorker(endpoint, options) {
  const resolver = options.registeredWorkerResolver || resolveRegisteredWorkerFromSystemOwner;
  const binding = await resolver();
  const code = typeof binding?.code === 'string' && /^XHS_[A-Z0-9_]+$/.test(binding.code)
    ? binding.code : 'COLLECTOR_WORKER_IDENTITY_UNVERIFIED';
  const port = Number(binding?.port);
  if (binding?.available !== true || binding.account !== 'XHS_RETINAUT'
      || binding.browser !== 'edge' || binding.headless !== true
      || binding.loopback_only !== true || !Number.isSafeInteger(binding.pid) || binding.pid <= 0
      || !Number.isInteger(port) || port < 1 || port > 65535
      || new Set([9222, 9223, 9224, 9225, 9226, 9227, 9228]).has(port)
      || binding.endpoint !== `http://127.0.0.1:${port}`
      || endpoint.origin !== binding.endpoint) {
    return { ok: false, code };
  }
  const { registeredXhsProfile } = await import('./xhs_profile_guard.js');
  const expectedProfile = registeredXhsProfile();
  if (!sameRegisteredPath(binding.profile, expectedProfile)) {
    return { ok: false, code: 'XHS_REGISTERED_PROFILE_MISMATCH' };
  }
  return { ok: true };
}

async function verifyConfiguredWorkerEndpoint(cdpUrl, options = {}) {
  if (typeof cdpUrl !== 'string' || !cdpUrl.trim()) {
    return { ok: false, code: 'COLLECTOR_ENDPOINT_NOT_CONFIGURED' };
  }
  let endpoint;
  try {
    endpoint = new URL(cdpUrl);
  } catch {
    return { ok: false, code: 'COLLECTOR_ENDPOINT_INVALID' };
  }
  const port = Number(endpoint.port);
  if (endpoint.protocol !== 'http:' || endpoint.hostname !== '127.0.0.1'
      || endpoint.username || endpoint.password || endpoint.pathname !== '/'
      || endpoint.search || endpoint.hash || !Number.isInteger(port)
      || port < 1 || port > 65535
      || new Set([9222, 9223, 9224, 9225, 9226, 9227, 9228]).has(port)) {
    return { ok: false,
      code: endpoint.hostname && endpoint.hostname !== '127.0.0.1'
        ? 'COLLECTOR_REMOTE_WORKER_IDENTITY_UNVERIFIED' : 'COLLECTOR_ENDPOINT_INVALID' };
  }
  try {
    const result = await verifyPreconnectedWorker(endpoint, options);
    if (!result.ok) return result;
  } catch {
    return { ok: false, code: 'COLLECTOR_WORKER_IDENTITY_UNVERIFIED' };
  }
  return { ok: true, endpoint: endpoint.origin, port };
}

async function connectRegisteredWorker(cdpUrl, options = {}) {
  const preflight = await verifyConfiguredWorkerEndpoint(cdpUrl, options);
  if (!preflight.ok) return preflight;
  const browserConnector = options.browserConnector || require('playwright').chromium;
  let browser;
  try {
    browser = await browserConnector.connectOverCDP(preflight.endpoint, { timeout: 12000 });
    const context = browser.contexts()[0];
    if (!context) throw new Error('COLLECTOR_IDENTITY_CONTEXT_UNAVAILABLE');
    const { verifyRegisteredXhsBrowserContext } = await import('./xhs_profile_guard.js');
    const identityEvidence = await verifyRegisteredXhsBrowserContext(context);
    return { ok: true, browser, context, identityEvidence, endpoint: preflight.endpoint };
  } catch (error) {
    try { if (browser) await browser.disconnect(); } catch {}
    const message = String(error?.message || '');
    const code = /^COLLECTOR_IDENTITY_[A-Z_]+$/.test(message)
      ? message : 'COLLECTOR_WORKER_CONNECTION_FAILED';
    return { ok: false, code };
  }
}

async function collect(options) {
  const { keyword, output, maxDetails, maxScroll } = options;
  const browserConnector = options.browserConnector || require('playwright').chromium;
  const collectionHost = (process.env.XHS_COLLECTION_HOST || 'www.rednote.com').trim().toLowerCase();
  if (collectionHost !== 'www.rednote.com') {
    return { ok: false, code: 'collection_host_not_allowed',
      error: '当前生产采集仅允许香港/国际 RedNote 主机 www.rednote.com', notes: [] };
  }
  const collectionOrigin = `https://${collectionHost}`;
  const cdpUrl = process.env.XHS_CDP_URL || '';
  const allResults = [];
  let verificationRequired = false;
  let ipBlocked = false;

  console.log(`[rednote] 关键词: ${keyword}`);
  console.log('[rednote] CDP endpoint configured');
  console.log(`[rednote] 最大详情数: ${maxDetails}, 滚动次数: ${maxScroll}`);

  // 1. 连接 CDP
  // Connect only after the SYSTEM-owned process/profile binding is verified.
  const connected = await connectRegisteredWorker(cdpUrl, {
    ...options, browserConnector,
  });
  if (!connected.ok) {
    console.error('[rednote] 受控会话不可用:', connected.code);
    return { ok: false, code: connected.code, error: connected.code,
      identity_verified: false, notes: [], summary: { identity_verified: false } };
  }
  const { browser, context, identityEvidence } = connected;
  let page;
  try {
    // v5.9.0 始终新建干净标签页采集，避免复用 MSN/扩展后台页导致 goto 卡死；结束时关闭
    const existing = context.pages().find(p => p.url().includes(`${collectionHost}/search_result`));
    page = existing || await context.newPage();
    console.log('[rednote] CDP 连接成功, 采集页面:', page.url().slice(0, 80));
  } catch (e) {
    console.error('[rednote] CDP 连接失败:', e.message);
    return { ok: false, error: 'CDP连接失败: ' + e.message, notes: [] };
  }

  // 2. 搜索
  console.log('\n[rednote] === 步骤1: 搜索 ===');
  const searchUrl = `${collectionOrigin}/search_result?keyword=${encodeURIComponent(keyword)}&source=web_explore_feed`;
  
  try {
    await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  } catch (e) {
    console.error('[rednote] 搜索页面goto超时(尝试继续):', e.message);
  }
  // v5.9.0 主动等待笔记卡片出现，而非固定睡眠；最多等18秒
  try {
    await page.waitForSelector('section.note-item', { timeout: 18000 });
    console.log('[rednote] 笔记列表已出现');
  } catch (e) {
    console.error('[rednote] 等待笔记列表超时，继续尝试提取');
  }
  await page.waitForTimeout(3000);

  // 检查是否被风控
  const bodyText = await page.locator('body').innerText().catch(() => '');
  if (bodyText.includes('IP存在风险') || bodyText.includes('错误码300012') || bodyText.includes('安全限制')) {
    ipBlocked = true;
    console.error('[rednote] ⚠️ IP 被风控拦截');
    return { ok: false, error: 'IP被风控拦截(错误码300012)', ip_blocked: true, notes: [] };
  }
  if (bodyText.includes('验证码') || bodyText.includes('安全验证') || bodyText.includes('请通过验证')) {
    verificationRequired = true;
    console.error('[rednote] ⚠️ 需要验证码');
    return { ok: false, error: '需要验证码', verification_required: true, notes: [] };
  }

  // v5.9.0 页面未加载成功归因：URL停留在about:blank或正文为空，多为goto被中止/临时风控，而非真的0条
  const curUrl = page.url();
  if (curUrl.startsWith('about:blank') || bodyText.replace(/\s/g, '').length < 20) {
    console.error('[rednote] ⚠️ 搜索页未加载成功 url=', curUrl.slice(0, 70), ' bodyLen=', bodyText.length);
    return { ok: false, error: '搜索页加载失败(可能临时风控或网络中断)，请冷却后重试', load_failed: true, notes: [] };
  }

  // 3. 滚动加载更多
  console.log('[rednote] 滚动加载...');
  for (let i = 0; i < maxScroll; i++) {
    await page.mouse.wheel(0, 2000);
    await page.waitForTimeout(2000);
  }

  // 4. 提取笔记列表
  console.log('\n[rednote] === 步骤2: 提取笔记列表 ===');
  const rawNotes = await page.evaluate((origin) => {
    const results = [];
    document.querySelectorAll('section.note-item').forEach(item => {
      const coverLink = item.querySelector('a.cover') || item.querySelector('a[href*="/search_result/"]');
      const href = coverLink ? coverLink.getAttribute('href') : '';
      const idMatch = href.match(/\/search_result\/([^/?]+)/);
      const noteId = idMatch ? idMatch[1] : '';
      const tokenMatch = href.match(/xsec_token=([^&]+)/);
      const xsecToken = tokenMatch ? decodeURIComponent(tokenMatch[1]) : '';

      const titleEl = item.querySelector('a.title span') || item.querySelector('.title');
      const title = titleEl ? (titleEl.innerText || '').trim() : '';
      const authorEl = item.querySelector('a.author .name') || item.querySelector('.author .name');
      const author = authorEl ? (authorEl.innerText || '').trim() : '';
      const timeEl = item.querySelector('a.author .time') || item.querySelector('.time');
      const time = timeEl ? (timeEl.innerText || '').trim() : '';
      const likeEl = item.querySelector('span.like-wrapper .count');
      const likes = likeEl ? (likeEl.innerText || '').trim() : '';
      const coverImg = item.querySelector('a.cover img');
      const cover = coverImg ? coverImg.getAttribute('src') : '';

      if (noteId) {
        results.push({
          note_id: noteId,
          xsec_token: xsecToken,
          title,
          author,
          publish_time_raw: time,
          likes_raw: likes,
          cover,
          url: origin + (href.startsWith('/') ? href : '/' + href)
        });
      }
    });
    return results;
  }, collectionOrigin);

  // 在 Node.js 端做标准化
  const notes = rawNotes.map(normalizeSearchNote);

  console.log(`[rednote] 发现 ${notes.length} 条笔记`);
  notes.slice(0, 5).forEach((n, i) => {
    console.log(`  ${i+1}. ${n.title.slice(0, 40)} | ${n.author} | ${n.publish_time} | 赞:${n.likes}`);
  });

  // 5. 详情页采集
  console.log(`\n[rednote] === 步骤3: 详情页采集 (最多${maxDetails}条) ===`);
  const actualMax = Math.min(maxDetails, notes.length);

  for (let i = 0; i < actualMax; i++) {
    const note = notes[i];
    console.log(`\n[rednote] --- 详情 ${i+1}/${actualMax}: ${note.title.slice(0, 30)} ---`);

    try {
      await page.goto(note.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      // v5.9.0 主动等正文/标题出现（兼容图文与视频笔记懒加载），最多10秒，最少3秒
      try { await page.waitForSelector('#detail-desc, #detail-title, .note-content .desc', { timeout: 10000 }); } catch (e) {}
      await page.waitForTimeout(3000);

      const detail = await page.evaluate(() => {
        const result = {};
        // 标题
        const titleEl = document.querySelector('#detail-title, .note-content .title, h1');
        result.title = titleEl ? (titleEl.innerText || '').trim() : '';
        // 正文
        const descEl = document.querySelector('#detail-desc, .note-content .desc, .note-text, .desc');
        result.desc = descEl ? (descEl.innerText || '').trim() : '';
        // 作者
        const authorEl = document.querySelector('.author-container .name, .author .name, .username');
        result.author = authorEl ? (authorEl.innerText || '').trim() : '';
        // 发布时间
        const timeEl = document.querySelector('.author-container .time, .publish-time, .date, .time');
        result.publish_time_raw = timeEl ? (timeEl.innerText || '').trim() : '';

        // 评论列表
        const commentItems = document.querySelectorAll('.comment-item');
        result.comment_list = Array.from(commentItems).map(c => {
          const userEl = c.querySelector('.name, .author a');
          const contentEl = c.querySelector('.content, .comment-content, .right > div:nth-child(2)');
          const timeEl = c.querySelector('.time, .date');
          const likeEl = c.querySelector('.like .count');
          return {
            user: userEl ? (userEl.innerText || '').trim() : '',
            content: contentEl ? (contentEl.innerText || '').trim() : '',
            time: timeEl ? (timeEl.innerText || '').trim() : '',
            likes_raw: likeEl ? (likeEl.innerText || '').trim() : ''
          };
        });
        result.loaded_comment_count = commentItems.length;

        return result;
      });

      // 在 Node.js 端处理评论 likes 和字段映射
      detail.comment_list.forEach((c, idx) => {
        c.likes = parseCount(c.likes_raw);
        // 兼容数据库字段
        c.comment_id = `${note.note_id}_c${idx}`;
        c.author_nickname = c.user;
        c.publish_time = c.time;
        c.author_id = '';
        c.parent_id = '';
        c.raw_data = { ...c };
      });

      const { likes, collects } = detailEngagementFields(note.likes);
      const commentFields = detailCommentFields(true, detail);

      // 数据质量评分
      let qualityScore = 0;
      if (detail.title) qualityScore += 15;
      if (detail.desc && detail.desc.length > 20) qualityScore += 25;
      if (detail.author) qualityScore += 10;
      if (detail.publish_time_raw) qualityScore += 15;
      if (likes !== null && likes > 0) qualityScore += 10;
      if (detail.loaded_comment_count > 0) qualityScore += 15;
      if (collects !== null && collects > 0) qualityScore += 10;
      const qualityStatus = qualityScore >= 80 ? 'complete' : (qualityScore >= 50 ? 'partial' : 'poor');

      const detailSourceTime = sourceTimeFields(detail.publish_time_raw);
      const detailSourceFields = {
        detail_source_display_time: detailSourceTime.source_display_time,
        detail_source_published_at: detailSourceTime.source_published_at,
        detail_source_updated_at: detailSourceTime.source_updated_at,
        detail_source_time_kind: detailSourceTime.source_time_kind,
        detail_source_publication_precision: detailSourceTime.source_publication_precision
      };

      // 主体过滤
      const fullText = (detail.title + ' ' + detail.desc + ' ' + note.title + ' ' + note.author).toLowerCase();
      const subjectHit = fullText.includes('太古汇') || fullText.includes('taikoo') || fullText.includes('广州太古汇');

      const record = {
        ...note,
        detail_title: detail.title,
        desc: detail.desc,
        detail_author: detail.author,
        detail_publish_time_raw: detail.publish_time_raw,
        ...detailSourceFields,
        detail_publish_time: normalizePublishTime(detail.publish_time_raw),
        likes,
        collects,
        ...commentFields,
        comment_list: detail.comment_list,
        quality_score: qualityScore,
        quality_status: qualityStatus,
        subject_hit: subjectHit,
        detail_fetched: true,
        detail_fetched_at: new Date().toISOString(),
        collector_version: 'rednote-v1.0-cdp',
        // === 兼容旧格式字段（供 persist_live 使用）===
        data_quality: { status: qualityStatus, score: qualityScore },
        comments_data: detail.comment_list,
        comments_collected: detail.loaded_comment_count,
        fetched_at: new Date().toISOString(),
        detail_status: 'success',
        publish_datetime: normalizePublishTime(detail.publish_time_raw) || note.publish_time,
        captured_at: new Date().toISOString(),
        detail_fetched_at: new Date().toISOString(),
        comments_fetched_at: new Date().toISOString(),
        data_quality_status: qualityStatus,
        data_quality_score: qualityScore
      };
      allResults.push(record);

      console.log(`  正文: ${(detail.desc || '').slice(0, 50)}...`);
      console.log(`  互动: 赞=${likes} 藏=${collects} 评=${commentFields.comments}`);
      console.log(`  帖子评论总数: ${commentFields.comment_count} | 已采集评论: ${detail.loaded_comment_count}`);
      console.log(`  质量: ${qualityStatus} (${qualityScore}分) | 主体命中: ${subjectHit}`);

    } catch (e) {
      console.log(`  详情失败: ${e.message}`);
      allResults.push({
        ...note,
        detail_fetched: false,
        ...detailCommentFields(false),
        error: e.message,
        detail_status: 'failed',
        data_quality: { status: 'poor', score: 20 },
        data_quality_status: 'poor',
        data_quality_score: 20,
        comments_data: [],
        comment_list: [],
        quality_status: 'poor',
        quality_score: 20,
        subject_hit: false,
        fetched_at: new Date().toISOString(),
        captured_at: new Date().toISOString(),
        collector_version: 'rednote-v1.0-cdp'
      });
    }
  }

  // 6. 汇总
  const summary = {
    keyword,
    discovered: notes.length,
    detail_success: allResults.filter(r => r.detail_fetched).length,
    detail_failed: allResults.filter(r => !r.detail_fetched).length,
    quality_complete: allResults.filter(r => r.quality_status === 'complete').length,
    quality_partial: allResults.filter(r => r.quality_status === 'partial').length,
    quality_poor: allResults.filter(r => r.quality_status === 'poor').length,
    subject_hit: allResults.filter(r => r.subject_hit).length,
    subject_reject: allResults.filter(r => !r.subject_hit).length,
    verification_required: verificationRequired,
    ip_blocked: ipBlocked
  };

  console.log('\n[rednote] === 采集汇总 ===');
  console.log(JSON.stringify(summary, null, 2));

  const outputData = {
    ok: !verificationRequired && !ipBlocked && allResults.length > 0,
    identity_verified: true,
    identity_evidence: identityEvidence,
    summary,
    notes: allResults,
    fetched_at: new Date().toISOString(),
    collector: 'rednote_collector.js v1.0',
    cdp_endpoint_configured: true
  };

  // 保存输出
  if (output) {
    const outDir = path.dirname(output);
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(output, JSON.stringify(outputData, null, 2), 'utf-8');
    console.log(`\n[rednote] 结果已保存到: ${output}`);
  }

  // v5.9.0 关闭本次采集标签页（保留 CDP browser，由 Python 端统一管理启停）
  try { if (page && !(await page.isClosed())) await page.close(); } catch (e) {}
  // 注意：CDP模式下不要关闭 browser！
  return outputData;
}

// ========== 入口 ==========

if (require.main === module) {
  const options = parseArgs();
  collect(options).then(result => {
    // 总是输出 JSON 到 stdout 供 Python 端解析
    console.log('\n---RESULT_JSON---');
    console.log(JSON.stringify(result));
    process.exit(result.ok ? 0 : 1);
  }).catch(e => {
    console.error('[rednote] 采集异常:', e);
    process.exit(2);
  });
}

module.exports = {
  collect, parseCount, normalizePublishTime, detailCommentFields,
  detailEngagementFields, normalizeSearchNote, sourceTimeFields,
  resolveRegisteredWorkerFromSystemOwner, verifyConfiguredWorkerEndpoint,
  connectRegisteredWorker
};
