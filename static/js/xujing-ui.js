/* ============================================================
   序境 Xujing · Unified UI Controller v1.0
   页面元数据映射 + 面包屑自动注入 + 页面头部统一
   遵循 Canonical 层级：Product → Subsystem → Module → Page
   ============================================================ */
(function(){
  'use strict';

  // 页面元数据注册表 — Canonical 层级映射
  var PAGE_REGISTRY = {
    // 舆情核心子系统
    'overview':      { subsystem: '舆情核心', module: '概览',     title: '首页概览',     icon: 'home' },
    'monitor':       { subsystem: '舆情核心', module: '监测',     title: '舆情监测',     icon: 'activity' },
    'alerts':        { subsystem: '舆情核心', module: '预警',     title: '风险预警',     icon: 'alert' },
    'events':        { subsystem: '舆情核心', module: '事件',     title: '事件中心',     icon: 'network' },
    'negative':      { subsystem: '舆情核心', module: '确认',     title: '负面确认',     icon: 'shield' },
    'topics':        { subsystem: '舆情核心', module: '话题',     title: '热门话题',     icon: 'trending' },
    'notes':         { subsystem: '舆情核心', module: '笔记',     title: '笔记搜索',     icon: 'search' },
    'analysis':      { subsystem: '舆情核心', module: '分析',     title: '数据分析',     icon: 'bar-chart' },
    'brands':        { subsystem: '舆情核心', module: '品牌',     title: '品牌业态',     icon: 'grid' },
    'official':      { subsystem: '舆情核心', module: '官方',     title: '官方动态',     icon: 'radio' },
    // 案例与知识子系统
    'swire':         { subsystem: '案例知识', module: '案例库',   title: '品牌营销案例库', icon: 'layers' },
    'cases':         { subsystem: '案例知识', module: '案例库',   title: '全网案例库',   icon: 'book' },
    'case-analysis': { subsystem: '案例知识', module: '深度拆解', title: '案例深度拆解', icon: 'file-text' },
    'knowledge-base':{ subsystem: '案例知识', module: '知识库',   title: '品牌知识库',   icon: 'database' },
    'event-graph':   { subsystem: '案例知识', module: '图谱',     title: '事件关系图谱', icon: 'share-2' },
    'brand-report':  { subsystem: '案例知识', module: '报告',     title: '品牌分析报告', icon: 'file-bar' },
    'app-evidence':  { subsystem: '案例知识', module: '证据',     title: 'App证据采集',  icon: 'smartphone' },
    // 序境-Intelligence 子系统
    'resident-health':{ subsystem: 'Intelligence', module: '驻场', title: '驻场浏览器',   icon: 'monitor' },
    'internal-browser':{subsystem: 'Intelligence', module: '浏览器',title: '系统内置浏览器',icon: 'globe' },
    'brand-hub':     { subsystem: 'Intelligence', module: '多品牌',title: '多品牌中心',   icon: 'grid-2x2' },
    'kos':           { subsystem: 'Intelligence', module: 'KOS',   title: 'KOS传播主体',  icon: 'users' },
    'evidence':      { subsystem: 'Intelligence', module: '证据',  title: '证据看板',     icon: 'shield-check' },
    'calendar':      { subsystem: 'Intelligence', module: '日历',  title: '舆情日历',     icon: 'calendar' },
    'reports':       { subsystem: 'Intelligence', module: '报告',  title: '报告中心',     icon: 'file-text' },
    'settings':      { subsystem: 'Intelligence', module: '设置',  title: '系统设置',     icon: 'settings' }
  };

  // 生成面包屑 HTML
  function buildBreadcrumb(pageKey) {
    var meta = PAGE_REGISTRY[pageKey];
    if (!meta) return '';
    return '<div class="xj-breadcrumb">' +
      '<a href="#" onclick="navigateTo(\'overview\');return false;">序境</a>' +
      '<span class="xj-breadcrumb-sep">/</span>' +
      '<a href="#" onclick="navigateTo(\'' + (pageKey === 'overview' ? 'overview' : getSubsystemDefaultPage(meta.subsystem)) + '\');return false;">' + meta.subsystem + '</a>' +
      '<span class="xj-breadcrumb-sep">/</span>' +
      '<span class="xj-breadcrumb-current">' + meta.title + '</span>' +
      '</div>';
  }

  // 获取子系统默认页面
  function getSubsystemDefaultPage(subsystem) {
    var defaults = { '舆情核心': 'monitor', '案例知识': 'knowledge-base', 'Intelligence': 'kos' };
    return defaults[subsystem] || 'overview';
  }

  // 为页面注入统一头部（如果页面没有 xj-page-header）
  function ensurePageHeader(pageKey) {
    var meta = PAGE_REGISTRY[pageKey];
    if (!meta) return;
    var pageEl = document.getElementById('page-' + pageKey);
    if (!pageEl) return;
    // 首页已有自定义头部，跳过
    if (pageKey === 'overview') return;
    // 检查是否已有统一头部
    if (pageEl.querySelector('.xj-page-header')) return;
    // 检查是否有旧的 page-hero / page-title
    var oldHero = pageEl.querySelector('.page-hero, .page-title, .page-head');
    // 页面已有原生 .page-header（含返回按钮+h2+右侧操作）：只注入面包屑条，不重复注入 h1，保留原生按钮
    var nativeHeader = pageEl.querySelector('.page-header');
    if (nativeHeader) {
      if (!pageEl.querySelector('.xj-breadcrumb')) {
        nativeHeader.insertAdjacentHTML('beforebegin', '<div class="xj-page-header xj-header-breadcrumb-only" data-auto-injected="1">' + buildBreadcrumb(pageKey) + '</div>');
      }
      return;
    }
    var headerHTML = '<div class="xj-page-header" data-auto-injected="1">' +
      buildBreadcrumb(pageKey) +
      '<div class="xj-page-header-inner">' +
      '<div class="xj-page-header-left">' +
      '<span class="xj-page-header-eyebrow">序境 · ' + meta.subsystem + ' · ' + meta.module + '</span>' +
      '<h1 class="xj-page-header-title">' + meta.title + '</h1>' +
      '</div></div></div>';
    if (oldHero) {
      oldHero.outerHTML = headerHTML;
    } else {
      pageEl.insertAdjacentHTML('afterbegin', headerHTML);
    }
  }

  // 监听页面切换
  var origNavigateTo = window.navigateTo;
  window.navigateTo = function(page) {
    // 执行原始导航
    if (typeof origNavigateTo === 'function') {
      origNavigateTo.apply(this, arguments);
    }
    // 延迟注入头部（等 DOM 切换完成）
    setTimeout(function(){ ensurePageHeader(page); }, 50);
  };

  // 初始化：为当前活动页面注入头部
  function init() {
    var activePage = document.querySelector('.page-view.active');
    if (activePage) {
      var pageKey = activePage.id.replace('page-', '');
      ensurePageHeader(pageKey);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 暴露给全局
  window.XujingUI = {
    PAGE_REGISTRY: PAGE_REGISTRY,
    buildBreadcrumb: buildBreadcrumb,
    ensurePageHeader: ensurePageHeader
  };
})();
