/**
 * 广州太古汇舆情监测系统 v5.8.0 前端交互补丁
 * 包含：每日弹窗、趋势图交互、实时同步、发布日期分桶、负面确认页面
 * 
 * 使用方法：
 * 1. 将此文件复制到 static/js/ 目录
 * 2. 在 index.html 的 </body> 前添加：<script src="/static/js/ui_interactions_v5.8.0.js"></script>
 * 3. 确保后端API已集成（api_v5.8.0.py）
 */

(function() {
    'use strict';

    // ============================================================
    // 全局状态
    // ============================================================
    const UIState = {
        negativePendingCount: 0,
        dashboardLastUpdate: null,
        publishBuckets: null,
        trendsData: null
    };

    // ============================================================
    // 工具函数
    // ============================================================
    function api(url, options = {}) {
        return fetch(url, {
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            ...options
        }).then(r => r.json());
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'error' ? '#ff4444' : type === 'success' ? '#44aa44' : '#333'};
            color: #fff;
            border-radius: 8px;
            z-index: 100000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // 添加动画样式
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }
        .modal-backdrop {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.2s ease;
        }
        .modal-content {
            background: #fff;
            border-radius: 16px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .modal-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }
        .modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #999;
            padding: 0 5px;
        }
        .modal-close:hover { color: #333; }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #1C1917;
            color: #fff;
        }
        .btn-primary:hover { opacity: 0.9; }
        .btn-success {
            background: #44aa44;
            color: #fff;
        }
        .btn-danger {
            background: #ff4444;
            color: #fff;
        }
        .btn-secondary {
            background: #f0f0f0;
            color: #333;
        }
        .data-card {
            background: #fff;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.2s;
        }
        .data-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }
        .data-card-title {
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }
        .data-card-value {
            font-size: 28px;
            font-weight: 700;
            color: #333;
        }
        .trend-chart-container {
            position: relative;
            width: 100%;
            height: 200px;
        }
        .trend-bar {
            position: absolute;
            bottom: 0;
            width: 8%;
            background: #57534E;
            border-radius: 4px 4px 0 0;
            cursor: pointer;
            transition: all 0.2s;
        }
        .trend-bar:hover {
            filter: brightness(1.2);
            transform: scaleY(1.05);
        }
        .trend-tooltip {
            position: absolute;
            background: #333;
            color: #fff;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            pointer-events: none;
            z-index: 100;
            display: none;
            white-space: nowrap;
        }
        .negative-item {
            padding: 12px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .negative-item:hover {
            background: #f9f9f9;
        }
        .negative-item-title {
            flex: 1;
            font-size: 14px;
            color: #333;
            margin-right: 12px;
        }
        .negative-item-meta {
            font-size: 12px;
            color: #999;
            margin-top: 4px;
        }
        .negative-item-actions {
            display: flex;
            gap: 8px;
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-danger { background: #ffebee; color: #c62828; }
        .badge-warning { background: #fff3e0; color: #e65100; }
        .badge-success { background: #e8f5e9; color: #2e7d32; }
        .badge-info { background: #e3f2fd; color: #1565c0; }
    `;
    document.head.appendChild(style);

    // v5.8.9 移动端非阻断轻提示：首屏不被全屏弹窗遮挡，点击横幅才展开完整弹窗（桌面端不受影响）
    window.showMobileNotice = function (html, onClick) {
        let bar = document.getElementById('mobileNoticeBar');
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'mobileNoticeBar';
            bar.style.cssText = 'position:fixed;left:10px;right:10px;bottom:calc(72px + env(safe-area-inset-bottom));z-index:99998;background:#1d1d1f;color:#fff;border-radius:14px;padding:11px 14px;font-size:13px;box-shadow:0 8px 30px rgba(0,0,0,.3);display:flex;gap:8px;align-items:center;line-height:1.45;max-width:100%;box-sizing:border-box';
            document.body.appendChild(bar);
        }
        bar.innerHTML = '<span style="flex:1;min-width:0">'+html+'</span><span style="opacity:.78;font-size:13px;white-space:nowrap">点击查看 ›</span>';
        bar.onclick = function () { bar.remove(); try { onClick && onClick(); } catch (e) {} };
        return bar;
    };

    // ============================================================
    // 1. 每日弹窗优先推送待确认负面
    // ============================================================
    function checkNegativePending() {
        api('/api/negative/stats')
            .then(data => {
                if (data.ok && data.pending > 0) {
                    UIState.negativePendingCount = data.pending;
                    /* 单模态原则：不再自动弹居中模态（会与“日报速览”叠加）；待审数仍写入侧栏 badge，提醒改非阻断 toast，入口在左侧“负面确认” */
                    try { if (window.showToast) showToast('您有 ' + data.pending + ' 条负面舆情待确认（见左侧“负面确认”）', 'info'); } catch(e) {}
                }
            })
            .catch(err => console.warn('检查待确认负面失败:', err));
    }

    function showNegativePendingModal(stats) {
        // 检查是否已经显示过今天
        const today = new Date().toDateString();
        const lastShow = localStorage.getItem('negative_pending_last_show');
        if (lastShow === today) return;

        localStorage.setItem('negative_pending_last_show', today);

        const modal = document.createElement('div');
        modal.className = 'modal-backdrop';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title">${xicon('warn')} 待确认负面舆情提醒</div>
                    <button class="modal-close">&times;</button>
                </div>
                <div style="margin-bottom: 16px;">
                    <p style="font-size: 14px; color: #666; margin-bottom: 12px;">
                        您有 <strong style="color: #c62828; font-size: 18px;">${stats.pending}</strong> 条负面舆情待确认
                    </p>
                    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                        <div class="data-card" style="flex: 1; text-align: center;">
                            <div class="data-card-title">总负面</div>
                            <div class="data-card-value" style="color: #c62828;">${stats.total_negative || stats.total || 0}</div>
                        </div>
                        <div class="data-card" style="flex: 1; text-align: center;">
                            <div class="data-card-title">已确认</div>
                            <div class="data-card-value" style="color: #2e7d32;">${stats.confirmed}</div>
                        </div>
                        <div class="data-card" style="flex: 1; text-align: center;">
                            <div class="data-card-title">已驳回</div>
                            <div class="data-card-value" style="color: #999;">${stats.rejected}</div>
                        </div>
                    </div>
                </div>
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button class="btn btn-secondary" id="negativeLater">稍后处理</button>
                    <button class="btn btn-primary" id="negativeReviewNow">立即审核</button>
                </div>
            </div>
        `;

        // v5.8.9 先绑定、暂不挂载，末尾按端决定（移动端收进底部轻提示，不遮挡首屏）

        modal.querySelector('.modal-close').onclick = () => modal.remove();
        modal.querySelector('#negativeLater').onclick = () => modal.remove();
        modal.querySelector('#negativeReviewNow').onclick = () => {
            modal.remove();
            showNegativeReviewPage();
        };
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        if (window.matchMedia && window.matchMedia('(max-width:768px)').matches) {
            window.showMobileNotice(`您有 <b>${stats.pending}</b> 条负面舆情待确认`, () => document.body.appendChild(modal));
        } else {
            document.body.appendChild(modal);
        }
    }

    // ============================================================
    // 2. 负面确认页面
    // ============================================================
    function showNegativeReviewPage(page = 1) {
        api(`/api/negative/pending?page=${page}&per_page=10`)
            .then(data => {
                if (!data.ok) {
                    showToast('获取待确认负面失败', 'error');
                    return;
                }

                const modal = document.createElement('div');
                modal.className = 'modal-backdrop';
                modal.style.alignItems = 'flex-start';
                modal.style.paddingTop = '40px';

                let notesHTML = '';
                if (data.notes.length === 0) {
                    notesHTML = '<div style="text-align: center; padding: 40px; color: #999;">暂无待确认负面舆情</div>';
                } else {
                    notesHTML = data.notes.map(note => `
                        <div class="negative-item" data-note-id="${note.note_id}">
                            <div style="flex: 1;">
                                <div class="negative-item-title">${escapeHtml(note.title || '无标题')}</div>
                                <div class="negative-item-meta">
                                    <span class="badge badge-danger">${note.risk_level || '未知'}</span>
                                    作者：${escapeHtml(note.author_nickname || '未知')}
                                    · 发布：${note.publish_date || '未知'}
                                    · 赞${note.likes || 0} 评${note.comments || 0}
                                </div>
                            </div>
                            <div class="negative-item-actions">
                                <button class="btn btn-success btn-sm" onclick="confirmNegative('${note.note_id}', this)">确认</button>
                                <button class="btn btn-danger btn-sm" onclick="rejectNegative('${note.note_id}', this)">驳回</button>
                            </div>
                        </div>
                    `).join('');
                }

                modal.innerHTML = `
                    <div class="modal-content" style="max-width: 700px; width: 95%;">
                        <div class="modal-header">
                            <div class="modal-title">负面舆情审核 (${data.total}条待确认)</div>
                            <button class="modal-close">&times;</button>
                        </div>
                        <div id="negativeList">
                            ${notesHTML}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid #eee;">
                            <div style="font-size: 13px; color: #666;">
                                第 ${data.page} / ${Math.ceil(data.total / data.per_page)} 页
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <button class="btn btn-secondary" id="prevPage" ${data.page <= 1 ? 'disabled' : ''}>上一页</button>
                                <button class="btn btn-secondary" id="nextPage" ${data.page >= Math.ceil(data.total / data.per_page) ? 'disabled' : ''}>下一页</button>
                            </div>
                        </div>
                    </div>
                `;

                document.body.appendChild(modal);

                modal.querySelector('.modal-close').onclick = () => modal.remove();
                modal.onclick = (e) => { if (e.target === modal) modal.remove(); };

                const prevBtn = modal.querySelector('#prevPage');
                const nextBtn = modal.querySelector('#nextPage');
                if (prevBtn) prevBtn.onclick = () => { modal.remove(); showNegativeReviewPage(data.page - 1); };
                if (nextBtn) nextBtn.onclick = () => { modal.remove(); showNegativeReviewPage(data.page + 1); };
            })
            .catch(err => {
                console.error('加载负面审核页面失败:', err);
                showToast('加载失败，请重试', 'error');
            });
    }

    // 全局暴露确认/驳回函数
    window.confirmNegative = function(noteId, btn) {
        api('/api/negative/confirm', {
            method: 'POST',
            body: JSON.stringify({ note_id: noteId, confirmed_by: 'admin' })
        }).then(data => {
            if (data.ok) {
                showToast('已确认负面', 'success');
                btn.closest('.negative-item').style.opacity = '0.5';
                btn.disabled = true;
                btn.nextElementSibling.disabled = true;
            } else {
                showToast('确认失败', 'error');
            }
        }).catch(() => showToast('确认失败', 'error'));
    };

    window.rejectNegative = function(noteId, btn) {
        api('/api/negative/reject', {
            method: 'POST',
            body: JSON.stringify({ note_id: noteId, confirmed_by: 'admin' })
        }).then(data => {
            if (data.ok) {
                showToast('已驳回', 'success');
                btn.closest('.negative-item').style.opacity = '0.5';
                btn.disabled = true;
                btn.previousElementSibling.disabled = true;
            } else {
                showToast('驳回失败', 'error');
            }
        }).catch(() => showToast('驳回失败', 'error'));
    };

    // ============================================================
    // 3. 趋势图动态交互（点击显示百分比）
    // ============================================================
    function renderTrendChart(containerId, days = 14) {
        const container = document.getElementById(containerId);
        if (!container) return;

        api(`/api/trends/global?days=${days}`)
            .then(data => {
                if (!data.ok || !data.data || data.data.length === 0) {
                    container.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">暂无趋势数据</div>';
                    return;
                }

                UIState.trendsData = data.data;
                const maxVal = Math.max(...data.data.map(d => d.total), 1);

                let barsHTML = '';
                data.data.forEach((d, i) => {
                    const height = (d.total / maxVal) * 100;
                    const left = (i / data.data.length) * 100 + 1;
                    const percent = ((d.negative / d.total) * 100).toFixed(1);
                    barsHTML += `
                        <div class="trend-bar" 
                             style="left: ${left}%; height: ${height}%;"
                             data-date="${d.date}"
                             data-total="${d.total}"
                             data-positive="${d.positive}"
                             data-negative="${d.negative}"
                             data-neutral="${d.neutral}"
                             data-percent="${percent}">
                        </div>
                    `;
                });

                container.innerHTML = `
                    <div class="trend-chart-container">
                        ${barsHTML}
                        <div class="trend-tooltip" id="trendTooltip"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 11px; color: #999;">
                        <span>${data.data[0].date}</span>
                        <span>${data.data[Math.floor(data.data.length/2)].date}</span>
                        <span>${data.data[data.data.length-1].date}</span>
                    </div>
                `;

                // 添加点击和悬停事件
                const tooltip = container.querySelector('#trendTooltip');
                container.querySelectorAll('.trend-bar').forEach(bar => {
                    bar.addEventListener('mouseenter', (e) => {
                        const rect = bar.getBoundingClientRect();
                        const containerRect = container.getBoundingClientRect();
                        tooltip.style.display = 'block';
                        tooltip.style.left = (rect.left - containerRect.left + rect.width/2 - 60) + 'px';
                        tooltip.style.top = (rect.top - containerRect.top - 50) + 'px';
                        tooltip.innerHTML = `
                            <div style="font-weight: 600; margin-bottom: 4px;">${bar.dataset.date}</div>
                            <div>总计: ${bar.dataset.total}条</div>
                            <div style="color: #4caf50;">正面: ${bar.dataset.positive}条</div>
                            <div style="color: #f44336;">负面: ${bar.dataset.negative}条 (${bar.dataset.percent}%)</div>
                            <div style="color: #999;">中性: ${bar.dataset.neutral}条</div>
                        `;
                    });
                    bar.addEventListener('mouseleave', () => {
                        tooltip.style.display = 'none';
                    });
                    bar.addEventListener('click', () => {
                        showToast(`${bar.dataset.date}: 负面占比 ${bar.dataset.percent}%`, 'info');
                    });
                });
            })
            .catch(err => {
                console.error('加载趋势图失败:', err);
                container.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">趋势图加载失败</div>';
            });
    }

    // ============================================================
    // 4. 30秒自动轮询实时同步
    // ============================================================
    function startDashboardSync() {
        // v5.9.0 不再独立30秒请求 /api/dashboard/changes；
        // 改为主轮询 dashboard/all 广播 'taikoo-poll' 事件后消费合并数据
        document.addEventListener('taikoo-poll', function(e) {
            applyDashboardChanges(e.detail || {});
        });
        // 兼容：若已有缓存数据立即应用一次
        if (window.__TAIKOO_POLL__) applyDashboardChanges(window.__TAIKOO_POLL__);
    }

    function applyDashboardChanges(data) {
        try {
            // 待审核负面数（合并字段）
            if (data.pending_negative !== undefined) {
                updateNegativeBadge(data.pending_negative);
            }
            // 今日采集数（合并字段 changes.stats）
            const stats = (data.changes && data.changes.stats) || data.stats || {};
            const todayCollected = stats.today_collected !== undefined ? stats.today_collected : stats.today;
            if (todayCollected !== undefined) {
                updateTodayCollected(todayCollected);
            }
            const lastUpdate = (data.changes && data.changes.server_time) || data.server_time;
            if (lastUpdate) UIState.dashboardLastUpdate = lastUpdate;
            document.dispatchEvent(new CustomEvent('dashboardUpdated', { detail: data }));
        } catch (err) { console.warn('dashboard sync apply failed', err); }
    }

    function syncDashboard() {
        // 兼容保留：从全局缓存读取（不再发起独立网络请求）
        if (window.__TAIKOO_POLL__) applyDashboardChanges(window.__TAIKOO_POLL__);
    }
    /* 旧实现已移除（原每30秒请求 /api/dashboard/changes，且该接口并不返回 pending_negative）
    function _legacySyncDashboard() {
        api('/api/dashboard/changes')
            .then(data => {
                if (!data.ok) return;

                // 检查是否有更新
                if (UIState.dashboardLastUpdate && data.last_update === UIState.dashboardLastUpdate) {
                    return; // 没有新数据，不更新
                }

                UIState.dashboardLastUpdate = data.last_update;

                // 更新待确认负面数量
                if (data.pending_negative !== undefined) {
                    updateNegativeBadge(data.pending_negative);
                }

                // 更新今日采集数
                if (data.today_collected !== undefined) {
                    updateTodayCollected(data.today_collected);
                }

                // 触发自定义事件，让页面其他部分可以监听
                document.dispatchEvent(new CustomEvent('dashboardUpdated', { detail: data }));
            })
            .catch(err => console.warn('仪表盘同步失败:', err));
    }
    */

    function updateNegativeBadge(count) {
        // 更新导航栏的负面确认红点
        const badge = document.querySelector('[data-badge="negative-pending"]');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }

        // 更新页面上所有显示待确认数量的元素
        document.querySelectorAll('[data-negative-pending-count]').forEach(el => {
            el.textContent = count;
        });
    }

    function updateTodayCollected(count) {
        document.querySelectorAll('[data-today-collected]').forEach(el => {
            el.textContent = count;
        });
    }

    // ============================================================
    // 5. 当日发布vs过往采集分开显示
    // ============================================================
    function loadPublishBuckets(date = null) {
        const dateStr = date || new Date().toISOString().split('T')[0];

        return api(`/api/notes/publish-buckets?date=${dateStr}`)
            .then(data => {
                if (!data.ok) return null;

                UIState.publishBuckets = data;

                // 更新页面上的分桶数据
                updatePublishBucketsUI(data);

                return data;
            })
            .catch(err => {
                console.warn('加载发布日期分桶失败:', err);
                return null;
            });
    }

    function updatePublishBucketsUI(data) {
        // 更新当日发布数量
        document.querySelectorAll('[data-published-today]').forEach(el => {
            el.textContent = data.published_today;
        });

        // 更新当日采集但历史发布数量
        document.querySelectorAll('[data-collected-today]').forEach(el => {
            el.textContent = data.collected_today;
        });

        // 如果有当日发布笔记列表容器，渲染列表
        const listContainer = document.querySelector('[data-published-notes-list]');
        if (listContainer && data.published_notes) {
            listContainer.innerHTML = data.published_notes.map(note => `
                <div class="negative-item">
                    <div style="flex: 1;">
                        <div class="negative-item-title">${escapeHtml(note.title || '无标题')}</div>
                        <div class="negative-item-meta">
                            <span class="badge ${note.sentiment === 'negative' ? 'badge-danger' : note.sentiment === 'positive' ? 'badge-success' : 'badge-info'}">
                                ${note.sentiment || '未知'}
                            </span>
                            作者：${escapeHtml(note.author_nickname || '未知')}
                            · 发布：${note.publish_date}
                            · 赞${note.likes || 0}
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }

    // ============================================================
    // 工具函数：HTML转义
    // ============================================================
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ============================================================
    // 初始化
    // ============================================================
    function initUIInteractions() {
        console.log('[v5.8.0] 前端交互补丁初始化中...');

        // 1. 检查待确认负面（页面加载后延迟2秒，避免和其他初始化冲突）
        setTimeout(checkNegativePending, 2000);

        // 2. 启动仪表盘实时同步
        startDashboardSync();

        // 3. 加载发布日期分桶
        loadPublishBuckets();

        // 4. 如果页面上有趋势图容器，自动渲染
        document.querySelectorAll('[data-trend-chart]').forEach(container => {
            const days = parseInt(container.dataset.days) || 14;
            renderTrendChart(container.id, days);
        });

        // 5. 添加负面审核入口按钮（如果页面上有占位元素）
        document.querySelectorAll('[data-negative-review-btn]').forEach(btn => {
            btn.addEventListener('click', () => showNegativeReviewPage());
        });

        console.log('[v5.8.0] 前端交互补丁初始化完成');
    }

    // 暴露到全局
    window.UIv580 = {
        checkNegativePending,
        showNegativeReviewPage,
        renderTrendChart,
        startDashboardSync,
        syncDashboard,
        loadPublishBuckets,
        confirmNegative: window.confirmNegative,
        rejectNegative: window.rejectNegative,
        showToast
    };

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUIInteractions);
    } else {
        initUIInteractions();
    }

    // ============================================================
    // v5.7.0 补充功能：周报事件、全网发现、品牌业态、AI分析、全网话题、开发者工具
    // ============================================================

    // 1. 周报事件展示
    async function loadWeeklyEvents(weekStart) {
        try {
            const url = weekStart ? `/api/weekly/events?week_start=${weekStart}` : '/api/weekly/events';
            const data = await api(url);
            if (data.ok) {
                console.log('[v5.8.0] 周报事件加载成功:', data.events?.length || 0, '条');
                return data.events || [];
            }
            return [];
        } catch (e) {
            console.error('[v5.8.0] 周报事件加载失败:', e);
            return [];
        }
    }

    // 渲染周报事件到页面
    function renderWeeklyEvents(events, containerId) {
        const container = document.getElementById(containerId) || document.querySelector('[data-weekly-events]');
        if (!container || !events || events.length === 0) return;
        
        container.innerHTML = events.map(ev => `
            <div class="event-card" data-event-id="${ev.id || ''}">
                <div class="event-level ${ev.level || 'normal'}">${ev.level || '一般'}</div>
                <div class="event-title">${ev.title || '未命名事件'}</div>
                <div class="event-meta">
                    <span>${ev.date || ''}</span>
                    <span>${ev.location || ''}</span>
                    <span>相关笔记: ${ev.note_count || 0}</span>
                </div>
                <div class="event-summary">${ev.summary || ''}</div>
            </div>
        `).join('');
    }

    // 2. 全网浏览器发现（不占用小红书检索次数）
    async function webBrowserDiscovery(keyword) {
        try {
            const url = `/api/web/browser-discovery?keyword=${encodeURIComponent(keyword || '广州太古汇')}`;
            const data = await api(url);
            if (data.ok) {
                console.log('[v5.8.0] 全网发现成功:', data.results?.length || 0, '条');
                return data.results || [];
            }
            return [];
        } catch (e) {
            console.error('[v5.8.0] 全网发现失败:', e);
            return [];
        }
    }

    // 3. 品牌业态全网监测
    async function loadBrandIndustryData(brand) {
        try {
            const url = `/api/web/brand-industry/${encodeURIComponent(brand || '广州太古汇')}`;
            const data = await api(url);
            if (data.ok) {
                console.log('[v5.8.0] 品牌业态数据加载成功');
                return data;
            }
            return null;
        } catch (e) {
            console.error('[v5.8.0] 品牌业态数据加载失败:', e);
            return null;
        }
    }

    // 4. AI提供商列表
    async function loadAIProviders() {
        try {
            const data = await api('/api/ai/providers');
            if (data.ok) {
                console.log('[v5.8.0] AI提供商加载成功:', data.providers?.length || 0, '个');
                return data.providers || [];
            }
            return [];
        } catch (e) {
            console.error('[v5.8.0] AI提供商加载失败:', e);
            return [];
        }
    }

    // AI分析v570
    async function aiAnalyzeV570(noteId, prompt, provider) {
        try {
            const data = await api('/api/ai/analyze-v570', {
                method: 'POST',
                body: JSON.stringify({ note_id: noteId, prompt, provider })
            });
            if (data.ok) {
                console.log('[v5.8.0] AI分析成功');
                return data.result;
            }
            showToast('AI分析失败: ' + (data.error || '未知错误'), 'error');
            return null;
        } catch (e) {
            console.error('[v5.8.0] AI分析失败:', e);
            showToast('AI分析请求失败', 'error');
            return null;
        }
    }

    // 渲染AI分析结果
    function renderAIResult(result, containerId) {
        const container = document.getElementById(containerId) || document.querySelector('[data-ai-result]');
        if (!container || !result) return;
        
        container.innerHTML = `
            <div class="ai-result">
                <div class="ai-result-header">
                    <span class="ai-provider">${result.provider || 'AI'}</span>
                    <span class="ai-time">${result.analyzed_at || ''}</span>
                </div>
                <div class="ai-result-content">${result.analysis || result.content || ''}</div>
                ${result.sentiment ? `<div class="ai-sentiment">情绪: ${result.sentiment}</div>` : ''}
                ${result.risk_level ? `<div class="ai-risk">风险: ${result.risk_level}</div>` : ''}
            </div>
        `;
    }

    // 5. 全网话题
    async function loadWebTopics() {
        try {
            const data = await api('/api/web-topics');
            if (data.ok) {
                console.log('[v5.8.0] 全网话题加载成功:', data.count || 0, '条');
                return data.topics || [];
            }
            return [];
        } catch (e) {
            console.error('[v5.8.0] 全网话题加载失败:', e);
            return [];
        }
    }

    // 刷新全网话题
    async function refreshWebTopics() {
        try {
            showToast('正在刷新全网话题...', 'info');
            const data = await api('/api/web-topics/refresh', { method: 'POST' });
            if (data.ok) {
                showToast(`全网话题刷新成功，共${data.count || 0}条`, 'success');
                return data.topics || [];
            }
            showToast('刷新失败', 'error');
            return [];
        } catch (e) {
            console.error('[v5.8.0] 刷新全网话题失败:', e);
            showToast('刷新请求失败', 'error');
            return [];
        }
    }

    // 渲染全网话题
    function renderWebTopics(topics, containerId) {
        const container = document.getElementById(containerId) || document.querySelector('[data-web-topics]');
        if (!container) return;
        
        if (!topics || topics.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无全网话题数据</div>';
            return;
        }
        
        container.innerHTML = topics.map(t => `
            <div class="topic-card" data-topic-url="${t.url || ''}">
                <div class="topic-title">${t.title || '无标题'}</div>
                <div class="topic-source">来源: ${t.source || 'web_search'}</div>
                <div class="topic-snippet">${(t.snippet || '').substring(0, 100)}...</div>
                ${t.url ? `<a href="${t.url}" target="_blank" class="topic-link">查看原文</a>` : ''}
            </div>
        `).join('');
    }

    // 6. 开发者工具：运行代码
    async function developerRunCode(code) {
        try {
            showToast('正在运行代码...', 'info');
            const data = await api('/api/developer/run', {
                method: 'POST',
                body: JSON.stringify({ code })
            });
            if (data.ok) {
                showToast('代码运行成功，已部署更新', 'success');
                return data;
            }
            showToast('代码运行失败: ' + (data.error || '未知错误'), 'error');
            return null;
        } catch (e) {
            console.error('[v5.8.0] 开发者工具运行失败:', e);
            showToast('运行请求失败', 'error');
            return null;
        }
    }

    // 开发者工具UI
    function showDeveloperTool() {
        const modal = document.createElement('div');
        modal.className = 'modal-backdrop';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 700px;">
                <div class="modal-header">
                    <h3 class="modal-title">${xicon('wrench')} 开发者工具 - 运行升级代码</h3>
                    <button class="modal-close">×</button>
                </div>
                <div class="modal-body">
                    <p style="color: #666; margin-bottom: 12px;">粘贴升级代码，系统将自动运行测试并部署更新。</p>
                    <textarea id="dev-code-input" style="width:100%;height:300px;font-family:monospace;font-size:12px;padding:12px;border:1px solid #ddd;border-radius:8px;resize:vertical;" placeholder="在此粘贴Python/JS升级代码..."></textarea>
                    <div id="dev-result" style="margin-top:12px;display:none;"></div>
                </div>
                <div class="modal-footer" style="margin-top:16px;display:flex;justify-content:flex-end;gap:8px;">
                    <button class="btn btn-secondary" id="dev-cancel">取消</button>
                    <button class="btn btn-primary" id="dev-run">运行并部署</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        modal.querySelector('.modal-close').onclick = () => modal.remove();
        modal.querySelector('#dev-cancel').onclick = () => modal.remove();
        modal.querySelector('#dev-run').onclick = async () => {
            const code = modal.querySelector('#dev-code-input').value;
            if (!code.trim()) {
                showToast('请输入代码', 'error');
                return;
            }
            const result = await developerRunCode(code);
            const resultDiv = modal.querySelector('#dev-result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `<pre style="background:#f5f5f5;padding:12px;border-radius:8px;max-height:200px;overflow:auto;">${JSON.stringify(result, null, 2)}</pre>`;
        };
    }

    // 绑定开发者工具入口
    document.querySelectorAll('[data-developer-tool]').forEach(btn => {
        btn.addEventListener('click', showDeveloperTool);
    });

    // 绑定全网话题刷新按钮
    document.querySelectorAll('[data-refresh-topics]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const topics = await refreshWebTopics();
            renderWebTopics(topics, 'web-topics-container');
        });
    });

    // 页面加载后自动加载全网话题
    setTimeout(async () => {
        const topics = await loadWebTopics();
        if (topics.length > 0) {
            renderWebTopics(topics, 'web-topics-container');
        }
    }, 2000);

    // 更新全局暴露
    Object.assign(window.UIv580, {
        loadWeeklyEvents,
        renderWeeklyEvents,
        webBrowserDiscovery,
        loadBrandIndustryData,
        loadAIProviders,
        aiAnalyzeV570,
        renderAIResult,
        loadWebTopics,
        refreshWebTopics,
        renderWebTopics,
        developerRunCode,
        showDeveloperTool
    });

    console.log('[v5.8.0] 补充功能（周报/全网/AI/开发者工具）已加载');

})();
