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

const { normalizePublishTime, sourceTimeFields } = loadedModule.exports;
const fields = value => JSON.parse(JSON.stringify(value));

test('publication time accepts only explicit valid calendar dates', () => {
  assert.equal(normalizePublishTime('2026-09-29'), '2026-09-29');
  assert.equal(normalizePublishTime('2024-02-29'), '2024-02-29');

  for (const raw of [
    '编辑于04-08',
    '编辑于2026-09-29',
    '04-08',
    '3天前',
    '今天',
    '刚刚',
    'unknown',
    '2026-02-29',
    '2024-02-30',
  ]) {
    assert.equal(normalizePublishTime(raw), '', `${raw} must remain unknown as publication time`);
  }
});

test('source publication and update fields keep search and detail provenance separate', () => {
  const searchRaw = ' 2026-09-28 ';
  const detailRaw = '编辑于2026-09-29';
  const search = fields(sourceTimeFields(searchRaw));
  const detail = fields(sourceTimeFields(detailRaw));

  assert.deepEqual(search, {
    source_display_time: searchRaw,
    source_published_at: '2026-09-28',
    source_updated_at: '',
    source_time_kind: 'ABSOLUTE_DATE',
    source_publication_precision: 'DATE',
  });
  assert.deepEqual(detail, {
    source_display_time: detailRaw,
    source_published_at: '',
    source_updated_at: '2026-09-29',
    source_time_kind: 'UPDATE_DISPLAY',
    source_publication_precision: 'UNKNOWN',
  });
  assert.equal(search.source_published_at, '2026-09-28');
  assert.equal(detail.source_published_at, '');
});

test('yearless, relative, and unknown source displays stay explicitly unverified', () => {
  const yearless = fields(sourceTimeFields('04-08'));
  assert.equal(yearless.source_time_kind, 'YEAR_UNKNOWN');
  assert.equal(yearless.source_published_at, '');
  assert.equal(yearless.source_updated_at, '');
  assert.equal(yearless.source_publication_precision, 'UNKNOWN');

  const yearlessUpdate = fields(sourceTimeFields('编辑于04-08'));
  assert.equal(yearlessUpdate.source_time_kind, 'UPDATE_DISPLAY');
  assert.equal(yearlessUpdate.source_published_at, '');
  assert.equal(yearlessUpdate.source_updated_at, '');

  for (const raw of ['3天前', '今天', '刚刚']) {
    const relative = fields(sourceTimeFields(raw));
    assert.equal(relative.source_time_kind, 'RELATIVE_DISPLAY');
    assert.equal(relative.source_published_at, '');
    assert.equal(relative.source_updated_at, '');
    assert.equal(relative.source_publication_precision, 'UNKNOWN');
  }

  const unknown = fields(sourceTimeFields('无法识别的时间'));
  assert.equal(unknown.source_time_kind, 'UNKNOWN');
  assert.equal(unknown.source_published_at, '');
  assert.equal(unknown.source_updated_at, '');
});

test('source time parsing preserves the input display text', () => {
  const raw = ' 编辑于2026-09-29 ';
  const before = raw;
  const result = fields(sourceTimeFields(raw));

  assert.equal(raw, before);
  assert.equal(result.source_display_time, raw);
  assert.equal(result.source_updated_at, '2026-09-29');
});
