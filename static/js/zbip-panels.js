/* ============================================================
 * ZBIP Workspace Panels  v1.0.0
 * 底部只读终端 + 右侧文件树 + 视图菜单（Codex 式工程面板）
 * 仅在 ZBMP 工作台内挂载；纯增量；终端只走后端只读白名单，不本地执行任何命令。
 * ============================================================ */
(function () {
  'use strict';
  var I = {
    term: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/></svg>',
    tree: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
    folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
    file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>',
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    chev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>',
    menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
  };
  var BT = String.fromCharCode(96); // 反引号，避免源码歧义
  var state = { termOpen: false, filesOpen: false, sessions: [mkSession('终端 1')], active: 0 };
  var view, termOut, termInput, treeEl, filesFoot, menuEl;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function mkSession(n) { return { name: n, lines: [{ t: 'sys', x: '只读 Web 终端已就绪，输入 help 查看可用命令；写操作请在本机终端执行。' }] }; }
  function fmtSize(n) { if (n == null) return ''; if (n < 1024) return n + ' B'; if (n < 1048576) return (n / 1024).toFixed(1) + ' KB'; return (n / 1048576).toFixed(1) + ' MB'; }
  function cur() { return state.sessions[state.active]; }

  function boot() {
    view = document.getElementById('zbmpView');
    if (!view || view.__zbPanels) return;
    view.__zbPanels = true;
    inject();
    bindGlobal();
    loadTree('');
  }

  function inject() {
    var bar = document.createElement('div');
    bar.className = 'zb-panelbar';
    bar.innerHTML =
      '<button class="zb-pb-btn" id="zbPbTerm" title="打开终端 (Ctrl+' + BT + ')">' + I.term + '<span class="lbl">终端</span></button>' +
      '<button class="zb-pb-btn" id="zbPbFiles" title="切换文件树 (Ctrl+Shift+E)">' + I.tree + '<span class="lbl">文件</span></button>' +
      '<button class="zb-pb-btn" id="zbPbView" title="视图菜单">' + I.menu + '<span class="lbl">视图</span></button>' +
      '<div class="zb-viewmenu" id="zbViewMenu">' +
        '<button class="zb-vm-item" data-act="termPanel"><span>切换底部面板</span><span class="kbd">Ctrl+J</span></button>' +
        '<button class="zb-vm-item" data-act="openTerm"><span>打开终端</span><span class="kbd">Ctrl+' + BT + '</span></button>' +
        '<div class="zb-vm-sep"></div>' +
        '<button class="zb-vm-item" data-act="files"><span>切换文件树</span><span class="kbd">Ctrl+Shift+E</span></button>' +
      '</div>';
    view.appendChild(bar);
    menuEl = bar.querySelector('#zbViewMenu');

    var term = document.createElement('div');
    term.className = 'zb-panel zb-term';
    term.id = 'zbTerm';
    term.innerHTML =
      '<div class="zb-term-tabs" id="zbTermTabs"></div>' +
      '<div class="zb-term-body" id="zbTermOut"></div>' +
      '<div class="zb-term-inputrow"><span class="zb-term-prompt">PS&gt;</span>' +
      '<input class="zb-term-input" id="zbTermInput" spellcheck="false" autocomplete="off" placeholder="输入只读命令，help 查看帮助">' +
      '<span class="zb-term-hint">只读 · Alt+数字切标签</span></div>';
    view.appendChild(term);
    termOut = term.querySelector('#zbTermOut');
    termInput = term.querySelector('#zbTermInput');

    var files = document.createElement('div');
    files.className = 'zb-panel zb-files';
    files.id = 'zbFiles';
    files.innerHTML =
      '<div class="zb-panel-head"><span class="zb-panel-title">' + I.folder + '打开文件</span><span class="zb-panel-spacer"></span>' +
      '<button class="zb-panel-iconbtn" id="zbFilesClose" title="关闭面板">' + I.x + '</button></div>' +
      '<div class="zb-files-cwd" id="zbFilesCwd">项目根加载中…</div>' +
      '<div class="zb-files-search"><input id="zbTreeFilter" placeholder="筛选当前层…"></div>' +
      '<div class="zb-tree" id="zbTree"></div>' +
      '<div class="zb-files-foot"><span class="dot"></span><span id="zbFilesFoot">—</span></div>';
    view.appendChild(files);
    treeEl = files.querySelector('#zbTree');
    filesFoot = files.querySelector('#zbFilesFoot');

    bar.querySelector('#zbPbTerm').addEventListener('click', function () { openTerm(); });
    bar.querySelector('#zbPbFiles').addEventListener('click', function () { toggleFiles(); });
    bar.querySelector('#zbPbView').addEventListener('click', function (e) { e.stopPropagation(); menuEl.classList.toggle('show'); });
    bar.querySelectorAll('.zb-vm-item').forEach(function (b) {
      b.addEventListener('click', function () {
        var a = b.dataset.act; menuEl.classList.remove('show');
        if (a === 'termPanel') toggleTerm();
        else if (a === 'openTerm') openTerm();
        else if (a === 'files') toggleFiles();
      });
    });
    files.querySelector('#zbFilesClose').addEventListener('click', function () { toggleFiles(false); });
    term.querySelector('#zbTermTabs').addEventListener('click', onTabsClick);
    termInput.addEventListener('keydown', onTermKey);
    files.querySelector('#zbTreeFilter').addEventListener('input', function (e) {
      var q = e.target.value.trim().toLowerCase();
      treeEl.querySelectorAll(':scope > .zb-tree-row').forEach(function (r) {
        r.style.display = (!q || r.dataset.name.indexOf(q) >= 0) ? '' : 'none';
      });
    });
    renderTabs(); renderLines();
  }

  /* ---------- 终端 ---------- */
  function toggleTerm(force) { state.termOpen = (typeof force === 'boolean') ? force : !state.termOpen; syncTerm(); }
  function openTerm() { if (!state.termOpen) state.termOpen = true; syncTerm(); setTimeout(function () { termInput.focus(); }, 220); }
  function syncTerm() {
    document.getElementById('zbTerm').classList.toggle('open', state.termOpen);
    view.classList.toggle('term-open', state.termOpen);
    document.getElementById('zbPbTerm').classList.toggle('is-active', state.termOpen);
    if (state.termOpen) setTimeout(function () { termInput.focus(); }, 260);
  }
  function renderTabs() {
    var wrap = document.getElementById('zbTermTabs'); if (!wrap) return;
    var h = '';
    state.sessions.forEach(function (s, i) {
      h += '<span class="zb-term-tab' + (i === state.active ? ' is-active' : '') + '" data-i="' + i + '">' + esc(s.name) +
        (state.sessions.length > 1 ? '<span class="x" data-x="' + i + '">' + I.x + '</span>' : '') + '</span>';
    });
    h += '<button class="zb-term-add" id="zbTermAdd" title="新建终端标签">' + I.plus + '</button>';
    wrap.innerHTML = h;
  }
  function onTabsClick(e) {
    var add = e.target.closest('#zbTermAdd');
    if (add) { state.sessions.push(mkSession('终端 ' + (state.sessions.length + 1))); state.active = state.sessions.length - 1; renderTabs(); renderLines(); return; }
    var x = e.target.closest('[data-x]');
    if (x) { e.stopPropagation(); var xi = +x.dataset.x; state.sessions.splice(xi, 1); if (state.active >= state.sessions.length) state.active = state.sessions.length - 1; renderTabs(); renderLines(); return; }
    var tab = e.target.closest('.zb-term-tab');
    if (tab) { state.active = +tab.dataset.i; renderTabs(); renderLines(); }
  }
  function renderLines() {
    if (!termOut) return;
    var s = cur();
    termOut.innerHTML = s.lines.map(function (l) { return '<p class="zb-term-line ' + l.t + '">' + esc(l.x) + '</p>'; }).join('');
    termOut.scrollTop = termOut.scrollHeight;
  }
  function onTermKey(e) {
    if (e.altKey && /^[1-9]$/.test(e.key)) { var i = +e.key - 1; if (state.sessions[i]) { state.active = i; renderTabs(); renderLines(); } return; }
    if (e.key !== 'Enter') return;
    var cmd = termInput.value.trim(); termInput.value = '';
    if (!cmd) return;
    var s = cur();
    s.lines.push({ t: 'cmd', x: cmd });
    if (/^clear$/i.test(cmd)) { s.lines = [{ t: 'sys', x: '已清屏。' }]; renderLines(); return; }
    renderLines();
    fetch('/api/workspace/term', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', body: JSON.stringify({ cmd: cmd }) })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.clear) { s.lines = []; return renderLines(); }
        if (j.output) s.lines.push({ t: j.ok ? 'out' : (j.blocked ? 'block' : 'err'), x: j.output });
        else if (j.error) s.lines.push({ t: j.blocked ? 'block' : 'err', x: j.error });
        renderLines();
      })
      .catch(function (err) { s.lines.push({ t: 'err', x: '请求失败：' + err.message }); renderLines(); });
  }

  /* ---------- 文件树 ---------- */
  function toggleFiles(force) { state.filesOpen = (typeof force === 'boolean') ? force : !state.filesOpen; syncFiles(); }
  function syncFiles() {
    document.getElementById('zbFiles').classList.toggle('open', state.filesOpen);
    view.classList.toggle('files-open', state.filesOpen);
    document.getElementById('zbPbFiles').classList.toggle('is-active', state.filesOpen);
  }
  function loadTree(path) {
    fetch('/api/workspace/file-tree?path=' + encodeURIComponent(path), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { treeEl.innerHTML = '<div class="zb-tree-empty">无法读取目录<br>' + esc(j.error || '') + '</div>'; return; }
        if (!path) document.getElementById('zbFilesCwd').textContent = j.root + ' / （项目根，已过滤 .env、库、凭证、profile 等敏感项）';
        if (!path) filesFoot.textContent = '当前层：目录 ' + j.counts.dirs + ' · 文件 ' + j.counts.files + ' · 共 ' + j.counts.total + ' 项';
        treeEl.innerHTML = '';
        j.items.forEach(function (it) { treeEl.appendChild(rowNode(it)); });
        if (!j.items.length) treeEl.innerHTML = '<div class="zb-tree-empty">此目录为空</div>';
      })
      .catch(function (err) { treeEl.innerHTML = '<div class="zb-tree-empty">加载失败<br>' + esc(err.message) + '</div>'; });
  }
  function rowNode(it) {
    var row = document.createElement('div');
    row.className = 'zb-tree-row ' + (it.type === 'dir' ? 'is-dir' : 'is-file');
    row.dataset.name = it.name.toLowerCase();
    row.innerHTML =
      (it.type === 'dir' ? '<span class="chev">' + I.chev + '</span>' : '<span class="chev"></span>') +
      '<span class="ico">' + (it.type === 'dir' ? I.folder : I.file) + '</span>' +
      '<span class="nm">' + esc(it.name) + '</span>' +
      '<span class="sz">' + (it.type === 'file' ? fmtSize(it.size) : '') + '</span>';
    if (it.type === 'dir') {
      var child = document.createElement('div');
      child.className = 'zb-tree-children';
      child.style.paddingLeft = '14px';
      row.parentNode;
      row.addEventListener('click', function () {
        var open = child.classList.toggle('open');
        row.querySelector('.chev').classList.toggle('open', open);
        if (open && !child.dataset.loaded) {
          child.dataset.loaded = '1';
          child.innerHTML = '<div class="zb-tree-empty">加载中…</div>';
          fetch('/api/workspace/file-tree?path=' + encodeURIComponent(it.rel), { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (j2) {
              child.innerHTML = '';
              (j2.items || []).forEach(function (c) { child.appendChild(rowNode(c)); });
              if (!(j2.items || []).length) child.innerHTML = '<div class="zb-tree-empty">空目录</div>';
            })
            .catch(function (e) { child.innerHTML = '<div class="zb-tree-empty">' + esc(e.message) + '</div>'; });
        }
      });
      var wrap = document.createElement('div');
      wrap.appendChild(row); wrap.appendChild(child);
      return wrap;
    }
    return row;
  }

  /* ---------- 全局快捷键 / 外部点击关菜单 ---------- */
  function bindGlobal() {
    document.addEventListener('keydown', function (e) {
      if ((document.body.dataset.workspace || '') !== 'zbmp') return;
      var k = e.key;
      if (e.ctrlKey && (k === BT || k === 'j' || k === 'J')) { e.preventDefault(); if (k === BT) openTerm(); else toggleTerm(); }
      else if (e.ctrlKey && e.shiftKey && (k === 'E' || k === 'e')) { e.preventDefault(); toggleFiles(); }
      else if (k === 'Escape' && menuEl) menuEl.classList.remove('show');
    });
    document.addEventListener('click', function (e) {
      if (menuEl && !e.target.closest('.zb-panelbar')) menuEl.classList.remove('show');
    });
  }

  // #zbmpView 由 workbench 注入/切换，轮询挂载；视图被重建则重新挂
  var timer = setInterval(function () {
    var v = document.getElementById('zbmpView');
    if (v && !v.__zbPanels) { boot(); }
    else if (!v && view && view.__zbPanels) { view.__zbPanels = false; }
  }, 400);
})();
