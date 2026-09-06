/**
 * settings.js — ZBC-LUMENIS 设置页前端逻辑
 * 对接 /api/system/account/* 所有端点
 * 守No-Scroll：内容在bounded区域内滚动，外层不滚
 */

const API = '/api/system/account';
let currentUser = null;
let auditPage = 1;
let navConfigData = [];

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  loadProfile();
  loadAboutInfo();
});

// ── Panel switching ──
function switchPanel(panel) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const el = document.getElementById('panel-' + panel);
  if (el) el.classList.add('active');
  const nav = document.querySelector(`.nav-item[data-panel="${panel}"]`);
  if (nav) nav.classList.add('active');
  const titles = {
    profile: '账户资料', security: '登录与安全', protection: '访问保护',
    members: '成员管理', approvals: '登录审批', recovery: '账号恢复',
    audit: '审计日志', keys: '程序化密钥', navcustom: '导航自定义',
    skills: '技能管理', about: '关于系统', domain: '域名与接入',
    developer: '开发者功能', appearance: '外观', ai: 'AI',
    collection: '采集与数据源', backup: '通知/备份/帮助'
  };
  document.getElementById('panelTitle').textContent = titles[panel] || panel;

  // Lazy load panel data
  if (panel === 'members') loadMembers();
  if (panel === 'security') loadDevices();
  if (panel === 'protection') loadProtection();
  if (panel === 'audit') loadAuditLogs();
  if (panel === 'keys') loadKeys();
  if (panel === 'approvals') loadApprovals();
  if (panel === 'recovery') loadRecovery();
  if (panel === 'navcustom') loadNavConfig();
  if (panel === 'skills') loadSkills();
}

// ── API helper ──
async function api(path, opts = {}) {
  try {
    const resp = await fetch(API + path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    return await resp.json();
  } catch (e) {
    showToast('网络错误: ' + e.message, 'error');
    return { ok: false, error: e.message };
  }
}

// ── Toast ──
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  setTimeout(() => t.classList.remove('show'), 2500);
}

// ── Modal ──
function openModal(id) { document.getElementById(id).classList.add('show'); }
function closeModal(id) { document.getElementById(id).classList.remove('show'); }
document.querySelectorAll('.modal-overlay').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) m.classList.remove('show'); });
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.querySelectorAll('.modal-overlay.show').forEach(m => m.classList.remove('show'));
});

// ── Profile ──
async function loadProfile() {
  const data = await api('/profile');
  if (data.ok) {
    currentUser = data.profile;
    document.getElementById('userName').textContent = data.profile.display_name || data.profile.username;
    document.getElementById('userRole').textContent = roleLabel(data.profile.role);
    document.getElementById('userAvatar').textContent = (data.profile.display_name || data.profile.username || '?')[0].toUpperCase();
    document.getElementById('profileDisplayName').value = data.profile.display_name || '';
    document.getElementById('profileEmail').value = data.profile.email || '';
    document.getElementById('profilePhone').value = data.profile.phone || '';
    document.getElementById('cthAccount').textContent = data.profile.username;
    if (data.profile.must_change_password) {
      document.getElementById('weakPwdWarning').style.display = 'block';
    }
    // Load quota mini
    const q = await api('/quota');
    if (q.ok) {
      document.getElementById('quotaMini').textContent =
        `${q.quota.admin.used}/${q.quota.admin.limit}管 · ${q.quota.member.used}/${q.quota.member.limit}子`;
    }
  }
}

function roleLabel(role) {
  return { owner: '主账号 Owner', admin: '管理员 Admin', user: '子账号 Member' }[role] || role;
}

async function saveProfile() {
  const data = await api('/profile', {
    method: 'PUT',
    body: {
      display_name: document.getElementById('profileDisplayName').value,
      email: document.getElementById('profileEmail').value,
      phone: document.getElementById('profilePhone').value,
    }
  });
  if (data.success) { showToast('资料已保存'); loadProfile(); }
  else showToast(data.error || '保存失败', 'error');
}

// ── Password ──
async function changePassword() {
  const oldP = document.getElementById('oldPassword').value;
  const newP = document.getElementById('newPassword').value;
  const confP = document.getElementById('confirmPassword').value;
  if (newP !== confP) { showToast('两次密码不一致', 'error'); return; }
  if (newP.length < 6) { showToast('新密码至少6位', 'error'); return; }
  const data = await api('/change-password', { method: 'POST', body: { old_password: oldP, new_password: newP } });
  if (data.success) {
    showToast('密码修改成功');
    document.getElementById('oldPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
    document.getElementById('weakPwdWarning').style.display = 'none';
  } else showToast(data.error || '修改失败', 'error');
}

// ── Devices ──
async function loadDevices() {
  const data = await api('/devices');
  const container = document.getElementById('deviceList');
  if (!data.ok) { container.innerHTML = '<div class="empty-state">加载失败</div>'; return; }
  if (!data.devices.length) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">📱</div>暂无受信任设备</div>'; return; }
  container.innerHTML = data.devices.map(d => `
    <div class="device-row">
      <div class="device-icon">💻</div>
      <div class="device-info">
        <div class="device-name">${d.user_agent ? d.user_agent.substring(0, 40) : '未知设备'}</div>
        <div class="device-meta">IP: ${d.ip || '—'} · ${d.created_at} · ${d.is_active ? '活跃' : '已过期'}</div>
      </div>
      <div class="device-battery">
        <div class="device-battery-fill" style="width:${d.is_active ? 80 : 0}%"></div>
        <span class="device-battery-text">${d.is_active ? '在线' : '离线'}</span>
      </div>
      ${d.id !== data.current_session_id ? `<button class="btn btn-danger btn-sm" onclick="revokeDevice(${d.id})">登出</button>` : '<span class="status-badge ok">当前</span>'}
    </div>
  `).join('');
}

async function revokeDevice(id) {
  if (!confirm('确认远程登出此设备？')) return;
  const data = await api(`/devices/${id}/revoke`, { method: 'POST' });
  if (data.success) { showToast('已登出'); loadDevices(); }
  else showToast(data.error || '失败', 'error');
}

// ── Protection (TOTP) ──
async function loadProtection() {
  const data = await api('/totp/status');
  if (data.ok) {
    if (data.bound && data.enabled) {
      document.getElementById('totpNotBound').style.display = 'none';
      document.getElementById('totpSetupArea').style.display = 'none';
      document.getElementById('totpBound').style.display = 'block';
      document.getElementById('totpLastUsed').textContent = data.last_used_at || '从未使用';
    } else {
      document.getElementById('totpNotBound').style.display = 'block';
      document.getElementById('totpBound').style.display = 'none';
    }
  }
}

async function setupTOTP() {
  const data = await api('/totp/setup', { method: 'POST', body: { account_name: currentUser?.username || 'ZBC' } });
  if (data.success) {
    document.getElementById('totpNotBound').style.display = 'none';
    document.getElementById('totpSetupArea').style.display = 'block';
    document.getElementById('totpQrImg').src = data.qr_code;
    document.getElementById('totpSecretText').textContent = data.secret;
    // Setup input handlers
    const inputs = document.querySelectorAll('#totpConfirmInputs input');
    inputs.forEach((inp, i) => {
      inp.addEventListener('input', () => {
        if (inp.value && i < 5) inputs[i + 1].focus();
      });
    });
  } else showToast(data.error || '失败', 'error');
}

function cancelTOTPSetup() {
  document.getElementById('totpSetupArea').style.display = 'none';
  document.getElementById('totpNotBound').style.display = 'block';
}

async function confirmTOTP() {
  const inputs = document.querySelectorAll('#totpConfirmInputs input');
  const code = Array.from(inputs).map(i => i.value).join('');
  if (code.length !== 6) { showToast('请输入6位验证码', 'error'); return; }
  const data = await api('/totp/confirm', { method: 'POST', body: { code } });
  if (data.success) { showToast('TOTP绑定成功'); loadProtection(); }
  else showToast(data.error || '绑定失败', 'error');
}

async function resetTOTP() {
  if (!confirm('确认重置TOTP？重置后需重新绑定。')) return;
  const data = await api('/totp/reset', { method: 'POST', body: { user_id: currentUser?.id } });
  if (data.success) { showToast('已重置'); loadProtection(); }
  else showToast(data.error || '失败', 'error');
}

// ── Members ──
async function loadMembers() {
  const data = await api('/members');
  if (!data.ok) { document.getElementById('memberList').innerHTML = '<div class="empty-state">加载失败</div>'; return; }
  // Quota
  if (data.quota) {
    document.getElementById('adminUsed').innerHTML = `${data.quota.admin.used}<span class="limit">/${data.quota.admin.limit}</span>`;
    document.getElementById('memberUsed').innerHTML = `${data.quota.member.used}<span class="limit">/${data.quota.member.limit}</span>`;
  }
  const container = document.getElementById('memberList');
  if (!data.members.length) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">👥</div>暂无成员</div>'; return; }
  container.innerHTML = data.members.map(m => {
    const auths = (m.authorizations || []).map(a =>
      `<span class="auth-chip ${a.product_id.toLowerCase()}">${a.product_id}:${a.action}</span>`
    ).join('');
    const canManage = currentUser?.role === 'owner';
    return `
    <div class="member-card">
      <div class="member-avatar ${m.role}">${(m.display_name || m.username)[0].toUpperCase()}</div>
      <div class="member-info">
        <div class="member-name">${m.display_name || m.username} <span style="font-size:10px;color:#94a3b8;font-weight:400">@${m.username}</span></div>
        <div class="member-meta">${roleLabel(m.role)} · ${m.email || '无邮箱'} · 最后登录: ${m.last_login_at || '从未'}</div>
        <div class="auth-chips">${auths || '<span style="font-size:10px;color:#94a3b8">未设置授权</span>'}</div>
      </div>
      <span class="member-status ${m.status}">${m.status === 'active' ? '活跃' : '停用'}</span>
      <div class="member-actions">
        ${m.role !== 'owner' ? `
          <button class="btn btn-secondary btn-sm" onclick="toggleMemberStatus(${m.id}, '${m.status}')">${m.status === 'active' ? '停用' : '启用'}</button>
          ${canManage ? `<button class="btn btn-danger btn-sm" onclick="removeMember(${m.id})">移除</button>` : ''}
        ` : ''}
      </div>
    </div>`;
  }).join('');
}

function openMemberModal() {
  document.getElementById('memberModalTitle').textContent = '新建成员';
  document.getElementById('mUsername').value = '';
  document.getElementById('mPassword').value = '';
  document.getElementById('mDisplayName').value = '';
  document.getElementById('mEmail').value = '';
  openModal('memberModal');
}

async function submitMember() {
  const auths = [];
  if (document.getElementById('authZbmpRead').checked) auths.push({ product_id: 'ZBMP', module: '*', action: 'read' });
  if (document.getElementById('authZbmpWrite').checked) auths.push({ product_id: 'ZBMP', module: '*', action: 'write' });
  if (document.getElementById('authCthRead').checked) auths.push({ product_id: 'CTH', module: '*', action: 'read' });
  if (document.getElementById('authCthWrite').checked) auths.push({ product_id: 'CTH', module: '*', action: 'write' });

  const data = await api('/members', {
    method: 'POST',
    body: {
      username: document.getElementById('mUsername').value,
      password: document.getElementById('mPassword').value,
      display_name: document.getElementById('mDisplayName').value,
      email: document.getElementById('mEmail').value,
      role: document.getElementById('mRole').value,
    }
  });
  if (data.success) {
    // Set authorizations
    if (auths.length) {
      await api(`/members/${data.user_id}/authorizations`, { method: 'PUT', body: { authorizations: auths } });
    }
    closeModal('memberModal');
    showToast('成员创建成功');
    loadMembers();
  } else {
    showToast(data.error || '创建失败', 'error');
  }
}

async function toggleMemberStatus(id, currentStatus) {
  const newStatus = currentStatus === 'active' ? 'disabled' : 'active';
  const data = await api(`/members/${id}`, { method: 'PUT', body: { status: newStatus } });
  if (data.success) { showToast('状态已更新'); loadMembers(); }
  else showToast(data.error || '失败', 'error');
}

async function removeMember(id) {
  if (!confirm('确认移除该成员？此操作释放名额且不可恢复。')) return;
  const data = await api(`/members/${id}`, { method: 'DELETE' });
  if (data.success) { showToast('成员已移除'); loadMembers(); }
  else showToast(data.error || '失败', 'error');
}

// ── Approvals ──
async function loadApprovals() {
  const data = await api('/approvals');
  const container = document.getElementById('approvalList');
  if (!data.ok || !data.approvals.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div>暂无待审批登录</div>';
    return;
  }
  container.innerHTML = data.approvals.map(a => `
    <div class="member-card">
      <div class="member-avatar user">${(a.username || '?')[0]}</div>
      <div class="member-info">
        <div class="member-name">${a.username || '未知'}</div>
        <div class="member-meta">IP: ${a.ip || '—'} · ${a.user_agent?.substring(0, 50) || ''} · ${a.requested_at}</div>
      </div>
      <div class="member-actions">
        <button class="btn btn-primary btn-sm" onclick="approveLogin(${a.id})">批准</button>
        <button class="btn btn-danger btn-sm" onclick="rejectLogin(${a.id})">拒绝</button>
      </div>
    </div>
  `).join('');
}

async function approveLogin(id) {
  const data = await api(`/approvals/${id}/approve`, { method: 'POST' });
  if (data.ok) { showToast('已批准'); loadApprovals(); }
  else showToast(data.error || '失败', 'error');
}

async function rejectLogin(id) {
  const data = await api(`/approvals/${id}/reject`, { method: 'POST' });
  if (data.ok) { showToast('已拒绝'); loadApprovals(); }
  else showToast(data.error || '失败', 'error');
}

// ── Recovery ──
async function loadRecovery() {
  const data = await api('/recovery');
  const container = document.getElementById('recoveryQuestions');
  if (data.ok && data.security_questions) {
    container.innerHTML = data.security_questions.map(q => `
      <div class="form-row">
        <label>${q.question}</label>
        <span class="status-badge ${q.is_active ? 'ok' : 'off'}">${q.is_active ? '已设置' : '未激活'}</span>
      </div>
    `).join('') + '<p style="font-size:11px;color:#94a3b8;margin-top:12px">安全问答答案已加密存储，无法查看。恢复码在首次设置时生成，请妥善保管。</p>';
  }
}

// ── Audit ──
async function loadAuditLogs(page = 1) {
  auditPage = page;
  const user = document.getElementById('auditFilterUser')?.value || '';
  const action = document.getElementById('auditFilterAction')?.value || '';
  const data = await api(`/audit?page=${page}&page_size=20&username=${encodeURIComponent(user)}&action=${encodeURIComponent(action)}`);
  const container = document.getElementById('auditTableContainer');
  if (!data.ok) { container.innerHTML = '<div class="empty-state">加载失败</div>'; return; }
  if (!data.logs.length) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div>暂无审计日志</div>'; return; }
  container.innerHTML = `
    <table class="audit-table">
      <thead><tr><th>时间</th><th>用户</th><th>动作</th><th>资源</th><th>IP</th><th>详情</th></tr></thead>
      <tbody>${data.logs.map(l => `<tr>
        <td>${l.created_at}</td><td>${l.username}</td><td>${l.action}</td>
        <td>${l.resource || '—'}</td><td>${l.ip || '—'}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.detail || '—'}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  // Pagination
  const pag = document.getElementById('auditPagination');
  let html = `<button ${page <= 1 ? 'disabled' : ''} onclick="loadAuditLogs(${page - 1})">上一页</button>`;
  html += `<span style="font-size:12px;color:#64748b">${page}/${data.total_pages || 1}</span>`;
  html += `<button ${page >= data.total_pages ? 'disabled' : ''} onclick="loadAuditLogs(${page + 1})">下一页</button>`;
  pag.innerHTML = html;
}

// ── Keys ──
async function loadKeys() {
  const data = await api('/workspace-keys');
  if (!data.ok) return;
  if (data.rotation_summary && data.rotation_summary.requires_rotation > 0) {
    document.getElementById('rotationWarning').style.display = 'block';
    document.getElementById('rotationCount').textContent = data.rotation_summary.requires_rotation;
  }
  const container = document.getElementById('keyList');
  if (!data.keys.length) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">🔑</div>暂无密钥</div>'; return; }
  container.innerHTML = data.keys.map(k => `
    <div class="member-card">
      <div class="member-avatar admin">🔑</div>
      <div class="member-info">
        <div class="member-name">${k.label || '未命名'} <span style="font-size:10px;color:#94a3b8">${k.workspace}</span></div>
        <div class="member-meta">前缀: ${k.key_prefix} · 创建: ${k.created_at} · 过期: ${k.expires_at || '永不过期'}</div>
        ${k.requires_rotation ? '<span style="font-size:10px;color:#d97706;font-weight:600">⚠️ 需要轮换</span>' : ''}
      </div>
      <span class="member-status ${k.status === 'active' ? 'active' : 'disabled'}">${k.status === 'active' ? '活跃' : '已吊销'}</span>
      ${k.status === 'active' ? `<button class="btn btn-danger btn-sm" onclick="revokeKey(${k.id})">吊销</button>` : ''}
    </div>
  `).join('');
}

function openKeyModal() { openModal('keyModal'); }

async function submitKey() {
  const data = await api('/workspace-keys', {
    method: 'POST',
    body: {
      label: document.getElementById('kLabel').value,
      workspace: document.getElementById('kWorkspace').value,
      expires_days: parseInt(document.getElementById('kExpires').value),
      bound_ip: document.getElementById('kBoundIp').value || null,
    }
  });
  if (data.success) {
    closeModal('keyModal');
    document.getElementById('keyResultText').textContent = data.key_plain;
    openModal('keyResultModal');
    loadKeys();
  } else showToast(data.error || '创建失败', 'error');
}

async function revokeKey(id) {
  if (!confirm('确认吊销此密钥？')) return;
  const data = await api(`/workspace-keys/${id}`, { method: 'DELETE' });
  if (data.success) { showToast('已吊销'); loadKeys(); }
  else showToast(data.error || '失败', 'error');
}

// ── Nav Config ──
async function loadNavConfig() {
  const domain = document.getElementById('navDomainSelect').value;
  const data = await api(`/nav?domain=${domain}`);
  const container = document.getElementById('navConfigList');
  if (!data.ok) return;
  navConfigData = data.nav_items || [];
  container.innerHTML = navConfigData.map((item, idx) => `
    <div class="form-row">
      <label style="display:flex;align-items:center;gap:8px">
        <span style="cursor:grab;color:#94a3b8">⠿</span>
        <input type="checkbox" ${item.visible ? 'checked' : ''} onchange="navConfigData[${idx}].visible=this.checked">
        <input type="text" value="${item.label}" style="width:120px;padding:6px 10px;border:1px solid #e2e8f0;border-radius:8px;font-size:12px" onchange="navConfigData[${idx}].label=this.value">
      </label>
      <span style="font-size:11px;color:#94a3b8">${item.id}</span>
    </div>
  `).join('');
}

async function saveNavConfig() {
  const domain = document.getElementById('navDomainSelect').value;
  const data = await api('/nav', { method: 'PUT', body: { domain, nav_items: navConfigData } });
  if (data.success) showToast('导航配置已保存');
  else showToast(data.error || '保存失败', 'error');
}

async function resetNavConfig() {
  if (!confirm('恢复默认导航配置？')) return;
  const domain = document.getElementById('navDomainSelect').value;
  const data = await api('/nav/reset', { method: 'POST', body: { domain } });
  if (data.success) { showToast('已恢复默认'); loadNavConfig(); }
}

// ── Skills ──
async function loadSkills() {
  const data = await api('/skills');
  const container = document.getElementById('skillList');
  if (!data.ok || !data.skills.length) { container.innerHTML = '<div class="empty-state">暂无技能</div>'; return; }
  container.innerHTML = data.skills.map(s => `
    <div class="member-card">
      <div class="member-avatar ${s.product === 'ZBMP' ? 'admin' : s.product === 'CTH' ? 'user' : 'owner'}">⚡</div>
      <div class="member-info">
        <div class="member-name">${s.name} <span style="font-size:10px;color:#94a3b8">${s.product} · ${s.domain}</span></div>
        <div class="member-meta">${s.description || '—'} · v${s.version || '1.0'}</div>
      </div>
      <span class="status-badge ${s.status === 'enabled' ? 'ok' : 'off'}">${s.status === 'enabled' ? '已启用' : '已禁用'}</span>
      ${currentUser?.role === 'owner' ? (s.status === 'enabled'
        ? `<button class="btn btn-secondary btn-sm" onclick="toggleSkill('${s.skill_id}','disabled')">禁用</button>`
        : `<button class="btn btn-primary btn-sm" onclick="toggleSkill('${s.skill_id}','enabled')">启用</button>`) : ''}
    </div>
  `).join('');
}

async function toggleSkill(skillId, status) {
  const path = status === 'enabled' ? `/skills/${skillId}/enable` : `/skills/${skillId}/disable`;
  const data = await api(path, { method: 'POST' });
  if (data.success) { showToast('技能状态已更新'); loadSkills(); }
  else showToast(data.error || '失败', 'error');
}

// ── About ──
function loadAboutInfo() {
  // Version from file
  fetch('/VERSION').then(r => r.text()).then(v => {
    document.getElementById('aboutVersion').textContent = v.trim() || '—';
  }).catch(() => { document.getElementById('aboutVersion').textContent = '—'; });
  // Git info
  document.getElementById('aboutCommit').textContent = 'ffc50d9 (基线)';
  document.getElementById('aboutBranch').textContent = 'lumenis-dual-domain-v3';
  document.getElementById('aboutBuild').textContent = new Date().toISOString().slice(0, 10);
}

// ── Theme ──
function applyTheme() {
  const theme = document.getElementById('themeSelect').value;
  if (theme === 'dark') {
    document.body.style.background = '#0f172a';
    document.body.style.color = '#e2e8f0';
  } else {
    document.body.style.background = '#f8fafc';
    document.body.style.color = '#1e293b';
  }
  showToast('主题已切换（演示）');
}
