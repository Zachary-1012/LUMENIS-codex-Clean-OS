/* ============================================================
   Taiji State Pipeline — 状态可见层渲染原语（presentational）
   不持有业务状态、不发业务请求；阶段与证据全部由调用方传入。
   用法：
     TaijiState.renderPipeline(document.getElementById('x'), {
       stages: [{key:'input', label:'输入信号', evidence:'原始笔记 128 条', src:'xhs_collector'}],
       current: 3,                 // 当前激活阶段索引（其前=done，其后=todo）
       loopNote: 'FEEDBACK 回流为下一轮芥子信号',
       onSelect: (s,i)=>{}         // 可选：点击/键盘下钻回调
     });
   ============================================================ */
(function (global) {
  'use strict';
  var DEFAULT_STAGES = [
    ['input', '输入信号'], ['detected', '已检测'], ['verified', '已核验'],
    ['classified', '已分类'], ['correlated', '已关联'], ['risk', '影响研判'],
    ['decision', '决策'], ['action', '行动生产'], ['feedback', '反馈学习']
  ];

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text; // textContent，杜绝 XSS
    return e;
  }

  function renderPipeline(root, opts) {
    if (!root) return null;
    opts = opts || {};
    var stages = (opts.stages && opts.stages.length)
      ? opts.stages.map(function (s, i) {
          return { key: s.key || ('s' + i), label: s.label || ('阶段' + (i + 1)),
                   evidence: s.evidence || '', src: s.src || '', state: s.state || '' };
        })
      : DEFAULT_STAGES.map(function (d) { return { key: d[0], label: d[1], evidence: '', src: '', state: '' }; });
    var current = (typeof opts.current === 'number') ? opts.current : -1;

    root.innerHTML = '';
    var wrap = el('div', 'tj-pipeline');
    wrap.setAttribute('role', 'group');
    wrap.setAttribute('aria-label', '信号到决策的状态管线');
    var track = el('ul', 'tj-track');
    var nodeRefs = [];

    stages.forEach(function (s, i) {
      var state = s.state || (i < current ? 'done' : (i === current ? 'active' : 'todo'));
      var li = el('li', 'tj-stage');
      li.classList.add('tj-is-' + (state === 'todo' ? 'todo' : state));
      li.dataset.idx = String(i);
      li.dataset.key = s.key;
      if (s.evidence) li.setAttribute('data-evidence', '1');

      var node = el('span', 'tj-node');
      node.setAttribute('aria-label', s.label + '，' + ({done:'已完成',active:'进行中',risk:'需关注',todo:'未开始'}[state] || state));
      if (state === 'active') node.setAttribute('aria-current', 'step');
      var idx = el('span', 'tj-idx', String(i + 1));
      var done = el('span', 'tj-glyph-done', '✓'); // 形状/符号编码，不仅靠颜色
      node.appendChild(idx); node.appendChild(done);

      var label = el('span', 'tj-label', s.label);
      li.appendChild(node); li.appendChild(label);

      if (s.evidence) {
        node.tabIndex = 0;
        node.setAttribute('role', 'button');
        node.setAttribute('aria-expanded', 'false');
        function open() { showEvidence(i); nodeRefs.forEach(function (n, j) { n.li.classList.toggle('tj-highlight', j === i); }); if (opts.onSelect) opts.onSelect(s, i); }
        node.addEventListener('click', open);
        node.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); open(); }
          else if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') {
            var dir = ev.key === 'ArrowRight' ? 1 : -1, j = i;
            do { j += dir; } while (j >= 0 && j < stages.length && !stages[j].evidence);
            if (j >= 0 && j < stages.length && nodeRefs[j]) nodeRefs[j].node.focus();
          }
        });
      }
      nodeRefs.push({ li: li, node: node });
      track.appendChild(li);
    });

    var panel = el('div', 'tj-evidence-panel');
    panel.hidden = true;
    var pTitle = el('div', 'tj-ev-title');
    var pName = el('span', 'tj-ev-name');
    var pClose = el('button', 'tj-ev-close', '×');
    pClose.setAttribute('aria-label', '关闭证据详情');
    var pBody = el('div', 'tj-ev-body');
    var pSrc = el('div', 'tj-ev-src');
    pTitle.appendChild(pName); pTitle.appendChild(pClose);
    panel.appendChild(pTitle); panel.appendChild(pBody); panel.appendChild(pSrc);
    pClose.addEventListener('click', function () { panel.hidden = true; nodeRefs.forEach(function (n) { n.node.setAttribute('aria-expanded', 'false'); n.li.classList.remove('tj-highlight'); }); });

    function showEvidence(i) {
      var s = stages[i];
      pName.textContent = (i + 1) + '. ' + s.label;
      pBody.textContent = s.evidence;
      pSrc.textContent = s.src ? ('证据来源：' + s.src) : '';
      panel.hidden = false;
      nodeRefs[i].node.setAttribute('aria-expanded', 'true');
    }

    wrap.appendChild(track);
    wrap.appendChild(panel);
    if (opts.loopNote) wrap.appendChild(el('div', 'tj-loop-note', opts.loopNote));
    root.appendChild(wrap);

    // 暴露 cross-highlight 句柄，供外部图表/列表联动
    return {
      highlight: function (key) {
        nodeRefs.forEach(function (n) { n.li.classList.toggle('tj-highlight', n.li.dataset.key === key); });
      },
      el: wrap
    };
  }

  global.TaijiState = { renderPipeline: renderPipeline, DEFAULT_STAGES: DEFAULT_STAGES };
})(window);
