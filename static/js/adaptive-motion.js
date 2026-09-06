/* ============================================================================
   ZBC Adaptive Motion System V1 — 统一动效系统
   原则：数据驱动（真变才动）/ 优先级（业务>数据>交互>装饰）/
        可访问性（prefers-reduced-motion 降级）/ 性能（transform+opacity）
   依赖：lumenis-motion-engine.js（LDMotion）— 复用 countUp/drawAreaChart/
        fillProgress/stagger/pulse/flashUpdate/slideTab，不重复实现
   加载顺序：在 lumenis-motion-engine.js 之后加载
   ============================================================================ */
(function() {
  'use strict';

  var Motion = {
    _initialized: false,
    _reduced: false,
    _priorities: { P0: 0, P1: 1, P2: 2, P3: 3 },
    _activeAnimations: new Map(), // element -> { type, priority, rafId }
    _observers: []
  };

  // ===== Motion Token（与 CSS --ad-motion-* 对应） =====
  Motion.TOKEN = {
    duration: {
      instant: 100,
      fast: 180,
      normal: 280,
      slow: 450,
      slower: 650
    },
    ease: {
      standard: 'cubic-bezier(0.2, 0, 0, 1)',
      decelerate: 'cubic-bezier(0, 0, 0.2, 1)',
      accelerate: 'cubic-bezier(0.4, 0, 1, 1)',
      spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)'
    }
  };

  // ===== Motion Preset 定义 =====
  Motion.PRESETS = {
    // 进入/退出
    enter: {
      opacity: [0, 1],
      transform: ['translateY(12px)', 'translateY(0)'],
      duration: 280,
      ease: 'cubic-bezier(0, 0, 0.2, 1)',
      priority: 'P2'
    },
    exit: {
      opacity: [1, 0],
      transform: ['translateY(0)', 'translateY(-8px)'],
      duration: 180,
      ease: 'cubic-bezier(0.4, 0, 1, 1)',
      priority: 'P2'
    },
    appear: {
      opacity: [0, 1],
      scale: [0.96, 1],
      duration: 280,
      ease: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      priority: 'P2'
    },
    // 展开/折叠
    expand: {
      maxHeight: ['0px', '1000px'],
      opacity: [0, 1],
      duration: 350,
      ease: 'cubic-bezier(0, 0, 0.2, 1)',
      priority: 'P2'
    },
    collapse: {
      maxHeight: ['1000px', '0px'],
      opacity: [1, 0],
      duration: 250,
      ease: 'cubic-bezier(0.4, 0, 1, 1)',
      priority: 'P2'
    },
    // 数据更新
    dataUpdate: {
      backgroundColor: ['rgba(0,212,170,0.12)', 'transparent'],
      duration: 800,
      ease: 'ease',
      priority: 'P1'
    },
    // 状态变化
    success: {
      boxShadow: ['0 0 0 0 rgba(16,185,129,0.4)', '0 0 0 8px rgba(16,185,129,0)'],
      duration: 600,
      ease: 'ease-out',
      priority: 'P0'
    },
    warning: {
      boxShadow: ['0 0 0 0 rgba(217,119,6,0.4)', '0 0 0 8px rgba(217,119,6,0)'],
      duration: 600,
      ease: 'ease-out',
      priority: 'P0'
    },
    error: {
      boxShadow: ['0 0 0 0 rgba(220,38,38,0.4)', '0 0 0 8px rgba(220,38,38,0)'],
      duration: 600,
      ease: 'ease-out',
      priority: 'P0'
    },
    shake: {
      transform: ['translateX(0)', 'translateX(-4px)', 'translateX(4px)', 'translateX(0)'],
      duration: 400,
      ease: 'ease',
      priority: 'P0'
    },
    // 交互
    hover: {
      transform: ['translateY(0)', 'translateY(-2px)'],
      boxShadow: ['var(--ld-shadow-sm)', 'var(--ld-shadow-lg)'],
      duration: 200,
      ease: 'cubic-bezier(0.2, 0, 0, 1)',
      priority: 'P3'
    },
    press: {
      transform: ['scale(1)', 'scale(0.98)'],
      duration: 100,
      ease: 'ease-in',
      priority: 'P3'
    },
    focus: {
      boxShadow: ['0 0 0 0 rgba(0,212,170,0)', '0 0 0 3px rgba(0,212,170,0.2)'],
      duration: 150,
      ease: 'ease-out',
      priority: 'P2'
    }
  };

  // ===== 初始化 =====
  Motion.init = function() {
    if (Motion._initialized) return;
    Motion._initialized = true;

    // 检测 reduced motion
    try {
      Motion._reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function(e) {
        Motion._reduced = e.matches;
        if (e.matches) Motion._cancelAllDecorative();
      });
    } catch(e) { Motion._reduced = false; }

    // IntersectionObserver：元素进入视口时触发 enter 动画
    if ('IntersectionObserver' in window && !Motion._reduced) {
      var io = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            Motion.applyPreset(entry.target, 'enter');
            io.unobserve(entry.target);
          }
        });
      }, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });
      Motion._io = io;
      document.querySelectorAll('[ad-motion="enter"]').forEach(function(el) { io.observe(el); });
    }

    // 监听 DOM 变化，自动接入新元素
    if ('MutationObserver' in window) {
      var mo = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
          if (m.addedNodes) {
            m.addedNodes.forEach(function(node) {
              if (node.nodeType === 1 && node.hasAttribute && node.hasAttribute('ad-motion')) {
                if (Motion._io) Motion._io.observe(node);
              }
            });
          }
        });
      });
      mo.observe(document.body, { childList: true, subtree: true });
    }
  };

  // ===== 核心：应用 Preset =====
  Motion.applyPreset = function(element, presetName, opts) {
    if (!element || Motion._reduced) {
      // reduced motion：直接设置终态
      if (element && presetName === 'enter') {
        element.style.opacity = '1';
        element.style.transform = 'none';
      }
      return;
    }
    var preset = Motion.PRESETS[presetName];
    if (!preset) {
      console.warn('[Motion] unknown preset:', presetName);
      return;
    }
    opts = opts || {};

    // 优先级检查：如果有更高优先级动画在运行，不打断
    var current = Motion._activeAnimations.get(element);
    if (current && Motion._priorities[current.priority] < Motion._priorities[preset.priority]) {
      return; // 高优先级不被低优先级打断
    }

    // 使用 Web Animations API（优先）或 CSS transition（降级）
    var keyframes = Motion._presetToKeyframes(preset);
    var animationOptions = {
      duration: opts.duration || preset.duration,
      easing: preset.ease,
      fill: 'forwards'
    };

    if (element.animate) {
      var anim = element.animate(keyframes, animationOptions);
      Motion._activeAnimations.set(element, { type: presetName, priority: preset.priority, animation: anim });
      anim.onfinish = function() {
        Motion._activeAnimations.delete(element);
        if (opts.onComplete) opts.onComplete();
      };
      anim.oncancel = function() {
        Motion._activeAnimations.delete(element);
      };
    } else {
      // 降级：CSS transition
      Motion._applyPresetFallback(element, preset, opts);
    }
  };

  Motion._presetToKeyframes = function(preset) {
    var keyframes = [];
    var props = Object.keys(preset).filter(function(k) {
      return k !== 'duration' && k !== 'ease' && k !== 'priority';
    });
    // 简单两帧
    var from = {}, to = {};
    props.forEach(function(prop) {
      if (Array.isArray(preset[prop])) {
        from[prop] = preset[prop][0];
        to[prop] = preset[prop][preset[prop].length - 1];
      }
    });
    keyframes.push(from, to);
    return keyframes;
  };

  Motion._applyPresetFallback = function(element, preset, opts) {
    var duration = opts.duration || preset.duration;
    element.style.transition = 'all ' + duration + 'ms ' + preset.ease;
    if (preset.opacity) element.style.opacity = preset.opacity[1];
    if (preset.transform) element.style.transform = preset.transform[1];
    setTimeout(function() {
      element.style.transition = '';
      if (opts.onComplete) opts.onComplete();
    }, duration);
  };

  // ===== 数据驱动 KPI Count-Up（复用 LDMotion.countUp） =====
  /**
   * 数据变化时才触发动画，数据没变不触发
   * element: DOM元素
   * newValue: 新数值
   * opts: { decimals, prefix, suffix, duration }
   */
  Motion.updateKPI = function(element, newValue, opts) {
    if (!element) return;
    var oldValue = parseFloat(element.getAttribute('data-kpi-value') || element.textContent || '0');
    if (oldValue === newValue) return; // 真变才动
    element.setAttribute('data-kpi-value', newValue);

    if (Motion._reduced) {
      element.textContent = newValue;
      return;
    }

    // 复用 LDMotion.countUp
    if (window.LDMotion && window.LDMotion.countUp) {
      window.LDMotion.countUp(element, newValue, opts);
    } else {
      Motion._countUpFallback(element, oldValue, newValue, opts);
    }

    // 数据更新高亮
    Motion.applyPreset(element.parentElement, 'dataUpdate');
  };

  Motion._countUpFallback = function(element, from, to, opts) {
    opts = opts || {};
    var duration = opts.duration || 800;
    var start = performance.now();
    function tick(now) {
      var progress = Math.min((now - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = from + (to - from) * eased;
      element.textContent = opts.decimals ? current.toFixed(opts.decimals) : Math.round(current);
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  };

  // ===== 趋势图动态更新（复用 LDMotion.drawAreaChart） =====
  /**
   * 平滑更新图表数据，禁止旧图消失新图瞬间出现
   * container: 图表容器
   * newData: [{x, y}] 新数据
   * opts: 图表选项
   */
  Motion.updateChart = function(container, newData, opts) {
    if (!container || !newData) return;
    var oldData = container._chartData;
    container._chartData = newData;

    if (Motion._reduced || !oldData || oldData.length === 0) {
      // 首次或 reduced：直接绘制
      if (window.LDMotion && window.LDMotion.drawAreaChart) {
        window.LDMotion.drawAreaChart(container, newData, opts);
      }
      return;
    }

    // 数据过渡：从旧数据插值到新数据
    var duration = 600;
    var start = performance.now();
    var maxLen = Math.max(oldData.length, newData.length);

    function tick(now) {
      var progress = Math.min((now - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var interpolated = [];
      for (var i = 0; i < maxLen; i++) {
        var oldY = oldData[i] ? oldData[i].y : 0;
        var newY = newData[i] ? newData[i].y : 0;
        interpolated.push({
          x: newData[i] ? newData[i].x : (oldData[i] ? oldData[i].x : i),
          y: oldY + (newY - oldY) * eased,
          label: newData[i] ? newData[i].label : (oldData[i] ? oldData[i].label : '')
        });
      }
      if (window.LDMotion && window.LDMotion.drawAreaChart) {
        window.LDMotion.drawAreaChart(container, interpolated, opts);
      }
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  };

  // ===== 进度条更新（复用 LDMotion.fillProgress） =====
  Motion.updateProgress = function(barElement, percent, opts) {
    if (!barElement) return;
    var oldPercent = parseFloat(barElement.getAttribute('data-progress') || '0');
    if (oldPercent === percent) return;
    barElement.setAttribute('data-progress', percent);

    if (window.LDMotion && window.LDMotion.fillProgress) {
      window.LDMotion.fillProgress(barElement, percent, opts);
    } else {
      barElement.style.transition = 'width 400ms cubic-bezier(0,0,0.2,1)';
      barElement.style.width = percent + '%';
    }
  };

  // ===== 卡片级联进入（复用 LDMotion.staggerChildren） =====
  Motion.staggerIn = function(container, opts) {
    if (!container || Motion._reduced) return;
    if (window.LDMotion && window.LDMotion.staggerChildren) {
      window.LDMotion.staggerChildren(container, opts);
    } else {
      var children = container.children;
      for (var i = 0; i < children.length; i++) {
        (function(child, idx) {
          child.style.opacity = '0';
          child.style.transform = 'translateY(12px)';
          setTimeout(function() {
            child.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            child.style.opacity = '1';
            child.style.transform = 'none';
          }, (opts.delay || 0) + idx * (opts.step || 60));
        })(children[i], i);
      }
    }
  };

  // ===== 状态脉冲（复用 LDMotion.pulse） =====
  Motion.pulse = function(element, color, opts) {
    if (!element || Motion._reduced) return;
    if (window.LDMotion && window.LDMotion.pulse) {
      window.LDMotion.pulse(element, color, opts);
    } else {
      Motion.applyPreset(element, 'success');
    }
  };

  // ===== 数据更新闪烁（复用 LDMotion.flashUpdate） =====
  Motion.flashUpdate = function(element) {
    if (!element || Motion._reduced) return;
    if (window.LDMotion && window.LDMotion.flashUpdate) {
      window.LDMotion.flashUpdate(element);
    } else {
      Motion.applyPreset(element, 'dataUpdate');
    }
  };

  // ===== Tab 滑动（复用 LDMotion.slideTab） =====
  Motion.slideTab = function(container, activeTab) {
    if (!container || !activeTab || Motion._reduced) return;
    if (window.LDMotion && window.LDMotion.slideTab) {
      window.LDMotion.slideTab(container, activeTab);
    }
  };

  // ===== 优先级管理 =====
  Motion._cancelAllDecorative = function() {
    Motion._activeAnimations.forEach(function(anim, el) {
      if (anim.priority === 'P3' && anim.animation) {
        anim.animation.cancel();
      }
    });
  };

  Motion.cancelAnimation = function(element) {
    var anim = Motion._activeAnimations.get(element);
    if (anim && anim.animation) {
      anim.animation.cancel();
    }
    Motion._activeAnimations.delete(element);
  };

  // ===== 性能：离屏元素暂停动画 =====
  Motion.pauseOffscreen = function() {
    if (!('IntersectionObserver' in window)) return;
    var io = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        var anim = Motion._activeAnimations.get(entry.target);
        if (anim && anim.animation) {
          if (entry.isIntersecting) {
            anim.animation.play();
          } else {
            anim.animation.pause();
          }
        }
      });
    }, { threshold: 0 });
    Motion._activeAnimations.forEach(function(anim, el) { io.observe(el); });
  };

  // ===== 自动初始化 =====
  function autoInit() {
    Motion.init();
  }

  if (document.readyState !== 'loading') {
    autoInit();
  } else {
    document.addEventListener('DOMContentLoaded', autoInit);
  }

  // 暴露到全局
  window.ZBCMotion = Motion;
  // 兼容旧命名
  window.AdaptiveMotion = Motion;
})();
