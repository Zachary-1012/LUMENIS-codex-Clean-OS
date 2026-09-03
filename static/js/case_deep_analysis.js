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

                    <!-- AI 智能评估（智谱增强层） -->
                    <section class="detail-section">
                        <h3 class="detail-section-title"><span class="detail-section-icon" style="background:#8e8e93">🧠</span>AI 智能评估（智谱增强层）</h3>
                        <button class="action primary" onclick="CaseDeepAnalysis.aiEvaluate('${c.case_id}')" style="margin-bottom:8px">开始 AI 评估</button>
                        <div id="aiEvaluateResult-${c.case_id}" style="font-size:13px;color:var(--muted)">对本案做 4 维评分（影响力/创新/可复制/风险）+ 推荐处置模板</div>
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
     * 处置模板推荐（学习资产：9模板 + 危机SOP）
     * 调用 /api/case-analysis/template-match
     */
    async matchTemplate() {
        const input = document.getElementById('templateMatchInput');
        const box = document.getElementById('templateMatchResults');
        if (!input || !box) return;
        const kw = (input.value || '').trim();
        if (!kw) { box.innerHTML = '<div style="font-size:12px;color:var(--muted)">请输入事件/场景关键词（如：商场商户坠楼事件舆情危机 / 品牌营销活动效果）</div>'; return; }
        box.innerHTML = '<div style="font-size:12px;color:var(--muted)">匹配中…</div>';
        try {
            const r = await fetch('/api/case-analysis/template-match?keyword=' + encodeURIComponent(kw), { headers: { 'Authorization': window.__Z_AUTH || '' } });
            const d = await r.json();
            if (!d.ok) { box.innerHTML = '<div style="font-size:12px;color:#c0392b">匹配失败: ' + (d.error || '') + '</div>'; return; }
            if (!d.templates || !d.templates.length) { box.innerHTML = '<div style="font-size:12px;color:var(--muted)">未匹配到模板，试试：危机 / 投诉 / 营销 / 活动 / 认知 / 口碑 等关键词</div>'; return; }
            let html = '';
            d.templates.forEach(t => {
                html += '<div style="border:1px solid var(--border,#eaeaea);border-radius:8px;padding:10px;margin-bottom:8px;background:var(--surface,#fff)">'
                    + '<div style="font-weight:600;font-size:13px">' + t.template_name
                    + ' <span style="color:var(--muted);font-weight:400;font-size:11px">' + (t.category || '') + ' · ' + (t.module || '') + '</span></div>'
                    + '<div style="font-size:12px;color:var(--muted);margin-top:4px">' + (t.scenario || '') + '</div>'
                    + '<div style="font-size:12px;margin-top:6px"><b>关键步骤：</b>' + (t.steps || []).join(' → ') + '</div>'
                    + '<div style="font-size:12px;margin-top:4px"><b>可量化指标：</b>' + (t.metrics || []).join('、') + '</div>'
                    + '</div>';
            });
            box.innerHTML = html;
        } catch (e) {
            box.innerHTML = '<div style="font-size:12px;color:#c0392b">请求失败: ' + (e.message || e) + '</div>';
        }
    },

    /**
     * AI 评估当前案例（智谱增强层）：4维评分 + 推荐处置模板 + 建议
     */
    async aiEvaluate(caseId) {
        const box = document.getElementById('aiEvaluateResult-' + caseId);
        if (!box) return;
        box.innerHTML = 'AI 评估中…（调用智谱，约需数秒）';
        try {
            const r = await fetch('/api/case-analysis/ai-evaluate', {
                method: 'POST',
                headers: { 'Authorization': window.__Z_AUTH || '', 'Content-Type': 'application/json' },
                body: JSON.stringify({ case_id: caseId })
            });
            const d = await r.json();
            if (!d.ok) { box.innerHTML = '<span style="color:#c0392b">评估失败: ' + (d.error || '') + '</span>'; return; }
            const ai = d.ai || {};
            const sc = ai.score || {};
            const tpls = d.templates || [];
            let html = '';
            if (ai.enabled) {
                html += '<div style="border:1px solid var(--border,#eee);border-radius:8px;padding:10px;background:var(--surface,#fff)">'
                    + '<div style="font-weight:600;margin-bottom:6px">综合评分: <span style="font-size:20px">' + (sc.overall != null ? sc.overall : '-') + '</span>/10</div>'
                    + '<div style="display:flex;gap:14px;flex-wrap:wrap;font-size:12px">'
                    + '<span>影响力 <b>' + (sc.impact != null ? sc.impact : '-') + '</b></span>'
                    + '<span>创新性 <b>' + (sc.innovation != null ? sc.innovation : '-') + '</b></span>'
                    + '<span>可复制性 <b>' + (sc.replicability != null ? sc.replicability : '-') + '</b></span>'
                    + '<span>风险系数 <b>' + (sc.risk != null ? sc.risk : '-') + '</b></span>'
                    + '</div>';
                if (ai.advice) html += '<div style="font-size:12px;margin-top:6px;color:#333"><b>AI 建议：</b>' + ai.advice + '</div>';
                html += '</div>';
            } else {
                html += '<div style="font-size:12px;color:#c0392b">AI 评估暂不可用' + (ai.error ? '：' + ai.error : '') + '，已回退本地模板匹配</div>';
            }
            if (tpls.length) {
                html += '<div style="margin-top:8px"><div style="font-weight:600;font-size:13px;margin-bottom:4px">推荐处置模板</div>';
                tpls.forEach(t => {
                    html += '<div style="font-size:12px;border:1px solid var(--border,#eee);border-radius:6px;padding:6px;margin-bottom:4px;background:var(--surface,#fff)"><b>' + t.template_name + '</b> · ' + (t.category || '') + '<br>' + (t.scenario || '') + '</div>';
                });
                html += '</div>';
            }
            box.innerHTML = html;
        } catch (e) {
            box.innerHTML = '<span style="color:#c0392b">请求失败: ' + (e.message || e) + '</span>';
        }
    },

    /**
     * 重置筛选
     */
    /**
     * 增强搜索（search-std）：用当前关键词搜外部商业案例/舆情资料，展示带来源结果
     */
    async enhanceSearch() {
        const box = document.getElementById('caseEnhanceResults');
        if (!box) return;
        const input = document.getElementById('caseAnalysisSearch');
        const kw = (input ? input.value : '').trim();
        if (!kw) { box.innerHTML = '<div style="font-size:12px;color:var(--muted)">请先在搜索框输入关键词（如：商业地产 舆情危机 公关 案例）</div>'; return; }
        box.innerHTML = '<div style="font-size:12px;color:var(--muted)">增强搜索中…（search-std · 消耗1次额度）</div>';
        try {
            const r = await fetch('/api/search/enhance', {
                method: 'POST',
                headers: { 'Authorization': window.__Z_AUTH || '', 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: kw, max_results: 5 })
            });
            const d = await r.json();
            if (!d.ok) { box.innerHTML = '<div style="font-size:12px;color:#c0392b">增强搜索失败: ' + (d.error || '') + '</div>'; return; }
            let html = '<div style="border:1px solid var(--border,#eee);border-radius:8px;padding:10px;background:var(--surface,#fff)">';
            html += '<div style="font-weight:600;font-size:13px;margin-bottom:6px;display:flex;align-items:center;gap:6px"><svg style="width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round" viewBox="0 0 24 24"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>外部增强结果（search-std）</div>';
            if (d.summary) html += '<div style="font-size:12px;color:#333;margin-bottom:6px"><b>综合摘要：</b>' + d.summary + '</div>';
            if (d.results && d.results.length) {
                d.results.forEach((r2, i) => {
                    html += '<div style="font-size:12px;border-top:1px solid #f0f0f0;padding:6px 0"><b>' + (i + 1) + '. ' + r2.title + '</b><br>'
                        + '<span style="color:#555">' + (r2.content || '').substring(0, 120) + '</span><br>'
                        + '<span style="color:var(--muted)">来源: ' + (r2.source || '') + (r2.url ? ' · <a href="' + r2.url + '" target="_blank" rel="noopener">链接</a>' : '') + '</span></div>';
                });
            } else {
                html += '<div style="font-size:12px;color:var(--muted)">无外部结果</div>';
            }
            html += '</div>';
            box.innerHTML = html;
        } catch (e) {
            box.innerHTML = '<div style="font-size:12px;color:#c0392b">请求失败: ' + (e.message || e) + '</div>';
        }
    },

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
