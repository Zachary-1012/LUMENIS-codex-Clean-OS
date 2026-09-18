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

  // Production Truth fence. Fixtures remain available only as structural input;
  // their example values must never flash as production facts.
  document.title = '序境 LUMENIS · Production';
  if (!document.querySelector('#lum-production-truth-fence')) {
    const fence = document.createElement('style');
    fence.id = 'lum-production-truth-fence';
    fence.textContent = '.lum-qa-bar{display:none!important}' +
      '.lum-page[data-source="prototype"]>*:not([data-unbound-banner]),' +
      '.lum-page[data-source="offline"]>*:not([data-unbound-banner]){display:none!important}';
    document.head.appendChild(fence);
  }

  // The production shell is protected by the same Basic contract as the
  // legacy app.  Browser navigation may satisfy the challenge once, but
  // script fetches are not guaranteed to reuse that header.  Reuse the
  // existing backend auth/config contract instead of embedding credentials or
  // letting every runtime request fall into the honest offline state.
  let authHeader = global.__Z_AUTH || '';
  let authConfigPromise = null;
  function loadAuthHeader() {
    if (authHeader) return Promise.resolve(authHeader);
    if (authConfigPromise) return authConfigPromise;
    authConfigPromise = fetch('/api/auth/config', {
      headers: { Accept: 'application/json' }, credentials: 'include',
    }).then(resp => resp.ok ? resp.json() : {})
      .then(data => {
        authHeader = data && data.auth_enabled && data.auth_header ? data.auth_header : '';
        if (authHeader) global.__Z_AUTH = authHeader;
        return authHeader;
      }).catch(() => '');
    return authConfigPromise;
  }
  async function apiFetch(input, init) {
    const opts = Object.assign({}, init || {});
    const headers = new Headers(opts.headers || {});
    if (!headers.has('Authorization')) {
      const header = await loadAuthHeader();
      if (header) headers.set('Authorization', header);
    }
    opts.headers = headers;
    opts.credentials = opts.credentials || 'include';
    return fetch(input, opts);
  }

  // Shared production auth bridge.  The experience shell does not load the
  // legacy base.html bundle, while SYS-06/browser.js still needs the same
  // backend auth contract.  Expose only the header getter/fetch wrapper; no
  // credential value is embedded in the frontend source.
  const lumenisAuth = global.LUMENIS || (global.LUMENIS = {});
  lumenisAuth.Auth = lumenisAuth.Auth || {};
  lumenisAuth.Auth.getHeader = loadAuthHeader;
  lumenisAuth.fetch = apiFetch;

  // UI hydration is optional; the auth bridge above is not.  SYS-06/browser.js
  // must still be able to call protected Browser Surface APIs if a visual
  // module fails to initialize.
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
    const map = {
      runtime: 'data-source=runtime · PRODUCTION',
      prototype: 'data-source=prototype · DESIGN_ONLY',
      offline: 'data-source=runtime unavailable · prototype fallback',
    };
    if (tag) tag.textContent = map[mode] || mode;
    const page = document.querySelector('#lum-page');
    if (page) page.dataset.source = mode;
  }

  /* 未绑定屏诚实横幅：生产外壳下绝不把 DESIGN_ONLY fixture 当成真实生产数据 */
  function unboundBanner(id, classification) {
    let bar = document.querySelector('[data-unbound-banner]');
    const host = document.querySelector('#lum-page') || document.querySelector('.lum-main') || document.body;
    if (!bar) {
      bar = document.createElement('div');
      bar.setAttribute('data-unbound-banner', '1');
      bar.className = 'lum-unbound-banner';
    }
    const reason = classification === 'BLOCKED_BY_EXTERNAL_DEPENDENCY'
      ? '生产数据源尚未接入（BLOCKED_BY_EXTERNAL_DEPENDENCY）'
      : classification === 'RUNTIME_UNAVAILABLE'
        ? '生产 Runtime / API 当前不可用，未展示任何设计样例数据'
        : '生产 ViewModel 尚未绑定';
    bar.innerHTML =
      '<span class="lum-unbound-banner__dot" aria-hidden="true"></span>' +
      '<span>当前为 <b>原型结构 · DESIGN_ONLY 示例</b>，' + reason +
      '，下列数值为设计样例，<b>不是真实生产数据</b>。屏幕：' + id + '</span>';
    // 固定为内容区第一个子节点，保证用户先看到诚实声明再看到样例
    if (bar.parentNode !== host) host.insertBefore(bar, host.firstChild);
  }
  function clearUnboundBanner() {
    const bar = document.querySelector('[data-unbound-banner]');
    if (bar && bar.parentNode) bar.parentNode.removeChild(bar);
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
    // Production Truth fence: app.js 先渲染的 DESIGN_ONLY fixture 仅是结构源。
    // 在真实 ViewModel 到达前保持隐藏，避免慢请求期间把样例数字误认作生产事实。
    setSourceTag('prototype');
    try {
      const resp = await apiFetch(`${API}/screen/${encodeURIComponent(id)}`, { headers: { Accept: 'application/json' } });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const vm = await resp.json();
      if (vm && vm.bound && Array.isArray(vm.sections)) {
        clearUnboundBanner();
        applyViewModel(id, vm);
        hydrated.add(sig);
        setSourceTag('runtime');
        reportBinding(vm.binding);
      } else {
        // 未绑定屏：保持原型结构，但必须显式标注 DESIGN_ONLY，防止假数据被当成生产值
        unboundBanner(id, vm && vm.classification);
        setSourceTag('prototype');
      }
    } catch (err) {
      console.warn('[runtime] hydrate failed, show honest unavailable state:', err);
      setSourceTag('offline');
      unboundBanner(id, 'RUNTIME_UNAVAILABLE');
      toast('运行时数据暂不可用，未展示设计样例数据', 'info');
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

  function wireComposerLegacy(root) {
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
        const resp = await apiFetch(`${API}/ai/intent`, {
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

  // Conversational UI is deliberately separate from task execution.  The
  // response is rendered with textContent so server/model text cannot inject
  // markup into the product surface or expose hidden reasoning.
  const chatHistory = [];

  function subjectContext() {
    return (global.LumShell && global.LumShell.SubjectContext.value) || {};
  }

  function threadNode(kind, text, meta) {
    const thread = $('[data-ai-thread]');
    if (!thread) return null;
    const node = document.createElement('div');
    node.className = 'lum-ai-turn';
    const bubble = document.createElement('div');
    bubble.className = kind === 'status' ? 'lum-ai-turn__status' : 'lum-ai-turn__bubble';
    bubble.textContent = String(text || '');
    node.appendChild(bubble);
    if (meta) {
      const line = document.createElement('div');
      line.className = 'lum-ai-turn__meta';
      line.textContent = String(meta);
      node.appendChild(line);
    }
    thread.appendChild(node);
    thread.scrollTop = thread.scrollHeight;
    return node;
  }

  function resultHost(root) {
    let host = root.querySelector('[data-shared-skill-results]');
    if (!host) {
      host = document.createElement('div');
      host.setAttribute('data-shared-skill-results', '1');
      host.className = 'lum-shared-skill-results';
      const palette = root.querySelector('[data-shared-skill-palette]');
      if (palette && palette.parentNode) palette.parentNode.appendChild(host);
      else root.appendChild(host);
    }
    return host;
  }

  function appendSharedSkillResult(root, skill, data) {
    const host = resultHost(root);
    const item = document.createElement('article');
    item.className = 'lum-shared-skill-result';
    const heading = document.createElement('div');
    heading.className = 'lum-row-between';
    const name = document.createElement('b');
    name.textContent = skill.name || skill.tool_name || skill.skill_id;
    const state = document.createElement('span');
    state.className = 'lum-chip'; state.textContent = data.status || 'unknown';
    heading.append(name, state);
    const meta = document.createElement('div');
    meta.className = 'lum-caption lum-mono';
    meta.textContent = [
      data.execution_id ? `execution:${data.execution_id}` : '',
      data.evidence_recorded ? 'Evidence:recorded' : 'Evidence:not-recorded',
      'external_fetch:false',
    ].filter(Boolean).join(' · ');
    const pre = document.createElement('pre');
    const raw = data.result === undefined ? (data.error || '没有返回结果') : JSON.stringify(data.result, null, 2);
    pre.textContent = String(raw).slice(0, 7000);
    item.append(heading, meta, pre);
    host.prepend(item);
  }

  async function runSharedSkill(root, skill, task, input) {
    const domain = subjectContext().domain || 'CTH';
    const action = skill.execution_policy === 'READ_ONLY' ? 'ANALYZE' : 'SUGGEST';
    const host = resultHost(root);
    const pendingNode = document.createElement('div');
    pendingNode.className = 'lum-ai-turn__status';
    pendingNode.textContent = `${skill.tool_name || skill.name} · 读取本地证据并执行…`;
    host.prepend(pendingNode);
    try {
      const resp = await apiFetch(`${API}/shared-skills/${encodeURIComponent(skill.skill_id)}/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          task: task || `查看 ${skill.name} 的本地可用能力`,
          input: input || {}, action_type: action, domain,
        }),
      });
      const data = await resp.json();
      pendingNode.remove();
      appendSharedSkillResult(root, skill, data);
    } catch (err) {
      pendingNode.textContent = `能力执行失败：${String(err.message || err)}`;
    }
  }

  function sharedStateLabel(state) {
    return ({
      BOUND_LOCAL_READ: 'LOCAL · READ',
      BOUND_LOCAL_DRAFT: 'LOCAL · DRAFT',
      BOUND_LOCAL_PARTIAL: 'LOCAL · PARTIAL',
      BOUND_LOCAL_WORKFLOW: 'LOCAL · WORKFLOW',
      UNBOUND: 'UNBOUND',
    }[state] || state || 'UNKNOWN');
  }

  async function mountSharedSkillPalette(root) {
    if (!root || !['AI-01', 'SH-01'].includes(currentId)) return;
    const host = root.querySelector('[data-shared-skill-palette]');
    if (!host || host.dataset.wired) return;
    host.dataset.wired = '1';
    try {
      const resp = await apiFetch(`${API}/shared-skills`, { headers: { Accept: 'application/json' } });
      const data = await resp.json();
      if (!resp.ok || !data.ok || !Array.isArray(data.skills)) throw new Error(data.error || `HTTP ${resp.status}`);
      host.replaceChildren();
      const box = root.querySelector('[data-ai-composer]');
      data.skills.forEach(skill => {
        const card = document.createElement('article'); card.className = 'lum-shared-skill';
        const top = document.createElement('div'); top.className = 'lum-shared-skill__top';
        const name = document.createElement('span'); name.className = 'lum-shared-skill__name'; name.textContent = skill.name || skill.tool_name;
        const state = document.createElement('span'); state.className = 'lum-shared-skill__state';
        state.dataset.state = skill.implementation_state || 'UNKNOWN'; state.textContent = sharedStateLabel(skill.implementation_state);
        top.append(name, state);
        const tool = document.createElement('span'); tool.className = 'lum-shared-skill__tool'; tool.textContent = skill.tool_name || skill.skill_id;
        const desc = document.createElement('span'); desc.className = 'lum-shared-skill__desc'; desc.textContent = skill.description || '';
        const actions = document.createElement('div'); actions.className = 'lum-row'; actions.style.marginTop = 'auto'; actions.style.gap = '6px';
        const select = document.createElement('button'); select.type = 'button'; select.className = 'lum-chip'; select.textContent = '装载';
        select.addEventListener('click', () => {
          if (box) { box.value = `使用 ${skill.tool_name || skill.name}：${skill.input_hint || ''}`.trim(); box.focus(); }
          toast(`${skill.tool_name || skill.name} 已装载到当前上下文`, 'info');
        });
        const run = document.createElement('button'); run.type = 'button'; run.className = 'lum-chip'; run.textContent = '运行预览';
        run.addEventListener('click', () => {
          const task = box && box.value.trim() ? box.value.trim() : `查看 ${skill.name} 的本地可用能力`;
          runSharedSkill(root, skill, task, { domain: subjectContext().domain || 'CTH' });
        });
        actions.append(select, run);
        card.append(top, tool, desc, actions); host.appendChild(card);
      });
    } catch (err) {
      host.textContent = `共享能力注册表暂不可用：${String(err.message || err)}`;
    }
  }

  function wireComposer(root) {
    const send = root.querySelector('[data-ai-send]');
    const execute = root.querySelector('[data-ai-execute]');
    const box = root.querySelector('[data-ai-composer]');
    if (!send && !execute) return;
    if (send && !send.dataset.wired) {
      send.dataset.wired = '1';
      send.addEventListener('click', async () => {
        const task = (box && box.value || '').trim();
        if (!task) { toast('请先输入任务', 'info'); box && box.focus(); return; }
        const subj = subjectContext();
        send.disabled = true;
        threadNode('user', task, `${subj.domain || 'CTH'} · 当前上下文`);
        try {
          const resp = await apiFetch('/api/ai/chat', {
            method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ message: task, domain: subj.domain || 'CTH', product: 'LUMENIS', history: chatHistory.slice(-6) }),
          });
          const data = await resp.json();
          if (!resp.ok || !data.ok) throw new Error(data.error || ('HTTP ' + resp.status));
          const reply = String(data.reply || '当前没有可展示的回答');
          chatHistory.push({ role: 'user', content: task }, { role: 'assistant', content: reply });
          threadNode('assistant', reply, `Provider: ${data.provider || 'unknown'} · AI 为派生层，不覆盖 Evidence/Canonical`);
        } catch (err) {
          threadNode('status', `对话暂不可用：${String(err.message || err)}`, '未改变生产数据');
        } finally {
          send.disabled = false;
        }
      });
    }
    if (execute && !execute.dataset.wired) {
      execute.dataset.wired = '1';
      execute.addEventListener('click', async () => {
        const task = (box && box.value || '').trim();
        if (!task) { toast('请先输入任务', 'info'); box && box.focus(); return; }
        const subj = subjectContext();
        execute.disabled = true;
        threadNode('status', '任务请求已提交：等待权限门与执行链结果…');
        try {
          const resp = await apiFetch(`${API}/ai/intent`, {
            method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ task, domain: subj.domain || 'CTH', product: 'LUMENIS', action_type: 'ANALYZE' }),
          });
          const data = await resp.json();
          const detail = [
            `任务状态：${data.status || (resp.ok ? 'unknown' : 'error')}`,
            data.execution_id ? `execution:${data.execution_id}` : '',
            data.evidence_recorded === true ? 'Evidence:recorded' : 'Evidence:待确认',
            data.reason || data.error || '',
          ].filter(Boolean).join(' · ');
          threadNode('status', detail, '权限/Trace 结果可见；不展示私有思考链');
        } catch (err) {
          threadNode('status', `任务提交失败：${String(err.message || err)}`, '未改变生产数据');
        } finally {
          execute.disabled = false;
        }
      });
    }
    $$('[data-action^="intent-"]', root).forEach(btn => {
      if (btn.dataset.wired) return;
      btn.dataset.wired = '1';
      btn.addEventListener('click', () => {
        const text = (currentId && intentMap[currentId] && intentMap[currentId][btn.dataset.action]) || '';
        if (box && text) { box.value = text; box.focus(); }
      });
    });
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
      } else if (a === 'open-content-evidence') {
        // Section render may already have applied the generic action binder before
        // runtime hydration. Bind this runtime-only query independently and once.
        if (node.dataset.contentEvidenceWired) return;
        node.dataset.contentEvidenceWired = '1';
        node.addEventListener('click', async () => {
          const n = node;
          const target = n.dataset.target || '';
          const host = root.querySelector('[data-content-evidence-detail]');
          if (!target || !host) return;
          n.disabled = true;
          host.querySelector('p').textContent = '正在读取真实 Evidence…';
          try {
            const res = await apiFetch(`${API}/content/evidence/${encodeURIComponent(target)}`);
            const data = await res.json();
            if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
            const ev = data.evidence || {};
            host.replaceChildren();
            const eyebrow = document.createElement('span');
            eyebrow.className = 'lum-eyebrow'; eyebrow.textContent = 'Evidence Detail · PRODUCTION';
            const title = document.createElement('h2');
            title.className = 'lum-h4'; title.textContent = ev.evidence_id || target;
            const meta = document.createElement('p');
            meta.className = 'lum-caption lum-mono';
            meta.textContent = [ev.content_type, ev.provider, ev.model, ev.status, ev.created_at].filter(Boolean).join(' · ');
            const output = document.createElement('pre');
            output.className = 'lum-body-2'; output.style.whiteSpace = 'pre-wrap';
            output.textContent = JSON.stringify(ev.output || {}, null, 2);
            const fence = document.createElement('p');
            fence.className = 'lum-caption'; fence.textContent = 'AI 为派生结果；Prompt 与内部研究上下文未下发。';
            host.append(eyebrow, title, meta, output, fence);
          } catch (err) {
            host.querySelector('p').textContent = `Evidence 读取失败：${String(err.message || err)}`;
          } finally {
            n.disabled = false;
          }
        });
      }
    });
    bindActions(root, handlers);
  }

  /* ---------------- SYS-05: 通用主体 + 香港授权 Cookie ----------------
   * 这是设置工作区的真实增量接线。主体登记只写通用注册表，不切换默认主体；
   * Cookie 只发往本地 LUMENIS Runtime，成功后清空输入框，响应永不回显凭证。
   */
  function wireSettingsSurface(root) {
    const surface = root.querySelector('[data-lumenis-settings-surface]');
    if (!surface || surface.dataset.wired) return;
    surface.dataset.wired = '1';

    const subjectForm = surface.querySelector('[data-subject-form]');
    const subjectList = surface.querySelector('[data-subject-list]');
    const subjectStatus = surface.querySelector('[data-subject-status]');
    const domain = surface.querySelector('[data-subject-domain]');
    const type = surface.querySelector('[data-subject-type]');
    const nameEn = surface.querySelector('[data-subject-name-en]');
    const nameZh = surface.querySelector('[data-subject-name-zh]');
    const industry = surface.querySelector('[data-subject-industry]');

    function subjectStatusText(text, tone) {
      if (!subjectStatus) return;
      subjectStatus.textContent = String(text || '');
      subjectStatus.dataset.tone = tone || 'neutral';
    }
    function renderSubjects(items) {
      if (!subjectList) return;
      subjectList.replaceChildren();
      if (!Array.isArray(items) || !items.length) {
        const empty = document.createElement('span');
        empty.className = 'lum-caption';
        empty.textContent = '尚未登记主体；此处不展示设计样例。';
        subjectList.appendChild(empty);
        return;
      }
      items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'lum-opt lum-opt-flat';
        const top = document.createElement('div');
        top.className = 'lum-row-between';
        const title = document.createElement('b');
        title.textContent = `${item.name_zh || '—'} / ${item.name_en || '—'}`;
        const badge = document.createElement('span');
        badge.className = 'lum-chip';
        badge.textContent = `${item.domain_id || '—'} · ${item.subject_type_name || item.subject_type || '—'}`;
        top.append(title, badge);
        const meta = document.createElement('span');
        meta.className = 'lum-caption';
        meta.textContent = `${item.industry || '不限行业'} · ${item.status || 'configured'} · 仅上下文选择`;
        row.append(top, meta);
        subjectList.appendChild(row);
      });
    }
    async function loadSubjects() {
      try {
        const resp = await apiFetch('/api/settings/subjects', { headers: { Accept: 'application/json' } });
        const data = await resp.json();
        if (!resp.ok || !data.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        renderSubjects(data.subjects);
      } catch (err) {
        renderSubjects([]);
        subjectStatusText(`主体注册表读取失败：${String(err.message || err)}`, 'error');
      }
    }
    if (subjectForm && !subjectForm.dataset.wired) {
      subjectForm.dataset.wired = '1';
      subjectForm.addEventListener('submit', async event => {
        event.preventDefault();
        const en = String(nameEn && nameEn.value || '').trim();
        const zh = String(nameZh && nameZh.value || '').trim();
        if (!en || !zh) {
          subjectStatusText('英文名与中文名必须同时填写；未写入。', 'error');
          return;
        }
        const submit = subjectForm.querySelector('[data-subject-submit]');
        if (submit) { submit.disabled = true; submit.textContent = '登记中…'; }
        subjectStatusText('正在等待权限门并写入通用主体注册表…', 'pending');
        try {
          const resp = await apiFetch('/api/settings/subjects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({
              domain_id: domain && domain.value,
              subject_type: type && type.value,
              name_en: en,
              name_zh: zh,
              industry: industry && industry.value,
            }),
          });
          const data = await resp.json();
          if (!resp.ok || !data.ok) throw new Error(data.error || `HTTP ${resp.status}`);
          subjectStatusText(data.created ? '主体已登记；未切换默认主体。' : '主体已存在；未重复写入。', 'success');
          if (data.created) {
            if (nameEn) nameEn.value = '';
            if (nameZh) nameZh.value = '';
            if (industry) industry.value = '';
          }
          await loadSubjects();
          toast(data.created ? '主体登记完成' : '主体已存在', 'success');
        } catch (err) {
          subjectStatusText(`主体登记未完成：${String(err.message || err)}`, 'error');
          toast('主体登记未完成，未改变两域运行规则', 'info');
        } finally {
          if (submit) { submit.disabled = false; submit.textContent = '登记主体'; }
        }
      });
    }
    const refresh = surface.querySelector('[data-subject-refresh]');
    if (refresh && !refresh.dataset.wired) {
      refresh.dataset.wired = '1';
      refresh.addEventListener('click', loadSubjects);
    }

    const cookieJson = surface.querySelector('[data-setting-cookie-json]');
    const cookieApply = surface.querySelector('[data-setting-cookie-apply]');
    const cookieStatus = surface.querySelector('[data-setting-cookie-status]');
    const cookieSubmit = surface.querySelector('[data-setting-cookie-submit]');
    function cookieStatusText(text) { if (cookieStatus) cookieStatus.textContent = String(text || ''); }
    async function loadCookieStatus() {
      try {
        const resp = await apiFetch('/api/cookies/import/status', { headers: { Accept: 'application/json' } });
        const data = await resp.json();
        if (!resp.ok || !data.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        const xhs = data.status && data.status.xhs || {};
        const active = xhs.source === 'private_cookie_file' && xhs.account === 'XHS_RETINAUT';
        cookieStatusText(active ? `XHS_RETINAUT 已配置 · ${xhs.logged_in ? '登录态已验证' : '等待验证'}` : 'XHS_RETINAUT 尚未应用有效 Cookie');
      } catch (err) {
        cookieStatusText(`Cookie 状态不可用：${String(err.message || err)}`);
      }
    }
    if (cookieSubmit && !cookieSubmit.dataset.wired) {
      cookieSubmit.dataset.wired = '1';
      cookieSubmit.addEventListener('click', async () => {
        let cookies;
        try { cookies = JSON.parse(String(cookieJson && cookieJson.value || '')); } catch (_) {
          cookieStatusText('Cookie 必须是合法 JSON 数组；未发起导入。');
          return;
        }
        if (!Array.isArray(cookies) || !cookies.length) {
          cookieStatusText('Cookie 必须是非空 JSON 数组；未发起导入。');
          return;
        }
        cookieSubmit.disabled = true;
        cookieStatusText('正在安全导入；不会向平台写入…');
        try {
          const resp = await apiFetch('/api/cookies/import/raw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ platform: 'xhs', account: 'XHS_RETINAUT', cookies, apply: !!(cookieApply && cookieApply.checked) }),
          });
          const data = await resp.json();
          if (!resp.ok || !data.ok) throw new Error(data.error || `HTTP ${resp.status}`);
          if (cookieJson) cookieJson.value = '';
          cookieStatusText(data.applied ? '已绑定 XHS_RETINAUT 香港/国际采集；凭证不回显。' : '已暂存待应用；凭证不回显。');
          toast('Cookie 导入完成（未向平台发布或写操作）', 'success');
          await loadCookieStatus();
        } catch (err) {
          cookieStatusText(`Cookie 未导入：${String(err.message || err)}`);
          toast('Cookie 导入未完成，未改变平台', 'info');
        } finally {
          cookieSubmit.disabled = false;
        }
      });
    }
    const cookieRefresh = surface.querySelector('[data-cookie-status-refresh]');
    if (cookieRefresh && !cookieRefresh.dataset.wired) {
      cookieRefresh.dataset.wired = '1';
      cookieRefresh.addEventListener('click', loadCookieStatus);
    }
    loadSubjects();
    loadCookieStatus();
  }

  /* ---------------- CTH secondary platform collection ---------------- */
  function wirePlatformCollection(root) {
    const forms = $$('[data-platform-collection-form]', root);
    const statusCopy = {
      SUCCESS: '只读采集完成',
      NO_NEW_DATA: '本次没有新记录',
      SESSION_EXPIRED: '登录状态需要更新',
      NEED_VERIFY: '需要人工验证连接',
      RISK_WARNING: '平台出现风险信号，采集已停止',
      BLOCKED: '本次请求已被安全门禁阻止',
      COOLING_DOWN: '平台处于冷却期，请稍后再试',
      NOT_SUPPORTED: '该平台暂不支持此项能力',
      NOT_CONFIGURED: '尚未配置该平台的运行方式',
      PROVIDER_UNAVAILABLE: '采集服务暂不可用',
      RATE_LIMITED: '已达到采集频率上限',
      POLICY_STATE_UNAVAILABLE: '无法确认采集门禁状态，本次已阻止',
      IMPORT_FAILED: '部分记录未能写入业务数据',
      CANONICAL_SYNC_FAILED: 'Canonical Data 同步未完成',
      EVIDENCE_WRITE_FAILED: 'Evidence 未能保存，本次不计为完成',
      BUSY: '该平台已有采集任务正在运行',
      UNAVAILABLE: '该平台当前未就绪',
      COLLECT_ERROR: '采集未完成',
    };
    function outcomeText(data, responseOk, platformFallback) {
      const statusKey = String(data && data.status || '').toUpperCase();
      const label = statusCopy[statusKey] || String(data && (data.reason || data.error) || '本次采集未完成').slice(0, 180);
      const platform = String(data && data.platform || platformFallback || '平台');
      const parts = [`${platform} · ${label}`];
      if (data && data.ok && responseOk) {
        parts.push(`${Number(data.imported || 0)} 条新增 / ${Number(data.updated || 0)} 条更新`);
        if (data.canonical_synced != null) parts.push(`Canonical ${Number(data.canonical_synced || 0)} 条`);
      }
      if (data && data.evidence_recorded === true) parts.push('Evidence 已记录');
      else if (data && data.evidence_recorded === false) parts.push('Evidence 未确认');
      const trace = data && data.provenance && typeof data.provenance === 'object' ? data.provenance : null;
      if (trace) {
        const traceParts = [trace.source, trace.provider, trace.collected_at].filter(Boolean).map(v => String(v).slice(0, 180));
        if (traceParts.length) parts.push(`溯源 ${traceParts.join(' · ')}`);
      }
      parts.push('未向平台写入 · 未发布');
      return parts.join(' · ');
    }
    forms.forEach(form => {
      if (form.dataset.wired) return;
      form.dataset.wired = '1';
      const select = form.querySelector('[data-platform-select]');
      const keyword = form.querySelector('[data-platform-keyword]');
      const limit = form.querySelector('[data-platform-limit]');
      const submit = form.querySelector('[data-platform-collection-submit]');
      const surface = form.closest('[data-platform-surface]') || form.parentElement;
      const status = surface && surface.querySelector('[data-platform-collection-status]');
      const idleLabel = submit && (submit.dataset.idleLabel || submit.textContent.trim());
      form.addEventListener('submit', async ev => {
        ev.preventDefault();
        if (form.getAttribute('aria-busy') === 'true') return;
        const query = String(keyword && keyword.value || '').trim();
        if (!query) {
          if (status) status.textContent = '请先输入关键词；未发起外部请求。';
          keyword && keyword.focus();
          return;
        }
        const submittedScreen = currentId;
        const selectedPlatform = String(select && select.value || '');
        let announcement = '';
        if (submit) submit.disabled = true;
        form.setAttribute('aria-busy', 'true');
        if (submit) submit.textContent = '正在读取…';
        if (status) status.textContent = '正在读取公开或已授权数据；不向平台写入…';
        try {
          const resp = await apiFetch(form.dataset.endpoint || `${API}/cth/platform-collection/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({
              operator: 'human_ui',
              confirm_read_only: true,
              platform: select && select.value,
              keyword: query,
              max_results: Number(limit && limit.value || 5),
            }),
          });
          const data = await resp.json();
          announcement = outcomeText(data, resp.ok, selectedPlatform);
          if (status) status.textContent = announcement;
          if (data && data.ok) {
            toast('只读采集完成，已回到 CTH Evidence 链路', 'success');
          } else {
            toast('平台采集未完成，未执行发布或外部写入', 'info');
          }
        } catch (_) {
          announcement = '采集响应未能确认；请查看平台最近运行状态后再决定是否重试。未向平台写入，也未发布。';
          if (status) status.textContent = announcement;
          toast('采集请求不可用，未改变外部平台', 'info');
        } finally {
          if (submit) submit.disabled = false;
          if (submit && idleLabel) submit.textContent = idleLabel;
          form.setAttribute('aria-busy', 'false');
        }
        // Reload the same screen from its canonical ViewModel, then restore
        // the live status message that re-rendering would otherwise replace.
        if (submittedScreen && submittedScreen === currentId) {
          for (const key of Array.from(hydrated)) if (key.startsWith(submittedScreen + '|')) hydrated.delete(key);
          await hydrate(submittedScreen);
          wireRuntime(document);
          const refreshedSurface = document.querySelector('[data-platform-surface]');
          const refreshedStatus = refreshedSurface && refreshedSurface.querySelector('[data-platform-collection-status]');
          if (refreshedStatus && announcement) refreshedStatus.textContent = announcement;
        }
      });
    });
  }

  function wireRuntime(root) {
    if (!root) return;
    init(root);                 // countup / tabs（对已水合真实数值生效）
    wireActions(root);
    wireSettingsSurface(root);
    wirePlatformCollection(root);
    wireComposer(root);
    mountSharedSkillPalette(root);
    // SYS-06 is a routed production screen.  Reuse the existing canonical
    // browser controller only while its real surface is mounted; leaving the
    // screen stops polling so an old UI process cannot overwrite the new one.
    if (currentId === 'SYS-06' && root.querySelector('[data-browser-surface]') &&
        global.BrowserApp && typeof global.BrowserApp.init === 'function') {
      global.BrowserApp.init();
    }
  }

  /* ---------------- SYS Runtime: explicit human approval -> one-shot archive ----------------
   * The confirmation modal is the human action.  The first request only mints
   * a five-minute, resource-scoped token; the second request performs the
   * archive and the backend consumes the token.  Text outside the product
   * cannot mint this approval. */
  async function archiveDeadWorkers() {
    try {
      toast('正在生成本次归档的人工审批令牌…', 'info');
      const approvalResp = await apiFetch('/api/runtime/archive-dead/approval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          confirm: true,
          action: 'archive_dead_workers',
          resource: '/api/runtime/archive-dead',
          hours: 24,
        }),
      });
      const approval = await approvalResp.json();
      if (!approvalResp.ok || !approval.ok || !approval.approval_token) {
        throw new Error(approval.error || `审批未通过（HTTP ${approvalResp.status}）`);
      }
      const runResp = await apiFetch('/api/runtime/archive-dead?hours=24', {
        method: 'POST', headers: { Accept: 'application/json' },
      });
      const result = await runResp.json();
      if (!runResp.ok || !result.ok || result.approval_consumed !== true) {
        throw new Error(result.error || result.warning || `归档未确认（HTTP ${runResp.status}）`);
      }
      toast(`已完成一次性归档：${result.archived || 0} 个 worker，审批已消费`, 'success');
      if (currentId) {
        for (const key of Array.from(hydrated)) if (key.startsWith(currentId + '|')) hydrated.delete(key);
        await hydrate(currentId);
        wireRuntime(document);
      }
    } catch (err) {
      toast(`归档未完成：${String(err.message || err)}`, 'error');
    }
  }

  /* ---------------- 事件接线 ---------------- */
  document.addEventListener('lum:screen', ev => {
    const id = ev.detail && ev.detail.id;
    if (!id) return;
    if (currentId === 'SYS-06' && currentId !== id && global.BrowserApp &&
        typeof global.BrowserApp.destroy === 'function') {
      global.BrowserApp.destroy();
    }
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

  // runtime.js is injected by the production mount after the prototype's
  // synchronous app.js boot.  That boot can dispatch the first lum:screen
  // event before this listener exists; recover the current hash explicitly so
  // the production shell never stays blank behind the truth fence.
  const initialId = (global.location.hash || '').replace(/^#\/?/, '') || global.LUM_FIRST || 'AI-01';
  if (!currentId && initialId) {
    currentId = initialId;
    hydrate(currentId).then(() => wireRuntime(document));
  }

  // 启动身份探测（失败不阻断）
  apiFetch(`${API}/runtime/identity`).then(r => r.json()).then(idn => {
    global.LUM_RUNTIME_IDENTITY = idn;
    console.info('[runtime] identity', idn && idn.database, idn && idn.runtime_guardian);
  }).catch(() => { /* 静默：屏幕水合各自处理失败 */ });

  global.LumRuntime = { hydrate, subjectSignature, setSourceTag, archiveDeadWorkers };
})(window);
