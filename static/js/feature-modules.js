/* ============================================================
 * feature-modules.js — 9项功能模块前端统一接线（ZBC V1.1 架构）
 * 函数驱动：真实 fetch → 数据转换 → 渲染 → 30s轮询 → 断API Error+重试
 * 缺失数据显示 "—" 不用0，禁止Mock/假数据
 * ============================================================ */
(function (global) {
  'use strict';

  /* ---------- 工具函数 ---------- */
  function fetchJSON(url, options) {
    if (typeof LUMENIS !== 'undefined' && LUMENIS.fetch) {
      return LUMENIS.fetch(url, options).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
    }
    return fetch(url, options).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function isMissing(v) {
    return v === null || v === undefined || v === '' || v === 'unknown' || v === 'null' || (typeof v === 'number' && isNaN(v));
  }

  function disp(v) { return isMissing(v) ? '—' : v; }
  function dispNum(v) { return isMissing(v) || isNaN(Number(v)) ? '—' : Number(v); }
  function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
  function trunc(s, n) { s = String(s || ''); return s.length > n ? s.substring(0, n) + '…' : s; }

  function showState(containerId, state, message, retryFn) {
    var c = document.getElementById(containerId);
    if (!c) return;
    var loading = c.querySelector('[data-state="loading"]');
    var empty = c.querySelector('[data-state="empty"]');
    var error = c.querySelector('[data-state="error"]');
    var content = c.querySelector('[data-state="content"]');
    [loading, empty, error, content].forEach(function (el) { if (el) el.style.display = 'none'; });
    var target = { loading: loading, empty: empty, error: error, content: content }[state];
    if (target) target.style.display = '';
    if (state === 'error' && message) {
      var msgEl = c.querySelector('[data-error-msg]');
      if (msgEl) msgEl.textContent = message;
      var retryBtn = c.querySelector('[data-retry]');
      if (retryBtn && retryFn) {
        retryBtn.onclick = function () { retryFn(); };
      }
    }
  }

  /* ============================================================
   * 1. 案例深度分析 (case_deep_analysis) → CTH Events/Evidence
   * API: /api/case-analysis/stats, /api/case-analysis/list, /api/case-analysis/detail
   * ============================================================ */
  var CaseAnalysis = {
    loadStats: function () {
      return fetchJSON('/api/case-analysis/stats');
    },
    loadList: function (page, pageSize) {
      return fetchJSON('/api/case-analysis/list?page=' + (page || 1) + '&page_size=' + (pageSize || 20));
    },
    loadDetail: function (caseId) {
      return fetchJSON('/api/case-analysis/detail?id=' + caseId);
    },
    renderStats: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadStats().then(function (data) {
        var stats = data.stats || data;
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var total = dispNum(stats.total_cases || stats.total);
        var categories = stats.by_category || {};
        var html = '<div class="zbc-kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;">';
        html += '<div class="card-gradient-cth" style="padding:14px;"><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);text-transform:uppercase;letter-spacing:.04em;">案例总数</div><div class="data-integer" style="margin-top:4px;">' + total + '</div></div>';
        for (var cat in categories) {
          if (categories.hasOwnProperty(cat)) {
            html += '<div class="zbc-kpi-card" style="padding:14px;"><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);">' + esc(cat) + '</div><div class="data-integer" style="margin-top:4px;font-size:20px;">' + dispNum(categories[cat]) + '</div></div>';
          }
        }
        html += '</div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderStats(containerId); });
      });
    },
    renderList: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadList(1, 30).then(function (data) {
        var cases = data.cases || data.items || data.list || [];
        if (!cases.length) { showState(containerId, 'empty'); return; }
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var html = '<div class="zbc-scroll-container" style="max-height:400px;"><table class="zbc-table" style="width:100%;border-collapse:collapse;font-size:12px;">';
        html += '<thead><tr style="text-align:left;border-bottom:1px solid var(--l-border,#e8e8e8);"><th style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);font-weight:600;">标题</th><th style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);font-weight:600;">分类</th><th style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);font-weight:600;">风险</th><th style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);font-weight:600;">时间</th></tr></thead><tbody>';
        cases.forEach(function (ca) {
          html += '<tr style="border-bottom:1px solid var(--l-border-light,#f0f0f0);cursor:pointer;" data-case-id="' + (ca.id || '') + '">';
          html += '<td style="padding:8px 10px;color:var(--l-text,#0d0d0d);max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + esc(trunc(ca.title || ca.name || '—', 40)) + '</td>';
          html += '<td style="padding:8px 10px;color:var(--l-text-secondary,#6b7280);">' + esc(ca.category || ca.type || '—') + '</td>';
          var riskColor = { high: '#DC2626', medium: '#D97706', low: '#10B981' }[ca.risk_level || ca.risk] || 'var(--l-text-tertiary,#9ca3af)';
          html += '<td style="padding:8px 10px;"><span style="color:' + riskColor + ';font-weight:600;">' + esc(ca.risk_level || ca.risk || '—') + '</span></td>';
          html += '<td style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);font-size:11px;">' + esc(ca.date || ca.created_at || '—') + '</td>';
          html += '</tr>';
        });
        html += '</tbody></table></div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderList(containerId); });
      });
    }
  };

  /* ============================================================
   * 2. PR案例集成 (pr_case_integration) → ZBMP Content/Competition
   * API: /api/pr/cases/<id>, /api/pr/act-principle, /api/pr/triggers
   * ============================================================ */
  var PRCase = {
    loadCase: function (caseId) {
      return fetchJSON('/api/pr/cases/' + caseId);
    },
    loadActPrinciple: function () {
      return fetchJSON('/api/pr/act-principle');
    },
    loadTriggers: function () {
      return fetchJSON('/api/pr/triggers');
    },
    renderPrinciple: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadActPrinciple().then(function (data) {
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var principle = data.principle || data.act_principle || data;
        var html = '<div class="card-gradient-zbmp" style="padding:18px;">';
        html += '<div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">PR 行动原则</div>';
        if (principle.title) html += '<div style="font-size:16px;font-weight:600;color:var(--l-text,#0d0d0d);margin-bottom:8px;">' + esc(principle.title) + '</div>';
        if (principle.description || principle.content) html += '<div style="font-size:13px;color:var(--l-text-secondary,#6b7280);line-height:1.6;">' + esc(principle.description || principle.content) + '</div>';
        if (principle.steps && Array.isArray(principle.steps)) {
          html += '<div style="margin-top:12px;display:flex;flex-direction:column;gap:6px;">';
          principle.steps.forEach(function (step, i) {
            html += '<div style="display:flex;gap:8px;align-items:flex-start;"><span style="width:20px;height:20px;border-radius:50%;background:var(--l-accent,#0f766e);color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">' + (i + 1) + '</span><span style="font-size:12px;color:var(--l-text,#0d0d0d);line-height:1.5;">' + esc(typeof step === 'string' ? step : step.text) + '</span></div>';
          });
          html += '</div>';
        }
        html += '</div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderPrinciple(containerId); });
      });
    },
    renderTriggers: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadTriggers().then(function (data) {
        var triggers = data.triggers || data.items || [];
        if (!triggers.length) { showState(containerId, 'empty'); return; }
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var html = '<div style="display:flex;flex-direction:column;gap:8px;">';
        triggers.forEach(function (t) {
          var level = t.severity || t.level || 'info';
          var color = { high: '#DC2626', medium: '#D97706', low: '#10B981', info: '#2563EB' }[level] || '#6B7280';
          html += '<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--l-bg-secondary,#f7f7f8);border-radius:10px;border-left:3px solid ' + color + ';">';
          html += '<span style="font-size:13px;font-weight:500;color:var(--l-text,#0d0d0d);flex:1;">' + esc(t.name || t.title || t.trigger || '—') + '</span>';
          html += '<span style="font-size:11px;color:' + color + ';font-weight:600;text-transform:uppercase;">' + esc(level) + '</span>';
          html += '</div>';
        });
        html += '</div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderTriggers(containerId); });
      });
    }
  };

  /* ============================================================
   * 3. 太古集团 (swire_group) → CTH Overview
   * API: /api/swire/overview, /api/swire/events, /api/swire/notes
   * ============================================================ */
  var SwireGroup = {
    loadOverview: function () {
      return fetchJSON('/api/swire/overview');
    },
    loadEvents: function () {
      return fetchJSON('/api/swire/events');
    },
    loadNotes: function () {
      return fetchJSON('/api/swire/notes');
    },
    renderOverview: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadOverview().then(function (data) {
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var overview = data.overview || data;
        var brands = overview.brands || overview.brand_list || [];
        var events = overview.event_count || overview.events || 0;
        var notes = overview.note_count || overview.notes || 0;
        var html = '<div class="zbc-kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;">';
        html += '<div class="card-gradient-cth" style="padding:14px;"><div style="font-size:11px;color:rgba(255,255,255,.7);text-transform:uppercase;">品牌数</div><div class="data-integer" style="margin-top:4px;color:#fff;">' + dispNum(brands.length || overview.brand_count) + '</div></div>';
        html += '<div class="zbc-kpi-card" style="padding:14px;"><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);">事件数</div><div class="data-integer" style="margin-top:4px;font-size:20px;">' + dispNum(events) + '</div></div>';
        html += '<div class="zbc-kpi-card" style="padding:14px;"><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);">笔记数</div><div class="data-integer" style="margin-top:4px;font-size:20px;">' + dispNum(notes) + '</div></div>';
        html += '</div>';
        if (brands.length) {
          html += '<div style="margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;">';
          brands.slice(0, 12).forEach(function (b) {
            html += '<span class="chip-unselected" style="font-size:11px;padding:4px 10px;">' + esc(b.name || b.brand || b) + '</span>';
          });
          html += '</div>';
        }
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderOverview(containerId); });
      });
    }
  };

  /* ============================================================
   * 4. 话题活动 (topic_campaign) → CTH Events
   * API: /api/topic-campaign/status, /api/topic-campaign/topics, /api/topic-campaign/stats, /api/topic-campaign/campaigns
   * ============================================================ */
  var TopicCampaign = {
    loadStatus: function () { return fetchJSON('/api/topic-campaign/status'); },
    loadTopics: function () { return fetchJSON('/api/topic-campaign/topics'); },
    loadStats: function () { return fetchJSON('/api/topic-campaign/stats'); },
    loadCampaigns: function () { return fetchJSON('/api/topic-campaign/campaigns'); },
    renderStatus: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadStatus().then(function (data) {
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var status = data.status || data.state || 'unknown';
        var color = { running: '#10B981', paused: '#D97706', stopped: '#DC2626', error: '#DC2626' }[status] || '#6B7280';
        var html = '<div style="display:flex;align-items:center;gap:12px;padding:14px 18px;background:var(--l-bg-secondary,#f7f7f8);border-radius:12px;">';
        html += '<span style="width:10px;height:10px;border-radius:50%;background:' + color + ';box-shadow:0 0 8px ' + color + ';"></span>';
        html += '<div><div style="font-size:14px;font-weight:600;color:var(--l-text,#0d0d0d);text-transform:uppercase;">' + esc(status) + '</div>';
        html += '<div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);">话题活动采集引擎</div></div>';
        if (data.last_run) html += '<div style="margin-left:auto;font-size:11px;color:var(--l-text-tertiary,#9ca3af);">上次: ' + esc(data.last_run) + '</div>';
        html += '</div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderStatus(containerId); });
      });
    },
    renderTopics: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadTopics().then(function (data) {
        var topics = data.topics || data.items || [];
        if (!topics.length) { showState(containerId, 'empty'); return; }
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var html = '<div class="zbc-scroll-container" style="max-height:320px;"><div style="display:flex;flex-direction:column;gap:6px;">';
        topics.forEach(function (t) {
          var heat = t.heat || t.mention_count || t.count || 0;
          html += '<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--l-bg-secondary,#f7f7f8);border-radius:8px;">';
          html += '<span style="font-size:13px;color:var(--l-text,#0d0d0d);flex:1;"># ' + esc(t.topic || t.name || t.keyword || '—') + '</span>';
          html += '<span style="font-size:12px;font-weight:600;color:var(--l-accent,#0f766e);font-variant-numeric:tabular-nums;">' + dispNum(heat) + '</span>';
          html += '</div>';
        });
        html += '</div></div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderTopics(containerId); });
      });
    }
  };

  /* ============================================================
   * 5. App证据 (app_evidence) → SYSTEM Evidence
   * API: /api/app_evidence/stats, /api/app_evidence/list
   * ============================================================ */
  var AppEvidence = {
    loadStats: function () { return fetchJSON('/api/app_evidence/stats'); },
    loadList: function (limit) { return fetchJSON('/api/app_evidence/list?limit=' + (limit || 20)); },
    renderStats: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadStats().then(function (data) {
        var stats = data.stats || data;
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var html = '<div class="zbc-kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;">';
        html += '<div class="card-gradient-system" style="padding:14px;"><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);text-transform:uppercase;">证据总数</div><div class="data-integer" style="margin-top:4px;">' + dispNum(stats.total || stats.count) + '</div></div>';
        html += '<div class="zbc-kpi-card" style="padding:14px;"><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);">已确认</div><div class="data-integer" style="margin-top:4px;font-size:20px;color:#10B981;">' + dispNum(stats.confirmed || stats.confirmed_count) + '</div></div>';
        html += '<div class="zbc-kpi-card" style="padding:14px;"><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);">待审核</div><div class="data-integer" style="margin-top:4px;font-size:20px;color:#D97706;">' + dispNum(stats.pending || stats.pending_count) + '</div></div>';
        html += '<div class="zbc-kpi-card" style="padding:14px;"><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);">已驳回</div><div class="data-integer" style="margin-top:4px;font-size:20px;color:#DC2626;">' + dispNum(stats.rejected || stats.rejected_count) + '</div></div>';
        html += '</div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderStats(containerId); });
      });
    },
    renderList: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadList(30).then(function (data) {
        var records = data.records || data.items || data.list || [];
        if (!records.length) { showState(containerId, 'empty'); return; }
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var html = '<div class="zbc-scroll-container" style="max-height:360px;"><table style="width:100%;border-collapse:collapse;font-size:12px;">';
        html += '<thead><tr style="text-align:left;border-bottom:1px solid var(--l-border,#e8e8e8);"><th style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);">来源</th><th style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);">内容</th><th style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);">状态</th><th style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);">时间</th></tr></thead><tbody>';
        records.forEach(function (r) {
          var statusColor = { confirmed: '#10B981', pending: '#D97706', rejected: '#DC2626', shadow: '#6B7280' }[r.status] || 'var(--l-text-tertiary,#9ca3af)';
          html += '<tr style="border-bottom:1px solid var(--l-border-light,#f0f0f0);">';
          html += '<td style="padding:8px 10px;color:var(--l-text-secondary,#6b7280);font-size:11px;">' + esc(r.source || r.platform || '—') + '</td>';
          html += '<td style="padding:8px 10px;color:var(--l-text,#0d0d0d);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + esc(trunc(r.title || r.content || r.summary || '—', 35)) + '</td>';
          html += '<td style="padding:8px 10px;"><span style="color:' + statusColor + ';font-weight:600;font-size:11px;text-transform:uppercase;">' + esc(r.status || '—') + '</span></td>';
          html += '<td style="padding:8px 10px;color:var(--l-text-tertiary,#9ca3af);font-size:11px;">' + esc(r.created_at || r.uploaded_at || r.time || '—') + '</td>';
          html += '</tr>';
        });
        html += '</tbody></table></div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderList(containerId); });
      });
    }
  };

  /* ============================================================
   * 6. 架构仪表盘 (architecture_dashboard) → SYSTEM Runtime
   * API: /api/architecture/status, /api/adaptive/status, /api/recovery/stats, /api/feedback/stats, /api/boundary/stats
   * ============================================================ */
  var Architecture = {
    loadStatus: function () { return fetchJSON('/api/architecture/status'); },
    loadAdaptive: function () { return fetchJSON('/api/adaptive/status'); },
    loadRecovery: function () { return fetchJSON('/api/recovery/stats'); },
    loadFeedback: function () { return fetchJSON('/api/feedback/stats'); },
    loadBoundary: function () { return fetchJSON('/api/boundary/stats'); },
    renderDashboard: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      Promise.all([
        this.loadStatus().catch(function () { return null; }),
        this.loadAdaptive().catch(function () { return null; }),
        this.loadRecovery().catch(function () { return null; }),
        this.loadFeedback().catch(function () { return null; }),
        this.loadBoundary().catch(function () { return null; })
      ]).then(function (results) {
        var arch = results[0] || {};
        var adaptive = results[1] || {};
        var recovery = results[2] || {};
        var feedback = results[3] || {};
        var boundary = results[4] || {};
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var layers = [
          { name: '自动调节引擎', icon: '⚙', data: adaptive, status: adaptive.status || adaptive.current_strategy || 'unknown', api: '/api/adaptive/status' },
          { name: '自动修复引擎', icon: '🔧', data: recovery, status: recovery.overall_status || recovery.status || 'unknown', api: '/api/recovery/stats' },
          { name: '数据闭环引擎', icon: '🔄', data: feedback, status: feedback.overall_status || feedback.status || 'unknown', api: '/api/feedback/stats' },
          { name: '边界控制引擎', icon: '🛡', data: boundary, status: boundary.overall_status || boundary.status || 'unknown', api: '/api/boundary/stats' }
        ];
        var html = '<div style="display:flex;flex-direction:column;gap:8px;">';
        layers.forEach(function (layer) {
          var statusColor = { running: '#10B981', healthy: '#10B981', ok: '#10B981', degraded: '#D97706', warning: '#D97706', error: '#DC2626', failed: '#DC2626', stopped: '#6B7280', unknown: '#9CA3AF' }[String(layer.status).toLowerCase()] || '#9CA3AF';
          html += '<div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--l-bg-secondary,#f7f7f8);border-radius:12px;">';
          html += '<span style="font-size:18px;">' + layer.icon + '</span>';
          html += '<div style="flex:1;"><div style="font-size:13px;font-weight:600;color:var(--l-text,#0d0d0d);">' + layer.name + '</div>';
          html += '<div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);font-family:JetBrains Mono,monospace;">' + esc(layer.api) + '</div></div>';
          html += '<span style="display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:' + statusColor + ';text-transform:uppercase;"><span style="width:8px;height:8px;border-radius:50%;background:' + statusColor + ';"></span>' + esc(layer.status) + '</span>';
          html += '</div>';
        });
        html += '</div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderDashboard(containerId); });
      });
    }
  };

  /* ============================================================
   * 7. 系统控制/特性 (system_controls) → SYSTEM全域
   * API: /api/security/scan, /api/evaluation/run, /api/local-ai/status, /api/collector/start-cdp, /api/collector/stop-cdp
   * ============================================================ */
  var SystemControls = {
    securityScan: function () { return fetchJSON('/api/security/scan'); },
    localAIStatus: function () { return fetchJSON('/api/local-ai/status'); },
    startCDP: function () { return fetchJSON('/api/collector/start-cdp', { method: 'POST' }); },
    stopCDP: function () { return fetchJSON('/api/collector/stop-cdp', { method: 'POST' }); },
    renderControlPanel: function (containerId) {
      var c = document.getElementById(containerId);
      if (!c) return;
      var content = c.querySelector('[data-state="content"]');
      if (!content) return;
      var html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;">';
      html += '<div class="zbc-card" style="padding:14px;"><div style="font-size:12px;font-weight:600;color:var(--l-text,#0d0d0d);margin-bottom:10px;">安全扫描</div><button class="btn-capsule-gradient" style="font-size:12px;padding:8px 16px;" onclick="ZBCFeatures.runSecurityScan(\'' + containerId + '\')">执行扫描</button><div id="' + containerId + '-scan-result" style="margin-top:8px;font-size:11px;color:var(--l-text-tertiary,#9ca3af);"></div></div>';
      html += '<div class="zbc-card" style="padding:14px;"><div style="font-size:12px;font-weight:600;color:var(--l-text,#0d0d0d);margin-bottom:10px;">CDP 浏览器</div><div style="display:flex;gap:8px;"><button class="zbc-btn zbc-btn--primary" style="font-size:12px;padding:6px 14px;" onclick="ZBCFeatures.startCDP(\'' + containerId + '\')">启动</button><button class="zbc-btn" style="font-size:12px;padding:6px 14px;" onclick="ZBCFeatures.stopCDP(\'' + containerId + '\')">停止</button></div><div id="' + containerId + '-cdp-result" style="margin-top:8px;font-size:11px;color:var(--l-text-tertiary,#9ca3af);"></div></div>';
      html += '<div class="zbc-card" style="padding:14px;"><div style="font-size:12px;font-weight:600;color:var(--l-text,#0d0d0d);margin-bottom:10px;">本地 AI 状态</div><button class="zbc-btn" style="font-size:12px;padding:6px 14px;" onclick="ZBCFeatures.checkLocalAI(\'' + containerId + '\')">检查状态</button><div id="' + containerId + '-ai-result" style="margin-top:8px;font-size:11px;color:var(--l-text-tertiary,#9ca3af);"></div></div>';
      html += '</div>';
      content.innerHTML = html;
      showState(containerId, 'content');
    },
    runSecurityScan: function (containerId) {
      var resultEl = document.getElementById(containerId + '-scan-result');
      if (resultEl) resultEl.textContent = '扫描中…';
      this.securityScan().then(function (data) {
        if (resultEl) resultEl.innerHTML = '<span style="color:#10B981;">完成: ' + esc(JSON.stringify(data).substring(0, 100)) + '</span>';
      }).catch(function (err) {
        if (resultEl) resultEl.innerHTML = '<span style="color:#DC2626;">失败: ' + esc(err.message) + '</span>';
      });
    },
    startCDP: function (containerId) {
      var resultEl = document.getElementById(containerId + '-cdp-result');
      if (resultEl) resultEl.textContent = '启动中…';
      this.startCDP().then(function (data) {
        if (resultEl) resultEl.innerHTML = '<span style="color:#10B981;">' + esc(data.message || data.status || '已启动') + '</span>';
      }).catch(function (err) {
        if (resultEl) resultEl.innerHTML = '<span style="color:#DC2626;">失败: ' + esc(err.message) + '</span>';
      });
    },
    stopCDP: function (containerId) {
      var resultEl = document.getElementById(containerId + '-cdp-result');
      if (resultEl) resultEl.textContent = '停止中…';
      this.stopCDP().then(function (data) {
        if (resultEl) resultEl.innerHTML = '<span style="color:#D97706;">' + esc(data.message || data.status || '已停止') + '</span>';
      }).catch(function (err) {
        if (resultEl) resultEl.innerHTML = '<span style="color:#DC2626;">失败: ' + esc(err.message) + '</span>';
      });
    },
    checkLocalAI: function (containerId) {
      var resultEl = document.getElementById(containerId + '-ai-result');
      if (resultEl) resultEl.textContent = '检查中…';
      this.localAIStatus().then(function (data) {
        var available = data.available || data.enabled || false;
        var color = available ? '#10B981' : '#D97706';
        if (resultEl) resultEl.innerHTML = '<span style="color:' + color + ';">' + (available ? '可用' : '未配置') + ' · ' + esc(data.model || data.provider || '—') + '</span>';
      }).catch(function (err) {
        if (resultEl) resultEl.innerHTML = '<span style="color:#DC2626;">失败: ' + esc(err.message) + '</span>';
      });
    }
  };

  /* ============================================================
   * 8. ZBMP工作台/面板 (zbmp-workbench) → ZBMP全域
   * 使用现有 /api/zbmp/* 端点
   * ============================================================ */
  var ZBMPWorkbench = {
    loadOverview: function () { return fetchJSON('/api/zbmp/overview'); },
    loadBrands: function () { return fetchJSON('/api/zbmp/brands'); },
    loadMetrics: function () { return fetchJSON('/api/zbmp/metrics'); },
    renderKPIGrid: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadOverview().then(function (data) {
        var overview = data.overview || data.data || data;
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        var kpis = [
          { label: '品牌总数', value: overview.brand_count || overview.total_brands, color: 'zbmp' },
          { label: '内容总数', value: overview.content_count || overview.total_content, color: '' },
          { label: 'KOS/KOL', value: overview.kos_count || overview.kol_count, color: '' },
          { label: '竞品监控', value: overview.competitor_count || overview.competition_count, color: '' }
        ];
        var html = '<div class="zbc-kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;">';
        kpis.forEach(function (kpi) {
          var cardClass = kpi.color === 'zbmp' ? 'card-gradient-zbmp' : 'zbc-kpi-card';
          var valueColor = kpi.color === 'zbmp' ? 'color:#fff;' : '';
          html += '<div class="' + cardClass + '" style="padding:16px;"><div style="font-size:11px;color:' + (kpi.color === 'zbmp' ? 'rgba(255,255,255,.7)' : 'var(--l-text-tertiary,#9ca3af)') + ';text-transform:uppercase;letter-spacing:.04em;">' + esc(kpi.label) + '</div><div class="data-integer" style="margin-top:6px;' + valueColor + '">' + dispNum(kpi.value) + '</div></div>';
        });
        html += '</div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderKPIGrid(containerId); });
      });
    }
  };

  /* ============================================================
   * 9. 辅助数据源 (auxiliary_sources) → 采集发现页（微博/B站）
   * 检查后端是否有对应API，如无则前端展示层
   * ============================================================ */
  var AuxiliarySources = {
    loadSources: function () {
      // 尝试多个可能的端点
      return fetchJSON('/api/auxiliary/sources').catch(function () {
        return fetchJSON('/api/web-sources').catch(function () {
          return { sources: [], message: '辅助数据源API暂不可用' };
        });
      });
    },
    renderSourceList: function (containerId) {
      var self = this;
      showState(containerId, 'loading');
      this.loadSources().then(function (data) {
        var sources = data.sources || data.items || [];
        var c = document.getElementById(containerId);
        if (!c) return;
        var content = c.querySelector('[data-state="content"]');
        if (!content) return;
        if (!sources.length) {
          content.innerHTML = '<div style="padding:24px;text-align:center;"><div style="font-size:24px;margin-bottom:8px;">📡</div><div style="font-size:13px;color:var(--l-text-secondary,#6b7280);">辅助数据源配置中</div><div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);margin-top:4px;">微博 / B站 / 知乎 / 抖音</div></div>';
          showState(containerId, 'content');
          return;
        }
        var html = '<div style="display:flex;flex-direction:column;gap:8px;">';
        sources.forEach(function (s) {
          var statusColor = { active: '#10B981', connected: '#10B981', error: '#DC2626', disconnected: '#6B7280' }[s.status] || '#9CA3AF';
          html += '<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--l-bg-secondary,#f7f7f8);border-radius:10px;">';
          html += '<span style="font-size:16px;">' + esc(s.icon || s.emoji || '📡') + '</span>';
          html += '<div style="flex:1;"><div style="font-size:13px;font-weight:500;color:var(--l-text,#0d0d0d);">' + esc(s.name || s.platform || '—') + '</div>';
          if (s.last_sync) html += '<div style="font-size:11px;color:var(--l-text-tertiary,#9ca3af);">上次同步: ' + esc(s.last_sync) + '</div></div>';
          html += '<span style="width:8px;height:8px;border-radius:50%;background:' + statusColor + ';"></span>';
          html += '</div>';
        });
        html += '</div>';
        content.innerHTML = html;
        showState(containerId, 'content');
      }).catch(function (err) {
        showState(containerId, 'error', err.message, function () { self.renderSourceList(containerId); });
      });
    }
  };

  /* ---------- 导出到全局 ---------- */
  global.ZBCFeatures = {
    CaseAnalysis: CaseAnalysis,
    PRCase: PRCase,
    SwireGroup: SwireGroup,
    TopicCampaign: TopicCampaign,
    AppEvidence: AppEvidence,
    Architecture: Architecture,
    SystemControls: SystemControls,
    ZBMPWorkbench: ZBMPWorkbench,
    AuxiliarySources: AuxiliarySources,
    // 便捷方法
    runSecurityScan: function (id) { SystemControls.runSecurityScan(id); },
    startCDP: function (id) { SystemControls.startCDP(id); },
    stopCDP: function (id) { SystemControls.stopCDP(id); },
    checkLocalAI: function (id) { SystemControls.checkLocalAI(id); }
  };

  console.log('[feature-modules] 9项功能模块接线已加载（CaseAnalysis/PRCase/SwireGroup/TopicCampaign/AppEvidence/Architecture/SystemControls/ZBMPWorkbench/AuxiliarySources）');
})(window);
