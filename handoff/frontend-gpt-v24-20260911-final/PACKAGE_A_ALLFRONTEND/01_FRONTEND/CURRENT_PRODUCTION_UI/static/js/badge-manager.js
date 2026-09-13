/* ============================================================
 * badge-manager.js — 全局红点提醒（ZBC V1.1 架构）
 * 铃铛未读数 + 负面待审数，30s 轮询，断API静默降级
 * ============================================================ */
(function () {
  'use strict';

  var POLL_INTERVAL = 30000;
  var timer = null;
  var currentCounts = { unread: 0, negative_pending: 0 };

  function injectBadgeStyle() {
    if (document.getElementById('zbc-badge-style')) return;
    var css = [
      '.zbc-bell-btn{position:relative}',
      '.zbc-badge{position:absolute;top:-2px;right:-2px;min-width:18px;height:18px;padding:0 5px;border-radius:9px;background:var(--l-danger,#dc2626);color:#fff;font-size:10px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;line-height:1;box-shadow:0 0 0 2px var(--l-bg,#fff);animation:zbc-badge-pulse 2s ease-in-out infinite}',
      '[data-theme="dark"] .zbc-badge{box-shadow:0 0 0 2px var(--d-bg,#0d0d0d)}',
      '@keyframes zbc-badge-pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}',
      '.zbc-badge--gold{background:var(--l-gold,#c9a961)}',
      '.zbc-notif-panel{position:fixed;top:64px;right:16px;width:360px;max-height:70vh;background:var(--l-bg,#fff);border:1px solid var(--l-border,#e8e8e8);border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.15);z-index:9998;display:none;flex-direction:column;overflow:hidden;animation:zbc-notif-in .2s ease}',
      '.zbc-notif-panel.is-open{display:flex}',
      '@keyframes zbc-notif-in{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}',
      '[data-theme="dark"] .zbc-notif-panel{background:var(--d-bg,#0d0d0d);border-color:var(--d-border,#2f2f2f)}',
      '.zbc-notif-head{padding:14px 16px;border-bottom:1px solid var(--l-border-light,#f0f0f0);display:flex;justify-content:space-between;align-items:center}',
      '[data-theme="dark"] .zbc-notif-head{border-color:var(--d-border-light,#262626)}',
      '.zbc-notif-head h3{font-size:14px;font-weight:600;margin:0;color:var(--l-text,#0d0d0d)}',
      '[data-theme="dark"] .zbc-notif-head h3{color:var(--d-text,#f5f5f5)}',
      '.zbc-notif-mark-all{font-size:11px;color:var(--l-accent,#0f766e);background:none;border:none;cursor:pointer;padding:4px 8px;border-radius:6px}',
      '.zbc-notif-mark-all:hover{background:var(--l-bg-secondary,#f7f7f8)}',
      '.zbc-notif-body{overflow-y:auto;flex:1;padding:8px}',
      '.zbc-notif-item{padding:10px 12px;border-radius:8px;margin-bottom:4px;cursor:pointer;transition:background .12s}',
      '.zbc-notif-item:hover{background:var(--l-bg-secondary,#f7f7f8)}',
      '[data-theme="dark"] .zbc-notif-item:hover{background:var(--d-bg-secondary,#141414)}',
      '.zbc-notif-item-title{font-size:13px;font-weight:500;color:var(--l-text,#0d0d0d);margin-bottom:2px}',
      '[data-theme="dark"] .zbc-notif-item-title{color:var(--d-text,#f5f5f5)}',
      '.zbc-notif-item-meta{font-size:11px;color:var(--l-text-tertiary,#9ca3af)}',
      '.zbc-notif-empty{padding:32px 16px;text-align:center;color:var(--l-text-tertiary,#9ca3af);font-size:13px}',
      '.zbc-notif-error{padding:16px;text-align:center;color:var(--l-danger,#dc2626);font-size:12px}',
      '@media(max-width:600px){.zbc-notif-panel{width:calc(100vw - 32px);right:16px;left:16px}}'
    ].join('');
    var st = document.createElement('style');
    st.id = 'zbc-badge-style';
    st.textContent = css;
    document.head.appendChild(st);
  }

  function fetchCounts() {
    if (typeof LUMENIS === 'undefined' || !LUMENIS.fetch) return Promise.reject(new Error('LUMENIS not ready'));
    return LUMENIS.fetch('/api/badge/counts').then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function updateBadge(data) {
    var total = (data.unread_alerts || 0) + (data.negative_pending || 0);
    currentCounts.unread = data.unread_alerts || 0;
    currentCounts.negative_pending = data.negative_pending || 0;
    var badge = document.getElementById('zbc-badge-count');
    if (badge) {
      if (total > 0) {
        badge.textContent = total > 99 ? '99+' : String(total);
        badge.hidden = false;
      } else {
        badge.hidden = true;
      }
    }
  }

  function refresh() {
    fetchCounts().then(updateBadge).catch(function () {
      // 静默降级：断API不显示错误，保持上次状态
    });
  }

  function buildNotifPanel() {
    var panel = document.createElement('div');
    panel.className = 'zbc-notif-panel';
    panel.id = 'zbc-notif-panel';
    panel.innerHTML =
      '<div class="zbc-notif-head"><h3>通知中心</h3>' +
      '<button class="zbc-notif-mark-all" id="zbc-notif-mark-all">全部已读</button></div>' +
      '<div class="zbc-notif-body" id="zbc-notif-body"><div class="zbc-notif-empty">暂无通知</div></div>';
    document.body.appendChild(panel);
    return panel;
  }

  function loadNotifList() {
    var body = document.getElementById('zbc-notif-body');
    if (!body) return;
    body.innerHTML = '<div class="zbc-notif-empty">加载中…</div>';
    if (typeof LUMENIS === 'undefined' || !LUMENIS.fetch) {
      body.innerHTML = '<div class="zbc-notif-error">LUMENIS 未就绪</div>';
      return;
    }
    LUMENIS.fetch('/api/badge/notifications?limit=20').then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (data) {
      var items = data.notifications || data.items || [];
      if (!items.length) {
        body.innerHTML = '<div class="zbc-notif-empty">暂无通知</div>';
        return;
      }
      body.innerHTML = items.map(function (n) {
        var title = n.title || n.message || '通知';
        var meta = n.time || n.created_at || '';
        var type = n.type || 'info';
        var typeLabel = { alert: '告警', negative: '负面待审', info: '系统' }[type] || type;
        return '<div class="zbc-notif-item" data-id="' + (n.id || '') + '">' +
          '<div class="zbc-notif-item-title">' + title + '</div>' +
          '<div class="zbc-notif-item-meta">' + typeLabel + ' · ' + meta + '</div></div>';
      }).join('');
    }).catch(function (err) {
      body.innerHTML = '<div class="zbc-notif-error">加载失败：' + (err.message || '未知错误') +
        ' <button onclick="ZBCBadgeManager.reloadNotif()" style="background:none;border:none;color:var(--l-accent,#0f766e);cursor:pointer;font-size:11px">重试</button></div>';
    });
  }

  function togglePanel() {
    var panel = document.getElementById('zbc-notif-panel') || buildNotifPanel();
    var isOpen = panel.classList.toggle('is-open');
    if (isOpen) loadNotifList();
  }

  function markAllRead() {
    if (typeof LUMENIS === 'undefined' || !LUMENIS.fetch) return;
    LUMENIS.fetch('/api/badge/mark-all-read', { method: 'POST' }).then(function () {
      refresh();
      loadNotifList();
    }).catch(function () {});
  }

  function boot() {
    injectBadgeStyle();
    var bell = document.getElementById('zbc-bell-btn');
    if (bell) bell.addEventListener('click', togglePanel);

    // 点击外部关闭通知面板
    document.addEventListener('click', function (e) {
      var panel = document.getElementById('zbc-notif-panel');
      var bell = document.getElementById('zbc-bell-btn');
      if (panel && panel.classList.contains('is-open') &&
          !panel.contains(e.target) && bell && !bell.contains(e.target)) {
        panel.classList.remove('is-open');
      }
    });

    // 全部已读
    document.addEventListener('click', function (e) {
      if (e.target.id === 'zbc-notif-mark-all') markAllRead();
    });

    refresh();
    timer = setInterval(refresh, POLL_INTERVAL);

    window.ZBCBadgeManager = {
      refresh: refresh,
      reloadNotif: loadNotifList,
      getCounts: function () { return currentCounts; }
    };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  console.log('[badge-manager] 全局红点提醒已加载（30s轮询）');
})();
