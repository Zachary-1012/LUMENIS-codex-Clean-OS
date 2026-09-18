/* ============================================================================
   LUMENIS i18n — 中英韩三语框架（阶段一地基）
   兼容现有页面约定：LUMENIS.i18n.dict / setLang / current / data-i18n
   词条源：static/locales/{zh-CN,en,ko}.json
   规则：
     - 所有可见文案走 t(key)，禁止硬编码裸串
     - 缺失词条回退 zh-CN，记 missing，不显示 key、不显示空白
     - 韩文没把握标 "__missing__"，回退中文，严禁机翻硬凑
     - 语言持久化 localStorage('lumenis-lang')，默认 zh-CN
     - 数字/日期/相对时间随语言本地化
   用法：
     LUMENIS.i18n.t('nav.overview')           // 取词条
     LUMENIS.i18n.setLang('en')               // 切换语言（整页即时生效）
     LUMENIS.i18n.current                     // 当前语言
     LUMENIS.i18n.registerDict(lang, obj)    // 页面级扩展词条
     <span data-i18n="nav.overview"></span>  // 自动绑定
     <input data-i18n-placeholder="common.search">
   ============================================================================ */
(function (global) {
  "use strict";

  var SUPPORTED = ["zh-CN", "en", "ko"];
  var DEFAULT = "zh-CN";
  var STORAGE_KEY = "lumenis-lang";
  var MISSING_PREFIX = "__missing__";
  var missingKeys = {}; // { lang: [key, ...] }

  // 内置最小词条（JSON 加载失败时的兜底，保证框架不裸奔）
  var FALLBACK = {
    "zh-CN": {
      "common.loading": "加载中…",
      "common.error": "加载失败",
      "common.empty": "暂无数据",
      "common.save": "保存",
      "common.cancel": "取消",
      "common.confirm": "确认",
      "common.search": "搜索…",
      "nav.overview": "概览",
      "nav.risk": "风险",
      "nav.reports": "报告",
      "nav.topics": "话题",
      "status.running": "运行中",
      "status.warning": "警告",
      "status.error": "异常",
      "status.unknown": "未知",
      "appearance.language": "语言",
      "appearance.theme": "主题",
      "theme.light": "浅色",
      "theme.dark": "深色"
    },
    "en": {
      "common.loading": "Loading…",
      "common.error": "Failed to load",
      "common.empty": "No data",
      "common.save": "Save",
      "common.cancel": "Cancel",
      "common.confirm": "Confirm",
      "common.search": "Search…",
      "nav.overview": "Overview",
      "nav.risk": "Risk",
      "nav.reports": "Reports",
      "nav.topics": "Topics",
      "status.running": "Running",
      "status.warning": "Warning",
      "status.error": "Error",
      "status.unknown": "Unknown",
      "appearance.language": "Language",
      "appearance.theme": "Theme",
      "theme.light": "Light",
      "theme.dark": "Dark"
    },
    "ko": {
      "common.loading": "로딩 중…",
      "common.error": "로드 실패",
      "common.empty": "데이터 없음",
      "common.save": "저장",
      "common.cancel": "취소",
      "common.confirm": "확인",
      "common.search": "검색…",
      "nav.overview": "개요",
      "nav.risk": "리스크",
      "nav.reports": "리포트",
      "nav.topics": "토픽",
      "status.running": "실행 중",
      "status.warning": "경고",
      "status.error": "오류",
      "status.unknown": "알 수 없음",
      "appearance.language": "언어",
      "appearance.theme": "테마",
      "theme.light": "라이트",
      "theme.dark": "다크"
    }
  };

  var dict = {};
  SUPPORTED.forEach(function (l) { dict[l] = {}; });

  var current = DEFAULT;
  try {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved && SUPPORTED.indexOf(saved) >= 0) current = saved;
  } catch (e) {}

  // 深合并词条
  function merge(target, src) {
    if (!src || typeof src !== "object") return;
    for (var k in src) {
      if (src.hasOwnProperty(k)) {
        if (typeof src[k] === "object" && src[k] !== null && !Array.isArray(src[k])) {
          if (!target[k] || typeof target[k] !== "object") target[k] = {};
          merge(target[k], src[k]);
        } else {
          target[k] = src[k];
        }
      }
    }
  }

  // 扁平化嵌套 key：a.b.c
  function getByPath(obj, path) {
    if (!obj || !path) return undefined;
    var parts = path.split(".");
    var cur = obj;
    for (var i = 0; i < parts.length; i++) {
      if (cur == null || typeof cur !== "object") return undefined;
      cur = cur[parts[i]];
    }
    return cur;
  }

  function isMissing(val) {
    return val == null || val === "" || (typeof val === "string" && val.indexOf(MISSING_PREFIX) === 0);
  }

  function recordMissing(lang, key) {
    if (!missingKeys[lang]) missingKeys[lang] = [];
    if (missingKeys[lang].indexOf(key) < 0) missingKeys[lang].push(key);
  }

  function t(key, opts) {
    opts = opts || {};
    var lang = opts.lang || current;
    // 1. 当前语言
    var val = getByPath(dict[lang], key);
    if (!isMissing(val)) return format(val, opts);
    recordMissing(lang, key);
    // 2. 回退 zh-CN
    if (lang !== DEFAULT) {
      var fb = getByPath(dict[DEFAULT], key);
      if (!isMissing(fb)) return format(fb, opts);
    }
    // 3. 兜底内置
    var fbi = FALLBACK[lang] ? FALLBACK[lang][key] : undefined;
    if (!isMissing(fbi)) return format(fbi, opts);
    if (lang !== DEFAULT) {
      var fbi2 = FALLBACK[DEFAULT] ? FALLBACK[DEFAULT][key] : undefined;
      if (!isMissing(fbi2)) return format(fbi2, opts);
    }
    // 4. 最终兜底：返回 key 本身（但控制台告警，不显示空白）
    if (global.console && console.warn) console.warn("[i18n] missing key:", key, "lang:", lang);
    return key;
  }

  // 简单占位符替换：t('greeting', {name:'X'}) → "你好，{name}"
  function format(str, opts) {
    if (typeof str !== "string") return str;
    if (!opts || !opts.vars) return str;
    return str.replace(/\{(\w+)\}/g, function (m, k) {
      return opts.vars[k] != null ? opts.vars[k] : m;
    });
  }

  // 应用到 DOM：扫描 data-i18n / data-i18n-placeholder
  function applyToDOM(root) {
    root = root || document;
    // textContent
    var nodes = root.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute("data-i18n");
      if (key) nodes[i].textContent = t(key);
    }
    // placeholder
    var phNodes = root.querySelectorAll("[data-i18n-placeholder]");
    for (var j = 0; j < phNodes.length; j++) {
      var pkey = phNodes[j].getAttribute("data-i18n-placeholder");
      if (pkey) phNodes[j].setAttribute("placeholder", t(pkey));
    }
    // aria-label
    var alNodes = root.querySelectorAll("[data-i18n-aria]");
    for (var k = 0; k < alNodes.length; k++) {
      var akey = alNodes[k].getAttribute("data-i18n-aria");
      if (akey) alNodes[k].setAttribute("aria-label", t(akey));
    }
    // <html lang>
    if (document.documentElement) document.documentElement.setAttribute("lang", current);
  }

  function setLang(lang, opts) {
    opts = opts || {};
    if (SUPPORTED.indexOf(lang) < 0) {
      if (global.console && console.warn) console.warn("[i18n] unsupported lang:", lang);
      return;
    }
    current = lang;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) {}
    if (!opts.silent) {
      applyToDOM(document);
      // 派发事件，供页面级脚本响应
      var evt;
      try {
        evt = new CustomEvent("lumenis:langchange", { detail: { lang: lang } });
      } catch (e) {
        evt = document.createEvent("CustomEvent");
        evt.initCustomEvent("lumenis:langchange", true, true, { lang: lang });
      }
      document.dispatchEvent(evt);
    }
  }

  // 页面级扩展词条（如 command_home.html 的 homeDict）
  function registerDict(lang, obj) {
    if (!dict[lang]) dict[lang] = {};
    merge(dict[lang], obj);
  }

  // 加载外部词条 JSON
  function loadLocale(lang) {
    var url = "/static/locales/" + lang + ".json";
    return fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        registerDict(lang, data);
        return data;
      })
      .catch(function (e) {
        if (global.console && console.warn) console.warn("[i18n] failed to load", url, e);
        return null;
      });
  }

  // 数字本地化
  function formatNumber(n, opts) {
    try {
      return new Intl.NumberFormat(current, opts || {}).format(n);
    } catch (e) { return String(n); }
  }

  // 日期本地化
  function formatDate(d, opts) {
    try {
      var date = (d instanceof Date) ? d : new Date(d);
      return new Intl.DateTimeFormat(current, opts || { year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
    } catch (e) { return String(d); }
  }

  // 相对时间（几分钟前/昨天）
  function formatRelativeTime(date) {
    try {
      var now = Date.now();
      var then = (date instanceof Date) ? date.getTime() : new Date(date).getTime();
      var diffSec = Math.round((now - then) / 1000);
      var rtf = new Intl.RelativeTimeFormat(current, { numeric: "auto" });
      if (Math.abs(diffSec) < 60) return rtf.format(-Math.round(diffSec), "second");
      if (Math.abs(diffSec) < 3600) return rtf.format(-Math.round(diffSec / 60), "minute");
      if (Math.abs(diffSec) < 86400) return rtf.format(-Math.round(diffSec / 3600), "hour");
      if (Math.abs(diffSec) < 2592000) return rtf.format(-Math.round(diffSec / 86400), "day");
      return formatDate(then);
    } catch (e) { return String(date); }
  }

  // 初始化：加载所有词条，然后应用
  var initPromise = null;
  function init() {
    if (initPromise) return initPromise;
    var loads = SUPPORTED.map(function (l) { return loadLocale(l); });
    initPromise = Promise.all(loads).then(function () {
      applyToDOM(document);
      return current;
    });
    return initPromise;
  }

  // 暴露 API（兼容现有 LUMENIS.i18n.dict / setLang / current 约定）
  global.LUMENIS = global.LUMENIS || {};
  global.LUMENIS.i18n = {
    dict: dict,
    current: current,
    t: t,
    setLang: setLang,
    registerDict: registerDict,
    applyToDOM: applyToDOM,
    formatNumber: formatNumber,
    formatDate: formatDate,
    formatRelativeTime: formatRelativeTime,
    getMissing: function (lang) { return missingKeys[lang] || []; },
    getAllMissing: function () { return missingKeys; },
    SUPPORTED: SUPPORTED,
    init: init
  };

  // 让 current 成为响应式（读时返回最新值）
  Object.defineProperty(global.LUMENIS.i18n, "current", {
    get: function () { return current; },
    enumerable: true
  });

  // DOM 就绪后初始化
  if (document.readyState !== "loading") {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})(window);
