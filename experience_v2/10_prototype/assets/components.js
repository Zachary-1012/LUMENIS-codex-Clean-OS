/* ============================================================================
 * LUMENIS Experience V2 — Component behaviors (vanilla, framework-free)
 * Toast / Modal / Drawer / Tabs / Segmented / count-up / sparkline / donut /
 * Action confirm (4 action classes) / universal state blocks.
 * Prototype only: NAVIGATION & QUERY fully interactive; DRAFT local;
 * EFFECT renders scope/target/permission + confirm + pending/success/error UI
 * but NEVER executes a real backend effect (no fake endpoint, no fake 200).
 * ========================================================================== */
(function (global) {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const NS = 'http://www.w3.org/2000/svg';
  function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function icon(name, size = 18) { return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${(global.LUM_ICONS || {})[name] || ''}</svg>`; }

  /* ---------------- Toast ---------------- */
  function toastStack() { let s = $('.lum-toast-stack'); if (!s) { s = el('div', 'lum-toast-stack'); s.setAttribute('role', 'status'); s.setAttribute('aria-live', 'polite'); document.body.appendChild(s); } return s; }
  function toast(message, tone = 'info', ms = 3200) {
    const t = el('div', 'lum-toast'); t.dataset.tone = tone;
    t.innerHTML = `${icon(tone === 'success' ? 'check' : tone === 'error' ? 'alert' : 'info')}<span></span>`;
    t.querySelector('span').textContent = message;
    toastStack().appendChild(t);
    LumMotion.contentIn(t, 'content');
    setTimeout(() => { t.classList.add('lum-closing'); setTimeout(() => t.remove(), 220); }, ms);
  }

  /* ---------------- Modal / Drawer ---------------- */
  function openModal(idOrNode, title, bodyHtml, footHtml) {
    let ov = typeof idOrNode === 'string' ? $('#' + idOrNode) : idOrNode;
    if (!ov) {
      ov = el('div', 'lum-overlay'); ov.id = idOrNode || ('m' + Date.now());
      ov.innerHTML = `<div class="lum-modal" role="dialog" aria-modal="true" aria-label="${title || ''}">
        <div class="lum-modal__head"><h3 class="lum-h3">${title || ''}</h3><button class="lum-iconbtn" data-close aria-label="Close">${icon('x')}</button></div>
        <div class="lum-modal__body">${bodyHtml || ''}</div>${footHtml ? `<div class="lum-modal__foot">${footHtml}</div>` : ''}</div>`;
      document.body.appendChild(ov);
      ov.addEventListener('click', e => { if (e.target === ov || e.target.closest('[data-close]')) closeModal(ov); });
    }
    requestAnimationFrame(() => ov.classList.add('is-open'));
    const c = $('.lum-modal', ov); c && LumMotion.contentIn(c, 'scale');
    return ov;
  }
  function closeModal(ov) { if (!ov) return; ov.classList.remove('is-open'); setTimeout(() => { if (ov.dataset.ephemeral !== 'keep') ov.remove(); }, 320); }
  function openDrawer(id, title, bodyHtml) {
    let d = $('#' + id);
    const host = $('.lum-app') || document.body;
    if (!d) { d = el('aside', 'lum-drawer'); d.id = id; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true');
      d.innerHTML = `<div class="lum-modal__head"><h3 class="lum-h3">${title || ''}</h3><button class="lum-iconbtn" data-close aria-label="Close">${icon('x')}</button></div><div class="lum-grow" style="overflow:auto;padding:0 20px 20px">${bodyHtml || ''}</div>`;
      host.appendChild(d); d.querySelector('[data-close]').onclick = () => closeDrawer(d); }
    else if (d.parentNode !== host) { host.appendChild(d); }
    requestAnimationFrame(() => d.classList.add('is-open')); return d;
  }
  function closeDrawer(d) { if (!d) return; d.classList.remove('is-open'); }

  /* ---------------- Tabs / Segmented (with morph) ---------------- */
  function bindTabs(root, onChange) {
    $$('.lum-tabs button', root).forEach(btn => btn.addEventListener('click', () => {
      $$('.lum-tabs button', root).forEach(b => b.setAttribute('aria-selected', b === btn ? 'true' : 'false'));
      const panel = $(btn.getAttribute('data-target'));
      $$('[data-panel]', root).forEach(p => { if (p !== panel) p.classList.add('lum-hide'); });
      if (panel) { panel.classList.remove('lum-hide'); LumMotion.contentIn(panel, 'settle'); }
      onChange && onChange(btn.dataset.tab, panel);
    }));
  }
  function bindSegmented(root, onChange) {
    $$('.lum-segmented button', root).forEach(btn => btn.addEventListener('click', () => {
      $$('.lum-segmented button', root).forEach(b => b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'));
      onChange && onChange(btn.dataset.val, btn);
    }));
  }

  /* ---------------- Sparkline (inline SVG, deterministic from points) ---------------- */
  let _sparkSeq = 0;
  function sparkline(points, { w = 120, h = 40, color = 'var(--lum-c-brand-500)', fill = true } = {}) {
    const min = Math.min(...points), max = Math.max(...points), span = (max - min) || 1;
    const X = i => (i / (points.length - 1)) * w, Y = v => h - 3 - ((v - min) / span) * (h - 6);
    const d = points.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1)).join(' ');
    const area = `${d} L${w} ${h} L0 ${h} Z`;
    const gid = 'lum-spark-g' + (++_sparkSeq);
    return `<svg class="lum-metric__spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
      <defs><linearGradient id="${gid}" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="var(--lum-c-brand-500)"/><stop offset="1" stop-color="var(--lum-c-icy-500,#4FC4E8)"/>
      </linearGradient></defs>
      ${fill ? `<path d="${area}" fill="url(#${gid})" opacity=".14"/>` : ''}<path d="${d}" fill="none" stroke="url(#${gid})" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  }
  function donut(pct, label) { return `<div class="lum-donut" style="--p:${pct}"><b>${label ?? pct + '%'}</b></div>`; }

  /* ---------------- Universal state blocks (11 states) ---------------- */
  const STATE_COPY = {
    empty_true: ['inbox', 'state.empty_true', 'state.empty_true_d'],
    empty_notcollected: ['download', 'state.empty_notcollected', 'state.empty_notcollected_d'],
    empty_filter: ['filter', 'state.empty_filter', 'state.empty_filter_d'],
    empty_permission: ['lock', 'state.empty_permission', 'state.empty_permission_d'],
    error: ['alert', 'state.error', 'state.error_d'],
    offline: ['wifi-off', 'state.offline', 'state.offline_d'],
    blocked: ['shield-off', 'state.blocked', 'state.blocked_d'],
    loading: ['loader', 'state.loading', 'state.loading_d'],
    updating: ['loader', 'state.updating', 'state.updating_d'],
    partial: ['layers', 'state.partial', 'state.partial_d'],
    stale: ['clock', 'state.stale', 'state.stale_d'],
    degraded: ['alert', 'state.degraded', 'state.degraded_d'],
    permission_denied: ['lock', 'state.permission_denied', 'state.permission_denied_d']
  };
  // canonical non-ready state order for state boards (Ready rendered separately)
  const STATE_ORDER = ['loading', 'updating', 'partial', 'stale', 'degraded', 'empty_true',
    'empty_notcollected', 'empty_filter', 'empty_permission', 'permission_denied', 'blocked', 'offline', 'error'];
  function stateBlock(kind, actionsHtml = '') {
    const [ic, title, desc] = STATE_COPY[kind] || STATE_COPY.empty_true;
    const t = global.LumI18n ? global.LumI18n.t : k => k;
    return `<div class="lum-state" data-kind="${kind.replace(/_.*$/, '')}">
      <div class="lum-state__ico">${icon(ic, 26)}</div>
      <div class="lum-state__title" data-i18n="${title}">${t(title)}</div>
      <div class="lum-state__desc" data-i18n="${desc}">${t(desc)}</div>
      ${actionsHtml ? `<div class="lum-state__actions">${actionsHtml}</div>` : ''}</div>`;
  }
  /** skeleton set */
  function skeletonRows(n = 4) { return Array.from({ length: n }, () => '<div class="lum-skeleton" style="height:16px;margin:10px 0"></div>').join(''); }

  /* ---------------- Action handling (4 classes) ----------------
   * NAVIGATION: route; QUERY: local filter/refetch(UI); DRAFT: local edit;
   * EFFECT: must show scope/target/permission + confirm; high-risk never blue. */
  function bindActions(root, handlers = {}) {
    $$('[data-action]', root).forEach(node => {
      if (node.dataset.bound) return; node.dataset.bound = '1';
      node.addEventListener('click', ev => {
        const a = node.dataset.action, cls = node.dataset.actClass || 'NAVIGATION';
        LumMotion.press(node);
        if (cls === 'EFFECT') return confirmEffect(node, handlers[a]);
        if (handlers[a]) handlers[a](node, ev);
      });
    });
  }
  function confirmEffect(node, run) {
    const scope = node.dataset.scope || 'UNKNOWN', target = node.dataset.target || 'UNKNOWN', perm = node.dataset.permission || 'UNKNOWN';
    const risk = node.dataset.risk === 'high';
    const t = global.LumI18n ? global.LumI18n.t : k => k;
    openModal('effect-confirm', t('action.confirm_title'), `
      <div class="lum-stack-4">
        <div class="lum-row"><span class="lum-caption" style="width:96px">${t('action.scope')}</span><code class="lum-mono">${scope}</code></div>
        <div class="lum-row"><span class="lum-caption" style="width:96px">${t('action.target')}</span><code class="lum-mono">${target}</code></div>
        <div class="lum-row"><span class="lum-caption" style="width:96px">${t('action.permission')}</span><code class="lum-mono">${perm}</code></div>
        <p class="lum-body-2">${t('action.prototype_notice')}</p>
      </div>`,
      `<button class="lum-btn lum-btn-ghost" data-close>${t('common.cancel')}</button>
       <button class="lum-btn ${risk ? 'lum-btn-effect-risk' : 'lum-btn-primary'}" id="effect-ok">${t('common.confirm')}</button>`);
    $('#effect-ok').onclick = () => {
      closeModal($('#effect-confirm'));
      if (node.dataset.action === 'archive-dead-workers' && global.LumRuntime &&
          typeof global.LumRuntime.archiveDeadWorkers === 'function') {
        global.LumRuntime.archiveDeadWorkers(node);
        return;
      }
      // Prototype: show pending then an explicit "not wired" result — never fake success.
      toast(t('action.not_wired_to_backend'), 'info');
      run && run(node);
    };
  }

  function init(root = document) {
    $$('[data-countup]').forEach(n => { const to = parseFloat(n.dataset.countup); LumMotion.countUp(n, to, { decimals: parseInt(n.dataset.decimals || 0) }); });
    bindTabs(root);
  }
  global.LumUI = { $, $$, el, icon, toast, openModal, closeModal, openDrawer, closeDrawer, bindTabs, bindSegmented,
    sparkline, donut, stateBlock, skeletonRows, bindActions, init, STATE_ORDER };
})(window);
