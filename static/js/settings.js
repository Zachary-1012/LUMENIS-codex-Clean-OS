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
  loadDomainIdentity();
});

// ── Domain Identity & Isolation ──
let currentDomain = 'system';
const DOMAIN_NAV_VISIBILITY = {
  cth: ['profile', 'security', 'protection', 'collection', 'appearance', 'about', 'backup', 'domain'],
  zbmp: ['profile', 'security', 'protection', 'ai', 'skills', 'appearance', 'about', 'backup', 'domain'],
  system: null, // null = show all
};

async function loadDomainIdentity() {
  try {
    const resp = await fetch('/api/auth/domain-identity', { credentials: 'include' });
    if (resp.ok) {
      const data = await resp.json();
      if (data.ok) {
        currentDomain = data.domain_identity || 'system';
      }
    }
  } catch (e) { /* fallback to system */ }
  updateDomainTag();
  applyDomainFilter();
}

function updateDomainTag() {
  const tag = document.getElementById('domainTag');
  if (!tag) return;
  const labels = { cth: 'CTH 太古汇域', zbmp: 'ZBMP 序境·品牌市场域', system: 'SYSTEM 系统全局' };
  tag.textContent = labels[currentDomain] || currentDomain.toUpperCase();
  tag.className = 'domain-tag ' + currentDomain;
}

function applyDomainFilter() {
  const visible = DOMAIN_NAV_VISIBILITY[currentDomain];
  document.querySelectorAll('.nav-item[data-panel]').forEach(item => {
    const panel = item.getAttribute('data-panel');
    if (visible === null || visible.includes(panel)) {
      item.style.display = '';
    } else {
      item.style.display = 'none';
    }
  });
  // Also hide corresponding panels
  document.querySelectorAll('.panel[id^="panel-"]').forEach(panel => {
    const panelName = panel.id.replace('panel-', '');
    if (visible !== null && !visible.includes(panelName)) {
      // Don't hide active panel, just hide nav entry
    }
  });
}

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
    skills: '插件与技能', about: '关于系统', domain: '域名与接入',
    developer: '开发者功能', appearance: '外观', config: '配置',
    keyboard: '键盘快捷键', browser: '浏览器', integrations: '集成与连接',
    ai: 'AI', collection: '采集与数据源', platforms: '平台与可见性',
    syslinks: '系统链接', 'zbmp-domain': 'ZBMP 序境·品牌市场', backup: '通知/备份/帮助'
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
  if (panel === 'skills') loadSkillsCodex();
  if (panel === 'ai') loadAIStatus();
  if (panel === 'collection') loadCollectorStatus();
  if (panel === 'appearance') initAppearancePanel();
  if (panel === 'config') initConfigPanel();
  if (panel === 'keyboard') initKeyboardPanel();
  if (panel === 'browser') initBrowserPanel();
  if (panel === 'integrations') loadIntegrations();
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

// ── Skills (legacy alias -> Codex pattern) ──
async function loadSkills() { loadSkillsCodex(); }

async function toggleSkill(skillId, status) {
  const path = status === 'enabled' ? `/skills/${skillId}/enable` : `/skills/${skillId}/disable`;
  const data = await api(path, { method: 'POST' });
  if (data.success) { showToast('技能状态已更新'); loadSkillsCodex(); }
  else showToast(data.error || '失败', 'error');
}
// Alias for Codex pattern skill rows
function toggleSkillStatus(skillId, status) { toggleSkill(skillId, status); }

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

// ── AI Status (real API) ──
async function loadAIStatus() {
  const container = document.getElementById('aiModelCards');
  if (!container) return;
  try {
    const resp = await fetch('/api/ai-resource-packs/status', { credentials: 'include' });
    if (resp.ok) {
      const data = await resp.json();
      if (data.ok) {
        const packs = data.packs || data.resource_packs || [];
        if (packs.length > 0) {
          container.innerHTML = packs.map(p => `
            <div class="hscroll-card">
              <h4>${p.name || p.model || 'AI模型'}</h4>
              <div class="card-value" style="color:${p.status === 'active' ? '#16a34a' : p.status === 'paused' ? '#f59e0b' : '#dc2626'}">
                ${p.status === 'active' ? '运行中' : p.status === 'paused' ? '已暂停' : '不可用'}
              </div>
              <div class="card-label">provider: ${p.provider || '—'}</div>
            </div>
          `).join('');
        }
      }
    }
  } catch (e) { /* keep default cards */ }
  // Load quota/cost
  try {
    const quotaEl = document.getElementById('aiQuota');
    const costEl = document.getElementById('aiCost');
    if (quotaEl) quotaEl.textContent = '查询中...';
    const resp = await fetch('/api/ai-resource-packs/status', { credentials: 'include' });
    if (resp.ok) {
      const data = await resp.json();
      if (quotaEl) quotaEl.textContent = data.total_quota != null ? data.total_quota : '—';
      if (costEl) costEl.textContent = data.monthly_cost != null ? '¥' + data.monthly_cost : '—';
    }
  } catch (e) { /* fallback */ }
}

// ── Collector Status (real API) ──
async function loadCollectorStatus() {
  const container = document.querySelector('#panel-collection .hscroll-container');
  if (!container) return;
  try {
    const resp = await fetch('/api/platform-health', { credentials: 'include' });
    if (resp.ok) {
      const data = await resp.json();
      const platforms = data.platforms || data;
      if (Array.isArray(platforms) && platforms.length > 0) {
        container.innerHTML = platforms.map(p => {
          const status = p.status || p.state || 'unknown';
          const color = status === 'logged_in' || status === 'ok' || status === 'active' ? '#16a34a'
                      : status === 'checking' || status === 'pending' ? '#f59e0b'
                      : '#dc2626';
          const label = status === 'logged_in' || status === 'ok' ? '已登录'
                      : status === 'checking' ? '检查中'
                      : status === 'blocked' ? 'BLOCKED'
                      : status;
          return `
            <div class="hscroll-card">
              <h4>${p.name || p.platform || '平台'}</h4>
              <div class="card-value" style="color:${color}">${label}</div>
              <div class="card-label">${p.detail || p.message || (p.cookie_valid ? 'cookie有效' : '缺cookie')}</div>
            </div>
          `;
        }).join('');
      }
    }
  } catch (e) { /* keep default cards */ }
}


// ================================================================
// Codex Design Pattern: New Panel Logic
// ================================================================

// ── Appearance Panel ──
let appearanceInitialized = false;

function initAppearancePanel() {
  if (appearanceInitialized) return;
  appearanceInitialized = true;
  // Load saved theme
  let savedTheme = 'light';
  try { savedTheme = localStorage.getItem('lumenis-theme') || 'light'; } catch(e) {}
  selectTheme(savedTheme, false);
  // Accent color dropdown
  if (window.SettingsDropdown) {
    SettingsDropdown.init(document.getElementById('accentColorDropdown'), {
      options: [
        { value: 'teal', label: '序境青绿', desc: '#0F766E · 品牌主色' },
        { value: 'blue', label: '太古汇蓝', desc: '#2563EB · 客户域色' },
        { value: 'purple', label: '系统紫', desc: '#7C3AED · 系统域色' },
        { value: 'custom', label: '自定义…', desc: '输入自定义色值' }
      ],
      value: (function(){ try { return localStorage.getItem('lumenis-accent') || 'teal'; } catch(e){ return 'teal'; } })(),
      onChange: function(v) {
        try { localStorage.setItem('lumenis-accent', v); } catch(e) {}
        if (v === 'custom') {
          const custom = prompt('输入自定义强调色（如 #1a1a1a）：', '#0F766E');
          if (custom) {
            try { localStorage.setItem('lumenis-accent-custom', custom); } catch(e) {}
          }
        }
        showToast('强调色已更新');
      }
    });
  }
  // Load font config
  loadFontConfig();
  // Load translucent sidebar
  let transOn = false;
  try { transOn = localStorage.getItem('lumenis-translucent-sidebar') === 'true'; } catch(e) {}
  const tst = document.getElementById('translucentSidebarToggle');
  if (tst) { if (transOn) tst.classList.add('on'); }
  // Load contrast
  let contrast = 45;
  try { contrast = parseInt(localStorage.getItem('lumenis-contrast')) || 45; } catch(e) {}
  setContrastValue(contrast);
  // Load font size
  let fontSize = 14;
  try { fontSize = parseInt(localStorage.getItem('lumenis-ui-font-size')) || 14; } catch(e) {}
  const fse = document.getElementById('uiFontSize');
  if (fse) fse.value = fontSize;
  // Load reduced motion
  let rm = 'system';
  try { rm = localStorage.getItem('lumenis-reduced-motion') || 'system'; } catch(e) {}
  setReducedMotion(rm, false);
}

function selectTheme(theme, save = true) {
  document.querySelectorAll('.theme-card').forEach(c => {
    c.classList.toggle('selected', c.dataset.theme === theme);
  });
  // Apply theme
  if (theme === 'dark') {
    document.body.style.background = '#0f172a';
    document.body.style.color = '#e2e8f0';
    document.getElementById('bgValue').textContent = '#0F172A';
    document.getElementById('fgValue').textContent = '#E2E8F0';
    document.getElementById('bgSwatch').style.background = '#0F172A';
    document.getElementById('fgSwatch').style.background = '#E2E8F0';
  } else if (theme === 'system') {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) {
      document.body.style.background = '#0f172a';
      document.body.style.color = '#e2e8f0';
      document.getElementById('bgValue').textContent = '#0F172A';
      document.getElementById('fgValue').textContent = '#E2E8F0';
      document.getElementById('bgSwatch').style.background = '#0F172A';
      document.getElementById('fgSwatch').style.background = '#E2E8F0';
    } else {
      document.body.style.background = '#f8fafc';
      document.body.style.color = '#1e293b';
      document.getElementById('bgValue').textContent = '#FFFFFF';
      document.getElementById('fgValue').textContent = '#1A1C1F';
      document.getElementById('bgSwatch').style.background = '#FFFFFF';
      document.getElementById('fgSwatch').style.background = '#1A1C1F';
    }
  } else {
    document.body.style.background = '#f8fafc';
    document.body.style.color = '#1e293b';
    document.getElementById('bgValue').textContent = '#FFFFFF';
    document.getElementById('fgValue').textContent = '#1A1C1F';
    document.getElementById('bgSwatch').style.background = '#FFFFFF';
    document.getElementById('fgSwatch').style.background = '#1A1C1F';
  }
  if (save) {
    try { localStorage.setItem('lumenis-theme', theme); } catch(e) {}
    showToast('主题已切换为' + ({light:'浅色',dark:'深色',system:'跟随系统'}[theme]||theme));
  }
}

function loadFontConfig() {
  try {
    const cfg = JSON.parse(localStorage.getItem('lumenis-font-config') || '{}');
    if (cfg.uiFamily) document.getElementById('uiFontFamily').value = cfg.uiFamily;
    if (cfg.uiWeight) document.getElementById('uiFontWeight').value = cfg.uiWeight;
    if (cfg.contentFamily) document.getElementById('contentFontFamily').value = cfg.contentFamily;
    if (cfg.contentWeight) document.getElementById('contentFontWeight').value = cfg.contentWeight;
    if (cfg.codeFamily) document.getElementById('codeFontFamily').value = cfg.codeFamily;
    if (cfg.codeWeight) document.getElementById('codeFontWeight').value = cfg.codeWeight;
  } catch(e) {}
}

function saveFontConfig() {
  const cfg = {
    uiFamily: document.getElementById('uiFontFamily').value,
    uiWeight: document.getElementById('uiFontWeight').value,
    contentFamily: document.getElementById('contentFontFamily').value,
    contentWeight: document.getElementById('contentFontWeight').value,
    codeFamily: document.getElementById('codeFontFamily').value,
    codeWeight: document.getElementById('codeFontWeight').value,
  };
  try { localStorage.setItem('lumenis-font-config', JSON.stringify(cfg)); } catch(e) {}
}

function toggleTranslucentSidebar() {
  const el = document.getElementById('translucentSidebarToggle');
  el.classList.toggle('on');
  const on = el.classList.contains('on');
  try { localStorage.setItem('lumenis-translucent-sidebar', on ? 'true' : 'false'); } catch(e) {}
  const sidebar = document.querySelector('.settings-sidebar');
  if (sidebar) {
    if (on) {
      sidebar.style.background = 'rgba(255,255,255,.7)';
      sidebar.style.backdropFilter = 'blur(20px)';
    } else {
      sidebar.style.background = '';
      sidebar.style.backdropFilter = '';
    }
  }
}

function setContrast(event) {
  const track = document.getElementById('contrastSlider');
  const rect = track.getBoundingClientRect();
  const pct = Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100));
  setContrastValue(Math.round(pct));
}

function setContrastValue(val) {
  document.getElementById('contrastFill').style.width = val + '%';
  document.getElementById('contrastThumb').style.left = val + '%';
  document.getElementById('contrastValue').textContent = val;
  try { localStorage.setItem('lumenis-contrast', val); } catch(e) {}
}

function saveFontSize() {
  const val = parseInt(document.getElementById('uiFontSize').value) || 14;
  try { localStorage.setItem('lumenis-ui-font-size', val); } catch(e) {}
  document.documentElement.style.fontSize = val + 'px';
}

function setReducedMotion(val, save = true) {
  document.querySelectorAll('#reducedMotionSegment button').forEach(b => {
    b.classList.toggle('active', b.dataset.value === val);
  });
  if (val === 'on') {
    document.documentElement.style.setProperty('reduced-motion', 'reduce');
    document.body.classList.add('reduced-motion');
  } else if (val === 'off') {
    document.documentElement.style.removeProperty('reduced-motion');
    document.body.classList.remove('reduced-motion');
  } else {
    const prefers = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefers) document.body.classList.add('reduced-motion');
    else document.body.classList.remove('reduced-motion');
  }
  if (save) {
    try { localStorage.setItem('lumenis-reduced-motion', val); } catch(e) {}
  }
}

// ── Config Panel ──
let configInitialized = false;

function initConfigPanel() {
  if (configInitialized) return;
  configInitialized = true;
  if (!window.SettingsDropdown) return;

  // AI Provider - read from real API
  fetch('/api/system/config', { credentials: 'include' }).then(r => r.json()).then(data => {
    const currentProvider = data.ai_provider || 'zhipu';
    const aiEnabled = data.ai_enabled !== false;
    const aiToggle = document.getElementById('aiEnabledToggle');
    if (aiToggle) { if (aiEnabled) aiToggle.classList.add('on'); else aiToggle.classList.remove('on'); }

    SettingsDropdown.init(document.getElementById('aiProviderDropdown'), {
      options: [
        { value: 'zhipu', label: '智谱主力', desc: 'GLM-4.5-Air 日常 · GLM-5.3 强推理' },
        { value: 'doubao', label: '豆包兜底', desc: 'ARK 通道 · 智谱不可用时降级' },
        { value: 'ollama', label: '本地 Ollama', desc: '离线本地模型 · 无需网络' },
        { value: 'rule', label: '纯规则', desc: '关闭 AI · 全部走确定性规则引擎' }
      ],
      value: currentProvider,
      onChange: function(v) {
        showToast('AI Provider 已切换为：' + v + '（重启后生效）');
      }
    });
  }).catch(() => {
    SettingsDropdown.init(document.getElementById('aiProviderDropdown'), {
      options: [
        { value: 'zhipu', label: '智谱主力', desc: 'GLM-4.5-Air 日常 · GLM-5.3 强推理' },
        { value: 'doubao', label: '豆包兜底', desc: 'ARK 通道 · 智谱不可用时降级' },
        { value: 'ollama', label: '本地 Ollama', desc: '离线本地模型 · 无需网络' },
        { value: 'rule', label: '纯规则', desc: '关闭 AI · 全部走确定性规则引擎' }
      ],
      value: 'zhipu',
      onChange: function(v) { showToast('AI Provider：' + v); }
    });
  });

  // Output detail
  SettingsDropdown.init(document.getElementById('outputDetailDropdown'), {
    options: [
      { value: 'low', label: '低', desc: '简洁回复，最少上下文' },
      { value: 'medium', label: '中', desc: '标准详细程度（默认）' },
      { value: 'high', label: '高', desc: '完整分析，包含推理过程' }
    ],
    value: (function(){ try { return localStorage.getItem('lumenis-output-detail') || 'medium'; } catch(e){ return 'medium'; } })(),
    onChange: function(v) { try { localStorage.setItem('lumenis-output-detail', v); } catch(e){} showToast('输出详细程度：' + v); }
  });

  // Reasoning summary
  SettingsDropdown.init(document.getElementById('reasoningSummaryDropdown'), {
    options: [
      { value: 'auto', label: '自动', desc: '根据问题复杂度自动决定' },
      { value: 'concise', label: '简洁', desc: '仅展示关键推理步骤' },
      { value: 'detailed', label: '详细', desc: '展示完整推理过程' },
      { value: 'none', label: '无', desc: '不展示推理过程' }
    ],
    value: (function(){ try { return localStorage.getItem('lumenis-reasoning-summary') || 'auto'; } catch(e){ return 'auto'; } })(),
    onChange: function(v) { try { localStorage.setItem('lumenis-reasoning-summary', v); } catch(e){} showToast('推理摘要：' + v); }
  });

  // Web search
  SettingsDropdown.init(document.getElementById('webSearchDropdown'), {
    options: [
      { value: 'disabled', label: '已禁用', desc: '不联网，仅用本地数据' },
      { value: 'cached', label: '已缓存', desc: '使用本地缓存的检索结果' },
      { value: 'indexed', label: '已索引', desc: '使用系统索引的内容库' },
      { value: 'realtime', label: '实时', desc: '实时联网检索（消耗额度）' }
    ],
    value: (function(){ try { return localStorage.getItem('lumenis-web-search') || 'indexed'; } catch(e){ return 'indexed'; } })(),
    onChange: function(v) { try { localStorage.setItem('lumenis-web-search', v); } catch(e){} showToast('联网方式：' + v); }
  });

  // Approval policy
  SettingsDropdown.init(document.getElementById('approvalPolicyDropdown'), {
    options: [
      { value: 'per_request', label: '按请求', desc: '每次高风险操作需审批确认' },
      { value: 'never', label: '从不请求审批', desc: '信任当前账号，跳过审批（不推荐）' }
    ],
    value: (function(){ try { return localStorage.getItem('lumenis-approval-policy') || 'per_request'; } catch(e){ return 'per_request'; } })(),
    onChange: function(v) { try { localStorage.setItem('lumenis-approval-policy', v); } catch(e){} showToast('采集批准策略：' + v); }
  });
}

function toggleAIEnabled() {
  const el = document.getElementById('aiEnabledToggle');
  el.classList.toggle('on');
  const on = el.classList.contains('on');
  const area = document.getElementById('configStatusArea');
  if (area) {
    area.innerHTML = on
      ? '<div class="status-badge ok">AI 已启用 · 规则引擎为兜底</div>'
      : '<div class="status-badge warn">AI 已关闭 · 全部走本地规则引擎</div>';
  }
  showToast(on ? 'AI 已启用' : 'AI 已关闭，切换为纯规则模式');
}

// ── Keyboard Shortcuts Panel ──
let keyboardShortcuts = [];

function initKeyboardPanel() {
  if (!window.SettingsKeyboard) {
    document.getElementById('keyboardShortcutsList').innerHTML = '<div class="empty-state">键盘快捷键模块未加载</div>';
    return;
  }
  keyboardShortcuts = SettingsKeyboard.load();
  renderKeyboardShortcuts();
}

function renderKeyboardShortcuts(filter) {
  const container = document.getElementById('keyboardShortcutsList');
  if (!container) return;
  const q = (filter || '').toLowerCase().trim();
  const categories = {};
  keyboardShortcuts.forEach(s => {
    if (q && !(s.name + ' ' + s.desc + ' ' + (s.combo || '')).toLowerCase().includes(q)) return;
    if (!categories[s.category]) categories[s.category] = [];
    categories[s.category].push(s);
  });
  const count = Object.values(categories).reduce((a, b) => a + b.length, 0);
  if (count === 0) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">⌨️</div>没有匹配的快捷键</div>';
    return;
  }
  let html = '';
  Object.keys(categories).forEach(cat => {
    html += '<div class="kb-group-title">' + cat + '</div>';
    categories[cat].forEach(s => {
      const comboHtml = s.combo
        ? '<span class="kb-combo">' + s.combo.split('+').map(k => '<kbd>' + k + '</kbd>').join('') + '</span>'
        : '<span class="kb-unassigned">未分配</span>';
      const editBtn = s.editable
        ? '<button class="kb-icon-btn" title="编辑" onclick="editKeyboardShortcut(\'' + s.id + '\')"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>'
        : '';
      const delBtn = s.editable
        ? '<button class="kb-icon-btn danger" title="删除" onclick="deleteKeyboardShortcut(\'' + s.id + '\')"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>'
        : '';
      html += '<div class="kb-row" id="kb-row-' + s.id + '">' +
        '<div class="kb-row-info"><div class="kb-row-name">' + s.name + '</div>' +
        '<div class="kb-row-desc">' + s.desc + '</div></div>' +
        comboHtml +
        '<div class="kb-actions">' + editBtn + delBtn + '</div>' +
        '</div>';
    });
  });
  container.innerHTML = html;
}

function filterKeyboardShortcuts() {
  const q = document.getElementById('kbFilterInput').value;
  renderKeyboardShortcuts(q);
}

function editKeyboardShortcut(id) {
  const row = document.getElementById('kb-row-' + id);
  if (row) row.classList.add('kb-capturing');
  SettingsKeyboard.capture(function(combo) {
    if (row) row.classList.remove('kb-capturing');
    if (!combo) return;
    const conflict = SettingsKeyboard.findConflict(keyboardShortcuts, id, combo);
    if (conflict) {
      showToast('快捷键冲突：' + combo + ' 已被「' + conflict.name + '」占用', 'error');
      return;
    }
    const s = keyboardShortcuts.find(x => x.id === id);
    if (s) { s.combo = combo; SettingsKeyboard.save(keyboardShortcuts); renderKeyboardShortcuts(); showToast('快捷键已更新：' + combo); }
  });
}

function deleteKeyboardShortcut(id) {
  const s = keyboardShortcuts.find(x => x.id === id);
  if (s && !s.editable) { showToast('系统快捷键不可删除', 'error'); return; }
  if (s) { s.combo = ''; SettingsKeyboard.save(keyboardShortcuts); renderKeyboardShortcuts(); showToast('快捷键已移除'); }
}

function resetKeyboardShortcuts() {
  if (!confirm('确认恢复所有快捷键为默认值？')) return;
  keyboardShortcuts = SettingsKeyboard.reset();
  renderKeyboardShortcuts();
  showToast('已恢复默认快捷键');
}

// ── Skills Panel (Codex pattern) ──
let skillsData = [];
let currentSkillTab = 'plugins';

function loadSkillsCodex() {
  const container = document.getElementById('skillList');
  if (!container) return;
  container.innerHTML = '<div class="loading-spinner"></div><div style="text-align:center;font-size:12px;color:#94a3b8;margin-top:8px">正在加载…</div>';
  fetch('/api/system/account/skills', { credentials: 'include' }).then(r => r.json()).then(data => {
    if (data.ok && data.skills) {
      skillsData = data.skills;
    } else {
      skillsData = [];
    }
    updateSkillCounts();
    renderSkillsCodex();
  }).catch(() => {
    skillsData = [];
    updateSkillCounts();
    renderSkillsCodex();
  });
}

function updateSkillCounts() {
  const plugins = skillsData.filter(s => s.type !== 'mcp').length;
  const mcps = skillsData.filter(s => s.type === 'mcp').length;
  const pc = document.getElementById('pluginCount');
  const mc = document.getElementById('mcpCount');
  if (pc) pc.textContent = plugins;
  if (mc) mc.textContent = mcps;
}

function switchSkillTab(tab) {
  currentSkillTab = tab;
  document.querySelectorAll('.skill-tab').forEach(t => t.classList.toggle('active', t.dataset.skillTab === tab));
  renderSkillsCodex();
}

function filterSkills() {
  renderSkillsCodex();
}

function renderSkillsCodex() {
  const container = document.getElementById('skillList');
  if (!container) return;
  const q = (document.getElementById('skillSearchInput')?.value || '').toLowerCase().trim();
  let list = skillsData.filter(s => {
    if (currentSkillTab === 'mcp') return s.type === 'mcp';
    return s.type !== 'mcp';
  });
  if (q) list = list.filter(s => (s.name + ' ' + (s.description || '')).toLowerCase().includes(q));
  if (list.length === 0) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div>' + (skillsData.length === 0 ? '暂无已安装插件' : '没有匹配的插件') + '</div>';
    return;
  }
  const colors = ['#0F766E', '#2563EB', '#7C3AED', '#D97706', '#DC2626', '#0891B2', '#65A30D', '#DB2777'];
  let html = '';
  list.forEach((s, idx) => {
    const color = colors[idx % colors.length];
    const enabled = s.status === 'enabled';
    const iconChar = (s.name || '?')[0].toUpperCase();
    html += '<div class="skill-row" onclick="toggleSkillDetail(\'' + (s.skill_id || s.id) + '\')" style="cursor:pointer">' +
      '<div class="skill-icon" style="background:' + color + '">' + iconChar + '</div>' +
      '<div class="skill-info">' +
        '<div class="skill-name">' + (s.name || '未命名') + '</div>' +
        '<div class="skill-desc">' + (s.description || '—') + '</div>' +
      '</div>' +
      '<div class="skill-toggle" onclick="event.stopPropagation()">' +
        '<div class="toggle ' + (enabled ? 'on' : '') + '" onclick="toggleSkillStatus(\'' + (s.skill_id || s.id) + '\',\'' + (enabled ? 'disabled' : 'enabled') + '\')"></div>' +
      '</div>' +
      '<button class="skill-more" onclick="event.stopPropagation();showToast(\'更多操作：' + (s.name || '') + '\')">⋯</button>' +
      '</div>' +
      '<div class="skill-detail" id="skill-detail-' + (s.skill_id || s.id) + '">' +
        '<div class="skill-detail-grid">' +
          '<div class="skill-detail-item"><span class="dt-label">版本：</span>v' + (s.version || '1.0') + '</div>' +
          '<div class="skill-detail-item"><span class="dt-label">类型：</span>' + (s.type || 'plugin') + '</div>' +
          '<div class="skill-detail-item"><span class="dt-label">域：</span>' + (s.product || s.domain || '—') + '</div>' +
          '<div class="skill-detail-item"><span class="dt-label">状态：</span>' + (enabled ? '已启用' : '已禁用') + '</div>' +
        '</div>' +
        '<div style="font-size:11px;color:#94a3b8;margin-bottom:8px">能力：' + (s.capabilities || '语义识别 · 内容分析 · 规则辅助') + '</div>' +
        '<div style="display:flex;gap:6px">' +
          '<button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();showToast(\'配置入口：' + (s.name || '') + '\')">配置</button>' +
          '<button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();showToast(\'使用记录：' + (s.name || '') + '\')">使用记录</button>' +
          (enabled
            ? '<button class="btn btn-danger btn-sm" onclick="event.stopPropagation();toggleSkillStatus(\'' + (s.skill_id || s.id) + '\',\'disabled\')">禁用</button>'
            : '<button class="btn btn-primary btn-sm" onclick="event.stopPropagation();toggleSkillStatus(\'' + (s.skill_id || s.id) + '\',\'enabled\')">启用</button>') +
        '</div>' +
      '</div>';
  });
  container.innerHTML = html;
}

function toggleSkillDetail(id) {
  const el = document.getElementById('skill-detail-' + id);
  if (el) el.classList.toggle('show');
}

function openAddSkillModal() {
  showToast('添加插件：请在「浏览目录」中选择安装');
}

// ── Browser Panel ──
let browserInitialized = false;

function initBrowserPanel() {
  if (browserInitialized) return;
  browserInitialized = true;
  if (!window.SettingsDropdown) return;

  SettingsDropdown.init(document.getElementById('linkOpenDropdown'), {
    options: [
      { value: 'current', label: '当前标签', desc: '在当前标签页打开链接' },
      { value: 'new_tab', label: '新标签', desc: '在新标签页打开链接' },
      { value: 'new_window', label: '新窗口', desc: '在新窗口打开链接' }
    ],
    value: (function(){ try { return localStorage.getItem('lumenis-link-open') || 'new_tab'; } catch(e){ return 'new_tab'; } })(),
    onChange: function(v) { try { localStorage.setItem('lumenis-link-open', v); } catch(e){} showToast('链接打开位置：' + v); }
  });

  SettingsDropdown.init(document.getElementById('screenshotDropdown'), {
    options: [
      { value: 'save', label: '保存到本地', desc: '截图自动保存到下载目录' },
      { value: 'annotate', label: '批注后保存', desc: '打开批注工具编辑后保存' },
      { value: 'clipboard', label: '复制到剪贴板', desc: '截图直接复制，不保存文件' }
    ],
    value: (function(){ try { return localStorage.getItem('lumenis-screenshot') || 'save'; } catch(e){ return 'save'; } })(),
    onChange: function(v) { try { localStorage.setItem('lumenis-screenshot', v); } catch(e){} showToast('批注截图：' + v); }
  });

  // Load toggles
  let showFull = false;
  try { showFull = localStorage.getItem('lumenis-show-full-url') === 'true'; } catch(e) {}
  const sf = document.getElementById('showFullUrlToggle');
  if (sf && showFull) sf.classList.add('on');

  let dlAsk = false;
  try { dlAsk = localStorage.getItem('lumenis-download-ask') === 'true'; } catch(e) {}
  const da = document.getElementById('downloadAskToggle');
  if (da && dlAsk) da.classList.add('on');
}

function toggleBrowserControl() {
  const el = document.getElementById('browserControlToggle');
  el.classList.toggle('on');
  showToast(el.classList.contains('on') ? '已允许系统控制内置浏览器' : '已禁止系统控制内置浏览器');
}

function toggleShowFullUrl() {
  const el = document.getElementById('showFullUrlToggle');
  el.classList.toggle('on');
  try { localStorage.setItem('lumenis-show-full-url', el.classList.contains('on') ? 'true' : 'false'); } catch(e) {}
}

function toggleDownloadAsk() {
  const el = document.getElementById('downloadAskToggle');
  el.classList.toggle('on');
  try { localStorage.setItem('lumenis-download-ask', el.classList.contains('on') ? 'true' : 'false'); } catch(e) {}
}

function clearBrowserData() {
  if (!confirm('确认清除浏览数据？此操作不可恢复。')) return;
  fetch('/api/browser-surface/history/clear', { method: 'POST', credentials: 'include' }).then(r => r.json()).then(data => {
    if (data.ok || data.success) showToast('浏览数据已清除');
    else showToast(data.error || '清除失败', 'error');
  }).catch(() => {
    // Fallback: clear local history file via browser_surface
    showToast('已发送清除请求（本地历史）');
  });
}

function showBrowserHistory() {
  openModal('browserHistoryModal');
  const container = document.getElementById('browserHistoryList');
  container.innerHTML = '<div class="loading-spinner"></div>';
  fetch('/api/browser-surface/history?limit=50', { credentials: 'include' }).then(r => r.json()).then(data => {
    const items = data.history || data.data?.history || [];
    if (!items.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">🕐</div>暂无浏览历史</div>';
      return;
    }
    container.innerHTML = items.map(h =>
      '<div class="device-row"><div class="device-icon">🌐</div>' +
      '<div class="device-info"><div class="device-name">' + (h.title || h.url || '无标题') + '</div>' +
      '<div class="device-meta">' + (h.url || '') + ' · ' + (h.visited_at || h.visitedAt || '') + '</div></div></div>'
    ).join('');
  }).catch(() => {
    container.innerHTML = '<div class="empty-state">浏览历史接口不可用</div>';
  });
}

function clearBrowserHistory() {
  if (!confirm('确认清除全部浏览历史？')) return;
  fetch('/api/browser-surface/history/clear', { method: 'POST', credentials: 'include' }).then(() => {
    showToast('浏览历史已清除');
    closeModal('browserHistoryModal');
  }).catch(() => showToast('清除请求已发送'));
}

function showDownloadHistory() {
  openModal('downloadHistoryModal');
  const container = document.getElementById('downloadHistoryList');
  container.innerHTML = '<div class="loading-spinner"></div>';
  fetch('/api/browser-surface/downloads', { credentials: 'include' }).then(r => r.json()).then(data => {
    const files = data.files || data.downloads || [];
    if (!files.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">📥</div>暂无下载记录</div>';
      return;
    }
    container.innerHTML = files.map(f =>
      '<div class="device-row"><div class="device-icon">📄</div>' +
      '<div class="device-info"><div class="device-name">' + (f.name || '文件') + '</div>' +
      '<div class="device-meta">' + (f.size ? Math.round(f.size/1024) + ' KB' : '') + ' · ' + (f.modified || '') + '</div></div></div>'
    ).join('');
  }).catch(() => {
    container.innerHTML = '<div class="empty-state">下载记录接口不可用</div>';
  });
}

// ── Integrations Panel ──
function loadIntegrations() {
  const container = document.getElementById('integrationsList');
  const summary = document.getElementById('integrationsSummary');
  if (!container) return;
  container.innerHTML = '<div class="loading-spinner"></div><div style="text-align:center;font-size:12px;color:#94a3b8;margin-top:8px">正在检测平台连接…</div>';

  fetch('/api/collector/status', { credentials: 'include' }).then(r => r.json()).then(data => {
    const platforms = (data.data && data.data.platforms) || data.platforms || [];
    if (!platforms.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">🔌</div>暂无采集平台配置</div>';
      if (summary) summary.textContent = '0 个平台';
      return;
    }
    const colors = { xiaohongshu: '#FF2442', weibo: '#E6162D', bilibili: '#00A1D6', zhihu: '#0066FF', douyin: '#000000', x: '#1DA1F2', instagram: '#E4405F', aurora: '#0F766E' };
    let html = '';
    let verified = 0, partial = 0, expired = 0, blocked = 0;
    platforms.forEach(p => {
      const name = p.name || p.platform || '未知';
      const status = (p.cookie_status || p.status || 'unknown').toUpperCase();
      const key = name.toLowerCase().replace(/[^a-z]/g, '');
      const color = colors[key] || '#64748B';
      const iconChar = name[0].toUpperCase();
      let statusClass = 'unknown', statusLabel = status;
      if (status === 'VERIFIED' || status === 'ACTIVE' || status === 'OK') { statusClass = 'verified'; statusLabel = 'VERIFIED'; verified++; }
      else if (status === 'PARTIAL') { statusClass = 'partial'; statusLabel = 'PARTIAL'; partial++; }
      else if (status === 'EXPIRED' || status === 'INVALID') { statusClass = 'expired'; statusLabel = 'EXPIRED'; expired++; }
      else if (status === 'BLOCKED' || status === 'MISSING') { statusClass = 'blocked'; statusLabel = 'BLOCKED'; blocked++; }
      const desc = p.detail || p.message || (statusClass === 'verified' ? '凭证有效，可正常采集' : statusClass === 'partial' ? '部分功能受限' : statusClass === 'expired' ? '凭证已过期，需重新登录' : '未配置或被平台限制');
      html += '<div class="integration-row">' +
        '<div class="integration-icon" style="background:' + color + '">' + iconChar + '</div>' +
        '<div class="integration-info">' +
          '<div class="integration-name">' + name + '</div>' +
          '<div class="integration-desc">' + desc + '</div>' +
        '</div>' +
        '<span class="integration-status ' + statusClass + '">' + statusLabel + '</span>' +
        '</div>';
    });
    container.innerHTML = html;
    if (summary) summary.textContent = platforms.length + ' 个平台 · ' + verified + ' 有效 · ' + partial + ' 受限 · ' + expired + ' 过期 · ' + blocked + ' 阻断';
  }).catch(err => {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div>采集器状态接口不可用<br><span style="font-size:11px">' + (err.message || '网络错误') + '</span></div>';
    if (summary) summary.textContent = '接口不可用';
  });
}


