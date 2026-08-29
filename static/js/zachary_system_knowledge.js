/**
 * Zachary 系统知识增强模块 v1.0
 * 让Zachary了解系统架构、功能、状态，能够查询并回答系统相关问题
 * 
 * 学习内容：
 * 1. 5层闭环架构
 * 2. 评测体系
 * 3. 系统功能模块
 * 4. 系统状态查询
 * 5. 操作指引
 */

const ZacharySystemKnowledge = {
    // 系统架构知识
    architecture: {
        name: '广州太古汇舆情监测系统',
        version: 'v5.9.0',
        layers: [
            {
                level: 1,
                name: '自动调节引擎',
                icon: '⚙️',
                description: '根据采集成功率、失败率、响应时间、登录态、风控迹象等7个指标，动态调整请求间隔、重试次数、并发数、暂停时间、下次采集时间等5个参数',
                status: 'running',
                api: '/api/adaptive/status'
            },
            {
                level: 2,
                name: '自动修复引擎',
                icon: '🔧',
                description: '健康检查→异常检测→判断→修复→验证→记录。支持6类自动修复（进程崩溃/网络失败/数据库断开/任务超时/推送失败/API错误）和6类需人工介入（数据库结构/过滤规则/风险逻辑/数据删除/账号失效/风控机制）',
                status: 'running',
                api: '/api/recovery/stats'
            },
            {
                level: 3,
                name: '数据闭环引擎',
                icon: '🔄',
                description: '正向流程：采集→清洗→过滤→去重→入库→事件聚合→风险识别→舆情分析→报告→推送。反向反馈：报告结果→发现异常→反馈采集/规则层→调整策略→下轮验证',
                status: 'running',
                api: '/api/feedback/stats'
            },
            {
                level: 4,
                name: '系统控制中心',
                icon: '📊',
                description: '统一监控面板，实时显示10个模块状态（采集器/登录态/数据库/去重/主体过滤/风险引擎/报告生成/微信推送/邮件推送/定时任务）+采集调度+自适应状态+异常告警',
                status: 'running',
                api: '/api/system/health/detailed'
            },
            {
                level: 5,
                name: '边界控制引擎',
                icon: '🛡️',
                description: '区分可自动修和需人工介入，防止越修越坏。10种操作安全分级，自动修复前备份，最多重试3次，文件完整性校验，人工确认流程',
                status: 'running',
                api: '/api/boundary/stats'
            }
        ]
    },

    // 系统功能模块
    modules: {
        collection: {
            name: '舆情采集',
            icon: '📥',
            description: '通过CDP浏览器连接小红书，采集广州太古汇相关舆情笔记。每日自动采集9次（8/10/12/14/16/18/20/22/23点），手动采集3次机会',
            features: ['小红书采集', 'CDP浏览器连接', '自动调度', '手动触发', 'Cookie持久化']
        },
        analysis: {
            name: '舆情分析',
            icon: '🔍',
            description: '对采集的笔记进行情绪分析、事件分类、品牌识别、主体过滤、去重处理',
            features: ['情绪分析（正面/负面/中性）', '事件分类', '品牌识别', '主体过滤', '去重处理']
        },
        report: {
            name: '报告生成',
            icon: '📋',
            description: '生成日报、周报、月报、年报，支持Word和Excel导出，严格按照太古汇汇报模板',
            features: ['日报（00:00-24:00）', '周报（自然周周一到周日）', '月报（自然月1号到月底）', '年报（自然年1.1-12.31）', 'Word/Excel导出']
        },
        push: {
            name: '推送通知',
            icon: '📢',
            description: '日报弹窗推送、邮件推送、微信推送（待配置）',
            features: ['日报弹窗（当日发布vs过往采集分开）', '邮件推送（每日9点）', '微信通知中心（待配置）', '高风险立即推送']
        },
        ai: {
            name: 'AI辅助',
            icon: '🤖',
            description: 'AI分析舆情、生成摘要、推荐话术、案例对标。支持豆包/GPT/Trae（待配置API Key）',
            features: ['AI舆情分析', '智能摘要生成', '公关话术推荐', '案例对标', '本地AI对接（Ollama）']
        },
        zachary: {
            name: 'Zachary智能助手',
            icon: '🤖',
            description: '我就是Zachary，广州太古汇舆情系统的智能助手。可以帮你查询实时舆情数据、解读风险事件、说明系统架构和功能模块、生成报告摘要、分析品牌业态分布',
            features: ['实时数据查询', '风险事件解读', '系统功能说明', '报告摘要生成', '品牌分析', '操作指引']
        },
        evaluation: {
            name: '评测体系',
            icon: '📝',
            description: '8大评测维度（采集质量/分析质量/报告质量/推送质量/系统稳定性/安全合规/路由专项/标注质量），Badcase库，Golden Case回归测试，周度汇总',
            features: ['8维度评测', 'Badcase管理', 'Golden Case回归', '周度汇总', '评测集5分类']
        }
    },

    // 常见问题回答
    faq: {
        '系统架构': '我们的系统采用5层闭环架构：1️⃣自动调节引擎（动态调整采集策略）、2️⃣自动修复引擎（异常自动检测修复）、3️⃣数据闭环引擎（正向采集+反向反馈）、4️⃣系统控制中心（10模块状态监控）、5️⃣边界控制引擎（安全操作分级）。每层都有独立的API可以查询状态。',
        '怎么采集': '点击右上角"采集数据"按钮可以手动触发采集，每日有3次手动机会。系统每天会在8/10/12/14/16/18/20/22/23点自动采集9次。采集通过CDP浏览器连接小红书，需要保持浏览器登录状态。',
        '怎么看报告': '点击右上角"导出报告"按钮，可以选择日报、周报、月报、年报。日报是当天00:00-24:00的舆情，周报是自然周周一到周日，月报是自然月，年报是自然年。报告支持Word和Excel格式导出。',
        '负面确认': '系统检测到的负面舆情需要二次确认。可以通过负面确认弹窗查看待确认列表，点击"确认负面"或"驳回"。只有二次确认的负面笔记才会进入周报、月报、年报。日报弹窗会优先推送待确认的负面笔记。',
        '系统稳定吗': '系统采用5层闭环架构保障稳定性：自动调节引擎会根据采集情况动态调整策略，自动修复引擎会检测并自动修复进程崩溃、网络失败等问题，系统控制中心实时监控10个模块状态，边界控制引擎确保操作安全。系统还支持开机自启动和进程守护。',
        'Zachary能做什么': '我是Zachary，你的舆情智能助手。我可以：1️⃣查询实时舆情数据和趋势、2️⃣解读风险事件和预警、3️⃣说明系统架构和功能模块、4️⃣生成日报/周报/月报摘要、5️⃣分析品牌业态分布、6️⃣提供操作指引。有什么可以帮你的？',
        '评测体系': '我们有完整的评测体系，包含8大维度：采集质量、分析质量、报告质量、推送质量、系统稳定性、安全合规、路由专项、标注质量。还有Badcase库沉淀问题案例，Golden Case用于回归测试，每周生成周度汇总。评测集分为开发集、回归集、盲测集、安全集、线上回流集5类。',
        '数据安全吗': '系统采用边界控制引擎保障数据安全：10种操作分为4个安全等级（安全/谨慎/需确认/禁止），涉及数据删除和规则修改的操作必须人工确认，自动修复前会备份数据库，文件完整性校验防止篡改，完整操作日志可审计。'
    },

    // 系统状态查询
    async getSystemStatus() {
        try {
            const response = await fetch('/api/architecture/status', {
                headers: { 'Authorization': 'Basic ' + btoa('Zachary:ID082610') }
            });
            const data = await response.json();
            return data.ok ? data : null;
        } catch (e) {
            console.error('获取系统状态失败:', e);
            return null;
        }
    },

    async getHealthStatus() {
        try {
            const response = await fetch('/api/system/health/detailed', {
                headers: { 'Authorization': 'Basic ' + btoa('Zachary:ID082610') }
            });
            const data = await response.json();
            return data.ok ? data : null;
        } catch (e) {
            console.error('获取健康状态失败:', e);
            return null;
        }
    },

    // 智能回答
    async answer(question) {
        const q = question.toLowerCase();

        // 匹配FAQ
        for (const [key, answer] of Object.entries(this.faq)) {
            if (q.includes(key)) {
                return answer;
            }
        }

        // 系统状态相关问题
        if (q.includes('状态') || q.includes('运行') || q.includes('正常吗') || q.includes('健康')) {
            const status = await this.getSystemStatus();
            if (status) {
                const layers = status.layers || {};
                return `当前系统整体状态：${status.overall_status === 'running' ? '✅ 运行中' : '⚠️ 异常'}\n\n` +
                    `5层架构状态：\n` +
                    `1️⃣ 自动调节引擎：${layers.layer1_adaptive?.current_strategy || '未知'}\n` +
                    `2️⃣ 自动修复引擎：总检查${layers.layer2_recovery?.stats?.total_checks || 0}次，成功修复${layers.layer2_recovery?.stats?.successful_fixes || 0}次\n` +
                    `3️⃣ 数据闭环引擎：总反馈${layers.layer3_feedback?.stats?.total_feedback || 0}条\n` +
                    `4️⃣ 系统控制中心：${layers.layer4_health?.status || '运行中'}\n` +
                    `5️⃣ 边界控制引擎：待确认${layers.layer5_boundary?.stats?.total_pending_confirmations || 0}个操作`;
            }
            return '抱歉，暂时无法获取系统状态，请稍后再试。';
        }

        // 采集相关问题
        if (q.includes('采集') || q.includes('数据') || q.includes('笔记')) {
            const health = await this.getHealthStatus();
            if (health) {
                const db = health.modules?.database || {};
                const collector = health.modules?.collector || {};
                const schedule = health.collection_schedule || {};
                return `当前采集情况：\n` +
                    `📊 笔记总数：${db.notes_count || 0}条\n` +
                    `📅 今日采集：${db.recent_24h || 0}条\n` +
                    `🔄 采集器状态：${collector.status || '未知'}\n` +
                    `⏰ 最近采集：${schedule.last_collect || '无'}\n` +
                    `⏭️ 下次采集：${schedule.next_collect || '未知'}\n` +
                    `🎯 今日剩余次数：${schedule.remaining_runs || '未知'}`;
            }
            return '抱歉，暂时无法获取采集数据。';
        }

        // 默认回答
        return '我是Zachary，广州太古汇舆情系统的智能助手。你可以问我：\n\n' +
            '🏗️ 系统架构 - 了解5层闭环架构\n' +
            '📊 系统状态 - 查询当前运行状态\n' +
            '📥 采集数据 - 了解采集情况\n' +
            '📋 报告生成 - 了解报告功能\n' +
            '⚠️ 负面确认 - 了解二次确认机制\n' +
            '📝 评测体系 - 了解质量评测\n' +
            '🔒 数据安全 - 了解安全机制\n\n' +
            '有什么可以帮你的？';
    }
};

// 暴露到全局
window.ZacharySystemKnowledge = ZacharySystemKnowledge;

console.log('[ZacharyKnowledge] Zachary系统知识增强模块已加载');
