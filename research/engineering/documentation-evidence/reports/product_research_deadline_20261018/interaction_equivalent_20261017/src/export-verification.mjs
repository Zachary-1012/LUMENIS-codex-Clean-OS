/** Isolated review contract. Host callbacks are trust boundaries, not product APIs. */
export const EXPORT_MEDIA_TYPES = Object.freeze({
  md: 'text/markdown', txt: 'text/plain',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  pdf: 'application/pdf',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
});
const digestPattern = /^[0-9a-f]{64}$/;
const keys = ['artifactId', 'version', 'sourceArtifactSha', 'format', 'generation'];
const fail = code => { throw Object.assign(new Error(code), { contractCode: code }); };
const same = (a, b) => keys.every(key => a?.[key] === b?.[key]);
const copyBinding = value => Object.freeze(Object.fromEntries(keys.map(key => [key, value?.[key]])));
function checkSelection(s) {
  if (!/^ART-[0-9a-f]{16}$/.test(s.artifactId ?? '') ||
      !Number.isSafeInteger(s.version) || s.version < 1 ||
      !digestPattern.test(s.sourceArtifactSha ?? '') ||
      !Object.hasOwn(EXPORT_MEDIA_TYPES, s.format) ||
      !Number.isSafeInteger(s.generation) || s.generation < 0) fail('INVALID_SELECTION');
}
function header(headers, name) {
  if (typeof headers?.get === 'function') return headers.get(name);
  const entries = Object.entries(headers ?? {}).filter(([key]) => key.toLowerCase() === name.toLowerCase());
  if (entries.length !== 1 || typeof entries[0][1] !== 'string') fail('INVALID_HEADERS');
  return entries[0][1];
}
async function sha256(bytes) {
  if (!globalThis.crypto?.subtle) fail('HASH_UNAVAILABLE');
  const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
}
/**
 * readOwner({selection, phase}) must independently read the selected source record,
 * authorize current export and source access, and return all binding fields plus
 * authorized:true. Optional independentExportDigest must come from a separately
 * verified host record, never from this response or its headers.
 * acquireResponse receives the frozen request binding; its requestBinding must
 * be set by the host request adapter (never copied from response metadata).
 */
export function createExportVerifier({ readOwner, getGeneration, maxBytes = 32 * 1024 * 1024 } = {}) {
  return Object.freeze({
    async verify({ selection, acquireResponse, signal } = {}) {
      try {
        if (typeof readOwner !== 'function' || typeof getGeneration !== 'function') fail('OWNER_UNBOUND');
        if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) fail('INVALID_BYTE_LIMIT');
        const expected = copyBinding(selection);
        checkSelection(expected);
        const live = () => {
          if (signal?.aborted) fail('CANCELLED');
          if (getGeneration() !== expected.generation) fail('STALE_GENERATION');
        };
        const read = async phase => {
          live();
          const record = await readOwner({ selection: expected, phase });
          live();
          if (record?.authorized !== true) fail('NOT_AUTHORIZED');
          if (!same(record, expected)) fail('OWNER_BINDING_MISMATCH');
          const digest = record.independentExportDigest ?? null;
          if (digest !== null && !digestPattern.test(digest)) fail('INVALID_INDEPENDENT_DIGEST');
          return digest;
        };
        const independentlyExpected = await read('before');
        if (typeof acquireResponse !== 'function') fail('RESPONSE_PROVIDER_UNBOUND');
        live();
        const response = await acquireResponse(expected, signal);
        live();
        if (!same(response?.requestBinding, expected)) fail('REQUEST_BINDING_MISMATCH');
        if (response.status !== 200) fail('HTTP_STATUS');
        if (header(response.headers, 'X-Source-Artifact-ID') !== expected.artifactId) fail('SOURCE_ID_MISMATCH');
        const contentType = header(response.headers, 'Content-Type');
        if (contentType?.split(';')[0].trim().toLowerCase() !== EXPORT_MEDIA_TYPES[expected.format]) fail('MEDIA_TYPE_MISMATCH');
        const claimedDigest = header(response.headers, 'X-Content-SHA256');
        if (!digestPattern.test(claimedDigest ?? '')) fail('INVALID_CONTENT_DIGEST');
        if (!(response.bytes instanceof Uint8Array)) fail('INVALID_BYTES');
        if (!response.bytes.byteLength) fail('EMPTY_BYTES');
        if (response.bytes.byteLength > maxBytes) fail('BYTES_TOO_LARGE');
        // Copy once so caller mutation cannot change the bytes being checked.
        const bytes = new Uint8Array(response.bytes);
        const actualExportDigest = await sha256(bytes);
        live();
        if (actualExportDigest !== claimedDigest) fail('CONTENT_DIGEST_MISMATCH');
        if (independentlyExpected !== null && actualExportDigest !== independentlyExpected) fail('INDEPENDENT_DIGEST_MISMATCH');
        const afterDigest = await read('after');
        if (afterDigest !== independentlyExpected) fail('OWNER_DIGEST_CHANGED');
        live();
        return Object.freeze({
          accepted: true,
          level: independentlyExpected === null ? 'SOURCE_BOUND_BYTE_INTEGRITY' : 'INDEPENDENT_EXPORT_DIGEST_MATCH',
          authenticity: independentlyExpected === null ? 'UNESTABLISHED' : 'MATCHES_HOST_VERIFIED_DIGEST',
          binding: expected, actualExportDigest,
          getVerifiedBytes: () => new Uint8Array(bytes),
          sourceArtifactSha: expected.sourceArtifactSha,
          independentlyExpectedExportDigest: independentlyExpected,
          diskPersistence: 'NOT_ESTABLISHED',
        });
      } catch (error) {
        return Object.freeze({ accepted: false, level: 'REJECTED', authenticity: 'UNESTABLISHED',
          code: error?.contractCode ?? 'HOST_OR_VERIFICATION_FAILURE', diskPersistence: 'NOT_ESTABLISHED' });
      }
    },
  });
}
