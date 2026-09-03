/**
 * V3.0 模块前端统一入口 v1.0
 * 包含：品牌知识库、事件关系图谱、品牌分析报告
 * 对接后端API：/api/brand-knowledge/*, /api/event-graph/*, /api/brand-report/*
 */

const V3Modules = {
    get auth() { return window.__Z_AUTH; },  // 动态获取，避免加载时快照为undefined导致401

    // ========== 品牌知识库模块 ==========
    knowledge: {
        state: { stats: null, results: [], loading: false, currentCategory: '', keyword: '' },

        async init() {
            await this.loadStats();
            await this.search('');
        },

        async loadStats() {
            try {
                const resp = await fetch('/api/brand-knowledge/stats', { headers: { 'Authorization': window.__Z_AUTH } });
                const data = await resp.json();
                if (data.data || data.ok) {
                    this.state.stats = data.data || data;
                    this.renderStats();
                }
            } catch (e) { console.error('知识库统计加载失败', e); }
        },

        async search(keyword, category = '') {
            this.state.loading = true;
            this.state.keyword = keyword;
            this.state.currentCategory = category;
            document.getElementById('kbResults').innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted)">加载中...</div>';
            try {
                let url = '/api/brand-knowledge/search?limit=50';
                if (keyword) url += '&q=' + encodeURIComponent(keyword);
                const resp = await fetch(url, { headers: { 'Authorization': window.__Z_AUTH } });
                const data = await resp.json();
                this.state.results = data.results || [];
                this.renderResults();
            } catch (e) {
                document.getElementById('kbResults').innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted)">加载失败，请刷新重试</div>';
            }
            this.state.loading = false;
        },

        renderStats() {
            const stats = this.state.stats;
            if (!stats) return;
            const byCat = stats.by_category || {};
            const colors = {
                '品牌营销': '#007aff', '危机公关': '#ff3b30', '品牌案例': '#34c759',
                '广告宣传': '#af52de', '消费者行为': '#ff9500', '舆情管理': '#5ac8fa',
                '传播策略': '#5856d6', '市场趋势': '#ff2d55'
            };
            const catHtml = Object.entries(byCat).map(([cat, count]) => {
                const color = colors[cat] || '#8e8e93';
                const active = this.state.currentCategory === cat ? 'active' : '';
                return `<button class="kb-cat-btn ${active}" style="border-left:3px solid ${color}" onclick="V3Modules.knowledge.search('', '${cat}')">
                    <b>${count}</b><span>${cat}</span>
                </button>`;
            }).join('');

            document.getElementById('kbStats').innerHTML = `
                <div class="kb-stats-grid">
                    <div class="kb-stat-card"><div class="kb-stat-icon">📚</div><div class="kb-stat-info"><strong>${stats.total || 0}</strong><span>知识条目</span></div></div>
                    <div class="kb-stat-card"><div class="kb-stat-icon">🏷️</div><div class="kb-stat-info"><strong>${Object.keys(byCat).length}</strong><span>知识分类</span></div></div>
                    <div class="kb-stat-card"><div class="kb-stat-icon">🎯</div><div class="kb-stat-info"><strong>影子板块</strong><span>AI学习知识库</span></div></div>
                    <div class="kb-stat-card"><div class="kb-stat-icon">🤖</div><div class="kb-stat-info"><strong>脱离AI</strong><span>自主分析基础</span></div></div>
                </div>
                <div class="kb-cat-filters">
                    <span class="kb-filter-label">按分类：</span>
                    <button class="kb-cat-btn ${!this.state.currentCategory ? 'active' : ''}" onclick="V3Modules.knowledge.search('', '')"><b>全部</b><span>${stats.total || 0}</span></button>
                    ${catHtml}
                </div>`;
        },

        renderResults() {
            const results = this.state.results;
            const container = document.getElementById('kbResults');
            if (results.length === 0) {
                container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted)">没有找到匹配的知识条目</div>';
                return;
            }
            const colors = {
                'brand_marketing': '#007aff', 'crisis_management': '#ff3b30', 'case_study': '#34c759',
                'advertising': '#af52de', 'consumer_behavior': '#ff9500', 'pr_management': '#5ac8fa',
                'communication': '#5856d6', 'market_trend': '#ff2d55'
            };
            container.innerHTML = results.map(item => {
                const color = colors[item.category] || '#8e8e93';
                const catName = (this.state.stats?.categories || {})[item.category] || item.category;
                return `<article class="kb-item glass-card" onclick="V3Modules.knowledge.showDetail(${item.id})">
                    <div class="kb-item-header" style="border-left:4px solid ${color}">
                        <span class="kb-type-badge" style="background:${color}">${catName}</span>
                        <h3>${item.title || ''}</h3>
                    </div>
                    <div class="kb-item-body">
                        <p>${(item.content || '').substring(0, 150)}${(item.content || '').length > 150 ? '...' : ''}</p>
                    </div>
                    <div class="kb-item-footer">
                        ${item.source ? `<span>📖 ${item.source}</span>` : ''}
                        ${item.tags ? `<span>🏷️ ${(item.tags || '').split(',').slice(0,3).join(' / ')}</span>` : ''}
                        <span class="kb-detail-link">查看详情 →</span>
                    </div>
                </article>`;
            }).join('');
        },

        async showDetail(id) {
            try {
                const resp = await fetch('/api/brand-knowledge/search?q=&limit=100', { headers: { 'Authorization': window.__Z_AUTH } });
                const data = await resp.json();
                const item = (data.results || []).find(i => i.id === id);
                if (!item) return;
                const catName = (this.state.stats?.categories || {})[item.category] || item.category;
                const html = `<div class="kb-detail">
                    <div class="kb-detail-hero">
                        <span class="kb-type-badge large">${catName}</span>
                        <h2>${item.title || ''}</h2>
                        ${item.source ? `<div class="kb-detail-meta">📖 来源：${item.source}</div>` : ''}
                        ${item.tags ? `<div class="kb-detail-meta">🏷️ 标签：${item.tags}</div>` : ''}
                    </div>
                    <div class="kb-detail-content">${(item.content || '').replace(/\n/g, '<br>')}</div>
                </div>`;
                if (typeof showModal === 'function') showModal('知识详情', html, 'large');
            } catch (e) { console.error(e); }
        }
    },

    // ========== 事件关系图谱模块 ==========
    eventGraph: {
        state: { stats: null, events: [], loading: false },

        async init() {
            await this.loadStats();
            await this.loadEvents();
            // 序境 Cross-filter：绑定事件类型/关系类型筛选源
            if (window.XJ_CrossFilter) {
                window.XJ_CrossFilter.bind(document.getElementById('page-event-graph'));
                var self = this;
                window.XJ_CrossFilter._on('event_type', function () { self.refreshEventsHighlight(); });
            }
        },

        refreshEventsHighlight() {
            // Cross-highlight：匹配当前筛选的事件卡片高亮，其余淡化
            if (!window.XJ_CrossFilter) return;
            window.XJ_CrossFilter.refresh();
        },

        async loadStats() {
            try {
                const resp = await fetch('/api/event-graph/stats', { headers: { 'Authorization': window.__Z_AUTH } });
                const data = await resp.json();
                if (data.ok) {
                    this.state.stats = data.data;
                    this.renderStats();
                }
            } catch (e) { console.error('事件图谱统计失败', e); }
        },

        async loadEvents() {
            this.state.loading = true;
            try {
                const resp = await fetch('/api/event-graph/events?limit=50', { headers: { 'Authorization': window.__Z_AUTH } });
                const data = await resp.json();
                this.state.events = data.events || [];
                this.renderEvents();
            } catch (e) {
                document.getElementById('egEvents').innerHTML = '<div style="padding:20px;color:var(--muted)">加载失败</div>';
            }
            this.state.loading = false;
        },

        renderStats() {
            const stats = this.state.stats || {};
            const byType = stats.events_by_type || {};
            const byRel = stats.relations_by_type || {};
            document.getElementById('egStats').innerHTML = `
                <div class="eg-stats-grid">
                    <div class="eg-stat-card"><div class="eg-stat-icon">📊</div><div class="eg-stat-info"><strong>${stats.total_events || 0}</strong><span>事件总数</span></div></div>
                    <div class="eg-stat-card" data-xf-dim="event_type" data-xf-value="营销事件" title="点击筛选营销事件"><div class="eg-stat-icon">📢</div><div class="eg-stat-info"><strong>${byType['营销事件'] || 0}</strong><span>营销事件</span></div></div>
                    <div class="eg-stat-card" data-xf-dim="event_type" data-xf-value="传播事件" title="点击筛选传播事件"><div class="eg-stat-icon">📡</div><div class="eg-stat-info"><strong>${byType['传播事件'] || 0}</strong><span>传播事件</span></div></div>
                    <div class="eg-stat-card" data-xf-dim="event_type" data-xf-value="舆情事件" title="点击筛选舆情事件"><div class="eg-stat-icon">⚠️</div><div class="eg-stat-info"><strong>${byType['舆情事件'] || 0}</strong><span>舆情事件</span></div></div>
                    <div class="eg-stat-card"><div class="eg-stat-icon">🔗</div><div class="eg-stat-info"><strong>${stats.total_relations || 0}</strong><span>关系总数</span></div></div>
                    <div class="eg-stat-card xf-clear" data-xf-clear="event_type" title="清除筛选" style="cursor:pointer"><div class="eg-stat-icon">✕</div><div class="eg-stat-info"><strong>清除</strong><span>筛选</span></div></div>
                </div>
                <div class="eg-legend">
                    <span><b>关系类型：</b></span>
                    <span class="eg-rel-tag xf-filter" data-xf-dim="relation" data-xf-value="trigger" style="background:#007aff;cursor:pointer">触发 trigger</span>
                    <span class="eg-rel-tag xf-filter" data-xf-dim="relation" data-xf-value="derive" style="background:#34c759;cursor:pointer">衍生 derive</span>
                    <span class="eg-rel-tag xf-filter" data-xf-dim="relation" data-xf-value="follow" style="background:#ff9500;cursor:pointer">继发 follow</span>
                    <span class="eg-rel-tag xf-filter" data-xf-dim="relation" data-xf-value="parallel" style="background:#af52de;cursor:pointer">并行 parallel</span>
                </div>`;
            // 清除筛选按钮
            var clearBtn = document.querySelector('[data-xf-clear="event_type"]');
            if (clearBtn) {
                clearBtn.addEventListener('click', function (e) {
                    e.preventDefault(); e.stopPropagation();
                    if (window.XJ_CrossFilter) window.XJ_CrossFilter.clear('event_type');
                });
            }
        },

        renderEvents() {
            const events = this.state.events;
            const container = document.getElementById('egEvents');
            if (events.length === 0) {
                container.innerHTML = `
                <div class="eg-empty glass-card">
                    <div class="eg-empty-icon">🕸️</div>
                    <h3>事件关系图谱暂无数据</h3>
                    <p>当前系统已具备事件关系图谱的后端架构和API，事件数据将在后续版本中逐步填充。</p>
                    <div class="eg-empty-info">
                        <div class="eg-empty-item"><b>三类事件：</b>营销事件 / 传播事件 / 舆情事件</div>
                        <div class="eg-empty-item"><b>四种关系：</b>触发(trigger) / 衍生(derive) / 继发(follow) / 并行(parallel)</div>
                        <div class="eg-empty-item"><b>API就绪：</b>GET /api/event-graph/stats、GET /api/event-graph/events</div>
                    </div>
                    <p style="color:var(--muted);font-size:13px;margin-top:16px">💡 后续可从舆情事件、营销活动中自动提取并构建事件关系图谱</p>
                </div>`;
                return;
            }
            const typeColors = { '营销事件': '#007aff', '传播事件': '#34c759', '舆情事件': '#ff3b30' };
            container.innerHTML = events.map(ev => {
                const color = typeColors[ev.event_type_name] || typeColors[ev.event_type] || '#8e8e93';
                const xfType = ev.event_type_name || ev.event_type || '';
                const xf = xfType ? ` data-xf-dim="event_type" data-xf-value="${xfType}"` : '';
                return `<div class="eg-event-card glass-card" style="border-left:4px solid ${color}"${xf}>
                    <div class="eg-event-header">
                        <span class="eg-type-badge" style="background:${color}">${ev.event_type || '未分类'}</span>
                        <h3>${ev.title || ev.name || '未命名事件'}</h3>
                    </div>
                    <div class="eg-event-body">
                        <p>${ev.description || ''}</p>
                        ${ev.event_date ? `<div class="eg-event-meta">📅 ${ev.event_date}</div>` : ''}
                        ${ev.relations && ev.relations.length > 0 ? `<div class="eg-event-relations"><b>关联事件：</b>${ev.relations.map(r => `<span class="eg-rel-mini" style="background:${typeColors[r.type]||'#8e8e93'}">${r.relation || r.type}</span>`).join('')}</div>` : ''}
                    </div>
                </div>`;
            }).join('');
        }
    },

    // ========== 品牌分析报告模块 ==========
    brandReport: {
        state: { generating: false, currentReport: null },

        init() {
            this.renderForm();
        },

        renderForm() {
            document.getElementById('brForm').innerHTML = `
                <div class="br-form-card glass-card">
                    <div class="br-form-header">
                        <h3>📊 生成品牌传播与市场情报报告</h3>
                        <p>从舆情监测数据自动生成多维度品牌分析报告（V3.0升级版）</p>
                    </div>
                    <div class="br-form-body">
                        <div class="br-form-row">
                            <div class="br-form-field">
                                <label>品牌名称</label>
                                <input type="text" id="brBrand" value="广州太古汇" placeholder="输入品牌名称">
                            </div>
                            <div class="br-form-field">
                                <label>报告周期（天）</label>
                                <select id="brDays">
                                    <option value="7">近7天</option>
                                    <option value="30" selected>近30天</option>
                                    <option value="90">近90天</option>
                                </select>
                            </div>
                        </div>
                        <div class="br-form-row">
                            <div class="br-form-field">
                                <label>报告维度（多选）</label>
                                <div class="br-dimensions">
                                    <label><input type="checkbox" checked> 品牌声量分析</label>
                                    <label><input type="checkbox" checked> 传播主体分析</label>
                                    <label><input type="checkbox" checked> 内容类型分布</label>
                                    <label><input type="checkbox" checked> 情绪分析</label>
                                    <label><input type="checkbox" checked> 竞品对比</label>
                                    <label><input type="checkbox" checked> 营销事件追踪</label>
                                    <label><input type="checkbox" checked> 舆情风险</label>
                                    <label><input type="checkbox" checked> 策略建议</label>
                                </div>
                            </div>
                        </div>
                        <button class="br-generate-btn" onclick="V3Modules.brandReport.generate()" id="brGenerateBtn">
                            🚀 生成报告
                        </button>
                    </div>
                </div>
                <div id="brResult"></div>`;
        },

        async generate() {
            const brand = document.getElementById('brBrand').value || '广州太古汇';
            const days = document.getElementById('brDays').value;
            const btn = document.getElementById('brGenerateBtn');
            btn.disabled = true;
            btn.innerHTML = '⏳ 正在生成报告...';
            this.state.generating = true;

            try {
                const resp = await fetch('/api/brand-report/generate', {
                    method: 'POST',
                    headers: { 'Authorization': window.__Z_AUTH, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ brand, days: parseInt(days) })
                });
                const data = await resp.json();
                if (data.ok && data.report) {
                    this.state.currentReport = data.report;
                    this.renderReport(data.report);
                } else {
                    document.getElementById('brResult').innerHTML = '<div class="br-error">报告生成失败：' + (data.error || '未知错误') + '</div>';
                }
            } catch (e) {
                document.getElementById('brResult').innerHTML = '<div class="br-error">报告生成异常：' + e.message + '</div>';
            }
            btn.disabled = false;
            btn.innerHTML = '🚀 生成报告';
            this.state.generating = false;
        },

        renderReport(report) {
            const sections = [
                { key: 'executive_summary', title: '📋 执行摘要', icon: '📋' },
                { key: 'communication_analysis', title: '📡 传播分析', icon: '📡' },
                { key: 'event_graph_analysis', title: '🕸️ 事件图谱分析', icon: '🕸️' },
                { key: 'market_intelligence', title: '📊 市场情报', icon: '📊' },
                { key: 'public_opinion_analysis', title: '💬 舆情分析', icon: '💬' },
                { key: 'recommendations', title: '💡 策略建议', icon: '💡' },
            ];
            const sectionsHtml = sections.map(s => {
                const content = report[s.key];
                const isEmpty = !content || Object.keys(content).length === 0;
                return `<div class="br-section glass-card">
                    <h3 class="br-section-title">${s.icon} ${s.title}</h3>
                    ${isEmpty ? '<div class="br-section-empty">该维度数据待填充（V3.0后续版本将接入真实舆情数据）</div>' :
                      `<div class="br-section-content">${this.renderObject(content)}</div>`}
                </div>`;
            }).join('');

            document.getElementById('brResult').innerHTML = `
                <div class="br-report-header glass-card">
                    <div class="br-report-title">
                        <span class="br-report-badge">${report.report_type || '品牌传播与市场情报报告'}</span>
                        <h2>${report.brand_name || '品牌'} · ${report.report_period || ''}</h2>
                    </div>
                    <div class="br-report-meta">
                        <div><span>报告ID</span><b>${report.report_id || '-'}</b></div>
                        <div><span>版本</span><b>${report.report_version || 'v3.0'}</b></div>
                        <div><span>生成时间</span><b>${report.generated_at || '-'}</b></div>
                    </div>
                </div>
                ${sectionsHtml}
                <div class="br-report-footer">
                    <p>📌 本报告由序境 自动生成，数据来源于系统舆情监测库。部分维度数据待后续版本填充。</p>
                </div>`;
        },

        renderObject(obj, depth = 0) {
            if (typeof obj !== 'object' || obj === null) return String(obj);
            if (Array.isArray(obj)) {
                return '<ul class="br-list">' + obj.map(item => `<li>${this.renderObject(item, depth+1)}</li>`).join('') + '</ul>';
            }
            return '<div class="br-kv">' + Object.entries(obj).map(([k, v]) =>
                `<div class="br-kv-row"><span class="br-kv-key">${k}</span><span class="br-kv-val">${this.renderObject(v, depth+1)}</span></div>`
            ).join('') + '</div>';
        }
    }
};

console.log('[V3Modules] V3.0模块前端已加载：知识库 / 事件图谱 / 品牌报告');
