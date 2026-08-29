/**
 * 系统控制模块 - AI聊天、设置、导出、采集器控制
 * 与app.js配合使用，提供系统级控制功能
 */

(function() {
    'use strict';

    // 认证信息（与app.js保持一致）
    const AUTH = 'Basic ' + btoa('Zachary:ID082610');

    // API请求封装
    async function api(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Authorization': AUTH,
                'Content-Type': 'application/json'
            }
        };
        const mergedOptions = { ...defaultOptions, ...options };
        if (mergedOptions.body && typeof mergedOptions.body === 'object') {
            mergedOptions.body = JSON.stringify(mergedOptions.body);
        }
        const response = await fetch(url, mergedOptions);
        const data = await response.json();
        if (!response.ok || data.ok === false) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        return data;
    }

    // Toast提示
    function toast(message, type = 'info') {
        const existing = document.getElementById('system-toast');
        if (existing) existing.remove();
        
        const toast = document.createElement('div');
        toast.id = 'system-toast';
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 10000;
            padding: 12px 20px; border-radius: 8px; color: white;
            background: ${type === 'error' ? '#ff3b30' : type === 'success' ? '#34c759' : '#0a84ff'};
            box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 14px;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // 创建弹窗
    function createModal(title, content, width = '600px') {
        const overlay = document.createElement('div');
        overlay.className = 'system-modal-overlay';
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 9999;
            display: flex; align-items: center; justify-content: center;
            animation: fadeIn 0.2s ease;
        `;
        
        const modal = document.createElement('div');
        modal.className = 'system-modal';
        modal.style.cssText = `
            background: white; border-radius: 12px; width: ${width};
            max-width: 90vw; max-height: 85vh; overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            animation: scaleIn 0.2s ease; display: flex; flex-direction: column;
        `;
        
        modal.innerHTML = `
            <div style="padding: 16px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; font-size: 18px; font-weight: 600;">${title}</h3>
                <button class="modal-close" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #999; padding: 0; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%;">×</button>
            </div>
            <div class="modal-body" style="padding: 20px; overflow-y: auto; flex: 1;">${content}</div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        // 关闭事件
        const close = () => {
            overlay.style.animation = 'fadeOut 0.2s ease';
            setTimeout(() => overlay.remove(), 200);
        };
        overlay.querySelector('.modal-close').onclick = close;
        overlay.onclick = (e) => { if (e.target === overlay) close(); };
        
        return { overlay, modal, close };
    }

    // ========== AI聊天功能 ==========
    let chatHistory = [];

    function openAIChat() {
        const content = `
            <div id="ai-chat-container" style="display: flex; flex-direction: column; height: 500px;">
                <div id="ai-chat-messages" style="flex: 1; overflow-y: auto; padding: 10px; background: #f9f9f9; border-radius: 8px; margin-bottom: 10px;">
                    <div style="text-align: center; color: #999; padding: 20px;">
                        <div style="font-size: 40px; margin-bottom: 10px;">🤖</div>
                        <div>AI助手已就绪，请问有什么可以帮您？</div>
                        <div style="font-size: 12px; margin-top: 8px; color: #bbb;">支持舆情分析、报告解读、系统操作咨询等</div>
                    </div>
                </div>
                <div style="display: flex; gap: 8px;">
                    <input type="text" id="ai-chat-input" placeholder="输入您的问题..." style="flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; outline: none;" />
                    <button id="ai-chat-send" style="padding: 10px 20px; background: #0a84ff; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">发送</button>
                </div>
                <div style="margin-top: 8px; font-size: 12px; color: #999; display: flex; justify-content: space-between;">
                    <span id="ai-provider-info">提供商: 检测中...</span>
                    <span>Enter发送，Shift+Enter换行</span>
                </div>
            </div>
        `;
        
        const { modal, close } = createModal('AI智能助手', content, '700px');
        
        // 加载AI状态
        api('/api/ai/status').then(data => {
            document.getElementById('ai-provider-info').textContent = 
                `提供商: ${data.provider || 'local_rule'} | 模型: ${data.model || '—'} | ${data.enabled ? '已连接' : '本地规则'}`;
        }).catch(() => {
            document.getElementById('ai-provider-info').textContent = '提供商: 本地规则引擎';
        });
        
        // 发送消息
        const sendMessage = async () => {
            const input = document.getElementById('ai-chat-input');
            const message = input.value.trim();
            if (!message) return;
            
            // 显示用户消息
            appendMessage('user', message);
            input.value = '';
            
            // 显示加载中
            const loadingId = appendMessage('assistant', '思考中...', true);
            
            try {
                // 优先使用豆包AI，失败回退本地AI
                let response;
                try {
                    response = await api('/api/ark/chat', {
                        method: 'POST',
                        body: { message, history: chatHistory }
                    });
                } catch (e) {
                    // 回退到本地AI
                    response = await api('/api/ai/chat', {
                        method: 'POST',
                        body: { message, history: chatHistory }
                    });
                }
                
                // 更新消息
                document.getElementById(loadingId).innerHTML = formatMessage(response.reply || response.message || '无回复');
                chatHistory.push({ role: 'user', content: message });
                chatHistory.push({ role: 'assistant', content: response.reply || response.message || '' });
                
            } catch (error) {
                document.getElementById(loadingId).innerHTML = `<span style="color: #ff3b30;">错误: ${error.message}</span>`;
            }
        };
        
        document.getElementById('ai-chat-send').onclick = sendMessage;
        document.getElementById('ai-chat-input').onkeydown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        };
        
        // 重置历史
        chatHistory = [];
    }

    function appendMessage(role, content, isLoading = false) {
        const container = document.getElementById('ai-chat-messages');
        const id = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        
        const isUser = role === 'user';
        const messageDiv = document.createElement('div');
        messageDiv.id = id;
        messageDiv.style.cssText = `
            margin-bottom: 12px; display: flex;
            justify-content: ${isUser ? 'flex-end' : 'flex-start'};
        `;
        messageDiv.innerHTML = `
            <div style="max-width: 80%; padding: 10px 14px; border-radius: 12px;
                background: ${isUser ? '#0a84ff' : 'white'};
                color: ${isUser ? 'white' : '#333'};
                border: ${isUser ? 'none' : '1px solid #eee'};
                font-size: 14px; line-height: 1.6;
                ${isLoading ? 'opacity: 0.7; font-style: italic;' : ''}">
                ${isLoading ? content : formatMessage(content)}
            </div>
        `;
        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    function formatMessage(text) {
        return String(text || '')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code style="background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 13px;">$1</code>');
    }

    // ========== 设置功能 ==========
    function openSettings() {
        const content = `
            <div id="settings-container">
                <div style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 12px 0; color: #333;">系统设置</h4>
                    <div style="background: #f9f9f9; padding: 12px; border-radius: 8px; font-size: 13px; color: #666;">
                        在这里配置系统参数，修改后点击保存生效。
                    </div>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">采集间隔（分钟）</label>
                    <input type="number" id="setting-collect-interval" value="120" min="30" max="1440" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;" />
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">AI提供商</label>
                    <select id="setting-ai-provider" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;">
                        <option value="auto">自动选择（优先豆包AI）</option>
                        <option value="ark">豆包AI（云端）</option>
                        <option value="local">本地AI/规则引擎</option>
                    </select>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">自动采集</label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="checkbox" id="setting-auto-collect" checked style="width: 18px; height: 18px;" />
                        <span>启用定时自动采集</span>
                    </label>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">负面预警阈值</label>
                    <input type="range" id="setting-risk-threshold" min="1" max="10" value="5" style="width: 100%;" />
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #999;">
                        <span>低</span><span id="threshold-value">5</span><span>高</span>
                    </div>
                </div>
                
                <div style="margin-top: 24px; display: flex; gap: 10px; justify-content: flex-end;">
                    <button id="settings-reset" style="padding: 10px 20px; background: #f0f0f0; color: #333; border: none; border-radius: 8px; cursor: pointer;">重置默认</button>
                    <button id="settings-save" style="padding: 10px 20px; background: #0a84ff; color: white; border: none; border-radius: 8px; cursor: pointer;">保存设置</button>
                </div>
            </div>
        `;
        
        const { close } = createModal('系统设置', content, '550px');
        
        // 阈值显示
        document.getElementById('setting-risk-threshold').oninput = (e) => {
            document.getElementById('threshold-value').textContent = e.target.value;
        };
        
        // 保存设置
        document.getElementById('settings-save').onclick = async () => {
            const settings = {
                collect_interval: document.getElementById('setting-collect-interval').value,
                ai_provider: document.getElementById('setting-ai-provider').value,
                auto_collect: document.getElementById('setting-auto-collect').checked,
                risk_threshold: document.getElementById('setting-risk-threshold').value
            };
            
            try {
                await api('/api/settings', {
                    method: 'POST',
                    body: settings
                });
                toast('设置保存成功', 'success');
                close();
            } catch (error) {
                toast('设置保存失败: ' + error.message, 'error');
            }
        };
        
        // 重置设置
        document.getElementById('settings-reset').onclick = () => {
            document.getElementById('setting-collect-interval').value = 120;
            document.getElementById('setting-ai-provider').value = 'auto';
            document.getElementById('setting-auto-collect').checked = true;
            document.getElementById('setting-risk-threshold').value = 5;
            document.getElementById('threshold-value').textContent = '5';
            toast('已重置为默认值');
        };
    }

    // ========== 导出功能 ==========
    function openExport() {
        const content = `
            <div id="export-container">
                <div style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 12px 0; color: #333;">导出报告</h4>
                    <div style="background: #f9f9f9; padding: 12px; border-radius: 8px; font-size: 13px; color: #666;">
                        选择报告类型和时间范围，导出为Word或Excel格式。
                    </div>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">报告类型</label>
                    <select id="export-type" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;">
                        <option value="daily">日报</option>
                        <option value="weekly">周报</option>
                        <option value="monthly">月报</option>
                        <option value="custom">自定义报告</option>
                    </select>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">导出格式</label>
                    <div style="display: flex; gap: 12px;">
                        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                            <input type="radio" name="export-format" value="word" checked />
                            <span>📄 Word文档</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                            <input type="radio" name="export-format" value="excel" />
                            <span>📊 Excel表格</span>
                        </label>
                    </div>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">时间范围</label>
                    <div style="display: flex; gap: 10px;">
                        <input type="date" id="export-start" style="flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;" />
                        <span style="align-self: center; color: #999;">至</span>
                        <input type="date" id="export-end" style="flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;" />
                    </div>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">包含内容</label>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="include-notes" checked />
                            <span>舆情笔记列表</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="include-events" checked />
                            <span>舆情事件汇总</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="include-analysis" checked />
                            <span>AI分析与建议</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="include-charts" />
                            <span>图表数据（仅Excel）</span>
                        </label>
                    </div>
                </div>
                
                <div style="margin-top: 24px; display: flex; gap: 10px; justify-content: flex-end;">
                    <button id="export-cancel" style="padding: 10px 20px; background: #f0f0f0; color: #333; border: none; border-radius: 8px; cursor: pointer;">取消</button>
                    <button id="export-generate" style="padding: 10px 20px; background: #0a84ff; color: white; border: none; border-radius: 8px; cursor: pointer;">生成报告</button>
                </div>
            </div>
        `;
        
        const { close } = createModal('导出报告', content, '600px');
        
        // 设置默认日期
        const today = new Date();
        const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
        document.getElementById('export-end').value = today.toISOString().split('T')[0];
        document.getElementById('export-start').value = weekAgo.toISOString().split('T')[0];
        
        // 取消
        document.getElementById('export-cancel').onclick = close;
        
        // 生成报告
        document.getElementById('export-generate').onclick = async () => {
            const format = document.querySelector('input[name="export-format"]:checked').value;
            const type = document.getElementById('export-type').value;
            const start = document.getElementById('export-start').value;
            const end = document.getElementById('export-end').value;
            
            const btn = document.getElementById('export-generate');
            btn.textContent = '生成中...';
            btn.disabled = true;
            
            try {
                const response = await api(`/api/export/generate?type=${type}&format=${format}&start=${start}&end=${end}`, {
                    method: 'POST'
                });
                
                if (response.download_url) {
                    toast('报告生成成功，开始下载', 'success');
                    window.open(response.download_url, '_blank');
                    close();
                } else {
                    toast('报告生成成功', 'success');
                    close();
                }
            } catch (error) {
                toast('报告生成失败: ' + error.message, 'error');
            } finally {
                btn.textContent = '生成报告';
                btn.disabled = false;
            }
        };
    }

    // ========== 采集器控制 ==========
    function openCollectorControl() {
        const content = `
            <div id="collector-container">
                <div style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 12px 0; color: #333;">采集器控制</h4>
                    <div style="background: #f9f9f9; padding: 12px; border-radius: 8px; font-size: 13px; color: #666;">
                        手动控制采集器，查看采集状态和历史记录。
                    </div>
                </div>
                
                <div id="collector-status" style="margin-bottom: 20px; padding: 16px; background: #f0f8ff; border-radius: 8px; border-left: 4px solid #0a84ff;">
                    <div style="font-weight: 600; margin-bottom: 8px;">采集器状态</div>
                    <div id="collector-status-detail" style="font-size: 14px; color: #666;">加载中...</div>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">采集模式</label>
                    <select id="collector-mode" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;">
                        <option value="quick">快速采集（约5分钟）</option>
                        <option value="standard" selected>标准采集（约20分钟）</option>
                        <option value="deep">深度采集（约30分钟）</option>
                    </select>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500; color: #333;">采集关键词</label>
                    <input type="text" id="collector-keywords" value="广州太古汇" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;" placeholder="多个关键词用逗号分隔" />
                </div>
                
                <div id="collector-progress" style="margin-bottom: 16px; display: none;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                        <span>采集中...</span>
                        <span id="collector-progress-text">0%</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: #eee; border-radius: 4px; overflow: hidden;">
                        <div id="collector-progress-bar" style="height: 100%; background: #0a84ff; width: 0%; transition: width 0.3s ease;"></div>
                    </div>
                </div>
                
                <div style="margin-top: 24px; display: flex; gap: 10px; justify-content: flex-end;">
                    <button id="collector-refresh" style="padding: 10px 20px; background: #f0f0f0; color: #333; border: none; border-radius: 8px; cursor: pointer;">刷新状态</button>
                    <button id="collector-start" style="padding: 10px 20px; background: #34c759; color: white; border: none; border-radius: 8px; cursor: pointer;">开始采集</button>
                    <button id="collector-stop" style="padding: 10px 20px; background: #ff3b30; color: white; border: none; border-radius: 8px; cursor: pointer; display: none;">停止采集</button>
                </div>
            </div>
        `;
        
        const { close } = createModal('采集器控制', content, '600px');
        
        // 加载采集器状态
        const loadStatus = async () => {
            try {
                const status = await api('/api/collector/status');
                const detail = document.getElementById('collector-status-detail');
                detail.innerHTML = `
                    <div>状态: <strong>${status.running ? '采集中' : '空闲'}</strong></div>
                    <div>今日采集次数: ${status.today_count || 0}</div>
                    <div>最后采集: ${status.last_collection || '未采集'}</div>
                    <div>新增笔记: ${status.new_notes || 0}条</div>
                `;
                
                // 更新按钮状态
                document.getElementById('collector-start').style.display = status.running ? 'none' : 'inline-block';
                document.getElementById('collector-stop').style.display = status.running ? 'inline-block' : 'none';
                document.getElementById('collector-progress').style.display = status.running ? 'block' : 'none';
                
            } catch (error) {
                document.getElementById('collector-status-detail').innerHTML = `<span style="color: #ff3b30;">状态加载失败: ${error.message}</span>`;
            }
        };
        
        loadStatus();
        
        // 刷新状态
        document.getElementById('collector-refresh').onclick = loadStatus;
        
        // 开始采集
        document.getElementById('collector-start').onclick = async () => {
            const mode = document.getElementById('collector-mode').value;
            const keywords = document.getElementById('collector-keywords').value;
            
            try {
                await api('/api/collector/start', {
                    method: 'POST',
                    body: { mode, keywords }
                });
                toast('采集已启动', 'success');
                loadStatus();
                
                // 模拟进度更新
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress += Math.random() * 10;
                    if (progress >= 100) {
                        progress = 100;
                        clearInterval(progressInterval);
                        setTimeout(loadStatus, 1000);
                    }
                    document.getElementById('collector-progress-bar').style.width = progress + '%';
                    document.getElementById('collector-progress-text').textContent = Math.round(progress) + '%';
                }, 2000);
                
            } catch (error) {
                toast('采集启动失败: ' + error.message, 'error');
            }
        };
        
        // 停止采集
        document.getElementById('collector-stop').onclick = async () => {
            try {
                await api('/api/collector/stop', { method: 'POST' });
                toast('采集已停止', 'success');
                loadStatus();
            } catch (error) {
                toast('停止失败: ' + error.message, 'error');
            }
        };
    }

    // ========== 初始化按钮 ==========
    function initButtons() {
        // 等待DOM加载完成
        const addButton = (id, title, icon, onClick) => {
            const existing = document.getElementById(id);
            if (existing) {
                existing.onclick = onClick;
                return;
            }
            
            // 尝试添加到header-right
            const headerRight = document.querySelector('.header-right') || document.querySelector('.header-actions');
            if (headerRight) {
                const btn = document.createElement('button');
                btn.id = id;
                btn.className = 'btn btn-secondary';
                btn.style.cssText = 'margin-left: 8px; padding: 6px 12px; font-size: 13px;';
                btn.innerHTML = `${icon} ${title}`;
                btn.onclick = onClick;
                headerRight.appendChild(btn);
            }
        };
        
        // 添加AI聊天按钮
        addButton('btn-ai-chat', 'AI助手', '🤖', openAIChat);
        
        // 添加设置按钮（如果已存在则绑定事件）
        const settingsBtn = document.getElementById('btn-settings');
        if (settingsBtn) {
            settingsBtn.onclick = openSettings;
        }
        
        // 添加导出按钮
        addButton('btn-export', '导出', '📤', openExport);
        
        // 添加采集器控制按钮
        addButton('btn-collector', '采集', '🔍', openCollectorControl);
    }

    // DOM加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initButtons);
    } else {
        initButtons();
    }

    // 暴露到全局，供其他脚本调用
    window.SystemControls = {
        openAIChat,
        openSettings,
        openExport,
        openCollectorControl,
        toast
    };

})();
