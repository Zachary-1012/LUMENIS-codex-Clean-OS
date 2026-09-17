/**
 * skill-store.js — Skill 商店逻辑（Codex 插件页形态）
 * 全部函数驱动接真实 API：/api/system/account/skills/*
 */
(function () {
  'use strict';
  const SKILL_COLORS = {ai_analyzer:'#0F766E',risk_engine:'#cf222e',report_generator:'#8250df',kos_engine:'#bf8700',collector_xhs:'#ff2442',collector_weibo:'#e6162d',collector_bilibili:'#0969da',brand_analysis:'#8250df',internal_browser:'#0969da',data_visualization:'#1a7f37',intelligence_library:'#8250df',alert_engine:'#bc4c00'};
  const SKILL_ICONS = {ai_analyzer:'🧠',risk_engine:'⚠️',report_generator:'📄',kos_engine:'👥',collector_xhs:'📕',collector_weibo:'🔴',collector_bilibili:'📺',brand_analysis:'📊',internal_browser:'🌐',data_visualization:'📈',intelligence_library:'📚',alert_engine:'🔔'};
  const DEFAULT_COLOR = '#656d76';
  let allSkills = [], currentTab = 'plugins', expandedSkillId = null, searchQuery = '', lastPreviewSource = '', lastPreviewResolveRemote = false, lastPreviewFetchRemoteManifest = false;

  async function api(url, opts) {
    try { const r = await fetch(url, {credentials:'include', ...opts}); return await r.json(); }
    catch(e) { return {ok:false, error:String(e)}; }
  }
  async function fetchSkills() { return (await api('/api/system/account/skills')).skills || []; }
  async function toggleSkill(id, en) { return api(`/api/system/account/skills/${id}/${en?'enable':'disable'}`, {method:'POST'}); }
  async function addSkill(id, name, desc) { return api('/api/system/account/skills', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({skill_id:id,name,description:desc,product:'SYSTEM',domain:'global'})}); }
  async function fetchExecutions(id, limit) { return (await api(`/api/system/account/skills/${id}/executions?limit=${limit||5}`)).executions || []; }
  async function executeSkill(id, task) { return api(`/api/system/account/skills/${id}/execute`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task:task||'manual run', action_type:'ANALYZE'})}); }
  async function previewSource(source, resolveRemote, fetchRemoteManifest) { return api('/api/system/account/skills/source/preview', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({source, resolve_remote:!!resolveRemote, fetch_remote_manifest:!!fetchRemoteManifest})}); }
  async function registerSource(source, resolveRemote, fetchRemoteManifest) { return api('/api/system/account/skills/source/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({source, resolve_remote:!!resolveRemote, fetch_remote_manifest:!!fetchRemoteManifest})}); }
  async function fetchGithubStatus() { return api('/api/system/account/connectors/github/status'); }

  function escapeHTML(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }

  function listValue(value) {
    return Array.isArray(value) && value.length ? value.map(escapeHTML).join(', ') : '—';
  }

  function renderGithubStatus(result) {
    const state = document.getElementById('ssGithubState');
    const meta = document.getElementById('ssGithubMeta');
    if (!state || !meta) return;
    if (!result || result.ok !== true || !result.connector) {
      state.textContent = result?.error || 'GitHub 连接状态不可用';
      meta.textContent = '未取得证据，不将此状态解释为已连接。';
      return;
    }
    const connector = result.connector;
    const labels = {
      NOT_CONFIGURED: '未配置 GitHub App / 外部凭证',
      READY_FOR_AUTHORIZATION: '授权入口已配置，等待用户授权',
      CONNECTED: '凭证已提供，仍需健康检查确认可用',
    };
    state.textContent = labels[connector.state] || connector.state || 'UNKNOWN';
    const repos = Array.isArray(connector.repositories) ? connector.repositories.length : 0;
    meta.textContent = `状态 ${connector.state || 'UNKNOWN'} · 白名单仓库 ${repos} 个 · 只读 · 写权限关闭`;
  }

  window.__ssRefreshGithubStatus = async function() {
    const state = document.getElementById('ssGithubState');
    if (state) state.textContent = '正在读取真实连接状态…';
    renderGithubStatus(await fetchGithubStatus());
  };

  function renderSourceResult(result) {
    const el = document.getElementById('ssSourceResult');
    if (!el) return;
    if (!result || result.ok !== true) {
      const security = result && result.security ? result.security : {};
      el.innerHTML = `<div class="ss-preview-state">${escapeHTML(result?.state || 'BLOCKED')}</div><div>${escapeHTML(result?.error || '来源预检未通过')}</div><div style="margin-top:6px;color:var(--ss-text3)">执行：${escapeHTML(security.execution || 'BLOCKED_UNVERIFIED')}</div>`;
      return;
    }
    const source = result.source || {};
    const validation = result.validation || {};
    const security = result.security || {};
    const ownership = result.ownership || {};
    const remote = result.remote_manifest || {};
    const remoteLine = remote.path ? `<div><b>远程 manifest</b>：<code>${escapeHTML(remote.path)}</code> · revision：<code>${escapeHTML(result.revision || '—')}</code></div>` : '';
    const completion = result.state === 'REMOTE_VALIDATED' ? '已完成远程 manifest 只读验证；安装、隔离、自测、权限授予与启用仍未开放。' : '当前仅完成来源预检。安装、隔离执行、权限授予与生命周期更新仍未开放。';
    el.innerHTML = `<div class="ss-preview-state">${escapeHTML(result.state || 'UNKNOWN')}</div>
      <div style="margin-top:8px"><b>来源</b>：<code>${escapeHTML(source.source || '')}</code></div>
      <div><b>类型 / 运行时</b>：${escapeHTML(source.source_type || 'unknown')} / ${escapeHTML(result.runtime || 'unknown')}</div>
      ${remoteLine}
      <div><b>Manifest</b>：${escapeHTML(result.manifest_state || 'UNKNOWN')}；兼容性：${validation.valid === true ? '通过' : '未通过'}</div>
      <div><b>能力</b>：${listValue(result.capabilities)}；工具：${listValue(result.tools)}</div>
      <div><b>请求权限</b>：${listValue(security.permissions_requested)}；已授予：${listValue(security.permissions_granted)}</div>
      <div><b>安全</b>：${escapeHTML(security.decision || 'DENY_BY_DEFAULT')}；Secrets 注入：${security.secrets_injected === true ? '是' : '否'}</div>
      <div><b>归属</b>：Registry=${escapeHTML(ownership.registry || '—')}；Evidence=${escapeHTML(ownership.evidence || '—')}</div>
      <div style="margin-top:8px;color:var(--ss-text3)">${completion}</div>
      ${result.state === 'VALIDATED' ? '<button class="ss-btn ss-btn-primary" style="margin-top:10px" onclick="window.__ssRegisterSourcePreview()">登记为禁用 Skill</button>' : ''}`;
  }

  const getColor = id => SKILL_COLORS[id] || DEFAULT_COLOR;
  const getIcon = id => SKILL_ICONS[id] || '⚡';
  function categorize(s) {
    const t = ((s.skill_id||'')+(s.domain||'')+(s.name||'')).toLowerCase();
    if (/collect|crawl|采集|xhs|weibo|bilibili/.test(t)) return '采集类';
    if (/analyze|analysis|分析|risk|ai|kos|brand/.test(t)) return '分析类';
    if (/report|报告|viz|visual|可视化/.test(t)) return '报告类';
    if (/alert|告警|operate|运营|library|智能/.test(t)) return '运营类';
    if (/browser|developer|开发|registry|agent|boundary/.test(t)) return '开发者工具';
    return '系统';
  }

  function renderSkeleton() {
    let h = '';
    for (let i=0;i<5;i++) h += `<div class="ss-skeleton-row"><div class="ss-skeleton-icon"></div><div style="flex:1;display:flex;flex-direction:column;gap:6px"><div class="ss-skeleton-text" style="width:40%"></div><div class="ss-skeleton-text" style="width:70%"></div></div></div>`;
    document.getElementById('ssList').innerHTML = h;
  }
  function renderEmpty(msg) {
    document.getElementById('ssList').innerHTML = `<div class="ss-empty"><div class="ss-empty-icon">📦</div><div class="ss-empty-title">${msg||'暂无 Skill'}</div><div class="ss-empty-desc">点击右上角「添加」按钮创建自定义 Skill，或在分类中启用已有 Skill</div></div>`;
  }

  function renderList() {
    const list = document.getElementById('ssList');
    let skills = allSkills;
    if (searchQuery) { const q = searchQuery.toLowerCase(); skills = skills.filter(s => (s.name||'').toLowerCase().includes(q)||(s.description||'').toLowerCase().includes(q)||(s.skill_id||'').toLowerCase().includes(q)); }
    if (!skills.length) { renderEmpty(searchQuery?'没有找到匹配的 Skill':'暂无已注册 Skill'); return; }
    const groups = {};
    skills.forEach(s => { const c = categorize(s); (groups[c]=groups[c]||[]).push(s); });
    const order = ['采集类','分析类','报告类','运营类','开发者工具','系统'];
    const cats = order.filter(c=>groups[c]).concat(Object.keys(groups).filter(c=>!order.includes(c)));
    let h = '';
    cats.forEach(cat => {
      h += `<div class="ss-category-header">${cat} <span class="ss-category-count">${groups[cat].length}</span></div>`;
      groups[cat].forEach(s => {
        h += renderRow(s);
        if (expandedSkillId === s.skill_id) h += `<div class="ss-skill-detail" id="ss-detail-${s.skill_id.replace(/\./g,'-')}"><div class="ss-loading"><div class="ss-spinner"></div><div class="ss-loading-text">加载详情…</div></div></div>`;
      });
    });
    list.innerHTML = h;
    bindEvents();
    if (expandedSkillId) loadDetail(expandedSkillId);
  }

  function renderRow(s) {
    const on = s.status === 'enabled';
    return `<div class="ss-skill-row ${expandedSkillId===s.skill_id?'expanded':''}" data-skill-id="${s.skill_id}">
      <div class="ss-skill-icon" style="background:${getColor(s.skill_id)}">${getIcon(s.skill_id)}</div>
      <div class="ss-skill-info"><div class="ss-skill-name">${s.name||s.skill_id}</div><div class="ss-skill-desc">${s.description||''}</div></div>
      <div class="ss-skill-actions"><div class="ss-toggle ${on?'on':''}" data-skill-id="${s.skill_id}"></div><div class="ss-more-btn" data-skill-id="${s.skill_id}">⋯</div></div></div>`;
  }

  function bindEvents() {
    document.querySelectorAll('.ss-skill-row').forEach(row => {
      row.addEventListener('click', e => { if (e.target.closest('.ss-toggle')||e.target.closest('.ss-more-btn')) return; toggleExpand(row.dataset.skillId); });
    });
    document.querySelectorAll('.ss-toggle').forEach(t => {
      t.addEventListener('click', async e => { e.stopPropagation(); const id=t.dataset.skillId; const on=t.classList.contains('on'); t.style.opacity='.5'; const r=await toggleSkill(id,!on); t.style.opacity='1'; if(r.success||r.ok) await refresh(); });
    });
    document.querySelectorAll('.ss-more-btn').forEach(b => b.addEventListener('click', e => { e.stopPropagation(); toggleExpand(b.dataset.skillId); }));
  }

  function toggleExpand(id) { expandedSkillId = expandedSkillId===id?null:id; renderList(); }

  async function loadDetail(id) {
    const el = document.getElementById(`ss-detail-${id.replace(/\./g,'-')}`);
    if (!el) return;
    const s = allSkills.find(x=>x.skill_id===id);
    const execs = await fetchExecutions(id, 5);
    const on = s?.status==='enabled';
    el.innerHTML = `<div class="ss-detail-desc">${s?.description||'暂无描述'}</div>
      <div class="ss-detail-grid">
        <div class="ss-detail-item"><div class="ss-detail-label">Skill ID</div><div class="ss-detail-value" style="font-family:monospace;font-size:11px">${id}</div></div>
        <div class="ss-detail-item"><div class="ss-detail-label">版本</div><div class="ss-detail-value">${s?.version||'1.0'}</div></div>
        <div class="ss-detail-item"><div class="ss-detail-label">产品/域</div><div class="ss-detail-value">${s?.product||'SYSTEM'} / ${s?.domain||'global'}</div></div>
        <div class="ss-detail-item"><div class="ss-detail-label">状态</div><div class="ss-detail-value" style="color:${on?'#1a7f37':'#656d76'}">${on?'已启用':'已禁用'}</div></div>
        <div class="ss-detail-item"><div class="ss-detail-label">分类</div><div class="ss-detail-value">${categorize(s||{})}</div></div>
        <div class="ss-detail-item"><div class="ss-detail-label">权限</div><div class="ss-detail-value">READ / ANALYZE</div></div>
      </div>
      <div class="ss-detail-actions">
        <button class="ss-btn ss-btn-primary" onclick="window.__ssRunSkill('${id}')">运行测试</button>
        <button class="ss-btn" onclick="window.__ssConfigSkill('${id}')">配置</button>
        <button class="ss-btn" onclick="window.__ssViewExecutions('${id}')">全部记录</button>
        ${on?`<button class="ss-btn ss-btn-danger" onclick="window.__ssDisableSkill('${id}')">禁用</button>`:`<button class="ss-btn ss-btn-primary" onclick="window.__ssEnableSkill('${id}')">启用</button>`}
      </div>
      <div class="ss-exec-section"><div class="ss-exec-title">最近执行记录</div>
        ${execs.length?execs.map(e=>`<div class="ss-exec-item"><span>${e.created_at||''} · ${e.action_type||'ANALYZE'}</span><span class="ss-exec-status ${e.status||''}">${e.status||''}</span></div>`).join(''):'<div class="ss-exec-item" style="justify-content:center;color:var(--ss-text3)">暂无执行记录</div>'}
      </div>`;
  }

  window.__ssSwitchTab = function(tab) {
    currentTab = tab;
    document.querySelectorAll('.ss-tab').forEach(t => t.classList.toggle('active', t.dataset.tab===tab));
    if (tab==='mcp') document.getElementById('ssList').innerHTML = `<div class="ss-empty"><div class="ss-empty-icon">🔌</div><div class="ss-empty-title">来源 / 协议适配</div><div class="ss-empty-desc">MCP 是可选传输协议，不是独立产品线。点击「来源预检」验证 GitHub、目录、ZIP、SKILL.md 或 MCP/HTTP 来源。</div><button class="ss-btn ss-btn-primary" style="margin-top:8px" onclick="window.__ssOpenSourcePreview()">来源预检</button></div>`;
    else renderList();
  };
  window.__ssBrowseCatalog = function() { document.getElementById('ssSearchInput').focus(); document.getElementById('ssSearchInput').value=''; searchQuery=''; renderList(); };
  window.__ssAddSkill = function() { document.getElementById('ssAddModal').style.display='flex'; document.getElementById('ssNewId').focus(); };
  window.__ssCloseAddModal = function() { document.getElementById('ssAddModal').style.display='none'; ['ssNewId','ssNewName','ssNewDesc'].forEach(i=>document.getElementById(i).value=''); };
  window.__ssSubmitAdd = async function() {
    const id=document.getElementById('ssNewId').value.trim(), name=document.getElementById('ssNewName').value.trim(), desc=document.getElementById('ssNewDesc').value.trim();
    if(!id||!name){alert('请填写 Skill ID 和名称');return;}
    const r=await addSkill(id,name,desc);
    if(r.success||r.ok){window.__ssCloseAddModal();await refresh();}else alert('添加失败：'+(r.error||'未知错误'));
  };
  window.__ssRunSkill = async function(id) { const r=await executeSkill(id); alert(`执行完成\n状态：${r.status||(r.success?'completed':'failed')}\n${r.error?'错误：'+r.error:''}`); if(expandedSkillId===id) loadDetail(id); };
  window.__ssConfigSkill = function(id) { alert('配置入口：Skill '+id+'\n（可通过 API PUT /api/system/account/skills/<id>/config 配置）'); };
  window.__ssViewExecutions = function(id) { toggleExpand(id); };
  window.__ssEnableSkill = async function(id) { await toggleSkill(id,true); await refresh(); };
  window.__ssDisableSkill = async function(id) { await toggleSkill(id,false); await refresh(); };
  window.__ssOpenSourcePreview = function() {
    const modal = document.getElementById('ssSourceModal');
    if (!modal) return;
    modal.style.display='flex';
    document.getElementById('ssSourceResult').innerHTML='';
    document.getElementById('ssSourceInput').focus();
  };
  window.__ssCloseSourcePreview = function() {
    const modal = document.getElementById('ssSourceModal');
    if (modal) modal.style.display='none';
  };
  window.__ssSubmitSourcePreview = async function() {
    const input = document.getElementById('ssSourceInput');
    const result = document.getElementById('ssSourceResult');
    const source = (input?.value || '').trim();
    if (!source) { if (result) result.innerHTML='<div class="ss-preview-state">BLOCKED</div><div>请提供 Skill 来源。</div>'; return; }
    if (result) result.innerHTML='<div class="ss-preview-state">CHECKING</div><div>正在执行只读来源预检…</div>';
    lastPreviewSource = source;
    lastPreviewResolveRemote = !!document.getElementById('ssResolveRemote')?.checked;
    lastPreviewFetchRemoteManifest = lastPreviewResolveRemote && !!document.getElementById('ssFetchRemoteManifest')?.checked;
    const response = await previewSource(source, lastPreviewResolveRemote, lastPreviewFetchRemoteManifest);
    renderSourceResult(response);
  };
  window.__ssRegisterSourcePreview = async function() {
    if (!lastPreviewSource) return;
    const result = document.getElementById('ssSourceResult');
    if (result) result.innerHTML='<div class="ss-preview-state">REGISTERING</div><div>正在登记元数据；不会安装或执行…</div>';
    const response = await registerSource(lastPreviewSource, lastPreviewResolveRemote, lastPreviewFetchRemoteManifest);
    if (response.success || response.ok) {
      if (result) result.innerHTML=`<div class="ss-preview-state">REGISTERED</div><div>已登记 ${escapeHTML(response.skill_id || '')}，状态：disabled，安装状态：not_installed。</div><div style="margin-top:6px;color:var(--ss-text3)">权限仍为默认拒绝，后续需经过安装、隔离、自测与人工授权门。</div>`;
      await refresh();
    } else renderSourceResult(response);
  };

  function setupSearch() {
    const input = document.getElementById('ssSearchInput');
    if(!input) return;
    input.addEventListener('input', () => { searchQuery=input.value.trim(); if(currentTab==='plugins') renderList(); });
    document.addEventListener('keydown', e => { if((e.metaKey||e.ctrlKey)&&e.key==='k'){e.preventDefault();input.focus();} if(e.key==='Escape'){window.__ssCloseAddModal();window.__ssCloseSourcePreview();} });
  }

  async function refresh() {
    renderSkeleton();
    allSkills = await fetchSkills();
    document.getElementById('ssCountPlugins').textContent = allSkills.length;
    if (currentTab==='plugins') renderList();
  }

  document.addEventListener('DOMContentLoaded', () => { setupSearch(); refresh(); window.__ssRefreshGithubStatus(); });
})();
