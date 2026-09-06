/* ============================================================
 * keyboard-shortcuts.js — 三域键盘快捷键帮助窗口（ZBC V1.1 架构）
 * Ctrl+/ 或 ? 唤起；覆盖三域导航、全局操作、视图切换。
 * 自包含模态，不依赖旧 openModal；从真实 .zbc-nav-item 动态生成。
 * ============================================================ */
(function () {
  'use strict';
  var STYLE_ID = 'zbc-kb-style';
  var MODAL_ID = 'zbc-kb-modal';

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var css = [
      '#zbc-kb-modal{position:fixed;inset:0;z-index:9999;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.45);backdrop-filter:blur(4px)}',
      '#zbc-kb-modal.is-open{display:flex;animation:zbc-kb-fade .18s ease}',
      '@keyframes zbc-kb-fade{from{opacity:0}to{opacity:1}}',
      '.zbc-kb-panel{width:min(560px,calc(100vw - 32px));max-height:min(78vh,680px);background:var(--l-bg,#fff);border:1px solid var(--l-border,#e8e8e8);border-radius:16px;box-shadow:0 24px 64px rgba(0,0,0,.18);display:flex;flex-direction:column;overflow:hidden;animation:zbc-kb-in .22s cubic-bezier(.16,1,.3,1)}',
      '@keyframes zbc-kb-in{from{opacity:0;transform:scale(.96) translateY(10px)}to{opacity:1;transform:none}}',
      '[data-theme="dark"] .zbc-kb-panel{background:var(--d-bg,#0d0d0d);border-color:var(--d-border,#2f2f2f)}',
      '.zbc-kb-head{display:flex;align-items:center;justify-content:space-between;padding:18px 22px 14px;border-bottom:1px solid var(--l-border-light,#f0f0f0)}',
      '[data-theme="dark"] .zbc-kb-head{border-color:var(--d-border-light,#262626)}',
      '.zbc-kb-head h2{font-size:17px;font-weight:600;color:var(--l-text,#0d0d0d);margin:0}',
      '[data-theme="dark"] .zbc-kb-head h2{color:var(--d-text,#f5f5f5)}',
      '.zbc-kb-head .zbc-kb-hint{font-size:11px;color:var(--l-text-tertiary,#9ca3af);font-family:"JetBrains Mono",monospace}',
      '.zbc-kb-close{background:none;border:none;font-size:18px;color:var(--l-text-secondary,#6b7280);cursor:pointer;padding:4px 8px;border-radius:8px}',
      '.zbc-kb-close:hover{background:var(--l-bg-secondary,#f7f7f8)}',
      '.zbc-kb-search-wrap{position:relative;padding:12px 22px 8px}',
      '.zbc-kb-search-wrap input{width:100%;box-sizing:border-box;padding:9px 12px 9px 36px;border:1px solid var(--l-border,#e8e8e8);border-radius:10px;background:var(--l-bg-secondary,#f7f7f8);font-size:13px;color:var(--l-text,#0d0d0d);outline:none;font-family:inherit}',
      '.zbc-kb-search-wrap input:focus{border-color:var(--l-accent,#0f766e);background:var(--l-bg,#fff);box-shadow:0 0 0 3px rgba(15,118,110,.12)}',
      '[data-theme="dark"] .zbc-kb-search-wrap input{background:var(--d-bg-secondary,#141414);border-color:var(--d-border,#2f2f2f);color:var(--d-text,#f5f5f5)}',
      '.zbc-kb-search-icon{position:absolute;left:34px;top:50%;transform:translateY(-50%);width:15px;height:15px;color:var(--l-text-tertiary,#9ca3af)}',
      '.zbc-kb-body{overflow-y:auto;overscroll-behavior:contain;padding:4px 22px 18px;flex:1}',
      '.zbc-kb-group-title{font-size:11px;font-weight:600;color:var(--l-text-tertiary,#9ca3af);margin:14px 2px 6px;letter-spacing:.06em;text-transform:uppercase}',
      '.zbc-kb-group-title:first-child{margin-top:6px}',
      '.zbc-kb-row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:7px 8px;border-radius:8px;cursor:pointer;transition:background .12s}',
      '.zbc-kb-row:hover{background:var(--l-bg-secondary,#f7f7f8)}',
      '[data-theme="dark"] .zbc-kb-row:hover{background:var(--d-bg-secondary,#141414)}',
      '.zbc-kb-name{font-size:13px;color:var(--l-text,#0d0d0d);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '[data-theme="dark"] .zbc-kb-name{color:var(--d-text,#f5f5f5)}',
      '.zbc-kb-keys{display:flex;gap:4px;align-items:center;flex-shrink:0}',
      '.zbc-kb-keys kbd{font-family:"JetBrains Mono",monospace;font-size:11px;padding:3px 7px;border:1px solid var(--l-border,#e8e8e8);border-bottom-width:2px;border-radius:6px;background:var(--l-bg-secondary,#f7f7f8);color:var(--l-text-secondary,#6b7280)}',
      '[data-theme="dark"] .zbc-kb-keys kbd{background:var(--d-card,#1f1f1f);border-color:var(--d-border,#2f2f2f);color:var(--d-text-secondary,#a1a1aa)}',
      '.zbc-kb-empty{display:none;padding:32px 8px;text-align:center;color:var(--l-text-tertiary,#9ca3af);font-size:13px}',
      '.zbc-kb-footer{padding:10px 22px;border-top:1px solid var(--l-border-light,#f0f0f0);font-size:11px;color:var(--l-text-tertiary,#9ca3af);display:flex;justify-content:space-between}',
      '[data-theme="dark"] .zbc-kb-footer{border-color:var(--d-border-light,#262626)}',
      '@media(max-width:600px){.zbc-kb-panel{max-height:88vh}.zbc-kb-head{padding:14px 16px 12px}.zbc-kb-search-wrap{padding:10px 16px 6px}.zbc-kb-body{padding:4px 16px 14px}}'
    ].join('');
    var st = document.createElement('style');
    st.id = STYLE_ID;
    st.textContent = css;
    document.head.appendChild(st);
  }

  function getNavItems() {
    var groups = document.querySelectorAll('.zbc-nav-group');
    var items = [];
    groups.forEach(function (g) {
      var domain = g.getAttribute('data-domain-nav') || '';
      var links = g.querySelectorAll('.zbc-nav-item');
      links.forEach(function (a, idx) {
        var label = a.querySelector('.zbc-nav-item__label');
        var name = label ? label.textContent.trim() : a.textContent.trim();
        var href = a.getAttribute('href') || '';
        if (name && href) items.push({ domain: domain, name: name, href: href, index: idx });
      });
    });
    return items;
  }

  function renderKbd(combo) {
    return combo.split('+').map(function (p) { return '<kbd>' + p + '</kbd>'; }).join('');
  }

  function buildGroups() {
    var groups = [];
    var navItems = getNavItems();
    var domainLabels = { zbmp: 'ZBMP 品牌智能域', cth: 'CTH 太古汇情报域', system: 'SYSTEM 运行控制域' };
    ['zbmp', 'cth', 'system'].forEach(function (domain) {
      var domainItems = navItems.filter(function (n) { return n.domain === domain; });
      if (domainItems.length) {
        var rows = domainItems.map(function (n, i) {
          var num = (i + 1) % 10;
          return { name: n.name, combos: ['Alt+' + num], href: n.href, text: (domain + ' ' + n.name).toLowerCase() };
        });
        groups.push({ title: domainLabels[domain] + '（Alt+数字）', rows: rows });
      }
    });
    groups.push({
      title: '全局操作',
      rows: [
        { name: '搜索', combos: ['Ctrl+K'], action: 'search', text: '搜索 search' },
        { name: '刷新当前页', combos: ['Ctrl+Shift+R'], action: 'refresh', text: '刷新 refresh' },
        { name: 'AI 助手', combos: ['Ctrl+J'], action: 'ai', text: 'ai 助手 智能' },
        { name: '切换主题', combos: ['Ctrl+T'], action: 'theme', text: '主题 theme dark light' },
        { name: '切换 ZBMP 域', combos: ['Ctrl+1'], action: 'domain-zbmp', text: 'zbmp 域' },
        { name: '切换 CTH 域', combos: ['Ctrl+2'], action: 'domain-cth', text: 'cth 域' },
        { name: '切换 SYSTEM 域', combos: ['Ctrl+3'], action: 'domain-system', text: 'system 域' }
      ]
    });
    groups.push({
      title: '视图与窗口',
      rows: [
        { name: '显示快捷键', combos: ['Ctrl+/', '?'], action: 'kb', text: '快捷键 shortcuts help' },
        { name: '关闭弹窗', combos: ['Esc'], action: 'close', text: '关闭 esc' },
        { name: '返回上一页', combos: ['Alt+Left'], action: 'back', text: '返回 back' }
      ]
    });
    return groups;
  }

  function renderPanel(groups) {
    var html = '<div class="zbc-kb-head"><h2>键盘快捷键</h2>' +
      '<div style="display:flex;align-items:center;gap:12px"><span class="zbc-kb-hint">搜索过滤</span>' +
      '<button class="zbc-kb-close" id="zbc-kb-close">×</button></div></div>' +
      '<div class="zbc-kb-search-wrap"><svg class="zbc-kb-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
      '<input type="text" id="zbc-kb-filter" placeholder="搜索快捷键…" autocomplete="off"></div>' +
      '<div class="zbc-kb-body" id="zbc-kb-body">';
    groups.forEach(function (g) {
      html += '<div class="zbc-kb-group"><div class="zbc-kb-group-title">' + g.title + '</div><div>';
      g.rows.forEach(function (r) {
        html += '<div class="zbc-kb-row" data-text="' + (r.text || r.name).toLowerCase() + '"' +
          (r.href ? ' data-href="' + r.href + '"' : '') + (r.action ? ' data-action="' + r.action + '"' : '') + '>' +
          '<span class="zbc-kb-name">' + r.name + '</span><span class="zbc-kb-keys">' + r.combos.map(renderKbd).join('') + '</span></div>';
      });
      html += '</div></div>';
    });
    html += '<div class="zbc-kb-empty" id="zbc-kb-empty">没有匹配的快捷键</div></div>' +
      '<div class="zbc-kb-footer"><span>三域导航 · 全局操作</span><span>Esc 关闭</span></div>';
    return html;
  }

  function bindFilter(modal) {
    var input = modal.querySelector('#zbc-kb-filter');
    var body = modal.querySelector('#zbc-kb-body');
    if (!input || !body) return;
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      var any = false;
      body.querySelectorAll('.zbc-kb-group').forEach(function (g) {
        var visible = 0;
        g.querySelectorAll('.zbc-kb-row').forEach(function (row) {
          var hit = !q || (row.getAttribute('data-text') || '').indexOf(q) !== -1;
          row.style.display = hit ? '' : 'none';
          if (hit) visible++;
        });
        g.style.display = visible ? '' : 'none';
        any += visible;
      });
      var empty = body.querySelector('#zbc-kb-empty');
      if (empty) empty.style.display = any ? 'none' : 'block';
    });
  }

  function executeAction(action) {
    switch (action) {
      case 'search':
        var si = document.querySelector('.zbc-search__input');
        if (si) { si.focus(); si.select(); }
        break;
      case 'refresh': window.location.reload(); break;
      case 'ai':
        if (window.ZBCAIAssistant && typeof window.ZBCAIAssistant.toggle === 'function') window.ZBCAIAssistant.toggle();
        break;
      case 'theme':
        var t = document.getElementById('zbc-theme-toggle');
        if (t) t.click();
        break;
      case 'domain-zbmp': case 'domain-cth': case 'domain-system':
        var d = action.replace('domain-', '');
        var tab = document.querySelector('.zbc-domain-tab[data-domain="' + d + '"]');
        if (tab) tab.click();
        break;
      case 'back': window.history.back(); break;
    }
  }

  function openKB() {
    var modal = document.getElementById(MODAL_ID);
    if (!modal) {
      modal = document.createElement('div');
      modal.id = MODAL_ID;
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      document.body.appendChild(modal);
    }
    modal.innerHTML = '<div class="zbc-kb-panel">' + renderPanel(buildGroups()) + '</div>';
    modal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    var cb = modal.querySelector('#zbc-kb-close');
    if (cb) cb.addEventListener('click', closeKB);
    modal.addEventListener('click', function (e) { if (e.target === modal) closeKB(); });
    modal.querySelectorAll('.zbc-kb-row').forEach(function (row) {
      row.addEventListener('click', function () {
        var href = row.getAttribute('data-href');
        var action = row.getAttribute('data-action');
        if (href) { closeKB(); setTimeout(function () { window.location.href = href; }, 80); }
        else if (action) { closeKB(); setTimeout(function () { executeAction(action); }, 80); }
      });
    });
    bindFilter(modal);
    setTimeout(function () {
      var input = modal.querySelector('#zbc-kb-filter');
      if (input) input.focus();
    }, 50);
  }

  function closeKB() {
    var modal = document.getElementById(MODAL_ID);
    if (modal) { modal.classList.remove('is-open'); document.body.style.overflow = ''; }
  }

  function isTyping(t) {
    if (!t) return false;
    var tag = t.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || !!t.isContentEditable;
  }

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === '/' || e.keyCode === 191)) {
      e.preventDefault();
      var modal = document.getElementById(MODAL_ID);
      if (modal && modal.classList.contains('is-open')) closeKB(); else openKB();
      return;
    }
    if (e.key === '?' && !e.ctrlKey && !e.altKey && !e.metaKey && !isTyping(e.target)) {
      e.preventDefault(); openKB(); return;
    }
    if (e.key === 'Escape') { closeKB(); return; }
    if (isTyping(e.target)) return;
    if (e.altKey && !e.ctrlKey && !e.metaKey) {
      var idx = null;
      if (/^[1-9]$/.test(e.key)) idx = parseInt(e.key, 10) - 1;
      else if (e.key === '0') idx = 9;
      if (idx !== null) {
        var activeDomain = document.body.getAttribute('data-domain') || 'cth';
        var group = document.querySelector('.zbc-nav-group[data-domain-nav="' + activeDomain + '"]');
        if (group) {
          var items = group.querySelectorAll('.zbc-nav-item');
          if (items[idx]) { e.preventDefault(); closeKB(); window.location.href = items[idx].getAttribute('href'); }
        }
      } else if (e.key === 'ArrowLeft') { e.preventDefault(); window.history.back(); }
      return;
    }
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); executeAction('search'); return; }
    if ((e.ctrlKey || e.metaKey) && (e.key === 'j' || e.key === 'J')) { e.preventDefault(); executeAction('ai'); return; }
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey) {
      if (e.key === '1') { e.preventDefault(); executeAction('domain-zbmp'); return; }
      if (e.key === '2') { e.preventDefault(); executeAction('domain-cth'); return; }
      if (e.key === '3') { e.preventDefault(); executeAction('domain-system'); return; }
    }
  }, true);

  function boot() {
    injectStyle();
    window.ZBCKeyboardShortcuts = { open: openKB, close: closeKB };
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  console.log('[keyboard-shortcuts] 三域键盘快捷键已加载（Ctrl+/ 唤起）');
})();
