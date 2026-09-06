/* ============================================================================
   LUMENIS Terminology — 渲染层术语替换
   产品术语表 V1.0 唯一权威来源：audit/PRODUCT_TERMINOLOGY_TABLE_V1.0.md
   规则：代码内部可保留工程代号，渲染给用户时必须替换为标准用名。
   用法：
     LUMENIS.term.replace(text)        // 替换文本中的代号
     LUMENIS.term.sanitizeElement(el)  // 递归替换元素及其子节点的文本
     LUMENIS.term.scanPage()           // 扫描整页，替换所有含代号的可见文本
   ============================================================================ */
(function (global) {
  "use strict";

  // 代号 → 标准用名映射（按长度降序排列，避免短串先匹配）
  var MAP = [
    // 产品总代号（最优先，避免被其他规则部分匹配）
    { from: /ZBC\s*生产真相\s*[×x]\s*OSAI\s*智能推理/g, to: "序境 · 品牌与舆情智能" },
    { from: /ZBC\s*Production\s*Truth\s*[×x]\s*OSAI\s*Intelligence/gi, to: "LUMENIS · Brand & Sentiment Intelligence" },
    { from: /ZBC\s*생산\s*진실\s*[×x]\s*OSAI\s*지능\s*추론/g, to: "서경 · 브랜드 및 감성 인텔리전스" },
    // 独立代号
    { from: /\bZBC\b/g, to: "序境 LUMENIS" },
    { from: /\bOSAI\b/g, to: "智能引擎" },
    // 域代号（独立词边界）
    { from: /\bZBMP\b/g, to: "品牌智能" },
    { from: /\bCTH\b/g, to: "太古汇智能" },
    { from: /\bSYS\b/g, to: "系统" },
    // 安全术语
    { from: /\bTOTP\b/g, to: "动态验证码" },
    // 技术态串（禁止直接显示）
    { from: /Provider:\s*detecting…/gi, to: "模型连接中…" },
    { from: /Provider:\s*local\s*fallback/gi, to: "本地模型" },
    { from: /\bAI\s*Ready\b/g, to: "智能就绪" },
    { from: /\bEvidence[- ]backed\b/gi, to: "证据支撑" },
    // source: 技术串（移除或替换）
    { from: /source:\s*OSAI/gi, to: "智能引擎" },
    { from: /source:\s*health\/summary/gi, to: "系统健康" },
    { from: /source:\s*evidence\s*chains/gi, to: "证据链" },
    { from: /source:\s*negative\/stats/gi, to: "负面舆情统计" },
    { from: /source:\s*collect\/tasks/gi, to: "采集任务" },
  ];

  // 开发者功能白名单：这些元素/区域内的代号不替换（加了中文注解的工程词）
  var DEV_SELECTOR = '[data-dev-term], .developer-zone, .api-doc';

  function replace(text) {
    if (typeof text !== "string" || !text) return text;
    var result = text;
    for (var i = 0; i < MAP.length; i++) {
      result = result.replace(MAP[i].from, MAP[i].to);
    }
    return result;
  }

  function isDevZone(el) {
    if (!el || !el.closest) return false;
    return !!el.closest(DEV_SELECTOR);
  }

  function sanitizeElement(root) {
    if (!root || isDevZone(root)) return;
    // 处理文本节点
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var node;
    while ((node = walker.nextNode())) {
      if (node.nodeValue && /ZBC|OSAI|ZBMP|CTH|\bSYS\b|TOTP|Provider:|AI Ready|Evidence[- ]backed|source:/.test(node.nodeValue)) {
        if (!isDevZone(node.parentElement)) {
          node.nodeValue = replace(node.nodeValue);
        }
      }
    }
    // 处理属性（placeholder, title, aria-label, data-i18n 不动）
    var attrs = ["placeholder", "title", "aria-label"];
    root.querySelectorAll("*").forEach(function (el) {
      if (isDevZone(el)) return;
      attrs.forEach(function (attr) {
        var val = el.getAttribute(attr);
        if (val && /ZBC|OSAI|ZBMP|CTH|\bSYS\b|TOTP|Provider:|AI Ready|Evidence[- ]backed|source:/.test(val)) {
          el.setAttribute(attr, replace(val));
        }
      });
    });
  }

  function scanPage() {
    sanitizeElement(document.body);
  }

  // 暴露 API
  global.LUMENIS = global.LUMENIS || {};
  global.LUMENIS.term = {
    replace: replace,
    sanitizeElement: sanitizeElement,
    scanPage: scanPage,
    MAP: MAP
  };

  // 自动扫描：DOM 就绪后执行一次
  if (document.readyState !== "loading") {
    scanPage();
  } else {
    document.addEventListener("DOMContentLoaded", scanPage);
  }
})(window);
