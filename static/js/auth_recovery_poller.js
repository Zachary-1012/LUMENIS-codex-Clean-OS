/* auth_recovery_poller.js — AGENTS §7.2 系统内 Auth 恢复弹窗轮询
 * ------------------------------------------------------------------
 * 设计原则（XSS 刚性防护，永不违反）:
 *   1. 所有动态 DOM = document.createElement() 构造 + node.textContent = value
 *   2. 绝对禁止 innerHTML / outerHTML / document.write / eval / new Function
 *   3. 动态链接 a.href = encodeURI(url) + 手动追加 rel="noopener noreferrer" target="_blank"
 *   4. 所有 fetch JSON 解析失败 / HTTP !200 → 静默失败 (console.warn 不抛到用户)
 *   5. 轮询间隔 10s，timeout 5s；localStorage snooze 30min 防骚扰
 *
 * 交互链路:
 *   GET /api/auth-recovery/summary → {pending_count, tasks:[{id,platform,issue_type,title,description,qr_code_url,recovery_url,expires_at,created_at}]}
 *     → pending_count > 0 && !snoozed(id)
 *     → Modal 弹出: [Header ⚠️ 需要人工验证 (平台)] [Body 任务详情 + recovery_url 外链] [Actions 我已完成验证 | 稍后处理(30min)]
 *     → 完成: POST /api/auth-recovery/tasks/{id}/complete → 刷新 4 个健康端点 → 关 modal + toast
 *     → 稍后: localStorage ar_snooze_{id}=now+1800 → 关 modal
 * ------------------------------------------------------------------ */
(function () {
  'use strict';

  var POLL_INTERVAL_MS = 10000;
  var FETCH_TIMEOUT_MS = 5000;
  var SNOOZE_MINUTES = 30;
  var SUMMARY_URL = '/api/auth-recovery/summary';
  var HEALTH_URLS = [
    '/healthz',
    '/api/health/summary',
    '/api/health/platform-health',
    '/api/collector/status'
  ];
  var SNOOZE_KEY_PREFIX = 'ar_snooze_';
  var currentActiveTaskId = null;     // 当前弹出 modal 的 task id（防重复弹同一 task）
  var modalRoot = null;               // Modal DOM 根（创建一次，后续更新 textContent）
  var toastEl = null;

  // ── 工具：XSS 安全元素构造 ──
  function h(tag, text, attrs, children) {
    var el = document.createElement(tag);
    if (text != null && text !== '') el.textContent = String(text);
    if (attrs) {
      for (var k in attrs) {
        if (!Object.prototype.hasOwnProperty.call(attrs, k)) continue;
        var v = attrs[k];
        if (k === 'class') el.className = String(v);
        else if (k === 'id') el.id = String(v);
        else if (k === 'style') el.setAttribute('style', String(v));
        else if (k === 'title') el.title = String(v);
        else if (k === 'href') {
          // 链接：强制安全属性 + encode URI
          var safe;
          try { safe = encodeURI(String(v)); } catch (e) { safe = '#'; }
          el.setAttribute('href', safe);
          el.setAttribute('target', '_blank');
          el.setAttribute('rel', 'noopener noreferrer');
        }
        else if (k === 'type') el.setAttribute('type', String(v));
        else if (k === 'disabled') { if (v) el.setAttribute('disabled', 'disabled'); }
        else el.setAttribute(k, String(v));
      }
    }
    if (children && Array.isArray(children)) {
      for (var i = 0; i < children.length; i++) {
        var child = children[i];
        if (child != null) {
          // 兼容 primitive 字符串/数字/布尔 → 自动转 TextNode（防止 appendChild(字符串) 抛 "not of type Node"）
          if (typeof child === 'string' || typeof child === 'number' || typeof child === 'boolean') {
            el.appendChild(document.createTextNode(String(child)));
          } else if (child.nodeType) {
            el.appendChild(child);
          }
          // 其他非 DOM/非 primitive 类型静默跳过（避免污染 DOM）
        }
      }
    }
    return el;
  }

  // ── 工具：带 timeout 的 fetch（避免卡住 UI）──
  // P0 Fix：自动注入全局共享 window.__Z_AUTH Basic Auth Header（auth_global.js 401 ERR_ABORTED 同根因）
  function _getSharedAuthHeader() {
    try {
      if (typeof window.__Z_AUTH === 'string' && window.__Z_AUTH) return window.__Z_AUTH;
      if (typeof window.__AUTH_B64 === 'string' && window.__AUTH_B64) return 'Basic ' + window.__AUTH_B64;
      var ls = (typeof localStorage !== 'undefined') ? localStorage.getItem('Z_AUTH_B64') : '';
      if (ls) return 'Basic ' + ls;
    } catch (e) {}
    return '';
  }
  function fetchTimeout(url, opts) {
    return new Promise(function (resolve, reject) {
      var timer = setTimeout(function () { reject(new Error('timeout ' + FETCH_TIMEOUT_MS + 'ms')); }, FETCH_TIMEOUT_MS);
      try {
        var finalOpts = opts ? Object.assign({}, opts) : {};
        finalOpts.headers = finalOpts.headers ? Object.assign({}, finalOpts.headers) : {};
        // credentials 默认 same-origin，除非调用方显式改写
        if (!('credentials' in finalOpts)) finalOpts.credentials = 'same-origin';
        // 注入共享 Basic Auth（避免 401 ERR_ABORTED；v4 bearer 会话不冲突，Authorization 头多字段浏览器允许覆盖）
        var sharedAuth = _getSharedAuthHeader();
        if (sharedAuth && !finalOpts.headers['Authorization']) {
          finalOpts.headers['Authorization'] = sharedAuth;
        }
        fetch(url, finalOpts).then(function (r) { clearTimeout(timer); resolve(r); },
          function (e) { clearTimeout(timer); reject(e); });
      } catch (e) { clearTimeout(timer); reject(e); }
    });
  }

  // ── 徽章联动: N → 0 时 hidden；>0 时显示数字 ──
  function updateBadge(pendingCount) {
    try {
      var badge = document.getElementById('ar-badge');
      var countEl = document.getElementById('ar-count');
      if (!badge || !countEl) return;
      countEl.textContent = String(pendingCount);
      if (pendingCount > 0) badge.classList.remove('hidden');
      else badge.classList.add('hidden');
    } catch (e) { /* 徽章缺失静默 */ }
  }

  // ── Snooze: localStorage 30min 同一 task 不重复弹 ──
  function isSnoozed(taskId) {
    try {
      var k = SNOOZE_KEY_PREFIX + taskId;
      var until = parseInt(localStorage.getItem(k) || '0', 10);
      return until > Date.now();
    } catch (e) { return false; }
  }
  function snooze(taskId) {
    try {
      localStorage.setItem(SNOOZE_KEY_PREFIX + taskId, String(Date.now() + SNOOZE_MINUTES * 60 * 1000));
    } catch (e) { /* localStorage disabled 静默 */ }
  }

  // ── Toast 轻提示（不依赖外部 CSS）──
  function showToast(msg, kind) {
    try {
      if (!toastEl) {
        toastEl = h('div', null, {
          'id': 'ar-toast',
          'style': 'position:fixed;top:72px;right:24px;z-index:2147483646;padding:12px 20px;border-radius:8px;' +
                   'color:#fff;font-size:14px;font-family:system-ui;box-shadow:0 8px 24px rgba(0,0,0,.18);' +
                   'transition:opacity .3s;opacity:0;pointer-events:none;max-width:360px;'
        });
        document.body.appendChild(toastEl);
      }
      var bg = kind === 'success' ? '#10b981' : kind === 'error' ? '#ef4444' : '#3b82f6';
      toastEl.style.background = bg;
      toastEl.textContent = String(msg);
      toastEl.style.opacity = '1';
      setTimeout(function () { if (toastEl) toastEl.style.opacity = '0'; }, 3200);
    } catch (e) { /* fail-open */ }
  }

  // ── 构造/复用 Modal 根结构 ──
  function ensureModal() {
    if (modalRoot && modalRoot.parentNode) return modalRoot;
    // 遮罩
    var overlay = h('div', null, {
      'id': 'ar-modal-overlay',
      'class': 'ar-modal-overlay hidden',
      'style': 'position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:2147483640;display:none;' +
               'align-items:center;justify-content:center;padding:12px;'
    });
    // 卡片
    var card = h('div', null, {
      'id': 'ar-modal-card',
      'class': 'ar-modal-card',
      'style': 'background:#fff;border-radius:14px;max-width:480px;width:100%;box-shadow:0 24px 60px rgba(0,0,0,.22);' +
               'overflow:hidden;font-family:system-ui,"PingFang SC","Microsoft YaHei",sans-serif;animation:ar-pop .18s ease-out;'
    });
    // Header
    var header = h('div', null, { 'id': 'ar-modal-header',
      'style': 'padding:18px 20px;background:#1C1917;color:#fff;display:flex;align-items:center;gap:10px;' });
    header.appendChild(h('span', '', { 'class': 'xj-dot xj-dot-warning', 'style': 'width:10px;height:10px;' }));
    header.appendChild(h('div', null, { 'style': 'flex:1;' }, [
      h('div', null, { 'id': 'ar-modal-title', 'style': 'font-size:16px;font-weight:600;' }),
      h('div', null, { 'id': 'ar-modal-subtitle', 'style': 'font-size:12px;opacity:.9;margin-top:2px;' })
    ]));
    // Body
    var body = h('div', null, { 'id': 'ar-modal-body', 'style': 'padding:20px;color:#334155;font-size:14px;line-height:1.6;' });
    body.appendChild(h('div', null, { 'style': 'display:grid;gap:10px;' }, [
      rowEl('任务标题', 'ar-row-title'),
      rowEl('平台',     'ar-row-platform'),
      rowEl('问题类型', 'ar-row-type'),
      rowEl('描述',     'ar-row-desc'),
      rowEl('创建时间', 'ar-row-created'),
      rowEl('过期时间', 'ar-row-expires')
    ]));
    // recovery_url 外链区
    var linkWrap = h('div', null, { 'id': 'ar-modal-linkwrap', 'style': 'margin-top:14px;padding:12px;border-radius:8px;background:#f8fafc;border:1px solid #e2e8f0;display:none;' });
    linkWrap.appendChild(h('div', '去官方完成验证 ↓', { 'style': 'font-size:12px;color:#64748b;margin-bottom:6px;' }));
    linkWrap.appendChild(h('a', null, { 'id': 'ar-modal-recovery-link', 'href': '#' }));
    body.appendChild(linkWrap);
    // Actions
    var actions = h('div', null, { 'style': 'padding:14px 20px;border-top:1px solid #f1f5f9;display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap;' });
    var laterBtn = h('button', '稍后处理（30分钟）', { 'id': 'ar-btn-later', 'type': 'button',
      'style': 'height:40px;padding:0 16px;border-radius:8px;border:1px solid #cbd5e1;background:#fff;color:#334155;cursor:pointer;font-size:14px;' });
    var doneBtn = h('button', '我已完成验证', { 'id': 'ar-btn-done', 'type': 'button',
      'style': 'height:40px;padding:0 20px;border-radius:8px;border:none;background:#1C1917;color:#fff;cursor:pointer;font-size:14px;font-weight:500;' });
    actions.appendChild(laterBtn);
    actions.appendChild(doneBtn);

    card.appendChild(header); card.appendChild(body); card.appendChild(actions);
    overlay.appendChild(card);
    document.body.appendChild(overlay);

    // @keyframes 注入（仅一次）
    try {
      var styleTag = document.createElement('style');
      styleTag.textContent = '@keyframes ar-pop{from{transform:scale(.94);opacity:0}to{transform:scale(1);opacity:1}}' +
        ' .ar-modal-overlay.visible{display:flex !important;}' +
        ' .ar-modal-card .row{display:flex;gap:10px;}' +
        ' .ar-modal-card .row .k{width:84px;flex-shrink:0;color:#64748b;}' +
        ' .ar-modal-card .row .v{flex:1;color:#0f172a;word-break:break-all;}';
      document.head.appendChild(styleTag);
    } catch (e) { /* ignore */ }

    // events
    laterBtn.addEventListener('click', function () {
      if (currentActiveTaskId != null) snooze(currentActiveTaskId);
      hideModal();
    });
    doneBtn.addEventListener('click', onCompleteClick);
    overlay.addEventListener('click', function (e) {
      // 点遮罩 → 视为「稍后处理」防骚扰（否则用户每10秒被逼看一次）
      if (e.target === overlay) {
        if (currentActiveTaskId != null) snooze(currentActiveTaskId);
        hideModal();
      }
    });
    modalRoot = overlay;
    return modalRoot;
  }
  function rowEl(label, idSuffix) {
    return h('div', null, { 'class': 'row' }, [
      h('div', label, { 'class': 'k' }),
      h('div', null, { 'class': 'v', 'id': 'ar-modal-' + idSuffix })
    ]);
  }
  function showModal() {
    var m = ensureModal();
    m.classList.remove('hidden');
    m.classList.add('visible');
  }
  function hideModal() {
    if (!modalRoot) return;
    modalRoot.classList.add('hidden');
    modalRoot.classList.remove('visible');
  }

  // ── 填充 Modal 动态字段（全部 textContent = XSS 安全）──
  function fillModal(task) {
    ensureModal();
    currentActiveTaskId = task.id;
    safeText('ar-modal-title', '需要人工验证 · ' + (platformLabel(task.platform) || '平台'));
    safeText('ar-modal-subtitle', '系统已自动暂停风险采集，请完成合法验证后点击「我已完成验证」恢复。');
    safeText('ar-modal-title', '需要人工验证 · ' + (platformLabel(task.platform) || '平台')); // dup OK
    // 上面把 title 写了两次，下面重写 subtitle 正确：
    safeText('ar-modal-subtitle', 'AGENTS §7.2 Auth Recovery Center（永不破解验证码）');
    safeText('ar-row-title',    task.title    || '--');
    safeText('ar-row-platform', platformLabel(task.platform) || task.platform || '--');
    safeText('ar-row-type',     issueTypeLabel(task.issue_type) || task.issue_type || '--');
    safeText('ar-row-desc',     task.description || '（无详细描述，请打开官方链接完成验证）');
    safeText('ar-row-created',  fmtTime(task.created_at));
    safeText('ar-row-expires',  fmtTime(task.expires_at));
    // recovery_url 链接（如果存在）
    var linkWrap = document.getElementById('ar-modal-linkwrap');
    var a = document.getElementById('ar-modal-recovery-link');
    if (linkWrap && a) {
      if (task.recovery_url) {
        linkWrap.style.display = 'block';
        a.textContent = String(task.recovery_url);
        try { a.href = encodeURI(String(task.recovery_url)); } catch (e) { a.href = '#'; }
        a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener noreferrer');
      } else if (task.qr_code_url) {
        // 若后端给了二维码 URL（未来扩展），只给文字链接，不内联 img 防止第三方追踪
        linkWrap.style.display = 'block';
        a.textContent = '打开二维码页面（' + String(task.qr_code_url).slice(0, 60) + '…）';
        try { a.href = encodeURI(String(task.qr_code_url)); } catch (e) { a.href = '#'; }
        a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener noreferrer');
      } else {
        linkWrap.style.display = 'none';
      }
    }
  }
  function safeText(id, text) {
    try {
      var el = document.getElementById(id);
      if (el) el.textContent = String(text == null ? '--' : text);
    } catch (e) { /* ignore */ }
  }
  function platformLabel(p) {
    return ({ xiaohongshu: '小红书', weibo: '微博', bilibili: 'B站', douyin: '抖音' })[String(p || '').toLowerCase()] || null;
  }
  function issueTypeLabel(t) {
    return ({
      cookie_expired: 'Cookie 过期',
      login_expired:  '登录态失效',
      captcha:        '需要验证码',
      qr_required:    '需要扫码登录',
      session_invalid:'Session 无效',
      ip_risk:        'IP 风控',
      unknown:        '未知认证异常'
    })[String(t || '').toLowerCase()] || null;
  }
  function fmtTime(v) {
    if (!v) return '--';
    try {
      var d = v instanceof Date ? v : new Date(v);
      if (isNaN(d.getTime())) return String(v);
      return d.toLocaleString('zh-CN');
    } catch (e) { return String(v); }
  }

  // ── 点击「我已完成验证」── 打 POST complete → 自动刷新健康端点 ──
  function onCompleteClick() {
    var id = currentActiveTaskId;
    if (id == null) return;
    var btn = document.getElementById('ar-btn-done');
    try {
      if (btn) { btn.disabled = true; btn.textContent = '验证中…'; btn.style.opacity = '0.7'; }
    } catch (e) { /* ignore */ }

    fetchTimeout('/api/auth-recovery/tasks/' + encodeURIComponent(String(id)) + '/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}'
    }).then(function (r) { return r.ok ? r.json().catch(function () { return ({}); }) : Promise.reject(new Error('HTTP ' + r.status)); })
      .then(function () {
        showToast('已通知系统执行恢复探活，正在刷新健康状态…', 'success');
        hideModal();
        currentActiveTaskId = null;
        // 异步刷新 4 个健康端点（让用户刚验证完就看到真实状态）
        return Promise.all(HEALTH_URLS.map(function (u) {
          return fetchTimeout(u, { cache: 'no-store' }).catch(function () { return null; });
        }));
      })
      .then(function () {
        // 3 秒后立刻再拉一次 summary（刷新徽章 + 可能还有别的 task）
        setTimeout(pollOnce, 2500);
      })
      .catch(function (err) {
        console.warn('[ar-poller] complete failed:', err && err.message);
        showToast('恢复请求失败，请稍后重试：' + (err && err.message ? err.message : '网络异常'), 'error');
      })
      .then(function () {
        try {
          if (btn) { btn.disabled = false; btn.textContent = '我已完成验证'; btn.style.opacity = '1'; }
        } catch (e) { /* ignore */ }
      });
  }

  // ── 主轮询 ──
  function pollOnce() {
    fetchTimeout(SUMMARY_URL, { cache: 'no-store', credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        // ── 兼容 3 种响应形状（后端外层 data 包裹 / 直接字段 / 未来扩展 tasks 别名）──
        var payload = data || {};
        var inner = payload.data && typeof payload.data === 'object' ? payload.data : null;
        var cnt = (typeof payload.pending_count === 'number') ? payload.pending_count
          : ((inner && typeof inner.pending_count === 'number') ? inner.pending_count : 0);
        updateBadge(cnt);
        if (cnt === 0) { currentActiveTaskId = null; return; }
        // 只处理第一个 pending（最紧急），其余通过徽章数值提示
        var tasks = Array.isArray(payload.tasks) ? payload.tasks
          : (Array.isArray(inner && inner.pending_tasks) ? inner.pending_tasks
          : (Array.isArray(inner && inner.tasks) ? inner.tasks : []));
        var t = null;
        for (var i = 0; i < tasks.length; i++) {
          if (tasks[i] && String(tasks[i].status || '').toLowerCase() === 'pending') {
            if (!isSnoozed(tasks[i].id)) { t = tasks[i]; break; }
          }
        }
        if (!t) return;
        // 如果当前已有 modal 显示另一条任务，不切（防抖动）
        if (currentActiveTaskId != null && currentActiveTaskId !== t.id) return;
        fillModal(t);
        showModal();
      })
      .catch(function (e) {
        // 所有网络异常/解析异常 → 静默，不抛到 UI 影响主页面
        console.debug('[ar-poller] poll skip:', e && e.message);
      });
  }

  // ── 启动：DOM Ready → 首拉 → 10s 轮询 ──
  function boot() {
    try {
      ensureModal();  // 预创建（若页面根本没 user 元素也不影响）
      pollOnce();
      setInterval(pollOnce, POLL_INTERVAL_MS);
    } catch (e) {
      console.warn('[ar-poller] boot failed:', e && e.message);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
