/* Z-Brand-Core 多品牌中心 Brand Hub JS
 * 品牌→地区→门店 层级导航
 * 品牌切换器 + 品牌网格 + 品牌Dashboard
 */
(function () {
  "use strict";

  // 品牌配置（与后端 subject_rules.BRAND_PROFILES 同步）
  var BRANDS = {
    guangzhou_taikoo_hui: {
      name: "广州太古汇", region: "广州", country: "中国", store_type: "购物中心",
      color: "#171717", icon: "太", kos_count: 900, note_count: 1052, active: true
    },
    hainan_cdf: {
      name: "海南中免/CDF", region: "海南", country: "中国", store_type: "免税城",
      color: "#c0392b", icon: "CDF", kos_count: 0, note_count: 0, active: false
    },
    hongkong_dfs: {
      name: "香港DFS免税店", region: "香港", country: "中国", store_type: "DFS免税店",
      color: "#e74c3c", icon: "HK", kos_count: 0, note_count: 0, active: false,
      stores: ["尖沙咀DFS T广场", "铜锣湾DFS", "中环DFS"]
    },
    macau_dfs: {
      name: "澳门DFS免税店", region: "澳门", country: "中国", store_type: "DFS免税店",
      color: "#f39c12", icon: "MO", kos_count: 0, note_count: 0, active: false,
      stores: ["路氹DFS T广场", "新濠天地DFS", "澳门半岛DFS"]
    },
    seoul_dfs: {
      name: "首尔DFS免税店", region: "首尔", country: "韩国", store_type: "DFS免税店",
      color: "#3498db", icon: "KR", kos_count: 0, note_count: 0, active: false,
      stores: ["明洞DFS", "乐天免税店", "新罗免税店", "东大门DFS"]
    },
    tokyo_dfs: {
      name: "东京DFS免税店", region: "东京", country: "日本", store_type: "DFS免税店",
      color: "#9b59b6", icon: "JP", kos_count: 0, note_count: 0, active: false,
      stores: ["银座DFS", "新宿DFS", "冲绳DFS T广场"]
    }
  };

  var currentBrand = "guangzhou_taikoo_hui";
  var currentLevel = "brand"; // brand / region / store

  function api(path) {
    return fetch(path, { credentials: "same-origin" }).then(function (r) { return r.json(); });
  }

  // 渲染品牌切换器
  function renderSwitcher() {
    var container = document.getElementById("brandSwitcher");
    if (!container) return;
    var b = BRANDS[currentBrand];
    container.innerHTML =
      '<button class="brand-switcher-btn" onclick="BrandHub.toggleDropdown()">' +
        '<span class="brand-dot" style="background:' + b.color + '"></span>' +
        '<span class="brand-name">' + b.name + '</span>' +
        '<span class="brand-region">' + b.region + ' · ' + b.country + '</span>' +
        '<svg class="chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
      '</button>' +
      '<div class="brand-dropdown">' +
        '<div class="brand-dropdown-header">切换品牌 / Switch Brand</div>' +
        Object.keys(BRANDS).map(function (key) {
          var brand = BRANDS[key];
          return '<div class="brand-dropdown-item' + (key === currentBrand ? ' active' : '') + '" onclick="BrandHub.switchBrand(\'' + key + '\')">' +
            '<span class="brand-dot" style="background:' + brand.color + '"></span>' +
            '<div class="brand-info">' +
              '<div class="brand-info-name">' + brand.name + '</div>' +
              '<div class="brand-info-meta">' + brand.region + ' · ' + brand.country + ' · ' + brand.store_type + '</div>' +
            '</div>' +
            '<svg class="brand-check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>' +
          '</div>';
        }).join('') +
      '</div>';
  }

  function toggleDropdown() {
    var el = document.getElementById("brandSwitcher");
    if (el) el.classList.toggle("open");
  }

  function closeDropdown() {
    var el = document.getElementById("brandSwitcher");
    if (el) el.classList.remove("open");
  }

  // 点击外部关闭下拉
  document.addEventListener("click", function (e) {
    var el = document.getElementById("brandSwitcher");
    if (el && !el.contains(e.target)) el.classList.remove("open");
  });

  // 渲染品牌网格
  function renderBrandGrid() {
    var container = document.getElementById("brandGrid");
    if (!container) return;
    container.innerHTML = Object.keys(BRANDS).map(function (key) {
      var b = BRANDS[key];
      return '<div class="brand-card" data-brand="' + key + '" onclick="BrandHub.openBrand(\'' + key + '\')">' +
        '<div class="brand-card-header">' +
          '<div class="brand-card-icon" style="background:' + b.color + '">' + b.icon + '</div>' +
          (b.active ? '<span class="brand-card-badge">已激活</span>' : '<span class="brand-card-badge">待采集</span>') +
        '</div>' +
        '<h3 class="brand-card-name">' + b.name + '</h3>' +
        '<div class="brand-card-meta">' +
          '<span>' + xicon('pin') + b.region + '</span>' +
          '<span>' + xicon('building') + b.store_type + '</span>' +
          '<span>' + xicon('globe') + b.country + '</span>' +
        '</div>' +
        '<div class="brand-card-stats">' +
          '<div class="brand-card-stat"><div class="brand-card-stat-value">' + b.kos_count + '</div><div class="brand-card-stat-label">KOS</div></div>' +
          '<div class="brand-card-stat"><div class="brand-card-stat-value">' + b.note_count + '</div><div class="brand-card-stat-label">笔记</div></div>' +
          '<div class="brand-card-stat"><div class="brand-card-stat-value">' + (b.stores ? b.stores.length : 1) + '</div><div class="brand-card-stat-label">门店</div></div>' +
        '</div>' +
        '<div class="brand-card-cta">进入品牌Dashboard <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div>' +
      '</div>';
    }).join('');
  }

  // 渲染层级导航树
  function renderHierarchy() {
    var container = document.getElementById("brandHierarchy");
    if (!container) return;
    var b = BRANDS[currentBrand];
    var html = '<li class="brand-level" onclick="BrandHub.setLevel(\'brand\')">' +
      '<span class="hier-icon" style="background:' + b.color + ';color:#fff">' + b.icon + '</span>' +
      '<span class="hier-name">' + b.name + '（品牌级）</span>' +
      '<span class="hier-count">' + b.kos_count + ' KOS</span>' +
    '</li>';
    html += '<li class="region-level" onclick="BrandHub.setLevel(\'region\')">' +
      '<span class="hier-icon" style="background:#f0f0f0">' + xicon('pin',12) + '</span>' +
      '<span class="hier-name">' + b.region + '（地区级）</span>' +
      '<span class="hier-count">' + (b.stores ? b.stores.length : 1) + ' 门店</span>' +
    '</li>';
    if (b.stores) {
      b.stores.forEach(function (store, i) {
        html += '<li class="store-level" onclick="BrandHub.setLevel(\'store\',\'' + i + '\')">' +
          '<span class="hier-icon" style="background:#f7f7f5">' + xicon('building',12) + '</span>' +
          '<span class="hier-name">' + store + '</span>' +
          '<span class="hier-count">待采集</span>' +
        '</li>';
      });
    }
    container.innerHTML = html;
  }

  // 渲染面包屑
  function renderBreadcrumb() {
    var container = document.getElementById("brandBreadcrumb");
    if (!container) return;
    var b = BRANDS[currentBrand];
    var html = '<a onclick="BrandHub.goHub()">品牌中心</a><span class="separator">/</span>';
    html += '<a onclick="BrandHub.openBrand(\'' + currentBrand + '\')">' + b.name + '</a>';
    if (currentLevel === "region") {
      html += '<span class="separator">/</span><span class="current">' + b.region + '</span>';
    } else if (currentLevel === "store") {
      html += '<span class="separator">/</span><span class="current">' + b.region + '门店</span>';
    }
    container.innerHTML = html;
  }

  // 渲染品牌Dashboard
  function renderDashboard() {
    var b = BRANDS[currentBrand];
    var iconEl = document.getElementById("brandDashboardIcon");
    var titleEl = document.getElementById("brandDashboardTitle");
    if (iconEl) { iconEl.style.background = b.color; iconEl.textContent = b.icon; }
    if (titleEl) {
      titleEl.innerHTML = '<h2>' + b.name + '</h2><p>' + b.region + ' · ' + b.country + ' · ' + b.store_type + ' · 品牌级Dashboard</p>';
    }
    renderBreadcrumb();
    renderHierarchy();

    // 已激活品牌：广州走原 KOS 全局链路（红线不动）；其他品牌走品牌隔离链路
    if (b.active) {
      if (currentBrand === "guangzhou_taikoo_hui") {
        api("/api/kos/overview").then(function (d) {
          if (d.ok && d.data) {
            var stats = d.data;
            document.getElementById("brandKosTotal").textContent = stats.total || 0;
            document.getElementById("brandKosS").textContent = (stats.by_tier && stats.by_tier.S) || 0;
            document.getElementById("brandKosPotential").textContent = stats.potential || 0;
            document.getElementById("brandNoteTotal").textContent = "1052";
          }
        }).catch(function () {});
        // 加载TOP KOS
        api("/api/kos/ownership?brand=guangzhou_taikoo_hui&limit=5").then(function (d) {
          if (d.ok && d.profiles) {
            renderKosRows(d.profiles, "guangzhou_taikoo_hui", document.getElementById("brandTopKos"));
          }
        }).catch(function () {});
      } else {
        // 非广州品牌：品牌隔离链路（实时聚合，不写 kos_profiles 主表）
        var bd = document.getElementById("brandDashboardContent");
        if (bd) bd.innerHTML = '<div class="brand-empty"><div class="brand-empty-icon">' + xicon('check',30) + '</div><h3>该品牌已激活采集</h3><p>品牌数据已按主体口径隔离入库，KOS 聚合见右栏统计与下方列表。</p></div>';
        refreshBrandData(currentBrand);
      }
    } else {
      // 未激活品牌显示空状态
      var emptyHtml = '<div class="brand-empty"><div class="brand-empty-icon">' + xicon('satellite',30) + '</div><h3>该品牌尚未激活采集</h3><p>点击下方按钮启动采集，数据将自动流入KOS引擎</p><button style="margin-top:16px;padding:10px 24px;background:#171717;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px" onclick="BrandHub.activateBrand(\'' + currentBrand + '\')">启动采集</button></div>';
      var el = document.getElementById("brandDashboardContent");
      if (el) el.innerHTML = emptyHtml;
    }
  }

  function switchBrand(key) {
    currentBrand = key;
    currentLevel = "brand";
    closeDropdown();
    renderSwitcher();
    // 如果在品牌中心，刷新网格；如果在Dashboard，刷新Dashboard
    if (document.getElementById("brandHubSection") && document.getElementById("brandHubSection").classList.contains("active")) {
      renderBrandGrid();
    }
    if (document.getElementById("brandDashboardSection") && document.getElementById("brandDashboardSection").classList.contains("active")) {
      renderDashboard();
    }
  }

  function openBrand(key) {
    currentBrand = key;
    currentLevel = "brand";
    closeDropdown();
    renderSwitcher();
    // 导航到品牌Dashboard
    if (typeof navigateTo === "function") {
      navigateTo("brand-dashboard");
    }
    setTimeout(renderDashboard, 100);
  }

  function goHub() {
    closeDropdown();
    if (typeof navigateTo === "function") navigateTo("brand-hub");
    setTimeout(renderBrandGrid, 100);
  }

  function setLevel(level, storeIndex) {
    currentLevel = level;
    renderBreadcrumb();
    if (level === "store" && storeIndex !== undefined) {
      var b = BRANDS[currentBrand];
      if (b.stores && b.stores[storeIndex]) {
        var el = document.getElementById("brandDashboardTitle");
        if (el) el.innerHTML = '<h2>' + b.stores[storeIndex] + '</h2><p>' + b.name + ' · 门店级Dashboard · 待采集</p>';
      }
    }
  }

  function activateBrand(key) {
    var b = BRANDS[key];
    var btn = document.querySelector("#brandDashboardContent .brand-empty button");
    if (btn) { btn.disabled = true; btn.textContent = "采集中…"; }
    fetch("/api/kos/collect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brand: key })
    }).then(function (r) { return r.json(); }).then(function (d) {
      var msg;
      if (d.ok === false && d.status === "USER_PAUSED") {
        msg = "「" + b.name + "」采集暂未启动：当前处于统一暂停状态（" + (d.reason || "用户暂停") + "）。\n\n请先恢复采集（设置页/采集控制），再重新启动品牌采集。";
      } else if (d.ok === true) {
        msg = "「" + b.name + "」采集完成：本次新增 " + (d.accepted_total || 0) + " 条笔记，品牌累计 " + ((d.collection && d.collection.note_count) || 0) + " 条。\n\n数据已按品牌隔离入库，KOS 聚合将自动刷新。";
      } else {
        msg = "「" + b.name + "」采集启动失败：" + (d.error || "未知错误");
      }
      alert(msg);
      if (btn) { btn.disabled = false; btn.textContent = "启动采集"; }
      if (d.ok === true) {
        b.active = true;
        b.kos_count = (d.collection && d.collection.author_count) || 0;
        b.note_count = (d.collection && d.collection.note_count) || 0;
        renderDashboard();
      } else {
        refreshBrandData(key);
      }
    }).catch(function (e) {
      alert("「" + b.name + "」采集请求失败：" + e);
      if (btn) { btn.disabled = false; btn.textContent = "启动采集"; }
    });
  }

  // 共享 KOS 行渲染：归属徽标 + 互动点 + relevance + 确认归属按钮（纯展示）
  function renderKosRows(profiles, brandKey, el) {
    if (!el || !profiles || !profiles.length) return;
    el.innerHTML = profiles.map(function (p, i) {
      var own = p.ownership || {};
      var rel = p.relevance || {};
      var inter = p.interaction || {};
      var ownLabel = own.ownership_class || "—";
      var ownState = own.ai_status === "VERIFIED"
        ? '<span style="font-size:10px;color:#15803d">✓人工</span>'
        : (own.needs_manual_review ? '<span style="font-size:10px;color:#b45309">待复核</span>' : "");
      var relTxt = rel.relevance_segment || (rel.avg_relevance !== undefined && rel.avg_relevance !== null ? rel.avg_relevance.toFixed(2) : "");
      var interDot = inter.pattern
        ? '<span title="' + inter.pattern + '" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' +
          (inter.pattern === "active" ? "#16a34a" : inter.pattern === "emerging" ? "#d97706" : "#a8a29e") + '"></span>'
        : "";
      var needConfirm = own.needs_manual_review || own.ownership_class === "UNKNOWN" || !own.ai_status;
      var confirmBtn = needConfirm
        ? '<button style="font-size:11px;padding:2px 8px;border:1px solid #d6d3d1;border-radius:6px;background:#fff;color:#44403c;cursor:pointer" onclick="window.KOSConfirmOwnership(\'' + brandKey + '\',\'' + String(p.author_id || "").replace(/[\'"]/g, "") + '\',\'' + String(p.author_nickname || "").replace(/[\'"]/g, "") + '\')">归属</button>'
        : "";
      return '<div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #f5f5f5">' +
        '<span style="width:18px;text-align:center;font-weight:600;color:#999;font-size:12px">' + (i + 1) + '</span>' +
        '<span style="flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px">' + (p.author_nickname || "") + '</span>' +
        '<span style="font-size:11px;padding:2px 6px;border-radius:3px;background:#f7f7f5;color:#666">' + (p.kos_tier || "") + '</span>' +
        interDot +
        (relTxt ? '<span style="font-size:10px;color:#78716c" title="relevance">' + relTxt + '</span>' : "") +
        '<span style="font-size:10px;color:#78716c">' + ownLabel + '</span>' + ownState +
        '<span style="font-weight:600;font-size:12px;width:30px;text-align:right">' + (p.total_engagement || p.kos_score || "") + '</span>' +
        confirmBtn + '</div>';
    }).join('');
  }

  // 品牌隔离 KOS 数据（实时聚合，广州不动）
  function refreshBrandData(key) {
    var b = BRANDS[key];
    if (!b || key === "guangzhou_taikoo_hui") return;
    fetch("/api/kos/brand?brand=" + encodeURIComponent(key) + "&limit=5").then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok || !d.stats) return;
      var st = d.stats;
      var kt = document.getElementById("brandKosTotal");
      var nt = document.getElementById("brandNoteTotal");
      if (kt) kt.textContent = st.author_count || 0;
      if (nt) nt.textContent = st.note_count || 0;
      if ((st.note_count || 0) > 0) {
        var el = document.getElementById("brandTopKos");
        if (el && d.profiles && d.profiles.length) {
          renderKosRows(d.profiles, key, el);
        }
        b.active = true;
        b.kos_count = st.author_count || 0;
        b.note_count = st.note_count || 0;
      }
    }).catch(function () {});
  }

  // KOS 主体归属人工确认（AI 只建议，人工确认后 VERIFIED；黑白灰极简 modal）
  window.KOSConfirmOwnership = function (brand, authorId, nickname) {
    var mask = document.createElement("div");
    mask.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:9999;display:flex;align-items:center;justify-content:center";
    var box = document.createElement("div");
    box.style.cssText = "background:#fff;border:1px solid #e7e5e4;border-radius:12px;padding:20px 24px;width:340px;box-shadow:0 12px 40px rgba(0,0,0,.12);font-family:system-ui,sans-serif;color:#1c1917";
    var types = [
      ["INDEPENDENT_KOL_KOC", "独立KOL/KOC"], ["MEDIA", "媒体/机构"], ["UGC_CONSUMER", "普通用户UGC"],
      ["TARGET_ENTITY_KOS", "主体官方KOS"], ["MERCHANT", "商户"], ["PARTNER", "合作方"], ["UNKNOWN", "未知/待定"]
    ];
    var title = document.createElement("div");
    title.style.cssText = "font-size:15px;font-weight:600;margin-bottom:4px";
    title.textContent = "确认主体归属";
    var sub = document.createElement("div");
    sub.style.cssText = "font-size:12px;color:#78716c;margin-bottom:14px";
    sub.textContent = (nickname || "") + " \u00b7 人工确认后即 VERIFIED（AI 不越权）";
    box.appendChild(title); box.appendChild(sub);
    types.forEach(function (t) {
      var b = document.createElement("button");
      b.type = "button";
      b.style.cssText = "display:block;width:100%;text-align:left;padding:9px 12px;margin:4px 0;border:1px solid #e7e5e4;border-radius:8px;background:#fff;color:#1c1917;font-size:13px;cursor:pointer";
      b.textContent = t[1] + "（" + t[0] + "）";
      b.onclick = function () {
        fetch("/api/kos/ownership/confirm", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ brand: brand, author_id: authorId, ownership_class: t[0], confirmed_by: "zachary" })
        }).then(function (r) { return r.json(); }).then(function (d) {
          document.body.removeChild(mask);
          if (d.ok) { alert("已确认：" + t[1] + "（VERIFIED）"); BrandHub.renderDashboard(); }
          else { alert("确认失败：" + (d.error || "未知错误")); }
        }).catch(function (e) { document.body.removeChild(mask); alert("请求失败：" + e); });
      };
      box.appendChild(b);
    });
    var cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "取消";
    cancel.style.cssText = "margin-top:10px;padding:8px 0;width:100%;border:none;background:#f5f5f4;border-radius:8px;font-size:13px;color:#44403c;cursor:pointer";
    cancel.onclick = function () { document.body.removeChild(mask); };
    box.appendChild(cancel);
    mask.appendChild(box);
    document.body.appendChild(mask);
  };


  // 初始化
  function init() {
    renderSwitcher();
    renderBrandGrid();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // 暴露全局
  window.BrandHub = {
    toggleDropdown: toggleDropdown,
    closeDropdown: closeDropdown,
    switchBrand: switchBrand,
    openBrand: openBrand,
    goHub: goHub,
    setLevel: setLevel,
    activateBrand: activateBrand,
    renderDashboard: renderDashboard,
    BRANDS: BRANDS
  };
})();
