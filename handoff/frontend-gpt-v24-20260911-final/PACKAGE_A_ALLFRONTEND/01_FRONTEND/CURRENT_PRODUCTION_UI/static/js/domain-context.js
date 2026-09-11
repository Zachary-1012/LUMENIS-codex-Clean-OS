/* ============================================================================
   Domain Context — 全局双域上下文注入与切换重载
   ----------------------------------------------------------------------------
   职责：
   1. 从当前 URL / 页面元数据推断当前域（/zbmp/*→ZBMP, /cth/*→CTH, /system/*→SYSTEM）
   2. 全局拦截 fetch + XMLHttpRequest，自动注入 X-Product-Id / X-Domain-Id
   3. 域切换时真正重载五样：Context(AI上下文) / 指标(metrics) / 数据(data) /
      权限(permissions) / 报告(reports)——派发 domainchange 事件，各页面监听后
      重新 fetch 所有数据，禁止"标题变了数据还是另一域"
   4. 与现有 LUMENIS.fetch 兼容（LUMENIS.fetch 内部走原生 fetch，自动被拦截）
   5. 域切换时 bust 缓存（给同源 API 请求加 _dc 时间戳），防止读到另一域缓存

   红线：不做视觉样式，只做功能性域切换。
   ============================================================================ */
(function (global) {
  "use strict";

  /* ---------- 常量 ---------- */
  var DOMAIN_ZBMP = "zbmp";
  var DOMAIN_CTH = "cth";
  var DOMAIN_SYSTEM = "system";
  var VALID_DOMAINS = [DOMAIN_ZBMP, DOMAIN_CTH, DOMAIN_SYSTEM];

  var PRODUCT_ZBMP = "ZBMP";
  var PRODUCT_CTH = "CTH";
  var PRODUCT_SYSTEM = "SYSTEM";

  var STORAGE_KEY = "zbc-domain";
  var EVENT_DOMAIN_CHANGE = "domainchange";

  /* 域→产品映射 */
  function domainToProduct(domain) {
    if (domain === DOMAIN_ZBMP) return PRODUCT_ZBMP;
    if (domain === DOMAIN_CTH) return PRODUCT_CTH;
    if (domain === DOMAIN_SYSTEM) return PRODUCT_SYSTEM;
    return PRODUCT_CTH; // 生产安全默认
  }

  /* ---------- 域推断：从 URL path ---------- */
  function inferDomainFromUrl() {
    var path = window.location.pathname || "";
    var lower = path.toLowerCase();
    // /lumenis/zbmp/* 或 /zbmp/*
    if (lower.indexOf("/zbmp") >= 0) return DOMAIN_ZBMP;
    if (lower.indexOf("/cth") >= 0) return DOMAIN_CTH;
    if (lower.indexOf("/system") >= 0) return DOMAIN_SYSTEM;
    // /api/zbmp/* 等 API 路径
    if (lower.indexOf("/api/zbmp") >= 0) return DOMAIN_ZBMP;
    if (lower.indexOf("/api/cth") >= 0) return DOMAIN_CTH;
    if (lower.indexOf("/api/system") >= 0) return DOMAIN_SYSTEM;
    return "";
  }

  /* ---------- 域推断：从 body data-domain 属性（服务端渲染） ---------- */
  function inferDomainFromBody() {
    try {
      var d = document.body.getAttribute("data-domain");
      if (d && VALID_DOMAINS.indexOf(d.toLowerCase()) >= 0) return d.toLowerCase();
    } catch (e) {}
    return "";
  }

  /* ---------- 域推断：从 meta 标签 ---------- */
  function inferDomainFromMeta() {
    try {
      var meta = document.querySelector('meta[name="x-domain-id"]');
      if (meta) {
        var d = meta.getAttribute("content");
        if (d && VALID_DOMAINS.indexOf(d.toLowerCase()) >= 0) return d.toLowerCase();
      }
    } catch (e) {}
    return "";
  }

  /* ---------- 综合推断（优先级：URL > body > meta > localStorage > 默认cth） ---------- */
  function inferCurrentDomain() {
    var d = inferDomainFromUrl() || inferDomainFromBody() || inferDomainFromMeta();
    if (d) return d;
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && VALID_DOMAINS.indexOf(saved.toLowerCase()) >= 0) return saved.toLowerCase();
    } catch (e) {}
    return DOMAIN_CTH;
  }

  /* ========================================================================
     DomainContext 核心对象
     ======================================================================== */
  var DomainContext = {
    _domain: DOMAIN_CTH,
    _product: PRODUCT_CTH,
    _listeners: [],
    _initialized: false,

    /** 初始化：推断当前域，安装全局拦截器 */
    init: function () {
      if (this._initialized) return;
      this._initialized = true;

      this._domain = inferCurrentDomain();
      this._product = domainToProduct(this._domain);

      this._installFetchInterceptor();
      this._installXhrInterceptor();
      this._syncBodyAttribute();

      // 监听现有域切换器按钮（base.html 中的 .zbc-domain-tab）
      this._bindDomainSwitcher();

      // 暴露到全局
      global.ZBCDomainContext = this;
      global.ZBC_DOMAIN = this._domain;
      global.ZBC_PRODUCT = this._product;
    },

    /** 当前域 */
    getDomain: function () { return this._domain; },
    getProduct: function () { return this._product; },

    /** 获取请求头 */
    getHeaders: function () {
      return {
        "X-Domain-Id": this._domain,
        "X-Product-Id": this._product
      };
    },

    /**
     * 切换域：真正重载五样
     * 1. 更新内部状态 + body 属性 + localStorage
     * 2. 派发 domainchange 事件（各页面监听后重新 fetch 数据）
     * 3. 更新域切换器 UI 状态
     * 4. 如目标域有对应 overview 路由则导航（整页重载保证数据全新）
     */
    switchDomain: function (domain, opts) {
      opts = opts || {};
      domain = (domain || "").toLowerCase();
      if (VALID_DOMAINS.indexOf(domain) < 0) {
        console.error("[DomainContext] 非法域: " + domain);
        return false;
      }
      if (domain === this._domain && !opts.force) return true;

      var oldDomain = this._domain;
      var oldProduct = this._product;
      this._domain = domain;
      this._product = domainToProduct(domain);
      global.ZBC_DOMAIN = domain;
      global.ZBC_PRODUCT = this._product;

      // 持久化
      try { localStorage.setItem(STORAGE_KEY, domain); } catch (e) {}

      // 同步 body 属性
      this._syncBodyAttribute();

      // 更新域切换器 UI
      this._updateSwitcherUI(domain);

      // 更新 topbar 域标签
      this._updateTopbarTag(domain);

      // 派发 domainchange 事件——各页面监听此事件重新 fetch 所有数据
      // 五样重载：Context / metrics / data / permissions / reports
      var event;
      try {
        event = new CustomEvent(EVENT_DOMAIN_CHANGE, {
          detail: {
            domain: domain,
            product: this._product,
            oldDomain: oldDomain,
            oldProduct: oldProduct,
            timestamp: Date.now(),
            // 明确要求重载的五类资源
            reload: ["context", "metrics", "data", "permissions", "reports"]
          }
        });
      } catch (e) {
        // IE 兼容
        event = document.createEvent("CustomEvent");
        event.initCustomEvent(EVENT_DOMAIN_CHANGE, true, true, {
          domain: domain, product: this._product, oldDomain: oldDomain,
          oldProduct: oldProduct, timestamp: Date.now(),
          reload: ["context", "metrics", "data", "permissions", "reports"]
        });
      }
      document.dispatchEvent(event);
      window.dispatchEvent(event);

      // 如指定 navigate=true 则导航到目标域 overview（整页重载，数据全新）
      if (opts.navigate) {
        var routes = {};
        routes[DOMAIN_ZBMP] = "/lumenis/zbmp/overview";
        routes[DOMAIN_CTH] = "/lumenis/cth/overview";
        routes[DOMAIN_SYSTEM] = "/lumenis/system/runtime";
        if (routes[domain]) {
          window.location.href = routes[domain];
        }
      }

      console.log("[DomainContext] 域切换: " + oldDomain + " → " + domain +
        " (product: " + oldProduct + " → " + this._product + ")");
      return true;
    },

    /** 监听域切换 */
    onChange: function (fn) {
      if (typeof fn !== "function") return;
      this._listeners.push(fn);
      var self = this;
      document.addEventListener(EVENT_DOMAIN_CHANGE, function (e) {
        try { fn(e.detail || {}); } catch (err) { console.error("[DomainContext] listener error:", err); }
      });
    },

    /** 同步 body data-domain 属性 */
    _syncBodyAttribute: function () {
      try {
        document.body.setAttribute("data-domain", this._domain);
      } catch (e) {}
    },

    /** 更新域切换器按钮 UI */
    _updateSwitcherUI: function (domain) {
      try {
        var tabs = document.querySelectorAll(".zbc-domain-tab");
        tabs.forEach(function (tab) {
          var d = tab.getAttribute("data-domain");
          if (d === domain) {
            tab.classList.add("is-active");
            tab.setAttribute("aria-selected", "true");
          } else {
            tab.classList.remove("is-active");
            tab.setAttribute("aria-selected", "false");
          }
        });
        // 导航组显隐
        var groups = document.querySelectorAll("[data-domain-nav]");
        groups.forEach(function (g) {
          if (g.getAttribute("data-domain-nav") === domain) {
            g.removeAttribute("hidden");
          } else {
            g.setAttribute("hidden", "");
          }
        });
      } catch (e) {}
    },

    /** 更新 topbar 域标签 */
    _updateTopbarTag: function (domain) {
      try {
        var tag = document.querySelector(".zbc-topbar__domain-tag");
        if (tag) {
          tag.textContent = domain.toUpperCase();
          tag.className = "zbc-topbar__domain-tag zbc-tag--" + domain;
        }
      } catch (e) {}
    },

    /** 绑定现有域切换器按钮（替换 base.html 内联逻辑） */
    _bindDomainSwitcher: function () {
      var self = this;
      try {
        var tabs = document.querySelectorAll(".zbc-domain-tab");
        tabs.forEach(function (tab) {
          // 移除已有 click 监听（通过 clone 节点）
          var newTab = tab.cloneNode(true);
          tab.parentNode.replaceChild(newTab, tab);
          newTab.addEventListener("click", function () {
            var domain = newTab.getAttribute("data-domain");
            // navigate=true：整页导航到目标域 overview，保证数据全新加载
            self.switchDomain(domain, { navigate: true });
          });
        });
      } catch (e) {
        console.warn("[DomainContext] 域切换器绑定失败:", e);
      }
    },

    /* ====================================================================
       全局 fetch 拦截器：自动注入 X-Domain-Id / X-Product-Id
       ==================================================================== */
    _installFetchInterceptor: function () {
      if (typeof global.fetch !== "function") return;
      var self = this;
      var _origFetch = global.fetch;

      global.fetch = function (input, init) {
        init = init || {};
        var headers = init.headers || {};

        // headers 为纯字符串（如直接传 Authorization 值）时无法安全挂键：
        // 对原始字符串赋属性会抛 TypeError，此时保持原样放行，域头不强制注入
        if (typeof headers === "string") {
          return _origFetch.call(global, input, init);
        }

        // 转换 Headers 对象为普通对象以便注入
        if (typeof Headers !== "undefined" && headers instanceof Headers) {
          var tmp = {};
          headers.forEach(function (v, k) { tmp[k] = v; });
          headers = tmp;
        }

        // 转换 [key, value] 数组形式为普通对象
        if (Array.isArray(headers)) {
          var tmpArr = {};
          headers.forEach(function (pair) {
            if (Array.isArray(pair) && pair.length === 2) tmpArr[pair[0]] = pair[1];
          });
          headers = tmpArr;
        }

        // 注入域头（不覆盖已显式设置的）
        if (!headers["X-Domain-Id"] && !headers["x-domain-id"]) {
          headers["X-Domain-Id"] = self._domain;
        }
        if (!headers["X-Product-Id"] && !headers["x-product-id"]) {
          headers["X-Product-Id"] = self._product;
        }

        init.headers = headers;

        // 缓存 busting：对同源 API GET 请求加 _dc 时间戳
        // 防止域切换后读到另一域的浏览器缓存
        var url = typeof input === "string" ? input : (input && input.url ? input.url : "");
        if (url && url.indexOf("/api/") >= 0 && (!init.method || init.method === "GET")) {
          var sep = url.indexOf("?") >= 0 ? "&" : "?";
          // 仅在域切换后短时间内 bust，避免正常操作缓存失效
          if (self._lastSwitchTs && (Date.now() - self._lastSwitchTs < 5000)) {
            url += sep + "_dc=" + Date.now();
            if (typeof input === "string") {
              input = url;
            } else if (input && input.url) {
              input = new Request(url, init);
            }
          }
        }

        return _origFetch.call(global, input, init);
      };
    },

    /* ====================================================================
       全局 XMLHttpRequest 拦截器：自动注入域头
       ==================================================================== */
    _installXhrInterceptor: function () {
      if (typeof global.XMLHttpRequest !== "function") return;
      var self = this;
      var _origOpen = XMLHttpRequest.prototype.open;
      var _origSetHeader = XMLHttpRequest.prototype.setRequestHeader;

      XMLHttpRequest.prototype.open = function (method, url) {
        this._zbc_url = url;
        this._zbc_headersSet = false;
        return _origOpen.apply(this, arguments);
      };

      XMLHttpRequest.prototype.setRequestHeader = function (name, value) {
        // 记录用户已设置的头
        if (!this._zbc_userHeaders) this._zbc_userHeaders = {};
        this._zbc_userHeaders[name.toLowerCase()] = true;
        return _origSetHeader.apply(this, arguments);
      };

      // 在 send 时注入域头
      var _origSend = XMLHttpRequest.prototype.send;
      XMLHttpRequest.prototype.send = function () {
        try {
          var userHeaders = this._zbc_userHeaders || {};
          if (!userHeaders["x-domain-id"]) {
            _origSetHeader.call(this, "X-Domain-Id", self._domain);
          }
          if (!userHeaders["x-product-id"]) {
            _origSetHeader.call(this, "X-Product-Id", self._product);
          }
        } catch (e) {}
        return _origSend.apply(this, arguments);
      };
    },

    /** 记录上次切换时间（用于缓存 busting） */
    _lastSwitchTs: 0
  };

  // 在 switchDomain 中记录时间戳
  var _origSwitch = DomainContext.switchDomain;
  DomainContext.switchDomain = function (domain, opts) {
    var result = _origSwitch.call(this, domain, opts);
    if (result) this._lastSwitchTs = Date.now();
    return result;
  };

  /* ---------- 自动初始化 ---------- */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { DomainContext.init(); });
  } else {
    DomainContext.init();
  }

  /* ---------- 导出 ---------- */
  global.ZBCDomainContext = DomainContext;
})(typeof window !== "undefined" ? window : this);
