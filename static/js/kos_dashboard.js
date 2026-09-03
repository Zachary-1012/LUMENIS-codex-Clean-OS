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

  // KM-03/06：漏斗 + 分层 + 多渠道 ROI 卡片（动态注入 #page-kos，不依赖静态模板）
  function ensureKosPanel(id, title) {
    var el = document.getElementById(id);
    if (el) return el;
    var page = document.getElementById("page-kos");
    if (!page) return null;
    var panel = document.createElement("div");
    panel.id = id;
    panel.style.cssText = "margin-top:14px";
    panel.innerHTML = '<div class="glass-card" style="padding:16px"><h4 style="margin:0 0 10px;font-size:14px">' + title + '</h4><div id="' + id + 'Body" style="font-size:13px;color:#999">加载中...</div></div>';
    page.appendChild(panel);
    return panel;
  }

  function kosBar(label, val, pct, color) {
    return '<div style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px"><span>' + label + '</span><b>' + val + '</b></div><div style="height:6px;background:#f0f0f0;border-radius:3px;overflow:hidden"><div style="height:100%;width:' + pct + '%;background:' + (color || "#171717") + ';border-radius:3px"></div></div></div>';
  }

  function loadKosFunnel() {
    ensureKosPanel("kosFunnelPanel", "KOS 三阶漏斗 & 分层集中度");
    api("/api/kos/funnel?entity=all&limit=5").then(function (d) {
      if (!d.ok || !d.data) return;
      var f = d.data.funnel || {};
      var body = document.getElementById("kosFunnelPanelBody");
      if (!body) return;
      body.innerHTML = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px">'
        + '<div style="background:#f9f9f9;padding:10px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (f.kos_cnt || 0) + '</div><div style="font-size:11px;color:#999">KOS 数</div></div>'
        + '<div style="background:#f9f9f9;padding:10px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (f.viewership != null ? f.viewership.toLocaleString() : "--") + '</div><div style="font-size:11px;color:#999">曝光</div></div>'
        + '<div style="background:#f9f9f9;padding:10px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (f.wecom_add || 0) + '</div><div style="font-size:11px;color:#999">WeCom</div></div>'
        + '<div style="background:#f9f9f9;padding:10px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (f.sales_amount || 0) + '</div><div style="font-size:11px;color:#999">销售(¥)</div></div>'
        + '</div><div style="font-size:11px;color:#999">分层集中度：</div>';
    }).catch(function () {});
    api("/api/kos/tier?limit=20").then(function (d) {
      if (!d.ok || !d.data) return;
      var body = document.getElementById("kosFunnelPanelBody");
      if (!body) return;
      var t = d.data.tiers || {};
      var map = [["Top5", t.top5], ["Top6-10", t.top6_10], ["Top11-20", t.top11_20], ["其他", t.others]];
      var bars = map.map(function (pair) {
        var v = pair[1] || {};
        var share = v.engagement_share || 0;
        return kosBar(pair[0], share + "%", Math.min(100, share), "#171717");
      }).join("");
      body.innerHTML += bars;
      renderKosHealth(d.data);
    }).catch(function () {});
  }

  // KM-02 成本指标表（DFS 口径：CPL=预算/进线、CPC=预算/点击、Cost-per-WeCom=预算/WeCom；缺失显式待回填，不造假）
  function loadKosCost() {
    ensureKosPanel("kosCostPanel", "KOS 成本指标（CPL / CPC / Cost-per-WeCom）");
    api("/api/kos/cost?period=month").then(function (d) {
      var body = document.getElementById("kosCostPanelBody");
      if (!body) return;
      if (!d.ok || !d.data) { body.innerHTML = '<span style="color:#999">加载失败</span>'; return; }
      var c = d.data;
      function money(v) { return v != null ? "¥" + Number(v).toLocaleString() : '<span style="color:#A8A29E">待回填</span>'; }
      function row(k, v) { return '<tr><td style="padding:6px 10px;color:#57534E;border-bottom:1px solid #E7E5E4">' + k + '</td><td style="padding:6px 10px;text-align:right;border-bottom:1px solid #E7E5E4;font-variant-numeric:tabular-nums">' + v + '</td></tr>'; }
      var html = '<table style="width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E7E5E4;border-radius:8px;overflow:hidden">'
        + row("Boosting 预算", money(c.boosting_budget))
        + row("进线 Inquiry", (c.inquiry || 0).toLocaleString())
        + row("点击 Clicks", (c.clicks || 0).toLocaleString())
        + row("WeCom 新增", (c.wecom_add || 0).toLocaleString())
        + row("CPL（预算/进线）", money(c.cpl))
        + row("CPC（预算/点击）", money(c.cpc))
        + row("Cost-per-WeCom", money(c.cost_per_wecom))
        + '</table>';
      if ((c.manual_pending || []).length) {
        html += '<div style="font-size:11px;color:#A8A29E;margin-top:8px">口径：DFS Y26 H1；' + c.manual_pending.join("、") + ' 待手动回填（下方手动回填面板），未填不估 0</div>';
      }
      body.innerHTML = html;
    }).catch(function () {});
  }

  // KM-03 高/低产出 KOS 健康画像（复用 /api/kos/tier 返回，不新增请求；无 manual 数据时显式待回填）
  function renderKosHealth(tierData) {
    if (!tierData) return;
    ensureKosPanel("kosHealthPanel", "高 / 低产出 KOS 健康画像");
    var body = document.getElementById("kosHealthPanelBody");
    if (!body) return;
    var p = tierData.profile || {};
    var hi = p.high_avg || {}, lo = p.low_avg || {};
    function cell(v) { return v != null ? v : "--"; }
    function head(t) { return '<th style="padding:6px 10px;text-align:left;color:#78716C;font-weight:500;border-bottom:1px solid #E7E5E4;font-size:11.5px">' + t + '</th>'; }
    function trR(label, a, b) { return '<tr><td style="padding:6px 10px;color:#57534E;border-bottom:1px solid #E7E5E4">' + label + '</td><td style="padding:6px 10px;text-align:right;border-bottom:1px solid #E7E5E4;font-variant-numeric:tabular-nums">' + cell(a) + '</td><td style="padding:6px 10px;text-align:right;border-bottom:1px solid #E7E5E4;font-variant-numeric:tabular-nums">' + cell(b) + '</td></tr>'; }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E7E5E4;border-radius:8px;overflow:hidden">'
      + '<tr>' + head("均值指标") + head("高产出") + head("低产出") + '</tr>'
      + trR("月均笔记数", hi.note_count, lo.note_count)
      + trR("WeCom 新增", hi.wecom, lo.wecom)
      + trR("Boosting 投入(¥)", hi.boosting, lo.boosting)
      + '</table>';
    html += '<div style="font-size:11px;color:#A8A29E;margin-top:8px">含手动 Sales/WeCom 数据的 KOS：' + (p.manual_data_kos || 0) + ' 个' + ((p.manual_data_kos || 0) === 0 ? '；回填后生成画像对比（Sales≥1万为高产出，DFS 口径）' : '') + '</div>';
    body.innerHTML = html;
  }

  // KM-04/05 KOC 分层（Gold/Silver/Bronze 阈值对齐 DFS；判定实时调 /api/kos/koc-tier，不前端硬算）
  function loadKosKoc() {
    ensureKosPanel("kosKocPanel", "KOC 分层激励（Gold / Silver / Bronze）");
    var body = document.getElementById("kosKocPanelBody");
    if (!body) return;
    function tierTag(t) {
      var map = { gold: "#1C1917", silver: "#44403C", bronze: "#78716C", none: "#A8A29E" };
      var label = { gold: "Gold", silver: "Silver", bronze: "Bronze", none: "未达标" };
      return '<span style="display:inline-block;padding:2px 10px;border-radius:999px;background:' + (map[t] || "#A8A29E") + ';color:#fff;font-size:11px">' + (label[t] || t) + '</span>';
    }
    body.innerHTML =
      '<table style="width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E7E5E4;border-radius:8px;overflow:hidden;margin-bottom:12px">'
      + '<tr><th style="padding:6px 10px;text-align:left;color:#78716C;font-weight:500;border-bottom:1px solid #E7E5E4;font-size:11.5px">层级</th><th style="padding:6px 10px;text-align:left;color:#78716C;font-weight:500;border-bottom:1px solid #E7E5E4;font-size:11.5px">达标（24h / 7d 任一）</th></tr>'
      + '<tr><td style="padding:6px 10px;border-bottom:1px solid #E7E5E4">' + tierTag("gold") + '</td><td style="padding:6px 10px;border-bottom:1px solid #E7E5E4;color:#57534E">24h ≥100 互动 或 7d ≥500</td></tr>'
      + '<tr><td style="padding:6px 10px;border-bottom:1px solid #E7E5E4">' + tierTag("silver") + '</td><td style="padding:6px 10px;border-bottom:1px solid #E7E5E4;color:#57534E">24h ≥50 或 7d ≥100</td></tr>'
      + '<tr><td style="padding:6px 10px">' + tierTag("bronze") + '</td><td style="padding:6px 10px;color:#57534E">达标参与（防流失参与奖）</td></tr>'
      + '</table>'
      + '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12.5px">'
      + '<span>实时判定：</span>'
      + '<input id="kocI24" type="number" min="0" placeholder="24h互动" style="width:90px;padding:5px 8px;border:1px solid #D6D3D1;border-radius:6px">'
      + '<input id="kocI7d" type="number" min="0" placeholder="7d互动" style="width:90px;padding:5px 8px;border:1px solid #D6D3D1;border-radius:6px">'
      + '<button onclick="kosJudgeTier()" style="padding:5px 14px;background:#1C1917;color:#fff;border:none;border-radius:6px;font-size:12.5px;cursor:pointer">判定</button>'
      + '<span id="kocJudgeOut"></span></div>'
      + '<div style="font-size:11px;color:#A8A29E;margin-top:8px">Campaign 复盘聚合（KOC数/曝光/High-intent）在选定活动 KOC 数据后接入，不做无数据聚合</div>';
  }
  window.kosJudgeTier = function () {
    var i24 = document.getElementById("kocI24").value || 0;
    var i7d = document.getElementById("kocI7d").value || 0;
    var out = document.getElementById("kocJudgeOut");
    if (out) out.textContent = "判定中…";
    api("/api/kos/koc-tier?interactions_24h=" + encodeURIComponent(i24) + "&interactions_7d=" + encodeURIComponent(i7d)).then(function (d) {
      if (!out) return;
      if (!d.ok || !d.data) { out.textContent = "判定失败"; return; }
      var t = d.data.tier;
      var labels = { gold: "Gold（金牌）", silver: "Silver（银牌）", bronze: "Bronze（参与）", none: "未达标 none" };
      out.innerHTML = '<b style="color:#1C1917">' + (labels[t] || t) + '</b>';
    }).catch(function () { if (out) out.textContent = "判定失败"; });
  };

  function loadKosRoi() {
    ensureKosPanel("kosRoiPanel", "多渠道 ROI 对比");
    api("/api/kos/channel-roi").then(function (d) {
      if (!d.ok || !d.data) return;
      var body = document.getElementById("kosRoiPanelBody");
      if (!body) return;
      var rows = (d.data.channels || []).map(function (c) {
        var cpl = c.cpl != null ? "¥" + c.cpl : "--";
        var ref = c.reference_cpl ? "基准 ¥" + c.reference_cpl + (c.vs_reference_pct != null ? " · " + c.vs_reference_pct + "%" : "") : "待回填";
        return '<div style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;font-size:12px"><span>' + (c.label || c.name) + '</span><b>CPL ' + cpl + '</b></div><div style="font-size:11px;color:#999">预算 ¥' + (c.budget || 0) + ' · 进线 ' + (c.inquiry || 0) + ' · ' + ref + '</div></div>';
      }).join("");
      body.innerHTML = rows || '<span style="color:#999">暂无数据（请回填 Boosting/进线）</span>';
    }).catch(function () {});
  }

  // KOS 生命周期分布（overview.by_lifecycle：发现/活跃/成长/稳定/爆发/沉寂）
  function loadKosLifecycle() {
    api("/api/kos/overview").then(function (d) {
      if (!d.ok || !d.data) return;
      var lc = d.data.by_lifecycle || {};
      ensureKosPanel("kosLifecyclePanel", "KOS 生命周期分布");
      var body = document.getElementById("kosLifecyclePanelBody");
      if (!body) return;
      var stages = [["discovered","发现"],["growing","成长"],["active","活跃"],["stable","稳定"]];
      var total = 0; stages.forEach(function(st){ total += (lc[st[0]]||0); });
      body.innerHTML = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">' +
        stages.map(function(st){
          var v = lc[st[0]]||0; var pct = total? Math.round(v*100/total):0;
          return '<div style="background:#f9f9f9;padding:10px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">'+v+'</div><div style="font-size:11px;color:#999">'+st[1]+' · '+pct+'%</div></div>';
        }).join('') + '</div>';
    }).catch(function () {});
  }

  // 投流候选：自然表现→投流评分；无真实转化/成本数据时不生成ROI
  function loadKosAdCandidates() {
    ensureKosPanel("kosAdPanel", "投流候选（自然表现 → 投流评分，无真实转化不生成 ROI）");
    api("/api/kos/ad-candidates").then(function (d) {
      var body = document.getElementById("kosAdPanelBody");
      if (!body) return;
      var cands = d.candidates || [];
      if (!cands.length) { body.innerHTML = '<span style="color:#999">暂无候选</span>'; return; }
      var groups = {"推荐投流":[], "建议观察":[], "不建议投流":[]};
      cands.forEach(function(c){ (groups[c.recommendation]||groups["建议观察"]).push(c); });
      body.innerHTML = Object.keys(groups).map(function(g){
        var list = groups[g]; if(!list.length) return "";
        var color = g==="推荐投流"?"#16a34a":(g==="建议观察"?"#d97706":"#9ca3af");
        return '<div style="margin-bottom:10px"><div style="font-size:12px;font-weight:600;color:'+color+';margin-bottom:6px">'+g+'（'+list.length+'）</div>' +
          list.slice(0,8).map(function(c){
            var eng = (c.engagement||0);
            return '<div style="display:flex;justify-content:space-between;gap:8px;padding:6px 0;border-bottom:1px solid #f5f5f5;font-size:12px"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+(c.title||"")+' <span style="color:#999">@'+(c.author||"")+'</span></span><b style="flex-shrink:0">'+(c.ad_score||0)+'分 · 互动'+(eng?eng.toLocaleString():"0")+'</b></div>';
          }).join('') + '</div>';
      }).join('');
    }).catch(function () {});
  }

  // 评论回复中心：分类/情绪/风险/是否回复；高风险 NO_REPLY 禁止AI自动回复
  function loadKosComments() {
    ensureKosPanel("kosCommentsPanel", "评论回复中心（自动分类 · 情绪 · 风险 · 高风险 NO_REPLY 转人工）");
    api("/api/kos/comments?limit=50").then(function (d) {
      var body = document.getElementById("kosCommentsPanelBody");
      if (!body) return;
      var cs = d.comments || [];
      if (!cs.length) { body.innerHTML = '<span style="color:#999">暂无评论</span>'; return; }
      var cat = d.by_category || {};
      var catBar = Object.keys(cat).map(function(k){ return '<span style="display:inline-block;padding:2px 8px;background:#f0f0f0;border-radius:10px;font-size:11px;margin:0 4px 4px 0">'+k+' '+cat[k]+'</span>'; }).join('');
      body.innerHTML = '<div style="margin-bottom:10px">'+catBar+'</div>' +
        cs.slice(0,15).map(function(c){
          var risk = c.risk_level || "";
          var noReply = (c.should_reply===false || c.should_reply==="false" || c.should_reply==="False" || c.should_reply===0);
          var replyTag = noReply ? '<span style="color:#dc2626;font-size:10px">NO_REPLY</span>' : (c.should_reply?'<span style="color:#16a34a;font-size:10px">建议回复</span>':'');
          return '<div style="padding:8px 0;border-bottom:1px solid #f5f5f5;font-size:12px"><div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:2px"><b>@'+(c.author_nickname||"匿名")+'</b><span style="color:#999;font-size:10px">'+(c.category||"")+' · '+(c.sentiment||"")+' '+replyTag+'</span></div><div style="color:#444">'+(c.content||"")+'</div>'+(c.reply_suggestion?'<div style="margin-top:4px;padding:6px 8px;background:#f7f7f5;border-radius:6px;color:#666">回复建议: '+c.reply_suggestion+'</div>':"")+'</div>';
        }).join('');
    }).catch(function () {});
  }

  // KM-02/04：手动回填入口（WeCom / Sales / Boosting / 进线 / 点击）→ /api/kos/manual
  function loadKosManualFill() {
    ensureKosPanel("kosManualPanel", "手动回填（KM-02：WeCom / Sales / Boosting / 进线）");
    api("/api/kos/list?limit=200&sort_by=kos_score").then(function (d) {
      if (!d.ok) return;
      var body = document.getElementById("kosManualPanelBody");
      if (!body) return;
      var opts = (d.profiles || []).map(function (p) {
        return '<option value="' + (p.author_id || "") + '">' + (p.author_nickname || p.author_id || "未知") + '</option>';
      }).join("");
      body.innerHTML =
        '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:end">'
        + '<select id="kosManualId" style="flex:1;min-width:160px;padding:8px;border:1px solid #e5e5e5;border-radius:6px">' + opts + '</select>'
        + '<input id="kosManualWecom" type="number" placeholder="WeCom新增" style="width:100px;padding:8px;border:1px solid #e5e5e5;border-radius:6px">'
        + '<input id="kosManualSales" type="number" placeholder="销售(¥)" style="width:110px;padding:8px;border:1px solid #e5e5e5;border-radius:6px">'
        + '<input id="kosManualBudget" type="number" placeholder="Boosting(¥)" style="width:110px;padding:8px;border:1px solid #e5e5e5;border-radius:6px">'
        + '<input id="kosManualInquiry" type="number" placeholder="进线" style="width:76px;padding:8px;border:1px solid #e5e5e5;border-radius:6px">'
        + '<input id="kosManualClicks" type="number" placeholder="点击" style="width:76px;padding:8px;border:1px solid #e5e5e5;border-radius:6px">'
        + '<button onclick="kosSubmitManual()" style="padding:8px 16px;background:#171717;color:#fff;border:none;border-radius:6px;cursor:pointer">保存回填</button>'
        + '</div>'
        + '<div id="kosManualResult" style="margin-top:8px;font-size:12px;color:#27ae60"></div>';
    }).catch(function () {});
  }

  function kosSubmitManual() {
    var id = document.getElementById("kosManualId");
    if (!id || !id.value) { alert("请先选择 KOS"); return; }
    function num(x) { var v = document.getElementById(x); return v && v.value !== "" ? Number(v.value) : undefined; }
    var payload = { kos_id: id.value };
    var w = num("kosManualWecom"), s = num("kosManualSales"), b = num("kosManualBudget"), i = num("kosManualInquiry"), c = num("kosManualClicks");
    if (w !== undefined) payload.wecom_add = w;
    if (s !== undefined) payload.sales_amount = s;
    if (b !== undefined) payload.boosting_budget = b;
    if (i !== undefined) payload.inquiry = i;
    if (c !== undefined) payload.clicks = c;
    fetch("/api/kos/manual", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    }).then(function (r) { return r.json(); }).then(function (d) {
      var el = document.getElementById("kosManualResult");
      if (el) el.innerHTML = d.ok ? ("已保存：" + JSON.stringify(d.data.entry)) : ("保存失败：" + (d.error || ""));
    }).catch(function (e) { var el = document.getElementById("kosManualResult"); if (el) el.innerHTML = "保存失败：" + e; });
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
    var tierColor = { S: "#1C1917", A: "#44403C", B: "#78716C", C: "#A8A29E" };
    var html = profiles.map(function (p, i) {
      var score = (p.kos_score || 0).toFixed(1);
      var tier = p.kos_tier || "C";
      var color = tierColor[tier] || "#A8A29E";
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

  // KOS详情弹窗：概览/归因/内容基因/评论 4 Tab
  function kosShowDetail(authorId) {
    if (!authorId) return;
    api("/api/kos/detail?author_id=" + encodeURIComponent(authorId)).then(function (d) {
      if (!d.ok || !d.data) { alert("加载详情失败"); return; }
      var p = d.data;
      var notes = (p.notes || []).slice(0, 5).map(function (n) {
        return '<li style="padding:6px 0;border-bottom:1px solid #f5f5f5"><strong>' + (n.title || n.note_id || "") + '</strong><br><span style="font-size:11px;color:#999">点赞 ' + (n.likes || 0) + ' · 评论 ' + (n.comments || 0) + ' · ' + (n.publish_datetime || "") + '</span></li>';
      }).join("");
      var html = '<div style="padding:16px 20px">'
        + '<h3 style="margin:0 0 4px">' + (p.author_nickname || "") + '</h3>'
        + '<p style="color:#666;margin:0 0 12px;font-size:13px">层级: <b>' + (p.kos_tier || "") + '</b> · 评分: <b>' + ((p.kos_score || 0).toFixed(1)) + '</b> · 生命周期: ' + (p.lifecycle_stage || "") + '</p>'
        + '<div style="display:flex;gap:4px;border-bottom:1px solid #f0f0f0;margin-bottom:12px">'
        + '<button class="kos-tab active" onclick="kosSwitchTab(this,\'overview\')" style="padding:8px 14px;background:none;border:none;border-bottom:2px solid #171717;cursor:pointer;font-size:13px;font-weight:500">概览</button>'
        + '<button class="kos-tab" onclick="kosSwitchTab(this,\'attribution\')" data-author="' + authorId + '" style="padding:8px 14px;background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;font-size:13px;color:#999">归因分析</button>'
        + '<button class="kos-tab" onclick="kosSwitchTab(this,\'dna\')" data-author="' + authorId + '" style="padding:8px 14px;background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;font-size:13px;color:#999">内容基因</button>'
        + '<button class="kos-tab" onclick="kosSwitchTab(this,\'reply\')" data-author="' + authorId + '" style="padding:8px 14px;background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;font-size:13px;color:#999">评论回复</button>'
        + '</div>'
        + '<div class="kos-tab-panel" data-tab="overview">'
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px">'
        + '<div style="background:#f9f9f9;padding:8px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (p.note_count || 0) + '</div><div style="font-size:11px;color:#999">笔记数</div></div>'
        + '<div style="background:#f9f9f9;padding:8px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (p.avg_engagement || 0) + '</div><div style="font-size:11px;color:#999">总互动</div></div>'
        + '<div style="background:#f9f9f9;padding:8px;border-radius:6px;text-align:center"><div style="font-size:18px;font-weight:600">' + (p.avg_quality || 0).toFixed(1) + '</div><div style="font-size:11px;color:#999">平均质量</div></div>'
        + '</div>'
        + '<h4 style="margin:0 0 8px;font-size:14px">最近笔记</h4><ul style="list-style:none;padding:0;margin:0">' + (notes || '<li>暂无</li>') + '</ul>'
        + '<div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">'
        + '<button onclick="kosGenOutreach(\'' + authorId + '\')" style="padding:8px 16px;background:#171717;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px">生成触达文案</button>'
        + '<button onclick="kosGenReward(\'' + authorId + '\')" style="padding:8px 16px;background:#f0f0f0;border:none;border-radius:6px;cursor:pointer;font-size:13px">奖励积分</button>'
        + '</div></div>'
        + '<div class="kos-tab-panel" data-tab="attribution" style="display:none"><div id="kosAttrContent" style="font-size:13px;color:#999">点击加载归因分析</div></div>'
        + '<div class="kos-tab-panel" data-tab="dna" style="display:none"><div id="kosDnaContent" style="font-size:13px;color:#999">点击加载内容基因</div></div>'
        + '<div class="kos-tab-panel" data-tab="reply" style="display:none">'
        + '<div style="margin-bottom:12px"><textarea id="kosReplyInput" placeholder="粘贴用户评论，AI生成回复建议（高风险自动NO_REPLY转人工）" style="width:100%;height:80px;padding:10px;border:1px solid #e5e5e5;border-radius:8px;font-size:13px;resize:vertical;box-sizing:border-box"></textarea></div>'
        + '<button onclick="kosGenerateReply()" style="padding:8px 16px;background:#171717;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px">生成回复建议</button>'
        + '<div id="kosReplyResult" style="margin-top:12px"></div>'
        + '</div></div>';
      showModal("KOS 详情", html);
    }).catch(function (e) { alert("加载详情失败: " + e); });
  }

  function kosSwitchTab(btn, tabName) {
    var modal = btn.closest("div[style*=fixed]") || document.body;
    modal.querySelectorAll(".kos-tab").forEach(function (t) {
      t.style.borderBottomColor = "transparent"; t.style.color = "#999"; t.classList.remove("active");
    });
    btn.style.borderBottomColor = "#171717"; btn.style.color = "#171717"; btn.classList.add("active");
    modal.querySelectorAll(".kos-tab-panel").forEach(function (p) {
      p.style.display = p.dataset.tab === tabName ? "block" : "none";
    });
    var authorId = btn.dataset.author;
    if (tabName === "attribution" && authorId) kosLoadAttribution(authorId);
    if (tabName === "dna" && authorId) kosLoadContentDna(authorId);
  }

  function kosLoadAttribution(authorId) {
    var el = document.getElementById("kosAttrContent");
    if (!el) return;
    el.innerHTML = "加载中...";
    api("/api/kos/attribution?author_id=" + encodeURIComponent(authorId)).then(function (d) {
      if (!d.ok) { el.innerHTML = "加载失败: " + (d.error || ""); return; }
      var a = d.data || d;
      var bd = a.breakdown || {};
      var dims = [["内容贡献","content"],["互动贡献","interaction"],["传播贡献","reach"],["事件贡献","event"],["品牌贡献","brand"],["需求贡献","demand"],["商业贡献","commercial"],["风险扣分","risk"]];
      var rows = dims.map(function (pair) {
        var label = pair[0], key = pair[1], val = bd[key] || 0;
        var pct = Math.min(100, Math.max(0, val));
        var color = key === "risk" ? "#e74c3c" : "#171717";
        return '<div style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px"><span>' + label + '</span><b>' + (typeof val === "number" ? val.toFixed(1) : val) + '</b></div><div style="height:6px;background:#f0f0f0;border-radius:3px;overflow:hidden"><div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:3px"></div></div></div>';
      }).join("");
      el.innerHTML = '<div style="margin-bottom:12px;padding:12px;background:#f7f7f5;border-radius:8px;text-align:center"><div style="font-size:28px;font-weight:600">' + ((a.total_attribution_score || 0).toFixed(1)) + '</div><div style="font-size:11px;color:#999">综合归因分</div></div>'
        + '<div style="font-size:12px;color:#666;margin-bottom:8px">笔记 ' + (a.note_count || 0) + ' · 总互动 ' + (a.total_interactions || 0) + ' · 多触点时间衰减归因</div>' + rows;
    }).catch(function (e) { el.innerHTML = "加载失败: " + e; });
  }

  function kosLoadContentDna(authorId) {
    var el = document.getElementById("kosDnaContent");
    if (!el) return;
    el.innerHTML = "加载中...";
    api("/api/kos/content-dna?author_id=" + encodeURIComponent(authorId)).then(function (d) {
      if (!d.ok) { el.innerHTML = "加载失败: " + (d.error || ""); return; }
      var dna = d.data || d;
      function barMap(obj) {
        var keys = Object.keys(obj || {});
        if (!keys.length) return "<span style='color:#999'>暂无数据</span>";
        return keys.map(function (k) {
          var v = obj[k]; var pct = typeof v === "number" && v <= 1 ? (v * 100).toFixed(0) : v;
          return '<div style="margin-bottom:6px"><div style="display:flex;justify-content:space-between;font-size:12px"><span>' + k + '</span><b>' + pct + '%</b></div><div style="height:5px;background:#f0f0f0;border-radius:3px"><div style="height:100%;width:' + pct + '%;background:#171717;border-radius:3px"></div></div></div>';
        }).join("");
      }
      function tagList(arr) {
        if (!arr || !arr.length) return "<span style='color:#999'>暂无</span>";
        return arr.map(function (t) { return '<span style="display:inline-block;padding:2px 8px;background:#f7f7f5;border-radius:4px;font-size:11px;margin:2px">' + t + '</span>'; }).join("");
      }
      el.innerHTML = '<div style="font-size:12px;color:#666;margin-bottom:10px">样本量: ' + (dna.sample_size || 0) + ' 篇笔记</div>'
        + '<h4 style="font-size:13px;margin:0 0 6px">情绪分布</h4><div style="margin-bottom:12px">' + barMap(dna.emotion_distribution) + '</div>'
        + '<h4 style="font-size:13px;margin:0 0 6px">场景分布</h4><div style="margin-bottom:12px">' + barMap(dna.scene_distribution) + '</div>'
        + '<h4 style="font-size:13px;margin:0 0 6px">标题结构</h4><div style="margin-bottom:12px">' + barMap(dna.title_style_distribution) + '</div>'
        + '<h4 style="font-size:13px;margin:0 0 6px">品牌提及</h4><div style="margin-bottom:12px">' + tagList(dna.brands_mentioned) + '</div>'
        + '<h4 style="font-size:13px;margin:0 0 6px">用户需求信号</h4><div>' + tagList(dna.demand_signals) + '</div>';
    }).catch(function (e) { el.innerHTML = "加载失败: " + e; });
  }

  function kosGenerateReply() {
    var input = document.getElementById("kosReplyInput");
    var result = document.getElementById("kosReplyResult");
    if (!input || !input.value.trim()) { alert("请先粘贴评论内容"); return; }
    result.innerHTML = "生成中...";
    fetch("/api/kos/reply/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ comment_text: input.value.trim(), brand_name: "海南中免/CDF" })
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) { result.innerHTML = '<span style="color:#e74c3c">生成失败: ' + (d.error || "") + '</span>'; return; }
      var r = d.data || d;
      var actionColor = r.action === "NO_REPLY" ? "#e74c3c" : "#27ae60";
      result.innerHTML = '<div style="padding:12px;border:1px solid #e5e5e5;border-radius:8px">'
        + '<div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap">'
        + '<span style="padding:2px 8px;background:#f7f7f5;border-radius:4px;font-size:11px">分类: ' + (r.category || "") + '</span>'
        + '<span style="padding:2px 8px;background:' + actionColor + '20;color:' + actionColor + ';border-radius:4px;font-size:11px;font-weight:500">' + (r.action || "") + '</span>'
        + (r.risk_level ? '<span style="padding:2px 8px;background:#fff3cd;border-radius:4px;font-size:11px">风险: ' + r.risk_level + '</span>' : "")
        + '</div>'
        + (r.reason ? '<p style="font-size:12px;color:#e74c3c;margin:0 0 8px">' + r.reason + '</p>' : "")
        + (r.suggested_action ? '<p style="font-size:12px;color:#666;margin:0 0 8px">建议动作: ' + r.suggested_action + '</p>' : "")
        + (r.suggested_reply ? '<div style="background:#f7f7f5;padding:10px;border-radius:6px;font-size:13px;line-height:1.6;white-space:pre-wrap">' + r.suggested_reply + '</div>' : "")
        + (r.auto_reply === false ? '<p style="font-size:11px;color:#999;margin:8px 0 0">默认仅生成建议，需人工确认后发送，高风险评论禁止AI自动回复</p>' : "")
        + '</div>';
    }).catch(function (e) { result.innerHTML = '<span style="color:#e74c3c">生成失败: ' + e + '</span>'; });
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
    modal.style.cssText = "background:#fff;border-radius:12px;max-width:540px;width:92%;max-height:82vh;overflow-y:auto;position:relative";
    modal.innerHTML = '<div style="padding:13px 18px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center"><h3 style="margin:0;font-size:15px">' + title + '</h3><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:none;border:none;font-size:19px;cursor:pointer;color:#999;line-height:1">×</button></div>' + html;
    overlay.appendChild(modal);
    overlay.onclick = function (e) { if (e.target === overlay) overlay.remove(); };
    document.body.appendChild(overlay);
  }

  // 暴露到全局
  window.kosShowDetail = kosShowDetail;
  window.kosGenOutreach = kosGenOutreach;
  window.kosGenReward = kosGenReward;
  window.kosFilterTier = kosFilterTier;
  window.kosSwitchTab = kosSwitchTab;
  window.kosLoadAttribution = kosLoadAttribution;
  window.kosLoadContentDna = kosLoadContentDna;
  window.kosGenerateReply = kosGenerateReply;

  // 页面进入 KOS 时加载
  document.addEventListener("DOMContentLoaded", function () {
    function loadAllKos() {
      loadKosStats();
      loadKosList("");
      loadKosFunnel();
      loadKosCost();
      loadKosKoc();
      loadKosRoi();
      loadKosLifecycle();
      loadKosAdCandidates();
      loadKosComments();
      loadKosManualFill();
    }
    // 独立 /kos 页面：存在 #page-kos 容器则立即加载
    if (document.getElementById("page-kos")) {
      loadAllKos();
    }
    // 监听 navigateTo 进入 kos 页面
    var origNavigate = window.navigateTo;
    if (origNavigate) {
      window.navigateTo = function (page) {
        origNavigate(page);
        if (page === "kos") {
          loadAllKos();
        }
      };
    }
  });

// KOS 运营操作辅助（kos_ops/kos_paid API · HCG 门控）——挂到 window 供 SPA 面板调用
window.recordKosOp = function () {
  var aid = document.getElementById("opAuthorId").value.trim();
  var action = document.getElementById("opAction").value;
  var out = document.getElementById("opResult");
  if (!aid) { out.textContent = "请输入 author_id"; return; }
  api("/api/kos/operation", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author_id: aid, action: action, actor: "zachary" }) })
    .then(function (d) { out.textContent = d.ok ? ("已记录: " + action + " → " + d.lifecycle_stage) : (d.error || "失败"); })
    .catch(function (e) { out.textContent = "错误: " + e.message; });
};
window.saveKosLead = function () {
  var aid = document.getElementById("leadAuthorId").value.trim();
  var email = document.getElementById("leadEmail").value.trim();
  var out = document.getElementById("leadResult");
  if (!aid) { out.textContent = "请输入 author_id"; return; }
  api("/api/kos/lead", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author_id: aid, email: email, actor: "zachary" }) })
    .then(function (d) { out.textContent = d.ok ? "留资已保存" : (d.error || "失败"); })
    .catch(function (e) { out.textContent = "错误: " + e.message; });
};
window.confirmKosCoop = function () {
  var aid = document.getElementById("leadAuthorId").value.trim();
  var out = document.getElementById("leadResult");
  if (!aid) { out.textContent = "请输入 author_id"; return; }
  api("/api/kos/cooperation/confirm", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author_id: aid, confirmed_by: "zachary", quote: 0, budget: 0 }) })
    .then(function (d) { var h = d.hcg || {}; out.textContent = d.ok ? ("合作确认已登记(HCG " + h.status + " 待人工审批)") : (d.error || "失败"); })
    .catch(function (e) { out.textContent = "错误: " + e.message; });
};
window.inviteKosEmail = function () {
  var aid = document.getElementById("leadAuthorId").value.trim();
  var out = document.getElementById("leadResult");
  if (!aid) { out.textContent = "请输入 author_id"; return; }
  api("/api/kos/email/invitation", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author_id: aid, subject: "KOS 合作邀约", body: "您好，邀请合作", actor: "zachary" }) })
    .then(function (d) { var h = d.hcg || {}; out.textContent = d.ok ? ("邀约已创建(HCG " + h.status + "，未发送)") : (d.error || "失败"); })
    .catch(function (e) { out.textContent = "错误: " + e.message; });
};

})();