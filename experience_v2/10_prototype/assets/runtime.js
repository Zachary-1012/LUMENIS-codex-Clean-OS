/* ============================================================================
 * LUMENIS Experience V2 — Production Runtime Hydration Adapter
 * ----------------------------------------------------------------------------
 * 仅在生产外壳（experience_runtime.py 注入 window.LUM_RUNTIME_API）下激活。
 * 直接双击 index.html 的离线原型不会有该全局，因此保持 DESIGN_ONLY 原型不变。
 *
 * 职责（最小、加法式）：
 *   1. 监听 app.js 的 'lum:screen'，对已绑定屏幕拉取与 section 描述符同构的真实
 *      ViewModel（/api/experience/screen/<id>），就地替换并重渲一次；未绑定屏保持原型。
 *   2. 绑定 AI-01 composer：发送到 /api/experience/ai/intent，只展示状态/证据/可追溯，
 *      绝不渲染私有 chain-of-thought / system prompt / 凭证。
 *   3. 能力入口卡（intent-*）把意图填入 composer；动作按钮沿用 LumUI.bindActions。
 *   4. 任何网络/服务失败都回退到原型渲染，绝不把页面清空，也不伪造成功数据。
 * 红线：不重算指标、不把 NULL/UNKNOWN 显示成 0、不暴露安全内部。
 * ========================================================================== */
(function (global) {
  'use strict';
  const API = global.LUM_RUNTIME_API;
  if (!API) return; // 离线原型：不激活

  const { $, $$, toast, bindActions, init } = global.LumUI || {};
  if (!$) { console.warn('[runtime] LumUI missing, hydration disabled'); return; }

  const SCREENS = () => global.LUM_SCREENS || {};
  const pending = new Set();      // 正在拉取的屏幕签名，防重复
  const hydrated = new Set();    // 已水合签名，防重渲循环
  const intentMap = {};          // action id -> 意图文本（来自真实 ViewModel cards）
  let currentId = null;          // 当前屏幕（由 lum:screen 事件维护，避免依赖 app.js 内部）

  function subjectSignature(id) {
    const sc = (global.LumShell && global.LumShell.SubjectContext.value) || {};
    return [id, sc.subject_id || '', sc.domain || '', sc.time_window || ''].join('|');
  }

  function setSourceTag(mode) {
    const tag = document.querySelector('[data-source-tag]');
    if (!tag) return;
    const map = {
      runtime: 'data-source=runtime · PRODUCTION',
      prototype: 'data-source=prototype · DESIGN_ONLY',
      offline: 'data-source=runtime unavailable · prototype fallback',
    };
    tag.textContent = map[mode] || mode;
  }

  /* 用真实 sections 替换并重渲一次 */
  function applyViewModel(id, vm) {
    const store = SCREENS();
    const sc = store[id];
    if (!sc) return;
    sc.sections = vm.sections;
    sc.__runtime = true;
    sc.__binding = vm.binding || null;
    // 收集能力入口意图
    intentMap[id] = {};
    (vm.sections || []).forEach(sec => {
      if (sec.type === 'cards' && Array.isArray(sec.items)) {
        sec.items.forEach(it => { if (it.action && it.action.id) intentMap[id][it.action.id] = it.action.intent || ''; });
      }
    });
    if (global.LumApp && typeof global.LumApp.renderScreen === 'function') {
      global.LumApp.renderScreen(id); // 会再次派发 lum:screen，但已在 hydrated 集合中，不会再 fetch
    }
  }

  async function hydrate(id) {
    const sig = subjectSignature(id);
    if (pending.has(sig) || hydrated.has(sig)) { wireRuntime(document); return; }
    pending.add(sig);
    try {
      const resp = await fetch(`${API}/screen/${encodeURIComponent(id)}`, { headers: { Accept: 'application/json' } });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const vm = await resp.json();
      if (vm && vm.bound && Array.isArray(vm.sections)) {
        applyViewModel(id, vm);
        hydrated.add(sig);
        setSourceTag('runtime');
        reportBinding(vm.binding);
      } else {
        // 未绑定屏：明确保持原型（诚实，不假装 runtime）
        setSourceTag('prototype');
      }
    } catch (err) {
      console.warn('[runtime] hydrate failed, keep prototype:', err);
      setSourceTag('offline');
      toast('运行时数据暂不可用，已回退到原型视图', 'info');
    } finally {
      pending.delete(sig);
    }
  }

  function reportBinding(binding) {
    if (!binding || !Array.isArray(binding.unavailable) || !binding.unavailable.length) return;
    // 外部依赖缺口只在控制台留痕，不在业务页面弹噪音；状态已由对应指标诚实展示
    console.info('[runtime] blocked fields for', binding.screen, ':', binding.unavailable);
  }

  /* ---------------- AI-01 composer ---------------- */
  function threadAdd(html) {
    const thread = $('[data-ai-thread]');
    if (!thread) return;
    const node = document.createElement('div');
    node.className = 'lum-ai-turn';
    node.innerHTML = html;
    thread.appendChild(node);
  }

  function wireComposer(root) {
    const send = root.querySelector('[data-ai-send]');
    const box = root.querySelector('[data-ai-composer]');
    if (!send || send.dataset.wired) return;
    send.dataset.wired = '1';

    // 能力入口卡：填入意图，不直接伪造结果
    $$('[data-action^="intent-"]', root).forEach(btn => {
      btn.addEventListener('click', () => {
        const text = (currentId && intentMap[currentId] && intentMap[currentId][btn.dataset.action]) || '';
        if (box && text) { box.value = text; box.focus(); }
      });
    });

    send.addEventListener('click', async () => {
      const task = (box && box.value || '').trim();
      if (!task) { toast('请先输入任务', 'info'); box && box.focus(); return; }
      const subj = (global.LumShell && global.LumShell.SubjectContext.value) || {};
      send.disabled = true;
      threadAdd('<div class="lum-ai-turn__status">检索证据 · 执行中…</div>');
      try {
        const resp = await fetch(`${API}/ai/intent`, {
          method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ task, domain: subj.domain || 'CTH', product: 'LUMENIS' }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.ok) throw new Error(data.error || ('HTTP ' + resp.status));
        // 只展示状态/证据/可追溯，绝不展示私有思考链
        threadAdd(
          '<div class="lum-opt lum-opt-flat" style="padding:12px">' +
          '<div class="lum-row-between"><b>执行状态</b><span class="lum-chip">' + data.status + '</span></div>' +
          '<div class="lum-caption lum-mono" style="margin-top:6px">execution: ' + (data.execution_id || '—') + '</div>' +
          '<div class="lum-caption" style="margin-top:4px">证据已记录：' + (data.evidence_recorded ? '是' : '否（待补）') + '</div>' +
          '<p class="lum-caption" style="margin-top:6px;color:var(--lum-text-3)">AI 为派生结果，不覆盖 Evidence/Canonical。</p></div>');
      } catch (err) {
        threadAdd('<div class="lum-ai-turn__status" style="color:var(--lum-c-danger,#c0563f)">执行失败：' +
          String(err.message || err) + '</div>');
      } finally {
        send.disabled = false;
      }
    });

    // 引用证据 / 指定主体 / 时间范围：QUERY 类本地控制，不造假数据
    ['[data-ai-ref]', '[data-ai-subject]', '[data-ai-window]'].forEach(sel => {
      const b = root.querySelector(sel);
      if (b && !b.dataset.wired) { b.dataset.wired = '1'; b.addEventListener('click', () => toast('该筛选为本地控制，待对应后端选择器接入', 'info')); }
    });
  }

  /* 动作：导航类按 data-target 走 hash；其余交给 LumUI（EFFECT 仍需确认，不伪造成功） */
  function wireActions(root) {
    const handlers = {};
    $$('[data-action]', root).forEach(node => {
      const a = node.dataset.action || '';
      if (a.startsWith('go-') || a === 'open-event') {
        handlers[a] = (n) => { const t = n.dataset.target; if (t) location.hash = '#/' + t; };
      }
    });
    bindActions(root, handlers);
  }

  function wireRuntime(root) {
    if (!root) return;
    init(root);                 // countup / tabs（对已水合真实数值生效）
    wireActions(root);
    wireComposer(root);
  }

  /* ---------------- 事件接线 ---------------- */
  document.addEventListener('lum:screen', ev => {
    const id = ev.detail && ev.detail.id;
    if (!id) return;
    currentId = id;
    const sig = subjectSignature(id);
    if (hydrated.has(sig)) { wireRuntime(document); return; }
    hydrate(id).then(() => wireRuntime(document));
  });

  // 主体/域切换：清掉旧签名，让绑定屏按新主体重新真实查询
  document.addEventListener('lum:subject', () => {
    if (!currentId) return;
    for (const k of Array.from(hydrated)) if (k.startsWith(currentId + '|')) hydrated.delete(k);
    hydrate(currentId).then(() => wireRuntime(document));
  });

  // 启动身份探测（失败不阻断）
  fetch(`${API}/runtime/identity`).then(r => r.json()).then(idn => {
    global.LUM_RUNTIME_IDENTITY = idn;
    console.info('[runtime] identity', idn && idn.database, idn && idn.runtime_guardian);
  }).catch(() => { /* 静默：屏幕水合各自处理失败 */ });

  global.LumRuntime = { hydrate, subjectSignature, setSourceTag };
})(window);
