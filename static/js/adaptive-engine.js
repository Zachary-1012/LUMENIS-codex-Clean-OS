/* ============================================================================
   ZBC Adaptive Engine V1 — 自适应布局引擎 JS
   能力：Container Query 检测 / Size Model 切换 / Module Registry /
        Resize 处理 / Density 控制 / Progressive Disclosure
   原则：CSS Container Query 为主，JS 仅做辅助检测和状态同步
   依赖：无（纯原生 JS，不依赖 jQuery/React）
   ============================================================================ */
(function() {
  'use strict';

  var Adaptive = {
    _initialized: false,
    _containers: new Map(),      // element -> { observer, size }
    _modules: new Map(),         // module_id -> contract
    _moduleInstances: new Map(), // module_id -> element
    _resizeTimer: null,
    _density: 'normal',
    _reducedMotion: false,
    _listeners: []
  };

  // ===== Size Model 定义 =====
  Adaptive.SIZES = {
    COMPACT:     { name: 'compact',     min: 0,    max: 479  },
    COMFORTABLE: { name: 'comfortable', min: 480,  max: 719  },
    EXPANDED:    { name: 'expanded',    min: 720,  max: 1023 },
    WIDE:        { name: 'wide',        min: 1024, max: Infinity }
  };

  // ===== 初始化 =====
  Adaptive.init = function() {
    if (Adaptive._initialized) return;
    Adaptive._initialized = true;

    // 检测 reduced motion
    try {
      Adaptive._reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function(e) {
        Adaptive._reducedMotion = e.matches;
        document.documentElement.setAttribute('data-reduced-motion', e.matches ? 'true' : 'false');
      });
      document.documentElement.setAttribute('data-reduced-motion', Adaptive._reducedMotion ? 'true' : 'false');
    } catch(e) { Adaptive._reducedMotion = false; }

    // 恢复密度偏好
    try {
      var saved = localStorage.getItem('zbc-density');
      if (saved) Adaptive.setDensity(saved);
    } catch(e) {}

    // 扫描所有 .ad-container 并建立 ResizeObserver
    Adaptive._scanContainers();

    // 监听 DOM 变化，自动接入新容器
    if ('MutationObserver' in window) {
      var mo = new MutationObserver(function(mutations) {
        var needsScan = false;
        mutations.forEach(function(m) {
          if (m.addedNodes && m.addedNodes.length) needsScan = true;
        });
        if (needsScan) Adaptive._scanContainers();
      });
      mo.observe(document.body, { childList: true, subtree: true });
    }

    // 视口变化时（debounced）同步全局 size
    window.addEventListener('resize', Adaptive._onViewportResize, { passive: true });

    // 初始化全局 viewport size
    Adaptive._updateViewportSize();
  };

  // ===== Container Query 检测 =====
  Adaptive._scanContainers = function() {
    if (!('ResizeObserver' in window)) {
      // 降级：用 setInterval 检测
      document.querySelectorAll('.ad-container:not([data-ad-scanned])').forEach(function(el) {
        el.setAttribute('data-ad-scanned', 'true');
        Adaptive._updateContainerSize(el);
      });
      return;
    }

    document.querySelectorAll('.ad-container:not([data-ad-scanned])').forEach(function(el) {
      el.setAttribute('data-ad-scanned', 'true');
      Adaptive._updateContainerSize(el);

      var ro = new ResizeObserver(function(entries) {
        entries.forEach(function(entry) {
          Adaptive._updateContainerSize(entry.target);
        });
      });
      ro.observe(el);
      Adaptive._containers.set(el, { observer: ro, size: null });
    });
  };

  Adaptive._updateContainerSize = function(el) {
    var width = el.clientWidth || 0;
    var size = Adaptive._getSizeForWidth(width);
    var current = el.getAttribute('data-size');
    if (current !== size.name) {
      el.setAttribute('data-size', size.name);
      // 触发自定义事件
      el.dispatchEvent(new CustomEvent('adaptive:sizechange', {
        detail: { size: size.name, width: width, previous: current }
      }));
    }
    if (Adaptive._containers.has(el)) {
      Adaptive._containers.get(el).size = size.name;
    }
  };

  Adaptive._getSizeForWidth = function(width) {
    if (width >= Adaptive.SIZES.WIDE.min) return Adaptive.SIZES.WIDE;
    if (width >= Adaptive.SIZES.EXPANDED.min) return Adaptive.SIZES.EXPANDED;
    if (width >= Adaptive.SIZES.COMFORTABLE.min) return Adaptive.SIZES.COMFORTABLE;
    return Adaptive.SIZES.COMPACT;
  };

  Adaptive._updateViewportSize = function() {
    var vw = window.innerWidth;
    var size = Adaptive._getSizeForWidth(vw);
    document.documentElement.setAttribute('data-viewport-size', size.name);
    document.documentElement.setAttribute('data-viewport-width', vw);
  };

  Adaptive._onViewportResize = function() {
    if (Adaptive._resizeTimer) clearTimeout(Adaptive._resizeTimer);
    Adaptive._resizeTimer = setTimeout(function() {
      Adaptive._updateViewportSize();
      // 通知所有模块视口变化
      Adaptive._emit('viewport:resize', { width: window.innerWidth, height: window.innerHeight });
    }, 150);
  };

  // ===== Density 控制 =====
  Adaptive.setDensity = function(density) {
    if (['compact', 'normal', 'comfortable'].indexOf(density) === -1) return;
    Adaptive._density = density;
    if (density === 'normal') {
      document.documentElement.removeAttribute('data-density');
    } else {
      document.documentElement.setAttribute('data-density', density);
    }
    try { localStorage.setItem('zbc-density', density); } catch(e) {}
    Adaptive._emit('density:change', { density: density });
  };

  Adaptive.getDensity = function() { return Adaptive._density; };

  // ===== Module Registry =====
  /**
   * 注册模块声明
   * contract: {
   *   module_id: string,
   *   module_type: 'kpi'|'chart'|'table'|'list'|'panel'|'ai'|'browser'|'custom',
   *   data_source: string,
   *   min_width: number,
   *   preferred_width: number,
   *   max_width: number,
   *   priority: number (P0=0, P1=1, P2=2, P3=3),
   *   responsive_mode: 'reflow'|'hide'|'scale'|'scroll',
   *   motion_mode: 'full'|'minimal'|'none',
   *   permission: string|null,
   *   visibility: 'always'|'desktop'|'tablet'|'mobile'|'conditional',
   *   onSizeChange: function(size, width)
   * }
   */
  Adaptive.registerModule = function(contract) {
    if (!contract || !contract.module_id) {
      console.warn('[Adaptive] registerModule requires module_id');
      return false;
    }
    // 默认值
    contract = Object.assign({
      module_type: 'custom',
      min_width: 200,
      preferred_width: 400,
      max_width: Infinity,
      priority: 2,
      responsive_mode: 'reflow',
      motion_mode: 'full',
      permission: null,
      visibility: 'always'
    }, contract);

    Adaptive._modules.set(contract.module_id, contract);
    Adaptive._emit('module:registered', { module_id: contract.module_id });
    return true;
  };

  Adaptive.unregisterModule = function(module_id) {
    Adaptive._modules.delete(module_id);
    Adaptive._moduleInstances.delete(module_id);
    Adaptive._emit('module:unregistered', { module_id: module_id });
  };

  Adaptive.getModule = function(module_id) {
    return Adaptive._modules.get(module_id) || null;
  };

  Adaptive.getAllModules = function() {
    return Array.from(Adaptive._modules.values());
  };

  // 绑定模块实例到 DOM 元素
  Adaptive.bindModule = function(module_id, element) {
    var contract = Adaptive._modules.get(module_id);
    if (!contract) {
      console.warn('[Adaptive] bindModule: module not registered:', module_id);
      return;
    }
    Adaptive._moduleInstances.set(module_id, element);
    element.setAttribute('data-module-id', module_id);
    element.setAttribute('data-module-type', contract.module_type);

    // 如果元素是 container，监听 size 变化
    if (element.classList.contains('ad-container')) {
      element.addEventListener('adaptive:sizechange', function(e) {
        if (contract.onSizeChange) {
          contract.onSizeChange(e.detail.size, e.detail.width);
        }
        Adaptive._applyResponsiveMode(element, contract, e.detail.size);
      });
    }
    // 初始应用
    var size = element.getAttribute('data-size') || 'expanded';
    Adaptive._applyResponsiveMode(element, contract, size);
  };

  Adaptive._applyResponsiveMode = function(element, contract, size) {
    var width = element.clientWidth || 0;
    // 可见性控制
    var shouldShow = true;
    if (contract.visibility === 'desktop' && (size === 'compact' || size === 'comfortable')) {
      shouldShow = false;
    } else if (contract.visibility === 'mobile' && (size === 'expanded' || size === 'wide')) {
      shouldShow = false;
    }
    if (contract.min_width && width < contract.min_width && contract.responsive_mode === 'hide') {
      shouldShow = false;
    }
    element.style.display = shouldShow ? '' : 'none';
    element.setAttribute('data-module-visible', shouldShow ? 'true' : 'false');
  };

  // ===== Dashboard 布局引擎 =====
  /**
   * 自动布局 Dashboard 模块
   * container: 容器元素
   * moduleIds: 模块ID数组（按优先级排序）
   */
  Adaptive.layoutDashboard = function(container, moduleIds) {
    if (!container) return;
    container.classList.add('ad-container', 'ad-grid');
    container.setAttribute('data-dashboard', 'true');

    var availableWidth = container.clientWidth;
    var modules = moduleIds.map(function(id) { return Adaptive.getModule(id); }).filter(Boolean);

    // 按优先级排序
    modules.sort(function(a, b) { return a.priority - b.priority; });

    // 计算每个模块的列跨度
    modules.forEach(function(mod) {
      var el = Adaptive._moduleInstances.get(mod.module_id);
      if (!el) return;
      var span = 1;
      if (mod.preferred_width > 0) {
        span = Math.max(1, Math.round(mod.preferred_width / (availableWidth / 4)));
        span = Math.min(span, 4);
      }
      el.style.gridColumn = 'span ' + span;
    });
  };

  // ===== Progressive Disclosure =====
  Adaptive.initDisclosure = function(container) {
    var root = container || document;
    root.querySelectorAll('.ad-disclosure:not([data-ad-init])').forEach(function(d) {
      d.setAttribute('data-ad-init', 'true');
      var summary = d.querySelector('.ad-disclosure__summary');
      if (summary) {
        summary.addEventListener('click', function() {
          d.classList.toggle('is-open');
        });
        summary.setAttribute('role', 'button');
        summary.setAttribute('tabindex', '0');
        summary.addEventListener('keydown', function(e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            d.classList.toggle('is-open');
          }
        });
      }
    });
  };

  // ===== Drawer / Modal / Sheet 控制 =====
  Adaptive.openDrawer = function(id) {
    var drawer = document.getElementById(id);
    if (!drawer) return;
    drawer.classList.add('is-open');
    var overlay = drawer.querySelector('.ad-drawer__overlay') || document.querySelector('.ad-drawer__overlay');
    if (overlay) overlay.classList.add('is-open');
    document.body.classList.add('has-overlay');
  };

  Adaptive.closeDrawer = function(id) {
    var drawer = document.getElementById(id);
    if (!drawer) return;
    drawer.classList.remove('is-open');
    var overlay = drawer.querySelector('.ad-drawer__overlay') || document.querySelector('.ad-drawer__overlay');
    if (overlay) overlay.classList.remove('is-open');
    document.body.classList.remove('has-overlay');
  };

  Adaptive.openModal = function(id) {
    var modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add('is-open');
    var overlay = modal.querySelector('.ad-modal__overlay') || document.querySelector('.ad-modal__overlay');
    if (overlay) overlay.classList.add('is-open');
    document.body.classList.add('has-overlay');
  };

  Adaptive.closeModal = function(id) {
    var modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove('is-open');
    var overlay = modal.querySelector('.ad-modal__overlay') || document.querySelector('.ad-modal__overlay');
    if (overlay) overlay.classList.remove('is-open');
    document.body.classList.remove('has-overlay');
  };

  Adaptive.openSheet = function(id) {
    var sheet = document.getElementById(id);
    if (!sheet) return;
    sheet.classList.add('is-open');
    document.body.classList.add('has-overlay');
  };

  Adaptive.closeSheet = function(id) {
    var sheet = document.getElementById(id);
    if (!sheet) return;
    sheet.classList.remove('is-open');
    document.body.classList.remove('has-overlay');
  };

  // ===== 事件系统 =====
  Adaptive.on = function(event, callback) {
    Adaptive._listeners.push({ event: event, callback: callback });
    return function() {
      Adaptive._listeners = Adaptive._listeners.filter(function(l) {
        return !(l.event === event && l.callback === callback);
      });
    };
  };

  Adaptive._emit = function(event, detail) {
    Adaptive._listeners.forEach(function(l) {
      if (l.event === event) {
        try { l.callback(detail); } catch(e) { console.error('[Adaptive] listener error:', e); }
      }
    });
    document.dispatchEvent(new CustomEvent('adaptive:' + event, { detail: detail }));
  };

  // ===== 工具：获取当前视口 size =====
  Adaptive.getViewportSize = function() {
    return Adaptive._getSizeForWidth(window.innerWidth).name;
  };

  Adaptive.isReducedMotion = function() {
    return Adaptive._reducedMotion;
  };

  // ===== 自动初始化 =====
  function autoInit() {
    Adaptive.init();
    Adaptive.initDisclosure();
  }

  if (document.readyState !== 'loading') {
    autoInit();
  } else {
    document.addEventListener('DOMContentLoaded', autoInit);
  }

  // 暴露到全局
  window.ZBCAdaptive = Adaptive;
  // 兼容旧命名
  window.AdaptiveEngine = Adaptive;
})();
