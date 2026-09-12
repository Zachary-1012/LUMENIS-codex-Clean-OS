/* ============================================================================
 * LUMENIS V2.5 — Launch / cold-start sequence (Brief §4/§11, re-skinned metal)
 * Decoupled from data loading: it never blocks app boot or interaction.
 *   full  ≈ 2.1s cold start (S0 point→drop→sea→world→return→settle→word)
 *   short ≈ 0.8s re-entry / low-power
 * Reduced-motion / low-power → static mark, ~0.65s, no motion.
 * Locale: ko renders 서경. Componentised (no baked frame).
 * ========================================================================== */
(function (global) {
  'use strict';
  const reduce = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)').matches : false;
  const lowPower = (navigator.hardwareConcurrency || 8) <= 4;

  function cjk(locale) { return locale === 'ko' ? '서경' : '序境'; }

  function play(opts = {}) {
    const locale = opts.locale || global.LUM_LOCALE || 'zh-CN';
    const short = opts.short || false;
    const root = document.createElement('div');
    root.className = 'lum-launch' + (short || reduce ? ' is-short' : '');
    root.setAttribute('aria-hidden', 'true');
    root.innerHTML = `
      <div class="lum-launch__stage">
        <div class="lum-launch__drop"></div>
        <div class="lum-launch__sea"></div>
        <div class="lum-launch__mark">${global.LumBrand.mark()}</div>
        <div class="lum-launch__word">
          <span class="cjk">${cjk(locale)}</span>
          <span class="lat">LUMENIS</span>
        </div>
      </div>`;
    // Mount INSIDE .lum-app so the overlay inherits design tokens + theme/realm
    // (mounting on <body> leaves var(--lum-*) unresolved and invalidates the
    // animation shorthand, leaving the mark stuck at opacity:0).
    (document.querySelector('.lum-app') || document.body).appendChild(root);
    const dur = reduce ? 700 : short ? 920 : 2320;
    setTimeout(() => { root.remove(); document.documentElement.classList.add('lum-launched'); }, dur);
    return root;
  }

  // Auto cold-start once per session; callers may force via play().
  function auto() {
    try { if (sessionStorage.getItem('lum-launched')) return; } catch (e) {}
    play({ short: lowPower && !reduce });
    try { sessionStorage.setItem('lum-launched', '1'); } catch (e) {}
  }

  global.LumLaunch = { play, auto, reduced: reduce, lowPower };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto, { once: true });
  else auto();
})(window);
