/**
 * 案例深度拆解前端模块 v1.0
 * 展示20个11维深度拆解案例，支持筛选、搜索、详情查看
 * 对接后端API：/api/case-analysis/*
 */

const CaseDeepAnalysis = {
    // 认证信息（与系统一致）
    auth: window.__Z_AUTH,
    
    // 状态
    state: {
        cases: [],
        stats: null,
        currentCase: null,
        filterType: '',
        filterIndustry: '',
        searchKeyword: '',
        loading: false,
    },

    // 类型标签颜色映射
    typeColors: {
        '品牌营销': '#007aff',
        '危机公关': '#ff3b30',
        '商业地产': '#34c759',
        '社媒平台': '#af52de',
        '产品化营销': '#ff9500',
    },

    /**
     * 初始化
     */
    async init() {
        console.log('[CaseAnalysis] 案例深度拆解模块初始化');
        await this.loadStats();
        await this.loadCases();
    },

    /**
     * 加载统计数据
     */
    async loadStats() {
        try {
            const resp = await fetch('/api/case-analysis/stats', {
                headers: { 'Authorization': this.auth }
            });
            const data = await resp.json();
            if (data.ok) {
                this.state.stats = data.data;
                this.renderStats();
            }
        } catch (e) {
            console.error('[CaseAnalysis] 加载统计失败:', e);
        }
    },

    /**
     * 加载案例列表
     */
    async loadCases() {
        this.state.loading = true;
        this.renderLoading();
        try {
            let url = '/api/case-analysis/list?limit=100';
            if (this.state.filterType) url += '&type=' + encodeURIComponent(this.state.filterType);
            if (this.state.filterIndustry) url += '&industry=' + encodeURIComponent(this.state.filterIndustry);
            
            const resp = await fetch(url, {
                headers: { 'Authorization': this.auth }
            });
            const data = await resp.json();
            if (data.ok) {
                this.state.cases = data.results || [];
                // 搜索过滤
                if (this.state.searchKeyword) {
                    const kw = this.state.searchKeyword.toLowerCase();
                    this.state.cases = this.state.cases.filter(c => 
                        (c.case_title || '').toLowerCase().includes(kw) ||
                        (c.brand || '').toLowerCase().includes(kw) ||
                        (c.big_idea || '').toLowerCase().includes(kw) ||
                        (c.challenge || '').toLowerCase().includes(kw)
                    );
                }
                this.renderCaseList();
            }
        } catch (e) {
            console.error('[CaseAnalysis] 加载案例失败:', e);
            document.getElementById('caseAnalysisList').innerHTML = 
                '<div style="padding:40px;text-align:center;color:var(--muted)">加载失败，请刷新重试</div>';
        }
        this.state.loading = false;
    },

    /**
     * 渲染统计卡片
     */
    renderStats() {
        const stats = this.state.stats;
        if (!stats) return;
        
        const byType = stats.by_type || {};
        const typeHtml = Object.entries(byType).map(([type, count]) => {
            const color = this.typeColors[type] || '#8e8e93';
            return `<div class="case-type-chip" style="border-left:3px solid ${color}" onclick="CaseDeepAnalysis.filterByType('${type}')">
                <b>${count}</b><span>${type}</span>
            </div>`;
        }).join('');

        document.getElementById('caseAnalysisStats').innerHTML = `
            <div class="case-stats-grid">
                <div class="case-stat-card">
                    <div class="case-stat-icon">📚</div>
                    <div class="case-stat-info">
                        <strong>${stats.total || 0}</strong>
                        <span>深度拆解案例</span>
                    </div>
                </div>
                <div class="case-stat-card">
                    <div class="case-stat-icon">🎯</div>
                    <div class="case-stat-info">
                        <strong>${Object.keys(byType).length}</strong>
                        <span>案例类型</span>
                    </div>
                </div>
                <div class="case-stat-card">
                    <div class="case-stat-icon">⭐</div>
                    <div class="case-stat-info">
                        <strong>${stats.avg_quality || 0}</strong>
                        <span>平均质量分</span>
                    </div>
                </div>
                <div class="case-stat-card">
                    <div class="case-stat-icon">🏢</div>
                    <div class="case-stat-info">
                        <strong>${Object.keys(stats.by_industry || {}).length}</strong>
                        <span>覆盖行业</span>
                    </div>
                </div>
            </div>
            <div class="case-type-filters">
                <span class="case-filter-label">按类型筛选：</span>
                <button class="case-filter-btn ${!this.state.filterType ? 'active' : ''}" onclick="CaseDeepAnalysis.filterByType('')">全部</button>
                ${Object.entries(byType).map(([type]) => 
                    `<button class="case-filter-btn ${this.state.filterType === type ? 'active' : ''}" onclick="CaseDeepAnalysis.filterByType('${type}')">${type}</button>`
                ).join('')}
            </div>
        `;
    },

    /**
     * 渲染案例列表
     */
    renderCaseList() {
        const list = document.getElementById('caseAnalysisList');
        const cases = this.state.cases;
        
        if (cases.length === 0) {
            list.innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted)">没有找到匹配的案例</div>';
            return;
        }

        list.innerHTML = cases.map(c => {
            const color = this.typeColors[c.case_type] || '#8e8e93';
            const successFactors = c.success_factors || [];
            const topFactor = successFactors[0] || {};
            return `
            <article class="case-card glass-card" onclick="CaseDeepAnalysis.showDetail('${c.case_id}')">
                <div class="case-card-header" style="border-left:4px solid ${color}">
                    <div class="case-card-title">
                        <span class="case-type-badge" style="background:${color}">${c.case_type || '未分类'}</span>
                        <h3>${c.case_title || ''}</h3>
                    </div>
                    <div class="case-card-meta">
                        <span class="case-brand">${c.brand || ''}</span>
                        <span class="case-year">${c.year || ''}</span>
                        <span class="case-quality" title="质量分">⭐ ${c.quality_score || 0}</span>
                    </div>
                </div>
                <div class="case-card-body">
                    <div class="case-idea">
                        <span class="case-label">核心创意</span>
                        <p>${(c.big_idea || '').substring(0, 120)}${(c.big_idea || '').length > 120 ? '...' : ''}</p>
                    </div>
                    ${topFactor.factor ? `
                    <div class="case-top-factor">
                        <span class="case-label">关键成功因素</span>
                        <div class="factor-item">
                            <span class="factor-name">${topFactor.factor}</span>
                            <span class="factor-weight">${Math.round((topFactor.weight || 0) * 100)}%</span>
                        </div>
                    </div>` : ''}
                </div>
                <div class="case-card-footer">
                    <span class="case-metric">📋 ${(c.execution || []).length} 阶段执行</span>
                    <span class="case-metric">📊 ${(c.channels || []).length} 传播渠道</span>
                    <span class="case-metric">🎯 ${(c.methodology || []).length} 方法论</span>
                    <span class="case-detail-link">查看详情 →</span>
                </div>
            </article>`;
        }).join('');
    },

    /**
     * 渲染加载状态
     */
    renderLoading() {
        document.getElementById('caseAnalysisList').innerHTML = 
            '<div style="padding:40px;text-align:center;color:var(--muted)">加载中...</div>';
    },

    /**
     * 显示案例详情
     */
    async showDetail(caseId) {
        try {
            const resp = await fetch('/api/case-analysis/detail?id=' + encodeURIComponent(caseId), {
                headers: { 'Authorization': this.auth }
            });
            const data = await resp.json();
            if (data.ok && data.data) {
                this.state.currentCase = data.data;
                this.renderDetailModal(data.data);
            }
        } catch (e) {
            console.error('[CaseAnalysis] 加载详情失败:', e);
        }
    },

    /**
     * 渲染详情弹窗
     */
    renderDetailModal(c) {
        const color = this.typeColors[c.case_type] || '#8e8e93';
        
        const executionHtml = (c.execution || []).map((e, i) => `
            <div class="detail-timeline-item">
                <div class="detail-timeline-dot" style="background:${color}">${i + 1}</div>
                <div class="detail-timeline-content">
                    <div class="detail-timeline-phase">${e.phase || ''}</div>
                    <div class="detail-timeline-name">${e.name || ''}</div>
                    <div class="detail-timeline-detail">${e.details || ''}</div>
                </div>
            </div>`).join('');

        const channelsHtml = (c.channels || []).map(ch => `
            <div class="detail-channel-item">
                <span class="detail-channel-name">${ch.channel || ''}</span>
                <span class="detail-channel-role">${ch.role || ''}</span>
            </div>`).join('');

        const factorsHtml = (c.success_factors || []).map(f => `
            <div class="detail-factor-item">
                <div class="detail-factor-header">
                    <span class="detail-factor-name">${f.factor || ''}</span>
                    <div class="detail-factor-bar">
                        <div class="detail-factor-fill" style="width:${Math.round((f.weight || 0) * 100)}%;background:${color}"></div>
                    </div>
                    <span class="detail-factor-weight">${Math.round((f.weight || 0) * 100)}%</span>
                </div>
                <div class="detail-factor-detail">${f.detail || ''}</div>
            </div>`).join('');

        const methodologyHtml = (c.methodology || []).map((m, i) => `
            <div class="detail-methodology-item">
                <div class="detail-methodology-name">📐 ${m.name || `方法论${i + 1}`}</div>
                <div class="detail-methodology-formula"><code>${m.formula || ''}</code></div>
                <div class="detail-methodology-applicability">适用：${m.applicability || ''}</div>
            </div>`).join('');

        const insightsHtml = (c.system_insights || []).map((ins, i) => `
            <div class="detail-insight-item">
                <span class="detail-insight-num">${i + 1}</span>
                <div class="detail-insight-content">
                    <div class="detail-insight-title">${ins.insight || ''}</div>
                    <div class="detail-insight-action">${ins.action || ''}</div>
                </div>
            </div>`).join('');

        const resultsHtml = c.results ? Object.entries(c.results).map(([k, v]) => `
            <div class="detail-result-item">
                <span class="detail-result-key">${k}</span>
                <span class="detail-result-value">${v}</span>
            </div>`).join('') : '';

        const awardsHtml = (c.awards || []).map(a => `
            <span class="detail-award-badge">🏆 ${a.award || ''} ${a.year ? `(${a.year})` : ''}</span>
        `).join('');

        const modalContent = `
            <div class="case-detail-modal">
                <div class="case-detail-hero" style="background:linear-gradient(135deg, ${color}22, ${color}08)">
                    <div class="case-detail-hero-top">
                        <span class="case-type-badge large" style="background:${color}">${c.case_type || ''}</span>
                        <span class="case-detail-quality">质量分 ${c.quality_score || 0}/100</span>
                    </div>
                    <h2 class="case-detail-title">${c.case_title || ''}</h2>
                    <div class="case-detail-subtitle">
                        <span>🏢 ${c.brand || ''}</span>
                        <span>📅 ${c.year || ''}</span>
                        <span>🏭 ${c.industry || ''}</span>
                        ${c.agency ? `<span>✂️ ${c.agency}</span>` : ''}
                    </div>
                </div>

                <div class="case-detail-body">
                    <!-- 核心挑战 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#ff3b30">!</span>核心挑战</h3>
                        <div class="detail-section-content">${c.challenge || ''}</div>
                    </section>

                    <!-- 策略目标 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#007aff">🎯</span>策略目标</h3>
                        <div class="detail-section-content">
                            ${c.strategy ? Object.entries(c.strategy).map(([k, v]) => 
                                `<div class="detail-strategy-item"><b>${k}：</b>${v}</div>`
                            ).join('') : ''}
                        </div>
                    </section>

                    <!-- 核心创意 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#af52de">💡</span>核心创意 Big Idea</h3>
                        <div class="detail-section-content big-idea-box">${c.big_idea || ''}</div>
                    </section>

                    <!-- 执行细节 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#34c759">⚙️</span>执行细节（${(c.execution || []).length}个阶段）</h3>
                        <div class="detail-timeline">${executionHtml}</div>
                    </section>

                    <!-- 传播渠道 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#ff9500">📡</span>传播渠道整合（${(c.channels || []).length}个渠道）</h3>
                        <div class="detail-channels-grid">${channelsHtml}</div>
                    </section>

                    <!-- 数据成果 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#5ac8fa">📊</span>数据成果</h3>
                        <div class="detail-results-grid">${resultsHtml}</div>
                        ${awardsHtml ? `<div class="detail-awards">${awardsHtml}</div>` : ''}
                    </section>

                    <!-- 成功要素 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:${color}">⭐</span>成功要素分析（带权重）</h3>
                        <div class="detail-factors-list">${factorsHtml}</div>
                    </section>

                    <!-- 可复用方法论 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#5856d6">📐</span>可复用方法论（${(c.methodology || []).length}个）</h3>
                        <div class="detail-methodology-list">${methodologyHtml}</div>
                    </section>

                    <!-- 系统启示 -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#ff2d55">🤖</span>对Z-Brand系统的启示（${(c.system_insights || []).length}条）</h3>
                        <div class="detail-insights-list">${insightsHtml}</div>
                    </section>
                </div>
            </div>
        `;

        // 使用系统的modal
        if (typeof showModal === 'function') {
            showModal('案例深度拆解', modalContent, 'large');
        } else {
            // fallback
            const modal = document.getElementById('modal');
            document.getElementById('modalContent').innerHTML = modalContent;
            modal.classList.add('show');
        }
    },

    /**
     * 按类型筛选
     */
    filterByType(type) {
        this.state.filterType = type;
        this.renderStats();
        this.loadCases();
    },

    /**
     * 搜索
     */
    search(keyword) {
        this.state.searchKeyword = keyword;
        this.loadCases();
    },

    /**
     * 重置筛选
     */
    resetFilters() {
        this.state.filterType = '';
        this.state.filterIndustry = '';
        this.state.searchKeyword = '';
        document.getElementById('caseAnalysisSearch').value = '';
        this.renderStats();
        this.loadCases();
    },
};

// 暴露到全局
window.CaseDeepAnalysis = CaseDeepAnalysis;

console.log('[CaseAnalysis] 案例深度拆解前端模块已加载');
