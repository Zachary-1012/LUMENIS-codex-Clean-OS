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
      { k: 'brands', t: '品牌资产', i: 'layers', s: 'core', d: '品牌画像、资产沉淀与健康度，接入 Core 品牌库。' },
      { k: 'compete', t: '竞品监控', i: 'crosshair', s: 'planned', d: '竞品声量与对比分析，规划中。' },
      { k: 'cases', t: '案例库', i: 'book', s: 'core', d: '公关/传播案例库，接入 Core 案例能力。' } ] },
    { title: '监测', items: [
      { k: 'content', t: '内容监测', i: 'file', s: 'live', d: '跨平台内容流与主体过滤，接入 Core 采集管线。' },
      { k: 'campaign', t: '话题战役', i: 'target', s: 'core', d: '15 周年等专题/战役监测，接入 Core 话题能力。' } ] },
    { title: '洞察', items: [
      { k: 'events', t: '事件中心', i: 'zap', s: 'live', d: '营销/传播/舆情事件与生命周期，接入 Core 事件引擎。' },
      { k: 'graph', t: '事件关系', i: 'share', s: 'core', d: '触发/衍生/继发/并行关系图谱，接入 Core 关系数据。' },
      { k: 'ai-eval', t: 'AI 评估', i: 'sparkle', s: 'core', d: 'Ollama 本地 AI 增强分析（仅增强层，不决定系统事实）。' } ] },
    { title: '产出', items: [
      { k: 'reports', t: '报告中心', i: 'doc', s: 'core', d: '日/周/月报与专题导出，接入 Core 报告能力。' } ] },
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
          rowStatic('info', '版本', 'Z-Brand Core v5.9.9 · ZBMP Workbench v1.0（Staging）', '') +
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
          if (res.ok && res.j.key) { out.innerHTML = '✅ 新密钥（只显示一次，请立即复制保存）：<br><b style="font-family:var(--zb-font-mono)">' + res.j.key + '</b>'; loadKeys(); }
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
