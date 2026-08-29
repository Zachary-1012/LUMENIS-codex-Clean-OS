/**
 * 广州太古汇舆情监测系统 v5.8.0 Zachary机器人模块
 * 黑色球体，液晶面部，荧光白/蓝表情，蓝色帽子，小耳麦，3D质感
 * 全局可拖拽，点击打开聊天弹窗，了解整个系统架构
 */

(function() {
    'use strict';

    // ============================================================
    // Zachary机器人配置
    // ============================================================
    const ZACHARY_CONFIG = {
        size: 60,
        position: { bottom: '80px', right: '30px' },
        expressions: ['happy', 'thinking', 'speaking', 'neutral', 'surprised'],
        expressionInterval: 3000,
        hatColors: ['#1E90FF', '#4169E1', '#00BFFF', '#6495ED'],
        wearHatProbability: 0.7
    };

    // ============================================================
    // Zachary机器人状态
    // ============================================================
    let zacharyState = {
        isDragging: false,
        dragOffset: { x: 0, y: 0 },
        currentExpression: 'neutral',
        chatOpen: false,
        wearHat: Math.random() < ZACHARY_CONFIG.wearHatProbability,
        hatColor: ZACHARY_CONFIG.hatColors[Math.floor(Math.random() * ZACHARY_CONFIG.hatColors.length)]
    };

    // ============================================================
    // 创建Zachary机器人HTML
    // ============================================================
    function createZacharyHTML() {
        const container = document.createElement('div');
        container.id = 'zacharyFloat';
        container.className = 'zachary-float';
        container.style.cssText = `
            position: fixed;
            bottom: ${ZACHARY_CONFIG.position.bottom};
            right: ${ZACHARY_CONFIG.position.right};
            width: ${ZACHARY_CONFIG.size}px;
            height: ${ZACHARY_CONFIG.size}px;
            z-index: 9999;
            cursor: grab;
            user-select: none;
            touch-action: none;
        `;

        container.innerHTML = `
            <div class="zachary-body">
                <!-- 帽子 -->
                <div class="zachary-hat" style="display: ${zacharyState.wearHat ? 'block' : 'none'}; background: ${zacharyState.hatColor};">
                    <div class="zachary-hat-top"></div>
                    <div class="zachary-hat-brim"></div>
                </div>
                
                <!-- 头部（黑色球体） -->
                <div class="zachary-head">
                    <!-- 液晶面部 -->
                    <div class="zachary-face">
                        <div class="zachary-expression" id="zacharyExpression">
                            <div class="zachary-eyes">
                                <div class="zachary-eye left"></div>
                                <div class="zachary-eye right"></div>
                            </div>
                            <div class="zachary-mouth"></div>
                        </div>
                    </div>
                    
                    <!-- 耳麦 -->
                    <div class="zachary-headset">
                        <div class="zachary-headset-band"></div>
                        <div class="zachary-headset-mic"></div>
                    </div>
                    
                    <!-- 3D光泽效果 -->
                    <div class="zachary-shine"></div>
                </div>
                
                <!-- 状态指示灯 -->
                <div class="zachary-status-light"></div>
            </div>
            
            <!-- 提示气泡 -->
            <div class="zachary-tooltip">点击和我聊天</div>
        `;

        return container;
    }

    // ============================================================
    // 创建Zachary聊天弹窗HTML
    // ============================================================
    function createZacharyChatHTML() {
        const modal = document.createElement('div');
        modal.id = 'zacharyChatModal';
        modal.className = 'zachary-chat-modal';
        modal.style.cssText = `
            position: fixed;
            width: 380px;
            height: 500px;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            z-index: 10000;
            display: none;
            flex-direction: column;
            overflow: hidden;
        `;

        modal.innerHTML = `
            <!-- 头部 -->
            <div class="zachary-chat-header">
                <div class="zachary-chat-avatar">
                    <div class="zachary-mini-head">
                        <div class="zachary-mini-face">
                            <div class="zachary-mini-eyes">
                                <div class="zachary-mini-eye left"></div>
                                <div class="zachary-mini-eye right"></div>
                            </div>
                            <div class="zachary-mini-mouth"></div>
                        </div>
                    </div>
                </div>
                <div class="zachary-chat-info">
                    <div class="zachary-chat-name">Zachary</div>
                    <div class="zachary-chat-status"><span class="online-dot"></span>在线</div>
                </div>
                <button class="zachary-chat-close" id="zacharyChatClose">×</button>
            </div>
            
            <!-- 消息区域 -->
            <div class="zachary-chat-messages" id="zacharyChatMessages">
                <div class="zachary-message zachary-message-bot">
                    <div class="zachary-message-avatar">Z</div>
                    <div class="zachary-message-content">
                        你好！我是Zachary，广州太古汇舆情监测系统的AI助手。我可以帮你：
                        <br><br>
                        • 查询舆情数据和统计
                        <br>
                        • 分析负面事件和风险
                        <br>
                        • 生成日报/周报/月报
                        <br>
                        • 解答系统使用问题
                        <br><br>
                        请问有什么可以帮你的？
                    </div>
                </div>
            </div>
            
            <!-- 快捷问题 -->
            <div class="zachary-quick-questions">
                <button class="zachary-quick-btn" data-question="今天有多少条负面舆情？">今天负面舆情</button>
                <button class="zachary-quick-btn" data-question="帮我生成今天的日报">生成日报</button>
                <button class="zachary-quick-btn" data-question="系统有哪些功能？">系统功能</button>
            </div>
            
            <!-- 输入区域 -->
            <div class="zachary-chat-input">
                <input type="text" id="zacharyChatInput" placeholder="输入你的问题..." />
                <button id="zacharyChatSend">发送</button>
            </div>
        `;

        return modal;
    }

    // ============================================================
    // 添加Zachary样式
    // ============================================================
    function addZacharyStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Zachary机器人主体 */
            .zachary-float {
                transition: transform 0.2s ease;
            }
            .zachary-float:hover {
                transform: scale(1.1);
            }
            .zachary-float:active {
                cursor: grabbing;
            }
            
            .zachary-body {
                position: relative;
                width: 100%;
                height: 100%;
            }
            
            /* 帽子 */
            .zachary-hat {
                position: absolute;
                top: -8px;
                left: 50%;
                transform: translateX(-50%);
                width: 40px;
                height: 20px;
                z-index: 10;
            }
            .zachary-hat-top {
                width: 30px;
                height: 18px;
                background: inherit;
                border-radius: 15px 15px 5px 5px;
                margin: 0 auto;
                box-shadow: inset -3px -3px 5px rgba(0,0,0,0.2);
            }
            .zachary-hat-brim {
                width: 40px;
                height: 5px;
                background: inherit;
                border-radius: 3px;
                margin-top: -2px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            
            /* 头部（黑色球体） */
            .zachary-head {
                position: relative;
                width: 100%;
                height: 100%;
                background: radial-gradient(circle at 30% 30%, #3a3a3a, #1a1a1a 60%, #000);
                border-radius: 50%;
                box-shadow: 
                    0 4px 15px rgba(0,0,0,0.4),
                    inset -5px -5px 15px rgba(0,0,0,0.5),
                    inset 3px 3px 10px rgba(255,255,255,0.1);
                overflow: hidden;
            }
            
            /* 液晶面部 */
            .zachary-face {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 70%;
                height: 50%;
                background: rgba(0, 20, 40, 0.8);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: inset 0 0 10px rgba(0, 255, 255, 0.2);
            }
            
            /* 表情 */
            .zachary-expression {
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 4px;
            }
            
            .zachary-eyes {
                display: flex;
                gap: 8px;
            }
            
            .zachary-eye {
                width: 10px;
                height: 5px;
                background: #ffffff;
                border-radius: 5px;
                box-shadow: 0 0 8px #ffffff, 0 0 15px rgba(100, 200, 255, 0.5);
                transition: all 0.3s ease;
            }
            
            .zachary-mouth {
                width: 12px;
                height: 3px;
                background: #ffffff;
                border-radius: 2px;
                box-shadow: 0 0 6px #ffffff;
                transition: all 0.3s ease;
            }
            
            /* 表情变化 */
            .zachary-expression.happy .zachary-eye {
                height: 6px;
                border-radius: 6px 6px 0 0;
            }
            .zachary-expression.happy .zachary-mouth {
                height: 6px;
                border-radius: 0 0 6px 6px;
            }
            
            .zachary-expression.thinking .zachary-eye.left {
                transform: rotate(-10deg);
            }
            .zachary-expression.thinking .zachary-eye.right {
                transform: rotate(10deg);
            }
            
            .zachary-expression.speaking .zachary-mouth {
                animation: mouthMove 0.3s infinite;
            }
            @keyframes mouthMove {
                0%, 100% { height: 3px; }
                50% { height: 8px; }
            }
            
            .zachary-expression.surprised .zachary-eye {
                width: 12px;
                height: 12px;
                border-radius: 50%;
            }
            .zachary-expression.surprised .zachary-mouth {
                width: 8px;
                height: 8px;
                border-radius: 50%;
            }
            
            /* 耳麦 */
            .zachary-headset {
                position: absolute;
                top: 20%;
                right: -5px;
                width: 15px;
                height: 25px;
                z-index: 5;
            }
            .zachary-headset-band {
                position: absolute;
                top: 0;
                right: 5px;
                width: 3px;
                height: 20px;
                background: linear-gradient(to bottom, #888, #555);
                border-radius: 2px;
            }
            .zachary-headset-mic {
                position: absolute;
                bottom: 0;
                right: 0;
                width: 10px;
                height: 6px;
                background: linear-gradient(to right, #666, #444);
                border-radius: 3px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            }
            
            /* 3D光泽效果 */
            .zachary-shine {
                position: absolute;
                top: 10%;
                left: 15%;
                width: 30%;
                height: 20%;
                background: radial-gradient(ellipse, rgba(255,255,255,0.3), transparent);
                border-radius: 50%;
                pointer-events: none;
            }
            
            /* 状态指示灯 */
            .zachary-status-light {
                position: absolute;
                bottom: 2px;
                right: 2px;
                width: 8px;
                height: 8px;
                background: #00ff00;
                border-radius: 50%;
                box-shadow: 0 0 8px #00ff00;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            /* 提示气泡 */
            .zachary-tooltip {
                position: absolute;
                bottom: 100%;
                right: 0;
                background: #333;
                color: #fff;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 12px;
                white-space: nowrap;
                opacity: 0;
                transform: translateY(5px);
                transition: all 0.3s ease;
                pointer-events: none;
                margin-bottom: 8px;
            }
            .zachary-float:hover .zachary-tooltip {
                opacity: 1;
                transform: translateY(0);
            }
            
            /* 聊天弹窗 */
            .zachary-chat-modal {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            .zachary-chat-modal.show {
                display: flex !important;
            }
            
            .zachary-chat-header {
                display: flex;
                align-items: center;
                padding: 12px 15px;
                background: linear-gradient(135deg, #1a1a2e, #16213e);
                color: #fff;
                gap: 10px;
            }
            
            .zachary-chat-avatar {
                width: 40px;
                height: 40px;
            }
            .zachary-mini-head {
                width: 100%;
                height: 100%;
                background: radial-gradient(circle at 30% 30%, #3a3a3a, #1a1a1a 60%, #000);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow: hidden;
            }
            .zachary-mini-face {
                width: 70%;
                height: 50%;
                background: rgba(0, 20, 40, 0.8);
                border-radius: 8px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 2px;
            }
            .zachary-mini-eyes {
                display: flex;
                gap: 5px;
            }
            .zachary-mini-eye {
                width: 6px;
                height: 3px;
                background: #ffffff;
                border-radius: 3px;
                box-shadow: 0 0 5px #ffffff;
            }
            .zachary-mini-mouth {
                width: 8px;
                height: 2px;
                background: #ffffff;
                border-radius: 1px;
                box-shadow: 0 0 3px #ffffff;
            }
            
            .zachary-chat-info {
                flex: 1;
            }
            .zachary-chat-name {
                font-weight: 600;
                font-size: 14px;
            }
            .zachary-chat-status {
                font-size: 11px;
                opacity: 0.8;
                display: flex;
                align-items: center;
                gap: 4px;
            }
            .online-dot {
                width: 6px;
                height: 6px;
                background: #00ff00;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }
            
            .zachary-chat-close {
                background: none;
                border: none;
                color: #fff;
                font-size: 24px;
                cursor: pointer;
                padding: 0 5px;
                opacity: 0.7;
                transition: opacity 0.2s;
            }
            .zachary-chat-close:hover {
                opacity: 1;
            }
            
            .zachary-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 15px;
                background: #f5f5f5;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            .zachary-message {
                display: flex;
                gap: 8px;
                max-width: 85%;
            }
            .zachary-message-bot {
                align-self: flex-start;
            }
            .zachary-message-user {
                align-self: flex-end;
                flex-direction: row-reverse;
            }
            
            .zachary-message-avatar {
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: linear-gradient(135deg, #1a1a2e, #16213e);
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: 600;
                flex-shrink: 0;
            }
            .zachary-message-user .zachary-message-avatar {
                background: linear-gradient(135deg, #667eea, #764ba2);
            }
            
            .zachary-message-content {
                background: #fff;
                padding: 10px 12px;
                border-radius: 12px;
                font-size: 13px;
                line-height: 1.5;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .zachary-message-user .zachary-message-content {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: #fff;
            }
            
            .zachary-quick-questions {
                display: flex;
                gap: 6px;
                padding: 8px 12px;
                background: #fff;
                border-top: 1px solid #eee;
                overflow-x: auto;
            }
            .zachary-quick-btn {
                flex-shrink: 0;
                padding: 5px 10px;
                background: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 15px;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.2s;
                white-space: nowrap;
            }
            .zachary-quick-btn:hover {
                background: #e0e0e0;
                border-color: #ccc;
            }
            
            .zachary-chat-input {
                display: flex;
                gap: 8px;
                padding: 10px 12px;
                background: #fff;
                border-top: 1px solid #eee;
            }
            .zachary-chat-input input {
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 20px;
                font-size: 13px;
                outline: none;
                transition: border-color 0.2s;
            }
            .zachary-chat-input input:focus {
                border-color: #667eea;
            }
            .zachary-chat-input button {
                padding: 8px 16px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: #fff;
                border: none;
                border-radius: 20px;
                font-size: 13px;
                cursor: pointer;
                transition: opacity 0.2s;
            }
            .zachary-chat-input button:hover {
                opacity: 0.9;
            }
        `;
        document.head.appendChild(style);
    }

    // ============================================================
    // 初始化Zachary拖拽功能
    // ============================================================
    function initZacharyDrag() {
        const zachary = document.getElementById('zacharyFloat');
        if (!zachary) return;

        let startX, startY, startLeft, startTop;
        let hasMoved = false;

        zachary.addEventListener('pointerdown', function(e) {
            zacharyState.isDragging = true;
            hasMoved = false;
            startX = e.clientX;
            startY = e.clientY;
            
            const rect = zachary.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;
            
            zachary.style.right = 'auto';
            zachary.style.bottom = 'auto';
            zachary.style.left = startLeft + 'px';
            zachary.style.top = startTop + 'px';
            zachary.style.zIndex = '10001';
            
            zachary.setPointerCapture(e.pointerId);
            e.preventDefault();
        });

        zachary.addEventListener('pointermove', function(e) {
            if (!zacharyState.isDragging) return;
            
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                hasMoved = true;
            }
            
            zachary.style.left = (startLeft + dx) + 'px';
            zachary.style.top = (startTop + dy) + 'px';
        });

        zachary.addEventListener('pointerup', function(e) {
            zacharyState.isDragging = false;
            zachary.style.zIndex = '9999';
            
            try {
                zachary.releasePointerCapture(e.pointerId);
            } catch(err) {}
            
            // 如果没有移动，视为点击，打开聊天
            if (!hasMoved) {
                toggleZacharyChat();
            }
        });

        zachary.addEventListener('pointercancel', function() {
            zacharyState.isDragging = false;
            zachary.style.zIndex = '9999';
        });
    }

    // ============================================================
    // 切换Zachary聊天弹窗
    // ============================================================
    function toggleZacharyChat() {
        const modal = document.getElementById('zacharyChatModal');
        if (!modal) return;
        
        zacharyState.chatOpen = !zacharyState.chatOpen;
        
        if (zacharyState.chatOpen) {
            // 定位到Zachary旁边
            const zachary = document.getElementById('zacharyFloat');
            const rect = zachary.getBoundingClientRect();
            
            modal.style.display = 'flex';
            modal.classList.add('show');
            
            // 计算位置，确保不超出屏幕
            let left = rect.left - 400;
            let top = rect.top - 200;
            
            if (left < 10) left = 10;
            if (top < 10) top = 10;
            if (left + 380 > window.innerWidth) left = window.innerWidth - 390;
            if (top + 500 > window.innerHeight) top = window.innerHeight - 510;
            
            modal.style.left = left + 'px';
            modal.style.top = top + 'px';
            
            // 使聊天弹窗也可拖拽
            makeChatDraggable(modal);
            
            // 改变表情为speaking
            setZacharyExpression('speaking');
            
            // 聚焦输入框
            setTimeout(() => {
                const input = document.getElementById('zacharyChatInput');
                if (input) input.focus();
            }, 100);
        } else {
            modal.style.display = 'none';
            modal.classList.remove('show');
            setZacharyExpression('neutral');
        }
    }

    // ============================================================
    // 使聊天弹窗可拖拽
    // ============================================================
    function makeChatDraggable(modal) {
        const header = modal.querySelector('.zachary-chat-header');
        if (!header) return;
        
        let isDragging = false;
        let startX, startY, startLeft, startTop;
        
        header.style.cursor = 'move';
        
        header.addEventListener('pointerdown', function(e) {
            if (e.target.classList.contains('zachary-chat-close')) return;
            
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            
            const rect = modal.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;
            
            header.setPointerCapture(e.pointerId);
            e.preventDefault();
        });
        
        header.addEventListener('pointermove', function(e) {
            if (!isDragging) return;
            
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            
            modal.style.left = (startLeft + dx) + 'px';
            modal.style.top = (startTop + dy) + 'px';
        });
        
        header.addEventListener('pointerup', function(e) {
            isDragging = false;
            try {
                header.releasePointerCapture(e.pointerId);
            } catch(err) {}
        });
    }

    // ============================================================
    // 设置Zachary表情
    // ============================================================
    function setZacharyExpression(expression) {
        const expr = document.getElementById('zacharyExpression');
        if (!expr) return;
        
        zacharyState.currentExpression = expression;
        expr.className = 'zachary-expression ' + expression;
    }

    // ============================================================
    // 随机切换表情
    // ============================================================
    function startExpressionCycle() {
        setInterval(() => {
            if (!zacharyState.chatOpen && !zacharyState.isDragging) {
                const expressions = ['happy', 'thinking', 'neutral', 'surprised'];
                const randomExpr = expressions[Math.floor(Math.random() * expressions.length)];
                setZacharyExpression(randomExpr);
                
                // 随机切换帽子
                if (Math.random() < 0.1) {
                    zacharyState.wearHat = !zacharyState.wearHat;
                    const hat = document.querySelector('.zachary-hat');
                    if (hat) {
                        hat.style.display = zacharyState.wearHat ? 'block' : 'none';
                    }
                }
            }
        }, ZACHARY_CONFIG.expressionInterval);
    }

    // ============================================================
    // 处理用户消息
    // ============================================================
    function handleUserMessage(message) {
        // 添加用户消息
        addChatMessage(message, 'user');
        
        // 模拟AI回复
        setTimeout(() => {
            let response = generateZacharyResponse(message);
            addChatMessage(response, 'bot');
            setZacharyExpression('speaking');
            setTimeout(() => setZacharyExpression('neutral'), 2000);
        }, 500);
    }

    // ============================================================
    // 生成Zachary回复
    // ============================================================
    function generateZacharyResponse(message) {
        const msg = message.toLowerCase();
        
        if (msg.includes('负面') || msg.includes('舆情')) {
            return '根据系统数据，当前待确认负面舆情有124条。你可以在"负面确认"页面进行审核。需要我帮你生成负面舆情分析报告吗？';
        }
        if (msg.includes('日报') || msg.includes('报告')) {
            return '我可以帮你生成日报、周报、月报和年报。请告诉我你需要哪种报告，以及报告的日期范围。报告将按照太古汇汇报模版导出，支持Excel和Word格式。';
        }
        if (msg.includes('功能') || msg.includes('系统')) {
            return '广州太古汇舆情监测系统包含以下功能：\n\n• 舆情监测：小红书实时采集，全网话题发现\n• 风险预警：负面舆情识别，风险等级评估\n• 事件中心：舆情事件聚合，传播路径分析\n• 负面确认：二次确认机制，确保数据准确\n• 报告中心：日报/周报/月报/年报导出\n• 品牌业态：199个品牌+9大业态监测\n• AI分析：智能摘要，情感分析，风险预测\n\n请问你想了解哪个功能？';
        }
        if (msg.includes('采集') || msg.includes('更新')) {
            return '当前采集状态：今日已采集0/12次，手动剩余3/3次，自动剩余9/9次。采集冷却时间15分钟。你可以点击"采集数据"按钮手动触发采集，系统也会自动进行9次采集。';
        }
        
        return '我理解你的问题是："' + message + '"。我正在学习更多系统知识，稍后会给你更准确的回答。你也可以尝试问我关于舆情数据、报告生成、系统功能等方面的问题。';
    }

    // ============================================================
    // 添加聊天消息
    // ============================================================
    function addChatMessage(content, type) {
        const messages = document.getElementById('zacharyChatMessages');
        if (!messages) return;
        
        const msgDiv = document.createElement('div');
        msgDiv.className = 'zachary-message zachary-message-' + type;
        
        const avatar = document.createElement('div');
        avatar.className = 'zachary-message-avatar';
        avatar.textContent = type === 'bot' ? 'Z' : '我';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'zachary-message-content';
        contentDiv.innerHTML = content.replace(/\n/g, '<br>');
        
        msgDiv.appendChild(avatar);
        msgDiv.appendChild(contentDiv);
        messages.appendChild(msgDiv);
        
        // 滚动到底部
        messages.scrollTop = messages.scrollHeight;
    }

    // ============================================================
    // 初始化Zachary聊天事件
    // ============================================================
    function initZacharyChatEvents() {
        // 关闭按钮
        const closeBtn = document.getElementById('zacharyChatClose');
        if (closeBtn) {
            closeBtn.addEventListener('click', toggleZacharyChat);
        }
        
        // 发送按钮
        const sendBtn = document.getElementById('zacharyChatSend');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                const input = document.getElementById('zacharyChatInput');
                if (input && input.value.trim()) {
                    handleUserMessage(input.value.trim());
                    input.value = '';
                }
            });
        }
        
        // 输入框回车
        const input = document.getElementById('zacharyChatInput');
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const sendBtn = document.getElementById('zacharyChatSend');
                    if (sendBtn) sendBtn.click();
                }
            });
        }
        
        // 快捷问题按钮
        const quickBtns = document.querySelectorAll('.zachary-quick-btn');
        quickBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const question = btn.getAttribute('data-question');
                if (question) {
                    handleUserMessage(question);
                }
            });
        });
    }

    // ============================================================
    // 初始化Zachary机器人
    // ============================================================
    function initZachary() {
        // 检查是否已经初始化
        if (document.getElementById('zacharyFloat')) {
            console.log('Zachary已经初始化');
            return;
        }
        
        // 添加样式
        addZacharyStyles();
        
        // 创建机器人
        const zachary = createZacharyHTML();
        document.body.appendChild(zachary);
        
        // 创建聊天弹窗
        const chatModal = createZacharyChatHTML();
        document.body.appendChild(chatModal);
        
        // 初始化拖拽
        initZacharyDrag();
        
        // 初始化聊天事件
        initZacharyChatEvents();
        
        // 启动表情循环
        startExpressionCycle();
        
        // 设置初始表情
        setZacharyExpression('happy');
        
        console.log('Zachary机器人已初始化');
    }

    // 暴露到全局
    window.initZachary = initZachary;
    window.toggleZacharyChat = toggleZacharyChat;
    window.setZacharyExpression = setZacharyExpression;
    window.addZacharyChatMessage = addChatMessage;
    window.zacharyState = zacharyState;

    // 页面加载完成后自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initZachary);
    } else {
        initZachary();
    }

})();
