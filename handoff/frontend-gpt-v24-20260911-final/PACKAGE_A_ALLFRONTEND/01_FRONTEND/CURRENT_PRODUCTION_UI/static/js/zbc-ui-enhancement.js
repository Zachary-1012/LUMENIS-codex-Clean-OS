/**
 * LUMENIS UI Enhancement JS v2.1
 * 交互细节 + 数据展示 + 性能 综合增强
 * 依赖：无（纯原生JS）
 */
(function () {
  'use strict';

  // ========== 1. 页面转场动画 ==========
  function initPageTransitions() {
    const main = document.querySelector('.zbc-main-content, .main-content, main');
    if (main && !main.classList.contains('zbc-page-enter')) {
      main.classList.add('zbc-page-enter');
    }
    // 给所有section加交错入场
    document.querySelectorAll('.zbc-section, section, .dashboard-section').forEach((el, i) => {
      if (!el.style.animationDelay) {
        el.style.animationDelay = Math.min(i * 0.05, 0.3) + 's';
      }
    });
  }

  // ========== 2. KPI 数字滚动动画 ==========
  function animateNumber(el, target, duration = 800) {
    const start = 0;
    const startTime = performance.now();
    const isFloat = target % 1 !== 0;

    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + (target - start) * eased;
      el.textContent = isFloat ? current.toFixed(1) : Math.round(current).toLocaleString();
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  function initKPICountUp() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const raw = el.dataset.count || el.textContent.trim();
          const num = parseFloat(raw.replace(/[^0-9.]/g, ''));
          if (!isNaN(num) && num > 0 && !el.dataset.animated) {
            el.dataset.animated = 'true';
            animateNumber(el, num);
          }
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.3 });

    document.querySelectorAll('.zbc-kpi-card__value, .stat-value, [data-count], [data-kpi]').forEach(el => {
      observer.observe(el);
    });
  }

  // ========== 3. 表格行交错入场 ==========
  function initTableStagger() {
    document.querySelectorAll('.zbc-table tbody, table tbody').forEach(tbody => {
      const rows = tbody.querySelectorAll('tr');
      rows.forEach((row, i) => {
        row.style.opacity = '0';
        row.style.transform = 'translateX(-8px)';
        row.style.transition = `opacity 0.3s ease ${Math.min(i * 0.02, 0.4)}s, transform 0.3s ease ${Math.min(i * 0.02, 0.4)}s`;
      });
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            rows.forEach(row => {
              row.style.opacity = '1';
              row.style.transform = 'translateX(0)';
            });
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 });
      observer.observe(tbody);
    });
  }

  // ========== 4. 懒加载 ==========
  function initLazyLoad() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          if (el.dataset.src) {
            el.src = el.dataset.src;
            el.removeAttribute('data-src');
          }
          el.classList.add('is-loaded');
          observer.unobserve(el);
        }
      });
    }, { rootMargin: '100px' });

    document.querySelectorAll('.zbc-lazy, [data-src]').forEach(el => observer.observe(el));
  }

  // ========== 5. Toast 通知系统 ==========
  window.ZBCToast = {
    show(message, type = 'info', duration = 3000) {
      const toast = document.createElement('div');
      toast.className = `zbc-toast zbc-toast--${type}`;
      toast.textContent = message;
      document.body.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
      }, duration);
    },
    success(msg) { this.show(msg, 'success'); },
    error(msg) { this.show(msg, 'error'); },
    warning(msg) { this.show(msg, 'warning'); },
    info(msg) { this.show(msg, 'info'); }
  };

  // ========== 6. 模态框统一 ==========
  window.ZBCModal = {
    open(content, options = {}) {
      const overlay = document.createElement('div');
      overlay.className = 'zbc-modal-overlay';
      overlay.innerHTML = `<div class="zbc-modal" style="width:${options.width || '520px'};padding:${options.padding || '24px'}">${content}</div>`;
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) this.close(overlay);
      });
      document.body.appendChild(overlay);
      document.body.style.overflow = 'hidden';
      return overlay;
    },
    close(overlay) {
      overlay.style.opacity = '0';
      overlay.style.transition = 'opacity 0.2s ease';
      setTimeout(() => {
        overlay.remove();
        document.body.style.overflow = '';
      }, 200);
    }
  };

  // ========== 7. 数据更新闪烁提示 ==========
  window.ZBCDataFlash = {
    flash(el) {
      el.style.transition = 'background 0.5s ease';
      el.style.background = 'rgba(0, 212, 170, 0.15)';
      setTimeout(() => { el.style.background = ''; }, 500);
    }
  };

  // ========== 8. 性能：防抖/节流工具 ==========
  window.ZBCUtils = {
    debounce(fn, delay = 300) {
      let timer;
      return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
      };
    },
    throttle(fn, limit = 300) {
      let inThrottle;
      return function (...args) {
        if (!inThrottle) {
          fn.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    }
  };

  // ========== 9. 初始化 ==========
  function init() {
    initPageTransitions();
    initKPICountUp();
    initTableStagger();
    initLazyLoad();
  }

  // DOM 就绪后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 路由切换后重新初始化（SPA场景）
  if (window.MutationObserver) {
    const mo = new MutationObserver(ZBCUtils.debounce(() => {
      initKPICountUp();
      initLazyLoad();
    }, 500));
    mo.observe(document.body, { childList: true, subtree: true });
  }

  console.log('[LUMENIS UI Enhancement] v2.1 已加载');
})();
