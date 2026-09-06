/* ============================================================================
   LUMENIS Motion Engine v1.0 — 数据驱动动效引擎
   原则：真变才动，不做假动画；所有动效可被 prefers-reduced-motion 关闭
   能力：数字count-up / 渐变面积图绘制 / 进度条填充 / 卡片级联进入 /
        状态脉冲 / 导航滑动 / IntersectionObserver 懒触发
   ============================================================================ */
(function() {
  'use strict';

  var Motion = {
    _reduced: false,
    _observers: [],
    _initialized: false
  };

  // ===== 初始化：检测减少动画偏好 =====
  Motion.init = function() {
    if (Motion._initialized) return;
    Motion._initialized = true;
    try {
      Motion._reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function(e) {
        Motion._reduced = e.matches;
      });
    } catch(e) { Motion._reduced = false; }

    // 全局 IntersectionObserver：元素进入视口时触发 ld-animate
    if ('IntersectionObserver' in window && !Motion._reduced) {
      var io = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            Motion._animateElement(entry.target);
            io.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
      Motion._io = io;
      document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('[ld-animate]').forEach(function(el) { io.observe(el); });
      });
    }
  };

  Motion._animateElement = function(el) {
    var type = el.getAttribute('ld-animate');
    if (type === 'count-up') {
      var target = parseFloat(el.getAttribute('ld-value') || el.textContent || '0');
      Motion.countUp(el, target);
    } else if (type === 'progress') {
      var pct = parseFloat(el.getAttribute('ld-progress') || '0');
      Motion.fillProgress(el, pct);
    } else if (type === 'stagger') {
      Motion.staggerChildren(el);
    } else {
      el.style.opacity = '1';
      el.style.transform = 'none';
    }
  };

  // ===== 1. 数字 Count-Up：从0滚动到真实值 =====
  // el: DOM元素, target: 目标数值, opts: {duration, decimals, prefix, suffix}
  Motion.countUp = function(el, target, opts) {
    if (!el) return;
    opts = opts || {};
    var duration = opts.duration || 1200;
    var decimals = opts.decimals != null ? opts.decimals : (target % 1 === 0 ? 0 : 1);
    var prefix = opts.prefix || '';
    var suffix = opts.suffix || '';
    var useLocale = opts.locale !== false;

    if (Motion._reduced || duration <= 0) {
      el.textContent = prefix + Motion._formatNum(target, decimals, useLocale) + suffix;
      return;
    }

    var start = performance.now();
    var from = 0;
    el.setAttribute('data-counting', 'true');

    function tick(now) {
      var elapsed = now - start;
      var progress = Math.min(elapsed / duration, 1);
      // easeOutExpo
      var eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      var current = from + (target - from) * eased;
      el.textContent = prefix + Motion._formatNum(current, decimals, useLocale) + suffix;
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = prefix + Motion._formatNum(target, decimals, useLocale) + suffix;
        el.removeAttribute('data-counting');
      }
    }
    requestAnimationFrame(tick);
  };

  Motion._formatNum = function(n, decimals, useLocale) {
    if (useLocale) {
      return Number(n).toLocaleString('zh-CN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      });
    }
    return Number(n).toFixed(decimals);
  };

  // 批量count-up：选择器或元素数组
  Motion.countUpAll = function(selectorOrEls, opts) {
    var els = typeof selectorOrEls === 'string'
      ? document.querySelectorAll(selectorOrEls)
      : selectorOrEls;
    els.forEach(function(el, i) {
      var target = parseFloat(el.getAttribute('ld-value') || el.dataset.value || el.textContent || '0');
      if (isNaN(target)) return;
      var delay = (opts && opts.stagger) ? i * (opts.staggerDelay || 60) : 0;
      setTimeout(function() { Motion.countUp(el, target, opts); }, delay);
    });
  };

  // ===== 2. 渐变面积图绘制（SVG path 从左到右动画） =====
  // svgEl: SVG元素, pathData: [{x, y}], opts: {color, fill, duration}
  Motion.drawAreaChart = function(container, data, opts) {
    if (!container || !data || data.length === 0) return null;
    opts = opts || {};
    var width = opts.width || container.clientWidth || 600;
    var height = opts.height || 200;
    var padding = opts.padding || { top: 20, right: 16, bottom: 24, left: 16 };
    var lineColor = opts.lineColor || '#8B5CF6';
    var areaGradient = opts.areaGradient || ['rgba(236,72,153,0.25)', 'rgba(59,130,246,0.02)'];
    var showDots = opts.showDots !== false;
    var showLabels = opts.showLabels !== false;

    var innerW = width - padding.left - padding.right;
    var innerH = height - padding.top - padding.bottom;
    var maxY = Math.max.apply(null, data.map(function(d) { return d.y; })) * 1.15 || 1;
    var minY = 0;

    // 创建SVG
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', width);
    svg.setAttribute('height', height);
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    svg.style.overflow = 'visible';

    // defs: 渐变
    var defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    var grad = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
    grad.setAttribute('id', 'ld-area-grad-' + Motion._gradId());
    grad.setAttribute('x1', '0'); grad.setAttribute('y1', '0');
    grad.setAttribute('x2', '0'); grad.setAttribute('y2', '1');
    var s1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
    s1.setAttribute('offset', '0%'); s1.setAttribute('stop-color', areaGradient[0]);
    var s2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
    s2.setAttribute('offset', '100%'); s2.setAttribute('stop-color', areaGradient[1]);
    grad.appendChild(s1); grad.appendChild(s2);
    defs.appendChild(grad);
    svg.appendChild(defs);

    // 坐标映射
    function mapX(i) { return padding.left + (data.length <= 1 ? innerW / 2 : (i / (data.length - 1)) * innerW); }
    function mapY(v) { return padding.top + innerH - ((v - minY) / (maxY - minY)) * innerH; }

    // 网格线
    for (var g = 0; g <= 3; g++) {
      var gy = padding.top + (innerH / 3) * g;
      var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', padding.left); line.setAttribute('y1', gy);
      line.setAttribute('x2', width - padding.right); line.setAttribute('y2', gy);
      line.setAttribute('stroke', 'rgba(0,0,0,0.05)');
      line.setAttribute('stroke-dasharray', '4 4');
      svg.appendChild(line);
    }

    // 面积path
    var areaPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    var areaD = 'M ' + mapX(0) + ' ' + (padding.top + innerH);
    data.forEach(function(d, i) { areaD += ' L ' + mapX(i) + ' ' + mapY(d.y); });
    areaD += ' L ' + mapX(data.length - 1) + ' ' + (padding.top + innerH) + ' Z';
    areaPath.setAttribute('d', areaD);
    areaPath.setAttribute('fill', 'url(#' + grad.getAttribute('id') + ')');
    areaPath.style.opacity = '0';
    svg.appendChild(areaPath);

    // 线条path
    var linePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    var lineD = 'M ' + mapX(0) + ' ' + mapY(data[0].y);
    data.forEach(function(d, i) { if (i > 0) lineD += ' L ' + mapX(i) + ' ' + mapY(d.y); });
    linePath.setAttribute('d', lineD);
    linePath.setAttribute('fill', 'none');
    linePath.setAttribute('stroke', lineColor);
    linePath.setAttribute('stroke-width', '2.5');
    linePath.setAttribute('stroke-linecap', 'round');
    linePath.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(linePath);

    // 数据点
    var dots = [];
    if (showDots) {
      data.forEach(function(d, i) {
        var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', mapX(i));
        circle.setAttribute('cy', mapY(d.y));
        circle.setAttribute('r', '4');
        circle.setAttribute('fill', '#fff');
        circle.setAttribute('stroke', lineColor);
        circle.setAttribute('stroke-width', '2.5');
        circle.style.opacity = '0';
        circle.style.cursor = 'pointer';
        circle.addEventListener('mouseenter', function() {
          circle.setAttribute('r', '6');
          Motion._showTooltip(container, d, mapX(i), mapY(d.y));
        });
        circle.addEventListener('mouseleave', function() {
          circle.setAttribute('r', '4');
          Motion._hideTooltip();
        });
        svg.appendChild(circle);
        dots.push(circle);
      });
    }

    // X轴标签
    if (showLabels) {
      data.forEach(function(d, i) {
        if (data.length > 8 && i % Math.ceil(data.length / 6) !== 0 && i !== data.length - 1) return;
        var text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', mapX(i));
        text.setAttribute('y', height - 6);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', '#9CA3AF');
        text.setAttribute('font-size', '10');
        text.textContent = d.label || '';
        svg.appendChild(text);
      });
    }

    container.innerHTML = '';
    container.appendChild(svg);

    // 动画：从左到右绘制
    if (!Motion._reduced) {
      var pathLen = linePath.getTotalLength ? linePath.getTotalLength() : 1000;
      linePath.style.strokeDasharray = pathLen;
      linePath.style.strokeDashoffset = pathLen;
      linePath.getBoundingClientRect(); // force reflow
      linePath.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(0.16,1,0.3,1)';
      linePath.style.strokeDashoffset = '0';

      setTimeout(function() {
        areaPath.style.transition = 'opacity 0.6s ease';
        areaPath.style.opacity = '1';
      }, 400);

      dots.forEach(function(dot, i) {
        setTimeout(function() {
          dot.style.transition = 'opacity 0.3s ease, r 0.2s ease';
          dot.style.opacity = '1';
        }, 800 + i * 80);
      });
    } else {
      areaPath.style.opacity = '1';
      dots.forEach(function(d) { d.style.opacity = '1'; });
    }

    return { svg: svg, linePath: linePath, areaPath: areaPath, dots: dots };
  };

  Motion._gradId = function() {
    return 'g' + Math.random().toString(36).substr(2, 6);
  };

  Motion._showTooltip = function(container, d, x, y) {
    Motion._hideTooltip();
    var tip = document.createElement('div');
    tip.className = 'ld-chart-tooltip';
    tip.innerHTML = '<div style="font-size:10px;opacity:0.7;margin-bottom:2px;">' + (d.label || '') + '</div>'
      + '<div style="font-size:14px;">' + Number(d.y).toLocaleString('zh-CN') + '</div>';
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
    container.style.position = 'relative';
    container.appendChild(tip);
    Motion._tooltip = tip;
  };

  Motion._hideTooltip = function() {
    if (Motion._tooltip && Motion._tooltip.parentNode) {
      Motion._tooltip.parentNode.removeChild(Motion._tooltip);
    }
    Motion._tooltip = null;
  };

  // ===== 3. 进度条填充动画 =====
  Motion.fillProgress = function(barEl, percent, opts) {
    if (!barEl) return;
    opts = opts || {};
    var duration = opts.duration || 800;
    percent = Math.max(0, Math.min(100, percent));

    if (Motion._reduced) {
      barEl.style.width = percent + '%';
      return;
    }
    barEl.style.width = '0%';
    barEl.getBoundingClientRect();
    barEl.style.transition = 'width ' + duration + 'ms cubic-bezier(0.16,1,0.3,1)';
    requestAnimationFrame(function() {
      barEl.style.width = percent + '%';
    });
  };

  // 批量进度条
  Motion.fillAllProgress = function(selector) {
    document.querySelectorAll(selector).forEach(function(el) {
      var pct = parseFloat(el.getAttribute('ld-progress') || el.dataset.progress || el.style.width || '0');
      Motion.fillProgress(el, pct);
    });
  };

  // ===== 4. 卡片级联进入（Stagger） =====
  Motion.staggerChildren = function(container, opts) {
    if (!container || Motion._reduced) return;
    opts = opts || {};
    var delay = opts.delay || 0;
    var step = opts.step || 60;
    var children = container.children;
    for (var i = 0; i < children.length; i++) {
      (function(child, idx) {
        child.style.opacity = '0';
        child.style.transform = 'translateY(12px)';
        setTimeout(function() {
          child.style.transition = 'opacity 0.5s cubic-bezier(0.16,1,0.3,1), transform 0.5s cubic-bezier(0.16,1,0.3,1)';
          child.style.opacity = '1';
          child.style.transform = 'none';
        }, delay + idx * step);
      })(children[i], i);
    }
  };

  // ===== 5. 状态变化脉冲 =====
  Motion.pulse = function(el, color, opts) {
    if (!el || Motion._reduced) return;
    opts = opts || {};
    var originalBg = el.style.background;
    var originalBox = el.style.boxShadow;
    el.style.transition = 'box-shadow 0.3s ease, background 0.3s ease';
    el.style.boxShadow = '0 0 0 4px ' + (color || 'rgba(0,212,170,0.3)');
    setTimeout(function() {
      el.style.boxShadow = originalBox;
      setTimeout(function() { el.style.transition = ''; }, 300);
    }, 600);
  };

  // ===== 6. 数据更新闪烁（真变才闪） =====
  Motion.flashUpdate = function(el) {
    if (!el || Motion._reduced) return;
    el.classList.remove('lm-data-update');
    void el.offsetWidth; // reflow
    el.classList.add('lm-data-update');
  };

  // ===== 7. 导航胶囊滑动（用于tab切换） =====
  Motion.slideTab = function(tabsContainer, activeTab) {
    if (!tabsContainer || !activeTab || Motion._reduced) return;
    var indicator = tabsContainer.querySelector('.ld-tab-indicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'ld-tab-indicator';
      indicator.style.cssText = 'position:absolute;top:4px;bottom:4px;border-radius:999px;background:var(--l-text,#0D0D0D);transition:all 0.35s cubic-bezier(0.16,1,0.3,1);z-index:0;pointer-events:none;';
      tabsContainer.style.position = 'relative';
      tabsContainer.insertBefore(indicator, tabsContainer.firstChild);
    }
    var rect = activeTab.getBoundingClientRect();
    var containerRect = tabsContainer.getBoundingClientRect();
    indicator.style.left = (rect.left - containerRect.left) + 'px';
    indicator.style.width = rect.width + 'px';
    activeTab.style.position = 'relative';
    activeTab.style.zIndex = '1';
  };

  // ===== 8. 工具：数字变化检测（真变才动） =====
  Motion.updateValue = function(el, newValue, opts) {
    if (!el) return;
    var oldValue = parseFloat(el.getAttribute('ld-current') || el.textContent || '0');
    if (oldValue === newValue) return; // 没变不动
    el.setAttribute('ld-current', newValue);
    Motion.countUp(el, newValue, opts);
    Motion.flashUpdate(el);
  };

  // ===== 9. 自动初始化：页面加载后扫描 [ld-count-up] [ld-progress] =====
  function autoInit() {
    Motion.init();
    // count-up
    Motion.countUpAll('[ld-count-up]', { stagger: true, staggerDelay: 80 });
    // progress
    document.querySelectorAll('[ld-progress-bar]').forEach(function(el) {
      var bar = el.querySelector('.ld-progress__bar') || el;
      var pct = parseFloat(el.getAttribute('ld-progress-bar') || '0');
      Motion.fillProgress(bar, pct);
    });
    // stagger
    document.querySelectorAll('[ld-stagger]').forEach(function(el) {
      Motion.staggerChildren(el);
    });
  }

  if (document.readyState !== 'loading') {
    autoInit();
  } else {
    document.addEventListener('DOMContentLoaded', autoInit);
  }

  // 暴露到全局
  window.LDMotion = Motion;
})();
