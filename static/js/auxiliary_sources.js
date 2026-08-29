/* ============================================================
 * v5.8.2 辅助数据源（微博 / B站）
 * Cookie 直连、无需扫码；不占用小红书检索次数
 * 结果写入 web_topics，反哺小红书关键词与事件发现
 * ============================================================ */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }
  // 复用全局 api()（app.js）；不存在则回退 fetch
  async function call(path, opts) {
    if (typeof window.api === 'function') return window.api(path, opts);
    const opt = Object.assign({ headers: {} }, opts || {});
    opt.headers['Content-Type'] = 'application/json';
    const r = await fetch(path, opt);
    return r.json();
  }

  function statusChip(name, loggedIn, detail) {
    const color = loggedIn ? '#1a9e54' : '#e08600';
    const bg = loggedIn ? '#e8f9ee' : '#fff4e5';
    const icon = loggedIn ? '●' : '○';
    const text = loggedIn ? `${name}：Cookie 已连接` : `${name}：未连接（请在设置导入 Cookie）`;
    return `<span style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:16px;background:${bg};color:${color};font-size:12px;font-weight:600" title="${(detail || '').replace(/"/g, '')}">${icon} ${text}</span>`;
  }

  async function refreshStatus() {
    const box = $('auxSourceStatus');
    if (!box) return;
    const platforms = [
      { name: '微博', url: '/api/weibo/login-status' },
      { name: 'B站', url: '/api/bilibili/login-status' }
    ];
    box.innerHTML = platforms.map(p => statusChip(p.name, null, '检测中…')).join('');
    const out = await Promise.all(platforms.map(async p => {
      try {
        const d = await call(p.url);
        const ok = !!(d && (d.logged_in || d.is_logged_in || d.login_status === 'logged_in'));
        const detail = d ? (d.login_method || d.nickname || d.username || '') : '';
        return statusChip(p.name, ok, [detail, d && d.expires_at].filter(Boolean).join(' · '));
      } catch (e) {
        return statusChip(p.name, false, '状态读取失败');
      }
    }));
    box.innerHTML = out.join('');
  }

  async function doCollect() {
    const btn = $('auxCollectBtn'), res = $('auxResult'), kw = $('auxKeyword');
    if (!btn) return;
    const keyword = (kw && kw.value.trim()) || '广州太古汇';
    btn.disabled = true; const old = btn.textContent; btn.textContent = '采集中…';
    res.textContent = '正在通过 Cookie 直连检索微博 / B站（约 10–30 秒）…';
    try {
      const d = await call('/api/web/collect', {
        method: 'POST',
        body: JSON.stringify({ keyword, platforms: ['weibo', 'bilibili'] })
      });
      const r = (d && d.results) || {};
      const wb = r.weibo || {}, bili = r.bilibili || {};
      const wbN = Array.isArray(wb.items) ? wb.items.length : (wb.count || 0);
      const biliN = Array.isArray(bili.videos) ? bili.videos.length : (bili.count || 0);
      res.innerHTML = `采集完成：微博 <b>${wbN}</b> 条${wb.ok ? '' : '（' + (wb.error || '失败') + '）'}，B站 <b>${biliN}</b> 条${bili.ok ? '' : '（' + (bili.error || '失败') + '）'}，已去重写入全网话题库。`;
      if (typeof window.toast === 'function') window.toast('辅助源采集完成');
    } catch (e) {
      res.textContent = '采集失败：' + (e.message || e);
    } finally {
      btn.disabled = false; btn.textContent = old;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const btn = $('auxCollectBtn');
    if (btn) btn.addEventListener('click', doCollect);
    // 切到官方动态页时刷新一次状态（轻量，不做轮询）
    refreshStatus();
    document.addEventListener('taikoo-page-change', refreshStatus);
  });
})();
