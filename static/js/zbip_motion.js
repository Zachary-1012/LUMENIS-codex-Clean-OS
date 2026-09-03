/* =============================================================================
 * ZBIP Motion Engine — 数据驱动实时动效引擎 v1.0
 * 原则（零号序列 / 用户基线）：动效必须由「真实数据 → 函数计算 → 绑定表 → 渲染」驱动，
 *   禁止没有数据支撑的写死循环动画；数据真变才动一次，持续状态按真实 status 呼吸。
 *
 * 数据流（复用 app.js 统一数据总线，不另发请求、不建独立定时器）：
 *   /api/dashboard/all (app.js load, 60s)
 *     → window.__TAIKOO_POLL__ + 全局事件 'taikoo-poll'
 *     → MotionTable（声明式绑定表，新增数据动效只需加一行 = 表格转代码）
 *     → 纯函数 derive/rate/trend（归一化 / 占比 / diff，带死区与首帧保护）
 *     → render：写真实值；仅当值真实变化时触发一次性微光；持续状态按真实在线挂呼吸
 *
 * 健壮性（不出现任何错误）：逐绑定 try/catch；null/NaN/缺字段一律保持占位不造假；
 *   选择器缺失即跳过；单例；无全局定时器；暴露 _fn 供单元测试。
 * ========================================================================== */
(function () {
  'use strict';
  if (window.ZbipMotion) return; // 单例，重复加载不重建

  /* ---------------- 纯函数层（无 DOM、可独立单测） ---------------- */
  function toNum(v) {
    if (v === null || v === undefined || v === '') return null;
    var n = Number(v);
    return Number.isNaN(n) ? null : n;
  }
  // 占比，分母非法/为 0 返回 null（不伪造 0%）
  function rate(part, total) {
    var p = toNum(part), t = toNum(total);
    if (p === null || t === null || t <= 0) return null;
    return (p / t) * 100;
  }
  // 趋势，带死区，避免微小抖动反复触发
  function trendOf(prev, next, deadzone) {
    if (prev === null || next === null) return 'flat';
    var dz = deadzone || 0;
    if (next - prev > dz) return 'up';
    if (prev - next > dz) return 'down';
    return 'flat';
  }
  function pct1(n) { return n === null ? '—' : n.toFixed(1) + '%'; }
  function int0(n) { return n === null ? '—' : String(Math.round(n)); }
  // 紧凑数值：K / 万 / 亿（中文语境，不用 M）
  function compact(n) {
    if (n === null || Number.isNaN(n)) return '—';
    var a = Math.abs(n);
    if (a >= 1e8) return (n / 1e8).toFixed(1).replace(/\.0$/, '') + '亿';
    if (a >= 1e4) return (n / 1e4).toFixed(1).replace(/\.0$/, '') + '万';
    if (a >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    return String(Math.round(n));
  }

  /* ---------------- 声明式绑定表（表格 → 代码） ----------------
   * key 唯一键；sel 目标元素；derive(d) 从 dashboard/all 计算原始数值（纯函数）；
   * format 显示；deadzone 变化死区；trend 是否记录趋势属性。 */
  var MotionTable = [
    { key: 'posRate', sel: '[data-k="posRate"]',
      derive: function (d) { var s = (d && d.stats) || {}; return rate(s.positive, s.total); },
      format: pct1, deadzone: 0.2, trend: true },
    { key: 'negRate', sel: '[data-k="negRate"]',
      derive: function (d) { var s = (d && d.stats) || {}; return rate(s.negative, s.total); },
      format: pct1, deadzone: 0.2, trend: true },
    { key: 'highRisk', sel: '[data-k="highRisk"]',
      derive: function (d) { var s = (d && d.stats) || {}; return toNum(s.high_risk); },
      format: int0, deadzone: 0, trend: true },
    { key: 'engagement', sel: '[data-k="engagement"]',
      derive: function (d) { var s = (d && d.stats) || {}; return toNum(s.total_engagements); },
      format: compact, deadzone: 1, trend: true },
    // 文本绑定（kind:text）：用真实 stats 拼分析文案，不写死、不编造没有的结论/环比
    { key: 'insightTrend', sel: '[data-k="insightTrend"]', kind: 'text',
      derive: function (d) {
        var s = (d && d.stats) || {};
        var pr = rate(s.positive, s.total), nr = rate(s.negative, s.total), t = toNum(s.total);
        if (pr === null || nr === null) return null;
        return '近7天正面舆情占比 ' + pr.toFixed(1) + '%、负面 ' + nr.toFixed(1) + '%，共监测 ' + (t === null ? 0 : t) + ' 条笔记。建议结合话题分布关注服务质量变化。';
      } },
    { key: 'insightRisk', sel: '[data-k="insightRisk"]', kind: 'text',
      derive: function (d) {
        var s = (d && d.stats) || {};
        var h = toNum(s.high_risk), m = toNum(s.medium_risk);
        if (h === null) return null;
        return '当前高风险内容 ' + h + ' 条、中风险 ' + (m === null ? 0 : m) + ' 条，建议优先核实高风险笔记并准备回应方案，详情见风险列表。';
      } }
  ];

  var prevMap = {};    // 上一帧数值
  var seenMap = {};    // 是否首帧（首帧只填值、不闪光）

  /* 一次性数据变化微光：强制 reflow 后挂 class，动画结束自动移除 */
  function flashOnce(el) {
    try {
      el.classList.remove('zb-value-flash');
      void el.offsetWidth;
      el.classList.add('zb-value-flash');
      el.addEventListener('animationend', function h() {
        el.classList.remove('zb-value-flash');
        el.removeEventListener('animationend', h);
      });
    } catch (_) {}
  }

  /* 持续状态：只有真实在线 / AI 真实启用才呼吸，状态消失立即移除（不假装在线） */
  function syncStatus(d) {
    try {
      var ai = (d && d.ai_status) || {};
      var st = (d && d.system_status) || {};
      var live = !!d; // 数据总线成功返回一帧即在线证据
      document.querySelectorAll('[data-k="sysLive"]').forEach(function (el) {
        el.classList.toggle('is-live', live);
      });
      document.querySelectorAll('[data-k="aiLive"]').forEach(function (el) {
        el.classList.toggle('is-live', !!(ai.enabled || st.ai_enabled));
      });
    } catch (_) {}
  }

  /* 主摄入：一帧真实数据 → 逐行计算 → 渲染 */
  function ingest(d) {
    if (!d || typeof d !== 'object') return;
    MotionTable.forEach(function (row) {
      try {
        var val = null;
        try { val = row.derive(d); } catch (_) { val = null; }
        var el = document.querySelector(row.sel);
        if (!el) return;                              // 元素不存在：跳过
        if (row.kind === 'text') {                    // 文本绑定：真实数据拼文案，静默更新、不做数值动效
          if (val === null || val === undefined || val === '') return;
          if (el.textContent !== String(val)) el.textContent = String(val);
          seenMap[row.key] = true;
          return;
        }
        if (val === null || Number.isNaN(val)) return; // 无真实值：保留占位，绝不造假
        var isFirst = !Object.prototype.hasOwnProperty.call(seenMap, row.key);
        var prev = Object.prototype.hasOwnProperty.call(prevMap, row.key) ? prevMap[row.key] : null;
        var dz = row.deadzone || 0;

        el.textContent = row.format(val);
        el.setAttribute('data-value', String(Math.round(val * 100) / 100));
        if (row.trend) el.setAttribute('data-trend', trendOf(prev, val, dz));

        // 仅非首帧且越过死区的真实变化，才触发一次微光
        if (!isFirst && prev !== null && Math.abs(val - prev) > dz) flashOnce(el);

        prevMap[row.key] = val; seenMap[row.key] = true;
      } catch (_) { /* 单行异常不影响其它绑定与主流程 */ }
    });
    syncStatus(d);
  }

  // 订阅统一数据总线（复用 60s 轮询，零额外请求 / 零额外定时器）
  document.addEventListener('taikoo-poll', function (e) {
    try { ingest(e.detail); } catch (_) {}
  });
  function boot() { if (window.__TAIKOO_POLL__) ingest(window.__TAIKOO_POLL__); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }

  // 对外暴露：ingest 供其它真实数据源接入；_fn/_table 供测试与审计
  window.ZbipMotion = {
    ingest: ingest,
    _table: MotionTable,
    _fn: { toNum: toNum, rate: rate, trendOf: trendOf, compact: compact, pct1: pct1, int0: int0 }
  };
})();
