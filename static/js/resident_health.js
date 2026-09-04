/* ================================================================
   Zachary OS AI · Resident Browser Health Monitor 前端逻辑
   - 轮询 /api/resident/health（默认 30s）
   - 渲染双身份健康卡片
   - 恢复按钮 POST /api/resident/recover
   - 系统内扫码弹窗（不跳转外部浏览器）
   ================================================================ */
(function () {
    'use strict';

    var POLL_INTERVAL = 30000; // 30 秒轮询
    var pollTimer = null;
    var currentData = null;

    // ---- 工具函数 ----
    function $(sel, ctx) { return (ctx || document).querySelector(sel); }
    function $all(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
    function el(tag, attrs, children) {
        var e = document.createElement(tag);
        if (attrs) for (var k in attrs) {
            if (k === 'class') e.className = attrs[k];
            else if (k === 'text') e.textContent = attrs[k];
            else if (k === 'html') e.innerHTML = attrs[k];
            else if (k.indexOf('on') === 0) e.addEventListener(k.slice(2), attrs[k]);
            else e.setAttribute(k, attrs[k]);
        }
        if (children) {
            if (!Array.isArray(children)) children = [children];
            children.forEach(function (c) {
                if (typeof c === 'string') e.appendChild(document.createTextNode(c));
                else if (c) e.appendChild(c);
            });
        }
        return e;
    }

    // ---- API 调用（同域，浏览器自动带 Basic auth）----
    function apiGet(path) {
        return fetch(path, { credentials: 'same-origin' })
            .then(function (r) { return r.json(); });
    }
    function apiPost(path, body) {
        return fetch(path, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {})
        }).then(function (r) { return r.json(); });
    }

    // ---- 状态中文映射 ----
    var STATUS_LABEL = {
        'HEALTHY': '运行正常',
        'NEEDS_LOGIN': '需重新登录',
        'CDP_DEGRADED': 'CDP 异常',
        'DOWN': '已离线'
    };
    var STATUS_CLASS = {
        'HEALTHY': 'healthy',
        'NEEDS_LOGIN': 'needs_login',
        'CDP_DEGRADED': 'cdp_degraded',
        'DOWN': 'down'
    };

    // ---- 渲染总览条 ----
    function renderOverview(data, container) {
        container.innerHTML = '';
        var overview = el('div', { class: 'rh-overview' });
        overview.appendChild(el('div', { class: 'rh-overview-stat healthy' }, [
            el('span', { text: '正常' }),
            el('b', { text: String(data.healthy || 0) })
        ]));
        overview.appendChild(el('div', { class: 'rh-overview-stat needs-login' }, [
            el('span', { text: '需登录' }),
            el('b', { text: String(data.needs_login || 0) })
        ]));
        overview.appendChild(el('div', { class: 'rh-overview-stat degraded' }, [
            el('span', { text: 'CDP异常' }),
            el('b', { text: String(data.degraded || 0) })
        ]));
        overview.appendChild(el('div', { class: 'rh-overview-stat down' }, [
            el('span', { text: '离线' }),
            el('b', { text: String(data.down || 0) })
        ]));
        overview.appendChild(el('div', { class: 'rh-overview-time', text: '更新于 ' + (data.checked_at || '--') }));
        container.appendChild(overview);
    }

    // ---- 渲染单个身份卡片 ----
    function renderAccountCard(account, info) {
        var statusCls = STATUS_CLASS[info.status] || 'down';
        var card = el('div', { class: 'rh-card status-' + statusCls });

        // 头部
        var head = el('div', { class: 'rh-card-head' });
        var identity = el('div', { class: 'rh-identity' });
        identity.appendChild(el('div', { class: 'rh-identity-name', text: account }));
        var platform = el('div', { class: 'rh-identity-platform' });
        platform.appendChild(el('span', { class: 'dot' }));
        platform.appendChild(el('span', { text: (info.home_url || '').replace('https://www.', '') }));
        identity.appendChild(platform);
        head.appendChild(identity);

        var badge = el('div', { class: 'rh-status-badge ' + statusCls });
        badge.appendChild(el('span', { class: 'pulse' }));
        badge.appendChild(el('span', { text: STATUS_LABEL[info.status] || info.status }));
        head.appendChild(badge);
        card.appendChild(head);

        // 指标
        var metrics = el('div', { class: 'rh-metrics' });
        // CDP 端口
        var m1 = el('div', { class: 'rh-metric' });
        m1.appendChild(el('div', { class: 'rh-metric-label', text: 'CDP端口' }));
        m1.appendChild(el('div', { class: 'rh-metric-value ' + (info.port_alive ? 'ok' : 'fail'), text: String(info.cdp_port) }));
        metrics.appendChild(m1);
        // WebSocket
        var m2 = el('div', { class: 'rh-metric' });
        m2.appendChild(el('div', { class: 'rh-metric-label', text: 'CDP控制面' }));
        var wsVal = el('div', { class: 'rh-metric-value ' + (info.cdp_ws_ok ? 'ok' : 'fail') });
        wsVal.appendChild(el('span', { class: 'check', text: '' }));
        wsVal.appendChild(document.createTextNode(info.cdp_ws_ok ? '在线' : '异常'));
        m2.appendChild(wsVal);
        metrics.appendChild(m2);
        // 登录态
        var m3 = el('div', { class: 'rh-metric' });
        m3.appendChild(el('div', { class: 'rh-metric-label', text: '登录态' }));
        var loginOk = info.login_state === 'logged_in';
        var loginVal = el('div', { class: 'rh-metric-value ' + (loginOk ? 'ok' : 'fail') });
        loginVal.appendChild(el('span', { class: 'check', text: '' }));
        loginVal.appendChild(document.createTextNode(loginOk ? '已登录' : '未登录'));
        m3.appendChild(loginVal);
        metrics.appendChild(m3);
        card.appendChild(metrics);

        // Cookie 数量（小字）
        var cookieInfo = el('div', { class: 'rh-detail ' + statusCls, text: info.detail + '（cookie ' + (info.cookie_count || 0) + ' 条）' });
        card.appendChild(cookieInfo);

        // 操作按钮
        var actions = el('div', { class: 'rh-card-actions' });
        // 恢复按钮（DOWN 或 CDP_DEGRADED 时显示）
        if (info.status === 'DOWN' || info.status === 'CDP_DEGRADED') {
            actions.appendChild(el('button', {
                class: 'rh-btn rh-btn-primary',
                text: '自动恢复',
                onclick: function () { recoverAccount(account); }
            }));
        }
        // 扫码登录按钮（NEEDS_LOGIN 时显示）
        if (info.status === 'NEEDS_LOGIN') {
            actions.appendChild(el('button', {
                class: 'rh-btn rh-btn-warning',
                text: '系统内扫码登录',
                onclick: function () { openQrModal(account, info); }
            }));
        }
        // 查看驻场浏览器（始终显示）
        actions.appendChild(el('button', {
            class: 'rh-btn rh-btn-secondary',
            text: '打开驻场窗口',
            onclick: function () {
                // 在新标签页打开 CDP 端口的 inspect 页面（用户可在系统外查看）
                window.open('http://127.0.0.1:' + info.cdp_port, '_blank');
            }
        }));
        card.appendChild(actions);

        return card;
    }

    // ---- 渲染全部 ----
    function render(data) {
        currentData = data;
        var section = ($('#resident-health-section') || $('#page-resident-health'));
        if (!section) return;
        var grid = $('#rh-grid', section);
        var overview = $('#rh-overview', section);
        if (!grid || !overview) return;

        renderOverview(data, overview);
        grid.innerHTML = '';
        var accounts = data.accounts || {};
        Object.keys(accounts).forEach(function (acct) {
            grid.appendChild(renderAccountCard(acct, accounts[acct]));
        });
    }

    // ---- 加载状态 ----
    function showLoading() {
        var section = ($('#resident-health-section') || $('#page-resident-health'));
        if (!section) return;
        var grid = $('#rh-grid', section);
        if (grid) {
            grid.innerHTML = '';
            grid.appendChild(el('div', { class: 'rh-loading' }, [
                el('span', { class: 'spinner' }),
                el('span', { text: '正在检测驻场浏览器状态...' })
            ]));
        }
    }

    // ---- 刷新健康状态 ----
    function refreshHealth() {
        showLoading();
        apiGet('/api/resident/health')
            .then(function (d) {
                if (d && d.ok && d.result) {
                    render(d.result);
                } else {
                    console.error('health API error', d);
                }
            })
            .catch(function (e) { console.error('health fetch error', e); });
    }

    // ---- 恢复单个身份 ----
    function recoverAccount(account) {
        var btn = event && event.target;
        if (btn) { btn.disabled = true; btn.textContent = '恢复中...'; }
        apiPost('/api/resident/recover', { account: account })
            .then(function (d) {
                alert('恢复指令已下发：' + (d && d.result && d.result.action ? d.result.action : JSON.stringify(d)));
                setTimeout(refreshHealth, 3000);
            })
            .catch(function (e) {
                alert('恢复失败：' + e.message);
                if (btn) { btn.disabled = false; btn.textContent = '自动恢复'; }
            });
    }

    // ---- 系统内扫码弹窗 ----
    var qrModal = null;
    var qrPollTimer = null;

    function buildQrModal() {
        if (qrModal) return qrModal;
        var overlay = el('div', { class: 'rh-qr-modal-overlay', id: 'rh-qr-modal' });
        var modal = el('div', { class: 'rh-qr-modal' });

        // 头部
        var head = el('div', { class: 'rh-qr-modal-head' });
        head.appendChild(el('h3', { text: '驻场浏览器登录' }));
        head.appendChild(el('button', { class: 'rh-close', text: '×', onclick: closeQrModal }));
        modal.appendChild(head);

        //  body
        var body = el('div', { class: 'rh-qr-modal-body', id: 'rh-qr-body' });
        modal.appendChild(body);

        // 底部
        var foot = el('div', { class: 'rh-qr-modal-foot' });
        foot.appendChild(el('button', { class: 'rh-btn rh-btn-secondary', text: '关闭', onclick: closeQrModal }));
        foot.appendChild(el('button', { class: 'rh-btn rh-btn-primary', text: '我已扫码，检测状态', onclick: function () {
            refreshHealth();
            setTimeout(function () {
                if (currentData && currentData.accounts) {
                    var acct = $('#rh-qr-account') ? $('#rh-qr-account').textContent : '';
                    var info = currentData.accounts[acct];
                    if (info && info.status === 'HEALTHY') {
                        closeQrModal();
                        alert('登录成功！驻场浏览器已恢复正常。');
                    } else {
                        alert('尚未检测到登录成功，请确认扫码完成后重试。');
                    }
                }
            }, 2000);
        } }));
        modal.appendChild(foot);

        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        qrModal = overlay;
        return overlay;
    }

    function openQrModal(account, info) {
        buildQrModal();
        var body = $('#rh-qr-body', qrModal);
        body.innerHTML = '';

        // 身份标签
        var idTag = el('div', { class: 'rh-qr-identity' });
        idTag.appendChild(el('span', { class: 'dot' }));
        idTag.appendChild(el('span', { id: 'rh-qr-account', text: account }));
        idTag.appendChild(el('span', { text: '· ' + (info.home_url || '').replace('https://www.', '') }));
        body.appendChild(idTag);

        // 二维码区域：尝试 iframe 嵌入登录页
        var frame = el('div', { class: 'rh-qr-frame' });
        var loginUrl = (info.home_url || 'https://www.xiaohongshu.com') + '/explore';
        // 尝试 iframe（可能被 X-Frame-Options 阻止）
        var iframe = el('iframe', {
            src: loginUrl,
            sandbox: 'allow-same-origin allow-scripts allow-forms',
            onload: function () {
                // iframe 加载成功，隐藏占位
                var ph = $('#rh-qr-placeholder', frame);
                if (ph) ph.style.display = 'none';
            },
            onerror: function () {
                showQrPlaceholder(frame, account, info);
            }
        });
        frame.appendChild(iframe);

        // 占位（iframe 被阻止时显示）
        var placeholder = el('div', { class: 'rh-qr-placeholder', id: 'rh-qr-placeholder' });
        placeholder.appendChild(el('div', { class: 'qr-icon', text: 'Z' }));
        placeholder.appendChild(el('div', { text: '正在加载登录页...' }));
        placeholder.appendChild(el('div', { text: '如长时间未显示，请点击下方"打开驻场窗口"在浏览器中扫码' }));
        frame.appendChild(placeholder);

        // 3 秒后如果 iframe 仍空白，显示备用提示
        setTimeout(function () {
            var ph = $('#rh-qr-placeholder', frame);
            if (ph && ph.style.display !== 'none') {
                ph.innerHTML = '';
                ph.appendChild(el('div', { class: 'qr-icon', text: 'Z' }));
                ph.appendChild(el('div', { text: '登录页无法在系统内嵌入' }));
                ph.appendChild(el('div', { text: '请点击"打开驻场窗口"在独立浏览器中扫码' }));
            }
        }, 3000);

        body.appendChild(frame);

        // 说明
        var instr = el('div', { class: 'rh-qr-instructions' });
        instr.innerHTML = '使用 <b>小红书 App</b> 扫描上方二维码完成登录。<br>登录成功后点击"我已扫码，检测状态"，系统将自动验证并关闭弹窗。<br><b>不会跳转外部浏览器</b>，全程在系统内完成。';
        body.appendChild(instr);

        qrModal.classList.add('open');

        // 开始轮询检测登录状态
        if (qrPollTimer) clearInterval(qrPollTimer);
        qrPollTimer = setInterval(function () {
            apiGet('/api/resident/health?account=' + encodeURIComponent(account))
                .then(function (d) {
                    if (d && d.ok && d.result && d.result.status === 'HEALTHY') {
                        closeQrModal();
                        alert(account + ' 登录成功！驻场浏览器已恢复正常。');
                    }
                })
                .catch(function () {});
        }, 10000);
    }

    function closeQrModal() {
        if (qrModal) qrModal.classList.remove('open');
        if (qrPollTimer) { clearInterval(qrPollTimer); qrPollTimer = null; }
    }

    // ---- 初始化 ----
    function init() {
        var section = ($('#resident-health-section') || $('#page-resident-health'));
        if (!section) return; // 页面没有这个 section 就不初始化

        // 刷新按钮
        var refreshBtn = $('#rh-refresh-btn', section);
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshHealth);
        }

        // 首次加载
        refreshHealth();

        // 定时轮询
        pollTimer = setInterval(refreshHealth, POLL_INTERVAL);
    }

    // DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 暴露给全局（供模板内联按钮调用）
    window.ResidentHealth = {
        refresh: refreshHealth,
        recover: recoverAccount,
        openQr: openQrModal,
        closeQr: closeQrModal
    };
})();
