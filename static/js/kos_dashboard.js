/* Z-Brand-Core KOS 传播主体智能 Dashboard
 * 复用 /api/kos/* API，不重复建设
 */
(function () {
  "use strict";

  var currentTier = "";
  var kosCache = [];

  function api(path, opts) {
    return fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}))
      .then(function (r) { return r.json(); });
  }

  function loadKosStats() {
    api("/api/kos/overview").then(function (d) {
      if (!d.ok || !d.data) return;
      var s = d.data;
      setText("kosTotal", s.total || 0);
      setText("kosS", (s.by_tier && s.by_tier.S) || 0);
      setText("kosA", (s.by_tier && s.by_tier.A) || 0);
      setText("kosPotential", s.potential || 0);
    }).catch(function (e) { console.error("[KOS] stats error", e); });
  }

  function loadKosList(tier) {
    currentTier = tier || "";
    var url = "/api/kos/list?limit=30&sort_by=kos_score" + (currentTier ? "&tier=" + currentTier : "");
    api(url).then(function (d) {
      if (!d.ok) return;
      kosCache = d.profiles || [];
      renderKosList(kosCache);
    }).catch(function (e) { console.error("[KOS] list error", e); });
  }

  function renderKosList(profiles) {
    var el = document.getElementById("kosList");
    if (!el) return;
    if (!profiles.length) {
      el.innerHTML = '<div style="padding:24px;text-align:center;color:#999">暂无数据</div>';
      return;
    }
    var tierColor = { S: "#e74c3c", A: "#f39c12", B: "#3498db", C: "#95a5a6" };
    var html = profiles.map(function (p, i) {
      var score = (p.kos_score || 0).toFixed(1);
      var tier = p.kos_tier || "C";
      var color = tierColor[tier] || "#95a5a6";
      var pct = Math.min(100, (p.kos_score || 0));
      return '<div class="kos-row" style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f0f0f0;cursor:pointer" onclick="kosShowDetail(\'' + (p.author_id || "") + '\')">'
        + '<span style="width:24px;text-align:center;font-weight:600;color:#666">' + (i + 1) + '</span>'
        + '<div style="flex:1;min-width:0">'
        + '<div style="font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + (p.author_nickname || p.author_id || "未知") + '</div>'
        + '<div style="font-size:11px;color:#999;margin-top:2px">' + (p.note_count || 0) + ' 篇 · 互动 ' + (p.avg_engagement || 0) + ' · ' + (p.lifecycle_stage || "") + '</div>'
        + '</div>'
        + '<span style="display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;border-radius:4px;font-size:11px;font-weight:600;color:#fff;background:' + color + '">' + tier + '</span>'
        + '<div style="width:120px;height:6px;background:#eee;border-radius:3px;overflow:hidden"><div style="width:' + pct + '%;height:100%;background:' + color + '"></div></div>'
        + '<span style="width:40px;text-align:right;font-weight:600">' + score + '</span>'
        + '</div>';
    }).join("");
    el.innerHTML = html;
  }

  function kosShowDetail(authorId) {
    if (!authorId) return;
    api("/api/kos/detail?author_id=" + encodeURIComponent(authorId)).then(function (d) {
      if (!d.ok || !d.data) { alert("加载详情失败"); return; }
      var p = d.data;
      var notes = (p.notes || []).slice(0, 5).map(function (n) {
        return '<li style="padding:6px 0;border-bottom:1px solid #f5f5f5"><strong>' + (n.title || n.note_id || "") + '</strong><br><span style="font-size:11px;color:#999">点赞 ' + (n.likes || 0) + ' · 评论 ' + (n.comments || 0) + ' · ' + (n.publish_datetime || "") + '</span></li>';
      }).join("");
      var html = '<div style="padding:20px;max-width:600px">'
        + '<h3 style="margin:0 0 8px">' + (p.author_nickname || "") + '</h3>'
        + '<p style="color:#666;margin:0 0 16px">层级: ' + (p.kos_tier || "") + ' · 评分: ' + ((p.kos_score || 0).toFixed(1)) + ' · 生命周期: ' + (p.lifecycle_stage || "") + '</p>'
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:16px">'
        + '<div style="background:#f9f9f9;padding:8px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (p.note_count || 0) + '</div><div style="font-size:11px;color:#999">笔记数</div></div>'
        + '<div style="background:#f9f9f9;padding:8px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (p.avg_engagement || 0) + '</div><div style="font-size:11px;color:#999">总互动</div></div>'
        + '<div style="background:#f9f9f9;padding:8px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (p.avg_quality || 0).toFixed(1) + '</div><div style="font-size:11px;color:#999">平均质量</div></div>'
        + '</div>'
        + '<h4 style="margin:0 0 8px">最近笔记</h4><ul style="list-style:none;padding:0;margin:0">' + (notes || '<li>暂无</li>') + '</ul>'
        + '<div style="margin-top:16px;display:flex;gap:8px">'
        + '<button onclick="kosGenOutreach(\'' + authorId + '\')" style="padding:8px 16px;background:#171717;color:#fff;border:none;border-radius:6px;cursor:pointer">生成触达文案</button>'
        + '<button onclick="kosGenReward(\'' + authorId + '\')" style="padding:8px 16px;background:#f0f0f0;border:none;border-radius:6px;cursor:pointer">奖励积分</button>'
        + '</div></div>';
      showModal("KOS 详情", html);
    }).catch(function (e) { alert("加载详情失败: " + e); });
  }

  function kosGenOutreach(authorId) {
    fetch("/api/kos/outreach", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ author_id: authorId, brand_name: "广州太古汇" })
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) { alert("生成失败: " + (d.error || "")); return; }
      showModal("博主触达文案（DRAFT）", '<div style="padding:20px;white-space:pre-wrap;font-size:13px;line-height:1.7">' + (d.outreach_text || d.content || "") + '</div>');
    }).catch(function (e) { alert("生成失败: " + e); });
  }

  function kosGenReward(authorId) {
    api("/api/kos/reward?author_id=" + encodeURIComponent(authorId)).then(function (d) {
      if (!d.ok) { alert("计算失败"); return; }
      var r = d.data || d;
      showModal("奖励积分", '<div style="padding:20px"><h3 style="margin:0 0 12px">总积分: ' + (r.total_points || 0) + '</h3>'
        + '<p>基础: ' + (r.base_points || 0) + ' · 质量: ' + (r.quality_points || 0) + ' · 传播: ' + (r.reach_points || 0) + '</p>'
        + '<p style="color:#999;font-size:12px">奖励金额/权益需配置后生效，当前仅展示积分模型</p></div>');
    }).catch(function (e) { alert("计算失败: " + e); });
  }

  function kosFilterTier(btn, tier) {
    document.querySelectorAll("#page-kos .filter-btn").forEach(function (b) { b.classList.remove("active"); });
    btn.classList.add("active");
    loadKosList(tier);
  }

  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function showModal(title, html) {
    var overlay = document.createElement("div");
    overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center";
    var modal = document.createElement("div");
    modal.style.cssText = "background:#fff;border-radius:12px;max-width:640px;width:90%;max-height:80vh;overflow-y:auto;position:relative";
    modal.innerHTML = '<div style="padding:16px 20px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center"><h3 style="margin:0">' + title + '</h3><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:none;border:none;font-size:20px;cursor:pointer;color:#999">×</button></div>' + html;
    overlay.appendChild(modal);
    overlay.onclick = function (e) { if (e.target === overlay) overlay.remove(); };
    document.body.appendChild(overlay);
  }

  // 暴露到全局
  window.kosShowDetail = kosShowDetail;
  window.kosGenOutreach = kosGenOutreach;
  window.kosGenReward = kosGenReward;
  window.kosFilterTier = kosFilterTier;

  // 页面进入 KOS 时加载
  document.addEventListener("DOMContentLoaded", function () {
    // 监听 navigateTo 进入 kos 页面
    var origNavigate = window.navigateTo;
    if (origNavigate) {
      window.navigateTo = function (page) {
        origNavigate(page);
        if (page === "kos") {
          loadKosStats();
          loadKosList("");
        }
      };
    }
  });
})();
