/* ============================================================================
 * LUMENIS Experience V2 — Application Shell controller
 * Global Subject Context (single source) -> Domain Lens -> Scope/Permission.
 * Renders Compact Rail (PAT-NAV-01), Bottom Dock (PAT-NAV-02), Topbar with
 * Subject pill + domain switch, and the right Context panel.
 *
 * Product hierarchy (the rail is the product contract):
 *   LUMENIS AI -> CTH / BMP -> Settings
 * AI chat and Content Studio are cross-domain capabilities with one canonical
 * screen each. They are linked from both product domains, never duplicated.
 * Subject selection changes ONLY the working context/view — never the data.
 * ========================================================================== */
(function (global) {
  'use strict';
  const { $, $$, el, icon } = global.LumUI;

  // Global Subject Context (presentation-layer; backend must re-verify, README sec2)
  const SubjectContext = {
    value: { subject_id: 'subj_taikoo_hui', subject_type: 'commercial_property', domain: 'CTH',
      scope: 'mall_group', permissions: ['read'], time_window: 'last_30d', locale: 'zh-CN', context_version: 'v2.1' },
    set(patch) { Object.assign(this.value, patch); document.dispatchEvent(new CustomEvent('lum:subject', { detail: this.value })); renderSubject(); },
    setDomain(domain) { return this.set({ domain }); }
  };

  function subjects() { return (global.LUM_FIXTURES && global.LUM_FIXTURES.subjects) || []; }
  function currentSubject() { return subjects().find(s => s.subject_id === SubjectContext.value.subject_id) || subjects()[0] || { name: 'UNKNOWN' }; }

  function navTree() { return (global.LUM_SHELL && global.LUM_SHELL.nav) || []; }

  function groupByKey(key) {
    const groups = navTree();
    return groups.find(g => g.labelKey === 'navgroup.' + key) || { label: key, items: [] };
  }

  function linkHTML(it) {
    const i18n = it.labelKey ? `data-i18n="${it.labelKey}"` : '';
    return `<a class="lum-nav-item" data-route="${it.id}" href="#/${it.id}" aria-current="false">
      <span class="lum-nav-item__mark" aria-hidden="true">${icon(it.icon || 'arrow-right', 15)}</span>
      <span class="lbl" ${i18n}>${it.label || ''}</span>${it.count ? `<span class="cnt">${it.count}</span>` : ''}</a>`;
  }

  function navGroupHTML(id, label, items, labelKey, extraClass = '') {
    const i18n = labelKey ? `data-i18n="${labelKey}"` : '';
    const entryRoute = (id === 'cth' || id === 'bmp') && items[0] ? `data-route="${items[0].id}"` : '';
    return `<div class="lum-nav-group ${extraClass}" data-group="${id}">
      <button type="button" class="lum-nav-group__label" ${entryRoute} data-collapse-group="${id}" aria-expanded="true">
        <span ${i18n}>${label}</span><span class="lum-nav-group__chev" aria-hidden="true">${icon('chevron-down', 12)}</span>
      </button>${items.map(linkHTML).join('')}</div>`;
  }

  function railHTML() {
    const cth = groupByKey('cth');
    const bmp = groupByKey('bmp');
    const system = groupByKey('system');
    const shared = groupByKey('shared');
    const aiEntry = { id: 'AI-01', label: 'LUMENIS AI', labelKey: null, icon: 'orb' };
    const aiChat = { id: 'AI-01', label: 'AI 对话', labelKey: null, icon: 'orb' };
    const studio = { id: 'SH-01', label: '内容制作 · Content Studio', labelKey: null, icon: 'content' };
    const sharedSupport = (shared.items || []).filter(it => it.id !== 'SH-01');
    const settingsItems = (system.items || []).concat(sharedSupport.map(it => ({
      ...it, label: `资产 · ${it.label || it.id}`,
    })));
    return `<a class="lum-rail__brand" data-route="AI-01" href="#/AI-01" aria-label="LUMENIS AI">
        <span data-lum-brand="standard" class="lum-brand--sm"></span>
        <span id="lum-domain-label" class="lum-rail__domain">LUMENIS AI · 序境</span>
      </a>
      <a class="lum-nav-item lum-nav-item--home" data-route="${aiEntry.id}" href="#/${aiEntry.id}" aria-current="false">
        <span class="lbl">${aiEntry.label}</span><span class="lum-nav-home-mark">↗</span>
      </a>
      ${navGroupHTML('cth', '商业运营', (cth.items || []).concat([aiChat, studio]), 'navgroup.cth', 'lum-nav-group--product lum-nav-group--cth')}
      ${navGroupHTML('bmp', '品牌市场', (bmp.items || []).concat([aiChat, studio]), 'navgroup.bmp', 'lum-nav-group--product lum-nav-group--bmp')}
      ${navGroupHTML('settings', 'Settings · 设置', settingsItems, null, 'lum-nav-group--settings')}`;
  }
  function dockHTML() {
    // Bottom dock: primary destinations + central AI FAB
    const flat = navTree().flatMap(g => g.items).filter(i => i.dock !== false).slice(0, 4);
    return flat.map(it => `<button class="lum-dock__item" data-route="${it.id}">${icon(it.icon, 22)}<span data-i18n="${it.labelKey}">${it.label}</span></button>`).join('')
      + `<button class="lum-dock__fab" data-route="AI-01" aria-label="AI"><canvas class="lum-orb" data-status="idle"></canvas></button>`;
  }

  function topbarHTML(title) {
    return `<button class="lum-iconbtn" id="lum-rail-toggle" aria-label="toggle rail">${icon('menu')}</button>
      <div class="lum-crumb"><span id="lum-crumb-domain" data-i18n="domain.cth">序境·商业运营</span> ${icon('chevron-right', 14)} <b id="lum-crumb-page">${title || ''}</b></div>
      <button class="lum-subject-pill" id="lum-subject-pill">
        <span class="av">主</span><span id="lum-subject-name">—</span>${icon('chevron-down', 16)}
      </button>
      <div class="lum-segmented" id="lum-domain-switch" role="tablist" aria-label="Domain lens">
        <button data-val="CTH" data-i18n="navgroup.cth" aria-pressed="true">商业运营</button><button data-val="BMP" data-i18n="navgroup.bmp" aria-pressed="false">品牌市场</button>
      </div>
      <div class="lum-topbar__tools">
        <button class="lum-iconbtn" id="lum-search-btn" aria-label="search">${icon('search')}</button>
        <button class="lum-iconbtn" id="lum-theme-btn" aria-label="theme">${icon('sun')}</button>
        <button class="lum-iconbtn" id="lum-bell-btn" aria-label="notifications">${icon('bell')}</button>
      </div>`;
  }

  function renderSubject() {
    const s = currentSubject(); const n = $('#lum-subject-name'); if (n) n.textContent = s.name || 'UNKNOWN';
    const dom = SubjectContext.value.domain;
    const dk = dom === 'BMP' ? 'domain.zbmp' : 'domain.cth';
    ['#lum-crumb-domain'].forEach(q => { const e = $(q); if (e && global.LumI18n) e.textContent = global.LumI18n.t(dk); });
    $$('#lum-domain-switch button').forEach(b => b.setAttribute('aria-pressed', b.dataset.val === dom ? 'true' : 'false'));
  }

  // Keep the rail as a realm switcher, not a permanent memo list.  The active
  // realm opens its next level; the other product and Settings stay folded.
  // Route IDs and IA do not change — only the visible hierarchy does.
  function syncNavHierarchy(id) {
    const active = String(id || '');
    const product = active.startsWith('BMP-') ? 'bmp' : active.startsWith('CTH-') ? 'cth' : '';
    $$('.lum-nav-group').forEach(group => {
      const groupId = group.dataset.group;
      const isProduct = group.classList.contains('lum-nav-group--product');
      const open = isProduct ? (product ? groupId === product : false) : (groupId === 'settings' && active.startsWith('SYS-'));
      group.dataset.collapsed = open ? 'false' : 'true';
      const toggle = group.querySelector('[data-collapse-group]');
      if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  function subjectDrawer() {
    const list = subjects().map(s => `<button class="lum-action-item" data-pick="${s.subject_id}" style="width:100%;text-align:left;border:0;cursor:pointer;background:transparent">
        <span class="lum-action-item__ico">${icon(s.subject_type === 'brand' ? 'campaign' : 'target')}</span>
        <span class="lum-action-item__txt"><b>${s.name}</b><span>${({commercial_property:'商业体',brand:'品牌',unit:'业务单元'}[s.subject_type]||s.subject_type)} · ${({mall_group:'商业体群组',single_unit:'单一业务单元',brand:'品牌'}[s.scope]||s.scope||'UNKNOWN')}</span></span>
        ${s.subject_id === SubjectContext.value.subject_id ? icon('check', 16) : ''}</button>`).join('');
    const d = global.LumUI.openDrawer('lum-subject-drawer', global.LumI18n.t('selector.subject'),
      `<div class="lum-stack-2">${list}<div class="lum-divider"></div>
       <p class="lum-caption">切换主体只改变当前工作上下文，不改变底层事实数据。</p></div>`);
    $$('[data-pick]', d).forEach(b => b.onclick = () => { SubjectContext.set({ subject_id: b.dataset.pick }); global.LumUI.closeDrawer(d); global.LumUI.toast(global.LumI18n.t('subject.switched'), 'success'); });
  }

  function mountShell(opts = {}) {
    const app = $('.lum-app') || el('div', 'lum-app');
    app.dataset.theme = localStorage.getItem('lum-theme') || 'light';
    app.dataset.optical = 'high';
    // On phone widths the context panel becomes an overlay: never auto-cover content at startup.
    const isPhone = global.matchMedia ? global.matchMedia('(max-width:768px)').matches : false;
    const ctxState = (opts.contextOpen === false || isPhone) ? 'closed' : 'open';
    app.innerHTML = `<div class="lum-shell" id="lum-shell" data-context="${ctxState}">
      <nav class="lum-rail" aria-label="primary">${railHTML()}</nav>
      <header class="lum-topbar">${topbarHTML(opts.title)}</header>
      <main class="lum-main" id="lum-main"><div class="lum-page" id="lum-page"></div></main>
      <aside class="lum-context" id="lum-context"><div class="lum-context__inner" id="lum-context-inner"></div></aside>
      <nav class="lum-dock" aria-label="mobile primary">${dockHTML()}</nav>
    </div>`;
    document.body.appendChild(app);
    if (global.LumOrb) global.LumOrb.mountAll(app);

    $('#lum-rail-toggle').onclick = () => { const sh = $('#lum-shell'); sh.dataset.rail = sh.dataset.rail === 'collapsed' ? '' : 'collapsed'; };
    $('#lum-subject-pill').onclick = subjectDrawer;
    global.LumUI.bindSegmented($('#lum-domain-switch'), v => {
      SubjectContext.setDomain(v);
      // The lens switch is a real first-level navigation action.  It lands on
      // the overview of the selected product domain rather than leaving the
      // user on a page whose evidence context silently changed.
      const next = v === 'BMP' ? 'BMP-01' : 'CTH-01';
      if (location.hash !== '#/' + next) location.hash = '#/' + next;
    });
    $('#lum-theme-btn').onclick = () => { const next = app.dataset.theme === 'dark' ? 'light' : 'dark'; app.dataset.theme = next; localStorage.setItem('lum-theme', next); };
    $$('[data-route]').forEach(b => b.addEventListener('click', () => { const r = b.dataset.route; if (r) location.hash = '#/' + r; }));
    // Collapsible nav groups (function folding); clicking a group label toggles its items.
    $$('[data-collapse-group]').forEach(btn => btn.addEventListener('click', () => {
      const grp = btn.closest('.lum-nav-group'); if (!grp) return;
      const collapsed = grp.dataset.collapsed === 'true';
      grp.dataset.collapsed = collapsed ? 'false' : 'true';
      btn.setAttribute('aria-expanded', collapsed ? 'true' : 'false');
    }));
    // Crossing into phone width: collapse the context panel so it never overlays content (reopen on demand).
    if (global.matchMedia) {
      const mq = global.matchMedia('(max-width:768px)');
      const sync = e => { if (e.matches) { const sh = $('#lum-shell'); if (sh) sh.dataset.context = 'closed'; } };
      if (mq.addEventListener) mq.addEventListener('change', sync); else if (mq.addListener) mq.addListener(sync);
    }
    renderSubject();
    syncNavHierarchy((global.location.hash || '').replace('#/', '') || global.LUM_FIRST || 'AI-01');
    return app;
  }

  function setActiveRoute(id) {
    $$('.lum-nav-item,.lum-dock__item').forEach(n => n.setAttribute('aria-current', n.dataset.route === id ? 'page' : 'false'));
    syncNavHierarchy(id);
    const item = navTree().flatMap(g => g.items).find(i => i.id === id);
    const crumb = $('#lum-crumb-page');
    const domain = $('#lum-crumb-domain');
    const railDomain = $('#lum-domain-label');
    const special = id === 'AI-01' ? 'LUMENIS AI' : id.startsWith('SYS-') ? 'Settings · 设置' : null;
    if (special) {
      if (domain) domain.textContent = special;
      if (railDomain) railDomain.textContent = special;
    } else if (id.startsWith('SH-')) {
      // Content Studio is one canonical capability consumed by both domains,
      // not a third product line.  Keep the user's active product lens in the
      // chrome while the screen itself remains shared and unduplicated.
      const dk = SubjectContext.value.domain === 'BMP' ? 'domain.zbmp' : 'domain.cth';
      const label = global.LumI18n ? global.LumI18n.t(dk) : (SubjectContext.value.domain === 'BMP' ? '品牌市场' : '商业运营');
      if (domain) domain.textContent = label;
      if (railDomain) railDomain.textContent = label;
    } else if (domain && global.LumI18n) {
      const dk = id.startsWith('BMP-') ? 'domain.zbmp' : 'domain.cth';
      domain.textContent = global.LumI18n.t(dk);
      if (railDomain) railDomain.textContent = global.LumI18n.t(dk);
    }
    if (crumb) {
      if (special) crumb.textContent = special;
      else if (item) crumb.textContent = global.LumI18n ? global.LumI18n.t(item.labelKey) : item.label;
    }
  }
  function setContext(html) { const c = $('#lum-context-inner'); if (c) c.innerHTML = html; }
  global.LumShell = { mountShell, setActiveRoute, setContext, SubjectContext, currentSubject, renderSubject, syncNavHierarchy };
})(window);
