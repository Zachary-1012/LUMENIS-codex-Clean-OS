import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { createExportVerifier } from '../src/export-verification.mjs';
if (!globalThis.crypto) globalThis.crypto = webcrypto;
// All data below are artificial fixtures, not exported product evidence.
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const bytes = new TextEncoder().encode('# Artificial fixture\n\nSources (original scopes and rights):\n[]');
const selection = { artifactId: 'ART-0123456789abcdef', version: 2, sourceArtifactSha: 'a'.repeat(64), format: 'md', generation: 7 };
function setup({ independent, owner, response, limit, acquire } = {}) {
  let generation = 7;
  const readOwner = async ({ phase }) => ({ ...selection, authorized: true,
    ...(independent === undefined ? {} : { independentExportDigest: independent }), ...owner?.(phase) });
  const verifier = createExportVerifier({ readOwner, getGeneration: () => generation, maxBytes: limit });
  return { run: (extra = {}) => verifier.verify({ selection, acquireResponse: async requestBinding => {
    if (acquire) await acquire(() => { generation++; });
    return { status: 200, requestBinding, headers: { 'Content-Type': 'text/markdown; charset=utf-8',
      'X-Source-Artifact-ID': selection.artifactId, 'X-Content-SHA256': hash(bytes) }, bytes, ...response };
  }, ...extra }) };
}
test('default Owner binding is fail closed', async () => {
  assert.equal((await createExportVerifier().verify({ selection })).code, 'OWNER_UNBOUND');
});
test('missing independent export digest never establishes authenticity or persistence', async () => {
  const result = await setup().run();
  assert.equal(result.accepted, true);
  assert.equal(result.level, 'SOURCE_BOUND_BYTE_INTEGRITY');
  assert.equal(result.authenticity, 'UNESTABLISHED');
  assert.equal(result.diskPersistence, 'NOT_ESTABLISHED');
  assert.notEqual(result.actualExportDigest, result.sourceArtifactSha);
});
test('explicit independent host digest is matched', async () => {
  const result = await setup({ independent: hash(bytes) }).run();
  assert.equal(result.level, 'INDEPENDENT_EXPORT_DIGEST_MATCH');
});
for (const [field, wrong] of Object.entries({ artifactId: 'ART-fedcba9876543210', format: 'txt', version: 1, sourceArtifactSha: 'b'.repeat(64), generation: 6 })) {
  test(`rejects wrong request ${field}`, async () => {
    assert.equal((await setup({ response: { requestBinding: { ...selection, [field]: wrong } } }).run()).code, 'REQUEST_BINDING_MISMATCH');
  });
  test(`rejects wrong Owner ${field}`, async () => {
    assert.equal((await setup({ owner: () => ({ [field]: wrong }) }).run()).code, 'OWNER_BINDING_MISMATCH');
  });
}
for (const [name, response, code] of [
  ['wrong source ID', { headers: { 'X-Source-Artifact-ID': 'ART-fedcba9876543210' } }, 'SOURCE_ID_MISMATCH'],
  ['wrong MIME', { headers: { 'X-Source-Artifact-ID': selection.artifactId, 'Content-Type': 'text/plain' } }, 'MEDIA_TYPE_MISMATCH'],
  ['empty bytes', { bytes: new Uint8Array() }, 'EMPTY_BYTES'],
  ['bad hash', { headers: { 'X-Source-Artifact-ID': selection.artifactId, 'Content-Type': 'text/markdown', 'X-Content-SHA256': 'b'.repeat(64) } }, 'CONTENT_DIGEST_MISMATCH'],
  ['non-200', { status: 403 }, 'HTTP_STATUS'],
]) test(name, async () => assert.equal((await setup({ response }).run()).code, code));
test('rejects oversized bytes', async () => assert.equal((await setup({ limit: 1 }).run()).code, 'BYTES_TOO_LARGE'));
test('self-consistent false body and response hash do not override independent expected digest', async () => {
  assert.equal((await setup({ independent: hash('different genuine content') }).run()).code, 'INDEPENDENT_DIGEST_MISMATCH');
});
test('rejects revoke after receiving bytes', async () => {
  assert.equal((await setup({ owner: phase => ({ authorized: phase === 'before' }) }).run()).code, 'NOT_AUTHORIZED');
});
test('rejects source revision changed after response', async () => {
  assert.equal((await setup({ owner: phase => ({ version: phase === 'before' ? 2 : 3 }) }).run()).code, 'OWNER_BINDING_MISMATCH');
});
test('rejects changed independent digest after response', async () => {
  assert.equal((await setup({ owner: phase => phase === 'after' ? { independentExportDigest: hash(bytes) } : {} }).run()).code, 'OWNER_DIGEST_CHANGED');
});
test('late response after generation changes is rejected', async () => {
  assert.equal((await setup({ acquire: change => change() }).run()).code, 'STALE_GENERATION');
});
test('cancellation before and during request is rejected', async () => {
  const controller = new AbortController(); controller.abort();
  assert.equal((await setup().run({ signal: controller.signal })).code, 'CANCELLED');
  const later = new AbortController();
  assert.equal((await setup({ acquire: () => later.abort() }).run({ signal: later.signal })).code, 'CANCELLED');
});
test('missing Owner authorization and throwing Owner are rejected', async () => {
  assert.equal((await setup({ owner: () => ({ authorized: undefined }) }).run()).code, 'NOT_AUTHORIZED');
  assert.equal((await setup({ owner: () => { throw Error('offline'); } }).run()).code, 'HOST_OR_VERIFICATION_FAILURE');
});
test('pure markdown hash is not the export hash when sources appendix is present', async () => {
  assert.equal((await setup({ independent: hash('# Artificial fixture') }).run()).code, 'INDEPENDENT_DIGEST_MISMATCH');
});
test('malformed response SHA is rejected', async () => {
  assert.equal((await setup({ response: { headers: { 'X-Source-Artifact-ID': selection.artifactId,
    'Content-Type': 'text/markdown', 'X-Content-SHA256': 'invalid' } } }).run()).code, 'INVALID_CONTENT_DIGEST');
});
test('unbound Owner never acquires bytes', async () => {
  let called = false;
  await createExportVerifier().verify({ selection, acquireResponse: () => { called = true; } });
  assert.equal(called, false);
});
test('invalid independent digest fails before acquisition', async () => {
  assert.equal((await setup({ independent: 'not-a-digest' }).run()).code, 'INVALID_INDEPENDENT_DIGEST');
});
test('handoff uses an isolated verified byte snapshot, not the mutable response buffer',async()=>{
 const input=new Uint8Array(bytes),result=await setup({response:{bytes:input}}).run();assert.equal(result.accepted,true);
 input.fill(0);const first=result.getVerifiedBytes();assert.equal(hash(first),result.actualExportDigest);first.fill(0);assert.equal(hash(result.getVerifiedBytes()),result.actualExportDigest);
});
test('frontend contract excludes internal JSON export',async()=>{const r=await setup().run({selection:{...selection,format:'json'}});assert.equal(r.code,'INVALID_SELECTION')});
