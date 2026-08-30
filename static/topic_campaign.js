// 话题监测端口 前端逻辑 v5.8.5
// 两层：监测任务列表 -> 单任务详情（话题指标 / 时段传播趋势 / 专题笔记库）
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

function n(x) { return Number(x || 0).toLocaleString('zh-CN'); }
function shortNum(x) {
  const v = Number(x || 0);
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿';
  if (v >= 1e4) return (v / 1e4).toFixed(1) + '万';
  return v.toLocaleString('zh-CN');
}
function escHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function cleanErr(e) {
  if (!e) return '';
  let s = String(e).replace(/\x1b\[[0-9;]*m/g, '');
  for (let i = 0; i < 3; i++) {
    const m = s.match(/"error"\s*:\s*"((?:[^"\\]|\\.)*)"/);
    if (!m) break;
    try { s = JSON.parse('"' + m[1] + '"'); } catch (_) { s = m[1]; break; }
  }
  s = s.replace(/\s+/g, ' ').trim();
  return s.length > 140 ? s.slice(0, 140) + '…' : s;
}
function toast(msg, duration = 3000) {
  const el = $('#toast');
  el.textContent = msg; el.classList.add('show');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('show'), duration);
}
async function api(url, options) {
  const r = await fetch(url, options);
  return r.json();
}
function niceCeil(v) {
  if (v <= 10) return 10;
  const pow = Math.pow(10, Math.floor(Math.log10(v)));
  const x = v / pow;
  let nice;
  if (x <= 1) nice = 1; else if (x <= 2) nice = 2; else if (x <= 5) nice = 5; else nice = 10;
  return nice * pow;
}

let CUR_KEY = null;      // 当前打开的任务 key
let allTopics = [];
let allNotes = [];
let TASKS = [];

function qk(extra) { // 拼 campaign_key
  const base = extra ? extra + '&' : '';
  return base + 'campaign_key=' + encodeURIComponent(CUR_KEY || '');
}

/* ============ 第一层：任务列表 ============ */
async function loadTaskList() {
  const d = await api('/api/topic-campaign/campaigns');
  TASKS = d.campaigns || [];
  const box = $('#taskCards');
  if (!TASKS.length) {
    box.innerHTML = '<div class="topic-card"><div class="topic-name">暂无监测任务</div><div class="metric-sub">点右上角「+ 新建话题监测」建立</div></div>';
    return;
  }
  box.innerHTML = TASKS.map(t => {
    const agg = t.agg || {};
    const paused = t.status === 'paused';
    const win = t.in_window;
    const stateCls = paused ? 'error' : (win ? '' : 'error');
    const stateTxt = paused ? '已暂停' : (win ? '监测中' : '窗口外');
    return `<div class="topic-card task-card ${stateCls}" data-key="${escHtml(t.campaign_key)}" style="cursor:pointer">
      <div style="display:flex;align-items:center;gap:8px">
        <div class="topic-name" style="flex:1;min-width:0">${escHtml(t.name)}</div>
        <span class="task-state" data-act="toggle" data-key="${escHtml(t.campaign_key)}" data-status="${paused ? 'active' : 'paused'}"
          style="font-size:11px;padding:3px 9px;border-radius:999px;background:${paused ? '#eee' : 'rgba(52,199,89,.14)'};color:${paused ? '#8e8e93' : '#248a42'};cursor:pointer">${stateTxt}</span>
      </div>
      <div class="metric-sub">${escHtml(t.start_date)} ~ ${escHtml(t.end_date)} · ${n(t.topic_count)} 话题 · 间隔 ${n(t.interval_minutes)} 分</div>
      <div class="metric-sub">专题笔记 <b>${n(t.note_count)}</b> · 累计讨论 <b>${n(agg.dis)}</b> · 累计互动 <b>${n(agg.eng)}</b>${agg.last ? ' · 最近 ' + escHtml(String(agg.last).slice(5, 16)) : ''}</div>
      <div style="display:flex;gap:8px;margin-top:8px">
        <span class="task-open" data-act="open" data-key="${escHtml(t.campaign_key)}" style="font-size:12px;color:#0a84ff;font-weight:600">进入任务 ›</span>
        <span class="task-edit" data-act="edit" data-key="${escHtml(t.campaign_key)}" style="font-size:12px;color:#8e8e93;cursor:pointer">✎ 编辑</span>
      </div>
    </div>`;
  }).join('');
  box.querySelectorAll('[data-act]').forEach(el => {
    el.onclick = (e) => {
      e.stopPropagation();
      const act = el.dataset.act, key = el.dataset.key;
      if (act === 'open') openTask(key);
      else if (act === 'edit') openEditor(key);
      else if (act === 'toggle') toggleTask(key, el.dataset.status);
    };
  });
  box.querySelectorAll('.task-card').forEach(card => {
    card.onclick = () => openTask(card.dataset.key);
  });
}

async function toggleTask(key, status) {
  await api('/api/topic-campaign/campaign-toggle', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ campaign_key: key, status })
  });
  toast(status === 'active' ? '已恢复监测' : '已暂停');
  loadTaskList();
}

/* ============ 第二层：任务详情 ============ */
function showDetail(show) {
  $('#taskListView').style.display = show ? 'none' : '';
  $('#taskDetailView').style.display = show ? '' : 'none';
}

async function openTask(key) {
  CUR_KEY = key;
  showDetail(true);
  window.scrollTo({ top: 0 });
  await Promise.all([loadStatus(), loadTopics()]);
  await Promise.all([loadNotes(), drawChart()]);
}

async function loadStatus() {
  try {
    const s = await api('/api/topic-campaign/status?campaign_key=' + encodeURIComponent(CUR_KEY));
    if (!s.ok) throw new Error(s.error || '加载失败');
    const c = s.campaign || {};
    $('#detailTitle').textContent = c.name || '任务详情';
    $('#campaignMeta').textContent =
      `监测周期 ${c.start_date || '—'} 至 ${c.end_date || '—'} · 每日 ${(s.collect_hours || []).join(':00 / ')}:00 错峰自动采集 · 今日已执行 ${(s.today_run_hours || []).length} 次`;
    const pill = $('#statusPill'), dot = pill.querySelector('.status-dot');
    if (s.active_window) { dot.className = 'status-dot'; $('#statusText').textContent = s.scheduler_running ? '监测中' : '调度未启动'; }
    else { dot.className = 'status-dot error'; $('#statusText').textContent = '窗口外/已暂停'; }
    const latest = s.latest || [];
    const cards = $('#topicCards');
    if (!latest.length) {
      cards.innerHTML = '<div class="topic-card"><div class="topic-name">暂无快照</div><div class="metric-sub">点击「立即更新」开始采集</div></div>';
    } else {
      cards.innerHTML = latest.map(x => {
        const st = x.status || '';
        const isError = st === 'error';
        const isVerify = st === 'need_verify';
        const isBlocked = st === 'blocked';
        const cardCls = isError ? 'error' : ((isVerify || isBlocked) ? 'warn' : '');
        const errMsg = cleanErr(x.error);
        const stateLine = isError ? `<div class="topic-err">采集未成功：${escHtml(errMsg.slice(0, 48)) || '浏览器未连接'}</div>`
          : isVerify ? `<div class="topic-warn">需安全验证：${escHtml(errMsg.slice(0, 48))}（已熔断，不计 0 条）</div>`
          : isBlocked ? `<div class="topic-warn">风控熔断冷却：${escHtml(errMsg.slice(0, 48))}</div>` : '';
        return `<div class="topic-card ${cardCls}" title="${escHtml(errMsg)}">
          <div class="topic-name">${escHtml(x.topic)}</div>
          ${stateLine}
          <div class="metric-row"><span class="metric-value blue">${shortNum(x.browse_count)}</span><span class="metric-label">浏览</span></div>
          <div class="metric-row"><span class="metric-value amber">${shortNum(x.discussion_count)}</span><span class="metric-label">讨论</span></div>
          <div class="metric-sub">笔记 <b>${n(x.note_count)}</b> · 新增 <b>${n(x.new_note_count)}</b> · 互动 <b>${n(x.engagement_count)}</b></div>
        </div>`;
      }).join('');
    }
    if (s.last_run_at) $('#statusText').textContent += ` · 最近 ${s.last_run_at.slice(5, 16)}`;
    renderCircuitBanner(s.circuit);
  } catch (e) { $('#campaignMeta').textContent = '加载失败: ' + e.message; }
}

/* 全局 Auth/风控熔断横幅：不跳页，当前详情内直接显示平台状态 + 合法验证后的恢复入口（对应统一 Auth Recovery） */
function renderCircuitBanner(cir) {
  const bar0 = $('#circuitBanner');
  if (!cir) { if (bar0) bar0.remove(); return; }
  const isVerify = cir.status === 'NEED_VERIFY';
  let bar = bar0;
  if (!bar) { bar = document.createElement('div'); bar.id = 'circuitBanner'; $('#topicCards').parentNode.insertBefore(bar, $('#topicCards')); }
  bar.className = 'circuit-banner ' + (isVerify ? 'verify' : 'blocked');
  bar.innerHTML =
    '<div class="cb-title">' + (isVerify ? '⚠ 小红书需要重新安全验证（采集已暂停，未计为 0 条）' : '⛔ 小红书采集风控熔断冷却中') + '</div>' +
    '<div class="cb-reason">平台：小红书 · 状态：' + escHtml(cir.status || '') + ' · ' + escHtml(cir.reason || '') + ' · 触发 ' + escHtml((cir.opened_at || '').slice(5)) + '</div>' +
    '<div class="cb-actions"><button class="cb-btn" id="cbRecoverBtn" type="button">我已完成验证，重新检测</button>' +
    '<span class="cb-sub">' + (isVerify ? '请在已登录浏览器或手机小红书 App 完成官方扫码/验证后，点此做健康检查，通过即自动恢复采集' : '冷却至 ' + escHtml(cir.resume_at || '—') + '，期间不发起任何请求') + '</span></div>';
  $('#cbRecoverBtn').onclick = async () => {
    const b = $('#cbRecoverBtn'); b.disabled = true; const oldTxt = b.textContent; b.textContent = '健康检测中…';
    try { const r = await api('/api/topic-campaign/recover', { method: 'POST' }); toast(r.message || '已恢复，熔断解除'); loadStatus(); }
    catch (e) { b.disabled = false; b.textContent = oldTxt; toast('尚未通过健康检查，保持熔断'); }
  };
}

async function loadTopics() {
  const t = await api('/api/topic-campaign/topics?campaign_key=' + encodeURIComponent(CUR_KEY));
  allTopics = t.topics || [];
  const opts = '<option value="">全部话题</option>' +
    allTopics.map(x => `<option value="${encodeURIComponent(x.topic)}">${escHtml(x.topic)}</option>`).join('');
  $('#topicSelect').innerHTML = opts;
  $('#notesTopicSelect').innerHTML = opts;
}

async function loadNotes(topic = '') {
  const url = '/api/topic-campaign/notes?limit=500&' + qk(topic ? 'topic=' + encodeURIComponent(topic) : '');
  const d = await api(url);
  allNotes = d.notes || [];
  $('#notesCount').textContent = `共 ${n(allNotes.length)} 条笔记`;
  const tbody = $('#notesBody');
  if (!allNotes.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="empty-row">暂无笔记数据，点击「立即更新」开始采集</td></tr>';
    return;
  }
  tbody.innerHTML = allNotes.map(x => `
    <tr>
      <td>${escHtml(x.topic)}</td>
      <td class="title-cell" title="${escHtml(x.title || '')}">${escHtml(x.title || '—')}</td>
      <td>${escHtml(x.author || '—')}</td>
      <td>${x.publish_datetime ? escHtml(x.publish_datetime.slice(0, 10)) : '—'}</td>
      <td class="num likes">${n(x.likes)}</td>
      <td class="num comments">${n(x.comments)}</td>
      <td class="num collects">${n(x.collects)}</td>
      <td class="num shares">${n(x.shares)}</td>
      <td>${x.last_seen_at ? escHtml(x.last_seen_at.slice(5, 16)) : '—'}</td>
      <td>${x.note_url ? `<a href="${escHtml(x.note_url)}" target="_blank">查看</a>` : '—'}</td>
    </tr>`).join('');
}

async function drawChart(topic = '') {
  const url = '/api/topic-campaign/timeline?limit=500&' + qk(topic ? 'topic=' + encodeURIComponent(topic) : '');
  const d = await api(url);
  const snapshots = d.snapshots || [];
  const canvas = $('#trendChart'), ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1, W = canvas.clientWidth, isNarrow = W < 480, H = isNarrow ? 230 : 260;
  canvas.width = W * dpr; canvas.height = H * dpr; ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);
  if (!snapshots.length) {
    ctx.fillStyle = '#86868b'; ctx.font = '13px -apple-system,sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('暂无快照数据，点击「立即更新」开始采集', W / 2, H / 2); return;
  }
  const byTopic = {};
  for (const s of snapshots) { (byTopic[s.topic] = byTopic[s.topic] || []).push(s); }
  let points;
  if (topic) {
    points = (byTopic[decodeURIComponent(topic)] || []).slice();
  } else {
    const tm = {};
    for (const s of snapshots) {
      const t = s.captured_at.slice(0, 16);
      if (!tm[t]) tm[t] = { time: t, browse_count: 0, discussion_count: 0, note_count: 0 };
      tm[t].browse_count += Number(s.browse_count || 0);
      tm[t].discussion_count += Number(s.discussion_count || 0);
      tm[t].note_count += Number(s.note_count || 0);
    }
    points = Object.values(tm).sort((a, b) => a.time.localeCompare(b.time));
  }
  if (!points.length) {
    ctx.fillStyle = '#86868b'; ctx.font = '13px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('该话题暂无数据', W / 2, H / 2); return;
  }
  const padL = isNarrow ? 44 : 50, padR = isNarrow ? 14 : 20, padT = 20, padB = isNarrow ? 46 : 36;
  const cw = W - padL - padR, chh = H - padT - padB;
  const maxVal = Math.max(1, ...points.map(x => Math.max(Number(x.browse_count || 0), Number(x.discussion_count || 0), Number(x.note_count || 0))));
  const niceMax = niceCeil(maxVal);
  ctx.strokeStyle = 'rgba(0,0,0,.05)'; ctx.lineWidth = 1; ctx.font = '10px sans-serif'; ctx.fillStyle = '#86868b'; ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const y = padT + chh * (1 - i / 4);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
    ctx.fillText(shortNum(niceMax * i / 4), padL - 6, y + 3);
  }
  ctx.textAlign = 'center';
  // v5.8.9 窄屏减少 x 轴标签数量并分两行显示，避免时间标签互相重叠
  const lc = Math.min(isNarrow ? 4 : 6, points.length);
  for (let i = 0; i < lc; i++) {
    const idx = Math.floor(i * (points.length - 1) / Math.max(1, lc - 1));
    const x = padL + cw * idx / Math.max(1, points.length - 1);
    const tp = points[idx].time || '';
    if (isNarrow) { ctx.fillText(tp.slice(5, 10), x, H - padB + 18); ctx.fillText(tp.slice(11, 16), x, H - padB + 31); }
    else { ctx.fillText(tp.slice(5, 10) + ' ' + tp.slice(11, 16), x, H - padB + 18); }
  }
  function line(key, color, fill) {
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = padL + cw * i / Math.max(1, points.length - 1);
      const y = padT + chh * (1 - Number(p[key] || 0) / niceMax);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.lineTo(padL + cw, padT + chh); ctx.lineTo(padL, padT + chh); ctx.closePath();
    ctx.fillStyle = fill; ctx.fill();
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = padL + cw * i / Math.max(1, points.length - 1);
      const y = padT + chh * (1 - Number(p[key] || 0) / niceMax);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color; ctx.lineWidth = 2.2; ctx.lineJoin = 'round'; ctx.stroke();
  }
  line('browse_count', '#0a84ff', 'rgba(10,132,255,.08)');
  line('discussion_count', '#ff9f0a', 'rgba(255,159,10,.05)');
  line('note_count', '#34c759', 'rgba(52,199,89,.06)');
}

/* ============ 新建 / 编辑弹窗 ============ */
function openEditor(key) {
  const modal = $('#taskModal');
  modal.style.display = '';
  if (key) {
    const t = TASKS.find(x => x.campaign_key === key);
    $('#taskModalTitle').textContent = '编辑话题监测';
    $('#tfName').value = t ? t.name : '';
    $('#tfStart').value = t ? t.start_date : '';
    $('#tfEnd').value = t ? (t.end_date === '2999-12-31' ? '' : t.end_date) : '';
    $('#tfInterval').value = t ? t.interval_minutes : 240;
    // 拉取该任务话题回填
    api('/api/topic-campaign/topics?campaign_key=' + encodeURIComponent(key)).then(d => {
      $('#tfTopics').value = (d.topics || []).map(x => x.topic).join('\n');
    });
    modal.dataset.key = key;
  } else {
    $('#taskModalTitle').textContent = '新建话题监测';
    ['tfName', 'tfStart', 'tfEnd', 'tfTopics'].forEach(id => $('#' + id).value = '');
    $('#tfInterval').value = 240; delete modal.dataset.key;
  }
}
function closeEditor() { $('#taskModal').style.display = 'none'; }
async function saveTask() {
  const name = $('#tfName').value.trim();
  if (!name) { toast('请填写任务名称'); return; }
  const body = {
    name,
    start_date: $('#tfStart').value || new Date().toISOString().slice(0, 10),
    end_date: $('#tfEnd').value || '2999-12-31',
    interval_minutes: Number($('#tfInterval').value || 240),
    topics: $('#tfTopics').value
  };
  const key = $('#taskModal').dataset.key;
  if (key) body.campaign_key = key;
  const btn = $('#taskModalSave'); btn.disabled = true; btn.textContent = '保存中…';
  try {
    const r = await api('/api/topic-campaign/campaign-save', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error(r.error || '保存失败');
    closeEditor(); toast(key ? '任务已更新' : '任务已建立，到达调度点自动采集');
    await loadTaskList();
    if (!key && r.campaign_key) openTask(r.campaign_key);
  } catch (e) { toast('保存失败: ' + e.message); }
  finally { btn.disabled = false; btn.textContent = '保存任务'; }
}

/* ============ 事件绑定 ============ */
$('#newTaskBtn').onclick = () => openEditor(null);
$('#taskModalCancel').onclick = closeEditor;
$('#taskModalSave').onclick = saveTask;
$('#taskModal').onclick = e => { if (e.target.id === 'taskModal') closeEditor(); };
$('#backToListBtn').onclick = () => { CUR_KEY = null; showDetail(false); loadTaskList(); };
$('#editTaskBtn').onclick = () => openEditor(CUR_KEY);
$('#runBtn').onclick = async () => {
  try {
    const r = await api('/api/topic-campaign/run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ campaign_key: CUR_KEY })
    });
    if (r.ok) { toast('采集已启动，约 1-3 分钟后刷新'); setTimeout(() => { loadStatus(); drawChart($('#topicSelect').value); loadNotes($('#notesTopicSelect').value); }, 4000); }
    else toast(r.error || '启动失败');
  } catch (e) { toast('请求失败: ' + e.message); }
};
$('#exportBtn').onclick = () => {
  const topic = $('#notesTopicSelect').value;
  window.open('/api/topic-campaign/export?' + qk(topic ? 'topic=' + topic : ''), '_blank');
  toast('正在导出 CSV…');
};
$('#topicSelect').onchange = e => drawChart(e.target.value);
$('#notesTopicSelect').onchange = e => loadNotes(e.target.value);

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (CUR_KEY) drawChart($('#topicSelect').value); }, 300);
});

// 初始化：进入任务列表
loadTaskList();
// 详情打开时每分钟刷新；列表每 60s 刷新任务卡
setInterval(() => { if (CUR_KEY) loadStatus(); else loadTaskList(); }, 60000);
