import test from 'node:test';
import assert from 'node:assert/strict';
import {initialRiskReview, riskReviewReduce, visibleRiskRecords} from '../src/risk-review.mjs';
import {initialVersionTree, versionTreeReduce, validateVersionTree} from '../src/version-tree.mjs';
import {
  initialChapters, validateChapterSource, validateChapters, chaptersReduce,
  chapterRange, chapterSeekSample, chapterStartFromSeconds, chapterAudioSamples,
  chapterSessionIsCurrent, activeChapterLoop
} from '../src/media-chapters.mjs';

// Read-only product references, not assertions that these fixtures bind a backend:
// BMP-10 §§2–5 and lines 77–82: unknown risk/outcome, local judgment, retained history.
// SH-04 §§2,5,7: exact reopened version, immutable selected parent, unchanged retry.
// BMP-08 Script/Audio refinement and acceptance: text changes are not changed sound.
// Experience §38 lines 1343–1350,1391–1398: stale actions, edits, undo and permissions.
// Source Owner Index lines 547–551: revision parent, recovery and affected-only edits.
const risk = (state, ...events) => events.reduce(riskReviewReduce, state);
const tree = (state, ...events) => events.reduce(versionTreeReduce, state);
const chapters = (state, ...events) => events.reduce(chaptersReduce, state);
const source = {id: 'manual-tone', version: 'tone-v1', sampleRate: 8000, sampleCount: 16};
const markers = [
  {id: 'intro', name: '开场', start: 0},
  {id: 'middle', name: '观察', start: 5},
  {id: 'end', name: '结束', start: 12}
];
const chapterState = () => initialChapters(source, markers);
const savedTree = () => tree(initialVersionTree(), {type: 'edit', text: '原稿'}, {type: 'save', reason: '初稿'});

test('risk judgment requires a reason and confirmation, then remains local and repeat-safe', () => {
  const original = initialRiskReview();
  let state = risk(original, {type: 'edit', text: '  '}, {type: 'preview'}, {type: 'record'});
  assert.equal(state.records.length, 0);
  state = risk(state, {type: 'edit', text: '尚无直接依据，继续核查'}, {type: 'decision', value: 'follow-up'}, {type: 'preview'});
  assert.equal(state.records.length, 0);
  state = risk(state, {type: 'record'}, {type: 'record'});
  assert.equal(state.records.length, 1);
  assert.equal(state.records[0].decision, 'follow-up');
  assert.equal(state.records[0].outcome, 'NOT_OBSERVED');
  assert.equal(state.items[0].severity, null);
  assert.equal(state.proposal, null);
  assert.equal(original.draft, '');
  assert.equal(original.records.length, 0);
});

test('risk edit, decision change and explicit cancel invalidate an already reviewed proposal', () => {
  const previewed = risk(initialRiskReview(), {type: 'edit', text: '待核查'}, {type: 'preview'});
  for (const event of [{type: 'edit', text: '补充后的判断'}, {type: 'decision', value: 'false-positive'}, {type: 'cancel-draft'}]) {
    const state = risk(previewed, event, {type: 'record'});
    assert.equal(state.records.length, 0, event.type);
    assert.equal(state.proposal, null, event.type);
  }
  assert.equal(previewed.proposal.text, '待核查');
});

test('risk source withdrawal fences stale confirmation and marks history without rewriting it', () => {
  let state = risk(initialRiskReview(), {type: 'edit', text: '已核查的旧判断'}, {type: 'preview'}, {type: 'record'});
  const history = structuredClone(state.records);
  state = risk(state, {type: 'edit', text: '尚未确认的判断'}, {type: 'preview'}, {type: 'withdraw-source'}, {type: 'record'});
  assert.deepEqual(state.records, history);
  assert.equal(state.draft, '尚未确认的判断');
  assert.equal(state.items[0].sourceVersion, 2);
  assert.equal(visibleRiskRecords(state)[0].impacted, true);
  assert.equal(visibleRiskRecords(state)[0].sourceVersion, 1);
  assert.equal(visibleRiskRecords(state)[0].sourceWithdrawn, false);
  assert.equal(visibleRiskRecords(state)[0].outcome, 'NOT_OBSERVED');
});

test('risk revocation hides retained history and blocks both old and fresh confirmations', () => {
  let state = risk(initialRiskReview(), {type: 'edit', text: '历史'}, {type: 'preview'}, {type: 'record'});
  const history = structuredClone(state.records);
  state = risk(state, {type: 'edit', text: '未提交'}, {type: 'preview'}, {type: 'revoke'}, {type: 'record'}, {type: 'preview'}, {type: 'record'});
  assert.equal(state.allowed, false);
  assert.equal(state.proposal, null);
  assert.deepEqual(visibleRiskRecords(state), []);
  assert.deepEqual(state.records, history);
  assert.equal(state.draft, '未提交');
});

test('risk selection preserves an unsaved judgment and isolates each item history', () => {
  let state = risk(initialRiskReview(), {type: 'edit', text: '仅针对线索 A'}, {type: 'select', id: 'signal-b'});
  assert.equal(state.selected, 'signal-a');
  assert.equal(state.draft, '仅针对线索 A');
  state = risk(state, {type: 'preview'}, {type: 'record'}, {type: 'select', id: 'signal-b'});
  assert.equal(state.selected, 'signal-b');
  assert.deepEqual(visibleRiskRecords(state), []);
  state = risk(state, {type: 'select', id: 'signal-a'});
  assert.equal(visibleRiskRecords(state)[0].text, '仅针对线索 A');
});

test('version save preserves immutable parent bytes, and repeated save creates no version', () => {
  const original = savedTree();
  const state = tree(original, {type: 'edit', text: '第二稿'}, {type: 'save', reason: '补充说明'}, {type: 'save'});
  assert.equal(state.versions.length, 2);
  assert.deepEqual(state.versions[0], original.versions[0]);
  assert.equal(state.versions[1].parent, original.head);
  assert.equal(state.versions[1].reason, '补充说明');
  assert.equal(state.dirty, false);
  assert.deepEqual(validateVersionTree(JSON.parse(JSON.stringify(state))), state);
});

test('version inspection does not overwrite editing; explicit old-content adoption creates a new child', () => {
  let state = tree(savedTree(), {type: 'edit', text: '第二稿'}, {type: 'save'}, {type: 'edit', text: '未保存的第三稿'});
  const old = state.versions[0], head = state.head;
  state = tree(state, {type: 'inspect', id: old.id});
  assert.equal(state.draft, '未保存的第三稿');
  assert.equal(state.head, head);
  state = tree(state, {type: 'adopt-old'});
  assert.equal(state.draft, old.text);
  assert.equal(state.base, head);
  assert.equal(state.versions.length, 2);
  state = tree(state, {type: 'save', reason: '明确恢复原文'});
  assert.equal(state.versions[2].text, old.text);
  assert.equal(state.versions[2].parent, head);
  assert.deepEqual(state.versions[0], old);
});

test('concurrent head change blocks overwrite while allowing an explicit branch from the original base', () => {
  let state = tree(savedTree(), {type: 'edit', text: '我的未保存修改'});
  const base = state.base;
  state = tree(state, {type: 'external-version'});
  const external = state.head;
  state = tree(state, {type: 'save'});
  assert.equal(state.versions.length, 2);
  assert.equal(state.draft, '我的未保存修改');
  assert.equal(state.dirty, true);
  state = tree(state, {type: 'branch'}, {type: 'branch'});
  assert.equal(state.versions.length, 3);
  assert.equal(state.versions[2].parent, base);
  assert.equal(state.versions[2].text, '我的未保存修改');
  assert.equal(state.head, external);
});

test('saved branch becomes the next draft base and cannot silently overwrite the main head', () => {
  let state = tree(savedTree(), {type: 'edit', text: '分支稿'}, {type: 'branch'});
  const branch = state.viewing, head = state.head;
  assert.equal(state.base, branch, 'clean draft must identify the version that saved its bytes');
  state = tree(state, {type: 'edit', text: '分支下一稿'}, {type: 'save'});
  assert.equal(state.versions.length, 2, 'branch edit cannot claim to be based on the main head');
  assert.equal(state.head, head);
  assert.equal(state.draft, '分支下一稿');
  state = tree(state, {type: 'branch'});
  assert.equal(state.versions[2].parent, branch);
  assert.equal(state.base, state.viewing);
  assert.equal(state.head, head);
});

test('validated restored IDs cannot collide with newly saved, branched or external versions', () => {
  const restored = validateVersionTree({
    versions: [{id: 'local-v2', parent: null, text: '恢复原稿', reason: '恢复'}],
    head: 'local-v2', viewing: 'local-v2', base: 'local-v2', draft: '恢复原稿', dirty: false, notice: ''
  });
  for (const type of ['save', 'branch', 'external-version']) {
    const state = tree(restored, {type: 'edit', text: '新稿'}, {type});
    assert.equal(new Set(state.versions.map(v => v.id)).size, state.versions.length, type);
    assert.equal(state.versions[1].parent, restored.head, type);
    assert.doesNotThrow(() => validateVersionTree(JSON.parse(JSON.stringify(state))), type);
  }
  assert.equal(restored.versions.length, 1);
});

test('version readback rejects damaged ancestry, duplicate IDs, missing references and oversized data', () => {
  const valid = savedTree();
  const damaged = [
    {...valid, versions: [...valid.versions, {...valid.versions[0]}]},
    {...valid, versions: [{...valid.versions[0], parent: 'missing'}]},
    {...valid, head: 'missing'}, {...valid, base: 'missing'}, {...valid, viewing: 'missing'},
    {...valid, draft: 'x'.repeat(50001)}, {...valid, dirty: 'false'},
    {...valid, versions: [{...valid.versions[0], text: 'x'.repeat(50001)}]}
  ];
  for (const state of damaged) assert.throws(() => validateVersionTree(state));
  const reopened = validateVersionTree(JSON.parse(JSON.stringify(valid)));
  reopened.versions[0].text = 'caller edit';
  assert.equal(valid.versions[0].text, '原稿');
});

test('chapter boundaries are half-open exact samples and extracting a chapter leaves audio unchanged', () => {
  const state = chapterState();
  const samples = Float32Array.from({length: source.sampleCount}, (_, i) => i / source.sampleCount);
  const before = samples.slice();
  assert.deepEqual(chapterRange(state, 'intro'), {start: 0, end: 5});
  assert.deepEqual(chapterRange(state, 'middle'), {start: 5, end: 12});
  assert.deepEqual(chapterRange(state, 'end'), {start: 12, end: 16});
  assert.deepEqual(chapterAudioSamples(samples, state, 'middle'), samples.slice(5, 12));
  assert.equal(chapterSeekSample(state, 'end'), 12);
  assert.equal(chapterRange(state, 'missing'), null);
  assert.equal(chapterSeekSample(state, 'missing'), null);
  assert.deepEqual(samples, before);
  assert.throws(() => chapterAudioSamples(new Float32Array(15), state));
  assert.throws(() => chapterAudioSamples(Float32Array.from([...samples.slice(0, 15), NaN]), state));
});

test('chapter time conversion accepts first and last samples, rounds explicitly, and rejects the endpoint', () => {
  assert.equal(chapterStartFromSeconds(0, source), 0);
  assert.equal(chapterStartFromSeconds(15 / 8000, source), 15);
  assert.equal(chapterStartFromSeconds(4.6 / 8000, source), 5);
  assert.equal(chapterStartFromSeconds(4.4 / 8000, source), 4);
  for (const seconds of [-1, NaN, Infinity, '0', 16 / 8000, 15.6 / 8000]) {
    assert.throws(() => chapterStartFromSeconds(seconds, source));
  }
});

test('chapter validators reject invalid source units and duplicate, overlapping or out-of-range markers', () => {
  for (const patch of [{id: ''}, {version: ''}, {sampleRate: 7999}, {sampleRate: 48001}, {sampleRate: 8000.5}, {sampleCount: 0}, {sampleCount: 1.5}, {sampleCount: 480001}]) {
    assert.throws(() => validateChapterSource({...source, ...patch}));
  }
  for (const patch of [{id: 'intro'}, {name: '  '}, {start: 0}, {start: -1}, {start: 16}, {start: 5.5}]) {
    assert.throws(() => validateChapters([markers[0], {...markers[1], ...patch}], source));
  }
  const empty = initialChapters(source);
  assert.equal(chapterRange(empty), null);
  assert.equal(activeChapterLoop(chapters(empty, {type: 'start-loop'})), null);
});

test('chapter proposal reorders only metadata; apply stops the old session and undo restores exact markers', () => {
  const original = chapterState();
  let state = chapters(original, {type: 'start-loop', id: 'middle'});
  const playing = state.session;
  state = chapters(state, {type: 'propose-edit', name: ' 移到末尾 ', start: 14});
  assert.deepEqual(state.chapters, original.chapters);
  assert.equal(state.revision, 1);
  assert.deepEqual(state.proposal.chapters.map(c => c.id), ['intro', 'end', 'middle']);
  state = chapters(state, {type: 'apply-edit'});
  assert.deepEqual(state.source, source);
  assert.equal(state.chapters.at(-1).name, '移到末尾');
  assert.deepEqual(chapterRange(state, 'middle'), {start: 14, end: 16});
  assert.equal(chapterSessionIsCurrent(state, playing), false);
  assert.equal(activeChapterLoop(state), null);
  assert.equal(state.revision, 2);
  state = chapters(state, {type: 'undo'});
  assert.deepEqual(state.chapters, original.chapters);
  assert.equal(state.selected, 'middle');
  assert.equal(state.revision, 3);
  assert.equal(state.proposal, null);
  assert.equal(state.loop, null);
  assert.deepEqual(original, chapterState());
});

test('chapter cancel, no-change apply and repeated apply create no phantom revision or undo entry', () => {
  let state = chapters(chapterState(), {type: 'propose-edit', name: '开场', start: 0}, {type: 'apply-edit'});
  assert.equal(state.revision, 1);
  assert.equal(state.history.length, 0);
  state = chapters(state, {type: 'propose-edit', name: '已取消', start: 1}, {type: 'cancel-edit'}, {type: 'apply-edit'});
  assert.equal(state.revision, 1);
  assert.deepEqual(state.chapters, markers);
  state = chapters(state, {type: 'propose-edit', name: '新开场', start: 1}, {type: 'apply-edit'}, {type: 'apply-edit'});
  assert.equal(state.revision, 2);
  assert.equal(state.history.length, 1);
  state = chapters(state, {type: 'undo'}, {type: 'undo'});
  assert.equal(state.revision, 3);
  assert.deepEqual(state.chapters, markers);
});

test('chapter undo invalidates a proposal made after the saved edit instead of reapplying stale metadata', () => {
  let state = chapters(chapterState(), {type: 'propose-edit', name: '第一改', start: 1}, {type: 'apply-edit'});
  state = chapters(state, {type: 'propose-edit', name: '未应用的第二改', start: 2}, {type: 'undo'}, {type: 'apply-edit'});
  assert.deepEqual(state.chapters, markers);
  assert.equal(state.revision, 3);
  assert.equal(state.proposal, null);
  assert.equal(state.history.length, 0);
});

test('chapter source replacement rejects old playback and proposals and cannot undo into another source', () => {
  let state = chapters(chapterState(), {type: 'propose-edit', name: '已改', start: 1}, {type: 'apply-edit'}, {type: 'start-loop'});
  const oldSession = state.session;
  state = chapters(state, {type: 'propose-edit', name: '旧素材提案', start: 2});
  state = chapters(state, {type: 'select-source', source: {...source, version: 'tone-v2', sampleCount: 24}, chapters: [{id: 'new', name: '新素材', start: 3}]});
  assert.equal(chapterSessionIsCurrent(state, oldSession), false);
  assert.equal(state.history.length, 0);
  assert.equal(state.proposal, null);
  assert.equal(state.loop, null);
  state = chapters(state, {type: 'apply-edit'}, {type: 'undo'});
  assert.equal(state.source.version, 'tone-v2');
  assert.deepEqual(state.chapters, [{id: 'new', name: '新素材', start: 3}]);
});

test('chapter stale version checks independently fence revision, source identity and source version', () => {
  const previewed = chapters(chapterState(), {type: 'propose-edit', name: '待应用', start: 1});
  for (const state of [
    {...previewed, revision: previewed.revision + 1},
    {...previewed, source: {...source, id: 'other'}},
    {...previewed, source: {...source, version: 'tone-v2'}}
  ]) {
    const result = chapters(state, {type: 'apply-edit'});
    assert.deepEqual(result.chapters, markers);
    assert.equal(result.history.length, 0);
    assert.equal(result.proposal, null);
  }
});

test('chapter invalid replacement and playback failure stop playback while preserving usable edits', () => {
  const edited = chapters(chapterState(), {type: 'propose-edit', name: '人工改名', start: 1}, {type: 'apply-edit'});
  for (const event of [
    {type: 'select-source', source: {...source, sampleCount: 0}, chapters: markers},
    {type: 'media-error'}, {type: 'stop'}, {type: 'select', id: 'middle'}
  ]) {
    const playing = chapters(edited, {type: 'start-loop'});
    const result = chapters(playing, event);
    assert.equal(chapterSessionIsCurrent(result, playing.session), false, event.type);
    assert.equal(activeChapterLoop(result), null, event.type);
    assert.deepEqual(result.chapters, edited.chapters, event.type);
    assert.deepEqual(result.source, edited.source, event.type);
    assert.deepEqual(result.history, edited.history, event.type);
  }
});

test('chapter loop readback is rejected when its session, version, source or sample range no longer matches', () => {
  const playing = chapters(chapterState(), {type: 'start-loop', id: 'middle'});
  assert.deepEqual({start: activeChapterLoop(playing).start, end: activeChapterLoop(playing).end}, {start: 5, end: 12});
  for (const state of [
    {...playing, session: playing.session + 1}, {...playing, revision: playing.revision + 1},
    {...playing, source: {...source, version: 'v2'}}, {...playing, source: {...source, id: 'other'}},
    {...playing, chapters: playing.chapters.map(c => c.id === 'middle' ? {...c, start: 6} : c)}
  ]) assert.equal(activeChapterLoop(state), null);
  const repeated = chapters(playing, {type: 'start-loop', id: 'end'});
  assert.equal(chapterSessionIsCurrent(repeated, playing.session), false);
  assert.equal(activeChapterLoop(repeated).id, 'end');
});
