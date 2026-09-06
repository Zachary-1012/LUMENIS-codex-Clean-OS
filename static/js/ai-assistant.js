/* ============================================================
 * ai-assistant.js — 轻量AI助手（ZBC V2.0 AI Task Engine 对接）
 * 右下角浮动按钮 + 展开面板，对接 /api/ai/tasks（Production-Ready）
 * 降级链：Task Engine API → /api/ai/chat → 本地提示
 * 支持：系统问答、快捷指令、上下文感知（当前域）、任务状态展示
 * ============================================================ */
(function () {
  'use strict';

  var STYLE_ID = 'zbc-ai-style';
  var PANEL_ID = 'zbc-ai-panel';
  var BTN_ID = 'zbc-ai-fab';
  var isOpen = false;
  var history = [];
  var isLoading = false;

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var css = [
      '#zbc-ai-fab{position:fixed;bottom:24px;right:24px;z-index:9990;width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,var(--l-accent,#0f766e),var(--l-accent-hover,#14b8a6));border:none;cursor:pointer;box-shadow:0 4px 20px rgba(15,118,110,.4);display:flex;align-items:center;justify-content:center;transition:transform .2s,box-shadow .2s;animation:zbc-ai-fab-in .4s ease}',
      '#zbc-ai-fab:hover{transform:scale(1.08);box-shadow:0 6px 28px rgba(15,118,110,.5)}',
      '#zbc-ai-fab:active{transform:scale(.96)}',
      '#zbc-ai-fab svg{width:26px;height:26px;color:#fff}',
      '#zbc-ai-fab .zbc-ai-pulse{position:absolute;inset:-4px;border-radius:50%;border:2px solid var(--l-accent,#0f766e);opacity:0;animation:zbc-ai-pulse 2s ease-out infinite}',
      '@keyframes zbc-ai-fab-in{from{opacity:0;transform:scale(0) translateY(20px)}to{opacity:1;transform:scale(1) translateY(0)}}',
      '@keyframes zbc-ai-pulse{0%{transform:scale(1);opacity:.6}100%{transform:scale(1.5);opacity:0}}',
      '#zbc-ai-panel{position:fixed;bottom:88px;right:24px;width:380px;max-width:calc(100vw - 32px);height:min(560px,calc(100vh - 120px));background:var(--l-bg,#fff);border:1px solid var(--l-border,#e8e8e8);border-radius:16px;box-shadow:0 16px 48px rgba(0,0,0,.18);z-index:9989;display:none;flex-direction:column;overflow:hidden;animation:zbc-ai-panel-in .25s cubic-bezier(.16,1,.3,1)}',
      '#zbc-ai-panel.is-open{display:flex}',
      '@keyframes zbc-ai-panel-in{from{opacity:0;transform:translateY(16px) scale(.96)}to{opacity:1;transform:none}}',
      '[data-theme="dark"] #zbc-ai-panel{background:var(--d-bg,#0d0d0d);border-color:var(--d-border,#2f2f2f)}',
      '.zbc-ai-head{padding:14px 16px;background:linear-gradient(135deg,var(--l-accent,#0f766e),var(--l-accent-deep,#0d5d56));color:#fff;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}',
      '.zbc-ai-head-title{display:flex;align-items:center;gap:10px}',
      '.zbc-ai-head-avatar{width:32px;height:32px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:16px}',
      '.zbc-ai-head-text h3{font-size:14px;font-weight:600;margin:0}',
      '.zbc-ai-head-text span{font-size:11px;opacity:.8}',
      '.zbc-ai-head-close{background:none;border:none;color:#fff;cursor:pointer;font-size:18px;padding:4px 8px;border-radius:6px;opacity:.8}',
      '.zbc-ai-head-close:hover{opacity:1;background:rgba(255,255,255,.15)}',
      '.zbc-ai-context{padding:6px 16px;background:var(--l-bg-secondary,#f7f7f8);font-size:11px;color:var(--l-text-tertiary,#9ca3af);border-bottom:1px solid var(--l-border-light,#f0f0f0);flex-shrink:0}',
      '[data-theme="dark"] .zbc-ai-context{background:var(--d-bg-secondary,#141414);border-color:var(--d-border-light,#262626)}',
      '.zbc-ai-messages{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:12px}',
      '.zbc-ai-msg{max-width:85%;padding:10px 14px;border-radius:12px;font-size:13px;line-height:1.6;word-break:break-word;animation:zbc-ai-msg-in .2s ease;white-space:pre-wrap}',
      '@keyframes zbc-ai-msg-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}',
      '.zbc-ai-msg--user{align-self:flex-end;background:var(--l-accent,#0f766e);color:#fff;border-bottom-right-radius:4px}',
      '.zbc-ai-msg--ai{align-self:flex-start;background:var(--l-bg-secondary,#f7f7f8);color:var(--l-text,#0d0d0d);border-bottom-left-radius:4px}',
      '[data-theme="dark"] .zbc-ai-msg--ai{background:var(--d-card,#1f1f1f);color:var(--d-text,#f5f5f5)}',
      '.zbc-ai-msg--error{background:var(--l-danger,#dc2626);color:#fff}',
      '.zbc-ai-msg--task{background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.15);font-size:11px;color:var(--l-text-secondary,#6B7280)}',
      '.zbc-ai-typing{display:inline-flex;gap:4px;align-items:center;padding:4px 0}',
      '.zbc-ai-typing span{width:6px;height:6px;border-radius:50%;background:var(--l-text-tertiary,#9ca3af);animation:zbc-ai-typing 1.2s infinite}',
      '.zbc-ai-typing span:nth-child(2){animation-delay:.2s}',
      '.zbc-ai-typing span:nth-child(3){animation-delay:.4s}',
      '@keyframes zbc-ai-typing{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-4px);opacity:1}}',
      '.zbc-ai-quick{padding:8px 16px;border-top:1px solid var(--l-border-light,#f0f0f0);flex-shrink:0}',
      '[data-theme="dark"] .zbc-ai-quick{border-color:var(--d-border-light,#262626)}',
      '.zbc-ai-quick-label{font-size:10px;color:var(--l-text-tertiary,#9ca3af);margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em}',
      '.zbc-ai-quick-chips{display:flex;flex-wrap:wrap;gap:6px}',
      '.zbc-ai-chip{padding:5px 10px;border:1px solid var(--l-border,#e8e8e8);border-radius:14px;background:var(--l-bg,#fff);font-size:11px;color:var(--l-text-secondary,#6b7280);cursor:pointer;transition:all .15s;font-family:inherit}',
      '.zbc-ai-chip:hover{border-color:var(--l-accent,#0f766e);color:var(--l-accent,#0f766e);background:rgba(15,118,110,.05)}',
      '[data-theme="dark"] .zbc-ai-chip{background:var(--d-bg,#0d0d0d);border-color:var(--d-border,#2f2f2f);color:var(--d-text-secondary,#a1a1aa)}',
      '.zbc-ai-input-wrap{padding:12px 16px;border-top:1px solid var(--l-border-light,#f0f0f0);display:flex;gap:8px;flex-shrink:0}',
      '[data-theme="dark"] .zbc-ai-input-wrap{border-color:var(--d-border-light,#262626)}',
      '.zbc-ai-input{flex:1;padding:9px 14px;border:1px solid var(--l-border,#e8e8e8);border-radius:20px;background:var(--l-bg-secondary,#f7f7f8);font-size:13px;color:var(--l-text,#0d0d0d);outline:none;font-family:inherit;transition:border-color .15s}',
      '.zbc-ai-input:focus{border-color:var(--l-accent,#0f766e);background:var(--l-bg,#fff)}',
      '[data-theme="dark"] .zbc-ai-input{background:var(--d-bg-secondary,#141414);border-color:var(--d-border,#2f2f2f);color:var(--d-text,#f5f5f5)}',
      '[data-theme="dark"] .zbc-ai-input:focus{background:var(--d-bg,#0d0d0d)}',
      '.zbc-ai-send{width:36px;height:36px;border-radius:50%;background:var(--l-accent,#0f766e);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#fff;transition:background .15s,transform .1s;flex-shrink:0}',
      '.zbc-ai-send:hover{background:var(--l-accent-hover,#14b8a6)}',
      '.zbc-ai-send:active{transform:scale(.92)}',
      '.zbc-ai-send:disabled{opacity:.4;cursor:not-allowed}',
      '.zbc-ai-send svg{width:16px;height:16px}',
      '.zbc-content{padding-right:88px!important;padding-bottom:88px!important}',
      '@media(max-width:768px){.zbc-content{padding-right:70px!important;padding-bottom:130px!important}#zbc-ai-fab{bottom:72px!important}}',
      '@media(max-width:600px){#zbc-ai-panel{right:12px;left:12px;width:auto;bottom:130px;height:calc(100vh - 150px)}#zbc-ai-fab{bottom:72px!important;right:16px;width:46px;height:46px}}'
    ].join('');
    var st = document.createElement('style');
    st.id = STYLE_ID;
    st.textContent = css;
    document.head.appendChild(st);
  }

  function getCurrentDomain() {
    return document.body.getAttribute('data-domain') || 'cth';
  }

  function getDomainLabel() {
    var d = getCurrentDomain();
    return { zbmp: 'ZBMP 品牌智能', cth: 'CTH 太古汇情报', system: 'SYSTEM 运行控制' }[d] || d.toUpperCase();
  }

  function getQuickCommands() {
    var domain = getCurrentDomain();
    var base = [
      { label: '系统状态', cmd: '当前系统运行状态如何？各模块是否正常？' },
      { label: '数据概览', cmd: '今天采集了多少条数据？舆情概览是什么？' },
      { label: '风险摘要', cmd: '当前有哪些高风险事件？需要关注什么？' }
    ];
    if (domain === 'cth') {
      base.push({ label: '太古汇动态', cmd: '广州太古汇最近有什么舆情动态？' });
      base.push({ label: '负面待审', cmd: '有哪些负面笔记待确认？' });
    } else if (domain === 'zbmp') {
      base.push({ label: '品牌分析', cmd: '当前品牌传播情况如何？有哪些竞品动态？' });
      base.push({ label: '内容建议', cmd: '基于当前数据，有什么内容营销建议？' });
    } else {
      base.push({ label: '架构状态', cmd: '系统5层架构各层状态如何？' });
      base.push({ label: '采集器', cmd: '采集器运行状态？最近采集情况？' });
    }
    return base;
  }

  function buildFAB() {
    var btn = document.createElement('button');
    btn.id = BTN_ID;
    btn.setAttribute('aria-label', 'AI 助手');
    btn.title = 'AI 助手（Ctrl+J）';
    btn.innerHTML = '<span class="zbc-ai-pulse"></span>' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M12 2a4 4 0 0 1 4 4v1a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/>' +
      '<path d="M8 12a4 4 0 0 0-4 4v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2a4 4 0 0 0-4-4"/>' +
      '<circle cx="9" cy="16" r="1"/><circle cx="15" cy="16" r="1"/></svg>';
    btn.addEventListener('click', toggle);
    document.body.appendChild(btn);
    return btn;
  }

  function buildPanel() {
    var panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'AI 助手');

    var quickCmds = getQuickCommands();
    var chipsHtml = quickCmds.map(function (c) {
      return '<button class="zbc-ai-chip" data-cmd="' + c.cmd.replace(/"/g, '&quot;') + '">' + c.label + '</button>';
    }).join('');

    panel.innerHTML =
      '<div class="zbc-ai-head">' +
      '<div class="zbc-ai-head-title">' +
      '<div class="zbc-ai-head-avatar">◆</div>' +
      '<div class="zbc-ai-head-text"><h3>序境 AI 助手</h3><span>Task Engine · 数据检索 · 风险分析</span></div></div>' +
      '<button class="zbc-ai-head-close" id="zbc-ai-close" aria-label="关闭">×</button></div>' +
      '<div class="zbc-ai-context">当前上下文：' + getDomainLabel() + ' 域 · AI Task Engine V1.0</div>' +
      '<div class="zbc-ai-messages" id="zbc-ai-messages">' +
      '<div class="zbc-ai-msg zbc-ai-msg--ai">你好！我是序境 AI 助手，已接入 AI Task Engine（Parser→Intent→Agent→Skill→Permission→Execution→Evidence→Verification→Trace）。当前在 ' + getDomainLabel() + ' 域，有什么可以帮你的？</div></div>' +
      '<div class="zbc-ai-quick"><div class="zbc-ai-quick-label">快捷指令</div><div class="zbc-ai-quick-chips">' + chipsHtml + '</div></div>' +
      '<div class="zbc-ai-input-wrap">' +
      '<input type="text" class="zbc-ai-input" id="zbc-ai-input" placeholder="输入问题或任务…" autocomplete="off">' +
      '<button class="zbc-ai-send" id="zbc-ai-send" aria-label="发送">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></button></div>';

    document.body.appendChild(panel);

    panel.querySelector('#zbc-ai-close').addEventListener('click', toggle);
    panel.querySelector('#zbc-ai-send').addEventListener('click', sendMessage);
    var input = panel.querySelector('#zbc-ai-input');
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });

    panel.querySelectorAll('.zbc-ai-chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        var cmd = chip.getAttribute('data-cmd');
        if (cmd) {
          input.value = cmd;
          sendMessage();
        }
      });
    });

    return panel;
  }

  function addMessage(text, type) {
    var container = document.getElementById('zbc-ai-messages');
    if (!container) return;
    var msg = document.createElement('div');
    msg.className = 'zbc-ai-msg zbc-ai-msg--' + type;
    msg.textContent = text;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
  }

  function addTyping() {
    var container = document.getElementById('zbc-ai-messages');
    if (!container) return;
    var msg = document.createElement('div');
    msg.className = 'zbc-ai-msg zbc-ai-msg--ai';
    msg.id = 'zbc-ai-typing-msg';
    msg.innerHTML = '<div class="zbc-ai-typing"><span></span><span></span><span></span></div>';
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
  }

  function removeTyping() {
    var t = document.getElementById('zbc-ai-typing-msg');
    if (t) t.remove();
  }

  function getFetchFn() {
    return (typeof LUMENIS !== 'undefined' && LUMENIS.fetch) ? LUMENIS.fetch : fetch;
  }

  function extractTaskReply(task) {
    if (!task) return '';
    if (task.status === 'succeeded' && task.result_json) {
      try {
        var ro = typeof task.result_json === 'string' ? JSON.parse(task.result_json) : task.result_json;
        if (ro.output) {
          if (ro.output.ai_summary) return ro.output.ai_summary;
          if (ro.output.ai_analysis) return JSON.stringify(ro.output.ai_analysis, null, 2);
          if (ro.output.note) return ro.output.note;
          return JSON.stringify(ro.output, null, 2);
        }
        if (ro.verification && ro.verification.result_summary) return ro.verification.result_summary;
        return JSON.stringify(ro, null, 2);
      } catch (e) { return String(task.result_json); }
    }
    if (task.status === 'awaiting_approval') {
      return '⚠ 此任务需要人工审批：' + (task.risk_reason || '高风险操作') + '\n请前往 AI Gateway 页面（/system/ai）审批后执行。\n任务ID: ' + task.task_id;
    }
    if (task.status === 'failed') {
      return '任务执行失败：' + (task.error || '未知错误') + '\n任务ID: ' + task.task_id;
    }
    if (task.status === 'cancelled') return '任务已取消。';
    if (task.status === 'dlq') return '任务进入死信队列（重试耗尽）：' + (task.error || '') + '\n请人工介入处理。';
    return '任务状态：' + task.status + '（任务ID: ' + task.task_id + '）';
  }

  function sendMessage() {
    if (isLoading) return;
    var input = document.getElementById('zbc-ai-input');
    var text = input ? input.value.trim() : '';
    if (!text) return;

    addMessage(text, 'user');
    input.value = '';
    isLoading = true;
    updateSendButton();
    history.push({ role: 'user', content: text });
    addTyping();

    var domain = getCurrentDomain();
    var fetchFn = getFetchFn();

    // 主链路：AI Task Engine API（Production-Ready）
    var taskPayload = {
      input: '[' + domain.toUpperCase() + '域] ' + text,
      context: { current_page: window.location.pathname, domain: domain },
      created_by: 'ai_assistant'
    };

    fetchFn('/api/ai/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(taskPayload)
    }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (d) {
      if (!d || !d.ok || !d.task) throw new Error('task create failed');
      var taskId = d.task.task_id;
      addMessage('任务已创建：' + taskId + '，正在执行…', 'task');
      return fetchFn('/api/ai/tasks/' + taskId + '/run', { method: 'POST' })
        .then(function (r2) { return r2.json(); })
        .then(function (runResult) {
          removeTyping();
          if (runResult && runResult.ok && runResult.task) {
            var reply = extractTaskReply(runResult.task);
            addMessage(reply, 'ai');
            history.push({ role: 'assistant', content: reply });
          } else {
            throw new Error('task run failed');
          }
        });
    }).catch(function (err) {
      removeTyping();
      // 降级链路1：旧 /api/ai/chat 接口
      var legacyPayload = {
        message: '[' + domain.toUpperCase() + '域] ' + text,
        history: history.slice(-10)
      };
      fetchFn('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(legacyPayload)
      }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function (data) {
        if (data && data.ok && data.reply) {
          addMessage(data.reply, 'ai');
          history.push({ role: 'assistant', content: data.reply });
        } else {
          addMessage('抱歉，AI 暂时无法回答。' + (data && data.error ? '错误：' + data.error : ''), 'error');
        }
      }).catch(function (err2) {
        // 降级链路2：本地提示
        addMessage('连接失败（Task Engine + Chat API 均不可用）：' + (err2.message || '未知错误') + '。请检查 8201 服务是否运行。', 'error');
      });
    }).finally(function () {
      isLoading = false;
      updateSendButton();
    });
  }

  function updateSendButton() {
    var btn = document.getElementById('zbc-ai-send');
    if (btn) btn.disabled = isLoading;
  }

  function toggle() {
    var panel = document.getElementById(PANEL_ID);
    if (!panel) panel = buildPanel();
    isOpen = !isOpen;
    panel.classList.toggle('is-open', isOpen);
    if (isOpen) {
      setTimeout(function () {
        var input = document.getElementById('zbc-ai-input');
        if (input) input.focus();
      }, 100);
    }
  }

  function boot() {
    injectStyle();
    buildFAB();
    window.ZBCAIAssistant = {
      toggle: toggle,
      open: function () { if (!isOpen) toggle(); },
      close: function () { if (isOpen) toggle(); }
    };
    console.log('[ai-assistant] AI助手已加载（对接 AI Task Engine，右下角浮动按钮，Ctrl+J）');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
