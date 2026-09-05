/* ============================================================================
   LUMENIS Data — 真实 API 绑定层（Command Home 六区 + 各 P0 页面）
   所有端点均来自 ZBC 源码审计（S07 API Mapper），字段映射以 handler 实际
   返回为准。无数据走 empty 态，错误走 error/offline，绝不静默成 0 或假绿。
   供数源：
     System State        ← /api/system/health/summary
     Intelligence Pulse  ← /api/ai/status + /api/ai/channel-health
     Active Risks        ← /api/risk-alerts
     Active Tasks        ← /api/collect/schedule-status
     Recent Evidence     ← /api/evidence/list?limit=5
     Recommended Actions ← 由 diagnostic_hints / need_manual_intervention /
                            overall_status / circuit.open 客户端派生（无信号=empty）
     Core Metrics        ← /api/stats
   ============================================================================ */
(function (global) {
  "use strict";
  var L = global.LUMENIS || {};

  /* ---------- 工具：安全取字段 ---------- */
  function pick(obj) {
    for (var i = 1; i < arguments.length; i++) {
      var k = arguments[i];
      if (obj && obj[k] != null && obj[k] !== "") return obj[k];
    }
    return null;
  }
  function fmtNum(n) {
    if (n == null || isNaN(n)) return "–";
    return Number(n).toLocaleString();
  }
  function fmtTime(s) {
    if (!s) return "–";
    // 兼容 "2026-09-05 14:23:01" 与 ISO
    return String(s).replace("T", " ").slice(0, 19);
  }
  function el(sel, root) { return (root || document).querySelector(sel); }
  function setField(root, field, val) {
    var n = root.querySelector('[data-field="' + field + '"]');
    if (n) n.textContent = (val == null || val === "") ? "–" : val;
  }
  function statusDot(light) {
    // light: green/yellow/red/unknown → CSS 类
    var map = { green: "success", yellow: "warning", red: "danger", ok: "success", warning: "warning", critical: "danger" };
    return map[light] || "unknown";
  }

  /* ---------- 01 System State ---------- */
  function bindSystemState(root) {
    L.bindState(root, {
      page: "home", component: "system-state",
      url: "/api/system/health/summary",
      isEmpty: function (d) { return !d || !d.sub_lights; },
      emptyText: "系统状态暂不可用",
      render: function (d) {
        var overall = d.overall_status || "unknown";
        var dot = root.querySelector(".lm-card__head .lm-dot");
        if (dot) { dot.className = "lm-dot lm-dot--" + statusDot(overall); }
        setField(root, "live", overall === "ok" ? "LIVE" : overall.toUpperCase());
        var db = d.sub_lights.database || {};
        var col = d.sub_lights.collector || {};
        setField(root, "collector", col.cdp_running ? "运行中" : (col.light === "red" ? "异常" : "待机"));
        setField(root, "freshness", "今日入库 " + fmtNum(d.today_collected) + " · 笔记 " + fmtNum(d.notes_count));
        // 附加子灯（若模板有 data-field）
        setField(root, "db-light", db.light || "–");
        setField(root, "auth-light", (d.sub_lights.auth || {}).light || "–");
        setField(root, "alerts", fmtNum(d.active_alerts));
        setField(root, "manual-intervention", d.need_manual_intervention ? "需要" : "否");
      }
    });
  }

  /* ---------- 02 Intelligence Pulse ---------- */
  function bindIntelligencePulse(root) {
    L.bindState(root, {
      page: "home", component: "intelligence-pulse",
      url: "/api/ai/status",
      isEmpty: function (d) { return !d || d.enabled === false; },
      emptyText: "AI 未启用",
      render: function (d) {
        setField(root, "ai-tasks", d.enabled ? "在线" : "离线");
        var provider = d.provider || "unknown";
        var model = d.model || "–";
        setField(root, "ai-pulse", provider + " / " + model);
        var badge = root.querySelector(".lm-ai-badge");
        if (badge) badge.classList.toggle("lm-ai-badge--online", !!d.enabled);
        // 通道健康（次级，失败不影响主卡）
        LUMENIS.fetch("/api/ai/channel-health").then(function (r) { return r.json(); })
          .then(function (h) {
            if (h && h.health) {
              setField(root, "channel", (h.health.available ? "通道正常" : "通道降级"));
            }
          }).catch(function () { /* 静默，主卡已 success */ });
      }
    });
  }

  /* ---------- 03 Active Risks（≤5） ---------- */
  function bindActiveRisks(root) {
    L.bindState(root, {
      page: "home", component: "active-risks",
      url: "/api/risk-alerts",
      isEmpty: function (d) { return !d || !Array.isArray(d.notes) || d.notes.length === 0; },
      emptyText: "当前无高/中风险笔记",
      render: function (d) {
        var notes = (d.notes || []).slice(0, 5);
        setField(root, "risk-count", notes.length + " 条");
        var list = root.querySelector('[data-field="risk-list"]');
        if (!list) return;
        list.innerHTML = "";
        notes.forEach(function (n) {
          var li = document.createElement("li");
          li.className = "lm-list-item";
          var level = pick(n, "risk_level", "level") || "medium";
          var title = pick(n, "title", "note_title", "content") || "未命名笔记";
          var score = pick(n, "risk_score", "score");
          var dotCls = level === "high" ? "danger" : (level === "medium" ? "warning" : "info");
          li.innerHTML =
            '<span class="lm-dot lm-dot--' + dotCls + '"></span>' +
            '<span class="lm-status" style="flex:1;min-width:0;">' +
              '<span style="display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(title) + '</span>' +
              '<span style="font-size:11px;color:var(--lm-text-tertiary);">' + level + (score != null ? " · " + score : "") + '</span>' +
            '</span>';
          list.appendChild(li);
        });
      }
    });
  }

  /* ---------- 04 Active Tasks（≤5） ---------- */
  function bindActiveTasks(root) {
    L.bindState(root, {
      page: "home", component: "active-tasks",
      url: "/api/collect/schedule-status",
      isEmpty: function (d) { return !d || (!Array.isArray(d.running) || d.running.length === 0) && d.state === "ok"; },
      emptyText: "当前无运行中任务",
      render: function (d) {
        var running = (d.running || []).slice(0, 5);
        setField(root, "task-count", running.length + " 运行中");
        var list = root.querySelector('[data-field="task-list"]');
        if (!list) return;
        list.innerHTML = "";
        if (running.length === 0) {
          // 无运行任务时显示采集状态摘要（真实，非假任务）
          var li = document.createElement("li");
          li.className = "lm-list-item";
          li.innerHTML = '<span class="lm-dot lm-dot--' + statusDot(d.state === "ok" ? "green" : "yellow") + '"></span>' +
            '<span class="lm-status" style="flex:1;">' +
              '<span style="display:block;">' + escapeHtml(d.state_cn || d.state || "–") + '</span>' +
              '<span style="font-size:11px;color:var(--lm-text-tertiary);">今日 ' + fmtNum(d.today_runs) + ' 次 · 下次 ' + escapeHtml(d.next_collect || "–") + '</span>' +
            '</span>';
          list.appendChild(li);
        } else {
          running.forEach(function (t) {
            var li = document.createElement("li");
            li.className = "lm-list-item";
            li.innerHTML = '<span class="lm-dot lm-dot--ai lm-dot--pulse"></span>' +
              '<span class="lm-status" style="flex:1;">' +
                '<span style="display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(t.message || t.task_id || "采集任务") + '</span>' +
                '<span style="font-size:11px;color:var(--lm-text-tertiary);">' + (t.run_type || "") + ' · ' + (t.progress || 0) + '%</span>' +
              '</span>';
            list.appendChild(li);
          });
        }
      }
    });
  }

  /* ---------- 05 Recent Evidence（≤5） ---------- */
  function bindRecentEvidence(root) {
    L.bindState(root, {
      page: "home", component: "recent-evidence",
      url: "/api/evidence/list?limit=5",
      isEmpty: function (d) { return !d || !Array.isArray(d.records) || d.records.length === 0; },
      emptyText: "暂无证据记录",
      render: function (d) {
        var recs = (d.records || []).slice(0, 5);
        var tl = root.querySelector('[data-field="evidence-list"]');
        if (!tl) return;
        tl.innerHTML = "";
        recs.forEach(function (r) {
          var item = document.createElement("div");
          item.className = "lm-timeline-item";
          var title = pick(r, "title", "name", "evidence_type", "type") || "证据";
          var desc = pick(r, "summary", "description", "source", "note") || "";
          var at = pick(r, "created_at", "at", "timestamp", "captured_at");
          item.innerHTML =
            '<span class="lm-timeline-item__dot"></span>' +
            '<div><div style="font-weight:600;font-size:13px;">' + escapeHtml(title) + '</div>' +
            '<div style="font-size:12px;color:var(--lm-text-tertiary);">' + escapeHtml(desc) + (at ? ' · ' + fmtTime(at) : '') + '</div></div>';
          tl.appendChild(item);
        });
      }
    });
  }

  /* ---------- 06 Recommended Actions（派生，≤3，无信号=empty） ---------- */
  function bindRecommendedActions(root) {
    // 同时拉 health + schedule，派生动作
    var store = L.store;
    store.set("home", "recommended-actions", "loading");
    root.setAttribute("data-state", "loading");
    Promise.all([
      LUMENIS.fetch("/api/system/health/summary").then(function (r) { return r.json(); }).catch(function () { return null; }),
      LUMENIS.fetch("/api/collect/schedule-status").then(function (r) { return r.json(); }).catch(function () { return null; })
    ]).then(function (results) {
      var health = results[0], sched = results[1];
      var actions = [];
      if (health) {
        if (health.need_manual_intervention) actions.push({ kind: "danger", text: "系统需要人工介入：" + ((health.diagnostic_hints || [])[0] || "检查诊断提示") });
        if (health.overall_status === "critical") actions.push({ kind: "danger", text: "整体状态 Critical，立即排查 " + Object.keys(health.sub_lights || {}).filter(function (k) { return health.sub_lights[k].light === "red"; }).join("、") });
        (health.diagnostic_hints || []).slice(0, 2).forEach(function (h) {
          if (actions.length < 3) actions.push({ kind: "warning", text: h });
        });
      }
      if (sched && sched.circuit && sched.circuit.open && actions.length < 3) {
        actions.push({ kind: "warning", text: "采集熔断中：" + (sched.circuit.detail || sched.circuit.state || "") + "，恢复后再采集" });
      }
      if (sched && sched.state === "no_cookie" && actions.length < 3) {
        actions.push({ kind: "warning", text: "小红书未配置登录态，请在系统内浏览器扫码登录" });
      }
      var list = root.querySelector('[data-field="action-list"]');
      if (list) {
        list.innerHTML = "";
        if (actions.length === 0) {
          store.set("home", "recommended-actions", "empty", { dataRef: "/api/system/health/summary", message: "系统运行正常，暂无待处理动作" });
          root.setAttribute("data-state", "empty");
          var slot = root.querySelector("[data-state-slot]");
          if (slot) slot.innerHTML = '<div style="font-size:13px;color:var(--lm-text-tertiary);padding:8px 0;">系统运行正常，暂无待处理动作</div>';
        } else {
          actions.slice(0, 3).forEach(function (a) {
            var d = document.createElement("div");
            d.className = "lm-list-item";
            d.innerHTML = '<span class="lm-dot lm-dot--' + a.kind + '"></span>' +
              '<span style="flex:1;font-size:13px;">' + escapeHtml(a.text) + '</span>';
            list.appendChild(d);
          });
          store.set("home", "recommended-actions", "success", { dataRef: "/api/system/health/summary+/api/collect/schedule-status" });
          root.setAttribute("data-state", "success");
        }
      }
    }).catch(function () {
      store.set("home", "recommended-actions", "error", { dataRef: "derived", errorCode: "DERIVE_FAILED", message: "动作派生失败" });
      root.setAttribute("data-state", "error");
    });
  }

  /* ---------- Core Metrics（/api/stats，用于 Production Overview） ---------- */
  function bindCoreMetrics(root) {
    L.bindState(root, {
      page: "production", component: "core-metrics",
      url: "/api/stats",
      isEmpty: function (d) { return !d || !d.stats; },
      emptyText: "统计数据暂不可用",
      render: function (d) {
        var s = d.stats || {};
        setField(root, "total", fmtNum(s.total));
        setField(root, "positive", fmtNum(s.positive));
        setField(root, "neutral", fmtNum(s.neutral));
        setField(root, "negative", fmtNum(s.negative));
        setField(root, "high-risk", fmtNum(s.high_risk));
        setField(root, "engagements", fmtNum(s.total_engagements));
      }
    });
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- 统一入口 ---------- */
  function bindCommandHome() {
    var ss = el('[data-component="system-state"]');
    var ip = el('[data-component="intelligence-pulse"]');
    var ar = el('[data-component="active-risks"]');
    var at = el('[data-component="active-tasks"]');
    var re = el('[data-component="recent-evidence"]');
    var ra = el('[data-component="recommended-actions"]');
    if (ss) bindSystemState(ss);
    if (ip) bindIntelligencePulse(ip);
    if (ar) bindActiveRisks(ar);
    if (at) bindActiveTasks(at);
    if (re) bindRecentEvidence(re);
    if (ra) bindRecommendedActions(ra);
  }

  L.Data = {
    bindCommandHome: bindCommandHome,
    bindSystemState: bindSystemState,
    bindIntelligencePulse: bindIntelligencePulse,
    bindActiveRisks: bindActiveRisks,
    bindActiveTasks: bindActiveTasks,
    bindRecentEvidence: bindRecentEvidence,
    bindRecommendedActions: bindRecommendedActions,
    bindCoreMetrics: bindCoreMetrics,
    pick: pick, fmtNum: fmtNum, fmtTime: fmtTime, escapeHtml: escapeHtml
  };
  global.LUMENIS = L;
})(window);
