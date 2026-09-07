// ZBC Motion System — 全局动效注入
// 自动给KPI/卡片/表格/数字应用设计系统动效
(function() {
  'use strict';

  const MOTION_ENABLED = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // KPI数字count-up动画
  function animateCountUp(el) {
    if (!MOTION_ENABLED) return;
    const target = parseFloat(el.dataset.countTarget || el.textContent.replace(/[^0-9.\-]/g, ''));
    if (isNaN(target) || target === 0) return;

    const duration = 800;
    const start = performance.now();
    const prefix = el.textContent.match(/^[^\d]*/)?.[0] || '';
    const suffix = el.textContent.match(/[^\d]*$/)?.[0] || '';
    const decimals = (el.textContent.match(/\.\d+/)?.[0] || '').length - 1;

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      const current = target * eased;
      el.textContent = prefix + current.toFixed(decimals > 0 ? decimals : 0) + suffix;
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // Intersection Observer：元素进入视口时触发动画
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        const el = entry.target;
        // 入场动画
        if (el.classList.contains('zbc-enter')) {
          el.style.animationPlayState = 'running';
        }
        // 数字滚动
        if (el.classList.contains('zbc-count-up') || el.dataset.countUp) {
          animateCountUp(el);
        }
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

  // 自动给常见元素添加动效class
  function autoApplyMotion() {
    if (!MOTION_ENABLED) return;

    // KPI卡片：入场+数字滚动
    document.querySelectorAll('.kpi-card, .stat-card, .metric-card, [class*="kpi"]').forEach((card, i) => {
      if (!card.classList.contains('zbc-enter')) {
        card.classList.add('zbc-enter');
        card.style.animationDelay = (i * 0.05) + 's';
      }
      // 卡片内的大数字
      card.querySelectorAll('[class*="value"], [class*="number"], [class*="count"], h1, h2, .big-number').forEach(num => {
        if (!num.classList.contains('zbc-count-up')) {
          num.classList.add('zbc-count-up');
        }
      });
    });

    // 数据卡片/面板：交错入场
    document.querySelectorAll('.zbc-card, .card, .panel, [class*="card"]:not(.kpi-card):not(.stat-card)').forEach((card, i) => {
      if (!card.classList.contains('zbc-enter') && !card.closest('.modal') && !card.closest('.zbc-browser-panel')) {
        card.classList.add('zbc-enter');
        card.style.animationDelay = Math.min(i * 0.03, 0.3) + 's';
      }
    });

    // 表格行：交错入场
    document.querySelectorAll('tbody tr').forEach((row, i) => {
      if (!row.classList.contains('zbc-enter')) {
        row.classList.add('zbc-enter');
        row.style.animationDelay = Math.min(i * 0.02, 0.4) + 's';
        row.style.animationDuration = '0.3s';
      }
    });

    // 按钮hover微交互
    document.querySelectorAll('.zbc-btn, button:not(.zbc-browser-panel__btn)').forEach(btn => {
      btn.style.transition = 'all 0.2s var(--zbc-ease)';
    });

    // 观察所有动效元素
    document.querySelectorAll('.zbc-enter, .zbc-count-up, [data-count-up]').forEach(el => {
      observer.observe(el);
    });
  }

  // 数据更新时的平滑过渡
  window.ZBCMotion = {
    refresh: function() {
      autoApplyMotion();
    },
    countUp: function(el, target) {
      el.dataset.countTarget = target;
      animateCountUp(el);
    },
    flashUpdate: function(el) {
      // 数据更新时的闪烁提示
      el.style.transition = 'background 0.3s';
      el.style.background = 'var(--zbc-primary-light)';
      setTimeout(() => { el.style.background = ''; }, 500);
    }
  };

  // 页面加载后自动应用
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(autoApplyMotion, 100);
    });
  } else {
    setTimeout(autoApplyMotion, 100);
  }

  // 路由切换后重新应用（SPA模式）
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(autoApplyMotion, 200);
    }
  }).observe(document, { subtree: true, childList: true });

  console.log('[ZBCMotion] 全局动效系统已就绪' + (MOTION_ENABLED ? '' : ' (reduced-motion已禁用)'));
})();
