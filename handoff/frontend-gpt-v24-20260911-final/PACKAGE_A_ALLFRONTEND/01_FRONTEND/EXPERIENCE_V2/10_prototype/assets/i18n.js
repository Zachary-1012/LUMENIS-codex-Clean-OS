/* ============================================================================
 * LUMENIS Experience V2 — i18n runtime
 * Four-layer naming (Supplement V2.1 sec14):
 *   MACHINE ID -> SEMANTIC KEY -> COPY ALIAS -> LOCALE VALUE
 *   e.g. cth / domain.cth.name / product.commerce.name / 序境·商业运营
 * Fixed UI copy ALWAYS comes from keys. Business data (subjects, brands, posts,
 * events, campaigns) comes from the ViewModel and is NEVER put in locale files.
 * Locales: zh-CN / en / ko + pseudo-expanded (130%/150%) text-stress mode.
 * Missing keys are surfaced (key wrapped in ⟦⟧) and counted — never silently faked.
 * Bundle is injected as window.LUM_COPY (works from file:// without fetch/CORS).
 * ========================================================================== */
(function (global) {
  'use strict';
  const SUPPORTED = ['zh-CN', 'en', 'ko'];
  const state = { locale: 'zh-CN', missing: [], bundle: (global.LUM_COPY || {}) };
  const alias = (global.LUM_COPY_ALIAS || {}); // alias -> semantic key

  function resolveKey(key) { return alias[key] || key; }
  function lookup(locale, key) {
    const b = state.bundle[locale] || {};
    return key.split('.').reduce((o, k) => (o == null ? undefined : o[k]), b);
  }
  function t(key, vars) {
    const sem = resolveKey(key);
    let v = lookup(state.locale, sem) ?? lookup('zh-CN', sem);
    if (v == null) { // surface, do not fake
      if (!state.missing.includes(sem)) state.missing.push(sem);
      v = '⟦' + sem + '⟧';
    }
    if (vars) Object.keys(vars).forEach(k => { v = String(v).replace(new RegExp('\\{' + k + '\\}', 'g'), vars[k]); });
    if (state.locale === 'pseudo') v = pseudoExpand(lookup('zh-CN', sem) ?? v);
    return v;
  }
  /** 130%/150% stress: pad latin words and add CJK width markers to expose overflow. */
  function pseudoExpand(s) {
    const target = global.LUM_STRESS || 1.3;
    const raw = String(s);
    const pad = Math.round(raw.length * (target - 1));
    return '⟨' + raw + '�' .repeat(Math.max(0, pad)) + '⟩';
  }
  function setLocale(loc) {
    state.locale = loc === 'pseudo' ? 'pseudo' : (SUPPORTED.includes(loc) ? loc : 'zh-CN');
    document.documentElement.lang = state.locale === 'zh-CN' ? 'zh-Hans' : state.locale;
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const k = el.getAttribute('data-i18n'); el.textContent = t(k);
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => el.setAttribute('placeholder', t(el.getAttribute('data-i18n-ph'))));
    document.dispatchEvent(new CustomEvent('lum:locale', { detail: { locale: state.locale } }));
  }
  /** Apply translations to a freshly rendered subtree. */
  function bind(root = document) {
    root.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.getAttribute('data-i18n')); });
    root.querySelectorAll('[data-i18n-ph]').forEach(el => el.setAttribute('placeholder', t(el.getAttribute('data-i18n-ph'))));
  }
  global.LumI18n = { t, setLocale, bind, state, SUPPORTED, pseudoExpand };
})(window);
