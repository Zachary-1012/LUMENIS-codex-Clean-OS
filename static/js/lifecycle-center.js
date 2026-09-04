/* ============================================================
 * 序境 · Lifecycle Center v1.0（生命周期中心 · 函数驱动）
 * 依据 CANONICAL EXECUTION V3 §21-24：
 *   需求/研究/决策/任务/运行时/证据/历史 全链路可追溯
 * 架构：LIFECYCLE_REGISTRY 数据表 → 纯函数 → 唯一 Renderer
 *   - 一个页面只有一个 Renderer Authority（本文件）
 *   - 不制造业务真相，只登记和呈现追溯链
 *   - 双向 Trace：Requirement→Commit / Commit→Requirement
 * ============================================================ */
(function (global) {
  'use strict';

  /* ============================================================
   * 1. 生命周期阶段定义（状态机，V3 §37）
   * ============================================================ */
  var STAGES = [
    { key: 'DISCOVERED',  label: '发现',     desc: '需求被识别' },
    { key: 'RESEARCHED',  label: '研究',     desc: '完成调研与证据' },
    { key: 'DECIDED',     label: '决策',     desc: '方案已决策' },
    { key: 'SPECIFIED',   label: '规格化',   desc: '转换为可执行契约' },
    { key: 'IMPLEMENTED', label: '已实现',   desc: '代码已存在' },
    { key: 'LOADED',      label: '已加载',   desc: '运行时已加载' },
    { key: 'RUNNING',     label: '运行中',   desc: '真实运行' },
    { key: 'TESTED',      label: '已测试',   desc: '测试已运行' },
    { key: 'VERIFIED',    label: '已验证',   desc: '测试与证据通过' },
    { key: 'DELIVERED',   label: '已交付',   desc: '符合交付标准' },
    { key: 'MONITORED',   label: '监控中',   desc: '生产监控' },
    { key: 'IMPROVED',    label: '已改进',   desc: '迭代优化' }
  ];
  var STAGE_INDEX = {};
  STAGES.forEach(function (s, i) { STAGE_INDEX[s.key] = i; });

  // 执行状态（V3 §5，与需求生命周期分离）
  var EXEC_STATUS = ['REGISTERED', 'SYNCED', 'LOADED', 'READY', 'RUNNING', 'UPDATED', 'VERIFIED'];
  var VERIFY_STATUS = ['UNVERIFIED', 'IMPLEMENTED', 'TESTED', 'VERIFIED', 'FAIL', 'BLOCKED'];

  /* ============================================================
   * 2. 生命周期登记表（唯一数据源 · 从真实任务提取）
   *    每条记录必须可追溯：Research→Decision→Requirement→Task→File→Commit
   * ============================================================ */
  var REGISTRY = [
    {
      id: 'REQ-20260904-AI-CHAT-ZHIPU',
      category: 'requirements',
      title: '聊天界面接通智谱 glm-4.5-air',
      stage: 'DELIVERED',
      execStatus: 'RUNNING',
      verifyStatus: 'VERIFIED',
      research: 'R-20260904-AI-CHAT-FIX：定位 per_call 额度不足导致 budget_blocked',
      decision: 'D-20260904-AI-CHAT-PACKID：test_connection 改用 glm_4_5_air 资源包',
      task: 'TASK-20260904-AI-CHAT-FIX',
      files: ['intelligence.py'],
      functions: ['intelligence.test_connection() L346', 'intelligence.chat()'],
      runtime: '8201 /api/ai/test 真实返回 provider=zhipu',
      tests: ['py_compile', 'API smoke test', '/api/ai/status 回归'],
      evidence: 'reply="我监测广州太古汇相关的网络舆情和消费者反馈。"',
      commits: ['801675a', '9949419'],
      next: '监控 token 消耗，其他默认 per_call 调用点逐步切换',
      updated: '2026-09-04 20:47'
    },
    {
      id: 'REQ-20260904-EMOJI-ZERO',
      category: 'requirements',
      title: '状态符号类 emoji 清零（纯 CSS 替代）',
      stage: 'DELIVERED',
      execStatus: 'RUNNING',
      verifyStatus: 'VERIFIED',
      research: '审计 14 个残留符号：5 个 ✕ 关闭符保留，9 个状态符号需处理',
      decision: '正式 icon→xicon()，状态符号→CSS ::before，注释/console 直接去除',
      task: 'TASK-20260904-EMOJI-ZERO',
      files: ['resident_health.js', 'taiji-state.js', 'zbip-shell.js', 'auth_recovery_poller.js', 'zachary_png_face.js', 'xujing-core.css', 'index.html'],
      functions: ['Pure-CSS Status Glyphs (.check/.tj-glyph-done/.zb-check)'],
      runtime: '首页可见 emoji=0，CSS 规则 3/3 注册',
      tests: ['node --check 5/5', 'TreeWalker 可见 emoji 扫描=0', 'CSS rules 注册校验'],
      evidence: '14→5（剩余 5 个为 ✕ 关闭符，非 emoji）',
      commits: ['feb48de'],
      next: 'frontend_enhancement 等历史文件继续按此协议处理',
      updated: '2026-09-04 21:10'
    },
    {
      id: 'REQ-20260904-COLLECTOR-SIX-FIX',
      category: 'requirements',
      title: '采集器 6 项基线修复（熔断/质量门/主体硬过滤）',
      stage: 'DELIVERED',
      execStatus: 'RUNNING',
      verifyStatus: 'VERIFIED',
      research: '双子库基线扫描：熔断死锁、EMPTY 风险分衰减、质量门缺失等 6 项',
      decision: '最小改造，复用现有 guard/limiter/metrics，不重写采集器',
      task: 'TASK-20260904-COLLECTOR-FIX',
      files: ['collector.py', 'collector_guard/guard.py', 'collector_guard/metrics.py'],
      functions: ['guard half-open 探测', 'record_quality() 9 项质量门', 'subject_hit_cdp 硬过滤'],
      runtime: '采集器运行，遵守每日 00:00/12:00 两次 + 手动 30min 边界',
      tests: ['py_compile', '采集状态机回归'],
      evidence: 'metrics.py 87→154 行，9 项质量计数器',
      commits: ['b2c9e62'],
      next: '真实采集窗口验证质量门指标产出',
      updated: '2026-09-04'
    },
    {
      id: 'REQ-20260904-UI-AUTHORITY-LAYER',
      category: 'requirements',
      title: '唯一视觉权威层 xujing-core.css + 六大场景导航',
      stage: 'MONITORED',
      execStatus: 'RUNNING',
      verifyStatus: 'VERIFIED',
      research: '14 个废弃 CSS（9735 行）造成样式覆盖；参考 Apple/iOS/GPT 布局',
      decision: '删除废弃 CSS，新建 xujing-core.css 为唯一权威层，六域 IA 函数化',
      task: 'TASK-20260904-UI-CONVERGE',
      files: ['xujing-core.css', 'xujing-nav.js', 'xj-chat.js', 'xujing-icons.js'],
      functions: ['xnav() 纯函数导航', 'xicon() 图标函数', 'NAV_IA 六域数据表'],
      runtime: '8201 首页六域导航渲染，CSS 最后加载 v5.1.0',
      tests: ['CSS 加载顺序', 'side-item 高度', '六域 28 项可见性'],
      evidence: '14 CSS 物理删除，xujing-core.css 2259+ 行',
      commits: ['fe0aafa', '3ff91ee', '3bf61d3'],
      next: '逐页面核对 14 条 UI 规范、弹窗协议、响应式精修',
      updated: '2026-09-04'
    },
    {
      id: 'REQ-20260904-LIFECYCLE-CENTER',
      category: 'requirements',
      title: 'Lifecycle Center 生命周期中心（本页）',
      stage: 'IMPLEMENTED',
      execStatus: 'LOADED',
      verifyStatus: 'TESTED',
      research: 'V3 §21-24：生命周期必须成为真实系统能力而非 Markdown',
      decision: '独立页面开发，不重构首页；函数驱动 + 单一 Renderer',
      task: 'TASK-20260904-LIFECYCLE-CENTER',
      files: ['static/js/lifecycle-center.js', 'index.html', 'xujing-nav.js', 'xujing-core.css'],
      functions: ['lcRender() 唯一渲染器', 'lcStageFlow()', 'lcTrace()'],
      runtime: '页面独立运行，fixed viewport',
      tests: ['node --check', '实机分类切换', '0 JS error'],
      evidence: '本页面',
      commits: [],
      next: '后端 /api/lifecycle 持久化、git log 自动同步登记',
      updated: '2026-09-04'
    }
  ];

  /* ============================================================
   * 3. 分类定义（左侧栏）
   * ============================================================ */
  var CATEGORIES = [
    { key: 'overview',     label: '总览',     icon: 'chart' },
    { key: 'requirements', label: '需求',     icon: 'list' },
    { key: 'research',     label: '研究',     icon: 'bulb' },
    { key: 'decisions',    label: '决策',     icon: 'check' },
    { key: 'tasks',        label: '任务',     icon: 'gear' },
    { key: 'runtime',       label: '运行时',   icon: 'refresh' },
    { key: 'evidence',     label: '证据',     icon: 'doc' },
    { key: 'history',      label: '历史',     icon: 'clock' }
  ];

  /* ============================================================
   * 4. 纯函数层（无 DOM 副作用，可测试）
   * ============================================================ */

  // 4.1 阶段进度：返回当前阶段索引/总数/百分比
  function lcStageProgress(stage) {
    var idx = STAGE_INDEX[stage] !== undefined ? STAGE_INDEX[stage] : 0;
    return { index: idx, total: STAGES.length - 1, pct: Math.round(idx / (STAGES.length - 1) * 100) };
  }

  // 4.2 按分类筛选记录
  function lcByCategory(category) {
    if (category === 'overview') return REGISTRY.slice();
    if (category === 'research') {
      return REGISTRY.filter(function (r) { return r.research; });
    }
    if (category === 'decisions') {
      return REGISTRY.filter(function (r) { return r.decision; });
    }
    if (category === 'tasks') {
      return REGISTRY.filter(function (r) { return r.task; });
    }
    if (category === 'runtime') {
      return REGISTRY.filter(function (r) { return r.runtime; });
    }
    if (category === 'evidence') {
      return REGISTRY.filter(function (r) { return r.evidence; });
    }
    if (category === 'history') {
      return REGISTRY.slice().sort(function (a, b) { return (b.updated || '').localeCompare(a.updated || ''); });
    }
    return REGISTRY.filter(function (r) { return r.category === category; });
  }

  // 4.3 阶段统计
  function lcStageStats() {
    var stats = {};
    STAGES.forEach(function (s) { stats[s.key] = 0; });
    REGISTRY.forEach(function (r) { if (stats[r.stage] !== undefined) stats[r.stage]++; });
    return stats;
  }

  // 4.4 正向 Trace：Requirement → Commit
  function lcTraceForward(record) {
    return [
      { label: 'Requirement', value: record.id },
      { label: 'Research',    value: record.research || 'UNKNOWN' },
      { label: 'Decision',    value: record.decision || 'UNKNOWN' },
      { label: 'Task',        value: record.task || 'UNKNOWN' },
      { label: 'Files',       value: (record.files || []).join(', ') || 'UNKNOWN' },
      { label: 'Functions',   value: (record.functions || []).join(', ') || 'UNKNOWN' },
      { label: 'Runtime',     value: record.runtime || 'UNKNOWN' },
      { label: 'Tests',       value: (record.tests || []).join(', ') || 'UNKNOWN' },
      { label: 'Evidence',    value: record.evidence || 'UNKNOWN' },
      { label: 'Commits',     value: (record.commits || []).join(', ') || 'PENDING' }
    ];
  }

  // 4.5 反向 Trace：Commit → Requirement
  function lcTraceByCommit(commitSha) {
    var hit = REGISTRY.filter(function (r) {
      return (r.commits || []).some(function (c) { return c.indexOf(commitSha) === 0; });
    });
    return hit;
  }

  // 4.6 状态语义 class
  function lcVerifyClass(v) {
    if (v === 'VERIFIED') return 'lc-ok';
    if (v === 'FAIL') return 'lc-err';
    if (v === 'BLOCKED') return 'lc-warn';
    if (v === 'TESTED') return 'lc-run';
    return 'lc-unk';
  }

  /* ============================================================
   * 5. 唯一 Renderer（本页面所有 DOM 由此产出）
   * ============================================================ */
  var state = { category: 'overview', selectedId: null };

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m];
    });
  }

  // 5.1 阶段流横向条
  function renderStageFlow(stage) {
    var prog = lcStageProgress(stage);
    var html = '<div class="lc-flow">';
    STAGES.forEach(function (s, i) {
      var cls = i < prog.index ? 'done' : (i === prog.index ? 'current' : 'todo');
      html += '<div class="lc-flow-node ' + cls + '" title="' + esc(s.desc) + '"><span class="lc-flow-dot"></span><span class="lc-flow-label">' + esc(s.label) + '</span></div>';
      if (i < STAGES.length - 1) html += '<div class="lc-flow-link ' + (i < prog.index ? 'done' : '') + '"></div>';
    });
    html += '</div>';
    return html;
  }

  // 5.2 记录卡片
  function renderRecordCard(r) {
    var vcls = lcVerifyClass(r.verifyStatus);
    var prog = lcStageProgress(r.stage);
    var commits = (r.commits || []).length ? r.commits.map(function (c) { return '<code>' + esc(c) + '</code>'; }).join(' ') : '<span class="lc-pending">PENDING</span>';
    return '' +
      '<div class="lc-card" data-id="' + esc(r.id) + '">' +
        '<div class="lc-card-head">' +
          '<div class="lc-card-title">' + esc(r.title) + '</div>' +
          '<span class="lc-badge ' + vcls + '">' + esc(r.verifyStatus) + '</span>' +
        '</div>' +
        '<div class="lc-card-meta">' +
          '<span class="lc-id">' + esc(r.id) + '</span>' +
          '<span class="lc-stage-tag">阶段 ' + (prog.index + 1) + '/' + (prog.total + 1) + ' · ' + esc(r.stage) + '</span>' +
          '<span class="lc-exec-tag">' + esc(r.execStatus) + '</span>' +
        '</div>' +
        '<div class="lc-stagebar"><div class="lc-stagebar-fill" style="width:' + prog.pct + '%"></div></div>' +
        '<div class="lc-card-commits">Commits: ' + commits + '</div>' +
        '<div class="lc-card-next">下一步：' + esc(r.next || 'UNKNOWN') + '</div>' +
      '</div>';
  }

  // 5.3 详情（双向 Trace）
  function renderDetail(r) {
    if (!r) return '<div class="lc-empty">选择左侧记录查看完整追溯链</div>';
    var forward = lcTraceForward(r);
    var rows = forward.map(function (node) {
      var isUnknown = node.value === 'UNKNOWN' || node.value === 'PENDING';
      return '<div class="lc-trace-row"><div class="lc-trace-k">' + esc(node.label) + '</div><div class="lc-trace-v ' + (isUnknown ? 'lc-unknown-v' : '') + '">' + esc(node.value) + '</div></div>';
    }).join('');
    return '' +
      '<div class="lc-detail">' +
        '<div class="lc-detail-head">' +
          '<h3>' + esc(r.title) + '</h3>' +
          '<span class="lc-badge ' + lcVerifyClass(r.verifyStatus) + '">' + esc(r.verifyStatus) + '</span>' +
        '</div>' +
        '<div class="lc-detail-section-title">当前生命周期</div>' +
        renderStageFlow(r.stage) +
        '<div class="lc-detail-section-title">正向追溯 · Requirement → Commit</div>' +
        '<div class="lc-trace">' + rows + '</div>' +
        '<div class="lc-detail-section-title">更新时间</div>' +
        '<div class="lc-detail-updated">' + esc(r.updated || 'UNKNOWN') + '</div>' +
      '</div>';
  }

  // 5.4 总览
  function renderOverview() {
    var stats = lcStageStats();
    var total = REGISTRY.length;
    var verified = REGISTRY.filter(function (r) { return r.verifyStatus === 'VERIFIED'; }).length;
    var running = REGISTRY.filter(function (r) { return r.execStatus === 'RUNNING'; }).length;
    var pendingCommit = REGISTRY.filter(function (r) { return !(r.commits || []).length; }).length;

    var kpis = [
      { label: '登记需求', value: total, icon: 'list' },
      { label: '已验证', value: verified, icon: 'check' },
      { label: '运行中', value: running, icon: 'refresh' },
      { label: '待提交', value: pendingCommit, icon: 'warn' }
    ];
    var kpiHtml = kpis.map(function (k) {
      return '<div class="lc-kpi"><div class="lc-kpi-icon">' + (typeof xicon === 'function' ? xicon(k.icon, 18) : '') + '</div><div class="lc-kpi-num">' + k.value + '</div><div class="lc-kpi-label">' + esc(k.label) + '</div></div>';
    }).join('');

    var stageDist = STAGES.filter(function (s) { return stats[s.key] > 0; }).map(function (s) {
      return '<div class="lc-dist-row"><span>' + esc(s.label) + '</span><div class="lc-dist-bar"><div style="width:' + (stats[s.key] / total * 100) + '%"></div></div><b>' + stats[s.key] + '</b></div>';
    }).join('');

    return '' +
      '<div class="lc-overview">' +
        '<div class="lc-kpi-grid">' + kpiHtml + '</div>' +
        '<div class="lc-overview-cols">' +
          '<div class="lc-panel-block"><h4>阶段分布</h4>' + stageDist + '</div>' +
          '<div class="lc-panel-block"><h4>状态机说明</h4>' +
            '<div class="lc-state-note">需求生命周期与执行状态分离（V3 §5）：lifecycle_stage / execution_status / verification_status 三字段独立，禁止混用。</div>' +
            '<div class="lc-state-flow">' + STAGES.map(function (s) { return '<span class="lc-state-chip">' + esc(s.label) + '</span>'; }).join('<i>→</i>') + '</div>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  // 5.5 主渲染（唯一入口）
  function lcRender() {
    var root = document.getElementById('page-lifecycle');
    if (!root) return;
    var body = root.querySelector('.lc-body');
    var side = root.querySelector('.lc-cats');
    if (!body || !side) return;

    // 左侧分类
    side.innerHTML = CATEGORIES.map(function (c) {
      var active = state.category === c.key ? ' active' : '';
      var icon = typeof xicon === 'function' ? xicon(c.icon, 16) : '';
      return '<button class="lc-cat' + active + '" data-cat="' + c.key + '">' + icon + '<span>' + esc(c.label) + '</span></button>';
    }).join('');

    // 右侧内容
    if (state.category === 'overview') {
      body.innerHTML = renderOverview();
      bindCards();
      return;
    }

    var list = lcByCategory(state.category);
    if (state.category === 'research') {
      body.innerHTML = '<div class="lc-section-list">' + list.map(function (r) {
        return '<div class="lc-note-row"><span class="lc-id">' + esc(r.id) + '</span><div class="lc-note-body">' + esc(r.research) + '</div></div>';
      }).join('') + '</div>';
      return;
    }
    if (state.category === 'decisions') {
      body.innerHTML = '<div class="lc-section-list">' + list.map(function (r) {
        return '<div class="lc-note-row"><span class="lc-id">' + esc(r.id) + '</span><div class="lc-note-body">' + esc(r.decision) + '</div></div>';
      }).join('') + '</div>';
      return;
    }

    var cards = list.map(renderRecordCard).join('');
    var selected = state.selectedId ? REGISTRY.filter(function (r) { return r.id === state.selectedId; })[0] : null;
    body.innerHTML = '<div class="lc-split"><div class="lc-list">' + (cards || '<div class="lc-empty">该分类暂无记录</div>') + '</div><div class="lc-detail-wrap">' + renderDetail(selected) + '</div></div>';
    bindCards();
  }

  function bindCards() {
    var root = document.getElementById('page-lifecycle');
    if (!root) return;
    root.querySelectorAll('.lc-cat').forEach(function (btn) {
      btn.onclick = function () {
        state.category = btn.getAttribute('data-cat');
        state.selectedId = null;
        lcRender();
      };
    });
    root.querySelectorAll('.lc-card').forEach(function (card) {
      card.onclick = function () {
        state.selectedId = card.getAttribute('data-id');
        root.querySelectorAll('.lc-card').forEach(function (c) { c.classList.remove('selected'); });
        card.classList.add('selected');
        var r = REGISTRY.filter(function (x) { return x.id === state.selectedId; })[0];
        var detailWrap = root.querySelector('.lc-detail-wrap');
        if (detailWrap) detailWrap.innerHTML = renderDetail(r);
      };
    });
  }

  /* ============================================================
   * 6. 对外 API（只读查询 + 渲染）
   * ============================================================ */
  global.LifecycleCenter = {
    render: lcRender,
    registry: function () { return REGISTRY.slice(); },
    traceByCommit: lcTraceByCommit,
    stageProgress: lcStageProgress,
    stages: STAGES,
    register: function (rec) {
      // 登记新记录（必须字段齐全，缺字段标记 UNKNOWN，不允许猜测）
      if (!rec || !rec.id) return false;
      if (REGISTRY.some(function (r) { return r.id === rec.id; })) return false;
      REGISTRY.push(rec);
      lcRender();
      return true;
    }
  };

  // 页面切换到 lifecycle 时懒加载（与 navigateTo 懒加载协议一致）
  global.renderLifecyclePage = lcRender;

})(window);
