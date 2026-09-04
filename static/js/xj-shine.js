/* =============================================================================
 * 序境 Xujing · 微光银表驱动引擎 v1.0
 *  - 数据表驱动：6 组方向向量随机分配给每张卡（海浪波纹划过方向随机）
 *  - 扩散：各产品面板统一挂 .xj-card-silver（panel/card），动态新增面板由 MutationObserver 补标
 *  - 尊重 prefers-reduced-motion（直接返回，CSS 同时关闭）
 * ========================================================================== */
(function () {
  'use strict';
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) { return; }

  /* 方向数据表（起点→终点，单位 %，相对卡片覆盖块） */
  var DIRS = [
    { x0: '-90%', y0: '-12%', x1: '34%',  y1: '14%' },  /* 左上→右下 */
    { x0: '90%',  y0: '-14%', x1: '-34%', y1: '12%' },  /* 右上→左下 */
    { x0: '-14%', y0: '-90%', x1: '12%',  y1: '34%' },  /* 上→下 */
    { x0: '-12%', y0: '90%',  x1: '10%',  y1: '-34%' }, /* 下→上 */
    { x0: '-80%', y0: '-34%', x1: '28%',  y1: '28%' },  /* 陡对角 */
    { x0: '80%',  y0: '-30%', x1: '-28%', y1: '26%' }   /* 反陡对角 */
  ];

  function live(el) {
    var d = DIRS[(Math.random() * DIRS.length) | 0];
    el.style.setProperty('--xj-shine-x0', d.x0);
    el.style.setProperty('--xj-shine-y0', d.y0);
    el.style.setProperty('--xj-shine-x1', d.x1);
    el.style.setProperty('--xj-shine-y1', d.y1);
    if (!el.classList.contains('is-live')) { el.classList.add('is-live'); }
  }

  /* ---- 玻璃质感参数表（函数驱动：数据表 → 函数计算 → 运行时应用）---- */
  var GLASS = {
    bgTop: 'rgba(255,255,255,.82)',
    bgBottom: 'rgba(255,255,255,.52)',
    blur: 14,
    sat: 1.35,
    border: 'rgba(255,255,255,.72)',
    radius: '10px'
  };

  /* 玻璃纯函数：由参数表计算并应用为内联 !important（绕开历史皮肤 CSS 级联，保证统一质感） */
  function glassify(el) {
    el.style.setProperty('background',
      'linear-gradient(180deg, ' + GLASS.bgTop + ', ' + GLASS.bgBottom + ')', 'important');
    el.style.setProperty('-webkit-backdrop-filter',
      'blur(' + GLASS.blur + 'px) saturate(' + GLASS.sat + ')', 'important');
    el.style.setProperty('backdrop-filter',
      'blur(' + GLASS.blur + 'px) saturate(' + GLASS.sat + ')', 'important');
    el.style.setProperty('border', '1px solid ' + GLASS.border, 'important');
    el.style.setProperty('border-radius', GLASS.radius, 'important');
  }

  var PANEL_SELECTOR = '.panel.glass-card, .panel, .glass-card, .metric-card, .home-card, ' +
    '.smart-card, .osai-module-card, .ev-stat-card, .case-card, .brand-card, .smart-center, ' +
    '.report-card, .event-card';

  function markAll() {
    document.querySelectorAll(PANEL_SELECTOR).forEach(function (el) {
      if (!el.classList.contains('xj-card-silver')) { el.classList.add('xj-card-silver'); }
      if (!el.classList.contains('is-live')) { live(el); }
      glassify(el);
    });
  }

  function init() {
    markAll();
    /* 动态新增面板：轻量补标（rAF 防抖），不重复设随机方向 */
    var mo = new MutationObserver(function (muts) {
      var need = false;
      for (var i = 0; i < muts.length; i++) {
        if (muts[i].addedNodes.length) { need = true; break; }
      }
      if (need && window.requestAnimationFrame) {
        window.requestAnimationFrame(markAll);
      } else if (need) { markAll(); }
    });
    if (document.body) { mo.observe(document.body, { childList: true, subtree: true }); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();
