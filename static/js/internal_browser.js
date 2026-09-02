/* ============================================================
 * Zachary OS AI · Internal Browser 前端控制
 * 截图流轮询 + 双账号切换 + 导航/点击/滚动/输入
 * ============================================================ */
(function () {
    'use strict';

    var REFRESH_MS = 1500;       // 截图流轮询间隔
    var currentAccount = 'XHS_CN_PRIMARY';
    var liveTimer = null;
    var isLive = false;
    var inFlight = false;
    var lastUrl = '';

    // 凭证：复用页面已有的全局 fetch 包装（ZBIP workbench 同源，浏览器会带 cookie/session）
    function api(path, opts) {
        opts = opts || {};
        var fetchOpts = { method: opts.method || 'GET', headers: { 'Content-Type': 'application/json' } };
        if (opts.body) fetchOpts.body = JSON.stringify(opts.body);
        return fetch(path, fetchOpts).then(function (r) { return r.json(); });
    }

    function el(id) { return document.getElementById(id); }

    function init() {
        var root = el('internal-browser-section');
        if (!root) return;

        // 标签切换
        var tabs = root.querySelectorAll('.ib-tab');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                var acct = tab.getAttribute('data-account');
                if (acct === currentAccount) return;
                currentAccount = acct;
                tabs.forEach(function (t) { t.classList.toggle('active', t === tab); });
                refreshNow();
            });
        });

        // 工具栏按钮
        on('ib-btn-back', function () { historyAct('back'); });
        on('ib-btn-forward', function () { historyAct('forward'); });
        on('ib-btn-reload', function () { historyAct('reload'); });
        on('ib-btn-home', function () { historyAct('home'); });
        on('ib-btn-refresh', function () { refreshNow(); });
        on('ib-btn-nav', doNavigate);
        on('ib-nav-input', function (input) {
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') doNavigate();
            });
        });

        // 实时开关
        var liveToggle = el('ib-live-checkbox');
        if (liveToggle) {
            liveToggle.addEventListener('change', function () {
                setLive(liveToggle.checked);
            });
        }

        // 截图点击（坐标回传）
        var shot = el('ib-screenshot');
        if (shot) {
            shot.addEventListener('click', function (e) {
                var rect = shot.getBoundingClientRect();
                var scaleX = shot.naturalWidth ? shot.naturalWidth / rect.width : 1;
                var scaleY = shot.naturalHeight ? shot.naturalHeight / rect.height : 1;
                var x = (e.clientX - rect.left) * scaleX;
                var y = (e.clientY - rect.top) * scaleY;
                api('/api/internal-browser/click', {
                    method: 'POST', body: { account: currentAccount, x: x, y: y }
                }).then(function () { setTimeout(refreshNow, 400); });
            });
            // 滚轮滚动
            shot.addEventListener('wheel', function (e) {
                e.preventDefault();
                api('/api/internal-browser/scroll', {
                    method: 'POST',
                    body: { account: currentAccount, delta_y: e.deltaY }
                }).then(function () { setTimeout(refreshNow, 200); });
            }, { passive: false });
        }

        // 初始加载账号状态 + 开启实时
        loadAccounts();
        if (liveToggle) { liveToggle.checked = true; setLive(true); }
    }

    function on(id, handler) {
        var node = el(id);
        if (node) handler(node);
    }

    function setLive(on) {
        isLive = on;
        var bar = el('ib-statusbar');
        if (bar) bar.classList.toggle('paused', !on);
        var liveText = el('ib-live-text');
        if (liveText) liveText.textContent = on ? '实时' : '已暂停';
        if (liveTimer) { clearInterval(liveTimer); liveTimer = null; }
        if (on) {
            refreshNow();
            liveTimer = setInterval(refreshNow, REFRESH_MS);
        }
    }

    function loadAccounts() {
        api('/api/internal-browser/accounts').then(function (data) {
            if (!data.ok) return;
            (data.accounts || []).forEach(function (st) {
                var tab = document.querySelector('.ib-tab[data-account="' + st.account + '"]');
                if (tab) {
                    var dot = tab.querySelector('.ib-tab-dot');
                    if (dot) {
                        dot.classList.toggle('online', st.online);
                        dot.classList.toggle('offline', !st.online);
                    }
                }
            });
        }).catch(function () {});
    }

    function showPlaceholder(html) {
        var viewport = el('ib-viewport');
        var shot = el('ib-screenshot');
        if (!viewport) return;
        if (shot) shot.style.display = 'none';
        var ph = el('ib-placeholder');
        if (!ph) {
            ph = document.createElement('div');
            ph.id = 'ib-placeholder';
            ph.className = 'ib-placeholder';
            viewport.appendChild(ph);
        }
        ph.innerHTML = html;
        ph.style.display = 'flex';
    }

    function refreshNow() {
        if (inFlight) return;
        inFlight = true;
        api('/api/internal-browser/screenshot?account=' + encodeURIComponent(currentAccount) + '&quality=65')
            .then(function (data) {
                inFlight = false;
                var viewport = el('ib-viewport');
                var shot = el('ib-screenshot');
                var ph = el('ib-placeholder');
                if (!data.ok) {
                    showPlaceholder('<div class="ib-spinner"></div><div>无法连接驻场浏览器<br><small>' +
                        escapeHtml(data.error || '未知错误') + '</small></div>');
                    return;
                }
                if (ph) ph.style.display = 'none';
                if (shot && data.image_base64) {
                    shot.style.display = 'block';
                    shot.src = 'data:image/jpeg;base64,' + data.image_base64;
                }
                // 地址栏 + 标题
                setText('ib-url', data.url || '');
                setText('ib-title-text', data.title || '');
                if (data.url && data.url !== lastUrl) {
                    var navInput = el('ib-nav-input');
                    if (navInput && document.activeElement !== navInput) navInput.value = data.url;
                    lastUrl = data.url;
                }
                setText('ib-captured-at', data.captured_at || '');
                // 更新在线点
                loadAccounts();
            })
            .catch(function (e) {
                inFlight = false;
                showPlaceholder('<div class="ib-spinner"></div><div>连接中…</div>');
            });
    }

    function doNavigate() {
        var input = el('ib-nav-input');
        var url = input ? input.value.trim() : '';
        if (!url) return;
        // 裸关键词 → 平台搜索
        if (!/^https?:\/\//.test(url) && !/^javascript:/.test(url)) {
            var home = currentAccount === 'XHS_RETINAUT'
                ? 'https://www.rednote.com/search_result?keyword='
                : 'https://www.xiaohongshu.com/search_result?keyword=';
            url = home + encodeURIComponent(url);
        }
        api('/api/internal-browser/navigate', { method: 'POST', body: { account: currentAccount, url: url } })
            .then(function (r) {
                if (!r.ok) { alert(r.error || '导航失败'); return; }
                setTimeout(refreshNow, 800);
            });
    }

    function historyAct(action) {
        api('/api/internal-browser/history', { method: 'POST', body: { account: currentAccount, action: action } })
            .then(function () { setTimeout(refreshNow, 600); });
    }

    function setText(id, txt) { var n = el(id); if (n) n.textContent = txt || ''; }
    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
