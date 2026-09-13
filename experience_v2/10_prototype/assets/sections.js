/* ============================================================================
 * LUMENIS Experience V2 — Section composition engine (Pattern -> Component)
 * Renders declarative section descriptors into the 10 core component families.
 * 44 screens may ONLY compose registered patterns/components (no bespoke layout).
 * All rendered data is prototype fixture: every root carries data-source=prototype.
 * Charts are deterministic inline SVG (no external chart library).
 * Exposes window.LumSections.render(section, state)
 * ========================================================================== */
(function (global) {
  'use strict';
  const { icon, sparkline, donut, stateBlock } = global.LumUI;
  const t = k => (global.LumI18n ? global.LumI18n.t(k) : k);
  // Internal domain/module codes (CTH/BMP/AI/SYS …) stay in data, never on the visible chrome.
  const human = s => (s == null ? s : String(s).replace(/^[A-Za-z]{2,}\s*[·•\-:：]\s*/, '').replace(/\s+[A-Z]{2,4}$/, ''));
  // normalize step state aliases (is-done/is-active/null) -> done/active/todo
  const stepState = s => (s === 'done' || s === 'is-done') ? 'done'
    : (s === 'active' || s === 'is-active') ? 'active' : 'todo';

  /* ---------------- deterministic inline-SVG charts ---------------- */
  function barChart(series, { w = 520, h = 200, labels = [] } = {}) {
    const pad = 26, max = Math.max(...series.flatMap(s => s.data), 1);
    const bw = (w - pad * 2) / series[0].data.length;
    const grp = series.length;
    return `<svg viewBox="0 0 ${w} ${h}" class="lum-chart" role="img" aria-label="chart">
      ${[0.25, .5, .75, 1].map(f => `<line x1="${pad}" x2="${w - 8}" y1="${h - pad - f * (h - pad * 2)}" y2="${h - pad - f * (h - pad * 2)}" stroke="var(--lum-line)"/>`).join('')}
      ${series.map((s, si) => s.data.map((v, i) => {
        const bh = (v / max) * (h - pad * 2), x = pad + i * bw + si * (bw / (grp + 1)) + 3, y = h - pad - bh;
        return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(bw / (grp + 1) - 2).toFixed(1)}" height="${bh.toFixed(1)}" rx="3" fill="${s.color || 'var(--lum-c-brand-500)'}"/>`;
      }).join('')).join('')}
      ${labels.map((l, i) => `<text x="${pad + i * bw + bw / 2}" y="${h - 8}" text-anchor="middle" font-size="10" fill="var(--lum-text-3)">${l}</text>`).join('')}</svg>`;
  }
  function lineChart(series, { w = 520, h = 200, labels = [] } = {}) {
    const pad = 26; const all = series.flatMap(s => s.data); const min = Math.min(...all), max = Math.max(...all), span = (max - min) || 1;
    const X = i => pad + (i / (series[0].data.length - 1)) * (w - pad * 2);
    const Y = v => h - pad - ((v - min) / span) * (h - pad * 2);
    return `<svg viewBox="0 0 ${w} ${h}" class="lum-chart" role="img">
      ${[0, .5, 1].map(f => `<line x1="${pad}" x2="${w - 8}" y1="${h - pad - f * (h - pad * 2)}" y2="${h - pad - f * (h - pad * 2)}" stroke="var(--lum-line)"/>`).join('')}
      ${series.map(s => {
        const d = s.data.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1)).join(' ');
        const area = `${d} L${X(s.data.length - 1)} ${h - pad} L${X(0)} ${h - pad} Z`;
        return `<path d="${area}" fill="${s.color || 'var(--lum-c-brand-500)'}" opacity=".1"/><path d="${d}" fill="none" stroke="${s.color || 'var(--lum-c-brand-500)'}" stroke-width="2.2"/>`;
      }).join('')}
      ${labels.map((l, i) => i % Math.ceil(labels.length / 8 || 1) === 0 ? `<text x="${X(i)}" y="${h - 8}" text-anchor="middle" font-size="10" fill="var(--lum-text-3)">${l}</text>` : '').join('')}</svg>`;
  }
  function ring(parts, { size = 140 } = {}) {
    const total = parts.reduce((a, p) => a + p.v, 0) || 1; let acc = 0; const r = 54, c = 2 * Math.PI * r;
    return `<svg viewBox="0 0 140 140" width="${size}" height="${size}">${parts.map(p => {
      const len = (p.v / total) * c, seg = `<circle cx="70" cy="70" r="${r}" fill="none" stroke="${p.color}" stroke-width="14" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-acc}" transform="rotate(-90 70 70)"/>`; acc += len; return seg;
    }).join('')}<text x="70" y="68" text-anchor="middle" font-size="20" font-weight="700" fill="var(--lum-text)">${total}</text><text x="70" y="86" text-anchor="middle" font-size="10" fill="var(--lum-text-3)">total</text></svg>`;
  }
  function heat(rows, cols, vals) {
    const cell = 26;
    return `<svg viewBox="0 0 ${cols * cell + 60} ${rows * cell + 24}" class="lum-chart">${vals.map((row, ri) => row.map((v, ci) => {
      const a = .10 + .9 * v; return `<rect x="${48 + ci * cell}" y="${ri * cell}" width="${cell - 3}" height="${cell - 3}" rx="4" fill="var(--lum-c-brand-500)" fill-opacity="${a.toFixed(2)}"/>`;
    }).join('')).join('')}</svg>`;
  }

  /* ---------------- component renderers ---------------- */
  const R = {
    head(d) {
      return `<header class="lum-page-head lum-stack-2" data-reveal>
        <div class="lum-row"><span class="lum-eyebrow" ${d.eyebrowKey ? `data-i18n="${d.eyebrowKey}"` : ''}>${human(d.eyebrow || '')}</span>${d.badge ? `<span class="lum-badge ${d.badge.cls || 'lum-badge-neutral'}">${d.badge.text}</span>` : ''}</div>
        <h1 class="lum-display" ${d.titleKey ? `data-i18n="${d.titleKey}"` : ''}>${d.title}</h1>${d.desc ? `<p class="lum-body-2" style="max-width:760px">${d.desc}</p>` : ''}
        ${d.actions ? `<div class="lum-row" style="flex-wrap:wrap">${d.actions.map(actionBtn).join('')}</div>` : ''}</header>`;
    },
    kpis(d) {
      // Per-metric truth state: a metric with state!=ready renders an honest placeholder
      // (— + reason), never a fabricated 0. Mirrors the 13-state system at metric granularity.
      const NA_KIND = { notcollected: 'empty_notcollected', empty: 'empty_true', offline: 'offline', error: 'error', permission: 'empty_permission', blocked: 'blocked' };
      return `<section class="lum-grid-4 lum-stagger" data-reveal>${d.items.map(m => {
        const na = m.state && m.state !== 'ready';
        // ready 值区分数值 / 文本：只有真正可数值化的才走 countup，状态串/名称/日期直接渲染，杜绝 NaN
        const isNum = m.value !== null && m.value !== undefined && m.value !== '' &&
          typeof m.value !== 'boolean' && !Number.isNaN(Number(m.value));
        const valueHtml = na
          ? `<span class="lum-metric__na" data-metric-state="${m.state}" title="${m.stateNote || ''}">—</span>`
          : isNum
            ? `<span data-countup="${m.value}" data-decimals="${m.decimals || 0}">${m.value}</span>`
            : `<span class="lum-metric__text">${m.value == null ? '—' : m.value}</span>`;
        const dotCls = na ? 'lum-dot' : 'lum-dot lum-dot-ok';
        const NA_FALLBACK = { notcollected: '尚未采集', empty: '暂无记录', offline: '运行时不可用', error: '加载出错', permission: '无权限', blocked: '已阻断' };
        const naLabel = m.stateNote || (t('state.' + (NA_KIND[m.state] || 'empty_true'))) || NA_FALLBACK[m.state] || 'NA';
        const freshTxt = na ? naLabel : t('freshness.' + (m.fresh || 'live'));
        return `
        <div class="lum-card lum-metric" data-state-slot>
          <div class="lum-metric__top"><span class="lum-metric__label">${icon(m.icon || 'trend', 15)}${m.label}</span>${m.badge ? `<span class="lum-badge lum-badge-neutral">${m.badge}</span>` : ''}</div>
          <div class="lum-metric__value">${valueHtml}${m.unit && !na ? `<span class="lum-unit">${m.unit}</span>` : ''}</div>
          ${!na && m.delta != null ? `<span class="lum-metric__delta ${m.delta >= 0 ? 'lum-delta-up' : 'lum-delta-down'}">${icon(m.delta >= 0 ? 'arrow-up' : 'arrow-down', 13)}${Math.abs(m.delta)}${m.deltaUnit || '%'}</span>` : ''}
          ${!na && m.spark ? sparkline(m.spark, { color: m.sparkColor }) : ''}
          <div class="lum-metric__foot" ${m.source ? `data-provenance="${m.source}" title="${na ? (m.stateNote || '') : m.source}"` : ''}><span class="lum-metric__freshness"><span class="${dotCls}"></span>${freshTxt}</span>${m.evidenceId ? `<span class="lum-ai-cite">${icon('link', 12)}${m.evidenceId}</span>` : ''}</div>
        </div>`;}).join('')}</section>`;
    },
    evidence(d) {
      return `<section class="lum-card lum-card-pad" data-reveal>
        <div class="lum-section-head"><span class="lum-eyebrow">${t('comp.evidence_chain')}</span><h2 class="lum-h4">${d.title || ''}</h2></div>
        <div class="lum-evidence-list">${d.items.map(e => `
          <article class="lum-evidence lum-card-solid" data-active="${e.active ? 'true' : 'false'}">
            <i class="lum-evidence-rail" aria-hidden="true"></i>
            <div class="lum-evidence__head"><span class="lum-badge lum-badge-brand">${e.kind}</span><span class="lum-caption lum-mono">${e.id || 'EV:UNKNOWN'}</span><span class="lum-spacer"></span>${conf(e.conf)}</div>
            <div class="lum-evidence__chain">${(e.chain || []).map((n, i, a) => `<span class="lum-ev-node">${n}</span>${i < a.length - 1 ? `<span class="lum-ev-arrow">${icon('chevron-right', 12)}</span>` : ''}`).join('')}</div>
            <p class="lum-evidence__quote">${e.quote}</p>
            <div class="lum-evidence__meta"><span>${icon('clock', 12)}${e.time}</span><span>${icon('link', 12)}${e.source}</span>${e.provider ? `<span class="lum-ai-tool">${icon('orb', 12)}${e.provider}</span>` : ''}</div>
          </article>`).join('')}</div></section>`;
    },
    insight(d) {
      return `<section class="lum-card lum-insight" data-reveal>
        <span class="lum-insight__kind">${icon('orb', 14)}${d.kind || t('comp.insight')}</span>
        <p class="lum-insight__text">${d.text}</p>
        ${d.why ? `<div class="lum-insight__why">${icon('info', 15)}<span>${d.why}</span></div>` : ''}
        ${d.evidence ? `<div class="lum-row" style="margin-top:6px">${d.evidence.map(c => `<span class="lum-ai-cite">${icon('link', 12)}${c}</span>`).join('')}</div>` : ''}
        ${d.actions ? `<div class="lum-row" style="margin-top:8px">${d.actions.map(actionBtn).join('')}</div>` : ''}</section>`;
    },
    events(d) {
      return `<section class="lum-card lum-card-pad" data-reveal>
        <div class="lum-section-head"><span class="lum-eyebrow">${t('comp.events')}</span><h2 class="lum-h4">${d.title || ''}</h2><span class="lum-spacer"></span>${d.more ? `<button class="lum-btn lum-btn-ghost lum-btn-sm">${t('common.more')}</button>` : ''}</div>
        <div class="lum-stack-4">${d.items.map(e => `
          <article class="lum-event">
            <div class="lum-event__time"><span class="t">${e.time}</span><span class="d">${e.date || ''}</span></div>
            <div class="lum-event__rail"><i></i></div>
            <div class="lum-event__body"><div class="lum-row-between"><span class="lum-event__title">${e.title}</span>${levelBadge(e.level)}</div>
              <p class="lum-body-2">${e.desc || ''}</p>
              <div class="lum-event__tags">${(e.tags || []).map(x => `<span class="lum-chip">${x}</span>`).join('')}<span class="lum-caption lum-mono">${e.evidence || ''}</span></div>
          </article>`).join('')}</div></section>`;
    },
    risks(d) {
      return `<section class="lum-grid-2" data-reveal>${d.items.map(r => `
        <article class="lum-card lum-risk" data-level="${r.level}">
          <div class="lum-risk__head"><span class="lum-risk-level">${icon('risk', 14)}${t('risk.level.' + r.level)}</span>${r.score != null ? `<span class="lum-num fw-sb">${r.score}</span>` : ''}</div>
          <b class="lum-fs-sm">${r.title}</b><p class="lum-body-2">${r.desc || ''}</p>
          ${r.score != null ? `<div class="lum-risk__meter"><i style="width:${r.score}%"></i></div>` : ''}
          <div class="lum-row-between"><span class="lum-caption lum-mono">${r.evidence || ''}</span><button class="lum-btn lum-btn-ghost lum-btn-sm">${t('risk.handle')}</button></div>
        </article>`).join('')}</section>`;
    },
    timeline(d) {
      return `<section class="lum-card lum-card-pad" data-reveal><div class="lum-section-head"><span class="lum-eyebrow">${d.label || ''}</span><h2 class="lum-h4">${d.title || ''}</h2></div>
        <div class="lum-timeline">${d.items.map(i => `
          <div class="lum-tl-item ${i.done ? 'is-done' : ''}"><div class="lum-tl-time lum-mono">${i.time}</div><div class="lum-tl-title">${i.title}</div><div class="lum-tl-desc">${i.desc || ''}</div></div>`).join('')}</div></section>`;
    },
    table(d) {
      return `<section class="lum-table-wrap" data-reveal data-state-slot>
        ${d.title ? `<div class="lum-row-between" style="padding:14px 16px"><h2 class="lum-h4">${d.title}</h2>${d.action ? actionBtn(d.action) : ''}</div>` : ''}
        <table class="lum-table"><thead><tr>${d.columns.map(c => `<th class="${c.numeric ? 'lum-num' : ''}">${c.label}</th>`).join('')}</tr></thead>
        <tbody>${d.rows.map(row => `<tr>${d.columns.map((c, i) => `<td class="${c.numeric ? 'lum-num' : ''}">${cellFmt(c, row[c.key], row)}</td>`).join('')}</tr>`).join('')}</tbody></table></section>`;
    },
    chart(d) {
      const fn = d.kind === 'bar' ? barChart : d.kind === 'ring' ? ring : d.kind === 'heat' ? heat : lineChart;
      return `<section class="lum-card lum-card-pad" data-reveal>
        <div class="lum-row-between"><div><h2 class="lum-h4">${d.title}</h2>${d.sub ? `<p class="lum-caption">${d.sub}</p>` : ''}</div>${d.legend ? `<div class="lum-wrap">${d.legend.map(l => `<span class="lum-chip"><span class="lum-dot" style="color:${l.color}"></span>${l.label}</span>`).join('')}</div>` : ''}</div>
        <div style="margin-top:10px">${d.kind === 'ring' ? fn(d.parts) : d.kind === 'heat' ? fn(d.rows, d.cols, d.vals) : fn(d.series, { labels: d.labels })}</div></section>`;
    },
    filters(d) {
      return `<section class="lum-card" style="padding:12px 16px" data-reveal><div class="lum-row" style="flex-wrap:wrap;gap:10px">
        <div class="lum-search" style="min-width:220px">${icon('search')}<input class="lum-input" data-i18n-ph="common.search" data-i18n-aria="common.search" placeholder="" aria-label="search"></div>
        ${d.chips ? d.chips.map(c => `<button class="lum-chip lum-press" aria-pressed="${c.on ? 'true' : 'false'}">${c.label}</button>`).join('') : ''}
        <span class="lum-spacer"></span>
        <button class="lum-btn lum-btn-secondary lum-btn-sm">${icon('filter', 15)}${t('common.filter')}</button></div></section>`;
    },
    cards(d) {
      return `<section class="lum-grid-${d.cols || 3} lum-stagger" data-reveal>${d.items.map(c => `
        <article class="lum-card lum-card-pad lum-press" style="gap:10px">
          <div class="lum-row-between">${c.ico ? `<span class="lum-action-item__ico">${icon(c.ico)}</span>` : '<span></span>'}${c.badge ? `<span class="lum-badge lum-badge-${c.badge.cls || 'neutral'}">${c.badge.text}</span>` : ''}</div>
          <b class="lum-h4">${c.title}</b><p class="lum-body-2">${c.desc || ''}</p>
          ${c.meta ? `<div class="lum-caption lum-mono">${c.meta}</div>` : ''}
          ${c.action ? `<div class="lum-row">${actionBtn(c.action)}</div>` : ''}</article>`).join('')}</section>`;
    },
    actions(d) {
      return `<section class="lum-card lum-action-panel" data-reveal><div class="lum-section-head"><span class="lum-eyebrow">${t('comp.actions')}</span><h2 class="lum-h4">${d.title || ''}</h2></div>
        ${d.items.map(a => `<button class="lum-action-item" data-action="${a.id || ''}" data-act-class="${a.cls || 'NAVIGATION'}"
            data-scope="${a.scope || 'UNKNOWN'}" data-target="${a.target || 'UNKNOWN'}" data-permission="${a.permission || 'UNKNOWN'}" ${a.risk ? 'data-risk="high"' : ''}>
          <span class="lum-action-item__ico">${icon(a.icon || 'zap')}</span>
          <span class="lum-action-item__txt"><b>${a.title}</b><span>${a.desc || ''}</span></span>
          <span class="lum-action-item__scope">${a.cls || 'NAVIGATION'}</span>${icon('chevron-right', 16)}</button>`).join('')}</section>`;
    },
    upload(d) {
      return `<section class="lum-card lum-card-pad" data-reveal><div class="lum-section-head"><span class="lum-eyebrow">${t('comp.pipeline')}</span><h2 class="lum-h4">${d.title || ''}</h2></div>
        <div class="lum-softglass" style="border:1.5px dashed var(--lum-line-strong);padding:28px;text-align:center">${icon('upload', 28)}<p class="lum-fw-sb" style="margin:8px 0 2px">${d.dropTitle || ''}</p><p class="lum-caption">${d.dropHint || ''}</p></div>
        <div class="lum-stack-2" style="margin-top:14px">${d.files.map(f => `
          <div><div class="lum-row-between lum-caption"><span class="lum-fw-sb lum-text-2">${icon('content', 14)}${f.name}</span><span class="lum-mono">${f.pct}%</span></div>
          <div class="lum-progress"><i style="width:${f.pct}%"></i></div><div class="lum-caption" style="margin-top:4px">${f.stage}</div></div>`).join('')}</div></section>`;
    },
    runtime(d) {
      return `<section class="lum-card lum-card-pad" data-reveal><div class="lum-section-head"><span class="lum-eyebrow">Runtime</span><h2 class="lum-h4">${d.title || ''}</h2></div>
        <div class="lum-runtime__grid">${d.items.map(s => `
          <div class="lum-runtime"><span class="lum-dot lum-dot-${s.state}"></span><div><b class="lum-fs-sm">${s.name}</b><div class="lum-caption lum-mono">${s.detail || ''}</div></div></div>`).join('')}</div></section>`;
    },
    ai(d) {
      return `<section class="lum-card lum-card-pad lum-ai" data-reveal>${d.title ? `<h3 class="lum-h4" style="margin-bottom:12px">${d.title}</h2>` : ''}${(d.thread || []).map(m => aiMsg(m)).join('')}${d.steps ? `<div class="lum-stack-2">${d.steps.map((s) => {
        const stt = stepState(s.state);
        return `<div class="lum-ai-step" data-state="${stt}">${icon(stt === 'done' ? 'check' : stt === 'todo' ? 'circle' : 'loader', 14)}<span>${s.label}</span><span class="lum-spacer"></span><span class="lum-mono lum-caption">${s.tool || ''}</span></div>`;
      }).join('')}</div>` : ''}${d.children || ''}</section>`;
    },
    split(d) { return `<div class="lum-grid-main-side"><div class="lum-stack-6">${(d.main || []).map(s => render(s)).join('')}</div><div class="lum-stack-6">${(d.side || []).map(s => render(s)).join('')}</div></div>`; },
    stack(d) { return `<div class="lum-stack-${d.gap || 6}">${(d.children || []).map(render).join('')}</div>`; },
    tabs(d) {
      return `<section data-reveal><div class="lum-tabs" role="tablist">${d.tabs.map((tb, i) => `<button aria-selected="${i === 0 ? 'true' : 'false'}" data-target="#${d.id}-p${i}">${tb.label}</button>`).join('')}</div>
        ${d.tabs.map((tb, i) => `<div data-panel id="${d.id}-p${i}" class="lum-stack-6" style="margin-top:16px;${i ? 'display:none' : ''}">${(tb.sections || []).map(render).join('')}</div>`).join('')}</section>`;
    },
    steps(d) {
      // Internal operating procedure stays in the viewmodel/logic (Codex contract),
      // it is never surfaced as UI. Concrete instance lifecycle status uses internal:false.
      if (d.internal) return '';
      return `<section class="lum-card lum-card-pad" data-reveal>${d.title ? `<h3 class="lum-h4" style="margin-bottom:12px">${d.title}</h2>` : ''}<div class="lum-steps">${d.items.map((s, i) => {
        const stt = stepState(s.state);
        return `<div class="lum-step ${stt}"><span class="n">${stt === 'done' ? icon('check', 12) : i + 1}</span><span class="lum-step-label">${s.label}</span>${i < d.items.length - 1 ? '<span class="lum-step-line"></span>' : ''}</div>`;
      }).join('')}</div>${d.children || ''}</section>`;
    },
    form(d) {
      return `<section class="lum-card lum-card-pad lum-stack-4" data-reveal><h2 class="lum-h4">${d.title || ''}</h2>
        ${d.fields.map(f => `<div class="lum-field"><label class="lum-label">${f.label}</label>${f.type === 'select' ? `<select class="lum-select" aria-label="${f.label}">${(f.opts || []).map(o => `<option>${o}</option>`).join('')}</select>` : f.type === 'textarea' ? `<textarea class="lum-textarea" placeholder="${f.ph || ''}" aria-label="${f.label}"></textarea>` : `<input class="lum-input" placeholder="${f.ph || ''}" aria-label="${f.label}">`}</div>`).join('')}
        <div class="lum-row">${(d.actions || []).map(actionBtn).join('')}</div></section>`;
    },
    note(d){return `<section class="lum-card lum-card-pad" style="border-left:3px solid var(--lum-c-info)"><div class="lum-row"><span class="lum-badge lum-badge-info">${d.kind||'NOTE'}</span><span class="lum-caption lum-mono">${d.code||''}</span></div><p class="lum-body-2" style="margin-top:8px">${d.text}</p></section>`;},
    raw(d){return d.html||'';}
  };

  function actionBtn(a) {
    return `<button class="lum-btn lum-btn-${a.variant || 'primary'} ${a.size ? 'lum-btn-' + a.size : ''}" data-action="${a.id || ''}" data-act-class="${a.cls || 'NAVIGATION'}"
      data-scope="${a.scope || 'UNKNOWN'}" data-target="${a.target || 'UNKNOWN'}" data-permission="${a.permission || 'UNKNOWN'}" ${a.risk ? 'data-risk="high"' : ''}>${a.ico ? icon(a.ico, 15) : ''}${a.label}</button>`;
  }
  function conf(c) { if (c == null || c === '') return ''; return `<span class="lum-conf">${icon('check', 12)}${t('comp.confidence')}<span class="lum-conf-bar"><i style="width:${c}%"></i></span><span class="lum-mono">${c}%</span></span>`; }
  function levelBadge(l) { const m = { low: 'lum-badge-success', med: 'lum-badge-warning', high: 'lum-badge-danger', critical: 'lum-badge-danger' }; return `<span class="lum-badge ${m[l] || 'lum-badge-neutral'}">${t('risk.level.' + (l || 'low'))}</span>`; }
  function cellFmt(c, v, row) { if (c.type === 'badge') return `<span class="lum-badge lum-badge-${row[c.toneKey] || 'neutral'}">${v}</span>`; if (c.type === 'delta') return `<span class="lum-metric__delta ${v >= 0 ? 'lum-delta-up' : 'lum-delta-down'}">${v >= 0 ? '+' : ''}${v}</span>`; return v; }
  function aiMsg(m) {
    return `<div class="lum-ai-msg" data-who="${m.who}"><div class="lum-ai-avatar">${m.who === 'ai' ? icon('orb', 16) : icon('user', 16)}</div>
      <div class="lum-ai-bubble">${m.text}${m.cites ? m.cites.map(c => `<span class="lum-ai-cite">${icon('link', 11)}${c}</span>`).join('') : ''}${m.tools ? m.tools.map(x => `<span class="lum-ai-tool">${icon('skill', 11)}${x}</span>`).join('') : ''}</div></div>`;
  }

  /** Render one section; inject a state block if section.state requests it (11 states). */
  function render(sec) {
    if (!sec) return '';
    if (sec.state && sec.state !== 'ready') {
      const wrap = R[sec.type] ? `<div class="lum-hide" data-real>${R[sec.type]({ ...sec, state: 'ready' })}</div>` : '';
      const acts = sec.stateActions ? sec.stateActions.map(actionBtn).join('') : '';
      return wrap + `<div data-state-slot>${stateBlock(stateKind(sec.state), acts)}</div>`;
    }
    const fn = R[sec.type]; if (!fn) return stateBlock('error');
    return fn(sec);
  }
  function stateKind(s) { return ({ loading: 'loading', empty: 'empty_true', notcollected: 'empty_notcollected', filtered: 'empty_filter', permission: 'empty_permission', error: 'error', offline: 'offline', blocked: 'blocked' })[s] || 'empty_true'; }

  global.LumSections = { render, R, barChart, lineChart, ring };
})(window);
