// 序境 · 播客情报工作台（Podcast Intelligence）
// 对齐 podcast/IMPLEMENTATION_PLAN_V1：实体图 + 确定性智能算法，不虚构平台数据
(function () {
  "use strict";

  // 选题十维信号（0-10），与 podcast/intelligence/topic_scoring.py 对齐
  var TOPIC_DIMS = [
    ["demand", "需求强度"], ["timeliness", "时效"], ["novelty", "新颖度"],
    ["human_relevance", "人物相关"], ["guest_fit", "嘉宾匹配"], ["evidence", "证据充分"],
    ["content_yield", "内容产出"], ["distribution", "分发潜力"], ["risk", "风险(低=高分)"], ["cost", "成本(低=高分)"]
  ];

  function api(url, opts) {
    return fetch(url, Object.assign({ headers: {} }, opts || {})).then(function (r) { return r.json(); });
  }
  function post(url, body) {
    return api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  function el(id) { return document.getElementById(id); }

  // ---------- 概览统计 ----------
  function loadOverview() {
    api("/api/podcast/overview").then(function (d) {
      if (!d.ok) return;
      var s = d.stats || {};
      var bt = s.by_type || {};
      var box = el("pcStats");
      if (!box) return;
      var order = ["show", "episode", "segment", "story_node", "topic", "question", "content_asset", "person"];
      var labelMap = { show: "节目", episode: "单集", segment: "分段", story_node: "故事节点", topic: "选题", question: "问题", content_asset: "内容资产", person: "人物" };
      box.innerHTML = order.map(function (k) {
        return '<div class="pc-stat"><b>' + (bt[k] || 0) + '</b><span>' + (labelMap[k] || k) + '</span></div>';
      }).join('') + '<div class="pc-stat"><b>' + (s.total || 0) + '</b><span>实体总数</span></div>';
    }).catch(function () {});
  }

  // ---------- 选题打分 ----------
  function initTopicScorer() {
    var grid = el("pcTopicDims");
    if (!grid || grid.dataset.inited) return;
    grid.dataset.inited = "1";
    grid.innerHTML = TOPIC_DIMS.map(function (dim, i) {
      return '<label class="pc-dim"><span>' + dim[1] + '</span>' +
        '<input type="range" min="0" max="10" step="1" value="' + (i < 6 ? 7 : 4) + '" data-dim="' + dim[0] + '">' +
        '<em data-val="' + dim[0] + '">7</em></label>';
    }).join('');
    grid.querySelectorAll("input[type=range]").forEach(function (inp) {
      inp.addEventListener("input", function () {
        var v = el("pcTopicDims").querySelector('[data-val="' + inp.dataset.dim + '"]');
        if (v) v.textContent = inp.value;
      });
    });
    var btn = el("pcScoreBtn");
    if (btn) btn.addEventListener("click", function () {
      var signals = {};
      grid.querySelectorAll("input[type=range]").forEach(function (inp) { signals[inp.dataset.dim] = Number(inp.value); });
      var out = el("pcScoreOut");
      if (out) out.innerHTML = "打分中…";
      post("/api/podcast/topic-score", { signals: signals }).then(function (d) {
        if (!d.ok) { if (out) out.textContent = "失败：" + (d.error || ""); return; }
        var stageMap = { now: "立即做", soon: "近期规划", watch: "持续观察", later: "暂缓" };
        if (out) out.innerHTML = '<div class="pc-score-big">' + d.score + '</div>' +
          '<div class="pc-score-stage">阶段：<b>' + (stageMap[d.stage] || d.stage) + '</b></div>' +
          '<div class="pc-score-hint">十维加权确定性打分，结果可复现，AI 不参与最终判定</div>';
      }).catch(function (e) { if (out) out.textContent = "错误：" + e.message; });
    });
  }

  // ---------- 实体库 ----------
  function loadEntities(type) {
    var q = type ? "?type=" + type : "";
    api("/api/podcast/entities" + q).then(function (d) {
      var box = el("pcEntityList");
      if (!box) return;
      var list = d.entities || [];
      if (!list.length) { box.innerHTML = '<div class="pc-empty">暂无实体。播客数据与品牌舆情物理隔离，可手动录入或经导入管线进入。</div>'; return; }
      box.innerHTML = list.slice(0, 40).map(function (e) {
        return '<div class="pc-entity-row"><span class="pc-entity-type">' + e.entity_type + '</span>' +
          '<span class="pc-entity-title">' + (e.title || e.entity_id) + '</span>' +
          '<span class="pc-entity-ev ' + e.evidence_status + '">' + e.evidence_status + '</span></div>';
      }).join('');
    }).catch(function () {});
  }

  function initEntityTools() {
    var sel = el("pcEntityFilter");
    if (sel && !sel.dataset.inited) {
      sel.dataset.inited = "1";
      sel.addEventListener("change", function () { loadEntities(sel.value); });
    }
    var add = el("pcAddEntity");
    if (add && !add.dataset.inited) {
      add.dataset.inited = "1";
      add.addEventListener("click", function () {
        var type = el("pcNewType").value, title = el("pcNewTitle").value.trim();
        if (!title) { alert("请填写标题"); return; }
        post("/api/podcast/entity", { entity_type: type, title: title }).then(function (d) {
          if (d.ok) { el("pcNewTitle").value = ""; loadEntities(sel ? sel.value : null); loadOverview(); }
          else alert(d.error || "录入失败");
        });
      });
    }
  }

  // ---------- 破圈分类工具 ----------
  function initBreakout() {
    var btn = el("pcBreakoutBtn");
    if (!btn || btn.dataset.inited) return;
    btn.dataset.inited = "1";
    btn.addEventListener("click", function () {
      var cur = Number(el("pcBoCurrent").value || 0), base = Number(el("pcBoBaseline").value || 0);
      post("/api/podcast/breakout", { current: cur, baseline: base }).then(function (d) {
        var out = el("pcBreakoutOut");
        if (!d.ok) { out.textContent = d.error || "失败"; return; }
        var map = { normal: "常态", breakout: "破圈", viral: "病毒式爆发" };
        out.innerHTML = '判定：<b>' + (map[d.state] || d.state) + '</b> <span class="pc-score-hint">（1.8×破圈 / 3×病毒，阈值可配）</span>';
      });
    });
  }

  function loadAllPodcast() {
    loadOverview();
    initTopicScorer();
    loadEntities("");
    initEntityTools();
    initBreakout();
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.getElementById("page-podcast")) loadAllPodcast();
    var origNavigate = window.navigateTo;
    if (origNavigate) {
      window.navigateTo = function (page) {
        origNavigate(page);
        if (page === "podcast") loadAllPodcast();
      };
    }
  });

  window.pcLoadEntities = loadEntities;
})();
