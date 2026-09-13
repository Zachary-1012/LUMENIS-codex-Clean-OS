/* ============================================================
 * ai-assistant.js — 轻量AI助手（ZBC V2.0 AI Task Engine 对接）
 * 右下角浮动按钮 + 展开面板，对接 /api/ai/tasks（Production-Ready）
 * 降级链：Task Engine API → /api/ai/chat → 本地提示
 * 支持：系统问答、快捷指令、上下文感知（当前域）、任务状态展示
 * V2.1 智谱UI升级：打字机流式输出 / 消息复制操作栏 / AI模块深色模式 / 多模态附件预览
 * 动效统一走 ZBCMotion/LDMotion，不单独写 @keyframes
 * ============================================================ */
(function () {
  'use strict';

  var STYLE_ID = 'zbc-ai-style';
  var PANEL_ID = 'zbc-ai-panel';
  var BTN_ID = 'zbc-ai-fab';
  var isOpen = false;
  var history = [];
  var isLoading = false;
  var _typeTimer = null;
  var _cursorTimer = null;
  var _attachedFiles = [];
  var _dark = false;

  function _reduced() {
    return (window.ZBCMotion && window.ZBCMotion._reduced) || (window.LDMotion && window.LDMotion._reduced) || false;
  }

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var css = [
      '#zbc-ai-fab{position:fixed;bottom:24px;right:24px;z-index:9990;width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,var(--ai-accent,#2f6bff),#6366f1);border:none;cursor:pointer;box-shadow:0 4px 20px rgba(47,107,255,.4);display:flex;align-items:center;justify-content:center;transition:transform .2s,box-shadow .2s}',
      '#zbc-ai-fab:hover{transform:scale(1.08);box-shadow:0 6px 28px rgba(47,107,255,.5)}',
      '#zbc-ai-fab:active{transform:scale(.96)}',
      '#zbc-ai-fab svg{width:26px;height:26px;color:#fff}',
      '#zbc-ai-panel{position:fixed;bottom:88px;right:24px;width:380px;max-width:calc(100vw - 32px);height:min(560px,calc(100vh - 120px));background:var(--l-bg,#fff);border:1px solid var(--l-border,#e8e8e8);border-radius:20px;box-shadow:0 16px 48px rgba(0,0,0,.18);z-index:9989;display:none;flex-direction:column;overflow:hidden}',
      '#zbc-ai-panel.is-open{display:flex}',
      '#zbc-ai-panel[data-ai-theme="dark"]{background:#1a1a1e;border-color:rgba(255,255,255,.08);color:#e8ecf1}',
      '.zbc-ai-head{padding:14px 16px;background:linear-gradient(135deg,var(--ai-accent,#2f6bff),#6366f1);color:#fff;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-head{background:linear-gradient(135deg,#1e3a8a,#2f6bff)}',
      '.zbc-ai-head-title{display:flex;align-items:center;gap:10px}',
      '.zbc-ai-head-avatar{width:32px;height:32px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:16px}',
      '.zbc-ai-head-text h3{font-size:14px;font-weight:600;margin:0}',
      '.zbc-ai-head-text span{font-size:11px;opacity:.8}',
      '.zbc-ai-head-actions{display:flex;align-items:center;gap:4px}',
      '.zbc-ai-head-btn{background:none;border:none;color:#fff;cursor:pointer;font-size:14px;padding:4px 8px;border-radius:8px;opacity:.8;transition:all .15s}',
      '.zbc-ai-head-btn:hover{opacity:1;background:rgba(255,255,255,.15)}',
      '.zbc-ai-context{padding:6px 16px;background:var(--l-bg-secondary,#f7f7f8);font-size:11px;color:var(--l-text-tertiary,#9ca3af);border-bottom:1px solid var(--l-border-light,#f0f0f0);flex-shrink:0}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-context{background:#202026;border-color:rgba(255,255,255,.08);color:#9aa3b2}',
      '.zbc-ai-messages{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:12px}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-messages{background:#1a1a1e}',
      '.zbc-ai-msg{max-width:85%;padding:10px 14px;border-radius:16px;font-size:13px;line-height:1.6;word-break:break-word;white-space:pre-wrap;position:relative}',
      '.zbc-ai-msg--user{align-self:flex-end;background:linear-gradient(135deg,var(--ai-accent,#2f6bff),#6366f1);color:#fff;border-bottom-right-radius:5px;box-shadow:0 4px 12px rgba(47,107,255,.25)}',
      '.zbc-ai-msg--ai{align-self:flex-start;background:var(--l-bg-secondary,#f7f7f8);color:var(--l-text,#0d0d0d);border-bottom-left-radius:5px;border:1px solid var(--l-border-light,#f0f0f0)}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-msg--ai{background:#25252b;color:#e8ecf1;border-color:rgba(255,255,255,.08)}',
      '.zbc-ai-msg--error{background:var(--l-danger,#dc2626);color:#fff}',
      '.zbc-ai-msg--task{background:rgba(47,107,255,0.06);border:1px solid rgba(47,107,255,0.15);font-size:11px;color:var(--l-text-secondary,#6B7280)}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-msg--task{background:rgba(47,107,255,0.12);color:#9aa3b2}',
      /* 打字机光标（JS切换可见性，无CSS animation） */
      '.zbc-ai-cursor{display:inline-block;width:2px;height:1em;background:var(--ai-accent,#2f6bff);margin-left:2px;vertical-align:text-bottom;border-radius:1px}',
      '.zbc-ai-cursor.is-hidden{opacity:0}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-cursor{background:#60a5fa}',
      /* 消息操作栏 */
      '.zbc-ai-msg-actions{display:flex;gap:4px;margin-top:6px;opacity:0;transition:opacity .15s ease}',
      '.zbc-ai-msg--ai:hover .zbc-ai-msg-actions{opacity:1}',
      '.zbc-ai-msg-action{display:inline-flex;align-items:center;gap:3px;padding:3px 8px;border-radius:999px;border:none;background:transparent;color:var(--l-text-tertiary,#9ca3af);font-size:10px;font-weight:600;cursor:pointer;transition:all .15s;font-family:inherit}',
      '.zbc-ai-msg-action:hover{background:rgba(47,107,255,.1);color:var(--ai-accent,#2f6bff)}',
      '.zbc-ai-msg-action.is-success{color:#10b981}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-msg-action{color:#6b7280}',
      '.zbc-ai-typing{display:inline-flex;gap:4px;align-items:center;padding:4px 0}',
      '.zbc-ai-typing span{width:6px;height:6px;border-radius:50%;background:var(--ai-accent,#2f6bff)}',
      '.zbc-ai-quick{padding:8px 16px;border-top:1px solid var(--l-border-light,#f0f0f0);flex-shrink:0}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-quick{border-color:rgba(255,255,255,.08);background:#1a1a1e}',
      '.zbc-ai-quick-label{font-size:10px;color:var(--l-text-tertiary,#9ca3af);margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-quick-label{color:#6b7280}',
      '.zbc-ai-quick-chips{display:flex;flex-wrap:wrap;gap:6px}',
      '.zbc-ai-chip{padding:5px 10px;border:1px solid var(--l-border,#e8e8e8);border-radius:14px;background:var(--l-bg,#fff);font-size:11px;color:var(--l-text-secondary,#6b7280);cursor:pointer;transition:all .15s;font-family:inherit}',
      '.zbc-ai-chip:hover{border-color:var(--ai-accent,#2f6bff);color:var(--ai-accent,#2f6bff);background:rgba(47,107,255,.05)}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-chip{background:#25252b;border-color:rgba(255,255,255,.1);color:#9aa3b2}',
      /* 多模态附件预览 */
      '.zbc-ai-attach-preview{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 8px}',
      '.zbc-ai-attach-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 8px 4px 4px;border-radius:10px;background:var(--l-bg-secondary,#f7f7f8);border:1px solid var(--l-border-light,#f0f0f0);font-size:10px;max-width:160px}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-attach-chip{background:#202026;border-color:rgba(255,255,255,.08);color:#9aa3b2}',
      '.zbc-ai-attach-chip__thumb{width:22px;height:22px;border-radius:6px;background:rgba(47,107,255,.1);color:var(--ai-accent,#2f6bff);display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;flex-shrink:0;overflow:hidden}',
      '.zbc-ai-attach-chip__thumb img{width:100%;height:100%;object-fit:cover}',
      '.zbc-ai-attach-chip__name{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}',
      '.zbc-ai-attach-chip__remove{background:none;border:none;cursor:pointer;color:var(--l-text-tertiary,#9ca3af);font-size:13px;line-height:1;padding:0 2px;border-radius:3px;flex-shrink:0}',
      '.zbc-ai-attach-chip__remove:hover{color:#dc2626}',
      '.zbc-ai-input-wrap{padding:10px 16px;border-top:1px solid var(--l-border-light,#f0f0f0);display:flex;gap:8px;align-items:flex-end;flex-shrink:0}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-input-wrap{border-color:rgba(255,255,255,.08);background:#1a1a1e}',
      '.zbc-ai-input{flex:1;padding:9px 14px;border:1px solid var(--l-border,#e8e8e8);border-radius:18px;background:var(--l-bg-secondary,#f7f7f8);font-size:13px;color:var(--l-text,#0d0d0d);outline:none;font-family:inherit;transition:border-color .15s;resize:none;max-height:80px;min-height:20px}',
      '.zbc-ai-input:focus{border-color:var(--ai-accent,#2f6bff);background:var(--l-bg,#fff)}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-input{background:#202026;border-color:rgba(255,255,255,.1);color:#e8ecf1}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-input:focus{background:#25252b}',
      '.zbc-ai-input-tools{display:flex;flex-direction:column;gap:4px;flex-shrink:0}',
      '.zbc-ai-attach-btn{width:32px;height:32px;border-radius:50%;border:1px solid var(--l-border,#e8e8e8);background:var(--l-bg,#fff);cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--l-text-secondary,#6b7280);transition:all .15s;padding:0}',
      '.zbc-ai-attach-btn:hover{border-color:var(--ai-accent,#2f6bff);color:var(--ai-accent,#2f6bff)}',
      '#zbc-ai-panel[data-ai-theme="dark"] .zbc-ai-attach-btn{background:#25252b;border-color:rgba(255,255,255,.1);color:#9aa3b2}',
      '.zbc-ai-attach-btn input{display:none}',
      '.zbc-ai-send{width:36px;height:36px;border-radius:50%;background:var(--ai-accent,#2f6bff);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#fff;transition:background .15s,transform .1s;flex-shrink:0}',
      '.zbc-ai-send:hover{background:#4a80ff}',
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
    return { zbmp: 'ZBMP 序境·品牌市场', cth: '序境·商业运营', system: 'SYSTEM 运行控制' }[d] || d.toUpperCase();
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
    btn.innerHTML =
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
    panel.setAttribute('data-ai-theme', 'light');

    var quickCmds = getQuickCommands();
    var chipsHtml = quickCmds.map(function (c) {
      return '<button class="zbc-ai-chip" data-cmd="' + c.cmd.replace(/"/g, '&quot;') + '">' + c.label + '</button>';
    }).join('');

    panel.innerHTML =
      '<div class="zbc-ai-head">' +
      '<div class="zbc-ai-head-title">' +
      '<div class="zbc-ai-head-avatar">◆</div>' +
      '<div class="zbc-ai-head-text"><h3>序境 AI 助手</h3><span>Task Engine · 数据检索 · 风险分析</span></div></div>' +
      '<div class="zbc-ai-head-actions">' +
      '<button class="zbc-ai-head-btn" id="zbc-ai-theme" title="切换深色/浅色" aria-label="切换主题">🌙</button>' +
      '<button class="zbc-ai-head-close zbc-ai-head-btn" id="zbc-ai-close" aria-label="关闭">×</button></div></div>' +
      '<div class="zbc-ai-context">当前上下文：' + getDomainLabel() + ' 域 · AI Task Engine V1.0</div>' +
      '<div class="zbc-ai-messages" id="zbc-ai-messages">' +
      '<div class="zbc-ai-msg zbc-ai-msg--ai">你好！我是序境 AI 助手，已接入 AI Task Engine（Parser→Intent→Agent→Skill→Permission→Execution→Evidence→Verification→Trace）。当前在 ' + getDomainLabel() + ' 域，有什么可以帮你的？</div></div>' +
      '<div class="zbc-ai-attach-preview" id="zbc-ai-attach-preview" style="display:none;"></div>' +
      '<div class="zbc-ai-quick"><div class="zbc-ai-quick-label">快捷指令</div><div class="zbc-ai-quick-chips">' + chipsHtml + '</div></div>' +
      '<div class="zbc-ai-input-wrap">' +
      '<button class="zbc-ai-attach-btn" title="附件（预览）">' +
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>' +
      '<input type="file" id="zbc-ai-file-input" multiple accept="image/*,.pdf,.txt,.docx"></button>' +
      '<textarea class="zbc-ai-input" id="zbc-ai-input" placeholder="输入问题或任务…" rows="1"></textarea>' +
      '<button class="zbc-ai-send" id="zbc-ai-send" aria-label="发送">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></button></div>';

    document.body.appendChild(panel);

    panel.querySelector('#zbc-ai-close').addEventListener('click', toggle);
    panel.querySelector('#zbc-ai-theme').addEventListener('click', toggleTheme);
    panel.querySelector('#zbc-ai-send').addEventListener('click', sendMessage);
    var input = panel.querySelector('#zbc-ai-input');
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    input.addEventListener('input', function () {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 80) + 'px';
    });

    panel.querySelectorAll('.zbc-ai-chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        var cmd = chip.getAttribute('data-cmd');
        if (cmd) { input.value = cmd; sendMessage(); }
      });
    });

    // 多模态附件
    var fileInput = panel.querySelector('#zbc-ai-file-input');
    fileInput.addEventListener('change', function (e) {
      var files = Array.prototype.slice.call(e.target.files || []);
      files.forEach(function (f) {
        if (f.type && f.type.indexOf('image/') === 0) {
          try { f.previewUrl = URL.createObjectURL(f); } catch (err) {}
        }
        _attachedFiles.push(f);
      });
      renderAttachPreview();
      fileInput.value = '';
    });

    // 恢复主题
    try {
      if (localStorage.getItem('ai_assistant_theme') === 'dark') {
        _dark = true;
        panel.setAttribute('data-ai-theme', 'dark');
        panel.querySelector('#zbc-ai-theme').textContent = '☀️';
      }
    } catch (e) {}

    return panel;
  }

  function toggleTheme() {
    _dark = !_dark;
    var panel = document.getElementById(PANEL_ID);
    panel.setAttribute('data-ai-theme', _dark ? 'dark' : 'light');
    panel.querySelector('#zbc-ai-theme').textContent = _dark ? '☀️' : '🌙';
    try { localStorage.setItem('ai_assistant_theme', _dark ? 'dark' : 'light'); } catch (e) {}
  }

  function renderAttachPreview() {
    var wrap = document.getElementById('zbc-ai-attach-preview');
    if (!wrap) return;
    if (!_attachedFiles.length) { wrap.style.display = 'none'; wrap.innerHTML = ''; return; }
    wrap.style.display = '';
    wrap.innerHTML = _attachedFiles.map(function (f, i) {
      var ext = (f.name.split('.').pop() || 'FILE').substring(0, 3).toUpperCase();
      var thumb = f.previewUrl ? '<div class="zbc-ai-attach-chip__thumb"><img src="' + f.previewUrl + '" alt=""></div>'
        : '<div class="zbc-ai-attach-chip__thumb">' + ext + '</div>';
      return '<div class="zbc-ai-attach-chip">' + thumb +
        '<span class="zbc-ai-attach-chip__name" title="' + escHtml(f.name) + '">' + escHtml(truncStr(f.name, 14)) + '</span>' +
        '<button class="zbc-ai-attach-chip__remove" data-idx="' + i + '">×</button></div>';
    }).join('');
    wrap.querySelectorAll('.zbc-ai-attach-chip__remove').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(btn.getAttribute('data-idx'), 10);
        var f = _attachedFiles[idx];
        if (f && f.previewUrl) { try { URL.revokeObjectURL(f.previewUrl); } catch (e) {} }
        _attachedFiles.splice(idx, 1);
        renderAttachPreview();
      });
    });
  }

  function escHtml(s) {
    var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML;
  }
  function truncStr(s, n) { s = String(s || ''); return s.length > n ? s.substring(0, n) + '…' : s; }

  function addMessage(text, type) {
    var container = document.getElementById('zbc-ai-messages');
    if (!container) return null;
    var msg = document.createElement('div');
    msg.className = 'zbc-ai-msg zbc-ai-msg--' + type;
    msg.textContent = text;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    // 动效：fade-in via ZBCMotion
    if (window.ZBCMotion && window.ZBCMotion.applyPreset) {
      try { window.ZBCMotion.applyPreset(msg, 'enter'); } catch (e) {}
    }
    return msg;
  }

  /* ---- 打字机流式输出 ---- */
  function typewriter(msgEl, fullText, onDone) {
    if (_typeTimer) { clearInterval(_typeTimer); _typeTimer = null; }
    msgEl.textContent = '';
    var cursor = document.createElement('span');
    cursor.className = 'zbc-ai-cursor';
    msgEl.appendChild(cursor);
    if (_cursorTimer) clearInterval(_cursorTimer);
    _cursorTimer = setInterval(function () { cursor.classList.toggle('is-hidden'); }, 530);

    if (_reduced() || !fullText) {
      msgEl.textContent = fullText || '';
      finishTypewriter(msgEl, cursor, onDone);
      return;
    }
    var idx = 0;
    var speed = Math.max(10, Math.min(35, Math.floor(1400 / Math.max(fullText.length, 1))));
    _typeTimer = setInterval(function () {
      if (idx >= fullText.length) { finishTypewriter(msgEl, cursor, onDone); return; }
      var chunk = fullText.slice(idx, idx + 2);
      idx += 2;
      msgEl.insertBefore(document.createTextNode(chunk), cursor);
      var container = document.getElementById('zbc-ai-messages');
      if (container) container.scrollTop = container.scrollHeight;
    }, speed);
  }

  function finishTypewriter(msgEl, cursor, onDone) {
    if (_typeTimer) { clearInterval(_typeTimer); _typeTimer = null; }
    if (_cursorTimer) { clearInterval(_cursorTimer); _cursorTimer = null; }
    if (cursor && cursor.parentNode) cursor.parentNode.removeChild(cursor);
    // 添加复制操作栏
    addCopyAction(msgEl);
    if (onDone) onDone();
  }

  function addCopyAction(msgEl) {
    var actions = document.createElement('div');
    actions.className = 'zbc-ai-msg-actions';
    actions.innerHTML = '<button class="zbc-ai-msg-action" title="复制">' +
      '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>复制</button>';
    msgEl.appendChild(actions);
    var btn = actions.querySelector('.zbc-ai-msg-action');
    btn.addEventListener('click', function () {
      var text = msgEl.textContent.replace(/复制$/, '').trim();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { flashCopy(btn); }).catch(function () { flashCopy(btn); });
      } else { flashCopy(btn); }
    });
  }

  function flashCopy(btn) {
    var orig = btn.innerHTML;
    btn.classList.add('is-success');
    btn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>已复制';
    setTimeout(function () { btn.classList.remove('is-success'); btn.innerHTML = orig; }, 1500);
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

    // 附件信息附加（UI预览，实际上传后续接入）
    var attachNote = _attachedFiles.length ? ' [附件:' + _attachedFiles.map(function (f) { return f.name; }).join(',') + ']' : '';
    _attachedFiles = [];
    renderAttachPreview();

    addMessage(text, 'user');
    input.value = '';
    input.style.height = 'auto';
    isLoading = true;
    updateSendButton();
    history.push({ role: 'user', content: text });
    addTyping();

    var domain = getCurrentDomain();
    var fetchFn = getFetchFn();

    // 主链路：AI Task Engine API（Production-Ready）
    var taskPayload = {
      input: '[' + domain.toUpperCase() + '域] ' + text + attachNote,
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
            var aiMsg = addMessage('', 'ai');
            typewriter(aiMsg, reply);
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
          var aiMsg = addMessage('', 'ai');
          typewriter(aiMsg, data.reply);
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
    // Ctrl+J 快捷键
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'j') { e.preventDefault(); toggle(); }
    });
    window.ZBCAIAssistant = {
      toggle: toggle,
      open: function () { if (!isOpen) toggle(); },
      close: function () { if (isOpen) toggle(); }
    };
    console.log('[ai-assistant] AI助手已加载 V2.1（智谱UI：打字机/复制/深色/多模态预览，对接 AI Task Engine，Ctrl+J）');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();

