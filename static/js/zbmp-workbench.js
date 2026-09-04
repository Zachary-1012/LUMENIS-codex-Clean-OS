/* =============================================================================
 * ZBMP Workbench runtime v1.0（Staging only）
 * 双工作区视图：在已确认外壳内新增 ZBMP 独立侧栏 + 主视图与内部路由。
 * 不复制 Core：模块数据下一轮接入现有 API；本轮先立交互架构，未接入模块用诚实空状态占位。
 * 依赖 zbip-shell（工作区切换器）；回滚 = 移除本 script 与对应 css。
 * ========================================================================== */
(function () {
  'use strict';
  if (window.__zbWbLoaded) return; window.__zbWbLoaded = true;

  var I = {
    back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>',
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    chev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
    grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    crosshair: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>',
    book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    target: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/></svg>',
    zap: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    share: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/><line x1="15.4" y1="6.5" x2="8.6" y2="10.5"/></svg>',
    sparkle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/></svg>',
    doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/></svg>',
    gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    plug: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2v6M15 2v6"/><path d="M6 8h12v3a6 6 0 0 1-12 0z"/><line x1="12" y1="17" x2="12" y2="22"/></svg>',
    palette: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="8" cy="10" r="1.2" fill="currentColor"/><circle cx="12" cy="7.5" r="1.2" fill="currentColor"/><circle cx="16" cy="10" r="1.2" fill="currentColor"/></svg>',
    shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    key: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.6 7.6a5 5 0 1 1-7.07 7.07 5 5 0 0 1 7.07-7.07zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>',
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16"/><circle cx="12" cy="8" r=".6" fill="currentColor"/></svg>',
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>'
  };

  // ZBMP 信息架构（6 分组）。status: core=Core 已具备待接入 / planned=规划中
  var GROUPS = [
    { title: '概览', items: [
      { k: 'home', t: '工作台', i: 'grid', hideInNav: true } ] },
    { title: '品牌', items: [
      { k: 'brands', t: '品牌资产', i: 'layers', s: 'live', d: '品牌画像、资产沉淀与健康度，接入 Core 品牌库。' },
      { k: 'compete', t: '竞品监控', i: 'crosshair', s: 'planned', d: '竞品声量与对比分析，规划中。' },
      { k: 'cases', t: '案例库', i: 'book', s: 'core', d: '公关/传播案例库，接入 Core 案例能力。' } ] },
    { title: '监测', items: [
      { k: 'content', t: '内容监测', i: 'file', s: 'live', d: '跨平台内容流与主体过滤，接入 Core 采集管线。' },
      { k: 'campaign', t: '话题战役', i: 'target', s: 'live', d: '15 周年等专题/战役监测，接入 Core 话题能力。' } ] },
    { title: '洞察', items: [
      { k: 'events', t: '事件中心', i: 'zap', s: 'live', d: '营销/传播/舆情事件与生命周期，接入 Core 事件引擎。' },
      { k: 'graph', t: '事件关系', i: 'share', s: 'live', d: '触发/衍生/继发/并行关系图谱，接入 Core 关系数据。' },
      { k: 'ai-eval', t: 'AI 评估', i: 'sparkle', s: 'core', d: 'Ollama 本地 AI 增强分析（仅增强层，不决定系统事实）。' } ] },
    { title: '产出', items: [
      { k: 'reports', t: '报告中心', i: 'doc', s: 'live', d: '日/周/月报与专题导出，接入 Core 报告能力。' } ] },
    { title: '系统', items: [
      { k: 'connectors', t: '连接器', i: 'plug', s: 'live', d: '平台采集适配器与状态。' },
      { k: 'settings', t: '工作区设置', i: 'gear', s: 'live', d: '外观、安全密钥与关于。' } ] }
  ];
  var MOD = {}; GROUPS.forEach(function (g) { g.items.forEach(function (m) { MOD[m.k] = m; }); });

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function dot(kind, label) { return '<span class="zb-status"><span class="zb-dot ' + kind + '"></span>' + label + '</span>'; }

  function boot() {
    var sidebar = document.querySelector('.sidebar');
    var content = document.querySelector('.content');
    if (!sidebar || !content) return;

    /* ---- 注入 ZBMP 侧栏导航（与 CTH .side-nav 共存，按 data-workspace 显隐） ---- */
    var nav = el('nav', 'zbmp-nav');
    GROUPS.forEach(function (g) {
      var grp = el('div', 'zb-nav-group'); grp.appendChild(el('div', 'zb-nav-title', g.title));
      g.items.forEach(function (m) {
        if (m.hideInNav) return;
        var b = el('button', 'zbmp-item', '<span class="ni">' + I[m.i] + '</span><span class="nt">' + m.t + '</span>' +
          (m.s === 'planned' ? '<span class="nb">规划</span>' : ''));
        b.type = 'button'; b.setAttribute('data-route', m.k);
        b.addEventListener('click', function () { go(m.k); });
        grp.appendChild(b);
      });
      nav.appendChild(grp);
    });
    var sideNav = sidebar.querySelector('.side-nav');
    sidebar.insertBefore(nav, sideNav ? sideNav.nextSibling : null);

    /* ---- 注入 ZBMP 主视图 ---- */
    var view = el('div'); view.id = 'zbmpView';
    view.innerHTML = '<div class="zbmp-main" id="zbmpMain"></div>';
    document.body.appendChild(view);
    var main = view.querySelector('#zbmpMain');

    // 半屏 Sheet 容器（全局复用）
    var sheetMask = el('div', 'zb-sheet-mask');
    sheetMask.innerHTML = '<aside class="zb-sheet" role="dialog" aria-modal="true"><div class="zb-sheet-head"><h3 id="zbSheetTitle"></h3><button class="zb-sheet-close" id="zbSheetClose" type="button">' + I.x + '</button></div><div class="zb-sheet-body" id="zbSheetBody"></div><div class="zb-sheet-foot" id="zbSheetFoot"></div></aside>';
    document.body.appendChild(sheetMask);
    function openSheet(title, bodyHtml, footHtml) {
      document.getElementById('zbSheetTitle').textContent = title;
      document.getElementById('zbSheetBody').innerHTML = bodyHtml || '';
      document.getElementById('zbSheetFoot').innerHTML = footHtml || '';
      sheetMask.classList.add('show');
    }
    function closeSheet() { sheetMask.classList.remove('show'); }
    sheetMask.addEventListener('click', function (e) { if (e.target === sheetMask || e.target.closest('#zbSheetClose')) closeSheet(); });
    window.__zbCloseSheet = closeSheet; window.__zbOpenSheet = openSheet;

    var route = 'home';
    function go(r) {
      route = r;
      nav.querySelectorAll('.zbmp-item').forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-route') === r); });
      render(); main.scrollTop = 0;
    }
    function pageHead(title, sub, actions) {
      return '<div class="zbmp-pagehead"><button class="zbmp-back" id="zbmpBack" type="button">' + I.back + '</button><h2>' + title + '</h2>' +
        (sub ? '<span class="sub">' + sub + '</span>' : '') + '<div class="ph-actions">' + (actions || '') + '</div></div>';
    }

    function renderHome() {
      var secs = GROUPS.filter(function (g) { return g.title !== '概览'; });
      var html = '<div class="zbmp-page-in"><div class="zbmp-home">' +
        '<div class="zbmp-hi"><div class="logo">Z</div><div><h1>Z-Brand 品牌监测平台</h1><p class="cap">ZBMP · 母平台增强能力层 · 同一 Core，不复制系统</p></div></div>' +
        '<div class="zbmp-home-search">' + I.search() + '<input placeholder="搜索品牌、事件、报告或功能…" aria-label="搜索"></div>';
      secs.forEach(function (g) {
        html += '<div class="zbmp-sec-title">' + g.title + '</div><div class="zbmp-grid">';
        g.items.forEach(function (m) {
          var state = m.s === 'live' ? dot('info', '可用') : m.s === 'core' ? dot('muted', '接入中') : dot('muted', '规划中');
          html += '<button class="zbmp-tile" data-go="' + m.k + '" type="button"><span class="th"><span class="ti">' + I[m.i] + '</span><b>' + m.t + '</b></span>' +
            '<span class="td">' + m.d + '</span><span class="tf">' + state + '</span></button>';
        });
        html += '</div>';
      });
      html += '</div></div>';
      main.innerHTML = html;
      main.querySelectorAll('.zbmp-tile').forEach(function (t) { t.addEventListener('click', function () { go(t.getAttribute('data-go')); }); });
    }
    I.search = function () { return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'; };

    function renderEmpty(m) {
      var tag = m.s === 'core'
        ? '<span class="zb-tag">' + dot('info', 'Core 能力已具备 · 正在接入工作台') + '</span>'
        : '<span class="zb-tag">' + dot('muted', '规划中 · 提前占位') + '</span>';
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead(m.t) +
        '<div class="zbmp-wrap"><div class="zb-empty"><div class="ei">' + I[m.i] + '</div><h3>' + m.t + '</h3>' +
        '<p>' + m.d + ' 该模块的信息架构位置已预留，数据将来自 Core 统一管线，不会在 ZBMP 另建一套；接入前不展示任何编造数字。</p>' + tag + '</div></div></div>';
      bindBack();
    }

    function renderConnectors() {
      var platforms = [
        { n: '小红书', ab: 'XHS', role: 'PRIMARY · 主监测平台', st: 'attention', stl: '暂停采集（按指令）/ 熔断保护中', can: false, btn: '暂停' },
        { n: '抖音', ab: 'DY', role: 'SECONDARY · 第二重点', st: 'muted', stl: 'Backend 未验证，默认禁用', can: false, btn: '未启用' },
        { n: '微博', ab: 'WB', role: 'Future · 保留扩展接口', st: 'muted', stl: '未开发', can: false, btn: '待建' },
        { n: 'B 站', ab: 'BILI', role: 'Future · 保留扩展接口', st: 'muted', stl: '未开发', can: false, btn: '待建' },
        { n: '快手 / 知乎 / 贴吧', ab: '···', role: 'Future · 统一 Adapter 接入', st: 'muted', stl: '未开发', can: false, btn: '待建' }
      ];
      var rows = platforms.map(function (p) {
        return '<div class="zb-connector"><div class="cl">' + p.ab + '</div><div class="ct"><b>' + p.n + '</b><small>' + p.role + ' · ' +
          '<span class="zb-status"><span class="zb-dot ' + p.st + '"></span>' + p.stl + '</span></small></div>' +
          '<button class="zb-add-btn" type="button" ' + (p.can ? '' : 'disabled') + '>' + p.btn + '</button></div>';
      }).join('');
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead('连接器', '平台采集适配器 · 独立 Session/状态机/冷却') +
        '<div class="zbmp-wrap"><div class="zb-group"><div class="zg-title">平台 Adapter（统一 Collector Interface，Core 不绑定单一平台）</div>' +
        '<div class="zb-card">' + rows + '</div></div>' +
        '<div class="zb-group"><div class="zg-title">说明</div><div class="zb-card">' +
        '<div class="zb-row static"><span class="ri">' + I.shield + '</span><span class="rt"><b>风控由系统状态机负责</b><small>验证码 / 300012 / IP 风险只识别→停止→熔断→冷却→合法人工验证→恢复；AI 不参与平台风控决策，也绝不把异常显示成 0 条。</small></span></div>' +
        '</div></div></div></div>';
      bindBack();
    }

    function switchHtml(checked) { return '<button class="zb-switch" role="switch" aria-checked="' + (!!checked) + '" type="button"><span class="track"></span><span class="knob"></span></button>'; }
    function renderSettings() {
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead('工作区设置') + '<div class="zbmp-wrap">' +
        group('外观',
          rowStatic('palette', '主题', '', '<span class="rv">跟随系统 ' + I.chev + '</span>') +
          rowStatic('sparkle', '强调色', '六语义色仅用于状态/关键操作', '<span class="rv"><span class="zb-dot info"></span> Stone ' + I.chev + '</span>') +
          rowStatic('doc', '字号', '', '<span class="rv">14 / 13 ' + I.chev + '</span>')) +
        group('通用',
          rowToggle('compact', '高密度模式', '更紧凑的行距与控件，默认开启', true) +
          rowToggle('microanim', '微交互与微光动效', '弹层淡入上移、状态点反馈', true)) +
        group('安全与访问',
          rowBtn('key', 'ZBMP 访问密钥', '签发 / 查看 / 吊销工作区 API Key', 'openKeys') +
          rowStatic('shield', '安全与登录', '会话 12 小时工作区授权', '<span class="rv">' + I.chev + '</span>')) +
        group('关于',
          rowStatic('info', '版本', '序境 v5.9.9 · ZBMP Workbench v1.0（Staging）', '') +
          '<button class="zb-row" id="zbExitWs" type="button"><span class="ri">' + I.grid + '</span><span class="rt"><b>返回 CTH-POMS 工作区</b></span><span class="chev">' + I.chev + '</span></button>') +
        '</div></div>';
      bindBack();
      main.querySelectorAll('.zb-switch').forEach(bindSwitch);
      var ok = main.querySelector('[data-act="openKeys"]'); if (ok) ok.addEventListener('click', openKeysSheet);
      var ex = document.getElementById('zbExitWs'); if (ex) ex.addEventListener('click', function () { window.dispatchEvent(new CustomEvent('zb:goto-cth')); });
    }
    function group(title, inner) { return '<div class="zb-group"><div class="zg-title">' + title + '</div><div class="zb-card">' + inner + '</div></div>'; }
    function rowStatic(ic, t, sub, right) {
      return '<div class="zb-row static"><span class="ri">' + I[ic] + '</span><span class="rt"><b>' + t + '</b>' + (sub ? '<small>' + sub + '</small>' : '') + '</span><span class="rv">' + right + '</span></div>';
    }
    function rowBtn(ic, t, sub, act) {
      return '<button class="zb-row" data-act="' + act + '" type="button"><span class="ri">' + I[ic] + '</span><span class="rt"><b>' + t + '</b>' + (sub ? '<small>' + sub + '</small>' : '') + '</span><span class="chev">' + I.chev + '</span></button>';
    }
    function rowToggle(id, t, sub, on) {
      return '<div class="zb-row static"><span class="rt"><b>' + t + '</b><small>' + sub + '</small></span>' + switchHtml(on).replace('zb-switch', 'zb-switch" data-id="' + id) + '</div>';
    }
    function bindSwitch(s) {
      s.addEventListener('click', function () {
        var on = s.getAttribute('aria-checked') !== 'true'; s.setAttribute('aria-checked', on ? 'true' : 'false');
      });
    }

    /* ---- 真实密钥管理 Sheet（接 Step5b 后端） ---- */
    function openKeysSheet() {
      openSheet('ZBMP 访问密钥',
        '<p style="font-size:12px;color:var(--zb-stone-500);line-height:1.7;margin:4px 2px 12px">明文密钥仅在签发时显示一次；库内只存哈希。吊销立即失效其授权。</p>' +
        '<div class="zb-group"><div class="zg-title">当前密钥</div><div class="zb-card" id="zbKeyList"><div class="zb-row static"><span class="rt"><small>加载中…</small></span></div></div></div>' +
        '<div class="zb-group"><div class="zg-title">签发新密钥</div><div class="zb-card"><div class="zb-row static"><span class="rt"><input id="zbKeyLabel" placeholder="备注，如：我的手机" style="width:100%;height:34px;border:1px solid var(--zb-stone-300);border-radius:6px;padding:0 10px;font:inherit;font-size:13px;outline:none"></span></div></div></div>' +
        '<div id="zbKeyOut" style="font-size:12px;word-break:break-all;margin:0 2px"></div>',
        '<button class="zb-block-btn ghost" id="zbKeyRefresh" type="button">刷新列表</button>' +
        '<button class="zb-block-btn primary" id="zbKeyIssue" type="button">签发密钥</button>');
      loadKeys();
      document.getElementById('zbKeyRefresh').addEventListener('click', loadKeys);
      document.getElementById('zbKeyIssue').addEventListener('click', issueKey);
      document.getElementById('zbKeyList').addEventListener('click', function (e) {
        var b = e.target.closest('[data-revoke]'); if (!b) return;
        if (!confirm('确认吊销该密钥？其授权将立即失效。')) return;
        fetch('/v4/auth/workspace/keys/revoke', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: Number(b.getAttribute('data-revoke')) }) })
          .then(function (r) { return r.json(); }).then(function (j) { if (j.success) loadKeys(); else alert('吊销失败：' + (j.error || '')); });
      });
    }
    function loadKeys() {
      var box = document.getElementById('zbKeyList');
      fetch('/v4/auth/workspace/keys?workspace=ZBMP', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j.success || !j.keys || !j.keys.length) { box.innerHTML = '<div class="zb-row static"><span class="rt"><small>暂无密钥</small></span></div>'; return; }
          box.innerHTML = j.keys.map(function (k) {
            var d = k.status === 'revoked' ? 'muted' : 'success';
            return '<div class="zb-row static"><span class="ri">' + I.key + '</span><span class="rt"><b>' + (k.label || '未命名') + ' · <span style="font-family:var(--zb-font-mono)">' + k.key_prefix + '…</span></b><small>' +
              dot(d, k.status === 'revoked' ? '已吊销' : '有效') + (k.last_used_at ? ' · 最近使用 ' + k.last_used_at : '') + ' · #' + k.id + '</small></span>' +
              (k.status === 'active' ? '<button class="zb-add-btn" data-revoke="' + k.id + '" type="button">吊销</button>' : '') + '</div>';
          }).join('');
        })
        .catch(function () { box.innerHTML = '<div class="zb-row static"><span class="rt"><small>读取失败：需先解锁/登录</small></span></div>'; });
    }
    function issueKey() {
      var label = (document.getElementById('zbKeyLabel').value || '').trim() || 'ZBMP 设备';
      var out = document.getElementById('zbKeyOut'); out.textContent = '签发中…';
      fetch('/v4/auth/workspace/keys', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ workspace: 'ZBMP', label: label }) })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (res.ok && res.j.key) { out.innerHTML = '新密钥（只显示一次，请立即复制保存）：<br><b style="font-family:var(--zb-font-mono)">' + res.j.key + '</b>'; loadKeys(); }
          else out.textContent = '签发失败：' + ((res.j && res.j.error) || '需要 owner 权限');
        })
        .catch(function () { out.textContent = '网络错误'; });
    }

    function bindBack() { var b = document.getElementById('zbmpBack'); if (b) b.addEventListener('click', function () { go('home'); }); }
    function render() {
      if (route === 'home') return renderHome();
      if (route === 'connectors') return renderConnectors();
      if (route === 'settings') return renderSettings();
      if (route === 'events') return renderEvents();
      if (route === 'content') return renderContent();
      if (route === 'graph') return renderGraph();
      if (route === 'reports') return renderReports();
      if (route === 'brands') return renderBrands();
      if (route === 'campaign') return renderCampaign();
      var m = MOD[route]; if (m) return renderEmpty(m); return renderHome();
    }

    /* -------- 真实数据接入（复用 Core 现有 API，不另建后端；失败显错误，绝不伪装 0 条） -------- */
    function esc(s) {
      return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
    }
    function riskMeta(level) {
      var v = String(level == null ? '' : level).toLowerCase();
      if (/high|严重|红|^3|danger|urgent/.test(v)) return { cls: 'danger', t: '高风险' };
      if (/med|mid|中|^2|risk|orange/.test(v)) return { cls: 'risk', t: '中风险' };
      if (/low|低|^1|attention/.test(v)) return { cls: 'attention', t: '低风险' };
      if (/normal|正常|安全|resolved|success/.test(v)) return { cls: 'success', t: '正常' };
      return { cls: 'muted', t: level ? esc(level) : '未定级' };
    }
    function fmtTime(s) {
      if (!s) return '';
      var m = String(s).match(/(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/);
      return m ? (m[1] + ' ' + m[2]) : String(s).slice(0, 16);
    }
    function skel(n) { var h = ''; for (var i = 0; i < n; i++) h += '<div class="zb-skel" style="margin-bottom:8px"><div class="bar w60"></div><div class="bar w80"></div><div class="bar w40"></div></div>'; return h; }
    function failBox(box, title, msg) {
      box.innerHTML = '<div class="zb-empty"><div class="ei">' + I.zap + '</div><h3>' + esc(title) + '</h3>' +
        '<p>数据接口未返回有效结果（' + esc(msg || 'network') + '）。这里不会用 0 条伪装成功，请检查 Core 服务/接口后重试。</p>' +
        '<button class="zb-add-btn" id="zbRetry" type="button">重试</button></div>';
      var rb = document.getElementById('zbRetry'); if (rb) rb.addEventListener('click', function () { render(); });
    }
    function statStrip(items) { return '<div class="zb-statstrip">' + items.map(function (x) { return '<div class="zb-stat"><span class="k">' + x.k + '</span><span class="v">' + x.v + (x.s ? '<small>' + x.s + '</small>' : '') + '</span></div>'; }).join('') + '</div>'; }

    function renderEvents() {
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead('事件中心', '营销 / 传播 / 舆情事件 · 来自 Core 事件引擎') +
        '<div class="zbmp-wrap"><div class="zb-data-note">统计按事件口径聚合；风险等级与证实状态来自系统规则，AI 仅辅助不决定事实。</div><div id="zbEvt"></div></div></div>';
      bindBack();
      var box = document.getElementById('zbEvt');
      box.innerHTML = skel(4);
      fetch('/api/events?limit=50', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j || j.ok === false) throw new Error('接口返回 ok=false');
          var evs = j.events || [];
          var hi = 0, mid = 0, confirmed = 0, active = 0;
          evs.forEach(function (e) { var m = riskMeta(e.risk_level); if (m.cls === 'danger') hi++; else if (m.cls === 'risk') mid++; if (/verif|confirm|证实|确认/.test(String(e.fact_status || ''))) confirmed++; if (e.status && !/resolv|archived|关闭/.test(String(e.status))) active++; });
          var html = statStrip([
            { k: '事件总数', v: evs.length, s: '/ 本页 50' },
            { k: '活跃事件', v: active },
            { k: '高 / 中风险', v: hi + ' / ' + mid },
            { k: '已证实', v: confirmed }
          ]);
          if (!evs.length) { html += '<div class="zb-empty"><div class="ei">' + I.zap + '</div><h3>当前无事件</h3><p>Core 事件引擎未返回事件（NO_NEW_DATA），这不是失败。</p></div>'; box.innerHTML = html; return; }
          html += '<div class="zb-list">';
          evs.forEach(function (e) {
            var rm = riskMeta(e.risk_level);
            var isConf = /verif|confirm|证实|确认/.test(String(e.fact_status || ''));
            var meta = '<span class="zb-status"><span class="zb-dot ' + rm.cls + '"></span>' + rm.t + '</span>' +
              '<span class="sep"></span><span>' + (e.event_date ? esc(e.event_date) : '日期未知') + '</span>' +
              '<span class="sep"></span><span class="zb-num">提及 ' + (e.mention_count || 0) + ' · 来源 ' + (e.source_count || 0) + '</span>' +
              (e.status ? '<span class="sep"></span><span class="zb-mini-tag">' + esc(e.status) + '</span>' : '') +
              '<span class="zb-mini-tag" style="' + (isConf ? 'color:var(--zb-success,#16A34A)' : 'color:var(--zb-attention,#D97706)') + '">' + (isConf ? '已证实' : '待核') + '</span>';
            html += '<div class="zb-li"><div class="zb-li-row1"><span class="zb-li-title">' + esc(e.title || '未命名事件') + '</span></div>' +
              (e.summary ? '<div class="zb-li-sub">' + esc(e.summary) + '</div>' : '') +
              '<div class="zb-li-meta">' + meta + '</div></div>';
          });
          html += '</div>';
          box.innerHTML = html;
        })
        .catch(function (err) { failBox(box, '事件数据加载失败', err.message); });
    }

    function renderContent() {
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead('内容监测', '跨平台内容流 · 已过主体过滤与去重') +
        '<div class="zbmp-wrap"><div class="zb-data-note">时间一律取真实发布时间 publish_datetime；缺失则标“发布时间未知”，绝不用采集时间 captured_at 顶替。</div><div id="zbNote"></div></div></div>';
      bindBack();
      var box = document.getElementById('zbNote');
      box.innerHTML = skel(4);
      fetch('/api/notes?per_page=30', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j || j.ok === false) throw new Error('接口返回 ok=false');
          var notes = j.notes || [];
          var neg = 0, official = 0, eng = { likes: 0, comments: 0, collects: 0 };
          notes.forEach(function (n) {
            if (/neg|负面|高|中/.test(String(n.risk_level || '').toLowerCase()) || n.negative_confirmed) neg++;
            if (n.is_official) official++;
            eng.likes += Number(n.likes) || 0; eng.comments += Number(n.comments) || 0; eng.collects += Number(n.collects) || 0;
          });
          var html = statStrip([
            { k: '命中总量', v: j.total != null ? j.total : notes.length, s: '条' },
            { k: '本页 / 总页', v: (j.page || 1) + ' / ' + (j.total_pages || 1) },
            { k: '负面 / 官方', v: neg + ' / ' + official },
            { k: '本页互动', v: eng.likes + eng.comments + eng.collects, s: '赞评藏' }
          ]);
          if (!notes.length) { html += '<div class="zb-empty"><div class="ei">' + I.file + '</div><h3>当前无内容</h3><p>未返回笔记（NO_NEW_DATA），这不是失败，也不显示为 0 条采集成功。</p></div>'; box.innerHTML = html; return; }
          html += '<div class="zb-list">';
          notes.forEach(function (n) {
            var rm = riskMeta(n.risk_level || n.sentiment);
            var title = n.title || (n.content || n.body || '').slice(0, 34) || '无标题内容';
            var sub = n.content || n.body || '';
            var pub = fmtTime(n.publish_datetime);
            var kws = [];
            if (n.matched_keywords) { var k = typeof n.matched_keywords === 'string' ? n.matched_keywords.split(/[,，;；]/) : n.matched_keywords; if (Array.isArray(k)) kws = k.slice(0, 3); }
            var meta = '<span class="zb-status"><span class="zb-dot ' + rm.cls + '"></span>' + rm.t + '</span>' +
              '<span class="sep"></span><span>' + esc(n.source_platform || n.note_type || '未知平台') + '</span>' +
              (n.author_nickname ? '<span class="sep"></span><span>' + esc(n.author_nickname) + '</span>' : '') +
              '<span class="sep"></span><span>' + (pub ? '发布 ' + esc(pub) : '发布时间未知') + '</span>' +
              '<span class="sep"></span><span class="zb-num">赞 ' + (n.likes || 0) + ' · 评 ' + (n.comments || 0) + ' · 藏 ' + (n.collects || 0) + '</span>' +
              (n.is_official ? '<span class="zb-mini-tag">官方</span>' : '') +
              kws.map(function (x) { return '<span class="zb-mini-tag">' + esc(x) + '</span>'; }).join('');
            var inner = '<div class="zb-li-row1"><span class="zb-li-title">' + esc(title) + '</span></div>' +
              (sub ? '<div class="zb-li-sub">' + esc(sub) + '</div>' : '') +
              '<div class="zb-li-meta">' + meta + '</div>';
            html += n.url ? '<a class="zb-li-link" href="' + esc(n.url) + '" target="_blank" rel="noopener noreferrer">' + inner + '</a>' : '<div class="zb-li">' + inner + '</div>';
          });
          html += '</div>';
          box.innerHTML = html;
        })
        .catch(function (err) { failBox(box, '内容数据加载失败', err.message); });
    }

    function getJSON(u) { return fetch(u, { credentials: 'same-origin' }).then(function (r) { return r.json(); }); }
    function typeChips(obj, cls) {
      var keys = Object.keys(obj || {});
      if (!keys.length) return '<span class="zb-mini-tag">字典为空</span>';
      return keys.map(function (k) { return '<span class="zb-mini-tag ' + (cls || '') + '">' + esc(obj[k]) + ' <span class="zb-num" style="opacity:.6">(' + esc(k) + ')</span></span>'; }).join(' ');
    }

    /* 事件关系：三类事件 × 四关系，数据来自 Core event_graph；Staging 副本无节点时诚实标注 */
    function renderGraph() {
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead('事件关系', '营销 / 传播 / 舆情事件的触发·衍生·继发·并行关系图谱') +
        '<div class="zbmp-wrap"><div class="zb-data-note">关系类型与节点来自 Core event_graph；关系判定遵循系统规则，AI 仅辅助建议。</div><div id="zbGraph"></div></div></div>';
      bindBack();
      var box = document.getElementById('zbGraph');
      box.innerHTML = skel(3);
      Promise.all([getJSON('/api/event-graph/stats'), getJSON('/api/event-graph/events'), getJSON('/api/event-graph/types')])
        .then(function (rs) {
          var st = rs[0] || {}, ev = rs[1] || {}, ty = rs[2] || {};
          var d = st.data || {};
          var html = statStrip([
            { k: '图谱节点', v: d.total_events != null ? d.total_events : (ev.count || 0) },
            { k: '关系连线', v: d.total_relations != null ? d.total_relations : 0 },
            { k: '事件类型', v: Object.keys(ty.event_types || {}).length },
            { k: '关系类型', v: Object.keys(ty.relation_types || {}).length }
          ]);
          html += '<div class="zb-li" style="margin-bottom:10px"><div class="zb-li-title" style="margin-bottom:7px">事件三类</div><div class="zb-li-meta">' + typeChips(ty.event_types) + '</div></div>';
          html += '<div class="zb-li" style="margin-bottom:14px"><div class="zb-li-title" style="margin-bottom:7px">关系四类</div><div class="zb-li-meta">' + typeChips(ty.relation_types, 'is-hot') + '</div></div>';
          var nodes = ev.events || [];
          if (!nodes.length) {
            html += '<div class="zb-empty"><div class="ei">' + I.share + '</div><h3>Staging 副本暂无图谱节点</h3>' +
              '<p>三列分层关系画布已就绪（营销 → 传播 → 舆情，触发/衍生/继发/并行连线）；当前 Staging 只读副本未同步 event_graph 数据，生产库已有节点与关系。这里不用占位数据造假，切到生产或同步副本后即自动出图。</p></div>';
          } else {
            html += '<div id="zbGraphCanvas"></div>';
          }
          box.innerHTML = html;
          if (nodes.length) drawGraphCanvas(document.getElementById('zbGraphCanvas'), nodes, ty);
        })
        .catch(function (err) { failBox(box, '事件关系数据加载失败', err.message); });
    }

    /* 三列分层关系画布：营销/传播/舆情三列，SVG 连线（自研、无第三方库）；颜色+文字双重表达关系 */
    var REL_COLOR = { trigger: '#DC2626', derive: '#2563EB', follow: '#78716C', parallel: '#D97706' };
    var TYPE_ORDER = ['marketing_event', 'propagation_event', 'public_opinion_event'];
    function drawGraphCanvas(host, events, ty) {
      var COLW = 248, GAPX = 84, NODEH = 72, GAPY = 14, PAD = 12, HEAD = 38;
      var etNames = (ty && ty.event_types) || {};
      var cols = {}; TYPE_ORDER.forEach(function (t) { cols[t] = []; });
      events.forEach(function (e) { (cols[e.event_type] || (cols[e.event_type] = [])).push(e); });
      var colKeys = Object.keys(cols).filter(function (k) { return cols[k].length; });
      var pos = {};
      colKeys.forEach(function (k, ci) {
        cols[k].forEach(function (e, ri) {
          pos[e.event_id] = { x: PAD + ci * (COLW + GAPX), y: PAD + HEAD + ri * (NODEH + GAPY), col: ci, e: e };
        });
      });
      var rows = colKeys.reduce(function (m, k) { return Math.max(m, cols[k].length); }, 0);
      var W = PAD * 2 + colKeys.length * COLW + (colKeys.length - 1) * GAPX;
      var H = PAD * 2 + HEAD + rows * NODEH + (rows - 1) * GAPY;
      var svg = ['<svg class="zb-graph-svg" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '">'];
      Object.keys(REL_COLOR).forEach(function (rt) {
        svg.push('<marker id="zbArr' + rt + '" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="' + REL_COLOR[rt] + '"/></marker>');
      });
      var labels = [];
      events.forEach(function (e) {
        var s = pos[e.event_id]; if (!s) return;
        (e.relations || []).forEach(function (rel) {
          var t = pos[rel.target_event_id]; if (!t) return;
          var rt = rel.relation_type || 'follow', color = REL_COLOR[rt] || REL_COLOR.follow;
          var d, lx, ly, x1, x2, y1, y2;
          if (t.col === s.col) {
            // 同列：底部→顶部垂直连线
            var cx = s.x + COLW / 2;
            x1 = cx; y1 = s.y + NODEH; x2 = cx; y2 = t.y;
            d = 'M' + x1 + ',' + y1 + ' L' + x2 + ',' + y2;
            lx = cx + 6; ly = (y1 + y2) / 2 - 10;
          } else {
            y1 = s.y + NODEH / 2; y2 = t.y + NODEH / 2;
            if (t.col > s.col) { x1 = s.x + COLW; x2 = t.x; } else { x1 = s.x; x2 = t.x + COLW; }
            var mx = (x1 + x2) / 2;
            d = 'M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2;
            lx = mx - 26; ly = (y1 + y2) / 2 - 10;
          }
          svg.push('<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="1.5" stroke-opacity="0.55" marker-end="url(#zbArr' + rt + ')"/>');
          labels.push('<span class="zb-edge-tag" style="left:' + lx + 'px;top:' + ly + 'px;border-color:' + color + ';color:' + color + '">' +
            esc(rel.relation_type_name || rt) + '</span>');
        });
      });
      svg.push('</svg>');
      var heads = '';
      colKeys.forEach(function (k, ci) {
        var x = PAD + ci * (COLW + GAPX);
        heads += '<div class="zb-graph-colhead" style="left:' + x + 'px;width:' + COLW + 'px"><span class="zb-graph-coldot zb-tc-' + k + '"></span>' + esc(etNames[k] || k) + '<span class="zb-num">' + cols[k].length + '</span></div>';
      });
      var nodesHtml = '';
      colKeys.forEach(function (k) {
        cols[k].forEach(function (e) {
          var p = pos[e.event_id]; var md = e.metadata || {};
          var risk = md.risk_level || '';
          var deg = e.relations ? e.relations.length : 0;
          nodesHtml += '<div class="zb-gnode zb-tc-' + k + '" style="left:' + p.x + 'px;top:' + p.y + 'px;width:' + COLW + 'px;height:' + NODEH + 'px" title="' + esc(e.description || e.title) + '">' +
            '<div class="zb-gnode-t">' + esc(e.title || e.event_id) + '</div>' +
            '<div class="zb-gnode-m"><span>' + esc(e.event_time || '时间未知') + '</span>' +
            (risk ? '<span class="zb-gnode-risk zb-rk-' + risk + '">' + esc(risk) + '</span>' : '') +
            (deg ? '<span class="zb-num">关系 ' + deg + '</span>' : '') + '</div></div>';
        });
      });
      var legend = '<div class="zb-graph-legend">' + Object.keys(REL_COLOR).map(function (rt) {
        var nm = (ty.relation_types && ty.relation_types[rt]) || rt;
        return '<span><i style="background:' + REL_COLOR[rt] + '"></i>' + esc(nm) + '</span>';
      }).join('') + '</div>';
      host.innerHTML = legend + '<div class="zb-graph-stage" style="width:' + W + 'px;height:' + H + 'px">' + svg.join('') + heads + labels.join('') + nodesHtml + '</div>';
    }
    if (typeof window !== 'undefined') window.__zbDrawGraphCanvas = drawGraphCanvas; // 调试/真实数据验证钩子（只读渲染）

    /* 报告中心：报告列表 + 真实统计口径；Staging 无报告文件时诚实标注，不自动触发生成 */
    function renderReports() {
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead('报告中心', '日报 / 周报 / 月报 / 专题，统计默认按 publish_datetime') +
        '<div class="zbmp-wrap"><div class="zb-data-note">报告统计口径以系统规则为准（发布时间、负面确认、时效分类），AI 仅做润色与解释，不改写统计数字。</div><div id="zbRep"></div></div></div>';
      bindBack();
      var box = document.getElementById('zbRep');
      box.innerHTML = skel(3);
      Promise.all([getJSON('/api/reports'), getJSON('/api/report/v2/stats')])
        .then(function (rs) {
          var list = rs[0] || {}, stats = rs[1] || {};
          var reps = list.reports || [];
          var nc = stats.negative_confirmation || {};
          var df = stats.daily_filter || {};
          var html = statStrip([
            { k: '报告总数', v: list.count != null ? list.count : reps.length, s: '份' },
            { k: '今日纳入日报', v: df.daily_report_included != null ? df.daily_report_included : '—' },
            { k: '负面确认率', v: nc.confirmation_rate != null ? nc.confirmation_rate + '%' : '—' },
            { k: '已确认 / 待确认', v: (nc.confirmed != null ? nc.confirmed : '—') + ' / ' + (nc.pending != null ? nc.pending : '—') }
          ]);
          html += '<div class="zb-data-note">报告类型：' +
            '<span class="zb-mini-tag">日报 daily</span> <span class="zb-mini-tag">周报 weekly</span> <span class="zb-mini-tag">月报 monthly</span> <span class="zb-mini-tag is-hot">专题 special</span></div>';
          if (stats.ok !== false) {
            var lines = [];
            ['daily_filter', 'age_classification', 'negative_confirmation', 'logic_explanation'].forEach(function (kk) {
              if (stats[kk] != null) lines.push('<div style="margin:3px 0"><span style="color:var(--zb-text-muted)">' + kk + '：</span>' + esc(typeof stats[kk] === 'object' ? JSON.stringify(stats[kk]) : stats[kk]) + '</div>');
            });
            if (lines.length) html += '<div class="zb-li" style="margin-bottom:12px"><div class="zb-li-title" style="margin-bottom:5px">统计口径（系统规则）</div>' + lines.join('') + '</div>';
          }
          if (!reps.length) {
            html += '<div class="zb-empty"><div class="ei">' + I.doc + '</div><h3>Staging 副本暂无已生成报告</h3>' +
              '<p>报告列表接口已接通；报告文件由生产侧按周期生成，Staging 只读副本未携带历史报告，故此处为空（不是 0 份生产报告）。可在 CTH-POMS 生产侧生成后回到此处查看/下载。</p></div>';
          } else {
            html += '<div class="zb-list">';
            reps.forEach(function (rp) {
              var title = rp.title || rp.filename || rp.report_id || '未命名报告';
              var meta = [rp.report_type, rp.period || rp.date, rp.created_at || rp.generated_at].filter(Boolean).map(esc).join(' · ');
              html += '<div class="zb-li"><div class="zb-li-row1"><span class="zb-li-title">' + esc(title) + '</span></div><div class="zb-li-meta"><span>' + meta + '</span></div></div>';
            });
            html += '</div>';
          }
          box.innerHTML = html;
        })
        .catch(function (err) { failBox(box, '报告数据加载失败', err.message); });
    }

    function fmtEng(n) { if (n == null) return '—'; n = +n; if (n >= 10000) return (n / 10000).toFixed(1) + 'w'; if (n >= 1000) return (n / 1000).toFixed(1) + 'k'; return '' + n; }

    /* 品牌资产：场内品牌 + 业态分布 + 知识库，全部来自 Core 真实品牌库 */
    function renderBrands() {
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead('品牌资产', '场内品牌画像、业态分布与品牌知识库，接入 Core 品牌库') +
        '<div class="zbmp-wrap"><div class="zb-data-note">品牌/楼层/铺号来自 Core 品牌目录，主体口径不变；这里只读呈现，不做改写。</div><div id="zbBrands"></div></div></div>';
      bindBack();
      var box = document.getElementById('zbBrands');
      box.innerHTML = skel(3);
      Promise.all([getJSON('/api/brands'), getJSON('/api/brand-stats'), getJSON('/api/brand-knowledge/stats')])
        .then(function (rs) {
          var bl = rs[0] || {}, bs = rs[1] || {}, bk = rs[2] || {};
          var brands = bl.brands || [];
          var cats = bs.categories || {};
          var byCat = (bk.data && bk.data.by_category) || {};
          var taikoo = brands.filter(function (b) { return b.is_taikoo_brand; }).length;
          var knowTotal = Object.keys(byCat).reduce(function (s, k) { return s + (+byCat[k] || 0); }, 0);
          var html = statStrip([
            { k: '场内品牌', v: brands.length },
            { k: '业态分类', v: Object.keys(cats).length },
            { k: '太古汇在场', v: taikoo },
            { k: '品牌知识库', v: knowTotal, s: '条' }
          ]);
          var catKeys = Object.keys(cats);
          html += '<div class="zb-li" style="margin-bottom:12px"><div class="zb-li-title" style="margin-bottom:7px">业态分布</div><div class="zb-li-meta">' +
            catKeys.map(function (c) { return '<span class="zb-mini-tag">' + esc(c) + ' · ' + (cats[c].brand_count != null ? cats[c].brand_count : (cats[c].brands || []).length) + '</span>'; }).join(' ') + '</div></div>';
          if (Object.keys(byCat).length) {
            html += '<div class="zb-li" style="margin-bottom:12px"><div class="zb-li-title" style="margin-bottom:7px">品牌知识库分类</div><div class="zb-li-meta">' +
              Object.keys(byCat).map(function (k) { return '<span class="zb-mini-tag is-hot">' + esc(k) + ' · ' + byCat[k] + '</span>'; }).join(' ') + '</div></div>';
          }
          html += '<div class="zb-list">';
          brands.forEach(function (b) {
            var name = (b.brand_cn && b.brand_cn !== '-') ? b.brand_cn : (b.brand_en || '未命名品牌');
            var meta = [b.category, b.floor ? (b.floor + (b.shop ? ' ' + b.shop : '')) : '', b.brand_en].filter(Boolean).map(esc).join(' · ');
            html += '<div class="zb-li"><div class="zb-li-row1"><span class="zb-li-title">' + esc(name) + '</span>' +
              (b.is_taikoo_brand ? '<span class="zb-mini-tag is-hot">在场</span>' : '') + '</div>' +
              '<div class="zb-li-meta"><span>' + meta + '</span></div></div>';
          });
          html += '</div>';
          if (!brands.length) html += '<div class="zb-empty"><h3>暂无品牌目录数据</h3><p>品牌接口已接通，当前环境无品牌记录。</p></div>';
          box.innerHTML = html;
        })
        .catch(function (err) { failBox(box, '品牌资产加载失败', err.message); });
    }

    /* 话题战役：战役状态 + 分话题主体命中表现 + 最新笔记，严守主体口径展示 */
    function renderCampaign() {
      main.innerHTML = '<div class="zbmp-page-in">' + pageHead('话题战役', '专题/战役监测、分话题主体命中与证据沉淀') +
        '<div class="zbmp-wrap"><div class="zb-data-note">分话题「主体命中率」来自 Core 主体过滤统计，是主体红线的直接体现；笔记均为命中主体后的真实采集。</div><div id="zbCamp"></div></div></div>';
      bindBack();
      var box = document.getElementById('zbCamp');
      box.innerHTML = skel(4);
      Promise.all([getJSON('/api/topic-campaign/status'), getJSON('/api/topic-campaign/campaigns'),
      getJSON('/api/topic-campaign/topics'), getJSON('/api/topic-campaign/stats'),
      getJSON('/api/topic-campaign/notes?limit=20')])
        .then(function (rs) {
          var st = rs[0] || {}, cp = rs[1] || {}, tp = rs[2] || {}, sta = rs[3] || {}, nt = rs[4] || {};
          var campaigns = cp.campaigns || [];
          var cur = campaigns[0] || {}; var agg = cur.agg || {};
          var topics = tp.topics || [];
          var byTopic = sta.by_topic || [];
          var notes = nt.notes || [];
          var avgHit = byTopic.length ? (byTopic.reduce(function (s, t) { return s + (+t.subject_hit_rate || 0); }, 0) / byTopic.length) : 0;
          var html = statStrip([
            { k: '战役笔记', v: agg.notes != null ? agg.notes : 0 },
            { k: '总互动', v: fmtEng(agg.eng) },
            { k: '监测话题', v: topics.length },
            { k: '平均主体命中率', v: avgHit ? avgHit.toFixed(1) + '%' : '—' }
          ]);
          if (cur.name || st.campaign) {
            var c = st.campaign || cur;
            var paused = (c.status === 'paused');
            html += '<div class="zb-li" style="margin-bottom:12px"><div class="zb-li-row1"><span class="zb-li-title">' + esc(cur.name || c.name || '当前战役') + '</span>' +
              '<span class="zb-mini-tag ' + (paused ? '' : 'is-hot') + '">' + esc(c.status || '未知') + '</span></div>' +
              '<div class="zb-li-meta"><span>' + esc((c.start_date || '?') + ' ~ ' + (c.end_date || '?')) + '</span>' +
              (agg.last ? '<span class="sep"></span><span>最近采集 ' + esc(agg.last) + '</span>' : '') +
              (c.interval_minutes ? '<span class="sep"></span><span>间隔 ' + c.interval_minutes + ' 分钟</span>' : '') + '</div></div>';
          }
          if (byTopic.length) {
            html += '<div class="zb-list" style="margin-bottom:12px">';
            byTopic.forEach(function (t) {
              html += '<div class="zb-li"><div class="zb-li-row1"><span class="zb-li-title">' + esc(t.topic || '未命名话题') + '</span>' +
                '<span class="zb-num">主体命中 ' + (t.subject_hits != null ? t.subject_hits : '—') + ' / ' + (t.unique_notes != null ? t.unique_notes : '—') + '</span></div>' +
                '<div class="zb-li-meta"><span>命中率 ' + (t.subject_hit_rate != null ? t.subject_hit_rate + '%' : '—') + '</span>' +
                '<span class="sep"></span><span>完整证据 ' + (t.full_evidence != null ? t.full_evidence : '—') + '</span>' +
                (t.risk_notes ? '<span class="sep"></span><span style="color:var(--zb-danger)">风险 ' + t.risk_notes + '</span>' : '') +
                '<span class="sep"></span><span>运行 ' + (t.runs != null ? t.runs : '—') + '</span></div></div>';
            });
            html += '</div>';
          }
          if (notes.length) {
            html += '<div class="zb-li-title" style="margin:6px 0 8px">最新战役笔记</div><div class="zb-list">';
            notes.forEach(function (n) {
              var body = n.content || n.body || n.title || n.note_text || '';
              var inter = [n.likes != null ? '赞 ' + n.likes : '', n.comments != null ? '评 ' + n.comments : '', n.collects != null ? '藏 ' + n.collects : ''].filter(Boolean).join(' · ');
              html += '<div class="zb-li"><div class="zb-li-row1"><span class="zb-li-title">' + esc(n.author || '匿名') + '</span>' +
                (inter ? '<span class="zb-num">' + esc(inter) + '</span>' : '') + '</div>' +
                (body ? '<div class="zb-li-sub">' + esc(String(body).slice(0, 110)) + '</div>' : '') + '</div>';
            });
            html += '</div>';
          }
          if (!campaigns.length && !byTopic.length) html += '<div class="zb-empty"><h3>暂无进行中的话题战役</h3><p>战役接口已接通，当前环境无战役记录。</p></div>';
          box.innerHTML = html;
        })
        .catch(function (err) { failBox(box, '话题战役加载失败', err.message); });
    }

    /* ---- 工作区切换：由 zbip-shell 派发事件驱动 ---- */
    function applyWs(name) {
      var isZb = name === 'ZBMP';
      document.body.setAttribute('data-workspace', isZb ? 'zbmp' : 'cth');
      if (isZb) { if (route) go(route); }
      else { closeSheet(); }
    }
    window.addEventListener('zb:workspace', function (e) { applyWs(e.detail && e.detail.name); });
    window.addEventListener('zb:goto-cth', function () {
      // 通过外壳工作区切换器回到 CTH：直接派发点击
      var cth = document.querySelector('.zb-pop-item[data-ws="cth"]'); if (cth) cth.click();
    });
    // ZBMP 侧栏搜索复用顶部搜索框
    var searchInput = document.querySelector('.zb-search input');
    if (searchInput) searchInput.addEventListener('input', function (e) {
      var q = (e.target.value || '').trim().toLowerCase();
      nav.querySelectorAll('.zbmp-item').forEach(function (it) { it.classList.toggle('hidden-by-search', q && (it.innerText || '').toLowerCase().indexOf(q) < 0); });
    });
    applyWs('CTH-POMS');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
