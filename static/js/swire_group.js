/* ============================================================
 * 品牌营销案例库（Brand Marketing Case Library）  v5.8.5
 * 一级：品牌主体矩阵（可增删，软删除可恢复）
 * 二级：点击品牌下钻其事件库 + 小红书笔记库
 * 数据接口：/api/swire/overview | brand-detail | brand-save |
 *           brand-remove | brand-collect | events | notes
 * ============================================================ */
(function () {
  const S = { key: '', type: '', kw: '', projects: [], timer: null, view: 'list' };

  async function get(url) {
    const r = await fetch(url, { credentials: 'same-origin' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }
  async function post(url, body) {
    const r = await fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {})
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok || d.ok === false) throw new Error(d.error || ('HTTP ' + r.status));
    return d;
  }
  const esc = s => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const num = x => Number(x || 0).toLocaleString('zh-CN');

  const SENT = {
    positive: ['正面', '#248a42', 'rgba(52,199,89,.12)'],
    neutral: ['中性', '#6e7781', 'rgba(120,120,128,.12)'],
    negative: ['负面', '#d52e25', 'rgba(255,59,48,.12)'],
  };
  const TYPE_COLOR = {
    '营销活动': '#0a84ff', '展览艺术': '#af52de', '联名快闪': '#ff9f0a',
    '开业周年': '#34c759', '品牌调整': '#5ac8fa', '服务体验': '#8e8e93',
    '公益可持续': '#30b0c7', '舆情风险': '#ff3b30',
  };
  // 采集补齐状态机：中文映射 + 配色
  const COLLECT_STATUS = {
    idle: ['未采集', '#8e8e93'], queued: ['排队中', '#ff9f0a'], collecting: ['采集中…', '#0a84ff'],
    ready: ['已补齐', '#34c759'], empty: ['暂无新笔记', '#8e8e93'], pending: ['待补齐', '#ff9f0a'],
  };

  function statCard(label, val, cls) {
    return `<div class="metric-card glass-card" style="min-height:auto;padding:14px 16px">
      <div class="metric-label">${label}</div><strong class="${cls || ''}" style="font-size:22px;margin-top:3px">${val}</strong></div>`;
  }

  /* ---------- 一级：品牌主体矩阵 ---------- */
  async function loadOverview() {
    const d = await get('/api/swire/overview?' + Date.now());
    S.projects = d.projects || [];
    document.getElementById('swireStat').innerHTML =
      statCard('在库品牌', S.projects.length) +
      statCard('营销/品牌事件', d.event_total) +
      statCard('相关笔记', num(d.note_total)) +
      statCard('已归档(软删)', d.removed_total || 0);
    const box = document.getElementById('swireProjects');
    if (!S.projects.length) {
      box.innerHTML = '<div class="muted" style="grid-column:1/-1;padding:22px;text-align:center">暂无品牌，点击右上角「+ 添加品牌」建立</div>';
      return;
    }
    box.innerHTML = S.projects.map(p => {
      const st = COLLECT_STATUS[p.collect_status] || COLLECT_STATUS.idle;
      return `<div class="brand-card glass-card" data-key="${esc(p.project_key)}" tabindex="0"
        style="position:relative;cursor:pointer;padding:14px 14px 12px;border:1px solid var(--border);border-radius:14px;transition:.15s">
        <button class="brand-del" data-key="${esc(p.project_key)}" data-name="${esc(p.name)}" title="软删除（数据保留，可恢复）"
          style="position:absolute;top:8px;right:8px;border:none;background:transparent;color:#bbb;font-size:15px;line-height:1;cursor:pointer;padding:2px 5px;border-radius:7px">×</button>
        <div style="font-size:14px;font-weight:700;padding-right:18px">${esc(p.name)}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:3px">${esc([p.city, p.line].filter(Boolean).join(' · ') || '品牌主体')}</div>
        <div style="display:flex;gap:8px;margin-top:9px;font-size:11px;flex-wrap:wrap">
          <span style="color:var(--muted)">${xicon('folder')} ${p.event_count} 事件</span>
          <span style="color:var(--muted)">${xicon('doc')} ${num(p.note_count)} 笔记</span>
        </div>
        <div style="margin-top:8px;font-size:10px;color:${st[1]};display:flex;align-items:center;gap:5px">
          <span style="width:7px;height:7px;border-radius:50%;background:${st[1]};display:inline-block"></span>${st[0]} · 点击进入事件库 ›
        </div></div>`;
    }).join('');
    box.querySelectorAll('.brand-card').forEach(card => {
      card.onclick = () => openBrand(card.dataset.key);
    });
    box.querySelectorAll('.brand-del').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        if (!confirm(`软删除「${btn.dataset.name}」？\n仅从列表隐藏，其事件与笔记数据保留在后端，再次添加同名品牌即可恢复。`)) return;
        try {
          await post('/api/swire/brand-remove', { project_key: btn.dataset.key });
          await loadOverview();
        } catch (err) { alert('删除失败：' + err.message); }
      };
    });
  }

  /* ---------- 二级：品牌下钻（事件库 + 笔记库） ---------- */
  async function openBrand(key) {
    S.key = key; S.type = ''; S.kw = ''; S.view = 'detail';
    document.getElementById('swireDetailView').style.display = '';
    const listPanel = document.querySelector('#page-swire .panel.glass-card');
    if (listPanel) listPanel.style.display = 'none';
    window.scrollTo({ top: 0, behavior: 'smooth' });
    await refreshBrandDetail();
  }
  function backToMatrix() {
    S.view = 'list'; S.key = '';
    document.getElementById('swireDetailView').style.display = 'none';
    const listPanel = document.querySelector('#page-swire .panel.glass-card');
    if (listPanel) listPanel.style.display = '';
    loadOverview();
  }

  async function refreshBrandDetail() {
    const q = new URLSearchParams({ key: S.key, _: Date.now() });
    const d = await get('/api/swire/brand-detail?' + q.toString());
    const b = d.brand, st = d.stat;
    // 详情头：返回 + 品牌信息 + 统计 + 采集补齐
    const cs = COLLECT_STATUS[b.collect_status] || COLLECT_STATUS.idle;
    document.getElementById('swireDetailHead').innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <button class="action" id="swireBackBtn" style="padding:6px 12px">‹ 返回品牌矩阵</button>
        <div style="flex:1;min-width:180px">
          <div style="font-size:17px;font-weight:800">${esc(b.name)}</div>
          <div style="font-size:11px;color:var(--muted);margin-top:2px">${esc([b.city, b.line, b.opened ? (b.opened + ' 年') : ''].filter(Boolean).join(' · '))}</div>
        </div>
        <button class="action primary" id="swireCollectBtn" style="padding:6px 12px">↻ 采集补齐</button>
        <span id="swireCollectState" style="font-size:11px;color:${cs[1]}">${cs[0]}</span>
      </div>
      ${b.intro ? `<div style="font-size:12px;color:var(--muted);margin-top:9px;line-height:1.6">${esc(b.intro)}</div>` : ''}
      <div class="metric-grid" style="grid-template-columns:repeat(6,1fr);margin-top:12px">
        ${statCard('事件', st.events)}${statCard('笔记', num(st.notes))}
        ${statCard('正面', st.pos)}${statCard('中性', st.neu)}${statCard('负面', st.neg)}
        ${statCard('总互动', num(st.engagements))}
      </div>`;
    document.getElementById('swireBackBtn').onclick = backToMatrix;
    document.getElementById('swireCollectBtn').onclick = async () => {
      try {
        await post('/api/swire/brand-collect', { project_key: S.key });
        document.getElementById('swireCollectState').textContent = '采集中…';
        setTimeout(refreshBrandDetail, 4000);
      } catch (e) { alert('采集触发失败：' + e.message); }
    };
    // 类型筛选
    const types = [''].concat(d.event_types || []);
    document.getElementById('swireTypeTabs').innerHTML = types.map(t => {
      const on = (S.type || '') === (t || '') ? 'filter-tab active' : 'filter-tab';
      const color = t ? `style="border-color:${TYPE_COLOR[t] || '#ddd'}"` : '';
      return `<span class="${on}" data-t="${esc(t)}" ${color}>${t || '全部类型'}</span>`;
    }).join('');
    document.querySelectorAll('#swireTypeTabs .filter-tab').forEach(t => t.onclick = () => {
      S.type = t.dataset.t || '';
      document.querySelectorAll('#swireTypeTabs .filter-tab').forEach(x => x.classList.toggle('active', x === t));
      renderEvents(d.events || []);
    });
    renderEvents(d.events || []);
    renderNotes(d.notes || [], d.note_src);
  }

  function renderEvents(events) {
    const box = document.getElementById('swireEvents');
    const list = events.filter(e => !S.type || e.event_type === S.type);
    if (!list.length) { box.innerHTML = '<div class="muted" style="padding:18px;text-align:center">该品牌暂无事件，后续由采集与全网检索补充</div>'; return; }
    box.innerHTML = list.map(e => {
      const tc = TYPE_COLOR[e.event_type] || '#8e8e93';
      const s = SENT[e.sentiment] || SENT.neutral;
      return `<div class="swire-event" style="border-left:4px solid ${tc};background:#fafafa;border-radius:12px;padding:12px 14px;margin-bottom:10px">
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:5px">
          <span style="font-size:10px;font-weight:700;color:#fff;background:${tc};padding:3px 8px;border-radius:999px">${esc(e.event_type)}</span>
          <b style="font-size:13px">${esc(e.title)}</b>
          <span style="margin-left:auto;font-size:10px;color:${s[1]};background:${s[2]};padding:2px 8px;border-radius:999px">${s[0]}</span>
        </div>
        <div style="font-size:11px;color:#666;line-height:1.6">${esc(e.summary || '（暂无分析摘要，待补全）')}</div>
        <div style="display:flex;gap:10px;margin-top:6px;font-size:10px;color:#999;flex-wrap:wrap">
          <span>${xicon('calendar')} ${esc(e.event_date || '')}</span><span>${xicon('link')} ${esc(e.source || '')}</span>
          ${e.brand ? `<span>${xicon('tag')} ${esc(e.brand)}</span>` : ''}
          ${e.url ? `<a href="${esc(e.url)}" target="_blank">链接</a>` : ''}
        </div></div>`;
    }).join('');
  }

  function renderNotes(notes, src) {
    document.getElementById('swireNotesSrc').textContent = src || '';
    const box = document.getElementById('swireNotes');
    const kw = S.kw.trim().toLowerCase();
    const list = notes.filter(n => !kw || String(n.title || '').toLowerCase().includes(kw) || String(n.author || '').toLowerCase().includes(kw));
    if (!list.length) { box.innerHTML = '<div class="muted" style="padding:16px;text-align:center;font-size:12px">该品牌暂无沉淀笔记，点「采集补齐」补充</div>'; return; }
    box.innerHTML = list.map(n => {
      const s = SENT[n.sentiment] || SENT.neutral;
      const url = n.note_url || '';
      const title = `<span style="font-size:12px;font-weight:600;color:var(--text)">${esc(n.title || '（无标题）')}</span>`;
      return `<div style="border:1px solid #efeff1;border-radius:11px;padding:9px 11px;background:#fff">
        <div style="display:flex;gap:7px;align-items:flex-start">
          <span style="flex-shrink:0;font-size:9px;color:${s[1]};background:${s[2]};padding:2px 7px;border-radius:999px;margin-top:2px">${s[0]}</span>
          <div style="min-width:0;flex:1">${url ? `<a href="${esc(url)}" target="_blank" style="color:inherit;text-decoration:none">${title}</a>` : title}
            <div style="font-size:10px;color:#999;margin-top:3px">${esc(n.author || '匿名')} · ${esc((n.publish_date || '').slice(0, 10))} · 赞${num(n.likes)} 评${num(n.comments)} 藏${num(n.collects)}</div>
          </div></div></div>`;
    }).join('');
  }

  /* ---------- 添加品牌弹窗 ---------- */
  function showAddBrandModal() {
    if (document.getElementById('swireAddModal')) { document.getElementById('swireAddModal').style.display = ''; return; }
    const wrap = document.createElement('div');
    wrap.id = 'swireAddModal';
    wrap.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.42);z-index:9999;display:flex;align-items:center;justify-content:center;padding:18px';
    wrap.innerHTML = `<div class="glass-card" style="width:min(480px,96vw);max-height:90vh;overflow:auto;padding:20px;border-radius:18px">
      <div style="display:flex;align-items:center;margin-bottom:14px">
        <h3 style="margin:0;font-size:16px">添加品牌主体</h3>
        <button id="swireModalClose" style="margin-left:auto;border:none;background:transparent;font-size:20px;color:#999;cursor:pointer">×</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:11px">
        <label style="font-size:12px">品牌名称 *<input id="sbName" style="width:100%;margin-top:4px;padding:8px 11px;border:1px solid var(--border);border-radius:9px;background:var(--bg);color:var(--text)"></label>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <label style="font-size:12px">城市<input id="sbCity" placeholder="如 广州" style="width:100%;margin-top:4px;padding:8px 11px;border:1px solid var(--border);border-radius:9px;background:var(--bg);color:var(--text)"></label>
          <label style="font-size:12px">产品线 / 品类<input id="sbLine" placeholder="如 美妆 / 太古里" style="width:100%;margin-top:4px;padding:8px 11px;border:1px solid var(--border);border-radius:9px;background:var(--bg);color:var(--text)"></label>
        </div>
        <label style="font-size:12px">采集关键词（;分隔，留空用品牌名）<input id="sbKw" placeholder="如 品牌名;品牌名 快闪" style="width:100%;margin-top:4px;padding:8px 11px;border:1px solid var(--border);border-radius:9px;background:var(--bg);color:var(--text)"></label>
        <label style="font-size:12px">简介<textarea id="sbIntro" rows="2" style="width:100%;margin-top:4px;padding:8px 11px;border:1px solid var(--border);border-radius:9px;background:var(--bg);color:var(--text);resize:vertical"></textarea></label>
        <div style="font-size:11px;color:var(--muted);line-height:1.6">添加后将异步触发一次关键词采集补齐；曾删除的同名品牌会自动恢复并保留历史数据。</div>
        <div style="display:flex;gap:9px;justify-content:flex-end;margin-top:4px">
          <button class="action" id="swireModalCancel">取消</button>
          <button class="action primary" id="swireModalSave">保存并采集</button>
        </div>
      </div></div>`;
    document.body.appendChild(wrap);
    const close = () => { wrap.style.display = 'none'; };
    wrap.querySelector('#swireModalClose').onclick = close;
    wrap.querySelector('#swireModalCancel').onclick = close;
    wrap.onclick = e => { if (e.target === wrap) close(); };
    wrap.querySelector('#swireModalSave').onclick = async () => {
      const name = wrap.querySelector('#sbName').value.trim();
      if (!name) { alert('请填写品牌名称'); return; }
      const body = {
        name, city: wrap.querySelector('#sbCity').value.trim(),
        line: wrap.querySelector('#sbLine').value.trim(),
        keywords: wrap.querySelector('#sbKw').value.trim(),
        intro: wrap.querySelector('#sbIntro').value.trim(),
      };
      const btn = wrap.querySelector('#swireModalSave');
      btn.disabled = true; btn.textContent = '保存中…';
      try {
        const r = await post('/api/swire/brand-save', body);
        close(); await loadOverview();
        alert((r.action === 'reactivated' ? '该品牌曾被删除，已恢复并更新资料' : '品牌已添加') + '，正在后台采集补齐。');
      } catch (e) { alert('保存失败：' + e.message); }
      finally { btn.disabled = false; btn.textContent = '保存并采集'; }
    };
  }

  /* ---------- 页面入口 ---------- */
  window.renderSwirePage = async function () {
    S.view = 'list'; S.key = '';
    document.getElementById('swireDetailView').style.display = 'none';
    const listPanel = document.querySelector('#page-swire .panel.glass-card');
    if (listPanel) listPanel.style.display = '';
    try {
      await loadOverview();
      const addBtn = document.getElementById('swireAddBrandBtn');
      if (addBtn && !addBtn._bound) { addBtn._bound = true; addBtn.onclick = showAddBrandModal; }
      const kw = document.getElementById('swireKw');
      if (kw && !kw._bound) {
        kw._bound = true;
        kw.addEventListener('input', () => {
          clearTimeout(S.timer);
          S.timer = setTimeout(async () => {
            S.kw = kw.value.trim();
            if (S.view === 'detail' && S.key) {
              const d = await get('/api/swire/brand-detail?key=' + encodeURIComponent(S.key));
              renderNotes(d.notes || [], d.note_src);
            }
          }, 350);
        });
      }
    } catch (e) {
      const box = document.getElementById('swireProjects');
      if (box) box.innerHTML = '<div class="muted" style="padding:16px">品牌营销案例库加载失败：' + esc(e.message) + '</div>';
      console.error('[BrandLibrary]', e);
    }
  };
})();
