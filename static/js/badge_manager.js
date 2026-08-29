/**
 * 红点提醒管理模块 v1.0
 * 功能：
 * 1. 自动加载未读告警数量，更新顶部铃铛和侧边栏红点
 * 2. 看过（标记已读）后红点自动消失或数量减少
 * 3. 有新推送时红点自动出现
 * 4. 数量显示准确
 * 5. 负面确认待审核数量也显示红点
 * 6. 每30秒自动刷新
 */

const BadgeManager = {
    alertUnreadCount: 0,
    negativePendingCount: 0,
    refreshTimer: null,
    initialized: false,

    /**
     * 初始化红点管理
     */
    init() {
        if (this.initialized) return;
        this.initialized = true;
        // v5.9.0 不再每60秒独立请求 alerts + negative/pending；
        // 由主轮询 dashboard/all 广播的 'taikoo-poll' 合并数据驱动
        document.addEventListener('taikoo-poll', (e) => {
            this.applyFromPoll(e.detail || {});
        });
        if (window.__TAIKOO_POLL__) this.applyFromPoll(window.__TAIKOO_POLL__);
        // 首次兜底拉取一次（之后靠主轮询）
        this.refreshAll();
        console.log('[BadgeManager] 红点提醒管理已初始化（事件驱动）');
    },

    /**
     * 从主轮询合并数据更新红点（零额外请求）
     */
    applyFromPoll(data) {
        try {
            if (typeof data.unread_alerts === 'number') {
                this.alertUnreadCount = data.unread_alerts;
                this.updateAlertBadge();
            }
            if (typeof data.pending_negative === 'number') {
                this.negativePendingCount = data.pending_negative;
                this.updateNegativeBadge();
            }
        } catch (e) { /* 静默 */ }
    },

    /**
     * 刷新所有红点
     */
    async refreshAll() {
        await Promise.all([
            this.refreshAlertBadge(),
            this.refreshNegativeBadge()
        ]);
    },

    /**
     * 刷新告警红点（顶部铃铛 + 侧边栏风险预警）
     */
    async refreshAlertBadge() {
        try {
            const response = await fetch('/api/alerts?unread=1', {
                headers: { 'Authorization': 'Basic ' + btoa('Zachary:ID082610') }
            });
            const data = await response.json();
            if (data.ok) {
                this.alertUnreadCount = data.unread_count || 0;
                this.updateAlertBadge();
            }
        } catch (e) {
            console.warn('[BadgeManager] 刷新告警红点失败:', e);
        }
    },

    /**
     * 刷新负面确认红点（侧边栏负面确认）
     */
    async refreshNegativeBadge() {
        try {
            const response = await fetch('/api/negative/pending?page=1&page_size=1', {
                headers: { 'Authorization': 'Basic ' + btoa('Zachary:ID082610') }
            });
            const data = await response.json();
            if (data.ok) {
                this.negativePendingCount = data.total || 0;
                this.updateNegativeBadge();
            }
        } catch (e) {
            // 负面确认API可能不存在，静默失败
            this.negativePendingCount = 0;
            this.updateNegativeBadge();
        }
    },

    /**
     * 更新告警红点显示
     */
    updateAlertBadge() {
        const count = this.alertUnreadCount;

        // 顶部铃铛badge
        const alertBadge = document.getElementById('alertBadge');
        if (alertBadge) {
            if (count > 0) {
                alertBadge.textContent = count > 99 ? '99+' : count;
                alertBadge.style.display = 'inline-flex';
            } else {
                alertBadge.style.display = 'none';
            }
        }

        // 侧边栏风险预警badge
        const sideRisk = document.getElementById('sideRisk');
        if (sideRisk) {
            if (count > 0) {
                sideRisk.textContent = count > 99 ? '99+' : count;
                sideRisk.style.display = 'inline-flex';
            } else {
                sideRisk.style.display = 'none';
            }
        }
    },

    /**
     * 更新负面确认红点显示
     */
    updateNegativeBadge() {
        const count = this.negativePendingCount;

        // 侧边栏负面确认badge
        const sideNegative = document.getElementById('sideNegative');
        if (sideNegative) {
            if (count > 0) {
                sideNegative.textContent = count > 99 ? '99+' : count;
                sideNegative.style.display = 'inline-flex';
            } else {
                sideNegative.style.display = 'none';
            }
        }
    },

    /**
     * 标记单个告警为已读
     */
    async markAlertRead(alertId, noteId) {
        try {
            const response = await fetch('/api/alerts/read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic ' + btoa('Zachary:ID082610')
                },
                body: JSON.stringify({ alert_id: alertId || noteId })
            });
            const data = await response.json();
            if (data.ok) {
                this.alertUnreadCount = data.unread_count || 0;
                this.updateAlertBadge();
            }
        } catch (e) {
            console.warn('[BadgeManager] 标记已读失败:', e);
        }
    },

    /**
     * 标记所有告警为已读
     */
    async markAllAlertsRead() {
        try {
            const response = await fetch('/api/alerts/read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic ' + btoa('Zachary:ID082610')
                },
                body: JSON.stringify({ all: true })
            });
            const data = await response.json();
            if (data.ok) {
                this.alertUnreadCount = data.unread_count || 0;
                this.updateAlertBadge();
            }
        } catch (e) {
            console.warn('[BadgeManager] 标记全部已读失败:', e);
        }
    },

    /**
     * 刷新告警（检查新告警）
     */
    async refreshAlerts() {
        try {
            const response = await fetch('/api/alerts/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic ' + btoa('Zachary:ID082610')
                }
            });
            const data = await response.json();
            if (data.ok && data.new_alerts > 0) {
                // 有新告警，刷新红点
                await this.refreshAlertBadge();
            }
            return data;
        } catch (e) {
            console.warn('[BadgeManager] 刷新告警失败:', e);
            return null;
        }
    },

    /**
     * 确认负面笔记
     */
    async confirmNegative(noteId) {
        try {
            const response = await fetch('/api/negative/confirm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic ' + btoa('Zachary:ID082610')
                },
                body: JSON.stringify({ note_id: noteId })
            });
            const data = await response.json();
            if (data.ok) {
                await this.refreshNegativeBadge();
            }
            return data;
        } catch (e) {
            console.warn('[BadgeManager] 确认负面笔记失败:', e);
            return null;
        }
    },

    /**
     * 驳回负面笔记
     */
    async rejectNegative(noteId) {
        try {
            const response = await fetch('/api/negative/reject', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic ' + btoa('Zachary:ID082610')
                },
                body: JSON.stringify({ note_id: noteId })
            });
            const data = await response.json();
            if (data.ok) {
                await this.refreshNegativeBadge();
            }
            return data;
        } catch (e) {
            console.warn('[BadgeManager] 驳回负面笔记失败:', e);
            return null;
        }
    }
};

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => BadgeManager.init());
} else {
    BadgeManager.init();
}

// 暴露到全局
window.BadgeManager = BadgeManager;

console.log('[BadgeManager] 红点提醒管理模块已加载');
