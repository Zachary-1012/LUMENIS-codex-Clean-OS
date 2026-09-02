/* ============================================================
 * Zachary OS AI · Evidence Dashboard 前端
 * 统计卡片 + 筛选 + 证据时间线
 * ============================================================ */
(function () {
    'use strict';

    var state = { feature: '', result: '', account: '', limit: 50 };
    var REFRESH_MS = 20000;
    var timer = null;

    function api(path) {
        return fetch(path).then(function (r) { return r.json(); });
    }
    function el(id) { return document.getElementById(id); }
    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function init() {
        if (!el('evidence-dashboard-section')) return;
        // 筛选 chips
        var chips = document.querySelectorAll('.ev-chip[data-filter]');
        chips.forEach(function (chip) {
            chip.addEventListener('click', function () {
                var type = chip.getAttribute('data-type');
                var val = chip.getAttribute('data-filter');
                chips.forEach(function (c) {
                    if (c.getAttribute('data-type') === type) c.classList.remove('active');
                });
                chip.classList.add('active');
                state[type] = (val === 'all' ? '' : val);
                loadList();
            });
        });
        var refreshBtn = el('ev-refresh-btn');
        if (refreshBtn) refreshBtn.addEventListener('click', function () { loadStats(); loadList(); });

        loadStats();
        loadList();
        timer = setInterval(function () { loadStats(); loadList(); }, REFRESH_MS);
    }

    function loadStats() {
        api('/api/evidence/stats').then(function (data) {
            if (!data.ok) return;
            var st = data.stats;
            setText('ev-stat-total', st.total);
            var pass = (st.by_result || {}).PASS || 0;
            var fail = (st.by_result || {}).FAIL || 0;
            setText('ev-stat-pass', pass);
            setText('ev-stat-fail', fail);
            var byAcct = st.by_account || {};
            var acctText = Object.keys(byAcct).map(function (k) {
                var short = k.replace('XHS_', '').replace('CN_PRIMARY', '大陆').replace('RETINAUT', '香港');
                return short + ' ' + byAcct[k];
            }).join(' · ') || '暂无';
            setText('ev-stat-account', acctText);
        }).catch(function () {});
    }

    function loadList() {
        var params = [];
        if (state.feature) params.push('feature_id=' + encodeURIComponent(state.feature));
        if (state.result) params.push('result=' + encodeURIComponent(state.result));
        if (state.account) params.push('account=' + encodeURIComponent(state.account));
        params.push('limit=' + state.limit);
        api('/api/evidence/list?' + params.join('&')).then(function (data) {
            var box = el('ev-timeline');
            if (!box) return;
            if (!data.ok) { box.innerHTML = '<div class="ev-empty">加载失败：' + esc(data.error) + '</div>'; return; }
            if (!data.records || data.records.length === 0) {
                box.innerHTML = '<div class="ev-empty">暂无符合条件的证据记录</div>';
                return;
            }
            box.innerHTML = data.records.map(renderItem).join('');
        }).catch(function () {});
    }

    function renderItem(r) {
        var result = r.result || 'UNKNOWN';
        var actual = r.actual || r.notes || '';
        var feature = r.feature_id || r.metric_name || 'evidence';
        var acct = r.account ? r.account.replace('XHS_CN_PRIMARY', '大陆主号').replace('XHS_RETINAUT', '香港号') : '';
        return '<div class="ev-item">' +
            '<span class="ev-item-dot ' + esc(result) + '"></span>' +
            '<div class="ev-item-body">' +
                '<div class="ev-item-head">' +
                    '<span class="ev-item-feature">' + esc(feature) + '</span>' +
                    (r.level ? '<span class="ev-badge level">' + esc(r.level) + '</span>' : '') +
                    '<span class="ev-badge result-' + esc(result) + '">' + esc(result) + '</span>' +
                    (acct ? '<span class="ev-badge account">' + esc(acct) + '</span>' : '') +
                    (r.source ? '<span class="ev-badge account">' + esc(r.source) + '</span>' : '') +
                    '<span class="ev-item-time">' + esc(r.created_at || '') + '</span>' +
                '</div>' +
                (actual ? '<div class="ev-item-actual">' + esc(actual) + '</div>' : '') +
            '</div>' +
        '</div>';
    }

    function setText(id, txt) { var n = el(id); if (n) n.textContent = txt; }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
