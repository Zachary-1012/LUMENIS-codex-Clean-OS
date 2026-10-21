import {
  initialChapters, validateChapters, chaptersReduce, chapterRange, chapterSeekSample,
  chapterStartFromSeconds, chapterAudioSamples, chapterSessionIsCurrent, activeChapterLoop
} from './media-chapters.mjs';
import {makeSignal, encodeWav} from './audio-signal.mjs';

export const chapterStudy = [
  'chapters', '34', 'CHAPTERS / ONE REAL PLAYER', '按章节听，停在准确的位置',
  '选择章节直接定位测试音；明确开始或停止区间循环。改名、移动起点与重新排序先预览，可取消和撤销，音频本身不改变。',
  '草图 BMP-08、规划§14 P7：单一播放器、章节与时间码。人工章节 / 确定性测试音；无ASR、模型、后端或产品验收。循环WAV取真实采样切片；原生播放器接缝延迟依浏览器，未宣称无缝。', []
];

export function createChapters({stage, button, status, reduce, onDispose, session}) {
  const rate = 8000;
  const fixtures = [
    {source: {id: 'tone-a', version: '人工测试音 A-v1', sampleRate: rate, sampleCount: 32000}, samples: makeSignal(rate, 4),
      chapters: [{id: 'a1', name: '人工章：开场', start: 0}, {id: 'a2', name: '人工章：观察', start: 8000}, {id: 'a3', name: '人工章：比较', start: 20000}]},
    {source: {id: 'tone-b', version: '人工测试音 B-v1', sampleRate: rate, sampleCount: 48000}, samples: makeSignal(rate, 6),
      chapters: [{id: 'b1', name: '人工章：准备', start: 0}, {id: 'b2', name: '人工章：测试', start: 16000}, {id: 'b3', name: '人工章：结束', start: 36000}]}
  ];
  let fixture = fixtures[0], state = initialChapters(fixture.source, fixture.chapters);
  const sourceStates = new Map();
  // Only known fixture data is admitted. Playback/permission/runtime objects are never restored.
  function restoreEntry(entry, target) {
    try {
      const saved = entry?.state;
      if (!saved || Object.keys(target.source).some(key => saved.source?.[key] !== target.source[key]) ||
          !Number.isSafeInteger(saved.revision) || saved.revision < 1 ||
          !Array.isArray(saved.history) || saved.history.length > 30) return null;
      const check = chapters => {
        const result = validateChapters(chapters, target.source);
        if (result.length !== target.chapters.length || result.some(c => !target.chapters.some(t => t.id === c.id))) throw Error('fixture mismatch');
        return result;
      };
      const chapters = check(saved.chapters);
      const selection = id => { if (!chapters.some(c => c.id === id)) throw Error('selection mismatch'); return id; };
      const restored = {...initialChapters(target.source, chapters), revision: saved.revision,
        selected: selection(saved.selected), history: saved.history.map(h => ({chapters: check(h.chapters), selected: selection(h.selected)}))};
      if (saved.proposal != null) {
        const p = saved.proposal;
        if (p.base !== saved.revision || p.sourceId !== target.source.id || p.sourceVersion !== target.source.version || p.id !== restored.selected) return null;
        restored.proposal = {id: p.id, base: p.base, sourceId: p.sourceId, sourceVersion: p.sourceVersion, chapters: check(p.chapters)};
      }
      const ui = {};
      for (const key of ['name', 'start']) {
        const field = entry.ui?.[key];
        if (field && typeof field.value === 'string' && field.value.length <= 10000) {
          const bound = n => Number.isInteger(n) ? Math.max(0, Math.min(n, field.value.length)) : 0;
          ui[key] = {value: field.value, start: bound(field.start), end: bound(field.end),
            direction: ['forward','backward','none'].includes(field.direction) ? field.direction : 'none',
            scroll: Number.isFinite(field.scroll) ? Math.max(0, field.scroll) : 0};
        }
      }
      ui.scroll = Number.isFinite(entry.ui?.scroll) ? Math.max(0, entry.ui.scroll) : 0;
      return {state: restored, ui};
    } catch { return null; }
  }
  let savedRoute = null;
  try { savedRoute = session?.read('chapters'); } catch { /* unavailable snapshot starts clean */ }
  if (savedRoute?.version === 1) {
    for (const target of fixtures) {
      const entry = restoreEntry(savedRoute.sources?.[target.source.id], target);
      if (entry) sourceStates.set(target.source.id, entry);
    }
    fixture = fixtures.find(item => item.source.id === savedRoute.active) || fixture;
    state = sourceStates.get(fixture.source.id)?.state || initialChapters(fixture.source, fixture.chapters);
  }
  let url = null, offset = 0, loadIntent = null, disposed = false, localGeneration = 0;
  const removers = [];
  stage.innerHTML = `<section class="lab-scroll" aria-label="章节与实际测试音试听">
    <p>人工章节对应真实生成的测试音，不是语音、转写或故事识别结果。音量默认较低。跨示例保留本页审核会话中的编辑；刷新或关闭页面会丢失，不是后端保存。</p>
    <label>测试素材 <select id="chapterSource"><option value="0">测试音 A · 4 秒</option><option value="1">测试音 B · 6 秒</option></select></label>
    <audio id="chapterAudio" controls preload="metadata" aria-label="所选测试音的唯一原生播放器" style="display:block;width:100%;margin:12px 0"></audio>
    <p id="chapterPosition"></p><p id="chapterPlayback" role="status"></p>
    <ol id="chapterList" aria-label="按起点排序的人工章节" style="padding-left:24px"></ol>
    <label>所选章节名称<input id="chapterName" maxlength="80" autocomplete="off"></label>
    <label>章节起点（秒；按 1/8000 秒采样定位）<input id="chapterStart" type="number" min="0" step="0.000125"></label>
    <p>起点改变后按时间重新排列；同一采样起点或范围外的时间会被拒绝。名称和顺序修订不改变声音。</p>
    <p id="chapterProposal" role="status"></p>
    <p>键盘：Tab 到章节后 Enter 选择；章节内 ↑ / ↓ 选择相邻项，Home / End 选首末项。Esc 停止并取消待修订。无播放头缓动。</p>
  </section>`;
  const q = selector => stage.querySelector(selector);
  const audio = q('#chapterAudio');
  audio.volume = .15;
  function captureEntry() {
    const field = selector => {
      const node = q(selector);
      return {value: node.value, start: node.selectionStart, end: node.selectionEnd,
        direction: node.selectionDirection, scroll: node.scrollTop};
    };
    return {state: {...structuredClone(state), loop: null, session: 1},
      ui: {name: field('#chapterName'), start: field('#chapterStart'), scroll: q('.lab-scroll').scrollTop}};
  }
  function restoreUI(entry) {
    if (!entry?.ui) return;
    for (const [key, selector] of [['name','#chapterName'], ['start','#chapterStart']]) {
      const saved = entry.ui[key], node = q(selector);
      if (!saved) continue;
      node.value = saved.value;
      // Native number inputs do not support text selections.
      try { node.setSelectionRange(saved.start, saved.end, saved.direction); } catch { /* number input */ }
      node.scrollTop = saved.scroll;
    }
    q('.lab-scroll').scrollTop = entry.ui.scroll;
  }
  const listen = (target, type, handler) => {
    target.addEventListener(type, handler);
    removers.push(() => target.removeEventListener(type, handler));
  };
  const send = event => { state = chaptersReduce(state, event); };
  const seconds = sample => (sample / rate).toFixed(6).replace(/0+$/, '').replace(/\.$/, '');
  const absoluteSample = () => Math.max(0, Math.min(state.source.sampleCount,
    offset + Math.round((Number.isFinite(audio.currentTime) ? audio.currentTime : 0) * rate)));
  function reportPosition() {
    if (disposed) return;
    q('#chapterPosition').textContent = `${state.source.version} · 章节修订 v${state.revision} · 绝对位置 ${seconds(absoluteSample())} / ${seconds(state.source.sampleCount)} 秒`;
  }
  function halt() {
    localGeneration++;
    loadIntent = null;
    audio.pause();
    audio.loop = false;
  }
  function draw() {
    if (disposed) return;
    const list = q('#chapterList');
    list.replaceChildren();
    for (const chapter of state.chapters) {
      const range = chapterRange(state, chapter.id), item = document.createElement('li'), control = document.createElement('button');
      control.type = 'button';
      control.dataset.chapter = chapter.id;
      control.setAttribute('aria-pressed', String(chapter.id === state.selected));
      control.textContent = `${chapter.name} · ${seconds(range.start)}–${seconds(range.end)} 秒`;
      control.style.margin = '3px 0';
      if (chapter.id === state.selected) control.style.outline = '2px solid var(--green)';
      item.append(control); list.append(item);
    }
    const selected = state.chapters.find(chapter => chapter.id === state.selected);
    q('#chapterName').value = selected?.name ?? '';
    q('#chapterStart').value = selected ? seconds(selected.start) : '';
    q('#chapterStart').max = seconds(state.source.sampleCount - 1);
    q('#chapterProposal').textContent = state.proposal
      ? `待应用（基线 v${state.proposal.base}）：` + state.proposal.chapters.map(chapter => `${chapter.name} ${seconds(chapter.start)} 秒`).join(' → ')
      : '没有待应用的章节修订。';
    reportPosition();
  }
  async function play(generation = localGeneration, session = state.session) {
    if (disposed || generation !== localGeneration || !chapterSessionIsCurrent(state, session)) return;
    try {
      await audio.play();
      if (disposed || generation !== localGeneration || !chapterSessionIsCurrent(state, session)) return;
      if (!audio.paused) status('原生播放器已开始测试音；实际可听性仍取决于设备。');
    } catch {
      if (disposed || generation !== localGeneration || !chapterSessionIsCurrent(state, session)) return;
      halt(); send({type: 'media-error'});
      q('#chapterPlayback').textContent = '播放器未能开始。可停止循环后重试，章节修订保留。';
      draw(); status(state.notice);
    }
  }
  function fulfillLoad() {
    if (!loadIntent || disposed || audio.readyState < 1 || audio.currentSrc !== url) return;
    const intent = loadIntent;
    if (intent.generation !== localGeneration || !chapterSessionIsCurrent(state, intent.session)) return;
    loadIntent = null;
    try { audio.currentTime = intent.relativeSample / rate; }
    catch { status('当前播放器尚不能定位；请用原生控件重试。'); return; }
    reportPosition();
    if (intent.play) play(intent.generation, intent.session);
  }
  function load(samples, absoluteOffset, target, autoPlay = false, loop = false) {
    halt();
    const previousUrl = url;
    audio.removeAttribute('src');
    audio.load();
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    url = URL.createObjectURL(new Blob([encodeWav(samples, rate)], {type: 'audio/wav'}));
    offset = absoluteOffset;
    audio.loop = loop;
    loadIntent = {generation: localGeneration, session: state.session, relativeSample: target - offset, play: autoPlay};
    audio.src = url;
    audio.load();
    q('#chapterPlayback').textContent = loop
      ? `循环已准备：原音频 ${seconds(offset)}–${seconds(offset + samples.length)} 秒。原生进度条从此区间的 0 秒开始；接缝由浏览器处理。`
      : '完整测试音；选择章节只定位，播放须由你启动。';
    fulfillLoad();
  }
  function fullSourceAt(sample) {
    load(fixture.samples, 0, Math.max(0, Math.min(sample, state.source.sampleCount)));
  }
  function selectChapter(id, focus = false) {
    if (!state.chapters.some(chapter => chapter.id === id)) return;
    halt(); send({type: 'select', id});
    const sample = chapterSeekSample(state);
    fullSourceAt(sample); draw();
    if (focus) Array.from(q('#chapterList').querySelectorAll('button')).find(control => control.dataset.chapter === id)?.focus();
    status(`定位目标 ${seconds(sample)} 秒（采样 ${sample}）；不自动播放。原生播放器显示实际位置。`);
  }
  function stop() {
    const position = absoluteSample();
    halt(); send({type: 'stop'}); fullSourceAt(position); draw(); status(state.notice);
  }
  function commit(type) {
    const oldRevision = state.revision, position = absoluteSample();
    send({type});
    if (state.revision !== oldRevision) {
      halt(); fullSourceAt(position);
    }
    draw(); status(state.notice);
  }
  listen(q('#chapterSource'), 'change', event => {
    const nextFixture = fixtures[Number(event.target.value)];
    if (!nextFixture) return;
    sourceStates.set(state.source.id, captureEntry());
    halt(); fixture = nextFixture;
    const nextSession = state.session + 1;
    const previous = sourceStates.get(fixture.source.id);
    state = {...(previous?.state || initialChapters(fixture.source, fixture.chapters)), session: nextSession, loop: null,
      notice: '已切换测试音；恢复此素材的本地编辑，未自动播放。'};
    fullSourceAt(0); draw(); restoreUI(previous); status(state.notice);
  });
  for (const field of [q('#chapterName'), q('#chapterStart')]) {
    listen(field, 'input', () => {
      if (!state.proposal) return;
      send({type: 'cancel-edit'});
      q('#chapterProposal').textContent = '输入已变化；请重新预览后再应用。';
    });
  }
  listen(q('#chapterList'), 'click', event => {
    const control = event.target.closest('button[data-chapter]');
    if (control) selectChapter(control.dataset.chapter, true);
  });
  listen(q('#chapterList'), 'keydown', event => {
    const control = event.target.closest('button[data-chapter]');
    if (!control || !['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const index = state.chapters.findIndex(chapter => chapter.id === control.dataset.chapter);
    const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? state.chapters.length - 1
      : Math.max(0, Math.min(state.chapters.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1)));
    selectChapter(state.chapters[nextIndex].id, true);
  });
  listen(stage, 'keydown', event => {
    if (event.key !== 'Escape') return;
    event.preventDefault(); stop(); send({type: 'cancel-edit'}); draw(); status('已停止试听，并取消待修订。');
  });
  listen(audio, 'loadedmetadata', fulfillLoad);
  listen(audio, 'timeupdate', reportPosition);
  listen(audio, 'playing', () => {
    if (!disposed) q('#chapterPlayback').textContent = activeChapterLoop(state)
      ? `正在循环 ${seconds(offset)}–${seconds(offset + chapterAudioSamples(fixture.samples, state).length)} 秒；单一原生播放器。`
      : '正在播放完整测试音；章节名称与音频内容无识别关系。';
  });
  listen(audio, 'pause', () => {
    if (!disposed && !loadIntent) q('#chapterPlayback').textContent = activeChapterLoop(state)
      ? '循环试听已暂停；原生播放键可继续，停止循环会返回完整测试音。' : '当前测试音已暂停。';
  });
  listen(audio, 'error', () => {
    if (disposed || !audio.error || audio.currentSrc !== url) return;
    halt(); send({type: 'media-error'}); draw();
    q('#chapterPlayback').textContent = '音频无法解码或加载；没有宣称播放成功。'; status(state.notice);
  });
  listen(document, 'visibilitychange', () => { if (document.hidden && !disposed) stop(); });
  button('试听所选章节起点', () => {
    const sample = chapterSeekSample(state);
    if (sample === null) { status('请先选择章节。'); return; }
    halt(); send({type: 'stop'}); load(fixture.samples, 0, sample, true); draw();
  }, true);
  button('开始所选章节循环', () => {
    halt(); send({type: 'start-loop'});
    const loop = activeChapterLoop(state);
    if (!loop) { status(state.notice); return; }
    load(chapterAudioSamples(fixture.samples, state), loop.start, loop.start, true, true); draw();
    status('已准备真实采样区间；等待播放器开始，尚不代表可听性已验证。');
  });
  button('停止试听 / 停止循环', stop);
  button('预览章节修订', () => {
    try {
      const raw = q('#chapterStart').value;
      if (!raw.trim()) throw Error('请填写章节起点');
      const start = chapterStartFromSeconds(Number(raw), state.source);
      send({type: 'propose-edit', name: q('#chapterName').value, start}); draw(); status(state.notice);
    } catch (error) {
      send({type: 'cancel-edit'}); draw(); status(error.message + '；保留当前章节。');
    }
  });
  button('应用章节修订', () => commit('apply-edit'));
  button('取消待修订', () => { send({type: 'cancel-edit'}); draw(); status(state.notice); });
  button('撤销章节修订', () => commit('undo'));
  onDispose(() => {
    if (disposed) return;
    sourceStates.set(state.source.id, captureEntry());
    try { session?.write('chapters', {version: 1, active: fixture.source.id, sources: Object.fromEntries(sourceStates)}); }
    catch { /* storage failure must never prevent media cleanup */ }
    disposed = true; halt();
    removers.forEach(remove => remove());
    audio.removeAttribute('src'); audio.load();
    if (url) URL.revokeObjectURL(url);
    url = null;
    sourceStates.clear();
  });
  // Exact media times do not depend on animation or reduced-motion settings.
  void reduce;
  q('#chapterSource').value = String(fixtures.indexOf(fixture));
  fullSourceAt(0); draw(); restoreUI(sourceStates.get(fixture.source.id)); status(state.notice);
}
