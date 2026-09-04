/* ============================================================================
   LUMENIS Core — 主题 / 9 态状态系统 / 真实 API 绑定 / 防假数据
   对齐 osai_engine/ui_state_contract.py：loading/empty/success/warning/
   error/blocked/offline/processing/completed；success 必须有 dataRef。
   ============================================================================ */
(function (global) {
  "use strict";

  var UI_STATES = ["loading", "empty", "success", "warning", "error",
                   "blocked", "offline", "processing", "completed"];

  /* ---------- 主题（Light/Dark，持久化，尊重系统偏好） ---------- */
  var Theme = {
    KEY: "lumenis-theme",
    init: function () {
      var saved = localStorage.getItem(this.KEY);
      if (saved === "light" || saved === "dark") {
        document.documentElement.setAttribute("data-theme", saved);
      }
    },
    toggle: function () {
      var cur = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
      var next = cur === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem(this.KEY, next);
      return next;
    },
    current: function () {
      return document.documentElement.getAttribute("data-theme") ||
        (global.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    }
  };

  /* ---------- UI State Machine（与后端 UI State Contract 同构） ---------- */
  function StateStore() {
    this._states = {};   // page::component -> state object
    this._listeners = {};
  }
  StateStore.prototype._key = function (page, comp) { return page + "::" + comp; };

  StateStore.prototype.set = function (page, comp, state, opts) {
    if (UI_STATES.indexOf(state) < 0) throw new Error("非法 UI 状态: " + state);
    opts = opts || {};
    // 红线：error/blocked 必须带 message 或 errorCode
    if ((state === "error" || state === "blocked") && !opts.message && !opts.errorCode) {
      throw new Error(state + " 状态必须提供 message 或 errorCode");
    }
    // 红线：success/completed 必须有 dataRef（指向真实 API），否则判定假状态
    if ((state === "success" || state === "completed") && !opts.dataRef) {
      console.warn("[LUMENIS] 假状态拦截: %s::%s success 但无 dataRef", page, comp);
    }
    var rec = {
      page: page, component: comp, state: state,
      freshness: opts.freshness || "unknown",
      message: opts.message || "", errorCode: opts.errorCode || "",
      dataRef: opts.dataRef || "", ts: new Date().toISOString()
    };
    this._states[this._key(page, comp)] = rec;
    this._emit(rec);
    return rec;
  };
  StateStore.prototype.get = function (page, comp) { return this._states[this._key(page, comp)]; };
  StateStore.prototype.on = function (fn) { this._listeners._ = fn; };
  StateStore.prototype._emit = function (rec) { if (this._listeners._) this._listeners._(rec); };
  StateStore.prototype.snapshot = function () {
    var byState = {}, fake = 0, list = [];
    for (var k in this._states) {
      var s = this._states[k];
      byState[s.state] = (byState[s.state] || 0) + 1;
      if ((s.state === "success" || s.state === "completed") && !s.dataRef) fake++;
      list.push(s);
    }
    return { total: list.length, byState: byState, fakeStateCount: fake, components: list };
  };

  /* ---------- 真实数据获取（统一走 fetch，显式状态，禁止静默成 0） ---------- */
  // 用法：LUMENIS.bindState(el, { page, component, url, render(resp) })
  function bindState(el, cfg) {
    var store = LUMENIS.store;
    function paint(state, opts) {
      if (!el) return;
      el.setAttribute("data-state", state);
      var slot = el.querySelector("[data-state-slot]");
      if (slot && opts && opts.message) slot.textContent = opts.message;
    }
    store.set(cfg.page, cfg.component, "loading");
    paint("loading");
    return fetch(cfg.url, cfg.fetchOpts || {})
      .then(function (r) {
        if (!r.ok) throw { code: "HTTP_" + r.status, status: r.status };
        return r.json();
      })
      .then(function (data) {
        var empty = cfg.isEmpty ? cfg.isEmpty(data) :
          (data == null || (Array.isArray(data) && data.length === 0) ||
           (data.items && data.items.length === 0));
        if (empty) {
          store.set(cfg.page, cfg.component, "empty", { dataRef: cfg.url, message: cfg.emptyText || "暂无数据" });
          paint("empty", { message: cfg.emptyText || "暂无数据" });
        } else {
          store.set(cfg.page, cfg.component, "success", { dataRef: cfg.url, freshness: "fresh" });
          paint("success");
          if (cfg.render) cfg.render(data, el);
        }
        return data;
      })
      .catch(function (err) {
        var offline = !navigator.onLine;
        var st = offline ? "offline" : "error";
        store.set(cfg.page, cfg.component, st,
          { dataRef: cfg.url, errorCode: (err && err.code) || "FETCH_ERROR",
            message: offline ? "网络已断开" : ((err && err.code) || "加载失败") });
        paint(st, { message: offline ? "网络已断开" : "加载失败" });
        if (cfg.onError) cfg.onError(err);
      });
  }

  /* ---------- Toast ---------- */
  function toast(message, kind) {
    var stack = document.querySelector(".lm-toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "lm-toast-stack";
      document.body.appendChild(stack);
    }
    var t = document.createElement("div");
    t.className = "lm-toast";
    if (kind) t.classList.add("lm-toast--" + kind);
    t.textContent = message;
    stack.appendChild(t);
    setTimeout(function () {
      t.style.opacity = "0";
      setTimeout(function () { t.remove(); }, 200);
    }, 3200);
  }

  /* ---------- 数字 count-up（数据驱动，仅真实值变化） ---------- */
  function countUp(el, to, opts) {
    opts = opts || {};
    var from = parseFloat(el.getAttribute("data-val") || "0") || 0;
    if (from === to) return;
    var dur = opts.duration || 320, start = null;
    el.classList.add("lm-data-update");
    function frame(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var val = from + (to - from) * p;
      el.textContent = opts.format ? opts.format(val) : Math.round(val).toLocaleString();
      if (p < 1) requestAnimationFrame(frame);
      else el.setAttribute("data-val", String(to));
    }
    requestAnimationFrame(frame);
  }

  var LUMENIS = {
    UI_STATES: UI_STATES,
    Theme: Theme,
    store: new StateStore(),
    bindState: bindState,
    toast: toast,
    countUp: countUp
  };
  global.LUMENIS = LUMENIS;

  if (document.readyState !== "loading") Theme.init();
  else document.addEventListener("DOMContentLoaded", function () { Theme.init(); });
})(window);
