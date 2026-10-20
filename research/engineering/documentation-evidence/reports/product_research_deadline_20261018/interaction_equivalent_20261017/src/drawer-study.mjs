import { initialPhysicalDrawer, physicalDrawerReduce, drawerSample } from './physical-drawer.mjs';

export const drawerStudy = [
  'physicaldrawer', '39', 'INSPECT / REVERSE / RETURN', '拉开来源，文稿还在',
  '边写边查当前段落的来源。打开或关闭途中再操作，来源面板带着原来的位置和速度转向；关闭后回到原入口。',
  'Experience Constitution lines 613–623：已有来源检查面板的可逆物理运动。共用 physics.mjs；质量、刚度、阻尼进入实际积分。全部来源为人工示例，只有当前页内草稿，无业务保存或写入。',
  ['mass', 'stiffness', 'damping'],
];

const SOURCES = [
  { id: 'review-source-a', title: '段落一 · 观察与判断', body: '人工示例句：先记录观察，再把判断与待核实问题分开。这里没有实际采集、原始文献或已验证证据。', provenance: '来源身份：本地交互审核样例 A；作者：人工编写；原生发布时间：未知；采集状态：未采集。' },
  { id: 'review-source-b', title: '段落二 · 保留缺口', body: '人工示例句：没有可核验依据的部分应保留为缺口，不能由面板动画变成已确认事实。', provenance: '来源身份：本地交互审核样例 B；作者：人工编写；原生发布时间：未知；采集状态：未采集。' },
];

/** Mounts an ordinary non-modal source inspector beside an unchanged editor.
 * getParameters is supplied by the parent review-settings UI, not this work area.
 * Returns a test/inspection handle and emits local review-physics-sample events.
 */
export function createPhysicalDrawer({ stage, button, status, reduce = () => false, onDispose = () => {}, listen, getParameters = () => ({}) }) {
  stage.innerHTML = `
    <style>
      .physical-drawer-page{position:absolute;inset:45px 16px 14px;background:#fffdf7;border:1px solid #ccd3c6;padding:18px;overflow:auto;scrollbar-gutter:stable}
      .physical-drawer-page h3{font:500 22px/1.4 Georgia,serif;margin:0 0 10px}
      .physical-drawer-page p{font-size:12px;line-height:1.7;margin:10px 0}
      .physical-drawer-page textarea{background:#fffef9;min-height:118px;padding:10px;border:1px solid #c4ccbf;resize:vertical}
      .physical-drawer-page .source-actions{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
      .physical-source-drawer{position:absolute;top:45px;bottom:14px;right:16px;width:min(360px,calc(100% - 32px));padding:16px;border:1px solid #9eafa3;border-left:3px solid #326d66;border-radius:5px 0 0 5px;background:#f7faf2;box-shadow:-10px 0 22px #203c3420;z-index:3;overflow:auto;scrollbar-gutter:stable;will-change:transform;font-size:13px;overscroll-behavior:contain}
      .physical-source-drawer h3{font-size:18px;line-height:1.5;margin:14px 0 12px}
      .physical-source-drawer p{line-height:1.8;overflow-wrap:anywhere}
      .physical-source-drawer .drawer-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
      .physical-source-drawer .drawer-tag{color:#326d66;font-size:11px;line-height:1.7}
      .physical-source-drawer [data-source-provenance]{border-top:1px solid #cbd5c8;padding-top:12px;font-size:12px}
      .physical-drawer-permission{color:#99543d}
    </style>
    <section class="physical-drawer-page" aria-label="本页研究草稿">
      <h3>研究草稿 · 边写边查</h3>
      <label for="physicalDrawerDraft">当前页内草稿</label>
      <textarea id="physicalDrawerDraft">观察、判断与下一步，需要分别说明。\n尚未核验的部分，暂时保留为空白。</textarea>
      <div class="source-actions">
        <button type="button" data-inspect="0">检查段落一来源</button>
        <button type="button" data-inspect="1">检查段落二来源</button>
      </div>
      <p>本例来源均为人工示例。文字只留在本页会话；刷新前请复制重要内容。</p>
      <p class="physical-drawer-permission" data-drawer-permission role="status"></p>
    </section>
    <section id="physicalSourceDrawer" class="physical-source-drawer" role="region" aria-labelledby="physicalSourceHeading" aria-hidden="true" inert>
      <div class="drawer-top"><span class="drawer-tag">只读来源检查<br>人工示例 · 未核验</span><button type="button" data-drawer-close>关闭来源</button></div>
      <h3 id="physicalSourceHeading" tabindex="-1" data-source-title></h3>
      <p data-source-body></p><p data-source-provenance></p>
      <p>Escape 关闭并返回原入口。文稿内容和选区不会被来源检查覆盖。</p>
    </section>`;
  const q = selector => stage.querySelector(selector);
  const panel = q('#physicalSourceDrawer');
  const draft = q('#physicalDrawerDraft');
  const sourceTitle = q('[data-source-title]');
  const sourceBody = q('[data-source-body]');
  const sourceProvenance = q('[data-source-provenance]');
  const localCleanups = [];
  const traces = [];
  let state = initialPhysicalDrawer({ parameters: getParameters() });
  let frame = 0, previousTime = 0, disposed = false, opener = null, selectedSource = 0;
  let shownSource = null;
  const inspectButtons = [...stage.querySelectorAll('[data-inspect]')];
  const openButton = button('打开当前段落来源', () => open(selectedSource), true);
  const closeButton = button('关闭来源并返回', close);
  const revokeButton = button('模拟撤回来源读取权限', revoke);
  const restoreButton = button('恢复示例读取权限', restorePermission);
  const openingButtons = [...inspectButtons, openButton].filter(Boolean);

  function bind(target, type, handler, options) {
    if (!target?.addEventListener) return;
    if (listen) listen(target, type, handler, options);
    else target.addEventListener(type, handler, options);
    localCleanups.push(() => target.removeEventListener(type, handler, options));
  }
  function stopFrame() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0; previousTime = 0;
  }
  function record(event) {
    const point = { ...drawerSample(state, performance.now() / 1000), event, study: 'physicaldrawer' };
    traces.push(point);
    if (traces.length > 2000) traces.shift();
    stage.dispatchEvent(new CustomEvent('review-physics-sample', { detail: point }));
  }
  function render() {
    panel.style.transform = `translate3d(${state.x}px,0,0)`;
    const readable = state.intent === 'open' && state.permission;
    panel.inert = !readable;
    panel.setAttribute('aria-hidden', String(!readable));
    panel.style.visibility = ['closed', 'disposed'].includes(state.phase) || !state.permission || (state.phase === 'unavailable' && !readable) ? 'hidden' : 'visible';
    panel.dataset.phase = state.phase;
    panel.dataset.x = String(state.x);
    panel.dataset.velocity = String(state.v);
    panel.dataset.target = String(state.target);
    panel.dataset.epoch = String(state.epoch);
    const identity = state.source ? `${state.source.id}\n${state.source.title}\n${state.source.body}\n${state.source.provenance}` : null;
    if (identity !== shownSource) {
      sourceTitle.textContent = state.source?.title || '';
      sourceBody.textContent = state.source?.body || '';
      sourceProvenance.textContent = state.source?.provenance || '';
      shownSource = identity;
    }
    for (const control of openingButtons) {
      control.setAttribute('aria-controls', panel.id);
      control.setAttribute('aria-expanded', String(readable));
      control.disabled = !state.permission;
    }
    if (closeButton) closeButton.disabled = state.intent !== 'open';
    if (revokeButton) revokeButton.disabled = !state.permission;
    if (restoreButton) restoreButton.disabled = state.permission;
    q('[data-drawer-permission]').textContent = state.permission ? '' : '来源读取权限已撤回，旧来源已清除。你的本页草稿仍然保留。';
  }
  function animate() {
    if (disposed || document.hidden || frame || !['opening', 'closing'].includes(state.phase)) return;
    if (reduce()) { state = physicalDrawerReduce(state, { type: 'reduce', parameters: getParameters() }); render(); record('reduced-motion'); return; }
    const epoch = state.epoch;
    previousTime = performance.now();
    function tick(now) {
      if (disposed || epoch !== state.epoch || document.hidden) return;
      frame = 0;
      const dt = (now - previousTime) / 1000;
      previousTime = now;
      state = physicalDrawerReduce(state, { type: 'step', dt, epoch, parameters: getParameters(), reduce: reduce() });
      render(); record('step');
      if (epoch === state.epoch && ['opening', 'closing'].includes(state.phase)) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
  }
  function send(event, continueMotion = true) {
    if (disposed) return;
    stopFrame();
    state = physicalDrawerReduce(state, { ...event, parameters: getParameters(), reduce: reduce() });
    render(); record(event.type);
    if (continueMotion) animate();
  }
  function measure() {
    if (disposed) return;
    send({ type: 'geometry', geometry: {
      stageWidth: stage.clientWidth, stageHeight: stage.clientHeight,
      panelWidth: panel.offsetWidth, panelHeight: panel.offsetHeight, panelLeft: panel.offsetLeft,
    } });
  }
  function returnFocus() {
    const destination = opener?.isConnected && !opener.disabled ? opener : openButton;
    if (destination?.isConnected && !destination.disabled) destination.focus({ preventScroll: true });
    else draft.focus({ preventScroll: true });
    // Never set the editor value, selection or scroll position here. The page is
    // still editable while the non-modal inspector is open, so its latest caret
    // position belongs to the user, rather than to an older open-action snapshot.
  }
  function open(index = selectedSource) {
    if (disposed || !state.permission) { if (!disposed) status('当前没有来源读取权限，旧来源不会重新出现。'); return; }
    selectedSource = index === 1 ? 1 : 0;
    if (!panel.contains(document.activeElement)) opener = document.activeElement;
    send({ type: 'open', source: SOURCES[selectedSource] });
    sourceTitle.focus({ preventScroll: true });
    status(`正在查看${selectedSource === 0 ? '段落一' : '段落二'}的人工来源样例。可立即关闭或切换；没有业务写入。`);
  }
  function close() {
    if (disposed || state.intent !== 'open') return;
    send({ type: 'close' });
    returnFocus();
    status('已关闭来源检查，返回原入口；本页草稿与选区保留。');
  }
  function revoke() {
    if (disposed) return;
    const focusWasInside = panel.contains(document.activeElement);
    send({ type: 'revoke' }, false);
    if (focusWasInside) returnFocus();
    status('示例读取权限已撤回：旧来源立即清除；文稿未改动。');
  }
  function restorePermission() {
    if (disposed) return;
    send({ type: 'restore-permission' }, false);
    status('示例读取权限已恢复。按需重新打开来源，旧内容不会自动回放。');
  }
  function suspend() { send({ type: 'suspend' }, false); }
  function dispose() {
    if (disposed) return;
    stopFrame();
    state = physicalDrawerReduce(state, { type: 'dispose' });
    render();
    disposed = true;
    for (const cleanup of localCleanups.splice(0)) cleanup();
    observer?.disconnect();
    traces.length = 0;
  }

  for (const control of inspectButtons) bind(control, 'click', () => open(Number(control.dataset.inspect)));
  bind(q('[data-drawer-close]'), 'click', close);
  bind(document, 'keydown', event => {
    if (event.key !== 'Escape' || event.defaultPrevented || state.intent !== 'open' || document.activeElement?.closest('dialog[open]')) return;
    event.preventDefault(); close();
  });
  bind(window, 'review-motion-change', () => { if (reduce()) send({ type: 'reduce' }, false); });
  bind(window, 'resize', measure);
  bind(window, 'orientationchange', measure);
  bind(window.visualViewport, 'resize', measure);
  bind(window, 'blur', suspend);
  bind(window, 'focus', measure);
  bind(window, 'pagehide', suspend);
  bind(document, 'visibilitychange', () => document.hidden ? suspend() : measure());
  bind(document.fonts, 'loadingdone', measure);
  const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(measure) : null;
  observer?.observe(stage); observer?.observe(panel);
  document.fonts?.ready.then(() => { if (!disposed) measure(); });
  onDispose(dispose);
  measure();
  status('先编辑草稿，再检查某段来源。面板可随时反向；Escape 关闭并返回原入口。');
  return { open, close, revoke, restorePermission, dispose, get state() { return state; }, get samples() { return traces.map(point => ({ ...point })); } };
}
