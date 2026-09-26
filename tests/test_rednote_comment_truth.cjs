const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'rednote_collector.cjs'), 'utf8');
const loadedModule = { exports: {} };
const safeRequire = request => {
  if (request === 'playwright') return { chromium: {} };
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

const { detailCommentFields } = loadedModule.exports;
const fields = (...args) => JSON.parse(JSON.stringify(detailCommentFields(...args)));

test('failed detail keeps all comment metrics unknown', () => {
  assert.deepEqual(fields(false, { all_counts: [0], comment_count: 0 }), {
    comments: null,
    comment_count: null,
    comments_collected: null,
  });
});

test('unscoped single and trailing comment-like counts never become post comments', () => {
  const oneCount = { all_counts: [42], comment_count: 0 };
  const trailingCommentLike = { all_counts: [100, 18, 4, 7], comment_count: 0 };
  assert.deepEqual(fields(true, oneCount), {
    comments: null,
    comment_count: 0,
    comments_collected: 0,
  });
  assert.deepEqual(fields(true, trailingCommentLike), {
    comments: null,
    comment_count: 0,
    comments_collected: 0,
  });
});

test('loaded comment items retain explicit zero and measured positive counts', () => {
  assert.deepEqual(fields(true, { all_counts: [], comment_count: 0 }), {
    comments: null,
    comment_count: 0,
    comments_collected: 0,
  });
  assert.deepEqual(fields(true, { all_counts: [0], comment_count: 3 }), {
    comments: null,
    comment_count: 3,
    comments_collected: 3,
  });
});

test('missing or nonnumeric loaded comment counts remain unknown', () => {
  assert.deepEqual(fields(true, { all_counts: [42] }), {
    comments: null,
    comment_count: null,
    comments_collected: null,
  });
  assert.deepEqual(fields(true, { all_counts: [], comment_count: 'unknown' }), {
    comments: null,
    comment_count: null,
    comments_collected: null,
  });
});
