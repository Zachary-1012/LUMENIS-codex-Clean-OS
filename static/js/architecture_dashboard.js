/**
 * 5层闭环架构 - 前端状态面板与交互
 * v1.0
 * 功能：
 * 1. 架构状态面板 - 显示5层架构运行状态
 * 2. 系统健康状态展示 - 10模块状态
 * 3. 负面舆情二次确认交互
 * 4. 日报弹窗逻辑 - 当日发布vs过往采集分开
 * 5. 报告逻辑前端接入
 */

// 全局状态
const ArchitectureDashboard = {
    currentStatus: null,
    healthStatus: null,
    negativePending: [],
    autoRefreshTimer: null,
    initialized: false
};

// ============================================
// 1. 架构状态面板
// ============================================

/**
 * 加载架构状态
 */
async function loadArchitectureStatus() {
    try {
        const response = await fetch('/api/architecture/status', {
            headers: { 'Authorization': window.__Z_AUTH }
        });
        const data = await response.json();
        if (data.ok) {
            ArchitectureDashboard.currentStatus = data;
            renderArchitectureStatus(data);
        }
    } catch (e) {
        console.error('加载架构状态失败:', e);
    }
}

/**
 * 渲染架构状态面板
 */
function renderArchitectureStatus(data) {
    // 查找或创建架构状态面板容器
    let panel = document.getElementById('architectureStatusPanel');
    if (!panel) {
        panel = createArchitecturePanel();
    }

    const layers = data.layers || {};
    const overallStatus = data.overall_status || 'unknown';

    // 更新整体状态
    const overallEl = document.getElementById('archOverallStatus');
    if (overallEl) {
        overallEl.textContent = getStatusText(overallStatus);
        overallEl.className = 'arch-status arch-status-' + overallStatus;
    }

    // 更新各层状态
    const layerConfigs = [
        { id: 'layer1_adaptive', name: '自动调节引擎', icon: '⚙️' },
        { id: 'layer2_recovery', name: '自动修复引擎', icon: '🔧' },
        { id: 'layer3_feedback', name: '数据闭环引擎', icon: '🔄' },
        { id: 'layer4_health', name: '系统控制中心', icon: '📊' },
        { id: 'layer5_boundary', name: '边界控制引擎', icon: '🛡️' }
    ];

    layerConfigs.forEach(config => {
        const layer = layers[config.id] || {};
        const status = layer.status || 'unknown';
        const el = document.getElementById('arch-' + config.id);
        if (el) {
            el.querySelector('.arch-layer-status').textContent = getStatusText(status);
            el.querySelector('.arch-layer-status').className = 'arch-layer-status status-' + status;
        }
    });
}

/**
 * 创建架构状态面板
 */
function createArchitecturePanel() {
    const panel = document.createElement('div');
    panel.id = 'architectureStatusPanel';
    panel.className = 'architecture-panel glass';
    panel.innerHTML = `
        <div class="arch-panel-header">
            <h3>🏗️ 5层闭环架构状态</h3>
            <span id="archOverallStatus" class="arch-status">加载中...</span>
        </div>
        <div class="arch-layers">
            <div class="arch-layer" id="arch-layer1_adaptive">
                <span class="arch-layer-icon">⚙️</span>
                <span class="arch-layer-name">自动调节引擎</span>
                <span class="arch-layer-status">未知</span>
            </div>
            <div class="arch-layer" id="arch-layer2_recovery">
                <span class="arch-layer-icon">🔧</span>
                <span class="arch-layer-name">自动修复引擎</span>
                <span class="arch-layer-status">未知</span>
            </div>
            <div class="arch-layer" id="arch-layer3_feedback">
                <span class="arch-layer-icon">🔄</span>
                <span class="arch-layer-name">数据闭环引擎</span>
                <span class="arch-layer-status">未知</span>
            </div>
            <div class="arch-layer" id="arch-layer4_health">
                <span class="arch-layer-icon">📊</span>
                <span class="arch-layer-name">系统控制中心</span>
                <span class="arch-layer-status">未知</span>
            </div>
            <div class="arch-layer" id="arch-layer5_boundary">
                <span class="arch-layer-icon">🛡️</span>
                <span class="arch-layer-name">边界控制引擎</span>
                <span class="arch-layer-status">未知</span>
            </div>
        </div>
        <div class="arch-panel-footer">
            <button onclick="loadArchitectureStatus()" class="arch-refresh-btn">🔄 刷新状态</button>
            <button onclick="toggleHealthPanel()" class="arch-health-btn">📋 系统健康详情</button>
        </div>
    `;

    // 插入到侧边栏或主内容区
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.appendChild(panel);
    }

    return panel;
}

// ============================================
// 2. 系统健康状态面板
// ============================================

/**
 * 加载系统健康状态
 */
async function loadHealthStatus() {
    try {
        const response = await fetch('/api/system/health/detailed', {
            headers: { 'Authorization': window.__Z_AUTH }
        });
        const data = await response.json();
        if (data.ok) {
            ArchitectureDashboard.healthStatus = data;
            renderHealthStatus(data);
        }
    } catch (e) {
        console.error('加载系统健康状态失败:', e);
    }
}

/**
 * 渲染系统健康状态
 */
function renderHealthStatus(data) {
    let panel = document.getElementById('healthStatusPanel');
    if (!panel) {
        panel = createHealthPanel();
    }

    const modules = data.modules || {};
    const statusCounts = data.status_counts || {};

    // 更新统计
    const countsEl = document.getElementById('healthCounts');
    if (countsEl) {
        countsEl.innerHTML = `
            <span class="health-count ok">✅ ${statusCounts.ok || 0}</span>
            <span class="health-count warning">⚠️ ${statusCounts.warning || 0}</span>
            <span class="health-count error">❌ ${statusCounts.error || 0}</span>
        `;
    }

    // 更新各模块状态
    const moduleConfigs = [
        { key: 'collector', name: '采集器' },
        { key: 'login_status', name: '登录态' },
        { key: 'database', name: '数据库' },
        { key: 'dedup', name: '去重模块' },
        { key: 'subject_filter', name: '主体过滤' },
        { key: 'risk_engine', name: '风险引擎' },
        { key: 'report_generator', name: '报告生成' },
        { key: 'wechat_push', name: '微信推送' },
        { key: 'email_push', name: '邮件推送' },
        { key: 'scheduler', name: '定时任务' }
    ];

    const modulesList = document.getElementById('healthModulesList');
    if (modulesList) {
        modulesList.innerHTML = moduleConfigs.map(config => {
            const module = modules[config.key] || {};
            const status = module.status || 'unknown';
            const statusIcon = status === 'ok' ? '✅' : status === 'warning' ? '⚠️' : status === 'error' ? '❌' : '❓';
            return `<div class="health-module">
                <span class="health-module-icon">${statusIcon}</span>
                <span class="health-module-name">${config.name}</span>
                <span class="health-module-status status-${status}">${getStatusText(status)}</span>
            </div>`;
        }).join('');
    }

    // 更新采集调度
    const schedule = data.collection_schedule || {};
    const scheduleEl = document.getElementById('healthSchedule');
    if (scheduleEl) {
        scheduleEl.innerHTML = `
            <div>最近采集: ${schedule.last_collect || '无'}</div>
            <div>下次采集: ${schedule.next_collect || '未知'}</div>
            <div>今日采集: ${schedule.today_collected_notes || 0}条</div>
            <div>剩余次数: ${schedule.remaining_runs || '未知'}</div>
        `;
    }
}

/**
 * 创建系统健康面板
 */
function createHealthPanel() {
    const panel = document.createElement('div');
    panel.id = 'healthStatusPanel';
    panel.className = 'health-panel modal';
    panel.style.display = 'none';
    panel.innerHTML = `
        <div class="health-panel-content glass">
            <div class="health-panel-header">
                <h3>📊 系统健康状态</h3>
                <button onclick="toggleHealthPanel()" class="health-close-btn">✕</button>
            </div>
            <div class="health-panel-body">
                <div class="health-section">
                    <h4>模块状态统计</h4>
                    <div id="healthCounts" class="health-counts">加载中...</div>
                </div>
                <div class="health-section">
                    <h4>10模块状态</h4>
                    <div id="healthModulesList" class="health-modules-list">加载中...</div>
                </div>
                <div class="health-section">
                    <h4>采集调度</h4>
                    <div id="healthSchedule" class="health-schedule">加载中...</div>
                </div>
                <div class="health-section">
                    <h4>异常告警</h4>
                    <div id="healthAlerts" class="health-alerts">暂无告警</div>
                </div>
            </div>
            <div class="health-panel-footer">
                <button onclick="loadHealthStatus()" class="health-refresh-btn">🔄 刷新</button>
                <button onclick="runRecoveryCycle()" class="health-recovery-btn">🔧 执行自动修复</button>
            </div>
        </div>
    `;
    document.body.appendChild(panel);
    return panel;
}

/**
 * 切换健康面板显示
 */
function toggleHealthPanel() {
    const panel = document.getElementById('healthStatusPanel');
    if (panel) {
        if (panel.style.display === 'none') {
            panel.style.display = 'flex';
            loadHealthStatus();
        } else {
            panel.style.display = 'none';
        }
    }
}

// ============================================
// 3. 负面舆情二次确认交互
// ============================================

/**
 * 加载待确认负面笔记
 */
async function loadPendingNegative() {
    try {
        const response = await fetch('/api/negative/pending?page=1&page_size=20', {
            headers: { 'Authorization': window.__Z_AUTH }
        });
        const data = await response.json();
        if (data.ok) {
            ArchitectureDashboard.negativePending = data.notes || data.data || [];
            renderNegativePending();
        }
    } catch (e) {
        console.error('加载待确认负面笔记失败:', e);
    }
}

/**
 * 渲染待确认负面笔记
 */
function renderNegativePending() {
    const container = document.getElementById('negativePendingList');
    if (!container) return;

    const notes = ArchitectureDashboard.negativePending;
    if (notes.length === 0) {
        container.innerHTML = '<div class="negative-empty">✅ 暂无待确认的负面笔记</div>';
        return;
    }

    container.innerHTML = notes.map(note => `
        <div class="negative-note-item" data-id="${note.id || note.note_id}">
            <div class="negative-note-header">
                <span class="negative-note-title">${note.title || '无标题'}</span>
                <span class="negative-note-date">${note.publish_date || note.collected_at || ''}</span>
            </div>
            <div class="negative-note-content">${(note.content || '').substring(0, 100)}...</div>
            <div class="negative-note-actions">
                <button onclick="confirmNegative('${note.id || note.note_id}')" class="negative-confirm-btn">✅ 确认负面</button>
                <button onclick="rejectNegative('${note.id || note.note_id}')" class="negative-reject-btn">❌ 驳回</button>
                <button onclick="viewNoteDetail('${note.id || note.note_id}')" class="negative-view-btn">👁️ 查看详情</button>
            </div>
        </div>
    `).join('');
}

/**
 * 确认负面笔记
 */
async function confirmNegative(noteId) {
    try {
        const response = await fetch('/api/negative/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': window.__Z_AUTH
            },
            body: JSON.stringify({ note_id: noteId, confirmed_by: 'admin' })
        });
        const data = await response.json();
        if (data.ok) {
            showToast('✅ 已确认负面笔记');
            loadPendingNegative();
        } else {
            showToast('❌ 确认失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        showToast('❌ 确认失败: ' + e.message);
    }
}

/**
 * 驳回负面笔记
 */
async function rejectNegative(noteId) {
    try {
        const response = await fetch('/api/negative/reject', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': window.__Z_AUTH
            },
            body: JSON.stringify({ note_id: noteId, rejected_by: 'admin', reason: '人工审核驳回' })
        });
        const data = await response.json();
        if (data.ok) {
            showToast('✅ 已驳回负面笔记');
            loadPendingNegative();
        } else {
            showToast('❌ 驳回失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        showToast('❌ 驳回失败: ' + e.message);
    }
}

/**
 * 显示负面确认弹窗
 */
function showNegativeModal() {
    let modal = document.getElementById('negativeModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'negativeModal';
        modal.className = 'negative-modal modal';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="negative-modal-content glass">
                <div class="negative-modal-header">
                    <h3>⚠️ 负面舆情二次确认</h3>
                    <button onclick="closeNegativeModal()" class="negative-close-btn">✕</button>
                </div>
                <div class="negative-modal-body">
                    <div class="negative-stats">
                        <span>待确认: <b id="negativePendingCount">0</b></span>
                        <span>已确认: <b id="negativeConfirmedCount">0</b></span>
                        <span>已驳回: <b id="negativeRejectedCount">0</b></span>
                    </div>
                    <div id="negativePendingList" class="negative-pending-list">加载中...</div>
                </div>
                <div class="negative-modal-footer">
                    <button onclick="loadPendingNegative()" class="negative-refresh-btn">🔄 刷新</button>
                    <button onclick="closeNegativeModal()" class="negative-close-btn2">关闭</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    modal.style.display = 'flex';
    loadPendingNegative();
    loadNegativeStats();
}

/**
 * 关闭负面确认弹窗
 */
function closeNegativeModal() {
    const modal = document.getElementById('negativeModal');
    if (modal) modal.style.display = 'none';
}

/**
 * 加载负面统计
 */
async function loadNegativeStats() {
    try {
        const response = await fetch('/api/negative/stats', {
            headers: { 'Authorization': window.__Z_AUTH }
        });
        const data = await response.json();
        if (data.ok) {
            document.getElementById('negativePendingCount').textContent = data.pending || 0;
            document.getElementById('negativeConfirmedCount').textContent = data.confirmed || 0;
            document.getElementById('negativeRejectedCount').textContent = data.rejected || 0;
        }
    } catch (e) {
        console.error('加载负面统计失败:', e);
    }
}

// ============================================
// 4. 日报弹窗逻辑 - 当日发布vs过往采集分开
// ============================================

/**
 * 显示日报弹窗（区分当日发布和过往采集）
 */
async function showDailyReportModal(dateStr) {
    dateStr = dateStr || new Date().toISOString().split('T')[0];

    try {
        const response = await fetch(`/api/notes/publish-buckets?date=${dateStr}`, {
            headers: { 'Authorization': window.__Z_AUTH }
        });
        const data = await response.json();

        let modal = document.getElementById('dailyReportModal');
        if (!modal) {
            modal = createDailyReportModal();
        }

        const todayPublished = data.today_published || [];
        const historicalCollected = data.historical_collected || [];

        document.getElementById('dailyReportDate').textContent = dateStr;
        document.getElementById('dailyTodayCount').textContent = todayPublished.length;
        document.getElementById('dailyHistoricalCount').textContent = historicalCollected.length;

        // 渲染当日发布
        const todayList = document.getElementById('dailyTodayList');
        todayList.innerHTML = todayPublished.length === 0
            ? '<div class="daily-empty">当日暂无新发布笔记</div>'
            : todayPublished.map(note => renderDailyNoteItem(note)).join('');

        // 渲染过往采集
        const historicalList = document.getElementById('dailyHistoricalList');
        historicalList.innerHTML = historicalCollected.length === 0
            ? '<div class="daily-empty">暂无过往采集笔记</div>'
            : historicalCollected.map(note => renderDailyNoteItem(note)).join('');

        modal.style.display = 'flex';
    } catch (e) {
        console.error('加载日报弹窗失败:', e);
        showToast('❌ 加载日报失败: ' + e.message);
    }
}

/**
 * 渲染日报笔记项
 */
function renderDailyNoteItem(note) {
    const sentiment = note.sentiment || 'neutral';
    const sentimentIcon = sentiment === 'negative' ? '🔴' : sentiment === 'positive' ? '🟢' : '🟡';
    return `
        <div class="daily-note-item">
            <span class="daily-note-sentiment">${sentimentIcon}</span>
            <div class="daily-note-info">
                <div class="daily-note-title">${note.title || '无标题'}</div>
                <div class="daily-note-meta">发布: ${note.publish_date || '未知'} | 采集: ${note.collected_at || '未知'}</div>
            </div>
        </div>
    `;
}

/**
 * 创建日报弹窗
 */
function createDailyReportModal() {
    const modal = document.createElement('div');
    modal.id = 'dailyReportModal';
    modal.className = 'daily-report-modal modal';
    modal.style.display = 'none';
    modal.innerHTML = `
        <div class="daily-report-content glass">
            <div class="daily-report-header">
                <h3>📋 舆情日报 - <span id="dailyReportDate">加载中...</span></h3>
                <button onclick="closeDailyReportModal()" class="daily-close-btn">✕</button>
            </div>
            <div class="daily-report-body">
                <div class="daily-section">
                    <div class="daily-section-header">
                        <h4>🆕 当日发布笔记</h4>
                        <span class="daily-count" id="dailyTodayCount">0</span>
                    </div>
                    <div id="dailyTodayList" class="daily-notes-list">加载中...</div>
                </div>
                <div class="daily-section">
                    <div class="daily-section-header">
                        <h4>📚 过往采集笔记（历史案例）</h4>
                        <span class="daily-count" id="dailyHistoricalCount">0</span>
                    </div>
                    <div id="dailyHistoricalList" class="daily-notes-list">加载中...</div>
                </div>
            </div>
            <div class="daily-report-footer">
                <button onclick="exportDailyReport()" class="daily-export-btn">📥 导出日报</button>
                <button onclick="closeDailyReportModal()" class="daily-close-btn2">关闭</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    return modal;
}

/**
 * 关闭日报弹窗
 */
function closeDailyReportModal() {
    const modal = document.getElementById('dailyReportModal');
    if (modal) modal.style.display = 'none';
}

// ============================================
// 5. 工具函数
// ============================================

/**
 * 获取状态文本
 */
function getStatusText(status) {
    const statusMap = {
        'ok': '正常',
        'running': '运行中',
        'warning': '警告',
        'error': '异常',
        'unknown': '未知',
        'need_confirm': '待确认'
    };
    return statusMap[status] || status;
}

/**
 * 显示Toast提示
 */
function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
}

/**
 * 执行自动修复周期
 */
async function runRecoveryCycle() {
    showToast('🔧 正在执行自动修复...');
    try {
        const response = await fetch('/api/recovery/run-cycle', {
            method: 'POST',
            headers: { 'Authorization': window.__Z_AUTH }
        });
        const data = await response.json();
        if (data.ok) {
            showToast('✅ 自动修复完成');
            loadHealthStatus();
        } else {
            showToast('❌ 自动修复失败');
        }
    } catch (e) {
        showToast('❌ 自动修复失败: ' + e.message);
    }
}

/**
 * 查看笔记详情
 */
function viewNoteDetail(noteId) {
    // 跳转到笔记详情页或显示详情弹窗
    showToast('📖 查看笔记详情: ' + noteId);
}

/**
 * 导出日报
 */
function exportDailyReport() {
    showToast('📥 正在导出日报...');
    // 调用导出API
    window.open('/api/report/export?type=daily&date=' + new Date().toISOString().split('T')[0], '_blank');
}

// ============================================
// 6. 初始化与自动刷新
// ============================================

/**
 * 初始化架构面板
 */
function initArchitectureDashboard() {
    if (ArchitectureDashboard.initialized) return;

    // 加载架构状态
    loadArchitectureStatus();

    // v5.9.0 自动刷新降为60秒，且仅在架构/健康面板实际可见时才请求，避免首页常驻并发
    function _archPanelVisible() {
        const a = document.getElementById('architectureStatusPanel');
        const h = document.getElementById('healthStatusPanel');
        const visible = (el) => el && (el.offsetParent !== null || el.classList.contains('show') || el.classList.contains('open'));
        return visible(a) || visible(h);
    }
    ArchitectureDashboard.autoRefreshTimer = setInterval(() => {
        if (_archPanelVisible()) loadArchitectureStatus();
    }, 60000);

    ArchitectureDashboard.initialized = true;
    console.log('[ArchitectureDashboard] 5层闭环架构前端面板已初始化');
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initArchitectureDashboard);
} else {
    initArchitectureDashboard();
}

// 暴露全局函数
window.loadArchitectureStatus = loadArchitectureStatus;
window.toggleHealthPanel = toggleHealthPanel;
window.loadHealthStatus = loadHealthStatus;
window.runRecoveryCycle = runRecoveryCycle;
window.showNegativeModal = showNegativeModal;
window.closeNegativeModal = closeNegativeModal;
window.confirmNegative = confirmNegative;
window.rejectNegative = rejectNegative;
window.viewNoteDetail = viewNoteDetail;
window.showDailyReportModal = showDailyReportModal;
window.closeDailyReportModal = closeDailyReportModal;
window.exportDailyReport = exportDailyReport;
window.showToast = showToast;

console.log('[ArchitectureDashboard] 5层闭环架构前端脚本已加载');
