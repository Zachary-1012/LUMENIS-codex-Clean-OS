/* ============================================================
 * 序境 Xujing · AI 聊天界面 v1.0
 * ChatGPT 风格对话，独立模块，不修改 app.js
 * 调用 /api/ai/test 接口，支持消息历史、打字指示器、建议问题
 * ============================================================ */
(function (global) {
  'use strict';

  const CHAT_API = '/api/ai/test';
  const MAX_HISTORY = 30;

  // 消息历史
  let messages = [];
  let isSending = false;
  let chatContainer = null;
  let messagesEl = null;
  let inputEl = null;
  let sendBtn = null;
  let statusEl = null;

  // 建议问题（空状态显示）
  const SUGGESTIONS = [
    { icon: '📊', text: '今日舆情概览', q: '今天的舆情情况怎么样？' },
    { icon: '⚠️', text: '高风险内容分析', q: '分析当前高风险内容' },
    { icon: '📈', text: '近7天趋势', q: '近7天舆情趋势如何？' },
    { icon: '🏷️', text: '品牌分布', q: '当前监测品牌分布情况' }
  ];

  /* ---------- 初始化 ---------- */
  function init(containerId) {
    chatContainer = document.getElementById(containerId);
    if (!chatContainer) {
      // 自动创建容器
      chatContainer = document.createElement('div');
      chatContainer.id = containerId || 'xjChat';
      chatContainer.className = 'xj-chat-container';
      const content = document.querySelector('.content');
      if (content) content.insertBefore(chatContainer, content.firstChild);
    }
    render();
    loadHistory();
  }

  /* ---------- 渲染聊天界面 ---------- */
  function render() {
    chatContainer.innerHTML = `
      <div class="xj-chat">
        <div class="xj-chat-header">
          <div class="xj-chat-title">
            <span class="xj-chat-avatar">序</span>
            <div>
              <div class="xj-chat-name">序境 AI</div>
              <div class="xj-chat-status"><span class="xj-dot xj-dot-ok xj-dot-pulse"></span><span class="xj-chat-status-text">在线 · 本地规则引擎</span></div>
            </div>
          </div>
          <div class="xj-chat-actions">
            <button class="xj-chat-icon-btn" id="xjChatClear" title="清空对话">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
        <div class="xj-chat-messages" id="xjChatMessages"></div>
        <div class="xj-chat-input-area">
          <div class="xj-chat-input-wrap">
            <textarea class="xj-chat-input" id="xjChatInput" placeholder="问序境任何问题…（Enter 发送，Shift+Enter 换行）" rows="1"></textarea>
            <button class="xj-chat-send" id="xjChatSend" disabled>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/></svg>
            </button>
          </div>
          <div class="xj-chat-hint">序境 AI · 数据来自本地采集与分析管线 · 生成内容仅供参考</div>
        </div>
      </div>
    `;

    messagesEl = document.getElementById('xjChatMessages');
    inputEl = document.getElementById('xjChatInput');
    sendBtn = document.getElementById('xjChatSend');
    statusEl = chatContainer.querySelector('.xj-chat-status-text');

    // 事件绑定
    inputEl.addEventListener('input', autoResize);
    inputEl.addEventListener('keydown', handleKeydown);
    sendBtn.addEventListener('click', sendMessage);
    document.getElementById('xjChatClear').addEventListener('click', clearChat);

    // 渲染空状态或历史
    if (messages.length === 0) {
      renderEmptyState();
    } else {
      messages.forEach(m => appendMessage(m.role, m.content, m.timestamp, false));
    }
  }

  /* ---------- 空状态（ChatGPT 风格欢迎页） ---------- */
  function renderEmptyState() {
    messagesEl.innerHTML = `
      <div class="xj-chat-empty">
        <div class="xj-chat-empty-avatar">序</div>
        <h2 class="xj-chat-empty-title">你好，我是序境 AI</h2>
        <p class="xj-chat-empty-sub">基于本地采集与分析管线，为你提供舆情、风险、品牌和 KOS 智能分析</p>
        <div class="xj-chat-suggestions">
          ${SUGGESTIONS.map(s => `
            <button class="xj-chat-suggestion" data-q="${escapeAttr(s.q)}">
              <span class="xj-chat-suggestion-icon">${s.icon}</span>
              <span class="xj-chat-suggestion-text">${s.text}</span>
            </button>
          `).join('')}
        </div>
      </div>
    `;
    // 建议问题点击
    messagesEl.querySelectorAll('.xj-chat-suggestion').forEach(btn => {
      btn.addEventListener('click', () => {
        inputEl.value = btn.dataset.q;
        autoResize();
        sendMessage();
      });
    });
  }

  /* ---------- 发送消息 ---------- */
  async function sendMessage() {
    if (isSending) return;
    const text = inputEl.value.trim();
    if (!text) return;

    // 清空空状态
    if (messages.length === 0) {
      messagesEl.innerHTML = '';
    }

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
    updateStatus('思考中…');

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
      updateStatus('在线 · 本地规则引擎');
      saveHistory();
    } catch (e) {
      typingEl.remove();
      const errMsg = { role: 'assistant', content: '抱歉，AI 服务暂时不可用：' + e.message, timestamp: Date.now() };
      messages.push(errMsg);
      appendMessage('assistant', errMsg.content, errMsg.timestamp);
      updateStatus('离线 · 服务不可用');
    }

    isSending = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }

  /* ---------- 追加消息到 DOM ---------- */
  function appendMessage(role, content, timestamp, animate = true) {
    const el = document.createElement('div');
    el.className = 'xj-chat-msg xj-chat-msg-' + role + (animate ? ' xj-chat-msg-in' : '');
    const time = new Date(timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    if (role === 'user') {
      el.innerHTML = `
        <div class="xj-chat-bubble">
          <div class="xj-chat-bubble-text">${escapeHtml(content)}</div>
          <div class="xj-chat-msg-time">${time}</div>
        </div>
        <div class="xj-chat-msg-avatar xj-chat-avatar-user">我</div>
      `;
    } else {
      el.innerHTML = `
        <div class="xj-chat-msg-avatar">序</div>
        <div class="xj-chat-bubble">
          <div class="xj-chat-bubble-text">${formatMarkdown(content)}</div>
          <div class="xj-chat-msg-time">${time}</div>
        </div>
      `;
    }
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  /* ---------- 打字指示器 ---------- */
  function showTyping() {
    const el = document.createElement('div');
    el.className = 'xj-chat-msg xj-chat-msg-assistant xj-chat-typing-wrap';
    el.innerHTML = `
      <div class="xj-chat-msg-avatar">序</div>
      <div class="xj-chat-bubble xj-chat-typing">
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
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
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

  function updateStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function clearChat() {
    if (!confirm('确定清空当前对话？')) return;
    messages = [];
    saveHistory();
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

  // 基础 Markdown 格式化（换行、粗体、代码）
  function formatMarkdown(text) {
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  // 统一 fetch（带 auth）
  async function apiFetch(url, opts) {
    const headers = opts.headers || {};
    if (global.__Z_AUTH) headers['Authorization'] = global.__Z_AUTH;
    const r = await fetch(url, { ...opts, headers });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    return d;
  }

  // 本地存储历史
  function saveHistory() {
    try {
      const toSave = messages.slice(-MAX_HISTORY);
      localStorage.setItem('xj_chat_history', JSON.stringify(toSave));
    } catch (e) { /* 存储失败忽略 */ }
  }

  function loadHistory() {
    try {
      const saved = localStorage.getItem('xj_chat_history');
      if (saved) {
        messages = JSON.parse(saved);
      }
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
    getMessages: () => messages
  };

  // 自动初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => init('xjChat'));
  } else {
    init('xjChat');
  }
})(window);
