/**
 * 序境 · Cross-Filter 通用联动框架（XUJING Cross-Filter）
 * -----------------------------------------------------------
 * 设计原则（序境母基线）：
 *  - 事件驱动：publish / subscribe 松耦合
 *  - Cross-highlight：点击筛选源 → 目标元素高亮/淡化，语义连续
 *  - 渐进增强：无框架也能正常展示；仅增强交互
 *  - 真实数据绑定：只作用于 DOM 中已存在的真实数据元素
 *
 * 用法：
 *  1. 筛选源元素加  data-xf-dim="维度" data-xf-value="值"
 *  2. 目标元素加    data-xf-dim="维度" data-xf-value="值"  （同维度）
 *  3. 调用 XJ_CrossFilter.bind(scope)  → 自动绑定筛选源点击 + 应用高亮
 *  4. 需要自定义时：publish / subscribe / clear
 */
(function () {
  'use strict';
  var state = {}; // { dim: value }
  var subs = {};  // { dim: [fn] }
  var knownDims = {}; // 出现过的维度（用于清空后仍刷新 UI）

  function publish(dim, value) {
    knownDims[dim] = true;
    var prev = state[dim];
    // 同一值再点 → 清除（toggle）
    if (prev === value) {
      delete state[dim];
    } else {
      state[dim] = value;
    }
    emit(dim);
  }

  function clear(dim) {
    delete state[dim];
    knownDims[dim] = true;
    emit(dim);
  }

  function emit(dim) {
    var fns = subs[dim] || [];
    for (var i = 0; i < fns.length; i++) {
      try { fns[i](state[dim]); } catch (e) { console.error('[XJ-CrossFilter]', e); }
    }
    try {
      window.dispatchEvent(new CustomEvent('xujing:crossfilter', { detail: { dim: dim, value: state[dim] } }));
    } catch (e) { /* ignore */ }
  }

  function subscribe(dim, fn) {
    if (!subs[dim]) subs[dim] = [];
    subs[dim].push(fn);
    // 立即回放当前值
    try { fn(state[dim]); } catch (e) { console.error('[XJ-CrossFilter]', e); }
  }

  function getState(dim) { return dim ? state[dim] : state; }

  /**
   * 在 scope 内绑定所有 [data-xf-dim][data-xf-value] 元素为筛选源，
   * 并维护其选中态（.xf-on）。
   */
  function bind(scope) {
    if (!scope) scope = document;
    var sources = scope.querySelectorAll('[data-xf-dim][data-xf-value]');
    Array.prototype.forEach.call(sources, function (el) {
      if (el.__xfBound) return;
      el.__xfBound = true;
      el.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var dim = el.getAttribute('data-xf-dim');
        var val = el.getAttribute('data-xf-value');
        publish(dim, val);
      });
    });
    // 初始选中态 + 订阅
    Object.keys(state).forEach(function (dim) {
      refreshDim(dim);
    });
  }

  /**
   * Cross-highlight：对 scope 内所有 [data-xf-dim] 元素，
   * 匹配当前筛选的加 .xf-on，不匹配的加 .xf-dimmed。
   */
  function refreshDim(dim) {
    var scope = document;
    var items = scope.querySelectorAll('[data-xf-dim="' + dim + '"]');
    var active = state[dim];
    Array.prototype.forEach.call(items, function (el) {
      var v = el.getAttribute('data-xf-value');
      var isSrc = el.classList.contains('xf-filter');
      if (active) {
        if (v === active) {
          el.classList.add('xf-on');
          el.classList.remove('xf-dimmed');
        } else {
          el.classList.remove('xf-on');
          el.classList.add('xf-dimmed');
        }
      } else {
        el.classList.remove('xf-on');
        el.classList.remove('xf-dimmed');
      }
    });
  }

  // 自动：任何 publish 后刷新所有已绑定维度
  ['click'].forEach(function () {});
  // 订阅一个全局刷新器（供 bind 后新渲染的元素）
  function bindAllDim() {
    Object.keys(knownDims).forEach(function (dim) { refreshDim(dim); });
  }

  window.XJ_CrossFilter = {
    publish: publish,
    clear: clear,
    subscribe: subscribe,
    getState: getState,
    bind: bind,
    refresh: bindAllDim,
    _on: function (dim, fn) { subscribe(dim, fn); }
  };

  // 供动态渲染后调用：新渲染的目标元素自动应用高亮
  document.addEventListener('click', function (e) {
    var t = e.target;
    while (t && t !== document) {
      if (t.getAttribute && t.getAttribute('data-xf-dim') && t.classList && !t.classList.contains('xf-filter')) {
        // 目标元素（非筛选源）点击不触发筛选，仅保持高亮刷新
        bindAllDim();
        break;
      }
      t = t.parentNode;
    }
  }, true);

  // 通知订阅维度变化（供业务层监听）
  window.addEventListener('xujing:crossfilter', function () { bindAllDim(); });
})();
