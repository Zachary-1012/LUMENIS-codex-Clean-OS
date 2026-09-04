/* =============================================================================
 * 序境 Xujing · 表驱动 Reveal 进入动效 v1.0
 * 方法学（GitHub 前沿研究 2026-09）：
 *   - IntersectionObserver + CSS 变量级联（stagger），fire-once，零依赖
 *   - 单组级联 75ms 阶梯、上限 400ms（卡片栅格 sweet spot）
 *   - 延迟由子元素索引计算（数据表驱动），禁硬编码动画
 *   - 尊重 prefers-reduced-motion（CSS 已强制显示，脚本仅负责触发 is-visible）
 * 用法：容器加 data-xj-reveal="pop"（可选值 pop/slide），进入视口时直接子元素依次入场。
 * ========================================================================== */
(function () {
  'use strict';
  if (!('IntersectionObserver' in window)) { return; }

  var STAGGER_MS = 75;   // 每子项级联间隔
  var MAX_MS = 400;      // 单组总级联上限

  function init() {
    var boxes = document.querySelectorAll('[data-xj-reveal]');
    if (!boxes.length) { return; }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        var box = entry.target;
        var kids = Array.prototype.slice.call(box.children);
        kids.forEach(function (k, i) {
          k.style.setProperty('--xj-delay', Math.min(i * STAGGER_MS, MAX_MS) + 'ms');
        });
        box.classList.add('is-visible');
        io.unobserve(box); // fire-once，避免重复触发
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    boxes.forEach(function (b) { io.observe(b); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
