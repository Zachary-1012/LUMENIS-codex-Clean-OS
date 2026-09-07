/* ============================================================================
   motion-bridge.js — Phase5b Motion 动态化桥接层
   职责：将 ZBCMotion（adaptive-motion.js）能力自动接入业务页面常见模式
   - KPI 数值 count-up（[data-kpi] 元素，数据真变才动）
   - 趋势图平滑过渡（[data-chart] 容器，旧图不瞬现）
   - 横向滑动模组自动初始化（.carousel-container）
   - prefers-reduced-motion 全局降级
   依赖：adaptive-motion.js（window.ZBCMotion）、carousel.js、lumenis-motion-engine.js
   加载顺序：在 adaptive-motion.js + carousel.js 之后加载
   ============================================================================ */
(function() {
  'use strict';

  var Motion = window.ZBCMotion || window.AdaptiveMotion;
  var reduced = false;

  // 检测 reduced motion
  try {
    reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function(e) {
      reduced = e.matches;
    });
  } catch(e) { reduced = false; }

  // ===== 1. KPI Count-Up 自动接入 =====
  /**
   * 对 [data-kpi] 元素启用 count-up 监控
   * 用法：<span data-kpi data-kpi-value="123">123</span>
   * 或调用 window.MotionBridge.updateKPI(el, newValue)
   */
  function initKPICountUp() {
    if (reduced) return;
    document.querySelectorAll('[data-kpi]').forEach(function(el) {
      if (el._kpiInitialized) return;
      el._kpiInitialized = true;
      var initial = parseFloat(el.getAttribute('data-kpi-value') || el.textContent || '0');
      if (!isNaN(initial)) {
        el.setAttribute('data-kpi-value', initial);
      }
    });
  }

  /**
   * 更新 KPI 数值，自动 count-up
   * @param {HTMLElement|string} el - 元素或选择器
   * @param {number} newValue - 新数值
   * @param {object} opts - { decimals, prefix, suffix, duration }
   */
  function updateKPI(el, newValue, opts) {
    if (typeof el === 'string') el = document.querySelector(el);
    if (!el) return;
    if (Motion && Motion.updateKPI) {
      Motion.updateKPI(el, newValue, opts);
    } else {
      // 降级：直接设置
      el.textContent = opts && opts.decimals ? newValue.toFixed(opts.decimals) : Math.round(newValue);
    }
  }

  // ===== 2. 趋势图平滑过渡 =====
  /**
   * 更新图表数据，走平滑插值过渡
   * @param {HTMLElement|string} container - 图表容器
   * @param {Array} newData - [{x, y, label}]
   * @param {object} opts - 图表选项
   */
  function updateChart(container, newData, opts) {
    if (typeof container === 'string') container = document.querySelector(container);
    if (!container) return;
    if (Motion && Motion.updateChart) {
      Motion.updateChart(container, newData, opts);
    }
  }

  // ===== 3. 横向滑动模组自动初始化 =====
  function initCarousels() {
    if (typeof window.Carousel === 'undefined') return;
    document.querySelectorAll('.carousel-container:not([data-carousel-init])').forEach(function(container) {
      container.setAttribute('data-carousel-init', 'true');
      try {
        new window.Carousel(container, {
          visibleCount: parseInt(container.getAttribute('data-visible') || '0', 10) || undefined
        });
      } catch(e) {
        console.warn('[MotionBridge] carousel init failed:', e);
      }
    });
  }

  // ===== 4. 数据刷新时的 KPI 自动更新（MutationObserver + textContent 侦测） =====
  function observeKPIChanges() {
    if (reduced || !('MutationObserver' in window)) return;

    function triggerCountUp(el, newVal) {
      if (el._animating) return; // 防止 count-up 过程中递归触发
      var oldVal = parseFloat(el.getAttribute('data-kpi-value') || el._lastText || '0');
      if (oldVal === newVal) return;
      el._animating = true;
      el.setAttribute('data-kpi-value', newVal);
      el._lastText = newVal;
      if (Motion && Motion.updateKPI) {
        Motion.updateKPI(el, newVal);
      } else {
        el.textContent = newVal;
      }
      setTimeout(function() { el._animating = false; }, 900);
    }

    // 监听 data-kpi-value 属性变化
    var attrMO = new MutationObserver(function(mutations) {
      mutations.forEach(function(m) {
        if (m.type === 'attributes' && m.attributeName === 'data-kpi-value') {
          var el = m.target;
          var newVal = parseFloat(el.getAttribute('data-kpi-value') || '0');
          if (!isNaN(newVal)) triggerCountUp(el, newVal);
        }
      });
    });

    // 监听 textContent 变化（characterData）——兼容现有页面直接 set textContent
    var textMO = new MutationObserver(function(mutations) {
      mutations.forEach(function(m) {
        var el = m.type === 'characterData' ? m.target.parentElement : m.target;
        if (!el || !el.hasAttribute || !el.hasAttribute('data-kpi')) return;
        var txt = (el.textContent || '').trim();
        // 提取数字（支持千分位、百分号、前缀）
        var numMatch = txt.replace(/,/g, '').match(/-?\d+(\.\d+)?/);
        if (numMatch) {
          var newVal = parseFloat(numMatch[0]);
          if (!isNaN(newVal)) triggerCountUp(el, newVal);
        }
      });
    });

    document.querySelectorAll('[data-kpi]').forEach(function(el) {
      attrMO.observe(el, { attributes: true, attributeFilter: ['data-kpi-value'] });
      textMO.observe(el, { characterData: true, subtree: true, childList: true });
      // 记录初始值
      var initTxt = (el.textContent || '').trim();
      var initMatch = initTxt.replace(/,/g, '').match(/-?\d+(\.\d+)?/);
      if (initMatch) el._lastText = parseFloat(initMatch[0]);
    });
  }

  // ===== 5. 离屏图表暂停高频动画 =====
  function pauseOffscreenCharts() {
    if (Motion && Motion.pauseOffscreen) {
      Motion.pauseOffscreen();
    }
  }

  // ===== 自动初始化 =====
  function autoInit() {
    initKPICountUp();
    initCarousels();
    observeKPIChanges();
    // 延迟执行离屏暂停，等页面渲染完成
    setTimeout(pauseOffscreenCharts, 1000);
  }

  if (document.readyState !== 'loading') {
    autoInit();
  } else {
    document.addEventListener('DOMContentLoaded', autoInit);
  }

  // 监听 DOM 变化，自动接入新元素
  if ('MutationObserver' in window) {
    var domMO = new MutationObserver(function() {
      initKPICountUp();
      initCarousels();
    });
    domMO.observe(document.body, { childList: true, subtree: true });
  }

  // 暴露全局 API
  window.MotionBridge = {
    updateKPI: updateKPI,
    updateChart: updateChart,
    initCarousels: initCarousels,
    initKPICountUp: initKPICountUp,
    isReduced: function() { return reduced; }
  };

})();
