/**
 * 公关案例前端接入 v1.0
 * 在笔记详情页中显示"案例对标"和"话术推荐"
 * 调用后端API: /api/pr/recommend, /api/pr/match
 */

(function() {
    'use strict';

    // 检查是否在笔记详情页
    function isNoteDetailPage() {
        return document.querySelector('.note-detail, .note-detail-modal, #noteDetailModal') !== null;
    }

    // 获取当前笔记的标题和内容
    function getCurrentNoteInfo() {
        const titleEl = document.querySelector('.note-title, .note-detail-title, h2.note-title');
        const contentEl = document.querySelector('.note-content, .note-detail-content, .note-desc');
        return {
            title: titleEl ? titleEl.textContent.trim() : '',
            content: contentEl ? contentEl.textContent.trim() : ''
        };
    }

    // 创建公关案例面板
    function createPRPanel() {
        const panel = document.createElement('div');
        panel.className = 'pr-case-panel';
        panel.id = 'prCasePanel';
        panel.style.cssText = `
            margin-top: 16px;
            padding: 16px;
            background: linear-gradient(135deg, #f8f9ff 0%, #eef2ff 100%);
            border-radius: 12px;
            border: 1px solid #e0e7ff;
        `;
        panel.innerHTML = `
            <div class="pr-panel-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <h4 style="margin:0;font-size:15px;color:#4338ca;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:18px;">${xicon('list',18)}</span> 公关案例对标 & 话术推荐
                </h4>
                <button id="prRefreshBtn" style="padding:4px 12px;border:1px solid #c7d2fe;background:#fff;border-radius:6px;cursor:pointer;font-size:12px;color:#4338ca;">
                    ${xicon('refresh')} 刷新
                </button>
            </div>
            <div id="prLoading" style="text-align:center;padding:20px;color:#6b7280;">
                <div style="display:inline-block;width:20px;height:20px;border:2px solid #c7d2fe;border-top-color:#4338ca;border-radius:50%;animation:spin 0.8s linear infinite;"></div>
                <p style="margin-top:8px;font-size:13px;">正在分析笔记，匹配公关案例...</p>
            </div>
            <div id="prContent" style="display:none;"></div>
            <div id="prError" style="display:none;color:#dc2626;font-size:13px;padding:12px;background:#fef2f2;border-radius:8px;"></div>
        `;
        return panel;
    }

    // 渲染匹配的案例
    function renderMatchedCases(cases) {
        if (!cases || cases.length === 0) {
            return '<p style="color:#6b7280;font-size:13px;margin:8px 0;">暂无匹配的公关案例</p>';
        }
        let html = '<div style="margin-bottom:16px;"><h5 style="margin:0 0 8px 0;font-size:14px;color:#374151;">' + xicon('book') + ' 匹配案例（' + cases.length + '个）</h5>';
        cases.forEach(function(c, idx) {
            const severityColor = c.severity === 'high' ? '#dc2626' : c.severity === 'medium' ? '#f59e0b' : '#10b981';
            html += `
                <div style="padding:10px 12px;background:#fff;border-radius:8px;margin-bottom:8px;border-left:3px solid ${severityColor};">
                    <div style="display:flex;justify-content:space-between;align-items:start;">
                        <strong style="font-size:13px;color:#1f2937;">${idx + 1}. ${c.title || c.case_id || '案例'}</strong>
                        <span style="font-size:11px;padding:2px 6px;background:${severityColor}15;color:${severityColor};border-radius:4px;">${c.severity || '未知'}</span>
                    </div>
                    ${c.category ? '<p style="margin:4px 0;font-size:12px;color:#6b7280;">分类: ' + c.category + '</p>' : ''}
                    ${c.summary ? '<p style="margin:4px 0;font-size:12px;color:#4b5563;line-height:1.5;">' + c.summary.substring(0, 150) + (c.summary.length > 150 ? '...' : '') + '</p>' : ''}
                    ${c.lesson ? '<p style="margin:6px 0 0 0;font-size:12px;color:#059669;background:#ecfdf5;padding:6px 8px;border-radius:4px;">💡 启示: ' + c.lesson.substring(0, 100) + '</p>' : ''}
                </div>
            `;
        });
        html += '</div>';
        return html;
    }

    // 渲染推荐话术
    function renderRecommendedTemplates(templates) {
        if (!templates || templates.length === 0) {
            return '<p style="color:#6b7280;font-size:13px;margin:8px 0;">暂无推荐话术</p>';
        }
        let html = '<div><h5 style="margin:0 0 8px 0;font-size:14px;color:#374151;">' + xicon('chat') + ' 推荐话术（' + templates.length + '个）</h5>';
        templates.forEach(function(t, idx) {
            html += `
                <div style="padding:10px 12px;background:#fff;border-radius:8px;margin-bottom:8px;border:1px solid #e5e7eb;">
                    <strong style="font-size:13px;color:#1f2937;">${idx + 1}. ${t.scene || t.name || '话术模板'}</strong>
                    ${t.formula ? '<p style="margin:6px 0;font-size:12px;color:#4b5563;line-height:1.6;background:#f9fafb;padding:8px;border-radius:6px;">📝 ' + t.formula + '</p>' : ''}
                    ${t.example ? '<p style="margin:6px 0 0 0;font-size:12px;color:#6b7280;line-height:1.5;">示例: ' + t.example.substring(0, 120) + '</p>' : ''}
                    ${t.taboo ? '<p style="margin:6px 0 0 0;font-size:12px;color:#dc2626;background:#fef2f2;padding:6px 8px;border-radius:4px;">⚠️ 禁忌: ' + t.taboo.substring(0, 100) + '</p>' : ''}
                </div>
            `;
        });
        html += '</div>';
        return html;
    }

    // 加载公关案例数据
    async function loadPRData(noteInfo) {
        const panel = document.getElementById('prCasePanel');
        if (!panel) return;

        const loading = document.getElementById('prLoading');
        const content = document.getElementById('prContent');
        const error = document.getElementById('prError');

        loading.style.display = 'block';
        content.style.display = 'none';
        error.style.display = 'none';

        try {
            // 调用推荐API
            const resp = await fetch('/api/pr/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: noteInfo.title,
                    content: noteInfo.content,
                    sentiment: 'negative',
                    top_k: 3
                })
            });

            if (!resp.ok) throw new Error('API请求失败: ' + resp.status);

            const data = await resp.json();

            let html = '';

            // 渲染匹配案例
            if (data.matched_cases || data.cases) {
                html += renderMatchedCases(data.matched_cases || data.cases);
            }

            // 渲染推荐话术
            if (data.recommended_templates || data.templates) {
                html += renderRecommendedTemplates(data.recommended_templates || data.templates);
            }

            // 专报触发判断
            if (data.trigger_check) {
                const tc = data.trigger_check;
                if (tc.should_trigger) {
                    html += `<div style="margin-top:12px;padding:10px 12px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;">
                        <strong style="color:#dc2626;font-size:13px;">${xicon('warn')} 专报触发: ${tc.reason || '符合专报条件'}</strong>
                    </div>`;
                }
            }

            if (html === '') {
                html = '<p style="color:#6b7280;font-size:13px;text-align:center;padding:12px;">暂无匹配的公关案例和话术</p>';
            }

            content.innerHTML = html;
            content.style.display = 'block';
            loading.style.display = 'none';

        } catch (err) {
            loading.style.display = 'none';
            error.style.display = 'block';
            error.textContent = '加载公关案例失败: ' + err.message;
        }
    }

    // 初始化
    function init() {
        // 添加CSS动画
        const style = document.createElement('style');
        style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
        document.head.appendChild(style);

        // 监听笔记详情打开
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            // 检查是否是笔记详情模态框
                            if (node.classList && (node.classList.contains('note-detail-modal') || node.id === 'noteDetailModal')) {
                                setTimeout(function() {
                                    attachPRPanel(node);
                                }, 500);
                            }
                        }
                    });
                }
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });

        // 如果已经在笔记详情页，直接添加
        if (isNoteDetailPage()) {
            const detailContainer = document.querySelector('.note-detail, .note-detail-modal, #noteDetailModal .modal-body');
            if (detailContainer) {
                attachPRPanel(detailContainer);
            }
        }

        console.log('[PR Case Integration] 公关案例前端接入已初始化');
    }

    // 附加公关案例面板
    function attachPRPanel(container) {
        if (container.querySelector('#prCasePanel')) return; // 已存在

        const panel = createPRPanel();
        container.appendChild(panel);

        // 绑定刷新按钮
        const refreshBtn = document.getElementById('prRefreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                const noteInfo = getCurrentNoteInfo();
                loadPRData(noteInfo);
            });
        }

        // 加载数据
        const noteInfo = getCurrentNoteInfo();
        if (noteInfo.title || noteInfo.content) {
            loadPRData(noteInfo);
        } else {
            document.getElementById('prLoading').innerHTML = '<p style="color:#6b7280;font-size:13px;">等待笔记内容加载...</p>';
        }
    }

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
