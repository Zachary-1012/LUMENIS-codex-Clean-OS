const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'rednote_collector.cjs'), 'utf8');
const loadedModule = { exports: {} };
const safeRequire = request => {
  if (request === 'playwright') {
    return { chromium: { connectOverCDP() { throw new Error('browser access is forbidden in this test'); } } };
  }
  return require(request);
};
safeRequire.main = {};
vm.runInNewContext(source, {
  require: safeRequire,
  module: loadedModule,
  exports: loadedModule.exports,
  process: { argv: [], env: {} },
  console: { log() {}, error() {} },
});

const {
  parseCount, detailCommentFields, detailEngagementFields, normalizeSearchNote,
} = loadedModule.exports;
const fields = value => JSON.parse(JSON.stringify(value));

test('missing, placeholder, and malformed engagement counts stay unknown', () => {
  for (const raw of [
    undefined, null, '', '   ', '-', '--', '—', '暂无', '未知', 'N/A', 'abc', '0abc', '1.2K',
  ]) {
    assert.equal(parseCount(raw), null, `${String(raw)} must remain unknown`);
  }
});

test('source-visible zero and supported display formats remain measured', () => {
  assert.equal(parseCount(0), 0);
  assert.equal(parseCount('0'), 0);
  assert.equal(parseCount('1.2万'), 12000);
  assert.equal(parseCount('1,234'), 1234);
  assert.equal(parseCount('999+'), 999);
});

test('rounded display counts keep the original source text and do not mutate input', () => {
  const raw = { note_id: 'n1', likes_raw: '1.2万', publish_time_raw: '2026-09-28' };
  const normalized = normalizeSearchNote(raw);

  assert.equal(normalized.likes, 12000);
  assert.equal(normalized.likes_raw, '1.2万');
  assert.equal(normalized.collects, null);
  assert.equal(normalized.shares, null);
  assert.deepEqual(fields(raw), {
    note_id: 'n1', likes_raw: '1.2万', publish_time_raw: '2026-09-28',
  });
  assert.equal(normalizeSearchNote({ likes_raw: '0' }).likes, 0);
});

test('loaded comment items remain a collection count, not a post comment total', () => {
  assert.deepEqual(fields(detailCommentFields(true, { loaded_comment_count: 3 })), {
    comments: null,
    comment_count: null,
    comments_collected: 3,
  });
});

test('detail fallback preserves a measured zero and leaves unobserved collections unknown', () => {
  assert.deepEqual(fields(detailEngagementFields(0)), { likes: 0, collects: null });
  assert.deepEqual(fields(detailEngagementFields(null)), { likes: null, collects: null });
  assert.deepEqual(fields(detailEngagementFields(undefined)), { likes: null, collects: null });
});
