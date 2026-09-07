/* ============================================================
 * ZBC 全局趋势线组件 v1.1
 * 函数驱动：API获取 → xujing-viz FN_TREND_SERIES → SVG趋势线 → 动效
 * 所有有时间序列的页面统一调用，不重复实现。
 * 用法：ZBCTrendLine.render(containerId, '/api/trend/notes', {title:'笔记趋势', days:30})
 *
 * v1.1 变更（P1-7 性能修复）：
 * - 新增按 endpoint+days 的内存缓存（TTL 60s），避免重复请求
 * - autoRefresh 定时器存储在 container.dataset 上，重渲染前 clearTimeout 旧定时器
 * - fetch 失败时显示 error 状态（不再静默）
 * ============================================================ */
(function (global) {
  'use strict';

  // ---- P1-7: 内存缓存（endpoint+days → {data, timestamp}）----
  var _cache = new Map();
  var _CACHE_TTL_MS = 60 * 1000; // 60 秒

  function _cacheKey(endpoint, days) {
    return endpoint + '::days=' + days;
  }

  function _cacheGet(endpoint, days) {
    var key = _cacheKey(endpoint, days);
    var entry = _cache.get(key);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > _CACHE_TTL_MS) {
      _cache.delete(key);
      return null;
    }
    return entry.data;
  }

  function _cacheSet(endpoint, days, data) {
    var key = _cacheKey(endpoint, days);
    _cache.set(key, { data: data, timestamp: Date.now() });
  }

  // ---- P1-7: 定时器管理（存 container.dataset，重渲染前清理）----
  function _clearAutoRefresh(container) {
    if (container && container.dataset && container.dataset.zbcTrendTimer) {
      clearTimeout(Number(container.dataset.zbcTrendTimer));
      delete container.dataset.zbcTrendTimer;
    }
  }

  function _setAutoRefresh(container, timerId) {
    if (container && container.dataset) {
      container.dataset.zbcTrendTimer = String(timerId);
    }
  }

  const TrendLine = {
    version: '1.1',

    /**
     * 渲染趋势线
     * @param {string} containerId - 容器元素ID
     * @param {string} apiEndpoint - 趋势API路径（如 /api/trend/notes）
     * @param {object} options - 配置项
     */
    render: async function (containerId, apiEndpoint, options) {
      const opts = Object.assign({
        title: '',
        days: 30,
        height: 180,
        color: '#00D4AA',
        metric: 'count',
        showArea: true,
        animate: true,
        autoRefresh: 0,  // 秒，0=不自动刷新
        emptyText: '暂无趋势数据'
      }, options || {});

      const container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
      if (!container) { console.warn('[TrendLine] 容器不存在:', containerId); return; }

      // P1-7: 重渲染前清理旧定时器，防止定时器叠加
      _clearAutoRefresh(container);

      // 渲染骨架
      container.innerHTML = `
        <div class="zbc-trend" style="width:100%;">
          ${opts.title ? `<div class="zbc-trend__title" style="font-size:13px;font-weight:600;color:#374151;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
            <span>${opts.title}</span>
            <span class="zbc-trend__value" style="font-size:18px;font-weight:700;color:${opts.color};"></span>
          </div>` : ''}
          <div class="zbc-trend__chart" style="width:100%;height:${opts.height}px;position:relative;"></div>
        </div>`;

      const chartEl = container.querySelector('.zbc-trend__chart');
      const valueEl = container.querySelector('.zbc-trend__value');

      try {
        let data;
        // P1-7: 优先读缓存
        const cached = _cacheGet(apiEndpoint, opts.days);
        if (cached) {
          data = cached;
        } else {
          const url = apiEndpoint + (apiEndpoint.includes('?') ? '&' : '?') + 'days=' + opts.days;
          const resp = await fetch(url, { headers: global.__Z_AUTH ? { 'Authorization': global.__Z_AUTH } : {} });
          if (!resp.ok) {
            throw new Error('HTTP ' + resp.status);
          }
          data = await resp.json();
          // P1-7: 写入缓存
          _cacheSet(apiEndpoint, opts.days, data);
        }

        if (!data.ok || !data.series || data.series.length === 0) {
          chartEl.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#9CA3AF;font-size:12px;">${opts.emptyText}</div>`;
          return;
        }

        const series = data.series;
        const total = series.reduce((sum, d) => sum + (d[opts.metric] || d.total || 0), 0);

        if (valueEl) {
          if (opts.animate) {
            this._animateNumber(valueEl, 0, total, 800);
          } else {
            valueEl.textContent = total.toLocaleString();
          }
        }

        this._renderSVG(chartEl, series, opts);

        // P1-7: 自动刷新 — 定时器存 container.dataset，便于重渲染前清理
        if (opts.autoRefresh > 0) {
          const self = this;
          const timerId = setTimeout(function () {
            self.render(container, apiEndpoint, opts);
          }, opts.autoRefresh * 1000);
          _setAutoRefresh(container, timerId);
        }
      } catch (e) {
        // P1-7: fetch 失败显式 error 状态，不再静默
        console.error('[TrendLine] 加载失败:', apiEndpoint, e.message);
        chartEl.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#F87171;font-size:12px;flex-direction:column;gap:4px;">
          <span>加载失败</span>
          <span style="font-size:10px;color:#9CA3AF;">${e.message}</span>
        </div>`;
      }
    },

    /**
     * SVG趋势线渲染（纯函数，无依赖）
     */
    _renderSVG: function (container, series, opts) {
      const w = container.offsetWidth || 300;
      const h = opts.height || 180;
      const padL = 36, padR = 12, padT = 12, padB = 24;
      const chartW = w - padL - padR;
      const chartH = h - padT - padB;

      const values = series.map(d => d[opts.metric] || d.total || 0);
      const maxVal = Math.max(...values, 1);
      const minVal = Math.min(...values, 0);
      const range = maxVal - minVal || 1;

      // X坐标
      const xStep = series.length > 1 ? chartW / (series.length - 1) : chartW;
      const points = series.map((d, i) => ({
        x: padL + i * xStep,
        y: padT + chartH - ((d[opts.metric] || d.total || 0) - minVal) / range * chartH,
        value: d[opts.metric] || d.total || 0,
        date: d.date,
        label: d.label
      }));

      // 路径
      let linePath = '';
      let areaPath = '';
      points.forEach((p, i) => {
        linePath += (i === 0 ? 'M' : 'L') + p.x.toFixed(1) + ',' + p.y.toFixed(1) + ' ';
      });
      if (opts.showArea && points.length > 0) {
        areaPath = linePath + `L${points[points.length-1].x.toFixed(1)},${(padT+chartH).toFixed(1)} L${points[0].x.toFixed(1)},${(padT+chartH).toFixed(1)} Z`;
      }

      // Y轴刻度
      const yTicks = 4;
      let yAxis = '';
      for (let i = 0; i <= yTicks; i++) {
        const val = minVal + (range * i / yTicks);
        const y = padT + chartH - (i / yTicks) * chartH;
        yAxis += `<line x1="${padL}" y1="${y}" x2="${w-padR}" y2="${y}" stroke="#F3F4F6" stroke-width="1"/>`;
        yAxis += `<text x="${padL-6}" y="${y+4}" font-size="9" fill="#9CA3AF" text-anchor="end">${Math.round(val)}</text>`;
      }

      // X轴标签（稀疏显示）
      let xLabels = '';
      const labelStep = Math.max(1, Math.floor(series.length / 8));
      points.forEach((p, i) => {
        if (i % labelStep === 0 || i === points.length - 1) {
          xLabels += `<text x="${p.x}" y="${h-6}" font-size="9" fill="#9CA3AF" text-anchor="middle">${p.label}</text>`;
        }
      });

      // 数据点
      let dots = '';
      points.forEach(p => {
        dots += `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="2.5" fill="${opts.color}" opacity="0.9">
          <title>${p.date}: ${p.value}</title></circle>`;
      });

      // 渐变定义
      const gradId = 'grad-' + Math.random().toString(36).substr(2, 8);

      container.innerHTML = `
        <svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="display:block;">
          <defs>
            <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="${opts.color}" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="${opts.color}" stop-opacity="0.02"/>
            </linearGradient>
          </defs>
          ${yAxis}
          ${opts.showArea ? `<path d="${areaPath}" fill="url(#${gradId})"/>` : ''}
          <path d="${linePath}" fill="none" stroke="${opts.color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          ${dots}
          ${xLabels}
        </svg>`;

      // 入场动效
      if (opts.animate) {
        const path = container.querySelector('path[stroke]');
        if (path) {
          const length = path.getTotalLength ? path.getTotalLength() : 500;
          path.style.strokeDasharray = length;
          path.style.strokeDashoffset = length;
          path.style.transition = 'stroke-dashoffset 1s ease-out';
          requestAnimationFrame(() => { path.style.strokeDashoffset = '0'; });
        }
      }
    },

    /**
     * 数字滚动动效
     */
    _animateNumber: function (el, from, to, duration) {
      const start = performance.now();
      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(from + (to - from) * eased).toLocaleString();
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    },

    /**
     * 多趋势线对比（如正面vs负面）
     */
    renderMulti: async function (containerId, apiEndpoint, seriesConfig, options) {
      // seriesConfig: [{metric:'positive',color:'#10B981',name:'正面'},{metric:'negative',color:'#EF4444',name:'负面'}]
      const opts = Object.assign({ title: '', days: 30, height: 180 }, options || {});
      const container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
      if (!container) return;

      container.innerHTML = `<div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:8px;">${opts.title}</div><div style="height:${opts.height}px;"></div>`;
      const chartEl = container.querySelector('div:last-child');

      try {
        let data;
        const cached = _cacheGet(apiEndpoint, opts.days);
        if (cached) {
          data = cached;
        } else {
          const resp = await fetch(apiEndpoint + '?days=' + opts.days, { headers: global.__Z_AUTH ? { 'Authorization': global.__Z_AUTH } : {} });
          if (!resp.ok) throw new Error('HTTP ' + resp.status);
          data = await resp.json();
          _cacheSet(apiEndpoint, opts.days, data);
        }
        if (!data.ok || !data.series) { chartEl.innerHTML = '<div style="color:#9CA3AF;font-size:12px;padding:40px;text-align:center;">暂无数据</div>'; return; }

        const w = chartEl.offsetWidth || 300;
        const h = opts.height;
        const padL = 36, padR = 12, padT = 12, padB = 24;
        const chartW = w - padL - padR, chartH = h - padT - padB;
        const series = data.series;

        let allVals = [];
        seriesConfig.forEach(sc => { allVals = allVals.concat(series.map(d => d[sc.metric] || 0)); });
        const maxVal = Math.max(...allVals, 1);
        const xStep = series.length > 1 ? chartW / (series.length - 1) : chartW;

        let paths = '', legend = '';
        seriesConfig.forEach((sc, idx) => {
          let path = '';
          series.forEach((d, i) => {
            const x = padL + i * xStep;
            const y = padT + chartH - (d[sc.metric] || 0) / maxVal * chartH;
            path += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1) + ' ';
          });
          paths += `<path d="${path}" fill="none" stroke="${sc.color}" stroke-width="2" stroke-linecap="round"/>`;
          legend += `<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px;font-size:11px;color:#6B7280;"><span style="width:8px;height:8px;border-radius:50%;background:${sc.color};"></span>${sc.name}</span>`;
        });

        // X标签
        let xLabels = '';
        const labelStep = Math.max(1, Math.floor(series.length / 8));
        series.forEach((d, i) => {
          if (i % labelStep === 0 || i === series.length - 1) {
            const x = padL + i * xStep;
            xLabels += `<text x="${x}" y="${h-6}" font-size="9" fill="#9CA3AF" text-anchor="middle">${d.label || d.date?.slice(5) || ''}</text>`;
          }
        });

        chartEl.innerHTML = `
          <div style="margin-bottom:6px;">${legend}</div>
          <svg width="100%" height="${h-20}" viewBox="0 0 ${w} ${h-20}" preserveAspectRatio="none">
            ${paths}${xLabels}
          </svg>`;
      } catch (e) {
        console.error('[TrendLine] renderMulti 加载失败:', apiEndpoint, e.message);
        chartEl.innerHTML = `<div style="color:#F87171;font-size:12px;padding:20px;text-align:center;">加载失败: ${e.message}</div>`;
      }
    }
  };

  // 导出
  global.ZBCTrendLine = TrendLine;
  // 兼容旧名
  global.zbc_trend = TrendLine;

})(typeof window !== 'undefined' ? window : this);
