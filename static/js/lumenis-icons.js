/* ============================================================================
   LUMENIS Icons — 24×24 viewBox / 1.5px stroke / currentColor / 圆头线帽
   禁 emoji 作为正式 icon。注册表模式：licon(name) 返回 SVG 字符串。
   ============================================================================ */
(function (global) {
  "use strict";

  var P = 'fill="none" stroke="currentColor" stroke-width="1.5" ' +
          'stroke-linecap="round" stroke-linejoin="round"';
  var paths = {
    // 导航
    home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9.5 21v-6h5v6"/>',
    intelligence: '<path d="M12 3v3M12 18v3M3 12h3M18 12h3"/><circle cx="12" cy="12" r="4.5"/><path d="m15.5 8.5 2-2M8.5 15.5l-2 2M15.5 15.5l2 2M8.5 8.5l-2-2"/>',
    production: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 16v-4M12 16V8M17 16v-6"/>',
    research: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
    operations: '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5 5l2.2 2.2M16.8 16.8 19 19M19 5l-2.2 2.2M7.2 16.8 5 19"/>',
    skill: '<path d="M12 3 4 7v10l8 4 8-4V7z"/><path d="M4 7l8 4 8-4M12 11v10"/>',
    agent: '<rect x="5" y="7" width="14" height="11" rx="2.5"/><path d="M12 7V4M9 12h.01M15 12h.01M9 15.5h6"/>',
    evidence: '<path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6z"/><path d="m9 12 2 2 4-4"/>',
    evaluation: '<path d="M4 20V4M4 20h16"/><rect x="7" y="12" width="3" height="5"/><rect x="12" y="8" width="3" height="9"/><rect x="17" y="5" width="3" height="12"/>',
    learning: '<path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H20v13H6.5A2.5 2.5 0 0 0 4 19.5z"/><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>',
    // 通用操作
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    chevronRight: '<path d="m9 6 6 6-6 6"/>',
    chevronDown: '<path d="m6 9 6 6 6-6"/>',
    close: '<path d="M6 6l12 12M18 6 6 18"/>',
    menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
    refresh: '<path d="M20 11a8 8 0 1 0-2.3 6.4M20 5v6h-6"/>',
    filter: '<path d="M3 5h18l-7 8v6l-4-2v-4z"/>',
    download: '<path d="M12 3v12m0 0 4-4m-4 4-4-4M4 19h16"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    bell: '<path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/>',
    moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>',
    // 状态/对象
    risk: '<path d="M12 3 2 20h20z"/><path d="M12 10v5M12 18h.01"/>',
    event: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    brand: '<path d="M12 22s8-6 8-12a8 8 0 0 0-16 0c0 6 8 12 8 12z"/><circle cx="12" cy="10" r="2.5"/>',
    content: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 15l4-4 3 3 4-5 5 5"/>',
    report: '<path d="M6 2h9l5 5v15a0 0 0 0 1 0 0H6z"/><path d="M14 2v6h6M9 13h6M9 17h6"/>',
    database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    task: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    link: '<path d="M9 15l6-6"/><path d="M10.5 6.5 12 5a4 4 0 0 1 6 6l-1.5 1.5M13.5 17.5 12 19a4 4 0 0 1-6-6l1.5-1.5"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    arrowUp: '<path d="M12 19V5M6 11l6-6 6 6"/>',
    arrowDown: '<path d="M12 5v14M6 13l6 6 6-6"/>',
    spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><circle cx="12" cy="12" r="3"/>',
  };

  function licon(name, size, cls) {
    var body = paths[name] || paths.search;
    var s = size || 24;
    var c = cls ? ' class="' + cls + '"' : "";
    return '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24" ' + P +
      ' aria-hidden="true"' + c + ">" + body + "</svg>";
  }

  global.LUMENIS_ICONS = paths;
  global.licon = licon;
})(window);
