// App Evidence 前端逻辑 v2.0（Shadow模式，不碰App自动化）
// 支持：小红书App/微信小程序/微信公众号/抖音App/微博App
const AppEvidence = {
    initialized: false,
    selectedFile: null,

    init() {
        if (this.initialized) return;
        this.initialized = true;
        this.loadStats();
        this.loadList();
        this.setupDragDrop();
    },

    // 平台选择卡片联动
    selectPlatform(platform) {
        // 更新卡片激活状态
        document.querySelectorAll('.ae-platform-card').forEach(card => {
            card.classList.toggle('active', card.dataset.platform === platform);
        });
        // 更新下拉选择
        document.getElementById('aeSource').value = platform;
        // 小程序专属字段显示/隐藏
        const isMini = platform === 'wechat_mini';
        document.getElementById('aeMiniAppNameWrap').style.display = isMini ? 'block' : 'none';
        document.getElementById('aeMiniPagePathWrap').style.display = isMini ? 'block' : 'none';
        // 更新指标选项（公众号显示阅读量/在看数，小程序显示访问量/UV）
        this.updateMetricOptions(platform);
    },

    // 根据平台更新指标选项
    updateMetricOptions(platform) {
        const metricSelect = document.getElementById('aeMetricName');
        const options = {
            xhs_app: [
                {value: 'browse_count', label: '浏览量'},
                {value: 'discussion_count', label: '讨论量'},
                {value: 'note_count', label: '笔记数'},
                {value: 'like_count', label: '点赞数'},
                {value: 'comment_count', label: '评论数'},
                {value: 'collect_count', label: '收藏数'},
                {value: 'share_count', label: '分享数'},
            ],
            wechat_mini: [
                {value: 'visit_count', label: '访问次数'},
                {value: 'uv_count', label: '独立访客(UV)'},
                {value: 'browse_count', label: '页面浏览量(PV)'},
                {value: 'share_count', label: '分享次数'},
                {value: 'like_count', label: '点赞数'},
                {value: 'comment_count', label: '评论数'},
                {value: 'collect_count', label: '收藏数'},
            ],
            wechat_mp: [
                {value: 'read_count', label: '阅读量'},
                {value: 'watching_count', label: '在看数'},
                {value: 'like_count', label: '点赞数'},
                {value: 'comment_count', label: '评论数'},
                {value: 'share_count', label: '分享数'},
                {value: 'collect_count', label: '收藏数'},
            ],
            douyin_app: [
                {value: 'browse_count', label: '播放量'},
                {value: 'like_count', label: '点赞数'},
                {value: 'comment_count', label: '评论数'},
                {value: 'collect_count', label: '收藏数'},
                {value: 'share_count', label: '分享数'},
            ],
            weibo_app: [
                {value: 'browse_count', label: '阅读量'},
                {value: 'like_count', label: '点赞数'},
                {value: 'comment_count', label: '评论数'},
                {value: 'share_count', label: '转发数'},
                {value: 'collect_count', label: '收藏数'},
            ],
            other: [
                {value: 'browse_count', label: '浏览量'},
                {value: 'other', label: '其他'},
            ],
        };
        const opts = options[platform] || options.other;
        metricSelect.innerHTML = opts.map(o => `<option value="${o.value}">${o.label}</option>`).join('');
    },

    // 文件选择处理
    handleFileSelect(input) {
        if (input.files && input.files[0]) {
            this.selectedFile = input.files[0];
            this.showFilePreview(this.selectedFile);
        }
    },

    // 显示文件预览
    showFilePreview(file) {
        const preview = document.getElementById('aeFilePreview');
        preview.style.display = 'block';
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.innerHTML = `
                    <div style="display:flex;align-items:center;gap:10px;padding:8px;background:var(--bg-secondary);border-radius:8px">
                        <img src="${e.target.result}" style="width:48px;height:48px;object-fit:cover;border-radius:6px">
                        <div style="flex:1;min-width:0">
                            <div style="font-size:12px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${file.name}</div>
                            <div style="font-size:11px;color:var(--text-tertiary)">${(file.size / 1024).toFixed(1)} KB</div>
                        </div>
                        <button onclick="AppEvidence.clearFile()" style="background:none;border:none;color:var(--text-tertiary);cursor:pointer;font-size:16px">×</button>
                    </div>
                `;
            };
            reader.readAsDataURL(file);
        } else {
            preview.innerHTML = `
                <div style="display:flex;align-items:center;gap:10px;padding:8px;background:var(--bg-secondary);border-radius:8px">
                    <div style="width:48px;height:48px;background:var(--bg-tertiary);border-radius:6px;display:flex;align-items:center;justify-content:center">${xicon('doc', 22)}</div>
                    <div style="flex:1;min-width:0">
                        <div style="font-size:12px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${file.name}</div>
                        <div style="font-size:11px;color:var(--text-tertiary)">${(file.size / 1024).toFixed(1)} KB</div>
                    </div>
                    <button onclick="AppEvidence.clearFile()" style="background:none;border:none;color:var(--text-tertiary);cursor:pointer;font-size:16px">×</button>
                </div>
            `;
        }
    },

    // 清除文件
    clearFile() {
        this.selectedFile = null;
        document.getElementById('aeFile').value = '';
        document.getElementById('aeFilePreview').style.display = 'none';
    },

    // 拖拽上传设置
    setupDragDrop() {
        const dropZone = document.querySelector('.ae-file-upload');
        if (!dropZone) return;
        ['dragenter', 'dragover'].forEach(evt => {
            dropZone.addEventListener(evt, (e) => {
                e.preventDefault();
                dropZone.style.borderColor = 'var(--apple-blue)';
                dropZone.style.background = 'rgba(0,113,227,0.05)';
            });
        });
        ['dragleave', 'drop'].forEach(evt => {
            dropZone.addEventListener(evt, (e) => {
                e.preventDefault();
                dropZone.style.borderColor = '';
                dropZone.style.background = '';
            });
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                document.getElementById('aeFile').files = e.dataTransfer.files;
                this.handleFileSelect(document.getElementById('aeFile'));
            }
        });
    },

    // 重置表单
    resetForm() {
        document.getElementById('aeSource').value = 'xhs_app';
        document.getElementById('aeCaptureMode').value = 'screenshot';
        document.getElementById('aeTopic').value = '';
        document.getElementById('aeMetricValue').value = '';
        document.getElementById('aeNotes').value = '';
        document.getElementById('aeMiniAppName').value = '';
        document.getElementById('aeMiniPagePath').value = '';
        this.clearFile();
        this.selectPlatform('xhs_app');
        document.getElementById('aeUploadStatus').textContent = '';
    },

    async loadStats() {
        try {
            const res = await fetch('/api/app_evidence/stats');
            const data = await res.json();
            if (data.ok) {
                const s = data.data;
                document.getElementById('aeStats').innerHTML = `
                    <div class="kb-stats-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:16px 0">
                        <div class="metric-card" style="padding:14px;cursor:default">
                            <div style="font-size:22px;font-weight:700">${s.total}</div>
                            <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px">总证据数</div>
                        </div>
                        <div class="metric-card" style="padding:14px;cursor:default">
                            <div style="font-size:22px;font-weight:700;color:var(--apple-orange)">${s.pending}</div>
                            <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px">待确认</div>
                        </div>
                        <div class="metric-card" style="padding:14px;cursor:default">
                            <div style="font-size:22px;font-weight:700;color:var(--apple-green)">${s.confirmed}</div>
                            <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px">已确认</div>
                        </div>
                        <div class="metric-card" style="padding:14px;cursor:default">
                            <div style="font-size:22px;font-weight:700;color:var(--apple-purple)">${s.shadow}</div>
                            <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px">Shadow</div>
                        </div>
                        <div class="metric-card" style="padding:14px;cursor:default">
                            <div style="font-size:22px;font-weight:700;color:var(--apple-red)">${s.rejected}</div>
                            <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px">已拒绝</div>
                        </div>
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
            const source = document.getElementById('aeSourceFilter')?.value || '';
            const topic = document.getElementById('aeTopicSearch').value;
            let url = '/api/app_evidence/list?limit=50';
            if (status) url += `&status=${status}`;
            if (source) url += `&source=${source}`;
            if (topic) url += `&topic=${encodeURIComponent(topic)}`;

            const res = await fetch(url);
            const data = await res.json();
            if (data.ok) {
                const records = data.data.records;
                const total = data.data.total;
                if (records.length === 0) {
                    document.getElementById('aeList').innerHTML = `
                        <div style="text-align:center;padding:48px;color:var(--text-tertiary)">
                            <div style="margin-bottom:16px">${xicon('list', 42)}</div>
                            <div style="font-size:15px;font-weight:500;margin-bottom:6px">暂无证据记录</div>
                            <div style="font-size:12px">选择平台，上传截图，填写字段，人工确认后进入Shadow</div>
                        </div>
                    `;
                    return;
                }

                const statusMap = {
                    pending: { label: '待确认', color: 'var(--apple-orange)' },
                    confirmed: { label: '已确认', color: 'var(--apple-green)' },
                    rejected: { label: '已拒绝', color: 'var(--apple-red)' },
                    shadow: { label: 'Shadow', color: 'var(--apple-purple)' }
                };
                const sourceMap = {
                    xhs_app: { label: '小红书App', icon: 'book' },
                    wechat_mini: { label: '微信小程序', icon: 'chat' },
                    wechat_mp: { label: '微信公众号', icon: 'megaphone' },
                    douyin_app: { label: '抖音App', icon: 'music' },
                    weibo_app: { label: '微博App', icon: 'globe' },
                    other: { label: '其他', icon: 'phone' }
                };
                const metricMap = {
                    browse_count: '浏览量', visit_count: '访问次数', uv_count: '独立访客',
                    discussion_count: '讨论量', note_count: '笔记数', like_count: '点赞数',
                    comment_count: '评论数', collect_count: '收藏数', share_count: '分享数',
                    read_count: '阅读量', watching_count: '在看数', other: '其他'
                };

                document.getElementById('aeList').innerHTML = `
                    <div style="font-size:12px;color:var(--text-tertiary);margin:12px 0">共 ${total} 条记录</div>
                    <div style="display:flex;flex-direction:column;gap:10px">
                        ${records.map(r => {
                            const st = statusMap[r.status] || { label: r.status, color: '#6b7280' };
                            const src = sourceMap[r.source] || { label: r.source, icon: 'phone' };
                            return `
                            <div class="panel" style="padding:14px;margin-bottom:0">
                                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
                                    <div style="flex:1;min-width:200px">
                                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap">
                                            <span style="background:${st.color}15;color:${st.color};padding:3px 10px;border-radius:var(--radius-full);font-size:11px;font-weight:600">${st.label}</span>
                                            <span style="font-size:12px;color:var(--text-secondary)">${xicon(src.icon, 14)} ${src.label}</span>
                                            <span style="font-size:11px;color:var(--text-tertiary)">#${r.id}</span>
                                        </div>
                                        <div style="font-size:14px;font-weight:600;margin-bottom:4px">
                                            ${metricMap[r.metric_name] || r.metric_name}: <span style="color:var(--apple-blue)">${r.metric_value}</span>
                                        </div>
                                        <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px">
                                            话题: ${r.topic || '未关联'} | 采集时间: ${r.captured_at || '-'}
                                        </div>
                                        ${r.notes ? `<div style="font-size:12px;color:var(--text-tertiary)">备注: ${r.notes}</div>` : ''}
                                    </div>
                                    <div style="display:flex;gap:6px;flex-wrap:wrap">
                                        ${r.status === 'pending' ? `
                                            <button class="action secondary" style="padding:5px 10px;font-size:11px" onclick="AppEvidence.confirm(${r.id})">确认</button>
                                            <button class="action secondary" style="padding:5px 10px;font-size:11px;color:var(--apple-purple)" onclick="AppEvidence.shadow(${r.id})">◐ Shadow</button>
                                            <button class="action secondary" style="padding:5px 10px;font-size:11px;color:var(--apple-red)" onclick="AppEvidence.reject(${r.id})">拒绝</button>
                                        ` : ''}
                                        <button class="action tertiary" style="padding:5px 10px;font-size:11px;color:var(--apple-red)" onclick="AppEvidence.remove(${r.id})">删除</button>
                                    </div>
                                </div>
                            </div>
                        `;}).join('')}
                    </div>
                `;
            }
        } catch (e) {
            console.error('AppEvidence list error:', e);
            document.getElementById('aeList').innerHTML = `<div style="color:var(--apple-red);padding:20px">加载失败: ${e.message}</div>`;
        }
    },

    async upload() {
        const source = document.getElementById('aeSource').value;
        const captureMode = document.getElementById('aeCaptureMode').value;
        const topic = document.getElementById('aeTopic').value;
        const metricName = document.getElementById('aeMetricName').value;
        const metricValue = document.getElementById('aeMetricValue').value;
        const notes = document.getElementById('aeNotes').value;
        const miniAppName = document.getElementById('aeMiniAppName')?.value || '';
        const miniPagePath = document.getElementById('aeMiniPagePath')?.value || '';
        const fileInput = document.getElementById('aeFile');
        const statusEl = document.getElementById('aeUploadStatus');

        if (!metricValue) {
            statusEl.textContent = '请填写指标值';
            statusEl.style.color = 'var(--apple-red)';
            return;
        }

        statusEl.textContent = '上传中...';
        statusEl.style.color = 'var(--text-tertiary)';

        // 合并备注（包含小程序专属字段）
        let fullNotes = notes;
        if (source === 'wechat_mini') {
            if (miniAppName) fullNotes = `[小程序:${miniAppName}] ${fullNotes}`;
            if (miniPagePath) fullNotes += ` [页面:${miniPagePath}]`;
        }

        const formData = new FormData();
        formData.append('source', source);
        formData.append('capture_mode', captureMode);
        formData.append('topic', topic);
        formData.append('metric_name', metricName);
        formData.append('metric_value', metricValue);
        formData.append('notes', fullNotes);
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
                statusEl.textContent = '上传成功（待人工确认）';
                statusEl.style.color = 'var(--apple-green)';
                setTimeout(() => { statusEl.textContent = ''; }, 3000);
                this.resetForm();
                this.loadStats();
                this.loadList();
            } else {
                statusEl.textContent = '上传失败: ' + (data.error || '未知错误');
                statusEl.style.color = 'var(--apple-red)';
            }
        } catch (e) {
            statusEl.textContent = '上传失败: ' + e.message;
            statusEl.style.color = 'var(--apple-red)';
        }
    },

    async confirm(id) {
        if (!confirm('确认这条证据？确认后进入Shadow模式。')) return;
        try {
            const formData = new FormData();
            formData.append('verified_by', 'Zachary');
            const res = await fetch(`/api/app_evidence/${id}/confirm`, {
                method: 'POST', body: formData
            });
            const data = await res.json();
            if (data.ok) { this.loadStats(); this.loadList(); }
            else alert('确认失败: ' + (data.error || '未知错误'));
        } catch (e) { alert('确认失败: ' + e.message); }
    },

    async shadow(id) {
        if (!confirm('标记为Shadow？')) return;
        try {
            const formData = new FormData();
            formData.append('verified_by', 'Zachary');
            const res = await fetch(`/api/app_evidence/${id}/shadow`, {
                method: 'POST', body: formData
            });
            const data = await res.json();
            if (data.ok) { this.loadStats(); this.loadList(); }
            else alert('操作失败: ' + (data.error || '未知错误'));
        } catch (e) { alert('操作失败: ' + e.message); }
    },

    async reject(id) {
        if (!confirm('拒绝这条证据？')) return;
        try {
            const formData = new FormData();
            formData.append('notes', '人工拒绝');
            const res = await fetch(`/api/app_evidence/${id}/reject`, {
                method: 'POST', body: formData
            });
            const data = await res.json();
            if (data.ok) { this.loadStats(); this.loadList(); }
            else alert('拒绝失败: ' + (data.error || '未知错误'));
        } catch (e) { alert('拒绝失败: ' + e.message); }
    },

    async remove(id) {
        if (!confirm('删除这条证据？证据文件也会被删除。')) return;
        try {
            const res = await fetch(`/api/app_evidence/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.ok) { this.loadStats(); this.loadList(); }
            else alert('删除失败: ' + (data.error || '未知错误'));
        } catch (e) { alert('删除失败: ' + e.message); }
    }
};
