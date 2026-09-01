/*!
 * Z-Brand Core · Global Auth Recovery & Collection Health (self-contained)
 * --------------------------------------------------------------------------
 * 任何 v4 页面引入一次即可获得：全局采集健康小点 + 系统内统一 Auth Recovery Modal。
 *  - 不跳页：登录失效 / 人机验证 / IP 风控一律在当前页弹全局 Modal；
 *  - 三类分清：A 登录失效(合法登录/扫码) · B 人机验证(人工) · C IP风控(只冷却，不伪装扫码可解)；
 *  - 平台隔离：小红书异常不影响其他平台；绝不把风控/验证/失败显示成“0 条舆情”；
 *  - 若页面已自带 #authMask 与 window.openAuthModal（如 console），则委托既有实现，不重复注入。
 * 数据：GET /api/platform-health；恢复动作：/v4/adapters/recovery/start|check|cancel。
 * 纯原生 JS，无外部依赖；不包含任何凭证。
 */
(function () {
  'use strict';
  if (window.__ZAuthLoaded) return;
  window.__ZAuthLoaded = true;

  var HEALTH_URL = '/api/platform-health';
  var POLL_MS = 20000;
  var STATE_CN = {
    SUCCESS: '采集正常', NO_NEW_DATA: '本批无新内容', RISK_WARNING: '轻度风险·已降频',
    NEED_VERIFY: '需要人机验证', BLOCKED: '平台风控拦截', SESSION_EXPIRED: '登录态失效',
    COLLECT_ERROR: '采集出错', COOLING_DOWN: '熔断冷却中', NETWORK_ERROR: '网络异常',
    IDLE: '待命中', DISABLED: '未启用'
  };
  var TRIAGE_CN = { A_AUTH: '登录失效', B_VERIFY: '人机验证', C_RISK: '风控熔断', NET: '网络异常', OK: '正常', IDLE: '待命', DISABLED: '未启用' };
  var snoozed = {};
  var lastHealth = null;
  var pollTimer = null;

  // ---------- 样式（苹果风，页面缺变量时用兜底值） ----------
  var css = '' +
    ':root{--za-accent:#0a84ff;--za-ok:#34c759;--za-warn:#ff9f0a;--za-bad:#ff3b30;--za-ink:#1d1d1f;--za-ink2:#86868b;--za-line:rgba(0,0,0,.08);--za-panel:#fff}' +
    '#zaFab{position:fixed;right:18px;bottom:18px;z-index:130;display:flex;align-items:center;gap:8px;padding:9px 13px;border-radius:999px;border:1px solid var(--za-line);' +
    'background:rgba(255,255,255,.82);backdrop-filter:blur(18px);box-shadow:0 6px 22px rgba(0,0,0,.12);cursor:pointer;font-size:12.5px;font-weight:600;color:var(--za-ink);user-select:none}' +
    '#zaFab .zd{width:9px;height:9px;border-radius:50%;background:var(--za-ok);flex:0 0 9px}' +
    '#zaFab.warn .zd{background:var(--za-warn)}#zaFab.bad .zd{background:var(--za-bad);animation:zaPulse 1.4s infinite}' +
    '#zaFab .zn{min-width:17px;height:17px;padding:0 5px;border-radius:9px;background:var(--za-bad);color:#fff;display:none;place-items:center;font-size:10.5px}' +
    '@keyframes zaPulse{0%{box-shadow:0 0 0 0 rgba(255,59,48,.45)}70%{box-shadow:0 0 0 9px rgba(255,59,48,0)}100%{box-shadow:0 0 0 0 rgba(255,59,48,0)}}' +
    '#zaPanel{position:fixed;right:18px;bottom:64px;z-index:131;width:min(340px,92vw);max-height:60vh;overflow:auto;background:var(--za-panel);border:1px solid var(--za-line);' +
    'border-radius:18px;box-shadow:0 12px 40px rgba(0,0,0,.18);padding:10px;display:none}' +
    '#zaPanel.show{display:block}' +
    '.zaRow{display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:12px}' +
    '.zaRow:hover{background:#f5f5f7}.zaRow .zd{width:8px;height:8px;border-radius:50%;flex:0 0 8px}' +
    '.zaRow .zm{flex:1;min-width:0}.zaRow .mt{font-size:12.5px;font-weight:600}.zaRow .ms{font-size:11px;color:var(--za-ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.zaRow button{border:none;background:var(--za-accent);color:#fff;border-radius:8px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer}' +
    '.zaMask{position:fixed;inset:0;background:rgba(0,0,0,.32);backdrop-filter:blur(6px);z-index:140;display:none;align-items:center;justify-content:center;padding:18px}' +
    '.zaMask.show{display:flex}' +
    '.zaModal{width:min(440px,94vw);max-height:90vh;overflow:auto;background:var(--za-panel);border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,.3);padding:20px}' +
    '.zaH{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}.zaH b{font-size:16px}.zaH .sub{font-size:11.5px;color:var(--za-ink2);margin-top:2px}' +
    '.zaX{border:none;background:transparent;font-size:22px;color:var(--za-ink2);cursor:pointer;line-height:1}' +
    '.zaRows{display:grid;grid-template-columns:auto 1fr;gap:7px 14px;font-size:12.5px;margin-bottom:12px}.zaRows span{color:var(--za-ink2)}.zaRows b{text-align:right;font-weight:600}' +
    '.zaKind{font-size:12px;line-height:1.55;border-radius:12px;padding:10px 12px;margin-bottom:12px;background:#f5f5f7}' +
    '.zaKind.A{background:rgba(10,132,255,.1);color:#0a5fc4}.zaKind.B{background:rgba(255,159,10,.14);color:#a86800}.zaKind.C{background:rgba(255,59,48,.1);color:#c4271e}' +
    '.zaSteps{display:flex;gap:7px;margin-bottom:12px}.zaStep{flex:1;text-align:center;font-size:11px;padding:7px 4px;border-radius:10px;background:#f0f0f4;color:var(--za-ink2)}' +
    '.zaStep.active{background:rgba(10,132,255,.14);color:var(--za-accent);font-weight:600}.zaStep.done{background:rgba(52,199,89,.16);color:#1c8c3f;font-weight:600}' +
    '.zaPause{font-size:11.5px;color:var(--za-ink2);line-height:1.5;background:#fafafa;border-radius:10px;padding:9px 11px;margin-bottom:12px}' +
    '.zaFoot{display:flex;gap:9px;justify-content:flex-end}.zaFoot button{border-radius:11px;padding:9px 15px;font-size:12.5px;font-weight:600;cursor:pointer;border:1px solid var(--za-line)}' +
    '.zaFoot .ghost{background:transparent;color:var(--za-ink)}.zaFoot .primary{background:var(--za-accent);color:#fff;border-color:var(--za-accent)}' +
    '@media(max-width:640px){.zaMask{align-items:flex-end;padding:0}.zaModal{width:100%;max-height:92vh;border-radius:20px 20px 0 0}#zaFab{right:12px;bottom:12px}#zaPanel{right:12px;bottom:58px}}';
  var styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  function colorOf(status, triage) {
    if (triage === 'OK' || status === 'SUCCESS' || status === 'NO_NEW_DATA') return 'var(--za-ok)';
    if (triage === 'A_AUTH' || triage === 'B_VERIFY' || status === 'SESSION_EXPIRED' || status === 'NEED_VERIFY') return 'var(--za-bad)';
    if (triage === 'C_RISK' || status === 'BLOCKED' || status === 'COOLING_DOWN') return 'var(--za-warn)';
    if (triage === 'NET' || status === 'NETWORK_ERROR' || status === 'COLLECT_ERROR') return 'var(--za-warn)';
    return '#c7c7cc';
  }
  var SOFT_INCIDENT = { RISK_WARNING: 1, COLLECT_ERROR: 1, NETWORK_ERROR: 1 };
  function needsAttention(p) { return !!p && p.enabled && (p.needs_human || p.stop_request || SOFT_INCIDENT[p.status]); }

  // ---------- 悬浮健康小点 ----------
  var fab = document.createElement('div');
  fab.id = 'zaFab';
  fab.innerHTML = '<span class="zd"></span><span class="zt">采集健康</span><span class="zn">0</span>';
  fab.onclick = function () { panel.classList.toggle('show'); renderPanel(); };
  var panel = document.createElement('div');
  panel.id = 'zaPanel';
  document.addEventListener('DOMContentLoaded', mount);
  if (document.body) mount();
  function mount() { if (!fab.parentNode) document.body.appendChild(fab); if (!panel.parentNode) document.body.appendChild(panel); }

  function renderFab(h) {
    var bad = h.platforms.filter(needsAttention);
    var cls = bad.some(function (p) { return p.needs_human; }) ? 'bad' : (bad.length ? 'warn' : '');
    fab.className = cls;
    var n = fab.querySelector('.zn');
    n.textContent = bad.length; n.style.display = bad.length ? 'grid' : 'none';
    fab.querySelector('.zt').textContent = bad.length ? ('需处理 ' + bad.length) : '采集健康';
  }
  function renderPanel() {
    if (!lastHealth) { panel.innerHTML = '<div class="zaRow"><div class="zm"><div class="ms">读取健康状态中…</div></div></div>'; return; }
    panel.innerHTML = lastHealth.platforms.map(function (p) {
      var c = colorOf(p.status, p.triage);
      var stTxt = STATE_CN[p.status] || p.status;
      var act = needsAttention(p) ? '<button data-p="' + p.platform + '">处理</button>' : '';
      return '<div class="zaRow"><span class="zd" style="background:' + c + '"></span>' +
        '<div class="zm"><div class="mt">' + p.name + ' · ' + (TRIAGE_CN[p.triage] || p.triage) + '</div>' +
        '<div class="ms">' + stTxt + (p.next_run_at ? ('｜下次 ' + p.next_run_at.slice(11, 16)) : '') + '</div></div>' + act + '</div>';
    }).join('');
    Array.prototype.forEach.call(panel.querySelectorAll('button[data-p]'), function (b) {
      b.onclick = function () {
        var p = lastHealth.platforms.filter(function (x) { return x.platform === b.dataset.p; })[0];
        panel.classList.remove('show'); openModal(p);
      };
    });
  }

  // ---------- 统一 Auth Modal ----------
  var mask = null, stepTimer = null;
  function ensureModal() {
    if (mask) return mask;
    mask = document.createElement('div');
    mask.className = 'zaMask';
    mask.innerHTML = '<div class="zaModal" role="dialog" aria-modal="true">' +
      '<div class="zaH"><div><b>账号恢复中心</b><div class="sub">统一登录态恢复 · 不离开当前页面</div></div>' +
      '<button class="zaX" aria-label="关闭">×</button></div>' +
      '<div class="zaRows"><span>平台</span><b data-k="platform">–</b><span>当前状态</span><b data-k="state">–</b>' +
      '<span>原因</span><b data-k="reason">–</b><span>任务状态</span><b>已自动暂停，恢复后续采</b></div>' +
      '<div class="zaKind" data-k="kind"></div>' +
      '<div class="zaSteps"><div class="zaStep" data-n="1">打开登录/验证</div><div class="zaStep" data-n="2">扫码 / 验证</div><div class="zaStep" data-n="3">恢复续采</div></div>' +
      '<div class="zaPause">系统不会把验证 / 风控 / 登录失败显示成“0 条舆情”。完成合法验证后自动健康检查并续采；未完成则保持暂停 / 冷却。</div>' +
      '<div class="zaFoot"><button class="ghost" data-a="later">稍后处理</button><button class="primary" data-a="recheck">我已完成验证，重新检测</button></div></div>';
    document.body.appendChild(mask);
    mask.querySelector('.zaX').onclick = closeModal;
    mask.querySelector('[data-a=later]').onclick = later;
    mask.querySelector('[data-a=recheck]').onclick = recheck;
    mask.onclick = function (e) { if (e.target === mask) closeModal(); };
    return mask;
  }
  function setStep(n) {
    Array.prototype.forEach.call(ensureModal().querySelectorAll('.zaStep'), function (el) {
      var i = +el.dataset.n;
      el.className = 'zaStep' + (i <= n ? ' done' : (i === n + 1 ? ' active' : ''));
    });
  }
  function field(k, v) { ensureModal().querySelector('[data-k="' + k + '"]').textContent = v; }
  function openModal(p) {
    if (!p) return;
    // 若页面已自带 openAuthModal（console），委托既有实现，避免重复弹窗
    if (typeof window.openAuthModal === 'function' && document.getElementById('authMask')) {
      return window.openAuthModal(p.platform, mapLegacyState(p), p.message || '');
    }
    ensureModal();
    mask.classList.add('show');
    mask.dataset.platform = p.platform;
    field('platform', p.name + '（' + p.platform + '）');
    field('state', STATE_CN[p.status] || p.status);
    field('reason', p.message || '采集时检测到需要登录或人工验证');
    var kind = mask.querySelector('.zaKind');
    setStep(1);
    if (p.triage === 'A_AUTH') {
      kind.className = 'zaKind A';
      kind.textContent = 'A 类 · 登录失效：请在采集浏览器（持久 Profile）完成合法登录/扫码，登录一次可长期复用，系统不保存账号密码。';
    } else if (p.triage === 'B_VERIFY') {
      kind.className = 'zaKind B';
      kind.textContent = 'B 类 · 人机/安全验证：这不是重新登录。请在采集浏览器完成滑块/安全验证后点“重新检测”，系统不会绕过验证。';
    } else if (p.triage === 'C_RISK') {
      kind.className = 'zaKind C';
      kind.textContent = 'C 类 · IP/平台风控（如 300012）：扫码无法解决，系统已自动降频/熔断冷却，不硬刚、不连续重试。';
    } else {
      kind.className = 'zaKind';
      kind.textContent = '网络异常：按退避策略重试，恢复后先小流量试运行。';
    }
    api('/v4/adapters/recovery/start', { platform: p.platform, source_state: p.status, detail: p.message || '' })
      .then(function (d) { if (d && d.session && d.session.state) field('state', AUTH_SESSION_CN[d.session.state] || d.session.state); })
      .catch(function () {});
  }
  var AUTH_SESSION_CN = { EXPIRED: '登录已失效', QR_DISPLAYED: '二维码已展示', WAITING_SCAN: '等待扫码/验证', SCANNED: '已扫码待确认', CONFIRMING: '确认中', RECOVERED: '已恢复', HEALTH_CHECK: '健康检查中', PLATFORM_BLOCKED: '风控冷却中' };
  function mapLegacyState(p) {
    return { SESSION_EXPIRED: 'AUTH_FAILED', NEED_VERIFY: 'CAPTCHA', BLOCKED: 'BLOCKED', COOLING_DOWN: 'BLOCKED', NETWORK_ERROR: 'NETWORK_ERROR' }[p.status] || p.status;
  }
  function closeModal() { if (mask) mask.classList.remove('show'); if (stepTimer) { clearInterval(stepTimer); stepTimer = null; } }
  function later() {
    var p = mask && mask.dataset.platform;
    if (p) { snoozed[p] = true; api('/v4/adapters/recovery/cancel', { platform: p }).catch(function () {}); }
    closeModal();
  }
  function recheck() {
    var p = mask.dataset.platform;
    setStep(2);
    api('/v4/adapters/recovery/check', { platform: p }).then(function (d) {
      if (d && d.recovered) { setStep(3); field('state', '已恢复 · 自动续采'); setTimeout(closeModal, 1500); poll(); }
      else setStep(2);
    }).catch(function () { setStep(2); });
  }

  // ---------- 轮询 ----------
  function _getBasicAuthHeader() {
    // 共享主站 app.js 已写入的基础认证，避免在 Basic Auth 页面 401。
    // 优先级：1) window.__Z_AUTH 原生 Auth Header  2) window.__AUTH_B64 手动设置的 btoa  3) localStorage Z_AUTH_B64
    try {
      if (typeof window.__Z_AUTH === 'string' && window.__Z_AUTH) return window.__Z_AUTH;
      if (typeof window.__AUTH_B64 === 'string' && window.__AUTH_B64) return 'Basic ' + window.__AUTH_B64;
      var ls = (typeof localStorage !== 'undefined') ? localStorage.getItem('Z_AUTH_B64') : '';
      if (ls) return 'Basic ' + ls;
    } catch (e) {}
    return '';
  }
  function api(url, body) {
    var opt = { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } };
    var authHdr = _getBasicAuthHeader();
    if (authHdr) opt.headers['Authorization'] = authHdr;
    if (body) { opt.method = 'POST'; opt.body = JSON.stringify(body); }
    return fetch(url, opt).then(function (r) {
      if (r.status === 401 || r.status === 403) return null; // 未登录页静默，不做跳转
      return r.json();
    }).catch(function () { return null; });
  }
  function poll() {
    api(HEALTH_URL).then(function (h) {
      if (!h || !h.platforms) return;
      lastHealth = h;
      mount(); renderFab(h);
      if (panel.classList.contains('show')) renderPanel();
      // 需人工处理的平台自动弹一次；稍后处理/已弹窗的不重复打扰
      h.platforms.forEach(function (p) {
        if (p.enabled && p.needs_human && !snoozed[p.platform] && (!mask || !mask.classList.contains('show'))) {
          var existing = mask && mask.dataset.platform === p.platform;
          if (!existing) openModal(p);
        }
      });
    });
  }
  function startLoop() {
    poll();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(poll, POLL_MS);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });
  }
  startLoop();
})();
