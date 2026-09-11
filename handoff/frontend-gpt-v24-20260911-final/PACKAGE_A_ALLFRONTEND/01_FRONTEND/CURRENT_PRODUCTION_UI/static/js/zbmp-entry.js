/**
 * zbmp-entry.js — ZBMP 域身份入口面板
 *
 * 职责：
 * 1. CTH已登录用户点击ZBMP入口/域切换tab时弹出面板
 * 2. 未绑定TOTP：调用 setup 获取二维码，用户扫码后 confirm 绑定
 * 3. 已绑定TOTP：输入6位动态码，调用 verify 获取ZBMP域身份
 * 4. 验证通过后设置 cookie 并导航到 /lumenis/zbmp/overview
 * 5. 支持 URL 参数 ?zbmp-entry=1 自动弹出
 *
 * 依赖：无外部库，纯原生JS。二维码用后端返回的 data URL 直接渲染。
 */
(function (global) {
  'use strict';

  var API_BASE = '/api/system/account';
  var ENTRY_API = '/api/auth/zbmp-entry';
  var PANEL_ID = 'zbmp-entry-panel';
  var OVERLAY_ID = 'zbmp-entry-overlay';

  /* ---------- 面板 HTML 模板（毛玻璃+线性图标+渐变） ---------- */
  var PANEL_HTML = ''
    + '<div id="' + OVERLAY_ID + '" class="zbmp-overlay" style="display:none">'
    + '  <div class="zbmp-modal" role="dialog" aria-modal="true" aria-labelledby="zbmp-modal-title">'
    + '    <button class="zbmp-close" id="zbmp-close-btn" aria-label="关闭">'
    + '      <span class="zbmp-icon" data-zbmp-icon="close"></span>'
    + '    </button>'
    + '    <div class="zbmp-modal-header">'
    + '      <div class="zbmp-modal-logo"><span class="zbmp-icon zbmp-icon--lg" data-zbmp-icon="intelligence"></span></div>'
    + '      <h2 id="zbmp-modal-title" class="zbmp-modal-h2">进入序境·品牌市场域</h2>'
    + '      <p class="zbmp-modal-sub" id="zbmp-modal-sub">动态验证码保护 · 每30秒刷新</p>'
    + '    </div>'
    + '    <div class="zbmp-modal-body" id="zbmp-modal-body">'
    + '    </div>'
    + '  </div>'
    + '</div>';

  /* ---------- 样式注入（Design System V1.1：毛玻璃+大圆角+渐变强调） ---------- */
  var STYLES = ''
    /* Overlay */
    + '.zbmp-overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);'
    + 'display:flex;align-items:center;justify-content:center;z-index:9999;'
    + 'font-family:"Inter","Noto Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}'
    /* Modal - 毛玻璃卡片 */
    + '.zbmp-modal{background:rgba(255,255,255,.72);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);'
    + 'border:1px solid rgba(255,255,255,.45);border-radius:24px;padding:36px 32px 28px;width:440px;max-width:92vw;'
    + 'max-height:88dvh;overflow-y:auto;box-shadow:0 24px 64px rgba(15,118,110,.18),0 8px 24px rgba(0,0,0,.08);'
    + 'position:relative;scrollbar-width:thin;scrollbar-color:rgba(15,118,110,.2) transparent;}'
    + '.zbmp-modal::-webkit-scrollbar{width:4px}.zbmp-modal::-webkit-scrollbar-thumb{background:rgba(15,118,110,.2);border-radius:2px;}'
    /* Close button */
    + '.zbmp-close{position:absolute;top:16px;right:16px;background:rgba(255,255,255,.5);border:1px solid rgba(255,255,255,.4);'
    + 'color:#64748b;cursor:pointer;width:36px;height:36px;border-radius:12px;display:flex;align-items:center;justify-content:center;'
    + 'transition:all .2s;}'
    + '.zbmp-close:hover{background:rgba(15,118,110,.08);color:#0F766E;border-color:rgba(15,118,110,.15);}'
    + '.zbmp-close .zbmp-icon{width:18px;height:18px;display:flex;align-items:center;justify-content:center;}'
    + '.zbmp-close svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;}'
    /* Header */
    + '.zbmp-modal-header{text-align:center;margin-bottom:24px;}'
    + '.zbmp-modal-logo{width:60px;height:60px;border-radius:18px;margin:0 auto 16px;'
    + 'background:linear-gradient(135deg,#0F766E,#14B8A6);display:flex;align-items:center;justify-content:center;'
    + 'color:#fff;box-shadow:0 6px 20px rgba(15,118,110,.35);}'
    + '.zbmp-modal-logo .zbmp-icon{width:28px;height:28px;display:flex;align-items:center;justify-content:center;}'
    + '.zbmp-modal-logo svg{width:28px;height:28px;stroke:#fff;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;}'
    + '.zbmp-modal-h2{font-size:20px;font-weight:700;color:#0f172a;margin:0 0 6px;letter-spacing:-.01em;}'
    + '.zbmp-modal-sub{font-size:12px;color:#64748b;margin:0;}'
    /* Error - 毛玻璃 */
    + '.zbmp-error{background:rgba(220,38,38,.08);backdrop-filter:blur(10px);border:1px solid rgba(220,38,38,.18);'
    + 'color:#dc2626;padding:12px 16px;border-radius:14px;font-size:13px;margin-bottom:16px;display:none;font-weight:500;}'
    + '.zbmp-error.show{display:block;}'
    /* Info - 毛玻璃 */
    + '.zbmp-info{background:rgba(15,118,110,.06);backdrop-filter:blur(10px);border:1px solid rgba(15,118,110,.14);'
    + 'border-radius:16px;padding:14px 16px;font-size:12.5px;color:#475569;margin-bottom:16px;line-height:1.8;}'
    + '.zbmp-info strong{color:#0F766E;font-weight:600;}'
    /* QR code */
    + '.zbmp-qr-wrap{text-align:center;margin-bottom:16px;}'
    + '.zbmp-qr{width:184px;height:184px;margin:0 auto 14px;border-radius:18px;background:rgba(255,255,255,.9);'
    + 'padding:14px;border:1px solid rgba(15,118,110,.12);box-shadow:0 4px 16px rgba(15,118,110,.08);}'
    + '.zbmp-qr img{width:100%;height:100%;object-fit:contain;border-radius:8px;}'
    + '.zbmp-secret{font-family:"JetBrains Mono",monospace;font-size:13px;background:rgba(15,118,110,.06);'
    + 'padding:8px 18px;border-radius:10px;display:inline-block;letter-spacing:2px;color:#0F766E;font-weight:600;'
    + 'border:1px solid rgba(15,118,110,.1);}'
    /* TOTP inputs */
    + '.zbmp-totp-label{display:block;font-size:13px;font-weight:600;color:#0f172a;margin-bottom:10px;text-align:center;}'
    + '.zbmp-totp-inputs{display:flex;gap:10px;justify-content:center;margin-bottom:10px;}'
    + '.zbmp-totp-inputs input{width:46px;height:54px;text-align:center;font-size:22px;font-weight:700;'
    + 'border:1.5px solid rgba(148,163,184,.3);border-radius:14px;background:rgba(255,255,255,.7);outline:none;'
    + 'transition:all .2s;-moz-appearance:textfield;color:#0f172a;}'
    + '.zbmp-totp-inputs input::-webkit-outer-spin-button,'
    + '.zbmp-totp-inputs input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0;}'
    + '.zbmp-totp-inputs input:focus{border-color:#0F766E;box-shadow:0 0 0 4px rgba(15,118,110,.1);background:rgba(255,255,255,.95);}'
    + '.zbmp-totp-inputs input.filled{background:linear-gradient(135deg,rgba(240,253,250,.8),rgba(204,251,241,.6));border-color:rgba(15,118,110,.25);}'
    /* Timer - 渐变 */
    + '.zbmp-timer-bar{height:5px;background:rgba(148,163,184,.18);border-radius:3px;overflow:hidden;margin:10px 0 6px;}'
    + '.zbmp-timer-fill{height:100%;background:linear-gradient(90deg,#0F766E,#14B8A6);border-radius:3px;transition:width 1s linear;}'
    + '.zbmp-timer-text{text-align:center;font-size:11px;color:#94a3b8;margin-bottom:16px;font-weight:500;}'
    /* Buttons - 渐变CTA */
    + '.zbmp-btn{width:100%;padding:14px 20px;border:none;border-radius:14px;font-size:15px;font-weight:600;'
    + 'cursor:pointer;transition:all .2s;letter-spacing:.01em;display:flex;align-items:center;justify-content:center;gap:8px;}'
    + '.zbmp-btn-primary{background:linear-gradient(135deg,#0F766E,#14B8A6);color:#fff;box-shadow:0 4px 14px rgba(15,118,110,.3);}'
    + '.zbmp-btn-primary:hover{transform:translateY(-1px);box-shadow:0 8px 24px rgba(15,118,110,.4);}'
    + '.zbmp-btn-primary:active{transform:translateY(0);}'
    + '.zbmp-btn-primary:disabled{opacity:.45;cursor:not-allowed;transform:none;box-shadow:none;}'
    + '.zbmp-btn-secondary{background:rgba(255,255,255,.6);backdrop-filter:blur(10px);color:#475569;'
    + 'border:1px solid rgba(148,163,184,.25);margin-top:10px;}'
    + '.zbmp-btn-secondary:hover{background:rgba(15,118,110,.06);color:#0F766E;border-color:rgba(15,118,110,.2);}'
    /* Loading */
    + '.zbmp-loading{text-align:center;padding:32px 24px;color:#64748b;font-size:13px;}'
    + '.zbmp-spinner{width:32px;height:32px;border:3px solid rgba(15,118,110,.12);border-top-color:#0F766E;'
    + 'border-radius:50%;animation:zbmp-spin .8s linear infinite;margin:0 auto 14px;}'
    + '@keyframes zbmp-spin{to{transform:rotate(360deg)}}'
    /* Step indicator - 渐变胶囊 */
    + '.zbmp-step-indicator{display:flex;gap:8px;justify-content:center;margin-bottom:20px;}'
    + '.zbmp-step-dot{width:24px;height:5px;border-radius:3px;background:rgba(148,163,184,.2);transition:all .3s;}'
    + '.zbmp-step-dot.active{background:linear-gradient(90deg,#0F766E,#14B8A6);}'
    /* Icon base */
    + '.zbmp-icon{display:inline-flex;align-items:center;justify-content:center;}'
    + '.zbmp-icon svg{stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;}'
    /* Responsive */
    + '@media(max-width:480px){.zbmp-modal{padding:28px 20px 24px;border-radius:20px;}'
    + '.zbmp-totp-inputs input{width:40px;height:48px;font-size:18px;}'
    + '.zbmp-totp-inputs{gap:6px;}}';

  /* ---------- 状态 ---------- */
  var state = {
    totpBound: false,
    totpEnabled: false,
    zbmpGranted: false,
    userId: null,
    username: null,
    setupData: null,
    timerInterval: null,
  };

  /* ---------- 工具函数 ---------- */
  function $(id) { return document.getElementById(id); }

  function api(path, opts) {
    opts = opts || {};
    var fetchOpts = {
      method: opts.method || 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    };
    if (opts.body) fetchOpts.body = JSON.stringify(opts.body);
    return fetch(path, fetchOpts).then(function (r) {
      return r.json().then(function (data) {
        return { ok: r.ok, status: r.status, data: data };
      });
    }).catch(function (e) {
      return { ok: false, status: 0, data: { error: e.message } };
    });
  }

  function injectStyles() {
    if (document.getElementById('zbmp-entry-styles')) return;
    var style = document.createElement('style');
    style.id = 'zbmp-entry-styles';
    style.textContent = STYLES;
    document.head.appendChild(style);
  }

  function injectPanel() {
    if ($(OVERLAY_ID)) return;
    var div = document.createElement('div');
    div.innerHTML = PANEL_HTML;
    document.body.appendChild(div.firstChild);
    $('zbmp-close-btn').addEventListener('click', closePanel);
    $(OVERLAY_ID).addEventListener('click', function (e) {
      if (e.target.id === OVERLAY_ID) closePanel();
    });
    renderZbmpIcons($(OVERLAY_ID));
  }

  function openPanel() {
    injectStyles();
    injectPanel();
    $(OVERLAY_ID).style.display = 'flex';
    document.body.style.overflow = 'hidden';
    loadStatus();
  }

  function closePanel() {
    var overlay = $(OVERLAY_ID);
    if (overlay) overlay.style.display = 'none';
    document.body.style.overflow = '';
    stopTimer();
  }

  function setBody(html) {
    $('zbmp-modal-body').innerHTML = html;
    renderZbmpIcons($('zbmp-modal-body'));
  }

  function showError(msg) {
    var el = $('zbmp-error');
    if (el) {
      el.textContent = msg;
      el.classList.add('show');
    }
  }

  function hideError() {
    var el = $('zbmp-error');
    if (el) el.classList.remove('show');
  }

  /* ---------- 线性图标渲染（优先用 licon()，兜底内联SVG） ---------- */
  var INLINE_ICONS = {
    close: '<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    intelligence: '<svg viewBox="0 0 24 24"><path d="M12 2a4 4 0 0 1 4 4c0 1.5-.8 2.8-2 3.5V12h2a2 2 0 0 1 2 2v1a3 3 0 0 1-3 3h-1v2a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1v-2H7a3 3 0 0 1-3-3v-1a2 2 0 0 1 2-2h2V9.5C6.8 8.8 6 7.5 6 6a4 4 0 0 1 4-4h2z"/></svg>',
    shield: '<svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    qrcode: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><line x1="14" y1="14" x2="14" y2="14"/><line x1="18" y1="14" x2="18" y2="14"/><line x1="14" y1="18" x2="21" y2="18"/><line x1="18" y1="21" x2="18" y2="21"/><line x1="21" y1="14" x2="21" y2="21"/></svg>',
    check: '<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>',
    arrow: '<svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    lock: '<svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    user: '<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  };

  function renderZbmpIcons(scope) {
    var root = scope || document;
    var icons = root.querySelectorAll('[data-zbmp-icon]');
    icons.forEach(function (el) {
      var name = el.getAttribute('data-zbmp-icon');
      if (typeof licon === 'function') {
        el.innerHTML = licon(name, parseInt(el.getAttribute('data-icon-size') || '18', 10));
      } else if (INLINE_ICONS[name]) {
        el.innerHTML = INLINE_ICONS[name];
      }
    });
  }

  /* ---------- 状态加载 ---------- */
  function loadStatus() {
    setBody('<div class="zbmp-loading"><div class="zbmp-spinner"></div>检查状态中...</div>');
    api(ENTRY_API + '/status').then(function (res) {
      if (!res.ok || !res.data.ok) {
        if (res.status === 401) {
          setBody('<div class="zbmp-info">请先登录CTH账号，再进入序境·品牌市场域。<br><br>'
            + '<a href="/cth/login" style="color:#0F766E;font-weight:600">前往CTH登录 →</a></div>');
        } else {
          setBody('<div class="zbmp-error show">' + (res.data.error || '状态检查失败') + '</div>');
        }
        return;
      }
      state.totpBound = res.data.totp_bound;
      state.totpEnabled = res.data.totp_enabled;
      state.zbmpGranted = res.data.zbmp_granted;
      state.userId = res.data.user_id;
      state.username = res.data.username;

      if (state.zbmpGranted) {
        showAlreadyGranted();
      } else if (state.totpBound && state.totpEnabled) {
        showVerifyView();
      } else {
        showSetupIntro();
      }
    });
  }

  /* ---------- 视图：已授权 ---------- */
  function showAlreadyGranted() {
    setBody(''
      + '<div class="zbmp-info" style="text-align:center">'
      + '  <strong>已获得序境·品牌市场域访问权限</strong><br>'
      + '  当前身份：' + (state.username || '') + '<br>'
      + '  域身份有效期：8小时'
      + '</div>'
      + '<button class="zbmp-btn zbmp-btn-primary" onclick="ZBMPEntry.gotoZBMP()">进入序境·品牌市场 →</button>'
      + '<button class="zbmp-btn zbmp-btn-secondary" onclick="ZBMPEntry.leaveZBMP()">退出ZBMP域身份</button>');
  }

  /* ---------- 视图：未绑定 - 介绍 ---------- */
  function showSetupIntro() {
    setBody(''
      + '<div class="zbmp-error" id="zbmp-error"></div>'
      + '<div class="zbmp-info">'
      + '  <strong>首次进入序境·品牌市场域需要绑定动态验证码</strong><br>'
      + '  系统将生成一个二维码，用iPhone「设置 → 密码」扫码添加，'
      + '  之后每30秒生成6位动态码用于验证身份。'
      + '</div>'
      + '<button class="zbmp-btn zbmp-btn-primary" id="zbmp-setup-btn">生成绑定二维码</button>');
    $('zbmp-setup-btn').addEventListener('click', startSetup);
  }

  /* ---------- TOTP Setup ---------- */
  function startSetup() {
    hideError();
    setBody('<div class="zbmp-loading"><div class="zbmp-spinner"></div>生成二维码中...</div>');
    api(API_BASE + '/totp/setup', { method: 'POST', body: {} }).then(function (res) {
      if (!res.ok || !res.data.success) {
        showSetupIntro();
        showError(res.data.error || res.data.message || '生成二维码失败');
        return;
      }
      state.setupData = res.data;
      showSetupQR();
    });
  }

  function showSetupQR() {
    var d = state.setupData;
    setBody(''
      + '<div class="zbmp-error" id="zbmp-error"></div>'
      + '<div class="zbmp-step-indicator"><div class="zbmp-step-dot active"></div><div class="zbmp-step-dot active"></div><div class="zbmp-step-dot"></div></div>'
      + '<div class="zbmp-qr-wrap">'
      + '  <div class="zbmp-qr"><img src="' + d.qr_code + '" alt="TOTP二维码"></div>'
      + '  <div class="zbmp-secret">' + d.secret + '</div>'
      + '</div>'
      + '<div class="zbmp-info">'
      + '  <strong>扫码绑定步骤：</strong><br>'
      + '  1. 打开iPhone「设置」→「密码」<br>'
      + '  2. 点击右上角「+」或「添加密码」<br>'
      + '  3. 选择「扫描二维码」，扫描上方二维码<br>'
      + '  4. 保存后，「密码」中会显示序境 LUMENIS 的6位动态码'
      + '</div>'
      + '<label class="zbmp-totp-label">输入6位动态码确认绑定</label>'
      + '<div class="zbmp-totp-inputs" id="zbmp-confirm-inputs">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="0">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="1">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="2">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="3">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="4">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="5">'
      + '</div>'
      + '<button class="zbmp-btn zbmp-btn-primary" id="zbmp-confirm-btn" disabled>确认绑定并进入</button>'
      + '<button class="zbmp-btn zbmp-btn-secondary" id="zbmp-cancel-setup">重新生成二维码</button>');

    bindTotpInputs('zbmp-confirm-inputs', function (code) {
      $('zbmp-confirm-btn').disabled = code.length !== 6;
    });
    $('zbmp-confirm-btn').addEventListener('click', confirmSetup);
    $('zbmp-cancel-setup').addEventListener('click', startSetup);
  }

  function confirmSetup() {
    var code = getTotpCode('zbmp-confirm-inputs');
    if (code.length !== 6) return;
    hideError();
    $('zbmp-confirm-btn').disabled = true;
    $('zbmp-confirm-btn').textContent = '绑定中...';
    api(API_BASE + '/totp/confirm', { method: 'POST', body: { code: code } }).then(function (res) {
      if (!res.ok || !res.data.success) {
        showError(res.data.error || res.data.message || '绑定失败，请检查动态码');
        $('zbmp-confirm-btn').disabled = false;
        $('zbmp-confirm-btn').textContent = '确认绑定并进入';
        clearTotpInputs('zbmp-confirm-inputs');
        return;
      }
      // 绑定成功，直接验证进入
      verifyAndEnter(code);
    });
  }

  /* ---------- 视图：已绑定 - 验证 ---------- */
  function showVerifyView() {
    setBody(''
      + '<div class="zbmp-error" id="zbmp-error"></div>'
      + '<div class="zbmp-info">'
      + '  <strong>已绑定动态验证码</strong><br>'
      + '  打开iPhone「设置 → 密码」找到序境 LUMENIS，输入当前6位动态码。'
      + '</div>'
      + '<label class="zbmp-totp-label">6位动态验证码</label>'
      + '<div class="zbmp-totp-inputs" id="zbmp-verify-inputs">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="0">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="1">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="2">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="3">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="4">'
      + '  <input type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" data-idx="5">'
      + '</div>'
      + '<div class="zbmp-timer-bar"><div class="zbmp-timer-fill" id="zbmp-timer-fill" style="width:100%"></div></div>'
      + '<div class="zbmp-timer-text" id="zbmp-timer-text">验证码每30秒刷新</div>'
      + '<button class="zbmp-btn zbmp-btn-primary" id="zbmp-verify-btn" disabled>验证并进入序境·品牌市场 →</button>');

    bindTotpInputs('zbmp-verify-inputs', function (code) {
      $('zbmp-verify-btn').disabled = code.length !== 6;
    });
    $('zbmp-verify-btn').addEventListener('click', function () {
      var code = getTotpCode('zbmp-verify-inputs');
      if (code.length === 6) verifyAndEnter(code);
    });
    startTimer();
    // 聚焦第一个输入框
    setTimeout(function () {
      var first = document.querySelector('#zbmp-verify-inputs input');
      if (first) first.focus();
    }, 100);
  }

  function verifyAndEnter(code) {
    hideError();
    var btn = $('zbmp-verify-btn') || $('zbmp-confirm-btn');
    if (btn) { btn.disabled = true; btn.textContent = '验证中...'; }
    api(ENTRY_API + '/verify', { method: 'POST', body: { code: code } }).then(function (res) {
      if (!res.ok || !res.data.success) {
        showError(res.data.error || res.data.message || '验证失败，请检查动态码');
        if (btn) { btn.disabled = false; btn.textContent = '验证并进入序境·品牌市场 →'; }
        clearTotpInputs('zbmp-verify-inputs');
        clearTotpInputs('zbmp-confirm-inputs');
        return;
      }
      // 验证成功
      setBody(''
        + '<div class="zbmp-loading">'
        + '  <div class="zbmp-spinner" style="border-top-color:#16a34a"></div>'
        + '  验证成功，正在进入序境·品牌市场域...'
        + '</div>');
      stopTimer();
      setTimeout(function () {
        window.location.href = '/lumenis/zbmp/overview';
      }, 800);
    });
  }

  /* ---------- TOTP 输入框绑定 ---------- */
  function bindTotpInputs(containerId, onChange) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var inputs = container.querySelectorAll('input');
    inputs.forEach(function (input, idx) {
      input.addEventListener('input', function (e) {
        var val = e.target.value.replace(/\D/g, '');
        e.target.value = val;
        if (val) {
          e.target.classList.add('filled');
          if (idx < inputs.length - 1) inputs[idx + 1].focus();
        } else {
          e.target.classList.remove('filled');
        }
        if (onChange) onChange(getTotpCode(containerId));
      });
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && !e.target.value && idx > 0) {
          inputs[idx - 1].focus();
        }
      });
      input.addEventListener('paste', function (e) {
        e.preventDefault();
        var paste = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
        for (var i = 0; i < 6 && i < paste.length; i++) {
          inputs[i].value = paste[i];
          inputs[i].classList.add('filled');
        }
        if (onChange) onChange(getTotpCode(containerId));
        if (paste.length >= 6) inputs[5].blur();
      });
    });
  }

  function getTotpCode(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return '';
    var inputs = container.querySelectorAll('input');
    var code = '';
    inputs.forEach(function (i) { code += i.value; });
    return code;
  }

  function clearTotpInputs(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var inputs = container.querySelectorAll('input');
    inputs.forEach(function (i) { i.value = ''; i.classList.remove('filled'); });
    var first = container.querySelector('input');
    if (first) first.focus();
  }

  /* ---------- 30秒计时器 ---------- */
  function startTimer() {
    stopTimer();
    function update() {
      var now = Math.floor(Date.now() / 1000);
      var remaining = 30 - (now % 30);
      var fill = $('zbmp-timer-fill');
      var text = $('zbmp-timer-text');
      if (fill) fill.style.width = (remaining / 30 * 100) + '%';
      if (text) text.textContent = '下次刷新 ' + remaining + 's';
    }
    update();
    state.timerInterval = setInterval(update, 1000);
  }

  function stopTimer() {
    if (state.timerInterval) {
      clearInterval(state.timerInterval);
      state.timerInterval = null;
    }
  }

  /* ---------- 公开 API ---------- */
  var ZBMPEntry = {
    open: openPanel,
    close: closePanel,
    gotoZBMP: function () {
      window.location.href = '/lumenis/zbmp/overview';
    },
    leaveZBMP: function () {
      api(ENTRY_API + '/leave', { method: 'POST', body: {} }).then(function () {
        closePanel();
        window.location.href = '/lumenis/cth/overview';
      });
    },
    checkAndOpen: function () {
      // 检查URL参数
      var params = new URLSearchParams(window.location.search);
      if (params.get('zbmp-entry') === '1') {
        openPanel();
        return true;
      }
      return false;
    },
  };

  global.ZBMPEntry = ZBMPEntry;

  /* ---------- 自动初始化 ---------- */
  function init() {
    // 检查URL参数自动弹出
    ZBMPEntry.checkAndOpen();
    // ESC关闭
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closePanel();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})(typeof window !== 'undefined' ? window : this);

