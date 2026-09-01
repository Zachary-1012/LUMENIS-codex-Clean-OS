/* ============================================================
 * keyboard_shortcuts.js — 键盘快捷键帮助窗口（独立补丁，可随时移除）
 * ------------------------------------------------------------
 * 对齐 ChatGPT / Codex「键盘快捷键」窗口：居中模态 + 实时搜索过滤 +
 * 分组列表 + 右侧 kbd 键帽；遵循 ZBIP 侘寂黑白灰与统一单模态规范。
 *
 * 设计约束：
 * 1. 复用既有统一单模态 #modal（openModal/closeModal），不新增遮罩、不造第二套弹窗；
 * 2. 导航条目从侧栏真实 .side-item[data-page] 动态生成，永远与系统实际页面一致；
 * 3. 只绑定无浏览器冲突的组合键（Ctrl+/、?、Alt+数字、移动端 Ctrl+B），
 *    绝不拦截 Ctrl+R / F5 / Ctrl+T/N/W/P / F12 等浏览器与系统默认行为；
 * 4. 不修改 app.js 与任何后端逻辑，纯前端增强，删除本文件即完全回滚。
 * ============================================================ */
(function () {
  'use strict';

  var KB_STYLE_ID = 'kb-shortcuts-style';
  var FILTER_ID = 'kbFilter';
  var BODY_ID = 'kbBody';

  /* ---------- 注入样式（一次；黑白灰，优先使用全局 token，带回退值） ---------- */
  function injectStyle() {
    if (document.getElementById(KB_STYLE_ID)) return;
    var css = [
      '.kb-dialog{display:flex;flex-direction:column;max-height:min(74vh,660px);color:var(--text,#1d1d1f);font-size:14px}',
      '.kb-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:2px}',
      '.kb-head h2{font-size:17px;font-weight:600;margin:0;letter-spacing:.01em;white-space:nowrap}',
      '.kb-head .kb-hint{font-size:12px;color:var(--muted,#86868b);white-space:nowrap}',
      '.kb-search-wrap{position:relative;margin:14px 0 8px}',
      '.kb-search-wrap svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);width:15px;height:15px;stroke:var(--muted,#8a8a8e);pointer-events:none}',
      '#kbFilter{width:100%;box-sizing:border-box;padding:9px 12px 9px 34px;border:1px solid var(--border,#d8d8dc);border-radius:10px;background:var(--bg,#f5f5f7);font-size:13px;line-height:1.4;color:inherit;outline:none;box-shadow:none;transition:border-color .15s,background .15s}',
      '#kbFilter:focus{border-color:var(--text,#1d1d1f);background:var(--surface,#fff);box-shadow:0 0 0 3px rgba(0,0,0,.06)}',
      '.kb-body{overflow-y:auto;overscroll-behavior:contain;margin:0 -6px;padding:0 6px 4px;max-height:min(60vh,560px)}',
      '.kb-group-title{font-size:12px;font-weight:600;color:var(--muted,#86868b);margin:14px 2px 6px;letter-spacing:.03em}',
      '.kb-group-title:first-child{margin-top:4px}',
      '.kb-row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:7px 6px;border-radius:8px}',
      '.kb-row.is-match{background:var(--bg,#f5f5f7)}',
      '.kb-name{font-size:13.5px;color:var(--text,#1d1d1f);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.kb-keys{display:flex;gap:5px;align-items:center;flex-shrink:0}',
      '.kb-keys kbd{font-family:inherit;font-size:12px;line-height:1;padding:3px 7px;border:1px solid var(--border,#d2d2d7);border-bottom-width:2px;border-radius:6px;background:var(--surface,#fff);color:var(--text,#3a3a3c);min-width:18px;text-align:center;white-space:nowrap}',
      '.kb-empty{display:none;padding:30px 8px;text-align:center;color:var(--muted,#86868b);font-size:13px}',
      '@media(max-width:600px){.kb-dialog{max-height:86vh}.kb-head{flex-direction:column;align-items:flex-start;gap:3px}.kb-body{max-height:64vh}.kb-name{font-size:13px}.kb-keys kbd{font-size:11px;padding:3px 6px}}',
      /* 快捷键窗口专属：桌面/移动一律苹果式居中（覆盖全局移动端底部 Sheet，仅作用本窗口） */
      '#modal.kb-modal{transform:none!important}',
      '#modal.kb-modal .modal-panel{position:fixed!important;top:50%!important;left:50%!important;right:auto!important;bottom:auto!important;transform:translate(-50%,-50%)!important;margin:0!important;width:calc(100vw - 32px)!important;max-width:520px!important;max-height:82vh!important;animation:none!important;overflow:auto!important;-webkit-overflow-scrolling:touch}',
      '#modal.kb-modal .modal-panel::before{display:none!important}',
      '@media(min-width:769px){#modal.kb-modal .modal-panel{width:520px!important}}'
    ].join('');
    var st = document.createElement('style');
    st.id = KB_STYLE_ID;
    st.textContent = css;
    document.head.appendChild(st);
  }

  /* ---------- 从真实侧栏读取可跳转页面（不写死，随系统页面自动同步） ---------- */
  function navItems() {
    var nodes = document.querySelectorAll('.side-nav .side-item[data-page]');
    var out = [];
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var page = el.getAttribute('data-page');
      var labelEl = el.querySelector('span:not(.navicon):not(.nav-badge)');
      var name = (labelEl ? labelEl.textContent : el.textContent) || '';
      name = name.replace(/\s+/g, ' ').trim();
      if (page && name) out.push({ page: page, name: name });
    }
    return out;
  }

  /* --------— 组合键拆成 kbd 键帽序列 ---------- */
  function kbds(combo) {
    return combo.split('+').map(function (part) {
      return '<kbd>' + part.replace('Alt', 'Alt').replace('Ctrl', 'Ctrl') + '</kbd>';
    }).join('');
  }

  /* ---------- 构建分组（导航动态 + 固定通用项） ---------- */
  function buildGroups() {
    var groups = [];
    var nav = navItems();
    var navRows = nav.slice(0, 10).map(function (n, i) {
      var num = (i + 1) % 10; // 1..9,0
      return { name: n.name, combos: ['Alt+' + num], text: (n.name + ' alt ' + num).toLowerCase() };
    });
    if (navRows.length) groups.push({ title: '页面导航（Alt + 数字快速跳转）', rows: navRows });

    groups.push({
      title: '视图',
      rows: [
        { name: '打开 / 收起导航抽屉（移动端）', combos: ['Ctrl+B'], text: '切换 侧边 导航 抽屉 ctrl b' }
      ]
    });

    groups.push({
      title: '通用',
      rows: [
        { name: '显示键盘快捷键', combos: ['Ctrl+/', '?'], text: '显示 键盘 快捷键 ctrl / ?' },
        { name: '关闭弹窗 / 取消', combos: ['Esc'], text: '关闭 弹窗 取消 esc' },
        { name: '返回上一页', combos: ['Alt+←'], text: '返回 上一页 alt 左' }
      ]
    });
    return groups;
  }

  function renderBody(groups) {
    var html = '';
    groups.forEach(function (g) {
      var rows = g.rows.map(function (r) {
        var keys = r.combos.map(kbds).join('<span class="kb-or" style="color:var(--muted,#aaa);font-size:11px;margin:0 1px"></span>');
        return '<div class="kb-row" data-text="' + (r.text || r.name).toLowerCase() + '">' +
          '<span class="kb-name"></span><span class="kb-keys">' + keys + '</span></div>';
      }).join('');
      html += '<div class="kb-group"><div class="kb-group-title"></div><div class="kb-rows">' + rows + '</div></div>';
    });
    // 上面用 textContent 注入避免 XSS：先建壳，再安全填字
    var wrap = document.createElement('div');
    wrap.innerHTML = html + '<div class="kb-empty" id="kbEmpty">没有匹配的快捷键</div>';
    var gNodes = wrap.querySelectorAll('.kb-group');
    groups.forEach(function (g, gi) {
      gNodes[gi].querySelector('.kb-group-title').textContent = g.title;
      var rowNodes = gNodes[gi].querySelectorAll('.kb-row');
      g.rows.forEach(function (r, ri) {
        rowNodes[ri].querySelector('.kb-name').textContent = r.name;
      });
    });
    return wrap.innerHTML;
  }

  /* ---------- 实时搜索过滤 ---------- */
  function bindFilter() {
    var input = document.getElementById(FILTER_ID);
    var body = document.getElementById(BODY_ID);
    if (!input || !body) return;
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      var any = false;
      body.querySelectorAll('.kb-group').forEach(function (g) {
        var visible = 0;
        g.querySelectorAll('.kb-row').forEach(function (row) {
          var hit = !q || (row.getAttribute('data-text') || '').indexOf(q) !== -1;
          row.style.display = hit ? '' : 'none';
          row.classList.toggle('is-match', !!q && hit);
          if (hit) visible++;
        });
        g.style.display = visible ? '' : 'none';
        any += visible;
      });
      var empty = document.getElementById('kbEmpty');
      if (empty) empty.style.display = any ? 'none' : 'block';
    });
  }

  /* ---------- 打开窗口 ---------- */
  function openKB() {
    var content = document.getElementById('modalContent');
    if (!content || typeof openModal !== 'function') return;
    var groups = buildGroups();
    content.innerHTML =
      '<div class="kb-dialog">' +
      '  <div class="kb-head"><h2>键盘快捷键</h2><span class="kb-hint">按名称或按键搜索</span></div>' +
      '  <div class="kb-search-wrap">' +
      '    <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
      '    <input type="text" id="' + FILTER_ID + '" placeholder="搜索快捷键" autocomplete="off" spellcheck="false">' +
      '  </div>' +
      '  <div class="kb-body" id="' + BODY_ID + '">' + renderBody(groups) + '</div>' +
      '</div>';
    var m0 = document.getElementById('modal');
    if (m0) m0.classList.add('kb-modal'); // 快捷键窗口专属居中态（须在 openModal 前打标）
    openModal();
    // 渲染后聚焦搜索框
    setTimeout(function () {
      var i = document.getElementById(FILTER_ID);
      if (i) i.focus();
    }, 30);
    bindFilter();
  }

  /* ---------- 移动端导航抽屉切换（桌面常驻，不强行折叠以免破坏布局） ---------- */
  function toggleNavDrawer() {
    if (window.innerWidth <= 768) {
      var t = document.getElementById('menuToggle');
      if (t) t.click();
    } else {
      // 桌面端：轻提示该快捷键用于移动端抽屉（不改变桌面布局，零错位风险）
      if (typeof toast === 'function') toast('桌面端导航常驻；Ctrl+B 用于移动端收起/展开抽屉');
    }
  }

  /* ---------- 全局快捷键（捕获阶段；不拦截浏览器默认） ---------- */
  function isTyping(t) {
    if (!t) return false;
    var tag = t.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || !!t.isContentEditable;
  }

  document.addEventListener('keydown', function (e) {
    // 1) Ctrl/Cmd + /：任何焦点下打开快捷键窗（浏览器无默认占用）
    if ((e.ctrlKey || e.metaKey) && (e.key === '/' || e.keyCode === 191)) {
      e.preventDefault();
      openKB();
      return;
    }
    if (isTyping(e.target)) return; // 输入态不触发其余导航快捷键

    // 2) 单按 ?（Shift+/）打开
    if (e.key === '?' && !e.ctrlKey && !e.altKey && !e.metaKey) {
      e.preventDefault();
      openKB();
      return;
    }
    // 3) Alt + 数字：跳转到对应侧栏页面
    if (e.altKey && !e.ctrlKey && !e.metaKey) {
      var idx = null;
      if (/^[1-9]$/.test(e.key)) idx = parseInt(e.key, 10) - 1;
      else if (e.key === '0') idx = 9;
      if (idx !== null) {
        var items = navItems();
        if (items[idx]) {
          e.preventDefault();
          if (typeof closeModal === 'function' && document.getElementById('modal') &&
              document.getElementById('modal').classList.contains('open')) closeModal();
          if (typeof navigateTo === 'function') navigateTo(items[idx].page);
        }
      } else if (e.key === 'ArrowLeft') {
        // Alt+← 返回上一页（仅在无输入时）
        if (typeof goBack === 'function') { e.preventDefault(); goBack(); }
      }
      return;
    }
    // 4) Ctrl/Cmd + B：导航抽屉（移动端）
    if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
      e.preventDefault();
      toggleNavDrawer();
    }
  }, true);

  /* ---------- 侧栏入口（本脚本晚于 app.js 加载，覆盖其统一 onclick） ---------- */
  function bindEntry() {
    var entry = document.getElementById('kbShortcutsEntry');
    if (entry) entry.onclick = function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      openKB();
    };
    window.openKeyboardShortcuts = openKB;
  }

  /* ---------- 包装全局模态开关：任何路径关闭时清理专属居中态，避免污染其它详情弹窗 ---------- */
  function wrapModal() {
    if (window.__kbWrapped) return;
    var origOpen = window.openModal, origClose = window.closeModal;
    window.openModal = function () { return origOpen ? origOpen.apply(this, arguments) : undefined; };
    window.closeModal = function () {
      var m = document.getElementById('modal');
      if (m) m.classList.remove('kb-modal');
      return origClose ? origClose.apply(this, arguments) : undefined;
    };
    window.__kbWrapped = true;
  }

  function boot() {
    injectStyle();
    wrapModal();
    bindEntry();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  console.log('[keyboard_shortcuts] 键盘快捷键窗口已加载（Ctrl+/ 唤起）');
})();
