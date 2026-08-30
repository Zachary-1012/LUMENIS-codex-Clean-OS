// App Evidence 前端逻辑（Shadow模式，不碰App自动化）
const AppEvidence = {
    initialized: false,

    init() {
        if (this.initialized) return;
        this.initialized = true;
        this.loadStats();
        this.loadList();
    },

    async loadStats() {
        try {
            const res = await fetch('/api/app_evidence/stats');
            const data = await res.json();
            if (data.ok) {
                const s = data.data;
                document.getElementById('aeStats').innerHTML = `
                    <div class="kb-stats-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:16px 0">
                        <div class="kb-stat-card" style="background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:16px">
                            <div style="font-size:24px;font-weight:700">${s.total}</div>
                            <div style="font-size:12px;color:var(--muted);margin-top:4px">总证据数</div>
                        </div>
                        <div class="kb-stat-card" style="background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:16px">
                            <div style="font-size:24px;font-weight:700;color:#f59e0b">${s.pending}</div>
                            <div style="font-size:12px;color:var(--muted);margin-top:4px">待确认</div>
                        </div>
                        <div class="kb-stat-card" style="background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:16px">
                            <div style="font-size:24px;font-weight:700;color:#10b981">${s.confirmed}</div>
                            <div style="font-size:12px;color:var(--muted);margin-top:4px">已确认</div>
                        </div>
                        <div class="kb-stat-card" style="background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:16px">
                            <div style="font-size:24px;font-weight:700;color:#8b5cf6">${s.shadow}</div>
                            <div style="font-size:12px;color:var(--muted);margin-top:4px">Shadow</div>
                        </div>
                        <div class="kb-stat-card" style="background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:16px">
                            <div style="font-size:24px;font-weight:700;color:#ef4444">${s.rejected}</div>
                            <div style="font-size:12px;color:var(--muted);margin-top:4px">已拒绝</div>
                        </div>
                    </div>
                    <div style="font-size:12px;color:var(--muted);margin-bottom:12px">
                        模块版本: ${s.module_version} | 模式: ${s.mode} | 来源分布: ${Object.entries(s.by_source).map(([k,v])=>`${k}:${v}`).join(', ') || '无'}
                    </div>
                `;
            }
        } catch (e) {
            console.error('AppEvidence stats error:', e);
        }
    },

    async loadList() {
        try {
            const status = document.getElementById('aeStatusFilter').value;
            const topic = document.getElementById('aeTopicSearch').value;
            let url = '/api/app_evidence/list?limit=50';
            if (status) url += `&status=${status}`;
            if (topic) url += `&topic=${encodeURIComponent(topic)}`;

            const res = await fetch(url);
            const data = await res.json();
            if (data.ok) {
                const records = data.data.records;
                const total = data.data.total;
                if (records.length === 0) {
                    document.getElementById('aeList').innerHTML = `
                        <div style="text-align:center;padding:40px;color:var(--muted)">
                            <div style="font-size:40px;margin-bottom:12px">📋</div>
                            <div>暂无证据记录</div>
                            <div style="font-size:12px;margin-top:8px">上传App截图，手动填写字段，人工确认后进入Shadow</div>
                        </div>
                    `;
                    return;
                }

                const statusMap = {
                    pending: { label: '待确认', color: '#f59e0b' },
                    confirmed: { label: '已确认', color: '#10b981' },
                    rejected: { label: '已拒绝', color: '#ef4444' },
                    shadow: { label: 'Shadow', color: '#8b5cf6' }
                };
                const sourceMap = {
                    xhs_app: '小红书App',
                    douyin_app: '抖音App',
                    weibo_app: '微博App',
                    other: '其他'
                };
                const metricMap = {
                    browse_count: '浏览量',
                    discussion_count: '讨论量',
                    note_count: '笔记数',
                    like_count: '点赞数',
                    comment_count: '评论数',
                    collect_count: '收藏数',
                    other: '其他'
                };

                document.getElementById('aeList').innerHTML = `
                    <div style="font-size:12px;color:var(--muted);margin:12px 0">共 ${total} 条记录</div>
                    <div style="display:flex;flex-direction:column;gap:10px">
                        ${records.map(r => {
                            const st = statusMap[r.status] || { label: r.status, color: '#6b7280' };
                            return `
                            <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:14px">
                                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
                                    <div style="flex:1;min-width:200px">
                                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap">
                                            <span style="background:${st.color}20;color:${st.color};padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600">${st.label}</span>
                                            <span style="font-size:12px;color:var(--muted)">${sourceMap[r.source] || r.source}</span>
                                            <span style="font-size:12px;color:var(--muted)">#${r.id}</span>
                                        </div>
                                        <div style="font-size:14px;font-weight:600;margin-bottom:4px">
                                            ${metricMap[r.metric_name] || r.metric_name}: <span style="color:#3b82f6">${r.metric_value}</span>
                                        </div>
                                        <div style="font-size:12px;color:var(--muted);margin-bottom:4px">
                                            话题: ${r.topic || '未关联'} | 采集时间: ${r.captured_at || '-'}
                                        </div>
                                        ${r.notes ? `<div style="font-size:12px;color:var(--muted)">备注: ${r.notes}</div>` : ''}
                                        ${r.verified_by ? `<div style="font-size:11px;color:var(--muted);margin-top:4px">确认人: ${r.verified_by} @ ${r.verified_at}</div>` : ''}
                                    </div>
                                    <div style="display:flex;gap:6px;flex-wrap:wrap">
                                        ${r.status === 'pending' ? `
                                            <button class="tertiary" style="padding:6px 12px;font-size:12px" onclick="AppEvidence.confirm(${r.id})">✓ 确认</button>
                                            <button class="tertiary" style="padding:6px 12px;font-size:12px;color:#8b5cf6" onclick="AppEvidence.shadow(${r.id})">◐ Shadow</button>
                                            <button class="tertiary" style="padding:6px 12px;font-size:12px;color:#ef4444" onclick="AppEvidence.reject(${r.id})">✗ 拒绝</button>
                                        ` : ''}
                                        <button class="tertiary" style="padding:6px 12px;font-size:12px;color:#ef4444" onclick="AppEvidence.remove(${r.id})">删除</button>
                                    </div>
                                </div>
                            </div>
                        `;}).join('')}
                    </div>
                `;
            }
        } catch (e) {
            console.error('AppEvidence list error:', e);
            document.getElementById('aeList').innerHTML = `<div style="color:#ef4444;padding:20px">加载失败: ${e.message}</div>`;
        }
    },

    async upload() {
        const source = document.getElementById('aeSource').value;
        const captureMode = document.getElementById('aeCaptureMode').value;
        const topic = document.getElementById('aeTopic').value;
        const metricName = document.getElementById('aeMetricName').value;
        const metricValue = document.getElementById('aeMetricValue').value;
        const notes = document.getElementById('aeNotes').value;
        const fileInput = document.getElementById('aeFile');

        if (!metricValue) {
            alert('请填写指标值');
            return;
        }

        const formData = new FormData();
        formData.append('source', source);
        formData.append('capture_mode', captureMode);
        formData.append('topic', topic);
        formData.append('metric_name', metricName);
        formData.append('metric_value', metricValue);
        formData.append('notes', notes);
        if (fileInput.files[0]) {
            formData.append('file', fileInput.files[0]);
        }

        try {
            const res = await fetch('/api/app_evidence/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.ok) {
                alert('证据已上传（Shadow模式，待人工确认）');
                // 清空表单
                document.getElementById('aeTopic').value = '';
                document.getElementById('aeMetricValue').value = '';
                document.getElementById('aeNotes').value = '';
                document.getElementById('aeFile').value = '';
                this.loadStats();
                this.loadList();
            } else {
                alert('上传失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            alert('上传失败: ' + e.message);
        }
    },

    async confirm(id) {
        if (!confirm('确认这条证据？确认后进入Shadow模式。')) return;
        try {
            const formData = new FormData();
            formData.append('verified_by', 'Zachary');
            const res = await fetch(`/api/app_evidence/${id}/confirm`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.ok) {
                this.loadStats();
                this.loadList();
            } else {
                alert('确认失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            alert('确认失败: ' + e.message);
        }
    },

    async shadow(id) {
        if (!confirm('标记为Shadow？')) return;
        try {
            const formData = new FormData();
            formData.append('verified_by', 'Zachary');
            const res = await fetch(`/api/app_evidence/${id}/shadow`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.ok) {
                this.loadStats();
                this.loadList();
            } else {
                alert('操作失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            alert('操作失败: ' + e.message);
        }
    },

    async reject(id) {
        if (!confirm('拒绝这条证据？')) return;
        try {
            const formData = new FormData();
            formData.append('notes', '人工拒绝');
            const res = await fetch(`/api/app_evidence/${id}/reject`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.ok) {
                this.loadStats();
                this.loadList();
            } else {
                alert('拒绝失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            alert('拒绝失败: ' + e.message);
        }
    },

    async remove(id) {
        if (!confirm('删除这条证据？证据文件也会被删除。')) return;
        try {
            const res = await fetch(`/api/app_evidence/${id}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (data.ok) {
                this.loadStats();
                this.loadList();
            } else {
                alert('删除失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            alert('删除失败: ' + e.message);
        }
    }
};
