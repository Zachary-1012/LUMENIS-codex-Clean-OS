/* ============================================================
 * 序境 · 导航函数化（函数驱动）
 * 依据 docs/UI-IA-INTERACTION-DESIGN-BASELINE-20260903.md
 *   6 大域 IA：工作台 / 监测 / 事件 / 洞察 / 资产 / 系统
 *   Domain -> Page -> Section -> Module -> Component -> Action -> State
 * NAV_IA 数据表 → xnav() 纯函数 → 渲染 side-nav
 * icon 复用 xujing-icons.js 注册表（xicon）
 * 新增页仅需改 NAV_IA 数据表，导航自动收敛。
 * ============================================================ */
(function (global) {
  'use strict';

  var XNAV_DEFAULT_PAGE = 'overview';

  /* ---- 6 大域 IA 数据表（唯一权威） ---- */
  var NAV_IA = [
    { domain: '工作台', items: [
      { page: 'overview', label: '智能问答', icon: 'chat', desc: '智能问答：AI驱动的舆情查询、风险判断、品牌分析，结论→依据→数据→Evidence→Action' }
    ] },
    { domain: '监测', items: [
      { page: 'monitor', label: '舆情监测', icon: 'search', desc: '情感分布、风险等级、内容分类统计' },
      { page: 'alerts', label: '风险预警', icon: 'warn', desc: '高风险预警通知、已读可消除红点', badgeId: 'sideRisk' },
      { page: 'negative', label: '负面确认', icon: 'shield', desc: '负面舆情二次确认、核准后才计入周报月报', badgeId: 'sideNegative' },
      { page: 'notes', label: '笔记搜索', icon: 'list', desc: '笔记搜索、详情查看、复核记录' },
      { page: 'official', label: '官方动态', icon: 'news', desc: '官网、微博、微信公众号官方动态采集' },
      { page: 'topics', label: '热门话题', icon: 'tag', desc: '热门话题、正向体验、消费热度' },
      { kind: 'link', id: 'topic-campaign-entry-v573', href: '/topic-campaign', label: '话题活动', icon: 'megaphone', desc: '话题活动入口' },
      { page: 'internal-browser', label: '内部浏览器', icon: 'globe', desc: '系统内置浏览器，小红书/rednote 双账号系统内完成，不跳转外部浏览器' }
    ] },
    { domain: '事件', items: [
      { page: 'events', label: '事件中心', icon: 'trend', desc: '舆情事件聚合、传播路径、案例对标' },
      { page: 'event-graph', label: '事件关系', icon: 'link', desc: '营销事件/传播事件/舆情事件的关系图谱，触发/衍生/继发/并行四种关系' },
      { page: 'calendar', label: '舆情日历', icon: 'calendar', desc: '舆情日历、每日舆情概览、点击查看详情' }
    ] },
    { domain: '洞察', items: [
      { page: 'analysis', label: '舆情分析', icon: 'chart', desc: '近14天舆情变化趋势、数据点详情' },
      { page: 'brands', label: '品牌业态', icon: 'building', desc: '8大业态分布、198个品牌舆情、点击查看笔记' },
      { page: 'kos', label: 'KOS 传播主体', icon: 'users', desc: 'KOS传播主体智能：S/A/B/C分层、潜力/风险识别、评论分析、博主触达、投流候选' },
      { page: 'reports', label: '报告中心', icon: 'doc', desc: '日报/周报/月报/年报导出，Word/Excel/CSV格式' },
      { page: 'brand-report', label: '品牌报告', icon: 'export', desc: '品牌传播与市场情报报告生成器，多维度自动分析' },
      { page: 'podcast', label: '播客工作台', icon: 'music', desc: '播客内容情报与生产工作台：选题打分、故事节点、运行时校验、破圈分类、实体图' }
    ] },
    { domain: '资产', items: [
      { page: 'brand-hub', label: '品牌中心', icon: 'target', desc: '多品牌中心：6大品牌矩阵，品牌→地区→门店层级导航，统一KOS引擎' },
      { page: 'swire', label: '太古地产案例', icon: 'box', desc: '品牌营销案例库：以品牌为一级维度，下钻其营销事件库与小红书笔记库' },
      { page: 'cases', label: '案例库总览', icon: 'book', desc: '全网舆情案例库、事件→回应→效果、太古汇启示' },
      { page: 'case-analysis', label: '案例深度拆解', icon: 'bulb', desc: '20个11维深度拆解案例：品牌营销/危机公关/商业地产/社媒平台/产品化营销' },
      { page: 'knowledge-base', label: '知识库', icon: 'brain', desc: '品牌营销/广告宣传/舆情管理知识库，80条结构化知识' },
      { page: 'evidence', label: 'Evidence', icon: 'eye', desc: '健康与采集全程证据看板，每个完成/失败都可回放' },
      { page: 'app-evidence', label: 'App证据', icon: 'check', desc: 'App端数据证据采集（Shadow模式）：用户主动截图上传→字段识别→人工确认' }
    ] },
    { domain: '系统', items: [
      { page: 'resident-health', label: '系统健康', icon: 'heart', desc: '双身份驻场浏览器三层健康检测、登录态监控、失效扫码恢复' },
      { page: 'settings', label: '系统设置', icon: 'gear', desc: '公司域名、推送邮箱、AI配置、开发者工具运行代码' },
      { kind: 'button', id: 'kbShortcutsEntry', label: '快捷键', icon: 'keyboard', desc: '查看并使用全部键盘快捷键（Ctrl+/ 随时唤起）' }
    ] }
  ];

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/"/g, '&quot;')
      .replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function icon(name) {
    if (global.xicon) return global.xicon(name, 18);
    return '<svg class="xj-ic" width="18" height="18" style="width:18px;height:18px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/></svg>';
  }

  function itemHtml(it) {
    var isPage = it.kind !== 'link' && it.kind !== 'button';
    var active = isPage && it.page === XNAV_DEFAULT_PAGE ? ' active' : '';
    var badge = it.badgeId ? '<b class="nav-badge" id="' + it.badgeId + '" style="display:none">0</b>' : '';
    var inner = '<span class="navicon">' + icon(it.icon) + '</span><span>' + esc(it.label) + '</span>' + badge;
    if (it.kind === 'link') {
      return '<a id="' + it.id + '" class="side-item" href="' + esc(it.href) + '" style="text-decoration:none">' + inner + '</a>';
    }
    if (it.kind === 'button') {
      return '<button id="' + it.id + '" class="side-item" type="button" data-desc="' + esc(it.desc) + '">' + inner + '</button>';
    }
    return '<button class="side-item' + active + '" data-page="' + it.page + '" data-desc="' + esc(it.desc) + '">' + inner + '</button>';
  }

  function xnav() {
    return NAV_IA.map(function (g) {
      return '<div class="side-group-label">' + esc(g.domain) + '</div>' +
        g.items.map(itemHtml).join('');
    }).join('');
  }

  function mount() {
    var host = document.getElementById('sideNav') || document.querySelector('.side-nav');
    if (!host) return;
    if (host.getAttribute('data-xnav-mounted')) return;
    host.innerHTML = xnav();
    host.setAttribute('data-xnav-mounted', '1');
  }

  /* 关键：必须同步立即渲染（容器在 body 前方已解析），
     保证 app.js 的 .side-item 顶层绑定拿到已渲染元素；否则绑定失效。 */
  var _host = document.getElementById('sideNav') || document.querySelector('.side-nav');
  if (_host) mount();
  else document.addEventListener('DOMContentLoaded', mount);

  global.NAV_IA = NAV_IA;
  global.xnav = xnav;
  global.XNAV_DEFAULT_PAGE = XNAV_DEFAULT_PAGE;
})(window);
