/* ============================================================================
 * LUMENIS Experience V2.5 — Brand system (Lumen Mark)
 * 哲学保留：芥子纳须弥 · 一点开境 (a point opens a realm)；小→大→归一。
 * 视觉收敛进 V2.5 单色金属生态：Point(icy) + Axis + 双层 Boundary，
 * 全部 currentColor，黑银/白银自动反相；不再使用旧版彩色液态海/紫靛金。
 *
 * 三版本（Logo Master Brief §3，材质按新生态重制，结构不丢）：
 *   standard = mark + 序境 + LUMENIS
 *   korean   = mark + 서경 + LUMENIS
 *   symbol   = mark only（favicon / app icon / 小尺寸 16/24/32/64）
 * Codex 契约：window.LumBrand.mark()/lockup()/mount(); [data-lum-brand].
 * 不写死颜色/尺寸，全部继承 token；旧手写体归档，正式字标用 display serif。
 * ========================================================================== */
(function (global) {
  'use strict';

  // The symbol: a vertical 序轴 through a two-strata vessel (滴中纳海）, one icy Point.
  function mark(svgClass) {
    return `<svg class="lum-brand-mark${svgClass ? ' ' + svgClass : ''}" viewBox="0 0 48 64" fill="none"
      xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LUMENIS" focusable="false">
      <line class="lum-brand-axis" x1="24" y1="1.5" x2="24" y2="62.5" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
      <path class="lum-brand-boundary-outer" d="M24 5.5 C15 18.5 12.5 28.5 24 40.5 C35.5 28.5 33 18.5 24 5.5 Z"
        stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
      <path class="lum-brand-boundary-inner" d="M24 13 C19.2 21.5 18 28.2 24 35.2 C30 28.2 28.8 21.5 24 13 Z"
        stroke="currentColor" stroke-width="1" stroke-linejoin="round"/>
      <circle class="lum-brand-core" cx="24" cy="28.6" r="2.1" fill="currentColor"/>
      <circle class="lum-brand-point" cx="24" cy="5.5" r="2.4"/>
    </svg>`;
  }

  function word(locale) {
    if (locale === 'ko') return { cjk: '서경', lat: 'LUMENIS' };
    return { cjk: '序境', lat: 'LUMENIS' };
  }

  // variant: standard | korean | symbol ; size in px (controls height)
  function lockup(opts = {}) {
    const locale = opts.locale || 'zh-CN';
    const variant = opts.variant || 'standard';
    if (variant === 'symbol') return `<span class="lum-brand lum-brand--symbol">${mark()}</span>`;
    const w = word(locale === 'ko' ? 'ko' : 'zh');
    return `<span class="lum-brand lum-brand--${variant}">
      ${mark()}
      <span class="lum-brand__txt">
        <span class="lum-brand__cjk">${w.cjk}</span>
        <span class="lum-brand__lat">${w.lat}</span>
      </span></span>`;
  }

  function mount(root) {
    (root || document).querySelectorAll('[data-lum-brand]:not([data-brand-mounted])').forEach(el => {
      el.dataset.brandMounted = '1';
      const variant = el.dataset.lumBrand || 'standard';
      const locale = el.dataset.lumLocale || (global.LUM_LOCALE || 'zh-CN');
      el.innerHTML = lockup({ variant, locale });
    });
  }

  function favicon() {
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 64'>
<g fill='none' stroke='%2314161B' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
<line x1='24' y1='2' x2='24' y2='62'/><path d='M24 6 C15 19 13 29 24 41 C35 29 33 19 24 6 Z'/>
<path d='M24 14 C19 22 18 28 24 35 C30 28 29 22 24 14 Z'/></g>
<circle cx='24' cy='29' r='2.6' fill='%2314161B'/><circle cx='24' cy='6' r='3' fill='%234FC4E8'/></svg>`;
    const href = "data:image/svg+xml," + svg.replace(/\n\s*/g, '');
    let l = document.querySelector('link[rel="icon"]');
    if (!l) { l = document.createElement('link'); l.rel = 'icon'; document.head.appendChild(l); }
    l.href = href; l.type = 'image/svg+xml';
  }

  global.LumBrand = { mark, lockup, mount, favicon, word };

  // favicon once; auto-mount lockups now and whenever the shell re-renders.
  function boot() { favicon(); mount(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  if ('MutationObserver' in global) {
    const mo = new MutationObserver(es => { for (const e of es) if (e.addedNodes.length) mount(); });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  }
})(window);
