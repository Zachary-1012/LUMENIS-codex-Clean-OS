/* ============================================================
 * Zachary OS AI · Internal Browser 前端控制
 * 实时画面：优先 SSE Screencast 流（CDP 主动推帧，流畅），
 * 浏览器不支持/中断时自动降级为截图轮询。
 * 双账号切换 + 导航/点击/滚动/输入
 * ============================================================ */
(function () {
    'use strict';

    var POLL_MS = 1500;          // 降级轮询间隔
    var currentAccount = 'XHS_CN_PRIMARY';
    var pollTimer = null;
    var es = null;               // EventSource(SSE 流)
    var mode = 'off';           // 'sse' | 'poll' | 'off'
    var inFlight = false;
    var lastUrl = '';
    var frameCount = 0, lastFpsTick = 0, uiFps = 0;

    function api(path, opts) {
        opts = opts || {};
        var fetchOpts = { method: opts.method || 'GET', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
        if (opts.body) fetchOpts.body = JSON.stringify(opts.body);
        return fetch(path, fetchOpts).then(function (r) {
            if (r.status === 401) return { ok: false, error: '登录凭证失效，请在系统登录弹窗重新输入账号密码后刷新' };
            return r.json();
        });
    }
    function el(id) { return document.getElementById(id); }

    function init() {
        var root = el('page-internal-browser');
        if (!root) return;

        var tabs = root.querySelectorAll('.ib-tab');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                var acct = tab.getAttribute('data-account');
                if (acct === currentAccount) return;
                currentAccount = acct;
                tabs.forEach(function (t) { t.classList.toggle('active', t === tab); });
                restartStream();
            });
        });

        on('ib-btn-back', function () { historyAct('back'); });
        on('ib-btn-forward', function () { historyAct('forward'); });
        on('ib-btn-reload', function () { historyAct('reload'); });
        on('ib-btn-home', function () { historyAct('home'); });
        on('ib-btn-refresh', function () { restartStream(); });
        on('ib-btn-nav', doNavigate);
        on('ib-btn-external', function (btn) {
            // 用户主动选择：在系统外部浏览器打开当前页（不自动跳转、不代操作账号）
            btn.addEventListener('click', function () {
                var u = (el('ib-url') || {}).textContent || '';
                if (u && /^https?:\/\//.test(u)) window.open(u, '_blank', 'noopener');
            });
        });
        on('ib-nav-input', function (input) {
            input.addEventListener('keydown', function (e) { if (e.key === 'Enter') doNavigate(); });
        });

        var liveToggle = el('ib-live-checkbox');
        if (liveToggle) {
            liveToggle.addEventListener('change', function () { setLive(liveToggle.checked); });
        }

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
                }); // 流会自动推回点击后的新帧，无需手动刷新
            });
            shot.addEventListener('wheel', function (e) {
                e.preventDefault();
                api('/api/internal-browser/scroll', {
                    method: 'POST', body: { account: currentAccount, delta_y: e.deltaY }
                });
            }, { passive: false });
        }

        loadAccounts();
        if (liveToggle) { liveToggle.checked = true; setLive(true); }
    }

    function on(id, handler) { var node = el(id); if (node) handler(node); }

    /* ---------- 流生命周期 ---------- */
    function setLive(on) {
        var bar = el('ib-statusbar');
        if (bar) bar.classList.toggle('paused', !on);
        if (!on) { stopAll(); setLiveText('已暂停'); return; }
        restartStream();
    }
    function stopAll() {
        if (es) { try { es.close(); } catch (e) {} es = null; }
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        mode = 'off';
    }
    function restartStream() {
        stopAll();
        // 优先 SSE 实时流
        if (window.EventSource) {
            try {
                es = new EventSource('/api/internal-browser/stream?account=' + encodeURIComponent(currentAccount) + '&quality=55', { withCredentials: true });
                var downgraded = false;
                es.onmessage = function (ev) {
                    var m; try { m = JSON.parse(ev.data); } catch (e) { return; }
                    if (m.t === 'frame') { renderStreamFrame(m); if (mode !== 'sse') { mode = 'sse'; stopPoll(); } }
                    else if (m.t === 'state') { setConnDot(m.online); }
                };
                es.onerror = function () {
                    // SSE 不可用（如认证/代理不支持流式）→ 降级轮询，只降一次避免抖动
                    if (downgraded) return; downgraded = true;
                    if (es) { try { es.close(); } catch (e) {} es = null; }
                    startPoll();
                };
                // 2.5s 仍没收到任何帧，也降级轮询
                setTimeout(function () { if (mode !== 'sse' && es) { if (es) { try { es.close(); } catch (e) {} es = null; } startPoll(); } }, 2500);
            } catch (e) { startPoll(); }
        } else {
            startPoll();
        }
        refreshNow(); // 立即先取一帧，不等流
    }
    function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }
    function startPoll() {
        if (mode === 'poll') return; mode = 'poll';
        setLiveText('实时');
        refreshNow();
        stopPoll();
        pollTimer = setInterval(refreshNow, POLL_MS);
    }

    function renderStreamFrame(m) {
        var ph = el('ib-placeholder'); if (ph) ph.style.display = 'none';
        var shot = el('ib-screenshot');
        if (shot && m.data) {
            shot.style.display = 'block';
            shot.src = 'data:image/jpeg;base64,' + m.data;
        }
        // 本地显示帧率
        frameCount++; var now = performance.now();
        if (!lastFpsTick) lastFpsTick = now;
        if (now - lastFpsTick >= 1000) {
            uiFps = Math.round(frameCount * 1000 / (now - lastFpsTick));
            frameCount = 0; lastFpsTick = now;
            setLiveText('实时流' + (uiFps ? ' · ' + uiFps + 'fps' : ''));
        }
        setConnDot(m.online !== false);
    }
    function setConnDot(online) {
        var bar = el('ib-statusbar');
        if (!bar) return;
        bar.classList.toggle('is-online', !!online);
        bar.classList.toggle('is-offline', !online);
    }
    function setLiveText(t) { var n = el('ib-live-text'); if (n) n.textContent = t; }

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
            ph.id = 'ib-placeholder'; ph.className = 'ib-placeholder';
            viewport.appendChild(ph);
        }
        ph.innerHTML = html; ph.style.display = 'flex';
    }

    function refreshNow() {
        if (inFlight) return;
        inFlight = true;
        api('/api/internal-browser/screenshot?account=' + encodeURIComponent(currentAccount) + '&quality=65')
            .then(function (data) {
                inFlight = false;
                var shot = el('ib-screenshot'), ph = el('ib-placeholder');
                if (!data.ok) {
                    showPlaceholder('<div class="ib-spinner"></div><div>无法连接驻场浏览器<br><small>' +
                        escapeHtml(data.error || '未知错误') + '</small></div>');
                    return;
                }
                if (ph) ph.style.display = 'none';
                if (shot && data.image_base64 && mode !== 'sse') {
                    shot.style.display = 'block';
                    shot.src = 'data:image/jpeg;base64,' + data.image_base64;
                }
                setText('ib-url', data.url || '');
                setText('ib-title-text', data.title || '');
                if (data.url && data.url !== lastUrl) {
                    var navInput = el('ib-nav-input');
                    if (navInput && document.activeElement !== navInput) navInput.value = data.url;
                    lastUrl = data.url;
                }
                setText('ib-captured-at', data.captured_at || '');
                loadAccounts();
            })
            .catch(function () { inFlight = false; showPlaceholder('<div class="ib-spinner"></div><div>连接中…</div>'); });
    }

    function doNavigate() {
        var input = el('ib-nav-input');
        var url = input ? input.value.trim() : '';
        if (!url) return;
        if (!/^https?:\/\//.test(url) && !/^javascript:/.test(url)) {
            var home = currentAccount === 'XHS_RETINAUT'
                ? 'https://www.rednote.com/search_result?keyword='
                : 'https://www.xiaohongshu.com/search_result?keyword=';
            url = home + encodeURIComponent(url);
        }
        api('/api/internal-browser/navigate', { method: 'POST', body: { account: currentAccount, url: url } })
            .then(function (r) { if (!r.ok) { alert(r.error || '导航失败'); } });
    }

    function historyAct(action) {
        api('/api/internal-browser/history', { method: 'POST', body: { account: currentAccount, action: action } });
    }

    function setText(id, txt) { var n = el(id); if (n) n.textContent = txt || ''; }
    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else { init(); }
})();
