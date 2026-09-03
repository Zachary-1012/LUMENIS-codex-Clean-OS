/**
 * 前端功能增强模块 - 广州太古汇舆情监测系统 v5.8.0
 * 完善报告中心、品牌业态、案例库、负面审核等功能
 */

(function() {
    'use strict';

    // 认证信息
    const AUTH = window.__Z_AUTH;

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
        const existing = document.getElementById('frontend-toast');
        if (existing) existing.remove();
        
        const toast = document.createElement('div');
        toast.id = 'frontend-toast';
        toast.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 10001;
            padding: 12px 20px; border-radius: 8px; color: white;
            background: ${type === 'error' ? '#ff3b30' : type === 'success' ? '#34c759' : '#1C1917'};
            box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 14px;
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // 创建弹窗
    function createModal(title, content, width = '700px') {
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 10000;
            display: flex; align-items: center; justify-content: center;
        `;
        
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white; border-radius: 12px; width: ${width};
            max-width: 95vw; max-height: 85vh; overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: flex; flex-direction: column;
        `;
        
        modal.innerHTML = `
            <div style="padding: 16px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; font-size: 18px; font-weight: 600;">${title}</h3>
                <button class="modal-close-btn" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #999; padding: 0; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%;">×</button>
            </div>
            <div class="modal-body-content" style="padding: 20px; overflow-y: auto; flex: 1;">${content}</div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        const close = () => overlay.remove();
        overlay.querySelector('.modal-close-btn').onclick = close;
        overlay.onclick = (e) => { if (e.target === overlay) close(); };
        
        return { overlay, modal, close };
    }

    // ========== 报告中心功能 ==========
    window.ReportCenter = {
        // 渲染报告中心页面
        renderPage(containerId) {
            const container = document.getElementById(containerId);
            if (!container) return;
            
            container.innerHTML = `
                <div class="report-center">
                    <div style="margin-bottom: 20px;">
                        <h2 style="margin: 0 0 12px 0;">📊 报告中心</h2>
                        <p style="color: #666; margin: 0;">生成和管理舆情报告，支持日报、周报、月报和自定义报告</p>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 24px;">
                        <div class="report-card" style="padding: 20px; background: var(--zb-stone-0,#FFFFFF); border:1px solid var(--zb-stone-200,#E7E5E4); border-radius: 12px; cursor: pointer; transition: border-color .18s, box-shadow .18s;" onclick="ReportCenter.generateReport('daily')" onmouseover="this.style.borderColor='var(--zb-stone-400,#A8A29E)';this.style.boxShadow='0 1px 4px rgba(0,0,0,.05)'" onmouseout="this.style.borderColor='var(--zb-stone-200,#E7E5E4)';this.style.boxShadow='none'">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;"><span style="width:8px;height:8px;border-radius:50%;background:var(--zb-info,#2563EB);display:inline-block;"></span><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--zb-stone-600,#57534E)"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div>
                            <h3 style="margin: 0 0 4px 0; color: var(--zb-stone-900,#1C1917); font-size: 15px; font-weight: 600;">日报</h3>
                            <p style="margin: 0; color: var(--zb-stone-500,#78716C); font-size: 13px;">每日舆情汇总</p>
                        </div>
                        <div class="report-card" style="padding: 20px; background: var(--zb-stone-0,#FFFFFF); border:1px solid var(--zb-stone-200,#E7E5E4); border-radius: 12px; cursor: pointer; transition: border-color .18s, box-shadow .18s;" onclick="ReportCenter.generateReport('weekly')" onmouseover="this.style.borderColor='var(--zb-stone-400,#A8A29E)';this.style.boxShadow='0 1px 4px rgba(0,0,0,.05)'" onmouseout="this.style.borderColor='var(--zb-stone-200,#E7E5E4)';this.style.boxShadow='none'">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;"><span style="width:8px;height:8px;border-radius:50%;background:var(--zb-attention,#D97706);display:inline-block;"></span><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--zb-stone-600,#57534E)"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="14" x2="16" y2="14"/><line x1="8" y1="17" x2="13" y2="17"/></svg></div>
                            <h3 style="margin: 0 0 4px 0; color: var(--zb-stone-900,#1C1917); font-size: 15px; font-weight: 600;">周报</h3>
                            <p style="margin: 0; color: var(--zb-stone-500,#78716C); font-size: 13px;">每周舆情分析</p>
                        </div>
                        <div class="report-card" style="padding: 20px; background: var(--zb-stone-0,#FFFFFF); border:1px solid var(--zb-stone-200,#E7E5E4); border-radius: 12px; cursor: pointer; transition: border-color .18s, box-shadow .18s;" onclick="ReportCenter.generateReport('monthly')" onmouseover="this.style.borderColor='var(--zb-stone-400,#A8A29E)';this.style.boxShadow='0 1px 4px rgba(0,0,0,.05)'" onmouseout="this.style.borderColor='var(--zb-stone-200,#E7E5E4)';this.style.boxShadow='none'">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;"><span style="width:8px;height:8px;border-radius:50%;background:var(--zb-success,#16A34A);display:inline-block;"></span><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--zb-stone-600,#57534E)"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div>
                            <h3 style="margin: 0 0 4px 0; color: var(--zb-stone-900,#1C1917); font-size: 15px; font-weight: 600;">月报</h3>
                            <p style="margin: 0; color: var(--zb-stone-500,#78716C); font-size: 13px;">月度趋势分析</p>
                        </div>
                        <div class="report-card" style="padding: 20px; background: var(--zb-stone-0,#FFFFFF); border:1px solid var(--zb-stone-200,#E7E5E4); border-radius: 12px; cursor: pointer; transition: border-color .18s, box-shadow .18s;" onclick="ReportCenter.generateReport('custom')" onmouseover="this.style.borderColor='var(--zb-stone-400,#A8A29E)';this.style.boxShadow='0 1px 4px rgba(0,0,0,.05)'" onmouseout="this.style.borderColor='var(--zb-stone-200,#E7E5E4)';this.style.boxShadow='none'">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;"><span style="width:8px;height:8px;border-radius:50%;background:var(--zb-stone-400,#A8A29E);display:inline-block;"></span><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--zb-stone-600,#57534E)"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></div>
                            <h3 style="margin: 0 0 4px 0; color: var(--zb-stone-900,#1C1917); font-size: 15px; font-weight: 600;">自定义</h3>
                            <p style="margin: 0; color: var(--zb-stone-500,#78716C); font-size: 13px;">自定义时间范围</p>
                        </div>
                    </div>
                    
                    <div style="background: #ffffff; border:1px solid #eef0f4; padding: 16px; border-radius: 12px; margin-bottom:24px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
                            <div>
                                <h4 style="margin:0 0 2px 0;">📑 报告预览</h4>
                                <p style="margin:0;color:#888;font-size:12px;">默认展示最近一个自然周（周一至周日），可切换周期与基准日期，非滚动近 7 天</p>
                            </div>
                            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                                <select id="rpPeriod" onchange="loadReportPreview()" style="padding:6px 10px;border-radius:8px;border:1px solid #d8dde8;background:#fff">
                                    <option value="daily">日报（当日）</option>
                                    <option value="weekly" selected>自然周报（周一至周日）</option>
                                    <option value="monthly">自然月报</option>
                                    <option value="yearly">自然年报</option>
                                </select>
                                <input type="date" id="rpDate" onchange="loadReportPreview()" style="padding:6px 10px;border-radius:8px;border:1px solid #d8dde8"/>
                                <button onclick="loadReportPreview()" style="padding:6px 12px;border:1px solid #E7E5E4;border-radius:8px;background:#F5F5F4;color:#292524;cursor:pointer">↻ 刷新</button>
                            </div>
                        </div>
                        <div id="reportPreviewBody" style="font-size:13px">正在加载报告预览…</div>
                    </div>

                    <div style="background: #f9f9f9; padding: 16px; border-radius: 8px;">
                        <h4 style="margin: 0 0 12px 0;">📋 历史报告</h4>
                        <div id="report-history-list" style="font-size: 14px; color: #666;">
                            加载中...
                        </div>
                    </div>
                </div>
            `;
            
            this.loadHistory();
            // 默认加载最近一个自然周的报告预览
            if (typeof window.loadReportPreview === 'function') { setTimeout(()=>window.loadReportPreview(), 60); }
        },
        
        // 生成报告
        async generateReport(type) {
            const content = `
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500;">报告类型</label>
                    <select id="report-type-select" style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;">
                        <option value="daily" ${type === 'daily' ? 'selected' : ''}>日报</option>
                        <option value="weekly" ${type === 'weekly' ? 'selected' : ''}>周报</option>
                        <option value="monthly" ${type === 'monthly' ? 'selected' : ''}>月报</option>
                        <option value="yearly" ${type === 'yearly' ? 'selected' : ''}>年报</option>
                        <option value="custom" ${type === 'custom' ? 'selected' : ''}>自定义报告</option>
                    </select>
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500;">导出格式</label>
                    <div style="display: flex; gap: 12px;">
                        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                            <input type="radio" name="report-format" value="word" checked />
                            <span>📄 Word文档</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                            <input type="radio" name="report-format" value="excel" />
                            <span>📊 Excel表格</span>
                        </label>
                    </div>
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 500;">时间范围</label>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <input type="date" id="report-start" style="flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;" />
                        <span style="color: #999;">至</span>
                        <input type="date" id="report-end" style="flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;" />
                    </div>
                </div>
                <div style="margin-top: 24px; display: flex; gap: 10px; justify-content: flex-end;">
                    <button id="report-cancel-btn" style="padding: 10px 20px; background: #f0f0f0; color: #333; border: none; border-radius: 8px; cursor: pointer;">取消</button>
                    <button id="report-generate-btn" style="padding: 10px 20px; background: #1C1917; color: #fff; border: none; border-radius: 8px; cursor: pointer;">生成报告</button>
                </div>
            `;
            
            const { modal, close } = createModal('生成报告', content, '550px');
            
            // 默认日期：按报告类型取自然周期（自然周=本周一至今，而非滚动最近7天），可用本地时区
            const fmtDate = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
            const startEl = document.getElementById('report-start');
            const endEl = document.getElementById('report-end');
            function setNaturalRange(tp) {
                const now = new Date();
                let s = new Date(now);
                if (tp === 'weekly') { const wd = (now.getDay() + 6) % 7; s = new Date(now.getTime() - wd * 86400000); } // 本周一
                else if (tp === 'monthly') { s = new Date(now.getFullYear(), now.getMonth(), 1); }
                else if (tp === 'yearly') { s = new Date(now.getFullYear(), 0, 1); }
                else if (tp === 'custom') { s = new Date(now.getTime() - 7 * 86400000); }
                startEl.value = fmtDate(s);
                endEl.value = fmtDate(now);
            }
            const typeSel = document.getElementById('report-type-select');
            setNaturalRange(typeSel.value);
            typeSel.onchange = () => setNaturalRange(typeSel.value);
            
            document.getElementById('report-cancel-btn').onclick = close;
            
            document.getElementById('report-generate-btn').onclick = async () => {
                const reportType = document.getElementById('report-type-select').value;
                const format = document.querySelector('input[name="report-format"]:checked').value;
                const start = document.getElementById('report-start').value;
                const end = document.getElementById('report-end').value;
                
                const btn = document.getElementById('report-generate-btn');
                btn.textContent = '生成中...';
                btn.disabled = true;
                
                try {
                    const result = await api(`/api/export/generate?type=${reportType}&format=${format}&start=${start}&end=${end}`, {
                        method: 'POST'
                    });
                    toast('报告生成成功', 'success');
                    if (result.download_url) {
                        window.open(result.download_url, '_blank');
                    }
                    close();
                    this.loadHistory();
                } catch (error) {
                    toast('报告生成失败: ' + error.message, 'error');
                } finally {
                    btn.textContent = '生成报告';
                    btn.disabled = false;
                }
            };
        },
        
        // 加载历史报告
        async loadHistory() {
            const listEl = document.getElementById('report-history-list');
            if (!listEl) return;
            
            try {
                const result = await api('/api/reports?limit=10');
                const reports = result.reports || [];
                
                if (reports.length === 0) {
                    listEl.innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">暂无历史报告</div>';
                    return;
                }
                
                listEl.innerHTML = reports.map(r => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: white; border-radius: 6px; margin-bottom: 8px;">
                        <div>
                            <strong>${r.title || r.type + '报告'}</strong>
                            <span style="color: #999; margin-left: 12px; font-size: 12px;">${r.created_at || ''}</span>
                        </div>
                        <button style="padding: 4px 12px; background: #1C1917; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;" onclick="ReportCenter.downloadReport('${r.id}')">下载</button>
                    </div>
                `).join('');
            } catch (error) {
                listEl.innerHTML = `<div style="color: #ff3b30;">加载失败: ${error.message}</div>`;
            }
        },
        
        // 下载报告
        async downloadReport(id) {
            try {
                const result = await api(`/api/reports/${id}/download`);
                if (result.download_url) {
                    window.open(result.download_url, '_blank');
                }
            } catch (error) {
                toast('下载失败: ' + error.message, 'error');
            }
        }
    };

    // ========== 品牌业态功能 ==========
    window.BrandIndustry = {
        // 渲染品牌业态页面
        renderPage(containerId) {
            const container = document.getElementById(containerId);
            if (!container) return;
            
            container.innerHTML = `
                <div class="brand-industry">
                    <div style="margin-bottom: 20px;">
                        <h2 style="margin: 0 0 12px 0;">🏢 品牌业态监测</h2>
                        <p style="color: #666; margin: 0;">监测场内品牌动态和业态分布</p>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
                        <div style="padding: 16px; background: #F5F5F4; border-radius: 8px; border-left: 4px solid #78716C;">
                            <div style="font-size: 24px; font-weight: bold; color: #1C1917;" id="brand-total">--</div>
                            <div style="color: #666; font-size: 13px;">品牌总数</div>
                        </div>
                        <div style="padding: 16px; background: #fff0f0; border-radius: 8px; border-left: 4px solid #ff3b30;">
                            <div style="font-size: 24px; font-weight: bold; color: #ff3b30;" id="brand-negative">--</div>
                            <div style="color: #666; font-size: 13px;">负面舆情品牌</div>
                        </div>
                        <div style="padding: 16px; background: #f0fff0; border-radius: 8px; border-left: 4px solid #34c759;">
                            <div style="font-size: 24px; font-weight: bold; color: #34c759;" id="brand-positive">--</div>
                            <div style="color: #666; font-size: 13px;">正面舆情品牌</div>
                        </div>
                        <div style="padding: 16px; background: #fff8f0; border-radius: 8px; border-left: 4px solid #ff9500;">
                            <div style="font-size: 24px; font-weight: bold; color: #ff9500;" id="brand-categories">--</div>
                            <div style="color: #666; font-size: 13px;">业态分类数</div>
                        </div>
                    </div>
                    
                    <div style="background: #f9f9f9; padding: 16px; border-radius: 8px;">
                        <h4 style="margin: 0 0 12px 0;">📋 品牌列表</h4>
                        <div id="brand-list" style="font-size: 14px; color: #666;">
                            加载中...
                        </div>
                    </div>
                </div>
            `;
            
            this.loadData();
        },
        
        // 加载品牌数据
        async loadData() {
            try {
                const result = await api('/api/brand-industry/stats');
                // API返回industries数组，计算统计数据
                const industries = result.industries || [];
                const totalBrands = industries.reduce((s, i) => s + (i.cnt || 0), 0);
                document.getElementById('brand-total').textContent = totalBrands || '--';
                document.getElementById('brand-negative').textContent = result.negative_brands || '--';
                document.getElementById('brand-positive').textContent = result.positive_brands || '--';
                document.getElementById('brand-categories').textContent = industries.length || '--';
                
                // 加载品牌列表
                const brandsResult = await api('/api/brand-industry/brands?limit=500');
                const allBrands = brandsResult.brands || [];
                this._allBrands = allBrands;
                const listEl = document.getElementById('brand-list');

                if (allBrands.length === 0) {
                    listEl.innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">暂无品牌数据</div>';
                    return;
                }
                // 业态筛选下钻条（全部 + 各业态），点击只看该业态品牌
                const indOf = b => b.industry || b.category || '未分类';
                const indCn = s => (s || '未分类').split(' ')[0];  // 业态只取中文名（去掉英文）
                // 一级下钻：8大业态卡片，点击弹出该业态概览 + 品牌网格（二级再点品牌进详情）
                const indAgg = {};
                allBrands.forEach(b => {
                    const k = indOf(b);
                    const a = indAgg[k] || (indAgg[k] = {cnt:0, withNote:0, neg:0, engage:0});
                    a.cnt++;
                    if((b.note_count||0)>0) a.withNote++;
                    if((b.negative_count||0)>0) a.neg++;
                    a.engage += (b.total_engagement||0);
                });
                const indCards = `<div id="brand-industry-cards" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin-bottom:14px">`
                    + industries.map(i => {
                        const k=i.industry, a=indAgg[k]||{cnt:i.cnt||0,withNote:0,neg:0,engage:0};
                        const danger=a.neg>0;
                        return `<div data-ind-card="${k.replace(/"/g,'&quot;')}" style="padding:12px 14px;background:#fff;border:1px solid ${danger?'#ffd4d2':'#e8ebf0'};border-left:4px solid ${danger?'#ff3b30':'#78716C'};border-radius:10px;cursor:pointer;transition:.15s" onmouseover="this.style.boxShadow='0 4px 14px rgba(0,0,0,.08)'" onmouseout="this.style.boxShadow=''">
                            <div style="font-weight:600;font-size:14px">${indCn(k)}</div>
                            <div style="font-size:12px;color:#888;margin-top:4px">${a.cnt} 个品牌 · ${a.withNote} 个有舆情${danger?` · <b style="color:#ff3b30">${a.neg} 负面</b>`:''}</div>
                        </div>`;
                    }).join('') + `</div>`;
                const chips = ['全部'].concat(industries.map(i => i.industry));
                const chipBar = `<div id="brand-filter-bar" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">`
                    + chips.map((c,idx)=>{const n = c==='全部'?allBrands.length:(industries.find(i=>i.industry===c)?.cnt||0);
                        return `<button data-ind="${c.replace(/"/g,'&quot;')}" class="brand-filter-chip ${idx===0?'active':''}" style="padding:5px 12px;font-size:12px;border-radius:16px;border:1px solid #d8dde8;background:${idx===0?'#1C1917':'#fff'};color:${idx===0?'#fff':'#333'};cursor:pointer">${c==='全部'?'全部品牌':indCn(c)} ${n}</button>`;}).join('')
                    + `</div>`;
                listEl.innerHTML = indCards + chipBar + `<div id="brand-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px;"></div>`;
                // 业态卡片点击 → 一级下钻弹窗
                listEl.querySelectorAll('[data-ind-card]').forEach(card=>{
                    card.onclick=()=>this.viewIndustry(card.dataset.indCard);
                });
                const grid = document.getElementById('brand-grid');
                const renderGrid = (filter) => {
                    const list = filter==='全部'?allBrands:allBrands.filter(b=>indOf(b)===filter);
                    if(!list.length){grid.innerHTML='<div style="color:#999;padding:14px 0;grid-column:1/-1">该业态下暂无匹配品牌</div>';return;}
                    grid.innerHTML = list.map(b => {
                        const nm = b.brand_name_cn || b.brand_name || '未命名';
                        return `<div style="padding: 8px 12px; background: white; border-radius: 6px; border: 1px solid #eee; cursor: pointer;" onclick="BrandIndustry.viewBrand('${nm.replace(/'/g,'')}')">
                                <div style="font-weight: 500; font-size: 13px;">${nm}</div>
                                <div style="font-size: 11px; color: #999;">${indOf(b)}</div>
                            </div>`;
                    }).join('');
                };
                listEl.querySelectorAll('.brand-filter-chip').forEach(btn=>{
                    btn.onclick=()=>{listEl.querySelectorAll('.brand-filter-chip').forEach(x=>{x.style.background='#fff';x.style.color='#333';x.classList.remove('active')});btn.style.background='#1C1917';btn.style.color='#fff';btn.classList.add('active');renderGrid(btn.dataset.ind);};
                });
                renderGrid('全部');
            } catch (error) {
                document.getElementById('brand-list').innerHTML = `<div style="color: #ff3b30;">加载失败: ${error.message}</div>`;
            }
        },
        
        // 一级下钻：查看某业态概览及其全部品牌（点击品牌再进二级详情）
        viewIndustry(industry) {
            try {
                const all = this._allBrands || [];
                const list = all.filter(b => (b.industry || b.category || '未分类') === industry);
                const indCn = (industry || '未分类').split(' ')[0];
                const withNote = list.filter(b => (b.note_count || 0) > 0);
                const negList = list.filter(b => (b.negative_count || 0) > 0);
                const totalNotes = list.reduce((s, b) => s + (b.note_count || 0), 0);
                // 品牌按是否有负面、笔记量排序
                list.sort((a, b) => (b.negative_count || 0) - (a.negative_count || 0) || (b.note_count || 0) - (a.note_count || 0));
                const content = `
                    <div style="margin-bottom:14px">
                        <h3 style="margin:0 0 6px 0">${indCn}</h3>
                        <p style="color:#666;margin:0;font-size:13px">共 ${list.length} 个品牌 · ${withNote.length} 个有相关舆情 · 累计 ${totalNotes} 条笔记${negList.length?` · <b style="color:#ff3b30">${negList.length} 个品牌有负面</b>`:' · 暂无负面品牌'}</p>
                    </div>
                    <input id="indBrandSearch" placeholder="搜索该业态品牌…" style="width:100%;box-sizing:border-box;padding:8px 12px;border:1px solid #ddd;border-radius:8px;margin-bottom:10px"/>
                    <div id="indBrandGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;max-height:46vh;overflow-y:auto">
                        ${list.map(b => {
                            const nm = b.brand_name_cn || b.brand_name || '未命名';
                            const neg = (b.negative_count || 0) > 0;
                            return `<div data-bn="${nm.replace(/"/g,'&quot;')}" class="ind-brand-cell" style="padding:9px 11px;background:${neg?'#fff5f5':'#fafafa'};border:1px solid ${neg?'#ffd4d2':'#eee'};border-radius:8px;cursor:pointer">
                                <div style="font-weight:500;font-size:13px">${nm}</div>
                                <div style="font-size:11px;color:${neg?'#ff3b30':'#999'};margin-top:2px">${b.note_count||0} 条${neg?` · ${b.negative_count} 负面`:''}${b.floor?(' · '+b.floor):''}</div>
                            </div>`;
                        }).join('') || '<div style="color:#999;grid-column:1/-1;padding:16px 0;text-align:center">该业态暂无品牌</div>'}
                    </div>
                    <p style="color:#aaa;font-size:12px;margin:10px 0 0">点击任意品牌查看其舆情统计与相关笔记</p>
                `;
                const m = createModal(indCn + ' · 业态详情', content, '720px');
                // 品牌点击 → 关闭业态弹窗、打开品牌二级详情
                m.modal.querySelectorAll('.ind-brand-cell').forEach(cell => {
                    cell.onclick = () => { m.close(); this.viewBrand(cell.dataset.bn); };
                });
                // 业态内品牌搜索过滤
                const search = m.modal.querySelector('#indBrandSearch');
                if (search) search.oninput = e => {
                    const kw = e.target.value.trim().toLowerCase();
                    m.modal.querySelectorAll('.ind-brand-cell').forEach(cell => {
                        cell.style.display = cell.dataset.bn.toLowerCase().includes(kw) ? '' : 'none';
                    });
                };
            } catch (error) {
                toast('加载业态详情失败: ' + error.message, 'error');
            }
        },

        // 查看品牌详情
        async viewBrand(name) {
            try {
                const result = await api(`/api/brand-industry/brands/${encodeURIComponent(name)}`);
                const brand = result.brand || {};
                const sentMap = {positive:['正面','#34c759'],negative:['负面','#ff3b30'],neutral:['中性','#8e8e93']};
                const sentTxt = s => (sentMap[s]||[s||'未知','#999'])[0];
                const sentColor = s => (sentMap[s]||['','#999'])[1];
                const recent = brand.recent_notes || [];

                const content = `
                    <div style="margin-bottom: 16px;">
                        <h3 style="margin: 0 0 8px 0;">${brand.name || name}</h3>
                        <p style="color: #666; margin: 0;">${brand.category || '未分类'}${brand.floor ? ' | ' + brand.floor : ''}${brand.shop_number ? ' | ' + brand.shop_number : ''}</p>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <h4 style="margin: 0 0 8px 0;">舆情统计 <span style="font-size:11px;color:#999;font-weight:normal;">按标题/正文实时匹配该品牌笔记</span></h4>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                            <div style="padding: 12px; background: #f0f8ff; border-radius: 6px; text-align: center;">
                                <div style="font-size: 20px; font-weight: bold; color: #1C1917;">${brand.total_notes || 0}</div>
                                <div style="font-size: 12px; color: #666;">总笔记</div>
                            </div>
                            <div style="padding: 12px; background: #f0fff0; border-radius: 6px; text-align: center;">
                                <div style="font-size: 20px; font-weight: bold; color: #34c759;">${brand.positive || 0}</div>
                                <div style="font-size: 12px; color: #666;">正面</div>
                            </div>
                            <div style="padding: 12px; background: #fafafa; border-radius: 6px; text-align: center;">
                                <div style="font-size: 20px; font-weight: bold; color: #8e8e93;">${brand.neutral || 0}</div>
                                <div style="font-size: 12px; color: #666;">中性</div>
                            </div>
                            <div style="padding: 12px; background: #fff0f0; border-radius: 6px; text-align: center;">
                                <div style="font-size: 20px; font-weight: bold; color: #ff3b30;">${brand.negative || 0}</div>
                                <div style="font-size: 12px; color: #666;">负面</div>
                            </div>
                        </div>
                    </div>
                    <div>
                        <h4 style="margin: 0 0 8px 0;">相关笔记（最近${recent.length}条）</h4>
                        <div style="font-size: 13px; color: #666; max-height:300px; overflow-y:auto;">
                            ${recent.map(n => `
                                <div style="padding: 8px; background: #f9f9f9; border-radius: 4px; margin-bottom: 6px; ${n.url?'cursor:pointer;':''}" ${n.url?`onclick="window.open('${n.url}','_blank')"`:''}>
                                    <div style="font-weight: 500; line-height:1.4;">${n.title || '（无标题）'}</div>
                                    <div style="font-size: 11px; color: #999; margin-top:3px;">${n.author_nickname||''} ${n.publish_date || ''} · <b style="color:${sentColor(n.sentiment)}">${sentTxt(n.sentiment)}</b>${n.risk_level?(' · '+n.risk_level):''}${n.likes?(' · ♥'+n.likes):''}</div>
                                </div>
                            `).join('') || '<div style="color: #999; padding:12px 0;">暂未检索到明确提及该品牌的笔记（笔记多以“广州太古汇”整体为主）</div>'}
                        </div>
                    </div>
                `;

                createModal('品牌详情', content, '640px');
            } catch (error) {
                toast('加载品牌详情失败: ' + error.message, 'error');
            }
        }
    };

    // ========== 案例库功能 ==========
    // 案例分类 key → 中文（数据里存的是英文 key，展示统一中文化）
    const CASE_CAT_MAP = {
        product: '产品质量', service: '服务投诉', safety: '安全事件', pr: '公关危机',
        service_attitude: '服务态度', food_safety: '食品安全', activity_safety: '活动安全',
        content_audit: '内容审核', price_rule: '价格规范', false_info: '不实信息',
        benchmark: '标杆应对', negative_example: '反面教材',
        critical: '🔴重大', medium: '🟡关注', low: '🟢一般'
    };
    const caseCatLabel = k => CASE_CAT_MAP[k] || k || '未分类';
    window.CaseLibrary = {
        // 渲染案例库页面
        renderPage(containerId) {
            const container = document.getElementById(containerId);
            if (!container) return;
            
            container.innerHTML = `
                <div class="case-library">
                    <div style="margin-bottom: 20px;">
                        <h2 style="margin: 0 0 12px 0;">📚 案例库</h2>
                        <p style="color: #666; margin: 0;">全网舆情案例和公关话术模板</p>
                    </div>
                    
                    <div style="margin-bottom: 16px; display: flex; gap: 10px;">
                        <input type="text" id="case-search" placeholder="搜索案例..." style="flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;" />
                        <select id="case-category" style="padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;">
                            <option value="">全部分类</option>
                            <option value="product">产品质量</option>
                            <option value="service_attitude">服务态度</option>
                            <option value="food_safety">食品安全</option>
                            <option value="activity_safety">活动安全</option>
                            <option value="content_audit">内容审核</option>
                            <option value="price_rule">价格规范</option>
                            <option value="false_info">不实信息</option>
                            <option value="safety">安全事件</option>
                            <option value="pr">公关危机</option>
                            <option value="benchmark">标杆应对</option>
                            <option value="negative_example">反面教材</option>
                        </select>
                    </div>
                    
                    <div id="case-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
                        加载中...
                    </div>
                </div>
            `;
            
            this.loadCases();
            
            document.getElementById('case-search').oninput = () => this.loadCases();
            document.getElementById('case-category').onchange = () => this.loadCases();
        },
        
        // 加载案例
        async loadCases() {
            const search = document.getElementById('case-search').value;
            const category = document.getElementById('case-category').value;
            const listEl = document.getElementById('case-list');
            
            try {
                const result = await api(`/api/pr/cases?keyword=${encodeURIComponent(search)}&category=${category}&limit=20`);
                const cases = result.cases || [];
                
                if (cases.length === 0) {
                    listEl.innerHTML = '<div style="grid-column: 1/-1; color: #999; text-align: center; padding: 40px;">暂无案例</div>';
                    return;
                }
                
                listEl.innerHTML = cases.map(c => `
                    <div style="padding: 16px; background: white; border: 1px solid #eee; border-radius: 8px; cursor: pointer; transition: box-shadow 0.2s;" onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'" onmouseout="this.style.boxShadow='none'" onclick="CaseLibrary.viewCase('${c.id}')">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <span style="padding: 2px 8px; background: #f0f0f0; border-radius: 4px; font-size: 11px; color: #666;">${caseCatLabel(c.category || c.scene || c.level)}</span>
                            <span style="font-size: 11px; color: #999;">${c.date || ''}</span>
                        </div>
                        <h4 style="margin: 0 0 8px 0; font-size: 15px;">${c.name || c.title || '未命名案例'}</h4>
                        <p style="margin: 0; color: #666; font-size: 13px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${c.event || c.summary || c.content || ''}</p>
                    </div>
                `).join('');
            } catch (error) {
                listEl.innerHTML = `<div style="grid-column: 1/-1; color: #ff3b30; text-align: center; padding: 40px;">加载失败: ${error.message}</div>`;
            }
        },
        
        // 查看案例详情
        async viewCase(id) {
            try {
                const result = await api(`/api/pr/cases/${id}`);
                const c0 = result.case || {};
                // 同时兼容 pr_case_library(name/event/spread/response/effect/insight)
                // 与 case_library(title/category/summary/spread_path/official_response/insights[])
                const title = c0.name || c0.title || '未命名案例';
                const scene = caseCatLabel(c0.category || c0.scene || c0.level);
                const eventText = c0.event || c0.summary || c0.content || '';
                const spread = c0.spread || c0.spread_path || '';
                const resp = c0.response || c0.official_response || '';
                const effect = c0.effect || '';
                let insight = c0.insight || c0.lesson || '';
                if (Array.isArray(c0.insights)) insight = c0.insights.join('\n');
                const tpl = c0.template || '';
                const block = (icon, head, body, bg, bd) => body ? `
                    <div style="margin-bottom: 16px;">
                        <h4 style="margin: 0 0 8px 0;">${icon} ${head}</h4>
                        <div style="padding: 12px; background: ${bg}; border-radius: 6px; border-left: 3px solid ${bd};">
                            <p style="margin: 0; line-height: 1.6; white-space: pre-wrap;">${body}</p>
                        </div>
                    </div>` : '';

                const content = `
                    <div style="margin-bottom: 16px;">
                        <span style="padding: 4px 10px; background: #f0f0f0; border-radius: 4px; font-size: 12px; color: #666;">${scene}</span>
                        <span style="margin-left: 12px; font-size: 12px; color: #999;">${c0.date || ''}</span>
                    </div>
                    <h3 style="margin: 0 0 12px 0;">${title}</h3>
                    ${block('📋', '事件概述', eventText || '暂无概述', '#f7f7f7', '#999')}
                    ${block('🌐', '传播路径', spread, '#F5F5F4', '#57534E')}
                    ${block('💬', '公关回应', resp, '#F5F5F4', '#57534E')}
                    ${block('📈', '处置效果', effect, '#fafaff', '#5856d6')}
                    ${block('🎯', '经验教训', insight, '#fffdf5', '#ff9500')}
                    ${block('📝', '话术模板', tpl, '#f0fff0', '#34c759')}
                `;

                createModal('案例详情', content, '700px');
            } catch (error) {
                toast('加载案例详情失败: ' + error.message, 'error');
            }
        }
    };

    // ========== 负面审核功能 ==========
    window.NegativeReview = {
        // 渲染负面审核页面
        renderPage(containerId) {
            const container = document.getElementById(containerId);
            if (!container) return;
            
            container.innerHTML = `
                <div class="negative-review">
                    <div style="margin-bottom: 20px;">
                        <h2 style="margin: 0 0 12px 0;">⚠️ 负面审核</h2>
                        <p style="color: #666; margin: 0;">审核和确认负面舆情，确保报告准确性</p>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px;">
                        <div style="padding: 16px; background: #fff0f0; border-radius: 8px; border-left: 4px solid #ff3b30;">
                            <div style="font-size: 24px; font-weight: bold; color: #ff3b30;" id="pending-count">--</div>
                            <div style="color: #666; font-size: 13px;">待审核</div>
                        </div>
                        <div style="padding: 16px; background: #f0fff0; border-radius: 8px; border-left: 4px solid #34c759;">
                            <div style="font-size: 24px; font-weight: bold; color: #34c759;" id="confirmed-count">--</div>
                            <div style="color: #666; font-size: 13px;">已确认</div>
                        </div>
                        <div style="padding: 16px; background: #f0f0f0; border-radius: 8px; border-left: 4px solid #999;">
                            <div style="font-size: 24px; font-weight: bold; color: #999;" id="rejected-count">--</div>
                            <div style="color: #666; font-size: 13px;">已驳回</div>
                        </div>
                        <div style="padding: 16px; background: #fff8f0; border-radius: 8px; border-left: 4px solid #ff9500;">
                            <div style="font-size: 24px; font-weight: bold; color: #ff9500;" id="high-risk-count">--</div>
                            <div style="color: #666; font-size: 13px;">高风险</div>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 16px; display: flex; gap: 10px;">
                        <select id="review-filter" style="padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;">
                            <option value="pending">待审核</option>
                            <option value="confirmed">已确认</option>
                            <option value="rejected">已驳回</option>
                            <option value="">全部</option>
                        </select>
                        <button id="refresh-review" style="padding: 8px 16px; background: #F5F5F4; color: #292524; border: 1px solid #E7E5E4; border-radius: 6px; cursor: pointer;">刷新</button>
                    </div>
                    
                    <div id="review-list" style="background: #f9f9f9; padding: 16px; border-radius: 8px;">
                        加载中...
                    </div>
                </div>
            `;
            
            this.loadStats();
            this.loadList();
            
            document.getElementById('review-filter').onchange = () => this.loadList();
            document.getElementById('refresh-review').onclick = () => {
                this.loadStats();
                this.loadList();
            };
        },
        
        // 加载统计
        async loadStats() {
            try {
                const result = await api('/api/negative-review/stats');
                document.getElementById('pending-count').textContent = result.pending != null ? result.pending : '--';
                document.getElementById('confirmed-count').textContent = result.confirmed != null ? result.confirmed : '--';
                document.getElementById('rejected-count').textContent = result.rejected != null ? result.rejected : '--';
                document.getElementById('high-risk-count').textContent = result.high_risk != null ? result.high_risk : '--';
            } catch (error) {
                console.error('加载统计失败:', error);
            }
        },
        
        // 加载列表
        async loadList() {
            const filter = document.getElementById('review-filter').value;
            const listEl = document.getElementById('review-list');
            
            try {
                const result = await api(`/api/negative/pending?status=${filter}&page=1&per_page=20`);
                const items = result.items || result.notes || [];
                
                if (items.length === 0) {
                    listEl.innerHTML = '<div style="color: #999; text-align: center; padding: 40px;">暂无数据</div>';
                    return;
                }
                
                listEl.innerHTML = items.map(item => {
                    const nc = item.negative_confirmed;
                    const st = nc === 1 ? 'confirmed' : nc === 2 ? 'rejected' : 'pending';
                    const stText = st === 'pending' ? '待审核' : st === 'confirmed' ? '已确认' : '已驳回';
                    const stBg = st === 'pending' ? '#fff8f0' : st === 'confirmed' ? '#f0fff0' : '#f0f0f0';
                    const stColor = st === 'pending' ? '#ff9500' : st === 'confirmed' ? '#34c759' : '#999';
                    const itemId = item.note_id || item.id;
                    return `
                    <div style="padding: 16px; background: white; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid ${item.risk_level === 'high' ? '#ff3b30' : item.risk_level === 'medium' ? '#ff9500' : '#34c759'};">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <div>
                                <h4 style="margin: 0 0 4px 0; font-size: 15px;">${item.title}</h4>
                                <div style="font-size: 12px; color: #999;">${item.author_nickname || '匿名'} | ${item.publish_date || ''} | ${item.sentiment || ''}</div>
                            </div>
                            <span style="padding: 2px 8px; background: ${stBg}; color: ${stColor}; border-radius: 4px; font-size: 11px;">${stText}</span>
                        </div>
                        <p style="margin: 0 0 12px 0; color: #666; font-size: 13px; line-height: 1.5;">${item.summary || item.content || '暂无摘要'}</p>
                        <div style="display: flex; gap: 8px;">
                            <button style="padding: 6px 14px; background: #34c759; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;" onclick="NegativeReview.confirmItem('${itemId}')">✓ 确认负面</button>
                            <button style="padding: 6px 14px; background: #ff9500; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;" onclick="NegativeReview.viewDetail('${itemId}')">👁 查看详情</button>
                            <button style="padding: 6px 14px; background: #999; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;" onclick="NegativeReview.rejectItem('${itemId}')">✗ 驳回</button>
                        </div>
                    </div>
                `}).join('');
            } catch (error) {
                listEl.innerHTML = `<div style="color: #ff3b30; text-align: center; padding: 20px;">加载失败: ${error.message}</div>`;
            }
        },
        
        // 确认负面
        async confirmItem(id) {
            try {
                await api(`/api/negative-review/${id}/confirm`, { method: 'POST' });
                toast('已确认负面', 'success');
                this.loadStats();
                this.loadList();
            } catch (error) {
                toast('确认失败: ' + error.message, 'error');
            }
        },
        
        // 驳回
        async rejectItem(id) {
            try {
                await api(`/api/negative-review/${id}/reject`, { method: 'POST' });
                toast('已驳回', 'success');
                this.loadStats();
                this.loadList();
            } catch (error) {
                toast('驳回失败: ' + error.message, 'error');
            }
        },
        
        // 查看详情
        async viewDetail(id) {
            try {
                const result = await api(`/api/notes/${id}`);
                const note = result.note || {};
                
                const content = `
                    <div style="margin-bottom: 16px;">
                        <h3 style="margin: 0 0 8px 0;">${note.title || '无标题'}</h3>
                        <div style="font-size: 12px; color: #999;">${note.author_nickname || '匿名'} | ${note.publish_date || ''} | ${note.sentiment || ''} | 风险: ${note.risk_level || ''}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <h4 style="margin: 0 0 8px 0;">📝 内容</h4>
                        <p style="color: #333; line-height: 1.6; margin: 0; white-space: pre-wrap;">${note.content || note.summary || '暂无内容'}</p>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <h4 style="margin: 0 0 8px 0;">📊 互动数据</h4>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                            <div style="text-align: center; padding: 8px; background: #f9f9f9; border-radius: 6px;">
                                <div style="font-size: 18px; font-weight: bold;">${note.likes || 0}</div>
                                <div style="font-size: 11px; color: #999;">点赞</div>
                            </div>
                            <div style="text-align: center; padding: 8px; background: #f9f9f9; border-radius: 6px;">
                                <div style="font-size: 18px; font-weight: bold;">${note.comments || 0}</div>
                                <div style="font-size: 11px; color: #999;">评论</div>
                            </div>
                            <div style="text-align: center; padding: 8px; background: #f9f9f9; border-radius: 6px;">
                                <div style="font-size: 18px; font-weight: bold;">${note.collects || 0}</div>
                                <div style="font-size: 11px; color: #999;">收藏</div>
                            </div>
                            <div style="text-align: center; padding: 8px; background: #f9f9f9; border-radius: 6px;">
                                <div style="font-size: 18px; font-weight: bold;">${note.shares || 0}</div>
                                <div style="font-size: 11px; color: #999;">分享</div>
                            </div>
                        </div>
                    </div>
                    ${note.url ? `<div><a href="${note.url}" target="_blank" style="color: #44403C; text-decoration: underline; text-underline-offset: 2px;">🔗 查看原文</a></div>` : ''}
                `;
                
                createModal('笔记详情', content, '700px');
            } catch (error) {
                toast('加载详情失败: ' + error.message, 'error');
            }
        }
    };

    // ========== 页面路由初始化 ==========
    function initPageRouting() {
        // 检查当前页面路径，渲染对应内容
        const path = window.location.pathname;
        
        if (path === '/reports' || document.getElementById('page-reports')) {
            if (window.ReportCenter && document.getElementById('page-reports')) {
                ReportCenter.renderPage('page-reports');
            }
        }
        
        if (path === '/brands' || document.getElementById('page-brands')) {
            if (window.BrandIndustry && document.getElementById('page-brands')) {
                BrandIndustry.renderPage('page-brands');
            }
        }
        
        if (path === '/cases' || document.getElementById('page-cases')) {
            if (window.CaseLibrary && document.getElementById('page-cases')) {
                CaseLibrary.renderPage('page-cases');
            }
        }
        
        if (path === '/negative' || document.getElementById('page-negative')) {
            if (window.NegativeReview && document.getElementById('page-negative')) {
                NegativeReview.renderPage('page-negative');
            }
        }
    }

    // DOM加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPageRouting);
    } else {
        initPageRouting();
    }

    // 暴露到全局
    window.FrontendEnhancement = {
        ReportCenter,
        BrandIndustry,
        CaseLibrary,
        NegativeReview,
        initPageRouting
    };

})();
