/* ============================================================
 * 序境 Xujing · 细线 SVG Icon 函数层
 * Canonical UI Icon Registry（数据表驱动 → xicon() 函数 → 模板调用）
 * 规范：黑白米灰侘寂 · 1.5px 细线 stroke · 24×24 viewBox
 * 红线：禁止 emoji 充当正式 icon；所有图标统一经 xicon() 产出
 * 用法：innerHTML 模板内 ${xicon('chart', 14)} 或 ${xicon('chart')}
 * ============================================================ */
(function (global) {
  'use strict';

  /* ---- Icon Registry（name → 24×24 stroke path 数组） ---- */
  var R = {
    /* 通用 */
    chart:  ['M4 20h16', 'M6 20V10', 'M10 20V4', 'M14 20v-8', 'M18 20V7'],
    trend:  ['M3 17l5-5 4 4 7-8', 'M14 8h5v5'],
    pin:    ['M12 21s-6-5.2-6-10a6 6 0 1 1 12 0c0 4.8-6 10-6 10z', 'M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z'],
    chat:   ['M4 5h16v11H9l-5 4V5z', 'M8 9h8', 'M8 12h5'],
    reply:  ['M20 9v6h-7l-3 3v-3H4V9h16z'],
    globe:  ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z', 'M3 12h18', 'M12 3a13 13 0 0 1 0 18 13 13 0 0 1 0-18z'],
    phone:  ['M7 3h10a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z', 'M10 18h4'],
    news:   ['M5 4h14v16H5z', 'M8 8h8', 'M8 11h8', 'M8 14h5'],
    bulb:   ['M9 18h6', 'M10 21h4', 'M12 3a6 6 0 0 1 4 10.5c-.7.6-1 1.5-1 2.5h-6c0-1-.3-1.9-1-2.5A6 6 0 0 1 12 3z'],
    box:    ['M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z', 'M4 7.5l8 4.5 8-4.5', 'M12 12v9'],
    doc:    ['M6 3h8l4 4v14H6z', 'M14 3v4h4', 'M9 12h6', 'M9 16h6'],
    warn:   ['M12 4L2.5 20h19L12 4z', 'M12 10v4', 'M12 16.5v.5'],
    users:  ['M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M2 21c0-3.3 2.7-6 6-6s6 2.7 6 6', 'M16 5a4 4 0 1 1-1.5 7.7', 'M17 15.2A6 6 0 0 1 22 21'],
    building:['M4 21V5l8-3 8 3v16', 'M4 21h16', 'M9 8h2', 'M9 12h2', 'M13 8h2', 'M13 12h2', 'M9 16h6'],
    target: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z', 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z'],
    /* 业态分类 */
    hanger: ['M12 6a2 2 0 1 1 2-2', 'M12 6v2', 'M4 18l8-4 8 4-8 4-8-4z'],
    dining: ['M7 3v7', 'M7 10v11', 'M4 3v4a3 3 0 0 0 6 0V3', 'M17 3v18', 'M17 3c-2 1-3 3-3 6s1 5 3 5'],
    jewelry:['M12 3l3 4h-6l3-4z', 'M12 7v3', 'M9 10h6l3 4H6l3-4z', 'M12 14v7'],
    beauty: ['M5 6h14', 'M8 6v3a4 4 0 0 0 8 0V6', 'M12 13v4', 'M12 21v-4'],
    sport:  ['M6 4h6a3 3 0 0 1 3 3v9', 'M6 4v16', 'M15 12l5 2v3l-5-1', 'M9 8h6'],
    bag:    ['M6 8h12l-1 12H7L6 8z', 'M9 8V6a3 3 0 0 1 6 0v2', 'M9 12h6'],
    toy:    ['M5 8h14v10a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V8z', 'M9 8V6a2 2 0 0 1 4 0v2', 'M9 13v2', 'M13 13v2', 'M8 5H5a2 2 0 0 0 0 4'],
    home:   ['M3 11l9-8 9 8', 'M5 9.5V21h14V9.5', 'M10 21v-6h4v6'],
    search: ['M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z', 'M21 21l-4.3-4.3'],
    check:  ['M4 12l5 5L20 6']
  };

  /* 分类 → 图标名映射（数据表，供页面复用） */
  var CAT = {
    '女装': 'hanger', '男装': 'hanger', '餐饮': 'dining', '珠宝钟表': 'jewelry',
    '美容护理': 'beauty', '运动休闲': 'sport', '鞋包皮具': 'bag', '童装玩具': 'toy', '生活时尚': 'home'
  };

  /* 渠道 → 图标名映射 */
  var CH = {
    'taikoo_official': 'globe', 'weibo_official': 'phone', 'wechat_service': 'chat', 'wechat_subscribe': 'news'
  };

  /* ---- xicon(name, size, cls) → inline SVG 字符串 ---- */
  function xicon(name, size, cls) {
    var paths = R[name] || R.box;
    size = size || 14;
    var p = paths.map(function (d) {
      return '<path d="' + d + '"/>';
    }).join('');
    return '<svg class="xj-ic' + (cls ? ' ' + cls : '') + '" width="' + size + '" height="' + size +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + '</svg>';
  }

  global.XJ_ICONS = { R: R, CAT: CAT, CH: CH, xicon: xicon };
  global.xicon = xicon;  /* 模板字符串内 ${xicon('chart')} 直接可用 */
})(window);
