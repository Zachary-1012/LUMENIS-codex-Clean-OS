/**
 * 系统功能前端接入模块 v1.0
 * 接入：安全检查、评测体系、本地AI、公关案例、采集器自动化
 * 功能：
 * 1. 安全检查面板 - 文件完整性/恶意代码扫描/敏感信息检测
 * 2. 评测体系面板 - 8维度评测/Badcase/Golden Case
 * 3. 本地AI面板 - 模型列表/情绪分析/事件分类/风险评估
 * 4. 公关案例面板 - 案例库/话术模板/ACT法则
 * 5. 采集器状态 - 自动启动CDP/状态监控
 */

const SystemFeaturesUI = {
    initialized: false,

    init() {
        if (this.initialized) return;
        this.initialized = true;
        this.createPanels();
        console.log('[SystemFeaturesUI] 系统功能前端接入已初始化');
    },

    createPanels() {
        // 在设置页面添加功能面板
        const settingsPage = document.getElementById('page-settings');
        if (!settingsPage) return;

        const panelsContainer = document.createElement('div');
        panelsContainer.className = 'system-features-panels';
        panelsContainer.innerHTML = `
            <div class="feature-section">
                <h3>🛡️ 安全检查</h3>
                <div class="feature-cards">
                    <div class="feature-card" onclick="SystemFeaturesUI.runSecurityScan()">
                        <div class="feature-icon">🔍</div>
                        <div class="feature-title">完整安全扫描</div>
                        <div class="feature-desc">文件完整性+恶意代码+敏感信息</div>
                    </div>
                    <div class="feature-card" onclick="SystemFeaturesUI.createBaseline()">
                        <div class="feature-icon">📋</div>
                        <div class="feature-title">创建完整性基线</div>
                        <div class="feature-desc">建立文件哈希基线</div>
                    </div>
                    <div class="feature-card" onclick="SystemFeaturesUI.checkIntegrity()">
                        <div class="feature-icon">✅</div>
                        <div class="feature-title">校验文件完整性</div>
                        <div class="feature-desc">对比基线检查篡改</div>
                    </div>
                </div>
                <div id="securityResult" class="feature-result"></div>
            </div>

            <div class="feature-section">
                <h3>📝 评测体系</h3>
                <div class="feature-cards">
                    <div class="feature-card" onclick="SystemFeaturesUI.runEvaluation()">
                        <div class="feature-icon">📊</div>
                        <div class="feature-title">运行完整评测</div>
                        <div class="feature-desc">8维度质量评测</div>
                    </div>
                    <div class="feature-card" onclick="SystemFeaturesUI.viewBadcases()">
                        <div class="feature-icon">⚠️</div>
                        <div class="feature-title">Badcase库</div>
                        <div class="feature-desc">问题案例沉淀</div>
                    </div>
                    <div class="feature-card" onclick="SystemFeaturesUI.viewGoldenCases()">
                        <div class="feature-icon">🏆</div>
                        <div class="feature-title">Golden Case</div>
                        <div class="feature-desc">回归测试用例</div>
                    </div>
                </div>
                <div id="evaluationResult" class="feature-result"></div>
            </div>

            <div class="feature-section">
                <h3>🤖 本地AI</h3>
                <div class="feature-cards">
                    <div class="feature-card" onclick="SystemFeaturesUI.checkLocalAI()">
                        <div class="feature-icon">🔌</div>
                        <div class="feature-title">检测本地AI</div>
                        <div class="feature-desc">检查Ollama可用性</div>
                    </div>
                    <div class="feature-card" onclick="SystemFeaturesUI.listAIModels()">
                        <div class="feature-icon">📦</div>
                        <div class="feature-title">模型列表</div>
                        <div class="feature-desc">可用本地模型</div>
                    </div>
                    <div class="feature-card" onclick="SystemFeaturesUI.testAIAnalysis()">
                        <div class="feature-icon">🧪</div>
                        <div class="feature-title">测试AI分析</div>
                        <div class="feature-desc">情绪/事件/风险分析</div>
                    </div>
                </div>
                <div id="aiResult" class="feature-result"></div>
            </div>

            <div class="feature-section">
                <h3>📚 公关案例</h3>
                <div class="feature-cards">
                    <div class="feature-card" onclick="SystemFeaturesUI.viewPRCases()">
                        <div class="feature-icon">📖</div>
                        <div class="feature-title">案例库</div>
                        <div class="feature-desc">15个全网典型案例</div>
                    </div>
                    <div class="feature-card" onclick="SystemFeaturesUI.viewPRTemplates()">
                        <div class="feature-icon">📝</div>
                        <div class="feature-title">话术模板</div>
                        <div class="feature-desc">6个场景话术模板</div>
                    </div>
                    <div class="feature-card" onclick="SystemFeaturesUI.viewACTPrinciple()">
                        <div class="feature-icon">🎯</div>
                        <div class="feature-title">ACT法则</div>
                        <div class="feature-desc">危机公关三步法</div>
                    </div>
                </div>
                <div id="prResult" class="feature-result"></div>
            </div>
        `;

        settingsPage.appendChild(panelsContainer);
        this.addStyles();
    },

    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .system-features-panels { margin-top: 20px; }
            .feature-section { margin-bottom: 24px; }
            .feature-section h3 { font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #1d1d1f; }
            .feature-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
            .feature-card { background: white; border: 1px solid #eaeef2; border-radius: 10px; padding: 16px; cursor: pointer; transition: all 0.2s; text-align: center; }
            .feature-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }
            .feature-icon { font-size: 28px; margin-bottom: 8px; }
            .feature-title { font-size: 13px; font-weight: 600; color: #1d1d1f; margin-bottom: 4px; }
            .feature-desc { font-size: 11px; color: #6e7781; }
            .feature-result { margin-top: 12px; padding: 12px; background: #f6f8fa; border-radius: 8px; font-size: 12px; display: none; }
            .feature-result.show { display: block; }
            @media (max-width: 768px) { .feature-cards { grid-template-columns: 1fr; } }
        `;
        document.head.appendChild(style);
    },

    showResult(containerId, html) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = html;
            container.classList.add('show');
        }
    },

    // 安全检查
    async runSecurityScan() {
        this.showResult('securityResult', '<div class="loading">🔄 正在执行安全扫描...</div>');
        try {
            const response = await fetch('/api/security/scan', { headers: this.getAuthHeader() });
            const data = await response.json();
            if (data.ok) {
                this.showResult('securityResult', `
                    <div><b>✅ 扫描完成</b> | 总问题: ${data.total_issues || 0} | 风险等级: ${data.overall_risk || 'low'}</div>
                    <div style="margin-top:8px">文件完整性: ${data.integrity?.issues_count || 0}个问题 | 恶意代码: ${data.dangerous_code?.findings_count || 0}个 | 敏感信息: ${data.sensitive_info?.findings_count || 0}个</div>
                `);
            } else {
                this.showResult('securityResult', `<div class="error">❌ 扫描失败: ${data.error}</div>`);
            }
        } catch (e) {
            this.showResult('securityResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    async createBaseline() {
        this.showResult('securityResult', '<div class="loading">🔄 正在创建完整性基线...</div>');
        try {
            const response = await fetch('/api/security/baseline', { method: 'POST', headers: this.getAuthHeader() });
            const data = await response.json();
            if (data.ok) {
                this.showResult('securityResult', `<div>✅ 基线已创建，共 ${data.baseline_count || 0} 个文件</div>`);
            } else {
                this.showResult('securityResult', `<div class="error">❌ 创建失败: ${data.error}</div>`);
            }
        } catch (e) {
            this.showResult('securityResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    async checkIntegrity() {
        this.showResult('securityResult', '<div class="loading">🔄 正在校验文件完整性...</div>');
        try {
            const response = await fetch('/api/security/integrity', { headers: this.getAuthHeader() });
            const data = await response.json();
            if (data.ok) {
                this.showResult('securityResult', `
                    <div><b>✅ 校验完成</b> | 状态: ${data.status} | 问题: ${data.issues_count || 0}个</div>
                    ${data.issues && data.issues.length > 0 ? `<div style="margin-top:8px">${data.issues.slice(0,5).map(i => `<div>⚠️ ${i.file}: ${i.issue}</div>`).join('')}</div>` : ''}
                `);
            } else {
                this.showResult('securityResult', `<div class="error">❌ 校验失败: ${data.error}</div>`);
            }
        } catch (e) {
            this.showResult('securityResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    // 评测体系
    async runEvaluation() {
        this.showResult('evaluationResult', '<div class="loading">🔄 正在运行完整评测...</div>');
        try {
            const response = await fetch('/api/evaluation/run', { headers: this.getAuthHeader() });
            const data = await response.json();
            if (data.ok) {
                this.showResult('evaluationResult', `
                    <div><b>✅ 评测完成</b> | 综合得分: ${data.overall_score || 0}/100 | 状态: ${data.status}</div>
                    <div style="margin-top:8px">采集质量: ${data.collection?.overall_score || 0}分 | 分析质量: ${data.analysis?.overall_score || 0}分 | 报告质量: ${data.report?.overall_score || 0}分 | 系统稳定: ${data.stability?.overall_score || 0}分</div>
                `);
            } else {
                this.showResult('evaluationResult', `<div class="error">❌ 评测失败: ${data.error}</div>`);
            }
        } catch (e) {
            this.showResult('evaluationResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    viewBadcases() {
        this.showResult('evaluationResult', '<div>📋 Badcase库：用于沉淀问题案例，支持分类查询和修复跟踪。可通过API /api/evaluation/badcases 查看。</div>');
    },

    viewGoldenCases() {
        this.showResult('evaluationResult', '<div>🏆 Golden Case：用于回归测试，确保核心功能不退化。可通过API /api/evaluation/golden-cases 查看。</div>');
    },

    // 本地AI
    async checkLocalAI() {
        this.showResult('aiResult', '<div class="loading">🔄 正在检测本地AI...</div>');
        try {
            const response = await fetch('/api/local-ai/status', { headers: this.getAuthHeader() });
            const data = await response.json();
            if (data.ok) {
                this.showResult('aiResult', `
                    <div><b>✅ 本地AI状态</b> | 可用: ${data.available ? '是' : '否'} | 默认模型: ${data.default_model || '未设置'}</div>
                    ${data.available_models && data.available_models.length > 0 ? `<div style="margin-top:8px">可用模型: ${data.available_models.join(', ')}</div>` : ''}
                `);
            } else {
                this.showResult('aiResult', `<div class="error">❌ 检测失败: ${data.error}</div>`);
            }
        } catch (e) {
            this.showResult('aiResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    async listAIModels() {
        await this.checkLocalAI();
    },

    async testAIAnalysis() {
        this.showResult('aiResult', '<div class="loading">🔄 正在测试AI分析...</div>');
        try {
            const response = await fetch('/api/local-ai/analyze', {
                method: 'POST',
                headers: { ...this.getAuthHeader(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: '测试文本：广州太古汇服务态度很好，环境不错', type: 'sentiment' })
            });
            const data = await response.json();
            if (data.ok) {
                this.showResult('aiResult', `<div><b>✅ AI分析完成</b><br><pre style="white-space:pre-wrap;margin-top:8px">${data.response || JSON.stringify(data, null, 2)}</pre></div>`);
            } else {
                this.showResult('aiResult', `<div class="error">❌ 分析失败: ${data.error}</div>`);
            }
        } catch (e) {
            this.showResult('aiResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    // 公关案例
    async viewPRCases() {
        this.showResult('prResult', '<div class="loading">🔄 正在加载案例库...</div>');
        try {
            const response = await fetch('/api/pr/cases', { headers: this.getAuthHeader() });
            const data = await response.json();
            if (data.ok) {
                this.showResult('prResult', `
                    <div><b>✅ 案例库</b> | 共 ${data.total || 0} 个案例</div>
                    <div style="margin-top:8px">${data.cases.slice(0,5).map(c => `<div>📖 ${c.title} (${c.brand} - ${c.severity})</div>`).join('')}</div>
                `);
            } else {
                this.showResult('prResult', `<div class="error">❌ 加载失败: ${data.error}</div>`);
            }
        } catch (e) {
            this.showResult('prResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    async viewPRTemplates() {
        this.showResult('prResult', '<div class="loading">🔄 正在加载话术模板...</div>');
        try {
            const response = await fetch('/api/pr/templates', { headers: this.getAuthHeader() });
            const data = await response.json();
            if (data.ok) {
                this.showResult('prResult', `
                    <div><b>✅ 话术模板</b> | 共 ${data.templates?.length || 0} 个场景</div>
                    <div style="margin-top:8px">${data.templates.map(t => `<div>📝 ${t.name}: ${t.scenario_desc}</div>`).join('')}</div>
                `);
            } else {
                this.showResult('prResult', `<div class="error">❌ 加载失败: ${data.error}</div>`);
            }
        } catch (e) {
            this.showResult('prResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    async viewACTPrinciple() {
        try {
            const response = await fetch('/api/pr/act-principle', { headers: this.getAuthHeader() });
            const data = await response.json();
            if (data.ok && data.act_principle) {
                const act = data.act_principle;
                this.showResult('prResult', `
                    <div><b>✅ ${act.name}</b> - ${act.full_name}</div>
                    <div style="margin-top:8px">${act.description}</div>
                    <div style="margin-top:8px">${act.steps.map(s => `<div><b>${s.step}</b>: ${s.description}</div>`).join('')}</div>
                `);
            }
        } catch (e) {
            this.showResult('prResult', `<div class="error">❌ 请求失败: ${e.message}</div>`);
        }
    },

    getAuthHeader() {
        return { 'Authorization': window.__Z_AUTH };
    }
};

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => SystemFeaturesUI.init());
} else {
    SystemFeaturesUI.init();
}

window.SystemFeaturesUI = SystemFeaturesUI;
console.log('[SystemFeaturesUI] 系统功能前端接入模块已加载');
