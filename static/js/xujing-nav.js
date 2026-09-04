/* ============================================================
 * 序境 · 导航函数化 v2.0（六大场景主导）
 * 依据产品白皮书 P24-P30 六大应用场景：
 *   品牌健康 / Campaign / KOS运营 / 舆情事件 / 危机预警 / 专题研究
 * 其他功能均为六大场景的下一层级
 * NAV_IA 数据表 → xnav() 纯函数 → 渲染 side-nav
 * icon 复用 xujing-icons.js 注册表（xicon）
 * ============================================================ */
(function (global) {
  'use strict';

  var XNAV_DEFAULT_PAGE = 'overview';

  /* ---- 六大场景 IA 数据表（唯一权威） ---- */
  var NAV_IA = [
    /* ===== 场景 1：品牌健康 ===== */
    {
      domain: '品牌健康',
      domainIcon: 'heart',
      items: [
        { page: 'overview', label: '智能问答', icon: 'chat', desc: 'AI驱动的舆情查询、风险判断、品牌分析' },
        { page: 'brands', label: '品牌声量', icon: 'building', desc: '品牌声量与趋势追踪、品牌健康度评分' },
        { page: 'monitor', label: '口碑情感', icon: 'search', desc: '口碑与情感分析、情感分布、内容分类' },
        { page: 'analysis', label: '竞品对比', icon: 'chart', desc: '竞品品牌对比、近14天舆情变化趋势' },
        { page: 'topics', label: '品牌资产', icon: 'tag', desc: '热门话题、正向体验、消费热度、品牌资产预警' }
      ]
    },
    /* ===== 场景 2：Campaign ===== */
    {
      domain: 'Campaign',
      domainIcon: 'megaphone',
      items: [
        { kind: 'link', id: 'topic-campaign-entry-v573', href: '/topic-campaign', label: '活动追踪', icon: 'megaphone', desc: 'Campaign 全周期追踪、话题活动入口' },
        { page: 'events', label: '内容表现', icon: 'trend', desc: '内容表现对比、事件聚合、传播路径' },
        { page: 'event-graph', label: '渠道效能', icon: 'link', desc: '渠道效能评估、事件关系图谱、触发/衍生/继发/并行' },
        { page: 'calendar', label: '复盘归因', icon: 'calendar', desc: 'Campaign 复盘与归因、舆情日历、每日概览' }
      ]
    },
    /* ===== 场景 3：KOS 运营 ===== */
    {
      domain: 'KOS 运营',
      domainIcon: 'users',
      items: [
        { page: 'kos', label: 'KOS 矩阵', icon: 'users', desc: 'KOS 矩阵管理与分级、账号资产' },
        { page: 'notes', label: '内容质量', icon: 'list', desc: '内容质量与转化评估、笔记搜索、详情查看' },
        { page: 'official', label: '销售线索', icon: 'news', desc: '销售线索追踪、官方动态采集' },
        { page: 'internal-browser', label: '效能排名', icon: 'globe', desc: 'KOS 效能排名、系统内置浏览器、双账号系统' }
      ]
    },
    /* ===== 场景 4：舆情事件 ===== */
    {
      domain: '舆情事件',
      domainIcon: 'trend',
      items: [
        { page: 'events', label: '事件检测', icon: 'trend', desc: '突发事件实时检测、事件热度与传播速度' },
        { page: 'event-graph', label: '生命周期', icon: 'link', desc: '事件生命周期追踪、关键节点与转折点' },
        { page: 'calendar', label: '影响评估', icon: 'calendar', desc: '事件影响范围评估、舆情日历' },
        { page: 'notes', label: '案例对标', icon: 'list', desc: '案例对标、笔记详情、复核记录' }
      ]
    },
    /* ===== 场景 5：危机预警 ===== */
    {
      domain: '危机预警',
      domainIcon: 'warn',
      items: [
        { page: 'alerts', label: '实时监测', icon: 'warn', desc: '负面舆情实时监测、高风险预警通知', badgeId: 'sideRisk' },
        { page: 'negative', label: '风险评估', icon: 'shield', desc: '风险等级自动评估、负面舆情二次确认', badgeId: 'sideNegative' },
        { page: 'monitor', label: '传播路径', icon: 'search', desc: '风险传播路径追踪、情感分布、风险等级' },
        { page: 'analysis', label: '处置复盘', icon: 'chart', desc: '处置建议与复盘、近14天舆情变化趋势' }
      ]
    },
    /* ===== 场景 6：专题研究 ===== */
    {
      domain: '专题研究',
      domainIcon: 'bulb',
      items: [
        { page: 'analysis', label: '深度研究', icon: 'chart', desc: '自定义主题深度研究、行业趋势与洞察' },
        { page: 'brands', label: '竞品策略', icon: 'building', desc: '竞品策略分析、品牌业态对比' },
        { page: 'monitor', label: '消费者洞察', icon: 'search', desc: '消费者洞察研究、内容分类统计' },
        { kind: 'link', id: 'report-export', href: '#', label: '报告生成', icon: 'doc', desc: '研究报告自动生成、日报/周报/月报' }
      ]
    }
  ];

  /* ---- xnav() 纯函数：渲染导航 ---- */
  function xnav(containerId) {
    var container = document.getElementById(containerId) || document.querySelector('.side-nav') || document.querySelector('#sideNav');
    if (!container) return;

    var html = '';
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
        if (page && typeof switchPage === 'function') {
          switchPage(page);
        }
        // 更新 active 状态
        container.querySelectorAll('.nav-item').forEach(function (n) { n.classList.remove('active'); });
        el.classList.add('active');
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
    return NAV_IA;
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
