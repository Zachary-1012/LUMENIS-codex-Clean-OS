/**
 * rednote_collector.js — rednote 真实数据采集引擎
 * 
 * 基于 CDP 连接已登录的 Edge 浏览器，从 rednote.com 采集真实数据。
 * 采集链路：搜索 → 笔记列表 → 详情页 → 正文/互动/评论 → 数据质量 → 主体过滤
 * 
 * 用法：
 *   node rednote_collector.js --keyword "广州太古汇" --output data/result.json --max-details 10 --max-scroll 3
 * 
 * 环境变量：
 *   XHS_CDP_URL — 香港/国际 CDP 调试地址，如 http://127.0.0.1:9223（必须）
 *   XHS_COLLECTION_HOST — 固定为 www.rednote.com
 * 
 * 注意：CDP 模式下不要调用 browser.close()，否则会关闭整个 Edge 浏览器。
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

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

function parseCount(str) {
  if (!str) return 0;
  str = String(str).trim();
  if (str.includes('万')) return Math.round(parseFloat(str) * 10000);
  const n = parseInt(str.replace(/[^0-9]/g, ''));
  return isNaN(n) ? 0 : n;
}

function normalizePublishTime(raw) {
  if (!raw) return '';
  raw = raw.trim();
  // "2025-09-27" → 保持
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.match(/^\d{4}-\d{2}-\d{2}/)[0];
  // "08-01" → 补当前年
  if (/^\d{2}-\d{2}/.test(raw)) {
    const year = new Date().getFullYear();
    return year + '-' + raw.match(/^\d{2}-\d{2}/)[0];
  }
  // "3天前" / "2天前" → 计算日期
  const daysMatch = raw.match(/(\d+)天前/);
  if (daysMatch) {
    const d = new Date();
    d.setDate(d.getDate() - parseInt(daysMatch[1]));
    return d.toISOString().slice(0, 10);
  }
  // "今天" / "刚刚"
  if (raw.includes('今天') || raw.includes('刚刚')) {
    return new Date().toISOString().slice(0, 10);
  }
  return raw;
}

// ========== 主采集逻辑 ==========

async function collect(options) {
  const { keyword, output, maxDetails, maxScroll } = options;
  const collectionHost = (process.env.XHS_COLLECTION_HOST || 'www.rednote.com').trim().toLowerCase();
  if (collectionHost !== 'www.rednote.com') {
    return { ok: false, code: 'collection_host_not_allowed',
      error: '当前生产采集仅允许香港/国际 RedNote 主机 www.rednote.com', notes: [] };
  }
  const collectionOrigin = `https://${collectionHost}`;
  const cdpUrl = process.env.XHS_CDP_URL || '';
  if (!cdpUrl) throw new Error('COLLECTOR_ENDPOINT_NOT_CONFIGURED');
  const allResults = [];
  let verificationRequired = false;
  let ipBlocked = false;

  console.log(`[rednote] 关键词: ${keyword}`);
  console.log(`[rednote] CDP: ${cdpUrl}`);
  console.log(`[rednote] 最大详情数: ${maxDetails}, 滚动次数: ${maxScroll}`);

  // 1. 连接 CDP
  let browser, context, page;
  try {
    browser = await chromium.connectOverCDP(cdpUrl);
    context = browser.contexts()[0];
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
      const likeEl = item.querySelector('span.like-wrapper .count') || item.querySelector('.count');
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
  const notes = rawNotes.map(n => ({
    ...n,
    publish_time: normalizePublishTime(n.publish_time_raw),
    likes: parseCount(n.likes_raw)
  }));

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

        // 所有 count 值（用于提取赞/藏/评）
        const allCounts = document.querySelectorAll('.count');
        result.all_counts = Array.from(allCounts).map(c => (c.innerText || '').trim()).filter(t => t);

        // 评论列表
        const commentItems = document.querySelectorAll('.comment-item');
        result.comment_list = Array.from(commentItems).map(c => {
          const userEl = c.querySelector('.name, .author a');
          const contentEl = c.querySelector('.content, .comment-content, .right > div:nth-child(2)');
          const timeEl = c.querySelector('.time, .date');
          const likeEl = c.querySelector('.like .count, .count');
          return {
            user: userEl ? (userEl.innerText || '').trim() : '',
            content: contentEl ? (contentEl.innerText || '').trim() : '',
            time: timeEl ? (timeEl.innerText || '').trim() : '',
            likes_raw: likeEl ? (likeEl.innerText || '').trim() : ''
          };
        });
        result.comment_count = commentItems.length;

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

      // 从 all_counts 最后三个值提取 赞/藏/评
      const counts = detail.all_counts.filter(c => /^\d+$/.test(c)).map(Number);
      const likes = counts.length >= 3 ? counts[counts.length - 3] : (counts[counts.length - 1] || note.likes);
      const collects = counts.length >= 2 ? counts[counts.length - 2] : 0;
      const comments = counts.length >= 1 ? counts[counts.length - 1] : 0;

      // 数据质量评分
      let qualityScore = 0;
      if (detail.title) qualityScore += 15;
      if (detail.desc && detail.desc.length > 20) qualityScore += 25;
      if (detail.author) qualityScore += 10;
      if (detail.publish_time_raw) qualityScore += 15;
      if (likes > 0) qualityScore += 10;
      if (detail.comment_count > 0) qualityScore += 15;
      if (collects > 0) qualityScore += 10;
      const qualityStatus = qualityScore >= 80 ? 'complete' : (qualityScore >= 50 ? 'partial' : 'poor');

      // 主体过滤
      const fullText = (detail.title + ' ' + detail.desc + ' ' + note.title + ' ' + note.author).toLowerCase();
      const subjectHit = fullText.includes('太古汇') || fullText.includes('taikoo') || fullText.includes('广州太古汇');

      const record = {
        ...note,
        detail_title: detail.title,
        desc: detail.desc,
        detail_author: detail.author,
        detail_publish_time_raw: detail.publish_time_raw,
        detail_publish_time: normalizePublishTime(detail.publish_time_raw),
        likes,
        collects,
        comments,
        comment_count: detail.comment_count,
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
        comments_collected: detail.comment_count,
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
      console.log(`  互动: 赞=${likes} 藏=${collects} 评=${comments}`);
      console.log(`  评论数: ${detail.comment_count}`);
      console.log(`  质量: ${qualityStatus} (${qualityScore}分) | 主体命中: ${subjectHit}`);

    } catch (e) {
      console.log(`  详情失败: ${e.message}`);
      allResults.push({
        ...note,
        detail_fetched: false,
        error: e.message,
        detail_status: 'failed',
        data_quality: { status: 'poor', score: 20 },
        data_quality_status: 'poor',
        data_quality_score: 20,
        comments_data: [],
        comments_collected: 0,
        comment_list: [],
        comment_count: 0,
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
    summary,
    notes: allResults,
    fetched_at: new Date().toISOString(),
    collector: 'rednote_collector.js v1.0',
    cdp_url: cdpUrl
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

module.exports = { collect, parseCount, normalizePublishTime };
