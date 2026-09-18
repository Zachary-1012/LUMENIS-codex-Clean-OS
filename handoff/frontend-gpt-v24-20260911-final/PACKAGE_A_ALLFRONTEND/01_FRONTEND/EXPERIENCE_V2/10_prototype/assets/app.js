/* ============================================================================
 * LUMENIS Experience V2 — application bootstrap / router
 * SPA mode: window.LUM_SCREENS registry + hash route #/<SCREEN_ID>.
 * Standalone mode: window.LUM_STANDALONE = <id> renders a single screen (used by
 * the per-screen handoff HTML and by Playwright capture).
 * Data is prototype fixture only; every screen root is marked data-source=prototype.
 * ========================================================================== */
(function (global) {
  'use strict';
  const { $, $$ } = global.LumUI;
  const screens = () => global.LUM_SCREENS || {};
  const byId = id => screens()[id];

  // Internal subject/domain codes stay in data; the context rail speaks business language.
  const DOMAIN_NAME = { CTH: '商业运营', BMP: '品牌市场' };
  const SCOPE_NAME = { mall_group: '商业体群组', single_unit: '单一业务单元', brand: '品牌' };
  const WINDOW_NAME = { last_30d: '近 30 天', last_7d: '近 7 天', last_24h: '近 24 小时' };
  const LOCALE_NAME = { 'zh-CN': '简体中文', 'en-US': 'English', 'ko-KR': '한국어' };
  function contextPanelFor(sc) {
    if (!sc.context) return '';
    const c = sc.context;
    const cv = global.LumShell.SubjectContext.value;
    const subj = (global.LumShell.currentSubject && global.LumShell.currentSubject()) || {};
    const row = (k, v, raw) => `<div class="lum-row-between lum-caption"><span>${k}</span><span class="lum-text-2" ${raw ? `title="${raw}"` : ''}>${v}</span></div>`;
    return `<div class="lum-stack-4">
      <div class="lum-softglass" style="padding:14px"><span class="lum-eyebrow">工作上下文</span>
        <div class="lum-stack-2" style="margin-top:10px">
          ${row('当前主体', subj.name || cv.subject_id, cv.subject_id)}
          ${row('领域', DOMAIN_NAME[cv.domain] || cv.domain)}
          ${row('范围', SCOPE_NAME[cv.scope] || cv.scope, cv.scope)}
          ${row('时间窗', WINDOW_NAME[cv.time_window] || cv.time_window, cv.time_window)}
          ${row('语言', LOCALE_NAME[cv.locale] || cv.locale)}</div></div>
      ${c.evidence ? `<div class="lum-card-solid lum-card-pad"><span class="lum-eyebrow">证据</span><div class="lum-stack-2" style="margin-top:8px">${c.evidence.map(e => `<div class="lum-row"><span class="lum-dot lum-dot-ok"></span><span class="lum-body-2 lum-mono">${e}</span></div>`).join('')}</div></div>` : ''}
      ${c.actions ? `<div class="lum-stack-2">${c.actions.map(a => global.LumSections.R.actions ? '' : '').join('')}<div id="ctx-actions"></div></div>` : ''}
    </div>`;
  }

  function renderScreen(id) {
    const sc = byId(id);
    const page = $('#lum-page');
    if (!page) return;
    if (!sc) { page.innerHTML = global.LumUI.stateBlock('error'); return; }
    page.dataset.screen = id;
    page.dataset.source = 'prototype';
    page.innerHTML = (sc.sections || []).map(s => global.LumSections.render(s)).join('');
    const shellEl = document.querySelector('.lum-shell');
    if (shellEl) shellEl.setAttribute('data-chrome', sc.chrome === 'none' ? 'none' : 'full');
    global.LumShell.setActiveRoute(id);
    global.LumShell.setContext(contextPanelFor(sc));
    const crumb = $('#lum-crumb-page'); if (crumb) crumb.textContent = global.LumI18n.t(sc.titleKey) || sc.title;
    global.LumI18n.bind(page);
    global.LumUI.init(page);
    global.LumUI.bindActions(page, sc.actionHandlers || {});
    global.LumMotion.observeReveal(page);
    // mount optical only on the 4 allowed surfaces
    $$('[data-opt]', page).forEach(n => global.LumOptical.mount(n));
    // screen-level client mounts (declarative name -> built-in deterministic filler)
    if (sc.onMountClient && CLIENT_MOUNTS[sc.onMountClient]) {
      try { CLIENT_MOUNTS[sc.onMountClient](page); } catch (e) { /* prototype never hard-crashes */ }
    }
    if (sc.onMount) try { sc.onMount(page); } catch (e) { /* prototype never hard-crashes */ }
    page.scrollTop = 0;
    document.dispatchEvent(new CustomEvent('lum:screen', { detail: { id } }));
  }

  // Deterministic, DESIGN_ONLY client mounts (no randomness, no backend)
  const CLIENT_MOUNTS = {
    fillCalendar(page) {
      const grid = page.querySelector('#cal-grid');
      if (!grid || grid.dataset.filled) return;
      const wd = ['一', '二', '三', '四', '五', '六', '日'];
      const head = wd.map(w => `<div class="lum-caption" style="text-align:center;color:var(--lum-text-3)">${w}</div>`).join('');
      // 2026-09-01 is Tuesday -> 2 leading blanks (Monday-first)
      const lead = 2, days = 30;
      let cells = '';
      for (let i = 0; i < lead; i++) cells += '<div></div>';
      for (let d = 1; d <= days; d++) {
        const lvl = (d * 7 + 3) % 5; // deterministic 0..4 density
        const tone = lvl >= 4 ? 'danger' : lvl === 3 ? 'warning' : lvl === 2 ? 'info' : '';
        const dot = lvl >= 2 ? `<span class="lum-dot ${tone ? 'lum-dot-' + tone : ''}" style="margin-top:3px"></span>` : '';
        cells += `<button type="button" class="lum-cal-cell ${tone}" data-day="${d}">${d}${dot}</button>`;
      }
      grid.innerHTML = head + cells; grid.dataset.filled = '1';
    }
  };

  function router() {
    const id = (location.hash || '').replace('#/', '') || global.LUM_FIRST || 'AI-01';
    renderScreen(id);
  }

  const DATA_TYPES = ['kpis','table','chart','events','risks','evidence','timeline','cards','runtime','upload'];
  function collectDataSections(list, acc) {
    (list || []).forEach(s => {
      if (!s || !s.type) return;
      if (s.type === 'split') { collectDataSections(s.main, acc); collectDataSections(s.side, acc); }
      else if (s.type === 'stack') { collectDataSections(s.children, acc); }
      else if (s.type === 'tabs') { (s.tabs || []).forEach(tb => collectDataSections(tb.sections, acc)); }
      else if (DATA_TYPES.indexOf(s.type) >= 0) acc.push(s);
    });
    return acc;
  }
  function renderStateBoard(id) {
    const sc = byId(id); const page = $('#lum-page'); if (!page) return;
    if (!sc) { page.innerHTML = global.LumUI.stateBlock('error'); return; }
    page.dataset.screen = id + '::state-board'; page.dataset.source = 'prototype';
    const shellEl = document.querySelector('.lum-shell');
    if (shellEl) shellEl.setAttribute('data-chrome', sc.chrome === 'none' ? 'none' : 'full');
    global.LumShell.setActiveRoute(id); global.LumShell.setContext('');
    const order = global.LumUI.STATE_ORDER || [];
    const groups = collectDataSections(sc.sections, []);
    const block = (s, i) => `<section class="lum-card lum-card-pad"><div class="lum-section-head"><span class="lum-eyebrow">${s.type} · ${s.title || '#' + i}</span>
        <h3 class="lum-h4">Ready</h3></div>${global.LumSections.render(s)}
        <div class="lum-stategrid">${order.map(k => `<div class="lum-statecell"><span class="lum-caption lum-mono">${k}</span>${global.LumUI.stateBlock(k)}</div>`).join('')}</div></section>`;
    page.innerHTML = `<div class="lum-stack-6"><div class="lum-card lum-card-pad" style="border-left:3px solid var(--lum-c-brand-500)">
        <span class="lum-eyebrow">State Board · DESIGN_ONLY</span>
        <h2 class="lum-h3" style="margin-top:6px">${global.LumI18n.t(sc.titleKey)} — 13 non-ready states</h2>
        <p class="lum-body-2 lum-text-2">Ready renders the real section; every other cell is the canonical empty/error/permission state. No fake success.</p></div>
        ${groups.map(block).join('')}</div>`;
    global.LumI18n.bind(page); global.LumUI.init(page); global.LumMotion.observeReveal(page);
    document.body.setAttribute('data-lum-ready', 'true');
  }

  function boot() {
    global.LumShell.mountShell({ contextOpen: !global.LUM_STANDALONE && !global.LUM_STATE_BOARD ? true : false, title: '' });
    global.LumI18n.setLocale(global.LUM_LOCALE || 'zh-CN');
    global.LumOptical.init(document);
    if (global.LUM_STATE_BOARD) { renderStateBoard(global.LUM_STATE_BOARD); }
    else if (global.LUM_STANDALONE) { renderScreen(global.LUM_STANDALONE); }
    else { global.LUM_FIRST = global.LUM_FIRST || Object.keys(screens())[0]; window.addEventListener('hashchange', router); router(); }
    // global demo controls (language / optical) if present
    document.addEventListener('change', e => {
      if (e.target.dataset && e.target.dataset.locale) global.LumI18n.setLocale(e.target.value);
    });
    document.body.setAttribute('data-lum-ready', 'true');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  global.LumApp = { renderScreen, router };
})(window);
