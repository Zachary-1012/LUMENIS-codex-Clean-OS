/* ============================================================
 * 序境 Xujing · 统一可视化函数层 v1.0
 * 函数驱动：数据获取 → Canonical 函数转换 → 表格 → SVG 趋势图/环形图 → 数字滚动 → 实时更新
 * 所有渲染均为纯函数，数据从 API 函数转换进来，不重复计算业务指标。
 * ============================================================ */
(function (global) {
  'use strict';

  /* ---------- 1. 数据获取层（统一 fetch，带 auth） ---------- */
  const api = async function (endpoint, params) {
    let url = endpoint.startsWith('http') ? endpoint : '/api' + (endpoint.startsWith('/') ? endpoint : '/' + endpoint);
    if (params) {
      const qs = new URLSearchParams(params).toString();
      if (qs) url += (url.includes('?') ? '&' : '?') + qs;
    }
    if (global.LUMENIS && global.LUMENIS.Auth && typeof global.LUMENIS.Auth.getHeader === 'function') {
      try { const h = await global.LUMENIS.Auth.getHeader(); if (h) global.__Z_AUTH = h; } catch (e) {}
    }
    const headers = {};
    if (global.__Z_AUTH) headers['Authorization'] = global.__Z_AUTH;
    const r = await fetch(url, { headers, credentials: 'include' });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    return d;
  };

  /* ---------- 2. Canonical 纯函数转换层（业务指标唯一真相） ---------- */
  const fn = {
    // FN-SENTIMENT-COUNT：情感计数（high 只计 high，critical 独立）
    FN_SENTIMENT_COUNT: function (data) {
      const s = data.stats || data.sentiment || data;
      return {
        positive: Number(s.positive || 0),
        neutral: Number(s.neutral || 0),
        negative: Number(s.negative || 0),
        total: Number(s.total || (s.positive || 0) + (s.neutral || 0) + (s.negative || 0))
      };
    },
    // FN-RISK-COUNT：风险计数（high 只计 high，critical 独立成更高指标）
    FN_RISK_COUNT: function (data) {
      const s = data.stats || data.risk || data;
      return {
        critical: Number(s.critical || 0),
        high: Number(s.high_risk || s.high || 0),
        medium: Number(s.medium_risk || s.medium || 0),
        low: Number(s.low_risk || s.low || 0),
        total: Number(s.total_risk || (s.high_risk || 0) + (s.medium_risk || 0) + (s.low_risk || 0))
      };
    },
    // FN-ENGAGEMENT：互动量（likes+comments+collects+shares）
    FN_ENGAGEMENT: function (data) {
      const s = data.stats || data.engagement || data;
      return {
        likes: Number(s.likes || 0),
        comments: Number(s.comments || s.total_comments || 0),
        collects: Number(s.collects || 0),
        shares: Number(s.shares || 0),
        total: Number(s.total_engagements || s.engagement || (s.likes || 0) + (s.comments || 0) + (s.collects || 0) + (s.shares || 0))
      };
    },
    // FN-TREND-SERIES：标准化时间序列
    FN_TREND_SERIES: function (trendArray, metric) {
      if (!Array.isArray(trendArray)) return [];
      return trendArray.map(function (d) {
        return {
          date: d.date || d.label || '',
          label: d.label || (d.date ? d.date.slice(5) : ''),
          value: Number(d[metric] || d.total || 0),
          total: Number(d.total || 0),
          positive: Number(d.positive || 0),
          negative: Number(d.negative || 0),
          high: Number(d.high || 0)
        };
      });
    }
  };

  /* ---------- 3. 工具函数 ---------- */
  const _ = {
    el: function (sel) { return typeof sel === 'string' ? document.querySelector(sel) : sel; },
    svgEl: function (tag, attrs) {
      const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
      if (attrs) for (const k in attrs) el.setAttribute(k, attrs[k]);
      return el;
    },
    fmt: function (n) {
      if (n >= 10000) return (n / 10000).toFixed(1) + '万';
      if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
      return String(Math.round(n));
    },
    clamp: function (v, min, max) { return Math.max(min, Math.min(max, v)); }
  };

  /* ---------- 4. 数字滚动动效 ---------- */
  function animateNumber(el, from, to, duration) {
    duration = duration || 800;
    const start = performance.now();
    const isFloat = String(to).includes('.') || to % 1 !== 0;
    function tick(now) {
      const t = _.clamp((now - start) / duration, 0, 1);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      const val = from + (to - from) * eased;
      el.textContent = isFloat ? val.toFixed(1) : _.fmt(val);
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /* ---------- 5. KPI 卡片渲染（数字滚动动效） ---------- */
  function kpi(container, label, value, opts) {
    opts = opts || {};
    const el = _.el(container);
    if (!el) return;
    const oldVal = parseFloat(el.dataset.value || '0');
    el.dataset.value = value;
    const colorClass = opts.color ? 'xj-kpi-' + opts.color : '';
    el.innerHTML = '<div class="xj-kpi-label">' + label + '</div>' +
      '<div class="xj-kpi-value ' + colorClass + '">' + _.fmt(oldVal) + '</div>' +
      (opts.sub ? '<div class="xj-kpi-sub">' + opts.sub + '</div>' : '');
    const valEl = el.querySelector('.xj-kpi-value');
    animateNumber(valEl, oldVal, value, opts.duration || 800);
  }

  /* ---------- 6. 表格渲染（数据→HTML 表格） ---------- */
  function table(container, data, columns) {
    const el = _.el(container);
    if (!el) return;
    if (!Array.isArray(data) || data.length === 0) {
      el.innerHTML = '<div class="xj-empty">暂无数据</div>';
      return;
    }
    let html = '<table class="xj-data-table"><thead><tr>';
    columns.forEach(function (c) {
      html += '<th>' + (c.label || c.key) + '</th>';
    });
    html += '</tr></thead><tbody>';
    data.forEach(function (row) {
      html += '<tr>';
      columns.forEach(function (c) {
        const val = c.render ? c.render(row[c.key], row) : row[c.key];
        html += '<td>' + (val == null ? '-' : val) + '</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
  }

  /* ---------- 7. SVG 趋势图渲染（折线/面积/柱状，带动画） ---------- */
  function trend(container, series, opts) {
    opts = opts || {};
    const el = _.el(container);
    if (!el) return;
    const W = opts.width || el.clientWidth || 320;
    const H = opts.height || 160;
    const pad = { top: 12, right: 12, bottom: 24, left: 32 };
    const iw = W - pad.left - pad.right;
    const ih = H - pad.top - pad.bottom;

    el.innerHTML = '';
    const svg = _.svgEl('svg', { width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, class: 'xj-trend-svg' });
    el.appendChild(svg);

    if (!series || series.length === 0) {
      svg.innerHTML = '<text x="' + (W / 2) + '" y="' + (H / 2) + '" text-anchor="middle" fill="#aeb4bf" font-size="12">暂无趋势数据</text>';
      return;
    }

    const maxVal = Math.max.apply(null, series.map(function (d) { return d.value; }).concat([1]));
    const minVal = 0;
    const n = series.length;

    function x(i) { return pad.left + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw); }
    function y(v) { return pad.top + ih - ((v - minVal) / (maxVal - minVal || 1)) * ih; }

    // 网格线
    for (let g = 0; g <= 3; g++) {
      const gy = pad.top + (g / 3) * ih;
      const gv = maxVal - (g / 3) * maxVal;
      svg.appendChild(_.svgEl('line', { x1: pad.left, y1: gy, x2: W - pad.right, y2: gy, stroke: '#e8eaee', 'stroke-width': 0.5 }));
      const t = _.svgEl('text', { x: pad.left - 4, y: gy + 3, 'text-anchor': 'end', fill: '#aeb4bf', 'font-size': 9 });
      t.textContent = _.fmt(gv);
      svg.appendChild(t);
    }

    // 类型：line / area / bar
    const type = opts.type || 'area';

    if (type === 'bar') {
      const bw = Math.max(2, iw / n * 0.6);
      series.forEach(function (d, i) {
        const bx = x(i) - bw / 2;
        const by = y(d.value);
        const bh = pad.top + ih - by;
        const rect = _.svgEl('rect', { x: bx, y: by, width: bw, height: 0, fill: opts.color || '#2f9e6e', rx: 2 });
        svg.appendChild(rect);
        setTimeout(function () { rect.setAttribute('height', bh); rect.style.transition = 'height .6s cubic-bezier(.22,1,.36,1)'; }, 30 + i * 40);
      });
    } else {
      // 折线路径
      let linePath = '';
      let areaPath = 'M' + x(0) + ',' + (pad.top + ih);
      series.forEach(function (d, i) {
        const px = x(i), py = y(d.value);
        linePath += (i === 0 ? 'M' : 'L') + px + ',' + py + ' ';
        areaPath += 'L' + px + ',' + py + ' ';
      });
      areaPath += 'L' + x(n - 1) + ',' + (pad.top + ih) + ' Z';

      if (type === 'area') {
        const area = _.svgEl('path', { d: areaPath, fill: opts.areaColor || 'url(#xjTrendGrad)', opacity: 0 });
        const grad = _.svgEl('defs', {});
        grad.innerHTML = '<linearGradient id="xjTrendGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="' + (opts.color || '#2f9e6e') + '" stop-opacity="0.25"/><stop offset="100%" stop-color="' + (opts.color || '#2f9e6e') + '" stop-opacity="0.02"/></linearGradient>';
        svg.appendChild(grad);
        svg.appendChild(area);
        setTimeout(function () { area.style.transition = 'opacity .8s ease'; area.setAttribute('opacity', '1'); }, 50);
      }

      const line = _.svgEl('path', { d: linePath, fill: 'none', stroke: opts.color || '#2f9e6e', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
      const len = line.getTotalLength ? 1000 : 0;
      if (len) {
        line.style.strokeDasharray = len;
        line.style.strokeDashoffset = len;
        line.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(.22,1,.36,1)';
      }
      svg.appendChild(line);
      if (len) setTimeout(function () { line.style.strokeDashoffset = '0'; }, 80);

      // 数据点
      series.forEach(function (d, i) {
        const dot = _.svgEl('circle', { cx: x(i), cy: y(d.value), r: 0, fill: '#fff', stroke: opts.color || '#2f9e6e', 'stroke-width': 2 });
        svg.appendChild(dot);
        setTimeout(function () { dot.style.transition = 'r .3s ease'; dot.setAttribute('r', 3); }, 400 + i * 60);
      });
    }

    // X 轴标签（稀疏显示）
    const labelStep = Math.max(1, Math.ceil(n / 6));
    series.forEach(function (d, i) {
      if (i % labelStep === 0 || i === n - 1) {
        const t = _.svgEl('text', { x: x(i), y: H - 6, 'text-anchor': 'middle', fill: '#8b91a0', 'font-size': 9 });
        t.textContent = d.label || '';
        svg.appendChild(t);
      }
    });
  }

  /* ---------- 8. 环形图渲染 ---------- */
  function donut(container, data, opts) {
    opts = opts || {};
    const el = _.el(container);
    if (!el) return;
    const size = opts.size || 120;
    const r = size / 2 - 8;
    const cx = size / 2, cy = size / 2;
    const total = data.reduce(function (s, d) { return s + Number(d.value || 0); }, 0) || 1;

    el.innerHTML = '';
    const svg = _.svgEl('svg', { width: size, height: size, viewBox: '0 0 ' + size + ' ' + size, class: 'xj-donut-svg' });
    el.appendChild(svg);

    // 背景环
    svg.appendChild(_.svgEl('circle', { cx: cx, cy: cy, r: r, fill: 'none', stroke: '#e8eaee', 'stroke-width': opts.thickness || 10 }));

    let offset = 0;
    const circ = 2 * Math.PI * r;
    data.forEach(function (d, i) {
      const frac = Number(d.value || 0) / total;
      const dash = frac * circ;
      const seg = _.svgEl('circle', {
        cx: cx, cy: cy, r: r, fill: 'none',
        stroke: d.color || '#2f9e6e', 'stroke-width': opts.thickness || 10,
        'stroke-dasharray': dash + ' ' + (circ - dash),
        'stroke-dashoffset': -offset,
        transform: 'rotate(-90 ' + cx + ' ' + cy + ')',
        opacity: 0
      });
      svg.appendChild(seg);
      setTimeout(function () { seg.style.transition = 'opacity .5s ease'; seg.setAttribute('opacity', '1'); }, 100 + i * 120);
      offset += dash;
    });

    // 中心文字
    if (opts.centerLabel) {
      const t1 = _.svgEl('text', { x: cx, y: cy - 4, 'text-anchor': 'middle', fill: '#1a1d23', 'font-size': '18', 'font-weight': '700' });
      t1.textContent = _.fmt(total);
      svg.appendChild(t1);
      const t2 = _.svgEl('text', { x: cx, y: cy + 14, 'text-anchor': 'middle', fill: '#8b91a0', 'font-size': '10' });
      t2.textContent = opts.centerLabel;
      svg.appendChild(t2);
    }
  }

  /* ---------- 9. Stagger 级联动效 ---------- */
  function stagger(container) {
    const el = _.el(container);
    if (!el) return;
    el.classList.add('xj-stagger');
    const kids = el.children;
    for (let i = 0; i < kids.length; i++) {
      kids[i].style.animationDelay = (0.03 + i * 0.05) + 's';
    }
  }

  /* ---------- 10. 实时更新循环（定时刷新 + 平滑过渡） ---------- */
  function realtime(container, endpoint, interval, renderFn) {
    let stopped = false;
    let currentData = null;
    async function tick() {
      if (stopped) return;
      try {
        const data = await api(endpoint);
        currentData = data;
        renderFn(container, data);
      } catch (e) { /* 静默失败，下次重试 */ }
      setTimeout(tick, interval || 30000);
    }
    tick();
    return {
      stop: function () { stopped = true; },
      getData: function () { return currentData; },
      refresh: tick
    };
  }

  /* ---------- 11. 组合渲染：AI 洞察面板（趋势图 + KPI + 环形图） ---------- */
  function renderAIPanel(container, data) {
    const el = _.el(container);
    if (!el || !data) return;
    const stats = data.stats || {};
    const overview = data.overview || {};
    const sentiment = fn.FN_SENTIMENT_COUNT(stats);
    const risk = fn.FN_RISK_COUNT(stats);
    const engagement = fn.FN_ENGAGEMENT(stats);

    // KPI 行
    const kpiRow = el.querySelector('.xj-kpi-row') || (function () {
      const d = document.createElement('div');
      d.className = 'xj-kpi-row xj-stagger';
      el.insertBefore(d, el.firstChild);
      return d;
    })();
    kpiRow.innerHTML = '';
    const kpis = [
      { label: '正面舆情', value: sentiment.positive, color: 'pos' },
      { label: '负面舆情', value: sentiment.negative, color: 'neg' },
      { label: '高风险内容', value: risk.high, color: 'warn' },
      { label: '总互动量', value: engagement.total, color: '' }
    ];
    kpis.forEach(function (k) {
      const card = document.createElement('div');
      card.className = 'xj-kpi-card';
      kpiRow.appendChild(card);
      kpi(card, k.label, k.value, { color: k.color });
    });

    // 趋势图
    const trendEl = el.querySelector('.xj-trend-container') || (function () {
      const d = document.createElement('div');
      d.className = 'xj-trend-container';
      el.appendChild(d);
      return d;
    })();
    const trendData = fn.FN_TREND_SERIES(overview.trend || [], 'total');
    trend(trendEl, trendData, { type: 'area', color: '#2f9e6e', height: 140 });

    // 情感环形图
    const donutEl = el.querySelector('.xj-donut-container') || (function () {
      const d = document.createElement('div');
      d.className = 'xj-donut-container';
      el.appendChild(d);
      return d;
    })();
    donut(donutEl, [
      { label: '正面', value: sentiment.positive, color: '#2f9e6e' },
      { label: '中性', value: sentiment.neutral, color: '#aeb4bf' },
      { label: '负面', value: sentiment.negative, color: '#c0463a' }
    ], { centerLabel: '情感分布', size: 110, thickness: 9 });
  }

  /* ---------- 导出 ---------- */
  global.xjViz = {
    api: api,
    fn: fn,
    kpi: kpi,
    table: table,
    trend: trend,
    donut: donut,
    animateNumber: animateNumber,
    stagger: stagger,
    realtime: realtime,
    renderAIPanel: renderAIPanel
  };
})(window);
