/* =============================================================================
 * ZBIP App Shell runtime v1.0（Staging only）
 * 运行时增强，不修改源 HTML：加 body class、侧栏分组、注入工作区切换/搜索/账户、
 * Home 居中提问页、ZBMP 密钥门。所有业务路由/数据仍走原有逻辑，本层只做外壳与视图切换。
 * 回滚 = 移除本 script。
 * ========================================================================== */
(function () {
  'use strict';
  if (window.__zbShellLoaded) return; window.__zbShellLoaded = true;

  var SVG = {
    chevron: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>',
    chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
    mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="22 6 12 13 2 6"/></svg>',
    lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    send: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>',
    refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><polyline points="21 3 21 9 15 9"/></svg>',
    sparkle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.7 1.8L21.5 17.5l-1.8.7L19 20l-.7-1.8L16.5 17.5l1.8-.7z"/></svg>',
    doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/></svg>'
  };

  // 21 项 → 分组（data-page；话题监测是 a#id）
  var GROUPS = [
    { title: '总览', items: ['overview'], rename: { overview: '舆情驾驶舱' } },
    { title: '监测', items: ['monitor', 'alerts', 'negative', 'notes', 'official', 'topic-campaign', 'topics'] },
    { title: '分析', items: ['analysis', 'events', 'event-graph', 'calendar'] },
    { title: '品牌资产', items: ['brands', 'swire', 'cases', 'case-analysis', 'knowledge-base', 'brand-report', 'app-evidence'] },
    { title: '产出', items: ['reports'] },
    { title: '系统', items: ['settings'] }
  ];

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function closeAllPops() { document.querySelectorAll('.zb-pop.show').forEach(function (p) { p.classList.remove('show'); }); document.querySelectorAll('.zb-ws-switch.open').forEach(function (b) { b.classList.remove('open'); }); }

  function boot() {
    var sidebar = document.querySelector('.sidebar');
    var nav = sidebar && sidebar.querySelector('.side-nav');
    if (!sidebar || !nav) return;
    document.body.classList.add('zb-shell-on');
    var userNavigated = false; // 仅真实用户导航才收起 Home，屏蔽主 app 初始化的程序化 click
    linearizeTopbar();
    normalizeNavLabels();

    // 规范个别旧导航文案（只改展示文本，不动源 DOM/路由；TreeWalker 兼容翻译包裹层）
    function normalizeNavLabels() {
      var tc = document.querySelector('#topic-campaign-entry-v573');
      if (!tc) return;
      var w = document.createTreeWalker(tc, NodeFilter.SHOW_TEXT), n;
      while ((n = w.nextNode())) { if (/话题监测端口/.test(n.nodeValue)) n.nodeValue = n.nodeValue.replace('话题监测端口', '话题监测'); }
    }

    // 顶栏 emoji 图标 → 线性 SVG（源 HTML 不改，仅外壳层替换，可回滚）
    function linearizeTopbar() {
      var map = { commandPaletteBtn: 'search', alertBellBtn: 'bell', refreshBtn: 'refresh', reviewBtn: 'sparkle', reportBtn: 'doc' };
      Object.keys(map).forEach(function (id) {
        var b = document.getElementById(id), ic = b && b.querySelector('.svgicon');
        if (ic && SVG[map[id]]) ic.innerHTML = SVG[map[id]];
      });
    }

    /* ---- A. 导航分组（运行时包裹，不改源 DOM 顺序之外的结构） ---- */
    var itemMap = {};
    nav.querySelectorAll('.side-item').forEach(function (it) {
      var key = it.getAttribute('data-page') || (it.id || '').replace('topic-campaign-entry-v573', 'topic-campaign');
      if (it.id === 'topic-campaign-entry-v573') key = 'topic-campaign';
      itemMap[key] = it;
    });
    GROUPS.forEach(function (g) {
      var group = el('div', 'zb-nav-group');
      group.appendChild(el('div', 'zb-nav-title', g.title));
      g.items.forEach(function (key) {
        var node = itemMap[key];
        if (!node) return;
        if (g.rename && g.rename[key]) { var lab = node.querySelector('span:last-of-type'); if (lab) lab.textContent = g.rename[key]; }
        group.appendChild(node);
      });
      nav.appendChild(group);
    });

    /* ---- B. 顶部：工作区切换器 + 搜索 + 通知 ---- */
    var bar = el('div', 'zb-workspace-bar');
    var wsBtn = el('button', 'zb-ws-switch', '<span class="zb-ws-name">CTH-POMS</span>' + SVG.chevron);
    wsBtn.type = 'button'; wsBtn.title = '切换产品工作区';
    var searchWrap = el('div', 'zb-search', SVG.search + '<input type="text" placeholder="搜索功能…" aria-label="搜索功能">');
    var bell = el('button', 'zb-icon-btn', SVG.bell); bell.type = 'button'; bell.title = '通知';
    var spacer = el('div'); spacer.style.flex = '1';
    // 第一行：工作区切换器 + 通知；第二行：整宽搜索框（避免侧栏内挤压换行）
    bar.appendChild(wsBtn); bar.appendChild(spacer); bar.appendChild(bell);
    sidebar.insertBefore(bar, nav);
    sidebar.insertBefore(searchWrap, nav);

    searchWrap.querySelector('input').addEventListener('input', function (e) {
      var q = e.target.value.trim().toLowerCase();
      nav.querySelectorAll('.side-item').forEach(function (it) {
        var t = (it.innerText || '').toLowerCase();
        var hit = !q || t.indexOf(q) >= 0;
        it.classList.toggle('hidden-by-search', !hit);
      });
    });

    /* ---- C. 底部：账户槽 ---- */
    var accSlot = el('div', 'zb-account-slot');
    var accBtn = el('button', 'zb-account-btn',
      '<span class="zb-avatar">Z</span><span class="zb-account-meta"><b>Zachary</b><small>本地账户 · CTH-POMS</small></span>' + SVG.chevron);
    accBtn.type = 'button';
    accSlot.appendChild(accBtn); sidebar.appendChild(accSlot);

    /* ---- D. 浮层：工作区切换 ---- */
    var wsPop = el('div', 'zb-pop');
    wsPop.innerHTML =
      popItem('cth', SVG.grid, 'CTH-POMS', '广州太古汇舆情监测 · 生产', '<span class="trail zb-check">✓</span>') +
      popItem('zbmp', SVG.lock, 'ZBMP', 'Z-Brand 品牌监测 · 需密钥', '<span class="trail">密钥</span>');
    document.body.appendChild(wsPop);
    function popItem(key, ico, name, desc, trail) {
      return '<button class="zb-pop-item" data-ws="' + key + '"><span class="ico">' + ico + '</span><span class="txt"><b>' + name + '</b><small>' + desc + '</small></span>' + trail + '</button>';
    }
    wsBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = wsPop.classList.contains('show'); closeAllPops();
      if (!open) { anchorBelow(wsBtn, wsPop); wsPop.classList.add('show'); wsBtn.classList.add('open'); }
    });
    wsPop.addEventListener('click', function (e) {
      var opt = e.target.closest('.zb-pop-item'); if (!opt) return;
      var ws = opt.getAttribute('data-ws');
      if (ws === 'cth') { setWorkspace('CTH-POMS'); closeAllPops(); }
      else { closeAllPops(); enterZbmp(); }
    });

    /* ---- E. 浮层：账户 ---- */
    var accPop = el('div', 'zb-pop');
    accPop.innerHTML =
      popRow('mail', SVG.mail, '邮箱通知', '推送邮箱配置') +
      popRow('zachary', SVG.chat, 'Zachary 助手', '打开 AI 分析') +
      '<div class="zb-pop-sep"></div>' +
      popRow('settings', SVG.gear, '设置', '', 'Ctrl+,') +
      popRow('logout', SVG.logout, '退出登录', '');
    document.body.appendChild(accPop);
    function popRow(key, ico, name, sub, trail) {
      return '<button class="zb-pop-item" data-act="' + key + '"><span class="ico">' + ico + '</span><span class="txt"><b>' + name + '</b>' + (sub ? '<small>' + sub + '</small>' : '') + '</span>' + (trail ? '<span class="trail">' + trail + '</span>' : '') + '</button>';
    }
    accBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = accPop.classList.contains('show'); closeAllPops();
      if (!open) { anchorAbove(accBtn, accPop); accPop.classList.add('show'); }
    });
    accPop.addEventListener('click', function (e) {
      var row = e.target.closest('.zb-pop-item'); if (!row) return;
      var act = row.getAttribute('data-act'); closeAllPops();
      if (act === 'settings') { gotoPage('settings'); }
      else if (act === 'zachary') { openZachary(); }
      else if (act === 'mail') { gotoPage('settings'); }
      else if (act === 'logout') { toast('当前为本地单机账户，退出登录待接入账号体系'); }
    });
    document.addEventListener('click', function () { closeAllPops(); });

    /* ---- F. ZBMP 密钥门 ---- */
    var mask = el('div', 'zb-modal-mask');
    mask.innerHTML =
      '<div class="zb-modal" role="dialog" aria-modal="true">' +
      '<h3>进入 ZBMP 工作区</h3>' +
      '<p>ZBMP 为受限工作区，需要管理员签发的访问密钥；校验通过后本会话获得 12 小时授权，登出或过期后需重新验证。</p>' +
      '<div class="zb-field"><input type="password" id="zbKeyInput" placeholder="请输入 ZBMP 访问密钥" autocomplete="off"></div>' +
      '<div class="zb-key-err" id="zbKeyErr"></div>' +
      '<div class="zb-modal-actions">' +
      '<button class="zb-btn-ghost" id="zbKeyCancel" type="button">取消</button>' +
      '<button class="zb-btn-primary" id="zbKeyOk" type="button">解锁进入</button></div></div>';
    document.body.appendChild(mask);
    function openKeyGate() { mask.classList.add('show'); setTimeout(function () { var i = document.getElementById('zbKeyInput'); if (i) i.focus(); }, 60); }
    // 进入 ZBMP：先问后端当前会话是否已授权，已授权直接进，否则弹密钥门
    function enterZbmp() {
      fetch('/v4/auth/workspace/status', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j && j.workspaces && j.workspaces['ZBMP']) { try { sessionStorage.setItem('zbmp_unlocked', '1'); } catch (e) {} setWorkspace('ZBMP'); toast('已进入 ZBMP 工作区（会话授权有效）'); }
          else openKeyGate();
        })
        .catch(function () { openKeyGate(); });
    }
    mask.addEventListener('click', function (e) { if (e.target === mask) mask.classList.remove('show'); });
    document.getElementById('zbKeyCancel').addEventListener('click', function () { mask.classList.remove('show'); });
    document.getElementById('zbKeyOk').addEventListener('click', submitKey);
    document.getElementById('zbKeyInput').addEventListener('keydown', function (e) { if (e.key === 'Enter') submitKey(); });
    function submitKey() {
      var v = (document.getElementById('zbKeyInput').value || '').trim();
      var err = document.getElementById('zbKeyErr');
      var okBtn = document.getElementById('zbKeyOk');
      if (!v) { err.textContent = '请输入密钥'; return; }
      err.textContent = ''; okBtn.disabled = true; okBtn.textContent = '验证中…';
      fetch('/v4/auth/workspace/unlock', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace: 'ZBMP', key: v })
      }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (res.ok && res.j.success) {
            try { sessionStorage.setItem('zbmp_unlocked', '1'); } catch (e) {}
            document.getElementById('zbKeyInput').value = '';
            mask.classList.remove('show'); setWorkspace('ZBMP');
            toast('ZBMP 工作区已解锁，本会话授权 12 小时');
          } else { err.textContent = (res.j && res.j.error) || '密钥无效'; }
        })
        .catch(function () { err.textContent = '网络错误，暂时无法校验密钥'; })
        .finally(function () { okBtn.disabled = false; okBtn.textContent = '解锁进入'; });
    }
    function setWorkspace(name) {
      wsBtn.querySelector('.zb-ws-name').textContent = name;
      var meta = accBtn.querySelector('.zb-account-meta small'); if (meta) meta.textContent = '本地账户 · ' + name;
      // 通知 workbench 等外层做视图切换（CTH/ZBMP 双工作区）
      window.dispatchEvent(new CustomEvent('zb:workspace', { detail: { name: name } }));
    }

    /* ---- G. Home 干净居中提问页 ---- */
    var content = document.querySelector('.content');
    if (content) {
      content.style.position = 'relative';
      var home = el('div'); home.id = 'zbHome';
      home.innerHTML =
        '<div class="zb-home-inner">' +
        '<h1 class="zb-home-title">你今天想知道什么？</h1>' +
        '<div class="zb-ask">' +
        '<textarea id="zbHomeInput" rows="1" placeholder="问 Zachary：例如 今天太古汇有哪些高风险舆情？"></textarea>' +
        '<div class="zb-ask-bar"><span class="zb-ask-model">Zachary · 本地 AI（Ollama）</span><span class="spacer"></span>' +
        '<button class="zb-send" id="zbHomeSend" type="button" title="发送">' + SVG.send + '</button></div></div>' +
        '<div class="zb-chips">' +
        chip('cockpit', SVG.grid, '进入舆情驾驶舱') +
        chip('risk', SVG.bell, '今日高风险') +
        chip('event', SVG.sparkle, '最新事件') +
        chip('report', SVG.gear, '生成日报') +
        '</div>' +
        '<div class="zb-home-sub">Z-Brand Core · CTH-POMS 生产工作区 · 数据来自本地采集与分析管线</div>' +
        '</div>';
      content.insertBefore(home, content.firstChild);
      requestAnimationFrame(function () { if (!userNavigated) home.classList.add('show'); });
      // 兜底：主 app 初始化时会程序化 .click() 默认页（isTrusted=false），延迟两次确保 Home 不被竞态带走
      window.addEventListener('load', function () { if (!userNavigated) requestAnimationFrame(showHome); });
      setTimeout(function () { if (!userNavigated) showHome(); }, 450);

      function chip(key, ico, txt) { return '<button class="zb-chip" data-q="' + key + '" type="button">' + ico + txt + '</button>'; }
      var ta = document.getElementById('zbHomeInput');
      function autosize() { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'; }
      ta.addEventListener('input', autosize);
      function ask() {
        var v = (ta.value || '').trim();
        if (v) { var zi = document.getElementById('zacharyInput'); if (zi) zi.value = v; if (typeof sendZacharyMsg === 'function') sendZacharyMsg(); openZachary(); }
        else { openZachary(); }
      }
      document.getElementById('zbHomeSend').addEventListener('click', ask);
      ta.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); } });
      home.addEventListener('click', function (e) {
        var c = e.target.closest('.zb-chip'); if (!c) return;
        var q = c.getAttribute('data-q'); userNavigated = true; hideHome();
        if (q === 'cockpit') gotoPage('overview');
        else if (q === 'risk') gotoPage('alerts');
        else if (q === 'event') gotoPage('events');
        else if (q === 'report') gotoPage('reports');
      });
    }
    function hideHome() { var h = document.getElementById('zbHome'); if (h) h.classList.remove('show'); }
    function showHome() { var h = document.getElementById('zbHome'); if (h) h.classList.add('show'); }

    // 点任意侧栏功能 → 进入具体页，收起 Home（只认真实用户点击，屏蔽初始化程序 click）
    nav.addEventListener('click', function (e) {
      var it = e.target.closest('.side-item'); if (!it) return;
      if (!e.isTrusted) return;
      if (it.getAttribute('data-page')) { userNavigated = true; hideHome(); }
    });
    // 点工作区名 → 回 Home
    wsBtn.addEventListener('dblclick', showHome);

    /* ---- H. 移动端：现有汉堡按钮驱动抽屉 ---- */
    var menu = document.getElementById('menuToggle');
    if (menu) menu.addEventListener('click', function () { document.body.classList.toggle('zb-nav-open'); });

    /* ---- 工具 ---- */
    function gotoPage(page) {
      hideHome();
      var node = itemMap[page];
      if (node) node.click();
      else { var s = document.querySelector('.side-item[data-page="' + page + '"]'); if (s) s.click(); }
    }
    function openZachary() {
      var m = document.getElementById('zacharyChatModal');
      if (!m) return;
      if (getComputedStyle(m).display === 'none' && typeof window.toggleZacharyChat === 'function') window.toggleZacharyChat();
      else m.style.display = 'flex';
    }
    function anchorBelow(anchor, pop) {
      var r = anchor.getBoundingClientRect(); pop.style.left = r.left + 'px'; pop.style.top = (r.bottom + 6) + 'px';
    }
    function anchorAbove(anchor, pop) {
      var r = anchor.getBoundingClientRect(); pop.style.left = r.left + 'px';
      var h = pop.offsetHeight; // pop 已在 DOM（opacity:0），可直接量高，不闪帧
      pop.style.top = Math.max(8, r.top - h - 6) + 'px';
    }
    var toastTimer;
    function toast(msg) {
      var t = document.querySelector('.zb-tip.global');
      if (!t) { t = el('div', 'zb-tip global'); document.body.appendChild(t); }
      t.textContent = msg; t.classList.add('show'); clearTimeout(toastTimer);
      toastTimer = setTimeout(function () { t.classList.remove('show'); }, 2600);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
