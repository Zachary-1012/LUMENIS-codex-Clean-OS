/* ============================================================
 * 序境 Xujing · AI 聊天界面 v2.0
 * GPT 风格简约对话，web 网页版适配
 * 调用 /api/ai/test 接口，支持消息历史、打字指示器、建议问题
 * ============================================================ */
(function (global) {
  'use strict';

  const CHAT_API = '/api/ai/test';
  const MAX_HISTORY = 30;

  let messages = [];
  let isSending = false;
  let chatContainer = null;
  let messagesEl = null;
  let inputEl = null;
  let sendBtn = null;

  // 建议问题（GPT 风格：输入框下方简约列表）
  const SUGGESTIONS = [
    { icon: 'chart', text: '今日舆情概览', q: '今天的舆情情况怎么样？' },
    { icon: 'warn', text: '高风险内容分析', q: '分析当前高风险内容' },
    { icon: 'trend', text: '近7天趋势', q: '近7天舆情趋势如何？' },
    { icon: 'tag', text: '品牌分布', q: '当前监测品牌分布情况' }
  ];

  // SVG 图标
  const ICONS = {
    chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>',
    warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    trend: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
    tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    brain: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/></svg>'
  };

  /* ---------- 初始化 ---------- */
  function init(containerId) {
    chatContainer = document.getElementById(containerId);
    if (!chatContainer) {
      chatContainer = document.createElement('div');
      chatContainer.id = containerId || 'xjChat';
      chatContainer.className = 'xj-chat-container';
      const content = document.querySelector('.content');
      if (content) content.insertBefore(chatContainer, content.firstChild);
    }
    render();
    loadHistory();
  }

  /* ---------- 渲染聊天界面（GPT 风格） ---------- */
  function render() {
    chatContainer.innerHTML = `
      <div class="xj-chat xj-chat-v2">
        <!-- 顶部分段控件 -->
        <div class="xj-chat-topbar">
          <div class="xj-chat-segment">
            <button class="xj-chat-seg-btn active" data-mode="chat">聊天</button>
            <button class="xj-chat-seg-btn" data-mode="work">工作</button>
          </div>
          <div class="xj-chat-topbar-actions">
            <button class="xj-chat-icon-btn" id="xjChatClear" title="清空对话">${ICONS.trash}</button>
          </div>
        </div>
        <!-- AI 洞察面板（聊天区顶部，可折叠） -->
        <div class="xj-chat-insight" id="xjChatInsight">
          <div class="xj-chat-insight-header" id="xjChatInsightToggle">
            <span class="xj-chat-insight-icon">${ICONS.brain}</span>
            <span class="xj-chat-insight-title">实时数据看板</span>
            <span class="xj-chat-insight-chevron">▾</span>
          </div>
          <div class="xj-chat-insight-body" id="xjChatInsightBody">
            <div class="xj-chat-insight-kpis">
              <div class="xj-chat-kpi"><span class="xj-chat-kpi-label">正面</span><span class="xj-chat-kpi-value pos" id="xjKpiPos">--</span></div>
              <div class="xj-chat-kpi"><span class="xj-chat-kpi-label">负面</span><span class="xj-chat-kpi-value neg" id="xjKpiNeg">--</span></div>
              <div class="xj-chat-kpi"><span class="xj-chat-kpi-label">高风险</span><span class="xj-chat-kpi-value warn" id="xjKpiRisk">--</span></div>
              <div class="xj-chat-kpi"><span class="xj-chat-kpi-label">互动</span><span class="xj-chat-kpi-value" id="xjKpiEng">--</span></div>
            </div>
            <div class="xj-chat-trend-wrap">
              <div class="xj-chat-trend-title">近7天舆情趋势</div>
              <div class="xj-chat-trend" id="xjChatTrend"></div>
            </div>
          </div>
        </div>
        <!-- 消息列表 -->
        <div class="xj-chat-messages" id="xjChatMessages"></div>
        <!-- 底部输入区（GPT 风格大圆角） -->
        <div class="xj-chat-input-area">
          <div class="xj-chat-input-wrap-v2">
            <button class="xj-chat-input-plus" title="添加">${ICONS.plus}</button>
            <textarea class="xj-chat-input-v2" id="xjChatInput" placeholder="有问题，随便问" rows="1"></textarea>
            <button class="xj-chat-send-v2" id="xjChatSend" disabled>${ICONS.send}</button>
          </div>
          <!-- 建议问题（输入框下方简约列表） -->
          <div class="xj-chat-suggestions-v2" id="xjChatSuggestions">
            ${SUGGESTIONS.map(s => `
              <button class="xj-chat-suggestion-v2" data-q="${escapeAttr(s.q)}">
                <span class="xj-chat-suggestion-icon-v2">${ICONS[s.icon] || ''}</span>
                <span class="xj-chat-suggestion-text-v2">${s.text}</span>
              </button>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    messagesEl = document.getElementById('xjChatMessages');
    inputEl = document.getElementById('xjChatInput');
    sendBtn = document.getElementById('xjChatSend');

    // 事件绑定
    inputEl.addEventListener('input', autoResize);
    inputEl.addEventListener('keydown', handleKeydown);
    sendBtn.addEventListener('click', sendMessage);
    document.getElementById('xjChatClear').addEventListener('click', clearChat);

    // 分段控件
    document.querySelectorAll('.xj-chat-seg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.xj-chat-seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // AI 洞察面板折叠
    document.getElementById('xjChatInsightToggle').addEventListener('click', () => {
      const body = document.getElementById('xjChatInsightBody');
      const chevron = document.querySelector('.xj-chat-insight-chevron');
      body.classList.toggle('collapsed');
      chevron.style.transform = body.classList.contains('collapsed') ? 'rotate(-90deg)' : 'rotate(0)';
    });

    // 建议问题点击
    document.querySelectorAll('.xj-chat-suggestion-v2').forEach(btn => {
      btn.addEventListener('click', () => {
        inputEl.value = btn.dataset.q;
        autoResize();
        sendMessage();
      });
    });

    // 加载 AI 洞察数据
    loadInsightData();

    // 渲染空状态或历史
    if (messages.length === 0) {
      renderEmptyState();
    } else {
      messages.forEach(m => appendMessage(m.role, m.content, m.timestamp, false));
    }
  }

  /* ---------- 空状态（GPT 风格：极简，只有输入框+建议） ---------- */
  function renderEmptyState() {
    // GPT 风格：消息列表区域留空，输入框和建议在底部
    // 当有消息时自动隐藏建议
    messagesEl.innerHTML = '';
    messagesEl.classList.add('empty');
  }

  /* ---------- 加载 AI 洞察数据 ---------- */
  async function loadInsightData() {
    try {
      const resp = await apiFetch('/api/dashboard/all');
      const stats = resp.stats || {};
      const pos = stats.positive || 0;
      const neg = stats.negative || 0;
      const risk = stats.high_risk || 0;
      const eng = stats.total_engagements || 0;
      animateNumber('xjKpiPos', pos);
      animateNumber('xjKpiNeg', neg);
      animateNumber('xjKpiRisk', risk);
      document.getElementById('xjKpiEng').textContent = formatEngagement(eng);

      // 渲染近7天趋势图（复用 xujing-viz.js）
      const trendEl = document.getElementById('xjChatTrend');
      if (trendEl && global.xjViz && global.xjViz.trend) {
        const trendData = (resp.overview && resp.overview.trend) || [];
        const last7 = trendData.slice(-7).map(function(d) {
          return { value: d.total || 0, label: d.label || d.date || '' };
        });
        if (last7.length > 0) {
          global.xjViz.trend(trendEl, last7, { height: 100, width: trendEl.clientWidth || 280 });
        }
      }
    } catch (e) {
      // 数据加载失败，保持 --
    }
  }

  function animateNumber(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const duration = 800;
    const start = performance.now();
    function update(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(target * eased).toLocaleString();
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  function formatEngagement(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + '万';
    return n.toLocaleString();
  }

  /* ---------- 发送消息 ---------- */
  async function sendMessage() {
    if (isSending) return;
    const text = inputEl.value.trim();
    if (!text) return;

    // 隐藏建议问题
    const suggestions = document.getElementById('xjChatSuggestions');
    if (suggestions) suggestions.style.display = 'none';
    messagesEl.classList.remove('empty');

    // 用户消息
    const userMsg = { role: 'user', content: text, timestamp: Date.now() };
    messages.push(userMsg);
    appendMessage('user', text, userMsg.timestamp);
    inputEl.value = '';
    autoResize();
    sendBtn.disabled = true;

    // 打字指示器
    const typingEl = showTyping();
    isSending = true;

    try {
      const resp = await apiFetch(CHAT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
      });

      typingEl.remove();
      const reply = resp.reply || resp.message || '（无回复）';
      const aiMsg = { role: 'assistant', content: reply, timestamp: Date.now() };
      messages.push(aiMsg);
      appendMessage('assistant', reply, aiMsg.timestamp);
      saveHistory();
    } catch (e) {
      typingEl.remove();
      const errMsg = { role: 'assistant', content: '抱歉，AI 服务暂时不可用：' + e.message, timestamp: Date.now() };
      messages.push(errMsg);
      appendMessage('assistant', errMsg.content, errMsg.timestamp);
    }

    isSending = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }

  /* ---------- 追加消息 ---------- */
  function appendMessage(role, content, timestamp, animate = true) {
    const el = document.createElement('div');
    el.className = 'xj-chat-msg xj-chat-msg-' + role + (animate ? ' xj-chat-msg-in' : '');
    const time = new Date(timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    if (role === 'user') {
      el.innerHTML = `
        <div class="xj-chat-bubble-v2 user">
          <div class="xj-chat-bubble-text">${escapeHtml(content)}</div>
        </div>
      `;
    } else {
      el.innerHTML = `
        <div class="xj-chat-msg-avatar-v2">序</div>
        <div class="xj-chat-bubble-v2 assistant">
          <div class="xj-chat-bubble-text">${formatMarkdown(content)}</div>
        </div>
      `;
    }
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  /* ---------- 打字指示器 ---------- */
  function showTyping() {
    const el = document.createElement('div');
    el.className = 'xj-chat-msg xj-chat-msg-assistant';
    el.innerHTML = `
      <div class="xj-chat-msg-avatar-v2">序</div>
      <div class="xj-chat-bubble-v2 assistant xj-chat-typing-v2">
        <span></span><span></span><span></span>
      </div>
    `;
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
  }

  /* ---------- 工具函数 ---------- */
  function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
    sendBtn.disabled = !inputEl.value.trim();
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  function clearChat() {
    if (!confirm('确定清空当前对话？')) return;
    messages = [];
    saveHistory();
    const suggestions = document.getElementById('xjChatSuggestions');
    if (suggestions) suggestions.style.display = '';
    renderEmptyState();
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function escapeAttr(s) {
    return s.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function formatMarkdown(text) {
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  async function apiFetch(url, opts = {}) {
    const headers = opts.headers || {};
    if (global.__Z_AUTH) headers['Authorization'] = global.__Z_AUTH;
    const r = await fetch(url, { ...opts, headers });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    return d;
  }

  function saveHistory() {
    try {
      localStorage.setItem('xj_chat_history', JSON.stringify(messages.slice(-MAX_HISTORY)));
    } catch (e) { /* ignore */ }
  }

  function loadHistory() {
    try {
      const saved = localStorage.getItem('xj_chat_history');
      if (saved) messages = JSON.parse(saved);
    } catch (e) { messages = []; }
  }

  /* ---------- 导出 ---------- */
  global.xjChat = {
    init: init,
    send: function (text) {
      if (inputEl) { inputEl.value = text; autoResize(); }
      sendMessage();
    },
    clear: clearChat,
    getMessages: () => messages,
    refreshInsight: loadInsightData
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => init('xjChat'));
  } else {
    init('xjChat');
  }
})(window);
