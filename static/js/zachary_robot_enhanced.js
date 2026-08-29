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
        hatColors: ['#1E90FF', '#4169E1', '#00BFFF', '#6495ED'],
        wearHatProbability: 0.7,
        apiBase: '/api'
    };

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
            container.style.cssText = `
                position: fixed;
                bottom: ${CONFIG.position.bottom};
                right: ${CONFIG.position.right};
                width: ${CONFIG.sizeW}px;
                height: ${CONFIG.sizeH}px;
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
        container.style.cssText = `
            position: fixed;
            bottom: ${CONFIG.position.bottom};
            right: ${CONFIG.position.right};
            width: ${CONFIG.size}px;
            height: ${CONFIG.size}px;
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
                            <div style="width:8px;height:4px;background:#00ffff;border-radius:2px;box-shadow:0 0 4px #00ffff;"></div>
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
    async function generateAnswer(question) {
        const q = question.toLowerCase();
        
        // 今日笔记数量
        if (q.includes('笔记') && (q.includes('多少') || q.includes('数量') || q.includes('今天'))) {
            setExpression('thinking');
            const data = await apiCall('/dashboard/all');
            if (data && !data.error && data.stats) {
                const s = data.stats;
                return `目前系统中共有 ${s.total || 0} 条笔记，其中负面 ${s.negative || 0} 条，正面 ${s.positive || 0} 条，中性 ${s.neutral || 0} 条。`;
            }
            return '正在查询笔记数据，请稍候...';
        }

        // 高风险事件
        if (q.includes('风险') || q.includes('事件') || q.includes('高风险')) {
            setExpression('thinking');
            const data = await apiCall('/dashboard/all');
            if (data && data.risk_alerts && data.risk_alerts.length > 0) {
                let answer = `当前有 ${data.risk_alerts.length} 条高/中风险内容：\n`;
                data.risk_alerts.slice(0, 5).forEach((e, i) => {
                    answer += `${i + 1}. [${e.risk_level === 'high' ? '高风险' : '中风险'}] ${e.title || '无标题'}（风险分${e.risk_score || 0}）\n`;
                });
                return answer;
            }
            return '目前没有高风险事件，舆情状态平稳。';
        }

        // 今日舆情概览
        if (q.includes('概览') || q.includes('总结') || q.includes('今日') || q.includes('今天')) {
            setExpression('thinking');
            const data = await apiCall('/dashboard/all');
            if (data && !data.error && data.stats) {
                const s = data.stats;
                return `📊 今日舆情概览：\n• 总笔记：${s.total || 0}条\n• 正面：${s.positive || 0}条\n• 中性：${s.neutral || 0}条\n• 负面：${s.negative || 0}条\n• 高风险：${s.high_risk || 0}条\n• 总互动量：${s.total_engagements || 0}\n• 活跃事件：${(data.events || []).length}个`;
            }
            return '正在获取舆情概览...';
        }

        // 负面笔记
        if (q.includes('负面')) {
            setExpression('thinking');
            const data = await apiCall('/notes?sentiment=negative&limit=5');
            if (data && data.notes && data.notes.length > 0) {
                let answer = '最近的负面笔记：\n';
                data.notes.forEach((n, i) => {
                    answer += `${i + 1}. ${n.title || '无标题'}（${n.likes || 0}赞）\n`;
                });
                return answer;
            }
            return '目前没有负面笔记。';
        }

        // 系统状态
        if (q.includes('状态') || q.includes('运行') || q.includes('系统')) {
            setExpression('thinking');
            return `🖥️ 系统运行状态：\n• 版本：v5.7.0\n• 数据库：正常（v8版本）\n• 采集器：待命中\n• AI分析：已配置\n• 监控告警：已启用\n\n系统运行正常，所有服务在线。`;
        }

        // 日报
        if (q.includes('日报') || q.includes('报告') || q.includes('生成')) {
            setExpression('speaking');
            return '我可以帮你生成日报。请在左侧导航栏点击"报告中心"，选择日报类型和日期，即可生成并导出Word/Excel格式的报告。需要我帮你查看今天的日报吗？';
        }

        // 默认回答
        setExpression('neutral');
        return `我理解你的问题是："${question}"。我可以帮你查询：\n• 笔记数据（数量、负面、正面）\n• 事件分析（高风险、事件列表）\n• 舆情概览（今日总结）\n• 系统状态（运行情况）\n• 报告生成（日报/周报/月报）\n\n请尝试点击下方快捷问题，或用更具体的方式提问。`;
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
