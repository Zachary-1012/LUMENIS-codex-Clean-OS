/**
 * 广州太古汇舆情监测系统 - Zachary机器人增强版
 * 黑色球体，液晶面部，荧光白/蓝表情，蓝色帽子，小耳麦，3D质感
 * 全局可拖拽，点击打开聊天弹窗，了解整个系统架构
 * 增强功能：API数据对接、系统查询、快捷问题、本地/云端AI对话
 */

(function() {
    'use strict';

    // ============================================================
    // Zachary配置
    // ============================================================
    const CONFIG = {
        size: 76,
        sizeW: 76,
        sizeH: 90,
        position: { bottom: '80px', right: '30px' },
        expressions: ['happy', 'thinking', 'speaking', 'neutral', 'surprised'],
        expressionInterval: 4000,
        hatColors: ['#57534E', '#44403C', '#78716C', '#292524'],
        wearHatProbability: 0.7,
        apiBase: '/api'
    };

    // v5.8.9 移动端浮层缩小、贴安全区，避免遮挡指标卡；尺寸/位置集中由该函数给出
    const isMobileUI = () => !!(window.matchMedia && window.matchMedia('(max-width:768px)').matches);
    function floatBox() {
        if (isMobileUI()) {
            return { w: 52, h: 52, bottom: 'calc(10px + env(safe-area-inset-bottom))', right: '10px' };
        }
        return { w: CONFIG.sizeW, h: CONFIG.sizeH, bottom: CONFIG.position.bottom, right: CONFIG.position.right };
    }

    // ============================================================
    // Zachary状态
    // ============================================================
    let state = {
        isDragging: false,
        dragOffset: { x: 0, y: 0 },
        currentExpression: 'neutral',
        chatOpen: false,
        wearHat: Math.random() < CONFIG.wearHatProbability,
        hatColor: CONFIG.hatColors[Math.floor(Math.random() * CONFIG.hatColors.length)],
        chatPosition: null
    };

    // ============================================================
    // 快捷问题
    // ============================================================
    const QUICK_QUESTIONS = [
        '今天有多少条笔记？',
        '有哪些高风险事件？',
        '今日舆情概览',
        '最近的负面笔记',
        '系统运行状态',
        '帮我生成日报'
    ];

    // ============================================================
    // 创建Zachary HTML
    // ============================================================
    function createZacharyHTML() {
        // 如果index.html中已有静态机器人元素，直接使用，不重复创建
        let container = document.getElementById('zacharyFloat');
        if (container) {
            // 确保样式正确
            const __fb = floatBox();
            container.style.cssText = `
                position: fixed;
                bottom: ${__fb.bottom};
                right: ${__fb.right};
                width: ${__fb.w}px;
                height: ${__fb.h}px;
                z-index: 9999;
                cursor: grab;
                user-select: none;
                touch-action: none;
            `;
            return container;
        }
        container = document.createElement('div');
        container.id = 'zacharyFloat';
        container.className = 'zachary-float';
        const __fb = floatBox();
        container.style.cssText = `
            position: fixed;
            bottom: ${__fb.bottom};
            right: ${__fb.right};
            width: ${__fb.w}px;
            height: ${__fb.h}px;
            z-index: 9999;
            cursor: grab;
            user-select: none;
            touch-action: none;
        `;

        const hatHTML = state.wearHat ? `<div class="zachary-hat" style="background: linear-gradient(180deg, ${state.hatColor} 0%, ${adjustColor(state.hatColor, -20)} 100%);"></div>` : '';

        container.innerHTML = `
            ${hatHTML}
            <div class="zachary-headset"></div>
            <div class="zachary-body">
                <div class="zachary-face">
                    <div class="zachary-eyes">
                        <div class="zachary-eye" id="zacharyLeftEye"></div>
                        <div class="zachary-eye" id="zacharyRightEye"></div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(container);
        return container;
    }

    // ============================================================
    // 元素兼容helper：优先静态 index.html 结构，回退动态创建的结构
    // ============================================================
    function getMessagesEl() {
        return document.getElementById('zacharyMessages') || document.getElementById('zacharyChatMessages');
    }
    function getInputEl() {
        return document.getElementById('zacharyInput') || document.getElementById('zacharyChatInput');
    }
    function getSendBtn() {
        return document.getElementById('zacharySendBtn') || document.getElementById('zacharyChatSend');
    }
    function getStaticModal() {
        return document.getElementById('zacharyChatModal');
    }

    // ============================================================
    // 创建聊天弹窗
    // ============================================================
    function createChatPanel() {
        // 如果 index.html 中已有静态聊天弹窗(zacharyChatModal)，直接复用，不重复创建
        const staticModal = getStaticModal();
        if (staticModal) {
            return staticModal;
        }
        // 兼容：若已有动态面板也直接返回
        let panel = document.getElementById('zacharyChatPanel');
        if (panel) {
            return panel;
        }
        panel = document.createElement('div');
        panel.id = 'zacharyChatPanel';
        panel.className = 'zachary-chat-panel';
        panel.style.cssText = 'display: none;';

        panel.innerHTML = `
            <div class="zachary-chat-header" id="zacharyChatHeader">
                <div class="zachary-chat-title">
                    <div class="zachary-chat-avatar">
                        <div style="width:20px;height:20px;border-radius:50%;background:#0a0a0a;display:flex;align-items:center;justify-content:center;">
                            <div style="width:8px;height:4px;background:#FAFAF9;border-radius:2px;box-shadow:0 0 4px rgba(250,250,249,.5);"></div>
                        </div>
                    </div>
                    <div>
                        <div class="zachary-chat-name">Zachary</div>
                        <div class="zachary-chat-status">● 在线</div>
                    </div>
                </div>
                <button class="zachary-chat-close" id="zacharyChatClose">×</button>
            </div>
            <div class="zachary-chat-messages" id="zacharyChatMessages">
                <div class="zachary-message bot">
                    <div class="zachary-message-avatar">Z</div>
                    <div class="zachary-message-bubble">
                        你好！我是Zachary，广州太古汇舆情监测系统的智能助手。我可以帮你查询舆情数据、分析事件、生成报告。有什么可以帮你的？
                    </div>
                </div>
            </div>
            <div class="zachary-quick-questions" id="zacharyQuickQuestions">
                ${QUICK_QUESTIONS.map(q => `<button class="zachary-quick-btn">${q}</button>`).join('')}
            </div>
            <div class="zachary-chat-input">
                <input type="text" id="zacharyChatInput" placeholder="输入你的问题..." />
                <button class="zachary-chat-send" id="zacharyChatSend">发送</button>
            </div>
        `;

        document.body.appendChild(panel);
        return panel;
    }

    // ============================================================
    // 颜色调整
    // ============================================================
    function adjustColor(color, amount) {
        const hex = color.replace('#', '');
        const r = Math.max(0, Math.min(255, parseInt(hex.substr(0, 2), 16) + amount));
        const g = Math.max(0, Math.min(255, parseInt(hex.substr(2, 2), 16) + amount));
        const b = Math.max(0, Math.min(255, parseInt(hex.substr(4, 2), 16) + amount));
        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }

    // ============================================================
    // 表情切换（NOMI风格：默认竖椭圆0 0，开心弯弧，思考/惊讶变化）
    // ============================================================
    function getEyes() {
        // 兼容静态 class 结构与动态 id 结构
        let l = document.querySelector('.zachary-eye.left') || document.getElementById('zacharyLeftEye');
        let r = document.querySelector('.zachary-eye.right') || document.getElementById('zacharyRightEye');
        return { l, r };
    }

    function switchExpression() {
        // 未指定时随机一个轻松表情
        if (!state._fixedExpr) {
            const pool = ['neutral', 'neutral', 'happy', 'blink'];
            state.currentExpression = pool[Math.floor(Math.random() * pool.length)];
        }
        applyExpression(state.currentExpression);
    }

    function applyExpression(expr) {
        state.currentExpression = expr;
        const { l, r } = getEyes();
        const exprBox = document.getElementById('zacharyExpression');
        // 同步表情容器 class（驱动 CSS 中 happy/excited/thinking 样式）
        if (exprBox) {
            exprBox.classList.remove('happy', 'excited', 'thinking', 'speaking', 'neutral', 'surprised', 'blink');
            exprBox.classList.add(expr);
        }
        if (!l || !r) return;
        // 清除内联临时样式，交给 CSS class 主导
        [l, r].forEach(e => { e.style.cssText = ''; });
        const glowWhite = '0 0 4px #e8f6ff,0 0 8px rgba(180,235,255,.8),0 0 14px rgba(80,200,255,.5)';
        switch (expr) {
            case 'happy': // 弯弯笑眼 ^ ^
                [l, r].forEach(e => {
                    e.style.width = '10px'; e.style.height = '5px';
                    e.style.borderRadius = '5px 5px 0 0';
                    e.style.background = 'transparent';
                    e.style.borderTop = '2.5px solid #e8f6ff';
                    e.style.boxShadow = '0 -2px 8px rgba(180,235,255,.7)';
                });
                break;
            case 'surprised':
            case 'excited': // 圆睁大眼
                [l, r].forEach(e => {
                    e.style.width = '9px'; e.style.height = '9px'; e.style.borderRadius = '50%';
                    e.style.background = '#fff'; e.style.border = 'none';
                    e.style.boxShadow = '0 0 6px #fff,0 0 12px rgba(200,240,255,.9),0 0 20px rgba(80,200,255,.6)';
                });
                break;
            case 'thinking': // 略微倾斜
                [l, r].forEach(e => {
                    e.style.width = '7px'; e.style.height = '10px'; e.style.borderRadius = '50%';
                    e.style.background = '#e8f6ff'; e.style.border = 'none'; e.style.boxShadow = glowWhite;
                });
                l.style.transform = 'rotate(-8deg)'; r.style.transform = 'rotate(8deg)';
                break;
            case 'blink': // 眨眼：压扁
                [l, r].forEach(e => {
                    e.style.width = '8px'; e.style.height = '2px'; e.style.borderRadius = '50%';
                    e.style.background = '#e8f6ff'; e.style.border = 'none';
                    e.style.boxShadow = '0 0 6px rgba(180,235,255,.7)';
                });
                break;
            default: // NOMI 默认竖椭圆 0 0
                [l, r].forEach(e => {
                    e.style.width = '7px'; e.style.height = '11px'; e.style.borderRadius = '45%';
                    e.style.transform = 'rotate(0deg)';
                    e.style.background = '#e8f6ff'; e.style.border = 'none'; e.style.boxShadow = glowWhite;
                });
        }
    }

    // ============================================================
    // API调用
    // ============================================================
    async function apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${CONFIG.apiBase}${endpoint}`, {
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                ...options
            });
            if (!response.ok) throw new Error(`API错误: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API调用失败:', error);
            return { error: error.message };
        }
    }

    // ============================================================
    // 智能回答
    // ============================================================
    // 时间范围解析：严格按“发布日期 publish_date”，绝不与采集时间 captured_at 混淆
    function resolveDateScope(q) {
        const pad = (n) => String(n).padStart(2, '0');
        const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        const now = new Date();
        if (/今日|今天|今早|刚刚|当日|当天|现在/.test(q)) return { start: ymd(now), end: ymd(now), label: '今日（按发布日期）' };
        if (/昨天|昨日/.test(q)) { const d = new Date(now); d.setDate(d.getDate() - 1); const z = ymd(d); return { start: z, end: z, label: '昨日（按发布日期）' }; }
        if (/前天/.test(q)) { const d = new Date(now); d.setDate(d.getDate() - 2); const z = ymd(d); return { start: z, end: z, label: '前日（按发布日期）' }; }
        return null;
    }

    // 真 AI 通道：后端 /api/ai/chat 已做“结构化检索 + 模型 + 规则兜底”，AI 仅增强、不替代系统事实
    async function askAiChat(question) {
        try {
            const r = await apiCall('/ai/chat', { method: 'POST', body: JSON.stringify({ message: question }) });
            if (r && r.ok && r.reply) return { reply: r.reply, provider: r.provider || 'ai' };
        } catch (e) { console.warn('AI chat 不可用，回退规则应答:', e); }
        return null;
    }

    // 健康检查在根路径 /healthz（不在 /api 下），单独请求
    async function getHealthz() {
        try { const r = await fetch('/healthz', { credentials: 'same-origin' }); if (r.ok) return await r.json(); } catch (e) { /* ignore */ }
        return null;
    }

    // 分析/建议/解释类信号：这类问题即便含“风险/负面”等名词，也应交给真 AI 做推理（后端会自动检索结构化数据）
    const ANALYTIC_RE = /建议|怎么看|怎么办|如何处置|如何应对|为什么|啥原因|什么原因|原因是|对策|措施|话术|方案|解读|分析一下|帮我分析|处置|应对|结论|怎么处理|如何处理/;
    // 纯名词/清单类信号：这些必须走确定性规则，数字不能交给模型编
    const LIST_RE = /多少|几条|数量|列表|有哪些|排名|分别|统计|总数|清单/;

    async function generateAnswer(question) {
        const q = (question || '').toLowerCase();
        const scope = resolveDateScope(q);
        setExpression('thinking');

        // 0) 系统状态/版本（确定性运维查询，最优先；走实时接口，禁止硬编码版本）
        if (/版本|运行状态|系统状态|服务状态|正常吗|在线吗|宕机|挂了吗/.test(q) || (/系统/.test(q) && /状态|运行|正常/.test(q))) {
            const hz = await getHealthz();
            let ai = null; try { ai = await apiCall('/ai/status'); } catch (e) { ai = null; }
            const ver = hz && hz.version ? 'v' + hz.version : '版本未知';
            const online = hz && hz.ok === true;
            const aiTxt = ai ? [ai.provider, ai.model].filter(Boolean).join(' / ') || '已配置' : '未知';
            return `系统运行状态：\n• 版本：${ver}\n• 服务：${online ? '在线' : (hz ? '异常' : '健康接口未响应')}\n• AI：${aiTxt}\n• 数据：本地实时库\n\n（以上来自实时接口，非静态文案）`;
        }

        // 1) 分析/建议/解释类 → 真 AI（纯清单提问除外，清单数字必须由规则权威给出）
        if (ANALYTIC_RE.test(q) && !LIST_RE.test(q)) {
            const ai = await askAiChat(question);
            if (ai) return ai.reply;
            // AI 不可用则继续落到下面的确定性规则
        }

        // 2) 具体情感（负面/投诉/差评）——排在“概览/今日”等宽泛词之前，避免“今日发布的负面”被概览拦截
        if (/负面|差评|投诉|吐槽|避雷|踩雷|不好|纠纷|维权/.test(q)) {
            const qs = new URLSearchParams({ sentiment: 'negative', per_page: '6' });
            if (scope) { qs.set('date_start', scope.start); qs.set('date_end', scope.end); }
            let data = await apiCall('/notes?' + qs.toString());
            let list = (data && data.notes) || [];
            if (scope && list.length === 0) {
                // 指定时间窗内为 0（真实结果，不伪造），再附带最近发布的负面作参考并明确标注
                const recent = await apiCall('/notes?sentiment=negative&per_page=3');
                const rl = (recent && recent.notes) || [];
                if (rl.length) {
                    let s = `${scope.label}未监测到负面笔记，情绪平稳。\n\n最近发布的负面（不限今日）：\n`;
                    rl.forEach((n, i) => { s += `${i + 1}. ${n.title || '无标题'}｜${(n.publish_date || '').slice(0, 10) || '日期未知'}｜${n.likes || 0}赞\n`; });
                    return s;
                }
                return `${scope.label}未监测到负面笔记，情绪平稳。`;
            }
            if (list.length) {
                let s = scope ? `${scope.label}发布的负面笔记共 ${data.total != null ? data.total : list.length} 条：\n` : '最近的负面笔记（按发布日期倒序）：\n';
                list.forEach((n, i) => { s += `${i + 1}. ${n.title || '无标题'}｜${n.risk_level === 'high' ? '高风险' : '负面'}｜${n.likes || 0}赞\n`; });
                return s;
            }
            return '目前没有负面笔记。';
        }

        // 3) 正面 / 好评
        if (/正面|好评|夸赞|表扬|口碑/.test(q)) {
            const qs = new URLSearchParams({ sentiment: 'positive', per_page: '6' });
            if (scope) { qs.set('date_start', scope.start); qs.set('date_end', scope.end); }
            const data = await apiCall('/notes?' + qs.toString());
            const list = (data && data.notes) || [];
            if (list.length) {
                let s = scope ? `${scope.label}发布的正面笔记共 ${data.total != null ? data.total : list.length} 条：\n` : '最近的正面笔记：\n';
                list.forEach((n, i) => { s += `${i + 1}. ${n.title || '无标题'}（${n.likes || 0}赞）\n`; });
                return s;
            }
            return scope ? `${scope.label}未监测到正面笔记。` : '目前没有正面笔记。';
        }

        // 4) 风险 / 事件 / 预警（纯清单）
        if (/风险|预警|事件|高风险|危机|闭店|出事/.test(q)) {
            const data = await apiCall('/dashboard/all');
            const alerts = (data && data.risk_alerts) || [];
            if (alerts.length) {
                let s = `当前有 ${alerts.length} 条高/中风险内容：\n`;
                alerts.slice(0, 5).forEach((e, i) => {
                    s += `${i + 1}. [${e.risk_level === 'high' ? '高风险' : '中风险'}] ${e.title || '无标题'}（风险分 ${e.risk_score || 0}）\n`;
                });
                s += '\n需要某条的处置建议，直接问我“这条该怎么处置”。';
                return s;
            }
            return '目前没有高风险事件，舆情状态平稳。';
        }

        // 5) 笔记数量 / 统计
        if (/多少|数量|几条|统计|总数/.test(q) && /笔记|舆情|内容|数据|条/.test(q)) {
            const data = await apiCall('/dashboard/all');
            if (data && data.stats) {
                const s = data.stats;
                return `系统共收录 ${s.total || 0} 条笔记：正面 ${s.positive || 0}、中性 ${s.neutral || 0}、负面 ${s.negative || 0}、高风险 ${s.high_risk || 0}。`;
            }
            return '正在查询笔记数据，请稍候…';
        }

        // 6) 概览 / 盘面（宽泛意图，放在具体情感与风险之后）
        if (/概览|总结|总体|整体|盘面|今日|今天|情况|如何/.test(q)) {
            const data = await apiCall('/dashboard/all');
            if (data && data.stats) {
                const s = data.stats;
                return `舆情概览${scope ? '（' + scope.label + '）' : ''}：\n• 总笔记：${s.total || 0}条\n• 正面：${s.positive || 0}条\n• 中性：${s.neutral || 0}条\n• 负面：${s.negative || 0}条\n• 高风险：${s.high_risk || 0}条\n• 总互动量：${s.total_engagements || 0}\n• 活跃事件：${(data.events || []).length}个`;
            }
            return '正在获取舆情概览…';
        }

        // 7) 报告引导
        if (/日报|周报|月报|年报|报告|导出/.test(q)) {
            setExpression('speaking');
            return '我可以帮你生成报告：在左侧导航进入「报告中心」，选择日报/周报/月报与日期，即可导出 Word/Excel。需要我先用一句话概述今天要点吗？';
        }

        // 8) 兜底：交给真 AI（分析/解释/品牌业态/公关话术/架构等开放问题）
        const ai = await askAiChat(question);
        if (ai) return ai.reply;

        // 9) AI 也不可用 → 能力引导
        setExpression('neutral');
        return `我理解你想问：“${question}”。我可以查询：负面/正面笔记（可指定“今日”，按发布日期筛选）、风险事件、舆情概览、系统实时状态、报告；也可以做风险分析与公关建议。可点下方快捷问题，或把问题说具体一些。`;
    }

    // ============================================================
    // 发送消息
    // ============================================================
    async function sendMessage(text) {
        text = (text || '').trim();
        if (!text) return;

        const inputEl = getInputEl();

        // 用户消息
        appendMessage('user', text);
        if (inputEl) inputEl.value = '';

        // 思考中
        setExpression('thinking');
        const thinkingId = appendMessage('bot', '正在思考...');

        // 生成回答
        const answer = await generateAnswer(text);

        // 替换思考消息
        const thinkingEl = document.getElementById(thinkingId);
        const bubble = thinkingEl && thinkingEl.querySelector('.zachary-msg-bubble,.zachary-message-bubble');
        if (bubble) { bubble.textContent = answer; bubble.style.whiteSpace = 'pre-line'; }

        setExpression('happy');
        const messagesEl = getMessagesEl();
        if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    // ============================================================
    // 追加消息（兼容静态 zachary-msg 与动态 zachary-message 两套样式）
    // ============================================================
    function appendMessage(type, text) {
        const messagesEl = getMessagesEl();
        if (!messagesEl) return null;
        const id = `zachary_msg_${Date.now()}_${Math.floor(Math.random()*1000)}`;

        const msgEl = document.createElement('div');
        msgEl.id = id;
        // 静态结构使用 zachary-msg / zachary-msg-bot|user
        msgEl.className = `zachary-msg ${type === 'bot' ? 'zachary-msg-bot' : 'zachary-msg-user'}`;
        const avatar = document.createElement('div');
        avatar.className = 'zachary-msg-avatar';
        avatar.textContent = type === 'bot' ? 'Z' : '我';
        const bubble = document.createElement('div');
        bubble.className = 'zachary-msg-bubble';
        bubble.style.whiteSpace = 'pre-line';
        bubble.textContent = text;
        msgEl.appendChild(avatar);
        msgEl.appendChild(bubble);

        messagesEl.appendChild(msgEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return id;
    }

    // ============================================================
    // 设置表情
    // ============================================================
    function setExpression(expr) {
        state.currentExpression = expr;
        state._fixedExpr = true;
        applyExpression(expr);
        // 2.5秒后恢复自动表情
        clearTimeout(state._exprTimer);
        state._exprTimer = setTimeout(() => { state._fixedExpr = false; }, 2500);
    }

    // ============================================================
    // 拖拽功能（Zachary机器人）
    // ============================================================
    function initDrag(container) {
        let startX, startY, startLeft, startTop;
        let hasMoved = false;

        function onStart(e) {
            const point = e.touches ? e.touches[0] : e;
            startX = point.clientX;
            startY = point.clientY;
            
            const rect = container.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;
            
            state.isDragging = true;
            hasMoved = false;
            container.style.cursor = 'grabbing';
            
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onEnd);
            document.addEventListener('touchmove', onMove, { passive: false });
            document.addEventListener('touchend', onEnd);
        }

        function onMove(e) {
            if (!state.isDragging) return;
            e.preventDefault();
            
            const point = e.touches ? e.touches[0] : e;
            const dx = point.clientX - startX;
            const dy = point.clientY - startY;
            
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                hasMoved = true;
            }
            
            // 视口边界钳制：机器人永远不会被拖出可视区域
            const cw = container.offsetWidth || 76, ch = container.offsetHeight || 76;
            let nx = startLeft + dx, ny = startTop + dy;
            nx = Math.max(4, Math.min(nx, window.innerWidth - cw - 4));
            ny = Math.max(4, Math.min(ny, window.innerHeight - ch - 4));

            container.style.left = nx + 'px';
            container.style.top = ny + 'px';
            container.style.right = 'auto';
            container.style.bottom = 'auto';
        }

        function onEnd() {
            state.isDragging = false;
            container.style.cursor = 'grab';
            
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onEnd);
            document.removeEventListener('touchmove', onMove);
            document.removeEventListener('touchend', onEnd);
            
            // v5.8.9 移动端拖拽结束自动吸附最近左右边缘，不停在中部遮挡内容
            if (hasMoved && isMobileUI()) {
                const w = container.offsetWidth || 52;
                const rc = container.getBoundingClientRect();
                const toLeft = (rc.left + rc.width / 2) < (window.innerWidth / 2);
                container.style.top = Math.max(8, Math.min(rc.top, window.innerHeight - w - 8)) + 'px';
                container.style.left = (toLeft ? 8 : window.innerWidth - w - 8) + 'px';
                container.style.right = 'auto';
                container.style.bottom = 'auto';
            }
            // 如果没有移动，视为点击
            if (!hasMoved) {
                toggleChat();
            }
        }

        container.addEventListener('mousedown', onStart);
        container.addEventListener('touchstart', onStart, { passive: false });
    }

    // ============================================================
    // 聊天弹窗拖拽
    // ============================================================
    function initChatDrag(panel) {
        // 兼容动态 id 头部与静态 class 头部；找不到则安全跳过
        const header = document.getElementById('zacharyChatHeader') ||
                       (panel ? panel.querySelector('.zachary-chat-header') : null);
        if (!header || !panel) return;
        let startX, startY, startLeft, startTop;

        header.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('zachary-chat-close')) return;
            
            startX = e.clientX;
            startY = e.clientY;
            const rect = panel.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;

            function onMove(e) {
                panel.style.left = (startLeft + e.clientX - startX) + 'px';
                panel.style.top = (startTop + e.clientY - startY) + 'px';
                panel.style.right = 'auto';
                panel.style.bottom = 'auto';
            }

            function onEnd() {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onEnd);
            }

            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onEnd);
        });
    }

    // ============================================================
    // 切换聊天弹窗（同时兼容静态 modal 与动态 panel）
    // ============================================================
    function toggleChat(forceState) {
        const modal = getStaticModal();
        const panel = document.getElementById('zacharyChatPanel');
        if (!modal && !panel) return;

        const willOpen = (typeof forceState === 'boolean') ? forceState : !state.chatOpen;

        if (!willOpen) {
            if (modal) modal.classList.remove('show');
            if (panel) panel.style.display = 'none';
            state.chatOpen = false;
            setExpression('neutral');
        } else {
            if (modal) modal.classList.add('show');
            if (panel && !modal) {
                panel.style.display = 'flex';
                panel.style.position = 'fixed';
                panel.style.right = '30px';
                panel.style.bottom = '150px';
                panel.style.left = 'auto';
                panel.style.top = 'auto';
                panel.style.zIndex = '10001';
            }
            state.chatOpen = true;
            setExpression('happy');
            setTimeout(() => { const input = getInputEl(); if (input) input.focus(); }, 120);
        }
    }

    // ============================================================
    // 初始化
    // ============================================================
    function init() {
        // 创建/复用机器人与聊天面板
        const container = createZacharyHTML();
        const panel = createChatPanel();

        // 机器人拖拽
        if (container) initDrag(container);

        // 聊天框拖拽（防御性：头部元素不存在时跳过，不阻断初始化）
        try { if (panel) initChatDrag(panel); } catch (e) { /* 静态结构无拖拽头，忽略 */ }

        // 关闭按钮：静态 .zachary-chat-close（含遮罩）+ 动态 #zacharyChatClose
        document.querySelectorAll('.zachary-chat-close').forEach(btn => {
            btn.removeAttribute('onclick');
            btn.addEventListener('click', (e) => { e.stopPropagation(); toggleChat(false); });
        });
        const dynClose = document.getElementById('zacharyChatClose');
        if (dynClose) dynClose.addEventListener('click', () => toggleChat(false));
        // 点击遮罩关闭
        const mask = document.querySelector('.zachary-chat-mask');
        if (mask) {
            mask.removeAttribute('onclick');
            mask.addEventListener('click', () => toggleChat(false));
        }

        // 发送按钮（兼容静态/动态；移除内联onclick避免双触发，统一事件绑定）
        const sendBtn = getSendBtn();
        if (sendBtn) {
            sendBtn.removeAttribute('onclick');
            sendBtn.addEventListener('click', () => {
                const input = getInputEl();
                if (input) sendMessage(input.value);
            });
        }

        // 回车发送
        const inputEl = getInputEl();
        if (inputEl) {
            inputEl.removeAttribute('onkeydown');
            inputEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') sendMessage(e.target.value);
            });
        }

        // 快捷问题：动态 .zachary-quick-btn
        document.querySelectorAll('.zachary-quick-btn').forEach(btn => {
            btn.addEventListener('click', () => sendMessage(btn.textContent));
        });
        // 静态 #zacharyQuick 内按钮（原 onclick=zacharyQuickAsk）：移除内联后统一绑定
        document.querySelectorAll('#zacharyQuick button').forEach(btn => {
            const q = btn.getAttribute('data-q') || btn.textContent;
            btn.removeAttribute('onclick');
            btn.addEventListener('click', () => sendMessage(q));
        });

        // 表情定时切换 + 初始表情
        setInterval(switchExpression, CONFIG.expressionInterval);
        applyExpression('neutral');

        // 暴露全局函数，供静态 HTML 的内联 onclick 调用
        window.toggleZacharyChat = function() { toggleChat(); };
        window.closeZacharyChat = function() { toggleChat(false); };
        window.openZacharyChat = function() { toggleChat(true); };
        window.sendZacharyMsg = function() {
            const input = getInputEl();
            if (input) sendMessage(input.value);
        };
        window.zacharyQuickAsk = function(q) { sendMessage(q); };

        console.log('Zachary robot enhanced started');
    }

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
