/* ============================================================================
 * LUMENIS Experience V2 — Application Shell controller
 * Global Subject Context (single source) -> Domain Lens -> Scope/Permission.
 * Renders Compact Rail (PAT-NAV-01), Bottom Dock (PAT-NAV-02), Topbar with
 * Subject pill + domain switch, and the right Context panel.
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

  function railHTML() {
    const groups = navTree();
    return `<div class="lum-rail__brand">
        <div class="lum-rail__logo">序</div>
        <div class="nm"><b data-i18n="product.mother">序境 LUMENIS</b><span id="lum-domain-label" data-i18n="domain.cth">序境·商业运营</span></div>
      </div>
      ${groups.map((g, gi) => `
        <div class="lum-nav-group" data-group="${gi}">
          <button type="button" class="lum-nav-group__label" data-collapse-group="${gi}" aria-expanded="true">
            <span data-i18n="${g.labelKey}">${g.label}</span><span class="lum-nav-group__chev" aria-hidden="true">${icon('chevron-down', 12)}</span>
          </button>
          ${g.items.map(it => `<a class="lum-nav-item" data-route="${it.id}" href="#/${it.id}" aria-current="false">
             <span class="lbl" data-i18n="${it.labelKey}">${it.label}</span>${it.count ? `<span class="cnt">${it.count}</span>` : ''}</a>`).join('')}
        </div>`).join('')}`;
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
        <button class="lum-iconbtn" id="lum-bell-btn" aria-label="notifications">${icon('bell')}<span class="badge-dot"></span></button>
      </div>`;
  }

  function renderSubject() {
    const s = currentSubject(); const n = $('#lum-subject-name'); if (n) n.textContent = s.name || 'UNKNOWN';
    const dom = SubjectContext.value.domain;
    const dk = dom === 'BMP' ? 'domain.zbmp' : 'domain.cth';
    ['#lum-domain-label', '#lum-crumb-domain'].forEach(q => { const e = $(q); if (e && global.LumI18n) e.textContent = global.LumI18n.t(dk); });
    $$('#lum-domain-switch button').forEach(b => b.setAttribute('aria-pressed', b.dataset.val === dom ? 'true' : 'false'));
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
    global.LumUI.bindSegmented($('#lum-domain-switch'), v => SubjectContext.setDomain(v));
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
    return app;
  }

  function setActiveRoute(id) {
    $$('.lum-nav-item,.lum-dock__item').forEach(n => n.setAttribute('aria-current', n.dataset.route === id ? 'page' : 'false'));
    const item = navTree().flatMap(g => g.items).find(i => i.id === id);
    const crumb = $('#lum-crumb-page'); if (crumb && item) crumb.textContent = global.LumI18n ? global.LumI18n.t(item.labelKey) : item.label;
  }
  function setContext(html) { const c = $('#lum-context-inner'); if (c) c.innerHTML = html; }
  global.LumShell = { mountShell, setActiveRoute, setContext, SubjectContext, currentSubject, renderSubject };
})(window);
