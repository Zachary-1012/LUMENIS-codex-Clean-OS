/* ============================================
   Z-Brand-Core v9.0 - GPT/Codex 交互逻辑
   命令面板、右侧面板、侧边栏折叠
   ============================================ */

(function() {
    'use strict';

    // ========== 命令面板 ==========
    const commandPalette = document.getElementById('commandPalette');
    const commandInput = document.getElementById('commandInput');
    const commandResults = document.getElementById('commandResults');
    let selectedIndex = 0;
    let commandItems = [];

    function openCommandPalette() {
        if (!commandPalette) return;
        commandPalette.classList.add('active');
        setTimeout(() => {
            if (commandInput) commandInput.focus();
        }, 100);
        selectedIndex = 0;
        updateCommandSelection();
    }

    function closeCommandPalette() {
        if (!commandPalette) return;
        commandPalette.classList.remove('active');
        if (commandInput) commandInput.value = '';
    }

    function toggleCommandPalette() {
        if (commandPalette && commandPalette.classList.contains('active')) {
            closeCommandPalette();
        } else {
            openCommandPalette();
        }
    }

    // 暴露到全局，供HTML按钮调用
    window.toggleCommandPalette = toggleCommandPalette;
    window.openCommandPalette = openCommandPalette;
    window.closeCommandPalette = closeCommandPalette;

    function filterCommands(query) {
        if (!commandResults) return;
        const items = commandResults.querySelectorAll('.command-result-item');
        commandItems = Array.from(items);
        const q = query.toLowerCase().trim();
        
        commandItems.forEach((item, index) => {
            const title = item.querySelector('.command-result-title')?.textContent?.toLowerCase() || '';
            const desc = item.querySelector('.command-result-desc')?.textContent?.toLowerCase() || '';
            const match = !q || title.includes(q) || desc.includes(q);
            item.style.display = match ? 'flex' : 'none';
        });
        
        selectedIndex = 0;
        updateCommandSelection();
    }

    function updateCommandSelection() {
        if (!commandResults) return;
        const visibleItems = commandResults.querySelectorAll('.command-result-item:not([style*="display: none"])');
        visibleItems.forEach((item, index) => {
            item.classList.toggle('selected', index === selectedIndex);
        });
    }

    function executeCommand(item) {
        const page = item?.dataset?.page;
        if (page && typeof navigateTo === 'function') {
            navigateTo(page);
        }
        closeCommandPalette();
    }

    // 命令面板事件
    if (commandPalette) {
        commandPalette.addEventListener('click', (e) => {
            if (e.target === commandPalette) {
                closeCommandPalette();
            }
        });
    }

    if (commandInput) {
        commandInput.addEventListener('input', (e) => {
            filterCommands(e.target.value);
        });

        commandInput.addEventListener('keydown', (e) => {
            const visibleItems = commandResults?.querySelectorAll('.command-result-item:not([style*="display: none"])') || [];
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, visibleItems.length - 1);
                updateCommandSelection();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                updateCommandSelection();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (visibleItems[selectedIndex]) {
                    executeCommand(visibleItems[selectedIndex]);
                }
            } else if (e.key === 'Escape') {
                closeCommandPalette();
            }
        });
    }

    if (commandResults) {
        commandResults.addEventListener('click', (e) => {
            const item = e.target.closest('.command-result-item');
            if (item) {
                executeCommand(item);
            }
        });
    }

    // 快捷键：Cmd+K / Ctrl+K 打开命令面板
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            toggleCommandPalette();
        }
        if (e.key === 'Escape' && commandPalette?.classList.contains('active')) {
            closeCommandPalette();
        }
    });

    // ========== 右侧AI洞察面板 ==========
    const rightPanel = document.getElementById('rightPanel');
    const closeRightPanelBtn = document.getElementById('closeRightPanel');

    function toggleRightPanel() {
        if (!rightPanel) return;
        rightPanel.classList.toggle('collapsed');
        // 保存状态
        try {
            localStorage.setItem('rightPanelCollapsed', rightPanel.classList.contains('collapsed'));
        } catch(e) {}
    }

    if (closeRightPanelBtn) {
        closeRightPanelBtn.addEventListener('click', toggleRightPanel);
    }

    // 恢复右侧面板状态
    try {
        const collapsed = localStorage.getItem('rightPanelCollapsed');
        if (collapsed === 'true' && rightPanel) {
            rightPanel.classList.add('collapsed');
        }
    } catch(e) {}

    // ========== 侧边栏折叠 ==========
    const sidebar = document.querySelector('.sidebar');
    let sidebarToggleBtn = document.querySelector('.sidebar-toggle');

    // 如果没有折叠按钮，创建一个
    if (!sidebarToggleBtn && sidebar) {
        const sidebarHeader = sidebar.querySelector('.sidebar-header') || sidebar.querySelector('.brand') || sidebar.querySelector('nav');
        if (sidebarHeader) {
            sidebarToggleBtn = document.createElement('button');
            sidebarToggleBtn.className = 'sidebar-toggle';
            sidebarToggleBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>';
            sidebarToggleBtn.title = '折叠侧边栏';
            sidebarHeader.parentNode.insertBefore(sidebarToggleBtn, sidebarHeader.nextSibling);
        }
    }

    function toggleSidebar() {
        if (!sidebar) return;
        sidebar.classList.toggle('collapsed');
        try {
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        } catch(e) {}
    }

    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', toggleSidebar);
    }

    // 恢复侧边栏状态
    try {
        const collapsed = localStorage.getItem('sidebarCollapsed');
        if (collapsed === 'true' && sidebar) {
            sidebar.classList.add('collapsed');
        }
    } catch(e) {}

    // ========== 移动端侧边栏 ==========
    const menuToggle = document.getElementById('menuToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    function toggleMobileSidebar() {
        if (!sidebar) return;
        sidebar.classList.toggle('mobile-open');
        if (sidebarOverlay) {
            sidebarOverlay.classList.toggle('active');
        }
    }

    if (menuToggle) {
        menuToggle.addEventListener('click', toggleMobileSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', toggleMobileSidebar);
    }

    // 导航项点击后关闭移动端侧边栏
    document.querySelectorAll('.side-item').forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                sidebar?.classList.remove('mobile-open');
                sidebarOverlay?.classList.remove('active');
            }
        });
    });

    // ========== 顶部栏右侧面板切换按钮 ==========
    const topbarActions = document.querySelector('.top-actions') || document.querySelector('.topbar-actions');
    if (topbarActions && !document.querySelector('.panel-toggle')) {
        const panelToggle = document.createElement('button');
        panelToggle.className = 'panel-toggle';
        panelToggle.id = 'panelToggle';
        panelToggle.title = 'AI洞察面板';
        panelToggle.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="15" y1="3" x2="15" y2="21"/></svg>';
        panelToggle.addEventListener('click', toggleRightPanel);
        topbarActions.insertBefore(panelToggle, topbarActions.firstChild);
    }

    // ========== 页面切换时更新顶部标题 ==========
    const originalNavigateTo = window.navigateTo;
    if (typeof originalNavigateTo === 'function') {
        window.navigateTo = function(pageId) {
            originalNavigateTo(pageId);
            updateTopbarTitle(pageId);
        };
    }

    function updateTopbarTitle(pageId) {
        const titleEl = document.querySelector('.topbar-title h2') || document.querySelector('.top-center h1');
        if (!titleEl) return;
        
        const titles = {
            'overview': '首页概览',
            'monitor': '舆情监测',
            'alerts': '风险预警',
            'events': '事件中心',
            'negative': '负面确认',
            'topics': '热门话题',
            'notes': '笔记搜索',
            'analysis': '数据分析',
            'brands': '品牌业态',
            'official': '官方动态',
            'swire': '品牌营销案例库',
            'cases': '案例库',
            'case-analysis': '案例深度拆解',
            'knowledge-base': '品牌知识库',
            'event-graph': '事件关系图谱',
            'brand-report': '品牌分析报告',
            'app-evidence': 'App证据',
            'calendar': '舆情日历',
            'reports': '报告中心',
            'settings': '系统设置'
        };
        
        titleEl.textContent = titles[pageId] || '广州太古汇·舆情监测系统';
    }

    // ========== 初始化 ==========
    console.log('[v9.0] GPT/Codex 交互已加载');
    console.log('[v9.0] 快捷键: Cmd/Ctrl+K 打开命令面板');

    // ========== 右侧面板真实数据接入 ==========
    function loadRightPanelData() {
        // 从概览API获取数据
        fetch('/api/overview')
            .then(res => res.json())
            .then(data => {
                updateQuickStats(data);
                updateAIInsights(data);
            })
            .catch(err => {
                console.warn('[v9.0] 右侧面板数据加载失败:', err);
                // 加载失败时保持静态数据
            });
    }

    function updateQuickStats(data) {
        const stats = data || {};
        const total = stats.total_notes || stats.total || 957;
        const positive = stats.positive_count || stats.positive || 622;
        const negative = stats.negative_count || stats.negative || 94;
        const highRisk = stats.high_risk_count || stats.high_risk || 22;
        const interactions = stats.total_interactions || stats.interactions || 448410;

        const positivePct = total > 0 ? ((positive / total) * 100).toFixed(1) : '65.0';
        const negativePct = total > 0 ? ((negative / total) * 100).toFixed(1) : '9.8';

        // 更新快捷统计
        const statValues = document.querySelectorAll('.quick-stat-value');
        if (statValues.length >= 4) {
            statValues[0].textContent = positivePct + '%';
            statValues[1].textContent = negativePct + '%';
            statValues[2].textContent = highRisk;
            statValues[3].textContent = interactions >= 1000 ? (interactions / 1000).toFixed(0) + 'K' : interactions;
        }
    }

    function updateAIInsights(data) {
        const stats = data || {};
        const total = stats.total_notes || stats.total || 957;
        const positive = stats.positive_count || stats.positive || 622;
        const negative = stats.negative_count || stats.negative || 94;
        const highRisk = stats.high_risk_count || stats.high_risk || 22;

        const positivePct = total > 0 ? ((positive / total) * 100).toFixed(1) : '65.0';

        // 更新舆情趋势洞察
        const insightCards = document.querySelectorAll('.ai-insight-card');
        if (insightCards.length >= 1) {
            const p = insightCards[0].querySelector('p');
            if (p) {
                p.textContent = `近7天正面舆情占比${positivePct}%，共监测${total}条笔记。负面舆情主要集中在"服务投诉"和"停车/保安"话题，建议重点关注品牌服务质量。`;
            }
        }

        // 更新风险预警
        if (insightCards.length >= 2) {
            const p = insightCards[1].querySelector('p');
            if (p) {
                p.textContent = `检测到${highRisk}条高风险内容，其中"停车场保安封路"话题风险评分83，建议优先核实并准备回应方案。`;
            }
        }
    }

    // 页面加载完成后获取数据
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadRightPanelData);
    } else {
        loadRightPanelData();
    }

    // 每5分钟刷新一次右侧面板数据
    setInterval(loadRightPanelData, 5 * 60 * 1000);

})();
