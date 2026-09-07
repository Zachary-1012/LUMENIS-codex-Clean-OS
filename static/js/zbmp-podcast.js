/* ============================================================
 * ZBMP Podcast Studio · 前端交互层
 * 对接 /api/podcast/* + /api/content/* 共 11 个端点
 * 纯原生 JS/CSS 自研可视化，不引入第三方图表库
 * ============================================================ */
(function (global) {
  'use strict';

  /* ---------- 工具 ---------- */
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function fmtMs(ms) {
    if (ms == null) return '-';
    var s = Math.floor(ms / 1000);
    var m = Math.floor(s / 60);
    s = s % 60;
    return (m > 0 ? m + 'm ' : '') + s + 's';
  }
  function pct(v) { return (Math.round(v * 100) / 100) + '%'; }
  function escapeHtml(s) { if (s == null) return ''; return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function escapeAttr(s) { return escapeHtml(s).replace(/'/g, '&#39;'); }

  /* POST JSON，走 LUMENIS.fetch（带 auth），回退原生 fetch */
  function postJSON(url, body) {
    var opts = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    };
    if (global.LUMENIS && LUMENIS.fetch) {
      return LUMENIS.fetch(url, opts).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          if (!r.ok) throw new Error((d && d.error) || ('HTTP ' + r.status));
          return d;
        });
      });
    }
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error((d && d.error) || ('HTTP ' + r.status));
        return d;
      });
    });
  }

  /* GET，走 xjViz.api（prepend /api/），回退原生 fetch */
  function getJSON(path) {
    if (global.xjViz && xjViz.api) return xjViz.api(path);
    return fetch('/api' + path).then(function (r) { return r.json(); });
  }

  /* ============================================================
   * 1. Overview & Entities
   * ============================================================ */
  function loadOverview() {
    getJSON('/podcast/overview').then(function (d) {
      var stats = (d && d.stats) || {};
      var total = stats.total || 0;
      var byType = stats.by_type || {};
      var byEvidence = stats.by_evidence || {};
      var typeKeys = Object.keys(byType);
      var topType = typeKeys.length ? typeKeys[0] + ': ' + byType[typeKeys[0]] : '暂无';

      if (global.xjViz) {
        xjViz.kpi('#podcast-kpi-entities', '实体总数', total, { sub: 'by_type: ' + Object.keys(byType).length });
        xjViz.kpi('#podcast-kpi-topics', '选题能力', 10, { sub: '10 维度确定性打分' });
        xjViz.kpi('#podcast-kpi-stories', '节点类型', 7, { sub: 'story/conflict/reveal/...' });
        xjViz.kpi('#podcast-kpi-runtime', '运行时校验', 1, { sub: '单调递增 · 非重叠' });
      }
      $('podcast-overview-panel').setAttribute('data-state', 'success');
    }).catch(function (e) {
      if (global.xjViz) {
        xjViz.kpi('#podcast-kpi-entities', '实体总数', 0, { sub: 'API 已注册' });
        xjViz.kpi('#podcast-kpi-topics', '选题能力', 10, { sub: '10 维度' });
        xjViz.kpi('#podcast-kpi-stories', '节点类型', 7, { sub: '' });
        xjViz.kpi('#podcast-kpi-runtime', '运行时', 0, { sub: 'STANDBY' });
      }
      $('podcast-overview-panel').setAttribute('data-state', 'degraded');
      console.warn('[podcast] overview:', e.message);
    });
  }

  function loadEntities() {
    getJSON('/podcast/entities?limit=100').then(function (d) {
      var entities = (d && d.entities) || [];
      var count = d && d.returned != null ? d.returned : entities.length;
      $('podcast-entity-count').textContent = count + ' entities';
      var box = $('podcast-entities-content');
      if (!entities.length) {
        $('podcast-entities-empty').style.display = '';
        $('podcast-entities-panel').setAttribute('data-state', 'empty');
        return;
      }
      var html = '<div class="xj-data-table-wrap"><table class="xj-data-table"><thead><tr>'
        + '<th>entity_id</th><th>类型</th><th>标题</th><th>证据状态</th><th>置信度</th><th>时长</th>'
        + '</tr></thead><tbody>';
      entities.forEach(function (e) {
        html += '<tr>'
          + '<td>' + (e.entity_id || '-') + '</td>'
          + '<td><span class="lm-badge">' + (e.entity_type || '-') + '</span></td>'
          + '<td>' + (e.title || '-') + '</td>'
          + '<td>' + (e.evidence_status || '-') + '</td>'
          + '<td>' + (e.confidence != null ? pct(e.confidence) : '-') + '</td>'
          + '<td>' + (e.start_ms != null ? fmtMs(e.start_ms) + ' – ' + fmtMs(e.end_ms) : '-') + '</td>'
          + '</tr>';
      });
      html += '</tbody></table></div>';
      box.innerHTML = html;
      $('podcast-entities-empty').style.display = 'none';
      $('podcast-entities-panel').setAttribute('data-state', 'success');
    }).catch(function () {
      $('podcast-entities-empty').style.display = '';
      $('podcast-entities-panel').setAttribute('data-state', 'empty');
    });
  }

  /* ============================================================
   * 2. 选题打分（10 维度滑块）
   * ============================================================ */
  var DIMENSIONS = [
    { key: 'demand',          label: '需求强度', weight: 0.16, positive: true  },
    { key: 'timeliness',      label: '时效性',   weight: 0.12, positive: true  },
    { key: 'novelty',         label: '新颖度',   weight: 0.10, positive: true  },
    { key: 'human_relevance', label: '人物关联', weight: 0.14, positive: true  },
    { key: 'guest_fit',       label: '嘉宾适配', weight: 0.12, positive: true  },
    { key: 'evidence',        label: '证据密度', weight: 0.10, positive: true  },
    { key: 'content_yield',   label: '内容产出', weight: 0.10, positive: true  },
    { key: 'distribution',    label: '分发潜力', weight: 0.06, positive: true  },
    { key: 'risk',            label: '风险',     weight: 0.05, positive: false },
    { key: 'cost',            label: '成本',     weight: 0.05, positive: false }
  ];

  var STAGE_LABELS = {
    rejected:  { label: '淘汰',   color: '#c0463a' },
    watch:     { label: '观察',   color: '#a07a2a' },
    evergreen: { label: '常青',   color: '#2f6e9e' },
    soon:      { label: '近期可做', color: '#2f9e6e' },
    now:       { label: '立即做', color: '#1a7a4a' }
  };

  function buildTopicForm() {
    var box = $('topic-sliders');
    var html = '';
    DIMENSIONS.forEach(function (dim) {
      var valId = 'topic-val-' + dim.key;
      html += '<div class="podcast-slider-row">'
        + '<div class="podcast-slider-label">'
        + '<span>' + dim.label + '</span>'
        + '<span class="podcast-slider-weight" title="权重">' + pct(dim.weight) + '</span>'
        + '</div>'
        + '<div class="podcast-slider-track">'
        + '<input type="range" min="0" max="100" value="50" data-key="' + dim.key + '" class="podcast-slider" id="topic-input-' + dim.key + '">'
        + '<span class="podcast-slider-value" id="' + valId + '">0.50</span>'
        + '</div>'
        + '</div>';
    });
    box.innerHTML = html;

    var sliders = box.querySelectorAll('.podcast-slider');
    sliders.forEach(function (s) {
      s.addEventListener('input', function () {
        var key = s.getAttribute('data-key');
        $('topic-val-' + key).textContent = (s.value / 100).toFixed(2);
        updateLiveScore();
      });
    });
    updateLiveScore();
  }

  function readSignals() {
    var sig = {};
    DIMENSIONS.forEach(function (d) {
      var s = $('topic-input-' + d.key);
      sig[d.key] = s ? (parseInt(s.value, 10) / 100) : 0;
    });
    return sig;
  }

  function computeLocalScore(sig) {
    var positive = 0;
    DIMENSIONS.forEach(function (d) {
      if (d.positive) positive += d.weight * sig[d.key];
    });
    var penalty = 0.05 * sig.risk + 0.05 * sig.cost;
    return Math.round(100 * Math.max(0, Math.min(1, positive - penalty)) * 100) / 100;
  }

  function updateLiveScore() {
    var sig = readSignals();
    var score = computeLocalScore(sig);
    $('topic-live-score').textContent = score.toFixed(1);
    var stage = 'watch';
    if (score < 35) stage = 'rejected';
    else if (sig.timeliness >= 0.85) stage = 'now';
    else if (score >= 75) stage = 'soon';
    else if (score >= 55) stage = 'evergreen';
    var sl = STAGE_LABELS[stage];
    var badge = $('topic-live-stage');
    badge.textContent = sl.label;
    badge.style.color = sl.color;
    badge.style.borderColor = sl.color;
  }

  function submitTopicScore() {
    var sig = readSignals();
    var btn = $('topic-submit-btn');
    btn.disabled = true;
    btn.textContent = '计算中…';
    postJSON('/api/podcast/topic-score', { signals: sig }).then(function (d) {
      var r = d || {};
      $('topic-result-score').textContent = r.score != null ? r.score : '-';
      var stageKey = r.stage || 'watch';
      var sl = STAGE_LABELS[stageKey] || STAGE_LABELS.watch;
      var sb = $('topic-result-stage');
      sb.textContent = sl.label;
      sb.style.color = sl.color;
      sb.style.borderColor = sl.color;

      var signals = r.signals || {};
      var weights = r.weights || {};
      var html = '';
      DIMENSIONS.forEach(function (dim) {
        var v = signals[dim.key] != null ? signals[dim.key] : 0;
        var w = weights[dim.key] != null ? weights[dim.key] : dim.weight;
        var contrib = dim.positive ? (v * w) : -(v * w);
        var barW = Math.abs(contrib) * 100 * 5;
        var color = dim.positive ? '#2f9e6e' : '#c0463a';
        html += '<div class="podcast-contrib-row">'
          + '<span class="podcast-contrib-label">' + dim.label + '</span>'
          + '<div class="podcast-contrib-bar-wrap">'
          + '<div class="podcast-contrib-bar" style="width:' + Math.min(100, barW) + '%;background:' + color + ';"></div>'
          + '</div>'
          + '<span class="podcast-contrib-val" style="color:' + color + ';">'
          + (dim.positive ? '+' : '') + (contrib * 100).toFixed(1)
          + '</span></div>';
      });
      $('topic-contrib-detail').innerHTML = html;
      $('topic-result-panel').style.display = '';
    }).catch(function (e) {
      $('topic-result-error').textContent = '打分失败: ' + e.message;
      $('topic-result-error').style.display = '';
    }).finally(function () {
      btn.disabled = false;
      btn.textContent = '提交打分';
    });
  }

  /* ============================================================
   * 3. 故事节点可视化（时间线 + 节点卡片）
   * ============================================================ */
  var NODE_TYPE_COLORS = {
    story:        '#4a7fb5',
    conflict:     '#c0463a',
    reveal:       '#9b59b6',
    emotion_peak: '#e67e22',
    insight_peak: '#2f9e6e',
    quote:        '#7f8c8d',
    problem:      '#a07a2a'
  };
  var NODE_TYPE_LABELS = {
    story: '故事', conflict: '冲突', reveal: '揭示',
    emotion_peak: '情绪峰值', insight_peak: '洞察峰值',
    quote: '金句', problem: '问题'
  };

  var DEFAULT_SEGMENTS = [
    { segment_id: 's0', start_ms: 0,     end_ms: 120000,  node_type: 'story',        text: '开场引入嘉宾背景与本期话题', confidence: 0.85, rationale: '建立语境' },
    { segment_id: 's1', start_ms: 120000, end_ms: 300000, node_type: 'conflict',     text: '核心矛盾展开：职业选择与家庭期待', confidence: 0.9, rationale: '冲突驱动叙事' },
    { segment_id: 's2', start_ms: 300000, end_ms: 480000, node_type: 'emotion_peak', text: '情绪爆发：讲述低谷期的真实感受', confidence: 0.95, rationale: '情感高点' },
    { segment_id: 's3', start_ms: 480000, end_ms: 660000, node_type: 'reveal',       text: '转折点：意外机会出现', confidence: 0.8, rationale: '叙事反转' },
    { segment_id: 's4', start_ms: 660000, end_ms: 840000, node_type: 'insight_peak', text: '洞察提炼：对行业的反思与建议', confidence: 0.88, rationale: '认知高点' },
    { segment_id: 's5', start_ms: 840000, end_ms: 960000, node_type: 'quote',        text: '金句收束与下期预告', confidence: 0.75, rationale: '可剪辑素材' }
  ];

  function loadStoryNodes() {
    $('story-input').value = JSON.stringify(DEFAULT_SEGMENTS, null, 2);
    fetchStoryNodes(DEFAULT_SEGMENTS);
  }

  function fetchStoryNodes(segments) {
    var panel = $('story-panel');
    panel.setAttribute('data-state', 'loading');
    postJSON('/api/podcast/story-nodes', { segments: segments }).then(function (d) {
      var nodes = (d && d.nodes) || [];
      renderStoryNodes(nodes);
      panel.setAttribute('data-state', 'success');
    }).catch(function (e) {
      $('story-error').textContent = '故事节点提取失败: ' + e.message;
      $('story-error').style.display = '';
      panel.setAttribute('data-state', 'error');
    });
  }

  function submitStoryNodes() {
    try {
      var segs = JSON.parse($('story-input').value);
      if (!Array.isArray(segs)) throw new Error('必须是数组');
      $('story-error').style.display = 'none';
      fetchStoryNodes(segs);
    } catch (e) {
      $('story-error').textContent = 'JSON 解析失败: ' + e.message;
      $('story-error').style.display = '';
    }
  }

  function renderStoryNodes(nodes) {
    if (!nodes.length) {
      $('story-timeline').innerHTML = '<div class="xj-empty">暂无节点</div>';
      $('story-node-cards').innerHTML = '';
      return;
    }
    var maxEnd = Math.max.apply(null, nodes.map(function (n) { return n.end_ms || 0; }));
    maxEnd = maxEnd || 1;

    var tl = '<div class="podcast-timeline">';
    nodes.forEach(function (n) {
      var left = ((n.start_ms || 0) / maxEnd) * 100;
      var width = Math.max(1, ((n.end_ms - n.start_ms) / maxEnd) * 100);
      var color = NODE_TYPE_COLORS[n.node_type] || '#666';
      tl += '<div class="podcast-tl-node" style="left:' + left.toFixed(2) + '%;width:' + width.toFixed(2)
        + '%;background:' + color + ';" title="' + (NODE_TYPE_LABELS[n.node_type] || n.node_type)
        + ' · ' + fmtMs(n.start_ms) + '–' + fmtMs(n.end_ms) + '">'
        + '<span class="podcast-tl-node-label">' + (NODE_TYPE_LABELS[n.node_type] || n.node_type) + '</span>'
        + '</div>';
    });
    tl += '</div>';
    tl += '<div class="podcast-timeline-scale">';
    for (var i = 0; i <= 4; i++) {
      var t = Math.round((maxEnd / 4) * i);
      tl += '<span style="left:' + (i * 25) + '%;">' + fmtMs(t) + '</span>';
    }
    tl += '</div>';
    $('story-timeline').innerHTML = tl;

    var cards = '';
    nodes.forEach(function (n, idx) {
      var color = NODE_TYPE_COLORS[n.node_type] || '#666';
      cards += '<div class="podcast-node-card" style="border-left-color:' + color + ';">'
        + '<div class="podcast-node-card-head">'
        + '<span class="podcast-node-index">#' + (idx + 1) + '</span>'
        + '<span class="lm-badge" style="background:' + color + ';color:#fff;border:none;">'
        + (NODE_TYPE_LABELS[n.node_type] || n.node_type) + '</span>'
        + '<span class="podcast-node-time">' + fmtMs(n.start_ms) + ' – ' + fmtMs(n.end_ms) + '</span>'
        + '</div>'
        + (n.rationale ? '<div class="podcast-node-rationale">' + n.rationale + '</div>' : '')
        + '<div class="podcast-node-meta">'
        + '<span>segments: ' + (n.segment_ids || []).join(', ') + '</span>'
        + '<span>confidence: ' + (n.confidence != null ? pct(n.confidence) : '-') + '</span>'
        + '</div>'
        + '</div>';
    });
    $('story-node-cards').innerHTML = cards;
  }

  /* ============================================================
   * 4. 破圈分类
   * ============================================================ */
  var BREAKOUT_LABELS = {
    normal:         { label: '正常',     color: '#6b7280' },
    accelerating:   { label: '加速中',   color: '#2f6e9e' },
    breakout:       { label: '破圈',     color: '#2f9e6e' },
    viral:          { label: '病毒传播', color: '#1a7a4a' },
    underperforming:{ label: '表现不佳', color: '#a07a2a' },
    decaying:       { label: '衰减中',   color: '#c0463a' }
  };

  function submitBreakout() {
    var current = parseFloat($('breakout-current').value);
    var baseline = parseFloat($('breakout-baseline').value);
    var br = parseFloat($('breakout-ratio').value) || 1.8;
    var vr = parseFloat($('breakout-viral').value) || 3.0;
    if (isNaN(current) || isNaN(baseline)) {
      $('breakout-result').innerHTML = '<span style="color:#c0463a;">请输入有效数值</span>';
      return;
    }
    postJSON('/api/podcast/breakout', {
      current: current, baseline: baseline,
      breakout_ratio: br, viral_ratio: vr
    }).then(function (d) {
      var state = (d && d.data && d.data.state) || d.state || 'normal';
      var bl = BREAKOUT_LABELS[state] || BREAKOUT_LABELS.normal;
      var ratio = baseline > 0 ? (current / baseline) : 0;
      var html = '<div class="podcast-breakout-result">'
        + '<div class="podcast-breakout-state" style="color:' + bl.color + ';border-color:' + bl.color + ';">'
        + bl.label + '</div>'
        + '<div class="podcast-breakout-metrics">'
        + '<div><span class="podcast-metric-label">当前值</span><span class="podcast-metric-val">' + current + '</span></div>'
        + '<div><span class="podcast-metric-label">基线值</span><span class="podcast-metric-val">' + baseline + '</span></div>'
        + '<div><span class="podcast-metric-label">倍数</span><span class="podcast-metric-val">' + ratio.toFixed(2) + 'x</span></div>'
        + '</div>'
        + '<div class="podcast-breakout-bar-wrap">'
        + '<div class="podcast-breakout-bar-bg"></div>'
        + '<div class="podcast-breakout-bar-fill" style="width:' + Math.min(100, ratio * 25) + '%;background:' + bl.color + ';"></div>'
        + '<div class="podcast-breakout-threshold" style="left:' + (1.8 * 25) + '%;" title="破圈阈值 1.8x"></div>'
        + '<div class="podcast-breakout-threshold" style="left:' + (3.0 * 25) + '%;" title="病毒阈值 3.0x"></div>'
        + '</div>'
        + '<div class="podcast-breakout-legend">'
        + '<span>0x</span><span>1.8x 破圈</span><span>3.0x 病毒</span><span>4x+</span>'
        + '</div></div>';
      $('breakout-result').innerHTML = html;
    }).catch(function (e) {
      $('breakout-result').innerHTML = '<span style="color:#c0463a;">破圈分类失败: ' + e.message + '</span>';
    });
  }

  /* ============================================================
   * 5. 内容产出率
   * ============================================================ */
  function submitContentYield() {
    var body = {
      story_count: parseInt($('yield-story').value, 10) || 0,
      insight_count: parseInt($('yield-insight').value, 10) || 0,
      emotion_peak_count: parseInt($('yield-emotion').value, 10) || 0,
      quote_count: parseInt($('yield-quote').value, 10) || 0,
      evidence_count: parseInt($('yield-evidence').value, 10) || 0
    };
    postJSON('/api/podcast/content-yield', body).then(function (d) {
      var plan = (d && d.data && d.data.plan) || d.plan || {};
      var assets = plan.assets || [];
      var rationale = plan.rationale || [];
      var ASSET_LABELS = {
        full_episode: '完整节目', chapter: '章节导航', clip: '剪辑片段',
        quote: '金句卡', short_video: '短视频', article: '长文',
        social_post: '社媒文案', newsletter: '通讯', research_node: '研究节点'
      };
      var html = '<div class="podcast-yield-assets">';
      assets.forEach(function (a) {
        html += '<span class="podcast-yield-asset">' + (ASSET_LABELS[a] || a) + '</span>';
      });
      html += '</div><div class="podcast-yield-rationale">';
      rationale.forEach(function (r) {
        html += '<div class="podcast-yield-rationale-item">• ' + r + '</div>';
      });
      html += '</div>';
      $('yield-result').innerHTML = html;
    }).catch(function (e) {
      $('yield-result').innerHTML = '<span style="color:#c0463a;">内容产出规划失败: ' + e.message + '</span>';
    });
  }

  /* ============================================================
   * 6. 运行时校验
   * ============================================================ */
  var DEFAULT_RUNTIME_SEGMENTS = [
    { segment_id: 'r0', start_ms: 0,      end_ms: 60000,   kind: 'opening' },
    { segment_id: 'r1', start_ms: 60000,  end_ms: 300000,  kind: 'story' },
    { segment_id: 'r2', start_ms: 300000, end_ms: 420000,  kind: 'conflict' },
    { segment_id: 'r3', start_ms: 420000, end_ms: 540000,  kind: 'emotion' },
    { segment_id: 'r4', start_ms: 540000, end_ms: 660000,  kind: 'insight' },
    { segment_id: 'r5', start_ms: 660000, end_ms: 720000,  kind: 'ending' }
  ];

  function loadRuntimeValidate() {
    $('runtime-input').value = JSON.stringify(DEFAULT_RUNTIME_SEGMENTS, null, 2);
    submitRuntimeValidate();
  }

  function submitRuntimeValidate() {
    try {
      var segs = JSON.parse($('runtime-input').value);
      if (!Array.isArray(segs)) throw new Error('必须是数组');
      $('runtime-error').style.display = 'none';
      postJSON('/api/podcast/runtime/validate', { segments: segs }).then(function (d) {
        var r = d || {};
        var html = '';
        if (r.valid) {
          html = '<div class="podcast-runtime-valid">'
            + '<span class="podcast-runtime-icon">✓</span>'
            + '<div><strong>校验通过</strong>'
            + '<div>分段数: ' + (r.segment_count || 0) + ' · 总时长: '
            + (r.total_runtime_seconds != null ? r.total_runtime_seconds + 's' : '-') + '</div></div></div>';
        } else {
          html = '<div class="podcast-runtime-invalid">'
            + '<span class="podcast-runtime-icon">✗</span>'
            + '<div><strong>校验失败</strong>'
            + '<div>' + (r.reason || '未知错误') + '</div></div></div>';
        }
        $('runtime-result').innerHTML = html;
      }).catch(function (e) {
        $('runtime-result').innerHTML = '<div class="podcast-runtime-invalid">'
          + '<span class="podcast-runtime-icon">✗</span>'
          + '<div><strong>请求失败</strong><div>' + e.message + '</div></div></div>';
      });
    } catch (e) {
      $('runtime-error').textContent = 'JSON 解析失败: ' + e.message;
      $('runtime-error').style.display = '';
    }
  }

  /* ============================================================
   * 7. 案例：凉子访谈录（嵌入静态内容）
   * ============================================================ */
  var LIANGZI_CASE = {
    title: '《凉子访谈录》— Benchmark Case V1',
    role: '播客研究库首个基准案例。作为研究目标，而非断言所有观察特征均具因果性或代表性。',
    layers: [
      { name: 'A. IP 层', items: ['节目定位与身份', '主持人身份与访谈风格', '嘉宾选择逻辑', ' recurring narrative promise', '系列/栏目架构'] },
      { name: 'B. 单集层', items: ['发布时间', '时长', '开场结构', '首个有效钩子', '问题序列', '故事转折', '冲突/反转', '情绪峰值', '洞察峰值', '结尾 / CTA'] },
      { name: 'C. 信息层', items: ['每个实质主张保留来源 URL/locator', '发布者、发布时间、观察时间', '内容哈希（如有）', '证据状态与置信度'] },
      { name: 'D. 平台层', items: ['仅采集可观测/公开指标或用户提供的导出', '平台观测独立保存', '跨平台推断指标必须标记 derived'] },
      { name: 'E. 内容产出层', items: ['完整节目', '章节', '剪辑候选', '金句', '社媒文案', '研究笔记', '人物档案更新', '知识图谱节点'] },
      { name: 'F. 学习层', items: ['假设、证据、混淆因素', '可复用内容', '格式特定内容', '不应复制的内容'] }
    ],
    dimensions: [
      'IP 定位', '受众承诺', '选题架构', '嘉宾架构', '嘉宾-选题适配', '问题架构',
      '追问深度', '故事密度', '冲突密度', '情绪密度', '洞察密度', '时长架构',
      '钩子架构', '章节架构', '金句/剪辑产出', '分发包装', '跨平台转译',
      '受众反馈', '增长/时长时间序列', '有证据的制作经济学', '失败案例',
      '可复制性', '因果置信度', '证据质量'
    ],
    hypotheses: [
      '为什么这个选题现在值得做一期？',
      '为什么这位嘉宾是合适的人？',
      '哪个问题解锁了最高的故事产出？',
      '单集在哪里创造情绪或认知峰值？',
      '当留存数据存在时，时长如何影响消费？',
      '哪些时刻可以成为衍生资产？',
      '哪些平台包装改变了表现？',
      '哪些观测是事实 vs 模型假设？',
      '哪些学习可迁移到新节目，哪些是此 IP 特有？'
    ],
    antiCopy: '不克隆表面风格。提取机制，对照证据检验，然后适配到 ZBC/Zachary Podcast 设计系统与编辑语态。'
  };

  function renderCaseStudy() {
    var c = LIANGZI_CASE;
    var html = '<div class="podcast-case-header">'
      + '<h3>' + c.title + '</h3>'
      + '<p class="podcast-case-role">' + c.role + '</p></div>';

    html += '<div class="podcast-case-section"><h4>案例分解（六层）</h4><div class="podcast-case-layers">';
    c.layers.forEach(function (l) {
      html += '<div class="podcast-case-layer"><h5>' + l.name + '</h5><ul>';
      l.items.forEach(function (it) { html += '<li>' + it + '</li>'; });
      html += '</ul></div>';
    });
    html += '</div></div>';

    html += '<div class="podcast-case-section"><h4>研究维度（24 项）</h4><div class="podcast-case-dims">';
    c.dimensions.forEach(function (d, i) {
      html += '<span class="podcast-case-dim">' + (i + 1) + '. ' + d + '</span>';
    });
    html += '</div></div>';

    html += '<div class="podcast-case-section"><h4>初始系统假设（核心问题）</h4><ul class="podcast-case-hypo">';
    c.hypotheses.forEach(function (h) { html += '<li>' + h + '</li>'; });
    html += '</ul></div>';

    html += '<div class="podcast-case-anticopy"><strong>反复制规则：</strong>' + c.antiCopy + '</div>';

    $('case-study-content').innerHTML = html;
  }

  /* ============================================================
   * 8. 话题研究 + 快照 + 持久化（闭环入口）
   * ============================================================ */
  var LS_KEY_HISTORY = 'zbmp_podcast_topic_history';
  var LS_KEY_SCORES = 'zbmp_podcast_saved_scores';
  var currentTopic = '';

  function getHistory() {
    try { return JSON.parse(localStorage.getItem(LS_KEY_HISTORY) || '[]'); } catch (e) { return []; }
  }
  function saveHistory(list) {
    try { localStorage.setItem(LS_KEY_HISTORY, JSON.stringify(list.slice(0, 20))); } catch (e) {}
  }
  function pushHistory(topic) {
    if (!topic) return;
    var list = getHistory().filter(function (t) { return t !== topic; });
    list.unshift(topic);
    saveHistory(list);
    renderHistory();
  }
  function renderHistory() {
    var box = $('research-history');
    if (!box) return;
    var list = getHistory();
    var html = '<span style="font-size:11px;color:var(--lm-color-text-secondary,#999);">历史：</span>';
    list.forEach(function (t) {
      html += '<span class="podcast-history-tag" data-topic="' + escapeAttr(t) + '">' + escapeHtml(t) + '</span>';
    });
    box.innerHTML = html;
    box.querySelectorAll('.podcast-history-tag').forEach(function (el) {
      el.addEventListener('click', function () {
        $('research-topic-input').value = el.getAttribute('data-topic');
      });
    });
  }

  function getSavedScores() {
    try { return JSON.parse(localStorage.getItem(LS_KEY_SCORES) || '[]'); } catch (e) { return []; }
  }
  function saveScoreRecord(rec) {
    var list = getSavedScores();
    list.unshift(rec);
    try { localStorage.setItem(LS_KEY_SCORES, JSON.stringify(list.slice(0, 30))); } catch (e) {}
    renderSavedScores();
  }
  function renderSavedScores() {
    var row = $('saved-scores-row');
    var listEl = $('saved-scores-list');
    if (!row || !listEl) return;
    var list = getSavedScores();
    if (!list.length) { row.style.display = 'none'; return; }
    row.style.display = '';
    var html = '';
    list.forEach(function (r, i) {
      html += '<span class="podcast-saved-score" title="' + escapeAttr(r.topic || '') + ' · ' + (r.stage || '') + '" data-idx="' + i + '">'
        + (r.topic ? escapeHtml(r.topic.substring(0, 12)) : '未命名') + ' · ' + (r.score != null ? r.score : '?') + '分</span>';
    });
    listEl.innerHTML = html;
    listEl.querySelectorAll('.podcast-saved-score').forEach(function (el) {
      el.addEventListener('click', function () {
        var idx = parseInt(el.getAttribute('data-idx'), 10);
        var rec = getSavedScores()[idx];
        if (rec && rec.signals) {
          Object.keys(rec.signals).forEach(function (k) {
            var s = $('topic-input-' + k);
            if (s) s.value = Math.round((rec.signals[k] || 0) * 100);
          });
          updateLiveScore();
          if (rec.topic) { $('research-topic-input').value = rec.topic; setCurrentTopic(rec.topic); }
        }
      });
    });
  }

  function setCurrentTopic(topic) {
    currentTopic = topic || '';
    var label = $('topic-current-label');
    if (label) {
      if (currentTopic) { label.style.display = ''; label.textContent = '话题：' + currentTopic; }
      else { label.style.display = 'none'; }
    }
  }

  function submitResearch() {
    var topic = $('research-topic-input').value.trim();
    if (!topic) { showResearchError('请输入话题'); return; }
    hideResearchError();
    pushHistory(topic);
    setCurrentTopic(topic);
    var btn = $('research-btn');
    btn.disabled = true; btn.textContent = '研究中…';
    postJSON('/api/content/podcast-research', { topic: topic, brand: 'ZBMP', platform: 'podcast' })
      .then(function (d) {
        var content = (d && (d.content || d.text || d.result || d.output)) || JSON.stringify(d, null, 2);
        $('research-result-content').textContent = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
        $('research-result').style.display = '';
        $('research-result-badge').textContent = '研究结果 · ' + topic;
      })
      .catch(function (e) {
        showResearchError('研究失败: ' + e.message);
      })
      .finally(function () { btn.disabled = false; btn.textContent = 'AI 研究'; });
  }

  function submitSnapshot() {
    var topic = $('research-topic-input').value.trim();
    if (!topic) { showResearchError('请输入话题'); return; }
    hideResearchError();
    pushHistory(topic);
    setCurrentTopic(topic);
    fetch('/api/content/topic-snapshot?topic=' + encodeURIComponent(topic))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) throw new Error(d.error || 'snapshot failed');
        var snap = d.snapshot || {};
        var html = '<div style="font-size:13px;line-height:1.8;">';
        if (typeof snap === 'object' && snap !== null) {
          Object.keys(snap).forEach(function (k) {
            var v = snap[k];
            html += '<div><strong>' + escapeHtml(k) + '：</strong>' + escapeHtml(typeof v === 'object' ? JSON.stringify(v) : String(v)) + '</div>';
          });
        } else {
          html += escapeHtml(String(snap));
        }
        html += '</div>';
        $('snapshot-result-content').innerHTML = html;
        $('snapshot-result').style.display = '';
      })
      .catch(function (e) { showResearchError('快照失败: ' + e.message); });
  }

  function applyTopicToScoring() {
    var topic = $('research-topic-input').value.trim();
    if (!topic) { showResearchError('请先输入话题'); return; }
    setCurrentTopic(topic);
    var panel = $('topic-score-panel');
    if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function saveCurrentScore() {
    var scoreEl = $('topic-result-score');
    var score = scoreEl ? parseFloat(scoreEl.textContent) : null;
    if (score == null || isNaN(score)) { showResearchError('请先提交打分后再保存'); return; }
    var stageEl = $('topic-result-stage');
    saveScoreRecord({
      topic: currentTopic || $('research-topic-input').value.trim() || '未命名',
      score: score,
      stage: stageEl ? stageEl.textContent : '',
      signals: readSignals(),
      saved_at: new Date().toISOString()
    });
  }

  function showResearchError(msg) { var e = $('research-error'); if (e) { e.textContent = msg; e.style.display = ''; } }
  function hideResearchError() { var e = $('research-error'); if (e) e.style.display = 'none'; }

  function clearHistory() {
    try { localStorage.removeItem(LS_KEY_HISTORY); } catch (e) {}
    renderHistory();
  }

  /* ============================================================
   * 9. 实体创建（POST /api/podcast/entity）
   * ============================================================ */
  function submitCreateEntity() {
    var etype = $('entity-type-input').value.trim();
    var title = $('entity-title-input').value.trim();
    var errEl = $('entity-create-error');
    if (!etype) { if (errEl) { errEl.textContent = '实体类型必填'; errEl.style.display = ''; } return; }
    if (errEl) errEl.style.display = 'none';
    var body = { entity_type: etype, title: title };
    var parent = $('entity-parent-input').value.trim();
    if (parent) body.parent_id = parent;
    var tags = $('entity-tags-input').value.trim();
    if (tags) body.tags = tags.split(/[,，]/).map(function (t) { return t.trim(); }).filter(Boolean);
    var btn = $('entity-create-btn');
    btn.disabled = true; btn.textContent = '创建中…';
    postJSON('/api/podcast/entity', body)
      .then(function (d) {
        $('entity-type-input').value = '';
        $('entity-title-input').value = '';
        $('entity-parent-input').value = '';
        $('entity-tags-input').value = '';
        loadEntities();
      })
      .catch(function (e) {
        if (errEl) { errEl.textContent = '创建失败: ' + e.message; errEl.style.display = ''; }
      })
      .finally(function () { btn.disabled = false; btn.textContent = '创建实体'; });
  }

  /* ============================================================
   * 初始化
   * ============================================================ */
  function init() {
    loadOverview();
    loadEntities();
    buildTopicForm();
    loadStoryNodes();
    loadRuntimeValidate();
    renderCaseStudy();
    renderHistory();
    renderSavedScores();

    var tsb = $('topic-submit-btn');
    if (tsb) tsb.addEventListener('click', submitTopicScore);
    var ssb = $('story-submit-btn');
    if (ssb) ssb.addEventListener('click', submitStoryNodes);
    var bsb = $('breakout-submit-btn');
    if (bsb) bsb.addEventListener('click', submitBreakout);
    var ysb = $('yield-submit-btn');
    if (ysb) ysb.addEventListener('click', submitContentYield);
    var rsb = $('runtime-submit-btn');
    if (rsb) rsb.addEventListener('click', submitRuntimeValidate);

    var rb = $('research-btn');
    if (rb) rb.addEventListener('click', submitResearch);
    var sb = $('snapshot-btn');
    if (sb) sb.addEventListener('click', submitSnapshot);
    var rab = $('research-apply-btn');
    if (rab) rab.addEventListener('click', applyTopicToScoring);
    var rsb2 = $('research-save-btn');
    if (rsb2) rsb2.addEventListener('click', saveCurrentScore);
    var rcb = $('research-clear-btn');
    if (rcb) rcb.addEventListener('click', clearHistory);
    var rti = $('research-topic-input');
    if (rti) rti.addEventListener('keydown', function (e) { if (e.key === 'Enter') submitResearch(); });

    var ecb = $('entity-create-btn');
    if (ecb) ecb.addEventListener('click', submitCreateEntity);
  }

  global.ZBMPPodcast = {
    init: init,
    refresh: function () { loadOverview(); loadEntities(); },
    submitTopicScore: submitTopicScore,
    submitStoryNodes: submitStoryNodes,
    submitBreakout: submitBreakout,
    submitContentYield: submitContentYield,
    submitRuntimeValidate: submitRuntimeValidate,
    submitResearch: submitResearch,
    submitSnapshot: submitSnapshot,
    submitCreateEntity: submitCreateEntity
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
