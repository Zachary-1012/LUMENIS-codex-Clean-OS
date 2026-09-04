/* ============================================================
 * 序境 · 导航函数化 v2.1（六大场景主导 + 设置入口）
 * 依据产品白皮书 P24-P30 六大应用场景：
 *   品牌健康 / Campaign / KOS运营 / 舆情事件 / 危机预警 / 专题研究
 * 系统级功能（状态/更新/浏览器/设置）放在设置页面，不占主导航
 * NAV_IA 数据表 → xnav() 纯函数 → 渲染 side-nav
 * ============================================================ */
(function (global) {
  'use strict';

  var XNAV_DEFAULT_PAGE = 'overview';

  /* ---- 六大域 IA 数据表（唯一权威，依据 UI-FINAL-CAPABILITY-MAP.md） ---- */
  var NAV_IA = [
    /* ===== 域 1：工作台 Console ===== */
    {
      domain: '工作台',
      domainIcon: 'chat',
      items: [
        { page: 'overview', label: '智能问答', icon: 'chat', desc: 'AI驱动的舆情查询、风险判断、品牌分析' },
        { page: 'brand-dashboard', label: '品牌声量', icon: 'building', desc: '品牌声量与趋势追踪、品牌健康度评分' },
        { page: 'monitor', label: '监测概览', icon: 'search', desc: '口碑与情感分析、情感分布、内容分类' }
      ]
    },
    /* ===== 域 2：监测采集 Collect ===== */
    {
      domain: '监测采集',
      domainIcon: 'satellite',
      items: [
        { page: 'alerts', label: '实时监测', icon: 'warn', desc: '负面舆情实时监测、高风险预警', badgeId: 'sideRisk' },
        { page: 'negative', label: '风险评估', icon: 'shield', desc: '风险等级自动评估、负面二次确认', badgeId: 'sideNegative' },
        { page: 'resident-health', label: '采集状态', icon: 'refresh', desc: '采集器健康、调度状态、最后成功时间' }
      ]
    },
    /* ===== 域 3：事件/笔记/报告 Insights ===== */
    {
      domain: '事件笔记报告',
      domainIcon: 'doc',
      items: [
        { page: 'events', label: '事件检测', icon: 'trend', desc: '突发事件实时检测、事件热度与聚合' },
        { page: 'event-graph', label: '事件图谱', icon: 'link', desc: '事件生命周期追踪、传播路径与关键节点' },
        { page: 'notes', label: '笔记库', icon: 'list', desc: '内容质量与转化评估、笔记搜索与筛选' },
        { page: 'reports', label: '报告生成', icon: 'doc', desc: '日/周/月/专题报告自动生成与导出' },
        { page: 'calendar', label: '舆情日历', icon: 'calendar', desc: 'Campaign复盘与归因、舆情时间线' }
      ]
    },
    /* ===== 域 4：Zachary AI ===== */
    {
      domain: 'Zachary AI',
      domainIcon: 'bot',
      items: [
        { page: 'analysis', label: '深度研究', icon: 'chart', desc: '自定义主题深度研究、行业趋势分析' },
        { page: 'knowledge-base', label: '知识库', icon: 'book', desc: '品牌知识、案例库、研究成果沉淀' },
        { page: 'case-analysis', label: '案例分析', icon: 'bulb', desc: '典型案例深度拆解、方法论提炼' }
      ]
    },
    /* ===== 域 5：品牌库 Brand(ZBMP) ===== */
    {
      domain: '品牌库',
      domainIcon: 'hanger',
      items: [
        { page: 'kos', label: 'KOS 矩阵', icon: 'users', desc: 'KOS矩阵管理与分级、账号资产盘点' },
        { page: 'brands', label: '品牌管理', icon: 'building', desc: '品牌档案、业态对比、竞品策略分析' },
        { page: 'official', label: '销售线索', icon: 'news', desc: '销售线索追踪、官方动态采集' },
        { page: 'cases', label: '案例库', icon: 'trophy', desc: '营销案例卡片、详情下钻与复盘' }
      ]
    },
    /* ===== 域 6：系统 System ===== */
    {
      domain: '系统',
      domainIcon: 'gear',
      items: [
        { page: 'evidence', label: '证据看板', icon: 'shield', desc: '采集证据、审计日志、操作追溯' },
        { page: 'lifecycle', label: '生命周期', icon: 'refresh', desc: '需求/研究/决策/任务/证据/提交全链路追溯' },
        { page: 'settings', label: '设置', icon: 'gear', desc: '系统状态、数据更新、内部浏览器、外观主题' }
      ]
    }
  ];

  /* ---- 设置入口  ];

  /* ---- 设置入口（导航底部，系统级功能） ---- */
  var SETTINGS_ENTRY = [
    { page: 'settings', label: '设置', icon: 'gear', desc: '系统状态、数据更新、内部浏览器、外观主题、关于序境' }
  ];

  /* ---- xnav() 纯函数：渲染导航 ---- */
  function xnav(containerId) {
    var container = document.getElementById(containerId) || document.querySelector('.side-nav') || document.querySelector('#sideNav');
    if (!container) return;

    var html = '';

    // 六大场景
    NAV_IA.forEach(function (domain) {
      html += '<div class="nav-domain">';
      html += '<div class="nav-domain-title">';
      if (domain.domainIcon && typeof xicon === 'function') {
        html += xicon(domain.domainIcon, 14, 'nav-domain-icon');
      }
      html += '<span>' + domain.domain + '</span>';
      html += '</div>';
      html += '<div class="nav-domain-items">';
      domain.items.forEach(function (item) {
        var active = (item.page && item.page === XNAV_DEFAULT_PAGE) ? ' active' : '';
        var badge = item.badgeId ? '<span class="nav-badge" id="' + item.badgeId + '" style="display:none">0</span>' : '';
        var iconHtml = (item.icon && typeof xicon === 'function') ? xicon(item.icon, 16, 'nav-item-icon') : '';

        if (item.kind === 'link' && item.href) {
          html += '<a class="nav-item' + active + '" href="' + item.href + '" data-page="' + (item.page || item.id) + '" title="' + (item.desc || '') + '">';
        } else {
          html += '<div class="nav-item' + active + '" data-page="' + item.page + '" title="' + (item.desc || '') + '">';
        }
        html += iconHtml;
        html += '<span class="nav-item-label">' + item.label + '</span>';
        html += badge;
        if (item.kind === 'link' && item.href) {
          html += '</a>';
        } else {
          html += '</div>';
        }
      });
      html += '</div>';
      html += '</div>';
    });

    container.innerHTML = html;

    // 绑定点击事件
    container.querySelectorAll('.nav-item').forEach(function (el) {
      el.addEventListener('click', function (e) {
        var page = el.getAttribute('data-page');
        if (page && typeof navigateTo === 'function') {
          navigateTo(page);
        } else if (page && typeof switchPage === 'function') {
          switchPage(page);
        }
        // 更新 active 状态
        container.querySelectorAll('.nav-item').forEach(function (n) { n.classList.remove('active'); });
        el.classList.add('active');
        document.querySelectorAll('.side-item').forEach(function (s) {
          s.classList.toggle('active', s.dataset.page === page);
        });
      });
    });
  }

  /* ---- 设置当前页 ---- */
  function xnavSetActive(page) {
    XNAV_DEFAULT_PAGE = page;
    document.querySelectorAll('.nav-item').forEach(function (el) {
      if (el.getAttribute('data-page') === page) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });
  }

  /* ---- 获取导航数据 ---- */
  function xnavGetData() {
    return { scenes: NAV_IA, settings: SETTINGS_ENTRY };
  }

  /* ---- 导出 ---- */
  global.xnav = xnav;
  global.xnavSetActive = xnavSetActive;
  global.xnavGetData = xnavGetData;
  global.NAV_IA = NAV_IA;

  /* ---- 自动渲染 ---- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { xnav('sideNav'); });
  } else {
    xnav('sideNav');
  }
})(window);
