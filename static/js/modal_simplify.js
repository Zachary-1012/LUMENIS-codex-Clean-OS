/* ============================================================
 * modal_simplify.js — 弹窗精简补丁（ZBIP 渐进式展开规范）
 * ------------------------------------------------------------
 * 设计原则：
 * 1. 一眼看懂：标题 + 核心结论 + 风险状态 + 主动作
 * 2. 渐进展开：次要信息收进「详细分析」折叠区，不删任何数据
 * 3. 独立补丁：覆盖 app.js 的 openNote/openEvent/openCaseDetail
 *    不改 app.js 源文件，避免与并行开发冲突，可随时移除回滚
 * 4. 手机端友好：字段纵向堆叠，折叠区大触控区域
 * ============================================================ */
(function () {
  'use strict';

  // 折叠区生成器：默认收起，点击展开
  function detailToggle(innerHtml, label) {
    label = label || '详细分析';
    return `<details class="ms-detail"><summary>${label}</summary><div class="ms-detail-body">${innerHtml}</div></details>`;
  }
  // 单行键值
  function kv(k, v) {
    return `<div class="kv"><span>${k}</span><span>${v}</span></div>`;
  }
  // 风险等级样式
  function riskBadge(level, score) {
    const map = { high: ['高风险', 'ms-badge ms-badge-high'], medium: ['中风险', 'ms-badge ms-badge-med'], low: ['低风险', 'ms-badge ms-badge-low'] };
    const [txt, cls] = map[level] || ['低风险', 'ms-badge ms-badge-low'];
    return `<span class="${cls}">${txt} ${score || 0}</span>`;
  }
  function sentBadge(s) {
    const map = { negative: ['负面', 'ms-badge ms-badge-neg'], positive: ['正面', 'ms-badge ms-badge-pos'], neutral: ['中性', 'ms-badge ms-badge-neu'] };
    const [txt, cls] = map[s] || ['中性', 'ms-badge ms-badge-neu'];
    return `<span class="${cls}">${txt}</span>`;
  }

  /* ============ 1. 笔记详情弹窗：核心信息 + 折叠详细分析 ============ */
  window.openNote = function (n) {
    const bodyText = (n.content || n.body || '').trim();
    let mk = [];
    try { mk = JSON.parse(n.matched_keywords || '[]'); if (!Array.isArray(mk)) mk = []; } catch (_) { mk = (n.matched_keywords || '').split(',').map(s => s.trim()).filter(Boolean); }
    const pub = (n.publish_date || n.publish_datetime || '').substring(0, 10);

    // —— 核心区（一眼看懂）：标题 / 摘要 / 情感风险 / 互动 / 作者日期 ——
    const core = `
      <div class="modal-eyebrow">小红书笔记 · 详情</div>
      <h2 class="modal-title">${esc(n.title || '无标题')}</h2>
      <div class="ms-core-row">${sentBadge(n.sentiment)} ${riskBadge(n.risk_level, n.risk_score)}</div>
      <p class="big-summary">${esc(n.summary || n.ai_reason || '暂无摘要')}</p>
      ${bodyText
        ? `<div class="note-body-block"><div class="modal-eyebrow" style="margin:10px 0 6px">笔记正文</div><div class="note-body-text">${esc(bodyText)}</div></div>`
        : '<p class="muted" style="font-size:12px;margin:6px 0">正文尚未抓取（详情页补抓后展示）</p>'}
      <div class="ms-quick-meta">
        <span>${xicon('user')} ${esc(n.author_nickname || '匿名')}</span>
        <span>${xicon('calendar')} ${esc(pub || '未知')}</span>
        <span>${xicon('heart')} ${fmt(n.likes)} · ${xicon('chat')} ${fmt(n.comments)} · ${xicon('star')} ${fmt(n.collects)}</span>
      </div>`;

    // —— 次要信息折叠区 ——
    const secondary =
      kv('采集时间', esc(n.collected_at || '—')) +
      kv('内容分类', esc(n.category || '未分类')) +
      kv('事实状态', `${esc(n.verification_status || '待核实')} · 可信度 ${(Number(n.verification_confidence || 0) * 100).toFixed(0)}%`) +
      kv('分享数', fmt(n.shares)) +
      ((mk.length || n.source_keyword)
        ? kv('命中关键词', (mk.length ? mk : [n.source_keyword]).filter(Boolean).map(k => `<span class="tag">${esc(k)}</span>`).join(' '))
        : '') +
      kv('研判依据', esc(n.ai_reason || '规则引擎判断')) +
      (n.ai_insight ? kv('AI 洞察', esc(n.ai_insight)) : '') +
      (n.url ? `<p style="margin-top:8px"><a href="${esc(n.url)}" target="_blank" rel="noopener">打开小红书原文 ›</a></p>` : '');

    $('modalContent').innerHTML = core + detailToggle(secondary, '详细分析与研判依据');
    openModal();
  };

  /* ============ 2. 事件详情弹窗：风险结论优先 + 折叠研判过程 ============ */
  window.openEvent = function (e) {
    const FACT = { unconfirmed: '待核实', confirmed: '已核实', verifying: '核实中', 'false': '不实信息', refuted: '已辟谣' };
    const ESTATUS = { active: '监测中', monitoring: '监测中', resolved: '已平息', closed: '已关闭' };
    let kws = [];
    try { kws = JSON.parse(e.keywords || '[]'); } catch (_) { kws = []; }
    if (!Array.isArray(kws)) kws = [];
    const isNormDate = /^\d{4}-\d{2}-\d{2}$/.test(e.event_date || '');

    // —— 核心区：标题 / 摘要 / 风险等级 / 状态 / 建议动作 / 操作按钮 ——
    const core = `
      <div class="modal-eyebrow">舆情事件 · 聚合分析</div>
      <h2 class="modal-title">${esc(e.title || '未命名事件')}</h2>
      <div class="ms-core-row">
        ${riskBadge(e.risk_level, e.risk_score)}
        <span class="ms-badge ms-badge-neu">${esc(ESTATUS[e.status] || '监测中')}</span>
        <span class="ms-badge ms-badge-neu">${esc(FACT[e.fact_status] || '待核实')}</span>
      </div>
      <p class="big-summary">${esc(e.summary || '系统正在聚合更多来源并进行事实核验。')}</p>
      <div class="ms-action-box">
        <div class="ms-action-label">建议动作</div>
        <div>${esc(e.recommended_action || '持续观察，等待更多事实核验')}</div>
      </div>
      <div class="ms-quick-meta">
        <span>${xicon('chart')} ${e.source_count || 1} 类来源</span>
        <span>${xicon('doc')} ${e.mention_count || 1} 条提及</span>
        <span>${xicon('clock')} ${esc((e.first_seen || '—').substring(0, 16))}</span>
      </div>`;

    // —— 次要研判信息折叠 ——
    const secondary =
      kv('发生日期', isNormDate ? esc(e.event_date) : '待核实（将由关联笔记最早发布日期回填）') +
      kv('影响方向', esc({ negative: '偏负面', positive: '偏正面', neutral: '中性', mixed: '多面' }[e.impact] || '中性')) +
      kv('风险研判', esc(e.risk_reason || '暂无')) +
      kv('发现窗口', `${esc(e.first_seen || '—')} → ${esc(e.last_seen || '—')}（采集发现，非发生日期）`) +
      (kws.length ? kv('关联关键词', kws.map(k => `<span class="tag">${esc(k)}</span>`).join(' ')) : '') +
      kv('负面二次确认', `<b id="evRvState">${e.negative_confirmed === 1 ? '已确认负面' : e.negative_confirmed === 2 ? '已驳回（误报）' : '待人工确认'}</b>`);

    // —— 操作按钮（主动作突出）——
    const actions = `
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="action" id="evConfirmBtn" style="background:#34c759;color:#fff;border:none">确认负面</button>
        <button class="action secondary" id="evRejectBtn">驳回 / 误报</button>
        <button class="action secondary" id="eventCaseBtn">相关笔记案例</button>
      </div>`;

    $('modalContent').innerHTML = core + detailToggle(secondary, '研判过程与详情') + actions;
    openModal();

    // 绑定事件（保留原有逻辑）
    const RVTXT = { 1: '已确认负面', 2: '已驳回（误报）' };
    const doEventRv = async (st, btn) => {
      btn.disabled = true;
      try {
        const r = await api(`/api/event-review/${e.id}/${st === 1 ? 'confirm' : 'reject'}`, { method: 'POST' });
        if (r && r.ok) {
          e.negative_confirmed = st;
          const lab = $('evRvState'); if (lab) lab.textContent = RVTXT[st];
          toast(st === 1 ? (`已确认负面，事件从未办清单移除${r.notes_linked ? `，联动确认 ${r.notes_linked} 条关联负面笔记` : ''}`) : '已驳回，事件从未办清单移除');
        } else { toast((r && r.error) || '操作失败'); btn.disabled = false; }
      } catch (err) { toast('操作失败：' + err.message); btn.disabled = false; }
    };
    const cfBtn = $('evConfirmBtn'), rjBtn = $('evRejectBtn');
    if (cfBtn) cfBtn.onclick = () => doEventRv(1, cfBtn);
    if (rjBtn) rjBtn.onclick = () => doEventRv(2, rjBtn);
    const btn = $('eventCaseBtn');
    if (btn) btn.onclick = () => showNoteCases((e.title || '事件') + ' · 相关笔记', null, null, '/api/events/' + e.id + '/notes');
  };

  /* ============ 3. 案例详情弹窗：事件经过+启示优先，其余折叠 ============ */
  window.openCaseDetail = async function (case_id) {
    try {
      const d = await api('/api/cases/' + case_id);
      if (!d.case) return;
      const c = d.case;

      // 核心区：标题/标签/事件经过/太古汇启示
      const core = `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap">
          <span class="case-level" style="font-size:16px">${esc(c.level || '')}</span>
          <span class="case-category">${esc(c.category || '')}</span>
        </div>
        <h2 class="modal-title" style="font-size:18px">${esc(c.title || '')}</h2>
        <div class="ms-quick-meta" style="margin:6px 0 12px"><span>${xicon('pin')} ${esc(c.location || '')}</span><span>${xicon('clock')} ${esc(c.time || '')}</span></div>
        <div class="case-detail-section"><h4>${xicon('pin')} 事件经过</h4><p>${esc(c.event || '')}</p></div>
        <div class="case-detail-section" style="background:var(--bg);padding:12px;border-radius:8px;border-left:3px solid var(--primary)"><h4 style="color:var(--primary)">${xicon('bulb')} 对太古汇启示</h4><p>${esc(c.taikoo_insight || '')}</p></div>`;

      // 次要信息折叠
      const secondary =
        (c.spread_path ? `<div class="case-detail-section"><h4>${xicon('trend')} 传播路径</h4><p>${esc(c.spread_path)}</p></div>` : '') +
        (c.response ? `<div class="case-detail-section"><h4>${xicon('reply')} 官方回应</h4><p>${esc(c.response)}</p></div>` : '') +
        (c.effect ? `<div class="case-detail-section"><h4>${xicon('chart')} 处理效果</h4><p>${esc(c.effect)}</p></div>` : '') +
        (c.reply_formula ? `<div class="case-detail-section"><h4>${xicon('doc')} 回复公式</h4><p>${esc(c.reply_formula)}</p></div>` : '') +
        (c.taboo ? `<div class="case-detail-section" style="color:var(--danger)"><h4>${xicon('warn')} 禁忌</h4><p>${esc(c.taboo)}</p></div>` : '');

      $('modalContent').innerHTML = core + (secondary ? detailToggle(secondary, '传播路径 / 回应 / 处理细节') : '') +
        '<div style="margin-top:14px"><button class="action primary" onclick="closeModal()">关闭</button></div>';
      openModal();
    } catch (e) { toast(e.message || '加载失败'); }
  };

  /* ============ 4. 注入精简补丁样式（一次） ============ */
  function injectStyle() {
    if (document.getElementById('ms-style')) return;
    const css = `
.ms-core-row{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.ms-badge{display:inline-flex;align-items:center;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;line-height:1.5}
.ms-badge-high{background:#ffe5e5;color:#d70015}
.ms-badge-med{background:#fff4e0;color:#b25e00}
.ms-badge-low{background:#e8f9ee;color:#1a9e54}
.ms-badge-neg{background:#ffe5e5;color:#d70015}
.ms-badge-pos{background:#e8f9ee;color:#1a9e54}
.ms-badge-neu{background:#f0f1f5;color:#666}
.ms-quick-meta{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:10px 0;padding:8px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.ms-action-box{background:linear-gradient(135deg,#eef4ff,#f6fbff);border-left:3px solid #4a7dff;border-radius:8px;padding:10px 12px;margin:10px 0;line-height:1.6;font-size:13px}
.ms-action-label{font-size:11px;color:var(--muted);margin-bottom:3px;font-weight:600}
.ms-detail{margin-top:10px;border:1px solid var(--border);border-radius:8px;overflow:hidden}
.ms-detail summary{padding:10px 12px;cursor:pointer;font-size:13px;font-weight:600;color:var(--primary);user-select:none;list-style:none;display:flex;align-items:center;gap:6px;background:var(--bg)}
.ms-detail summary::before{content:'▸';transition:transform .2s;display:inline-block}
.ms-detail[open] summary::before{transform:rotate(90deg)}
.ms-detail-body{padding:10px 12px}
@media(max-width:768px){.ms-quick-meta{gap:8px;font-size:11px}.ms-badge{font-size:11px;padding:2px 8px}}
`;
    const style = document.createElement('style');
    style.id = 'ms-style';
    style.textContent = css;
    document.head.appendChild(style);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', injectStyle);
  else injectStyle();

  console.log('[modal_simplify] 弹窗精简补丁已加载（渐进式展开）');
})();
